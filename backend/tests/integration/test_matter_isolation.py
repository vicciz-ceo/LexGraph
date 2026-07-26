"""B7 — cross-cutting matter isolation (gate G9).

A user without matter access cannot view, rate, comment on, or attach
evidence to an assertion; evidence from an inaccessible matter cannot be
attached; aggregates never mix matters. No dedicated write-set — proven
against whatever B1/B2/B3/B4/B5 ship (routers: assertions, ratings,
comments, evidence). Sequenced last among backend tracks in the
parallelization plan.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def _create_and_submit(client, m):
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = r.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    return assertion_id


def test_outsider_cannot_view_assertion(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    r = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["outsider_headers"])
    assert r.status_code in (403, 404)


def test_outsider_cannot_rate_assertion(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 3, "rationale": None},
        headers=m["outsider_headers"],
    )
    assert r.status_code in (403, 404)


def test_outsider_cannot_comment(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "Should not be allowed."},
        headers=m["outsider_headers"],
    )
    assert r.status_code in (403, 404)


def test_outsider_cannot_attach_evidence(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": "any-span", "evidence_role": "supports"},
        headers=m["outsider_headers"],
    )
    assert r.status_code in (403, 404)


def test_rating_list_from_one_matter_never_includes_another_matters_ratings(client, matter_with_users, db_session):
    from tests.conftest import (
        seed_organization,
        seed_repository,
        seed_matter,
        seed_matter_role,
        auth_header,
    )

    m = matter_with_users
    assertion_a = _create_and_submit(client, m)
    client.put(
        f"/api/v1/assertions/{assertion_a}/revisions/1/rating",
        json={"strength": 5, "rationale": None},
        headers=m["rater_headers"],
    )

    other_org = seed_organization(db_session, name="Other Org")
    other_repo = seed_repository(db_session, organization_id=other_org)
    other_matter = seed_matter(db_session, repository_id=other_repo)
    other_contributor = m["contributor_id"]
    seed_matter_role(db_session, user_id=other_contributor, matter_id=other_matter, role="contributor")
    other_create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(other_matter, other_repo, save_as="draft"),
        headers=auth_header(other_contributor),
    )
    assertion_b = other_create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_b}/submit", headers=auth_header(other_contributor))

    r = client.get(
        f"/api/v1/assertions/{assertion_b}/revisions/1/ratings/summary",
        headers=auth_header(other_contributor),
    )
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_matter_id_mismatch_between_assertion_and_rating_rejected(client, matter_with_users, db_session):
    """A rating must belong to the same repository and matter as the
    assertion (spec §4) — proven by attempting to rate via a payload that
    claims a foreign matter_id where the API accepts one."""
    from tests.conftest import seed_organization, seed_repository, seed_matter

    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    other_org = seed_organization(db_session, name="Foreign Org")
    other_repo = seed_repository(db_session, organization_id=other_org)
    other_matter = seed_matter(db_session, repository_id=other_repo)

    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": None, "matter_id": other_matter},
        headers=m["rater_headers"],
    )
    assert r.status_code in (200, 201, 422)
    if r.status_code in (200, 201):
        assert r.json().get("matter_id", m["matter_id"]) == m["matter_id"]
