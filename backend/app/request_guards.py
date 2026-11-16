"""Refuse request bodies that carry text no field can store (audit finding
api:20, review persistence:2).

JSON can escape a lone UTF-16 surrogate (``"\\ud800"``), and Python's json
module decodes it -- as it decodes a raw surrogate code unit, which it reads
with "surrogatepass" -- into a str that has no UTF-8 encoding. Such a string
answered 500 wherever it met UTF-8: bound to SQLite, or echoed back in a 422
body (validation errors and several error details repeat the input). No
field of this API can hold one, so a request body that contains one -- in
any value or key, on any route -- is refused with a 422 before routing,
validation or any handler runs, and nothing is written.

The body is read exactly as the JSON parser reads it: Starlette parses with
``json.loads(bytes)``, which accepts UTF-8, UTF-16 and UTF-32, with or
without a byte-order mark. Matching UTF-8 byte patterns instead let the same
surrogate through in UTF-16 or UTF-32 (a 500) and refused valid UTF-16 text
whose bytes happen to look like one (U+A0ED is ED A0 in UTF-16-LE).

Pure ASGI middleware, so it does not depend on where in ``create_app`` it is
registered; ``register_request_guards`` is called from ``app.main``.

It also registers two exception handlers:

* Validation errors (audit finding review:6, review persistence:2): FastAPI's
  422 body echoes the offending input, which a JSON response could not always
  carry, so the 422 itself answered 500. JSON numbers such as ``1e999``,
  ``NaN`` and ``Infinity`` parse to non-finite floats; a value is spelled as
  the string ``"Infinity"``, ``"-Infinity"`` or ``"NaN"``. A body FastAPI
  does not parse as JSON (no JSON content type) is echoed as bytes; bytes
  that are not UTF-8 are spelled with ``\\xNN`` escapes. A string with no
  UTF-8 encoding keeps its other characters and spells the surrogate as
  ``\\uNNNN``. The rest of the body is FastAPI's.
* The exact-duplicate 409 (audit finding ui:5) answers the existing
  assertion's id as data, ``existing_assertion_id``, next to the documented
  ``detail`` text.
"""

from __future__ import annotations

import json
import math
import re

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.duplicates import DuplicateAssertionError

UNPAIRED_SURROGATE_DETAIL = (
    "request body contains an unpaired UTF-16 surrogate (such as \\ud800), "
    "which is not valid Unicode text"
)

# A \uD800-\uDFFF escape; whether it is paired only parsing can tell.
_ESCAPED_SURROGATE = re.compile(r"\\u[dD][89a-fA-F]")
_SURROGATE = re.compile("[\ud800-\udfff]")


def contains_unpaired_surrogate(body: bytes) -> bool:
    """Whether `body`, read as the JSON parser reads it, holds a lone surrogate.

    ``json.loads(bytes)`` picks UTF-8, UTF-16 or UTF-32 with
    ``json.detect_encoding`` and decodes with "surrogatepass", so the body is
    decoded the same way here. A surrogate code unit left in the decoded text
    is unpaired whatever the JSON says; an escaped one needs a parse. A body
    that does not decode is not this guard's business: the route answers it
    (400, or 422 when it is not sent as JSON).
    """
    try:
        text = body.decode(json.detect_encoding(body), "surrogatepass")
    except UnicodeDecodeError:
        return False
    if _SURROGATE.search(text):
        return True
    if not _ESCAPED_SURROGATE.search(text):
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


def json_safe(value):
    """`value` in a form a JSON response can always carry (UTF-8, no NaN).

    A non-finite float becomes its JSON spelling as a string. Bytes become
    text, with ``\\xNN`` for bytes that are not UTF-8. A string or key with
    no UTF-8 encoding (a lone surrogate) spells the surrogate as ``\\uNNNN``;
    every other string is returned unchanged.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, str):
        return value.encode("utf-8", "backslashreplace").decode("utf-8")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "backslashreplace")
    if isinstance(value, dict):
        return {json_safe(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


async def validation_error_response(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's 422 for an invalid request, JSON-safe (review:6, persistence:2).

    `json_safe` also runs before `jsonable_encoder`, which decodes echoed
    bytes as strict UTF-8 and raised on a body that is not UTF-8.
    """
    detail = json_safe(jsonable_encoder(json_safe(exc.errors())))
    return JSONResponse(status_code=422, content={"detail": detail})


async def duplicate_assertion_response(request: Request, exc: DuplicateAssertionError) -> JSONResponse:
    """The exact-duplicate 409 with the existing assertion's id (ui:5)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "existing_assertion_id": exc.existing_assertion_id},
        headers=exc.headers,
    )


def register_request_guards(app: FastAPI) -> None:
    app.add_middleware(UnpairedSurrogateGuard)
    app.add_exception_handler(RequestValidationError, validation_error_response)
    app.add_exception_handler(DuplicateAssertionError, duplicate_assertion_response)
