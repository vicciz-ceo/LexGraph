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
that must survive on an already-provisioned production database -- NOT
`Document.jurisdiction`'s fresh-test-only `Base.metadata.create_all()`
shape, which only works for tables that do not exist yet and would fail
against a real, already-provisioned database.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE articles ADD COLUMN heading_breadcrumbs TEXT"))


def downgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE articles DROP COLUMN heading_breadcrumbs"))
