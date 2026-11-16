"""`app.migrations.m20261116_users_email_unique` (findings api:24 / ui:25).

Builds a database whose `users` table predates the unique email index
(raw DDL; emails stored the way the old code stored them: as typed, with
case variants and even exact duplicates left by the old creation race),
upgrades it, and checks the migration convention: idempotent, True only
when something changed, nothing deleted. Accounts that share an address
once case and surrounding spaces are ignored are reported, left exactly
as they are, and keep the index from being created until an operator
resolves them; meanwhile the API answers 409 for them, never 500.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.auth import hash_sign_in_token
from app.db import Base
from app.main import create_app
from app.migrate import SchemaNotCurrentError, check_schema, inspect_schema
from app.migrate import main as migrate_main
from app.migrations import m20261116_users_email_unique as migration
from app.routers.users import normalize_email
from tests.conftest import auth_header

# `users` as it was before this migration (sign-in tokens already added).
OLD_USERS_DDL = (
    "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) NOT NULL, "
    "display_name VARCHAR(255) NOT NULL, sign_in_token_hash VARCHAR(64))"
)


def _old_db(path, emails: dict[str, str]):
    engine = create_engine(f"sqlite:///{path}")
    import app.models  # noqa: F401  (register mappings)

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DROP TABLE users"))
        conn.execute(text(OLD_USERS_DDL))
        conn.execute(
            text("CREATE UNIQUE INDEX ix_users_sign_in_token_hash ON users (sign_in_token_hash)")
        )
        for user_id, email in emails.items():
            conn.execute(
                text(
                    "INSERT INTO users (id, email, display_name, sign_in_token_hash) "
                    "VALUES (:id, :email, :name, :hash)"
                ),
                {"id": user_id, "email": email, "name": user_id, "hash": hash_sign_in_token(user_id)},
            )
    return engine


def _emails(engine) -> dict[str, str]:
    with engine.connect() as conn:
        return dict(conn.execute(text("SELECT id, email FROM users")).all())


def _email_index(engine):
    return next(
        (i for i in inspect(engine).get_indexes("users") if i["name"] == "ix_users_email"), None
    )


def test_upgrade_normalizes_emails_and_adds_the_unique_index(tmp_path):
    engine = _old_db(
        tmp_path / "old.db",
        {"u1": "Mixed@Case.Test", "u2": "  padded@example.test ", "u3": "plain@example.test"},
    )

    assert migration.MIGRATION_ID == "20261116_users_email_unique"
    assert migration.upgrade(engine) is True

    assert _emails(engine) == {
        "u1": "mixed@case.test",
        "u2": "padded@example.test",
        "u3": "plain@example.test",
    }
    index = _email_index(engine)
    assert index is not None and index["unique"] and index["column_names"] == ["email"]
    assert migration.upgrade(engine) is False
    engine.dispose()


def test_shared_addresses_are_reported_and_left_untouched_until_resolved(tmp_path, caplog):
    before = {
        "u1": "dana@example.test",
        "u2": "Dana@Example.test",  # case variant of u1
        "u3": "exact@example.test",
        "u4": "exact@example.test",  # exact duplicate (old creation race)
        "u5": "Solo@Example.test",  # no conflict: normalized
    }
    engine = _old_db(tmp_path / "dupes.db", before)

    with caplog.at_level(logging.WARNING, logger=migration.__name__):
        assert migration.upgrade(engine) is True  # u5 was normalized

    after = _emails(engine)
    assert after == {**before, "u5": "solo@example.test"}  # nothing else changed
    assert _email_index(engine) is None
    warning = " ".join(r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    assert "2 email address(es)" in warning
    for user_id in ("u1", "u2", "u3", "u4"):
        assert user_id in warning
    assert "u5" not in warning

    # Re-running changes nothing more and reports them again.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=migration.__name__):
        assert migration.upgrade(engine) is False
    assert any("u2" in r.getMessage() for r in caplog.records)

    # Once an operator gives each account its own address, the next run
    # normalizes the rest and creates the index.
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET email = 'dana.b@example.test' WHERE id = 'u2'"))
        conn.execute(text("UPDATE users SET email = 'exact.b@example.test' WHERE id = 'u4'"))
    assert migration.upgrade(engine) is True
    assert _email_index(engine) is not None
    assert migration.upgrade(engine) is False
    engine.dispose()


def test_upgrade_is_a_no_op_on_a_fresh_create_all_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    assert _email_index(engine) is not None  # the model declares it
    assert migration.upgrade(engine) is False
    engine.dispose()


def test_upgrade_is_a_no_op_without_a_users_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    assert migration.upgrade(engine) is False
    assert not inspect(engine).has_table("users")
    engine.dispose()


@pytest.mark.parametrize(
    "raw", ["Ada@Firm.Example", "  ada@firm.example\t", "ÉLODIE@Example.test", "plain@x.test"]
)
def test_the_migration_normalizes_exactly_like_the_api(raw):
    assert migration.normalize_email(raw) == normalize_email(raw)


def test_the_runner_upgrades_around_shared_addresses_and_finishes_once_resolved(tmp_path, capsys):
    db_path = tmp_path / "shared.db"
    engine = _old_db(
        db_path, {"u1": "dana@example.test", "u2": "DANA@example.test", "u3": "Solo@Example.test"}
    )
    engine.dispose()

    # Usable but not finished: exit 0, and the pending index is named with
    # the accounts that block it (not reported as a missing migration).
    assert migrate_main(["--db", str(db_path)]) == 0
    out = capsys.readouterr().out
    assert "1 unique index(es) wait for an operator" in out
    assert "unique index ix_users_email" in out and "u1" in out and "u2" in out
    engine = create_engine(f"sqlite:///{db_path}")
    report, pending = check_schema(engine)
    assert report.is_current and report.pending_uniques == ("(email) on users",)
    assert list(pending) == ["ix_users_email"]
    assert _emails(engine)["u3"] == "solo@example.test"

    # After the operator's fix, the same command creates the index.
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET email = 'dana.b@example.test' WHERE id = 'u2'"))
    engine.dispose()
    assert migrate_main(["--db", str(db_path)]) == 0
    assert "the schema is current" in capsys.readouterr().out
    engine = create_engine(f"sqlite:///{db_path}")
    assert check_schema(engine) == (inspect_schema(engine), {})
    assert inspect_schema(engine).is_current and _email_index(engine) is not None
    engine.dispose()


def test_only_the_index_waiting_for_an_operator_is_excused_at_startup(tmp_path, monkeypatch):
    db_path = tmp_path / "shared-and-old.db"
    engine = _old_db(db_path, {"u1": "dana@example.test", "u2": "Dana@example.test"})
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX ix_users_sign_in_token_hash"))
    engine.dispose()

    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app()
    try:
        with pytest.raises(SchemaNotCurrentError, match=r"unique \(sign_in_token_hash\) on users"):
            with TestClient(app):
                pass
    finally:
        app.state.engine.dispose()


def test_unresolved_shared_addresses_answer_409_not_500(tmp_path, monkeypatch, caplog):
    db_path = tmp_path / "unresolved.db"
    engine = _old_db(
        db_path,
        {
            "admin": "admin@example.test",
            "u1": "dana@example.test",
            "u2": "DANA@example.test",
            "u3": "exact@example.test",
            "u4": "exact@example.test",
        },
    )
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id, name) VALUES ('o1', 'Org')"))
        conn.execute(
            text("INSERT INTO repositories (id, organization_id, name) VALUES ('r1', 'o1', 'R')")
        )
        conn.execute(text("INSERT INTO matters (id, repository_id, name) VALUES ('m1', 'r1', 'M')"))
        conn.execute(
            text(
                "INSERT INTO matter_roles (id, user_id, matter_id, role) "
                "VALUES ('r-admin', 'admin', 'm1', 'admin')"
            )
        )
    migration.upgrade(engine)
    engine.dispose()

    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app()
    try:
        # The startup schema check accepts the database (spec section 12: the
        # app keeps working until an operator resolves the shared addresses)
        # and logs which accounts block the index.
        with caplog.at_level(logging.WARNING, logger="uvicorn.error"), TestClient(app) as client:
            startup = " ".join(r.getMessage() for r in caplog.records if r.name == "uvicorn.error")
            assert "ix_users_email" in startup
            assert all(user_id in startup for user_id in ("u1", "u2", "u3", "u4"))
            for email in ("Dana@Example.test", "exact@example.test"):
                created = client.post(
                    "/api/v1/users",
                    json={"email": email, "display_name": "Another"},
                    headers=auth_header("admin"),
                )
                assert created.status_code == 409, created.text
                added = client.post(
                    "/api/v1/matters/m1/members",
                    json={"email": email, "role": "viewer"},
                    headers=auth_header("admin"),
                )
                assert added.status_code == 409, added.text
    finally:
        app.state.engine.dispose()
