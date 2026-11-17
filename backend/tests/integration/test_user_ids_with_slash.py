"""Accounts whose public id contains "/" (review identity:4).

Before the api:24 id rules, ``POST /api/v1/users`` accepted any caller-chosen
id, so a database can hold accounts such as ``team/lead``. ``app.migrate``
gives each a legacy sign-in token equal to that public id, and the admin
console is where the RUNBOOK sends admins to rotate it. Clients send the id
percent-encoded (``team%2Flead``), but the server decodes ``%2F`` before
routing, so the three routes that end in a user id used to answer a bare 404
for such an account: it could not be rotated, re-roled or removed in-app.

The rows are inserted through SQLAlchemy Core (``seed_user``), because the API
no longer creates such ids (they are 422 now).
"""

from __future__ import annotations

from urllib.parse import quote

import pytest

from tests.conftest import auth_header, seed_matter_role, seed_user, token_header

SLASH_IDS = ["team/lead", "a/b/c", "legal/sign-in-token", "/lead", "team/"]


def _encoded(user_id: str) -> str:
    """What the web app sends: encodeURIComponent(user_id)."""
    return quote(user_id, safe="")


def _matter_admin(db_session, matter_id: str) -> str:
    admin_id = seed_user(db_session, display_name="Matter Admin", email="admin@example.test")
    seed_matter_role(db_session, user_id=admin_id, matter_id=matter_id, role="admin")
    return admin_id


def _legacy_member(
    db_session,
    matter_id: str,
    user_id: str,
    role: str = "reviewer",
    *,
    email: str = "lead@firm.example",
) -> str:
    # seed_user stores the legacy hash (sha256 of the id): exactly what the
    # m20261116_sign_in_tokens migration leaves an upgraded account with.
    seed_user(db_session, id=user_id, display_name="Team Lead", email=email)
    seed_matter_role(db_session, user_id=user_id, matter_id=matter_id, role=role)
    return user_id


def _roster(client, matter_id: str, admin_id: str) -> dict[str, str]:
    rows = client.get(
        f"/api/v1/matters/{matter_id}/members", headers=auth_header(admin_id)
    ).json()
    return {row["user"]["id"]: row["role"] for row in rows}


@pytest.mark.parametrize("user_id", SLASH_IDS)
def test_an_admin_can_change_the_role_of_an_account_whose_id_has_a_slash(
    client, db_session, matter_with_users, user_id
):
    m = matter_with_users
    admin_id = _matter_admin(db_session, m["matter_id"])
    _legacy_member(db_session, m["matter_id"], user_id)

    r = client.put(
        f"/api/v1/matters/{m['matter_id']}/members/{_encoded(user_id)}",
        json={"role": "viewer"},
        headers=auth_header(admin_id),
    )

    assert r.status_code == 200, r.text
    assert r.json() == {
        "user": {"id": user_id, "email": "lead@firm.example", "display_name": "Team Lead"},
        "role": "viewer",
    }
    assert _roster(client, m["matter_id"], admin_id)[user_id] == "viewer"


@pytest.mark.parametrize("user_id", SLASH_IDS)
def test_an_admin_can_remove_an_account_whose_id_has_a_slash(
    client, db_session, matter_with_users, user_id
):
    m = matter_with_users
    admin_id = _matter_admin(db_session, m["matter_id"])
    _legacy_member(db_session, m["matter_id"], user_id)

    r = client.delete(
        f"/api/v1/matters/{m['matter_id']}/members/{_encoded(user_id)}",
        headers=auth_header(admin_id),
    )

    assert r.status_code == 204, r.text
    assert user_id not in _roster(client, m["matter_id"], admin_id)
    # Removing the membership does not touch the account.
    assert client.get("/api/v1/me", headers=auth_header(user_id)).json()["matters"] == []


@pytest.mark.parametrize("user_id", SLASH_IDS)
def test_rotating_retires_the_legacy_credential_of_an_id_with_a_slash(
    client, db_session, matter_with_users, user_id
):
    m = matter_with_users
    admin_id = _matter_admin(db_session, m["matter_id"])
    _legacy_member(db_session, m["matter_id"], user_id)
    # Upgraded legacy account: anyone who can read the roster can sign in
    # with the public id until it is rotated.
    assert client.get("/api/v1/me", headers=auth_header(user_id)).status_code == 200
    listed = {row["id"]: row for row in client.get(
        "/api/v1/users", headers=auth_header(admin_id)).json()}
    assert listed[user_id]["sign_in_status"] == "legacy"

    r = client.post(
        f"/api/v1/users/{_encoded(user_id)}/sign-in-token", headers=auth_header(admin_id)
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == user_id
    assert body["sign_in_status"] == "active"
    assert client.get("/api/v1/me", headers=auth_header(user_id)).status_code == 401
    me = client.get("/api/v1/me", headers=token_header(body["sign_in_token"]))
    assert me.status_code == 200
    assert me.json()["user"]["id"] == user_id


def test_an_admin_can_rotate_their_own_token_when_their_id_has_a_slash(
    client, db_session, matter_with_users
):
    m = matter_with_users
    _legacy_member(db_session, m["matter_id"], "firm/admin", role="admin")

    r = client.post("/api/v1/users/firm%2Fadmin/sign-in-token", headers=auth_header("firm/admin"))

    assert r.status_code == 200, r.text
    assert client.get("/api/v1/me", headers=auth_header("firm/admin")).status_code == 401
    assert client.get(
        "/api/v1/me", headers=token_header(r.json()["sign_in_token"])
    ).status_code == 200


def test_ids_with_a_slash_keep_every_rule_of_the_member_and_rotation_routes(
    client, db_session, matter_with_users
):
    """The path converter only widens which ids reach the handlers; the
    handlers' own checks still decide."""
    m = matter_with_users
    admin_id = _matter_admin(db_session, m["matter_id"])
    _legacy_member(db_session, m["matter_id"], "team/lead")
    seed_user(db_session, id="other/team", email="other@firm.example")
    base = f"/api/v1/matters/{m['matter_id']}/members"

    # Not a member / no such account.
    assert client.put(f"{base}/other%2Fteam", json={"role": "viewer"},
                      headers=auth_header(admin_id)).status_code == 404
    assert client.delete(f"{base}/a%2Fb%2Fc", headers=auth_header(admin_id)).json() == {
        "detail": "not a member of this matter"
    }
    assert client.post("/api/v1/users/no%2Fsuch/sign-in-token",
                       headers=auth_header(admin_id)).json() == {"detail": "user not found"}
    # A non-admin is still refused.
    assert client.put(f"{base}/team%2Flead", json={"role": "admin"},
                      headers=m["reviewer_headers"]).status_code == 403
    assert client.delete(f"{base}/team%2Flead",
                         headers=m["reviewer_headers"]).status_code == 403
    assert client.post("/api/v1/users/team%2Flead/sign-in-token",
                       headers=m["reviewer_headers"]).status_code == 403
    # An invalid role is still 422.
    assert client.put(f"{base}/team%2Flead", json={"role": "owner"},
                      headers=auth_header(admin_id)).status_code == 422
    assert _roster(client, m["matter_id"], admin_id)["team/lead"] == "reviewer"
    # Ordinary ids are unaffected, and the roster and add routes still answer.
    assert client.put(f"{base}/{m['contributor_id']}", json={"role": "reviewer"},
                      headers=auth_header(admin_id)).status_code == 200
    assert client.post(base, json={"email": "other@firm.example", "role": "viewer"},
                       headers=auth_header(admin_id)).status_code == 201
    assert client.get(base, headers=auth_header(admin_id)).status_code == 200
    # New ids with a slash are still refused (api:24).
    created = client.post("/api/v1/users", json={
        "id": "new/lead", "email": "new@firm.example", "display_name": "New"},
        headers=auth_header(admin_id))
    assert created.status_code == 422
    # A matter still keeps its last admin, whatever its id looks like.
    _legacy_member(db_session, m["matter_id"], "sole/admin", role="admin",
                   email="sole-admin@firm.example")
    assert client.delete(f"{base}/{_encoded(admin_id)}",
                         headers=auth_header(admin_id)).status_code == 204
    assert client.put(f"{base}/sole%2Fadmin", json={"role": "viewer"},
                      headers=auth_header("sole/admin")).json() == {
        "detail": "a matter must keep at least one admin"
    }
    assert client.delete(f"{base}/sole%2Fadmin",
                         headers=auth_header("sole/admin")).status_code == 409


def test_the_openapi_paths_still_name_the_user_id_parameters(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/users/{target_user_id}/sign-in-token" in paths
    member = paths["/api/v1/matters/{matter_id}/members/{member_user_id}"]
    assert set(member) == {"put", "delete"}
