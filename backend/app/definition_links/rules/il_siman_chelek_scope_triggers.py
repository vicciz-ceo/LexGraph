"""Rule: `בסימן זה, "term" - definition` / `בחלק זה, "term" - definition`
scoped quoted definitions (sprint 2026-08-04-defs-il, program
2026-08-04-definition-completeness, item 2b; gate I2(a) sub-cases).

Same quote-first grammar as `il_chapter_scope_triggers.py`'s `בפרק זה`
rule, two sibling trigger words: `בסימן זה` ("in this siman") and `בחלק
זה` ("in this chelek/part") -- a DIFFERENT structural axis from chapter
(`Article.chapter` only ever holds `==`-level heading text), so these
stamp the NEW generic kinds `scope="siman"` / `scope="chelek"`, never
`"chapter"`.

`scope_value=None` -- there is no live way to derive the owning
סימן/חלק's own identifying text this sprint (`sections.py` discards every
3+-equals heading's text today; see the sprint log's escalation E1/E6).

CAPTURE ONLY, deliberately: containment for these two kinds is NOT
achievable this sprint. `matcher._in_scope`'s generic branch (any kind
other than chapter/local/subsection/law-wide) checks
`article.structural_units`, which no rule in this sprint populates and
which a real production `MatcherArticle` never carries -- so a
`"siman"`/`"chelek"`-scoped `Definition` is captured (a real row exists)
but never links a `USES_DEFINITION` edge on the live pipeline path. This
is a known, escalated wiring gap (`StructuralUnitRule`/
`heading_breadcrumbs` have zero production callers), not something a
rule-module-only file can fix.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(r'(בסימן זה|בחלק זה),\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE)

_SCOPE_BY_TRIGGER = {"בסימן זה": "siman", "בחלק זה": "chelek"}


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for match in _TRIGGER_RE.finditer(article_body):
        trigger, term, definition_text = match.group(1), match.group(2), match.group(3)
        results.append(
            DefinitionCandidate(
                terms=(term.strip(),),
                definition_text=definition_text.strip(),
                scope=_SCOPE_BY_TRIGGER[trigger],
                scope_value=None,
            )
        )
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
