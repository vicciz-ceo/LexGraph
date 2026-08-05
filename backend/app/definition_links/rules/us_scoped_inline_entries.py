"""Sprint 2026-08-04-defs-us-scoped-inline, fix cycle 5 (Developer). Second
sanctioned style-gate overflow module (same pattern as
`us_scoped_inline_shapes.py`'s own docstring, "Sanctioned overflow" -- that
module was itself back at the 300-line ceiling once this cycle's QA
cycle-2 vocabulary widenings landed). Holds the ENTRY-SPLITTING mechanics
-- the functions that walk an already-located trigger REGION and cut it
into `(terms, definition_text)` pairs -- while `us_scoped_inline_shapes.py`
keeps the trigger/idiom VOCABULARY regexes and the subsection-scope
derivation. Imports the vocabulary regexes it needs FROM that module
(`_MARKER_QUOTE_RE`, `_IDIOM_RE`, `_QUOTE_CHAIN_SEP_RE`); does not import
`us_scoped_inline` (would be circular) and calls no `register_*` function,
so `rules/__init__.py`'s auto-discovery can safely import this file too --
same sanctioned, import-safe, no-new-dispatch-surface pattern.

QA cycle-2 root causes fixed here (full corpus-wide measurement in this
sprint's report; `us_scoped_inline.py`'s own docstring lists all 6, the
other 4 living in `us_scoped_inline_shapes.py`/`us_scoped_inline.py`):

  6. `_single_entry` (the non-colon path) only ever extracted the FIRST
     quote-chain-then-idiom entry in its region and returned -- a second,
     independent `and "Y" means Z` entry sharing the SAME region (no
     colon, no marker, so neither `_multi_entries` nor `_unmarked_multi_
     entries` is ever even reached) was silently dropped. `_single_entry`
     now loops, but ONLY ever continues onto a further entry immediately
     (whitespace/comma-only) introduced by a literal `and` directly
     adjacent to a FRESH quote (`_AND_QUOTE_ENTRY_RE`) -- the same
     bounded-adjacency precision philosophy as `_QUOTE_CHAIN_SEP_RE` and
     the marker-quote gate, just applied at the ENTRY boundary (two
     independent idioms) instead of the quote-CHAIN boundary (one shared
     idiom -- finding 3's job, `us_scoped_inline_shapes.py`). Critically,
     the and-quote boundary is only ever searched for WITHIN an entry's
     own already-computed natural extent (`_find_entry_end`'s own,
     unbounded-by-this-mechanism result) -- never beyond it -- so a region
     that runs to the end of a long article body can never have this
     mechanism reach past unrelated, far-away prose to manufacture a
     spurious split; it can only ever TIGHTEN an entry's own boundary,
     never extend a search past it.

  2 (D-INCLUDES targeted guard). Program ruling D-INCLUDES authorizes the
     `includes`-family verbs (`includes`/`shall include`) into the naive
     quoted-term-anchor vocabulary program-wide (100/100 hand-read
     definitional across two independent seeds; tightened guards measured
     to cost 32-56% of TRUE definitions for no measured precision gain --
     rejected). The ONE narrow guard the ruling DOES require survives
     here: `_preceded_by_references_to` suppresses an entry only when its
     OWN term-starting quote is immediately (whitespace-only) preceded by
     "References to"/"references to" -- the PA `References to "X" shall
     include Y` construction-clause shape (a rule about how OTHER text
     should be read, not a `"X" means Y`-shaped definition). Measured: 22
     real construction-clause rows protected vs. 4,729 genuine
     `includes`-family recall rows kept (program log, D-INCLUDES). Wired
     into all three entry-start call sites below (`_single_entry`,
     `_multi_entries`, `_unmarked_multi_entries`) -- never a broad
     idiom-absence trick, which the ruling explicitly rejected.
"""

from __future__ import annotations

import re

from app.definition_links.rules.us_scoped_inline_shapes import (
    _IDIOM_RE,
    _MARKER_QUOTE_RE,
    _QUOTE_CHAIN_SEP_RE,
)

_QUOTE_TERM_RE = re.compile(r'["“](?P<term>[^"”]+?),?["”]')
_COMMA_SEP_RE = re.compile(r"\s*,\s*")
_SENTENCE_BOUNDARY_RE = re.compile(r"\.\s")
_LEADING_WS_RE = re.compile(r"\s*")

# Finding 6: an "and"-introduced follow-on ENTRY (two INDEPENDENT idioms,
# e.g. `"X" means A ... and "Y" means B`) -- distinct from
# `_QUOTE_CHAIN_SEP_RE`'s "or"/"and" (finding 3: a chain of terms sharing
# ONE idiom, checked immediately after a quote, before any idiom has even
# been looked for). This one only ever fires once an entry's own idiom and
# definition text have already been found, immediately (whitespace/
# comma-only) before a FRESH quote.
_AND_QUOTE_ENTRY_RE = re.compile(r"\s*,?\s*and\s+(?=[\"“])", re.IGNORECASE)

# D-INCLUDES targeted guard (program ruling, scoped-inline QA2 item 11):
# suppress an entry ONLY when its term-starting quote is immediately
# preceded by "References to" -- see this module's own docstring.
_REFERENCES_TO_GUARD_RE = re.compile(r"references?\s+to\s*$", re.IGNORECASE)


def _preceded_by_references_to(body: str, pos: int) -> bool:
    window = body[max(0, pos - 32) : pos]
    return bool(_REFERENCES_TO_GUARD_RE.search(window))


def _find_entry_end(body: str, def_start: int, boundary: int) -> int:
    """Nearer of the next marker-adjacent quote (a new entry) or the next
    sentence boundary, bounded by `boundary` (region end or next entry)."""
    marker_match = _MARKER_QUOTE_RE.search(body, def_start, boundary)
    period_match = _SENTENCE_BOUNDARY_RE.search(body, def_start, boundary)
    ends = [m.start() for m in (marker_match, period_match) if m]
    return min(ends) if ends else boundary


def _match_quote_chain(body: str, pos: int, boundary: int) -> tuple[tuple[str, ...], int]:
    """A quote at `pos`, plus any further quotes chained onto it by a
    literal "or"/"and" (root cause 7's TN alias shape, widened by finding
    3) -- e.g. `"X" or "Y"` / `"X" and "Y"`. Returns `((), pos)` (empty
    terms, unchanged position) if `pos` is not itself a quote."""
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
    just the stripped text) so callers can resume scanning for a FOLLOW-ON
    entry from the right place."""
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
    """Finding 6: loops to also pick up a follow-on "and "Y" means Z" entry
    sharing this same non-colon region -- see module docstring for why the
    and-quote search is always bounded to an entry's OWN already-computed
    natural extent, never beyond it."""
    ws = _LEADING_WS_RE.match(body, region_start, region_end)
    pos = ws.end() if ws else region_start
    entries: list[tuple[tuple[str, ...], str]] = []
    while True:
        if _preceded_by_references_to(body, pos):
            break
        terms, chain_end = _match_quote_chain(body, pos, region_end)
        if not terms:
            break
        entry = _split_idiom_chain(body, terms, chain_end, region_end)
        if not entry:
            break
        and_match = _AND_QUOTE_ENTRY_RE.search(body, chain_end, entry[2])
        if and_match:
            truncated = _split_idiom_chain(body, terms, chain_end, and_match.start())
            if truncated:
                entries.append((truncated[0], truncated[1]))
                pos = and_match.end()
                continue
        entries.append((entry[0], entry[1]))
        break
    return entries


def _multi_entries(body: str, region_start: int, region_end: int) -> list[tuple[tuple[str, ...], str]]:
    markers = list(_MARKER_QUOTE_RE.finditer(body, region_start, region_end))
    entries: list[tuple[tuple[str, ...], str]] = []
    for i, marker_match in enumerate(markers):
        boundary = markers[i + 1].start() if i + 1 < len(markers) else region_end
        quote_pos = marker_match.end() - 1
        if _preceded_by_references_to(body, quote_pos):
            continue
        terms, chain_end = _match_quote_chain(body, quote_pos, boundary)
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
    surface. Stops at the first entry that fails to parse, or whose
    term-starting quote is a D-INCLUDES-guarded "References to" quote
    (conservative by design, same rationale as the marker-adjacency gate:
    an ambiguous stop is safer than guessing which later quote resumes the
    list)."""
    entries: list[tuple[tuple[str, ...], str]] = []
    pos = region_start
    while pos < region_end:
        ws = _LEADING_WS_RE.match(body, pos, region_end)
        p = ws.end() if ws else pos
        if _preceded_by_references_to(body, p):
            break
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
