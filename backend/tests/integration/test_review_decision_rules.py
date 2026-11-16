"""Review-decision rules (`app/routers/review.py`), driven through the real API.

Pins the 2026-11-16 review-workflow fix package (spec addendum "Review
decision rules"):

- ui:2  -- a decision may carry `expected_revision_number`; a stale value is
  refused with 409 before anything changes (spec §3 "review decisions must
  identify the assertion revision that was reviewed", §13 "use optimistic
  concurrency or revision checks / prevent lost updates"). Check order is
  404 -> 403 -> 409 -> 422, and the write itself is a conditional UPDATE so
  a change that lands between the checks and the write is also refused.
- api:6 / ui:9 -- decisions are only recorded from a reviewable status:
  never on an unsubmitted draft, a withdrawn assertion or a superseded one,
  and never as a same-status repeat (double-click). Re-review between
  reviewed statuses stays allowed.
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


# --- ui:2: decisions are tied to the revision the reviewer saw ---------------


@pytest.mark.parametrize("action", list(DECISIONS))
def test_stale_expected_revision_is_refused_and_changes_nothing(
    client, matter_with_users, db_session, action
):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    _bump_revision(client, m, assertion_id)  # author edits after the reviewer loaded rev 1

    r = _post(
        client, assertion_id, action, m["reviewer_headers"],
        _body_for(action, expected_revision_number=1),
    )

    assert r.status_code == 409, r.text
    assert "expected_revision_number" in r.json()["detail"]
    row = _row(db_session, assertion_id)
    assert row["status"] == "proposed"
    assert row["reviewed_by"] is None
    assert row["current_revision_number"] == 2
    assert _decision_events(db_session, assertion_id) == []
    assert _comment_rows(db_session, assertion_id) == [], "no request-revision comment left behind"
    assert NOTIFICATION_KIND[action] not in _author_notifications(client, m, assertion_id)


@pytest.mark.parametrize("action", list(DECISIONS))
def test_matching_expected_revision_records_the_reviewed_revision(
    client, matter_with_users, db_session, action
):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    _bump_revision(client, m, assertion_id)

    r = _post(
        client, assertion_id, action, m["reviewer_headers"],
        _body_for(action, expected_revision_number=2),
    )

    assert r.status_code == 200, r.text
    assert r.json()["status"] == DECISIONS[action]
    event = _history_event(client, m, assertion_id, EVENT_TYPE[action])
    assert event["assertion_revision_number"] == 2


def test_supersede_checks_expected_revision(client, matter_with_users, db_session):
    m = matter_with_users
    old_id = _supported(client, db_session, m)
    successor = _supported(client, db_session, m)
    _bump_revision(client, m, old_id)

    stale = _post(
        client, old_id, "supersede", m["reviewer_headers"],
        {"superseded_by_assertion_id": successor, "expected_revision_number": 1},
    )
    assert stale.status_code == 409, stale.text
    assert _row(db_session, old_id)["status"] == "proposed"
    assert _row(db_session, old_id)["superseded_by_assertion_id"] is None
    assert _decision_events(db_session, old_id) == []

    fresh = _post(
        client, old_id, "supersede", m["reviewer_headers"],
        {"superseded_by_assertion_id": successor, "expected_revision_number": 2},
    )
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()["status"] == "superseded"
    assert fresh.json()["superseded_by_assertion_id"] == successor


@pytest.mark.parametrize("action", list(DECISIONS))
def test_decision_without_a_body_is_still_accepted(client, matter_with_users, db_session, action):
    """expected_revision_number is optional, as on PATCH (seed, scripts, e2e)."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    r = _post(client, assertion_id, action, m["reviewer_headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == DECISIONS[action]


@pytest.mark.parametrize("action", list(DECISIONS) + ["supersede"])
def test_expected_revision_number_must_be_positive(client, matter_with_users, db_session, action):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    body = _body_for(action, expected_revision_number=0)
    if action == "supersede":
        body["superseded_by_assertion_id"] = _supported(client, db_session, m)
    r = _post(client, assertion_id, action, m["reviewer_headers"], body)
    assert r.status_code == 422, r.text
    assert _row(db_session, assertion_id)["status"] == "proposed"


def test_check_order_is_404_then_403_then_409_then_422(client, matter_with_users, db_session):
    m = matter_with_users
    stale = {"expected_revision_number": 1}

    missing = _post(client, str(uuid.uuid4()), "accept", m["reviewer_headers"], stale)
    assert missing.status_code == 404

    # Unsupported (no evidence), edited to rev 2: every check below would fail.
    assertion_id = _create(client, m)
    _bump_revision(client, m, assertion_id)
    assert _post(client, assertion_id, "accept", m["outsider_headers"], stale).status_code == 403
    assert _post(client, assertion_id, "accept", m["contributor_headers"], stale).status_code == 403
    # Stale revision outranks the missing justification.
    assert _post(client, assertion_id, "accept", m["reviewer_headers"], stale).status_code == 409
    # With a current view only the missing justification is left.
    current = _post(
        client, assertion_id, "accept", m["reviewer_headers"], {"expected_revision_number": 2}
    )
    assert current.status_code == 422
    assert _row(db_session, assertion_id)["status"] == "proposed"


def _interleave_after_load(monkeypatch, app, sql: str, params: dict) -> None:
    """Commit `sql` from a second connection right after the route has loaded
    the assertion -- i.e. a concurrent request that lands between this
    request's checks and its write."""
    from app.routers import review

    original = review._get_assertion_or_404

    def load_then_race(db, wanted_id):
        assertion = original(db, wanted_id)
        other = app.state.session_factory()
        try:
            other.execute(text(sql), params)
            other.commit()
        finally:
            other.close()
        return assertion

    monkeypatch.setattr(review, "_get_assertion_or_404", load_then_race)


def test_concurrent_decision_between_check_and_write_is_refused(
    client, app, matter_with_users, db_session, monkeypatch
):
    """Two reviewers (or a double-click): the second write must not land."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    _interleave_after_load(
        monkeypatch, app,
        "UPDATE assertions SET status = 'rejected', reviewed_by = :other WHERE id = :id",
        {"id": assertion_id, "other": m["rater_id"]},
    )

    r = _post(client, assertion_id, "accept", m["reviewer_headers"])

    assert r.status_code == 409, r.text
    row = _row(db_session, assertion_id)
    assert row["status"] == "rejected"
    assert row["reviewed_by"] == m["rater_id"]
    assert _decision_events(db_session, assertion_id) == []


def test_concurrent_edit_between_check_and_write_is_refused(
    client, app, matter_with_users, db_session, monkeypatch
):
    """An author's edit landing after the revision check must not be accepted unread."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    _interleave_after_load(
        monkeypatch, app,
        "UPDATE assertions SET current_revision_number = current_revision_number + 1 "
        "WHERE id = :id",
        {"id": assertion_id},
    )

    r = _post(
        client, assertion_id, "request-revision", m["reviewer_headers"],
        {"comment": "Cite the clause.", "expected_revision_number": 1},
    )

    assert r.status_code == 409, r.text
    assert _row(db_session, assertion_id)["status"] == "proposed"
    assert _decision_events(db_session, assertion_id) == []
    assert _comment_rows(db_session, assertion_id) == []


# --- api:6 / ui:9: status preconditions ---------------------------------------


@pytest.mark.parametrize("status", ["draft", "withdrawn", "superseded"])
@pytest.mark.parametrize("action", list(DECISIONS) + ["supersede"])
def test_no_decision_on_a_draft_withdrawn_or_superseded_assertion(
    client, matter_with_users, db_session, status, action
):
    m = matter_with_users
    assertion_id = _drive_to(client, db_session, m, status)
    before = _row(db_session, assertion_id)
    events_before = _decision_events(db_session, assertion_id)
    body = _body_for(action)
    if action == "accept":
        body["acceptance_justification"] = "Accepted on the reviewer's own reading."
    if action == "supersede":
        body["superseded_by_assertion_id"] = _supported(client, db_session, m)

    r = _post(client, assertion_id, action, m["reviewer_headers"], body)

    assert r.status_code == 409, r.text
    assert status in r.json()["detail"]
    assert _row(db_session, assertion_id) == before
    assert _decision_events(db_session, assertion_id) == events_before
    if action in NOTIFICATION_KIND:
        assert NOTIFICATION_KIND[action] not in _author_notifications(client, m, assertion_id)


def test_refused_decision_leaves_the_draft_with_its_author(client, matter_with_users, db_session):
    m = matter_with_users
    draft_id = _drive_to(client, db_session, m, "draft")
    assert _post(client, draft_id, "reject", m["reviewer_headers"]).status_code == 409

    submit = client.post(f"/api/v1/assertions/{draft_id}/submit", headers=m["contributor_headers"])
    assert submit.status_code == 200, submit.text
    assert submit.json()["status"] == "proposed"
    accept = _post(client, draft_id, "accept", m["reviewer_headers"])
    assert accept.status_code == 200, accept.text


@pytest.mark.parametrize("action", list(DECISIONS))
def test_repeating_the_same_decision_is_refused(client, matter_with_users, db_session, action):
    """A double-click must not record the decision (or notify) twice."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    first = _post(client, assertion_id, action, m["reviewer_headers"], _body_for(action))
    assert first.status_code == 200, first.text

    second = _post(client, assertion_id, action, m["reviewer_headers"], _body_for(action))

    assert second.status_code == 409, second.text
    assert "already" in second.json()["detail"]
    events = [e for e in _decision_events(db_session, assertion_id) if e[0] == EVENT_TYPE[action]]
    assert len(events) == 1
    assert _author_notifications(client, m, assertion_id).count(NOTIFICATION_KIND[action]) == 1
    if action == "request-revision":
        assert len(_comment_rows(db_session, assertion_id)) == 1


def test_reviewed_assertions_can_still_be_re_reviewed(client, matter_with_users, db_session):
    """Transitions between reviewed statuses stay open (contested rulings, re-review)."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    chain = ["request-revision", "accept", "dispute", "reject", "accept", "request-revision", "dispute"]
    for action in chain:
        r = _post(client, assertion_id, action, m["reviewer_headers"], _body_for(action))
        assert r.status_code == 200, (action, r.text)
        assert r.json()["status"] == DECISIONS[action]


def test_superseded_assertion_cannot_be_re_accepted(client, matter_with_users, db_session):
    m = matter_with_users
    old_id = _drive_to(client, db_session, m, "accepted")
    new_id = _drive_to(client, db_session, m, "accepted")
    r = _post(client, old_id, "supersede", m["reviewer_headers"], {"superseded_by_assertion_id": new_id})
    assert r.status_code == 200, r.text

    again = _post(client, old_id, "accept", m["reviewer_headers"])

    assert again.status_code == 409, again.text
    row = _row(db_session, old_id)
    assert row["status"] == "superseded"
    assert row["superseded_by_assertion_id"] == new_id
    graph = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["reviewer_headers"])
    edge_ids = {e["assertion_id"] for e in graph.json()["edges"]}
    assert old_id not in edge_ids
    assert new_id in edge_ids


def test_status_conflict_outranks_the_missing_justification(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create(client, m)  # unsupported
    r = client.post(f"/api/v1/assertions/{assertion_id}/withdraw", headers=m["contributor_headers"])
    assert r.status_code == 200
    assert _post(client, assertion_id, "accept", m["reviewer_headers"]).status_code == 409


def test_decision_clears_a_stale_superseded_by_link(client, matter_with_users, db_session):
    """Rows re-decided out of `superseded` before this fix kept their link; the
    next decision restores the invariant (link set only while superseded)."""
    m = matter_with_users
    stale_id = _drive_to(client, db_session, m, "accepted")
    other_id = _drive_to(client, db_session, m, "accepted")
    db_session.execute(
        text("UPDATE assertions SET superseded_by_assertion_id = :other WHERE id = :id"),
        {"other": other_id, "id": stale_id},
    )
    db_session.commit()

    r = _post(client, stale_id, "dispute", m["reviewer_headers"])

    assert r.status_code == 200, r.text
    assert r.json()["superseded_by_assertion_id"] is None
    assert _row(db_session, stale_id)["superseded_by_assertion_id"] is None


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
