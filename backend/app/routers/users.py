"""Users API (sprint 2026-07-31-admin-provisioning, item B2; sign-in
tokens 2026-11-16).

Access model (ruling R2): listing/creating user accounts requires the
caller to hold the ``admin`` role on >=1 matter — a global "admin
somewhere" gate, NOT scoped to a single matter the way
``workspace.py``'s ``_require_admin`` is. Role grants themselves stay
per-matter via the existing members endpoints.

Sign-in tokens (superseding the old R3 "the user id IS the credential"):
the user id is a public reference; the credential is a separate random
token (see ``app.auth``). This router is where tokens are minted, and
the only place besides ``app.bootstrap`` and the operator CLI
``app.rotate_sign_in_token`` that ever shows one:

- ``POST /users`` returns the new account's token once
  (``sign_in_token``);
- ``POST /users/{user_id}/sign-in-token`` replaces an account's token and
  returns the new one once. The old token stops working immediately.
  Because the caller learns the new credential, an admin may rotate an
  account only when they are also admin on EVERY matter that account
  belongs to (or it is their own account) — otherwise an admin of one
  matter could take over another matter's members.

``GET /users`` rows carry ``sign_in_status``: ``active`` (a generated
token), ``legacy`` (the token is still the public user id, as left by the
``m20261116_sign_in_tokens`` migration — rotate it), or ``none`` (no
credential). Token hashes are never returned.

Email uniqueness is enforced here at the API layer (ruling R4 — the
``users`` table has no unique constraint on email). Duplicate
caller-chosen id is grouped with the other input-validation failures
(422), not 409 — 409 is reserved for the duplicate-email case.

Follows workspace.py's per-router conventions: local session/auth
dependencies, no shared deps module, bare-array/bare-object responses
(no envelope).
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    AuthHeaderError,
    get_bearer_user_id,
    is_legacy_sign_in_hash,
    issue_sign_in_token,
)
from app.models.matter_role import MatterRole
from app.models.user import User

logger = logging.getLogger("app.routers.users")

router = APIRouter(prefix="/api/v1", tags=["users"])

# Deliberately simple — this is API-layer input validation, not RFC 5322
# parsing; it just needs to reject obviously-malformed input like the
# "not-an-email" case the RED tests pin.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Local dependencies (this router only) ---------------------------------


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user_id(request: Request) -> str:
    try:
        return get_bearer_user_id(request.headers.get("Authorization"))
    except AuthHeaderError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


# --- Request/response schemas ------------------------------------------------


class UserIn(BaseModel):
    email: str
    display_name: str
    id: str | None = None


# --- Helpers ------------------------------------------------------------------


def _sign_in_status(user: User) -> str:
    if user.sign_in_token_hash is None:
        return "none"
    if is_legacy_sign_in_hash(user.id, user.sign_in_token_hash):
        return "legacy"
    return "active"


def _serialize_account(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "sign_in_status": _sign_in_status(user),
    }


def _serialize_issued(user: User, token: str) -> dict:
    """The only response shape that carries a sign-in token (shown once)."""
    return {**_serialize_account(user), "sign_in_token": token}


def _get_user_or_401(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        # The token resolved but its account is gone — treat like a bad
        # credential, not a missing resource (matches workspace.py).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown user")
    return user


def _require_admin_somewhere(session: Session, user_id: str) -> None:
    """R2: any holder of the admin role on >=1 matter, not the current one."""
    admin_row = session.execute(
        select(MatterRole.id).where(MatterRole.user_id == user_id, MatterRole.role == "admin")
    ).first()
    if admin_row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role on at least one matter required",
        )


def _require_can_rotate(session: Session, caller_id: str, target_id: str) -> None:
    """The caller learns the target's new credential, so they must already
    administer every matter the target can act in (or be the target)."""
    if caller_id == target_id:
        return
    target_matters = set(
        session.execute(
            select(MatterRole.matter_id).where(MatterRole.user_id == target_id)
        ).scalars()
    )
    caller_admin_matters = set(
        session.execute(
            select(MatterRole.matter_id).where(
                MatterRole.user_id == caller_id, MatterRole.role == "admin"
            )
        ).scalars()
    )
    if not target_matters <= caller_admin_matters:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "rotating this account's sign-in token requires the admin role on "
                "every matter it belongs to"
            ),
        )


# --- Routes ------------------------------------------------------------------


@router.get("/users")
def list_users(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    _get_user_or_401(session, user_id)
    _require_admin_somewhere(session, user_id)

    rows = session.execute(select(User).order_by(User.display_name.asc())).scalars().all()
    return [_serialize_account(user) for user in rows]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserIn,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    _get_user_or_401(session, user_id)
    _require_admin_somewhere(session, user_id)

    email = body.email.strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=422, detail="invalid email"
        )

    display_name = body.display_name.strip()
    if not display_name:
        raise HTTPException(
            status_code=422,
            detail="display_name must not be blank",
        )

    new_id = body.id.strip() if body.id else str(uuid.uuid4())
    if not new_id or session.get(User, new_id) is not None:
        raise HTTPException(
            status_code=422,
            detail="id must be non-empty and not already in use",
        )

    duplicate_email = session.execute(
        select(User.id).where(User.email == email)
    ).scalar_one_or_none()
    if duplicate_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already in use")

    user = User(id=new_id, email=email, display_name=display_name)
    token = issue_sign_in_token(user)
    session.add(user)
    session.commit()
    logger.info("user %s created by %s", user.id, user_id)
    return _serialize_issued(user, token)


@router.post("/users/{target_user_id}/sign-in-token")
def rotate_sign_in_token(
    target_user_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    _get_user_or_401(session, user_id)
    _require_admin_somewhere(session, user_id)

    target = session.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    _require_can_rotate(session, user_id, target_user_id)

    token = issue_sign_in_token(target)
    session.commit()
    logger.info("sign-in token for user %s rotated by %s", target.id, user_id)
    return _serialize_issued(target, token)
