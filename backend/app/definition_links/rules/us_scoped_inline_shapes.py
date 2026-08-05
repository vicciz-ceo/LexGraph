"""Sprint 2026-08-04-defs-us-scoped-inline, fix cycles 2-4 (Developer).
Sanctioned style-gate overflow from `us_scoped_inline.py` (that module's
docstring, "Sanctioned overflow" -- `us_scoped_inline.py` was already at
the 300-line style-gate ceiling before cycle 2's fixes, and again before
cycle 3's). Holds the BODY-SHAPE regex vocabulary, the entry-splitting
helpers, and (cycle 3, revised cycle 4 per D-S15) the subsection-scope
derivation: everything that
operates on an already-located trigger region/offset and does not need
`_SCOPE_BY_UNIT` or `DefinitionCandidate` directly (`_resolve_subsection_
scope` returns a bare tuple, not a `DefinitionCandidate` -- the caller in
`us_scoped_inline.py` builds that). Deliberately NOT a `ScopeTriggerRule`
-- it calls no `register_*` function and has no import-time side effects,
so `rules/__init__.py`'s auto-discovery (every sibling module in this
package gets imported at package-import time) can safely import this file
without adding new dispatch surface. Does not import `us_scoped_inline`
(would be circular); `us_scoped_inline.py` imports FROM here.

QA cycle-1 root causes fixed in this module (full detail in
`us_scoped_inline.py`'s docstring and this sprint's report):

  2. Period-style list markers (`1.` `2.`, not just `(1)` `(2)`) --
     `_MARKER_RE` now accepts either.
  1. Unmarked colon-then-quoted-list (the most severe miss: the entire
     block was lost, not merely under-split) -- `_unmarked_multi_entries`,
     a new fallback tried only when the marker-based `_multi_entries`
     finds nothing.
  7. Plural `have the same meaning as` (`_IDIOM_RE` recognized only
     singular `has`).
  8. Bare copula `is` (measured for false-positive surface against the
     real corpus per program ruling D-Q1 -- see the sprint report; shipped
     unnarrowed, ~0% FP in a 40-row hand-inspected sample of 846 corpus-wide
     new candidates).
  (Also: a "X" or "Y" alias chain -- `_match_quote_chain` -- needed to even
  REACH the Tennessee row's plural `have` idiom, since its two terms share
  one idiom via "or".)

Fix cycle 3 (ruling S-R14, the subsection revert): `_resolve_subsection_
scope`/`_subsection_scope_level` moved here (not left in `us_scoped_
inline.py`) purely for the 300-line style gate -- see that module's
docstring for the full S-R9/S-R10/S-R11/S-R14/S-R15/D-S15 design
reasoning, repeated here only where load-bearing for these two functions
themselves.

Fix cycle 4 (director ruling D-S15, supersedes S-R15): `_subsection_
scope_level` now returns the OUTERMOST step of the resolved path, not the
innermost -- see that function's own docstring for the SC live-path
evidence and the corpus-wide vocabulary census. `_resolve_subsection_
scope` itself is UNCHANGED: same resolver call, same zero-miss `"local"`
degrade on an empty path, same same-step stamping of `scope_value`/
`scope_unit_kind` -- only WHICH step `_subsection_scope_level` picks moved.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from app.definition_links.us_profile import resolve_unit_path

# Connector between a STRONG trigger's unit word and the definiendum.
# Root cause 4 (intervening secondary citation clause, e.g. Delaware's "As
# used in this section AND IN Section 15-105 of this title, the term..."):
# tolerates one optional "and [in] <citation text>" clause -- bounded to
# stop at the next comma/colon (the real connector), never swallowing past
# it -- before the rest of the connector vocabulary.
# Root cause 5 (DC's "the term:" -- no space before the colon) and root
# cause 7 (Tennessee's plural "the terms ... have"): "the term(s)" now uses
# a `\b` word boundary instead of requiring trailing whitespace, so it
# can't over-consume into "terms" nor refuse a colon glued directly onto
# "term".
# Root cause 6 (NY's "shall have the following meanings", MS's "shall have
# meanings as follows"): added alongside the existing "the following terms
# mean(s)" phrasing.
_STRONG_CONNECTOR_RE = re.compile(
    r"\s*"
    r"(?:and\s+(?:in\s+)?[^,:]{0,120})?"
    r"\s*(?:,\s*)?"
    r"(?:"
    r"the following terms?\s+(?:mean|means|shall have(?:\s+the following)?\s+meanings?(?:\s+as\s+follows)?)\s*"
    r"|shall have\s+(?:the following\s+)?meanings?(?:\s+as\s+follows)?\s*"
    r")?"
    r"(?:the terms?\b\s*|an?\s+)?"
    r"(?P<colon>:)?\s*",
    re.IGNORECASE,
)

# Strict: only a comma or a colon, no filler words -- the bare-`in` trigger's
# load-bearing adjacency gate (QA cycle-1 mutation testing target). NOT
# touched by this fix cycle.
_BARE_CONNECTOR_RE = re.compile(r"\s*(?:(?P<colon>:)|(?P<comma>,))?\s*")

_QUOTE_TERM_RE = re.compile(r'["“](?P<term>[^"”]+?),?["”]')

# Root cause 7's Tennessee row aliases two quoted terms with a shared idiom
# ("the terms "X" or "Y" have the same meaning as..."): a chain of quotes
# joined by literal "or" (optionally comma-preceded) all share ONE
# definition. A bare comma alone does NOT continue the chain -- that stays
# reserved for separate marked/unmarked list entries.
_QUOTE_CHAIN_SEP_RE = re.compile(r"\s*(?:,\s*)?or\s*", re.IGNORECASE)

# Root cause 2 (Florida's period-style "1." "2." list markers, not just
# parenthesized "(1)" "(2)"): a bare 1-3 digit number followed by a literal
# period is now ALSO a valid marker. Still gated by `_MARKER_QUOTE_RE`'s
# immediate (whitespace-only) adjacency to a quote -- the same precision
# mechanism as before, just a wider marker-syntax vocabulary, never a wider
# gap tolerance (that gate stays load-bearing, untouched: see
# `us_scoped_inline.py`'s docstring).
_MARKER_RE = r"(?:\((?:[0-9]{1,3}|[A-Za-z]{1,3})\)|(?<!\d)[0-9]{1,3}\.)"
_MARKER_QUOTE_RE = re.compile(rf'{_MARKER_RE}\s*["“]')

# Root cause 7 (plural "have the same meaning as") and root cause 8 (bare
# copula "is", measured -- see module docstring and the sprint report's
# D-Q1 section) added to the existing idiom vocabulary. Order matters:
# "is defined as" is tried before bare "is" so the longer, more specific
# phrase wins when both are present.
_IDIOM_RE = re.compile(
    r"\s*(?:has the same meaning as|have the same meaning as|has the meaning"
    r"|shall be construed to mean"
    r"|shall mean|does not include|is defined as|includes?|means|is)\b,?\s*",
    re.IGNORECASE,
)

_COMMA_SEP_RE = re.compile(r"\s*,\s*")
_SENTENCE_BOUNDARY_RE = re.compile(r"\.\s")
_LEADING_WS_RE = re.compile(r"\s*")


def _find_entry_end(body: str, def_start: int, boundary: int) -> int:
    """Nearer of the next marker-adjacent quote (a new entry) or the next
    sentence boundary, bounded by `boundary` (region end or next entry)."""
    marker_match = _MARKER_QUOTE_RE.search(body, def_start, boundary)
    period_match = _SENTENCE_BOUNDARY_RE.search(body, def_start, boundary)
    ends = [m.start() for m in (marker_match, period_match) if m]
    return min(ends) if ends else boundary


def _match_quote_chain(body: str, pos: int, boundary: int) -> tuple[tuple[str, ...], int]:
    """A quote at `pos`, plus any further quotes chained onto it by a
    literal "or" (root cause 7's TN alias shape) -- e.g. `"X" or "Y"`.
    Returns `((), pos)` (empty terms, unchanged position) if `pos` is not
    itself a quote."""
    terms: list[str] = []
    cur = pos
    while True:
        quote_match = _QUOTE_TERM_RE.match(body, cur, boundary)
        if not quote_match:
            break
        term = quote_match.group("term").strip()
        if not term:
            break
        terms.append(term)
        cur = quote_match.end()
        sep_match = _QUOTE_CHAIN_SEP_RE.match(body, cur, boundary)
        if not sep_match:
            break
        cur = sep_match.end()
    return (tuple(terms), cur) if terms else ((), pos)


def _split_idiom_chain(
    body: str, terms: tuple[str, ...], chain_end: int, boundary: int
) -> tuple[tuple[str, ...], str, int] | None:
    """`terms` is the (one or more) quoted term(s) from `_match_quote_chain`,
    `chain_end` the position right after them. Returns
    `(terms, definition_text, entry_end)` -- `entry_end` is exposed (not
    just the stripped text) so `_unmarked_multi_entries` can resume
    scanning for a FOLLOW-ON entry from the right place."""
    idiom_match = _IDIOM_RE.match(body, chain_end, boundary)
    if idiom_match:
        def_start = idiom_match.end()
    else:
        comma_match = _COMMA_SEP_RE.match(body, chain_end, boundary)
        if not comma_match:
            return None
        def_start = comma_match.end()
    entry_end = _find_entry_end(body, def_start, boundary)
    definition_text = body[def_start:entry_end].strip()
    return (terms, definition_text, entry_end) if definition_text else None


def _single_entry(body: str, region_start: int, region_end: int) -> list[tuple[tuple[str, ...], str]]:
    ws = _LEADING_WS_RE.match(body, region_start, region_end)
    pos = ws.end() if ws else region_start
    terms, chain_end = _match_quote_chain(body, pos, region_end)
    if not terms:
        return []
    entry = _split_idiom_chain(body, terms, chain_end, region_end)
    return [(entry[0], entry[1])] if entry else []


def _multi_entries(body: str, region_start: int, region_end: int) -> list[tuple[tuple[str, ...], str]]:
    markers = list(_MARKER_QUOTE_RE.finditer(body, region_start, region_end))
    entries: list[tuple[tuple[str, ...], str]] = []
    for i, marker_match in enumerate(markers):
        boundary = markers[i + 1].start() if i + 1 < len(markers) else region_end
        terms, chain_end = _match_quote_chain(body, marker_match.end() - 1, boundary)
        if not terms:
            continue
        entry = _split_idiom_chain(body, terms, chain_end, boundary)
        if entry:
            entries.append((entry[0], entry[1]))
    return entries


def _unmarked_multi_entries(body: str, region_start: int, region_end: int) -> list[tuple[tuple[str, ...], str]]:
    """Root cause 1 fix: a colon-then-quoted-list with NO per-entry marker
    (Illinois: `"As used in this Section: "X" means... "Y" means..."`;
    Virginia: seven terms separated only by blank lines) -- the single most
    severe QA cycle-1 miss, where `_multi_entries` finding zero markers
    meant the ENTIRE block was silently dropped, not merely under-split.

    Only ever called as a fallback AFTER `_multi_entries` returns nothing
    (see `extract_us_scoped_inline_definitions`), and only ever advances
    entry-to-entry through content immediately (whitespace/period-only)
    adjacent to the previous entry's end -- it can never skip over
    unrelated intervening prose to pick up some later, unrelated quote,
    which is what keeps this fallback from becoming a new false-positive
    surface. Stops at the first entry that fails to parse (conservative by
    design, same rationale as the marker-adjacency gate: an ambiguous stop
    is safer than guessing which later quote resumes the list)."""
    entries: list[tuple[tuple[str, ...], str]] = []
    pos = region_start
    while pos < region_end:
        ws = _LEADING_WS_RE.match(body, pos, region_end)
        p = ws.end() if ws else pos
        terms, chain_end = _match_quote_chain(body, p, region_end)
        if not terms:
            break
        entry = _split_idiom_chain(body, terms, chain_end, region_end)
        if not entry:
            break
        entries.append((entry[0], entry[1]))
        entry_end = entry[2]
        skip = re.match(r"[.\s]*", body[entry_end:region_end])
        next_pos = entry_end + (skip.end() if skip else 0)
        if next_pos <= pos:
            break  # guard against a zero-width loop on malformed input
        pos = next_pos
    return entries


def _subsection_scope_level(path):
    """D-S15 (director ruling, supersedes S-R15 -- cite D-S15 when changing
    this again): WHICH step of core's `resolve_unit_path` result a
    subsection trigger's `scope_value`/`scope_unit_kind` are drawn from.
    Adopted semantics: the OUTERMOST step (`path[0]`) -- "as used in this
    subsection" scopes to the top-level subdivision, not to whatever unit
    happens to be innermost at the trigger's own offset. Evidence: on
    `STATE_SC_T12_C6_A9_S12-6-1170` (structure `(A)(1)..(4)`, definition in
    item (2)), the innermost step stamps `('2', digit)` and links 0 of 4
    genuine reuses, while the outermost step stamps `('A', upper_alpha)`
    and links all 4; a corpus-wide census of the drafters' own vocabulary
    found 202,943 phrases placing "subsection" directly under "section"
    across 48 of 53 jurisdictions, against only 12 inverted occurrences.
    Named follow-up (not this cycle): SD/NY/VT genuinely nest subsection
    under subdivision and are not covered by this default. This stays the
    ONE swappable decision point -- D-S15 preserves that property, so
    answering a future per-state question is still a one-line change here,
    never a redesign scattered across call sites."""
    return path[0]


def _resolve_subsection_scope(body: str, trigger_start: int) -> tuple[str, str | None, str | None]:
    """S-R14: the single derivation, replacing the old two-derivation
    defect family (S-R10/S-R11) -- this module no longer guesses its own
    subsection label from glyph shape; it asks CORE's own
    `resolve_unit_path` for the unit step open at the TRIGGER's own char
    offset and stamps `scope_value`/`scope_unit_kind` from that SAME step.
    `resolve_unit_path` only reads `.body` (below-article `UnitPath`,
    v2.4), so a bare `SimpleNamespace(body=body)` stands in for a full
    `MatcherArticle` -- the caller already has the body and the trigger
    offset, nothing else is needed.

    Zero-miss fallback (S-R9/S-R11/S-R14 precedent): some states number
    subsections in a style core's `_US_UNIT_MARKER_RE` cannot see at all
    (PARENTHESIZED markers only -- Maine's "2-A.", Florida's "1." are
    invisible to it), so `resolve_unit_path` returns an EMPTY path at the
    trigger offset. A `scope="subsection"` candidate stamped anyway would
    be guaranteed to link NOTHING. Degrade to `"local"` instead -- the
    narrowest REPRESENTABLE enclosing unit -- rather than ship a scope
    that can never match; precision cost measured (sprint report), not
    silently dropped.
    """
    path = resolve_unit_path(SimpleNamespace(body=body), char_offset=trigger_start)
    if not path:
        return "local", None, None
    step = _subsection_scope_level(path)
    return "subsection", step.value, step.kind
