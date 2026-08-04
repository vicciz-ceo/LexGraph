"""Reversible migration: add `assertions.subject_unit_path` (sprint
2026-08-04-defs-core-scope, seam spec v2.2 §6 / v2.4, director ruling
D-ANCHOR final -- Option A: row-level anchor + a structured sub-article
path, no new entity).

Additive, nullable text column -- a serialized `UnitPath` recording the
sub-article granularity a `USES_DEFINITION` assertion's mention resolved
to (see `app/definition_links/pipeline.py`'s `get_mention_unit_paths`
retrieval seam). No backfill: historical rows predate sub-article
anchoring entirely, so `NULL` (== "no sub-article path known") is the
correct, honest value for every pre-existing row, not an approximation.

Same raw-DDL-against-a-plain-`Engine` shape as `add_raw_text_columns.py`,
`add_definition_scope_value_column.py`'s sibling precedent named in the
sprint contract.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE assertions ADD COLUMN subject_unit_path TEXT"))


def downgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE assertions DROP COLUMN subject_unit_path"))
