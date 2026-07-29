"""Definition ORM model (sprint 2026-07-29-definition-links, item DL1, ruling M1).

`definitions(id, document_id, matter_id, article_id, terms [JSON list],
definition_text, scope, qualifier, parent_definition_id)` -- an additive
schema extension authorized by ruling M1. `terms` is stored as a JSON-
encoded list of strings (Stage 2's "multi-term single definition" case: one
dash, N terms sharing one definition body) rather than a separate join
table -- a deliberately minimal, additive design for this sprint's scope.
`parent_definition_id` is a nullable self-referential FK supporting Stage
2's recursive nested sub-definition case. Schema only -- no business logic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Definition(Base):
    __tablename__ = "definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    article_id: Mapped[str] = mapped_column(String(36), ForeignKey("articles.id"), nullable=False)

    terms: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    definition_text: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    qualifier: Mapped[str | None] = mapped_column(Text, nullable=True)

    parent_definition_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("definitions.id"), nullable=True
    )
