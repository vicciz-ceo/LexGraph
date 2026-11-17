"""A COMMIT that fails must leave nothing behind (review authoring:0).

On SQLite a COMMIT needs every other connection's SHARED lock gone; a reader
that keeps one past the busy timeout makes it fail with "database is locked".
SQLAlchemy then deactivates the transaction without rolling it back, and
closing the session handed the connection back to the pool still inside it:
the whole database stayed locked for every process, and the next request that
drew that connection committed the failed request's rows or answered with a
409 naming an assertion that was never committed.

These tests hold a real SHARED lock from a second sqlite3 connection across a
write, through the HTTP app and through the MCP server's per-call sessions, and
then check what other processes and the next requests see. The busy timeout is
shortened through the database URL so a failing COMMIT takes half a second.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text

import app.db as app_db
from app.db import Base, make_engine, make_session_factory
from app.main import create_app
from app.mcp.server import create_server
from app.models.assertion import Assertion
from app.services.write_lock import ForeignTransactionError, lock_assertion_writes
from tests.conftest import assertion_payload, seed_document, seed_source_span
from tests.integration.agent_surface_helpers import call_tool, tool_error

BUSY_TIMEOUT_SECONDS = 0.5


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """The conftest `app`, with a short busy timeout (overrides it here)."""
    monkeypatch.setenv(
        "LEXGRAPH_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}?timeout={BUSY_TIMEOUT_SECONDS}"
    )
    application = create_app()
    Base.metadata.create_all(bind=application.state.engine)
    yield application
    application.state.engine.dispose()


@contextmanager
def _reader_holding_shared(database: str):
    """Another process's open read transaction: it holds SHARED until it ends."""
    reader = sqlite3.connect(database, isolation_level=None)
    try:
        reader.execute("BEGIN")
        reader.execute("SELECT count(*) FROM assertions").fetchone()
        yield
    finally:
        reader.execute("ROLLBACK")
        reader.close()


def _database(app) -> str:
    return app.state.engine.url.database


def _assert_database_released(database: str) -> None:
    """No hot journal is left and another process can take the write lock at once."""
    assert not Path(database + "-journal").exists(), "a rolled-back transaction leaves no journal"
    other = sqlite3.connect(database, timeout=0, isolation_level=None)
    try:
        other.execute("BEGIN IMMEDIATE")
        other.execute("ROLLBACK")
    finally:
        other.close()


def _stored(database: str, proposition: str) -> int:
    """Committed rows with `proposition`, read by another process."""
    reader = sqlite3.connect(database, timeout=5)
    try:
        return reader.execute(
            "SELECT count(*) FROM assertions WHERE proposition = ?", (proposition,)
        ).fetchone()[0]
    finally:
        reader.close()


def _assert_idle_connections_hold_no_transaction(engine) -> None:
    idle = [engine.raw_connection() for _ in range(engine.pool.checkedin())]
    try:
        assert idle, "the pool should hold the connections the requests used"
        assert [conn.dbapi_connection.in_transaction for conn in idle] == [False] * len(idle)
    finally:
        for conn in idle:
            conn.close()


def test_a_create_whose_commit_failed_leaves_the_database_unlocked_and_unchanged(app, matter_with_users):
    m = matter_with_users
    database = _database(app)
    payload = assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed")
    with TestClient(app, raise_server_exceptions=False) as client:
        listing = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]},
                             headers=m["reviewer_headers"])
        assert listing.status_code == 200

        with _reader_holding_shared(database):
            failed = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
        # A JSON 503 that names the locked database, not the bare plain-text 500
        # (test_database_busy_answers_503.py covers the other ways to meet the lock).
        assert failed.status_code == 503, failed.text
        assert "database is locked" in failed.json()["detail"]
        assert int(failed.headers["retry-after"]) >= 1
        assert failed.headers.get("x-request-id")

        _assert_database_released(database)
        assert _stored(database, payload["proposition"]) == 0
        _assert_idle_connections_hold_no_transaction(app.state.engine)

        # Other requests are served normally, and none of them commits the failed write.
        other = client.post("/api/v1/assertions", headers=m["contributor_headers"], json=assertion_payload(
            m["matter_id"], m["repository_id"], proposition="Clause 9 governs notices.", save_as="proposed"))
        assert other.status_code == 201, other.text
        assert _stored(database, payload["proposition"]) == 0

        # Retrying the same payload, as the agent guide advises for a locked database, stores it once.
        retried = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
        assert retried.status_code == 201, retried.text
        assert _stored(database, payload["proposition"]) == 1
        history = client.get(f"/api/v1/assertions/{retried.json()['id']}/history",
                             headers=m["contributor_headers"])
        assert [row["event_type"] for row in history.json()] == ["assertion_created", "comment_created"]


@pytest.fixture()
def suggestion(db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                            quote_text="Confidentiality shall survive termination.")
    return dict(repository_id=m["repository_id"], matter_id=m["matter_id"], assertion_type="SURVIVES_TERMINATION",
                proposition="The confidentiality obligation survives termination.",
                subject_entity={"type": "Document", "id": doc},
                evidence=[{"source_span_id": span, "evidence_role": "primary_basis"}],
                agent={"platform": "claude-code"}, save_as="proposed")


@pytest.mark.parametrize("next_call", ["retry", "other"])
def test_an_mcp_suggestion_whose_commit_failed_is_not_committed_later(app, matter_with_users, suggestion,
                                                                       next_call):
    """The MCP server is one long-lived process: its next call used to draw
    the leaked connection, then answer the retry with a 409 naming an
    assertion that was never committed, or commit the failed one together
    with a different suggestion."""
    database = _database(app)
    server = create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"])

    with _reader_holding_shared(database):
        failure = tool_error(server, "suggest_assertion", {"payload": suggestion})
    assert failure["status"] == 500 and "locked" in failure["error"], failure

    _assert_database_released(database)
    assert _stored(database, suggestion["proposition"]) == 0

    payload = suggestion if next_call == "retry" else {**suggestion, "proposition": "Clause 9 governs notices."}
    is_error, body = call_tool(server, "suggest_assertion", {"payload": payload})
    assert not is_error, body
    assert _stored(database, payload["proposition"]) == 1
    assert _stored(database, suggestion["proposition"]) == (1 if next_call == "retry" else 0)


def test_the_write_lock_refuses_a_transaction_its_session_did_not_open(tmp_path, matter_with_users):
    """Even with the pool's rollback removed, a write that follows a failed
    commit does not adopt the leaked transaction: `lock_assertion_writes`
    discards it and refuses, instead of claiming the lock inside it."""
    del matter_with_users  # the schema and a matter, in the conftest database
    path = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{path}?timeout={BUSY_TIMEOUT_SECONDS}")
    event.remove(engine, "reset", app_db.rollback_leftover_transaction)
    sessions = make_session_factory(engine)
    matter_id = sqlite3.connect(path).execute("SELECT id FROM matters").fetchone()[0]
    try:
        failed = sessions()
        failed.execute(text("UPDATE matters SET name = 'written by a request that failed' WHERE id = :id"),
                       {"id": matter_id})
        with _reader_holding_shared(str(path)), pytest.raises(Exception, match="locked"):
            failed.commit()
        failed.close()  # the connection goes back to the pool inside its transaction

        later = sessions()
        assert later.connection().connection.dbapi_connection.in_transaction  # the leak this guards against
        with pytest.raises(ForeignTransactionError):
            lock_assertion_writes(later, matter_id)
        assert not later.connection().connection.dbapi_connection.in_transaction
        later.close()

        _assert_database_released(str(path))
        with sessions() as fresh:
            assert fresh.scalar(text("SELECT name FROM matters WHERE id = :id"), {"id": matter_id}) != (
                "written by a request that failed")
            lock_assertion_writes(fresh, matter_id)  # a clean connection takes the lock as before
            fresh.rollback()
    finally:
        engine.dispose()


def test_every_engine_rolls_back_what_a_failed_commit_left_open(tmp_path, matter_with_users):
    """The fix lives in `make_engine`, so the CLIs, the MCP server, the auth and
    hook sessions and every router get it: the next session on the same
    pooled connection starts outside any transaction and sees no failed write."""
    del matter_with_users
    path = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{path}?timeout={BUSY_TIMEOUT_SECONDS}")
    sessions = make_session_factory(engine)
    try:
        with sessions() as failed:
            failed.add(Assertion(
                organization_id=failed.scalar(text("SELECT id FROM organizations")),
                repository_id=failed.scalar(text("SELECT id FROM repositories")),
                matter_id=failed.scalar(text("SELECT id FROM matters")),
                assertion_type="INTERPRETS", proposition="Never committed.", subject_entity_type="Provision",
                subject_entity_id="p-1", origin="user_suggested", status="draft",
                author_user_id=failed.scalar(text("SELECT id FROM users LIMIT 1")),
                created_at=_now(), updated_at=_now(), current_revision_number=1,
            ))
            failed.flush()
            with _reader_holding_shared(str(path)), pytest.raises(Exception, match="locked"):
                failed.commit()

        _assert_database_released(str(path))
        with sessions() as later:
            assert not later.connection().connection.dbapi_connection.in_transaction
            assert later.scalars(select(Assertion.proposition)).all() == []
    finally:
        engine.dispose()


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
