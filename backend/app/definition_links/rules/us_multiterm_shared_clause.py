"""Rule module: F5 multi-term shared-clause definitions (sprint
2026-08-04-defs-us-multiterm, items 1-3).

`"The term(s) "X"[, "Y"[, and "Z"]] mean(s) ..."` -- one clause defines
several terms at once. `USProfile`'s baseline block parser
(`_leading_quote_candidate`, `us_profile.py`) only ever recovers the FIRST
quoted span of a block via `_LEADING_QUOTE_RE.match(block)` -- every other
co-defined term is silently dropped into that first term's own
`definition_text` as dead prose.

Three real shapes, sharing one extraction primitive (`_extract_leading_
terms`, porting the "scan a run of quoted spans, then check what follows"
logic Hebrew's `extract._parse_terms_and_qualifier` already uses to
English's comma/"and" list convention):

1. **Top-level list** (MI real row): a block's OWN leading content is 2+
   quoted terms joined by comma/"and", immediately followed by
   "mean(s)". Fires ONLY for >=2 terms -- a lone leading quote is exactly
   what baseline already parses correctly, and re-emitting it here would
   double-count the working baseline states (M-R12).
2. **Nested clause** (MT real row): the SAME quoted-run-then-idiom shape,
   but introduced by a "the term(s)" trigger phrase ANYWHERE inside a
   block's OWN body (not just its leading position) -- e.g. entry
   "Affiliate"'s own definition text embeds "the terms \"owns,\" \"is
   owned\" and \"ownership\" mean ...". Fires for >=1 term (unlike case
   1): baseline never looks past a block's own leading quote, so there is
   no baseline behavior here to collide with, and a lone nested term
   ("...and the term \"person\" means...") is recovered as a natural
   side effect of the identical mechanism -- not special-cased.
3. **Parent-clause redirect** (TX real rows): "(4) The following terms
   have the meanings assigned by Section 2001.003:" followed by a
   LETTERED list of bare quoted term names ("(A) \"contested case\"; (B)
   \"party\"; ..."). The parent line and its children are FIVE SEPARATE
   baseline blocks (the parent has no leading quote so baseline drops it
   outright; each child is its own quote-anchored block whose
   `definition_text` is just trailing punctuation). No single
   already-split block contains both the redirect text and the term
   list, so `TermClauseRule.parse`'s one-block signature cannot bridge
   them alone -- a companion `EntrySplitterRule`, gated narrowly on this
   exact redirect phrase, re-contributes the WHOLE section text as one
   extra block so `parse` can see parent+children together and emit ONE
   combined N-term candidate. That candidate gets its OWN new `Definition`
   row (its `.terms` tuple differs from any single child's, so
   pipeline.py's existing `(article_id, sorted(terms))` dedup key never
   collides with the degenerate per-child rows) and, because
   `USProfile.extract_definitions_from_section` runs every registered
   `TermClauseRule` strictly AFTER baseline's own per-block pass, it is
   always created LATER than the degenerate rows -- which is exactly what
   makes a term-keyed lookup built from `created_definitions` (as both
   this sprint's integration tests and `pipeline.py` itself do) resolve
   to the correct, later-created row.

Every helper below only ever ADDS a new candidate for a shape baseline
demonstrably does not already produce a correct candidate for; nothing
here removes, reorders, or mutates a baseline-produced candidate.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    EntrySplitterRule,
    TermClauseRule,
    register_entry_splitter_rule,
    register_term_clause_rule,
)

# --- Shared primitive: scan a run of quoted spans -------------------------

# No leading `^` on any of these: they are matched via `.match(text, pos)`
# with a `pos` that is usually NOT 0, and Python's `^` anchors to the
# TRUE start of the string, not to `pos` -- `.match()` already anchors
# the attempt at `pos` on its own, so `^` here would silently make every
# non-zero-`pos` call fail instead of matching (a real bug caught live
# while verifying this module against the real MI fixture row).
_QUOTE_START_RE = re.compile(r'[“"]([^”"]+)[”"]')
_TERM_SEP_RE = re.compile(r"(?:\s*,\s*and\s+|\s*,\s*|\s+and\s+|\s+)", re.IGNORECASE)
_IDIOM_RE = re.compile(r"[\s,]*\b(?:means?|shall\s+mean)\b", re.IGNORECASE)


def _extract_leading_terms(text: str, pos: int) -> tuple[list[str], int]:
    """Scan a run of quoted spans starting at `pos`, each pair joined by a
    comma/"and" separator. Returns `(terms, end_pos)` where `end_pos` is
    the position right after the LAST matched quote -- a trailing
    separator is only ever consumed when ANOTHER quote follows it, so a
    lone match never swallows unrelated punctuation. Each term is
    right-stripped of a trailing comma/semicolon picked up from real
    drafting that places serial-list punctuation INSIDE the closing quote
    (e.g. MT's `"owns,"`)."""
    terms: list[str] = []
    cursor = pos
    while True:
        m = _QUOTE_START_RE.match(text, cursor)
        if m is None:
            break
        terms.append(m.group(1).rstrip(" ,;"))
        end = m.end()
        sep = _TERM_SEP_RE.match(text, end)
        if sep is not None and _QUOTE_START_RE.match(text, sep.end()) is not None:
            cursor = sep.end()
            continue
        cursor = end
        break
    return terms, cursor


# --- Case 1: top-level leading multi-term list (MI shape) -----------------


def _leading_multiterm_candidate(block: str) -> DefinitionCandidate | None:
    terms, end = _extract_leading_terms(block, 0)
    if len(terms) < 2:
        # Exactly what baseline's own `_leading_quote_candidate` already
        # handles correctly -- returning None here is what keeps this
        # rule from double-emitting on every ordinary single-term block
        # across every US-* jurisdiction (M-R12).
        return None
    if _IDIOM_RE.match(block, end) is None:
        return None
    definition_text = block[end:].strip()
    if not definition_text:
        return None
    return DefinitionCandidate(terms=tuple(terms), definition_text=definition_text, scope="law-wide")


# --- Case 2: nested clause anywhere inside a block's own body (MT shape) --

_NESTED_TRIGGER_RE = re.compile(r"\bthe\s+terms?\b\s*", re.IGNORECASE)
# Ruling M-R14 (QA finding 2): trims a trailing ", and"/" and" chain-link
# off a clause's own definition_text -- used only AFTER the boundary is
# already known (the NEXT trigger's own start), not to LOCATE the
# boundary itself (that was the old, defective design: searching ahead
# for an "and"-chained continuation specifically overshoots past every
# UNCHAINED, independent "The term X means Y." sentence in between,
# silently dropping all of them -- real AL row, 18 triggers in one
# block, only 2 ever recovered before this fix).
_TRAILING_CHAIN_LINK_RE = re.compile(r",?\s*and\s*$", re.IGNORECASE)


def _nested_clause_candidates(block: str) -> list[DefinitionCandidate]:
    """Every "the term(s)" trigger is its OWN clause, full stop -- the
    boundary between clause N and clause N+1 is simply wherever trigger
    N+1 itself starts (whether N+1 is "and"-chained to N or an entirely
    independent sentence later in the block), trimmed of any trailing
    chain-link text. This makes each trigger's own candidate fully
    independent of whether ITS neighbours succeed or fail their own
    idiom check -- no cursor/skip bookkeeping needed."""
    candidates: list[DefinitionCandidate] = []
    triggers = list(_NESTED_TRIGGER_RE.finditer(block))
    for index, trigger in enumerate(triggers):
        terms, end = _extract_leading_terms(block, trigger.end())
        if not terms:
            # "the term(s)" not immediately followed by a quote -- an
            # ordinary phrase like "the term includes" or "the terms of
            # this agreement", not a definition clause.
            continue
        if _IDIOM_RE.match(block, end) is None:
            continue
        stop = triggers[index + 1].start() if index + 1 < len(triggers) else len(block)
        definition_text = _TRAILING_CHAIN_LINK_RE.sub("", block[end:stop]).strip()
        if definition_text:
            candidates.append(
                DefinitionCandidate(terms=tuple(terms), definition_text=definition_text, scope="law-wide")
            )
    return candidates


# --- Case 3: parent-clause redirect + lettered children (TX shape) --------

_PARENT_REDIRECT_RE = re.compile(
    r"(?P<intro>The following terms?\s+have\s+the\s+meanings?\s+assigned\s+by\s+[^:\n]+):\s*",
    re.IGNORECASE,
)
_LETTERED_TERM_RE = re.compile(r'\s*\([A-Za-z]+\)\s*[“"]([^”"]+)[”"]\s*[;.,]?\s*(?:and\s*)?')


def _parent_redirect_candidates(text: str) -> list[DefinitionCandidate]:
    candidates: list[DefinitionCandidate] = []
    for parent in _PARENT_REDIRECT_RE.finditer(text):
        terms: list[str] = []
        cursor = parent.end()
        while True:
            m = _LETTERED_TERM_RE.match(text, cursor)
            if m is None:
                break
            terms.append(m.group(1))
            cursor = m.end()
        if len(terms) < 2:
            continue
        definition_text = f'{parent.group("intro").strip()}.'
        candidates.append(DefinitionCandidate(terms=tuple(terms), definition_text=definition_text, scope="law-wide"))
    return candidates


def _has_parent_redirect_with_children(text: str) -> bool:
    for parent in _PARENT_REDIRECT_RE.finditer(text):
        if _LETTERED_TERM_RE.match(text, parent.end()) is not None:
            return True
    return False


# Ruling U-R10 (program, binding): `entry_splitter` is additive across
# EVERY panel scanning EVERY US-* body (`all_blocks = baseline_blocks +
# extra_blocks`), so a `US-*`-wide whole-section contribution inflates
# every other panel's block population too, not just this sprint's own.
# Empirically derived (disable-and-measure, not guessed -- see the
# Planner's RED test module docstring for the exact kill-experiment
# output): only US-TX has a currently-accepted item needing this
# splitter. 2000 chars is >2.2x headroom over the largest real accepted
# row (881 chars) and >5.6x under markers' measured 11,314-char worst
# case.
_MAX_CONTRIBUTION_CHARS = 2000


def _split_parent_redirect_whole_text(text: str) -> list[str]:
    # A per-block `EntrySplitterRule` cannot see the parent's own text and
    # its lettered children at once (baseline already splits them into
    # separate blocks) -- re-contribute the WHOLE section text as one
    # extra block, gated narrowly so this never fires for a section that
    # doesn't contain the redirect shape at all, and bounded so it can
    # never contribute an unbounded whole-section blob even for the
    # in-scope jurisdiction (U-R10).
    if len(text) > _MAX_CONTRIBUTION_CHARS:
        return []
    return [text] if _has_parent_redirect_with_children(text) else []


# --- Dispatch ---------------------------------------------------------------


def _parse(block: str) -> list[DefinitionCandidate]:
    candidates: list[DefinitionCandidate] = []
    leading = _leading_multiterm_candidate(block)
    if leading is not None:
        candidates.append(leading)
    candidates.extend(_nested_clause_candidates(block))
    candidates.extend(_parent_redirect_candidates(block))
    return candidates


register_term_clause_rule(TermClauseRule(jurisdiction_codes=("US-*",), parse=_parse))
register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("US-TX",), split=_split_parent_redirect_whole_text)
)
