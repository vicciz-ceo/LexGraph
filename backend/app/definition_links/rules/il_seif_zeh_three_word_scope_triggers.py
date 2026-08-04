"""Rule: `לענין סעיף זה, "term" - definition` / `לעניין סעיף זה, "term" -
definition` -- the 3-word variant of today's 2-word `לענין זה,`/`בסעיף
זה,` local-scope trigger (sprint 2026-08-04-defs-il, program
2026-08-04-definition-completeness, item 3; gate I2(b)).

`extract._LOCAL_TRIGGER_RE` only recognizes the literal 2-word phrases
`לענין זה`/`בסעיף זה` immediately followed by a comma; it does not match
the 3-word `לענין/לעניין סעיף זה` variant (the substring `לענין זה` is
NOT contained in `לענין סעיף זה` -- `סעיף` sits between the two words),
so this is additive coverage, not an overlap with the existing rule.
Both spelling variants (`לענין`/`לעניין`) are covered. Stamps
`scope="local"` -- same granularity as today's 2-word trigger,
`source_article_number` auto-defaulted to the current article by
`HebrewProfile.extract_local_scope_definitions`.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(r'(?:לענין|לעניין) סעיף זה,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return [
        DefinitionCandidate(
            terms=(match.group(1).strip(),),
            definition_text=match.group(2).strip(),
            scope="local",
        )
        for match in _TRIGGER_RE.finditer(article_body)
    ]


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
