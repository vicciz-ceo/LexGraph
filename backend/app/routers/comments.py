"""Assertion comment routes (item B3, spec §9 — ASSERTION DISCUSSION AND
RATIONALES).

    POST   /api/v1/assertions/{assertion_id}/comments
    GET    /api/v1/assertions/{assertion_id}/comments
    PATCH  /api/v1/assertions/{assertion_id}/comments/{comment_id}
    DELETE /api/v1/assertions/{assertion_id}/comments/{comment_id}

Matter-scoped: any user holding a `matter_roles` row for the assertion's
matter may read/post comments; a user with no matter role at all (the
"outsider" case) gets 403. Soft-delete: DELETE sets `deleted_at` rather
than removing the row, and the default GET listing excludes soft-deleted
comments. Edit-own-only: only the comment's original author may PATCH or
DELETE it -- no reviewer/admin override, per this item's brief.

Every mutation writes an `audit_events` row via `app.services.audit`
(this track's audit service).

DB access is via a small local dependency reading
`request.app.state.session_factory` (same convention as every other
router in this codebase -- no shared deps module, per sprint-harness
instruction).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.matter_role import MatterRole
from app.services.audit import record_audit_event
from app.services.validation import sanitize_for_storage

router = APIRouter(prefix="/api/v1/assertions", tags=["comments"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


class CommentCreate(BaseModel):
    comment_text: str = Field(min_length=1)
    parent_comment_id: str | None = None


class CommentPatch(BaseModel):
    comment_text: str = Field(min_length=1)


# --- Helpers ------------------------------------------------------------


def _get_assertion_or_404(session: Session, assertion_id: str) -> Assertion:
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assertion not found")
    return assertion


def _require_matter_member(session: Session, user_id: str, matter_id: str) -> str:
    role = session.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no access to matter")
    return role


def _get_comment_or_404(session: Session, assertion_id: str, comment_id: str) -> AssertionComment:
    comment = session.get(AssertionComment, comment_id)
    if comment is None or comment.assertion_id != assertion_id or comment.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="comment not found")
    return comment


def _serialize(c: AssertionComment) -> dict:
    return {
        "id": c.id,
        "assertion_id": c.assertion_id,
        "user_id": c.user_id,
        "parent_comment_id": c.parent_comment_id,
        "comment_text": c.comment_text,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "deleted_at": c.deleted_at,
    }


# --- Routes -------------------------------------------------------------


@router.post("/{assertion_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    assertion_id: str,
    body: CommentCreate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)

    if body.parent_comment_id is not None:
        parent = session.get(AssertionComment, body.parent_comment_id)
        if parent is None or parent.assertion_id != assertion_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="parent comment not found"
            )

    now = _now()
    comment = AssertionComment(
        assertion_id=assertion_id,
        user_id=user_id,
        parent_comment_id=body.parent_comment_id,
        comment_text=sanitize_for_storage(body.comment_text),
        created_at=now,
        updated_at=now,
    )
    session.add(comment)
    session.flush()  # allocate comment.id before it's referenced elsewhere

    record_audit_event(
        session,
        actor_user_id=user_id,
        event_type="comment_created",
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion_id,
    )
    session.commit()
    session.refresh(comment)
    return _serialize(comment)


@router.get("/{assertion_id}/comments")
def list_comments(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    rows = (
        session.execute(
            select(AssertionComment)
            .where(
                AssertionComment.assertion_id == assertion_id,
                AssertionComment.deleted_at.is_(None),
            )
            .order_by(AssertionComment.created_at.asc())
        )
        .scalars()
        .all()
    )
    return [_serialize(c) for c in rows]


@router.patch("/{assertion_id}/comments/{comment_id}")
def update_comment(
    assertion_id: str,
    comment_id: str,
    body: CommentPatch,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    comment = _get_comment_or_404(session, assertion_id, comment_id)

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="can only edit your own comment"
        )

    comment.comment_text = sanitize_for_storage(body.comment_text)
    comment.updated_at = _now()

    record_audit_event(
        session,
        actor_user_id=user_id,
        event_type="comment_updated",
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion_id,
    )
    session.commit()
    session.refresh(comment)
    return _serialize(comment)


@router.delete("/{assertion_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    assertion_id: str,
    comment_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    comment = _get_comment_or_404(session, assertion_id, comment_id)

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="can only delete your own comment"
        )

    comment.deleted_at = _now()

    record_audit_event(
        session,
        actor_user_id=user_id,
        event_type="comment_deleted",
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion_id,
    )
    session.commit()
    return None
