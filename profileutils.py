# coding=utf-8
# Copyright (C) 2018 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

from pathlib import Path


def isProOrPriFile(filePath: Path) -> bool:
    return filePath.suffix.casefold() in ('.pro', '.pri')


def extractProFiles(files: list[Path]) -> list[Path]:
    return [f for f in files if isProOrPriFile(f)]
