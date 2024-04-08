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

from translator import ConversionData, Translator
from ts import saveTS

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


def loadQmFile(tor: Translator, qm_filename: Path) -> bool:
    cd: ConversionData = ConversionData()
    ok: bool = tor.load(qm_filename, cd)
    if not ok:
        printErr(f"ldecompile error: {cd.error()}")
    else:
        if cd.errors():
            printOut(cd.error())
    cd.clearErrors()
    return ok


def decompileTranslator(
    tor: Translator,
    ts_filename: Path,
    cd: ConversionData,
    remove_identical: bool,
) -> bool:
    tor.reportDuplicates(tor.resolveDuplicates(), ts_filename, cd.isVerbose())

    if cd.isVerbose():
        printOut(f"Writing '{ts_filename}'...\n")
    if remove_identical:
        if cd.isVerbose():
            printOut(
                f"Removing translations equal to source text in '{ts_filename}'...\n"
            )
        tor.stripIdenticalSourceTranslations()

    tor.normalizeTranslations(cd)
    try:
        file: BinaryIO
        with open(ts_filename, "wb") as file:
            ok: bool = saveTS(tor, file, cd)
    except OSError as ex:
        printErr(f"ldecompile error: cannot create '{ts_filename}': {ex}\n")
        return False

    if not ok:
        printErr(f"ldecompile error: cannot save '{ts_filename}': {cd.error()}")
    elif cd.errors():
        printOut(cd.error())
    cd.clearErrors()
    return ok


def decompileQmFile(
    qm_filename: Path,
    cd: ConversionData,
    remove_identical: bool,
) -> bool:
    tor: Translator = Translator()
    if not loadQmFile(tor, qm_filename):
        return False

    ts_filename: Path = qm_filename
    fmt: Translator.FileFormat
    for fmt in Translator.registeredFileFormats():
        if ts_filename.suffix.casefold() == "." + fmt.extension.casefold():
            ts_filename = ts_filename.with_suffix(".ts")
            break

    return decompileTranslator(tor, ts_filename, cd, remove_identical)


def main() -> int:
    app: QCoreApplication = QCoreApplication(sys.argv)
    cd: ConversionData = ConversionData()
    cd.m_verbose = True  # the default is True starting with Qt 4.2
    tor: Translator = Translator()
    ap: argparse.ArgumentParser = argparse.ArgumentParser(
        add_help=False,
        description="""\
ldecompile is not a part of Qt's Linguist tool chain. It can be used as a
stand-alone tool to decompile translations files in the QM format used by
QTranslator objects back into TS format.""",
    )
    ap.add_argument("-help", action="help", help="Display this information and exit")
    ap.add_argument(
        "".join(("-id", "based")),
        action="store_true",
        help="Use IDs instead of source strings for message keying",
    )
    ap.add_argument(
        "-remove" "identical",
        action="store_true",
        help="If the translated text is the same as the source text, do not include the message",
    )
    ap.add_argument(
        "-silent", action="store_true", help="Do not explain what is being done"
    )
    ap.add_argument(
        "-version",
        action="version",
        version=f"ldecompile version {qVersion()}",
        help="Display the version of ldecompile and exit",
    )
    ap.add_argument("qm", metavar="qm-file", type=Path, nargs="+")
    ap.add_argument("-ts", metavar="ts-file", type=Path)
    args: argparse.Namespace = ap.parse_args()

    if args.idbased:
        cd.m_idBased = True
    if args.silent:
        cd.m_verbose = False

    for inputFile in args.qm:
        if not args.ts:
            if not decompileQmFile(inputFile, cd, args.removeidentical):
                return 1
        else:
            if not loadQmFile(tor, inputFile):
                return 1

    if args.ts:
        if decompileTranslator(tor, args.ts, cd, args.removeidentical):
            return 0
        return 1

    return int(bool(app is None))


if __name__ == "__main__":
    sys.exit(main())
