"""Sprint 2026-07-29-definition-links, item DL1 — additive schema (ruling
M1): new `Article` + `Definition` ORM models, existing tables unchanged.

Schema RED (same shape as the F1-era tests this mirrors, e.g.
`matter_with_users`'s own docstring): `seed_article`/`seed_definition`
(tests/conftest.py) INSERT into `articles`/`definitions` via raw SQL, then
the test reads the row back via a raw SELECT. Until a Developer registers
the matching ORM model classes against `app.db.Base`
(`app/models/article.py`, `app/models/definition.py`, wired into
`app/models/__init__.py`), the seed call itself raises
`sqlalchemy.exc.OperationalError: no such table: articles` / `...:
definitions` -- an UNCAUGHT error at test setup (pytest ERROR), a genuine
missing-schema RED signal, not an import/collection error. This is
deliberately NOT wrapped in `pytest.raises` -- doing so would make "the
table doesn't exist" the test's PASSING condition, which would flip to
FAILING once the Developer builds the schema (a flip-to-red trap).

Column design (documented in `tests/conftest.py`'s seed helpers):
`articles(id, document_id, matter_id, source_span_id, number, heading,
chapter)`; `definitions(id, document_id, matter_id, article_id, terms
[JSON list], definition_text, scope, qualifier, parent_definition_id)`.
"""

from __future__ import annotations

from sqlalchemy import text

from tests.conftest import seed_article, seed_definition, seed_document, seed_source_span


def test_seeding_an_article_row_persists_and_reads_back_via_raw_sql(db_session, matter_with_users):
    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])

    article_id = seed_article(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        source_span_id=span_id,
        number="1",
        heading="הגדרות",
        chapter="פרק א'",
    )

    row = db_session.execute(
        text("SELECT number, heading, chapter, source_span_id FROM articles WHERE id = :id"),
        {"id": article_id},
    ).one()
    assert row.number == "1"
    assert row.heading == "הגדרות"
    assert row.chapter == "פרק א'"
    assert row.source_span_id == span_id


def test_seeding_a_definition_row_persists_and_reads_back_via_raw_sql(db_session, matter_with_users):
    import json

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])
    article_id = seed_article(
        db_session, document_id=doc_id, matter_id=m["matter_id"], source_span_id=span_id
    )

    definition_id = seed_definition(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        article_id=article_id,
        terms=["נכס"],
        definition_text="מקרקעין ומיטלטלין.",
        scope="law-wide",
    )

    row = db_session.execute(
        text("SELECT terms, definition_text, scope FROM definitions WHERE id = :id"),
        {"id": definition_id},
    ).one()
    assert json.loads(row.terms) == ["נכס"]
    assert row.definition_text == "מקרקעין ומיטלטלין."
    assert row.scope == "law-wide"


def test_article_model_is_registered_against_base_metadata_once_implemented(db_session, matter_with_users):
    """Once `app.models.article.Article` exists and is imported by
    `app/models/__init__.py`, `Base.metadata.create_all()` (the `app`
    fixture already calls this) creates the real `articles` table -- so a
    direct ORM insert-and-query round trip must succeed with no raw SQL.
    RED today via ModuleNotFoundError (the model doesn't exist)."""
    from app.models.article import Article

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])

    article = Article(
        document_id=doc_id,
        matter_id=m["matter_id"],
        source_span_id=span_id,
        number="34כד",
        heading="הגדרות",
        chapter="פרק ה'2",
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    fetched = db_session.get(Article, article.id)
    assert fetched is not None
    assert fetched.number == "34כד"
    assert fetched.chapter == "פרק ה'2"


def test_definition_model_stores_multiple_terms_and_nested_parent(db_session, matter_with_users):
    """RED today via ModuleNotFoundError (`app.models.definition` doesn't
    exist). Once implemented: `.terms` round-trips a list of strings
    (Stage 2's multi-term case), and `.parent_definition_id` supports the
    nested sub-definition case (Stage 2's recursive extraction)."""
    from app.models.article import Article
    from app.models.definition import Definition

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])
    article = Article(
        document_id=doc_id, matter_id=m["matter_id"], source_span_id=span_id,
        number="3", heading="הגדרת מונחים",
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    outer = Definition(
        document_id=doc_id,
        matter_id=m["matter_id"],
        article_id=article.id,
        terms=["חומר מחשב", "מחשב", "פלט"],
        definition_text="כהגדרתם בחוק המחשבים",
        scope="law-wide",
    )
    db_session.add(outer)
    db_session.commit()
    db_session.refresh(outer)

    inner = Definition(
        document_id=doc_id,
        matter_id=m["matter_id"],
        article_id=article.id,
        terms=["אדם הניתן לזיהוי"],
        definition_text="מי שניתן לזהותו במאמץ סביר",
        scope="law-wide",
        parent_definition_id=outer.id,
    )
    db_session.add(inner)
    db_session.commit()
    db_session.refresh(inner)

    fetched_outer = db_session.get(Definition, outer.id)
    assert list(fetched_outer.terms) == ["חומר מחשב", "מחשב", "פלט"]

    fetched_inner = db_session.get(Definition, inner.id)
    assert fetched_inner.parent_definition_id == outer.id
