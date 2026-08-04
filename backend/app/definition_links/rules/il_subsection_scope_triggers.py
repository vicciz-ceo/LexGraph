"""Rule: subsection-scoped (סעיף קטן / תקנת משנה / פסקת משנה) quote-first
triggers (sprint 2026-08-04-defs-il, QA cycle 1 fix, Group A tests
3+5+6+8; program 2026-08-04-definition-completeness, ruling D-Q1).

Four sibling trigger phrases, all classified subsection-level by D-Q1
(narrower than `"local"`/article-level -- exactly the granularity the
seam's `UnitPath`/`resolve_unit_path` model already accounts for, so
`scope="subsection"` is the correct existing kind, not a new generic
one): `בסעיף קטן זה` ("in this sub-article"), `בתקנת משנה זו` /
`(לענין|לעניין) תקנת משנה זו` ("in this sub-regulation" -- QA's sweep
found the `ב`-prefixed and bare `לענין/לעניין`-prefixed spellings as two
distinct real families), and `בפסקת משנה זו` ("in this sub-paragraph").
None of the four trigger phrases is a substring of another (`קטן`/
`תקנת`/`פסקת` all differ), so no pattern can ever double-match the same
text span as a sibling.

Stamps `scope="subsection"`, `scope_value=None` -- CAPTURE ONLY, per this
sprint's established discipline throughout (deliberately not attempting
to compute a real subsection label here). This is deliberately SAFE, not
merely incomplete: `matcher._subsection_contains_offset` requires
`mention_path[0].value in allowed`, where `allowed = (None,)` when
`scope_value` is `None` -- a real subsection label read off `resolve_
unit_path` is never `None` itself, so that membership test is always
False and no spurious `USES_DEFINITION` edge can ever be fabricated from
an under-specified `scope_value`. Full containment for this class is a
separate concern this RED-test cycle does not ask this Developer to
solve.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_PATTERNS = (
    re.compile(r'בסעיף קטן זה,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE),
    re.compile(r'בתקנת משנה זו,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE),
    re.compile(r'(?:לענין|לעניין) תקנת משנה זו,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE),
    re.compile(r'בפסקת משנה זו,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE),
)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for pattern in _TRIGGER_PATTERNS:
        for match in pattern.finditer(article_body):
            results.append(
                DefinitionCandidate(
                    terms=(match.group(1).strip(),),
                    definition_text=match.group(2).strip(),
                    scope="subsection",
                    scope_value=None,
                )
            )
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
