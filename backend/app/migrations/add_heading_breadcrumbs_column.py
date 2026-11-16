"""Reversible migration: add `articles.heading_breadcrumbs` (sprint
2026-08-05-defs-core-follow-on-2, gate G9, item G9-2 -- program-manager
approval on four binding conditions; see this sprint's log "Appendix B --
Planner record: plan6 (G9)",
`docs/sprint/sprints/2026-08-05-defs-core-follow-on-2-log.md`).

Additive, nullable text column -- a JSON-serialized ordered
`[[depth, heading_text], ...]` array (see
`app.definition_links.sections.serialize_heading_breadcrumbs`/
`deserialize_heading_breadcrumbs`) capturing EVERY heading level
`sections.parse_articles` (item G9-1) now accumulates above an article
(chapter, siman, chelek, ...), not just the single `.chapter` field.
`pipeline.py`'s `run_definition_linking` loads `Article` rows via
`select(Article)` and never re-parses raw article text, and no
document-level raw text is persisted anywhere either (`add_raw_text_
columns.py` covers assertion tables only) -- so this column is the only
route from ingest-time capture to pipeline-time consumption. No
backfill: historical rows predate breadcrumb capture entirely, so `NULL`
(== "no breadcrumbs known") is the correct, honest value for every
pre-existing row, exactly like `add_assertion_subject_unit_path_column.py`'s
own `subject_unit_path`.

Same raw-DDL-against-a-plain-`Engine` shape as `add_assertion_subject_
unit_path_column.py`, this sprint's named D-ANCHOR precedent for a column
that must survive on an already-provisioned production database. (When this
was written, `Document.jurisdiction` had no migration and relied on
`Base.metadata.create_all()`, which only works for tables that do not exist
yet; `m20260802_add_document_jurisdiction_column.py` now covers it.)

A database provisioned before 2026-07-29 has no `articles` table at all;
`m20260729_add_definition_link_tables.py` creates it earlier in the same
`python -m app.migrate` run. Called on its own against such a database this
module has nothing to change and returns False.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.migrations import has_column, has_table

MIGRATION_ID = "20260805_add_heading_breadcrumbs_column"


def upgrade(engine: Engine) -> bool:
    """Add the column unless it is already there (idempotent)."""
    with engine.begin() as conn:
        if not has_table(conn, "articles") or has_column(conn, "articles", "heading_breadcrumbs"):
            return False
        conn.execute(text("ALTER TABLE articles ADD COLUMN heading_breadcrumbs TEXT"))
        return True


def downgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        if has_column(conn, "articles", "heading_breadcrumbs"):
            conn.execute(text("ALTER TABLE articles DROP COLUMN heading_breadcrumbs"))
