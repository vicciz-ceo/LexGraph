"""Document ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`documents(id, repository_id, matter_id, title)` per the sprint log's
Data model reference. Schema only — no business logic.

`jurisdiction` (sprint 2026-08-02-us-state-law, item 2, gate G1/G5):
NOT NULL, defaulting to `"IL"` -- every pre-existing Hebrew document is
implicitly Israeli law. Carries BOTH a Python-side `default` (applied by
SQLAlchemy at flush for ORM-constructed `Document(...)` rows) AND a DB-level
`server_default` (embedded in the `CREATE TABLE` DDL): `tests/conftest.py`'s
`seed_document` helper inserts via raw `text("INSERT INTO documents (id,
repository_id, matter_id, title) VALUES (...)")` -- a fixture this item may
not edit (Planner-owned) -- which bypasses the ORM entirely, so only a
`server_default` keeps that pre-existing raw-SQL insert satisfying the new
NOT NULL constraint. This is an additive column on a table created fresh
via `Base.metadata.create_all()` (no persisted schema/migration to
reconcile -- see `app/db.py`), so no migration module is needed for it.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(
        String(10), nullable=False, default="IL", server_default="IL"
    )
