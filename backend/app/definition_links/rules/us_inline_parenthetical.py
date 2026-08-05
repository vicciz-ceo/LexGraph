"""Rule module: F6 inline parenthetical/cross-reference definitions
(sprint 2026-08-04-defs-us-multiterm, items 5-6).

Two real shapes, neither reachable by baseline today:

1. **Bare apposition, no means-idiom** (`("Term")` / `(the "Term")`) --
   e.g. NH's short-title `(the "Act")`, NH/ND's compact-withdrawal
   `("withdrawing state")`. Rejected even by `us_profile._extract_inline_
   quoted_definitions`'s idiom-gap check, since there is no
   "means"/"shall mean"/"has the meaning" anywhere nearby -- the
   parenthetical wrapping IS the defining signal here, not a trailing
   idiom.
2. **Cross-reference idiom** (`"Term" has the meaning given that term in
   ORS 153.005` / `has the meaning assigned by Section N`) -- e.g. OR's
   `STATE_OR_T41_C496_S496.716`. `_MEANS_IDIOM_GAP_RE` already matches
   "has the meaning" (confirmed live, sprint log), so this shape's real
   defect is REACHABILITY, not idiom recognition: it lives inside an
   ORDINARY (non-Definitions-heading) article body, which
   `USProfile.extract_local_scope_definitions` (the `ScopeTriggerRule`
   union) is the only live path into -- `extract_inline_quoted_
   definitions` is never reached for it at all.

Both shapes fire via TWO complementary dispatch paths, sharing one
apposition primitive (`_apposition_candidates`):

- A `ScopeTriggerRule` (`jurisdiction_codes=("US-*",)`) scans an ORDINARY
  article body directly -- this is how the real production pipeline
  reaches NH/ND's compact articles and OR's wildlife-inspection section
  (none of which have a "Definitions" heading), via `pipeline.py`'s
  already-profile-dispatched `extract_local_scope_definitions` call.
- A `TermClauseRule` + companion `EntrySplitterRule` pair covers the
  case where this shape appears inside a body that IS being parsed as a
  Definitions section but carries NO "(N)" entry markers at all (e.g.
  NH's own short-title row) -- baseline's block splitter yields zero
  blocks for such text, so (mirroring F5's TX-parent-redirect mechanism
  in `us_multiterm_shared_clause.py`) the `EntrySplitterRule`
  re-contributes the whole section text as one extra block, narrowly
  gated on the SAME apposition pattern, so `TermClauseRule.parse` has
  something to scan.

**Precision guard (P-R2 -- this family is FP-prone by nature, an
acknowledged trade-off, not a defect):** `_APPOSITION_RE` requires the
parenthesized quote to look like a genuine word/phrase (starts with a
letter, letters/spaces/hyphens only) -- this is what correctly REJECTS
OK's `("-..-")` map-marker (dash characters, no letters at all) while
still accepting `("withdrawing state")`/`(the "Act")`. The cross-reference
idiom scan reuses the same bounded, literal-idiom-word gap check the
existing (already-shipped, already-accepted) `_extract_inline_quoted_
definitions` uses for CA/IL/GA -- here applied to a broader population
(every ordinary US-* article body, not only placeholder-heading
Definitions sections), which is a real, acknowledged widening of this
family's false-positive surface. A corpus-wide FP measurement across all
53 jurisdictions is this sprint's own U4 zero-miss sweep (QA's remit, not
this module's) -- see this Developer's report to the sprint manager for
the explicit escalation.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    EntrySplitterRule,
    RuleContext,
    ScopeTriggerRule,
    TermClauseRule,
    register_entry_splitter_rule,
    register_scope_trigger_rule,
    register_term_clause_rule,
)

# --- Case 1: bare apposition, `("Term")` / `(the "Term")` -----------------

_APPOSITION_RE = re.compile(r'\((?:the\s+)?[“"]([A-Za-z][A-Za-z \-]{0,60})[”"]\)')

_SENTENCE_BOUNDARY_RE = re.compile(r"\.\s")


def _sentence_around(text: str, start: int, end: int) -> str:
    """The sentence containing `text[start:end]` -- bounded backward/
    forward by the nearest `". "`/`".\\n"`-style sentence break (or the
    text's own start/end), robust to real scrape formatting that joins
    sentences with a newline instead of a literal space after the
    period."""
    left_matches = list(_SENTENCE_BOUNDARY_RE.finditer(text, 0, start))
    left = left_matches[-1].end() if left_matches else 0
    right_match = _SENTENCE_BOUNDARY_RE.search(text, end)
    right = right_match.start() + 1 if right_match else len(text)
    return text[left:right].strip()


def _apposition_candidates(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Ruling M-R14: `text` is scanned unconditionally for EVERY apposition
    match, and a real acronym/short-title shorthand (`("ASAM")`, `("BOP")`,
    `("OSSE")`) is routinely (re-)named more than once in one article body
    for otherwise-unrelated sentences -- "one term, one candidate" (never
    one term, N candidates from the SAME body) is enforced here, at the
    extraction primitive both dispatch paths share, by keeping only the
    FIRST occurrence's `definition_text` per distinct term and skipping
    every later occurrence of an already-seen term outright."""
    candidates: list[DefinitionCandidate] = []
    seen_terms: set[str] = set()
    for m in _APPOSITION_RE.finditer(text):
        term = m.group(1).strip()
        if not term or term in seen_terms:
            continue
        definition_text = _sentence_around(text, m.start(), m.end())
        if not definition_text:
            continue
        seen_terms.add(term)
        candidates.append(DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope))
    return candidates


# --- Case 2: cross-reference / means idiom, scanned over an ORDINARY body -

_QUOTE_TERM_RE = re.compile(r'[“"]([^”"]{1,200})[”"]')
# Deliberately a TIGHT gap (whitespace/comma only, no arbitrary prose) --
# every real target shape (OR's cross-reference idioms) has the idiom
# word immediately after the closing quote. A wide gap (mirroring
# `us_profile._MEANS_IDIOM_GAP_RE`'s own 200-char allowance, which is
# safe there only because it is gated behind a placeholder-heading
# Definitions section) would false-positive broadly across ordinary
# bodies -- caught live: `"Term" applies only within subsection one of
# this section, and means ...` (an unrelated synthetic fixture in
# `test_definition_links_pipeline_cd_i10_scope_level_semantics_live.py`)
# has "means" ~58 characters after its own unrelated quoted term.
#
# Ruling E3 (program manager, corpus-measured; sprint log Residual ledger
# R3): the bare "means"/"shall mean" alternatives are DELETED here, not
# just gap-tightened. A plain quoted-term-then-"means" idiom inside an
# ORDINARY (non-Definitions) body is family 1's ("As used in this
# section:" scoped-inline) own mechanism, an active sibling sprint --
# keeping it here caused two panels to independently emit overlapping
# rows for the same corpus population (measured: 8.87% of sampled rows
# firing, 10.8% duplicate-term rows), corrupting both panels' U6
# before/after measurement. F6's own, non-overlapping remit is the
# CROSS-REFERENCE idiom specifically ("has the meaning given that term
# in <citation>" / "has the meaning assigned by <citation>") -- kept
# below, unchanged. One consequence, tracked as Residual ledger R3, not
# silently absorbed: OR's real row `STATE_OR_T41_C496_S496.716` defines
# 5 terms, 4 by cross-reference (still captured below) and one
# ("Taken") by plain "means" -- "Taken" is deliberately NOT captured by
# this rule anymore; it is family 1's to pick up, closing only on their
# own live proof against this exact row.
#
# QA finding 3: "as defined in <citation>" is a THIRD, distinct
# cross-reference idiom -- the single largest gap the U4 sweep found
# (2,813 real corpus occurrences). It is a genuine cross-reference (a
# term whose meaning is pointed at elsewhere), squarely F6's own remit,
# not family 1's plain-"means" territory E3 carved out above -- adding
# it does not reopen that boundary question.
_IDIOM_GAP_RE = re.compile(
    r"^[\s,]{0,5}\b(?:has the meaning given that term in"
    r"|has the meaning assigned by|as defined in)\b:?\s*",
    re.IGNORECASE,
)


def _cross_reference_candidates(text: str, *, scope: str) -> list[DefinitionCandidate]:
    entries: list[tuple[str, int, int]] = []
    for term_match in _QUOTE_TERM_RE.finditer(text):
        gap = text[term_match.end() : term_match.end() + 250]
        idiom_match = _IDIOM_GAP_RE.match(gap)
        if idiom_match is None:
            continue
        term = term_match.group(1).strip()
        if not term:
            continue
        entries.append((term, term_match.start(), term_match.end() + idiom_match.end()))

    candidates: list[DefinitionCandidate] = []
    for index, (term, _start, definition_start) in enumerate(entries):
        end = entries[index + 1][1] if index + 1 < len(entries) else min(len(text), definition_start + 400)
        definition_text = text[definition_start:end].strip()
        if not definition_text:
            continue
        candidates.append(DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope))
    return candidates


# --- Dispatch: ScopeTriggerRule (ordinary article body, real production) --


def _extract_ordinary_body(article_body: str, _ctx: RuleContext) -> list[DefinitionCandidate]:
    return _apposition_candidates(article_body, scope="local") + _cross_reference_candidates(
        article_body, scope="local"
    )


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract_ordinary_body))


# --- Dispatch: TermClauseRule + EntrySplitterRule (blocks inside a
# recognized Definitions section, or a marker-less body being parsed as
# one, e.g. NH's own short-title row) ---------------------------------------

# QA finding 4: baseline's own `_leading_quote_candidate` already
# correctly handles a block whose OWN leading quote is immediately
# followed by a cross-reference idiom (e.g. TX's `"Governmental body"
# has the meaning assigned by Section 552.003.`) -- wiring
# `_cross_reference_candidates` into every block unconditionally would
# double-emit exactly that already-working shape (M-R12). This mirrors
# baseline's own `_LEADING_QUOTE_RE.match(block)` check (not imported --
# `us_profile.py` stays untouched and its internals stay private) to
# skip only a term baseline's leading-quote parse would already produce
# for THIS block, while still capturing a cross-reference idiom sitting
# anywhere else inside the block (e.g. DC's `"Parent. -- The term
# \"parent\" has the meaning given that term in section 8101..."`,
# which does NOT start with a quote, so baseline never touches it).
_LEADING_QUOTE_TERM_RE = re.compile(r'^[“"]([^”"]+)[”"]')


def _leading_quote_term(block: str) -> str | None:
    m = _LEADING_QUOTE_TERM_RE.match(block)
    return m.group(1) if m else None


def _parse_block(block: str) -> list[DefinitionCandidate]:
    candidates = _apposition_candidates(block, scope="law-wide")
    leading_term = _leading_quote_term(block)
    for candidate in _cross_reference_candidates(block, scope="law-wide"):
        if candidate.terms and candidate.terms[0] == leading_term:
            continue
        candidates.append(candidate)
    return candidates


# Ruling U-R10 (program, binding): see the identical rationale in
# `rules/us_multiterm_shared_clause.py` -- `entry_splitter` contributions
# are additive across every panel scanning every US-* body. Empirically
# derived: only US-NH has a currently-accepted item needing this
# splitter (NH's OTHER apposition rows reach the shape through the
# `ScopeTriggerRule` registration above instead, a different rule kind,
# unaffected by this narrowing). Same 2000-char bound as the sibling
# module, same evidence (>2.2x headroom over the largest real accepted
# row, 99 chars here; >5.6x under markers' 11,314-char worst case).
_MAX_CONTRIBUTION_CHARS = 2000


def _split_apposition_whole_text(text: str) -> list[str]:
    if len(text) > _MAX_CONTRIBUTION_CHARS:
        return []
    return [text] if _APPOSITION_RE.search(text) else []


register_term_clause_rule(TermClauseRule(jurisdiction_codes=("US-*",), parse=_parse_block))
register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("US-NH",), split=_split_apposition_whole_text)
)
