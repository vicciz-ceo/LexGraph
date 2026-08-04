"""Sprint 2026-08-04-defs-us-scoped-inline, fix cycle 2 (Developer). Sanctioned
style-gate overflow from `us_scoped_inline.py` (that module's docstring,
"Sanctioned overflow" -- `us_scoped_inline.py` was already at the 300-line
style-gate ceiling before this cycle's fixes). Holds the BODY-SHAPE regex
vocabulary and the entry-splitting helpers: everything that operates on an
already-located trigger region and does not need `_SCOPE_BY_UNIT` or
`DefinitionCandidate`. Deliberately NOT a `ScopeTriggerRule` -- it calls no
`register_*` function and has no import-time side effects, so
`rules/__init__.py`'s auto-discovery (every sibling module in this package
gets imported at package-import time) can safely import this file without
adding new dispatch surface. Does not import `us_scoped_inline` (would be
circular); `us_scoped_inline.py` imports FROM here.

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
"""

from __future__ import annotations

import re

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
