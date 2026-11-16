"""Concurrent assertion writers (audit finding api:0).

The races are made deterministic rather than left to timing: a barrier
placed right after the unlocked part of a request holds every writer there
until all of them have read the same database state -- exactly the
interleaving that used to store duplicate revision numbers. Requests go
through the real HTTP app.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

import app.routers.assertions as assertions_router
from app.models.assertion_revision import AssertionRevision
from tests.conftest import assertion_payload, new_id

STALE = "assertion has been modified since expected_revision_number"


def _run_in_threads(count: int, fn) -> list:
    results: list = [None] * count
    errors: list[BaseException] = []

    def run(index: int) -> None:
        try:
            results[index] = fn(index)
        except BaseException as exc:  # reported below, never swallowed
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=90)
    assert not errors, errors
    return results


def _hold_after(monkeypatch, name: str, barrier: threading.Barrier) -> None:
    """Make `app.routers.assertions.<name>` wait at `barrier` after running."""
    original = getattr(assertions_router, name)

    def held(*args, **kwargs):
        result = original(*args, **kwargs)
        barrier.wait(timeout=30)
        return result

    monkeypatch.setattr(assertions_router, name, held)


@pytest.mark.parametrize("send_expected_revision", [True, False])
def test_concurrent_edits_of_one_revision_conflict_instead_of_duplicating_its_number(
        client, db_session, matter_with_users, monkeypatch, send_expected_revision):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    path = f"/api/v1/assertions/{created['id']}"
    _hold_after(monkeypatch, "validate_proposition_not_empty", threading.Barrier(2))

    def edit(index: int):
        body = {"proposition": f"Edited concurrently, version {index}."}
        if send_expected_revision:
            body["expected_revision_number"] = 1
        return client.patch(path, json=body, headers=m["contributor_headers"])

    responses = _run_in_threads(2, edit)

    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    assert next(r for r in responses if r.status_code == 409).json()["detail"] == STALE
    winner = next(r for r in responses if r.status_code == 200).json()
    numbers = db_session.scalars(select(AssertionRevision.revision_number).where(
        AssertionRevision.assertion_id == created["id"]).order_by(AssertionRevision.revision_number)).all()
    assert numbers == [1, 2]
    detail = client.get(path, headers=m["reviewer_headers"])
    assert detail.status_code == 200
    assert (detail.json()["current_revision_number"], detail.json()["proposition"]) == (2, winner["proposition"])
    listing = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]}, headers=m["reviewer_headers"])
    assert listing.status_code == 200


def test_a_revision_number_taken_by_another_writer_maps_to_the_stale_conflict(app, client, db_session,
                                                                               matter_with_users, monkeypatch):
    """A writer that bypassed the lock (or a database edited by hand) still
    cannot make two rows share a number: the unique index refuses the
    second, and the API reports the same 409 as a stale edit."""
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    original = assertions_router.validate_text_length

    def take_revision_two(value, **kwargs):
        with app.state.engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO assertion_revisions (id, assertion_id, revision_number, proposition, "
                "proposition_raw, assertion_type, subject_entity_type, subject_entity_id, "
                "edited_by_user_id, created_at) VALUES (:id, :aid, 2, 'other', 'other', 'X', 'Provision', "
                "'p', :uid, '2026-11-16 00:00:00')"),
                {"id": new_id(), "aid": created["id"], "uid": m["reviewer_id"]})
        monkeypatch.setattr(assertions_router, "validate_text_length", original)
        return original(value, **kwargs)

    monkeypatch.setattr(assertions_router, "validate_text_length", take_revision_two)
    response = client.patch(f"/api/v1/assertions/{created['id']}",
                            json={"proposition": "My edit.", "expected_revision_number": 1},
                            headers=m["contributor_headers"])

    assert (response.status_code, response.json()["detail"]) == (409, STALE)
    detail = client.get(f"/api/v1/assertions/{created['id']}", headers=m["contributor_headers"]).json()
    assert (detail["current_revision_number"], detail["proposition"]) == (1, created["proposition"])


def test_the_database_refuses_two_rows_with_one_revision_number(client, db_session, matter_with_users):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    db_session.add(AssertionRevision(
        id=new_id(), assertion_id=created["id"], revision_number=1, proposition="dup",
        assertion_type="X", subject_entity_type="Provision", subject_entity_id="p",
        edited_by_user_id=m["contributor_id"], created_at=datetime.now(timezone.utc),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_reads_survive_duplicate_revision_numbers_left_by_the_old_race(app, client, matter_with_users):
    """A database that has not run the unique-index migration yet may still
    hold two rows with one number; reads must not 500 the whole matter."""
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    with app.state.engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS uq_assertion_revisions_assertion_id_revision_number"))
        conn.execute(text(
            "INSERT INTO assertion_revisions (id, assertion_id, revision_number, proposition, "
            "proposition_raw, assertion_type, subject_entity_type, subject_entity_id, "
            "edited_by_user_id, created_at) VALUES (:id, :aid, 1, 'later', 'later duplicate', 'X', "
            "'Provision', 'p', :uid, '2999-01-01 00:00:00')"),
            {"id": new_id(), "aid": created["id"], "uid": m["contributor_id"]})

    detail = client.get(f"/api/v1/assertions/{created['id']}", headers=m["reviewer_headers"])
    assert detail.status_code == 200
    assert detail.json()["proposition_raw"] == "later duplicate"
    listing = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]}, headers=m["reviewer_headers"])
    assert listing.status_code == 200 and listing.json()["total"] == 1


@pytest.mark.parametrize("transaction", ["none", "after_a_write", "deferred_begin"])
def test_the_write_lock_excludes_other_writers_until_the_transaction_ends(app, matter_with_users,
                                                                          transaction):
    """`lock_assertion_writes` must hold SQLite's write lock whether or not
    the session's transaction was already open -- BEGIN IMMEDIATE when it
    was not; a no-op write when it was, including a deferred BEGIN that has
    not written yet (as under non-legacy sqlite3 transaction control) --
    and release it when the transaction ends."""
    import sqlite3

    from app.services.write_lock import lock_assertion_writes

    m = matter_with_users
    database = app.state.engine.url.database
    session = app.state.session_factory()
    try:
        if transaction == "after_a_write":
            session.execute(text("UPDATE users SET display_name = display_name WHERE id = :id"),
                            {"id": m["contributor_id"]})
        elif transaction == "deferred_begin":
            session.execute(text("BEGIN"))
            session.execute(text("SELECT COUNT(*) FROM assertions"))
        lock_assertion_writes(session, m["matter_id"])
        other = sqlite3.connect(database, timeout=0, isolation_level=None)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute("BEGIN IMMEDIATE")
            session.rollback()
            other.execute("BEGIN IMMEDIATE")
            other.execute("ROLLBACK")
        finally:
            other.close()
    finally:
        session.close()
