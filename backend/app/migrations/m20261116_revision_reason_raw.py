"""Migration: add `assertion_revisions.revision_reason_raw` (review authoring:5).

From 2026-11-16 an edit's reason is submitted text like any other: capped at
100,000 characters, stored with active markup removed in `revision_reason`,
and kept exactly as the editor sent it in this new nullable column (as a
revision keeps `proposition_raw` next to `proposition`). Revisions saved
before have no raw copy; their stored reason is left exactly as it was.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.migrations import has_column, has_table

MIGRATION_ID = "20261116_revision_reason_raw"


def upgrade(engine: Engine) -> bool:
    """Add the column unless it is already there (idempotent)."""
    with engine.begin() as conn:
        if not has_table(conn, "assertion_revisions") or has_column(
            conn, "assertion_revisions", "revision_reason_raw"
        ):
            return False
        conn.execute(text("ALTER TABLE assertion_revisions ADD COLUMN revision_reason_raw TEXT"))
        return True
