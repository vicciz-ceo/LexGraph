"""Definition-linker persistence pipeline (sprint 2026-07-29-definition-links,
item DL8, rulings M2/M5/M7).

Mirrors `app/enrich/pipeline.py::run_enrichment`'s shape and philosophy:
reads real `Article` rows already ingested for a matter (via
`app.definition_links.ingest.ingest_wiki_law`), runs them through the
deterministic Stage 0/2-5 extractor/matcher/derivation-detector, and
writes REAL `Definition` rows plus `Assertion` rows -- never mock objects,
never a model call.

Scoping note: "law-wide" (Stage 1) means scoped to the single law/Document
an article belongs to, not to the whole matter -- Stage 3 matching (and
the article-number lookup for building `USES_DEFINITION` edges) is
therefore run PER DOCUMENT, since a matter may hold several ingested laws
whose articles can share the same bare number (e.g. two laws both having
an article "1").
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.definition_links.derivation import detect_cross_law_derivations, strip_year_suffix
from app.definition_links.extract import (
    DefinitionCandidate,
    extract_adhoc_definitions,
    extract_definitions_from_section,
    extract_local_definitions,
)
from app.definition_links.guards import is_bidi_degraded
from app.definition_links.matcher import link_articles_to_definitions
from app.definition_links.normalize import normalize_for_parsing, strip_wikilinks
from app.definition_links.sections import Article as MatcherArticle
from app.definition_links.sections import is_definitions_heading
from app.models.article import Article
from app.models.assertion import Assertion
from app.models.definition import Definition
from app.models.document import Document
from app.models.matter import Matter
from app.models.repository import Repository
from app.models.source_span import SourceSpan

_ORIGIN = "system_generated"
_STATUS = "proposed"

# Ruling M2's confidence tiering (a range, not a magic number): USES_DEFINITION
# is structural (>= 0.9); DERIVES_FROM_LAW is prose-derived (>= 0.8 resolved,
# strictly lower unresolved).
_USES_DEFINITION_CONFIDENCE = 0.95
_DERIVES_RESOLVED_CONFIDENCE = 0.85
_DERIVES_UNRESOLVED_CONFIDENCE = 0.5

# Stage 1.2's chapter-scoping triggers -- a הגדרות section is chapter-
# scoped only when its own opening line explicitly restricts it (e.g.
# "לענין עבירה -", "בסימן זה -"); otherwise it defaults to law-wide, even
# when the section itself happens to sit under a `==` chapter heading.
_CHAPTER_SCOPE_TRIGGERS = (
    "לענין פרק זה",
    "לענין סימן זה",
    "לענין עבירה",
    "בפרק זה",
    "בסימן זה",
)


class UnknownMatterError(ValueError):
    """Raised when `run_definition_linking` is asked to run over a matter
    (or a matter with no resolvable repository) that does not exist.
    `app/definition_links/cli.py::main` turns this into a clear non-zero
    exit.
    """


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _determine_scope(body_text: str) -> str:
    first_line = next((ln for ln in body_text.splitlines() if ln.strip()), "")
    if any(trigger in first_line for trigger in _CHAPTER_SCOPE_TRIGGERS):
        return "chapter"
    return "law-wide"


def run_definition_linking(
    session: Session, *, matter_id: str, triggered_by_user_id: str
) -> dict:
    """Run one definition-linking pass over `matter_id`'s existing
    (already-ingested) `Article` rows.

    Returns `{"created_assertions": [...], "created_definitions": [...],
    "skipped_degraded_article_ids": [...]}`. An idempotent re-run over
    unchanged articles returns empty `created_*` lists.
    """
    matter = session.get(Matter, matter_id)
    if matter is None:
        raise UnknownMatterError(f"matter '{matter_id}' does not exist")
    repository = session.get(Repository, matter.repository_id)
    if repository is None:
        raise UnknownMatterError(
            f"matter '{matter_id}' has no resolvable repository '{matter.repository_id}'"
        )

    articles_orm = (
        session.execute(select(Article).where(Article.matter_id == matter_id)).scalars().all()
    )

    skipped_degraded_article_ids: list[str] = []
    live_articles: list[tuple[Article, MatcherArticle]] = []
    for art in articles_orm:
        span = session.get(SourceSpan, art.source_span_id)
        raw_body = span.quote_text if span is not None else ""
        if is_bidi_degraded(raw_body):
            skipped_degraded_article_ids.append(art.id)
            continue
        normalized = normalize_for_parsing(raw_body)
        stripped_body, _hints = strip_wikilinks(normalized)
        live_articles.append(
            (art, MatcherArticle(number=art.number, heading=art.heading, body=stripped_body, chapter=art.chapter))
        )

    # Stage 2: extract every DefinitionCandidate, tagged with its owning
    # (ORM) article for provenance/persistence.
    all_candidates: list[tuple[DefinitionCandidate, Article]] = []
    for art, matcher_article in live_articles:
        if is_definitions_heading(art.heading):
            scope = _determine_scope(matcher_article.body)
            for candidate in extract_definitions_from_section(matcher_article.body, scope=scope):
                candidate.source_chapter = art.chapter if scope == "chapter" else None
                all_candidates.append((candidate, art))
        else:
            for candidate in extract_local_definitions(matcher_article.body):
                candidate.source_article_number = art.number
                all_candidates.append((candidate, art))
            for candidate in extract_adhoc_definitions(matcher_article.body):
                candidate.source_article_number = art.number
                all_candidates.append((candidate, art))

    # Persist Definitions -- idempotent: reuse an existing Definition row
    # keyed by (owning article, sorted terms) rather than re-inserting.
    existing_definitions = (
        session.execute(select(Definition).where(Definition.matter_id == matter_id))
        .scalars()
        .all()
    )
    definitions_by_key: dict[tuple[str, tuple[str, ...]], Definition] = {
        (d.article_id, tuple(sorted(d.terms))): d for d in existing_definitions
    }

    now = _now()
    created_definitions: list[dict] = []
    resolved: list[tuple[DefinitionCandidate, Definition, Article]] = []
    for candidate, owning_art in all_candidates:
        key = (owning_art.id, tuple(sorted(candidate.terms)))
        definition_row = definitions_by_key.get(key)
        if definition_row is None:
            definition_row = Definition(
                id=str(uuid.uuid4()),
                document_id=owning_art.document_id,
                matter_id=matter_id,
                article_id=owning_art.id,
                terms=list(candidate.terms),
                definition_text=candidate.definition_text,
                scope=candidate.scope,
                qualifier=candidate.qualifier,
                parent_definition_id=None,
            )
            session.add(definition_row)
            session.flush()
            definitions_by_key[key] = definition_row
            created_definitions.append(
                {"id": definition_row.id, "terms": list(candidate.terms), "scope": candidate.scope}
            )
        resolved.append((candidate, definition_row, owning_art))

    # Existing (system_generated) assertion identity tuples, for
    # idempotent assertion creation.
    existing_assertions = (
        session.execute(
            select(Assertion).where(
                Assertion.matter_id == matter_id, Assertion.origin == _ORIGIN
            )
        )
        .scalars()
        .all()
    )
    existing_keys = {
        (
            a.assertion_type,
            a.subject_entity_type,
            a.subject_entity_id,
            a.object_entity_type,
            a.object_entity_id,
            a.proposition,
        )
        for a in existing_assertions
    }

    created_assertions: list[dict] = []

    def _create_assertion(**fields) -> None:
        key = (
            fields["assertion_type"],
            fields["subject_entity_type"],
            fields["subject_entity_id"],
            fields.get("object_entity_type"),
            fields.get("object_entity_id"),
            fields["proposition"],
        )
        if key in existing_keys:
            return
        existing_keys.add(key)
        assertion = Assertion(
            id=str(uuid.uuid4()),
            organization_id=repository.organization_id,
            repository_id=repository.id,
            matter_id=matter_id,
            assertion_type=fields["assertion_type"],
            proposition=fields["proposition"],
            subject_entity_type=fields["subject_entity_type"],
            subject_entity_id=fields["subject_entity_id"],
            object_entity_type=fields.get("object_entity_type"),
            object_entity_id=fields.get("object_entity_id"),
            origin=_ORIGIN,
            status=_STATUS,
            author_user_id=triggered_by_user_id,
            confidence=fields["confidence"],
            jurisdiction=None,
            effective_from=None,
            effective_to=None,
            created_at=now,
            updated_at=now,
            submitted_at=None,
            reviewed_by=None,
            reviewed_at=None,
            superseded_by_assertion_id=None,
            current_revision_number=1,
        )
        session.add(assertion)
        session.flush()
        created_assertions.append(
            {
                "id": assertion.id,
                "assertion_type": assertion.assertion_type,
                "proposition": assertion.proposition,
                "status": assertion.status,
                "origin": assertion.origin,
            }
        )

    # Stage 3: article -> definition links, grouped per document (a
    # "law-wide" scope is scoped to its own law, not the whole matter).
    candidates_by_document: dict[str, list[tuple[DefinitionCandidate, Definition]]] = defaultdict(
        list
    )
    for candidate, definition_row, owning_art in resolved:
        candidates_by_document[owning_art.document_id].append((candidate, definition_row))

    articles_by_document: dict[str, list[tuple[Article, MatcherArticle]]] = defaultdict(list)
    for art, matcher_article in live_articles:
        articles_by_document[art.document_id].append((art, matcher_article))

    for document_id, doc_articles in articles_by_document.items():
        doc_candidates = candidates_by_document.get(document_id, [])
        if not doc_candidates:
            continue
        term_to_definition: dict[str, Definition] = {}
        for candidate, definition_row in doc_candidates:
            for term in candidate.terms:
                term_to_definition[term] = definition_row
        matcher_arts = [matcher_article for _, matcher_article in doc_articles]

        edges = link_articles_to_definitions([c for c, _ in doc_candidates], matcher_arts)
        for edge in edges:
            definition_row = term_to_definition.get(edge.term)
            # DL11 (cycle 2, G5, ruling M9(a)): resolve by the edge's
            # POSITION within `doc_articles`, not by a `{number: article}`
            # dict -- a document can contain more than one `@ N.` marker
            # sharing the same `N` (poc-run.md §8 Issue 1), so a number-keyed
            # lookup can silently misattribute to the wrong duplicate.
            using_article = (
                doc_articles[edge.article_index][0]
                if 0 <= edge.article_index < len(doc_articles)
                else None
            )
            if definition_row is None or using_article is None:
                continue
            _create_assertion(
                assertion_type="USES_DEFINITION",
                proposition=f'Article {using_article.number} uses the definition of "{edge.term}".',
                subject_entity_type="Article",
                subject_entity_id=using_article.id,
                object_entity_type="Definition",
                object_entity_id=definition_row.id,
                confidence=_USES_DEFINITION_CONFIDENCE,
            )

    # Stage 4: cross-law derivations. `known_law_titles` covers every
    # Document ingested into this matter, keyed by its year-stripped
    # canonical short title.
    documents = (
        session.execute(select(Document).where(Document.matter_id == matter_id)).scalars().all()
    )
    known_law_titles = {strip_year_suffix(doc.title): doc.id for doc in documents}

    for candidate, definition_row, _owning_art in resolved:
        for term in candidate.terms:
            derivation_edges = detect_cross_law_derivations(
                candidate.definition_text, source_term=term, known_law_titles=known_law_titles
            )
            for derivation_edge in derivation_edges:
                resolved_id = derivation_edge.target_law_id
                if resolved_id is not None:
                    object_entity_type: str | None = "Document"
                    object_entity_id: str | None = resolved_id
                    confidence = _DERIVES_RESOLVED_CONFIDENCE
                else:
                    object_entity_type = None
                    object_entity_id = None
                    confidence = _DERIVES_UNRESOLVED_CONFIDENCE
                proposition = (
                    f'"{derivation_edge.source_term}" {derivation_edge.trigger_phrase} '
                    f"{derivation_edge.matched_text}"
                )
                _create_assertion(
                    assertion_type="DERIVES_FROM_LAW",
                    proposition=proposition,
                    subject_entity_type="Definition",
                    subject_entity_id=definition_row.id,
                    object_entity_type=object_entity_type,
                    object_entity_id=object_entity_id,
                    confidence=confidence,
                )

    session.commit()

    return {
        "created_assertions": created_assertions,
        "created_definitions": created_definitions,
        "skipped_degraded_article_ids": skipped_degraded_article_ids,
    }
