"""Per-request audit context (item B3, spec §16).

Spec §16 requires every audit record to carry a "request or correlation
ID". This module gives every HTTP request one: a pure ASGI middleware,
registered via one append-only line in `app.main.create_app()`
(`register_audit_hooks`), binds a fresh server-generated id for the
duration of the request (`app.services.audit.bind_request_correlation_id`)
and returns it in the `X-Request-ID` response header. Every audit row the
request writes -- whichever router, helper or flush hook writes it --
records that id, so the rows of one action can be found together and tied
to the response the client got. The id is never taken from the client: a
caller-supplied `X-Request-ID` would let one request's rows pose as
another's.

History: this middleware used to write `assertion_created`,
`rating_created`/`rating_changed` and `evidence_added`/`evidence_removed`
rows itself, after the response, in a second transaction whose errors were
swallowed -- so a mutation could commit with no audit row, and the rows
lacked the revision and the previous value (finding api:5). Every audited
mutation now records its rows in its own transaction instead
(`app.services.audit`): creation, evidence, submit, withdraw and edits in
`app/routers/assertions.py`, comments in `app/routers/comments.py`, review
decisions in `app/routers/review.py`, rating removal in
`app/routers/ratings.py`, and rating creation/changes by the flush hook in
`app.services.audit`.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.audit import bind_request_correlation_id

#: Response header carrying the request's audit correlation id.
REQUEST_ID_HEADER = "X-Request-ID"


class AuditHookMiddleware:
    """Binds one audit correlation id per HTTP request and echoes it in the
    `X-Request-ID` response header. Never alters the request or the
    response body or status."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        with bind_request_correlation_id() as correlation_id:

            async def send_with_request_id(message: Message) -> None:
                if message["type"] == "http.response.start":
                    message.setdefault("headers", [])  # optional in the ASGI spec
                    MutableHeaders(scope=message)[REQUEST_ID_HEADER] = correlation_id
                await send(message)

            await self.app(scope, receive, send_with_request_id)


def register_audit_hooks(app: FastAPI) -> None:
    """Wire the audit middleware into `app` (called from create_app())."""
    app.add_middleware(AuditHookMiddleware)
