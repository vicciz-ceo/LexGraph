"""The rating summary says how many ratings earlier revisions received
(finding ui:12, spec §10: "Inform users that the revised assertion has not
yet been rated").

GET .../revisions/{n}/ratings/summary gains ``prior_revision_rating_count``:
the number of ratings recorded against this assertion's revisions numbered
below ``n``. Ratings stay attached to the revision they were given on (ruling
R5); this count only lets a client say that earlier revisions were rated while
the one in front of the user is not.
"""

from __future__ import annotations

from tests.conftest import assertion_payload, auth_header, seed_matter_role, seed_user


def _summary(client, assertion_id: str, revision: int, headers) -> dict:
    response = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/{revision}/ratings/summary", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def _rate(client, assertion_id: str, revision: int, headers, strength: int = 4) -> None:
    response = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{revision}/rating",
        json={"strength": strength},
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text


def _revise(client, assertion_id: str, headers, proposition: str) -> None:
    response = client.patch(
        f"/api/v1/assertions/{assertion_id}", json={"proposition": proposition}, headers=headers
    )
    assert response.status_code == 200, response.text


def test_summary_counts_ratings_recorded_on_earlier_revisions(client, matter_with_users, db_session):
    m = matter_with_users
    third = seed_user(db_session, display_name="Third rater")
    seed_matter_role(db_session, user_id=third, matter_id=m["matter_id"], role="contributor")
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assert created.status_code == 201, created.text
    assertion_id = created.json()["id"]
    other = client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            m["matter_id"], m["repository_id"], save_as="proposed",
            proposition="An unrelated assertion whose ratings must never be counted here.",
        ),
        headers=m["contributor_headers"],
    ).json()["id"]

    _rate(client, assertion_id, 1, m["rater_headers"])
    _rate(client, assertion_id, 1, m["reviewer_headers"], strength=5)
    _rate(client, other, 1, auth_header(third))
    first = _summary(client, assertion_id, 1, m["rater_headers"])
    assert first["count"] == 2
    assert first["prior_revision_rating_count"] == 0

    _revise(client, assertion_id, m["reviewer_headers"], "Clause 8.4 narrows the Clause 8.2 notice duty.")
    second = _summary(client, assertion_id, 2, m["rater_headers"])
    assert second["count"] == 0
    assert second["prior_revision_rating_count"] == 2

    _revise(client, assertion_id, m["reviewer_headers"], "Clause 8.4 limits the Clause 8.2 notice duty.")
    _rate(client, assertion_id, 2, auth_header(third), strength=2)
    third_revision = _summary(client, assertion_id, 3, m["rater_headers"])
    assert third_revision["count"] == 0
    assert third_revision["prior_revision_rating_count"] == 3
    # Ratings stay where they were given: revision 2 counts only revision 1.
    assert _summary(client, assertion_id, 2, m["rater_headers"])["prior_revision_rating_count"] == 2
