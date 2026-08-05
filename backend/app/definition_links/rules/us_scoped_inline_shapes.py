"""Sprint 2026-08-04-defs-us-scoped-inline, fix cycles 2-5 (Developer).
Sanctioned style-gate overflow from `us_scoped_inline.py` (that module's
docstring, "Sanctioned overflow" -- `us_scoped_inline.py` was already at
the 300-line style-gate ceiling before cycle 2's fixes, and again before
cycle 3's/5's). Holds the trigger/idiom VOCABULARY regexes and (cycle 3,
revised cycle 4 per D-S15) the subsection-scope derivation. Deliberately
NOT a `ScopeTriggerRule` -- it calls no `register_*` function and has no
import-time side effects, so `rules/__init__.py`'s auto-discovery (every
sibling module in this package gets imported at package-import time) can
safely import this file without adding new dispatch surface. Does not
import `us_scoped_inline` (would be circular); `us_scoped_inline.py`
imports FROM here. Fix cycle 5 moved the ENTRY-SPLITTING mechanics
(`_single_entry`/`_multi_entries`/`_unmarked_multi_entries`/
`_find_entry_end`/`_match_quote_chain`/`_split_idiom_chain`) OUT to a
second sanctioned overflow module, `us_scoped_inline_entries.py` (same
pattern, imports the vocabulary regexes it needs FROM this file) -- this
file was back at the 300-line ceiling once cycle 5's own vocabulary
widenings landed; see that module's own docstring for the entry-mechanics
history and the fix-6/D-INCLUDES-guard detail.

QA cycle-1 root causes fixed in this module (full detail in
`us_scoped_inline.py`'s docstring and this sprint's report):

  2. Period-style list markers (`1.` `2.`, not just `(1)` `(2)`) --
     `_MARKER_RE` now accepts either.
  7. Plural `have the same meaning as` (`_IDIOM_RE` recognized only
     singular `has`).
  8. Bare copula `is` (measured for false-positive surface against the
     real corpus per program ruling D-Q1 -- see the sprint report; shipped
     unnarrowed, ~0% FP in a 40-row hand-inspected sample of 846 corpus-wide
     new candidates).
  (Also: a "X" or "Y" alias chain -- needed to even REACH the Tennessee
  row's plural `have` idiom, since its two terms share one idiom via "or".)

Fix cycle 3 (ruling S-R14, the subsection revert): `_resolve_subsection_
scope`/`_subsection_scope_level` moved here purely for the 300-line style
gate -- see `us_scoped_inline.py`'s docstring for the full S-R9/S-R10/
S-R11/S-R14/S-R15/D-S15 design reasoning, repeated here only where
load-bearing for these two functions themselves.

Fix cycle 4 (director ruling D-S15, supersedes S-R15): `_subsection_
scope_level` now returns the OUTERMOST step of the resolved path -- see
that function's own docstring for the SC live-path evidence and the
corpus-wide vocabulary census. `_resolve_subsection_scope` itself is
UNCHANGED: same resolver call, same zero-miss `"local"` degrade on an
empty path, same same-step stamping of `scope_value`/`scope_unit_kind` --
only WHICH step `_subsection_scope_level` picks moved.

Fix cycle 5 (QA cycle-2, 4 of the 6 root causes; the other 2 -- Georgia's
"Code section" and the second and-joined non-colon entry -- live in
`us_scoped_inline.py`/`us_scoped_inline_entries.py` respectively):

  1. Bare-`in this <unit>` trigger's connector did not tolerate a
     `the term(s)` phrase before the quote, unlike `_STRONG_CONNECTOR_RE`'s
     own tolerance (12,189 corpus-wide hits). `_BARE_CONNECTOR_RE` now
     tolerates it -- but ONLY as a trailing, optional group AFTER the
     existing `colon`/`comma` capture groups, which are what the strict
     adjacency gate in `_leading_events` actually inspects
     (`conn.group("colon") or conn.group("comma")`); the gate's own
     matching -- whether a comma/colon appears immediately (whitespace-only)
     after the unit word -- is completely untouched by whether this new
     trailing group also happens to match. `test_bare_in_strict_comma_or_
     colon_adjacency_gate_is_load_bearing` (the isolating probe, no colon/
     comma at all) is unaffected: its own gate check still fires and
     rejects the probe before the new group is ever reached.
  2. `shall include` was not a recognized idiom (director ruling
     D-INCLUDES: the `includes`-family verbs join the defining vocabulary
     program-wide with the naive quoted-term anchor, 100/100 hand-read
     definitional; see `us_scoped_inline_entries.py`'s docstring for the
     ONE targeted guard the ruling still requires). Finding 3's own KS row
     (below) also needed a bare `(shall )?have the meaning(s)` alternative
     -- the same cross-reference-friendly, no-`same`/`as`-required design
     as the existing `has the meaning` (OH cross-reference) alternative,
     just its `have` cousin.
  3. A quote chain sharing one idiom could only be joined by `or`
     (`_QUOTE_CHAIN_SEP_RE`), not `and` -- KS's `the terms "governing
     body" and "municipality" shall have the meanings ascribed to...`.
  5. An intervening `unless the context otherwise indicates` clause (and
     variants, 2,113 corpus-wide hits / 31 states) broke
     `_STRONG_CONNECTOR_RE`'s recognition of `the following terms ...
     meaning(s)` the same way root cause 4's `and <citation>` clause used
     to -- the SAME bounded-filler mechanism (an anchor phrase then a
     comma/colon-bounded clause that can never swallow past the real
     connector) now tolerates a second such clause, in the position
     drafters actually use it (Maine: after the leading comma, before "the
     following terms"). Maine's own phrasing is also bare "the following
     terms have the following meanings" (no "shall"), so "shall" is now
     optional there too; and Maine numbers its list with a bare, single
     letter/digit label ("A.") that `_MARKER_RE` does not cover (letters
     without parens) -- rather than widen that shared vocabulary (which
     would open `_multi_entries`'s marker recognition broadly, out of this
     finding's scope), the trailing `(?:\\.\\s*(?:[A-Za-z0-9]{1,3}\\.\\s*)?)?`
     is scoped to fire ONLY once the FULL "the following terms ...
     meaning(s)" anchor phrase has already matched -- never a bare,
     unconditional swallow of an arbitrary period.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from app.definition_links.us_profile import resolve_unit_path

# Connector between a STRONG trigger's unit word and the definiendum.
# Root cause 4 (intervening secondary citation clause, e.g. Delaware's "As
# used in this section AND IN Section 15-105 of this title, the term...")
# and fix cycle 5's finding 5 (Maine's "unless the context otherwise
# indicates..."): a SINGLE bounded-filler mechanism -- an anchor phrase
# followed by a comma/colon-bounded clause, never able to swallow past the
# next comma/colon -- tolerates one intervening qualifier clause in EITHER
# of the two positions drafters actually use it (directly after the unit
# word, no leading comma; or after a comma, before "the following terms").
# Root cause 5 (DC's "the term:" -- no space before the colon) and root
# cause 7 (Tennessee's plural "the terms ... have"): "the term(s)" now uses
# a `\b` word boundary instead of requiring trailing whitespace, so it
# can't over-consume into "terms" nor refuse a colon glued directly onto
# "term".
# Root cause 6 (NY's "shall have the following meanings", MS's "shall have
# meanings as follows") and fix cycle 5's finding 5 (Maine's bare "have the
# following meanings", no "shall"): "shall" is now optional before
# "have (the following) meaning(s) (as follows)"; when that whole "the
# following terms ... meaning(s)" phrase matches, an OPTIONAL trailing
# sentence-period-then-bare-list-label (Maine's "A.") is also tolerated --
# see this module's own docstring for why that tail is scoped to fire only
# inside this one branch.
_STRONG_CONNECTOR_RE = re.compile(
    r"\s*"
    r"(?:and\s+(?:in\s+)?[^,:]{0,120})?"
    r"\s*(?:,\s*)?"
    r"(?:unless\s+the\s+context[^,:]{0,80})?"
    r"\s*(?:,\s*)?"
    r"(?:"
    r"the following terms?\s+(?:mean|means|(?:shall\s+)?have(?:\s+the following)?"
    r"\s+meanings?(?:\s+as\s+follows)?)\s*(?:\.\s*(?:[A-Za-z0-9]{1,3}\.\s*)?)?"
    r"|shall have\s+(?:the following\s+)?meanings?(?:\s+as\s+follows)?\s*"
    r")?"
    r"(?:the terms?\b\s*|an?\s+)?"
    r"(?P<colon>:)?\s*",
    re.IGNORECASE,
)

# Strict: only a comma or a colon, no filler words -- the bare-`in` trigger's
# load-bearing adjacency gate (QA cycle-1 mutation testing target). The gate
# check in `_leading_events` reads ONLY the `colon`/`comma` groups below, so
# fix cycle 5's trailing `the term(s)` tolerance (finding 1) -- appended
# AFTER those groups -- cannot loosen what the gate itself accepts as
# "immediately adjacent"; it only widens where `region_start` lands once the
# gate has ALREADY passed.
_BARE_CONNECTOR_RE = re.compile(
    r"\s*(?:(?P<colon>:)|(?P<comma>,))?\s*(?:the terms?\b\s*)?",
    re.IGNORECASE,
)

# Root cause 7's Tennessee row aliases two quoted terms with a shared idiom
# ("the terms "X" or "Y" have the same meaning as..."), and fix cycle 5's
# finding 3 (KS) needs the same for "and": a chain of quotes joined by a
# literal "or" OR "and" (optionally comma-preceded) all share ONE
# definition. A bare comma alone does NOT continue the chain -- that stays
# reserved for separate marked/unmarked list entries.
_QUOTE_CHAIN_SEP_RE = re.compile(r"\s*(?:,\s*)?(?:or|and)\s*", re.IGNORECASE)

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
# D-Q1 section) added to the existing idiom vocabulary. Fix cycle 5's
# finding 2 (director ruling D-INCLUDES) adds `shall include`, the
# `shall`-prefixed cousin of `includes` that `shall mean` already proves
# this vocabulary intends to support; finding 3 adds a bare `(shall )?have
# the meaning(s)` alternative (KS's "shall have the meanings ascribed to
# <cross-reference>", the same cross-reference-friendly design as `has the
# meaning`). Order matters: more specific phrases are tried before their
# shorter cousins so the longer one wins when both are present.
_IDIOM_RE = re.compile(
    r"\s*(?:has the same meaning as|have the same meaning as|has the meaning"
    r"|(?:shall\s+)?have the meanings?"
    r"|shall be construed to mean"
    r"|shall include|shall mean|does not include|is defined as|includes?|means|is)\b,?\s*",
    re.IGNORECASE,
)


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
