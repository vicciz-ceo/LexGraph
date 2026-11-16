"""`app.migrations.m20261116_sign_in_tokens` (finding api:2 backward
compatibility).

Builds a database in the exact pre-upgrade `users` shape with raw DDL (no
`sign_in_token_hash`), upgrades it, and proves existing sign-ins keep
working as flagged legacy credentials. Follows the migration convention:
idempotent, True only when something changed.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.auth import hash_sign_in_token
from app.db import Base
from app.main import create_app
from app.migrate import SchemaNotCurrentError
from app.migrate import main as migrate_main
from app.migrations import m20261116_sign_in_tokens as migration
from tests.conftest import auth_header, token_header

OLD_USERS_DDL = (
    "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, "
    "email VARCHAR(255) NOT NULL, display_name VARCHAR(255) NOT NULL)"
)


def _old_schema_db(path):
    """Every current table, but `users` in its pre-upgrade shape."""
    engine = create_engine(f"sqlite:///{path}")
    import app.models  # noqa: F401  (register mappings)

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DROP TABLE users"))
        conn.execute(text(OLD_USERS_DDL))
    return engine


def _seed_old(engine):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id, name) VALUES ('o1', 'Org')"))
        conn.execute(
            text("INSERT INTO repositories (id, organization_id, name) VALUES ('r1', 'o1', 'Repo')")
        )
        conn.execute(text("INSERT INTO matters (id, repository_id, name) VALUES ('m1', 'r1', 'M')"))
        for user_id, role in (("old-admin", "admin"), ("old-viewer", "viewer")):
            conn.execute(
                text("INSERT INTO users (id, email, display_name) VALUES (:id, :e, :n)"),
                {"id": user_id, "e": f"{user_id}@example.test", "n": user_id.title()},
            )
            conn.execute(
                text(
                    "INSERT INTO matter_roles (id, user_id, matter_id, role) "
                    "VALUES (:id, :u, 'm1', :role)"
                ),
                {"id": f"role-{user_id}", "u": user_id, "role": role},
            )


def _user_schema(engine):
    inspector = inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("users")}
    indexes = {i["name"]: i for i in inspector.get_indexes("users")}
    return columns, indexes


def test_upgrade_adds_the_column_and_preserves_existing_sign_ins(tmp_path, monkeypatch, caplog):
    db_path = tmp_path / "old.db"
    engine = _old_schema_db(db_path)
    _seed_old(engine)

    assert migration.MIGRATION_ID == "20261116_sign_in_tokens"
    assert migration.upgrade(engine) is True

    columns, indexes = _user_schema(engine)
    assert columns["sign_in_token_hash"]["nullable"] is True
    index = indexes["ix_users_sign_in_token_hash"]
    assert index["column_names"] == ["sign_in_token_hash"] and index["unique"]
    with engine.connect() as conn:
        rows = dict(conn.execute(text("SELECT id, sign_in_token_hash FROM users")).all())
    assert rows == {
        "old-admin": hash_sign_in_token("old-admin"),
        "old-viewer": hash_sign_in_token("old-viewer"),
    }

    # Second run: nothing left to do.
    assert migration.upgrade(engine) is False
    engine.dispose()

    # The server only starts on a current schema (app.migrate's startup
    # check), and this old `users` table also predates the unique email
    # index: an operator upgrades with the runner, which re-runs this
    # migration as a no-op and applies the others.
    assert migrate_main(["--db", str(db_path)]) == 0
    migrated = create_engine(f"sqlite:///{db_path}")
    with migrated.connect() as conn:
        assert dict(conn.execute(text("SELECT id, sign_in_token_hash FROM users")).all()) == rows
    migrated.dispose()

    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app()
    try:
        with caplog.at_level(logging.WARNING, logger="app.auth"):
            with TestClient(app) as client:
                # The old credential (the id) still signs in...
                me = client.get("/api/v1/me", headers=auth_header("old-admin"))
                assert me.status_code == 200
                assert me.json()["matters"][0]["role"] == "admin"
                # ...and is flagged for rotation.
                listed = client.get("/api/v1/users", headers=auth_header("old-admin")).json()
                assert {u["id"]: u["sign_in_status"] for u in listed} == {
                    "old-admin": "legacy",
                    "old-viewer": "legacy",
                }
                rotated = client.post(
                    "/api/v1/users/old-viewer/sign-in-token", headers=auth_header("old-admin")
                )
                assert rotated.status_code == 200
                assert client.get("/api/v1/me", headers=auth_header("old-viewer")).status_code == 401
                new_token = rotated.json()["sign_in_token"]
                assert client.get("/api/v1/me", headers=token_header(new_token)).status_code == 200
        warning = next(r.getMessage() for r in caplog.records if r.name == "app.auth")
        assert "2 user account(s) still sign in with their public user id" in warning
    finally:
        app.state.engine.dispose()


def test_an_unmigrated_database_is_refused_at_startup_with_the_upgrade_command(tmp_path, monkeypatch):
    """Nobody could sign in on it, so the server does not start at all (the
    startup schema check) and says which command upgrades it."""
    db_path = tmp_path / "unmigrated.db"
    engine = _old_schema_db(db_path)
    _seed_old(engine)
    engine.dispose()

    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app()
    try:
        with pytest.raises(SchemaNotCurrentError) as refused:
            with TestClient(app):
                pass
        message = str(refused.value)
        assert "column users.sign_in_token_hash" in message
        assert f"-m app.migrate --db {db_path}" in message
    finally:
        app.state.engine.dispose()
    # Untouched: still the pre-upgrade users table.
    check = create_engine(f"sqlite:///{db_path}")
    assert "sign_in_token_hash" not in _user_schema(check)[0]
    check.dispose()


def test_upgrade_is_a_no_op_on_a_fresh_create_all_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    assert migration.upgrade(engine) is False
    columns, indexes = _user_schema(engine)
    assert "sign_in_token_hash" in columns and "ix_users_sign_in_token_hash" in indexes
    engine.dispose()


def test_upgrade_is_a_no_op_without_a_users_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    assert migration.upgrade(engine) is False
    assert not inspect(engine).has_table("users")
    engine.dispose()


def test_upgrade_finishes_an_interrupted_run(tmp_path):
    """SQLite commits ADD COLUMN at once; a run that stopped right after it
    must still backfill legacy hashes on the next run."""
    engine = _old_schema_db(tmp_path / "interrupted.db")
    _seed_old(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN sign_in_token_hash VARCHAR(64)"))

    assert migration.upgrade(engine) is True
    with engine.connect() as conn:
        hashes = dict(conn.execute(text("SELECT id, sign_in_token_hash FROM users")).all())
    assert hashes["old-admin"] == hash_sign_in_token("old-admin")
    assert "ix_users_sign_in_token_hash" in _user_schema(engine)[1]
    assert migration.upgrade(engine) is False
    engine.dispose()


def test_rerunning_never_turns_a_missing_credential_into_the_public_id(tmp_path):
    engine = _old_schema_db(tmp_path / "migrated.db")
    _seed_old(engine)
    assert migration.upgrade(engine) is True
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, display_name, sign_in_token_hash) "
                "VALUES ('no-credential', 'n@example.test', 'N', NULL)"
            )
        )

    assert migration.upgrade(engine) is False
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT sign_in_token_hash FROM users WHERE id = 'no-credential'")
        ).scalar_one()
    assert value is None
    engine.dispose()
