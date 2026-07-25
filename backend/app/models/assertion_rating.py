"""AssertionRating ORM model (sprint 2026-07-25-collaborative-assertions,
item F1).

Field list per spec §4/§10 PLUS `assertion_revision_id` (ruling R5:
ratings are revision-scoped — one current rating per user per revision;
prior-revision ratings are preserved, never auto-copied). Per R5/the F1
brief, the unique constraint is on (user_id, assertion_revision_id) —
this supersedes the spec §4 (assertion_id, user_id) constraint, since a
user may rate each revision of the same assertion independently. Schema
only — aggregate computation is B2's `app.services.ratings` work.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AssertionRating(Base):
    __tablename__ = "assertion_ratings"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "assertion_revision_id", name="uq_assertion_ratings_user_revision"
        ),
        CheckConstraint("strength BETWEEN 1 AND 5", name="ck_assertion_ratings_strength_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    assertion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=False
    )
    assertion_revision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assertion_revisions.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    strength: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
