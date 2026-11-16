"""Column types shared by the ORM models.

`UtcDateTime` is the single place where stored instants become timezone-aware
(audit findings api:15 / ui:3). Every router, the MCP server and the agent CLI
serialize model attributes as they are, so fixing the type fixes every response
at once.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """A point in time, always returned as a timezone-aware UTC ``datetime``.

    ``DateTime(timezone=True)`` cannot keep that promise on SQLite, the
    documented database: SQLite has no timezone-aware storage, so the dialect
    stores wall-clock digits and returns NAIVE datetimes. Every writer stores
    ``datetime.now(timezone.utc)``, but the naive values reached JSON without
    an offset, and browsers read an offset-less date-time as local time.

    Binding converts an aware value to UTC. A naive value is taken to be UTC
    already, which is the storage convention. Reading re-attaches UTC. The DDL
    is the one ``DateTime(timezone=True)`` emits, so no migration is needed:
    existing rows already hold UTC digits.

    Use this for instants only. Calendar dates such as ``effective_from`` and
    ``effective_to`` stay plain ``DateTime``. Stamping them as UTC would show
    1 January as 31 December to every viewer west of Greenwich.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    @staticmethod
    def _as_utc(value):
        if not isinstance(value, datetime):
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_bind_param(self, value, dialect):
        return self._as_utc(value)

    def process_result_value(self, value, dialect):
        return self._as_utc(value)
