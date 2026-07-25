"""AuditEvent ORM model (sprint 2026-07-25-collaborative-assertions,
item F1).

Exact field list per spec §16 (AUDIT REQUIREMENTS) as concretized in the
sprint log's Data model reference: id, actor_user_id, event_type,
timestamp, repository_id, matter_id, assertion_id, assertion_revision_id,
previous_value, new_value, correlation_id. `assertion_id`/
`assertion_revision_id`/`previous_value`/`new_value`/`correlation_id` are
nullable — spec: "Previous value where appropriate", "New value where
appropriate", and not every audited event (e.g. future non-assertion
events) need reference a specific assertion/revision. Schema only — B3
owns `app.services.audit` (the code that writes these rows).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    assertion_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=True
    )
    assertion_revision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assertion_revisions.id"), nullable=True
    )

    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
