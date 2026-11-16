"""Refuse request bodies that carry text no field can store (audit finding api:20).

JSON can escape a lone UTF-16 surrogate (``"\\ud800"``), and Python's json
module decodes it -- as it decodes the raw bytes ED A0 80 .. ED BF BF, which
it reads with "surrogatepass" -- into a str that has no UTF-8 encoding. Such
a string answered 500 wherever it met UTF-8: bound to SQLite, or echoed back
in a 422 body (validation errors and several error details repeat the
input). No field of this API can hold one, so a request body that contains
one -- in any value or key, on any route -- is refused with a 422 before
routing, validation or any handler runs, and nothing is written.

Pure ASGI middleware, so it does not depend on where in ``create_app`` it is
registered; ``register_request_guards`` is called from ``app.main``.
"""

from __future__ import annotations

import json
import re

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

UNPAIRED_SURROGATE_DETAIL = (
    "request body contains an unpaired UTF-16 surrogate (such as \\ud800), "
    "which is not valid Unicode text"
)

# Raw ED A0..ED BF lead bytes encode surrogates, which valid UTF-8 never contains.
_RAW_SURROGATE = re.compile(rb"\xed[\xa0-\xbf]")
# A \uD800-\uDFFF escape; whether it is paired only parsing can tell.
_ESCAPED_SURROGATE = re.compile(rb"\\u[dD][89a-fA-F]")
_SURROGATE = re.compile("[\ud800-\udfff]")


def contains_unpaired_surrogate(body: bytes) -> bool:
    """Whether `body` would decode to text containing a lone surrogate."""
    if _RAW_SURROGATE.search(body):
        return True
    if not _ESCAPED_SURROGATE.search(body):
        return False  # the common case: no parse needed
    try:
        data = json.loads(body)
    except ValueError:
        return False  # not JSON: the route answers that itself
    pending = [data]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if _SURROGATE.search(item):
                return True
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


class UnpairedSurrogateGuard:
    """Buffer the request body, refuse it with 422 if it carries a lone
    surrogate, otherwise replay it unchanged to the app."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        messages: list[Message] = []
        chunks: list[bytes] = []
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        if body and contains_unpaired_surrogate(body):
            await JSONResponse({"detail": UNPAIRED_SURROGATE_DETAIL}, status_code=422)(scope, receive, send)
            return

        async def replay() -> Message:
            return messages.pop(0) if messages else await receive()

        await self.app(scope, replay, send)


def register_request_guards(app: FastAPI) -> None:
    app.add_middleware(UnpairedSurrogateGuard)
