"""`UtcDateTime`: instants round-trip as aware UTC on SQLite (api:15, ui:3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, Table, create_engine, insert, select, text

from app.db import Base
from app.db_types import UtcDateTime

_PLUS_TWO = timezone(timedelta(hours=2))


@pytest.fixture()
def table_and_engine():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    table = Table("t", metadata, Column("id", Integer, primary_key=True), Column("at", UtcDateTime()))
    metadata.create_all(engine)
    yield table, engine
    engine.dispose()


def _stored_text(engine, row_id: int) -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT at FROM t WHERE id = :id"), {"id": row_id}).scalar_one()


def _read(engine, table, row_id: int):
    with engine.connect() as conn:
        return conn.execute(select(table.c.at).where(table.c.id == row_id)).scalar_one()


def test_aware_value_is_stored_as_utc_digits_and_read_back_aware(table_and_engine):
    table, engine = table_and_engine
    with engine.begin() as conn:
        conn.execute(insert(table), {"id": 1, "at": datetime(2026, 11, 16, 1, 30, tzinfo=_PLUS_TWO)})
    # Plain DateTime would have stored the +02:00 wall clock ("01:30") and lost the offset.
    assert _stored_text(engine, 1) == "2026-11-15 23:30:00.000000"
    value = _read(engine, table, 1)
    assert value == datetime(2026, 11, 15, 23, 30, tzinfo=timezone.utc)
    assert value.utcoffset() == timedelta(0)


def test_naive_value_and_legacy_rows_are_utc_by_convention(table_and_engine):
    table, engine = table_and_engine
    with engine.begin() as conn:
        conn.execute(insert(table), {"id": 1, "at": datetime(2026, 11, 15, 20, 16, 17, 835814)})
        # A row written before this type existed (or by raw SQL, as the test seeds do).
        conn.execute(text("INSERT INTO t (id, at) VALUES (2, '2026-11-15 20:16:17.835814')"))
        conn.execute(text("INSERT INTO t (id, at) VALUES (3, NULL)"))
    expected = datetime(2026, 11, 15, 20, 16, 17, 835814, tzinfo=timezone.utc)
    assert _stored_text(engine, 1) == "2026-11-15 20:16:17.835814"
    assert _read(engine, table, 1) == expected
    assert _read(engine, table, 2) == expected
    assert _read(engine, table, 2).tzinfo is timezone.utc
    assert _read(engine, table, 3) is None


def test_comparisons_bind_through_the_same_conversion(table_and_engine):
    table, engine = table_and_engine
    with engine.begin() as conn:
        conn.execute(insert(table), [{"id": 1, "at": datetime(2026, 11, 15, 22, 0, tzinfo=timezone.utc)},
                                     {"id": 2, "at": datetime(2026, 11, 16, 0, 30, tzinfo=timezone.utc)}])
        # Local midnight in UTC+2 is 22:00 UTC, so only row 2 is strictly later.
        later = conn.execute(
            select(table.c.id).where(table.c.at > datetime(2026, 11, 16, 0, 0, tzinfo=_PLUS_TWO))
        ).scalars().all()
    assert later == [2]


# Instants vs calendar dates on the real models: a future column must pick a side.
_CALENDAR_DATE_COLUMNS = {
    ("assertions", "effective_from"),
    ("assertions", "effective_to"),
    ("assertion_revisions", "effective_from"),
    ("assertion_revisions", "effective_to"),
}


def test_every_model_instant_column_is_utc_aware_and_calendar_dates_are_not():
    import app.models  # noqa: F401  register every mapping

    instants, dates = [], []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if isinstance(column.type, UtcDateTime):
                instants.append((table.name, column.name))
            elif isinstance(column.type, DateTime):
                dates.append((table.name, column.name))
    assert set(dates) == _CALENDAR_DATE_COLUMNS, f"plain DateTime used for an instant: {sorted(dates)}"
    assert {
        ("assertions", "created_at"),
        ("assertions", "updated_at"),
        ("assertions", "submitted_at"),
        ("assertions", "reviewed_at"),
        ("assertion_revisions", "created_at"),
        ("assertion_evidence", "created_at"),
        ("assertion_ratings", "created_at"),
        ("assertion_ratings", "updated_at"),
        ("assertion_comments", "created_at"),
        ("assertion_comments", "updated_at"),
        ("assertion_comments", "deleted_at"),
        ("audit_events", "timestamp"),
        ("notifications", "created_at"),
        ("notifications", "read_at"),
        ("notification_preferences", "updated_at"),
    } <= set(instants)
