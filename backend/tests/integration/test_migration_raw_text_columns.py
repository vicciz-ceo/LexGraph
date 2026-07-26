"""Track A, item A1 — reversible migration adding `_raw` text columns
(issue #2, gate G3).

`app.migrations.add_raw_text_columns` does not exist yet -- ModuleNotFoundError
is the expected RED signal. Once the Developer adds it, `upgrade(engine)`
must add `proposition_raw` (assertion_revisions), `comment_text_raw`
(assertion_comments), and `rationale_raw` (assertion_ratings), backfilling
each pre-existing row's raw column with its current sanitized value (issue
#2: "historical rows cannot be recovered" -- the sanitized value is the best
available approximation). `downgrade(engine)` must remove exactly those
three columns and leave every other column/row untouched.

This test builds the PRE-migration schema by hand (raw DDL matching the
columns those three tables have TODAY, before this sprint's ORM changes) --
it deliberately does NOT use `Base.metadata.create_all()`, since after the
Developer edits the ORM models `Base.metadata` will already include the new
columns and could no longer represent a genuinely pre-migration database
(the realistic scenario this migration exists for: an existing local SQLite
file created by an older version of this app).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text


def _new_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def pre_migration_engine(tmp_path):
    """A SQLite DB with the three affected tables in their PRE-sprint shape
    (plus the minimal parent tables their foreign keys reference), seeded
    with one row each so backfill/downgrade behavior is observable.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'pre_migration.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE organizations (id VARCHAR(36) PRIMARY KEY, name VARCHAR(255))"))
        conn.execute(
            text(
                "CREATE TABLE repositories (id VARCHAR(36) PRIMARY KEY, "
                "organization_id VARCHAR(36), name VARCHAR(255))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE matters (id VARCHAR(36) PRIMARY KEY, "
                "repository_id VARCHAR(36), name VARCHAR(255))"
            )
        )
        conn.execute(text("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255), display_name VARCHAR(255))"))
        conn.execute(
            text(
                "CREATE TABLE assertions (id VARCHAR(36) PRIMARY KEY, organization_id VARCHAR(36), "
                "repository_id VARCHAR(36), matter_id VARCHAR(36), assertion_type VARCHAR(255), "
                "proposition TEXT, subject_entity_type VARCHAR(255), subject_entity_id VARCHAR(255), "
                "origin VARCHAR(64), status VARCHAR(64), author_user_id VARCHAR(36), "
                "current_revision_number INTEGER)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE assertion_revisions (id VARCHAR(36) PRIMARY KEY, "
                "assertion_id VARCHAR(36), revision_number INTEGER, proposition TEXT, "
                "assertion_type VARCHAR(255), subject_entity_type VARCHAR(255), "
                "subject_entity_id VARCHAR(255), edited_by_user_id VARCHAR(36), created_at TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE assertion_comments (id VARCHAR(36) PRIMARY KEY, "
                "assertion_id VARCHAR(36), user_id VARCHAR(36), comment_text TEXT, "
                "created_at TEXT, updated_at TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE assertion_ratings (id VARCHAR(36) PRIMARY KEY, "
                "assertion_id VARCHAR(36), assertion_revision_id VARCHAR(36), user_id VARCHAR(36), "
                "strength INTEGER, rationale TEXT, created_at TEXT, updated_at TEXT)"
            )
        )

        conn.execute(
            text(
                "INSERT INTO assertion_revisions (id, assertion_id, revision_number, proposition, "
                "assertion_type, subject_entity_type, subject_entity_id, edited_by_user_id, created_at) "
                "VALUES (:id, :aid, 1, :prop, 'INTERPRETS', 'Provision', :sid, :uid, '2026-01-01')"
            ),
            {"id": _new_id(), "aid": _new_id(), "prop": "see  for details", "sid": _new_id(), "uid": _new_id()},
        )
        conn.execute(
            text(
                "INSERT INTO assertion_comments (id, assertion_id, user_id, comment_text, created_at, updated_at) "
                "VALUES (:id, :aid, :uid, :text, '2026-01-01', '2026-01-01')"
            ),
            {"id": _new_id(), "aid": _new_id(), "uid": _new_id(), "text": "Good point."},
        )
        conn.execute(
            text(
                "INSERT INTO assertion_ratings (id, assertion_id, assertion_revision_id, user_id, "
                "strength, rationale, created_at, updated_at) "
                "VALUES (:id, :aid, :rid, :uid, 4, :rationale, '2026-01-01', '2026-01-01')"
            ),
            {
                "id": _new_id(),
                "aid": _new_id(),
                "rid": _new_id(),
                "uid": _new_id(),
                "rationale": "Strong support.",
            },
        )
    return engine


def _columns(engine, table: str) -> set[str]:
    return {col["name"] for col in inspect(engine).get_columns(table)}


def test_upgrade_adds_raw_columns_and_backfills_existing_rows(pre_migration_engine):
    from app.migrations.add_raw_text_columns import upgrade

    upgrade(pre_migration_engine)

    assert "proposition_raw" in _columns(pre_migration_engine, "assertion_revisions")
    assert "comment_text_raw" in _columns(pre_migration_engine, "assertion_comments")
    assert "rationale_raw" in _columns(pre_migration_engine, "assertion_ratings")

    with pre_migration_engine.connect() as conn:
        rev = conn.execute(text("SELECT proposition, proposition_raw FROM assertion_revisions")).one()
        assert rev.proposition_raw == rev.proposition == "see  for details"

        comment = conn.execute(text("SELECT comment_text, comment_text_raw FROM assertion_comments")).one()
        assert comment.comment_text_raw == comment.comment_text == "Good point."

        rating = conn.execute(text("SELECT rationale, rationale_raw FROM assertion_ratings")).one()
        assert rating.rationale_raw == rating.rationale == "Strong support."


def test_downgrade_removes_raw_columns_and_preserves_other_data(pre_migration_engine):
    from app.migrations.add_raw_text_columns import downgrade, upgrade

    upgrade(pre_migration_engine)
    downgrade(pre_migration_engine)

    assert "proposition_raw" not in _columns(pre_migration_engine, "assertion_revisions")
    assert "comment_text_raw" not in _columns(pre_migration_engine, "assertion_comments")
    assert "rationale_raw" not in _columns(pre_migration_engine, "assertion_ratings")

    with pre_migration_engine.connect() as conn:
        rev = conn.execute(text("SELECT proposition FROM assertion_revisions")).one()
        assert rev.proposition == "see  for details"
