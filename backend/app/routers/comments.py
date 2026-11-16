"""Assertion comment routes (item B3, spec §9 — ASSERTION DISCUSSION AND
RATIONALES).

    POST   /api/v1/assertions/{assertion_id}/comments
    GET    /api/v1/assertions/{assertion_id}/comments
    PATCH  /api/v1/assertions/{assertion_id}/comments/{comment_id}
    DELETE /api/v1/assertions/{assertion_id}/comments/{comment_id}

Matter-scoped and permission-checked (spec §12): reading needs
`assertion:view` (every matter role); posting, editing and deleting need
`assertion:comment` (contributor, reviewer, admin), so a viewer can read
the discussion but not post to it, and a user demoted to viewer can no
longer edit or delete their old comments (finding api:10). A user with no
matter role at all (the "outsider" case) gets 403. Edit-own-only: only the
comment's original author may PATCH or DELETE it -- no reviewer/admin
override, per this item's brief.

Text rules (finding api:25): the length cap is checked on the raw text, and
a comment must still contain non-whitespace text once markup is removed --
blank and markup-only text is rejected with 422 on create and on edit (the
same rule the proposition path applies).

Threads and soft-delete (finding api:25): DELETE sets `deleted_at` rather
than removing the row. A reply must target a live comment on the same
assertion (a deleted parent is a 409 conflict). The GET listing omits
deleted comments, except that a deleted comment which still has a live
reply somewhere below it is returned as a tombstone -- `deleted_at` set,
`comment_text` empty, `comment_text_raw` null -- so every listed reply's
`parent_comment_id` resolves within the listing and no deleted text leaks.

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
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.matter_role import MatterRole
from app.services.audit import record_audit_event
from app.services.permissions import has_permission
from app.services.validation import ValidationError, sanitize_for_storage, validate_text_length

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


# `comment_text` emptiness is checked by `_sanitized_comment_text_or_422`
# (blank once markup is removed), not by a `min_length` constraint: that
# would make pydantic reject a lone surrogate itself, and FastAPI's default
# 422 renderer then crashes (HTTP 500) echoing that input back.


class CommentCreate(BaseModel):
    comment_text: str
    parent_comment_id: str | None = None


class CommentPatch(BaseModel):
    comment_text: str


# --- Helpers ------------------------------------------------------------


def _get_assertion_or_404(session: Session, assertion_id: str) -> Assertion:
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assertion not found")
    return assertion


_PERMISSION_DENIED_DETAIL = {
    "assertion:view": "no access to matter",
    "assertion:comment": "your role in this matter does not permit commenting",
}


def _require_permission(session: Session, user_id: str, matter_id: str, permission: str) -> str:
    role = session.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no access to matter")
    if not has_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=_PERMISSION_DENIED_DETAIL[permission]
        )
    return role


def _sanitized_comment_text_or_422(raw_text: str) -> str:
    """Return the text to store as `comment_text`, or raise a 422.

    Track A, item A8 (issue #2 sub-item, gate G4): the length cap is checked
    against the raw submitted text, before sanitization. A comment must also
    keep some non-whitespace text once markup is removed (finding api:25),
    so blank (`"   "`) and markup-only (`"<script>…</script>"`) comments are
    rejected rather than stored as an empty entry in the discussion.
    """
    try:
        validate_text_length(raw_text, label="comment_text")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        # JSON can escape a lone UTF-16 surrogate ("\ud800") that no UTF-8
        # database can store; the insert used to fail with a 500.
        raw_text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise HTTPException(
            status_code=422, detail="comment_text contains an unpaired surrogate character"
        ) from exc
    sanitized = sanitize_for_storage(raw_text)
    if not sanitized.strip():
        raise HTTPException(
            status_code=422,
            detail="comment_text must contain text other than whitespace or markup",
        )
    return sanitized


def _get_comment_or_404(session: Session, assertion_id: str, comment_id: str) -> AssertionComment:
    comment = session.get(AssertionComment, comment_id)
    if comment is None or comment.assertion_id != assertion_id or comment.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="comment not found")
    return comment


def _serialize(c: AssertionComment, *, tombstone: bool = False) -> dict:
    return {
        "id": c.id,
        "assertion_id": c.assertion_id,
        "user_id": c.user_id,
        "parent_comment_id": c.parent_comment_id,
        # A tombstone keeps its place in the thread but never its text.
        "comment_text": "" if tombstone else c.comment_text,
        # Track A, item A3 (issue #2, gate G1): the author's exact
        # submitted bytes, independent of whatever sanitize_for_storage
        # did to `comment_text` above.
        "comment_text_raw": None if tombstone else c.comment_text_raw,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "deleted_at": c.deleted_at,
    }


def list_visible_comments(session: Session, assertion_id: str) -> list[dict]:
    """Serialize the assertion's discussion as the GET listing returns it.

    Live comments in creation order, plus a redacted tombstone for each
    deleted comment that still has a live reply somewhere below it, so a
    reply never references a parent that is missing from the result. A
    deleted comment with no live replies is omitted. No permission check:
    callers must already have checked `assertion:view` for the matter.
    """
    rows = (
        session.execute(
            select(AssertionComment)
            .where(AssertionComment.assertion_id == assertion_id)
            .order_by(AssertionComment.created_at.asc(), AssertionComment.id.asc())
        )
        .scalars()
        .all()
    )
    by_id = {c.id: c for c in rows}
    has_live_reply: set[str] = set()
    for comment in rows:
        if comment.deleted_at is not None:
            continue
        parent_id = comment.parent_comment_id
        # Walk up until an ancestor already known to have a live reply
        # (its own ancestors were marked then); `has_live_reply` also
        # guards against a malformed parent cycle.
        while parent_id is not None and parent_id in by_id and parent_id not in has_live_reply:
            has_live_reply.add(parent_id)
            parent_id = by_id[parent_id].parent_comment_id
    return [
        _serialize(c, tombstone=c.deleted_at is not None)
        for c in rows
        if c.deleted_at is None or c.id in has_live_reply
    ]


# --- Routes -------------------------------------------------------------


@router.post("/{assertion_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    assertion_id: str,
    body: CommentCreate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_permission(session, user_id, assertion.matter_id, "assertion:comment")
    comment_text = _sanitized_comment_text_or_422(body.comment_text)

    if body.parent_comment_id is not None:
        parent = session.get(AssertionComment, body.parent_comment_id)
        if parent is None or parent.assertion_id != assertion_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="parent comment not found"
            )
        if parent.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="cannot reply to a deleted comment"
            )

    now = _now()
    comment = AssertionComment(
        assertion_id=assertion_id,
        user_id=user_id,
        parent_comment_id=body.parent_comment_id,
        comment_text=comment_text,
        comment_text_raw=body.comment_text,
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
    _require_permission(session, user_id, assertion.matter_id, "assertion:view")
    return list_visible_comments(session, assertion_id)


@router.patch("/{assertion_id}/comments/{comment_id}")
def update_comment(
    assertion_id: str,
    comment_id: str,
    body: CommentPatch,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_permission(session, user_id, assertion.matter_id, "assertion:comment")
    comment = _get_comment_or_404(session, assertion_id, comment_id)

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="can only edit your own comment"
        )

    comment.comment_text = _sanitized_comment_text_or_422(body.comment_text)
    comment.comment_text_raw = body.comment_text
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
    _require_permission(session, user_id, assertion.matter_id, "assertion:comment")
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
