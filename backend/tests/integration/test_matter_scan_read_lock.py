"""How the duplicate and related scans read a matter on SQLite (review
authoring:3, second round).

On SQLite (rollback journal) a statement holds the database's read lock
until it has finished, and a COMMIT anywhere in the database waits for every
statement that was running when it began, for at most the 5 s busy timeout.
The first fix read a matter in one statement that built a JSON array per row.
Alone that took 0.2 s on a matter of 220,000 assertions, but when 12 agent
submissions read the matter at once each statement ran 5 to 7 s: every row
value took an allocation from SQLite's process-wide heap, behind one lock,
once a long-lived connection had used up its private allocator on the
statements it keeps prepared. A comment posted in another matter meanwhile
failed with "database is locked" (a 500) in 3 of 3 such bursts.

The scan now reads a matter with one json_group_array() per column, straight
over the table (no per-row allocation), in statements of at most
MATTER_ROWS_PER_STATEMENT rows. These tests pin that it returns exactly what
the ORM query returns, that no statement reads more than one chunk, that no
lock is held between the statements, and that every statement is a single
index search with no per-row value building.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid

import pytest
from sqlalchemy import select, text

import app.routers.assertions as assertions_router
from app.models.assertion import Assertion
from tests.conftest import seed_matter, seed_organization, seed_repository, seed_user

WAIT = 30

pytestmark = pytest.mark.skipif(not assertions_router._SQLITE_HAS_JSON, reason="the JSON scan needs SQLite 3.38")

# Text a JSON encoding must carry exactly.
AWKWARD = [
    'He said "no" \\ then left', "emoji \U0001F600 and é", "tab\tnew\nline\r", "nul\x00inside",
    "ctrl \x01\x1f", "<b>markup</b>", "'single' quotes", "trailing space ", "  ", "",
]
STATUSES = ["accepted", "proposed", "draft", "withdrawn", "rejected", "revision_requested", "disputed",
            "superseded"]
STAMPS = ["2026-11-16 10:00:00.000000", "2026-11-16T09:00:00", "2026-11-16 10:00:00+00:00",
          "2026-01-01 00:00:00", "2026-11-16 10:00:00.000000"]


@pytest.fixture()
def matters(db_session) -> dict:
    org = seed_organization(db_session)
    repo = seed_repository(db_session, organization_id=org)
    author = seed_user(db_session, display_name="Author")
    return {"org": org, "repo": repo, "author": author,
            "matter": seed_matter(db_session, repository_id=repo, name="Big"),
            "other": seed_matter(db_session, repository_id=repo, name="Other")}


def _insert(session, matters, matter_id: str, count: int) -> None:
    rows = []
    for k in range(count):
        rows.append({
            "id": str(uuid.uuid4()), "org": matters["org"], "repo": matters["repo"], "m": matter_id,
            "p": f"{AWKWARD[k % len(AWKWARD)]} {k}" if k % 3 else AWKWARD[k % len(AWKWARD)],
            "t": "INTERPRETS" if k % 2 else "USES_DEFINITION",
            "st": "Document" if k % 2 else "Article", "sid": str(uuid.uuid4()),
            "ot": None if k % 4 else "Definition", "oid": None if k % 4 else str(uuid.uuid4()),
            "status": STATUSES[k % len(STATUSES)], "author": matters["author"],
            "created": STAMPS[k % len(STAMPS)],
        })
    session.execute(text(
        "INSERT INTO assertions (id, organization_id, repository_id, matter_id, assertion_type, proposition, "
        "subject_entity_type, subject_entity_id, object_entity_type, object_entity_id, origin, status, "
        "author_user_id, created_at, updated_at, current_revision_number) VALUES (:id, :org, :repo, :m, :t, :p, "
        ":st, :sid, :ot, :oid, 'system_generated', :status, :author, :created, :created, 1)"), rows)
    session.commit()


def _orm_rows(session, matter_id: str) -> list[tuple]:
    return [tuple(row) for row in session.execute(
        select(*assertions_router._MATCH_COLUMNS)
        .where(Assertion.matter_id == matter_id)
        .order_by(Assertion.created_at, Assertion.id)
    ).all()]


@pytest.mark.parametrize("per_statement", [1, 2, 3, 7, 50_000])
def test_the_scan_reads_exactly_what_the_orm_query_reads(db_session, matters, monkeypatch, per_statement):
    _insert(db_session, matters, matters["matter"], 45)
    _insert(db_session, matters, matters["other"], 5)
    monkeypatch.setattr(assertions_router, "MATTER_ROWS_PER_STATEMENT", per_statement)

    rows = [tuple(row) for row in assertions_router._matter_rows(db_session, matters["matter"])]

    assert rows == _orm_rows(db_session, matters["matter"])
    assert len(rows) == 45
    assert assertions_router._matter_rows(db_session, str(uuid.uuid4())) == []


def test_no_statement_reads_more_than_one_chunk(db_session, matters, monkeypatch):
    _insert(db_session, matters, matters["matter"], 45)  # 8 statuses, 5 or 6 rows each
    monkeypatch.setattr(assertions_router, "MATTER_ROWS_PER_STATEMENT", 4)
    sizes: list[int] = []
    original = assertions_router._decoded_rows

    def measured(session, statement, params):
        rows = original(session, statement, params)
        sizes.append(len(rows))
        return rows

    monkeypatch.setattr(assertions_router, "_decoded_rows", measured)

    assert len(assertions_router._matter_rows(db_session, matters["matter"])) == 45
    assert max(sizes) == 4 and sum(sizes) == 45 and len(sizes) == 16  # two statements per status


def test_a_write_elsewhere_commits_between_the_statements_of_a_matter_read(app, db_session, matters, monkeypatch):
    """While a large matter is being read, no read lock is held between its
    statements: another connection commits with a 0.2 s busy timeout."""
    _insert(db_session, matters, matters["matter"], 45)
    monkeypatch.setattr(assertions_router, "MATTER_ROWS_PER_STATEMENT", 4)
    original = assertions_router._decoded_rows
    paused, resume, calls = threading.Event(), threading.Event(), []

    def pausing(session, statement, params):
        rows = original(session, statement, params)
        calls.append(len(rows))
        if len(calls) == 1:
            paused.set()
            assert resume.wait(WAIT)
        return rows

    monkeypatch.setattr(assertions_router, "_decoded_rows", pausing)
    result: dict = {}

    def read() -> None:
        session = app.state.session_factory()
        try:
            result["rows"] = [tuple(row) for row in assertions_router._matter_rows(session, matters["matter"])]
        finally:
            session.close()

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    assert paused.wait(WAIT)

    path = app.state.engine.url.database
    writer = sqlite3.connect(path, timeout=0.2, isolation_level=None)
    holder = sqlite3.connect(path, timeout=0.2, isolation_level=None)
    try:
        # The control: a connection that keeps a read lock makes this commit fail.
        holder.execute("BEGIN")
        holder.execute("SELECT count(*) FROM assertions").fetchone()
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE matters SET name = 'Other matter' WHERE id = ?", (matters["other"],))
        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            writer.execute("COMMIT")
        writer.execute("ROLLBACK")
        holder.execute("ROLLBACK")

        # The reader, paused between two statements, keeps none.
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE matters SET name = 'Other matter' WHERE id = ?", (matters["other"],))
        writer.execute("COMMIT")
    finally:
        resume.set()
        writer.close()
        holder.close()
    reader.join(WAIT)
    assert not reader.is_alive()
    assert result["rows"] == _orm_rows(db_session, matters["matter"])
    assert len(calls) > 1


def test_every_statement_of_the_scan_is_one_index_search(db_session):
    """No subquery, sort or temporary table, and no JSON value built per row:
    each of those allocates for every row (see the module docstring)."""
    statements = [
        assertions_router._MATTER_SIZE_SQL, assertions_router._ALL_ROWS_AS_JSON,
        assertions_router._FIRST_MATTER_STATUS_SQL, assertions_router._NEXT_MATTER_STATUS_SQL,
        *assertions_router._STATUS_ROWS_AS_JSON.values(), *assertions_router._CHUNK_END_SQL.values(),
    ]
    params = {"matter_id": "m", "status": "accepted", "after": 1, "upto": 9, "offset": 3}
    for statement in statements:
        sql = str(statement)
        assert "json_array(" not in sql and "json_object(" not in sql, sql
        plan = [row[-1] for row in db_session.execute(text("EXPLAIN QUERY PLAN " + sql), params).all()]
        assert len(plan) == 1, (sql, plan)
        assert plan[0].startswith("SEARCH assertions USING ") and "ix_assertions_matter_id_status" in plan[0], plan
