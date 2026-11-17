"""Concurrent rating writes by one user (review listing:3).

A double submit, two tabs or an agent's retry send the same user's rating
twice at once. Each request read the user's rating and then inserted or
updated it, so two first ratings both inserted (the second failed the
unique (user, revision) constraint: a 500) and an update racing a removal
updated a row that no longer existed (StaleDataError: a 500). Every request
here is held after its permission check until all of them got there, then
released together through the real HTTP app. The answers must be the ones
some serial order of the same requests gives, never a 500.
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import func, select

import app.routers.ratings as ratings_router
from app.models.assertion_rating import AssertionRating
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload

WAIT = 30


def _release_together(monkeypatch, parties: int) -> None:
    """The first `parties` permission checks wait for each other; later
    requests (the reads after the race) pass straight through."""
    original = ratings_router._require_permission
    barrier = threading.Barrier(parties)
    calls = []
    lock = threading.Lock()

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        with lock:
            calls.append(None)
            racing = len(calls) <= parties
        if racing:
            barrier.wait(timeout=WAIT)
        return result

    monkeypatch.setattr(ratings_router, "_require_permission", wrapper)


def _all_at_once(*calls) -> list:
    results: list = [None] * len(calls)
    errors: list[BaseException] = []

    def run(index: int) -> None:
        try:
            results[index] = calls[index]()
        except BaseException as exc:  # a 500 surfaces here through TestClient
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(calls))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=WAIT)
    assert not errors, errors
    return results


@pytest.fixture()
def rated_path(client, matter_with_users) -> str:
    m = matter_with_users
    created = client.post("/api/v1/assertions", headers=m["contributor_headers"], json=assertion_payload(
        m["matter_id"], m["repository_id"], save_as="proposed"))
    assert created.status_code == 201, created.text
    return f"/api/v1/assertions/{created.json()['id']}/revisions/1/rating"


def _ratings(db_session) -> list[tuple]:
    db_session.expire_all()
    return [tuple(row) for row in db_session.execute(
        select(AssertionRating.user_id, AssertionRating.strength)).all()]


def _rating_events(db_session) -> list[str]:
    db_session.expire_all()
    return list(db_session.scalars(
        select(AuditEvent.event_type).where(AuditEvent.event_type.like("rating_%")).order_by(AuditEvent.timestamp)))


def test_simultaneous_first_ratings_store_one_and_answer_as_in_sequence(
        client, db_session, matter_with_users, rated_path, monkeypatch):
    m = matter_with_users
    parallel = 4
    _release_together(monkeypatch, parallel)

    responses = _all_at_once(*[
        (lambda: client.put(rated_path, json={"strength": 4}, headers=m["reviewer_headers"]))
        for _ in range(parallel)])

    assert sorted(r.status_code for r in responses) == [200] * (parallel - 1) + [201], [r.text for r in responses]
    assert len({r.json()["id"] for r in responses}) == 1
    assert _ratings(db_session) == [(m["reviewer_id"], 4)]
    assert _rating_events(db_session) == ["rating_created"] + ["rating_changed"] * (parallel - 1)


@pytest.mark.parametrize("round_", range(4))
def test_a_rating_update_racing_its_removal_never_fails(client, db_session, matter_with_users, rated_path,
                                                        monkeypatch, round_):
    m = matter_with_users
    assert client.put(rated_path, json={"strength": 2}, headers=m["reviewer_headers"]).status_code == 201
    _release_together(monkeypatch, 2)

    put, delete = _all_at_once(
        lambda: client.put(rated_path, json={"strength": 5}, headers=m["reviewer_headers"]),
        lambda: client.delete(rated_path, headers=m["reviewer_headers"]),
    )

    assert delete.status_code == 204, delete.text
    assert put.status_code in (200, 201), put.text
    if put.status_code == 200:  # updated, then removed
        assert _ratings(db_session) == []
        assert _rating_events(db_session) == ["rating_created", "rating_changed", "rating_removed"]
    else:  # removed, then rated afresh
        assert _ratings(db_session) == [(m["reviewer_id"], 5)]
        assert _rating_events(db_session) == ["rating_created", "rating_removed", "rating_created"]


def test_simultaneous_removals_remove_once(client, db_session, matter_with_users, rated_path, monkeypatch):
    m = matter_with_users
    assert client.put(rated_path, json={"strength": 3}, headers=m["reviewer_headers"]).status_code == 201
    _release_together(monkeypatch, 2)

    responses = _all_at_once(*[(lambda: client.delete(rated_path, headers=m["reviewer_headers"]))
                               for _ in range(2)])

    assert sorted(r.status_code for r in responses) == [204, 404], [r.text for r in responses]
    assert _ratings(db_session) == []
    assert db_session.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event_type == "rating_removed")) == 1
