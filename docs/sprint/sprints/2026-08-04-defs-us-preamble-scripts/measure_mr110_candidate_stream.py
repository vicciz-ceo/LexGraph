"""Runtime-only M-R121 uniform source-truth + plural-list B1 prototype.

This deliberately patches the proposed additive seam, never production:
registry returns a ``BodyPreambleMatch``-shaped value for B1, B1 discovers
one bounded plural-anaphora list, ``USProfile`` carries the match into
extraction, and the pipeline's profile resolver sees that patched profile. A
bounded term-local payload classifies malformed B1 candidates; substantive
baseline candidates retain their exact current text and the list adds only a
missing term.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))
from qa_g7_common import canonical_bytes, SNAPSHOT_ID, capture_row, jurisdiction_for, tuple_key, validate_corpus, write_json, write_jsonl


@dataclass(frozen=True)
class ClauseGroup:
    """One matched numbered list plus its explicit shared relationship.

    The production equivalent belongs in ``registry.py`` as additive evidence
    on a B1-only ``BodyPreambleMatch``.  Spans are body offsets; no group is a
    body boundary.  This runtime prototype deliberately carries no generic
    clause/alias/citation discovery.
    """

    term_spans: tuple[tuple[str, int, int], ...]
    relationship_span: tuple[int, int]
    colon_list: bool = False
    shared_trailing_relation: bool = False


@dataclass(frozen=True)
class BodyPreambleMatch:
    heading: str
    clause_groups: tuple[ClauseGroup, ...] = ()
    baseline_eligible: bool = False


_CLAUSE_BOUNDARY = re.compile(r"[;\n]")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.?!])(?:\s|$)")
_MATCHED_NUMBERED_ENTRY = re.compile(
    r'\(\s*\d+[A-Za-z]?\s*\)[ \t]*(?:"(?P<straight>[^"]{1,200})"|“(?P<curly>[^”]{1,200})”)'
)
# The only additive shape: at least two numbered entries, each with a matched
# quote delimiter, followed immediately by a forwarding relation that names
# the plural antecedent.  It intentionally excludes generic aliases,
# descriptive copulas, exclusions, citations, and unmatched source quotes.
_SHARED_TRAILING_LIST = re.compile(
    r"(?P<entries>(?:\(\s*\d+[A-Za-z]?\s*\)[ \t]*(?:\"[^\"]{1,200}\"|“[^”]{1,200}”)\s*;\s*(?:(?:and|or)\s*)?){2,})"
    r"(?P<relation>(?:has|have|shall\s+have)\s+the\s+(?:same\s+)?(?:meaning|definition)"
    r"(?:\s+(?:set\s+forth|provided|given|found|prescribed))?\s+(?:for\s+)?those\s+terms\b[^;\n]{0,300})",
    re.IGNORECASE,
)
_MAX_GROUP = 600
_FORWARDING_LOOKBACK = 6000
_COLON_INTRO_WINDOW = 160
_COORDINATION = frozenset({"and", "or"})
_STRUCTURAL_MARKER = re.compile(
    r"(?:\(\s*(?:\d+|[a-z]+)\s*\)|\[\s*(?:\d+|[a-z]+)\s*\]|\d+)", re.IGNORECASE
)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_LEGISLATIVE_HISTORY_PREFIX = re.compile(r"^\s*\[(?:L|Acts?)\s+\d{4}\b", re.IGNORECASE)
_DIRECT_POST_QUOTE_RELATION = re.compile(
    r"^[\s:;,.\-–—]*(?:(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\]|[A-Za-z]\.)\s*)*"
    r"(?:[^;.\n]{1,160}?,\s*)?"
    r"(?:means|shall\s+mean|includes|shall\s+include|"
    r"(?:has|have|shall\s+have)\s+the\s+(?:same\s+)?meaning|"
    r"the\s+meaning\s+(?:given|provided|set\s+forth|specified|prescribed))\b",
    re.IGNORECASE,
)
_ENUMERATED_POST_QUOTE_RELATION = re.compile(
    r"^[\s\-–—]*:\s*(?:(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\])\s*)"
    r"[^;.\n]{0,160}?\b(?:means|shall\s+mean|includes|shall\s+include|"
    r"(?:has|have|shall\s+have)\s+the\s+(?:same\s+)?meaning)\b",
    re.IGNORECASE,
)
_ALIAS_NAME_VERB = r"(?:referred\s+to|known|designated|established|maintained)"
_ALIAS_OR_NAME_INTRO = re.compile(
    r"(?:(?:is|are|(?:may|shall)\s+be|in\s+[^.;:\n()]{1,100})\s+)?"
    rf"(?:commonly\s+)?{_ALIAS_NAME_VERB}"
    r"(?:\s+in\s+[^.;:\n]{0,100})?\s+as(?:\s+the)?\s*$",
    re.IGNORECASE,
)
_ALIAS_LIST_INTRO = re.compile(
    r"(?:shall|may)\s+be\s+(?:known|referred\s+to)\s+as\s+the\s*[\-–—:]\s*"
    r"(?:(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\])\s*"
    r"(?:\"[^\"]{1,200}\"|“[^”]{1,200}”)\s*[;,]?\s*(?:and|or)?\s*)*"
    r"(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\])?\s*$",
    re.IGNORECASE,
)
_RECIPROCAL_ALIAS_LIST_INTRO = re.compile(
    rf"\b{_ALIAS_NAME_VERB}\s*,?\s*respectively\s*,?\s*as\s*"
    r"(?:(?:\"[^\"]{1,200}\"|“[^”]{1,200}”)\s*"
    r"(?:,\s*)?(?:(?:and|or)\s*)?)*$",
    re.IGNORECASE,
)
_FORWARDING_INTRO = re.compile(
    r"(?:the\s+following\s+definitions?\s+in\s+(?:other\s+)?[^:.;\n]{0,100}\s+apply\s+to\s+this\s+[^:.;\n]{0,50}|"
    r"definitions?\s+in\s+other\s+[^:.;\n]{0,100}\s+applying\s+to\s+this\s+[^:.;\n]{0,100}\s+(?:include|are)|"
    r"the\s+following\s+terms?\s+(?:shall\s+)?have\s+the\s+(?:same\s+)?meaning\s+as\s+"
    r"(?:provided|set\s+forth|specified)\s+in\s+[^:.;\n]{0,100})\s*:",
    re.IGNORECASE,
)


def has_substantive_definition_text(definition_text: str) -> bool:
    """Normalize a local payload without vocabulary or corpus exceptions."""
    if _LEGISLATIVE_HISTORY_PREFIX.match(definition_text):
        return False
    residual = _STRUCTURAL_MARKER.sub(" ", definition_text)
    return any(word.casefold() not in _COORDINATION for word in _WORD.findall(residual))


def _normalized_production_term(term: str) -> str:
    """Use the candidate's production spelling, minus boundary punctuation."""
    return re.sub(r"\s+", " ", term.strip().rstrip(".,;:"))


def _matched_quote_occurrences(text: str, term: str):
    """Yield the best delimiter-matched raw occurrences for one emitted term.

    Exact emitted punctuation is authoritative for payload classification.
    Terminal-punctuation-tolerant occurrences remain available only to prove
    an explicit relation; they cannot lend arbitrary trailing prose to a
    dotted pseudo-entry.
    """
    emitted_term = re.sub(r"\s+", " ", term.strip())
    if not emitted_term:
        return ()

    def quoted(pattern: str, *, tolerant_terminal: bool):
        terminal = r"[.,;:]*" if tolerant_terminal else ""
        return tuple(re.finditer(
            rf'(?:"\s*{pattern}{terminal}\s*"|“\s*{pattern}{terminal}\s*”)',
            text,
            re.IGNORECASE,
        ))

    exact_pattern = r"\s+".join(re.escape(part) for part in emitted_term.split())
    exact = quoted(exact_pattern, tolerant_terminal=False)
    normalized_term = _normalized_production_term(emitted_term)
    normalized_pattern = r"\s+".join(re.escape(part) for part in normalized_term.split())
    tolerant = quoted(normalized_pattern, tolerant_terminal=True)
    exact_spans = {match.span() for match in exact}
    matches = exact + tuple(match for match in tolerant if match.span() not in exact_spans)
    # Straight quotes carry no intrinsic direction, and global parity is not
    # reliable across a whole consolidated-code row. Reject only the bounded
    # statutory continuation shape: the nearest prior quote opens a numbered
    # paragraph and has no closer before this apparent opening quote. This is
    # the federal Sunset malformed-source shape; ordinary independently
    # quoted form provisions remain valid even if an earlier row fragment has
    # unbalanced punctuation.
    def is_continuation_opening(match) -> bool:
        if text[match.start()] != '"':
            return False
        previous = text.rfind('"', max(0, match.start() - _FORWARDING_LOOKBACK), match.start())
        if previous < 0:
            return False
        # A continuation quote must itself open a quoted statutory line.  A
        # quote after visible line content is a closer; treating it as an
        # opener suppresses the next independent ``(marker) "term"`` pair.
        line_start = max(text.rfind("\n", 0, previous), text.rfind("\r", 0, previous)) + 1
        if text[line_start:previous].strip():
            return False
        return re.match(r'\s*\([A-Za-z0-9]+\)\s+', text[previous + 1 : match.start()]) is not None

    return tuple(
        match
        for match in matches
        if not is_continuation_opening(match)
    )


def _occurrence_matches_emitted_term(text: str, term: str, quote) -> bool:
    emitted = re.sub(r"\s+", " ", term.strip()).casefold()
    raw_term = re.sub(r"\s+", " ", text[quote.start() + 1 : quote.end() - 1].strip()).casefold()
    return emitted == raw_term


def _group_owns_occurrence(term: str, quote, groups: tuple[ClauseGroup, ...]) -> bool:
    """Return whether a matched plural group owns this exact quote occurrence."""
    normalized = _normalized_production_term(term).casefold()
    return any(
        normalized == _normalized_production_term(group_term).casefold()
        and quote.start() <= start
        and end <= quote.end()
        for group in groups
        for group_term, start, end in group.term_spans
    )


def _bounded_local_payload(text: str, quote_end: int) -> str:
    """Return the source-local payload without crossing a list boundary.

    A physically wrapped direct relation (``"term"`` followed by ``means``)
    remains one local occurrence.  Any other newline is a source boundary, so
    an ensuing numbered/subsection clause cannot lend its payload to the quote.
    """
    tail = text[quote_end : quote_end + _MAX_GROUP]
    semicolon = tail.find(";")
    newline = tail.find("\n")
    boundaries = [index for index in (semicolon,) if index >= 0]
    if newline >= 0:
        before_newline = tail[:newline]
        after_newline = tail[newline:]
        wrapped_relation = not before_newline.strip() and re.match(
            r"\s*(?:means|shall\s+mean|includes|shall\s+include)\b", after_newline, re.I
        )
        if not wrapped_relation:
            boundaries.append(newline)
    return tail[: min(boundaries)] if boundaries else tail


def _has_explicit_post_quote_relation(text: str, quote_end: int) -> bool:
    """Recognize a direct verb through only punctuation/list structure."""
    tail = text[quote_end : quote_end + _MAX_GROUP]
    return (
        _DIRECT_POST_QUOTE_RELATION.match(tail) is not None
        or _ENUMERATED_POST_QUOTE_RELATION.match(tail) is not None
    )


def _has_explicit_pre_quote_relation(text: str, quote_start: int) -> bool:
    """Recognize alias/name and indexed-list relations before the quote."""
    lookback = text[max(0, quote_start - _MAX_GROUP) : quote_start]
    sentence_tail = re.split(r"[.;\n]", lookback)[-1]
    if _ALIAS_OR_NAME_INTRO.search(sentence_tail):
        return True
    if _ALIAS_LIST_INTRO.search(lookback):
        return True
    if _RECIPROCAL_ALIAS_LIST_INTRO.search(lookback):
        return True
    # Forwarding intros govern a bounded enumerated list, so the first
    # relation can precede intervening markers and earlier quoted entries.
    forwarding_lookback = text[max(0, quote_start - _FORWARDING_LOOKBACK) : quote_start]
    return _FORWARDING_INTRO.search(forwarding_lookback) is not None


def candidate_has_substantive_local_payload(text: str, candidate, groups: tuple[ClauseGroup, ...] = ()) -> bool:
    """Preserve a candidate if any exact quoted occurrence is substantive.

    Every occurrence is matched with like quote delimiters and normalized from
    the existing production term.  The first semicolon or newline bounds each
    payload.  A missing source quote fails open to the existing candidate text,
    preserving uncertain baseline data.
    """
    for term in candidate.terms:
        normalized_term = _normalized_production_term(term)
        if not normalized_term:
            return True
        quotes = tuple(_matched_quote_occurrences(text, term))
        if not quotes:
            # No matched delimiters means the source cannot establish the
            # M-R117 all-occurrence condition (for example, malformed quote
            # encoding). Preserve the current tuple rather than infer a loss.
            return True
        has_exact_occurrence = any(_occurrence_matches_emitted_term(text, term, quote) for quote in quotes)
        for quote in quotes:
            # The shared relation repairs this occurrence itself. It must not
            # preserve a stale baseline candidate, but any independent
            # substantive occurrence of the same term still wins below.
            if _group_owns_occurrence(term, quote, groups):
                continue
            if _has_explicit_post_quote_relation(text, quote.end()):
                return True
            if _has_explicit_pre_quote_relation(text, quote.start()):
                return True
            if has_exact_occurrence and not _occurrence_matches_emitted_term(text, term, quote):
                continue
            if has_substantive_definition_text(_bounded_local_payload(text, quote.end())):
                return True
    return False


def _group_end(body: str, start: int) -> int:
    """End at the first clause/sentence boundary, never a whole body."""
    limit = min(len(body), start + _MAX_GROUP)
    tail = body[start:limit]
    ends = [m.start() + start + 1 for m in _CLAUSE_BOUNDARY.finditer(tail)]
    sentence = _SENTENCE_BOUNDARY.search(tail)
    if sentence is not None:
        ends.append(start + sentence.start() + 1)
    return min(ends) if ends else limit


def discover_clause_groups(body: str) -> tuple[ClauseGroup, ...]:
    """Find only an explicit matched quoted/list-marker plural relationship."""
    groups: list[ClauseGroup] = []
    from app.definition_links.rules.us_body_preamble_b1 import (
        _B1_LOOKAHEAD,
        _B1_TRIGGER_RE,
        _b1_colon_list_branch,
    )

    for trigger in _B1_TRIGGER_RE.finditer(body):
        after = body[trigger.end() : trigger.end() + _B1_LOOKAHEAD]
        if not _b1_colon_list_branch(after):
            continue
        colon = after.find(":")
        if colon < 0:
            continue
        list_start = trigger.end() + colon + 1
        list_end = min(len(body), list_start + _MAX_GROUP)
        for shared in _SHARED_TRAILING_LIST.finditer(body, list_start, list_end):
            entries = []
            for entry in _MATCHED_NUMBERED_ENTRY.finditer(body, shared.start("entries"), shared.end("entries")):
                name = entry.group("straight") or entry.group("curly")
                start = entry.start("straight") if entry.group("straight") is not None else entry.start("curly")
                end = entry.end("straight") if entry.group("straight") is not None else entry.end("curly")
                if name.strip():
                    entries.append((name.strip(), start, end))
            if len(entries) < 2:
                continue
            groups.append(
                ClauseGroup(
                    term_spans=tuple(entries),
                    relationship_span=(shared.start("relation"), _group_end(body, shared.start("relation"))),
                    shared_trailing_relation=True,
                )
            )
    # A duplicate can arise from a nested regex alternative; preserve source
    # order but make union deterministic.
    seen: set[tuple[tuple[tuple[str, int, int], ...], tuple[int, int], bool, bool]] = set()
    return tuple(
        g
        for g in groups
        if not ((key := (g.term_spans, g.relationship_span, g.colon_list, g.shared_trailing_relation)) in seen or seen.add(key))
    )


def _b1_default_preserve_match(body: str) -> BodyPreambleMatch | None:
    """Patch only a row already won by the current B1 rule."""
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means

    original_b1 = _b1_trigger_colon_or_quote_means(body) is not None
    if not original_b1:
        return None
    return BodyPreambleMatch("Definitions", discover_clause_groups(body), baseline_eligible=True)


def _group_candidates(text: str, groups: tuple[ClauseGroup, ...], scope: str):
    from app.definition_links.extract import DefinitionCandidate

    candidates = []
    for group in groups:
        start, end = group.relationship_span
        definition_text = text[start:end].strip()
        if group.colon_list or len(group.term_spans) == 1:
            idiom = re.match(r"(?:means?|shall\s+mean|includes?|shall\s+include)\b:?\s*", definition_text, re.I)
            if idiom is not None:
                definition_text = definition_text[idiom.end():]
        if not definition_text:
            continue
        for term, _, _ in group.term_spans:
            candidates.append(DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope))
    return candidates


def _preserved_baseline_candidates(text: str, candidates, match: BodyPreambleMatch):
    """Keep the complete stream only when the original B1 rule dispatched."""
    if not match.baseline_eligible:
        return []
    preserved = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(sorted(candidate.terms))
        if key in seen or not candidate_has_substantive_local_payload(
            text, candidate, match.clause_groups
        ):
            continue
        seen.add(key)
        preserved.append(candidate)
    return preserved


@contextlib.contextmanager
def default_preserve_runtime_patch():
    """Patch and restore the four proposed layers deterministically."""
    from app.definition_links import pipeline
    from app.definition_links.rules import registry
    from app.definition_links.rules.registry import BodyPreambleRule
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import BodyPreambleMatch as ProductionBodyPreambleMatch
    from app.definition_links.us_profile import USProfile, derive_heading_from_body

    original_rules_for = registry.body_preamble_rules_for
    original_derive = USProfile.derive_heading_from_body
    original_extract = USProfile.extract_definitions_from_section
    original_extract_local = USProfile.extract_local_scope_definitions
    original_normalize = USProfile.normalize_for_parsing
    # The production resolver may materialize equivalent profile instances;
    # body text is the immutable carrier key that survives all four layers.
    matches: dict[str, BodyPreambleMatch] = {}
    raw_source_by_parser_body: dict[str, str] = {}

    def normalize_for_parsing(self, text: str):
        normalized = original_normalize(self, text)
        raw_source_by_parser_body[normalized] = text
        return normalized

    def source_view(parser_body: str) -> str:
        # Parser normalization may repair malformed delimiters. It may help
        # discovery, but only the raw source can justify removing a current
        # B1 tuple.
        return raw_source_by_parser_body.get(parser_body, parser_body)

    def rules_for(code: str):
        rules = original_rules_for(code)
        return [
            BodyPreambleRule(rule.jurisdiction_codes, _b1_default_preserve_match)
            if rule.derive_heading is _b1_trigger_colon_or_quote_means
            else rule
            for rule in rules
        ]

    def derive(self, heading: str, body: str, *, raw_source=None, article_number="", chapter=None):
        baseline = derive_heading_from_body(heading, body)
        if baseline is not None:
            return baseline
        for rule in registry.body_preamble_rules_for(self.code):
            value = rule.derive_heading(body)
            if value is None:
                continue
            if isinstance(value, BodyPreambleMatch):
                scope = self.determine_scope(body)
                baseline_candidates = original_extract(
                    self, body, scope=scope, heading_was_derived=True, raw_source=raw_source, b1_winner=False
                )
                raw_body = raw_source or source_view(body)
                preserved = _preserved_baseline_candidates(raw_body, baseline_candidates, value)
                # Some direct B1 tuples are emitted only through the existing
                # local extractor.  They are still current B1 candidates and
                # must take the same all-occurrence preservation path before
                # this B1-only prototype may suppress derived recognition.
                local_candidates = original_extract_local(
                    self, body, article_number=article_number, chapter=chapter, raw_source=raw_source, b1_winner=False
                )
                preserved_local = _preserved_baseline_candidates(raw_body, local_candidates, value)
                additions = _group_candidates(body, value.clause_groups, scope)
                if not preserved and not preserved_local and not additions:
                    return None
                matches[body] = value
                return ProductionBodyPreambleMatch(value.heading, b1_winner=True)
            return value
        return None

    def extract(self, text: str, *, scope: str, heading_was_derived=False, raw_source=None, b1_winner=None):
        match = matches.get(text)
        if match is None or not heading_was_derived:
            return original_extract(self, text, scope=scope, heading_was_derived=heading_was_derived, raw_source=raw_source, b1_winner=b1_winner)
        baseline = original_extract(self, text, scope=scope, heading_was_derived=True, raw_source=raw_source, b1_winner=False)
        preserved = _preserved_baseline_candidates(raw_source or source_view(text), baseline, match)
        present_terms = {tuple(sorted(candidate.terms)) for candidate in preserved}
        additions = [
            candidate
            for candidate in _group_candidates(text, match.clause_groups, scope)
            if tuple(sorted(candidate.terms)) not in present_terms
        ]
        return preserved + additions

    def extract_local(self, article_body: str, *, article_number: str, chapter=None, raw_source=None, b1_winner=False):
        match = matches.get(article_body)
        original = original_extract_local(self, article_body, article_number=article_number, chapter=chapter, raw_source=raw_source, b1_winner=False)
        if match is None:
            return original
        return _preserved_baseline_candidates(raw_source or source_view(article_body), original, match)

    registry.body_preamble_rules_for = rules_for
    USProfile.normalize_for_parsing = normalize_for_parsing
    USProfile.derive_heading_from_body = derive
    USProfile.extract_definitions_from_section = extract
    USProfile.extract_local_scope_definitions = extract_local
    try:
        yield
    finally:
        USProfile.normalize_for_parsing = original_normalize
        USProfile.extract_definitions_from_section = original_extract
        USProfile.extract_local_scope_definitions = original_extract_local
        USProfile.derive_heading_from_body = original_derive
        registry.body_preamble_rules_for = original_rules_for


def _current_b1_winner(code: str, heading: str, body: str) -> bool:
    """Exact live parser-body first-winner prefilter; prototype never expands it."""
    # Registration is import-time by design; make the production family
    # module explicit so a forked worker starts from the same registry state
    # as the real profile/pipeline imports.
    import app.definition_links.rules.us_body_preamble  # noqa: F401
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import derive_heading_from_body

    if derive_heading_from_body(heading, body) is not None:
        return False
    # The runtime patch replaces the public lookup for AFTER capture.  The
    # audited winner prefilter must instead read the unchanged registered
    # sequence directly, retaining current first-winner membership exactly.
    for rule in (rule for rule in registry._body_preamble_rules if registry._matches(rule.jurisdiction_codes, code)):
        if rule.derive_heading(body) is not None:
            return rule.derive_heading is _b1_trigger_colon_or_quote_means
    return False


def _file(path_text: str):
    path = Path(path_text)
    code = jurisdiction_for(path)
    before, after, current_members, evaluated_members, selected = [], [], [], [], []
    # Current production is the baseline.  ``capture_row(after=True)`` is
    # intentional here: it exercises today's registered B1 pipeline, before
    # the runtime patch exists, rather than the pre-B1 legacy baseline.
    for batch_index, batch in enumerate(
        pq.ParquetFile(path).iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=4096
        )
    ):
        for row_index, row in enumerate(batch.to_pylist()):
            source_row = batch_index * 4096 + row_index
            raw_body, heading = row["text"] or "", row["section_title"] or ""
            from app.definition_links.normalize import strip_wikilinks
            from app.definition_links.profiles import get_profile

            profile = get_profile(code)
            body, _ = strip_wikilinks(profile.normalize_for_parsing(raw_body))
            current_b1 = _current_b1_winner(code, heading, body)
            if not current_b1:
                continue
            selected.append((source_row, row))
            member = {
                "source_file": path.name,
                "source_row": source_row,
                "source_row_id": str(row["act_id"] or f"{path.name}:{source_row}"),
            }
            evaluated_members.append(member)
            current_members.append(member)
            before.extend(x.record() for x in capture_row(jurisdiction=code, source_file=path.name, source_row=source_row, row=row, after=True))
    with default_preserve_runtime_patch():
        for source_row, row in selected:
            after.extend(x.record() for x in capture_row(jurisdiction=code, source_file=path.name, source_row=source_row, row=row, after=True))
    baseline = {tuple_key(x): x for x in before}
    proposed = {tuple_key(x): x for x in after}
    changes = []
    for change, left, right in (("removed", baseline, proposed), ("added", proposed, baseline)):
        for key in left.keys() - right.keys():
            row = left[key]
            changes.append(
                {
                    "change": change,
                    "term_local_substantive": has_substantive_definition_text(row["definition_text"]),
                    "classification": "needs_source_adjudication",
                    **row,
                }
            )
    return changes, current_members, evaluated_members


_EXPECTED_CURRENT_B1_COUNT = 193830
_EXPECTED_CURRENT_B1_SHA256 = "851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a"


def _run_self_check() -> int:
    """Run direct and persistence controls under the prototype.

    Canonical invocation: ``PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python
    docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/
    measure_mr110_candidate_stream.py --self-check``.
    """
    import pytest

    tests = [
        "backend/tests/unit/test_us_body_preamble_b1_occurrence_local_profile_red.py",
        "backend/tests/integration/test_us_body_preamble_b1_occurrence_local_persistence_red.py",
        "backend/tests/unit/test_us_body_preamble_b1_structural_future_law_red.py",
        "backend/tests/integration/test_us_body_preamble_b1_structural_future_law_persistence_red.py",
        "backend/tests/unit/test_mr121_b1_source_truth_red.py",
        "backend/tests/integration/test_mr121_b1_source_truth_persistence_red.py",
    ]
    with default_preserve_runtime_patch():
        return pytest.main(["-q", *[str(ROOT / test) for test in tests]])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        return _run_self_check()
    if args.snapshot is None or args.out is None:
        parser.error("--snapshot and --out are required unless --self-check")
    files, rows, _ = validate_corpus(args.snapshot)
    chosen = files[args.shard :: args.shards]
    # Deliberately foreground and sequential: each shard is independently
    # reviewable, and macOS fork workers can hide import failures from the
    # evidence command's documented stdout/stderr contract.
    parts = [_file(str(path)) for path in chosen]
    changed = [row for part, _, _ in parts for row in part]
    current_members = [row for _, part, _ in parts for row in part]
    evaluated_members = [row for _, _, part in parts for row in part]
    changed.sort(key=lambda row: (tuple_key(row), row["change"]))
    current_members.sort(key=lambda row: (row["source_file"], row["source_row"]))
    evaluated_members.sort(key=lambda row: (row["source_file"], row["source_row"]))
    if evaluated_members != current_members:
        raise RuntimeError("evaluated B1 membership differs from the current B1-winner population")
    current_digest = hashlib.sha256()
    for member in current_members:
        current_digest.update(canonical_bytes(member))
        current_digest.update(b"\n")
    current_sha256 = current_digest.hexdigest()
    if len(current_members) != _EXPECTED_CURRENT_B1_COUNT or current_sha256 != _EXPECTED_CURRENT_B1_SHA256:
        raise RuntimeError(
            f"current B1 membership drift: count={len(current_members)} hash={current_sha256}"
        )
    args.out.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "lexgraph.mr113.default-preserve-additive-groups.v1",
        "snapshot_id": SNAPSHOT_ID,
        "files": len(files),
        "rows": rows,
        "shard": [args.shard, args.shards],
        "current_b1_winner_row_count": len(current_members),
        "current_b1_winner_membership_sha256": write_jsonl(
            args.out / "current_b1_winner_rows.jsonl", current_members
        ),
        "evaluated_b1_row_count": len(evaluated_members),
        "evaluated_b1_membership_sha256": write_jsonl(
            args.out / "evaluated_b1_rows.jsonl", evaluated_members
        ),
        "changed_key_count": len(changed),
        "classification_totals": dict(sorted(Counter(row["classification"] for row in changed).items())),
        "ledger_sha256": write_jsonl(args.out / "changed.jsonl", changed),
    }
    write_json(args.out / "summary.json", result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
