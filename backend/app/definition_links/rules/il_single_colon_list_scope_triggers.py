"""Rule: the `::-` nested-list-under-preamble SHAPE
(`il_colon_dash_nested_list_scope_triggers.py`), generalized to the
SINGLE-colon `:-` marker (sprint 2026-08-04-defs-il, Phase C, item C4).

`extract._ENTRY_START_RE` (the definitions-SECTION entry marker,
`^\\s*:-\\s?`) is FROZEN and only ever consulted by the definitions-
section dispatch path (`HebrewProfile.extract_definitions_from_section`).
Articles that are NOT dispatched as a definitions section (heading not
recognized by `sections._DEFINITIONS_HEADING_RE`) but whose body still
contains a genuine `preamble line ending in a bare "-"` followed by
`:-`-marked `"term" - definition` entries were reached by NO rule at all
-- not even `il_colon_dash_nested_list_scope_triggers.py`, which only
ever matches the DOUBLE-colon `::-` marker. Two sub-shapes, both
live-confirmed (see the sprint log's Phase C entry):
  (i)  `פרשנות` ("Interpretation") heading synonym -- `sections.
       _DEFINITIONS_HEADING_RE` does not recognize it (nor its
       `(תיקון: ...)` suffix), so every real article headed exactly
       `פרשנות` dispatches as an ORDINARY article and its genuine
       `:-`-marked definitions list was reached by nothing.
  (ii) genuine embedded `:-`-marked definitions lists sitting inside
       substantive, topically-unrelated articles (heading recognized
       fine, article legitimately about something else).
Both sub-shapes reach the ordinary-article `extract_local_scope_
definitions` dispatch path TODAY (no frozen-file change needed) -- this
is a NEW rule-module-only file, `sections.py` is NOT touched (per the
brief's explicit instruction: reach `פרשנות` via the ordinary-article
`ScopeTriggerRule` path, exactly as the `::-` rule already does, never
by teaching `sections.py` a new heading synonym).

**Non-overlap with `il_colon_dash_nested_list_scope_triggers.py` is
structural, not merely conventional** (pinned by
`test_c4_entry_start_re_cannot_match_double_colon_marker` against the
FROZEN `extract._ENTRY_START_RE`, whose pattern `^\\s*:-\\s?` this
module's own `_ENTRY_LINE_RE` mirrors): the leading `\\s*` in a
single-colon entry regex can never consume the FIRST colon of a `::-`
line, so the very next required character (`-`) fails to match against
that line's actual second character (`:`) -- a `::-` line can never
satisfy a single-`:-`-anchored pattern, and (by the mirror-image
argument) a genuine single-`:-` line's second character is never `:`
either, so it can never satisfy the double-colon module's own `^\\s*::-`
anchor. The two rules are therefore mutually exclusive BY CONSTRUCTION
on any one physical line -- no article can ever have the same entry
double-captured by both with conflicting scopes.

Shares its preamble->scope vocabulary table and candidate-building logic
with `il_colon_dash_nested_list_scope_triggers.py` via
`il_list_shape_scope.py` (program efficiency directive: ONE table,
measured once) -- including ruling M16's law-wide fix, so a single-`:-`
list under a `בחוק זה -`/`בתקנות אלה -`/... preamble correctly classifies
`scope="law-wide"` from day one (never shipped with the M16 under-claim
the `::-` rule originally had). Sprint 2026-08-04-defs-il, Phase D, D-1a
bundle: also now shares `parse_entry` (multi-term-aware, see `il_list_
shape_scope.py`'s own docstring) instead of the single-term-only
`ENTRY_TERM_DASH_RE` this rule used before.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_list_shape_scope import (
    PREAMBLE_RE,
    infer_scope,
    make_candidate,
    parse_entry,
)
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

# Mirrors the FROZEN `extract._ENTRY_START_RE` (`^\s*:-\s?`) exactly in
# spirit -- single colon only, structurally unable to match a `::-` line
# (see module docstring's non-overlap argument).
_ENTRY_LINE_RE = re.compile(r"^\s*:-\s*(.*)$")


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    lines = article_body.split("\n")
    n = len(lines)
    results: list[DefinitionCandidate] = []
    i = 0
    while i < n:
        if not PREAMBLE_RE.search(lines[i].rstrip()):
            i += 1
            continue
        scope = infer_scope(lines[i])
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            entry_match = _ENTRY_LINE_RE.match(line)
            if not entry_match:
                break
            parsed = parse_entry(entry_match.group(1).strip())
            if parsed is not None:
                terms, definition_text = parsed
                results.append(
                    make_candidate(terms, definition_text.rstrip(";").strip(), scope, ctx)
                )
            i += 1
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
