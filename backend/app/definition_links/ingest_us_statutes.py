"""US statute dataset ingestion (sprint 2026-08-02-us-state-law, item 5,
gate G6).

Ingests already-parsed row dicts from the `vaquill/open-us-law` HuggingFace
dataset schema (`act_id, citation, state, jurisdiction, section_number,
section_title, text, ...`) -- mirrors `app.definition_links.ingest
.ingest_wiki_law`'s shape (one `Document` per ingested file, one `Article` +
backing `SourceSpan` per section), but the input here is already-parsed row
dicts rather than raw wiki-marker text, so there is no `parse_articles` call:
each row maps directly to one Article.

`jurisdiction` is REQUIRED (keyword-only, no default) -- unlike
`ingest_wiki_law`'s `jurisdiction="IL"` default (which exists only for
Hebrew-test backward compatibility), this is a brand-new function with zero
existing call sites, so there is no backward-compatibility reason to accept
an unvalidated/missing jurisdiction, and gate G5 requires every ingested
document to carry a real, validated jurisdiction from the start.

Idempotency: re-ingesting the same `(repository_id, matter_id, title)` reuses
the existing `Document` row (rather than creating a second one for what is
semantically the same file), and re-ingesting a row whose `section_number`
already has an `Article` under that `Document` reuses the existing
`Article`/`SourceSpan` rather than inserting a duplicate. This dataset's rows
are commit
    keyed by `act_id`, but `act_id` is not itself part of the `Article` schema
(an additive-only surface, per ruling M1) -- `(document_id, section_number)`
is the resumability key instead, since each state file's `section_number`
values are unique within that file.

Error paths (all have RED tests):
  - a row missing (or with `None`) required `"text"` is SKIPPED, not fatal --
    collected into `result["skipped_rows"]` with a reason, every other row in
    the same batch still ingests.
  - an unknown jurisdiction code raises `ValidationError` (same controlled
    vocabulary the API enforces, `app.services.jurisdiction
    .validate_jurisdiction`).
  - an empty `rows` list raises `ValueError` -- never a silent no-op that
    could be mistaken for "ingested, zero sections".
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.document import Document
from app.models.source_span import SourceSpan
from app.services.jurisdiction import validate_jurisdiction


def ingest_us_statute_rows(
    session: Session,
    *,
    repository_id: str,
    matter_id: str,
    title: str,
    rows: list[dict],
    jurisdiction: str,
) -> dict:
    """Ingest already-parsed US statute `rows` into one `Document`, one
    `Article` + backing `SourceSpan` per row.

    Returns `{"document_id": str, "article_ids": list[str],
    "source_span_ids": list[str], "skipped_rows": list[dict]}` --
    `article_ids`/`source_span_ids` are in the same order as the
    successfully-ingested rows appear in `rows`; `skipped_rows` holds
    `{"act_id": ..., "reason": ...}` for every row that failed to ingest
    (never fatal to the rest of the batch).
    """
    validate_jurisdiction(jurisdiction)

    if not rows:
        raise ValueError(
            "ingest_us_statute_rows requires at least one row (got an empty list); "
            "an empty batch must fail loudly, not silently no-op"
        )

    document = session.execute(
        select(Document).where(
            Document.repository_id == repository_id,
            Document.matter_id == matter_id,
            Document.title == title,
        )
    ).scalar_one_or_none()

    if document is None:
        document = Document(
            id=str(uuid.uuid4()),
            repository_id=repository_id,
            matter_id=matter_id,
            title=title,
            jurisdiction=jurisdiction,
        )
        session.add(document)
        session.flush()

    article_ids: list[str] = []
    source_span_ids: list[str] = []
    skipped_rows: list[dict] = []

    for row in rows:
        act_id = row.get("act_id")
        text = row.get("text")
        if not text:
            skipped_rows.append(
                {"act_id": act_id, "reason": "missing required 'text' column"}
            )
            continue

        number = str(row.get("section_number"))

        existing_article = session.execute(
            select(Article).where(
                Article.document_id == document.id,
                Article.number == number,
            )
        ).scalar_one_or_none()

        if existing_article is not None:
            article_ids.append(existing_article.id)
            source_span_ids.append(existing_article.source_span_id)
            continue

        source_span = SourceSpan(
            id=str(uuid.uuid4()),
            document_id=document.id,
            matter_id=matter_id,
            quote_text=text,
        )
        session.add(source_span)
        session.flush()

        article = Article(
            id=str(uuid.uuid4()),
            document_id=document.id,
            matter_id=matter_id,
            source_span_id=source_span.id,
            number=number,
            heading=row.get("section_title") or "",
            chapter=row.get("chapter"),
        )
        session.add(article)
        session.flush()

        article_ids.append(article.id)
        source_span_ids.append(source_span.id)

    session.commit()

    return {
        "document_id": document.id,
        "article_ids": article_ids,
        "source_span_ids": source_span_ids,
        "skipped_rows": skipped_rows,
    }
