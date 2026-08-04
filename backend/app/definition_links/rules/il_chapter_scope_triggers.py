"""Rule: `בפרק זה, "term" - definition` chapter-scoped quoted definitions
(sprint 2026-08-04-defs-il, program 2026-08-04-definition-completeness,
item 2a; gate I2(a)/I3).

Quote-first grammar, mirroring `extract._LOCAL_TRIGGER_RE`'s shape but
with the chapter trigger word instead of the 2-word local triggers:
`TRIGGER, "term" - definition` ending at end-of-line. Trigger word
`בפרק זה` ONLY -- `לפרק זה` is deliberately DROPPED (live-reconfirmed on
the real corpus: 103 raw occurrences, all cross-references like `סימן ג'
לפרק זה` / `התוספת לפרק זה`, zero in this definitional quote-dash
grammar; see the sprint log's "v2 -> v2.5 re-spec" entry).

Stamps `scope="chapter"` AND `source_chapter=ctx.chapter` itself --
`HebrewProfile.extract_local_scope_definitions` (profiles.py) only
auto-defaults `.source_article_number` when a rule leaves it unset, never
`.source_chapter`; a rule that omitted this would produce a `Definition`
`matcher._in_scope`'s `"chapter"` branch could never contain (it compares
`article.chapter` against `definition.source_chapter`).
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(r'בפרק זה,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return [
        DefinitionCandidate(
            terms=(match.group(1).strip(),),
            definition_text=match.group(2).strip(),
            scope="chapter",
            source_chapter=ctx.chapter,
        )
        for match in _TRIGGER_RE.finditer(article_body)
    ]


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
