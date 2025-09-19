# File: /sqlalchemy-pydantic-codegen/sqlalchemy-pydantic-codegen/src/sqlalchemy_pydantic_codegen/utils/type_mapping.py

import uuid
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.types import TypeEngine


def map_sqlalchemy_type_to_pydantic(
    sqlalchemy_type: TypeEngine[Any],
) -> tuple[str, dict[str, Any]]:
    if isinstance(sqlalchemy_type, String):
        return "str", {
            "max_length": sqlalchemy_type.length
        } if sqlalchemy_type.length else {}
    elif isinstance(sqlalchemy_type, Integer):
        return "int", {}
    elif isinstance(sqlalchemy_type, (Float, Numeric)):
        return "float", {}
    elif isinstance(sqlalchemy_type, Boolean):
        return "bool", {}
    elif isinstance(sqlalchemy_type, DateTime):
        return "datetime.datetime", {}
    elif isinstance(sqlalchemy_type, Date):
        return "datetime.date", {}
    elif isinstance(sqlalchemy_type, JSONB):
        return "list[dict[str, Any]] | dict[str, Any]", {}
    elif (
        isinstance(sqlalchemy_type, PG_UUID)
        or getattr(sqlalchemy_type, "python_type", None) is uuid.UUID
    ):
        return "UUID", {}
    elif isinstance(sqlalchemy_type, Enum) and hasattr(sqlalchemy_type, "enums"):
        return (
            sqlalchemy_type.enum_class.__name__
            if sqlalchemy_type.enum_class
            else "str",
            {},
        )
    else:
        try:
            return sqlalchemy_type.python_type.__name__, {}
        except Exception:
            return "Any", {}


def is_nullable(sqlalchemy_type: NamedColumn[Any]) -> bool:
    return sqlalchemy_type.nullable if hasattr(sqlalchemy_type, "nullable") else False


def get_default_value(sqlalchemy_type: NamedColumn[Any]) -> Any:
    return sqlalchemy_type.default if hasattr(sqlalchemy_type, "default") else None
