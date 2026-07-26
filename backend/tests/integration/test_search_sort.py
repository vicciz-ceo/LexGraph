"""B5 — search, filter, sort (spec §17) + reviewer queue filters (spec §10).

Owning track: B5. GET /api/v1/assertions with query params.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def _create(client, m, **overrides):
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=m["contributor_headers"],
    )
    return r.json()["id"]


def test_search_by_proposition_text(client, matter_with_users):
    m = matter_with_users
    _create(client, m, proposition="Clause 8.4 creates a limited exception to Clause 8.2.")
    _create(client, m, proposition="An entirely unrelated proposition about jurisdiction.")
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "q": "Clause 8.4"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    results = r.json()["items"]
    assert len(results) == 1
    assert "8.4" in results[0]["proposition"]


def test_filter_by_origin_user_suggested(client, matter_with_users):
    m = matter_with_users
    _create(client, m)
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "origin": "user_suggested"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert all(a["origin"] == "user_suggested" for a in r.json()["items"])


def test_filter_by_review_status(client, matter_with_users):
    m = matter_with_users
    _create(client, m, save_as="draft")
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "status": "draft"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert all(a["status"] == "draft" for a in r.json()["items"])


def test_filter_average_rating_at_least(client, matter_with_users):
    m = matter_with_users
    a1 = _create(client, m, save_as="proposed")
    client.put(
        f"/api/v1/assertions/{a1}/revisions/1/rating",
        json={"strength": 5, "rationale": None},
        headers=m["rater_headers"],
    )
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "min_average_rating": 4},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert all(a["id"] == a1 for a in r.json()["items"])


def test_filter_assertions_current_user_has_not_rated(client, matter_with_users):
    m = matter_with_users
    a1 = _create(client, m, save_as="proposed")
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "unrated_by_me": True},
        headers=m["rater_headers"],
    )
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["items"]]
    assert a1 in ids


def test_sort_by_creation_date_descending(client, matter_with_users):
    m = matter_with_users
    first = _create(client, m, proposition="First created proposition text.")
    second = _create(client, m, proposition="Second created proposition text.")
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "sort": "-created_at"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["items"]]
    assert ids.index(second) < ids.index(first)


def test_reviewer_queue_filters_by_user_suggested_and_evidence_status(client, matter_with_users):
    m = matter_with_users
    _create(client, m, evidence=[], save_as="proposed")
    r = client.get(
        "/api/v1/assertions",
        params={
            "matter_id": m["matter_id"],
            "origin": "user_suggested",
            "evidence_status": "awaiting_evidence",
            "status": "proposed",
        },
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


def test_search_results_never_cross_matter(client, matter_with_users, db_session):
    from tests.conftest import seed_organization, seed_repository, seed_matter, seed_matter_role, auth_header

    m = matter_with_users
    _create(client, m, proposition="Shared phrase: notification obligation exception.")

    other_org = seed_organization(db_session, name="Other Org")
    other_repo = seed_repository(db_session, organization_id=other_org)
    other_matter = seed_matter(db_session, repository_id=other_repo)
    seed_matter_role(db_session, user_id=m["contributor_id"], matter_id=other_matter, role="contributor")
    client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            other_matter, other_repo, proposition="Shared phrase: notification obligation exception."
        ),
        headers=m["contributor_headers"],
    )

    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "q": "notification obligation"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert all(a["matter_id"] == m["matter_id"] for a in r.json()["items"])
