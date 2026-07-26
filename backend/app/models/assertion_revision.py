"""AssertionRevision ORM model (sprint 2026-07-25-collaborative-assertions,
item F1).

Exact field list per spec §3 (ASSERTION REVISION HISTORY). Nullability
mirrors Assertion: `object_entity_type`/`object_entity_id` may be null for
standalone propositions; `jurisdiction`/`effective_from`/`effective_to`
are optional; `revision_reason` is an optional free-text reason for the
edit. Schema only — no business logic (revision creation is B1 work).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AssertionRevision(Base):
    __tablename__ = "assertion_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assertion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    proposition: Mapped[str] = mapped_column(Text, nullable=False)
    assertion_type: Mapped[str] = mapped_column(String(255), nullable=False)

    subject_entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    object_entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    jurisdiction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
