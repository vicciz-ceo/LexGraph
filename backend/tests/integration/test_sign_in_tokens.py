"""Sign-in tokens are separate from public user ids (findings api:2, ui:0).

Before this change the bearer token WAS the user id, and every matter
member receives other members' ids (roster, author/reviewer/commenter
ids), so a viewer could read an admin's id and sign in as the admin.
These tests drive the real app (TestClient over create_app(), the real
bootstrap/seed CLIs via subprocess) with real random tokens.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AuthHeaderError,
    get_bearer_user_id,
    hash_sign_in_token,
    is_legacy_sign_in_hash,
)
from app.main import create_app
from app.models.audit_event import AuditEvent
from app.models.user import User
from tests.conftest import (
    assertion_payload,
    auth_header,
    seed_document,
    seed_matter,
    seed_matter_role,
    seed_source_span,
    seed_user,
    token_header,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
TOKEN_LINE = re.compile(r"sign-in token[^:\n]*:\s*(\S+)")


# --- helpers -----------------------------------------------------------------


def _admin_with_real_token(client, db_session, matter_id, *, email="admin@example.test"):
    """A seeded admin whose legacy credential is replaced by a real token."""
    admin_id = seed_user(db_session, display_name="Matter Admin", email=email)
    seed_matter_role(db_session, user_id=admin_id, matter_id=matter_id, role="admin")
    r = client.post(f"/api/v1/users/{admin_id}/sign-in-token", headers=auth_header(admin_id))
    assert r.status_code == 200, r.text
    return admin_id, r.json()["sign_in_token"]


def _create_account(client, admin_token, email, display_name):
    r = client.post(
        "/api/v1/users",
        json={"email": email, "display_name": display_name},
        headers=token_header(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"], r.json()["sign_in_token"]


def _grant(client, admin_token, matter_id, email, role):
    r = client.post(
        f"/api/v1/matters/{matter_id}/members",
        json={"email": email, "role": role},
        headers=token_header(admin_token),
    )
    assert r.status_code == 201, r.text


def _app_on(db_path: Path, monkeypatch):
    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    return create_app()


def _run_module(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


# --- api:2 regression: the roster id is not a credential ---------------------


def test_fresh_bootstrap_non_admin_cannot_sign_in_with_the_admin_id_from_the_roster(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "fresh.db"
    boot = _run_module("app.bootstrap", "--db", str(db_path))
    assert boot.returncode == 0, boot.stderr
    admin_token = TOKEN_LINE.search(boot.stdout).group(1)

    app = _app_on(db_path, monkeypatch)
    try:
        with TestClient(app) as client:
            me = client.get("/api/v1/me", headers=token_header(admin_token))
            assert me.status_code == 200, me.text
            admin_id = me.json()["user"]["id"]
            matter_id = me.json()["matters"][0]["id"]
            assert admin_token != admin_id

            viewer_id, viewer_token = _create_account(
                client, admin_token, "vera@example.test", "Vera Viewer"
            )
            _grant(client, admin_token, matter_id, "vera@example.test", "viewer")

            # Only the viewer's own credential from here on.
            roster = client.get(
                f"/api/v1/matters/{matter_id}/members", headers=token_header(viewer_token)
            )
            assert roster.status_code == 200
            stolen = next(m["user"]["id"] for m in roster.json() if m["role"] == "admin")
            assert stolen == admin_id  # ids stay public references

            assert client.get("/api/v1/me", headers=auth_header(stolen)).status_code == 401
            escalate = client.put(
                f"/api/v1/matters/{matter_id}/members/{viewer_id}",
                json={"role": "admin"},
                headers=auth_header(stolen),
            )
            assert escalate.status_code == 401
            assert client.get("/api/v1/users", headers=auth_header(stolen)).status_code == 401

            mine = client.get("/api/v1/me", headers=token_header(viewer_token)).json()
            assert mine["matters"][0]["role"] == "viewer"
            # The viewer's own id is not its credential either.
            assert client.get("/api/v1/me", headers=auth_header(viewer_id)).status_code == 401
    finally:
        app.state.engine.dispose()


# --- POST /users -------------------------------------------------------------


def test_token_from_post_users_signs_in_and_the_user_id_does_not(
    client, db_session, matter_with_users
):
    m = matter_with_users
    _, admin_token = _admin_with_real_token(client, db_session, m["matter_id"])

    r = client.post(
        "/api/v1/users",
        json={"email": "new.hire@example.test", "display_name": "New Hire"},
        headers=token_header(admin_token),
    )
    assert r.status_code == 201
    body = r.json()
    token, user_id = body["sign_in_token"], body["id"]
    assert len(token) >= 32 and token != user_id
    assert body["sign_in_status"] == "active"

    me = client.get("/api/v1/me", headers=token_header(token))
    assert me.status_code == 200
    assert me.json()["user"] == {
        "id": user_id,
        "email": "new.hire@example.test",
        "display_name": "New Hire",
    }
    assert client.get("/api/v1/me", headers=auth_header(user_id)).status_code == 401

    stored = db_session.get(User, user_id)
    db_session.refresh(stored)
    assert stored.sign_in_token_hash == hash_sign_in_token(token)
    assert token not in str(stored.sign_in_token_hash)

    # Shown once: listing accounts never returns it again.
    listed = client.get("/api/v1/users", headers=token_header(admin_token))
    assert token not in listed.text
    assert stored.sign_in_token_hash not in listed.text


def test_caller_chosen_id_is_not_a_credential(client, db_session, matter_with_users):
    m = matter_with_users
    _, admin_token = _admin_with_real_token(client, db_session, m["matter_id"])
    r = client.post(
        "/api/v1/users",
        json={"id": "root-admin", "email": "root@example.test", "display_name": "Root"},
        headers=token_header(admin_token),
    )
    assert r.status_code == 201
    assert client.get("/api/v1/me", headers=auth_header("root-admin")).status_code == 401
    me = client.get("/api/v1/me", headers=token_header(r.json()["sign_in_token"]))
    assert me.json()["user"]["id"] == "root-admin"


# --- rotation ----------------------------------------------------------------


def test_rotation_returns_a_new_token_once_and_invalidates_the_old_one(
    client, db_session, matter_with_users
):
    m = matter_with_users
    _, admin_token = _admin_with_real_token(client, db_session, m["matter_id"])
    user_id, old_token = _create_account(client, admin_token, "r@example.test", "Rotated")

    r = client.post(f"/api/v1/users/{user_id}/sign-in-token", headers=token_header(admin_token))
    assert r.status_code == 200
    body = r.json()
    new_token = body["sign_in_token"]
    assert set(body) == {"id", "email", "display_name", "sign_in_status", "sign_in_token"}
    assert body["id"] == user_id and body["sign_in_status"] == "active"
    assert new_token not in (old_token, user_id)

    assert client.get("/api/v1/me", headers=token_header(old_token)).status_code == 401
    me = client.get("/api/v1/me", headers=token_header(new_token))
    assert me.status_code == 200 and me.json()["user"]["id"] == user_id


def test_admin_can_rotate_their_own_legacy_token(client, db_session, matter_with_users):
    m = matter_with_users
    admin_id = seed_user(db_session, display_name="Legacy Admin", email="legacy@example.test")
    seed_matter_role(db_session, user_id=admin_id, matter_id=m["matter_id"], role="admin")

    listed = client.get("/api/v1/users", headers=auth_header(admin_id)).json()
    assert next(u for u in listed if u["id"] == admin_id)["sign_in_status"] == "legacy"

    r = client.post(f"/api/v1/users/{admin_id}/sign-in-token", headers=auth_header(admin_id))
    assert r.status_code == 200
    new_token = r.json()["sign_in_token"]

    # The public id no longer signs in; the new token does.
    assert client.get("/api/v1/me", headers=auth_header(admin_id)).status_code == 401
    listed = client.get("/api/v1/users", headers=token_header(new_token)).json()
    assert next(u for u in listed if u["id"] == admin_id)["sign_in_status"] == "active"


def test_rotation_needs_the_admin_role_on_every_matter_of_the_target(
    client, db_session, matter_with_users
):
    """An admin of one matter must not take over another matter's admin by
    rotating their token and reading back the new one."""
    m = matter_with_users
    _, admin_a_token = _admin_with_real_token(client, db_session, m["matter_id"])

    other_matter = seed_matter(db_session, repository_id=m["repository_id"], name="Other")
    admin_b_id = seed_user(db_session, display_name="Admin B", email="b@example.test")
    seed_matter_role(db_session, user_id=admin_b_id, matter_id=other_matter, role="admin")
    # Admin B also shares admin A's matter, as a viewer.
    seed_matter_role(db_session, user_id=admin_b_id, matter_id=m["matter_id"], role="viewer")

    r = client.post(
        f"/api/v1/users/{admin_b_id}/sign-in-token", headers=token_header(admin_a_token)
    )
    assert r.status_code == 403
    assert "sign_in_token" not in r.json()
    # Admin B's credential is untouched.
    assert client.get("/api/v1/me", headers=auth_header(admin_b_id)).status_code == 200

    # An account with no memberships can be (re)issued by any admin.
    loner_id, _ = _create_account(client, admin_a_token, "loner@example.test", "Loner")
    r = client.post(f"/api/v1/users/{loner_id}/sign-in-token", headers=token_header(admin_a_token))
    assert r.status_code == 200


def test_rotation_rejects_non_admins_unknown_accounts_and_bad_credentials(
    client, db_session, matter_with_users
):
    m = matter_with_users
    target = m["contributor_id"]
    path = f"/api/v1/users/{target}/sign-in-token"

    assert client.post(path, headers=m["reviewer_headers"]).status_code == 403
    assert client.post(path, headers=m["contributor_headers"]).status_code == 403
    assert client.post(path).status_code == 401
    assert client.post(path, headers=token_header("not-a-token")).status_code == 401

    _, admin_token = _admin_with_real_token(client, db_session, m["matter_id"])
    missing = client.post("/api/v1/users/nobody/sign-in-token", headers=token_header(admin_token))
    assert missing.status_code == 404
    # The contributor still signs in with its fixture credential.
    assert client.get("/api/v1/me", headers=m["contributor_headers"]).status_code == 200


# --- every router authenticates through the token -----------------------------


def test_unknown_tokens_are_401_on_every_router(client, db_session, matter_with_users):
    m = matter_with_users
    bad = token_header("definitely-not-a-sign-in-token")
    matter = m["matter_id"]
    assert client.get("/api/v1/me", headers=bad).status_code == 401
    assert client.get("/api/v1/users", headers=bad).status_code == 401
    assert client.get(f"/api/v1/matters/{matter}/members", headers=bad).status_code == 401
    assert client.get("/api/v1/assertions", params={"matter_id": matter}, headers=bad).status_code == 401
    assert client.get("/api/v1/notifications", headers=bad).status_code == 401
    assert client.get(f"/api/v1/matters/{matter}/graph", headers=bad).status_code == 401
    assert client.get(f"/api/v1/matters/{matter}/entities", headers=bad).status_code == 401
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(matter, m["repository_id"]),
        headers=m["contributor_headers"],
    ).json()
    assert client.get(f"/api/v1/assertions/{created['id']}/history", headers=bad).status_code == 401
    assert client.get(f"/api/v1/assertions/{created['id']}/comments", headers=bad).status_code == 401
    assert (
        client.get(f"/api/v1/assertions/{created['id']}/revisions/1/ratings", headers=bad).status_code
        == 401
    )
    assert client.post(f"/api/v1/assertions/{created['id']}/accept", headers=bad).status_code == 401


def test_audit_events_and_notifications_record_the_user_id_not_the_token(
    client, db_session, matter_with_users
):
    m = matter_with_users
    _, admin_token = _admin_with_real_token(client, db_session, m["matter_id"])
    author_id, author_token = _create_account(client, admin_token, "au@example.test", "Author")
    reviewer_id, reviewer_token = _create_account(client, admin_token, "rv@example.test", "Rev")
    _grant(client, admin_token, m["matter_id"], "au@example.test", "contributor")
    _grant(client, admin_token, m["matter_id"], "rv@example.test", "reviewer")

    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"])
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=token_header(author_token),
    )
    assert created.status_code == 201, created.text
    aid = created.json()["id"]
    assert created.json()["author_user_id"] == author_id

    evidence = client.post(
        f"/api/v1/assertions/{aid}/evidence",
        json={"source_span_id": span, "evidence_role": "supports"},
        headers=token_header(author_token),
    )
    assert evidence.status_code == 201, evidence.text
    assert client.post(f"/api/v1/assertions/{aid}/submit", headers=token_header(author_token)).status_code == 200
    rating = client.put(
        f"/api/v1/assertions/{aid}/revisions/1/rating",
        json={"strength": 4, "rationale": "fine"},
        headers=token_header(reviewer_token),
    )
    assert rating.status_code in (200, 201), rating.text
    accepted = client.post(f"/api/v1/assertions/{aid}/accept", headers=token_header(reviewer_token))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["reviewed_by"] == reviewer_id

    actors = {
        e.event_type: e.actor_user_id
        for e in db_session.scalars(select(AuditEvent).where(AuditEvent.assertion_id == aid))
    }
    assert actors["evidence_added"] == author_id
    assert actors["rating_created"] == reviewer_id
    assert set(actors.values()) <= {author_id, reviewer_id}

    notes = client.get("/api/v1/notifications", headers=token_header(author_token)).json()
    accepted_note = next(n for n in notes if n["event_type"] == "assertion_accepted")
    assert accepted_note["actor_user_id"] == reviewer_id
    assert accepted_note["recipient_user_id"] == author_id


def test_bearer_resolution_fails_closed_outside_a_request():
    with pytest.raises(AuthHeaderError):
        get_bearer_user_id("Bearer any-token")
    with pytest.raises(AuthHeaderError):
        get_bearer_user_id(None)


def test_legacy_detection_compares_the_stored_hash_with_the_public_id():
    assert is_legacy_sign_in_hash("u-1", hash_sign_in_token("u-1"))
    assert not is_legacy_sign_in_hash("u-1", hash_sign_in_token("random-token"))
    assert not is_legacy_sign_in_hash("u-1", None)


# --- legacy credentials surface at startup and in the admin listing ----------


def test_startup_logs_a_warning_naming_legacy_sign_ins(app, db_session, caplog):
    first = seed_user(db_session, display_name="Legacy One")
    second = seed_user(db_session, display_name="Legacy Two")

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        with TestClient(app):
            pass
    warnings = [r.getMessage() for r in caplog.records if r.name == "app.auth"]
    assert len(warnings) == 1
    assert "2 user account(s) still sign in with their public user id" in warnings[0]
    assert first in warnings[0] and second in warnings[0]

    for user in db_session.scalars(select(User)):
        user.sign_in_token_hash = hash_sign_in_token(f"rotated-{user.id}")
    db_session.commit()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="app.auth"):
        with TestClient(app):
            pass
    assert [r for r in caplog.records if r.name == "app.auth"] == []


def test_list_users_reports_sign_in_status(client, db_session, matter_with_users):
    m = matter_with_users
    admin_id, admin_token = _admin_with_real_token(client, db_session, m["matter_id"])
    no_token_id = seed_user(db_session, display_name="No Credential")
    db_session.get(User, no_token_id).sign_in_token_hash = None
    db_session.commit()

    rows = {u["id"]: u for u in client.get("/api/v1/users", headers=token_header(admin_token)).json()}
    assert rows[admin_id]["sign_in_status"] == "active"
    assert rows[m["contributor_id"]]["sign_in_status"] == "legacy"
    assert rows[no_token_id]["sign_in_status"] == "none"
    for row in rows.values():
        assert set(row) == {"id", "email", "display_name", "sign_in_status"}


# --- demo seed ---------------------------------------------------------------


def test_demo_seed_accounts_sign_in_with_their_role_names(tmp_path, monkeypatch):
    db_path = tmp_path / "demo.db"
    seeded = _run_module("app.seed_demo", "--db", str(db_path))
    assert seeded.returncode == 0, seeded.stderr

    app = _app_on(db_path, monkeypatch)
    try:
        with TestClient(app) as client:
            for role in ("admin", "reviewer", "contributor", "viewer"):
                me = client.get("/api/v1/me", headers=token_header(role))
                assert me.status_code == 200, (role, me.text)
                assert any(mm["role"] == role for mm in me.json()["matters"])
            assert client.get("/api/v1/me", headers=token_header("owner")).status_code == 401
            listed = client.get("/api/v1/users", headers=token_header("admin")).json()
            assert {u["sign_in_status"] for u in listed} == {"legacy"}
    finally:
        app.state.engine.dispose()


# --- no other response carries a token or a hash ------------------------------


def test_sign_in_tokens_and_hashes_appear_in_no_other_response(
    client, app, db_session, matter_with_users
):
    """Exercise every route and scan every response body and header.

    Each minted token may appear only in the one response that minted it
    (POST /users or the rotate endpoint); no stored hash may appear at all.
    """
    m = matter_with_users
    matter_id = m["matter_id"]
    responses: list[tuple[str, object]] = []
    minted: dict[str, int] = {}  # token -> index of the response that minted it

    def call(method: str, path: str, token: str, **kwargs):
        r = client.request(method, path, headers=token_header(token), **kwargs)
        responses.append((f"{method} {path}", r))
        if r.content and r.headers.get("content-type", "").startswith("application/json"):
            data = r.json()
            if isinstance(data, dict) and "sign_in_token" in data:
                minted[data["sign_in_token"]] = len(responses) - 1
        return r

    admin_id = seed_user(db_session, display_name="Scan Admin", email="scan-admin@example.test")
    seed_matter_role(db_session, user_id=admin_id, matter_id=matter_id, role="admin")
    legacy_hash = hash_sign_in_token(admin_id)
    admin_token = call("POST", f"/api/v1/users/{admin_id}/sign-in-token", admin_id).json()[
        "sign_in_token"
    ]

    people = {}
    for key, role in (("author", "contributor"), ("rater", "contributor"),
                      ("reviewer", "reviewer"), ("viewer", "viewer"), ("spare", "viewer")):
        email = f"{key}@scan.example.test"
        body = call("POST", "/api/v1/users", admin_token,
                    json={"email": email, "display_name": key.title()}).json()
        people[key] = (body["id"], body["sign_in_token"])
        assert call("POST", f"/api/v1/matters/{matter_id}/members", admin_token,
                    json={"email": email, "role": role}).status_code == 201
    author, rater, reviewer, viewer, spare = (people[k] for k in
                                              ("author", "rater", "reviewer", "viewer", "spare"))

    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=matter_id,
                        title="Scan agreement")
    span = seed_source_span(db_session, document_id=doc, matter_id=matter_id,
                            quote_text="Confidentiality shall survive termination.")

    created = call("POST", "/api/v1/assertions", author[1], json=assertion_payload(
        matter_id, m["repository_id"], save_as="proposed",
        evidence=[{"source_span_id": span, "evidence_role": "supports"}]))
    assert created.status_code == 201, created.text
    aid = created.json()["id"]
    # Submitted for review, so a reviewer may dispute it below (a draft takes
    # no review decision: spec "Review decision rules").
    second = call("POST", "/api/v1/assertions", author[1], json=assertion_payload(
        matter_id, m["repository_id"], save_as="proposed",
        proposition="A second, unrelated proposition."))
    assert second.status_code == 201, second.text
    agent = call("POST", "/api/v1/agent/assertions", author[1], json={
        "repository_id": m["repository_id"], "matter_id": matter_id,
        "assertion_type": "SURVIVES_TERMINATION",
        "proposition": "The confidentiality obligation survives termination.",
        "subject_entity": {"type": "Document", "id": doc},
        "evidence": [{"source_span_id": span, "evidence_role": "primary_basis"}],
        "explanation": "Survival sentence.", "agent": {"platform": "scan-test"}, "confidence": 0.5})
    assert agent.status_code == 201, agent.text
    evidence = call("POST", f"/api/v1/assertions/{aid}/evidence", author[1],
                    json={"source_span_id": span, "evidence_role": "qualifies"})
    assert evidence.status_code == 201, evidence.text
    comment = call("POST", f"/api/v1/assertions/{aid}/comments", rater[1],
                   json={"comment_text": "Looks right."})
    assert comment.status_code == 201, comment.text
    assert call("PUT", f"/api/v1/assertions/{aid}/revisions/1/rating", rater[1],
                json={"strength": 4, "rationale": "Clear text."}).status_code in (200, 201)
    assert call("PUT", f"/api/v1/assertions/{aid}/revisions/1/rating", reviewer[1],
                json={"strength": 5, "rationale": None}).status_code in (200, 201)
    assert call("POST", f"/api/v1/assertions/{aid}/accept", reviewer[1]).status_code == 200
    assert call("POST", f"/api/v1/assertions/{second.json()['id']}/dispute",
                reviewer[1]).status_code == 200

    params = {
        "assertion_id": aid,
        "matter_id": matter_id,
        "evidence_id": evidence.json()["id"],
        "comment_id": comment.json()["id"],
        "revision_number": "1",
        "member_user_id": spare[0],
        "target_user_id": spare[0],
    }
    schema_paths = app.openapi()["paths"]
    routes = [(method.upper(), path) for path, ops in schema_paths.items() for method in ops]
    routes += [("GET", p) for p in ("/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect")]

    def concrete(path: str) -> str:
        return re.sub(r"\{(\w+)\}", lambda mt: params.get(mt.group(1), "unknown"), path)

    # Reads first, as several roles; then every mutating route (state changes
    # are fine at this point — they only need to be scanned).
    for method, path in routes:
        if method == "GET":
            for token in (admin_token, author[1], viewer[1]):
                call(method, concrete(path), token, params={"matter_id": matter_id})
    for method, path in routes:
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            call(method, concrete(path), admin_token, json={})

    assert len(responses) > 100
    succeeded = {label for label, r in responses if r.status_code < 300}
    for label in (
        "GET /api/v1/me",
        "GET /api/v1/users",
        f"GET /api/v1/matters/{matter_id}/members",
        f"GET /api/v1/assertions/{aid}",
        f"GET /api/v1/assertions/{aid}/history",
        f"GET /api/v1/assertions/{aid}/comments",
        f"GET /api/v1/assertions/{aid}/revisions/1/ratings",
        "GET /api/v1/notifications",
        "GET /api/v1/assertions",
    ):
        assert label in succeeded, f"{label} never succeeded, so its payload was not scanned"
    hashes = {legacy_hash} | {hash_sign_in_token(token) for token in minted}
    hashes |= {u.sign_in_token_hash for u in db_session.scalars(select(User))
               if u.sign_in_token_hash}
    for index, (label, response) in enumerate(responses):
        blob = response.text + "\n" + "\n".join(f"{k}: {v}" for k, v in response.headers.items())
        for token_hash in hashes:
            assert token_hash not in blob, f"stored hash leaked by {label}"
        for token, minted_at in minted.items():
            if index != minted_at:
                assert token not in blob, f"sign-in token leaked by {label}"
    # Every user-creating response and the rotations minted a token.
    assert len(minted) >= 1 + len(people) + 1
