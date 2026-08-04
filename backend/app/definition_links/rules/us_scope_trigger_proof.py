"""Core-authored proof-of-mechanism `ScopeTriggerRule` for the `US-*`
family (sprint 2026-08-04-defs-core-scope, gate C2: "English triggers
('As used in this section/subsection/chapter', 'For purposes of this
section/part') produce correctly-scoped definitions" -- one proven
English example, so the mechanism is live, not theoretical).

`"As used in this section, "Term" means ..."` -> a `scope="local"`
definition, scoped to the article it was found in. Family panels add
broader phrase/marker coverage as their OWN new modules in this same
directory (seam spec Seam 2's worked example); this module stays core's
minimal, always-on proof.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(
    r'As used in this section,\s*["“]([^"”]+)["”]\s*means\s+(.*?)(?=\.\s|$)',
    re.IGNORECASE | re.DOTALL,
)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return [
        DefinitionCandidate(
            terms=(match.group(1).strip(),),
            definition_text=match.group(2).strip(),
            scope="local",
            source_article_number=ctx.article_number,
        )
        for match in _TRIGGER_RE.finditer(article_body)
    ]


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))
