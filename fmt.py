# coding=utf-8

# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from qtpy.QtCore import QCoreApplication


class FMT:
    @staticmethod
    def tr(sourceText: str, disambiguation: str = '', n: int = -1):
        # FIXME: bytes of str??
        return QCoreApplication.translate(b'Linguist', sourceText.encode(), disambiguation.encode(), n)
