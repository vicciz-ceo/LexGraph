"""Build genuinely old LexGraph databases for upgrade-path tests.

Each ``tests/fixtures/schema_history/<date>_<change>.sql`` is the exact DDL an
older tree's ``Base.metadata.create_all()`` produced, generated from that
commit's own ORM models (see each file's header). ``build_historical_db``
replays one and seeds a row into every table, using only columns that exist in
every historical schema.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

SCHEMA_HISTORY = Path(__file__).resolve().parent / "fixtures" / "schema_history"
HISTORICAL_SCHEMAS = sorted(path.name for path in SCHEMA_HISTORY.glob("*.sql"))
OLDEST = "2026-07-26_initial.sql"
# What app.bootstrap / app.seed_demo produced from 2026-07-29 to 2026-08-02:
# the "pre-August" workspace of findings api:3 / ops:1.
PRE_AUGUST = "2026-07-29_definition_link_tables.sql"

_NOW = "2026-07-30 10:00:00.000000"
SEED_ROWS: tuple[tuple[str, dict], ...] = (
    ("organizations", {"id": "org-1", "name": "Org"}),
    ("repositories", {"id": "repo-1", "organization_id": "org-1", "name": "Repo"}),
    ("matters", {"id": "matter-1", "repository_id": "repo-1", "name": "Matter"}),
    ("users", {"id": "user-1", "email": "user-1@example.test", "display_name": "User One"}),
    ("matter_roles", {"id": "role-1", "user_id": "user-1", "matter_id": "matter-1", "role": "contributor"}),
    ("documents", {"id": "doc-1", "repository_id": "repo-1", "matter_id": "matter-1", "title": "Act"}),
    ("source_spans", {"id": "span-1", "document_id": "doc-1", "matter_id": "matter-1", "quote_text": "Quoted."}),
    (
        "assertions",
        {
            "id": "assertion-1", "organization_id": "org-1", "repository_id": "repo-1",
            "matter_id": "matter-1", "assertion_type": "INTERPRETS",
            "proposition": "Clause 8.4 limits clause 8.2.", "subject_entity_type": "Provision",
            "subject_entity_id": "p-1", "origin": "user_suggested", "status": "draft",
            "author_user_id": "user-1", "created_at": _NOW, "updated_at": _NOW,
            "current_revision_number": 1,
        },
    ),
    (
        "assertion_revisions",
        {
            "id": "revision-1", "assertion_id": "assertion-1", "revision_number": 1,
            "proposition": "Clause 8.4 limits clause 8.2.", "assertion_type": "INTERPRETS",
            "subject_entity_type": "Provision", "subject_entity_id": "p-1",
            "edited_by_user_id": "user-1", "created_at": _NOW,
        },
    ),
    (
        "assertion_comments",
        {
            "id": "comment-1", "assertion_id": "assertion-1", "user_id": "user-1",
            "comment_text": "Agreed, see 8.4.", "created_at": _NOW, "updated_at": _NOW,
        },
    ),
    (
        "assertion_ratings",
        {
            "id": "rating-1", "organization_id": "org-1", "repository_id": "repo-1",
            "matter_id": "matter-1", "assertion_id": "assertion-1",
            "assertion_revision_id": "revision-1", "user_id": "user-1", "strength": 4,
            "rationale": "Strong textual support.", "created_at": _NOW, "updated_at": _NOW,
        },
    ),
    (
        "assertion_evidence",
        {
            "id": "evidence-1", "assertion_id": "assertion-1", "source_span_id": "span-1",
            "evidence_role": "supports", "added_by_user_id": "user-1", "created_at": _NOW,
        },
    ),
)


def build_historical_db(path: Path, schema: str) -> Path:
    """Replay one historical schema into ``path`` and seed one row per table."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript((SCHEMA_HISTORY / schema).read_text(encoding="utf-8"))
        for table, row in SEED_ROWS:
            columns = ", ".join(row)
            params = ", ".join(f":{name}" for name in row)
            conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({params})", row)
        conn.commit()
    finally:
        conn.close()
    return path


def build_fresh_db(path: Path) -> Path:
    """What create_all() builds today: the target of every upgrade."""
    import app.models  # noqa: F401  (register every mapped table)
    from app.db import Base

    engine = create_engine(f"sqlite:///{path}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    return path


def rows(path: Path, sql: str) -> list[tuple]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()
