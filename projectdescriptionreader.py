# coding=utf-8
# Copyright (C) 2018 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import BinaryIO, Final, TypeAlias

from qtpy.QtCore import QJsonArray, QJsonDocument, QJsonParseError, QJsonValue

from fmt import FMT

QJsonObject: TypeAlias = dict[str, QJsonValue]


@dataclass
class Project:
    filePath: str = ""
    compileCommands: str = ""
    codec: str = ""
    excluded: list[str] = field(default_factory=list)
    includePaths: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    subProjects: list["Project"] = field(default_factory=list)
    translations: list[str] | None = None


Projects: TypeAlias = list[Project]


class Validator:
    def __init__(self, errorString: str) -> None:
        self.m_errorString: str = errorString

    def isValidProject(self, project: QJsonObject) -> bool:
        required_keys: Final[set[str]] = {"projectFile"}
        allowed_keys: Final[set[str]] = required_keys.union(
            {
                "codec",
                "excluded",
                "includePaths",
                "sources",
                "compileCommands",
                "subProjects",
                "translations",
            }
        )
        # FIXME: set of `QJsonObject::const_iterator::key()`
        actual_keys: Final[set[str]] = set(project)
        missing_keys: Final[set[str]] = required_keys - actual_keys
        if missing_keys:
            self.m_errorString = FMT.tr("Missing keys in project description: %1.").arg(
                ", ".join(missing_keys)
            )
            return False
        unexpected: Final[set[str]] = actual_keys - allowed_keys
        if unexpected:
            self.m_errorString = FMT.tr("Unexpected keys in project %1: %2.").arg(
                project.get("projectFile"), ", ".join(unexpected)
            )
            return False
        return self.isValidProjectDescription(
            project.get("subProjects", QJsonValue()).toArray()
        )

    def isValidProjectObject(self, v: QJsonValue) -> bool:
        if not v.isObject():
            self.m_errorString = FMT.tr("JSON object expected.")
            return False
        return self.isValidProject(v.toObject())

    def isValidProjectDescription(self, projects: QJsonArray) -> bool:
        return all(map(self.isValidProjectObject, projects.toVariantList()))


def readRawProjectDescription(filePath: str) -> tuple[QJsonArray, str]:
    error_string: str = ""
    parse_error: QJsonParseError = QJsonParseError()
    try:
        file: BinaryIO
        with open(filePath, "rb") as file:
            doc: QJsonDocument = QJsonDocument.fromJson(file.read(), parse_error)
    except OSError:
        error_string = FMT.tr("Cannot open project description file '%1'.\n").arg(
            filePath
        )
        return QJsonArray(), error_string
    else:
        if doc.isNull():
            error_string = FMT.tr("%1 in %2 at offset %3.\n").arg(
                parse_error.errorString(), filePath, parse_error.offset
            )
            return QJsonArray(), error_string
        result: QJsonArray = (
            doc.array()
            if doc.isArray()
            else QJsonArray.fromVariantList(list(doc.object()))
        )
        validator: Validator = Validator(error_string)
        if not validator.isValidProjectDescription(result):
            return QJsonArray(), validator.m_errorString
        return result, error_string


class ProjectConverter:
    def __init__(self, errorString: str) -> None:
        self.m_errorString: str = errorString

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
        result.filePath = self.stringValue(obj, "projectFile")
        result.compileCommands = self.stringValue(obj, "compileCommands")
        result.codec = self.stringValue(obj, "codec")
        result.excluded = self.stringListValue(obj, "excluded")
        result.includePaths = self.stringListValue(obj, "includePaths")
        result.sources = self.stringListValue(obj, "sources")
        if "translations" in obj:
            result.translations = self.stringListValue(obj, "translations")
        result.subProjects = self.convertProjects(
            obj.get("subProjects", QJsonValue()).toArray()
        )
        return result

    def checkType(self, v: QJsonValue, t: QJsonValue.Type, key: str) -> bool:
        if v.type() == t:
            return True
        self.m_errorString = FMT.tr("Key %1 should be %2 but is %3.").arg(
            key, self.jsonTypeName(t), self.jsonTypeName(v.type())
        )
        return False

    @staticmethod
    @functools.lru_cache(maxsize=7, typed=True)
    def jsonTypeName(t: QJsonValue.Type) -> str:
        # If QJsonValue::Type was declared with Q_ENUM, we could just query QMetaEnum.
        name: dict[QJsonValue.Type, str] = {
            QJsonValue.Type.Null: "null",
            QJsonValue.Type.Bool: "bool",
            QJsonValue.Type.Double: "double",
            QJsonValue.Type.String: "string",
            QJsonValue.Type.Array: "array",
            QJsonValue.Type.Object: "object",
            QJsonValue.Type.Undefined: "undefined",
        }
        return name.get(t, "unknown")

    def stringValue(self, obj: QJsonObject, key: str) -> str:
        if self.m_errorString:
            return ""
        v: QJsonValue = obj.get(key)
        if v.isUndefined():
            return ""
        if self.checkType(v, QJsonValue.Type.String, key):
            return ""
        return v.toString()

    def stringListValue(self, obj: QJsonObject, key: str) -> list[str]:
        if self.m_errorString:
            return []
        v: QJsonValue = obj.get(key, QJsonValue())
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
                self.m_errorString = FMT.tr(
                    "Unexpected type %1 in a string array in key %2."
                ).arg(self.jsonTypeName(v.type()), key)
                return []
            result.append(v.toString())
        return result


def readProjectDescription(filePath: str) -> tuple[Projects, str]:
    error_string: str
    raw_projects: QJsonArray
    raw_projects, error_string = readRawProjectDescription(filePath)
    if error_string:
        return [], error_string
    converter: ProjectConverter = ProjectConverter(error_string)
    result: Projects = converter.convertProjects(raw_projects)
    if converter.m_errorString:
        return [], converter.m_errorString
    return result, error_string
