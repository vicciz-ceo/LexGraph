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
from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.definition_links.derivation import strip_year_suffix
from app.definition_links.extract import DefinitionCandidate
from app.definition_links.guards import is_bidi_degraded
from app.definition_links.matcher import (
    definition_covers_mention,
    link_articles_to_definitions,
    scope_rank,
)
from app.definition_links.normalize import strip_wikilinks
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry
from app.definition_links.rules.registry import ScopeUnit, StructuralContext, UnitStep
from app.definition_links.sections import Article as MatcherArticle
from app.definition_links.sections import deserialize_heading_breadcrumbs
from app.models.article import Article
from app.models.assertion import Assertion
from app.models.definition import Definition
from app.models.document import Document
from app.models.matter import Matter
from app.models.repository import Repository
from app.models.source_span import SourceSpan

_ORIGIN = "system_generated"
_STATUS = "accepted"

# Ruling M2's confidence tiering (a range, not a magic number): USES_DEFINITION
# is structural (>= 0.9); DERIVES_FROM_LAW is prose-derived (>= 0.8 resolved,
# strictly lower unresolved).
_USES_DEFINITION_CONFIDENCE = 0.95
_DERIVES_RESOLVED_CONFIDENCE = 0.85
_DERIVES_UNRESOLVED_CONFIDENCE = 0.5


def _serialize_unit_path(path) -> str:
    """`UnitPath` -> a compact string (`"kind:value>kind:value"`) for
    `Assertion.subject_unit_path` -- the D-ANCHOR retrieval seam's
    storage shape (v2.2 §6 Option A: additive text column, no new
    entity)."""
    return ">".join(f"{step.kind}:{step.value}" for step in path)


def _deserialize_unit_path(serialized: str | None):
    if not serialized:
        return ()
    steps = []
    for chunk in serialized.split(">"):
        kind, _, value = chunk.partition(":")
        steps.append(UnitStep(kind=kind, value=value))
    return tuple(steps)


def get_mention_unit_paths(session: Session, assertion_id: str) -> list:
    """Retrieval seam (director ruling D-ANCHOR, seam spec v2.2 §6 /
    v2.4, Option A -- final): returns every sub-article `UnitPath`
    recorded for a `USES_DEFINITION` assertion's own mention. Today, at
    most one entry (the mention that first created this row -- Stage 3's
    existing dedup key is unaffected by this sprint, so a later,
    duplicate-keyed mention's own path is not separately retained).

    This is the STABLE contract a consumer reads through -- whatever the
    eventual storage shape (an additive column today; a possible `Unit`
    entity later, per D-ANCHOR's own explicit "later-phase possibility"),
    never a raw column name/type a consumer should depend on directly.
    """
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        return []
    return [_deserialize_unit_path(assertion.subject_unit_path)]


def _article_by_number(doc_articles, number: str) -> Article | None:
    """First `Article` ORM row in `doc_articles` (a same-document
    `[(Article, MatcherArticle), ...]` list) whose `.number == number` --
    used ONLY for resolving a pointer definition's internal (same-law)
    target (seam spec v2.1 §4), a generic same-document lookup, not a
    jurisdiction-specific one."""
    for art, _ in doc_articles:
        if art.number == number:
            return art
    return None


class UnknownMatterError(ValueError):
    """Raised when `run_definition_linking` is asked to run over a matter
    (or a matter with no resolvable repository) that does not exist.
    `app/definition_links/cli.py::main` turns this into a clear non-zero
    exit.
    """


def _now() -> datetime:
    return datetime.now(timezone.utc)


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

    # Per-document jurisdiction lookup: a matter may legitimately mix
    # jurisdictions (e.g. an Israeli law and a Delaware statute side by
    # side), so every assertion must be stamped from the jurisdiction of
    # the Document its owning Article belongs to -- never a single
    # matter-wide value.
    document_jurisdictions: dict[str, str] = {
        doc.id: doc.jurisdiction
        for doc in session.execute(
            select(Document).where(Document.matter_id == matter_id)
        )
        .scalars()
        .all()
    }

    # Per-document jurisdiction-profile dispatch (sprint 2026-08-02-us-state-law,
    # item 3, gates G2-G4): Stages 2-4 resolve `get_profile(document.jurisdiction)`
    # PER DOCUMENT rather than calling the bare Hebrew `sections`/`extract`/
    # `matcher`/`derivation` functions directly -- a matter may hold documents
    # from more than one jurisdiction side by side. `HebrewProfile` (the "IL"
    # profile) is a pass-through to those exact, unchanged functions, so
    # routing Hebrew through this dispatch is a no-op -- proven by the full
    # Hebrew suite, not merely assumed (ruling R2/gate G1). Falls back to
    # `"IL"` only for the defensive case of a document row that vanished from
    # `document_jurisdictions` between the two queries above (matches
    # `Document.jurisdiction`'s own NOT NULL default).
    profile_cache: dict[str, object] = {}

    def _profile_for_document(document_id: str):
        code = document_jurisdictions.get(document_id, "IL")
        profile = profile_cache.get(code)
        if profile is None:
            profile = get_profile(code)
            profile_cache[code] = profile
        return profile

    skipped_degraded_article_ids: list[str] = []
    live_articles: list[tuple[Article, MatcherArticle]] = []
    for art in articles_orm:
        span = session.get(SourceSpan, art.source_span_id)
        raw_body = span.quote_text if span is not None else ""
        if is_bidi_degraded(raw_body):
            skipped_degraded_article_ids.append(art.id)
            continue
        profile = _profile_for_document(art.document_id)
        normalized = profile.normalize_for_parsing(raw_body)
        stripped_body, _hints = strip_wikilinks(normalized)

        # Sprint 2026-08-04-defs-core-dispatch, item I4 (manager ruling
        # M-D1): article-metadata enrichment. This is THE population call
        # site (a pipeline pre-stage, the Developer's own choice over
        # parse-time enrichment in sections.py -- both jurisdictions'
        # articles converge into a `MatcherArticle` right HERE regardless
        # of whether they were wiki- or parquet-sourced, so this is the one
        # place a per-document jurisdiction dispatch can reach both; a
        # parse-time hook in sections.py could only ever serve the
        # wiki-sourced side). Core stamps a container unit for this
        # article's own chapter unconditionally (mirrors the existing
        # dedicated `.chapter` field, for consistency with the generic
        # containment path -- see matcher._in_scope's dedicated "chapter"
        # branch, which never actually reads this generic tuple); every
        # registered StructuralUnitRule for this document's jurisdiction
        # code ADDS to that set, never replaces it (union). Sprint
        # 2026-08-05-defs-core-follow-on-2, item G9-4: `heading_breadcrumbs`
        # now reads the per-article value items G9-1/G9-2/G9-3 captured at
        # parse/ingest time (`art.heading_breadcrumbs`, the new additive
        # `Article` column), deserialized back into `tuple[tuple[int,
        # str], ...]`. Deliberately GENERIC -- this read does not care
        # whether the column was populated from wiki/Hebrew ingestion or
        # (a future gate's own work, not built here) US/parquet ingestion;
        # it defaults to `()` whenever the column is null/absent (a
        # pre-G9 row, or a jurisdiction this gate does not populate it
        # for), preserving the exact safe default the seam spec already
        # promises.
        structural_ctx = StructuralContext(
            article_number=art.number,
            heading_breadcrumbs=deserialize_heading_breadcrumbs(art.heading_breadcrumbs),
        )
        structural_units = (ScopeUnit(kind="chapter", value=art.chapter),) + tuple(
            unit
            for rule in registry.structural_unit_rules_for(profile.code)
            for unit in rule.derive(structural_ctx)
        )

        live_articles.append(
            (
                art,
                MatcherArticle(
                    number=art.number,
                    heading=art.heading,
                    body=stripped_body,
                    chapter=art.chapter,
                    structural_units=structural_units,
                ),
            )
        )

    # Stage 2: extract every DefinitionCandidate, tagged with its owning
    # (ORM) article for provenance/persistence.
    all_candidates: list[tuple[DefinitionCandidate, Article]] = []
    for art, matcher_article in live_articles:
        profile = _profile_for_document(art.document_id)
        is_definitions_section = profile.is_definitions_heading(art.heading, matcher_article.body)

        # Wave 6 (ruling R12): CA/IL/GA leave a bare placeholder in
        # `section_title` (`Article.heading`), so the check above always
        # returns False for them even when the article genuinely IS a
        # Definitions section -- try deriving the real heading from the
        # body instead (`profile.derive_heading_from_body`, C2/C3: moved
        # behind the profile seam; `HebrewProfile`'s own implementation is
        # always `None`, so this is naturally a no-op for Hebrew with no
        # jurisdiction-code check needed here). This ordering means the
        # derivation attempt only ever runs for an article that was
        # ALREADY going to fall through to the ordinary-article path
        # below -- a heading that already matched the ordinary check is
        # completely untouched, so the 7 states already working off
        # `section_title` are byte-for-byte unaffected.
        used_body_derived_heading = False
        if not is_definitions_section:
            derived_heading = profile.derive_heading_from_body(art.heading, matcher_article.body)
            if derived_heading is not None and profile.is_definitions_heading(
                derived_heading, matcher_article.body
            ):
                is_definitions_section = True
                used_body_derived_heading = True

        if is_definitions_section:
            # G8: body-derived headings can also contain ordinary local-scope
            # definitions.  Keep the registered local candidates first, then
            # add only non-colliding section candidates so a later, broader
            # section candidate cannot reach persistence or Stage 3.
            local_candidate_keys: set[tuple[str, ...]] = set()
            if used_body_derived_heading:
                for candidate in profile.extract_local_scope_definitions(
                    matcher_article.body, article_number=art.number, chapter=art.chapter
                ):
                    candidate_key = tuple(sorted(candidate.terms))
                    if candidate_key in local_candidate_keys:
                        continue
                    local_candidate_keys.add(candidate_key)
                    all_candidates.append((candidate, art))

            scope = profile.determine_scope(matcher_article.body)
            section_candidates = profile.extract_definitions_from_section(
                matcher_article.body, scope=scope, heading_was_derived=used_body_derived_heading
            )
            # G6 (sprint 2026-08-05-defs-core-follow-on-2, seam v2.8 §4):
            # `determine_scope_assignments` replaces the old bare
            # `candidate.source_chapter = art.chapter if scope == "chapter"
            # else None` stamping line -- fan out ONE `DefinitionCandidate`
            # copy per returned `ScopeAssignment` (1 assignment, the
            # article's own chapter/law-wide default, in the overwhelming
            # common case -- byte-identical to today; >1 only for a body
            # naming more than one co-equal scope at once, e.g. TN's "this
            # part and Section 6-51-301", resolved by the already-shipped
            # M10 tie class, not a new mechanism here).
            assignments = profile.determine_scope_assignments(
                matcher_article.body,
                scope=scope,
                article_number=art.number,
                chapter=art.chapter,
            )
            for candidate in section_candidates:
                if used_body_derived_heading:
                    candidate_key = tuple(sorted(candidate.terms))
                    if candidate_key in local_candidate_keys:
                        continue
                    local_candidate_keys.add(candidate_key)
                for assignment in assignments:
                    stamped = replace(candidate, scope=assignment.kind)
                    if assignment.kind == "chapter":
                        stamped.source_chapter = assignment.value
                    elif assignment.kind == "local":
                        stamped.source_article_number = assignment.value
                    else:
                        stamped.scope_value = assignment.value
                    all_candidates.append((stamped, art))
        else:
            for candidate in profile.extract_local_scope_definitions(
                matcher_article.body, article_number=art.number, chapter=art.chapter
            ):
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
            subject_unit_path=fields.get("subject_unit_path"),
            origin=_ORIGIN,
            status=_STATUS,
            author_user_id=triggered_by_user_id,
            confidence=fields["confidence"],
            jurisdiction=fields["jurisdiction"],
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
        # Sprint 2026-08-04-defs-core-scope, seam spec's attribution fix
        # (v2.1, generalized by v2.2 §3's "narrowest governs = longest
        # matching prefix"): group by TERM, not a flat last-write-wins
        # `{term: Definition}` dict -- today's dict collapses every
        # Definition row sharing a bare term string into ONE entry per
        # document, a latent bug for chapter-scoped Hebrew dupes made
        # COMMON by subsection/enumerated scoping (the same term name
        # routinely redefined per-article/per-subsection in real US
        # statutes). Each edge below is re-resolved against EVERY
        # candidate sharing its term, not just whichever was seen last.
        candidates_by_term: dict[str, list[tuple[DefinitionCandidate, Definition]]] = defaultdict(
            list
        )
        for candidate, definition_row in doc_candidates:
            for term in candidate.terms:
                candidates_by_term[term].append((candidate, definition_row))
        matcher_arts = [matcher_article for _, matcher_article in doc_articles]
        profile = _profile_for_document(document_id)

        edges = link_articles_to_definitions(
            [c for c, _ in doc_candidates],
            matcher_arts,
            profile=profile,
        )
        for edge in edges:
            # DL11 (cycle 2, G5, ruling M9(a)): resolve by the edge's
            # POSITION within `doc_articles`, not by a `{number: article}`
            # dict -- a document can contain more than one `@ N.` marker
            # sharing the same `N` (poc-run.md §8 Issue 1), so a number-keyed
            # lookup can silently misattribute to the wrong duplicate.
            using_article_pair = (
                doc_articles[edge.article_index]
                if 0 <= edge.article_index < len(doc_articles)
                else None
            )
            if using_article_pair is None:
                continue
            using_article, using_matcher_article = using_article_pair

            # Narrowest-governs precedence (director ruling, seam spec
            # v2.2 §3): collect every candidate definition sharing this
            # edge's term that genuinely covers THIS mention's own
            # article+position; keep only those at the MINIMUM (narrowest)
            # scope rank. Equal-rank ties ALL survive -- deliberate,
            # zero-miss-safe (ruling M10), pinned live by
            # `test_two_same_rank_local_scoped_definitions_that_tie_both_
            # get_a_uses_definition_assertion_live`.
            covering = [
                (definition_row, scope_rank(candidate.scope))
                for candidate, definition_row in candidates_by_term.get(edge.term, [])
                if definition_covers_mention(
                    candidate, using_matcher_article, edge.char_offset, profile=profile
                )
            ]
            if not covering:
                continue
            min_rank = min(rank for _, rank in covering)
            seen_definition_ids: set[str] = set()
            governing_definitions: list[Definition] = []
            for definition_row, rank in covering:
                if rank != min_rank or definition_row.id in seen_definition_ids:
                    continue
                seen_definition_ids.add(definition_row.id)
                governing_definitions.append(definition_row)

            # D-ANCHOR (director ruling, final -- seam spec v2.2 §6/v2.4,
            # Option A): the mention's own sub-article `UnitPath`, stored
            # alongside the (unchanged-shape) whole-Article-subject
            # assertion -- a retrieval seam (`get_mention_unit_paths`),
            # never a storage-shape commitment a consumer should depend on.
            mention_unit_path = profile.resolve_unit_path(
                using_matcher_article, char_offset=edge.char_offset
            )
            serialized_unit_path = _serialize_unit_path(mention_unit_path) or None

            for definition_row in governing_definitions:
                _create_assertion(
                    assertion_type="USES_DEFINITION",
                    proposition=(
                        f'Article {using_article.number} uses the definition of "{edge.term}".'
                    ),
                    subject_entity_type="Article",
                    subject_entity_id=using_article.id,
                    object_entity_type="Definition",
                    object_entity_id=definition_row.id,
                    confidence=_USES_DEFINITION_CONFIDENCE,
                    jurisdiction=document_jurisdictions.get(using_article.document_id),
                    subject_unit_path=serialized_unit_path,
                )

    # Stage 4: cross-law derivations. `known_law_titles` covers every
    # Document ingested into this matter, keyed by its year-stripped
    # canonical short title.
    documents = (
        session.execute(select(Document).where(Document.matter_id == matter_id)).scalars().all()
    )
    known_law_titles = {strip_year_suffix(doc.title): doc.id for doc in documents}

    for candidate, definition_row, owning_art in resolved:
        profile = _profile_for_document(owning_art.document_id)
        for term in candidate.terms:
            derivation_edges = profile.detect_cross_law_derivations(
                candidate.definition_text, source_term=term, known_law_titles=known_law_titles
            )
            for derivation_edge in derivation_edges:
                # Pointer definitions, internal (same-law) targets (seam
                # spec v2.1 §4, director ruling -- no persisted pointer
                # field, ever; a consumer determines pointer-ness only by
                # checking whether a DERIVES_FROM_LAW assertion exists
                # with subject_entity_id equal to the Definition's own
                # id). `internal_article_number` (set only for a
                # whole-definition pointer whose trigger+citation match
                # consumed the ENTIRE definition_text) redirects to an
                # Article-targeted edge in the SAME document, resolved
                # the same way Stage 3 already resolves same-document
                # article numbers -- reusing DERIVES_FROM_LAW UNCHANGED
                # as an assertion type (verified, not a new entity-type
                # vocabulary concept).
                internal_article_number = getattr(
                    derivation_edge, "internal_article_number", None
                )
                if internal_article_number is not None:
                    target_article = _article_by_number(
                        articles_by_document.get(owning_art.document_id, []),
                        internal_article_number,
                    )
                    if target_article is not None:
                        object_entity_type: str | None = "Article"
                        object_entity_id: str | None = target_article.id
                        confidence = _DERIVES_RESOLVED_CONFIDENCE
                    else:
                        object_entity_type = None
                        object_entity_id = None
                        confidence = _DERIVES_UNRESOLVED_CONFIDENCE
                else:
                    resolved_id = derivation_edge.target_law_id
                    if resolved_id is not None:
                        object_entity_type = "Document"
                        object_entity_id = resolved_id
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
                    jurisdiction=document_jurisdictions.get(owning_art.document_id),
                )

    session.commit()

    return {
        "created_assertions": created_assertions,
        "created_definitions": created_definitions,
        "skipped_degraded_article_ids": skipped_degraded_article_ids,
    }
