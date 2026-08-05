"""Article-aware wiki-format ingestion (sprint 2026-07-29-definition-links,
item DL7, ruling M4).

Unlike the POC's `build_assertions_db.py` (which only ever creates
whole-document rows), this ingestion creates one `Article` row PER `@ N.`
section, each backed by its own `SourceSpan` row -- so `AssertionEvidence`
can point at it exactly like any other quoted span.

Ruling M4: never import from the POC path (`lexgraph-assertions-db`) at
runtime -- this module ports the `normalize_title`/`WIKILINK_RE` *patterns*
(see `app/definition_links/normalize.py`'s `strip_wikilinks`) into
in-repo, from-scratch code.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.definition_links.sections import parse_articles, serialize_heading_breadcrumbs
from app.models.article import Article
from app.models.document import Document
from app.models.source_span import SourceSpan


def ingest_wiki_law(
    session: Session,
    *,
    repository_id: str,
    matter_id: str,
    title: str,
    wiki_text: str,
    jurisdiction: str = "IL",
) -> dict:
    """Parse `wiki_text` into articles and persist one `Document` row for
    `title`, one `Article` + one backing `SourceSpan` row per parsed
    article.

    `jurisdiction` (sprint 2026-08-02-us-state-law, item 2, gate G1)
    defaults to `"IL"` -- deliberately a DEFAULT, not a required kwarg,
    so every existing Hebrew call site (~20 tests) that calls this
    function with no such kwarg at all keeps working unchanged.

    Returns `{"document_id": str, "article_ids": list[str],
    "source_span_ids": list[str]}` -- the latter two in the same
    left-to-right order the articles appear in `wiki_text`.
    """
    document = Document(
        id=str(uuid.uuid4()),
        repository_id=repository_id,
        matter_id=matter_id,
        title=title,
        jurisdiction=jurisdiction,
    )
    session.add(document)

    article_ids: list[str] = []
    source_span_ids: list[str] = []

    for parsed_article in parse_articles(wiki_text):
        source_span = SourceSpan(
            id=str(uuid.uuid4()),
            document_id=document.id,
            matter_id=matter_id,
            quote_text=parsed_article.body,
        )
        session.add(source_span)

        article = Article(
            id=str(uuid.uuid4()),
            document_id=document.id,
            matter_id=matter_id,
            source_span_id=source_span.id,
            number=parsed_article.number,
            heading=parsed_article.heading,
            chapter=parsed_article.chapter,
            # Item G9-3: threaded exactly parallel to `.chapter` above.
            heading_breadcrumbs=serialize_heading_breadcrumbs(
                parsed_article.heading_breadcrumbs
            ),
        )
        session.add(article)

        article_ids.append(article.id)
        source_span_ids.append(source_span.id)

    session.commit()

    return {
        "document_id": document.id,
        "article_ids": article_ids,
        "source_span_ids": source_span_ids,
    }
