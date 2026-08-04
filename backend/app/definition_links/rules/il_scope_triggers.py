"""IL's own registered `ScopeTriggerRule` bodies (sprint
2026-08-04-defs-core-scope, seam spec Seam 2; gate C3).

Wraps `extract.extract_local_definitions`/`extract_adhoc_definitions`
verbatim -- today's `לענין זה,`/`בסעיף זה,`/`(להלן - X)` behavior,
UNCHANGED (C5: Hebrew is a regression surface). These two functions are
NOT deleted (the seam spec's own "Deleted / emptied" list is explicit
about this); they simply become reachable ONLY via this registration +
`HebrewProfile.extract_local_scope_definitions`'s registry dispatch --
`pipeline.py` never calls either function directly again (C3).
"""

from __future__ import annotations

from app.definition_links.extract import (
    DefinitionCandidate,
    extract_adhoc_definitions,
    extract_local_definitions,
)
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)


def _extract_local(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return extract_local_definitions(article_body)


def _extract_adhoc(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return extract_adhoc_definitions(article_body)


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract_local))
register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract_adhoc))
