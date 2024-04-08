# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

import warnings
from enum import IntEnum
from typing import BinaryIO, Final, NamedTuple

from qtpy.QtCore import QByteArray, QCoreApplication, QDataStream, QLocale, QSysInfo

from fmt import QString
from numerus import getNumerusInfo
from translator import ConversionData, Translator
from translatormessage import TranslatorMessage, TranslatorSaveMode


def _set_bytes(container: bytearray, data: bytes, pos: int) -> tuple[bytearray, int]:
    end_pos: int = pos + len(data)
    container[pos:end_pos] = data
    return container, end_pos


# fmt: off
magic: Final[bytes] = bytes([
    0x3c, 0xb8, 0x64, 0x18, 0xca, 0xef, 0x9c, 0x95,
    0xcd, 0x21, 0x1c, 0xbf, 0x60, 0xa1, 0xbd, 0xdd
])
# fmt: on


class Tag(IntEnum):
    Tag_End = 1
    Tag_SourceText16 = 2
    Tag_Translation = 3
    Tag_Context16 = 4
    Tag_Obsolete1 = 5
    Tag_SourceText = 6
    Tag_Context = 7
    Tag_Comment = 8
    Tag_Obsolete2 = 9


class QMTag(IntEnum):
    Contexts = 0x2F
    Hashes = 0x42
    Messages = 0x69
    NumerusRules = 0x88
    Dependencies = 0x96
    Language = 0xA7


class Prefix(IntEnum):
    NoPrefix = 0
    Hash = 1
    HashContext = 2
    HashContextSourceText = 3
    HashContextSourceTextComment = 4


def elfHash(ba: bytes) -> int:
    h: int = 0
    g: int
    k: int
    for k in ba:
        h = (h << 4) + k
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g
    if not h:
        h = 1
    return h


def uint8(n: int) -> bytes:
    return n.to_bytes(1, "big", signed=False)


def uint16(n: int) -> bytes:
    return n.to_bytes(2, "big", signed=False)


def uint32(n: int) -> bytes:
    return n.to_bytes(4, "big", signed=False)


class ByteTranslatorMessage(NamedTuple):
    m_context: bytes
    m_sourceText: bytes
    m_comment: bytes
    m_translations: list[str]

    def context(self) -> bytes:
        return self.m_context

    def sourceText(self) -> bytes:
        return self.m_sourceText

    def comment(self) -> bytes:
        return self.m_comment

    def translations(self) -> list[str]:
        return self.m_translations

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ByteTranslatorMessage):
            return NotImplemented
        if self.m_context != other.m_context:
            return self.m_context < other.m_context
        if self.m_sourceText != other.m_sourceText:
            return self.m_sourceText < other.m_sourceText
        return self.m_comment < other.m_comment


class Releaser:
    class Offset(NamedTuple):
        h: int = 0
        o: int = 0

        def __lt__(self, other: object) -> bool:
            if isinstance(other, Releaser.Offset):
                return self.h < other.h if self.h != other.h else self.o < other.o
            return NotImplemented

    Contexts: Final[int] = 0x2F
    Hashes: Final[int] = 0x42
    Messages: Final[int] = 0x69
    NumerusRules: Final[int] = 0x88
    Dependencies: Final[int] = 0x96
    Language: Final[int] = 0xA7

    def __init__(self, language: str) -> None:
        self.m_language: str = language
        # for squeezed but non-file data, this is what needs to be deleted
        self.m_messageArray: bytearray = bytearray()
        self.m_offsetArray: bytearray = bytearray()
        self.m_contextArray: bytearray = bytearray()
        self.m_messages: list[ByteTranslatorMessage] = []
        self.m_numerusRules: bytes = b""
        self.m_dependencies: list[str] = []
        self.m_dependencyArray: bytes = b""

    @staticmethod
    def originalBytes(string: str) -> bytes:
        return string.encode("utf-8")

    @staticmethod
    def msgHash(msg: ByteTranslatorMessage) -> int:
        return elfHash(msg.sourceText() + msg.comment())

    def commonPrefix(
        self,
        m1: ByteTranslatorMessage,
        m2: ByteTranslatorMessage,
    ) -> Prefix:
        if self.msgHash(m1) != self.msgHash(m2):
            return Prefix.NoPrefix
        if m1.context() != m2.context():
            return Prefix.Hash
        if m1.sourceText() != m2.sourceText():
            return Prefix.HashContext
        if m1.comment() != m2.comment():
            return Prefix.HashContextSourceText
        return Prefix.HashContextSourceTextComment

    @staticmethod
    def writeMessage(
        msg: ByteTranslatorMessage,
        mode: TranslatorSaveMode,
        prefix: Prefix,
    ) -> bytes:
        stream: bytes = b""

        t: str
        for t in msg.translations():
            stream += (
                uint8(Tag.Tag_Translation)
                + uint32(len(t.encode("utf_16_be")))
                + t.encode("utf_16_be")
            )

        if mode == TranslatorSaveMode.SaveEverything:
            prefix = Prefix.HashContextSourceTextComment

        if prefix == Prefix.HashContextSourceTextComment:
            stream += (
                uint8(Tag.Tag_Comment) + uint32(len(msg.comment())) + msg.comment()
            )
            stream += (
                uint8(Tag.Tag_SourceText)
                + uint32(len(msg.sourceText()))
                + msg.sourceText()
            )
            stream += (
                uint8(Tag.Tag_Context) + uint32(len(msg.context())) + msg.context()
            )
        if prefix == Prefix.HashContextSourceText:
            stream += (
                uint8(Tag.Tag_SourceText)
                + uint32(len(msg.sourceText()))
                + msg.sourceText()
            )
            stream += (
                uint8(Tag.Tag_Context) + uint32(len(msg.context())) + msg.context()
            )
        if prefix == Prefix.HashContext:
            stream += (
                uint8(Tag.Tag_Context) + uint32(len(msg.context())) + msg.context()
            )

        stream += uint8(Tag.Tag_End)

        return stream

    def save(self, s: BinaryIO) -> bool:
        s.write(magic)

        if self.m_language:
            lang: bytes = self.originalBytes(self.m_language)
            s.write(uint8(Releaser.Language))
            s.write(uint32(len(lang)))
            s.write(lang)
        if self.m_dependencyArray:
            s.write(uint8(Releaser.Dependencies))
            s.write(uint32(len(self.m_dependencyArray)))
            s.write(self.m_dependencyArray)
        if self.m_offsetArray:
            s.write(uint8(Releaser.Hashes))
            s.write(uint32(len(self.m_offsetArray)))
            s.write(self.m_offsetArray)
        if self.m_messageArray:
            s.write(uint8(Releaser.Messages))
            s.write(uint32(len(self.m_messageArray)))
            s.write(self.m_messageArray)
        if self.m_contextArray:
            s.write(uint8(Releaser.Contexts))
            s.write(uint32(len(self.m_contextArray)))
            s.write(self.m_contextArray)
        if self.m_numerusRules:
            s.write(uint8(Releaser.NumerusRules))
            s.write(uint32(len(self.m_numerusRules)))
            s.write(self.m_numerusRules)
        return True

    def squeeze(self, mode: TranslatorSaveMode) -> None:
        self.m_dependencyArray = b""
        dep: str
        for dep in self.m_dependencies:
            self.m_dependencyArray += dep.encode()

        if not self.m_messages and mode == TranslatorSaveMode.SaveEverything:
            return

        messages: list[ByteTranslatorMessage] = sorted(self.m_messages)

        # re-build contents
        self.m_messageArray = bytearray()
        self.m_offsetArray = bytearray()
        self.m_contextArray = bytearray()
        self.m_messages.clear()

        offsets: list[Releaser.Offset] = []

        prev_prefix: Prefix
        next_prefix: Prefix = Prefix.NoPrefix
        i: int
        it: ByteTranslatorMessage
        next_it: ByteTranslatorMessage
        for i, it in enumerate(messages):
            prev_prefix = next_prefix
            if i == len(messages) - 1:
                next_prefix = Prefix.NoPrefix
            else:
                next_it = messages[i + 1]
                next_prefix = self.commonPrefix(it, next_it)
            offsets.append(Releaser.Offset(self.msgHash(it), len(self.m_messageArray)))
            self.m_messageArray += self.writeMessage(
                it,
                mode,
                Prefix(max(prev_prefix, next_prefix + 1)),
            )

        self.m_offsetArray = bytearray(
            b"".join(sorted(uint32(k.h) + uint32(k.o) for k in offsets))
        )

        if mode == TranslatorSaveMode.SaveStripped:
            context_set: dict[bytes, int] = {}
            for it in messages:
                context_set[it.context()] += 1

            h_table_size: int
            if len(context_set) < 60:
                h_table_size = 151
            elif len(context_set) < 200:
                h_table_size = 503
            elif len(context_set) < 750:
                h_table_size = 1511
            elif len(context_set) < 2500:
                h_table_size = 5003
            elif len(context_set) < 10000:
                h_table_size = 15013
            else:
                h_table_size = 3 * len(context_set) // 2

            hash_map: list[tuple[int, bytes]] = []
            for c in context_set:
                hash_map.append((elfHash(c) % h_table_size, c))

            # The contexts found in this translator are stored in a hash
            # table to provide fast lookup. The context array has the
            # following format:
            #
            #     quint16 h_table_size;
            #     quint16 h_table[h_table_size];
            #     quint8  contextPool[...];
            #
            # The context pool stores the contexts as Pascal strings:
            #
            #     quint8  len;
            #     quint8  data[len];
            #
            # Let's consider the look-up of context "FunnyDialog".  A
            # hash value between 0 and h_table_size - 1 is computed, say h.
            # If h_table[h] is 0, "FunnyDialog" is not covered by this
            # translator. Else, we check in the contextPool at offset
            # 2 * h_table[h] to see if "FunnyDialog" is one of the
            # contexts stored there, until we find it, or we meet the
            # empty string.

            self.m_contextArray = bytearray(2 + (h_table_size << 1))
            h_table: list[int] = [0] * h_table_size

            pos: int = 0
            self.m_contextArray, pos = _set_bytes(
                self.m_contextArray,
                uint16(h_table_size),
                pos,
            )
            pos = 2 + (h_table_size << 1)
            # the entry at offset 0 cannot be used
            self.m_contextArray, pos = _set_bytes(self.m_contextArray, uint16(0), pos)
            up_to: int = 2

            j: int = 0
            entry: bytes
            while j < len(hash_map):
                i = hash_map[j][0]
                h_table[i] = up_to >> 1

                while j < len(hash_map) and hash_map[j][0] == i:
                    entry = hash_map[j][1]
                    self.m_contextArray, pos = _set_bytes(
                        self.m_contextArray, uint8(min(len(entry), 255)), pos
                    )
                    self.m_contextArray, pos = _set_bytes(
                        self.m_contextArray, entry, pos
                    )
                    up_to += 1 + len(entry)
                    j += 1
                if up_to & 0x1:
                    # offsets have to be even
                    self.m_contextArray, pos = _set_bytes(
                        self.m_contextArray, b"\0", pos
                    )  # empty string
                    up_to += 1
            pos = 2
            for i in h_table:
                self.m_contextArray, pos = _set_bytes(
                    self.m_contextArray, uint16(i), pos
                )
            del h_table

            if up_to > 131072:
                warnings.warn("Releaser::squeeze: Too many contexts")
                self.m_contextArray = bytearray()

    def insert(
        self,
        message: TranslatorMessage,
        translations: list[str],
        forceComment: bool,
    ) -> None:
        b_msg: ByteTranslatorMessage = ByteTranslatorMessage(
            self.originalBytes(message.context()),
            self.originalBytes(message.sourceText()),
            self.originalBytes(message.comment()),
            translations,
        )
        if not forceComment:
            b_msg2: ByteTranslatorMessage = ByteTranslatorMessage(
                b_msg.context(),
                b_msg.sourceText(),
                b"",
                b_msg.translations(),
            )
            if b_msg2 not in self.m_messages:
                self.m_messages.append(b_msg2)
                return
        self.m_messages.append(b_msg)

    def insertIdBased(
        self,
        message: TranslatorMessage,
        translations: list[str],
    ) -> None:
        b_msg: ByteTranslatorMessage = ByteTranslatorMessage(
            b"", self.originalBytes(message.id()), b"", translations
        )
        self.m_messages.append(b_msg)

    def setNumerusRules(self, rules: bytes) -> None:
        self.m_numerusRules = rules

    def setDependencies(self, dependencies: list[str]) -> None:
        self.m_dependencies = dependencies


def read8(data: bytes) -> int:
    return int.from_bytes(data[:1], "big")


def read32(data: bytes, signed: bool = False) -> int:
    return int.from_bytes(data[:4], "big", signed=signed)


def fromBytes(data: bytes, length: int) -> tuple[str, bool]:
    out: str = ""
    utf8_fail: bool = False
    try:
        out = data[:length].decode(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        utf8_fail = True
    return out, utf8_fail


def loadQM(translator: Translator, dev: BinaryIO, cd: ConversionData) -> bool:
    data: bytes = dev.read()
    if not data.startswith(magic):
        cd.appendError("QM-Format error: magic marker missing")
        return False

    # for squeezed but non-file data, this is what needs to be deleted
    message_array: bytes = b""
    offset_array: bytes = b""
    offset_length: int = 0

    ok: bool = True
    utf8_fail: bool = False

    data = data[len(magic) :]
    tag: int

    while len(data) > 4:
        tag = read8(data)
        data = data[1:]
        block_length: int = read32(data)
        # qDebug() << "TAG:" << tag <<  "BLOCK LEN:" << block_length
        data = data[4:]
        if not tag or not block_length:
            break
        if block_length > len(data):
            ok = False
            break

        if tag == QMTag.Hashes:
            offset_array = data
            offset_length = block_length
            # qDebug() << "HASHES: " << block_length << QByteArray((const char *)data, block_length).toHex()
        elif tag == QMTag.Messages:
            message_array = data
            # qDebug() << "MESSAGES: " << block_length << QByteArray((const char *)data, block_length).toHex()
        elif tag == QMTag.Dependencies:
            dependencies: list[str] = []
            stream: QDataStream = QDataStream(
                QByteArray.fromRawData(data, block_length)
            )
            while not stream.atEnd():
                dep: str = stream.readQString()
                dependencies.append(dep)
            translator.setDependencies(dependencies)
        elif tag == QMTag.Language:
            language: str
            language, utf8_fail = fromBytes(data, block_length)
            translator.setLanguageCode(language)

        data = data[block_length:]

    num_items: int = offset_length // 8
    # qDebug() << "NUM ITEMS: " << num_items;

    str_pro_n: str = "%n"
    lang: QLocale.Language
    country: QLocale.Country
    lang, country = Translator.languageAndTerritory(translator.languageCode())
    numerus_forms: list[str]
    guess_plurals: bool = True
    numerus_ok: bool
    _, numerus_forms, _, numerus_ok = getNumerusInfo(lang, country)
    if numerus_ok:
        guess_plurals = len(numerus_forms) == 1

    for start in range(0, num_items << 3, 8):
        context: str = ""
        source_text: str = ""
        comment: str = ""
        translations: list[str] = []

        # hash: int = read32(offset_array[start])
        ro: int = read32(offset_array[start + 4 :])
        # qDebug() << "\nHASH:" << hash
        m: bytes = message_array[ro:]

        length: int
        while m:
            tag = read8(m)
            m = m[1:]
            # qDebug() << "Tag:" << tag << " ADDR: " << m
            match tag:
                case Tag.Tag_End:
                    break
                case Tag.Tag_Translation:
                    length = read32(m, signed=True)
                    assert length >= -1
                    m = m[4:]

                    # -1 indicates an empty string
                    # Otherwise, streaming format is UTF-16 -> 2 bytes per character
                    if length != -1 and length & 1:
                        cd.appendError("QM-Format error")
                        return False
                    if length != -1:
                        string_bytes: bytes = m[:length]
                        if QSysInfo.Endian.ByteOrder == QSysInfo.Endian.LittleEndian:
                            string_bytes = bytes(
                                sum(
                                    (
                                        [string_bytes[i + 1], string_bytes[i]]
                                        for i in range(0, len(string_bytes), 2)
                                    ),
                                    [],
                                )
                            )
                        translations.append(string_bytes.decode("utf-16le"))
                        m = m[length:]
                case Tag.Tag_Obsolete1:
                    m = m[4:]
                    # qDebug() << "OBSOLETE"
                case Tag.Tag_SourceText:
                    length = read32(m)
                    m = m[4:]
                    # qDebug() << "SOURCE LEN: " << length
                    # qDebug() << "SOURCE: " << m[:length]
                    source_text, utf8_fail = fromBytes(m, length)
                    m = m[length:]
                case Tag.Tag_Context:
                    length = read32(m)
                    m = m[4:]
                    # qDebug() << "CONTEXT LEN: " << length
                    # qDebug() << "CONTEXT: " << m[:length]
                    context, utf8_fail = fromBytes(m, length)
                    m = m[length:]
                case Tag.Tag_Comment:
                    length = read32(m)
                    m = m[4:]
                    # qDebug() << "COMMENT LEN: " << length
                    # qDebug() << "COMMENT: " << m[:length]
                    comment, utf8_fail = fromBytes(m, length)
                    m = m[length:]
                case _:
                    # qDebug() << "UNKNOWN TAG" << tag
                    pass

        msg: TranslatorMessage = TranslatorMessage()
        msg.setType(TranslatorMessage.Type.Finished)
        if len(translations) > 1:
            # If guess_plurals is not false here, plural form discard messages
            # will be spewn out later.
            msg.setPlural(True)
        elif guess_plurals:
            # This might cause false positives, so it is a fallback only.
            if str_pro_n in source_text:
                msg.setPlural(True)
        msg.setTranslations(translations)
        msg.setContext(context)
        msg.setSourceText(source_text)
        msg.setComment(comment)
        translator.append(msg)

    if utf8_fail:
        cd.appendError("Error: File contains invalid UTF-8 sequences.")
        return False

    return ok


def containsStripped(translator: Translator, msg: TranslatorMessage) -> bool:
    t_msg: TranslatorMessage
    for t_msg in translator.messages():
        if (
            t_msg.sourceText() == msg.sourceText()
            and t_msg.context() == msg.context()
            and not t_msg.comment()
        ):
            return True
    return False


def saveQM(translator: Translator, dev: BinaryIO, cd: ConversionData) -> bool:
    releaser: Releaser = Releaser(translator.languageCode())
    language: QLocale.Language
    country: QLocale.Country
    language, country = Translator.languageAndTerritory(translator.languageCode())
    rules: bytes
    ok: bool
    rules, _, _, ok = getNumerusInfo(language, country)
    if ok:
        releaser.setNumerusRules(rules)

    finished: int = 0
    unfinished: int = 0
    untranslated: int = 0
    missing_ids: int = 0
    dropped_data: int = 0

    msg: TranslatorMessage
    for msg in translator.messages():
        typ: TranslatorMessage.Type = msg.type()
        if typ not in (
            TranslatorMessage.Type.Obsolete,
            TranslatorMessage.Type.Vanished,
        ):
            if cd.m_idBased and not msg.id():
                missing_ids += 1
                continue
            if typ == TranslatorMessage.Type.Unfinished:
                if not msg.translation() and not cd.m_idBased and not cd.m_unTrPrefix:
                    untranslated += 1
                    continue
                else:
                    if cd.ignoreUnfinished():
                        continue
                    unfinished += 1
            else:
                finished += 1

            translations: list[str] = list(msg.translations())
            if msg.type() == TranslatorMessage.Type.Unfinished and (
                cd.m_idBased or cd.m_unTrPrefix
            ):
                j: int
                for j in range(len(translations)):
                    if not translations[j]:
                        translations[j] = cd.m_unTrPrefix + msg.sourceText()
            if cd.m_idBased:
                if msg.context() or msg.comment():
                    dropped_data += 1
                releaser.insertIdBased(msg, translations)
            else:
                # Drop the comment in (context, sourceText, comment),
                # unless the context is empty,
                # unless (context, sourceText, "") already exists or
                # unless we already dropped the comment of (context,
                # sourceText, comment0).
                force_comment: bool = (
                    not msg.comment()
                    or not msg.context()
                    or containsStripped(translator, msg)
                )
                releaser.insert(msg, translations, force_comment)

    if missing_ids:
        cd.appendError(
            QCoreApplication.translate(
                "LRelease",
                "Dropped %n message(s) which had no ID.",
                None,
                missing_ids,
            )
        )
    if dropped_data:
        cd.appendError(
            QCoreApplication.translate(
                "LRelease",
                "Excess context/disambiguation dropped from %n message(s).",
                None,
                dropped_data,
            )
        )

    releaser.setDependencies(translator.dependencies())
    releaser.squeeze(cd.m_saveMode)
    saved: bool = releaser.save(dev)
    if saved and cd.isVerbose():
        cd.appendError(
            QString(
                QCoreApplication.translate(
                    "LRelease",
                    "    Generated %n translation(s) (%1 finished and %2 unfinished)",
                    None,
                    finished + unfinished,
                )
            ).arg(finished, unfinished)
        )
        if untranslated:
            cd.appendError(
                QCoreApplication.translate(
                    "LRelease",
                    "    Ignored %n untranslated source text(s)",
                    None,
                    untranslated,
                )
            )
    return saved


def initQM() -> None:
    fmt: Translator.FileFormat = Translator.FileFormat()
    fmt.extension = "qm"
    fmt.fileType = Translator.FileFormat.FileType.TranslationBinary
    fmt.priority = 0
    fmt.untranslatedDescription = "Compiled Qt translations"
    fmt.loader = loadQM
    fmt.saver = saveQM

    Translator.registerFileFormat(fmt)


if __name__ == "__main__":
    initQM()
