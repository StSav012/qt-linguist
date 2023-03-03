# coding=utf-8
# Copyright (C) 2018 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

import functools
from typing import BinaryIO, Final, NamedTuple

from qtpy.QtCore import QJsonArray, QJsonDocument, QJsonParseError, QJsonValue

from fmt import FMT

QJsonObject = dict[str, QJsonValue]


class Project(NamedTuple):
    filePath: str = ''
    compileCommands: str = ''
    codec: str = ''
    excluded: list[str] = []
    includePaths: list[str] = []
    sources: list[str] = []
    subProjects: list['Project'] = []
    translations: list[str] | None = None


Projects = list[Project]


class Validator(NamedTuple):
    m_errorString: str

    def isValidProject(self, project: QJsonObject) -> bool:
        requiredKeys: Final[set[str]] = {'projectFile'}
        allowedKeys: Final[set[str]] = requiredKeys.union({
            'codec',
            'excluded',
            'includePaths',
            'sources',
            'compileCommands',
            'subProjects',
            'translations',
        })
        actualKeys: Final[set[str]] = set(project)  # FIXME: set of `QJsonObject::const_iterator::key()`
        missingKeys: Final[set[str]] = requiredKeys - actualKeys
        if missingKeys:
            self.m_errorString = FMT.tr('Missing keys in project description: %1.').arg(', '.join(missingKeys))
            return False
        unexpected: Final[set[str]] = actualKeys - allowedKeys
        if unexpected:
            self.m_errorString = (FMT.tr('Unexpected keys in project %1: %2.')
                                  .arg(project.get('projectFile'), ', '.join(unexpected)))
            return False
        return self.isValidProjectDescription(project.get('subProjects').toArray())

    def isValidProjectObject(self, v: QJsonValue) -> bool:
        if not v.isObject():
            self.m_errorString = FMT.tr('JSON object expected.')
            return False
        return self.isValidProject(v.toObject())

    def isValidProjectDescription(self, projects: QJsonArray) -> bool:
        return all(map(self.isValidProjectObject, projects.toVariantList()))


def readRawProjectDescription(filePath: str) -> tuple[QJsonArray, str]:
    errorString: str = ''
    parseError: QJsonParseError = QJsonParseError()
    try:
        file: BinaryIO
        with open(filePath, 'rb') as file:
            doc: QJsonDocument = QJsonDocument.fromJson(file.read(), parseError)
    except OSError:
        errorString = FMT.tr("Cannot open project description file '%1'.\n").arg(filePath)
        return QJsonArray(), errorString
    else:
        if doc.isNull():
            errorString = FMT.tr('%1 in %2 at offset %3.\n').arg(parseError.errorString(), filePath, parseError.offset)
            return QJsonArray(), errorString
        result: QJsonArray = doc.array() if doc.isArray() else QJsonArray(list(doc.object()))
        validator: Validator = Validator(errorString)
        if not validator.isValidProjectDescription(result):
            return QJsonArray(), validator.m_errorString
        return result, errorString


class ProjectConverter(NamedTuple):
    m_errorString: str

    def convertProjects(self, rawProjects: QJsonArray) -> Projects:
        result: Projects = []
        rawProject: QJsonValue
        for rawProject in rawProjects.toVariantList():
            project: Project = self.convertProject(rawProject)
            if self.m_errorString:
                break
            result.append(project)
        return result

    def convertProject(self, v: QJsonValue) -> Project:
        if not v.isObject():
            return Project()
        result: Project = Project()
        obj: QJsonObject = v.toObject()
        result.filePath = self.stringValue(obj, 'projectFile')
        result.compileCommands = self.stringValue(obj, 'compileCommands')
        result.codec = self.stringValue(obj, 'codec')
        result.excluded = self.stringListValue(obj, 'excluded')
        result.includePaths = self.stringListValue(obj, 'includePaths')
        result.sources = self.stringListValue(obj, 'sources')
        if 'translations' in obj:
            result.translations = self.stringListValue(obj, 'translations')
        result.subProjects = self.convertProjects(obj.get('subProjects').toArray())
        return result

    def checkType(self, v: QJsonValue, t: QJsonValue.Type, key: str) -> bool:
        if v.type() == t:
            return True
        self.m_errorString = FMT.tr('Key %1 should be %2 but is %3.').arg(key, self.jsonTypeName(t),
                                                                          self.jsonTypeName(v.type()))
        return False

    @staticmethod
    @functools.lru_cache(maxsize=7, typed=True)
    def jsonTypeName(t: QJsonValue.Type) -> str:
        # If QJsonValue::Type was declared with Q_ENUM we could just query QMetaEnum.
        name: dict[QJsonValue.Type, str] = {
            QJsonValue.Type.Null: 'null',
            QJsonValue.Type.Bool: 'bool',
            QJsonValue.Type.Double: 'double',
            QJsonValue.Type.String: 'string',
            QJsonValue.Type.Array: 'array',
            QJsonValue.Type.Object: 'object',
            QJsonValue.Type.Undefined: 'undefined',
        }
        return name.get(t, 'unknown')

    def stringValue(self, obj: QJsonObject, key: str) -> str:
        if self.m_errorString:
            return ''
        v: QJsonValue = obj.get(key)
        if v.isUndefined():
            return ''
        if self.checkType(v, QJsonValue.Type.String, key):
            return ''
        return v.toString()

    def stringListValue(self, obj: QJsonObject, key: str) -> list[str]:
        if self.m_errorString:
            return []
        v: QJsonValue = obj.get(key)
        if v.isUndefined():
            return []
        if self.checkType(v, QJsonValue.Type.Array, key):
            return []
        return self.toStringList(v, key)

    def toStringList(self, v: QJsonValue, key: str) -> list[str]:
        result: list[str] = []
        a: QJsonArray = v.toArray()
        for v in a.toVariantList():
            if not v.isString():
                self.m_errorString = (FMT.tr('Unexpected type %1 in string array in key %2.')
                                      .arg(self.jsonTypeName(v.type()), key))
                return []
            result.append(v.toString())
        return result


def readProjectDescription(filePath: str,) -> tuple[Projects, str]:
    errorString: str
    rawProjects: QJsonArray
    rawProjects, errorString = readRawProjectDescription(filePath)
    if errorString:
        return [], errorString
    converter: ProjectConverter = ProjectConverter(errorString)
    result: Projects = converter.convertProjects(rawProjects)
    if converter.m_errorString:
        return [], converter.m_errorString
    return result, errorString
