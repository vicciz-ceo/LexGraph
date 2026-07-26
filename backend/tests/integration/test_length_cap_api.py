"""Track A, item A8 — length cap enforced at the API (issue #2 sub-item,
gate G4, ruling R3: 100,000 characters, director may override).

Every write path that stores a proposition/comment_text/rationale must
reject text longer than 100,000 characters with a 422 and a clear error
message; exactly 100,000 characters is still accepted. RED against the
current API: none of these fields has a max length today, so an
over-the-cap submission currently succeeds (2xx) instead of being rejected.
"""

from __future__ import annotations

from tests.conftest import assertion_payload

MAX_LENGTH = 100_000
OVER_CAP = "x" * (MAX_LENGTH + 1)
AT_CAP = "x" * MAX_LENGTH


def test_create_assertion_rejects_proposition_over_cap(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=OVER_CAP)
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 422
    assert "100,000" in r.text or "100000" in r.text


def test_create_assertion_accepts_proposition_at_exactly_the_cap(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=AT_CAP)
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201


def test_patch_assertion_rejects_proposition_over_cap(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": OVER_CAP},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_create_revision_rejects_proposition_over_cap(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/revisions",
        json={"proposition": OVER_CAP},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_create_comment_rejects_comment_text_over_cap(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": OVER_CAP},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_update_comment_rejects_comment_text_over_cap(client, matter_with_users):
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
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}/comments/{comment_id}",
        json={"comment_text": OVER_CAP},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_put_rating_rejects_rationale_over_cap(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": OVER_CAP},
        headers=m["rater_headers"],
    )
    assert r.status_code == 422
