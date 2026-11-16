"""Migration `20261116_revision_reason_raw` (review authoring:5).

A database written before 2026-11-16 has no `assertion_revisions.
revision_reason_raw`. The migration adds it as a nullable column, leaves
every stored reason exactly as it was (with no raw copy), and changes
nothing on a fresh or an already-migrated database. That every historical
schema ends up matching the models after all migrations is checked by
test_migrate_runner.py.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.migrations import m20261116_revision_reason_raw as migration
from tests.schema_history import HISTORICAL_SCHEMAS, build_fresh_db, build_historical_db, rows

NEWEST_HISTORICAL = HISTORICAL_SCHEMAS[-1]


def _columns(path) -> dict:
    engine = create_engine(f"sqlite:///{path}")
    try:
        return {column["name"]: column for column in inspect(engine).get_columns("assertion_revisions")}
    finally:
        engine.dispose()


def _upgrade(path) -> bool:
    engine = create_engine(f"sqlite:///{path}")
    try:
        return migration.upgrade(engine)
    finally:
        engine.dispose()


def test_an_older_database_gets_the_nullable_column_and_keeps_its_reasons(tmp_path):
    path = build_historical_db(tmp_path / "old.db", NEWEST_HISTORICAL)
    before = rows(path, "SELECT id, revision_reason FROM assertion_revisions")
    assert "revision_reason_raw" not in _columns(path)

    assert _upgrade(path) is True

    column = _columns(path)["revision_reason_raw"]
    assert column["nullable"] is True
    assert rows(path, "SELECT id, revision_reason, revision_reason_raw FROM assertion_revisions") == [
        (revision_id, reason, None) for revision_id, reason in before]
    assert _upgrade(path) is False  # idempotent


def test_a_fresh_database_is_left_alone(tmp_path):
    path = build_fresh_db(tmp_path / "fresh.db")
    assert "revision_reason_raw" in _columns(path)
    assert _upgrade(path) is False

