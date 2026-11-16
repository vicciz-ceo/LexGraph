"""Every response carries X-Request-ID, the bare 500 excepted (spec §16;
review workflow:6).

Starlette makes the middleware registered last the outermost one. The
unpaired-surrogate guard was registered after the audit middleware, so its
422 was sent before any request id existed and carried no X-Request-ID,
although spec §16 exempts only the bare 500 of an unhandled error.
`register_audit_hooks` now keeps the audit middleware outermost (inside
Starlette's error middleware) whatever is registered before or after it.
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from starlette.responses import PlainTextResponse

from app.audit_middleware import AuditHookMiddleware, register_audit_hooks
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload

SPOOFED = "chosen-by-the-client"


def _audit_rows(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(AuditEvent))


def test_a_body_the_surrogate_guard_refuses_still_gets_a_request_id(client, db_session, matter_with_users):
    m = matter_with_users
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    ).json()
    before = _audit_rows(db_session)
    bodies = [
        b'{"comment": "\\ud800"}',  # escaped
        b'{"comment": "\xed\xa0\x80"}',  # raw UTF-8 bytes
        '{"comment": "\ud800"}'.encode("utf-16-le", "surrogatepass"),
    ]
    seen = set()
    for headers in (m["reviewer_headers"], {}):  # with and without a credential
        for body in bodies:
            response = client.post(
                f"/api/v1/assertions/{created['id']}/request-revision",
                content=body,
                headers={**headers, "Content-Type": "application/json", "X-Request-ID": SPOOFED},
            )
            assert response.status_code == 422, (headers, body, response.text)
            assert "surrogate" in response.json()["detail"]
            request_id = response.headers.get("x-request-id")
            assert request_id and request_id != SPOOFED, (headers, body, dict(response.headers))
            seen.add(request_id)
    assert len(seen) == 2 * len(bodies)  # a fresh id per request
    assert _audit_rows(db_session) == before  # a refusal writes nothing
    assert client.get(f"/api/v1/assertions/{created['id']}",
                      headers=m["reviewer_headers"]).json()["status"] == "proposed"


def test_a_decision_after_the_guard_is_audited_under_its_request_id(client, matter_with_users):
    """Moving the guard inside the audit middleware keeps the rows of an
    accepted request tied to the id its response carries."""
    m = matter_with_users
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    ).json()
    response = client.post(
        f"/api/v1/assertions/{created['id']}/request-revision",
        content=json.dumps({"comment": "Cite clause 8.2."}).encode(),
        headers={**m["reviewer_headers"], "Content-Type": "application/json", "X-Request-ID": SPOOFED},
    )
    assert response.status_code == 200, response.text
    history = client.get(f"/api/v1/assertions/{created['id']}/history", headers=m["reviewer_headers"]).json()
    decision_rows = [e for e in history if e["correlation_id"] == response.headers["x-request-id"]]
    assert decision_rows, history
    assert all(e["correlation_id"] != SPOOFED for e in history)


def _app_with_a_middleware_registered_after_the_audit_hooks() -> FastAPI:
    app = FastAPI()
    register_audit_hooks(app)

    class AnswersByItself:
        """Answers /refused itself, as the surrogate guard does."""

        def __init__(self, inner):
            self.inner = inner

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http" and scope["path"] == "/refused":
                await PlainTextResponse("refused", status_code=418)(scope, receive, send)
                return
            await self.inner(scope, receive, send)

    app.add_middleware(AnswersByItself)  # Starlette alone would make this one outermost

    @app.get("/ok")
    def ok() -> dict:
        return {"ok": True}

    @app.get("/boom")
    def boom() -> dict:
        raise RuntimeError("unhandled")

    return app


def test_the_request_id_middleware_is_outermost_whatever_the_registration_order():
    app = _app_with_a_middleware_registered_after_the_audit_hooks()
    client = TestClient(app, raise_server_exceptions=False)

    refused = client.get("/refused", headers={"X-Request-ID": SPOOFED})
    assert refused.status_code == 418
    assert refused.headers.get("x-request-id") not in (None, "", SPOOFED)

    ok = client.get("/ok")
    assert ok.status_code == 200 and ok.headers.get("x-request-id")
    assert ok.headers["x-request-id"] != refused.headers["x-request-id"]

    # Spec §16's one exception stays: the bare 500 of an unhandled error,
    # answered by Starlette's error middleware outside every user middleware.
    boom = client.get("/boom")
    assert boom.status_code == 500
    assert "x-request-id" not in boom.headers

    assert [m.cls for m in app.user_middleware][0] is AuditHookMiddleware


def test_create_app_puts_the_request_id_middleware_first(app, client):
    client.get("/healthz")  # builds the middleware stack
    assert [m.cls for m in app.user_middleware][0] is AuditHookMiddleware
