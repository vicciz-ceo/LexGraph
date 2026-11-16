"""Status transitions that race other writers (reviews authoring:1,
persistence:1, workflow:1, authoring:2, workflow:2, workflow:0, workflow:3).

A transition checks the row it read and then writes it. Each test here holds
one request right after its unlocked checks -- the point where it used to be
too late to notice anything -- lets the competing request run to completion
through the real HTTP app, and then releases the first. Whatever the order,
the outcome must be one that some serial order of the two requests gives:
a decision the API confirmed is never overwritten, an accepted assertion is
never left without the support or justification its acceptance required,
supersede links never form a cycle, and one submission notifies once.
"""

from __future__ import annotations

import threading
import uuid

import pytest
from sqlalchemy import select, text

import app.notification_hooks as notification_hooks
import app.routers.assertions as assertions_router
import app.routers.review as review_router
from app.models.audit_event import AuditEvent
from tests.conftest import (
    assertion_payload,
    auth_header,
    seed_document,
    seed_matter_role,
    seed_source_span,
    seed_user,
)

WAIT = 30  # seconds; generous, a test only waits this long when it fails


class _Request(threading.Thread):
    """One API call on its own thread, like a second browser tab or client."""

    def __init__(self, call):
        super().__init__(daemon=True)
        self._call = call
        self.response = None
        self.error: BaseException | None = None
        self.start()

    def run(self) -> None:
        try:
            self.response = self._call()
        except BaseException as exc:  # reported by result(), never swallowed
            self.error = exc

    def result(self):
        self.join(timeout=WAIT)
        assert not self.is_alive(), "request did not finish"
        if self.error is not None:
            raise self.error
        return self.response


def _hold_first_call(monkeypatch, module, name: str, *, when=lambda *args, **kwargs: True):
    """Make the first call of `module.<name>` that satisfies `when` run, then
    wait until released. Returns (reached, release) events."""
    original = getattr(module, name)
    reached, release = threading.Event(), threading.Event()
    held = []

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        if not held and when(*args, **kwargs):
            held.append(True)
            reached.set()
            assert release.wait(timeout=WAIT)
        return result

    monkeypatch.setattr(module, name, wrapper)
    return reached, release


def _barrier_on_first_call(monkeypatch, module, name: str, parties: int, *, key):
    """Make every request wait at one barrier after its first call of
    `module.<name>`; later calls by the same request (keyed by `key(args)`)
    pass straight through."""
    original = getattr(module, name)
    barrier = threading.Barrier(parties)
    seen: set = set()
    lock = threading.Lock()

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        with lock:
            first = key(*args, **kwargs) not in seen
            seen.add(key(*args, **kwargs))
        if first:
            barrier.wait(timeout=WAIT)
        return result

    monkeypatch.setattr(module, name, wrapper)


@pytest.fixture()
def admin(db_session, matter_with_users) -> dict:
    """A second reviewer (an admin) for decisions that race a reviewer's."""
    admin_id = seed_user(db_session, display_name="Admin")
    seed_matter_role(db_session, user_id=admin_id, matter_id=matter_with_users["matter_id"], role="admin")
    return {"id": admin_id, "headers": auth_header(admin_id)}


def _span(db_session, m) -> str:
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    return seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"])


def _create(client, db_session, m, *, save_as="proposed", supported=True) -> dict:
    evidence = [{"source_span_id": _span(db_session, m), "evidence_role": "supports"}] if supported else []
    r = client.post("/api/v1/assertions", headers=m["contributor_headers"], json=assertion_payload(
        m["matter_id"], m["repository_id"], save_as=save_as, evidence=evidence, explanation=None,
        proposition=f"Race probe proposition {uuid.uuid4()}."))
    assert r.status_code == 201, r.text
    return r.json()


def _row(db_session, assertion_id) -> dict:
    db_session.expire_all()
    return dict(db_session.execute(text(
        "SELECT status, reviewed_by, reviewed_at, superseded_by_assertion_id FROM assertions WHERE id = :id"
    ), {"id": assertion_id}).mappings().one())


def _events(db_session, assertion_id, *event_types) -> list[tuple]:
    db_session.expire_all()
    return [tuple(row) for row in db_session.execute(
        select(AuditEvent.event_type, AuditEvent.previous_value, AuditEvent.new_value)
        .where(AuditEvent.assertion_id == assertion_id, AuditEvent.event_type.in_(event_types))
        .order_by(AuditEvent.timestamp)
    ).all()]


def _notices(client, headers, assertion_id, event_type) -> list[dict]:
    r = client.get("/api/v1/notifications", params={"limit": 200}, headers=headers)
    assert r.status_code == 200, r.text
    return [n for n in r.json() if n["event_type"] == event_type and n["assertion_id"] == assertion_id]


def _post(client, assertion_id, action, headers, body=None):
    return client.post(f"/api/v1/assertions/{assertion_id}/{action}", headers=headers,
                       **({"json": body} if body is not None else {}))


def _held_author_request(monkeypatch, m):
    """Hold the author's request after its first (unlocked) permission check."""
    return _hold_first_call(monkeypatch, assertions_router, "_require_can_modify",
                            when=lambda session, user_id, assertion: user_id == m["contributor_id"])


# --- withdraw and resubmit never overwrite a decision (authoring:1, persistence:1, workflow:1)


def test_a_withdraw_held_while_a_reviewer_accepts_is_refused(client, db_session, matter_with_users,
                                                             monkeypatch):
    m = matter_with_users
    a = _create(client, db_session, m)
    reached, release = _held_author_request(monkeypatch, m)

    withdraw = _Request(lambda: _post(client, a["id"], "withdraw", m["contributor_headers"]))
    assert reached.wait(timeout=WAIT)
    accept = _post(client, a["id"], "accept", m["reviewer_headers"], {"expected_revision_number": 1})
    release.set()

    assert (accept.status_code, accept.json()["status"]) == (200, "accepted"), accept.text
    refused = withdraw.result()
    assert refused.status_code == 403, refused.text  # the author may not withdraw a reviewed assertion
    row = _row(db_session, a["id"])
    assert (row["status"], row["reviewed_by"]) == ("accepted", m["reviewer_id"])
    assert _events(db_session, a["id"], "assertion_withdrawn") == []


def test_a_reviewer_s_withdraw_held_while_another_reviewer_accepts_is_refused(
        client, db_session, matter_with_users, admin, monkeypatch):
    m = matter_with_users
    a = _create(client, db_session, m)
    reached, release = _hold_first_call(monkeypatch, assertions_router, "_require_can_modify",
                                        when=lambda session, user_id, assertion: user_id == admin["id"])

    withdraw = _Request(lambda: _post(client, a["id"], "withdraw", admin["headers"]))
    assert reached.wait(timeout=WAIT)
    assert _post(client, a["id"], "accept", m["reviewer_headers"]).status_code == 200
    release.set()

    refused = withdraw.result()
    assert (refused.status_code, refused.json()["detail"]) == (
        409, "Only an unreviewed assertion can be withdrawn"), refused.text
    assert _row(db_session, a["id"])["status"] == "accepted"
    assert _events(db_session, a["id"], "assertion_withdrawn") == []


def test_a_resubmit_held_while_a_reviewer_rejects_is_refused(client, db_session, matter_with_users,
                                                             monkeypatch):
    m = matter_with_users
    a = _create(client, db_session, m)
    assert _post(client, a["id"], "request-revision", m["reviewer_headers"],
                 {"comment": "Cite the clause."}).status_code == 200
    submitted_before = [n["id"] for n in _notices(client, m["reviewer_headers"], a["id"], "assertion_submitted")]
    reached, release = _held_author_request(monkeypatch, m)

    resubmit = _Request(lambda: _post(client, a["id"], "submit", m["contributor_headers"]))
    assert reached.wait(timeout=WAIT)
    reject = _post(client, a["id"], "reject", m["reviewer_headers"], {"expected_revision_number": 1})
    release.set()

    assert (reject.status_code, reject.json()["status"]) == (200, "rejected"), reject.text
    refused = resubmit.result()
    assert refused.status_code == 403, refused.text
    row = _row(db_session, a["id"])
    assert (row["status"], row["reviewed_by"]) == ("rejected", m["reviewer_id"])
    assert row["reviewed_at"] is not None
    assert _events(db_session, a["id"], "assertion_submitted") == []
    assert [n["id"] for n in _notices(client, m["reviewer_headers"], a["id"], "assertion_submitted")] == (
        submitted_before)


def test_an_accept_held_while_the_author_withdraws_is_refused(client, db_session, matter_with_users,
                                                              monkeypatch):
    """The reverse order: the decision is the one that must give way."""
    m = matter_with_users
    a = _create(client, db_session, m)
    reached, release = _hold_first_call(monkeypatch, review_router, "_require_decidable")

    accept = _Request(lambda: _post(client, a["id"], "accept", m["reviewer_headers"]))
    assert reached.wait(timeout=WAIT)
    withdrawn = _post(client, a["id"], "withdraw", m["contributor_headers"])
    release.set()

    assert withdrawn.status_code == 200, withdrawn.text
    assert accept.result().status_code == 409
    assert _row(db_session, a["id"])["status"] == "withdrawn"
    assert _events(db_session, a["id"], "assertion.accept") == []


# --- accept versus removing the last supporting evidence (authoring:2, workflow:2) ---------


@pytest.mark.parametrize(("remover", "refusal"), [("author", 403), ("admin", 409)])
def test_removing_the_last_support_while_an_accept_reads_it_cannot_leave_it_unsupported(
        client, db_session, matter_with_users, admin, monkeypatch, remover, refusal):
    m = matter_with_users
    a = _create(client, db_session, m)
    (evidence,) = client.get(f"/api/v1/assertions/{a['id']}/evidence", headers=m["reviewer_headers"]).json()
    reached, release = _hold_first_call(monkeypatch, review_router, "_evidence_status")
    headers = m["contributor_headers"] if remover == "author" else admin["headers"]

    accept = _Request(lambda: _post(client, a["id"], "accept", m["reviewer_headers"]))
    assert reached.wait(timeout=WAIT)  # the accept has read 'evidenced'
    removal = _Request(lambda: client.delete(
        f"/api/v1/assertions/{a['id']}/evidence/{evidence['id']}", headers=headers))
    removal.join(timeout=1.0)  # a removal the accept does not exclude completes by now
    release.set()

    accepted = accept.result()
    assert (accepted.status_code, accepted.json()["evidence_status"]) == (200, "evidenced"), accepted.text
    refused = removal.result()
    assert refused.status_code == refusal, refused.text
    detail = client.get(f"/api/v1/assertions/{a['id']}", headers=m["reviewer_headers"]).json()
    assert (detail["status"], detail["evidence_status"]) == ("accepted", "evidenced")
    assert [e["id"] for e in detail["evidence"]] == [evidence["id"]]
    assert _events(db_session, a["id"], "evidence_removed") == []


def test_an_accept_after_the_last_support_was_removed_still_needs_a_justification(
        client, db_session, matter_with_users):
    m = matter_with_users
    a = _create(client, db_session, m)
    (evidence,) = client.get(f"/api/v1/assertions/{a['id']}/evidence", headers=m["reviewer_headers"]).json()
    assert client.delete(f"/api/v1/assertions/{a['id']}/evidence/{evidence['id']}",
                         headers=m["contributor_headers"]).status_code == 204

    assert _post(client, a["id"], "accept", m["reviewer_headers"]).status_code == 422
    assert _row(db_session, a["id"])["status"] == "proposed"


# --- crossing supersedes (workflow:0) ---------------------------------------------------------


def test_crossing_supersedes_cannot_close_a_cycle(client, db_session, matter_with_users, admin,
                                                 monkeypatch):
    m = matter_with_users
    first, second = _create(client, db_session, m), _create(client, db_session, m)
    _barrier_on_first_call(monkeypatch, review_router, "_validated_successor", 2,
                           key=lambda db, assertion, successor_id: assertion.id)

    requests = [
        _Request(lambda: _post(client, first["id"], "supersede", m["reviewer_headers"],
                               {"superseded_by_assertion_id": second["id"], "expected_revision_number": 1})),
        _Request(lambda: _post(client, second["id"], "supersede", admin["headers"],
                               {"superseded_by_assertion_id": first["id"], "expected_revision_number": 1})),
    ]
    responses = [request.result() for request in requests]

    assert sorted(r.status_code for r in responses) == [200, 422], [r.text for r in responses]
    winner = next(r.json() for r in responses if r.status_code == 200)
    loser = next(r for r in responses if r.status_code == 422)
    assert "superseded" in loser.json()["detail"]
    successor_id = winner["superseded_by_assertion_id"]
    assert _row(db_session, winner["id"])["status"] == "superseded"
    assert _row(db_session, successor_id) | {"reviewed_at": None} == {
        "status": "proposed", "reviewed_by": None, "reviewed_at": None, "superseded_by_assertion_id": None}
    assert [len(_events(db_session, a["id"], "assertion.supersede")) for a in (first, second)] in ([1, 0], [0, 1])


def test_a_supersede_held_while_its_successor_is_withdrawn_is_refused(client, db_session, matter_with_users,
                                                                     monkeypatch):
    """The successor is checked again on what is committed under the lock: one
    withdrawn meanwhile is refused as it is in sequence, never linked to."""
    m = matter_with_users
    superseded, successor = _create(client, db_session, m), _create(client, db_session, m)
    reached, release = _hold_first_call(monkeypatch, review_router, "_validated_successor")

    supersede = _Request(lambda: _post(client, superseded["id"], "supersede", m["reviewer_headers"],
                                       {"superseded_by_assertion_id": successor["id"]}))
    assert reached.wait(timeout=WAIT)
    assert _post(client, successor["id"], "withdraw", m["contributor_headers"]).status_code == 200
    release.set()

    refused = supersede.result()
    assert refused.status_code == 422, refused.text
    assert "withdrawn" in refused.json()["detail"]
    assert _row(db_session, superseded["id"]) == {
        "status": "proposed", "reviewed_by": None, "reviewed_at": None, "superseded_by_assertion_id": None}


# --- one submission, one transition, one notice (workflow:3) ----------------------------------


def _submitted_notices(client, m, assertion_id) -> list[dict]:
    return _notices(client, m["reviewer_headers"], assertion_id, "assertion_submitted")


def test_a_second_submit_whose_snapshot_predates_the_first_notifies_nobody(
        client, db_session, matter_with_users, monkeypatch):
    """The notification hook reads the assertion before the request runs. A
    second submit that read 'draft' before the first one committed used to
    notify every reviewer again, its notice claiming the move from draft."""
    m = matter_with_users
    draft = _create(client, db_session, m, save_as="draft")
    stale = notification_hooks._snapshot(client.app.state.session_factory, draft["id"])
    assert stale.status == "draft"

    first = _post(client, draft["id"], "submit", m["contributor_headers"])
    assert first.status_code == 200, first.text
    monkeypatch.setattr(notification_hooks, "_snapshot", lambda session_factory, assertion_id: stale)
    again = _post(client, draft["id"], "submit", m["contributor_headers"])
    assert again.status_code == 200, again.text

    notices = _submitted_notices(client, m, draft["id"])
    assert [n["payload"]["previous_status"] for n in notices] == ["draft"]
    assert _events(db_session, draft["id"], "assertion_submitted") == [
        ("assertion_submitted", "draft", "proposed"), ("assertion_submitted", "proposed", "proposed")]


def test_simultaneous_submits_move_a_draft_into_review_once(client, db_session, matter_with_users,
                                                           monkeypatch):
    m = matter_with_users
    draft = _create(client, db_session, m, save_as="draft")
    _barrier_on_first_call(monkeypatch, notification_hooks, "_snapshot", 2,
                           key=lambda *args: threading.get_ident())

    requests = [_Request(lambda: _post(client, draft["id"], "submit", m["contributor_headers"]))
                for _ in range(2)]

    assert [r.result().status_code for r in requests] == [200, 200]
    assert _events(db_session, draft["id"], "assertion_submitted") == [
        ("assertion_submitted", "draft", "proposed"), ("assertion_submitted", "proposed", "proposed")]
    assert [n["payload"]["previous_status"] for n in _submitted_notices(client, m, draft["id"])] == ["draft"]


def test_simultaneous_resubmits_return_an_assertion_to_review_once(client, db_session, matter_with_users,
                                                                  monkeypatch):
    m = matter_with_users
    a = _create(client, db_session, m)
    assert _post(client, a["id"], "request-revision", m["reviewer_headers"],
                 {"comment": "Cite the clause."}).status_code == 200
    _barrier_on_first_call(monkeypatch, assertions_router, "_require_can_modify", 2,
                           key=lambda *args: threading.get_ident())

    requests = [_Request(lambda: _post(client, a["id"], "submit", m["contributor_headers"]))
                for _ in range(2)]

    assert [r.result().status_code for r in requests] == [200, 200]
    assert _events(db_session, a["id"], "assertion_submitted") == [
        ("assertion_submitted", "revision_requested", "proposed"),
        ("assertion_submitted", "proposed", "proposed")]
    resubmitted = [n for n in _submitted_notices(client, m, a["id"])
                   if n["payload"]["previous_status"] == "revision_requested"]
    assert len(resubmitted) == 1
