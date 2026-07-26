"""AssertionEvidence ORM model (sprint 2026-07-25-collaborative-assertions,
item F1).

Exact field list per spec §2 (ASSERTION DATA MODEL, evidence join
entity): id, assertion_id, source_span_id, evidence_role,
added_by_user_id, created_at. `evidence_role` validation against the
spec's supported-roles list is Developer route/service logic (B1), not
enforced at the schema layer here. Schema only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AssertionEvidence(Base):
    __tablename__ = "assertion_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assertion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=False
    )
    source_span_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_spans.id"), nullable=False
    )
    evidence_role: Mapped[str] = mapped_column(String(64), nullable=False)
    added_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
