"""A request that meets a locked SQLite database answers a JSON 503.

SQLite answers "database is locked" (SQLITE_BUSY) when another connection
keeps a lock past the busy timeout: a COMMIT waits for a reader, the write
lock's BEGIN IMMEDIATE (app.services.write_lock) for another writer under
heavy load, a read for a writer that is writing its changes out. Over REST
that OperationalError reached Starlette's plain-text "Internal Server Error":
no reason, no X-Request-ID, nothing to tell a client that a retry would do,
while the agent guide says a 500 names its reason and that a locked database
is worth retrying. Such a request now answers 503 with a JSON `detail` that
names the locked database, a Retry-After header and X-Request-ID, once its
transaction is rolled back (the request's session closes first, and app.db's
pool hook rolls back what a failed COMMIT left open). Every other database
error is still the bare 500.

The locks are real, held from a second sqlite3 connection, with the busy
timeout shortened through the database URL; the last HTTP test goes through a
real uvicorn server on a socket. What other processes and the next requests
see after a failed COMMIT is checked in
test_failed_commit_releases_the_database.py.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import request_guards
from app.db import Base, make_engine
from app.main import create_app
from tests.conftest import assertion_payload, seed_document, seed_source_span
from tests.integration.test_failed_commit_releases_the_database import (
    BUSY_TIMEOUT_SECONDS,
    _assert_database_released,
    _reader_holding_shared,
    _stored,
)

SPOOFED = "chosen-by-the-client"
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


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
def _locked(database: str, begin: str) -> Iterator[None]:
    """Another process's transaction: BEGIN IMMEDIATE holds the write lock
    (readers proceed, writers wait); BEGIN EXCLUSIVE holds off readers too."""
    holder = sqlite3.connect(database, isolation_level=None)
    try:
        holder.execute(begin)
        yield
    finally:
        holder.execute("ROLLBACK")
        holder.close()


def _assert_busy_503(status: int, headers, body: bytes) -> None:
    assert status == 503, body
    assert headers["content-type"] == "application/json"
    assert "database is locked" in json.loads(body)["detail"]
    assert headers["retry-after"] == str(request_guards.DATABASE_BUSY_RETRY_AFTER_SECONDS)
    assert headers.get("x-request-id") not in (None, "", SPOOFED)


def test_a_write_that_waited_past_the_busy_timeout_for_the_write_lock_answers_503(app, matter_with_users):
    m = matter_with_users
    database = app.state.engine.url.database
    payload = assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed")
    with TestClient(app, raise_server_exceptions=False) as client:
        with _locked(database, "BEGIN IMMEDIATE"):
            refused = client.post("/api/v1/assertions", json=payload,
                                  headers={**m["contributor_headers"], "X-Request-ID": SPOOFED})
        _assert_busy_503(refused.status_code, refused.headers, refused.content)

        _assert_database_released(database)
        assert _stored(database, payload["proposition"]) == 0
        retried = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
        assert retried.status_code == 201, retried.text
        assert _stored(database, payload["proposition"]) == 1


def test_a_failed_commit_is_rolled_back_before_the_503_is_answered(app, matter_with_users, monkeypatch):
    """By the time the handler looks at the error, the request's session is
    closed and the pool has rolled back the transaction SQLAlchemy left open:
    no journal, and another process can take the write lock, so a client that
    retries at once does not meet this request's own leftover lock."""
    m = matter_with_users
    database = app.state.engine.url.database
    decided = []
    real = request_guards.is_database_busy

    def observing(exc):
        _assert_database_released(database)
        decided.append(app.state.engine.pool.checkedout())
        return real(exc)

    monkeypatch.setattr(request_guards, "is_database_busy", observing)
    with TestClient(app, raise_server_exceptions=False) as client:
        with _reader_holding_shared(database):
            refused = client.post("/api/v1/assertions", headers=m["contributor_headers"],
                                  json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"))
    _assert_busy_503(refused.status_code, refused.headers, refused.content)
    assert decided == [0]  # no connection is still checked out


def test_any_route_that_meets_the_lock_answers_503_and_the_next_request_is_served(app, matter_with_users):
    """Reads too, before the request is even authenticated (the token lookup
    waits for the lock), and a comment, whose INSERT waits for the write lock."""
    m = matter_with_users
    database = app.state.engine.url.database
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post("/api/v1/assertions", headers=m["contributor_headers"],
                              json=assertion_payload(m["matter_id"], m["repository_id"]))
        assert created.status_code == 201, created.text
        comments = f"/api/v1/assertions/{created.json()['id']}/comments"
        discussion = client.get(comments, headers=m["contributor_headers"]).json()  # the explanation

        with _locked(database, "BEGIN EXCLUSIVE"):
            read = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]},
                              headers=m["reviewer_headers"])
            assert client.get("/healthz").status_code == 200  # no database, no wait
        _assert_busy_503(read.status_code, read.headers, read.content)

        comment = {"comment_text": "Clause 8.4 governs."}
        with _locked(database, "BEGIN IMMEDIATE"):
            refused = client.post(comments, json=comment, headers=m["contributor_headers"])
        _assert_busy_503(refused.status_code, refused.headers, refused.content)
        assert read.headers["x-request-id"] != refused.headers["x-request-id"]

        _assert_database_released(database)
        assert client.get(comments, headers=m["contributor_headers"]).json() == discussion
        assert client.post(comments, json=comment, headers=m["contributor_headers"]).status_code == 201
        assert len(client.get(comments, headers=m["contributor_headers"]).json()) == len(discussion) + 1


def test_every_other_database_error_is_still_the_bare_500(app, matter_with_users):
    m = matter_with_users
    with TestClient(app) as strict, TestClient(app, raise_server_exceptions=False) as lenient:
        dropper = sqlite3.connect(app.state.engine.url.database, isolation_level=None)
        dropper.execute("DROP TABLE notifications")  # after the startup check, which would refuse it
        dropper.close()
        with pytest.raises(OperationalError, match="no such table"):
            strict.get("/api/v1/notifications", headers=m["contributor_headers"])  # unhandled, as before
        response = lenient.get("/api/v1/notifications", headers=m["contributor_headers"])
    assert (response.status_code, response.text) == (500, "Internal Server Error")
    assert "retry-after" not in response.headers and "x-request-id" not in response.headers


# --- Through a real server ------------------------------------------------------


def _free_port() -> int:
    """A free port, from LEXGRAPH_TEST_PORTS=first-last when it is set."""
    first, _, last = os.environ.get("LEXGRAPH_TEST_PORTS", "").partition("-")
    for candidate in range(int(first), int(last or first) + 1) if first else [0]:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return probe.getsockname()[1]
    pytest.skip("no free TCP port in LEXGRAPH_TEST_PORTS")


@contextmanager
def _serving(app) -> Iterator[str]:
    """`app` on a uvicorn server in its own thread; yields the base URL. Always stopped."""
    import uvicorn

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline, "uvicorn did not start"
            time.sleep(0.05)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(30)


def _post(url: str, body: dict, headers: dict) -> tuple[int, object, bytes]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with _DIRECT.open(request, timeout=30) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, error.headers, error.read()


def test_an_agent_submission_through_a_real_server_answers_503_and_its_retry_201(
        app, db_session, matter_with_users):
    m = matter_with_users
    database = app.state.engine.url.database
    document = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=document, matter_id=m["matter_id"],
                            quote_text="Confidentiality shall survive termination.")
    suggestion = dict(
        repository_id=m["repository_id"], matter_id=m["matter_id"], assertion_type="SURVIVES_TERMINATION",
        proposition="The confidentiality obligation survives termination.",
        subject_entity={"type": "Document", "id": document},
        evidence=[{"source_span_id": span, "evidence_role": "primary_basis"}],
        agent={"platform": "claude-code"}, save_as="proposed")
    with _serving(app) as base:
        url = f"{base}/api/v1/agent/assertions"
        with _locked(database, "BEGIN IMMEDIATE"):
            status, headers, body = _post(url, suggestion, m["contributor_headers"])
        _assert_busy_503(status, headers, body)
        assert _stored(database, suggestion["proposition"]) == 0

        status, _, body = _post(url, suggestion, m["contributor_headers"])
        assert status == 201, body
        assert _stored(database, suggestion["proposition"]) == 1


# --- Which errors are the busy database -----------------------------------------


def test_only_sqlite_busy_counts_as_the_busy_database(tmp_path):
    busy = request_guards.is_database_busy
    path = str(tmp_path / "busy.db")
    setup = sqlite3.connect(path, isolation_level=None)
    setup.execute("CREATE TABLE t (x)")
    setup.execute("INSERT INTO t VALUES (1), (2)")
    engine = make_engine(f"sqlite:///{path}?timeout=0")
    try:
        with _locked(path, "BEGIN IMMEDIATE"):
            other = sqlite3.connect(path, timeout=0, isolation_level=None)
            with pytest.raises(sqlite3.OperationalError) as raw:
                other.execute("BEGIN IMMEDIATE")
            other.close()
            with engine.connect() as connection, pytest.raises(OperationalError) as wrapped:
                connection.execute(text("INSERT INTO t VALUES (3)"))
        assert raw.value.sqlite_errorcode == sqlite3.SQLITE_BUSY
        assert busy(raw.value) and busy(wrapped.value)

        with engine.connect() as connection, pytest.raises(OperationalError) as missing:
            connection.execute(text("SELECT * FROM missing"))
        reading = setup.execute("SELECT x FROM t")
        reading.fetchone()
        with pytest.raises(sqlite3.OperationalError) as table_locked:  # SQLITE_LOCKED: within one connection
            setup.execute("DROP TABLE t")
        assert table_locked.value.sqlite_errorcode == sqlite3.SQLITE_LOCKED
        assert not busy(missing.value) and not busy(table_locked.value)
    finally:
        engine.dispose()
        setup.close()

    # Without SQLite's result code (another sqlite3 build), the message decides.
    assert busy(sqlite3.OperationalError("database is locked"))
    assert not busy(sqlite3.OperationalError("database table is locked"))
    # Another driver's error is never this one.
    assert not busy(OperationalError("SELECT 1", {}, RuntimeError("database is locked")))
