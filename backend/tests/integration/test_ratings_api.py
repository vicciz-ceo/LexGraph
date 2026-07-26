"""B2 — ratings + aggregates.

Gates: G3 (rate/update/remove, one current rating per user per revision,
audited), G4 (count/mean/median/distribution, separate from confidence/
review/evidence status, never computed with zero ratings, never mutates
review status). DoD items 5-9.

Owning track: B2. Routes: PUT/GET/DELETE
/api/v1/assertions/{id}/revisions/{rev}/rating,
GET .../ratings/summary, GET .../ratings.
"""

from __future__ import annotations

from tests.conftest import assertion_payload, rating_payload


def _create_submitted_assertion(client, m):
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    body = create.json()
    client.post(f"/api/v1/assertions/{body['id']}/submit", headers=m["contributor_headers"])
    return body["id"], body.get("current_revision_number", 1)


def test_rate_assertion_revision_1_to_5(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=4),
        headers=m["rater_headers"],
    )
    assert r.status_code in (200, 201)
    assert r.json()["strength"] == 4


def test_rating_below_1_rejected(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=0),
        headers=m["rater_headers"],
    )
    assert r.status_code == 422


def test_rating_above_5_rejected(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=6),
        headers=m["rater_headers"],
    )
    assert r.status_code == 422


def test_non_integer_rating_rejected(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json={"strength": 3.5, "rationale": None},
        headers=m["rater_headers"],
    )
    assert r.status_code == 422


def test_second_submission_updates_not_duplicates(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=2),
        headers=m["rater_headers"],
    )
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=5),
        headers=m["rater_headers"],
    )
    r = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/ratings",
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    ratings = [x for x in r.json() if x["user_id"] == m["rater_id"]]
    assert len(ratings) == 1
    assert ratings[0]["strength"] == 5


def test_user_can_remove_rating(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=3),
        headers=m["rater_headers"],
    )
    r = client.delete(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        headers=m["rater_headers"],
    )
    assert r.status_code == 204


def test_summary_absent_with_zero_ratings(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/ratings/summary",
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0
    assert body["average"] is None
    assert body["median"] is None


def test_summary_computes_mean_median_distribution(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)

    from tests.conftest import seed_user, seed_matter_role, auth_header

    strengths = [1, 3, 3, 5, 5]
    for i, s in enumerate(strengths):
        rater = seed_user(db_session, display_name=f"Rater {i}")
        seed_matter_role(db_session, user_id=rater, matter_id=m["matter_id"], role="contributor")
        client.put(
            f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
            json=rating_payload(strength=s),
            headers=auth_header(rater),
        )

    r = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/ratings/summary",
        headers=m["reviewer_headers"],
    )
    body = r.json()
    assert body["count"] == 5
    assert body["average"] == 3.4
    assert body["median"] == 3
    assert body["distribution"] == {"1": 1, "2": 0, "3": 2, "4": 0, "5": 2}


def test_rating_does_not_alter_model_confidence(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    before = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"]).json()
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=5),
        headers=m["rater_headers"],
    )
    after = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"]).json()
    assert after["confidence"] == before["confidence"]


def test_high_aggregate_rating_does_not_change_review_status(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)

    from tests.conftest import seed_user, seed_matter_role, auth_header

    for i in range(5):
        rater = seed_user(db_session, display_name=f"Enthusiast {i}")
        seed_matter_role(db_session, user_id=rater, matter_id=m["matter_id"], role="contributor")
        client.put(
            f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
            json=rating_payload(strength=5),
            headers=auth_header(rater),
        )
    after = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"]).json()
    assert after["status"] == "proposed"


def test_rating_requires_matter_access(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=4),
        headers=m["outsider_headers"],
    )
    assert r.status_code == 403
