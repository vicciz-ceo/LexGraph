"""Track A, item A2 — assertion write paths store raw + sanitized text
(issue #2, gate G1).

`sanitize_for_storage` itself is NOT weakened by this item -- the sanitized
`proposition` column keeps its existing (possibly lossy, browser-faithful)
value. What's new is `proposition_raw`: the author's exact submitted bytes,
stored on the `assertion_revisions` row created by every write path, and
surfaced back on `GET /assertions/{id}` (the current revision's raw text)
and `GET /assertions/{id}/revisions` (every revision's own raw text).

RED against current code: `proposition_raw` does not exist anywhere in the
response yet, so every assertion below fails with a KeyError today.
"""

from __future__ import annotations

from tests.conftest import assertion_payload

ANGLE_BRACKET_TEXT = "Signatory: <Title> of the Company."


def test_create_stores_raw_on_revision_one(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=ANGLE_BRACKET_TEXT)
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201
    assertion_id = r.json()["id"]

    revisions = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions", headers=m["contributor_headers"]
    ).json()
    assert len(revisions) == 1
    assert revisions[0]["proposition_raw"] == ANGLE_BRACKET_TEXT
    # Sanitized column is unchanged/unweakened -- it may still differ from raw.
    assert revisions[0]["proposition"] == r.json()["proposition"]


def test_get_assertion_exposes_current_revision_raw_proposition(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=ANGLE_BRACKET_TEXT)
    create = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assertion_id = create.json()["id"]

    fetched = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["contributor_headers"])
    assert fetched.status_code == 200
    assert fetched.json()["proposition_raw"] == ANGLE_BRACKET_TEXT


def test_patch_stores_raw_on_new_revision(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]

    patched_text = "see <appendix A> for details"
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": patched_text},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert r.json()["proposition_raw"] == patched_text

    revisions = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions", headers=m["contributor_headers"]
    ).json()
    assert revisions[-1]["proposition_raw"] == patched_text


def test_create_revision_endpoint_stores_raw(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]

    revision_text = "Pre <img plaintail <b>Y</b> Z"
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/revisions",
        json={"proposition": revision_text},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    assert r.json()["proposition_raw"] == revision_text
