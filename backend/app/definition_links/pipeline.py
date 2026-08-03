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

import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.definition_links.derivation import strip_year_suffix
from app.definition_links.extract import (
    DefinitionCandidate,
    extract_adhoc_definitions,
    extract_local_definitions,
)
from app.definition_links.guards import is_bidi_degraded
from app.definition_links.matcher import link_articles_to_definitions
from app.definition_links.normalize import normalize_for_parsing, strip_wikilinks
from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle
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


# --- Wave 6 (sprint 2026-08-02-us-state-law, ruling R12): placeholder-
# heading jurisdictions (California, Illinois, Georgia) -----------------
#
# For these three states `Article.heading` (sourced from the dataset's
# `section_title` column) is a bare placeholder that carries NO real
# heading text at all -- real examples:
#
#   Illinois:   "Section 15"
#   California: "Section 22970.21"
#   Georgia:    "Georgia Code Title 45. Public Officers and Employees
#                 § 45-2-20"    (a reconstructed citation breadcrumb --
#                 "Public Officers and Employees" is the TITLE's name,
#                 repeated verbatim across every section under that
#                 title, not this section's own heading)
#
# The genuine heading, when one exists, lives at the START of the
# article's own body text instead -- real Illinois shape:
#
#   "(325 ILCS 7/15) (Section scheduled to be repealed on January 1,
#    2027) Sec. 15. Definitions. As used in this Act: \"Bias-free\"
#    means ..."
#
# `_is_placeholder_heading` recognizes ONLY the bare-placeholder shape
# itself (never a genuine, even terse, heading like DE's "Employer Match
# Plan" or FL's "941.34 Definition of “state.”" -- both carry
# real words of their own and never match either pattern below), so the
# body-derivation fallback below can NEVER fire for a heading that
# already means something -- it is only ever attempted after the
# ordinary `profile.is_definitions_heading(heading)` check has already
# returned False AND the heading itself is proven to carry no
# information. This is what keeps the 7 states already working off
# `section_title` (DE/NY/TX/FL/OH/PA/WA, 0.5-10.3% miss, 0 false
# positives) byte-for-byte unaffected -- their headings never match
# either pattern (verified against all 4 real files' full section_title
# columns, not merely asserted).
_BARE_SECTION_LABEL_RE = re.compile(r"^Section\s+\d[\w.\-]*\.?$", re.IGNORECASE)
_BARE_CITATION_LABEL_RE = re.compile(
    r"^.+\bCode Title\s+\d+[A-Za-z]?\.\s+.+§\s*[\w.\-]+\.?$", re.IGNORECASE
)


def _is_placeholder_heading(heading: str) -> bool:
    """True when `heading` carries no real descriptive text of its own --
    either a bare `"Section 15"` / `"Section 22970.21"` label (real
    Illinois/California shape -- the token right after "Section" must
    start with a digit, so a genuine heading that merely happens to start
    with the word "Section", e.g. a real NY row's `"Section Captions"`,
    is never mistaken for a placeholder), or a reconstructed
    `"<Jurisdiction> Code Title <N>. <Title name> § <section>"` citation
    breadcrumb (real Georgia shape). Both regexes are anchored/bounded
    with no nested quantifier over an alternation, so this stays a single
    linear-time scan of `heading` regardless of input shape.
    """
    if not heading:
        return False
    return bool(_BARE_SECTION_LABEL_RE.match(heading) or _BARE_CITATION_LABEL_RE.match(heading))


# Bounds how far into the body `_derive_heading_from_body` looks -- a
# fixed, small window keeps this a bounded-cost scan regardless of how
# long the article's full body text is (the body of a real US statute
# section can run to several KB).
_BODY_HEADING_SEARCH_WINDOW = 400

# Real Illinois/scrape-noise bodies open with one or more parenthetical
# asides before the genuine "Sec. N. Heading." sentence -- e.g.
# "(325 ILCS 7/15) (Section scheduled to be repealed on January 1, 2027)
#  Sec. 15. Definitions. ...". A single quantifier over a fixed,
# non-nested group (bounded to 4 repeats, each aside capped at 200 chars)
# -- no alternation-in-nested-quantifier, so no backtracking blowup.
_LEADING_PARENTHETICAL_RE = re.compile(r"^\s*(?:\([^()]{0,200}\)\s*){0,4}")

# The genuine embedded heading convention (Illinois): "Sec[tion] <N>.
# Definitions[.]" -- matched only immediately after the leading-
# parenthetical noise at the very START of the body (via `.match(window,
# pos)`, not `.search`), so a MID-body reference to some OTHER section's
# definitions ("...as required by Sec. 10. Definitions...") is never
# mistaken for this article's own heading.
_BODY_EMBEDDED_HEADING_RE = re.compile(
    r"Sec(?:tion)?\.?\s+[\w.\-]+\.\s*Definitions?\b\.?",
    re.IGNORECASE,
)

# The definitions-PREAMBLE convention (California/Georgia real shape --
# these two states have no embedded "Sec. N. Heading." sentence at all;
# the body opens directly with the substantive preamble), e.g. real:
#   "Unless the context otherwise requires, the definitions in this
#    article govern the construction of this chapter."
#   "For purposes of this chapter, the following definitions apply: ..."
# Bounded, non-greedy quantifiers (`.{0,80}?`, `.{0,120}?`) cap the total
# scan cost at a small constant regardless of body length -- no unbounded
# `.*`, so no catastrophic-backtracking surface. The lookahead requires
# "definition(s)" to be followed, within a short bounded gap, by a verb
# that only shows up in a genuine "these ARE the definitions for this
# text" preamble (appl(y/ies/ied), govern, shall apply) -- a passing
# mention like "...meets the definition of a licensee..." (no such verb
# nearby) correctly does NOT match. The captured span ends at
# "definition(s)" itself (not the verb), so the returned string's own
# LAST word is "Definitions" -- exactly what `is_definitions_heading`'s
# last-word rule checks.
_BODY_DEFINITIONS_PREAMBLE_RE = re.compile(
    r"^.{0,80}?\bDefinitions?\b(?=.{0,120}?\b(?:appl(?:y|ies|ied)|govern|shall\s+apply)\b)",
    re.IGNORECASE | re.DOTALL,
)


def _derive_heading_from_body(body: str) -> str | None:
    """Derive the article's real heading from the START of `body`, for a
    jurisdiction whose `section_title` is a bare placeholder (wave 6,
    ruling R12).

    Tries, in order:

    1. The Illinois embedded-heading convention -- real:
       `"(325 ILCS 7/15) (Section scheduled to be repealed on January 1,
        2027) Sec. 15. Definitions."` -> returns everything through
       "Definitions." (this substring, fed to `is_definitions_heading`,
       matches via its last-word rule regardless of the messy prefix,
       since only the token immediately before "Definitions" is checked
       against a small preposition list).
    2. The California/Georgia definitions-preamble convention -- real:
       `"Unless the context otherwise requires, the definitions"` (from
       "...the definitions in this article govern the construction of
       this chapter.") or `"For purposes of this chapter, the following
       definitions"` (from "...the following definitions apply: ...").

    Returns `None` when neither convention is found in the leading
    `_BODY_HEADING_SEARCH_WINDOW` characters of `body` -- e.g. an ordinary
    (non-definitions) placeholder-headed section never derives a
    heading, so it falls through to the same Hebrew local/adhoc fallback
    an ordinary non-definitions article always has.
    """
    window = body[:_BODY_HEADING_SEARCH_WINDOW]

    noise_match = _LEADING_PARENTHETICAL_RE.match(window)
    embedded_match = _BODY_EMBEDDED_HEADING_RE.match(window, noise_match.end())
    if embedded_match is not None:
        return window[: embedded_match.end()]

    preamble_match = _BODY_DEFINITIONS_PREAMBLE_RE.match(window)
    if preamble_match is not None:
        return window[: preamble_match.end()]

    return None


# A quoted defined term (straight or curly double quotes), real US
# statutory drafting shape for CA/IL/GA's placeholder-heading bodies --
# these have NO "(N)"-numbered-paragraph structure at all (unlike DE's
# fixture shape, which `USProfile.extract_definitions_from_section`
# already handles), just an inline run of `"Term" means ...` sentences,
# e.g. real Illinois:
#   "... As used in this Act: \"Bias-free\" means to review a case file
#    ... \"BIPOC\" means people who are members of ..."
# Bounded to 200 chars per term so a single unterminated quote can't force
# an unbounded scan.
_QUOTE_TERM_RE = re.compile(r'["“]([^"”]{1,200})["”]')

# Whether a quoted span is a genuine defined-TERM marker (as opposed to a
# quoted phrase appearing somewhere INSIDE another entry's own definition
# text) -- checked by looking for a "means"/"shall mean"/"has the
# meaning" idiom within a bounded gap after the closing quote, with NO
# other quote character in between (so a later quoted phrase belonging to
# the CURRENT entry's own definition text is never mistaken for the next
# entry's term). Real Illinois shape has both the immediate case
# (`"BIPOC" means ...`) and a delayed case with an intervening clause
# (`"Immediate and urgent necessity", in accordance with Section 5 ...,
#  means (i) ...`) -- the bounded, non-greedy `{0,200}?` gap covers both
# without unbounded backtracking.
_MEANS_IDIOM_GAP_RE = re.compile(
    r'^[^"“”]{0,200}?\b(?:means|shall mean|has the meaning)\b:?\s*',
    re.IGNORECASE,
)


def _extract_inline_quoted_definitions(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Extract `(term, definition)` pairs from a placeholder-heading
    jurisdiction's Definitions-section body composed of inline `"Term"
    means ...` sentences with NO numbered-paragraph markers -- the real
    Illinois/California/Georgia shape that
    `USProfile.extract_definitions_from_section`'s `"(N)"`-block splitter
    cannot parse (there are no `"(N)"` markers to split on at all).

    Only used as a FALLBACK, after `profile.extract_definitions_from_
    section` has already been tried and returned nothing for this body --
    some real CA/GA sections DO use a numbered-paragraph structure the
    profile's own extractor already handles; this only covers the
    remaining inline-sentence shape, and only for articles reached via
    `_derive_heading_from_body` (never for the 7 states already working
    off their own `section_title`, so this is zero-risk for them).

    A quoted span only starts a new entry when it is followed (within a
    bounded gap, no intervening quote) by a defining idiom
    (`_MEANS_IDIOM_GAP_RE`) -- a quoted phrase inside another entry's own
    definition prose is correctly left alone. Each entry runs from its own
    term through to the START of the next recognized entry (or end of
    text).
    """
    entries: list[tuple[str, int, int]] = []
    for term_match in _QUOTE_TERM_RE.finditer(text):
        gap = text[term_match.end() : term_match.end() + 200]
        means_match = _MEANS_IDIOM_GAP_RE.match(gap)
        if means_match is None:
            continue
        term = term_match.group(1).strip()
        if not term:
            continue
        entries.append((term, term_match.start(), term_match.end() + means_match.end()))

    candidates: list[DefinitionCandidate] = []
    for index, (term, start, definition_start) in enumerate(entries):
        end = entries[index + 1][1] if index + 1 < len(entries) else len(text)
        definition_text = text[definition_start:end].strip()
        if not definition_text:
            continue
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
        )
    return candidates


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
        normalized = normalize_for_parsing(raw_body)
        stripped_body, _hints = strip_wikilinks(normalized)
        live_articles.append(
            (art, MatcherArticle(number=art.number, heading=art.heading, body=stripped_body, chapter=art.chapter))
        )

    # Stage 2: extract every DefinitionCandidate, tagged with its owning
    # (ORM) article for provenance/persistence.
    all_candidates: list[tuple[DefinitionCandidate, Article]] = []
    for art, matcher_article in live_articles:
        profile = _profile_for_document(art.document_id)
        is_definitions_section = profile.is_definitions_heading(art.heading)

        # Wave 6 (ruling R12): CA/IL/GA leave a bare placeholder in
        # `section_title` (`Article.heading`), so the check above always
        # returns False for them even when the article genuinely IS a
        # Definitions section -- try deriving the real heading from the
        # body instead, but ONLY when the heading is proven to carry no
        # information of its own (`_is_placeholder_heading`) and never
        # for Hebrew (`profile.code == "IL"`, the Israeli jurisdiction --
        # unrelated to the US "US-IL" Illinois code). This ordering means
        # the derivation attempt only ever runs for an article that was
        # ALREADY going to fall through to the (always-empty-for-English)
        # Hebrew local/adhoc path below -- a heading that already matched
        # the ordinary check is completely untouched, so the 7 states
        # already working off `section_title` are byte-for-byte
        # unaffected (verified against DE/NY/TX/FL/OH/PA/WA's real
        # `section_title` columns -- see the developer report).
        used_body_derived_heading = False
        if (
            not is_definitions_section
            and profile.code != "IL"
            and _is_placeholder_heading(art.heading)
        ):
            derived_heading = _derive_heading_from_body(matcher_article.body)
            if derived_heading is not None and profile.is_definitions_heading(derived_heading):
                is_definitions_section = True
                used_body_derived_heading = True

        if is_definitions_section:
            scope = _determine_scope(matcher_article.body)
            section_candidates = profile.extract_definitions_from_section(
                matcher_article.body, scope=scope
            )
            # The profile's own extractor expects a "(N)"-numbered-
            # paragraph body (DE's real shape); CA/IL/GA's placeholder-
            # heading bodies are often an inline `"Term" means ...` run
            # with no numbering at all, which yields zero candidates from
            # that extractor -- fall back to the inline-quote extractor
            # ONLY for a body-derived article (never for the 7 already-
            # working states, whose bodies keep using the profile's own
            # extractor exclusively, unchanged).
            if not section_candidates and used_body_derived_heading:
                section_candidates = _extract_inline_quoted_definitions(
                    matcher_article.body, scope=scope
                )
            for candidate in section_candidates:
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
        term_to_definition: dict[str, Definition] = {}
        for candidate, definition_row in doc_candidates:
            for term in candidate.terms:
                term_to_definition[term] = definition_row
        matcher_arts = [matcher_article for _, matcher_article in doc_articles]

        edges = link_articles_to_definitions(
            [c for c, _ in doc_candidates],
            matcher_arts,
            profile=_profile_for_document(document_id),
        )
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
                jurisdiction=document_jurisdictions.get(using_article.document_id),
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
                    jurisdiction=document_jurisdictions.get(owning_art.document_id),
                )

    session.commit()

    return {
        "created_assertions": created_assertions,
        "created_definitions": created_definitions,
        "skipped_degraded_article_ids": skipped_degraded_article_ids,
    }
