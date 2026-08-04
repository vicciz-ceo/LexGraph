"""PR's own registered `ScopeTriggerRule` bodies (sprint 2026-08-04-defs-us-pr,
cycle-5 item 26; gate P2). Mirrors `il_scope_triggers.py`'s exact shape:
wraps `pr_profile`'s own Spanish-language extractors verbatim.

Under ruling M-R13 (Option D), this module registers exactly TWO rules --
`extract_local_definitions` (widened, item 18a: the explicit "A los fines/
efectos/propósitos de este Artículo" trigger family) and
`extract_adhoc_definitions` (the "(en adelante, X)" apposition, unchanged).
The originally-planned THIRD rule, wrapping a NEW `extract_inline_local_
definitions` (item 18c, an untriggered whole-body sweep), is deliberately
NOT built or registered this cycle -- deferred until core's dispatch sprint
lands and canonical `Definiciones` rows route to `pipeline.py`'s `if`
branch instead of reaching this seam at all (see the sprint log's M-R13
ruling for the full reasoning: the 38-row residual an unguarded sweep would
otherwise leak on disappears by construction at that point, at zero recall
cost -- guarding it here now would only be approximating that outcome with
a body-side heuristic, which the measured data rejected as an option).

These two functions are NOT deleted or moved; they simply become reachable
via this registration + `USProfile.extract_local_scope_definitions`'s
registry dispatch (`us_profile.py:1162`), exactly as `il_scope_triggers.py`
already does for Hebrew.
"""

from __future__ import annotations

from app.definition_links import pr_profile
from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)


def _extract_local(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return pr_profile.extract_local_definitions(article_body)


def _extract_adhoc(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return pr_profile.extract_adhoc_definitions(article_body)


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-PR",), extract=_extract_local))
register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-PR",), extract=_extract_adhoc))
