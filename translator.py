# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

import enum
import sys
from pathlib import Path
from typing import BinaryIO, Callable, Final, NamedTuple, Sequence, overload

from qtpy.QtCore import QLocale

from fmt import FMT
from numerus import getNumerusInfo
from translatormessage import TranslatorMessage, TranslatorSaveMode


# A struct of "interesting" data passed to and from the load and save routines
class ConversionData:
    def __init__(self) -> None:
        self.m_defaultContext: str = ''
        self.m_sourceIsUtf16: bool = False  # CPP & JAVA specific
        self.m_unTrPrefix: str = ''  # QM specific
        self.m_sourceFileName: str = ''
        self.m_targetFileName: str = ''
        self.m_compilationDatabaseDir: str = ''
        self.m_excludes: list[str] = []
        self.m_sourceDir: Path | None = None
        self.m_targetDir: Path | None = None  # FIXME: TS specific
        self.m_projectRoots: set[str] = set()
        self.m_allCSources: dict[str, str] = dict()
        self.m_includePath: list[str] = []
        self.m_dropTags: list[str] = []  # tags to be dropped
        self.m_errors: list[str] = []
        self.m_verbose: bool = False
        self.m_ignoreUnfinished: bool = False
        self.m_sortContexts: bool = False
        self.m_noUiLines: bool = False
        self.m_idBased: bool = False
        self.m_saveMode: TranslatorSaveMode = TranslatorSaveMode.SaveEverything
        self.m_rootDirs: list[str] = []

    # tag manipulation

    def dropTags(self) -> Sequence[str]:
        return self.m_dropTags

    def targetDir(self) -> Path:
        return self.m_targetDir

    def isVerbose(self) -> bool:
        return self.m_verbose

    def ignoreUnfinished(self) -> bool:
        return self.m_ignoreUnfinished

    def sortContexts(self) -> bool:
        return self.m_sortContexts

    def appendError(self, error: str) -> None:
        self.m_errors.append(error)

    def error(self) -> str:
        if self.m_errors:
            return '\n'.join(self.m_errors) + '\n'
        return ''

    def errors(self) -> Sequence[str]:
        return self.m_errors

    def clearErrors(self) -> None:
        self.m_errors.clear()


class TMMKey:
    def __init__(self, msg: TranslatorMessage) -> None:
        self.context = msg.context()
        self.source = msg.sourceText()
        self.comment = msg.comment()

    def __eq__(self, other: 'TMMKey') -> bool:
        return self.context == other.context and self.source == other.source and self.comment == other.comment

    def __hash__(self) -> int:
        return hash(self.context) ^ hash(self.source) ^ hash(self.comment)


def elidedId(id_: str, length: int) -> str:
    return id_ if len(id_) <= length else id_[:length - 5] + '[...]'


def makeMsgId(msg: TranslatorMessage) -> str:
    id_: str = msg.context() + '//' + elidedId(msg.sourceText(), 100)
    if msg.comment():
        id_ += '//' + elidedId(msg.comment(), 30)
    return id_


def guessFormat(filename: str | Path, fmt: str = 'auto') -> str:
    if not isinstance(filename, Path):
        filename = Path(filename)

    if fmt != 'auto':
        return fmt

    _fmt: Translator.FileFormat
    for _fmt in Translator.registeredFileFormats():
        if filename.suffix.casefold() == '.' + _fmt.extension.casefold():
            return _fmt.extension

    # the default format.
    # FIXME: change to something more widely distributed later.
    return 'ts'


class TranslatorMessagePtrBase:
    def __init__(self, tor: 'Translator', messageIndex: int) -> None:
        self.tor: Final['Translator'] = tor
        self.messageIndex: Final[int] = messageIndex


class TranslatorMessageIdPtr(TranslatorMessagePtrBase):
    def __hash__(self) -> int:
        return hash(self.tor.message(self.messageIndex).id())

    def __eq__(self, other: 'TranslatorMessageIdPtr') -> bool:
        message: TranslatorMessage = self.tor.message(self.messageIndex)
        other_message: TranslatorMessage = other.tor.message(other.messageIndex)
        return message.id() == other_message.id()


class TranslatorMessageContentPtr(TranslatorMessagePtrBase):
    def __hash__(self) -> int:
        # FIXME: in the Qt source, the function is different, but looks wrong
        message: TranslatorMessage = self.tor.message(self.messageIndex)
        h: int = hash(message.context()) ^ hash(message.sourceText())
        if not message.sourceText():
            # Special treatment for context comments (empty source).
            h ^= hash(message.comment())
        return h

    def __eq__(self, other: 'TranslatorMessageContentPtr') -> bool:
        message: TranslatorMessage = self.tor.message(self.messageIndex)
        other_message: TranslatorMessage = other.tor.message(other.messageIndex)
        if message.context() != other_message.context() or message.sourceText() != other_message.sourceText():
            return False
        # Special treatment for context comments (empty source).
        if not message.sourceText():
            return True
        return message.comment() == other_message.comment()


class Translator:
    # registration of file formats
    SaveFunction = Callable[['Translator', BinaryIO, ConversionData], bool]
    LoadFunction = Callable[['Translator', BinaryIO, ConversionData], bool]

    class FileFormat:
        def __init__(self):
            self.untranslatedDescription: str | None = None
            self.loader: Translator.LoadFunction | None = None
            self.saver: Translator.SaveFunction | None = None
            self.priority: int = -1  # 0 = highest, -1 = invisible
            self.extension: str = ''  # such as "ts", "xlf"

        def description(self):
            """ human-readable description """
            return FMT.tr(self.untranslatedDescription)

        class FileType(enum.Enum):
            TranslationSource = enum.auto()
            TranslationBinary = enum.auto()

        fileType = FileType

    _theFormats: list['Translator.FileFormat'] = []

    def __init__(self) -> None:
        self.m_messages: list[TranslatorMessage] = []
        self.m_locationsType: Translator.LocationsType = Translator.LocationsType.AbsoluteLocations
        
        # A string beginning with a 2 or 3 letter language code (ISO 639-1
        # or ISO-639-2), followed by the optional territory variant to distinguish
        # between territory-specific variations of the language. The language code
        # and territory code are always separated by '_'
        # Note that the language part can also be a 3-letter ISO 639-2 code.
        # Legal examples:
        # 'pt'         portuguese, assumes portuguese from portugal
        # 'pt_BR'      Brazilian portuguese (ISO 639-1 language code)
        # 'por_BR'     Brazilian portuguese (ISO 639-2 language code)
        self.m_language: str = ''
        self.m_sourceLanguage: str = ''
        self.m_dependencies: list[str] = []
        self.m_extra: Translator.ExtraData = dict()
        self.m_indexOk: bool = True
        self.m_ctxCmtIdx: dict[str, int] = dict()
        self.m_idMsgIdx: dict[str, int] = dict()
        self.m_msgIdx: dict[TMMKey, int] = dict()

    def load(self, filename: Path, cd: ConversionData, fmt: str = 'auto') -> bool:
        cd.m_sourceDir = Path(filename).parent.absolute()
        cd.m_sourceFileName = str(filename)

        file: BinaryIO
        try:
            with open(filename if (filename and filename != '-') else sys.stdin.fileno(), 'rb') as file:
                fmt_extension: str = guessFormat(filename, fmt)

                f: Translator.FileFormat
                for f in Translator.registeredFileFormats():
                    if fmt_extension == f.extension:
                        if f.loader is not None:
                            return f.loader(self, file, cd)
                        cd.appendError(f'No loader for format {fmt_extension} found')
                        return False

            cd.appendError(f'Unknown format {fmt} for file {filename}')
        except OSError as ex:
            cd.appendError(f'Cannot open {filename}: {ex}')
        return False

    def save(self, filename: Path, cd: ConversionData, fmt: str = 'auto') -> bool:
        file: BinaryIO
        try:
            with open(filename if (filename and filename != '-') else sys.stdin.fileno(), 'wb') as file:
                fmt_extension: str = guessFormat(filename, fmt)
                cd.m_targetDir = Path(filename).parent.absolute()

                f: Translator.FileFormat
                for f in Translator.registeredFileFormats():
                    if fmt_extension == f.extension:
                        if f.saver is not None:
                            return f.saver(self, file, cd)
                        cd.appendError(f'Cannot save {fmt_extension} files')
                        return False

            cd.appendError(f'Unknown format {fmt} for file {filename}')
        except OSError as ex:
            cd.appendError(f'Cannot create {filename}: {ex}')
        return False

    @overload
    def find(self, msg: TranslatorMessage) -> int:
        pass

    @overload
    def find(self, context: str, comment: str, refs: TranslatorMessage.References) -> int:
        pass

    @overload
    def find(self, context: str) -> int:
        pass

    def find(self, context_or_msg: str | TranslatorMessage,
             comment: str = '', refs: TranslatorMessage.References = ()) -> int:
        i: int = -1
        if isinstance(context_or_msg, TranslatorMessage):
            msg: TranslatorMessage = context_or_msg
            self.ensureIndexed()
            if msg.id():
                return self.m_msgIdx.get(TMMKey(msg), -1)
            i: int = self.m_idMsgIdx.get(msg.id(), -1)
            if i >= 0:
                return i
            i = self.m_msgIdx.get(TMMKey(msg), -1)
            # If both have an id, then find only by id.
            if i >= 0 and not self.m_messages[i].id():  # FIXME: id() is empty??
                return i
        elif isinstance(context_or_msg, str):
            context: str = context_or_msg
            if refs:
                it: TranslatorMessage
                for i, it in enumerate(self.m_messages):
                    if it.context() == context and it.comment() == comment:
                        all_references: TranslatorMessage.References = it.allReferences()
                        it_ref: TranslatorMessage.Reference
                        for it_ref in all_references:
                            if it_ref in refs:
                                return i
            else:
                self.ensureIndexed()
                return self.m_ctxCmtIdx.get(context, -1)
        return i

    def replaceSorted(self, msg: TranslatorMessage) -> None:
        index: int = self.find(msg)
        if index == -1:
            self.appendSorted(msg)
        else:
            self.delIndex(index)
            self.m_messages[index] = msg
            self.addIndex(index, msg)

    def extend(self, msg: TranslatorMessage, cd: ConversionData) -> None:  # Only for single-location messages
        index: int = self.find(msg)
        if index == -1:
            self.append(msg)
        else:
            emsg: TranslatorMessage = self.m_messages[index]
            if not emsg.sourceText():
                self.delIndex(index)
                emsg.setSourceText(msg.sourceText())
                self.addIndex(index, msg)
            elif msg.sourceText() and emsg.sourceText() != msg.sourceText():
                cd.appendError(f"Contradicting source strings for message with id '{emsg.id()}'.")
                return
            if not emsg.extras():
                emsg.setExtras(msg.extras())
            elif msg.extras() and emsg.extras() != msg.extras():
                if emsg.id():
                    cd.appendError(f"Contradicting meta data for message with id '{emsg.id()}'.")
                else:
                    cd.appendError(f"Contradicting meta data for message '{makeMsgId(msg)}'.")
                return
            emsg.addReferenceUniq(msg.fileName(), msg.lineNumber())
            if msg.extraComment():
                cmt: str = emsg.extraComment()
                if cmt:
                    cmts: list[str] = cmt.split("\n----------\n")
                    if msg.extraComment() not in cmts:
                        cmts.append(msg.extraComment())
                        cmt = "\n----------\n".join(cmts)
                else:
                    cmt = msg.extraComment()
                emsg.setExtraComment(cmt)

    def append(self, msg: TranslatorMessage) -> None:
        self.insert(len(self.m_messages), msg)

    def appendSorted(self, msg: TranslatorMessage) -> None:
        msg_line: int = msg.lineNumber()
        if msg_line < 0:
            self.append(msg)
            return

        best_idx: int = 0  # Best insertion point found so far
        best_score: int = 0  # Its category: 0 = no hit, 1 = pre or post, 2 = middle
        best_size: int = 0  # The length of the region. Longer is better within one category.

        # The insertion point to use should this region turn out to be the best one so far
        this_idx: int = 0
        this_score: int = 0
        this_size: int = 0
        # Working vars
        prev_line: int = 0
        cur_idx: int = 0
        mit: TranslatorMessage
        for mit in self.m_messages:
            same_file: bool = mit.fileName() == msg.fileName() and mit.context() == msg.context()
            cur_line: int = mit.lineNumber()
            if same_file and cur_line >= prev_line:
                if prev_line <= msg_line < cur_line:
                    this_idx = cur_idx
                    this_score = 2 if this_size else 1
                this_size += 1
                prev_line = cur_line
            elif this_size:
                if not this_score:
                    this_idx = cur_idx
                    this_score = 1
                if this_score > best_score or (this_score == best_score and this_size > best_size):
                    best_idx = this_idx
                    best_score = this_score
                    best_size = this_size
                this_score = 0
                this_size = 1 if same_file else 0
                prev_line = 0
            cur_idx += 1
        if this_size and not this_score:
            this_idx = cur_idx
            this_score = 1
        if this_score > best_score or (this_score == best_score and this_size > best_size):
            self.insert(this_idx, msg)
        elif best_score:
            self.insert(best_idx, msg)
        else:
            self.append(msg)

    def stripObsoleteMessages(self) -> None:
        i: int = 0
        while i < len(self.m_messages):
            if self.m_messages[i].type() in (TranslatorMessage.Type.Obsolete, TranslatorMessage.Type.Vanished):
                del self.m_messages[i]
                self.m_indexOk = False
            else:
                i += 1

    def stripFinishedMessages(self) -> None:
        i: int = 0
        while i < len(self.m_messages):
            if self.m_messages[i].type() in (TranslatorMessage.Type.Finished, ):
                del self.m_messages[i]
                self.m_indexOk = False
            else:
                i += 1

    def stripUntranslatedMessages(self) -> None:
        i: int = 0
        while i < len(self.m_messages):
            if not self.m_messages[i].isTranslated():
                del self.m_messages[i]
                self.m_indexOk = False
            else:
                i += 1

    def stripEmptyContexts(self) -> None:
        i: int = 0
        while i < len(self.m_messages):
            if self.m_messages[i].sourceText() == ContextComment:
                del self.m_messages[i]
                self.m_indexOk = False
            else:
                i += 1

    def stripNonPluralForms(self) -> None:
        i: int = 0
        while i < len(self.m_messages):
            if not self.m_messages[i].isPlural():
                del self.m_messages[i]
                self.m_indexOk = False
            else:
                i += 1

    def stripIdenticalSourceTranslations(self) -> None:
        i: int = 0
        while i < len(self.m_messages):
            if list(self.m_messages[i].translations()) == [self.m_messages[i].sourceText()]:
                del self.m_messages[i]
                self.m_indexOk = False
            else:
                i += 1

    def dropTranslations(self) -> None:
        message: TranslatorMessage
        for message in self.m_messages:
            if message.type() == TranslatorMessage.Type.Finished:
                message.setType(TranslatorMessage.Type.Unfinished)
            message.setTranslation('')

    def dropUiLines(self) -> None:
        ui_xt: Final[str] = '.ui'
        jui_xt: Final[str] = '.jui'
        message: TranslatorMessage
        for message in self.m_messages:
            have: dict[str, int] = dict()
            refs: TranslatorMessage.References = []
            it_ref: TranslatorMessage.Reference
            for it_ref in message.allReferences():
                fn: str = it_ref.fileName()
                if fn.casefold().endswith(ui_xt) or fn.casefold().endswith(jui_xt):
                    have[fn] += 1
                    if have[fn] == 1:
                        refs.append(TranslatorMessage.Reference(fn, -1))
                    else:
                        refs.append(it_ref)
            message.setReferences(refs)

    def makeFileNamesAbsolute(self, originalPath: Path) -> None:
        """ Used by `lupdate` to be able to search using absolute paths during merging """
        msg: TranslatorMessage
        for msg in self.m_messages:
            refs: TranslatorMessage.References = msg.allReferences()
            msg.clearReferences()
            ref: TranslatorMessage.Reference
            for ref in refs:
                msg.addReference(str(originalPath / Path(ref.fileName())), ref.lineNumber())

    def translationsExist(self) -> bool:
        message: TranslatorMessage
        return any(message.isTranslated() for message in self.m_messages)

    class Duplicates(NamedTuple):
        byId: set[int] = set()
        byContents: set[int] = set()

    def resolveDuplicates(self) -> Duplicates:
        dups: Translator.Duplicates = Translator.Duplicates()
        id_refs: set[TranslatorMessageIdPtr] = set()
        content_refs: set[TranslatorMessageContentPtr] = set()
        i: int = 0
        while i < len(self.m_messages):
            msg: TranslatorMessage = self.m_messages[i]
            omsg: TranslatorMessage = TranslatorMessage()
            oi: int = 0
            p_dup: set[int] = set()
            got_dupe: bool = False
            if msg.id():
                if TranslatorMessageIdPtr(self, i) in id_refs:
                    ip: TranslatorMessageIdPtr = id_refs.intersection([TranslatorMessageIdPtr(self, i)]).pop()
                    oi = ip.messageIndex
                    omsg = self.m_messages[oi]
                    p_dup = dups.byId
                    got_dupe = True
            if not got_dupe:
                if TranslatorMessageContentPtr(self, i) in content_refs:
                    cp: TranslatorMessageContentPtr \
                        = content_refs.intersection([TranslatorMessageContentPtr(self, i)]).pop()
                    oi = cp.messageIndex
                    omsg = self.m_messages[oi]
                    if not msg.id() or not omsg.id():
                        if msg.id() and not omsg.id():
                            omsg.setId(msg.id())
                            id_refs.add(TranslatorMessageIdPtr(self, oi))
                        p_dup = dups.byContents
                        got_dupe = True
            if not got_dupe:
                if msg.id():
                    id_refs.add(TranslatorMessageIdPtr(self, i))
                content_refs.add(TranslatorMessageContentPtr(self, i))
                i += 1
            else:
                p_dup.add(oi)
                if not omsg.isTranslated() and msg.isTranslated():
                    omsg.setTranslations(msg.translations())
                self.m_indexOk = False
                del msg, self.m_messages[i]

        return dups

    def reportDuplicates(self, dupes: Duplicates, fileName: Path, verbose: bool) -> None:
        if dupes.byId or dupes.byContents:
            sys.stderr.write(f"Warning: dropping duplicate messages in '{fileName}'")
            if not verbose:
                sys.stderr.write('\n(try -verbose for more info).\n')
            else:
                sys.stderr.write(':\n')
                i: int
                for i in dupes.byId:
                    sys.stderr.write(f'\n* ID: {self.message(i).id()}\n')
                for i in dupes.byContents:
                    msg: TranslatorMessage = self.message(i)
                    sys.stderr.write(f'\n* Context: {msg.context()}\n* Source: {msg.sourceText()}\n')
                    if msg.comment():
                        sys.stderr.write(f'* Comment: {msg.comment()}\n')
                    ts_line: int = msg.tsLineNumber()
                    if ts_line >= 0:
                        sys.stderr.write(f'* Line in .ts File: {ts_line}\n')
                sys.stderr.write('\n')

    def languageCode(self) -> str:
        return self.m_language

    def sourceLanguageCode(self) -> str:
        return self.m_sourceLanguage

    class LocationsType(enum.Enum):
        DefaultLocations = enum.auto()
        NoLocations = enum.auto()
        RelativeLocations = enum.auto()
        AbsoluteLocations = enum.auto()

    def setLocationsType(self, lt: LocationsType) -> None:
        self.m_locationsType = lt

    def locationsType(self) -> LocationsType:
        return self.m_locationsType

    @staticmethod
    def makeLanguageCode(language: QLocale.Language, territory: QLocale.Country) -> str:
        result: str = QLocale.languageToCode(language)
        if language != QLocale.Language.C and territory != QLocale.Country.AnyCountry:
            result += '_'
            result += QLocale.territoryToCode(territory)
        return result

    @staticmethod
    def languageAndTerritory(languageCode: str) -> tuple[QLocale.Language, QLocale.Country]:
        if '_' in languageCode:
            l: str
            t: str
            l, t = languageCode.split('_', maxsplit=1)  # "de_DE"
            return QLocale.codeToLanguage(l), QLocale.codeToCountry(t)
        else:
            language: QLocale.Language = QLocale.codeToLanguage(languageCode)
            return language, QLocale(language).territory()

    def setLanguageCode(self, languageCode: str) -> None:
        self.m_language = languageCode

    def setSourceLanguageCode(self, languageCode: str) -> None:
        self.m_sourceLanguage = languageCode

    @staticmethod
    def guessLanguageCodeFromFileName(filename: Path) -> str:
        fmt: Translator.FileFormat
        for fmt in Translator.registeredFileFormats():
            if filename.suffix.casefold() == fmt.extension.casefold():
                filename = filename.with_suffix('')
                break
        while filename.name:
            locale: QLocale = QLocale(filename.name)
            # qDebug() << "LANGUAGE FROM " << filename << "LANG: " << locale.language();
            if locale.language() != QLocale.Language.C:
                # qDebug() << "FOUND " << locale.name();
                return locale.name()
            if filename.suffix:
                filename = filename.with_suffix('')
            elif '_' in filename.name:
                filename = filename.with_name(filename.name[:filename.name.index('_')])
            else:
                break
        # qDebug() << "LANGUAGE GUESSING UNSUCCESSFUL";
        return ''

    def messages(self) -> list[TranslatorMessage]:
        return self.m_messages

    @staticmethod
    @overload
    def normalizedTranslations(msg: TranslatorMessage, numPlurals: int) -> list[str]:
        pass

    def normalizeTranslations(self, cd: ConversionData) -> None:
        truncated: bool = False
        lang: QLocale.Language
        c: QLocale.Country
        lang, c = self.languageAndTerritory(self.languageCode())
        num_plurals: int = 1
        if lang != QLocale.Language.C:
            forms: list[str]
            _, forms, _, ok = getNumerusInfo(lang, c)
            if ok:
                num_plurals = len(forms)  # includes singular
        msg: TranslatorMessage
        for msg in self.m_messages:
            tlns: list[str] = list(msg.translations())
            ccnt: int = num_plurals if msg.isPlural() else 1
            if len(tlns) != ccnt:
                if len(tlns) < ccnt:
                    tlns.extend([''] * (ccnt - len(tlns)))
                elif len(tlns) > ccnt:
                    tlns = tlns[:-(len(tlns) - ccnt)]
                    truncated = True
                msg.setTranslations(tlns)
        if truncated:
            cd.appendError("Removed plural forms as the target language has less "
                           "forms.\nIf this sounds wrong, possibly the target language is "
                           "not set or recognized.")

    @overload
    def normalizedTranslations(self, m: TranslatorMessage, cd: ConversionData) -> tuple[list[str], bool]:
        pass

    def normalizedTranslations(*args) -> list[str] | tuple[list[str], bool]:
        if len(args) == 2:
            msg: TranslatorMessage
            num_plurals: int
            msg, num_plurals = args
            translations: list[str] = list(msg.translations())
            num_translations: int = num_plurals if msg.isPlural() else 1

            # make sure that the string list always have the size of the
            # language's current numerus, or 1 if it's not plural
            if len(translations) > num_translations:
                translations = translations[:-(len(translations) - num_translations)]
            elif len(translations) < num_translations:
                translations.extend([''] * (num_translations - len(translations)))
            return translations
        else:
            raise NotImplementedError  # TODO

    def messageCount(self) -> int:
        return len(self.m_messages)
    
    def message(self, i: int) -> TranslatorMessage:
        return self.m_messages[i]
    
    def dump(self) -> None:
        msg: TranslatorMessage
        for msg in self.m_messages:
            msg.dump()
    
    def setDependencies(self, dependencies: list[str]) -> None:
        self.m_dependencies = dependencies
        
    def dependencies(self) -> list[str]:
        return self.m_dependencies
    
    # additional file format specific data
    # note: use '<fileformat>:' as prefix for file format specific members,
    # e.g. "po-flags", "po-msgid_plural"
    ExtraData = TranslatorMessage.ExtraData
    
    def extra(self, key: str) -> str:
        return self.m_extra[key]

    def setExtra(self, key: str, value: str) -> None:
        self.m_extra[key] = value

    def hasExtra(self, key: str) -> bool:
        return key in self.m_extra

    def extras(self) -> ExtraData:
        return self.m_extra

    def setExtras(self, extras: ExtraData) -> None:
        self.m_extra = extras

    @staticmethod
    def registerFileFormat(fmt: FileFormat) -> None:
        # qDebug() << "Translator: Registering format " << format.extension;
        formats: list[Translator.FileFormat] = Translator.registeredFileFormats()
        i: int
        for i in range(len(formats)):
            if fmt.fileType == formats[i].fileType and fmt.priority < formats[i].priority:
                formats.insert(i, fmt)
                return
        formats.append(fmt)

    @staticmethod
    def registeredFileFormats() -> list[FileFormat]:
        return Translator._theFormats
    
    TextVariantSeparator = 0x2762  # some weird character nobody ever heard of :-D
    BinaryVariantSeparator = 0x9c  # unicode "STRING TERMINATOR"
    
    def insert(self, idx: int, msg: TranslatorMessage) -> None:
        if self.m_indexOk:
            if idx == len(self.m_messages):
                self.addIndex(idx, msg)
            else:
                self.m_indexOk = False
        self.m_messages.insert(idx, msg)
    
    def addIndex(self, idx: int, msg: TranslatorMessage) -> None:
        if not msg.sourceText() and not msg.id():
            self.m_ctxCmtIdx[msg.context()] = idx
        else:
            self.m_msgIdx[TMMKey(msg)] = idx
            if msg.id():
                self.m_idMsgIdx[msg.id()] = idx
    
    def delIndex(self, idx: int) -> None:
        msg: TranslatorMessage = self.m_messages[idx]
        if not msg.sourceText() and not msg.id():
            self.m_ctxCmtIdx.pop(msg.context())
        else:
            self.m_msgIdx.pop(TMMKey(msg))
            if msg.id():
                self.m_idMsgIdx.pop(msg.id())
    
    def ensureIndexed(self) -> None:
        if not self.m_indexOk:
            self.m_indexOk = True
            self.m_ctxCmtIdx.clear()
            self.m_idMsgIdx.clear()
            self.m_msgIdx.clear()
            i: int
            m: TranslatorMessage
            for i, m in enumerate(self.m_messages):
                self.addIndex(i, m)

    TMM = list[TranslatorMessage]   


'''
  This is a quick hack. The proper way to handle this would be
  to extend Translator's interface.
'''

ContextComment = "QT_LINGUIST_INTERNAL_CONTEXT_COMMENT"
