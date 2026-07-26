"""Track A, item A3 — comment write paths store raw + sanitized text
(issue #2, gate G1). See test_assertion_raw_text_fidelity.py's module
docstring for the fidelity contract; the same split applies here to
`assertion_comments.comment_text_raw`.

RED against current code: `comment_text_raw` is absent from every comment
response today, so these fail with a KeyError.
"""

from __future__ import annotations

from tests.conftest import assertion_payload

ANGLE_BRACKET_TEXT = "see <appendix A> for details"


def test_create_comment_stores_raw(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]

    r = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": ANGLE_BRACKET_TEXT},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    assert r.json()["comment_text_raw"] == ANGLE_BRACKET_TEXT

    listing = client.get(
        f"/api/v1/assertions/{assertion_id}/comments", headers=m["contributor_headers"]
    ).json()
    assert listing[0]["comment_text_raw"] == ANGLE_BRACKET_TEXT


def test_update_comment_stores_raw(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    comment = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "initial comment"},
        headers=m["contributor_headers"],
    )
    comment_id = comment.json()["id"]

    edited_text = "Signatory: <Title> of the Company."
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}/comments/{comment_id}",
        json={"comment_text": edited_text},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert r.json()["comment_text_raw"] == edited_text
