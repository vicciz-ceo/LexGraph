"""B1 — assertion CRUD, submission, evidence, revisions.

Gates: G1 (draft creation + evidence), G2 (submission never implies
acceptance), G6 (revisions). DoD items 1-4, 12-13.

Owning track: B1. Routes: POST/GET/PATCH /api/v1/assertions[...], submit,
withdraw, revisions, evidence. All currently 404 (no router registered —
app/main.py). Tests that only exercise routing need no DB fixtures and are
plain assertion-RED right now; tests that need seeded matter/user context
use `matter_with_users` and are schema-RED (OperationalError) until item F1
lands.
"""

from __future__ import annotations

from tests.conftest import assertion_payload, auth_header, new_id


def test_create_draft_assertion_returns_201(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], save_as="draft")
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "draft"
    assert body["origin"] == "user_suggested"
    assert body["author_user_id"] == m["contributor_id"]


def test_create_assertion_requires_auth(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"])
    r = client.post("/api/v1/assertions", json=payload)
    assert r.status_code == 401


def test_create_assertion_missing_proposition_returns_422(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"])
    payload["proposition"] = ""
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 422


def test_create_assertion_without_evidence_marks_unsupported(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], evidence=[])
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201
    assert r.json()["evidence_status"] in ("unsupported", "awaiting_evidence")


def test_submit_draft_marks_proposed_and_user_suggested(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "proposed"
    assert body["origin"] == "user_suggested"


def test_submission_never_auto_accepts(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    assert r.json()["status"] != "accepted"


def test_get_assertion_returns_full_shape(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["contributor_headers"])
    assert r.status_code == 200
    body = r.json()
    for field in (
        "proposition",
        "status",
        "origin",
        "confidence",
        "current_revision_number",
        "evidence_status",
    ):
        assert field in body


def test_user_can_edit_own_draft(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": "An edited proposition text."},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert r.json()["proposition"] == "An edited proposition text."


def test_user_cannot_edit_another_users_draft(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": "Hostile takeover edit."},
        headers=m["rater_headers"],
    )
    assert r.status_code == 403


def test_editing_accepted_assertion_creates_new_proposed_revision(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])

    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": "A materially different proposition."},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "proposed"
    assert body["current_revision_number"] >= 2


def test_original_revision_remains_available(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.get(f"/api/v1/assertions/{assertion_id}/revisions", headers=m["contributor_headers"])
    assert r.status_code == 200
    revisions = r.json()
    assert len(revisions) >= 1
    assert revisions[0]["revision_number"] == 1


def test_withdraw_own_draft(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(f"/api/v1/assertions/{assertion_id}/withdraw", headers=m["contributor_headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "withdrawn"


def test_attach_evidence_with_role(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": new_id(), "evidence_role": "supports"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    assert r.json()["evidence_role"] == "supports"


def test_attach_evidence_invalid_role_rejected(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": new_id(), "evidence_role": "not_a_real_role"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_remove_evidence(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    add = client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": new_id(), "evidence_role": "supports"},
        headers=m["contributor_headers"],
    )
    evidence_id = add.json()["id"]
    r = client.delete(
        f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
        headers=m["contributor_headers"],
    )
    assert r.status_code == 204


def test_optimistic_concurrency_conflict_on_stale_patch(client, matter_with_users):
    """PATCH must use revision checks and prevent lost updates (spec §13)."""
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    body = create.json()
    assertion_id = body["id"]
    stale_revision = body["current_revision_number"]
    # First edit advances the revision.
    client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": "First edit.", "expected_revision_number": stale_revision},
        headers=m["contributor_headers"],
    )
    # Second edit still claims the now-stale revision number -> conflict.
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": "Second, conflicting edit.", "expected_revision_number": stale_revision},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 409
