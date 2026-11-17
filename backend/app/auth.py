"""Sign-in token authentication.

History: sprint 2026-07-25-collaborative-assertions ruling R3 chose a
test-friendly scheme in which the bearer token WAS the user id. User ids
are public references -- every matter member sees the roster and every
author/reviewer/commenter id -- so that let any member sign in as any
other user, including an admin (findings api:2, ui:0). The scheme is now:

- Every user has a secret sign-in token, generated server-side with
  ``secrets.token_urlsafe(SIGN_IN_TOKEN_BYTES)`` and shown exactly once:
  by ``app.bootstrap``, ``POST /api/v1/users``, the admin-only
  ``POST /api/v1/users/{id}/sign-in-token`` rotate endpoint, or the
  operator CLI ``python -m app.rotate_sign_in_token``.
- Only ``sha256(token)`` (hex) is stored, in the unique, indexed
  ``users.sign_in_token_hash`` column. Tokens and hashes never appear in
  any other API response. A NULL hash means the account has no sign-in
  credential at all.
- ``Authorization: Bearer <token>`` is resolved by hashing the presented
  value and looking the hash up. An unknown token is rejected (401).
- User ids stay plain public references.

Legacy credentials: ``app.migrations.m20261116_sign_in_tokens`` upgrades a
pre-existing database by setting each existing user's hash to
``sha256(user id)``, so existing sign-ins keep working. Such a credential
is known to everyone who can see that id, so it is detected by
``is_legacy_sign_in_hash`` (hash == sha256(id)), logged at startup, shown
as a badge in the admin console, and should be rotated.

Wiring: every router's local ``get_current_user_id`` dependency, and the
notification middleware (``app.notification_hooks``, for the actor of a
mutation), call ``get_bearer_user_id(header)``. The audit middleware only
binds the request's correlation id; it does not resolve the caller. That
function needs the database of the app serving the request, so
``register_auth(app)`` (one line in ``app.main.create_app()``) binds a
request-scoped resolver in a context variable for the duration of every
request. Outside a bound request nothing can be verified, and
``get_bearer_user_id`` fails closed.
"""

from __future__ import annotations

import contextvars
import hashlib
import logging
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger("app.auth")

#: Random bytes behind each sign-in token (token_urlsafe -> 43 characters).
SIGN_IN_TOKEN_BYTES = 32

#: Legacy-credential user ids named in the startup warning before "and N more".
_LEGACY_IDS_LOGGED = 20


class AuthHeaderError(ValueError):
    """Raised when the Authorization header is missing, malformed, or does
    not carry a known sign-in token."""


# --- Token helpers ------------------------------------------------------------


def generate_sign_in_token() -> str:
    """A new random sign-in token. Show it once; store only its hash."""
    return secrets.token_urlsafe(SIGN_IN_TOKEN_BYTES)


def hash_sign_in_token(token: str) -> str:
    """The stored form of a sign-in token: sha256, lowercase hex."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_legacy_sign_in_hash(user_id: str, token_hash: str | None) -> bool:
    """True when the stored credential is the account's public user id.

    That is the state the legacy migration leaves pre-existing accounts
    in (and the demo seed's role-name accounts): anyone who can see the id
    can sign in as the account, so the token should be rotated.
    """
    return token_hash is not None and token_hash == hash_sign_in_token(user_id)


def issue_sign_in_token(user: Any) -> str:
    """Give ``user`` (an ORM ``User``) a fresh token and return it.

    Replaces any previous credential. The caller commits the session and
    shows the returned token exactly once.
    """
    token = generate_sign_in_token()
    user.sign_in_token_hash = hash_sign_in_token(token)
    return token


# --- Header parsing + request-scoped resolution -------------------------------


def parse_bearer_token(authorization: str | None) -> str:
    """Return the raw token from ``Authorization: Bearer <token>``.

    The scheme name is case-insensitive, as HTTP defines it (RFC 9110
    section 11.1): ``bearer <token>`` and ``BEARER <token>`` are read too.
    Raises AuthHeaderError on a missing, malformed, or empty header. It
    does not say whether the token is valid; see ``get_bearer_user_id``.
    """
    scheme, space, token = (authorization or "").partition(" ")
    if not space or scheme.lower() != "bearer":
        raise AuthHeaderError("missing or malformed Authorization header")
    token = token.strip()
    if not token:
        raise AuthHeaderError("empty bearer token")
    return token


class _RequestAuth:
    """Resolves sign-in tokens against one app's database for one request.

    Shared by reference with every task/thread the request spawns, so the
    router dependency and the notification middleware look a token up once
    per request: authentication costs one statement per request.
    """

    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory
        self._cache: dict[str, str | None] = {}

    def resolve(self, token: str) -> str | None:
        token_hash = hash_sign_in_token(token)
        if token_hash in self._cache:
            return self._cache[token_hash]

        from sqlalchemy import select

        from app.models.user import User

        session = self._session_factory()
        try:
            user_id = session.execute(
                select(User.id).where(User.sign_in_token_hash == token_hash)
            ).scalar_one_or_none()
        finally:
            session.close()
        self._cache[token_hash] = user_id
        return user_id


_REQUEST_AUTH: contextvars.ContextVar[_RequestAuth | None] = contextvars.ContextVar(
    "lexgraph_request_auth", default=None
)


def get_bearer_user_id(authorization: str | None) -> str:
    """Resolve ``Authorization: Bearer <sign-in token>`` to a user id.

    Raises AuthHeaderError when the header is missing/malformed/empty, when
    the token belongs to no account, or when called outside a request bound
    by ``register_auth`` (fail closed: nothing can be verified there).
    Callers (route dependencies) translate that into a 401 response.
    """
    token = parse_bearer_token(authorization)
    request_auth = _REQUEST_AUTH.get()
    if request_auth is None:
        raise AuthHeaderError("sign-in tokens can only be verified inside an API request")
    user_id = request_auth.resolve(token)
    if user_id is None:
        raise AuthHeaderError("unknown sign-in token")
    return user_id


class SignInTokenContextMiddleware:
    """Pure ASGI middleware binding the request-scoped token resolver."""

    def __init__(self, app: Any, *, session_factory_source: Any) -> None:
        self.app = app
        self._source = session_factory_source

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        bound = _REQUEST_AUTH.set(_RequestAuth(self._source.state.session_factory))
        try:
            await self.app(scope, receive, send)
        finally:
            _REQUEST_AUTH.reset(bound)


# --- Legacy-credential reporting ---------------------------------------------


def legacy_sign_in_user_ids(session: Any) -> list[str]:
    """Ids of accounts whose sign-in token is still their public user id."""
    from sqlalchemy import select

    from app.models.user import User

    rows = session.execute(select(User.id, User.sign_in_token_hash)).all()
    return [user_id for user_id, token_hash in rows if is_legacy_sign_in_hash(user_id, token_hash)]


def warn_about_legacy_sign_ins(session_factory: Callable[[], Any]) -> int:
    """Log a warning naming how many accounts still use legacy credentials.

    Returns that count. The server calls it only once the startup schema
    check (``app.migrate.ensure_schema_current``) has accepted the database,
    so the ``sign_in_token_hash`` column exists: a database that predates it
    is refused at startup with the ``python -m app.migrate`` command instead.
    """
    session = session_factory()
    try:
        legacy = legacy_sign_in_user_ids(session)
    finally:
        session.close()

    if legacy:
        shown = sorted(legacy)[:_LEGACY_IDS_LOGGED]
        more = len(legacy) - len(shown)
        logger.warning(
            "%d user account(s) still sign in with their public user id (a legacy "
            "credential every matter member can see). Rotate them: Admin -> User "
            "accounts -> Rotate sign-in token, or python -m app.rotate_sign_in_token "
            "--db PATH --user-id ID (--list-legacy lists them all). Affected user ids: %s%s",
            len(legacy),
            ", ".join(shown),
            f" and {more} more" if more else "",
        )
    return len(legacy)


# --- Registration -------------------------------------------------------------


def register_auth(app: Any) -> None:
    """Wire sign-in token resolution into ``app`` (called from create_app()).

    The resolver must wrap every other middleware, because the notification
    middleware resolves the caller after the response. Wrapping the built
    middleware stack keeps it outermost no matter where in create_app() this
    is called or what is added later.

    Also logs the legacy-credential warning at startup. It runs inside the
    app's own lifespan, after the schema check there: querying first would
    make SQLite create a missing database file, and an older database would
    fail on the missing column before the check could name the upgrade.
    """
    build_stack = app.build_middleware_stack

    def build_stack_with_sign_in_tokens():
        return SignInTokenContextMiddleware(build_stack(), session_factory_source=app)

    app.build_middleware_stack = build_stack_with_sign_in_tokens

    lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan_with_legacy_warning(asgi_app):
        async with lifespan(asgi_app) as state:
            warn_about_legacy_sign_ins(app.state.session_factory)
            yield state

    app.router.lifespan_context = lifespan_with_legacy_warning
