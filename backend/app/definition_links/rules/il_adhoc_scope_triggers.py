"""Rule: ad-hoc parenthetical `(TRIGGER - term)` markers, widened beyond
today's `להלן`-only `extract_adhoc_definitions` (sprint 2026-08-04-defs-il,
program 2026-08-04-definition-completeness, item 4; gate I2(c)).

Same unquoted-apposition grammar as `extract._ADHOC_RE`
(`\\(\\s*TRIGGER\\s*[-:]\\s*term\\s*\\)`), NEW trigger words `בפרק זה`/
`בסימן זה`/`בחלק זה` -- this is an ADDITIONAL rule, distinct from (and
does not touch) the existing `להלן`-triggered `il_scope_triggers.py`
registration.

Scope is dispatched BY TRIGGER WORD, not uniform:
- `בפרק זה` -> `scope="chapter"`, `source_chapter=ctx.chapter` (same
  containment-enabling requirement as `il_chapter_scope_triggers.py`'s
  quote-first sibling -- this sub-case also serves gate I3).
- `בסימן זה`/`בחלק זה` -> `scope="siman"`/`"chelek"`, `scope_value=None`
  (same capture-only limitation as `il_siman_chelek_scope_triggers.py` --
  containment is a separate, unwired architecture gap, not something this
  rule can fix).

Reuses the existing <=4-token safety cap on the captured term (Planner's
corpus scan: only 46/1041 sampled real parentheticals exceed it; 0/1041
verb-shaped false positives) -- same discipline as `extract_adhoc_
definitions`, applied here independently since that function is frozen
and not called by this new rule.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(r"\(\s*(בפרק זה|בסימן זה|בחלק זה)\s*[-:]\s*([^)]+?)\s*\)")

_SCOPE_BY_TRIGGER = {"בפרק זה": "chapter", "בסימן זה": "siman", "בחלק זה": "chelek"}


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for match in _TRIGGER_RE.finditer(article_body):
        trigger, raw_term = match.group(1), match.group(2).strip()
        term = raw_term
        if term.startswith('"') and term.endswith('"') and len(term) >= 2:
            term = term[1:-1].strip()
        if not term or len(term.split()) > 4:
            continue

        scope = _SCOPE_BY_TRIGGER[trigger]
        if scope == "chapter":
            candidate = DefinitionCandidate(
                terms=(term,),
                definition_text=term,
                scope=scope,
                source_chapter=ctx.chapter,
            )
        else:
            candidate = DefinitionCandidate(
                terms=(term,),
                definition_text=term,
                scope=scope,
                scope_value=None,
            )
        results.append(candidate)
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
