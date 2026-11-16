"""Audit trail completeness (spec section 16; audit findings api:4, api:5,
review:2, pipeline:5).

Spec section 16 lists the actions that must be audited (among them
"Assertion submitted", "Assertion withdrawn", "Evidence added or removed",
"Rating created/changed", "Comment created, edited, or deleted", "Status
changed") and the fields every audit record carries (actor, timestamp,
repository, matter, assertion, assertion revision, previous/new value where
appropriate, request or correlation ID). Section 13: every mutation API
produces audit events.

These tests drive the real app through its HTTP API (and the agent CLI and
MCP server for the non-HTTP creation paths) and read the trail back through
`GET /api/v1/assertions/{id}/history`, the way the assertion detail page
does.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text

from app.models.assertion_rating import AssertionRating
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload, seed_document, seed_source_span

BACKEND = Path(__file__).resolve().parents[2]


# --- helpers -------------------------------------------------------------------


def _url(assertion_id: str, suffix: str = "") -> str:
    return f"/api/v1/assertions/{assertion_id}{suffix}"


def _spans(db_session, m: dict, *quotes: str) -> list[str]:
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    return [
        seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"], quote_text=quote)
        for quote in quotes
    ]


def _create(client, m: dict, *, headers=None, **overrides) -> dict:
    overrides.setdefault("proposition", f"Clause 8.4 qualifies Clause 8.2 ({uuid.uuid4()}).")
    overrides.setdefault("explanation", None)
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=headers or m["contributor_headers"],
    )
    assert r.status_code == 201, r.text
    return r.json()


def _history(client, m: dict, assertion_id: str) -> list[dict]:
    r = client.get(_url(assertion_id, "/history"), headers=m["reviewer_headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _of_type(history: list[dict], event_type: str) -> list[dict]:
    return [e for e in history if e["event_type"] == event_type]


def _summary(e: dict) -> tuple:
    return (e["actor_user_id"], e["assertion_revision_number"], e["previous_value"], e["new_value"])


@contextmanager
def _audit_insert_fails(event_type: str):
    """Make the INSERT of any audit row of `event_type` raise, so a test
    can prove the row is written in the same transaction as its mutation
    (spec section 16: a mutation must never commit without its audit row)."""

    def _refuse(_mapper, _connection, target):
        if target.event_type == event_type:
            raise RuntimeError(f"injected failure writing {event_type}")

    event.listen(AuditEvent, "before_insert", _refuse)
    try:
        yield
    finally:
        event.remove(AuditEvent, "before_insert", _refuse)


# --- api:4 / pipeline:5 / review:2: submit and withdraw --------------------------


def test_submit_is_audited_with_previous_status_revision_and_actor(client, matter_with_users):
    m = matter_with_users
    a = _create(client, m)
    r = client.post(_url(a["id"], "/submit"), headers=m["contributor_headers"])
    assert r.status_code == 200, r.text
    # Submitting again is allowed (it refreshes submitted_at) and is audited too.
    again = client.post(_url(a["id"], "/submit"), headers=m["contributor_headers"])
    assert again.status_code == 200, again.text

    submitted = _of_type(_history(client, m, a["id"]), "assertion_submitted")
    assert [_summary(e) for e in submitted] == [
        (m["contributor_id"], 1, "draft", "proposed"),
        (m["contributor_id"], 1, "proposed", "proposed"),
    ]
    assert [e["correlation_id"] for e in submitted] == [r.headers["x-request-id"], again.headers["x-request-id"]]


def test_resubmitting_after_a_revision_request_is_audited(client, db_session, matter_with_users):
    m = matter_with_users
    (span,) = _spans(db_session, m, "Clause 8.4 applies except where prohibited by law.")
    a = _create(client, m, evidence=[{"source_span_id": span, "evidence_role": "supports"}])
    assert client.post(_url(a["id"], "/submit"), headers=m["contributor_headers"]).status_code == 200
    assert client.post(
        _url(a["id"], "/request-revision"), json={"comment": "Cite 8.2 too."},
        headers=m["reviewer_headers"],
    ).status_code == 200
    edited = client.patch(
        _url(a["id"]), json={"proposition": f"Clause 8.4 qualifies 8.2 ({uuid.uuid4()}).",
                             "expected_revision_number": 1},
        headers=m["contributor_headers"],
    )
    assert edited.status_code == 200, edited.text
    assert client.post(_url(a["id"], "/submit"), headers=m["contributor_headers"]).status_code == 200

    submitted = _of_type(_history(client, m, a["id"]), "assertion_submitted")
    assert [_summary(e) for e in submitted] == [
        (m["contributor_id"], 1, "draft", "proposed"),
        (m["contributor_id"], 2, "revision_requested", "proposed"),
    ]


def test_withdraw_is_audited_with_the_withdrawing_user(client, matter_with_users):
    """A reviewer may withdraw another user's proposal; the trail must say who."""
    m = matter_with_users
    own_draft = _create(client, m)
    proposal = _create(client, m, save_as="proposed")

    assert client.post(_url(own_draft["id"], "/withdraw"), headers=m["contributor_headers"]).status_code == 200
    r = client.post(_url(proposal["id"], "/withdraw"), headers=m["reviewer_headers"])
    assert r.status_code == 200, r.text

    (by_author,) = _of_type(_history(client, m, own_draft["id"]), "assertion_withdrawn")
    assert _summary(by_author) == (m["contributor_id"], 1, "draft", "withdrawn")
    (by_reviewer,) = _of_type(_history(client, m, proposal["id"]), "assertion_withdrawn")
    assert _summary(by_reviewer) == (m["reviewer_id"], 1, "proposed", "withdrawn")
    assert by_reviewer["correlation_id"] == r.headers["x-request-id"]


def test_a_refused_submit_or_withdraw_writes_no_audit_row(client, matter_with_users):
    m = matter_with_users
    a = _create(client, m)
    assert client.post(_url(a["id"], "/withdraw"), headers=m["contributor_headers"]).status_code == 200
    before = _history(client, m, a["id"])
    # The author may no longer modify it (403); a reviewer may, but not from
    # 'withdrawn' (409); an outsider has no access (403).
    for action, headers, refused in (
        ("/submit", m["contributor_headers"], 403),
        ("/submit", m["reviewer_headers"], 409),
        ("/withdraw", m["reviewer_headers"], 409),
        ("/withdraw", m["outsider_headers"], 403),
    ):
        assert client.post(_url(a["id"], action), headers=headers).status_code == refused, action
    assert _history(client, m, a["id"]) == before


def test_submit_and_its_audit_row_commit_together(app, client, matter_with_users):
    m = matter_with_users
    a = _create(client, m)
    raw = TestClient(app, raise_server_exceptions=False)
    with _audit_insert_fails("assertion_submitted"):
        assert raw.post(_url(a["id"], "/submit"), headers=m["contributor_headers"]).status_code == 500
    assert client.get(_url(a["id"]), headers=m["contributor_headers"]).json()["status"] == "draft"


# --- api:4 / review:2: the accepted -> proposed reversal on edit -------------------


def test_editing_an_accepted_assertion_audits_the_status_change(client, db_session, matter_with_users):
    m = matter_with_users
    (span,) = _spans(db_session, m, "Clause 8.4 applies except where prohibited by law.")
    a = _create(client, m, save_as="proposed",
                evidence=[{"source_span_id": span, "evidence_role": "supports"}])
    assert client.post(_url(a["id"], "/accept"), headers=m["reviewer_headers"]).status_code == 200

    r = client.patch(_url(a["id"]), json={"proposition": f"Edited ({uuid.uuid4()}).",
                                           "expected_revision_number": 1},
                     headers=m["reviewer_headers"])
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["reviewed_by"]) == ("proposed", None)

    history = _history(client, m, a["id"])
    (changed,) = _of_type(history, "assertion_status_changed")
    assert _summary(changed) == (m["reviewer_id"], 2, "accepted", "proposed")
    (revised,) = _of_type(history, "assertion_revised")
    assert _summary(revised) == (m["reviewer_id"], 2, "1", "2")
    assert changed["correlation_id"] == revised["correlation_id"] == r.headers["x-request-id"]

    # An edit that does not change the status records no status change.
    again = client.patch(_url(a["id"]), json={"proposition": f"Edited again ({uuid.uuid4()})."},
                         headers=m["reviewer_headers"])
    assert again.status_code == 200, again.text
    assert len(_of_type(_history(client, m, a["id"]), "assertion_status_changed")) == 1


# --- review:2: evidence attached at creation (the only agent evidence path) ---------


def test_evidence_attached_at_creation_is_audited(client, db_session, matter_with_users):
    m = matter_with_users
    spans = _spans(db_session, m, "Clause 8.4 applies.", "Clause 8.2 requires notice.")
    r = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition=f"Inline evidence ({uuid.uuid4()}).",
        evidence=[{"source_span_id": spans[0], "evidence_role": "supports"},
                  {"source_span_id": spans[1], "evidence_role": "contextualizes"}],
    ), headers=m["contributor_headers"])
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    evidence_ids = {e["id"] for e in client.get(_url(aid, "/evidence"), headers=m["reviewer_headers"]).json()}

    history = _history(client, m, aid)
    added = _of_type(history, "evidence_added")
    assert {e["new_value"] for e in added} == evidence_ids and len(added) == 2
    assert {_summary(e)[:3] for e in added} == {(m["contributor_id"], 1, None)}
    # One request, one correlation id: creation, evidence and explanation rows.
    assert {e["correlation_id"] for e in history} == {r.headers["x-request-id"]}


def test_agent_creation_audits_its_evidence_under_one_correlation_id(client, db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                            quote_text="Confidentiality shall survive termination.")
    r = client.post("/api/v1/agent/assertions", json={
        "repository_id": m["repository_id"], "matter_id": m["matter_id"],
        "assertion_type": "SURVIVES_TERMINATION", "proposition": "Confidentiality survives (agent).",
        "subject_entity": {"type": "Document", "id": doc},
        "evidence": [{"source_span_id": span, "evidence_role": "primary_basis"}],
        "explanation": "The survival sentence.", "agent": {"platform": "pytest"},
    }, headers=m["contributor_headers"])
    assert r.status_code == 201, r.text
    history = _history(client, m, r.json()["id"])
    assert sorted(e["event_type"] for e in history) == [
        "assertion_agent_provenance", "assertion_created", "comment_created", "evidence_added",
    ]
    assert {e["correlation_id"] for e in history} == {r.headers["x-request-id"]}
    assert {e["assertion_revision_number"] for e in history} == {1}


def test_cli_and_mcp_creations_share_one_correlation_id_per_suggestion(
    app, client, db_session, matter_with_users
):
    """The agent CLI and MCP server create assertions without HTTP; each
    suggestion is one transaction and its audit rows share one id."""
    from app.mcp.server import create_server

    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                            quote_text="Confidentiality shall survive termination.")
    suggestion = {
        "repository_id": m["repository_id"], "matter_id": m["matter_id"],
        "assertion_type": "SURVIVES_TERMINATION", "proposition": "Confidentiality survives (CLI).",
        "subject_entity": {"type": "Document", "id": doc},
        "evidence": [{"source_span_id": span, "evidence_role": "primary_basis"}],
        "explanation": "The survival sentence.", "agent": {"platform": "pytest-cli"},
    }
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": str(app.state.engine.url),
           "LEXGRAPH_AGENT_USER_ID": m["contributor_id"]}
    done = subprocess.run([sys.executable, "-m", "app.agent_cli", "suggest"], input=json.dumps(suggestion),
                          capture_output=True, text=True, env=env, cwd=BACKEND)
    assert done.returncode == 0, done.stderr
    cli_id = json.loads(done.stdout)["id"]

    server = create_server(app.state.session_factory, agent_user_id=m["contributor_id"])
    payload = {**suggestion, "proposition": "Confidentiality survives (MCP).", "agent": {"platform": "pytest-mcp"}}
    result = asyncio.run(server.call_tool("suggest_assertion", {"payload": payload}))
    assert not getattr(result, "isError", False), result
    mcp_id = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]},
                        headers=m["reviewer_headers"]).json()["items"]
    mcp_id = next(a["id"] for a in mcp_id if a["id"] != cli_id)

    ids = []
    for aid in (cli_id, mcp_id):
        history = _history(client, m, aid)
        assert len(history) == 4 and len(_of_type(history, "evidence_added")) == 1
        (correlation_id,) = {e["correlation_id"] for e in history}
        assert correlation_id
        ids.append(correlation_id)
    assert ids[0] != ids[1]


# --- api:5 / review:2: evidence endpoints, in the mutation's own transaction ---------


def test_evidence_endpoint_events_carry_the_evidence_id_and_revision(client, db_session, matter_with_users):
    m = matter_with_users
    (span,) = _spans(db_session, m, "Clause 8.4 applies.")
    a = _create(client, m)
    client.patch(_url(a["id"]), json={"proposition": f"Second revision ({uuid.uuid4()})."},
                 headers=m["contributor_headers"])
    added = client.post(_url(a["id"], "/evidence"), json={"source_span_id": span, "evidence_role": "supports"},
                        headers=m["rater_headers"])
    assert added.status_code == 201, added.text
    evidence_id = added.json()["id"]
    removed = client.delete(_url(a["id"], f"/evidence/{evidence_id}"), headers=m["reviewer_headers"])
    assert removed.status_code == 204

    history = _history(client, m, a["id"])
    (add_event,) = _of_type(history, "evidence_added")
    (remove_event,) = _of_type(history, "evidence_removed")
    assert _summary(add_event) == (m["rater_id"], 2, None, evidence_id)
    assert _summary(remove_event) == (m["reviewer_id"], 2, None, evidence_id)
    assert add_event["correlation_id"] == added.headers["x-request-id"]
    assert remove_event["correlation_id"] == removed.headers["x-request-id"]


def test_evidence_mutations_and_their_audit_rows_commit_together(app, client, db_session, matter_with_users):
    m = matter_with_users
    (span,) = _spans(db_session, m, "Clause 8.4 applies.")
    a = _create(client, m)
    raw = TestClient(app, raise_server_exceptions=False)
    with _audit_insert_fails("evidence_added"):
        r = raw.post(_url(a["id"], "/evidence"), json={"source_span_id": span, "evidence_role": "supports"},
                     headers=m["contributor_headers"])
    assert r.status_code == 500
    assert client.get(_url(a["id"], "/evidence"), headers=m["contributor_headers"]).json() == []

    evidence_id = client.post(_url(a["id"], "/evidence"), headers=m["contributor_headers"],
                              json={"source_span_id": span, "evidence_role": "supports"}).json()["id"]
    with _audit_insert_fails("evidence_removed"):
        r = raw.delete(_url(a["id"], f"/evidence/{evidence_id}"), headers=m["contributor_headers"])
    assert r.status_code == 500
    remaining = client.get(_url(a["id"], "/evidence"), headers=m["contributor_headers"]).json()
    assert [e["id"] for e in remaining] == [evidence_id]


# --- api:5: rating events -------------------------------------------------------------


def test_rating_events_carry_the_rated_revision_and_the_previous_strength(client, matter_with_users):
    m = matter_with_users
    a = _create(client, m, save_as="proposed")
    rating = _url(a["id"], "/revisions/1/rating")
    first = client.put(rating, json={"strength": 4}, headers=m["rater_headers"])
    assert first.status_code == 201, first.text
    second = client.put(rating, json={"strength": 2, "rationale": "Weaker on reflection."},
                        headers=m["rater_headers"])
    assert second.status_code == 200, second.text
    # Revision 2 becomes current; a later rating of revision 1 still names revision 1.
    client.patch(_url(a["id"]), json={"proposition": f"Second revision ({uuid.uuid4()})."},
                 headers=m["reviewer_headers"])
    assert client.put(rating, json={"strength": 3}, headers=m["rater_headers"]).status_code == 200
    # Updating only the rationale is still an audited rating change.
    assert client.put(rating, json={"strength": 3, "rationale": "Same strength, new reason."},
                      headers=m["rater_headers"]).status_code == 200
    assert client.delete(rating, headers=m["rater_headers"]).status_code == 204

    history = _history(client, m, a["id"])
    assert [_summary(e) for e in _of_type(history, "rating_created")] == [(m["rater_id"], 1, None, "4")]
    assert [_summary(e) for e in _of_type(history, "rating_changed")] == [
        (m["rater_id"], 1, "4", "2"), (m["rater_id"], 1, "2", "3"), (m["rater_id"], 1, "3", "3"),
    ]
    assert [_summary(e) for e in _of_type(history, "rating_removed")] == [(m["rater_id"], 1, "3", None)]
    assert _of_type(history, "rating_created")[0]["correlation_id"] == first.headers["x-request-id"]
    assert _of_type(history, "rating_changed")[0]["correlation_id"] == second.headers["x-request-id"]


def test_a_rating_and_its_audit_row_commit_together(app, client, db_session, matter_with_users):
    """Formerly written by middleware in a second transaction after the
    response, with errors swallowed: the rating could commit unaudited."""
    m = matter_with_users
    a = _create(client, m, save_as="proposed")
    rating = _url(a["id"], "/revisions/1/rating")
    raw = TestClient(app, raise_server_exceptions=False)
    with _audit_insert_fails("rating_created"):
        assert raw.put(rating, json={"strength": 4}, headers=m["rater_headers"]).status_code == 500
    assert db_session.scalar(select(func.count()).select_from(AssertionRating)) == 0

    assert client.put(rating, json={"strength": 4}, headers=m["rater_headers"]).status_code == 201
    with _audit_insert_fails("rating_changed"):
        assert raw.put(rating, json={"strength": 1}, headers=m["rater_headers"]).status_code == 500
    db_session.expire_all()
    assert db_session.scalars(select(AssertionRating.strength)).all() == [4]


# --- api:5: comment events -------------------------------------------------------------


def test_comment_events_carry_the_comment_id_and_current_revision(client, matter_with_users):
    m = matter_with_users
    a = _create(client, m)
    created = client.post(_url(a["id"], "/comments"), json={"comment_text": "First reading."},
                          headers=m["rater_headers"])
    assert created.status_code == 201, created.text
    comment_id = created.json()["id"]
    client.patch(_url(a["id"]), json={"proposition": f"Second revision ({uuid.uuid4()})."},
                 headers=m["contributor_headers"])
    assert client.patch(_url(a["id"], f"/comments/{comment_id}"), json={"comment_text": "Second reading."},
                        headers=m["rater_headers"]).status_code == 200
    deleted = client.delete(_url(a["id"], f"/comments/{comment_id}"), headers=m["rater_headers"])
    assert deleted.status_code == 204

    history = _history(client, m, a["id"])
    assert [(e["event_type"],) + _summary(e) for e in history if e["event_type"].startswith("comment_")] == [
        ("comment_created", m["rater_id"], 1, None, comment_id),
        ("comment_updated", m["rater_id"], 2, None, comment_id),
        ("comment_deleted", m["rater_id"], 2, None, comment_id),
    ]
    assert _of_type(history, "comment_deleted")[0]["correlation_id"] == deleted.headers["x-request-id"]


def test_the_explanation_comment_of_a_creation_names_its_comment_and_revision(client, matter_with_users):
    m = matter_with_users
    r = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition=f"With explanation ({uuid.uuid4()})."),
        headers=m["contributor_headers"])
    assert r.status_code == 201, r.text
    (comment,) = client.get(_url(r.json()["id"], "/comments"), headers=m["contributor_headers"]).json()
    (created,) = _of_type(_history(client, m, r.json()["id"]), "comment_created")
    assert _summary(created) == (m["contributor_id"], 1, None, comment["id"])


# --- api:5: one correlation id per request -------------------------------------------


def test_every_request_gets_its_own_correlation_id(client):
    first = client.get("/healthz")
    second = client.get("/healthz")
    assert first.headers["x-request-id"] and second.headers["x-request-id"]
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    # Not taken from the client: an id supplied by the caller is not trusted.
    spoofed = client.get("/healthz", headers={"X-Request-ID": "chosen-by-client"})
    assert spoofed.headers["x-request-id"] != "chosen-by-client"


def test_review_decision_rows_carry_the_request_correlation_id(client, db_session, matter_with_users):
    m = matter_with_users
    (span,) = _spans(db_session, m, "Clause 8.4 applies.")
    a = _create(client, m, save_as="proposed",
                evidence=[{"source_span_id": span, "evidence_role": "supports"}])
    r = client.post(_url(a["id"], "/accept"), headers=m["reviewer_headers"])
    assert r.status_code == 200, r.text
    (accepted,) = _of_type(_history(client, m, a["id"]), "assertion.accept")
    assert accepted["correlation_id"] == r.headers["x-request-id"]


def test_no_audit_row_is_stored_without_a_correlation_id(app, matter_with_users):
    """A writer that builds an AuditEvent itself (outside record_audit_event)
    still gets a correlation id."""
    from datetime import datetime, timezone

    m = matter_with_users
    session = app.state.session_factory()
    try:
        session.add(AuditEvent(
            actor_user_id=m["reviewer_id"], event_type="probe", timestamp=datetime.now(timezone.utc),
            repository_id=m["repository_id"], matter_id=m["matter_id"],
        ))
        session.commit()
        assert session.execute(text(
            "SELECT COUNT(*) FROM audit_events WHERE correlation_id IS NULL"
        )).scalar_one() == 0
    finally:
        session.close()


# --- 83efb55: creation is audited exactly once on every HTTP path -------------------


def test_each_http_creation_path_writes_exactly_one_creation_event(client, db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    human = _create(client, m)
    agent = client.post("/api/v1/agent/assertions", json={
        "repository_id": m["repository_id"], "matter_id": m["matter_id"],
        "assertion_type": "SURVIVES_TERMINATION", "proposition": f"Agent ({uuid.uuid4()}).",
        "subject_entity": {"type": "Document", "id": doc}, "agent": {"platform": "pytest"},
    }, headers=m["contributor_headers"])
    assert agent.status_code == 201, agent.text
    for aid, status in ((human["id"], "draft"), (agent.json()["id"], "proposed")):
        created = _of_type(_history(client, m, aid), "assertion_created")
        assert [_summary(e) for e in created] == [(m["contributor_id"], 1, None, status)]


# --- app.services.audit: correlation and revision defaults ---------------------------


def test_outside_http_one_transaction_is_one_correlation_id(app, client, matter_with_users):
    """The id rule the agent CLI, the MCP server and offline pipelines rely
    on: rows recorded in one transaction share an id; the next transaction
    gets a new one; an explicit id wins. The revision defaults to the
    assertion's current one."""
    from app.services.audit import record_audit_event

    m = matter_with_users
    a = _create(client, m)
    (revision,) = client.get(_url(a["id"], "/revisions"), headers=m["reviewer_headers"]).json()
    common = dict(actor_user_id=m["reviewer_id"], repository_id=m["repository_id"],
                  matter_id=m["matter_id"], assertion_id=a["id"])
    session = app.state.session_factory()
    try:
        first = record_audit_event(session, event_type="probe_one", **common)
        second = record_audit_event(session, event_type="probe_two", **common)
        session.commit()
        third = record_audit_event(session, event_type="probe_three", **common)
        explicit = record_audit_event(session, event_type="probe_four", correlation_id="given", **common)
        session.commit()
    finally:
        session.close()
    assert first.correlation_id and first.correlation_id == second.correlation_id
    assert third.correlation_id and third.correlation_id != first.correlation_id
    assert explicit.correlation_id == "given"
    assert {e.assertion_revision_id for e in (first, second, third, explicit)} == {revision["id"]}


def test_new_correlation_id_is_the_bound_request_id():
    from app.services.audit import bind_request_correlation_id, new_correlation_id, request_correlation_id

    assert request_correlation_id() is None
    outside = {new_correlation_id(), new_correlation_id()}
    assert len(outside) == 2
    with bind_request_correlation_id() as bound:
        assert new_correlation_id() == request_correlation_id() == bound
        with bind_request_correlation_id("inner") as inner:
            assert (inner, new_correlation_id()) == ("inner", "inner")
        assert new_correlation_id() == bound
    assert request_correlation_id() is None


def test_an_event_about_a_pending_assertion_names_its_pending_revision(app, matter_with_users):
    """A writer may record before it flushes (autoflush is off in the app's
    sessions); the pending revision is found without flushing."""
    from datetime import datetime, timezone

    from app.models.assertion import Assertion
    from app.models.assertion_revision import AssertionRevision
    from app.services.audit import record_assertion_event

    m = matter_with_users
    now = datetime.now(timezone.utc)
    session = app.state.session_factory()
    try:
        assertion = Assertion(
            id=str(uuid.uuid4()), organization_id=m["organization_id"], repository_id=m["repository_id"],
            matter_id=m["matter_id"], assertion_type="CREATES_EXCEPTION_TO", proposition="Pending.",
            subject_entity_type="Provision", subject_entity_id=str(uuid.uuid4()), origin="imported",
            status="draft", author_user_id=m["contributor_id"], created_at=now, updated_at=now,
            current_revision_number=1,
        )
        revision = AssertionRevision(
            id=str(uuid.uuid4()), assertion_id=assertion.id, revision_number=1, proposition="Pending.",
            proposition_raw="Pending.", assertion_type="CREATES_EXCEPTION_TO", subject_entity_type="Provision",
            subject_entity_id=assertion.subject_entity_id, revision_reason="initial creation",
            edited_by_user_id=m["contributor_id"], created_at=now,
        )
        session.add_all([assertion, revision])
        row = record_assertion_event(session, assertion, actor_user_id=m["contributor_id"],
                                     event_type="probe_pending", new_value="draft")
        assert row.assertion_revision_id == revision.id
        session.commit()
        stored = session.execute(text(
            "SELECT assertion_revision_id, repository_id, matter_id FROM audit_events WHERE id = :id"
        ), {"id": row.id}).one()
        assert tuple(stored) == (revision.id, m["repository_id"], m["matter_id"])
    finally:
        session.close()
