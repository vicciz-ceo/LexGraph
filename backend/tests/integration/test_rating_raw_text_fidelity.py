"""Track A, item A4 — rating write paths store raw + sanitized rationale
(issue #2, gate G1). See test_assertion_raw_text_fidelity.py's module
docstring for the fidelity contract; the same split applies here to
`assertion_ratings.rationale_raw`.

RED against current code: `rationale_raw` is absent from every rating
response today, so these fail with a KeyError.
"""

from __future__ import annotations

from tests.conftest import assertion_payload

ANGLE_BRACKET_TEXT = "see <appendix A> for details"


def test_put_rating_stores_raw_rationale(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]

    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": ANGLE_BRACKET_TEXT},
        headers=m["rater_headers"],
    )
    assert r.status_code == 201
    assert r.json()["rationale_raw"] == ANGLE_BRACKET_TEXT


def test_rating_list_exposes_raw_rationale_to_authorized_viewer(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    edited_text = "Signatory: <Title> of the Company."
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 3, "rationale": "initial rationale"},
        headers=m["rater_headers"],
    )
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": edited_text},
        headers=m["rater_headers"],
    )

    listing = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=m["reviewer_headers"]
    )
    assert listing.status_code == 200
    ratings = [row for row in listing.json() if row["user_id"] == m["rater_id"]]
    assert len(ratings) == 1
    assert ratings[0]["rationale_raw"] == edited_text
