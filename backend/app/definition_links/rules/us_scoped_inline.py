"""Sprint 2026-08-04-defs-us-scoped-inline (Developer, Phase A). Captures the
dominant US miss-class: definitions declared inline in an ordinary
substantive section body via `"As used in this section, ... means"` /
`"For (the) purposes of this <unit>..."` / `"When used in this <unit>..."` /
strict-adjacency bare `"In this <unit>..."` -- never inside a
`Definitions`-headed section (`pipeline.py`'s existing
`if is_definitions_section:` branch, untouched).

Self-registers at import time by existing as a file in this package
(`rules/__init__.py`'s auto-discovery, core-authored) -- no other file
needs to change (ruling S-R2/U3).

Scope-unit -> `.scope` mapping (ruling S-R9, binding -- full reasoning in
the sprint log's S-R4/S-R5/S-R9 sections):

    "section"                                     -> "local"
    "chapter"                                      -> "chapter"
    "subsection"                                   -> "subsection"
    "part" / "subchapter" (residue kinds below)     -> "law-wide"
    "article"/"title"/"paragraph"/"division"/
    "subdivision"/"subpart"/"act"                   -> "law-wide"

`"local"`/`"chapter"`/`"subsection"` are shipped and live-enforced by
`matcher.py`'s `_in_scope` (S-R4). Every OTHER literal kind string falls
into `_in_scope`'s generic branch, which reads a `MatcherArticle` attribute
that does not exist in production, so it returns `False` for every
article, including the definition's own (S-R5) -- a guaranteed zero-miss
violation. `"part"`/`"subchapter"` were measured (Planner D8) UNSOUND under
a chapter-fallback (a single Maine Part spans up to 106 chapters -- S-R9),
so, like the other residue kinds, they fall back to `"law-wide"`: core's
own precedent for an unrepresentable narrowing (seam v2 S1, AK
multi-chapter ranges) -- zero-miss-safe, precision cost recorded rather
than silently dropped (a NAMED OPEN CONFLICT CLASS under P-R2).

The pure function leaves `.source_article_number`/`.source_chapter` `None`
on every candidate (matching `extract_local_definitions`'s convention) --
`us_profile.py`'s `extract_local_scope_definitions` auto-defaults
`.source_article_number` from the owning article whenever `None`, but NOT
`.source_chapter`, so the adapter at the bottom of this module stamps
`source_chapter=ctx.chapter` itself for every `scope="chapter"` candidate
(mirrors core's own `pipeline.py` Definitions-section-path pattern).
`.scope_value` (the subsection label, transient per S-R7 -- no persisted
column) IS derivable from body text alone, so the pure function sets it
directly for `scope="subsection"` candidates; no test pins its exact value
(grep confirmed zero hits sprint-wide) -- best-effort, not a contract.

Body-shape (idiom) vocabulary, real corpus evidence (Planner D1/D11):
`"X" means`, `"X" shall mean`, `"X" has the meaning`/`"X" has the same
meaning as in section N` (OH cross-reference), `"X" includes`/`the term
"X" includes`, `"X" does not include`, `"X" is defined as`, and (D11,
Missouri's house style) a bare `"X" , <definition>` with no idiom keyword.
Colon-then-list (including Oregon's capital-letter `(A)(B)` convention) is
supported by only ever starting a NEW entry at a short list marker
IMMEDIATELY followed by a quote -- the same precision mechanism that keeps
a term's OWN numbered elaboration list (no new quoted term per item, e.g.
Montana's fantasy-sports-league row) from being spuriously split, and that
keeps PA's `References to "X" shall include Y` construction-clause shape
(a marker NOT immediately followed by a quote) from ever being recognized.
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

_SCOPE_BY_UNIT: dict[str, str] = {
    "section": "local",
    "chapter": "chapter",
    "subsection": "subsection",
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
# unit word + an optional short parenthetical qualifier, e.g. "this
# Subsection (2)," -- a specific-numbered cross-reference, not vocabulary.
_UNIT_TAIL = rf"(?P<unit>{_UNIT_ALT})\b(?:\s*\([^)\n]{{1,12}}\))?"

_STRONG_TRIGGER_RE = re.compile(
    rf"(?:as used in|for (?:the )?purposes? of|when used in)\s+this\s+{_UNIT_TAIL}",
    re.IGNORECASE,
)

# Bare "In this <unit>" -- genuine only ~21% of the time (vs. ~77% for "as
# used in"), so precision rests entirely on the connector check below
# finding a comma-or-colon immediately after the unit word, never on this.
_BARE_IN_TRIGGER_RE = re.compile(rf"\bin\s+this\s+{_UNIT_TAIL}", re.IGNORECASE)

_STRONG_CONNECTOR_RE = re.compile(
    r"\s*(?:,\s*)?"
    r"(?:the following terms?\s+(?:mean|means)\s*)?"
    r"(?:the term\s+|an?\s+)?"
    r"(?P<colon>:)?\s*",
    re.IGNORECASE,
)

# Strict: only a comma or a colon, no filler words -- the adjacency gate.
_BARE_CONNECTOR_RE = re.compile(r"\s*(?:(?P<colon>:)|(?P<comma>,))?\s*")

_QUOTE_TERM_RE = re.compile(r'["“](?P<term>[^"”]+?),?["”]')

_MARKER_RE = r"\((?:[0-9]{1,3}|[A-Za-z]{1,3})\)"
# A new list entry starts ONLY where a marker is immediately (whitespace
# only) followed by a quote -- keeps a nested roman-numeral sub-clause or a
# construction-clause's "(1) References to ..." from being mistaken for one.
_MARKER_QUOTE_RE = re.compile(rf'{_MARKER_RE}\s*["“]')

_IDIOM_RE = re.compile(
    r"\s*(?:has the same meaning as|has the meaning|shall be construed to mean"
    r"|shall mean|does not include|is defined as|includes?|means)\b,?\s*",
    re.IGNORECASE,
)

_COMMA_SEP_RE = re.compile(r"\s*,\s*")
_SENTENCE_BOUNDARY_RE = re.compile(r"\.\s")
_LEADING_WS_RE = re.compile(r"\s*")

# Trigger AFTER its own quoted term, mid-sentence (VT: `"State facilities,"
# when used in this chapter, shall mean ...`), not as a leading preamble.
_EMBEDDED_TRIGGER_RE = re.compile(
    rf'["“](?P<term>[^"”]+?),?["”]\s*,?\s*'
    rf"(?:as used in|when used in)\s+this\s+{_UNIT_TAIL}\s*,\s*",
    re.IGNORECASE,
)

_SUBSECTION_LABEL_RE = re.compile(r"(?:^|\n)\s*([0-9]+(?:-[A-Za-z])?\.|\([0-9A-Za-z]{1,3}\))\s")


def _find_entry_end(body: str, def_start: int, boundary: int) -> int:
    """Nearer of the next marker-adjacent quote (a new entry) or the next
    sentence boundary, bounded by `boundary` (region end or next entry)."""
    marker_match = _MARKER_QUOTE_RE.search(body, def_start, boundary)
    period_match = _SENTENCE_BOUNDARY_RE.search(body, def_start, boundary)
    ends = [m.start() for m in (marker_match, period_match) if m]
    return min(ends) if ends else boundary


def _split_idiom(body: str, quote_match: re.Match, boundary: int) -> tuple[str, str] | None:
    term = quote_match.group("term").strip()
    if not term:
        return None
    after_quote = quote_match.end()
    idiom_match = _IDIOM_RE.match(body, after_quote, boundary)
    if idiom_match:
        def_start = idiom_match.end()
    else:
        comma_match = _COMMA_SEP_RE.match(body, after_quote, boundary)
        if not comma_match:
            return None
        def_start = comma_match.end()
    entry_end = _find_entry_end(body, def_start, boundary)
    definition_text = body[def_start:entry_end].strip()
    return (term, definition_text) if definition_text else None


def _single_entry(body: str, region_start: int, region_end: int) -> list[tuple[str, str]]:
    ws = _LEADING_WS_RE.match(body, region_start, region_end)
    pos = ws.end() if ws else region_start
    quote_match = _QUOTE_TERM_RE.match(body, pos, region_end)
    if not quote_match:
        return []
    entry = _split_idiom(body, quote_match, region_end)
    return [entry] if entry else []


def _multi_entries(body: str, region_start: int, region_end: int) -> list[tuple[str, str]]:
    markers = list(_MARKER_QUOTE_RE.finditer(body, region_start, region_end))
    entries: list[tuple[str, str]] = []
    for i, marker_match in enumerate(markers):
        quote_match = _QUOTE_TERM_RE.match(body, marker_match.end() - 1, region_end)
        if not quote_match:
            continue
        boundary = markers[i + 1].start() if i + 1 < len(markers) else region_end
        entry = _split_idiom(body, quote_match, boundary)
        if entry:
            entries.append(entry)
    return entries


def _subsection_label(body: str, trigger_start: int) -> str:
    """Best-effort nearest preceding paragraph marker (e.g. Maine's "2-A.",
    or a lettered "(F)") as the subsection label -- transient (S-R7), no
    test pins its exact value; falls back to a generic label if none is
    found nearby so the field is never left unset."""
    matches = list(_SUBSECTION_LABEL_RE.finditer(body, 0, trigger_start))
    return matches[-1].group(1).rstrip(".") if matches else "subsection"


@dataclass
class _TriggerEvent:
    start: int
    region_start: int
    saw_colon: bool
    scope: str
    scope_value: str | None


def _leading_events(body: str) -> list[_TriggerEvent]:
    events: list[_TriggerEvent] = []
    strong_matches = list(_STRONG_TRIGGER_RE.finditer(body))
    for match in strong_matches:
        conn = _STRONG_CONNECTOR_RE.match(body, match.end())
        region_start = conn.end() if conn else match.end()
        scope = _SCOPE_BY_UNIT[match.group("unit").lower()]
        scope_value = _subsection_label(body, match.start()) if scope == "subsection" else None
        events.append(
            _TriggerEvent(match.start(), region_start, bool(conn and conn.group("colon")), scope, scope_value)
        )

    strong_spans = [(m.start(), m.end()) for m in strong_matches]
    for match in _BARE_IN_TRIGGER_RE.finditer(body):
        if any(start <= match.start() < end for start, end in strong_spans):
            continue  # the "in" tail of "as used in"/"when used in", not a bare trigger
        conn = _BARE_CONNECTOR_RE.match(body, match.end())
        if not conn or not (conn.group("colon") or conn.group("comma")):
            continue  # strict adjacency failed -- ordinary prose, not a trigger
        scope = _SCOPE_BY_UNIT[match.group("unit").lower()]
        scope_value = _subsection_label(body, match.start()) if scope == "subsection" else None
        events.append(_TriggerEvent(match.start(), conn.end(), bool(conn.group("colon")), scope, scope_value))

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
        scope = _SCOPE_BY_UNIT[match.group("unit").lower()]
        scope_value = _subsection_label(body, match.start()) if scope == "subsection" else None
        candidates.append(
            DefinitionCandidate(
                terms=(term,), definition_text=definition_text, scope=scope, scope_value=scope_value
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
        finder = _multi_entries if event.saw_colon else _single_entry
        for term, definition_text in finder(body, event.region_start, region_end):
            candidates.append(
                DefinitionCandidate(
                    terms=(term,),
                    definition_text=definition_text,
                    scope=event.scope,
                    scope_value=event.scope_value,
                )
            )
    candidates.extend(_embedded_entries(body))
    return candidates


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    candidates = extract_us_scoped_inline_definitions(article_body)
    for candidate in candidates:
        if candidate.scope == "chapter":
            # `extract_local_scope_definitions` (us_profile.py) auto-defaults
            # only `.source_article_number` when `None` -- `.source_chapter`
            # is never filled in downstream, so this rule must stamp it
            # itself or a "chapter"-scoped definition silently matches only
            # articles whose `.chapter` is also `None`.
            candidate.source_chapter = ctx.chapter
    return candidates


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))
