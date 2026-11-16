"""Concurrent first-time preference writes both succeed (review workflow:4).

PUT /api/v1/notifications/preferences read the user's stored rows and then
inserted one for each event type that had none. Two overlapping first-time
PUTs for the same event type (a quick double toggle in the bell's settings)
both found no row and both inserted; the second insert violated the unique
(user_id, event_type) key and answered 500, so the user's last choice was
lost. The write is now one upsert per event type.

The race is made deterministic the way a busy server makes it likely:
another connection holds SQLite's write lock (as an assertion write, the
agent CLI or an enrichment batch does) while both requests arrive. Each
request reads "no stored choice" and then waits for the lock; once it is
released they write one after the other.
"""

from __future__ import annotations

import sqlite3
import threading
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.notification import NotificationPreference
from tests.conftest import auth_header, seed_user

URL = "/api/v1/notifications/preferences"


def _stored(db_session, user_id: str) -> dict[str, list[bool]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(NotificationPreference.event_type, NotificationPreference.enabled).where(
            NotificationPreference.user_id == user_id
        )
    ).all()
    stored: dict[str, list[bool]] = {}
    for event_type, enabled in rows:
        stored.setdefault(event_type, []).append(bool(enabled))
    return stored


def _race(app, user_id: str, bodies: list[dict]) -> list[int]:
    """Send `bodies` as overlapping PUTs while another connection holds the
    database's write lock; return their status codes in send order."""
    blocker = sqlite3.connect(app.state.engine.url.database, isolation_level=None)
    blocker.execute("BEGIN IMMEDIATE")  # the write lock: readers proceed, writers wait
    statuses: list[int | None] = [None] * len(bodies)
    clients = [TestClient(app, raise_server_exceptions=False) for _ in bodies]

    def put(index: int) -> None:
        response = clients[index].put(URL, json=bodies[index], headers=auth_header(user_id))
        statuses[index] = response.status_code

    threads = [threading.Thread(target=put, args=(index,)) for index in range(len(bodies))]
    try:
        for thread in threads:
            thread.start()
            time.sleep(0.25)  # each request has read the (empty) stored choices and waits to write
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    for thread in threads:
        thread.join(timeout=30)
    return statuses


@pytest.mark.parametrize("first,second", [(False, True), (True, False), (False, False)])
def test_overlapping_first_time_writes_of_one_event_both_succeed(app, client, db_session, first, second):
    user_id = seed_user(db_session)
    statuses = _race(app, user_id, [
        {"preferences": {"comment_added": first}},
        {"preferences": {"comment_added": second}},
    ])
    assert statuses == [200, 200]
    stored = _stored(db_session, user_id)
    assert len(stored["comment_added"]) == 1  # still one row per user and event type
    assert stored["comment_added"][0] in (first, second)  # whichever write committed last
    listed = {p["event_type"]: p["enabled"] for p in client.get(URL, headers=auth_header(user_id)).json()}
    assert listed["comment_added"] == stored["comment_added"][0]


def test_overlapping_first_time_writes_of_several_events_both_succeed(app, client, db_session):
    user_id = seed_user(db_session)
    statuses = _race(app, user_id, [
        {"preferences": {"comment_added": False, "assertion_rated": True, "evidence_added": False}},
        {"preferences": {"evidence_added": False, "comment_added": False, "revision_created": False}},
    ])
    assert statuses == [200, 200]
    assert _stored(db_session, user_id) == {
        "comment_added": [False], "assertion_rated": [True], "evidence_added": [False],
        "revision_created": [False],
    }


def test_the_later_sequential_write_wins_and_an_unchanged_one_keeps_its_time(client, db_session):
    user_id = seed_user(db_session)
    headers = auth_header(user_id)
    assert client.put(URL, json={"preferences": {"comment_added": False}}, headers=headers).status_code == 200
    assert client.put(URL, json={"preferences": {"comment_added": True}}, headers=headers).status_code == 200
    db_session.expire_all()
    row = db_session.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user_id)).one()
    assert row.enabled is True
    changed_at = row.updated_at
    assert client.put(URL, json={"preferences": {"comment_added": True}}, headers=headers).status_code == 200
    db_session.expire_all()
    row = db_session.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user_id)).one()
    assert (row.enabled, row.updated_at) == (True, changed_at)  # a write that changes nothing changes nothing
    # An unknown event type is still refused before anything is written.
    response = client.put(URL, json={"preferences": {"comment_added": False, "no_such_event": True}}, headers=headers)
    assert response.status_code == 422
    db_session.expire_all()
    assert db_session.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user_id)).one().enabled is True
