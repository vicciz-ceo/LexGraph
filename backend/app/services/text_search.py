"""Unicode-aware text matching and natural ordering for SQL queries.

REST assertion search matches Python-lowercased text (`needle in
text.lower()`). SQLite's built-in lower() and LIKE fold ASCII letters only, so
`column.icontains("übergabe")` misses "ÜBERGABE". `contains_text` keeps that
native SQL for needles without cased non-ASCII letters (ASCII, Hebrew, digits)
and otherwise lowercases both sides with Python's `str.lower()`, which every
SQLite connection exposes as `lexgraph_unicode_lower`.

`NaturalOrder` sorts article numbers such as "2", "2א", "10", "9-101" by
comparing digit runs numerically (`lexgraph_natural_key` on SQLite).

Both functions are registered on each new SQLite connection of any engine
once this module is imported; other dialects compile to native SQL.
"""
from __future__ import annotations

import re
import sqlite3

from sqlalchemy import String, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement

_DIGIT_RUN = re.compile(r"[0-9]+")


def unicode_lower_value(value):
    return value.lower() if isinstance(value, str) else value


def natural_key(value):
    """Sort key in which digit runs compare by value: '9-20' < '9-101' < '10-1'."""
    if not isinstance(value, str):
        return value
    return _DIGIT_RUN.sub(_digit_token, value)


def _digit_token(match: re.Match) -> str:
    digits = match.group().lstrip("0") or "0"
    return f"{len(digits):02d}{digits}"  # length first, so 9 < 10 < 100


class UnicodeLower(FunctionElement):
    """lower() with Python's Unicode case mapping."""
    type = String()
    inherit_cache = True


class NaturalOrder(FunctionElement):
    """Natural sort key of a string column (the column itself off SQLite)."""
    type = String()
    inherit_cache = True


@compiles(UnicodeLower)
def _lower(element, compiler, **kw):
    return f"lower({compiler.process(element.clauses, **kw)})"


@compiles(UnicodeLower, "sqlite")
def _lower_sqlite(element, compiler, **kw):
    return f"lexgraph_unicode_lower({compiler.process(element.clauses, **kw)})"


@compiles(NaturalOrder)
def _natural(element, compiler, **kw):
    return compiler.process(element.clauses, **kw)


@compiles(NaturalOrder, "sqlite")
def _natural_sqlite(element, compiler, **kw):
    return f"lexgraph_natural_key({compiler.process(element.clauses, **kw)})"


@event.listens_for(Engine, "connect")
def _register_sqlite_functions(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function("lexgraph_unicode_lower", 1, unicode_lower_value, deterministic=True)
        dbapi_connection.create_function("lexgraph_natural_key", 1, natural_key, deterministic=True)


def _has_cased_non_ascii(text: str) -> bool:
    return any(not ch.isascii() and ch.lower() != ch.upper() for ch in text)


def contains_text(column, needle: str):
    """Case-insensitive literal substring match (`%` and `_` are not wildcards)."""
    needle = needle.strip()
    if _has_cased_non_ascii(needle):
        return UnicodeLower(column).contains(needle.lower(), autoescape=True)
    return column.icontains(needle, autoescape=True)
