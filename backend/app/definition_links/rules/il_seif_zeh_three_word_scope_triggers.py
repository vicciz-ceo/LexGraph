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

Sprint 2026-08-04-defs-il Phase C (item C1): the trigger-to-quote
connector was hardcoded to a literal comma; the real corpus also uses a
bare space, colon, or dash. Widened via the shared `il_trigger_grammar`
connector/parser (program efficiency directive).
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_trigger_grammar import (
    extract_quote_first_candidates,
    quote_first_re,
)
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = quote_first_re(r"(?:לענין|לעניין) סעיף זה")


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return extract_quote_first_candidates(article_body, _TRIGGER_RE, scope="local")


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
