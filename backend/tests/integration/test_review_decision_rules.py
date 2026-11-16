"""Review-decision rules (`app/routers/review.py`), driven through the real API.

Pins the 2026-11-16 review-workflow fix package (spec addendum "Review
decision rules"):

- ui:35 -- every review route returns the full assertion, like the other
  assertion mutation routes.
- new:review-audit-correlation-id -- decision audit rows carry a
  correlation id (spec §16, gate G8), shared by every row one request
  writes.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.models.assertion_comment import AssertionComment
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload, seed_document, seed_source_span

# action -> resulting status
DECISIONS = {
    "accept": "accepted",
    "reject": "rejected",
    "dispute": "disputed",
    "request-revision": "revision_requested",
}
# action -> the author notification the decision raises on success
NOTIFICATION_KIND = {
    "accept": "assertion_accepted",
    "reject": "assertion_rejected",
    "dispute": "assertion_disputed",
    "request-revision": "revision_requested",
}
# action -> audit event_type written by review.py
EVENT_TYPE = {
    "accept": "assertion.accept",
    "reject": "assertion.reject",
    "dispute": "assertion.dispute",
    "request-revision": "assertion.request_revision",
    "supersede": "assertion.supersede",
}
DETAIL_ONLY_KEYS = {"evidence", "ratings_summary", "comments", "revision_history"}


# --- helpers ------------------------------------------------------------------


def _span(db_session, m) -> str:
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    return seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])


def _create(client, m, *, save_as="proposed", evidence=(), headers=None) -> str:
    # No explanation: it would become an initial comment (+ comment_created
    # event) and blur the comment/audit assertions below.
    payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        save_as=save_as,
        proposition=f"Review-rule probe proposition {uuid.uuid4()}.",
        evidence=list(evidence),
        explanation=None,
    )
    r = client.post("/api/v1/assertions", json=payload, headers=headers or m["contributor_headers"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _supported(client, db_session, m, **kwargs) -> str:
    span = _span(db_session, m)
    return _create(
        client, m, evidence=[{"source_span_id": span, "evidence_role": "supports"}], **kwargs
    )


def _post(client, assertion_id, action, headers, body=None):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return client.post(f"/api/v1/assertions/{assertion_id}/{action}", **kwargs)


def _body_for(action, **extra) -> dict:
    body = dict(extra)
    if action == "request-revision":
        body.setdefault("comment", "Please cite the governing clause.")
    return body


def _get(client, m, assertion_id) -> dict:
    r = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _row(db_session, assertion_id) -> dict:
    row = db_session.execute(
        text(
            "SELECT status, reviewed_by, current_revision_number, superseded_by_assertion_id "
            "FROM assertions WHERE id = :id"
        ),
        {"id": assertion_id},
    ).mappings().one()
    return dict(row)


def _decision_events(db_session, assertion_id) -> list[tuple]:
    return list(
        db_session.execute(
            select(
                AuditEvent.event_type,
                AuditEvent.previous_value,
                AuditEvent.new_value,
                AuditEvent.correlation_id,
            ).where(
                AuditEvent.assertion_id == assertion_id,
                AuditEvent.event_type.like("assertion.%"),
            )
        ).all()
    )


def _comment_rows(db_session, assertion_id) -> list[tuple]:
    return list(
        db_session.execute(
            select(AssertionComment.id, AssertionComment.comment_text, AssertionComment.comment_text_raw)
            .where(AssertionComment.assertion_id == assertion_id)
        ).all()
    )


def _author_notifications(client, m, assertion_id) -> list[str]:
    r = client.get("/api/v1/notifications", headers=m["contributor_headers"])
    assert r.status_code == 200
    return [
        n["event_type"] for n in r.json() if n["payload"].get("assertion_id") == assertion_id
    ]


def _history_event(client, m, assertion_id, event_type) -> dict:
    r = client.get(f"/api/v1/assertions/{assertion_id}/history", headers=m["reviewer_headers"])
    assert r.status_code == 200
    matches = [e for e in r.json() if e["event_type"] == event_type]
    assert len(matches) == 1, r.json()
    return matches[0]


def _bump_revision(client, m, assertion_id, *, expected=1) -> None:
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={
            "proposition": f"Edited after the reviewer loaded it {uuid.uuid4()}.",
            "expected_revision_number": expected,
        },
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["current_revision_number"] == expected + 1


def _drive_to(client, db_session, m, status) -> str:
    """Create a supported assertion and move it to `status` through the API."""
    if status == "draft":
        return _supported(client, db_session, m, save_as="draft")
    assertion_id = _supported(client, db_session, m)
    if status == "proposed":
        return assertion_id
    if status == "withdrawn":
        r = client.post(f"/api/v1/assertions/{assertion_id}/withdraw", headers=m["contributor_headers"])
    elif status == "superseded":
        successor = _supported(client, db_session, m)
        r = _post(
            client, assertion_id, "supersede", m["reviewer_headers"],
            {"superseded_by_assertion_id": successor},
        )
    else:
        action = {v: k for k, v in DECISIONS.items()}[status]
        r = _post(client, assertion_id, action, m["reviewer_headers"], _body_for(action))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == status
    return assertion_id


# --- ui:35: response shape ------------------------------------------------------


@pytest.mark.parametrize("action", list(DECISIONS) + ["supersede"])
def test_review_routes_return_the_full_assertion(client, matter_with_users, db_session, action):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    body = _body_for(action)
    if action == "supersede":
        body["superseded_by_assertion_id"] = _supported(client, db_session, m)

    r = _post(client, assertion_id, action, m["reviewer_headers"], body)

    assert r.status_code == 200, r.text
    detail = _get(client, m, assertion_id)
    expected = {k: v for k, v in detail.items() if k not in DETAIL_ONLY_KEYS}
    assert r.json() == expected


# --- new:review-audit-correlation-id -------------------------------------------


@pytest.mark.parametrize("action", list(DECISIONS) + ["supersede"])
def test_decision_audit_rows_carry_a_correlation_id(client, matter_with_users, db_session, action):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    body = _body_for(action)
    if action == "supersede":
        body["superseded_by_assertion_id"] = _supported(client, db_session, m)
    assert _post(client, assertion_id, action, m["reviewer_headers"], body).status_code == 200
    events = _decision_events(db_session, assertion_id)
    assert len(events) == 1
    assert events[0][3], "spec §16: audit rows carry a request/correlation id"
