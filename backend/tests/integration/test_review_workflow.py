"""B4 — review workflow + server-side permissions.

Gate G5 (reviewer sees proposition/evidence/ratings/comments/history and
can accept/reject/dispute/request-revision; unsupported cannot be accepted
without recorded justification; decisions never erase ratings), G8
(permission-checked server-side, per role viewer/contributor/reviewer/
admin). DoD items 10-11, 15.

Owning track: B4. Routes: POST /api/v1/assertions/{id}/accept|reject|
dispute|request-revision|supersede.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def _create_submitted(client, m, **overrides):
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft", **overrides),
        headers=m["contributor_headers"],
    )
    assertion_id = r.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    return assertion_id


def test_reviewer_can_accept(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(
        client, m, evidence=[{"source_span_id": "seed-span", "evidence_role": "primary_basis"}]
    )
    r = client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_reviewer_can_reject(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    r = client.post(f"/api/v1/assertions/{assertion_id}/reject", headers=m["reviewer_headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_reviewer_can_dispute(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    r = client.post(f"/api/v1/assertions/{assertion_id}/dispute", headers=m["reviewer_headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "disputed"


def test_reviewer_can_request_revision(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/request-revision",
        json={"comment": "Please clarify jurisdiction."},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    assert r.json()["status"] == "revision_requested"


def test_contributor_cannot_accept(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    r = client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["contributor_headers"])
    assert r.status_code == 403


def test_unsupported_assertion_cannot_be_accepted_without_justification(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m, evidence=[])
    r = client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    assert r.status_code == 422


def test_unsupported_assertion_can_be_accepted_with_recorded_justification(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m, evidence=[])
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/accept",
        json={"acceptance_justification": "Accepted on reviewer's independent legal knowledge."},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_review_decision_never_erases_ratings(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": "Good support."},
        headers=m["rater_headers"],
    )
    client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    r = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=m["reviewer_headers"]
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_review_decision_records_reviewed_revision(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/accept",
        json={"acceptance_justification": "Accepted for revision-tracking coverage."},
        headers=m["reviewer_headers"],
    )
    body = r.json()
    assert body["reviewed_by"] == m["reviewer_id"]
    history = client.get(f"/api/v1/assertions/{assertion_id}/history", headers=m["reviewer_headers"])
    assert any(
        event.get("assertion_revision_number") == 1 for event in history.json()
    )


def test_reviewer_sees_evidence_ratings_comments_history(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_submitted(client, m)
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 3, "rationale": "Mixed."},
        headers=m["rater_headers"],
    )
    client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "Worth a second look."},
        headers=m["rater_headers"],
    )
    r = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"])
    body = r.json()
    for field in ("evidence", "ratings_summary", "comments", "revision_history"):
        assert field in body


def test_viewer_cannot_rate_or_suggest(client, matter_with_users, db_session):
    from tests.conftest import seed_user, seed_matter_role, auth_header

    m = matter_with_users
    viewer_id = seed_user(db_session, display_name="Read-only viewer")
    seed_matter_role(db_session, user_id=viewer_id, matter_id=m["matter_id"], role="viewer")
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=auth_header(viewer_id),
    )
    assert r.status_code == 403
