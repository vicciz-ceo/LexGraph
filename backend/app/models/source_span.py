"""SourceSpan ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`source_spans(id, document_id, matter_id, quote_text)` per the sprint
log's Data model reference. Schema only — no business logic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SourceSpan(Base):
    __tablename__ = "source_spans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    quote_text: Mapped[str] = mapped_column(Text, nullable=False)
