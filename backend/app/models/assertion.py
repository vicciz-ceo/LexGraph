"""Assertion ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

Exact field list per spec §2 (ASSERTION DATA MODEL). Nullability follows
the spec's explicit rules: `object_entity_type`/`object_entity_id` may be
null for standalone propositions; `confidence` is reserved for
machine/rule extraction and is normally null for user-created assertions;
`jurisdiction`/`effective_from`/`effective_to` are optional per the
suggestion payload; `submitted_at`/`reviewed_by`/`reviewed_at` are only
populated once those workflow steps occur;
`superseded_by_assertion_id` is a nullable self-referential FK. Schema
only — no routes/service logic (that is B1/B4/B5 work).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Assertion(Base):
    __tablename__ = "assertions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)

    assertion_type: Mapped[str] = mapped_column(String(255), nullable=False)
    proposition: Mapped[str] = mapped_column(Text, nullable=False)

    subject_entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    object_entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    origin: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    author_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    superseded_by_assertion_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=True
    )
    current_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
