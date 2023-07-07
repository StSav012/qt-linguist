#!/bin/env python3
# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any, Iterator, Sequence, cast

from qtpy.QtCore import QCoreApplication, qVersion

from fmt import QString
from translator import ConversionData, Translator
from translatormessage import TranslatorMessage

try:
    import ts
except ImportError:
    pass


def printOut(out: str) -> None:
    sys.stdout.write(out + '\n')


def printErr(out: str) -> None:
    sys.stderr.write(out + '\n')


def list_files(path: Path, recursive: bool = True, *, suffix: str | Sequence[str] = '') -> list[Path]:
    if isinstance(suffix, str):
        suffix = suffix.casefold()
    else:
        suffix = list(map(str.casefold, suffix))

    if path.is_dir():
        files: list[Path] = []
        for file in path.iterdir():
            if not recursive and not file.is_file():
                continue
            files.extend(list_files(file, suffix=suffix))
        return files
    elif path.is_file():
        # return the path in one of the three following cases
        if not suffix:
            return [path]
        if isinstance(suffix, str) and path.suffix.casefold() == suffix:
            return [path]
        if path.suffix.casefold() in suffix:
            return [path]
    return []


def find_translation_calls(filename: Path, base_path: Path) -> Iterator[TranslatorMessage]:
    m: ast.Module = ast.parse(source=filename.read_text(), filename=str(filename))

    import_translate_as: set[str] = set()
    import_qt_core_as: set[str] = set()
    import_qt_gui_as: set[str] = set()
    import_qt_widgets_as: set[str] = set()
    import_qt_core_application_as: set[str] = set()

    def message_from_translate_call(line: int, context: str, sourceText: str,
                                    disambiguation: str | None = None, n: int = -1) -> TranslatorMessage:
        def relative_path(_path: Path, _base_path: Path) -> Path:
            while not _base_path.is_dir():
                _base_path = _base_path.parent
                if _base_path.parent.samefile(_base_path):
                    raise RuntimeError('Cannot reach a valid directory')
            _path_parts = list(_path.absolute().parts)
            _base_path_parts = list(_base_path.absolute().parts)
            while _path_parts[0] == _base_path_parts[0]:
                del _path_parts[0]
                del _base_path_parts[0]
            return Path(*(['..'] * len(_base_path_parts)), *_path_parts)

        msg: TranslatorMessage = TranslatorMessage(context=context, sourceText=sourceText,
                                                   comment=disambiguation, plural=(n != -1),
                                                   fileName=relative_path(filename, base_path), lineNumber=line)
        return msg

    def check_expression(operator: ast.expr, class_name: str = '') -> Iterator[TranslatorMessage]:
        field: str
        for field in getattr(operator, '_fields', ()):
            if not hasattr(operator, field):
                continue
            operator_field: Any = getattr(operator, field)
            if isinstance(operator_field, ast.expr):
                yield from check_expression(operator_field, class_name=class_name)
            elif isinstance(operator_field, list):
                field_item: Any
                for field_item in operator_field:
                    yield from check_expression(field_item, class_name=class_name)

        if isinstance(operator, ast.Call):
            if isinstance(operator.func, ast.Name) and operator.func.id in import_translate_as:
                yield message_from_translate_call(
                    line=operator.lineno,
                    context=(cast(ast.Constant, operator.args[0]).value
                             if isinstance(operator.args[0], ast.Constant)
                             else ast.unparse(cast(ast.stmt, operator.args[0]))),
                    sourceText=(cast(ast.Constant, operator.args[1]).value
                                if isinstance(operator.args[1], ast.Constant)
                                else ast.unparse(cast(ast.stmt, operator.args[1]))),
                    disambiguation=(cast(ast.Constant, operator.args[2]).value
                                    if len(operator.args) > 2 and isinstance(operator.args[2], ast.Constant)
                                    else (ast.unparse(cast(ast.stmt, operator.args[2]))
                                          if len(operator.args) > 2 else '')),
                    n=(cast(ast.Constant, operator.args[3]).value
                       if len(operator.args) > 3 and isinstance(operator.args[3], ast.Constant)
                       else -1))
            elif (class_name and isinstance(operator.func, ast.Attribute)
                  and operator.func.attr == 'tr'
                  and isinstance(operator.func.value, ast.Name)
                  and operator.func.value.id == 'self'):
                yield message_from_translate_call(
                    line=operator.lineno,
                    context=class_name,
                    sourceText=(cast(ast.Constant, operator.args[0]).value
                                if isinstance(operator.args[0], ast.Constant)
                                else ast.unparse(cast(ast.stmt, operator.args[0]))),
                    disambiguation=(cast(ast.Constant, operator.args[1]).value
                                    if len(operator.args) > 1 and isinstance(operator.args[1], ast.Constant)
                                    else (ast.unparse(cast(ast.stmt, operator.args[1]))
                                          if len(operator.args) > 1 else '')),
                    n=(cast(ast.Constant, operator.args[2]).value
                       if len(operator.args) > 2 and isinstance(operator.args[2], ast.Constant)
                       else -1))
            elif (isinstance(operator.func, ast.Attribute)
                  and operator.func.attr == 'translate'
                  and isinstance(operator.func.value, ast.Name)
                  and operator.func.value.id in import_qt_core_application_as):
                yield message_from_translate_call(
                    line=operator.lineno,
                    context=(cast(ast.Constant, operator.args[0]).value
                             if isinstance(operator.args[0], ast.Constant)
                             else ast.unparse(cast(ast.stmt, operator.args[0]))),
                    sourceText=(cast(ast.Constant, operator.args[1]).value
                                if isinstance(operator.args[1], ast.Constant)
                                else ast.unparse(cast(ast.stmt, operator.args[1]))),
                    disambiguation=(cast(ast.Constant, operator.args[2]).value
                                    if len(operator.args) > 2 and isinstance(operator.args[2], ast.Constant)
                                    else (ast.unparse(cast(ast.stmt, operator.args[2]))
                                          if len(operator.args) > 2 else '')),
                    n=(cast(ast.Constant, operator.args[3]).value
                       if len(operator.args) > 3 and isinstance(operator.args[3], ast.Constant)
                       else -1))
        return

    def walk_body(body: list[ast.stmt] | list[ast.excepthandler], class_name: str = '') -> Iterator[TranslatorMessage]:
        item: ast.stmt | ast.excepthandler
        for item in body:
            if isinstance(item, ast.Import):
                i_name: ast.alias
                for i_name in item.names:
                    if i_name.name.endswith('.QtCore'):
                        import_qt_core_as.add(i_name.asname or i_name.name)
                    if i_name.name.endswith('.QtGui'):
                        import_qt_gui_as.add(i_name.asname or i_name.name)
                    if i_name.name.endswith('.QtWidgets'):
                        import_qt_widgets_as.add(i_name.asname or i_name.name)
            if isinstance(item, ast.ImportFrom):
                if_name: ast.alias
                for if_name in item.names:
                    if if_name.name == 'QtCore':
                        import_qt_core_as.add(if_name.asname or if_name.name)
                    if if_name.name == 'QtGui':
                        import_qt_gui_as.add(if_name.asname or if_name.name)
                    if if_name.name == 'QtWidgets':
                        import_qt_widgets_as.add(if_name.asname or if_name.name)
                # item.module is None when `from . import ...`
                if item.module is not None and item.module.endswith('.QtCore'):
                    for if_name in item.names:
                        if (if_name.asname or if_name.name) in ('QCoreApplication', 'QGuiApplication', 'QApplication'):
                            import_qt_core_application_as.add(if_name.asname or if_name.name)
            if isinstance(item, (ast.AnnAssign, ast.Assign)):
                """
                _translate = QCoreApplication.translate
                """
                target: Any = item.targets[0] if isinstance(item, ast.Assign) else item.target
                if isinstance(item.value, ast.Attribute) and isinstance(target, ast.Name):
                    r_value: ast.Attribute = item.value
                    if r_value.attr == 'translate':
                        r_name: Any = r_value.value
                        if isinstance(r_name, ast.Name):
                            if r_name.id in import_qt_core_application_as:
                                import_translate_as.add(target.id)
                        if isinstance(r_name, ast.Attribute):
                            if r_name.attr == 'QCoreApplication' and r_name.value.id in import_qt_core_as:
                                import_translate_as.add(target.id)
                            if r_name.attr == 'QGuiApplication' and r_name.value.id in import_qt_gui_as:
                                import_translate_as.add(target.id)
                            if r_name.attr == 'QApplication' and r_name.value.id in import_qt_widgets_as:
                                import_translate_as.add(target.id)
                if isinstance(item.value, ast.Tuple) and isinstance(target, ast.Tuple):
                    for l_el, r_el in zip(target.elts, item.value.elts):
                        if isinstance(r_el, ast.Attribute) and isinstance(l_el, ast.Name):
                            r_el_name: Any = r_el.value
                            if r_el.attr == 'translate':
                                if isinstance(r_el_name, ast.Name):
                                    if r_el_name.id in import_qt_core_application_as:
                                        import_translate_as.add(l_el.id)
                                if isinstance(r_el_name, ast.Attribute):
                                    if r_el_name.attr == 'QCoreApplication' and r_el_name.value.id in import_qt_core_as:
                                        import_translate_as.add(l_el.id)
                                    if r_el_name.attr == 'QGuiApplication' and r_el_name.value.id in import_qt_gui_as:
                                        import_translate_as.add(l_el.id)
                                    if r_el_name.attr == 'QApplication' and r_el_name.value.id in import_qt_widgets_as:
                                        import_translate_as.add(l_el.id)
            elif isinstance(item, ast.ClassDef):
                item: ast.ClassDef
                yield from walk_body(item.body, class_name=item.name)

            field: str
            for field in getattr(item, '_fields', ()):
                if not hasattr(item, field):
                    continue
                item_field: Any = getattr(item, field)
                if isinstance(item_field, ast.expr):
                    yield from check_expression(item_field, class_name=class_name)
                elif isinstance(item_field, list):
                    field_item: Any
                    if all(isinstance(field_item, ast.stmt) for field_item in item_field):
                        yield from walk_body(item_field, class_name=class_name)
                    elif all(isinstance(field_item, ast.excepthandler) for field_item in item_field):
                        yield from walk_body(item_field, class_name=class_name)
                    elif all(isinstance(field_item, ast.expr) for field_item in item_field):
                        for i_f in item_field:
                            yield from check_expression(i_f, class_name=class_name)
                    elif all(isinstance(field_item, ast.keyword) for field_item in item_field):
                        for i_f in item_field:
                            yield from check_expression(i_f, class_name=class_name)
                    elif all(isinstance(field_item, ast.match_case) for field_item in item_field):
                        pass  # see ast.Match below
                    elif all(isinstance(field_item, ast.withitem) for field_item in item_field):
                        pass  # see ast.AsyncWith & ast.With below
                    elif all(isinstance(field_item, ast.alias) for field_item in item_field):
                        pass  # when importing
                    elif all(isinstance(field_item, str) for field_item in item_field):
                        pass  # `nonlocal` and `global`
                    else:  # non-homogeneous list
                        raise ValueError(f'do not know what to do with {field} = {item_field} of statement {item}')
                else:
                    pass  # all the troubling statements are below

        return

    yield from walk_body(m.body)


def loadTsFile(tor: Translator, ts_filename: Path) -> bool:
    cd: ConversionData = ConversionData()
    ok: bool = tor.load(ts_filename, cd)
    if not ok:
        printErr(f'lupdate error: {cd.error()}')
    else:
        if cd.errors():
            printOut(cd.error())
    cd.clearErrors()
    return ok


def saveTsFile(tor: Translator, ts_filename: Path) -> bool:
    cd: ConversionData = ConversionData()
    ok: bool = tor.save(ts_filename, cd)
    if not ok:
        printErr(f'lupdate error: {cd.error()}')
    else:
        if cd.errors():
            printOut(cd.error())
    cd.clearErrors()
    return ok


def main() -> int:
    app: QCoreApplication = QCoreApplication(sys.argv)
    cd: ConversionData = ConversionData()
    cd.m_verbose = True  # the default is True starting with Qt 4.2
    tor: Translator = Translator()
    ap: argparse.ArgumentParser = argparse.ArgumentParser(add_help=False, description="""\
lupdate is part of Qt's Linguist tool chain. It extracts translatable \
messages from Qt UI files, C++, Java and JavaScript/QtScript source code. \
Extracted messages are stored in textual translation source files (typically \
Qt TS XML). New and modified messages can be merged into existing TS files.""")
    ap.add_argument('-help', action='help', help='Display this information and exit.')
    ap.add_argument('-silent', action='store_true', help='Do not explain what is being done.')
    ap.add_argument('-version', action='version', version=f'lupdate version {qVersion()}',
                    help='Display the version of lupdate and exit.')
    ap.add_argument('-no-obsolete', action='store_true', help='Drop all obsolete and vanished strings.')
    ap.add_argument('-recursive', action=argparse.BooleanOptionalAction, help='Recursively scan directories (default).')
    ap.add_argument('-ext', nargs='+', default=['.py', '.pyw'],
                    help='Process files with the given extensions only. Default: .py, .pyw')
    ap.add_argument('-locations', choices=['absolute', 'relative', 'none'],
                    help='''Specify/override how source code references are saved in TS files.
    absolute: Source file path is relative to target file. Absolute line number is stored.
    relative: Source file path is relative to target file. \
Line number is relative to other entries in the same source file.
    none: no information about source location is stored.
Guessed from existing TS files if not specified.
Default is absolute for new files.''')
    ap.add_argument('-source-language', type=str, default='C',
                    help='Specify the language of the source strings for new files. '
                         'Defaults to POSIX if not specified.')
    ap.add_argument('-target-language', type=str,
                    help='Specify the language of the translations for new files. '
                         'Guessed from the file name if not specified.')
    ap.add_argument('source-file', type=Path, nargs='+')
    ap.add_argument('-ts', type=Path, metavar='ts-file', required=True,
                    help='Save the translations found into this file.')
    args: argparse.Namespace = ap.parse_args()

    if args.silent:
        cd.m_verbose = False

    if args.ts.exists() and not loadTsFile(tor, args.ts):
        return 1
    if args.source_language:
        tor.setSourceLanguageCode(args.source_language)
    if args.target_language:
        tor.setLanguageCode(args.target_language)
    else:
        tor.setLanguageCode(Translator.guessLanguageCodeFromFileName(args.ts))

    if args.locations == 'none':
        tor.setLocationsType(Translator.LocationsType.NoLocations)
    elif args.locations == 'relative':
        tor.setLocationsType(Translator.LocationsType.RelativeLocations)
    elif args.locations == 'absolute':
        tor.setLocationsType(Translator.LocationsType.AbsoluteLocations)

    sources: list[Path] = []

    fn: Path
    for fn in args.__dict__['source-file']:
        sources.extend(list_files(fn, recursive=args.recursive, suffix=args.ext))

    init_messages: list[TranslatorMessage] = tor.messages().copy()
    current_messages: list[TranslatorMessage] = []
    new_messages: list[TranslatorMessage] = []
    ts_path: Path = args.ts.parent.absolute()
    for fn in sources:
        current_messages.extend(find_translation_calls(fn.absolute(), base_path=ts_path))

    new_references: dict[tuple[str, str, str], TranslatorMessage.References] = {}

    cur_msg: TranslatorMessage
    init_msg_index: int
    init_msg: TranslatorMessage
    for cur_msg in current_messages:
        if (cur_msg.context(), cur_msg.sourceText(), cur_msg.comment()) not in new_references:
            new_references[(cur_msg.context(), cur_msg.sourceText(), cur_msg.comment())] = []
        new_references[(cur_msg.context(), cur_msg.sourceText(), cur_msg.comment())]\
            .append(TranslatorMessage.Reference(cur_msg.fileName(), cur_msg.lineNumber()))
    for cur_msg in current_messages:
        if (cur_msg.context(), cur_msg.sourceText(), cur_msg.comment()) not in new_references:
            continue  # already added
        new: bool = True
        for init_msg_index, init_msg in enumerate(init_messages):
            if (cur_msg.context() == init_msg.context()
                    and cur_msg.sourceText() == init_msg.sourceText()
                    and cur_msg.comment() == init_msg.comment()):
                init_msg.setReferences(new_references[(cur_msg.context(), cur_msg.sourceText(), cur_msg.comment())])
                new_messages.append(init_msg)
                del init_messages[init_msg_index]
                new = False
                break
        if new:
            cur_msg.setReferences(new_references[(cur_msg.context(), cur_msg.sourceText(), cur_msg.comment())])
            new_messages.append(cur_msg)
        del new_references[(cur_msg.context(), cur_msg.sourceText(), cur_msg.comment())]
    # mark the rest obsolete
    for init_msg in init_messages:
        init_msg.setType(TranslatorMessage.Type.Obsolete)

    if args.no_obsolete:
        init_messages.clear()

    tor.messages().clear()
    tor.messages().extend(init_messages)
    tor.messages().extend(new_messages)

    saveTsFile(tor, args.ts)

    printOut(QString(QCoreApplication.translate(
        'LUpdate',
        '    Generated %n translation(s) (%1 obsolete and %2 actual)', None,
        tor.messageCount())).arg(len(init_messages), len(new_messages)))

    return 0


if __name__ == '__main__':
    sys.exit(main())
