"""Rule: regulation-level (`תקנה`) local-scope quote-first triggers
(sprint 2026-08-04-defs-il, QA cycle 1 fix, Group A tests 2+4; program
2026-08-04-definition-completeness, ruling D-Q1).

`בתקנה זו, "term" - definition` (2-word) and its 3-word sibling `לענין/
לעניין תקנה זו, "term" - definition` -- D-Q1 closed the scope question by
evidence, not assumption: the manager measured `sections.parse_articles`
over three real regulation documents (65 / 60 / 8 `Article` rows, every
one containing `בתקנה זו`) and confirmed `תקנה` units parse as ordinary
`Article` rows on the live pipeline path. A regulation-scoped definition
is therefore exactly as narrow as an article-scoped one -- `scope=
"local"`, enforced by the SAME existing containment machinery as any
other local-scoped definition (`matcher._in_scope`'s `"local"` branch),
no schema gap, no capture-only caveat needed.

427 real ordinary-article occurrences / 289 files for the 2-word form;
104 more / 90 files for the 3-word form, both spellings combined (QA
cycle 1's trigger-independent sweep). Both spellings (`לענין`/`לעניין`)
covered for the 3-word variant, same precedent as item 3's
`il_seif_zeh_three_word_scope_triggers.py`. The two patterns' trigger
text never overlaps (`בתקנה` vs. `לענין`/`לעניין` are different leading
words), so a given real occurrence can only ever match one of them --
no double-capture risk.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TWO_WORD_RE = re.compile(r'בתקנה זו,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE)
_THREE_WORD_RE = re.compile(
    r'(?:לענין|לעניין) תקנה זו,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE
)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for pattern in (_TWO_WORD_RE, _THREE_WORD_RE):
        for match in pattern.finditer(article_body):
            results.append(
                DefinitionCandidate(
                    terms=(match.group(1).strip(),),
                    definition_text=match.group(2).strip(),
                    scope="local",
                )
            )
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
