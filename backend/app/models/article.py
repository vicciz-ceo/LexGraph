"""Article ORM model (sprint 2026-07-29-definition-links, item DL1, ruling M1).

`articles(id, document_id, matter_id, source_span_id, number, heading,
chapter)` -- an additive schema extension authorized by ruling M1 on top of
the F1-era, otherwise-frozen schema. Every ingested article always gets a
backing `SourceSpan` row (see `app/definition_links/ingest.py`), so
`source_span_id` is NON-NULL -- `AssertionEvidence` can point at an
article's text exactly like any other quoted span, with no schema change
to `source_spans`/`assertion_evidence` needed. Schema only -- no business
logic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    source_span_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_spans.id"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    heading: Mapped[str] = mapped_column(String(1024), nullable=False)
    chapter: Mapped[str | None] = mapped_column(String(1024), nullable=True)
