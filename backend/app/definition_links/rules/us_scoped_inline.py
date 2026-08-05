"""Sprint 2026-08-04-defs-us-scoped-inline (Developer, Phase A). Captures the
dominant US miss-class: definitions declared inline in an ordinary
substantive section body via `"As used in this section, ... means"` /
`"For (the) purposes of this <unit>..."` / `"When used in this <unit>..."` /
strict-adjacency bare `"In this <unit>..."` -- never inside a
`Definitions`-headed section (`pipeline.py`'s existing branch, untouched).
Self-registers at import time by existing as a file in this package
(`rules/__init__.py`'s auto-discovery, core-authored) -- no other file
needs to change (ruling S-R2/U3).

Scope-unit -> `.scope` mapping (rulings S-R9/S-R14/S-R15/D-S15, binding --
full reasoning in the sprint log's S-R4/S-R5/S-R9/S-R10/S-R11/S-R14/D-S15
sections):

    "section" -> "local"; "chapter" -> "chapter";
    "subsection" -> "subsection", derived from CORE's resolver (S-R14,
    see `_resolve_subsection_scope`), degrading to "local" when core
    cannot resolve a step at the trigger offset (same fn, zero-miss);
    "part"/"subchapter"/"article"/"title"/"paragraph"/"division"/
    "subdivision"/"subpart"/"act" (residue kinds) -> "law-wide"

`"local"`/`"chapter"` are shipped and live-enforced by `matcher.py`'s
`_in_scope` (S-R4); every OTHER literal kind falls into its generic
branch, reading a `MatcherArticle` attribute that does not exist in
production -- `False` for every article, including the definition's own
(S-R5): a guaranteed zero-miss violation. `"part"`/`"subchapter"` (D8:
UNSOUND under a chapter-fallback -- a single Maine Part spans up to 106
chapters) therefore fall back to the narrowest REPRESENTABLE enclosing
unit rather than a kind guaranteed dead -- `"law-wide"` -- core's own
precedent for an unrepresentable narrowing (seam v2 S1, AK ranges):
zero-miss-safe, precision cost recorded not silently dropped (NAMED OPEN
CONFLICT CLASSES, P-R2).

`"subsection"`'s own history (S-R9 diagnosis -> S-R10 live-path proof ->
S-R11 interim -> S-R14 fix -> D-S15 director ruling, full detail in
`us_scoped_inline_shapes.py`'s own docstring, not repeated here): the old
design compared this module's OWN regex-guessed label against core's
`resolve_unit_path` -- two derivations that silently disagreed, a total
under-link on the live path (S-R10). S-R14 replaces both with ONE:
`_resolve_subsection_scope` stamps `.scope_value`/`.scope_unit_kind` from
core's OWN resolved step, never a shape guess. WHICH step is
`_subsection_scope_level`'s job (D-S15: the OUTERMOST step, `path[0]`).
When core's resolver returns no usable step at all (Maine/Florida
period-style subsections core's marker regex cannot see),
`_resolve_subsection_scope` degrades to `"local"` -- zero-miss-safe,
unaffected by D-S15 since the degrade fires on an EMPTY path.

The pure function leaves `.source_article_number`/`.source_chapter` `None`
(matching `extract_local_definitions`'s convention): `us_profile.py`'s
`extract_local_scope_definitions` auto-defaults `.source_article_number`
from the owning article whenever `None`, but NOT `.source_chapter`, so the
adapter below stamps `source_chapter=ctx.chapter` itself for every
`scope="chapter"` candidate (mirrors core's `pipeline.py` Definitions-
path). `.scope_value`/`.scope_unit_kind` are stamped for every
`subsection`-TRIGGERED candidate by `_resolve_subsection_scope`; the
VALUE stays transient (S-R7, no test pins it literally), but whether an
in-subsection mention links and an out-of-subsection one does not is now
genuinely live-path test-pinned.

Body-shape (idiom) vocabulary, real corpus evidence (Planner D1/D11):
`means`/`shall mean`/`has the meaning`/`has the same meaning as in
section N` (OH cross-reference)/`includes`/`the term "X" includes`/`does
not include`/`is defined as`, and (D11, Missouri) a bare `"X" ,
<definition>` with no idiom keyword. Colon-then-list (incl. Oregon's
capital-letter `(A)(B)` convention) is supported by only ever starting a
NEW entry at a short list marker IMMEDIATELY followed by a quote -- the
same precision mechanism that keeps a term's OWN numbered elaboration
list (no new quoted term per item, e.g. Montana's fantasy-sports-league
row) from being spuriously split, and keeps PA's `References to "X"
shall include Y` construction-clause (a marker NOT immediately followed
by a quote) from ever being recognized.

Fix cycle 2 (QA cycle-1, 8 root causes -- full detail and real-corpus
before/after evidence in this sprint's report): the body-shape regex
vocabulary and entry-splitting helpers moved to the sanctioned overflow
module `us_scoped_inline_shapes.py` (style gate -- this file was already
at the 300-line ceiling). Added: period-style list markers, an unmarked
colon-then-quoted-list fallback (the single most severe QA cycle-1 miss),
one tolerated intervening "and [in] <citation>" clause, `the term(s)`
without requiring trailing whitespace before a colon, `shall have (the
following) meaning(s) (as follows)`, plural `have the same meaning as`,
an "X" or "Y" alias chain, and a bare copula `is` (measured against the
real corpus per D-Q1 -- see the report). The two precision gates flagged
load-bearing-but-under-pinned by QA cycle-1 mutation testing are
UNCHANGED by this cycle: the bare-`in` trigger's strict comma/colon
adjacency gate, and `_MARKER_QUOTE_RE`'s marker-immediately-followed-by-
quote rule (only the marker SYNTAX vocabulary widened, never the
immediate-adjacency requirement itself).

Fix cycle 5 (QA cycle-2, 6 root causes; full detail and corpus-wide
measurement in this sprint's report): `_UNIT_TAIL` (Georgia's "Code
section") is the only change here. The other five live in
`us_scoped_inline_shapes.py` (vocabulary) and the new sanctioned overflow
module `us_scoped_inline_entries.py` (entry-splitting mechanics, moved out
this cycle to stay under the 300-line gate a second time; also holds the
D-INCLUDES targeted "References to" guard). Both precision gates flagged
load-bearing by QA cycle-1 mutation testing are UNCHANGED again: the
bare-`in` adjacency gate (`_BARE_CONNECTOR_RE`'s `colon`/`comma` groups,
which `_leading_events` below still reads directly; this cycle's new
tolerance is appended AFTER them, never inside), and `_MARKER_QUOTE_RE`'s
marker-immediately-followed-by-quote rule (untouched this cycle).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)
from app.definition_links.rules.us_scoped_inline_entries import (
    _find_entry_end,
    _multi_entries,
    _single_entry,
    _unmarked_multi_entries,
)
from app.definition_links.rules.us_scoped_inline_shapes import (
    _BARE_CONNECTOR_RE,
    _IDIOM_RE,
    _STRONG_CONNECTOR_RE,
    _resolve_subsection_scope,
)

_SCOPE_BY_UNIT: dict[str, str] = {
    "section": "local",
    "chapter": "chapter",
    "subsection": "subsection",  # S-R14 revert -- restored; see module docstring
    "part": "law-wide",
    "subchapter": "law-wide",
    "article": "law-wide",
    "title": "law-wide",
    "paragraph": "law-wide",
    "division": "law-wide",
    "subdivision": "law-wide",
    "subpart": "law-wide",
    "act": "law-wide",
}

_UNIT_ALT = "|".join(sorted(_SCOPE_BY_UNIT, key=len, reverse=True))
# unit word + a CHAIN of zero or more parenthetical qualifiers, e.g. "this
# Subsection (2)," or (root cause 3, Colorado) "this subsection
# (1)(a)(I)(A),". Was a single optional group (`?`); a chain of qualifiers
# immediately after the unit word left the later ones unconsumed, breaking
# both the connector match and the quote-adjacency check that follows.
# Fix cycle 5, finding 4 (Georgia): optional "Code " before the unit word
# -- "Code section" names the SAME unit as plain "section" (1,299 rows use
# "as used in this Code section", vs. 1 plain-form GA row), so no
# `_SCOPE_BY_UNIT` change is needed.
_UNIT_TAIL = rf"(?:Code\s+)?(?P<unit>{_UNIT_ALT})\b(?:\s*\([^)\n]{{1,12}}\))*"

_STRONG_TRIGGER_RE = re.compile(
    rf"(?:as used in|for (?:the )?purposes? of|when used in)\s+this\s+{_UNIT_TAIL}", re.IGNORECASE
)

# Bare "In this <unit>" -- genuine ~21% of the time (vs. ~77% for "as used
# in"); precision rests on the connector check below, never this regex alone.
_BARE_IN_TRIGGER_RE = re.compile(rf"\bin\s+this\s+{_UNIT_TAIL}", re.IGNORECASE)

# Trigger AFTER its own quoted term, mid-sentence, not a leading preamble
# (VT: `"State facilities," when used in this chapter, shall mean ...`).
_EMBEDDED_TRIGGER_RE = re.compile(
    rf'["“](?P<term>[^"”]+?),?["”]\s*,?\s*'
    rf"(?:as used in|when used in)\s+this\s+{_UNIT_TAIL}\s*,\s*",
    re.IGNORECASE,
)


@dataclass
class _TriggerEvent:
    start: int
    region_start: int
    saw_colon: bool
    scope: str
    scope_value: str | None
    scope_unit_kind: str | None


def _event_scope(body: str, unit: str, trigger_start: int) -> tuple[str, str | None, str | None]:
    if unit == "subsection":
        return _resolve_subsection_scope(body, trigger_start)
    return _SCOPE_BY_UNIT[unit], None, None


def _leading_events(body: str) -> list[_TriggerEvent]:
    events: list[_TriggerEvent] = []
    strong_matches = list(_STRONG_TRIGGER_RE.finditer(body))
    for match in strong_matches:
        conn = _STRONG_CONNECTOR_RE.match(body, match.end())
        region_start = conn.end() if conn else match.end()
        unit = match.group("unit").lower()  # gate on the unit word, not `scope` (S-R11: dead)
        scope, scope_value, scope_unit_kind = _event_scope(body, unit, match.start())
        events.append(
            _TriggerEvent(
                match.start(),
                region_start,
                bool(conn and conn.group("colon")),
                scope,
                scope_value,
                scope_unit_kind,
            )
        )

    strong_spans = [(m.start(), m.end()) for m in strong_matches]
    for match in _BARE_IN_TRIGGER_RE.finditer(body):
        if any(start <= match.start() < end for start, end in strong_spans):
            continue  # the "in" tail of "as used in"/"when used in", not a bare trigger
        conn = _BARE_CONNECTOR_RE.match(body, match.end())
        if not conn or not (conn.group("colon") or conn.group("comma")):
            continue  # strict adjacency failed -- ordinary prose, not a trigger
        unit = match.group("unit").lower()
        scope, scope_value, scope_unit_kind = _event_scope(body, unit, match.start())
        events.append(
            _TriggerEvent(
                match.start(), conn.end(), bool(conn.group("colon")), scope, scope_value, scope_unit_kind
            )
        )

    events.sort(key=lambda e: e.start)
    return events


def _embedded_entries(body: str) -> list[DefinitionCandidate]:
    candidates: list[DefinitionCandidate] = []
    for match in _EMBEDDED_TRIGGER_RE.finditer(body):
        term = match.group("term").strip()
        if not term:
            continue
        idiom_match = _IDIOM_RE.match(body, match.end(), len(body))
        if not idiom_match:
            continue
        def_start = idiom_match.end()
        entry_end = _find_entry_end(body, def_start, len(body))
        definition_text = body[def_start:entry_end].strip()
        if not definition_text:
            continue
        unit = match.group("unit").lower()
        scope, scope_value, scope_unit_kind = _event_scope(body, unit, match.start())
        candidates.append(
            DefinitionCandidate(
                terms=(term,),
                definition_text=definition_text,
                scope=scope,
                scope_value=scope_value,
                scope_unit_kind=scope_unit_kind,
            )
        )
    return candidates


def extract_us_scoped_inline_definitions(body: str) -> list[DefinitionCandidate]:
    """PURE: scan an already-normalized US article body for family-1 inline
    scoped definitions. No heading, no article/document context. See this
    module's docstring for the trigger vocabulary, scope mapping, and
    over-split precision mechanism."""
    candidates: list[DefinitionCandidate] = []
    events = _leading_events(body)
    for i, event in enumerate(events):
        region_end = events[i + 1].start if i + 1 < len(events) else len(body)
        if event.saw_colon:
            entries = _multi_entries(body, event.region_start, region_end)
            if not entries:
                # Root cause 1 (QA cycle-1's most severe miss): a colon-then
                # -quoted-list with NO per-entry marker. Only tried once the
                # marker-based split finds nothing.
                entries = _unmarked_multi_entries(body, event.region_start, region_end)
        else:
            entries = _single_entry(body, event.region_start, region_end)
        for terms, definition_text in entries:
            candidates.append(
                DefinitionCandidate(
                    terms=terms,
                    definition_text=definition_text,
                    scope=event.scope,
                    scope_value=event.scope_value,
                    scope_unit_kind=event.scope_unit_kind,
                )
            )
    candidates.extend(_embedded_entries(body))
    return candidates


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    candidates = extract_us_scoped_inline_definitions(article_body)
    for candidate in candidates:
        if candidate.scope == "chapter":
            # us_profile.py auto-defaults only source_article_number -- see
            # module docstring for why source_chapter must be stamped here.
            candidate.source_chapter = ctx.chapter
    return candidates


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))
