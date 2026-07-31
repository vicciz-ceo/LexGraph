"""Workspace/session surface (Consensus UI build-out).

Covers GET /api/v1/me, the matter member roster, and admin role
management — including the no-lockout guard (a matter can never lose its
last admin).
"""

from __future__ import annotations

from tests.conftest import auth_header, seed_matter_role, seed_user


def _seed_admin(db_session, matter_id: str):
    admin_id = seed_user(db_session, display_name="Matter Admin", email="admin@example.test")
    seed_matter_role(db_session, user_id=admin_id, matter_id=matter_id, role="admin")
    return admin_id


# --- GET /me ----------------------------------------------------------------


def test_me_returns_user_and_matter_memberships(client, matter_with_users):
    m = matter_with_users
    r = client.get("/api/v1/me", headers=m["reviewer_headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["id"] == m["reviewer_id"]
    assert body["user"]["display_name"] == "Reviewer"
    assert len(body["matters"]) == 1
    matter = body["matters"][0]
    assert matter["id"] == m["matter_id"]
    assert matter["role"] == "reviewer"
    assert matter["repository_id"] == m["repository_id"]
    assert matter["organization_id"] == m["organization_id"]


def test_me_with_no_memberships_returns_empty_matter_list(client, matter_with_users):
    m = matter_with_users
    r = client.get("/api/v1/me", headers=m["outsider_headers"])
    assert r.status_code == 200
    assert r.json()["matters"] == []


def test_me_unknown_token_is_401(client, matter_with_users):
    r = client.get("/api/v1/me", headers=auth_header("no-such-user"))
    assert r.status_code == 401


def test_me_missing_header_is_401(client):
    assert client.get("/api/v1/me").status_code == 401


def test_me_empty_bearer_token_is_401(client):
    # "Authorization: Bearer " with nothing (or only whitespace) after the
    # scheme is a malformed credential per app/auth.py::get_bearer_user_id
    # (raises AuthHeaderError on an empty token), not a header that happens
    # to resolve to an empty-string user id.
    r = client.get("/api/v1/me", headers={"Authorization": "Bearer "})
    assert r.status_code == 401
    r = client.get("/api/v1/me", headers={"Authorization": "Bearer    "})
    assert r.status_code == 401


# --- Member roster ----------------------------------------------------------


def test_members_visible_to_any_matter_member(client, matter_with_users):
    m = matter_with_users
    r = client.get(f"/api/v1/matters/{m['matter_id']}/members", headers=m["contributor_headers"])
    assert r.status_code == 200
    members = r.json()
    ids = {entry["user"]["id"] for entry in members}
    assert {m["contributor_id"], m["rater_id"], m["reviewer_id"]} <= ids
    assert m["outsider_id"] not in ids
    roles = {entry["user"]["id"]: entry["role"] for entry in members}
    assert roles[m["reviewer_id"]] == "reviewer"


def test_members_forbidden_for_outsiders(client, matter_with_users):
    m = matter_with_users
    r = client.get(f"/api/v1/matters/{m['matter_id']}/members", headers=m["outsider_headers"])
    assert r.status_code == 403


def test_members_unknown_matter_is_404(client, matter_with_users):
    m = matter_with_users
    r = client.get("/api/v1/matters/nope/members", headers=m["reviewer_headers"])
    assert r.status_code == 404


# --- Admin role management --------------------------------------------------


def test_add_member_requires_admin(client, matter_with_users):
    m = matter_with_users
    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": "whoever@example.test", "role": "viewer"},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 403


def test_admin_adds_existing_account_by_email(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])

    outsider_email = client.get(
        "/api/v1/me", headers=m["outsider_headers"]
    ).json()["user"]["email"]

    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": outsider_email, "role": "viewer"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 201
    assert r.json()["role"] == "viewer"

    roster = client.get(
        f"/api/v1/matters/{m['matter_id']}/members", headers=auth_header(admin_id)
    ).json()
    assert any(entry["user"]["id"] == m["outsider_id"] for entry in roster)


def test_add_member_unknown_email_is_404(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": "ghost@example.test", "role": "viewer"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 404


def test_add_existing_member_is_409(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    reviewer_email = client.get("/api/v1/me", headers=m["reviewer_headers"]).json()["user"][
        "email"
    ]
    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": reviewer_email, "role": "viewer"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 409


def test_add_member_invalid_role_is_422(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": "x@example.test", "role": "owner"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 422


def test_add_member_unknown_matter_is_404_even_with_invalid_role(client, matter_with_users):
    # Ordering: add_member checks matter existence (_get_matter_or_404)
    # before it validates the role body (_validate_role). An unknown matter
    # must win with 404, not surface a 422 about the bogus role — the
    # caller isn't even admin of a matter that doesn't exist.
    m = matter_with_users
    r = client.post(
        "/api/v1/matters/nope/members",
        json={"email": "whoever@example.test", "role": "owner"},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 404


def test_admin_changes_member_role(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{m['contributor_id']}",
        json={"role": "reviewer"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "reviewer"

    me = client.get("/api/v1/me", headers=m["contributor_headers"]).json()
    assert me["matters"][0]["role"] == "reviewer"


def test_role_change_requires_admin(client, matter_with_users):
    m = matter_with_users
    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{m['contributor_id']}",
        json={"role": "reviewer"},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 403


def test_admin_removes_member(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.delete(
        f"/api/v1/matters/{m['matter_id']}/members/{m['rater_id']}",
        headers=auth_header(admin_id),
    )
    assert r.status_code == 204
    roster = client.get(
        f"/api/v1/matters/{m['matter_id']}/members", headers=auth_header(admin_id)
    ).json()
    assert all(entry["user"]["id"] != m["rater_id"] for entry in roster)


def test_cannot_demote_last_admin(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{admin_id}",
        json={"role": "viewer"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 409


def test_cannot_remove_last_admin(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.delete(
        f"/api/v1/matters/{m['matter_id']}/members/{admin_id}",
        headers=auth_header(admin_id),
    )
    assert r.status_code == 409


def test_second_admin_can_be_demoted(client, matter_with_users, db_session):
    m = matter_with_users
    first_admin = _seed_admin(db_session, m["matter_id"])
    second_admin = seed_user(db_session, display_name="Second Admin")
    seed_matter_role(db_session, user_id=second_admin, matter_id=m["matter_id"], role="admin")

    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{second_admin}",
        json={"role": "reviewer"},
        headers=auth_header(first_admin),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "reviewer"


# --- Unknown-matter and non-member edge cases on the mutating routes --------
#
# The roster GET already has an unknown-matter 404 test
# (test_members_unknown_matter_is_404); the three mutating routes
# (POST/PUT/DELETE) share the same _get_matter_or_404 guard but had no
# direct coverage before this QA pass.


def test_role_change_unknown_matter_is_404(client, matter_with_users):
    m = matter_with_users
    r = client.put(
        f"/api/v1/matters/nope/members/{m['contributor_id']}",
        json={"role": "reviewer"},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 404


def test_remove_member_unknown_matter_is_404(client, matter_with_users):
    m = matter_with_users
    r = client.delete(
        f"/api/v1/matters/nope/members/{m['contributor_id']}",
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 404


def test_role_change_on_non_member_is_404(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{m['outsider_id']}",
        json={"role": "reviewer"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 404


def test_remove_non_member_is_404(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    r = client.delete(
        f"/api/v1/matters/{m['matter_id']}/members/{m['outsider_id']}",
        headers=auth_header(admin_id),
    )
    assert r.status_code == 404
