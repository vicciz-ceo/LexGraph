"""Workspace/session surface for the web UI (Consensus UI build-out).

Three gaps the Stitch design exposed, closed here with minimal additive
endpoints (no changes to existing routers):

- ``GET /api/v1/me`` — resolve the caller's identity + matter memberships.
  The UI needs this at sign-in: the bearer token IS the user id
  (``app/auth.py`` test-token seam), so "signing in" = proving the token
  resolves to a real user, then learning which matters (and roles) the
  account has.
- ``GET /api/v1/matters/{matter_id}/members`` — member roster for a
  matter (any member may view; there is no user-enumeration endpoint
  outside a shared matter).
- Admin role management (``POST``/``PUT``/``DELETE`` members) — powers
  the design's Admin console. Guarded so a matter can never lose its
  last admin (no lockout).

Follows the established per-router conventions: local session/auth
dependencies, no shared deps module, roles from ``matter_roles``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.matter import Matter
from app.models.matter_role import VALID_ROLES, MatterRole
from app.models.repository import Repository
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["workspace"])


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


# --- Request/response schemas ----------------------------------------------


class MemberIn(BaseModel):
    email: str
    role: str


class MemberRoleIn(BaseModel):
    role: str


# --- Helpers ----------------------------------------------------------------


def _serialize_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name}


def _get_user_or_401(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        # The token parsed but names no known account — treat like a bad
        # credential, not a missing resource.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown user")
    return user


def _get_matter_or_404(session: Session, matter_id: str) -> Matter:
    matter = session.get(Matter, matter_id)
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="matter not found")
    return matter


def _role_for(session: Session, user_id: str, matter_id: str) -> str | None:
    return session.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()


def _require_member(session: Session, user_id: str, matter_id: str) -> str:
    role = _role_for(session, user_id, matter_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no access to matter")
    return role


def _require_admin(session: Session, user_id: str, matter_id: str) -> None:
    if _require_member(session, user_id, matter_id) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="matter admin role required"
        )


def _validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {', '.join(VALID_ROLES)}",
        )


def _admin_count(session: Session, matter_id: str) -> int:
    rows = session.execute(
        select(MatterRole).where(MatterRole.matter_id == matter_id, MatterRole.role == "admin")
    ).scalars().all()
    return len(rows)


def _forbid_removing_last_admin(session: Session, membership: MatterRole) -> None:
    if membership.role == "admin" and _admin_count(session, membership.matter_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a matter must keep at least one admin",
        )


# --- Routes ------------------------------------------------------------------


@router.get("/me")
def me(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    user = _get_user_or_401(session, user_id)

    rows = session.execute(
        select(MatterRole, Matter, Repository)
        .join(Matter, MatterRole.matter_id == Matter.id)
        .join(Repository, Matter.repository_id == Repository.id)
        .where(MatterRole.user_id == user_id)
        .order_by(Matter.name.asc())
    ).all()

    return {
        "user": _serialize_user(user),
        "matters": [
            {
                "id": matter.id,
                "name": matter.name,
                "repository_id": matter.repository_id,
                "organization_id": repository.organization_id,
                "role": membership.role,
            }
            for membership, matter, repository in rows
        ],
    }


@router.get("/matters/{matter_id}/members")
def list_members(
    matter_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    _get_user_or_401(session, user_id)
    _get_matter_or_404(session, matter_id)
    _require_member(session, user_id, matter_id)

    rows = session.execute(
        select(MatterRole, User)
        .join(User, MatterRole.user_id == User.id)
        .where(MatterRole.matter_id == matter_id)
        .order_by(User.display_name.asc())
    ).all()
    return [
        {"user": _serialize_user(user), "role": membership.role}
        for membership, user in rows
    ]


@router.post("/matters/{matter_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    matter_id: str,
    body: MemberIn,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    _get_matter_or_404(session, matter_id)
    _require_admin(session, user_id, matter_id)
    _validate_role(body.role)

    target = session.execute(
        select(User).where(User.email == body.email)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no user account with that email",
        )

    existing = session.execute(
        select(MatterRole).where(
            MatterRole.user_id == target.id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user is already a member of this matter",
        )

    session.add(
        MatterRole(
            id=str(uuid.uuid4()), user_id=target.id, matter_id=matter_id, role=body.role
        )
    )
    session.commit()
    return {"user": _serialize_user(target), "role": body.role}


@router.put("/matters/{matter_id}/members/{member_user_id}")
def set_member_role(
    matter_id: str,
    member_user_id: str,
    body: MemberRoleIn,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    _get_matter_or_404(session, matter_id)
    _require_admin(session, user_id, matter_id)
    _validate_role(body.role)

    membership = session.execute(
        select(MatterRole).where(
            MatterRole.user_id == member_user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not a member of this matter"
        )

    if body.role != "admin":
        _forbid_removing_last_admin(session, membership)

    membership.role = body.role
    session.commit()

    target = session.get(User, member_user_id)
    assert target is not None  # FK guarantees the account exists
    return {"user": _serialize_user(target), "role": membership.role}


@router.delete(
    "/matters/{matter_id}/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    matter_id: str,
    member_user_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    _get_matter_or_404(session, matter_id)
    _require_admin(session, user_id, matter_id)

    membership = session.execute(
        select(MatterRole).where(
            MatterRole.user_id == member_user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not a member of this matter"
        )

    _forbid_removing_last_admin(session, membership)

    session.delete(membership)
    session.commit()
