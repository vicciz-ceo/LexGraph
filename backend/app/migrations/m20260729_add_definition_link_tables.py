"""Migration: create the `articles` and `definitions` tables (sprint
2026-07-29-definition-links, ruling M1: additive Article + Definition tables).

The tables shipped on 2026-07-29 (commit 10ab30f) with no migration: only
`Base.metadata.create_all()` created them, which never runs against an
existing database. A workspace provisioned before then answered HTTP 500 on
every endpoint that reads articles (e.g. `GET /api/v1/matters/{id}/entities`),
and `add_heading_breadcrumbs_column` crashed with `no such table: articles`.

The tables are created from a frozen Core snapshot of the 2026-07-29 models,
not from today's ORM classes. Later columns (`articles.heading_breadcrumbs`,
2026-08-05) arrive through their own, later migrations, so this module's
output never drifts when a model changes. New tables are empty, so no data is
touched.
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, ForeignKey, MetaData, String, Table, Text
from sqlalchemy.engine import Engine

from app.migrations import has_table

MIGRATION_ID = "20260729_add_definition_link_tables"

_SNAPSHOT = MetaData()
# Parents referenced by the snapshot's foreign keys. Only their names matter
# (for compiling REFERENCES clauses); they are never created here.
Table("documents", _SNAPSHOT, Column("id", String(36), primary_key=True))
Table("matters", _SNAPSHOT, Column("id", String(36), primary_key=True))
Table("source_spans", _SNAPSHOT, Column("id", String(36), primary_key=True))

_ARTICLES = Table(
    "articles",
    _SNAPSHOT,
    Column("id", String(36), primary_key=True),
    Column("document_id", String(36), ForeignKey("documents.id"), nullable=False),
    Column("matter_id", String(36), ForeignKey("matters.id"), nullable=False),
    Column("source_span_id", String(36), ForeignKey("source_spans.id"), nullable=False),
    Column("number", String(64), nullable=False),
    Column("heading", String(1024), nullable=False),
    Column("chapter", String(1024), nullable=True),
)

_DEFINITIONS = Table(
    "definitions",
    _SNAPSHOT,
    Column("id", String(36), primary_key=True),
    Column("document_id", String(36), ForeignKey("documents.id"), nullable=False),
    Column("matter_id", String(36), ForeignKey("matters.id"), nullable=False),
    Column("article_id", String(36), ForeignKey("articles.id"), nullable=False),
    Column("terms", JSON, nullable=False),
    Column("definition_text", Text, nullable=False),
    Column("scope", String(32), nullable=False),
    Column("qualifier", Text, nullable=True),
    Column("parent_definition_id", String(36), ForeignKey("definitions.id"), nullable=True),
)


def upgrade(engine: Engine) -> bool:
    """Create whichever of the two tables is missing. Returns whether any was."""
    with engine.begin() as conn:
        missing = [table for table in (_ARTICLES, _DEFINITIONS) if not has_table(conn, table.name)]
        for table in missing:
            table.create(conn)
    return bool(missing)


def downgrade(engine: Engine) -> None:
    """Drop both tables, refusing if either holds rows (never silently delete
    ingested articles or definitions)."""
    with engine.begin() as conn:
        for table in (_DEFINITIONS, _ARTICLES):
            if not has_table(conn, table.name):
                continue
            rows = conn.execute(table.select().limit(1)).first()
            if rows is not None:
                raise RuntimeError(f"refusing to drop non-empty table {table.name!r}")
            table.drop(conn)
