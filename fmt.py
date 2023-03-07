# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

from typing import Any

from qtpy.QtCore import QCoreApplication


class QString(str):
    def arg(self, *args: Any) -> 'QString':  # FIXME: consider formatting hints
        s: QString = self
        for i, a in reversed(list(enumerate(args, start=1))):  # FIXME: start from the first index used
            s = s.replace(f'%{i}', str(a))
        return s


class FMT:
    @staticmethod
    def tr(sourceText: str, disambiguation: str = '', n: int = -1) -> QString:
        return QString(QCoreApplication.translate('Linguist', sourceText, disambiguation, n))
