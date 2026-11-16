"""Workspace/session surface for the web UI (Consensus UI build-out).

Three gaps the Stitch design exposed, closed here with minimal additive
endpoints (no changes to existing routers):

- ``GET /api/v1/me`` — resolve the caller's identity + matter memberships.
  The UI needs this at sign-in: "signing in" = proving the bearer sign-in
  token resolves to a real user (``app/auth.py``), then learning the
  account's PUBLIC user id and which matters (and roles) it has.
- ``GET /api/v1/matters/{matter_id}/members`` — member roster for a
  matter (any member may view; there is no user-enumeration endpoint
  outside a shared matter). Roster ids are public references, not
  credentials, so showing them to every member is safe.
- Admin role management (``POST``/``PUT``/``DELETE`` members) — powers
  the design's Admin console. Guarded so a matter can never lose its
  last admin (no lockout).

Concurrency (2026-11-16, finding api:24 and new:last-admin-race): adding
a member looks the account up by normalized email
(``app.routers.users.find_users_by_email``), and a request that loses a
race to a concurrent add of the same member gets the sequential 409, not
a 500. The last-admin guard is re-checked inside the demoting or
removing statement itself, so two admins demoting each other at the same
moment cannot both succeed (they used to, every time, leaving the matter
with no admin).

Follows the established per-router conventions: local session/auth
dependencies, no shared deps module, roles from ``matter_roles``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.matter import Matter
from app.models.matter_role import VALID_ROLES, MatterRole
from app.models.repository import Repository
from app.models.user import User
from app.routers.users import find_users_by_email

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
            status_code=422,
            detail=f"role must be one of {', '.join(VALID_ROLES)}",
        )


def _admin_count(session: Session, matter_id: str) -> int:
    rows = session.execute(
        select(MatterRole).where(MatterRole.matter_id == matter_id, MatterRole.role == "admin")
    ).scalars().all()
    return len(rows)


_LAST_ADMIN = "a matter must keep at least one admin"
_ALREADY_MEMBER = "user is already a member of this matter"


def _forbid_removing_last_admin(session: Session, membership: MatterRole) -> None:
    if membership.role == "admin" and _admin_count(session, membership.matter_id) <= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_LAST_ADMIN)


def _unless_last_admin(membership: MatterRole):
    """WHERE clause that lets a demoting/removing statement touch
    ``membership`` only if it is not an admin row or another admin row
    remains on the matter.

    The read-then-write check above can see a stale count when two admins
    demote each other at the same moment. Evaluated inside the UPDATE or
    DELETE, the check runs under the database's write lock (SQLite admits
    one writer at a time), so the second statement sees the first one's
    committed change and matches no row.
    """
    other_admin = exists().where(
        MatterRole.matter_id == membership.matter_id,
        MatterRole.role == "admin",
        MatterRole.id != membership.id,
    )
    return (MatterRole.id == membership.id) & ((MatterRole.role != "admin") | other_admin)


def _membership(session: Session, user_id: str, matter_id: str) -> MatterRole | None:
    return session.execute(
        select(MatterRole).where(MatterRole.user_id == user_id, MatterRole.matter_id == matter_id)
    ).scalar_one_or_none()


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

    # Case-insensitive, whitespace-tolerant (finding api:24 / ui:25).
    matches = find_users_by_email(session, body.email)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no user account with that email",
        )
    if len(matches) > 1:
        # Older accounts that share an address in different letter case
        # (see the m20261116_users_email_unique migration): never guess
        # which person gets access.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "several user accounts share that email address (ignoring letter case); "
                "an operator must give each its own address first"
            ),
        )
    target = matches[0]

    if _membership(session, target.id, matter_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_ALREADY_MEMBER)

    session.add(
        MatterRole(
            id=str(uuid.uuid4()), user_id=target.id, matter_id=matter_id, role=body.role
        )
    )
    try:
        session.commit()
    except IntegrityError:
        # A concurrent request added this member after the check above.
        session.rollback()
        if _membership(session, target.id, matter_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=_ALREADY_MEMBER
            ) from None
        raise
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

    membership = _membership(session, member_user_id, matter_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not a member of this matter"
        )

    if body.role != "admin" and membership.role == "admin":
        _forbid_removing_last_admin(session, membership)
        demoted = session.execute(
            update(MatterRole)
            .where(_unless_last_admin(membership))
            .values(role=body.role)
            .execution_options(synchronize_session=False)
        ).rowcount
        if not demoted:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_LAST_ADMIN)
    else:
        membership.role = body.role
    session.commit()

    target = session.get(User, member_user_id)
    assert target is not None  # FK guarantees the account exists
    return {"user": _serialize_user(target), "role": body.role}


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

    membership = _membership(session, member_user_id, matter_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not a member of this matter"
        )

    _forbid_removing_last_admin(session, membership)

    removed = session.execute(
        delete(MatterRole)
        .where(_unless_last_admin(membership))
        .execution_options(synchronize_session=False)
    ).rowcount
    if not removed:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_LAST_ADMIN)
    session.commit()
