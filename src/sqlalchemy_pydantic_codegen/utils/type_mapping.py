# File: /sqlalchemy-pydantic-codegen/sqlalchemy-pydantic-codegen/src/sqlalchemy_pydantic_codegen/utils/type_mapping.py

import re
import uuid
from typing import Any, Literal, cast

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.types import TypeEngine


def _safe_python_type(sqlalchemy_type: TypeEngine[Any]) -> Any:
    """Return ``sqlalchemy_type.python_type`` or ``None`` if unsupported.

    Some SQLAlchemy types (notably ``NullType``, produced for unrecognized
    column types like pgvector's ``vector``) raise ``NotImplementedError``
    from the ``python_type`` property. ``getattr(..., default)`` does not
    swallow that exception, so we guard explicitly.
    """
    try:
        return sqlalchemy_type.python_type
    except (NotImplementedError, AttributeError):
        return None


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
    elif isinstance(sqlalchemy_type, ARRAY):
        item: TypeEngine[Any] = cast(TypeEngine[Any], sqlalchemy_type.item_type)
        if isinstance(item, JSONB):
            return "list[dict[str, Any]] | dict[str, Any]", {}
        return "list[Any]", {}
    elif (
        isinstance(sqlalchemy_type, PG_UUID)
        or _safe_python_type(sqlalchemy_type) is uuid.UUID
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
        py = _safe_python_type(sqlalchemy_type)
        if py is not None:
            try:
                return py.__name__, {}
            except Exception:
                pass
        return "Any", {}


def is_nullable(sqlalchemy_type: NamedColumn[Any]) -> bool:
    return sqlalchemy_type.nullable if hasattr(sqlalchemy_type, "nullable") else False


DefaultKind = Literal["none", "literal", "non_literal"]


def _server_default_sql(server_default: Any) -> str | None:
    """Return the raw SQL text of a column's ``server_default``, or ``None``.

    ``server_default`` is normally a ``DefaultClause`` whose ``.arg`` is a
    ``TextClause`` (from ``text(...)``) or a plain string. A bare
    ``FetchedValue`` has no ``.arg`` and yields ``None``.
    """
    arg = getattr(server_default, "arg", None)
    if arg is None:
        return None
    text_attr = getattr(arg, "text", None)
    if isinstance(text_attr, str):
        return text_attr
    if isinstance(arg, str):
        return arg
    return None


def _parse_sql_literal(sql: str) -> tuple[DefaultKind, Any]:
    """Classify a server-default SQL fragment as a scalar literal or not."""
    s = sql.strip()
    # Strip a trailing Postgres cast: "'concise'::text" -> "'concise'".
    s = re.sub(r"::[\w ]+$", "", s).strip()
    lowered = s.lower()
    if re.fullmatch(r"-?\d+", s):
        return ("literal", int(s))
    if re.fullmatch(r"-?\d+\.\d+", s):
        return ("literal", float(s))
    if lowered in ("true", "false"):
        return ("literal", lowered == "true")
    # Single-quoted string with no call expression -> str literal. Checked
    # before the non-literal fallthrough so e.g. 'current_user' stays a str.
    m = re.fullmatch(r"'(.*)'", s, re.DOTALL)
    if m and "(" not in s:
        return ("literal", m.group(1).replace("''", "'"))
    # now(), nextval(...), gen_random_uuid(), current_timestamp, etc.
    return ("non_literal", None)


_LITERAL_PY_TYPE_NAMES: dict[type, frozenset[str]] = {
    int: frozenset({"int"}),
    float: frozenset({"float"}),
    bool: frozenset({"bool"}),
    str: frozenset({"str"}),
}


def can_materialize_literal(value: Any, py_type: str) -> bool:
    """Whether a parsed scalar literal is safe to emit as the field default.

    Guards against cases like JSONB ``'{}'::jsonb`` — ``_parse_sql_literal``
    correctly extracts the string ``"{}"``, but emitting that as the default
    for a ``dict[str, Any]`` field produces a Pydantic schema that fails
    validation whenever the field is omitted.
    """
    return py_type in _LITERAL_PY_TYPE_NAMES.get(type(value), frozenset())


def resolve_column_default(col: NamedColumn[Any]) -> tuple[DefaultKind, Any]:
    """Resolve a column's insert-time default.

    Returns ``(kind, value)``:
      * ``("none", None)``        -- no default; the column must be supplied
      * ``("literal", value)``    -- a scalar literal the DB/ORM supplies
      * ``("non_literal", None)`` -- a function/expression/callable default

    Reads ``server_default`` (DB-side) first, then ``default`` (ORM-side).
    """
    server_default = getattr(col, "server_default", None)
    if server_default is not None:
        sql = _server_default_sql(server_default)
        return _parse_sql_literal(sql) if sql is not None else ("non_literal", None)

    default = getattr(col, "default", None)
    if default is not None:
        if getattr(default, "is_scalar", False):
            return ("literal", default.arg)
        # Callables, sequences and SQL expressions are not materializable.
        return ("non_literal", None)

    return ("none", None)
