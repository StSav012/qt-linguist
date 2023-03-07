# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

import enum
import logging
from pathlib import Path
from typing import Sequence, overload


class TranslatorSaveMode(enum.Enum):
    SaveEverything = enum.auto()
    SaveStripped = enum.auto()


class TranslatorMessage:
    class Type(enum.Enum):
        Unfinished = enum.auto()
        Finished = enum.auto()
        Vanished = enum.auto()
        Obsolete = enum.auto()

    ExtraData = dict[str, str]

    class Reference:
        def __init__(self, name: Path, line_number: int) -> None:
            self._file_name: Path = name
            self._line_number: int = line_number

        def __eq__(self, other: 'TranslatorMessage.Reference') -> bool:
            return self.fileName() == other.fileName() and self.lineNumber() == other.lineNumber()

        def fileName(self) -> Path:
            return self._file_name

        def lineNumber(self) -> int:
            return self._line_number

    References = list[Reference]

    def __init__(self, context: str = '', sourceText: str = '',
                 comment: str | None = '', userData: str = '',
                 fileName: Path | None = None, lineNumber: int = -1,
                 translations: Sequence[str] = (),
                 type_: Type = Type.Unfinished, plural: bool = False) -> None:
        self.m_id: str = ''
        self.m_context: str = context
        self.m_sourcetext: str = sourceText
        self.m_oldsourcetext: str = ''
        self.m_comment: str = comment or ''
        self.m_oldcomment: str = ''
        self.m_userData: str = userData
        self.m_extra: TranslatorMessage.ExtraData = dict()  # PO flags, PO plurals
        self.m_extraComment: str = ''
        self.m_translatorComment: str = ''
        self.m_warning: str = ''
        self.m_translations: Sequence[str] = translations
        self.m_fileName: Path | None = fileName
        self.m_lineNumber: int = lineNumber
        self.m_tsLineNumber: int = -1
        self.m_extraRefs: TranslatorMessage.References = []
        self.m_warningOnly: bool = False

        self.m_type: TranslatorMessage.Type = type_
        self.m_plural: bool = plural

    def id(self) -> str:
        return self.m_id

    def setId(self, new_id: str) -> None:
        self.m_id = new_id

    def context(self) -> str:
        return self.m_context

    def setContext(self, context: str) -> None:
        self.m_context = context

    def sourceText(self) -> str:
        return self.m_sourcetext

    def setSourceText(self, sourceText: str) -> None:
        self.m_sourcetext = sourceText

    def oldSourceText(self) -> str:
        return self.m_oldsourcetext

    def setOldSourceText(self, oldSourceText: str) -> None:
        self.m_oldsourcetext = oldSourceText

    def comment(self) -> str:
        return self.m_comment

    def setComment(self, comment: str) -> None:
        self.m_comment = comment

    def oldComment(self) -> str:
        return self.m_oldcomment

    def setOldComment(self, oldComment: str) -> None:
        self.m_oldcomment = oldComment

    def translations(self) -> Sequence[str]:
        return self.m_translations

    def setTranslations(self, translations: Sequence[str]) -> None:
        self.m_translations = translations

    def translation(self) -> str:
        return self.m_translations[0] if self.m_translations else ''

    def setTranslation(self, translation: str) -> None:
        self.m_translations = [translation]

    def appendTranslation(self, translation: str) -> None:
        self.m_translations = [*self.m_translations, translation]

    def isTranslated(self) -> bool:
        for trans in self.m_translations:
            if trans:
                return True
        return False

    def fileName(self) -> Path | None:
        return self.m_fileName

    def setFileName(self, fileName: Path) -> None:
        self.m_fileName = fileName

    def lineNumber(self) -> int:
        return self.m_lineNumber

    def setLineNumber(self, lineNumber: int) -> None:
        self.m_lineNumber = lineNumber

    def tsLineNumber(self) -> int:
        return self.m_tsLineNumber

    def setTsLineNumber(self, tsLineNumber: int) -> None:
        self.m_tsLineNumber = tsLineNumber

    def clearReferences(self) -> None:
        self.m_fileName = None
        self.m_lineNumber = -1
        self.m_extraRefs.clear()

    def setReferences(self, refs0: References) -> None:
        if refs0:
            refs: TranslatorMessage.References = refs0.copy()
            ref: TranslatorMessage.Reference = refs.pop(0)
            self.m_fileName = ref.fileName()
            self.m_lineNumber = ref.lineNumber()
            self.m_extraRefs = refs
        else:
            self.clearReferences()

    @overload
    def addReference(self, fileName: Path, lineNumber: int) -> None:
        pass

    @overload
    def addReference(self, ref: Reference) -> None:
        pass

    def addReference(self, fileName_or_ref: Path | Reference,
                     lineNumber: int | None = None) -> None:
        if isinstance(fileName_or_ref, Path) and lineNumber is not None:
            if not self.m_fileName:
                self.m_fileName = fileName_or_ref
                self.m_lineNumber = lineNumber
            else:
                self.m_extraRefs.append(TranslatorMessage.Reference(fileName_or_ref, lineNumber))

        elif isinstance(fileName_or_ref, TranslatorMessage.Reference):
            self.addReference(fileName_or_ref.fileName(), fileName_or_ref.lineNumber())

        else:
            raise NotImplementedError

    def addReferenceUniq(self, fileName: Path, lineNumber: int) -> None:
        if self.m_fileName is None:
            self.m_fileName = fileName
            self.m_lineNumber = lineNumber
        else:
            if fileName == self.m_fileName and lineNumber == self.m_lineNumber:
                return
            if self.m_extraRefs:  # Rather common case, so special-case it
                for ref in self.m_extraRefs:
                    if fileName == ref.fileName() and lineNumber == ref.lineNumber():
                        return
            self.m_extraRefs.append(TranslatorMessage.Reference(fileName, lineNumber))

    def extraReferences(self) -> References:
        return self.m_extraRefs

    def allReferences(self) -> References:
        if self.m_fileName is not None:
            return [TranslatorMessage.Reference(self.m_fileName, self.m_lineNumber), *self.m_extraRefs]
        return []

    def userData(self) -> str:
        return self.m_userData

    def setUserData(self, userData: str) -> None:
        self.m_userData = userData

    def extraComment(self) -> str:
        return self.m_extraComment

    def setExtraComment(self, extraComment: str) -> None:
        self.m_extraComment = extraComment

    def translatorComment(self) -> str:
        return self.m_translatorComment

    def setTranslatorComment(self, translatorComment: str) -> None:
        self.m_translatorComment = translatorComment

    def warning(self) -> str:
        return self.m_warning

    def setWarning(self, warning: str) -> None:
        self.m_warning = warning

    def isNull(self) -> bool:
        return not self.m_sourcetext and self.m_lineNumber == -1 and not self.m_translations

    def type(self) -> Type:
        return self.m_type

    def setType(self, t: Type) -> None:
        self.m_type = t

    def isPlural(self) -> bool:
        return self.m_plural

    def setPlural(self, is_plural: bool) -> None:
        self.m_plural = is_plural

    # note: use '<fileformat>:' as prefix for file format specific members,
    # e.g. "po-msgid_plural"

    def extra(self, ba: str) -> str:
        return self.m_extra[ba]

    def setExtra(self, ba: str, var: str) -> None:
        self.m_extra[ba] = var

    def hasExtra(self, ba: str) -> bool:
        return ba in self.m_extra

    def extras(self) -> ExtraData:
        return self.m_extra

    def setExtras(self, extras: ExtraData) -> None:
        self.m_extra = extras

    def unsetExtra(self, key: str) -> None:
        del self.m_extra[key]

    def warningOnly(self) -> bool:
        return self.m_warningOnly

    def setWarningOnly(self, isWarningOnly: bool) -> None:
        self.m_warningOnly = isWarningOnly

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(id={self.m_id!r}, context={self.m_context!r}, ' \
               f'source={self.m_sourcetext!r}, filename={self.m_fileName!s}, line={self.m_lineNumber})'

    def dump(self) -> None:
        logging.debug(
            f'\nId                : {self.m_id}'
            f'\nContext           : {self.m_context}'
            f'\nSource            : {self.m_sourcetext}'
            f'\nComment           : {self.m_comment}'
            f'\nUserData          : {self.m_userData}'
            f'\nExtraComment      : {self.m_extraComment}'
            f'\nTranslatorComment : {self.m_translatorComment}'
            f'\nTranslations      : {self.m_translations}'
            f'\nFileName          : {self.m_fileName!s}'
            f'\nLineNumber        : {self.m_lineNumber}'
            f'\nType              : {self.m_type}'
            f'\nPlural            : {self.m_plural}'
            f'\nExtra             : {self.m_extra}'
        )
