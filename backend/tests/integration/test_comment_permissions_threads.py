"""Comment permissions, blank-text validation and thread integrity.

Fix package "detail", findings api:10 and api:25 (spec §9, §12):

- api:10: posting, editing and deleting comments requires
  `assertion:comment` (contributor and above). Viewers keep read access
  (`assertion:view`) but cannot mutate comments, not even their own (a user
  demoted to viewer keeps their old comments but can no longer edit them).
- api:25: a comment must contain readable text once markup is removed
  (blank and markup-only text is rejected with 422 on create and on edit);
  a reply must target a live comment (a deleted parent is a 409 conflict);
  and a deleted comment that still has live replies is listed as a
  tombstone (`deleted_at` set, text redacted), so no listed reply ever
  points at a parent that is missing from the listing.

Every test drives the real API through the `client` fixture.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest import assertion_payload, auth_header, seed_matter_role, seed_user


def _create_assertion(client, m) -> str:
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], explanation=None),
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_member(db_session, m, role: str) -> str:
    user_id = seed_user(db_session, display_name=f"{role} member")
    seed_matter_role(db_session, user_id=user_id, matter_id=m["matter_id"], role=role)
    return user_id


def _comments_url(assertion_id: str) -> str:
    return f"/api/v1/assertions/{assertion_id}/comments"


def _post(client, assertion_id, headers, comment_text, parent_comment_id=None):
    return client.post(
        _comments_url(assertion_id),
        json={"comment_text": comment_text, "parent_comment_id": parent_comment_id},
        headers=headers,
    )


def _comment_audit_count(db_session, assertion_id: str) -> int:
    return db_session.execute(
        text(
            "SELECT COUNT(*) FROM audit_events WHERE assertion_id = :aid "
            "AND event_type LIKE 'comment_%'"
        ),
        {"aid": assertion_id},
    ).scalar_one()


# --- api:10: comment mutations require assertion:comment ---------------------


def test_viewer_cannot_post_a_comment(client, matter_with_users, db_session):
    m = matter_with_users
    viewer_id = _seed_member(db_session, m, "viewer")
    assertion_id = _create_assertion(client, m)

    r = _post(client, assertion_id, auth_header(viewer_id), "viewer says hi")

    assert r.status_code == 403
    listing = client.get(_comments_url(assertion_id), headers=m["contributor_headers"])
    assert listing.json() == []
    assert _comment_audit_count(db_session, assertion_id) == 0


def test_viewer_can_still_read_comments(client, matter_with_users, db_session):
    m = matter_with_users
    viewer_id = _seed_member(db_session, m, "viewer")
    assertion_id = _create_assertion(client, m)
    _post(client, assertion_id, m["contributor_headers"], "Visible to every member.")

    r = client.get(_comments_url(assertion_id), headers=auth_header(viewer_id))

    assert r.status_code == 200
    assert [c["comment_text"] for c in r.json()] == ["Visible to every member."]


def test_outsider_cannot_read_comments(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    _post(client, assertion_id, m["contributor_headers"], "Matter-internal remark.")

    r = client.get(_comments_url(assertion_id), headers=m["outsider_headers"])

    assert r.status_code == 403


def test_user_demoted_to_viewer_cannot_edit_or_delete_their_comment(
    client, matter_with_users, db_session
):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    created = _post(client, assertion_id, m["rater_headers"], "Written while a contributor.")
    assert created.status_code == 201
    comment_id = created.json()["id"]

    db_session.execute(
        text("UPDATE matter_roles SET role = 'viewer' WHERE user_id = :uid AND matter_id = :mid"),
        {"uid": m["rater_id"], "mid": m["matter_id"]},
    )
    db_session.commit()

    edit = client.patch(
        f"{_comments_url(assertion_id)}/{comment_id}",
        json={"comment_text": "Edited as a viewer."},
        headers=m["rater_headers"],
    )
    delete = client.delete(f"{_comments_url(assertion_id)}/{comment_id}", headers=m["rater_headers"])

    assert edit.status_code == 403
    assert delete.status_code == 403
    listing = client.get(_comments_url(assertion_id), headers=m["contributor_headers"]).json()
    assert [(c["id"], c["comment_text"], c["deleted_at"]) for c in listing] == [
        (comment_id, "Written while a contributor.", None)
    ]


@pytest.mark.parametrize("role", ["contributor", "reviewer", "admin"])
def test_every_role_with_comment_permission_can_post_edit_and_delete(
    client, matter_with_users, db_session, role
):
    m = matter_with_users
    user_id = _seed_member(db_session, m, role)
    headers = auth_header(user_id)
    assertion_id = _create_assertion(client, m)

    created = _post(client, assertion_id, headers, f"Comment from a {role}.")
    assert created.status_code == 201
    comment_id = created.json()["id"]
    edited = client.patch(
        f"{_comments_url(assertion_id)}/{comment_id}",
        json={"comment_text": f"Edited comment from a {role}."},
        headers=headers,
    )
    assert edited.status_code == 200
    deleted = client.delete(f"{_comments_url(assertion_id)}/{comment_id}", headers=headers)
    assert deleted.status_code == 204


# --- api:25: blank and markup-only text is rejected ---------------------------

_BLANK_AFTER_SANITIZING = [
    "   ",
    "\n\t ",
    "<script>alert(1)</script>",
    "<b></b>",
    "<Annex 2>",
]


@pytest.mark.parametrize("comment_text", _BLANK_AFTER_SANITIZING)
def test_blank_or_markup_only_comment_is_rejected(
    client, matter_with_users, db_session, comment_text
):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)

    r = _post(client, assertion_id, m["contributor_headers"], comment_text)

    assert r.status_code == 422
    listing = client.get(_comments_url(assertion_id), headers=m["contributor_headers"])
    assert listing.json() == []
    assert _comment_audit_count(db_session, assertion_id) == 0


@pytest.mark.parametrize("comment_text", _BLANK_AFTER_SANITIZING)
def test_editing_a_comment_to_blank_or_markup_only_text_is_rejected(
    client, matter_with_users, comment_text
):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    created = _post(client, assertion_id, m["contributor_headers"], "Original <b>text</b>.")
    comment_id = created.json()["id"]

    r = client.patch(
        f"{_comments_url(assertion_id)}/{comment_id}",
        json={"comment_text": comment_text},
        headers=m["contributor_headers"],
    )

    assert r.status_code == 422
    listing = client.get(_comments_url(assertion_id), headers=m["contributor_headers"]).json()
    assert [(c["comment_text"], c["comment_text_raw"]) for c in listing] == [
        ("Original text.", "Original <b>text</b>.")
    ]


def test_comment_with_markup_around_real_text_is_still_accepted(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)

    r = _post(client, assertion_id, m["contributor_headers"], "<b>Clause 8.4</b> narrows it.")

    assert r.status_code == 201
    assert r.json()["comment_text"] == "Clause 8.4 narrows it."
    assert r.json()["comment_text_raw"] == "<b>Clause 8.4</b> narrows it."


# --- api:25: replies and deleted parents --------------------------------------


def test_reply_to_a_deleted_comment_is_rejected(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    parent_id = _post(client, assertion_id, m["reviewer_headers"], "Parent remark.").json()["id"]
    assert client.delete(
        f"{_comments_url(assertion_id)}/{parent_id}", headers=m["reviewer_headers"]
    ).status_code == 204
    audit_before = _comment_audit_count(db_session, assertion_id)

    r = _post(client, assertion_id, m["contributor_headers"], "Late reply.", parent_id)

    assert r.status_code == 409
    assert "deleted" in r.json()["detail"]
    assert _comment_audit_count(db_session, assertion_id) == audit_before
    stored = db_session.execute(
        text("SELECT COUNT(*) FROM assertion_comments WHERE parent_comment_id = :pid"),
        {"pid": parent_id},
    ).scalar_one()
    assert stored == 0


def test_reply_to_a_comment_on_another_assertion_is_not_found(client, matter_with_users):
    m = matter_with_users
    first = _create_assertion(client, m)
    second = client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            m["matter_id"],
            m["repository_id"],
            proposition="A second, unrelated proposition about Clause 9.",
            explanation=None,
        ),
        headers=m["contributor_headers"],
    ).json()["id"]
    foreign_parent = _post(client, first, m["contributor_headers"], "On the first one.").json()["id"]

    r = _post(client, second, m["contributor_headers"], "Cross-thread reply.", foreign_parent)

    assert r.status_code == 404


def test_deleting_a_parent_keeps_its_replies_attached_through_a_tombstone(
    client, matter_with_users
):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    parent = _post(client, assertion_id, m["reviewer_headers"], "Parent <i>remark</i>.").json()
    reply = _post(
        client, assertion_id, m["contributor_headers"], "Reply to the parent.", parent["id"]
    ).json()
    assert client.delete(
        f"{_comments_url(assertion_id)}/{parent['id']}", headers=m["reviewer_headers"]
    ).status_code == 204

    listing = client.get(_comments_url(assertion_id), headers=m["rater_headers"])

    assert listing.status_code == 200
    by_id = {c["id"]: c for c in listing.json()}
    assert list(by_id) == [parent["id"], reply["id"]]
    tombstone = by_id[parent["id"]]
    assert tombstone["deleted_at"] is not None
    assert tombstone["comment_text"] == ""
    assert tombstone["comment_text_raw"] is None
    assert tombstone["user_id"] == m["reviewer_id"]
    assert by_id[reply["id"]]["parent_comment_id"] == parent["id"]
    assert by_id[reply["id"]]["comment_text"] == "Reply to the parent."


def test_tombstones_cover_every_deleted_ancestor_of_a_live_reply(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    url = _comments_url(assertion_id)
    root = _post(client, assertion_id, m["contributor_headers"], "Root.").json()["id"]
    middle = _post(client, assertion_id, m["rater_headers"], "Middle.", root).json()["id"]
    leaf = _post(client, assertion_id, m["reviewer_headers"], "Leaf.", middle).json()["id"]
    unrelated = _post(client, assertion_id, m["rater_headers"], "Unrelated.").json()["id"]
    for comment_id, headers in (
        (root, m["contributor_headers"]),
        (middle, m["rater_headers"]),
        (unrelated, m["rater_headers"]),
    ):
        assert client.delete(f"{url}/{comment_id}", headers=headers).status_code == 204

    listing = client.get(url, headers=m["contributor_headers"]).json()

    assert [(c["id"], c["deleted_at"] is not None) for c in listing] == [
        (root, True),
        (middle, True),
        (leaf, False),
    ]
    listed = {c["id"] for c in listing}
    assert all(c["parent_comment_id"] in listed for c in listing if c["parent_comment_id"])

    # Once the last live reply goes, the deleted thread disappears entirely.
    assert client.delete(f"{url}/{leaf}", headers=m["reviewer_headers"]).status_code == 204
    assert client.get(url, headers=m["contributor_headers"]).json() == []


def test_a_tombstone_cannot_be_edited_or_deleted_again(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    url = _comments_url(assertion_id)
    parent = _post(client, assertion_id, m["contributor_headers"], "Parent.").json()["id"]
    _post(client, assertion_id, m["rater_headers"], "Reply.", parent)
    assert client.delete(f"{url}/{parent}", headers=m["contributor_headers"]).status_code == 204

    edit = client.patch(
        f"{url}/{parent}", json={"comment_text": "Resurrected."}, headers=m["contributor_headers"]
    )
    delete = client.delete(f"{url}/{parent}", headers=m["contributor_headers"])

    assert edit.status_code == 404
    assert delete.status_code == 404


def test_assertion_detail_embeds_the_same_thread_as_the_comment_listing(client, matter_with_users):
    """GET /assertions/{id} embeds `comments` for the detail page; it must
    apply the same visibility rule as GET .../comments (tombstones for
    deleted parents, creation order), or the page shows orphaned replies."""
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    url = _comments_url(assertion_id)
    parent = _post(client, assertion_id, m["reviewer_headers"], "Parent remark.").json()["id"]
    reply = _post(client, assertion_id, m["contributor_headers"], "Reply.", parent).json()["id"]
    lone = _post(client, assertion_id, m["rater_headers"], "Deleted, no replies.").json()["id"]
    later = _post(client, assertion_id, m["rater_headers"], "Later remark.").json()["id"]
    assert client.delete(f"{url}/{parent}", headers=m["reviewer_headers"]).status_code == 204
    assert client.delete(f"{url}/{lone}", headers=m["rater_headers"]).status_code == 204

    listing = client.get(url, headers=m["contributor_headers"]).json()
    detail = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["contributor_headers"])

    assert detail.status_code == 200
    embedded = detail.json()["comments"]
    assert [c["id"] for c in embedded] == [c["id"] for c in listing] == [parent, reply, later]
    tombstone = embedded[0]
    assert tombstone["deleted_at"] is not None
    assert (tombstone["comment_text"], tombstone["comment_text_raw"]) == ("", None)
    assert embedded[1]["parent_comment_id"] == parent


# --- new:unpaired-surrogate-text (also api:20 part b, for this router) -------

_UNPAIRED_SURROGATE_BODY = b'{"comment_text": "lone \\ud800 surrogate"}'


def test_comment_with_an_unpaired_surrogate_is_rejected_not_a_500(client, matter_with_users):
    """JSON may escape a lone UTF-16 surrogate (`\\ud800`) that no UTF-8
    database can store; it used to crash the insert (HTTP 500)."""
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    headers = {**m["contributor_headers"], "Content-Type": "application/json"}

    created = client.post(_comments_url(assertion_id), content=_UNPAIRED_SURROGATE_BODY, headers=headers)
    original = _post(client, assertion_id, m["contributor_headers"], "Fine text.").json()["id"]
    edited = client.patch(
        f"{_comments_url(assertion_id)}/{original}", content=_UNPAIRED_SURROGATE_BODY, headers=headers
    )

    assert created.status_code == 422
    assert edited.status_code == 422
    listing = client.get(_comments_url(assertion_id), headers=m["contributor_headers"]).json()
    assert [c["comment_text"] for c in listing] == ["Fine text."]


def test_empty_comment_text_is_rejected_with_a_readable_detail(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)

    r = _post(client, assertion_id, m["contributor_headers"], "")

    assert r.status_code == 422
    assert r.json()["detail"] == "comment_text must contain text other than whitespace or markup"
