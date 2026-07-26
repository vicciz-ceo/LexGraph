"""Reversible migration: add `_raw` text columns (issue #2, gates G1/G3).

Adds `proposition_raw` (assertion_revisions), `comment_text_raw`
(assertion_comments), and `rationale_raw` (assertion_ratings) — the raw,
byte-exact authored text stored alongside each table's existing
(possibly lossy, browser-faithful) sanitized column. `sanitize_for_storage`
itself is untouched by this migration or anything downstream of it; the
new columns are the durable fidelity story, not a weakened sanitizer.

`upgrade` backfills each pre-existing row's new raw column with its
current sanitized value — per issue #2, historical rows predate raw-text
capture, so the sanitized value is the best available approximation, not
a claim that it is byte-exact to what was originally authored.
`downgrade` drops exactly the three columns this migration added and
otherwise leaves the schema/data untouched.

Written as raw DDL against a plain SQLAlchemy `Engine` (no Alembic, no
declarative model import) so it can run standalone against an existing
local SQLite file created by an older version of this app, independent
of whatever the current `Base.metadata` looks like.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

# (table, new raw column, existing sanitized column to backfill from)
_RAW_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("assertion_revisions", "proposition_raw", "proposition"),
    ("assertion_comments", "comment_text_raw", "comment_text"),
    ("assertion_ratings", "rationale_raw", "rationale"),
)


def upgrade(engine: Engine) -> None:
    """Add each `_raw` column and backfill it from its sanitized sibling."""
    with engine.begin() as conn:
        for table, raw_column, source_column in _RAW_COLUMNS:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {raw_column} TEXT"))
            conn.execute(text(f"UPDATE {table} SET {raw_column} = {source_column}"))


def downgrade(engine: Engine) -> None:
    """Drop exactly the three `_raw` columns this migration added."""
    with engine.begin() as conn:
        for table, raw_column, _source_column in _RAW_COLUMNS:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {raw_column}"))
