"""Rule: `לעניין זה, "term" - definition` -- the TZERE spelling of the
frozen 2-word local-scope trigger, which `extract._LOCAL_TRIGGER_RE`
recognizes only in its YOD spelling (`לענין זה`) (sprint
2026-08-04-defs-il, QA cycle 1 fix, Group A test 1; program
2026-08-04-definition-completeness).

`לענין` (yod: ל-ע-נ-י-ן) and `לעניין` (tzere: ל-ע-נ-י-י-ן) are two
different literal strings to a regex -- neither is a substring of the
other (the tzere spelling has a doubled `י` where the yod spelling has
only one, so the yod 5-letter sequence never occurs contiguously inside
the tzere 6-letter one). This rule's trigger therefore matches ONLY the
tzere spelling and can never overlap with, or double-capture alongside,
`il_scope_triggers.py`'s frozen yod-only match: a given real occurrence
has exactly one spelling, so exactly one of the two rules ever fires on
it, and the union (zero-miss, no-suppression) mechanism the seam
guarantees for `ScopeTriggerRule` handles the rest. Deliberately does
NOT edit `extract._LOCAL_TRIGGER_RE` itself (frozen).

`il_seif_zeh_three_word_scope_triggers.py` (item 3) already covers both
spellings correctly for the 3-word `לענין/לעניין סעיף זה` variant; this
is the missing 2-word sibling QA cycle 1's yod/tzere audit found -- the
ONLY hole among all seven shipped IL rule modules (every other trigger
word this sprint uses does not contain the לענין/לעניין word at all).

1,563 real ordinary-article occurrences / 714 files corpus-wide (QA
cycle 1's trigger-independent sweep). Stamps `scope="local"`;
`source_article_number` is left unset and auto-defaulted to the current
article by `HebrewProfile.extract_local_scope_definitions`, same as the
frozen yod rule.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(r'לעניין זה,\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE)


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
