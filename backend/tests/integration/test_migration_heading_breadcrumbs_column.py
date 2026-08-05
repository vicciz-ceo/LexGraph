"""Regression contract for G9's hand-rolled Article migration.

This deliberately builds the old ``articles`` table with raw SQLite DDL,
rather than ``Base.metadata.create_all()``: the ORM now includes
``heading_breadcrumbs``, while a real database needing this migration does
not.  The migration package's established raw-DDL harness uses the same
shape in ``test_migration_raw_text_columns.py``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from app.definition_links.sections import deserialize_heading_breadcrumbs


_ARTICLE_ID = "pre-g9-article"


@pytest.fixture()
def pre_g9_article_engine(tmp_path):
    """Seed one Article in the exact pre-G9 table shape."""
    engine = create_engine(f"sqlite:///{tmp_path / 'pre_g9_article.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE articles ("
                "id VARCHAR(36) PRIMARY KEY, document_id VARCHAR(36) NOT NULL, "
                "matter_id VARCHAR(36) NOT NULL, source_span_id VARCHAR(36) NOT NULL, "
                "number VARCHAR(64) NOT NULL, heading VARCHAR(1024) NOT NULL, "
                "chapter VARCHAR(1024))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO articles "
                "(id, document_id, matter_id, source_span_id, number, heading, chapter) "
                "VALUES (:id, :document_id, :matter_id, :source_span_id, :number, :heading, "
                ":chapter)"
            ),
            {
                "id": _ARTICLE_ID,
                "document_id": "pre-g9-document",
                "matter_id": "pre-g9-matter",
                "source_span_id": "pre-g9-span",
                "number": "12",
                "heading": "Existing article",
                "chapter": "Existing chapter",
            },
        )
    return engine


def _columns(engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("articles")}


def _column(engine, name: str) -> dict:
    return next(column for column in inspect(engine).get_columns("articles") if column["name"] == name)


def test_heading_breadcrumbs_migration_round_trip_preserves_pre_g9_null_and_safe_default(
    pre_g9_article_engine,
):
    """Execute upgrade -> downgrade -> upgrade on a real pre-G9 SQLite file.

    Historical Article rows intentionally have no breadcrumb data.  Their
    migrated SQL value must therefore remain ``NULL`` and flow through the
    owned deserialization contract as ``()`` on both upgrades.
    """
    from app.migrations.add_heading_breadcrumbs_column import downgrade, upgrade

    engine = pre_g9_article_engine

    upgrade(engine)
    assert "heading_breadcrumbs" in _columns(engine)
    assert _column(engine, "heading_breadcrumbs")["nullable"] is True
    with engine.connect() as conn:
        upgraded = conn.execute(
            text(
                "SELECT id, document_id, matter_id, source_span_id, number, heading, chapter, "
                "heading_breadcrumbs FROM articles WHERE id = :id"
            ),
            {"id": _ARTICLE_ID},
        ).one()
    assert upgraded.heading_breadcrumbs is None
    assert deserialize_heading_breadcrumbs(upgraded.heading_breadcrumbs) == ()

    downgrade(engine)
    assert "heading_breadcrumbs" not in _columns(engine)
    with engine.connect() as conn:
        downgraded = conn.execute(
            text(
                "SELECT id, document_id, matter_id, source_span_id, number, heading, chapter "
                "FROM articles WHERE id = :id"
            ),
            {"id": _ARTICLE_ID},
        ).one()
    assert tuple(downgraded) == (
        _ARTICLE_ID,
        "pre-g9-document",
        "pre-g9-matter",
        "pre-g9-span",
        "12",
        "Existing article",
        "Existing chapter",
    )

    upgrade(engine)
    assert "heading_breadcrumbs" in _columns(engine)
    assert _column(engine, "heading_breadcrumbs")["nullable"] is True
    with engine.connect() as conn:
        reupgraded = conn.execute(
            text("SELECT heading_breadcrumbs FROM articles WHERE id = :id"),
            {"id": _ARTICLE_ID},
        ).one()
    assert reupgraded.heading_breadcrumbs is None
    assert deserialize_heading_breadcrumbs(reupgraded.heading_breadcrumbs) == ()
