#!/bin/env python3
# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import BinaryIO

from qtpy.QtCore import QCoreApplication, qVersion

from profileutils import extractProFiles
from projectdescriptionreader import Projects, readProjectDescription
from qm import saveQM
from translator import ConversionData, Translator
from translatormessage import TranslatorSaveMode

try:
    from ts import initTS
except ImportError:

    def initTS() -> None:
        return None

else:
    initTS()

try:
    from qm import initQM
except ImportError:

    def initQM() -> None:
        return None

else:
    initQM()


def printOut(out: str) -> None:
    sys.stdout.write(out)


def printErr(out: str) -> None:
    sys.stderr.write(out)


def loadTsFile(tor: Translator, ts_filename: Path) -> bool:
    cd: ConversionData = ConversionData()
    ok: bool = tor.load(ts_filename, cd)
    if not ok:
        printErr(f'lrelease error: {cd.error()}')
    else:
        if cd.errors():
            printOut(cd.error())
    cd.clearErrors()
    return ok


def releaseTranslator(tor: Translator, qm_filename: Path,
                      cd: ConversionData, remove_identical: bool) -> bool:
    tor.reportDuplicates(tor.resolveDuplicates(), qm_filename, cd.isVerbose())

    if cd.isVerbose():
        printOut(f"Updating '{qm_filename}'...\n")
    if remove_identical:
        if cd.isVerbose():
            printOut(f"Removing translations equal to source text in '{qm_filename}'...\n")
        tor.stripIdenticalSourceTranslations()

    tor.normalizeTranslations(cd)
    try:
        file: BinaryIO
        with open(qm_filename, 'wb') as file:
            ok: bool = saveQM(tor, file, cd)
    except OSError as ex:
        printErr(f"lrelease error: cannot create '{qm_filename}': {ex}\n")
        return False

    if not ok:
        printErr(f"lrelease error: cannot save '{qm_filename}': {cd.error()}")
    elif cd.errors():
        printOut(cd.error())
    cd.clearErrors()
    return ok


def releaseTsFile(ts_filename: Path,
                  cd: ConversionData, remove_identical: bool) -> bool:
    tor: Translator = Translator()
    if not loadTsFile(tor, ts_filename):
        return False

    qm_filename: Path = ts_filename
    fmt: Translator.FileFormat
    for fmt in Translator.registeredFileFormats():
        if qm_filename.suffix.casefold() == '.' + fmt.extension.casefold():
            qm_filename = qm_filename.with_suffix('.qm')
            break

    return releaseTranslator(tor, qm_filename, cd, remove_identical)


def translationsFromProjects(projects: Projects, topLevel: bool = True) -> list[Path]:
    raise NotImplementedError  # TODO


def main() -> int:
    app: QCoreApplication = QCoreApplication(sys.argv)
    cd: ConversionData = ConversionData()
    cd.m_verbose = True  # the default is True starting with Qt 4.2
    tor: Translator = Translator()
    ap: argparse.ArgumentParser = argparse.ArgumentParser(add_help=False, description="""\
lrelease is part of Qt's Linguist tool chain. It can be used as a
stand-alone tool to convert XML-based translations files in the TS
format into the 'compiled' QM format used by QTranslator objects.""")
    ap.add_argument('-help', action='help', help='Display this information and exit')
    ap.add_argument('-id''based', action='store_true', help='Use IDs instead of source strings for message keying')
    ap.add_argument('-compress', action=argparse.BooleanOptionalAction, help='Compress the QM files')
    ap.add_argument('-no''unfinished', action='store_true', help='Do not include unfinished translations')
    ap.add_argument('-remove''identical', action='store_true',
                    help='If the translated text is the same as the source text, do not include the message')
    ap.add_argument('-mark''untranslated', type=str, metavar='<prefix>',
                    help='If a message has no real translation, use the source text '
                         'prefixed with the given string instead')
    ap.add_argument('-project', type=Path, metavar='<filename>', nargs='?',
                    help="Name of a file containing the project's description in JSON format. "
                         "Such a file may be generated from a .pro file using the lprodump tool.")
    ap.add_argument('-silent', action='store_true', help='Do not explain what is being done')
    ap.add_argument('-version', action='version', version=f'lrelease version {qVersion()}',
                    help='Display the version of lrelease and exit')
    ap.add_argument('ts', metavar='ts-file', type=Path, nargs='+')
    ap.add_argument('-qm', metavar='qm-file')
    args: argparse.Namespace = ap.parse_args()

    if args.compress:
        cd.m_saveMode = TranslatorSaveMode.SaveStripped
    else:
        cd.m_saveMode = TranslatorSaveMode.SaveEverything
    if args.idbased:
        cd.m_idBased = True
    if args.nounfinished:
        cd.m_ignoreUnfinished = True
    if args.silent:
        cd.m_verbose = False

    if extractProFiles(args.ts):
        printErr("""Passing .pro files to lrelease is deprecated.
Please use the lrelease-pro tool instead, or use qmake's lrelease.prf
feature.\n""")

    if args.project:
        if args.ts:
            printErr("lrelease error: Do not specify TS files if -project is given.\n")
            return 1
        project_description: Projects
        error_string: str
        project_description, error_string = readProjectDescription(args.project)
        if error_string:
            printErr(f'lrelease error: {error_string}\n')
            return 1
        args.ts = translationsFromProjects(args.project)

    for inputFile in args.ts:
        if not args.qm:
            if not releaseTsFile(inputFile, cd, args.removeidentical):
                return 1
        else:
            if not loadTsFile(tor, inputFile):
                return 1

    if args.qm:
        if releaseTranslator(tor, args.qm, cd, args.removeidentical):
            return 0
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
