"""Migration `20261116_durable_notifications` (findings pipeline:9, ui:7).

An existing database predates the `notifications` and
`notification_preferences` tables, because notifications used to be held in
process. The migration must create both on such a database so that it
matches what a fresh `Base.metadata.create_all()` builds today, leave every
existing row alone, and report False (changing nothing) on a fresh or an
already-migrated database.
"""

from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401  register every mapped table
from app.db import Base
from app.migrations import m20261116_durable_notifications as migration

NEW_TABLES = ("notifications", "notification_preferences")


def _engine(path):
    return create_engine(f"sqlite:///{path}")


def _build_pre_notification_db(path):
    """Today's schema minus the two notification tables, with a few rows."""
    engine = _engine(path)
    Base.metadata.create_all(
        engine, tables=[t for t in Base.metadata.sorted_tables if t.name not in NEW_TABLES]
    )
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id, name) VALUES ('org-1', 'Org')"))
        conn.execute(text("INSERT INTO repositories (id, organization_id, name) VALUES ('repo-1', 'org-1', 'Repo')"))
        conn.execute(text("INSERT INTO matters (id, repository_id, name) VALUES ('m-1', 'repo-1', 'Matter')"))
        conn.execute(text("INSERT INTO users (id, email, display_name) VALUES ('u-1', 'u1@x', 'User One')"))
    return engine


def _shape(engine) -> dict:
    """Tables, columns with nullability, indexes and unique column sets."""
    insp = inspect(engine)
    shape = {}
    for table in insp.get_table_names():
        uniques = {tuple(sorted(u["column_names"])) for u in insp.get_unique_constraints(table)}
        uniques |= {tuple(sorted(i["column_names"])) for i in insp.get_indexes(table) if i["unique"]}
        shape[table] = {
            "columns": {c["name"]: c["nullable"] for c in insp.get_columns(table)},
            "indexes": sorted((i["name"], tuple(i["column_names"])) for i in insp.get_indexes(table)),
            "unique": sorted(uniques),
            "foreign_keys": sorted(
                (tuple(fk["constrained_columns"]), fk["referred_table"])
                for fk in insp.get_foreign_keys(table)
            ),
        }
    return shape


def _dump(path) -> list[str]:
    conn = sqlite3.connect(path)
    try:
        return list(conn.iterdump())
    finally:
        conn.close()


def test_upgrade_creates_both_tables_exactly_as_create_all_does_and_keeps_rows(tmp_path):
    old = _build_pre_notification_db(tmp_path / "old.db")
    fresh = _engine(tmp_path / "fresh.db")
    Base.metadata.create_all(fresh)
    try:
        assert not set(NEW_TABLES) & set(inspect(old).get_table_names())

        assert migration.upgrade(old) is True

        assert _shape(old) == _shape(fresh)
        with old.connect() as conn:
            assert conn.execute(text("SELECT id, display_name FROM users")).all() == [("u-1", "User One")]
            assert conn.execute(text("SELECT count(*) FROM notifications")).scalar_one() == 0
            # The migrated table accepts the rows the application writes.
            conn.execute(
                text(
                    "INSERT INTO notifications (id, recipient_user_id, actor_user_id, event_type, "
                    "matter_id, assertion_id, payload, created_at, read_at) VALUES "
                    "('n-1', 'u-1', 'u-1', 'assertion_submitted', 'm-1', NULL, '{}', "
                    "'2026-11-16 08:00:00.000000', NULL)"
                )
            )
            conn.commit()
    finally:
        old.dispose()
        fresh.dispose()


def test_second_run_reports_false_and_changes_nothing(tmp_path):
    path = tmp_path / "old.db"
    engine = _build_pre_notification_db(path)
    try:
        assert migration.upgrade(engine) is True
        before = _dump(path)
        assert migration.upgrade(engine) is False
        assert _dump(path) == before
    finally:
        engine.dispose()


def test_fresh_create_all_database_is_left_untouched(tmp_path):
    path = tmp_path / "fresh.db"
    engine = _engine(path)
    Base.metadata.create_all(engine)
    try:
        before = _dump(path)
        assert migration.upgrade(engine) is False
        assert _dump(path) == before
    finally:
        engine.dispose()


def test_missing_index_on_an_existing_table_is_repaired(tmp_path):
    path = tmp_path / "half.db"
    engine = _build_pre_notification_db(path)
    try:
        assert migration.upgrade(engine) is True
        with engine.begin() as conn:
            conn.execute(text("DROP INDEX ix_notifications_recipient_read"))
        assert migration.upgrade(engine) is True
        names = {i["name"] for i in inspect(engine).get_indexes("notifications")}
        assert "ix_notifications_recipient_read" in names
        assert migration.upgrade(engine) is False
    finally:
        engine.dispose()


def test_database_without_lexgraph_tables_is_not_touched(tmp_path):
    path = tmp_path / "empty.db"
    engine = _engine(path)
    try:
        assert migration.upgrade(engine) is False
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()


def test_downgrade_refuses_to_drop_stored_notifications(tmp_path):
    path = tmp_path / "old.db"
    engine = _build_pre_notification_db(path)
    try:
        assert migration.upgrade(engine) is True
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO notifications (id, recipient_user_id, actor_user_id, event_type, "
                    "payload, created_at) VALUES ('n-1', 'u-1', 'u-1', 'comment_added', '{}', "
                    "'2026-11-16 08:00:00.000000')"
                )
            )
        with pytest.raises(RuntimeError, match="non-empty table 'notifications'"):
            migration.downgrade(engine)
        assert "notifications" in inspect(engine).get_table_names()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM notifications"))
        migration.downgrade(engine)
        assert not set(NEW_TABLES) & set(inspect(engine).get_table_names())
        assert migration.upgrade(engine) is True
    finally:
        engine.dispose()


def test_migration_follows_the_discovery_convention():
    assert migration.MIGRATION_ID == "20261116_durable_notifications"
    assert callable(migration.upgrade)
