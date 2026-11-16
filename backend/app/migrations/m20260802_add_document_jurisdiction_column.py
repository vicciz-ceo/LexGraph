"""Migration: add `documents.jurisdiction` (sprint 2026-08-02-us-state-law,
item 2, gates G1/G5).

`app/models/document.py` added the column on 2026-08-02 (commit 7daf286) as
`VARCHAR(10) NOT NULL DEFAULT 'IL'` and relied on `Base.metadata.create_all()`,
which never alters an existing table. Every database provisioned before then
answered HTTP 500 (`no such column: documents.jurisdiction`) on assertion
detail, evidence, and any create or evidence call that resolves a source span.

The column is added exactly as `create_all()` declares it. SQLite fills the
`DEFAULT 'IL'` into every existing row, which is the model's own rule: every
pre-existing (Hebrew) document is Israeli law. The server default also keeps
raw-SQL inserts that omit the column working, as on a fresh database.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.migrations import has_column, has_table

MIGRATION_ID = "20260802_add_document_jurisdiction_column"


def upgrade(engine: Engine) -> bool:
    """Add the column unless it is already there (idempotent)."""
    with engine.begin() as conn:
        if not has_table(conn, "documents") or has_column(conn, "documents", "jurisdiction"):
            return False
        conn.execute(
            text("ALTER TABLE documents ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'IL' NOT NULL")
        )
        return True


def downgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        if has_column(conn, "documents", "jurisdiction"):
            conn.execute(text("ALTER TABLE documents DROP COLUMN jurisdiction"))
