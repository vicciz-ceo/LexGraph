"""`app.migrations.m20261116_assertion_read_indexes` (XREQ-67, lists api:14).

The batched list, graph and statistics queries look rows up by assertion,
revision and matter. These indexes turn those lookups from table scans into
index probes; the models declare them and the migration adds them to older
databases, following the migration convention.
"""

from __future__ import annotations

import sqlite3

from sqlalchemy import create_engine, inspect

from app import migrate
from app.migrations import m20261116_assertion_read_indexes as migration
from tests.schema_history import OLDEST, build_fresh_db, build_historical_db

EXPECTED = {
    ("assertions", "ix_assertions_matter_id_status"): ["matter_id", "status"],
    ("assertion_evidence", "ix_assertion_evidence_assertion_id"): ["assertion_id"],
    ("assertion_ratings", "ix_assertion_ratings_assertion_revision_id"): ["assertion_revision_id"],
    ("audit_events", "ix_audit_events_assertion_id_event_type"): ["assertion_id", "event_type"],
}


def _indexes(path) -> dict:
    engine = create_engine(f"sqlite:///{path}")
    try:
        insp = inspect(engine)
        return {
            (table, index["name"]): index["column_names"]
            for table, _name in EXPECTED
            for index in insp.get_indexes(table)
        }
    finally:
        engine.dispose()


def _dump(path) -> list[str]:
    conn = sqlite3.connect(path)
    try:
        return list(conn.iterdump())
    finally:
        conn.close()


def test_the_models_declare_the_indexes_and_upgrade_is_a_no_op_on_them(tmp_path):
    db = build_fresh_db(tmp_path / "fresh.db")
    assert EXPECTED.items() <= _indexes(db).items()
    before = _dump(db)
    engine = migrate.make_migration_engine(f"sqlite:///{db}")
    try:
        assert migration.MIGRATION_ID == "20261116_assertion_read_indexes"
        assert migration.upgrade(engine) is False
    finally:
        engine.dispose()
    assert _dump(db) == before


def test_upgrade_adds_them_to_an_older_database_once(tmp_path):
    db = build_historical_db(tmp_path / "old.db", OLDEST)
    assert not EXPECTED.keys() & _indexes(db).keys()
    engine = migrate.make_migration_engine(f"sqlite:///{db}")
    try:
        assert migration.upgrade(engine) is True
        assert migration.upgrade(engine) is False
    finally:
        engine.dispose()
    assert EXPECTED.items() <= _indexes(db).items()


def test_downgrade_removes_them_and_the_runner_restores_them(tmp_path):
    db = build_fresh_db(tmp_path / "fresh.db")
    engine = migrate.make_migration_engine(f"sqlite:///{db}")
    try:
        assert migration.downgrade(engine) is True
        assert migration.downgrade(engine) is False
    finally:
        engine.dispose()
    assert not EXPECTED.keys() & _indexes(db).keys()
    assert migrate.main(["--db", str(db)]) == 0
    assert EXPECTED.items() <= _indexes(db).items()


def test_the_list_lookups_use_them(tmp_path):
    db = build_fresh_db(tmp_path / "fresh.db")
    conn = sqlite3.connect(db)
    try:
        plans = {
            sql: " ".join(row[-1] for row in conn.execute(f"EXPLAIN QUERY PLAN {sql}"))
            for sql in (
                "SELECT assertion_id, evidence_role FROM assertion_evidence WHERE assertion_id IN ('a', 'b')",
                "SELECT strength FROM assertion_ratings WHERE assertion_revision_id IN ('r1', 'r2')",
                "SELECT max(timestamp) FROM audit_events WHERE assertion_id IN ('a', 'b')",
                "SELECT count(id) FROM assertions WHERE matter_id = 'm' AND status IN ('accepted', 'proposed')",
            )
        }
    finally:
        conn.close()
    for sql, plan in plans.items():
        assert "USING INDEX ix_" in plan or "USING COVERING INDEX ix_" in plan, (sql, plan)
