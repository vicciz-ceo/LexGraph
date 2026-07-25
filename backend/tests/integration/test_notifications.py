"""B6 — in-app notifications (spec §15, ruling R4: in-app only, no email/push).

Owning track: B6. Read surface assumed at GET /api/v1/notifications
(scoped to the caller via the auth seam) — not enumerated verbatim in
spec §13; Planner assumption documented here for QA to reconcile against
whatever path B6 actually ships.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def test_submission_notifies_reviewers(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])

    r = client.get("/api/v1/notifications", headers=m["reviewer_headers"])
    assert r.status_code == 200
    kinds = [n["event_type"] for n in r.json()]
    assert "assertion_submitted" in kinds


def test_acceptance_notifies_author(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])

    r = client.get("/api/v1/notifications", headers=m["contributor_headers"])
    assert r.status_code == 200
    kinds = [n["event_type"] for n in r.json()]
    assert "assertion_accepted" in kinds


def test_every_individual_rating_does_not_generate_a_notification_by_default(client, matter_with_users, db_session):
    """Spec §15: 'Do not send a notification for every rating by default.'"""
    from tests.conftest import seed_user, seed_matter_role, auth_header

    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])

    for i in range(3):
        rater = seed_user(db_session, display_name=f"Rater {i}")
        seed_matter_role(db_session, user_id=rater, matter_id=m["matter_id"], role="contributor")
        client.put(
            f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
            json={"strength": 4, "rationale": None},
            headers=auth_header(rater),
        )

    r = client.get("/api/v1/notifications", headers=m["contributor_headers"])
    rating_notifications = [n for n in r.json() if n["event_type"] == "assertion_rated"]
    assert len(rating_notifications) == 0


def test_notifications_are_matter_scoped(client, matter_with_users):
    m = matter_with_users
    r = client.get("/api/v1/notifications", headers=m["outsider_headers"])
    assert r.status_code == 200
    assert r.json() == []
