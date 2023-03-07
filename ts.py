# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

import enum
import sys
import xml.dom.minidom
import xml.etree.ElementTree as _et  # for IDE code highlighting
from pathlib import Path
from typing import BinaryIO, Callable, Final, cast

from translator import ConversionData, Translator
from translatormessage import TranslatorMessage

# Force python XML parser not faster C accelerators
# because we can't hook the C implementation
del sys.modules['_elementtree']
try:
    import xml.etree.ElementTree as et
except ImportError:
    et = _et
    
    
class ElementWithLocation(et.Element):
    def __init__(self, tag: str | Callable[..., et.Element], **extra: str):
        super().__init__(tag, **extra)

        self.line_number: int = -1
        self.column_number: int = -1
        self.loc: str = '-1:-1'


class LineNumberingParser(et.XMLParser):
    def _start(self, tag_name: str, attributes: list[str]) -> ElementWithLocation:
        # Here we assume the default XML parser which is expat
        # and copy its element position attrib into output Elements
        element: ElementWithLocation = getattr(super(self.__class__, self), '_start')(tag_name, attributes)
        element.line_number = self.parser.CurrentLineNumber
        element.column_number = self.parser.CurrentColumnNumber
        element.loc = f'{element.line_number}:{element.column_number}'
        return element


def byteValue(value: str) -> str:
    base: int = 10
    if value.startswith('x'):
        base = 16
        value = value[1:]
    try:
        n: int = int(value, base)
    except ValueError:
        return ''
    else:
        return chr(n)


class TS:
    class Tags(enum.StrEnum):
        TS: Final[str] = 'TS'
        dependencies: Final[str] = 'dependencies'
        dependency: Final[str] = 'dependency'
        context: Final[str] = 'context'
        name: Final[str] = 'name'
        message: Final[str] = 'message'
        location: Final[str] = 'location'
        comment: Final[str] = 'comment'
        translator_comment: Final[str] = 'translator''comment'
        old_comment: Final[str] = 'old''comment'
        extra_comment: Final[str] = 'extra''comment'
        numerus_form: Final[str] = 'numerus''form'
        source: Final[str] = 'source'
        old_source: Final[str] = 'old''source'
        translation: Final[str] = 'translation'
        userdata: Final[str] = 'userdata'
        byte: Final[str] = 'byte'
        length_variant: Final[str] = 'length''variant'

    class Attributes(enum.StrEnum):
        catalog: Final[str] = 'catalog'
        filename: Final[str] = 'filename'
        id: Final[str] = 'id'
        language: Final[str] = 'language'
        line: Final[str] = 'line'
        numerus: Final[str] = 'numerus'
        source_language: Final[str] = 'source''language'
        type: Final[str] = 'type'
        version: Final[str] = 'version'
        encoding: Final[str] = 'encoding'
        value: Final[str] = 'value'
        variants: Final[str] = 'variants'

    class Values(enum.StrEnum):
        obsolete: Final[str] = 'obsolete'
        unfinished: Final[str] = 'unfinished'
        vanished: Final[str] = 'vanished'
        yes: Final[str] = 'yes'

    # prefix
    prefix_extra: Final[str] = 'extra-'

    def __init__(self, cd: ConversionData) -> None:
        self.m_cd: ConversionData = cd

    # the "real thing"
    def read(self, dev: BinaryIO, translator: Translator) -> bool:
        current_line: dict[str, int] = dict()
        current_file: str = ''
        maybe_relative: bool = False
        maybe_absolute: bool = False

        def report_unexpected_tag(tag: ElementWithLocation) -> None:
            self.m_cd.appendError(f'Unexpected message_tag <{tag.tag}> at {self.m_cd.m_sourceFileName}:{tag.loc}')

        def readContents(contents: ElementWithLocation) -> str:
            """ needed to expand <byte ... /> """
            result: str = contents.text or ''
            tag: ElementWithLocation
            for tag in contents:
                if tag.tag == TS.Tags.byte:
                    # <byte value="...">
                    result += byteValue(contents.get(TS.Attributes.value)) + tag.tail.strip()
                    if len(tag):
                        tok: str = et.tostring(tag, encoding='unicode')
                        if len(tok) > 30:
                            tok = tok[:30] + '[...]'
                        self.m_cd.appendError(f'Unexpected characters "{tok}" '
                                              f'at {self.m_cd.m_sourceFileName}:{tag.loc}')
                        break
                else:
                    report_unexpected_tag(tag)
                    break
            # qDebug() << "TEXT: " << result;
            return result + contents.tail.strip()

        def readTransContents(trans_contents: ElementWithLocation) -> str:
            """ needed to join <lengthvariant>s """
            if trans_contents.get(TS.Attributes.variants) != TS.Values.yes:
                return readContents(trans_contents)

            result: str = ''
            tag: ElementWithLocation
            for tag in trans_contents:
                if tag.tag == TS.Tags.length_variant:
                    if result:
                        result += Translator.BinaryVariantSeparator
                    result += readContents(tag)
                else:
                    report_unexpected_tag(tag)
                    break
            return result

        def readDependencies(dependencies: ElementWithLocation) -> list[str]:
            deps: list[str] = []
            tag: ElementWithLocation
            for tag in dependencies:
                if tag.tag == TS.Tags.dependency:
                    # <dependency>
                    deps.append(tag.get(TS.Attributes.catalog))
                else:
                    report_unexpected_tag(tag)
            return deps

        def readTS(ts: ElementWithLocation) -> None:
            nonlocal current_line, current_file, maybe_relative, maybe_absolute

            def readContext(context: ElementWithLocation) -> None:
                nonlocal current_line, current_file, maybe_relative, maybe_absolute

                def readMessage(message: ElementWithLocation) -> TranslatorMessage:
                    nonlocal current_line, current_file, maybe_relative, maybe_absolute

                    def readTranslation(translation: ElementWithLocation) -> list[str]:
                        translations: list[str] = []
                        translation_type: str = translation.get(TS.Attributes.type)
                        if translation_type == TS.Values.unfinished:
                            msg.setType(TranslatorMessage.Type.Unfinished)
                        elif translation_type == TS.Values.vanished:
                            msg.setType(TranslatorMessage.Type.Vanished)
                        elif translation_type == TS.Values.obsolete:
                            msg.setType(TranslatorMessage.Type.Obsolete)
                        if msg.isPlural():
                            translation_tag: ElementWithLocation
                            for translation_tag in translation:
                                if translation_tag.tag == TS.Tags.numerus_form:
                                    # <numerusform>...</numerusform>
                                    translations.append(readTransContents(translation_tag))
                                else:
                                    report_unexpected_tag(translation_tag)
                                    break
                            return translations
                        else:
                            return [readTransContents(translation)]

                    def readLocation(location: ElementWithLocation) -> None:
                        nonlocal current_line, current_file, maybe_relative, maybe_absolute
                        nonlocal refs, current_msg_file

                        maybe_absolute = True
                        file_name: str = location.get(TS.Attributes.filename)
                        if not file_name:
                            file_name = current_msg_file
                            maybe_relative = True
                        else:
                            if not refs:
                                current_file = file_name
                            current_msg_file = file_name
                        lin: str = location.get(TS.Attributes.line)
                        if not lin:
                            refs.append(TranslatorMessage.Reference(Path(file_name), -1))
                        else:
                            try:
                                line_no: int = int(lin)
                            except ValueError:
                                pass
                            else:
                                if lin[0] in '+-':
                                    current_line[file_name] = current_line.get(file_name, 0) + line_no
                                    line_no = current_line[file_name]
                                    maybe_relative = True
                                refs.append(TranslatorMessage.Reference(Path(file_name), line_no))
                        readContents(location)

                    refs: TranslatorMessage.References = []
                    current_msg_file: str = current_file
                    msg: TranslatorMessage = TranslatorMessage()
                    msg.setId(message.get(TS.Attributes.id))
                    msg.setContext(ctx)
                    msg.setType(TranslatorMessage.Type.Finished)
                    msg.setPlural(message.get(TS.Attributes.numerus) == TS.Values.yes)
                    msg.setTsLineNumber(getattr(message, 'line_number', -1))

                    message_tag: ElementWithLocation
                    for message_tag in message:
                        if message_tag.tag == TS.Tags.source:
                            # <source>...</source>
                            msg.setSourceText(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.old_source:
                            # <oldsource>...</oldsource>
                            msg.setOldSourceText(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.old_comment:
                            # <oldcomment>...</oldcomment>
                            msg.setOldComment(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.extra_comment:
                            # <extracomment>...</extracomment>
                            msg.setExtraComment(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.translator_comment:
                            # <translatorcomment>...</translatorcomment>
                            msg.setTranslatorComment(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.location:
                            # <location/>
                            readLocation(message_tag)
                        elif message_tag.tag == TS.Tags.comment:
                            # <comment>...</comment>
                            msg.setComment(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.userdata:
                            # <userdata>...</userdata>
                            msg.setUserData(readContents(message_tag))
                        elif message_tag.tag == TS.Tags.translation:
                            # <translation>...</translation>
                            msg.setTranslations(readTranslation(message_tag))
                        elif message_tag.tag.startswith(TS.prefix_extra):
                            # <extra-...>...</extra-...>
                            msg.setExtra(message_tag.tag[6:], readContents(message_tag))
                        else:
                            report_unexpected_tag(message_tag)
                    msg.setReferences(refs)
                    return msg

                ctx: str = ''
                context_tag: ElementWithLocation
                for context_tag in context:
                    if context_tag.tag == TS.Tags.name:
                        # <name>...</name>
                        ctx = context_tag.text
                    elif context_tag.tag == TS.Tags.message:
                        # <message>...</message>
                        translator.append(readMessage(context_tag))
                    else:
                        report_unexpected_tag(context_tag)

            # version: str = self().value(TS.Attributes.version)
            translator.setLanguageCode(ts.get(TS.Attributes.language))
            translator.setSourceLanguageCode(ts.get(TS.Attributes.source_language))
            tag: ElementWithLocation
            for tag in ts:
                if tag.tag.startswith(TS.prefix_extra):
                    # <extra-...>...</extra-...>
                    translator.setExtra(tag.tag[len(TS.prefix_extra):], readContents(tag))
                elif tag.tag == TS.Tags.dependencies:
                    # <dependencies>
                    # <dependency catalog="qtsystems_no"/>
                    # <dependency catalog="qtbase_no"/>
                    # </dependencies>
                    translator.setDependencies(readDependencies(tag))
                elif tag.tag == TS.Tags.context:
                    # <context>...</context>
                    readContext(tag)
                else:
                    report_unexpected_tag(tag)
                # if the file is empty adopt AbsoluteLocation (default location type for Translator)
                if translator.messageCount() == 0:
                    maybe_absolute = True
                translator.setLocationsType(Translator.LocationsType.RelativeLocations
                                            if maybe_relative
                                            else (Translator.LocationsType.AbsoluteLocations
                                                  if maybe_absolute
                                                  else Translator.LocationsType.NoLocations))
            # </TS>

        try:
            readTS(cast(ElementWithLocation, et.XML(dev.read(), parser=LineNumberingParser())))  # </TS>
        except et.ParseError as ex:
            self.m_cd.appendError(str(ex))
            return False
        return True
    
    def write(self, dev: BinaryIO, translator: Translator) -> bool:
        def make_xml_doc() -> xml.dom.minidom.Document:
            doc: xml.dom.minidom.Document = xml.dom.minidom.Document()

            def new_element(tag_name: str, text: str = '', **attrs: str) -> xml.dom.minidom.Element:
                element: xml.dom.minidom.Element = doc.createElement(tag_name)
                if text:
                    element.appendChild(doc.createTextNode(text))
                key: str
                value: str
                for key, value in attrs.items():
                    if value:
                        element.setAttribute(key, value)
                return element

            doc.appendChild(xml.dom.minidom.DocumentType(TS.Tags.TS))
            root: xml.dom.minidom.Element = new_element(
                TS.Tags.TS,
                **{TS.Attributes.version: "2.1",
                   TS.Attributes.language: translator.languageCode(),
                   TS.Attributes.source_language: translator.sourceLanguageCode()})
            messages: dict[str, list[TranslatorMessage]] = {}
            msg: TranslatorMessage
            for msg in translator.messages():
                if msg.context() not in messages:
                    messages[msg.context()] = [msg]
                else:
                    messages[msg.context()].append(msg)

            ctx: str
            for ctx in messages:
                context: xml.dom.minidom.Element = doc.createElement(TS.Tags.context)
                context.appendChild(new_element(TS.Tags.name, ctx))
                for msg in messages[ctx]:
                    message: xml.dom.minidom.Element = new_element(TS.Tags.message, **{TS.Attributes.id: msg.id()})
                    for ref in msg.allReferences():
                        message.appendChild(new_element(TS.Tags.location,
                                                        **{TS.Attributes.filename: ref.fileName(),
                                                           TS.Attributes.line: str(ref.lineNumber())}))
                    if msg.sourceText():
                        message.appendChild(new_element(TS.Tags.source, msg.sourceText()))
                    if msg.oldSourceText():
                        message.appendChild(new_element(TS.Tags.old_source, msg.oldSourceText()))
                    if msg.isPlural() and msg.translations():
                        translation: xml.dom.minidom.Element = new_element(TS.Tags.translation)
                        translation_type: str = ''
                        if msg.type() == TranslatorMessage.Type.Unfinished:
                            translation_type = TS.Values.unfinished
                        elif msg.type() == TranslatorMessage.Type.Vanished:
                            translation_type = TS.Values.vanished
                        elif msg.type() == TranslatorMessage.Type.Obsolete:
                            translation_type = TS.Values.obsolete
                        numerus_form: str
                        for numerus_form in msg.translations():
                            translation.appendChild(new_element(TS.Tags.numerus_form, numerus_form,
                                                                **{TS.Attributes.type: translation_type}))
                        message.appendChild(translation)
                    else:
                        translation_type: str = ''
                        if msg.type() == TranslatorMessage.Type.Unfinished:
                            translation_type = TS.Values.unfinished
                        elif msg.type() == TranslatorMessage.Type.Vanished:
                            translation_type = TS.Values.vanished
                        elif msg.type() == TranslatorMessage.Type.Obsolete:
                            translation_type = TS.Values.obsolete
                        message.appendChild(new_element(TS.Tags.translation, msg.translation(),
                                                        **{TS.Attributes.type: translation_type}))
                    if msg.comment():
                        message.appendChild(new_element(TS.Tags.comment, msg.comment()))
                    if msg.oldComment():
                        message.appendChild(new_element(TS.Tags.old_comment, msg.oldComment()))
                    if msg.userData():
                        message.appendChild(new_element(TS.Tags.userdata, msg.userData()))
                    if msg.extraComment():
                        message.appendChild(new_element(TS.Tags.extra_comment, msg.extraComment()))
                    if msg.translatorComment():
                        message.appendChild(new_element(TS.Tags.translator_comment, msg.translatorComment()))
                    if msg.extras():
                        me: str
                        for me in msg.extras():
                            message.appendChild(new_element(TS.prefix_extra + me, msg.extra(me)))
                    context.appendChild(message)
                root.appendChild(context)

            if translator.dependencies():
                dependencies: xml.dom.minidom.Element = doc.createElement(TS.Tags.dependencies)
                dep: str
                for dep in translator.dependencies():
                    dependencies.appendChild(new_element(TS.Tags.dependency, **{TS.Attributes.catalog: dep}))
                root.appendChild(dependencies)

            if translator.extras():
                te: str
                for te in translator.extras():
                    root.appendChild(new_element(TS.prefix_extra + te, translator.extra(te)))

            doc.appendChild(root)

            return doc

        try:
            dev.write(make_xml_doc().toprettyxml(encoding='utf-8'))
        except Exception as ex:
            self.m_cd.appendError(str(ex))
            return False
        return True


def saveTS(translator: Translator, dev: BinaryIO, cd: ConversionData) -> bool:
    ts: TS = TS(cd)
    return ts.write(dev, translator)


def loadTS(translator: Translator, dev: BinaryIO, cd: ConversionData) -> bool:
    ts: TS = TS(cd)
    return ts.read(dev, translator)


def initTS() -> None:
    fmt: Translator.FileFormat = Translator.FileFormat()
    fmt.extension = 'ts'
    fmt.fileType = Translator.FileFormat.FileType.TranslationSource
    fmt.priority = 0
    fmt.untranslatedDescription = 'Qt translation sources'
    fmt.loader = loadTS
    fmt.saver = saveTS

    Translator.registerFileFormat(fmt)


initTS()
