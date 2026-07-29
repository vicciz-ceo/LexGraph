"""Sprint 2026-07-29-definition-links, item DL7 — article-aware wiki-format
ingestion (ruling M4).

`app.definition_links.ingest` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

M4: never import from the POC path (`lexgraph-assertions-db`) at runtime;
port `normalize_title`/`WIKILINK_RE` PATTERNS into repo code; this new
article-aware wiki-format parser lives entirely in-repo. Unlike the POC's
`build_assertions_db.py` (which only ever creates whole-document rows), this
ingestion creates one `Article` row PER `@ N.` section, each backed by its
own `SourceSpan` row (so `AssertionEvidence` can point at it exactly like
any other quoted span -- see `tests/unit/test_definition_links_models.py`).

Public API pinned:
- `ingest_wiki_law(session, *, repository_id, matter_id, title, wiki_text)
  -> dict` returns `{"document_id": str, "article_ids": list[str],
  "source_span_ids": list[str]}` (the latter two in the same left-to-right
  order the articles appear in `wiki_text`). Creates one `Document` row for
  `title`, one `Article` + one backing `SourceSpan` row per parsed article.

Uses the vendored fixtures (ruling M3) via the real file on disk -- no
placeholder text.
"""

from __future__ import annotations

import pathlib

from sqlalchemy import select

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_ingest_wiki_law_creates_a_document_and_one_article_per_section(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.models.article import Article
    from app.models.document import Document

    m = matter_with_users
    wiki_text = _read("חוק להגנת רכוש מופקד.wiki")

    result = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=wiki_text,
    )

    document = db_session.get(Document, result["document_id"])
    assert document is not None
    assert document.title == 'חוק להגנת רכוש מופקד, תשכ"ה-1964'

    assert len(result["article_ids"]) == 8  # articles 1-8, see DL3's sections test
    assert len(result["source_span_ids"]) == 8

    articles = (
        db_session.execute(select(Article).where(Article.document_id == result["document_id"]))
        .scalars()
        .all()
    )
    numbers = sorted(a.number for a in articles)
    assert numbers == ["1", "2", "3", "4", "5", "6", "7", "8"]


def test_ingest_wiki_law_backs_each_article_with_its_own_source_span(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.models.article import Article
    from app.models.source_span import SourceSpan

    m = matter_with_users
    wiki_text = _read("חוק להגנת רכוש מופקד.wiki")

    result = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק להגנת רכוש מופקד",
        wiki_text=wiki_text,
    )

    articles = (
        db_session.execute(select(Article).where(Article.document_id == result["document_id"]))
        .scalars()
        .all()
    )
    article_1 = next(a for a in articles if a.number == "1")
    span = db_session.get(SourceSpan, article_1.source_span_id)
    assert span is not None
    assert span.matter_id == m["matter_id"]
    assert "האפוטרופוס הכללי" in span.quote_text


def test_ingest_wiki_law_never_imports_the_poc_build_assertions_db_module():
    """Ruling M4: never import from the POC path at runtime -- static check
    that `app.definition_links.ingest` has no reference to the POC's module
    name anywhere in its source."""
    import ast
    import importlib

    module = importlib.import_module("app.definition_links.ingest")
    source = open(module.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
    assert not any("build_assertions_db" in name for name in imported_names)
    assert not any("lexgraph_assertions_db" in name for name in imported_names)


def test_ingest_wiki_law_is_idempotent_free_of_side_effects_on_a_dry_parse():
    """Parsing the same wiki text twice (independent of persistence) must
    yield the same article count -- a basic determinism sanity check
    reusing the already-pinned `sections.parse_articles` (DL3)."""
    from app.definition_links.sections import parse_articles

    wiki_text = _read("חוק העונשין_excerpt.wiki")
    first = [a.number for a in parse_articles(wiki_text)]
    second = [a.number for a in parse_articles(wiki_text)]
    assert first == second
