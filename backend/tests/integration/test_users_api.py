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

Response shape pin (UI1 note; sign-in tokens 2026-11-16): bare JSON,
exact field names `{id, email, display_name, sign_in_status}`, plus a
one-time `sign_in_token` on creation -- no `{"items": [...]}` envelope on
the list, matching `list_members`'s bare-array convention in workspace.py.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event, text

from app.models.user import User
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
    # sign_in_status (2026-11-16): active | legacy | none, for the admin
    # console's legacy badge. Never the token or its hash.
    assert set(row.keys()) == {"id", "email", "display_name", "sign_in_status"}
    assert row["email"] == "global-admin@example.test"
    assert row["display_name"] == "Global Admin"
    assert row["sign_in_status"] == "legacy"  # seed_user's token == id


def test_list_users_requires_admin_on_at_least_one_matter(client, matter_with_users):
    m = matter_with_users
    # A reviewer is the highest non-admin role -- if it's forbidden,
    # contributor/viewer certainly are too.
    r = client.get("/api/v1/users", headers=m["reviewer_headers"])
    assert r.status_code == 403


def test_list_users_forbidden_for_authenticated_user_with_no_matter_role_at_all(
    client, matter_with_users
):
    # QA regression (2026-07-31-admin-provisioning): the existing 403 test
    # above only proves the gate rejects a non-admin role (reviewer). It
    # doesn't prove the gate also rejects a known, authenticated account
    # that holds NO matter_roles row whatsoever -- a materially different
    # code path through _require_admin_somewhere's `admin_row is None`
    # branch (matter_with_users' own "outsider" persona, seeded with
    # intentionally zero roles).
    m = matter_with_users
    r = client.get("/api/v1/users", headers=m["outsider_headers"])
    assert r.status_code == 403


def test_list_users_missing_token_is_401(client, matter_with_users):
    r = client.get("/api/v1/users")
    assert r.status_code == 401


def test_list_users_unknown_token_is_401(client, matter_with_users):
    r = client.get("/api/v1/users", headers=auth_header("no-such-user"))
    assert r.status_code == 401


# --- POST /api/v1/users -------------------------------------------------


def test_admin_creates_account_and_response_surfaces_its_sign_in_token_once(
    client, matter_with_users, db_session
):
    # Re-pointed 2026-11-16 (findings api:2/ui:0): the id is no longer the
    # credential (it is shown to every matter member), so the creation
    # response now carries a separate random sign-in token, shown once.
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={"email": "new.hire@example.test", "display_name": "New Hire"},
        headers=auth_header(admin_id),
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {"id", "email", "display_name", "sign_in_status", "sign_in_token"}
    assert body["email"] == "new.hire@example.test"
    assert body["display_name"] == "New Hire"
    assert isinstance(body["id"], str) and body["id"] != ""
    assert isinstance(body["sign_in_token"], str) and len(body["sign_in_token"]) >= 32
    assert body["sign_in_token"] != body["id"]
    assert body["sign_in_status"] == "active"

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


def test_create_account_duplicate_email_differing_only_by_surrounding_whitespace_is_409(
    client, matter_with_users, db_session
):
    # QA regression (2026-07-31-admin-provisioning): app/routers/users.py's
    # create_user strips the incoming email (`body.email.strip()`) BEFORE
    # the duplicate check, so a caller padding an existing address with
    # leading/trailing whitespace must still collide as 409, not slip past
    # the uniqueness check (R4) and create a second account for the same
    # real address. Pins the strip-before-compare behavior directly.
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])
    outsider_email = client.get("/api/v1/me", headers=m["outsider_headers"]).json()["user"][
        "email"
    ]

    r = client.post(
        "/api/v1/users",
        json={"email": f"  {outsider_email}  ", "display_name": "Dup Whitespace"},
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


# --- Account input rules (2026-11-16, findings api:24 / ui:25) -------------
#
# Emails are normalized (stripped, lowercased) on write and lookup, so
# "Ada@Firm.example" and "ada@firm.example" are one address; the unique
# index on users.email backs the API-level check, so a request that loses
# a creation race gets 409, not a second account (or a later 500 from
# MultipleResultsFound). Caller-chosen ids must be usable in the URL paths
# that manage an account and fit users.id (VARCHAR(36)).


def _create(client, admin_id, **body):
    return client.post("/api/v1/users", json=body, headers=auth_header(admin_id))


def test_create_account_duplicate_email_differing_only_by_case_is_409(
    client, matter_with_users, db_session
):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = _create(client, admin_id, email="Global-Admin@Example.TEST", display_name="Dup")

    assert r.status_code == 409
    emails = [row["email"].lower() for row in client.get(
        "/api/v1/users", headers=auth_header(admin_id)
    ).json()]
    assert emails.count("global-admin@example.test") == 1


def test_create_account_stores_the_email_normalized(client, matter_with_users, db_session):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = _create(client, admin_id, email="  New.Hire@Example.TEST ", display_name="New Hire")

    assert r.status_code == 201
    assert r.json()["email"] == "new.hire@example.test"
    listed = client.get("/api/v1/users", headers=auth_header(admin_id)).json()
    assert [row["email"] for row in listed if row["id"] == r.json()["id"]] == [
        "new.hire@example.test"
    ]


@pytest.mark.parametrize(
    "bad_id",
    [
        "a" * 37,  # longer than users.id (VARCHAR(36))
        "דנה",  # not ASCII
        "team/lead",  # cannot be addressed in /users/{id}/... or /members/{id}
        "who?me",
        "has space",
        "50%",
        "..",
        ".hidden",
        "-dash",
    ],
)
def test_create_account_rejects_caller_chosen_ids_that_cannot_be_used(
    client, matter_with_users, db_session, bad_id
):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = _create(client, admin_id, id=bad_id, email="odd@example.test", display_name="Odd")

    assert r.status_code == 422, r.text
    listed = client.get("/api/v1/users", headers=auth_header(admin_id)).json()
    assert all(row["email"] != "odd@example.test" for row in listed)


@pytest.mark.parametrize("good_id", ["a" * 36, "Root.Admin_2-x", "9lives"])
def test_create_account_accepts_url_safe_caller_chosen_ids(
    client, matter_with_users, db_session, good_id
):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])

    r = _create(client, admin_id, id=good_id, email="fine@example.test", display_name="Fine")

    assert r.status_code == 201, r.text
    assert r.json()["id"] == good_id
    # The id works in the URL paths that manage the account.
    rotated = client.post(
        f"/api/v1/users/{good_id}/sign-in-token", headers=auth_header(admin_id)
    )
    assert rotated.status_code == 200


@pytest.mark.parametrize(
    "field, value",
    [("email", "x" * 250 + "@example.test"), ("display_name", "x" * 256)],
)
def test_create_account_overlong_fields_are_422(client, matter_with_users, db_session, field, value):
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])
    body = {"email": "long@example.test", "display_name": "Long", field: value}

    r = _create(client, admin_id, **body)

    assert r.status_code == 422, r.text


def test_create_account_that_loses_a_concurrent_creation_race_is_409_not_500(
    app, client, matter_with_users, db_session
):
    # Eight concurrent POST /users with one email used to create two
    # accounts. Replay that interleaving deterministically: a concurrent
    # request commits the same address after this request's duplicate check
    # ran, just before this request commits.
    m = matter_with_users
    admin_id = _make_admin(db_session, m["matter_id"])
    fired = []

    def concurrent_request_commits_first(session):
        pending = [o for o in session.new if isinstance(o, User) and o.email.lower() == "race@example.test"]
        if pending and not fired:
            fired.append(True)
            with app.state.engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO users (id, email, display_name) "
                        "VALUES ('race-winner', 'race@example.test', 'Winner')"
                    )
                )

    event.listen(app.state.session_factory, "before_commit", concurrent_request_commits_first)
    try:
        r = _create(client, admin_id, email="race@example.test", display_name="Loser")
    finally:
        event.remove(app.state.session_factory, "before_commit", concurrent_request_commits_first)

    assert fired, "the simulated concurrent request never ran"
    assert r.status_code == 409, r.text
    count = db_session.execute(
        text("SELECT count(*) FROM users WHERE lower(email) = 'race@example.test'")
    ).scalar_one()
    assert count == 1
