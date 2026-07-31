"""Users API (sprint 2026-07-31-admin-provisioning, item B2).

Access model (ruling R2): listing/creating user accounts requires the
caller to hold the ``admin`` role on >=1 matter — a global "admin
somewhere" gate, NOT scoped to a single matter the way
``workspace.py``'s ``_require_admin`` is. Role grants themselves stay
per-matter via the existing members endpoints; this router only mints
accounts (R3: the user id IS the sign-in credential, so it's surfaced
prominently in the response) and lists them.

Email uniqueness is enforced here at the API layer (ruling R4 — the
``users`` table has no unique constraint; adding one is a schema
migration, out of scope for this sprint). Duplicate caller-chosen id is
grouped with the other input-validation failures (422), not 409 — 409 is
reserved for the duplicate-email case.

Follows workspace.py's per-router conventions: local session/auth
dependencies, no shared deps module, bare-array/bare-object responses
(no envelope).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.matter_role import MatterRole
from app.models.user import User

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


def _serialize_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name}


def _get_user_or_401(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        # The token parsed but names no known account — treat like a bad
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


# --- Routes ------------------------------------------------------------------


@router.get("/users")
def list_users(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    _get_user_or_401(session, user_id)
    _require_admin_somewhere(session, user_id)

    rows = session.execute(select(User).order_by(User.display_name.asc())).scalars().all()
    return [_serialize_user(user) for user in rows]


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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid email"
        )

    display_name = body.display_name.strip()
    if not display_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="display_name must not be blank",
        )

    new_id = body.id.strip() if body.id else str(uuid.uuid4())
    if not new_id or session.get(User, new_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="id must be non-empty and not already in use",
        )

    duplicate_email = session.execute(
        select(User.id).where(User.email == email)
    ).scalar_one_or_none()
    if duplicate_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already in use")

    user = User(id=new_id, email=email, display_name=display_name)
    session.add(user)
    session.commit()
    return _serialize_user(user)
