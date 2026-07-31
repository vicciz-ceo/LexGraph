"""B2 — Users API RED tests (`GET /api/v1/users`, `POST /api/v1/users`).

Access model (ruling R2): any caller holding the `admin` role on >=1
matter may list and create user accounts. This is a global "admin
somewhere" gate, NOT scoped to a single matter -- unlike the per-matter
member endpoints in `app/routers/workspace.py` -- so the `matter_with_users`
fixture's reviewer/contributor/outsider accounts are never sufficient, an
admin role has to be seeded explicitly (`_make_admin`, mirroring
`test_workspace.py::_seed_admin`).

Every `/api/v1/...` route not yet registered 404s today (see
`app/main.py`'s own comment on that), so every assertion below currently
fails on a 404 instead of the intended status code -- the right RED
reason until a Developer track adds and registers the router.

Response shape pin (R3 + UI1 note): bare JSON, exact field names
`{id, email, display_name}` -- no `{"items": [...]}` envelope on the list,
matching `list_members`'s bare-array convention in workspace.py.
"""

from __future__ import annotations

from tests.conftest import auth_header, seed_matter_role, seed_user


def _make_admin(db_session, matter_id: str, *, email: str = "global-admin@example.test") -> str:
    admin_id = seed_user(db_session, display_name="Global Admin", email=email)
    seed_matter_role(db_session, user_id=admin_id, matter_id=matter_id, role="admin")
    return admin_id


# --- GET /api/v1/users -------------------------------------------------


def test_list_users_returns_bare_array_with_exact_fields(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.get("/api/v1/users", headers=auth_header(admin_id))
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list), "bare array, not an {'items': [...]} envelope"

    ids = {row["id"] for row in body}
    assert admin_id in ids
    assert m["contributor_id"] in ids

    row = next(row for row in body if row["id"] == admin_id)
    assert set(row.keys()) == {"id", "email", "display_name"}
    assert row["email"] == "global-admin@example.test"
    assert row["display_name"] == "Global Admin"


def test_list_users_requires_admin_on_at_least_one_matter(client, matter_with_users):
    m = matter_with_users
    # A reviewer is the highest non-admin role -- if it's forbidden,
    # contributor/viewer certainly are too.
    r = client.get("/api/v1/users", headers=m["reviewer_headers"])
    assert r.status_code == 403


def test_list_users_missing_token_is_401(client, matter_with_users):
    r = client.get("/api/v1/users")
    assert r.status_code == 401


def test_list_users_unknown_token_is_401(client, matter_with_users):
    r = client.get("/api/v1/users", headers=auth_header("no-such-user"))
    assert r.status_code == 401


# --- POST /api/v1/users -------------------------------------------------


def test_admin_creates_account_and_response_surfaces_id_prominently(
    client, matter_with_users, db_session
):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={"email": "new.hire@example.test", "display_name": "New Hire"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {"id", "email", "display_name"}
    assert body["email"] == "new.hire@example.test"
    assert body["display_name"] == "New Hire"
    assert isinstance(body["id"], str) and body["id"] != ""

    listed = client.get("/api/v1/users", headers=auth_header(admin_id)).json()
    assert any(row["id"] == body["id"] for row in listed)


def test_create_account_accepts_caller_chosen_id(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={"id": "root-admin", "email": "root@example.test", "display_name": "Root Admin"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 201
    assert r.json()["id"] == "root-admin"


def test_create_account_requires_admin_on_at_least_one_matter(client, matter_with_users):
    m = matter_with_users
    r = client.post(
        "/api/v1/users",
        json={"email": "x@example.test", "display_name": "X"},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 403


def test_create_account_missing_token_is_401(client, matter_with_users):
    r = client.post("/api/v1/users", json={"email": "x@example.test", "display_name": "X"})
    assert r.status_code == 401


def test_create_account_duplicate_email_is_409(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])
    outsider_email = client.get("/api/v1/me", headers=m["outsider_headers"]).json()["user"][
        "email"
    ]

    r = client.post(
        "/api/v1/users",
        json={"email": outsider_email, "display_name": "Dup"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 409


def test_create_account_invalid_email_is_422(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "display_name": "X"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 422


def test_create_account_empty_display_name_is_422(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={"email": "blank.name@example.test", "display_name": "   "},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 422


def test_create_account_duplicate_caller_chosen_id_is_422(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={
            "id": m["contributor_id"],
            "email": "another@example.test",
            "display_name": "Another",
        },
        headers=auth_header(admin_id),
    )
    assert r.status_code == 422
