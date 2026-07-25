"""Test-token auth seam.

Declared boundary seam (Planner brief, self-mock ban exceptions) — real,
not mocked. Sprint 2026-07-25-collaborative-assertions ruling R3: in-DB
users + per-matter roles, with a test-friendly token scheme (no external
IdP). The scheme: the bearer token IS the user_id, e.g.
`Authorization: Bearer <user_id>`.

This module only parses the header into a caller identity. It performs NO
database lookup, role resolution, or permission check — those are
Developer-owned business logic (see `services/permissions.py` and each
router), and are gate G8/G9 acceptance targets, not scaffolding.
"""

from __future__ import annotations


class AuthHeaderError(ValueError):
    """Raised when the Authorization header is missing or malformed."""


def get_bearer_user_id(authorization: str | None) -> str:
    """Parse `Authorization: Bearer <user_id>` and return the user_id.

    Raises AuthHeaderError on a missing/malformed/empty header. Callers
    (route dependencies) are expected to translate that into a 401
    response — that translation is Developer wiring, not done here.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthHeaderError("missing or malformed Authorization header")
    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise AuthHeaderError("empty bearer token")
    return token
