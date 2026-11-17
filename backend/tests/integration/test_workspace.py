"""Workspace/session surface (Consensus UI build-out).

Covers GET /api/v1/me, the matter member roster, and admin role
management — including the no-lockout guard (a matter can never lose its
last admin).
"""

from __future__ import annotations

from sqlalchemy import event, text

from app.models.matter_role import MatterRole
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


# --- Email lookup and races (2026-11-16, findings api:24 / ui:25) -----------


def _admins_left(db_session, matter_id: str) -> int:
    return db_session.execute(
        text("SELECT count(*) FROM matter_roles WHERE matter_id = :m AND role = 'admin'"),
        {"m": matter_id},
    ).scalar_one()


def test_add_member_finds_the_account_whatever_the_email_case_or_padding(
    client, matter_with_users, db_session
):
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    vera = seed_user(db_session, display_name="Vera", email="vera.viewer@example.test")

    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": "  Vera.Viewer@Example.TEST ", "role": "viewer"},
        headers=auth_header(admin_id),
    )

    assert r.status_code == 201, r.text
    assert r.json()["user"]["id"] == vera


def test_add_member_email_shared_by_two_older_accounts_is_409(
    client, matter_with_users, db_session
):
    # Accounts created before emails were normalized can share an address
    # in different letter case until an operator resolves them; granting
    # access by that address must not guess which account is meant.
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    seed_user(db_session, display_name="Dana A", email="dana@example.test")
    seed_user(db_session, display_name="Dana B", email="Dana@Example.test")

    r = client.post(
        f"/api/v1/matters/{m['matter_id']}/members",
        json={"email": "dana@example.test", "role": "viewer"},
        headers=auth_header(admin_id),
    )

    assert r.status_code == 409, r.text
    assert "several" in r.json()["detail"]


def test_add_member_that_loses_a_concurrent_add_race_is_409_not_500(
    app, client, matter_with_users, db_session
):
    # Concurrent adds of one user used to 500 (IntegrityError on
    # uq_matter_roles_user_matter). Replay the interleaving: a concurrent
    # request adds the membership after this request's "already a member"
    # check, just before this request commits.
    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    outsider = m["outsider_id"]
    fired = []

    def concurrent_request_commits_first(session):
        pending = [o for o in session.new if isinstance(o, MatterRole) and o.user_id == outsider]
        if pending and not fired:
            fired.append(True)
            with app.state.engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO matter_roles (id, user_id, matter_id, role) "
                        "VALUES ('race-winner', :u, :m, 'viewer')"
                    ),
                    {"u": outsider, "m": m["matter_id"]},
                )

    event.listen(app.state.session_factory, "before_commit", concurrent_request_commits_first)
    try:
        r = client.post(
            f"/api/v1/matters/{m['matter_id']}/members",
            json={"email": f"{outsider}@example.test", "role": "reviewer"},
            headers=auth_header(admin_id),
        )
    finally:
        event.remove(app.state.session_factory, "before_commit", concurrent_request_commits_first)

    assert fired, "the simulated concurrent request never ran"
    assert r.status_code == 409, r.text
    roles = db_session.execute(
        text("SELECT role FROM matter_roles WHERE user_id = :u AND matter_id = :m"),
        {"u": outsider, "m": m["matter_id"]},
    ).scalars().all()
    assert roles == ["viewer"]


def test_a_demotion_that_read_a_stale_admin_count_cannot_remove_the_last_admin(
    client, matter_with_users, db_session, monkeypatch
):
    # new:last-admin-race. Two admins demoting each other at the same
    # moment both counted two admins before either committed; live, 10 of
    # 10 such races left the matter with no admin at all. The guard must
    # hold when the write happens, so replay the stale read.
    from app.routers import workspace

    m = matter_with_users
    admin_id = _seed_admin(db_session, m["matter_id"])
    monkeypatch.setattr(workspace, "_admin_count", lambda session, matter_id: 2)

    demote = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{admin_id}",
        json={"role": "viewer"},
        headers=auth_header(admin_id),
    )
    assert demote.status_code == 409, demote.text
    assert _admins_left(db_session, m["matter_id"]) == 1

    remove = client.delete(
        f"/api/v1/matters/{m['matter_id']}/members/{admin_id}",
        headers=auth_header(admin_id),
    )
    assert remove.status_code == 409, remove.text
    assert _admins_left(db_session, m["matter_id"]) == 1


def test_an_admin_can_still_step_down_while_another_admin_remains(
    client, matter_with_users, db_session
):
    m = matter_with_users
    first_admin = _seed_admin(db_session, m["matter_id"])
    second_admin = seed_user(db_session, display_name="Second Admin")
    seed_matter_role(db_session, user_id=second_admin, matter_id=m["matter_id"], role="admin")

    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{first_admin}",
        json={"role": "viewer"},
        headers=auth_header(first_admin),
    )
    assert r.status_code == 200 and r.json()["role"] == "viewer"
    removed = client.delete(
        f"/api/v1/matters/{m['matter_id']}/members/{first_admin}",
        headers=auth_header(second_admin),
    )
    assert removed.status_code == 204
    assert _admins_left(db_session, m["matter_id"]) == 1
