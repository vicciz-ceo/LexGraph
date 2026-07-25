"""AssertionComment ORM model (sprint 2026-07-25-collaborative-assertions,
item F1).

Exact field list per spec §9 (ASSERTION DISCUSSION AND RATIONALES):
id, assertion_id, user_id, parent_comment_id, comment_text, created_at,
updated_at, deleted_at. `parent_comment_id` is a nullable self-referential
FK (top-level vs threaded reply); `deleted_at` is nullable (soft-delete
per spec: "Deleted comments should be soft-deleted where audit
requirements apply"). Schema only — B3 owns comment routes/audit calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AssertionComment(Base):
    __tablename__ = "assertion_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assertion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    parent_comment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assertion_comments.id"), nullable=True
    )
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
