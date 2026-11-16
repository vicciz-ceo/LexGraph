"""`app.migrations.m20261116_assertion_comments_index` (review workflow:5).

Comments are read per assertion: the notice recipients of every comment,
evidence and edit, and GET /assertions/{id}/comments. assertion_comments had
no index on assertion_id, so each such read scanned every matter's comments.
The model declares ix_assertion_comments_assertion_id and this migration adds
it to older databases, following the migration convention.
"""

from __future__ import annotations

import sqlite3

from sqlalchemy import create_engine, inspect

from app import migrate
from app.migrations import m20261116_assertion_comments_index as migration
from tests.schema_history import OLDEST, build_fresh_db, build_historical_db

EXPECTED = {("assertion_comments", "ix_assertion_comments_assertion_id"): ["assertion_id"]}


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


def test_the_model_declares_the_index_and_upgrade_is_a_no_op_on_it(tmp_path):
    db = build_fresh_db(tmp_path / "fresh.db")
    assert EXPECTED.items() <= _indexes(db).items()
    before = _dump(db)
    engine = migrate.make_migration_engine(f"sqlite:///{db}")
    try:
        assert migration.MIGRATION_ID == "20261116_assertion_comments_index"
        assert migration.upgrade(engine) is False
    finally:
        engine.dispose()
    assert _dump(db) == before


def test_upgrade_adds_it_to_an_older_database_once(tmp_path):
    db = build_historical_db(tmp_path / "old.db", OLDEST)
    assert not EXPECTED.keys() & _indexes(db).keys()
    engine = migrate.make_migration_engine(f"sqlite:///{db}")
    try:
        assert migration.upgrade(engine) is True
        assert migration.upgrade(engine) is False
    finally:
        engine.dispose()
    assert EXPECTED.items() <= _indexes(db).items()


def test_downgrade_removes_it_and_the_runner_restores_it(tmp_path):
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


def test_the_per_assertion_comment_lookups_use_it(tmp_path):
    db = build_fresh_db(tmp_path / "fresh.db")
    conn = sqlite3.connect(db)
    try:
        plans = {
            sql: " ".join(row[-1] for row in conn.execute(f"EXPLAIN QUERY PLAN {sql}"))
            for sql in (
                "SELECT DISTINCT user_id FROM assertion_comments WHERE assertion_id = 'a' AND deleted_at IS NULL",
                "SELECT * FROM assertion_comments WHERE assertion_id = 'a' ORDER BY created_at",
            )
        }
    finally:
        conn.close()
    for sql, plan in plans.items():
        assert "USING INDEX ix_assertion_comments_assertion_id" in plan, (sql, plan)
