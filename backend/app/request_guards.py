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

A pure ASGI middleware; ``register_request_guards`` is called from
``app.main``. It answers by itself, so its 422 carries ``X-Request-ID`` only
because ``app.audit_middleware`` keeps the request-id middleware outside
every other one, whatever the registration order (review workflow:6).

It also registers three exception handlers:

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
* A locked database is a JSON 503 with ``Retry-After``. SQLite reports
  "database is locked" (SQLITE_BUSY) when another connection keeps a lock
  past the busy timeout: a COMMIT waiting for a reader, the write lock's
  BEGIN IMMEDIATE (``app.services.write_lock``) waiting for another writer
  under heavy load, a read waiting for a writer that is writing its changes
  out. That OperationalError reached clients as Starlette's plain-text
  "Internal Server Error", although a retry is all it takes. FastAPI runs
  the request's dependency teardown, which closes its session, before a
  handler sees the error, and ``app.db``'s pool hook rolls back what a
  failed COMMIT left open, so the transaction is rolled back and the
  database released by the time the 503 is sent. Every other
  OperationalError is re-raised: the bare 500, as before. The 503 carries
  ``X-Request-ID`` (the audit middleware is outside this handler); the
  bare 500 still does not.
"""

from __future__ import annotations

import json
import logging
import math
import re
import sqlite3

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.audit import request_correlation_id
from app.services.duplicates import DuplicateAssertionError

# Where uvicorn logs the server's errors, so the warning for a 503 shows in its
# format next to the request's access line (app.main logs there too).
logger = logging.getLogger("uvicorn.error")

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


#: Seconds the 503 for a locked database asks a client to wait (Retry-After)
#: before it repeats the request. The server itself has already waited the
#: busy timeout (5 s by default) for the lock.
DATABASE_BUSY_RETRY_AFTER_SECONDS = 1

DATABASE_BUSY_DETAIL = (
    "The database is busy: another connection kept it locked for longer than the server "
    "waits (database is locked), so this request was not completed. Try again in a moment."
)


def is_database_busy(exc: BaseException) -> bool:
    """Whether `exc` is SQLite's "database is locked": SQLITE_BUSY, or one of
    its extended codes, raised when the busy timeout ran out while another
    connection held a lock. Waiting longer can succeed.

    Not SQLITE_LOCKED ("database table is locked": a conflict within one
    connection, which no retry resolves), any other SQLite error, or an error
    of another database driver. An error raised without SQLite's result
    code (a sqlite3 build that does not set it) is judged by its message.
    """
    error = exc.orig if isinstance(exc, DBAPIError) else exc
    if not isinstance(error, sqlite3.OperationalError):
        return False
    code = getattr(error, "sqlite_errorcode", None)
    if code is None:
        return str(error).startswith("database is locked")
    return code & 0xFF == sqlite3.SQLITE_BUSY


async def database_busy_response(request: Request, exc: OperationalError) -> JSONResponse:
    """The 503 for a locked database; any other OperationalError stays the bare 500."""
    if not is_database_busy(exc):
        raise exc  # unhandled, as before: Starlette's error middleware answers it
    logger.warning(
        "%s %s answered 503: the database is locked (X-Request-ID %s)",
        request.method, request.url.path, request_correlation_id(),
    )
    return JSONResponse(
        status_code=503,
        content={"detail": DATABASE_BUSY_DETAIL},
        headers={"Retry-After": str(DATABASE_BUSY_RETRY_AFTER_SECONDS)},
    )


def register_request_guards(app: FastAPI) -> None:
    app.add_middleware(UnpairedSurrogateGuard)
    app.add_exception_handler(RequestValidationError, validation_error_response)
    app.add_exception_handler(DuplicateAssertionError, duplicate_assertion_response)
    app.add_exception_handler(OperationalError, database_busy_response)
