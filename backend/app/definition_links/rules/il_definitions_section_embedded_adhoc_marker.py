"""Rule: `TermClauseRule` for the ad-hoc `(בפסקה זו - X)` apposition
marker EMBEDDED inside an existing entry's OWN body text, within a
recognized הגדרות-heading section (sprint 2026-08-04-defs-il, Phase D /
D-1b bundle, contract item 11 -- `test_class_c_adhoc_parenthetical_
beparagraph_zo_inside_definitions_section_is_captured`).

## Root cause (re-confirmed live this session)

`pipeline.py`'s strict `if is_definitions_section: ... else: ...` dispatch
(FROZEN, unchanged) means a definitions-heading article's body is handled
ONLY by `profile.extract_definitions_from_section` -- `il_adhoc_scope_
triggers.py`'s `ScopeTriggerRule` (the ordinary-article `(TRIGGER - X)`
widening, items 4/10) is never invoked for it, no matter how its own
trigger list is widened. The real fixture (`חוק הבנקאות (שירות ללקוח)`
article 1) already captures its other 20 `:-`-marked entries correctly
today via baseline's own unchanged `:-` grammar (confirmed live -- this is
NOT a class-(d) missing-block gap) -- only the ad-hoc `(בפסקה זו - חוק
הדואר)` marker embedded INSIDE the "גוף פיננסי" entry's own multi-line
body (a `::`-continuation of that entry's baseline `:-` block) is missed,
because nothing ever scans an already-extracted block's OWN text for a
second, embedded definition.

## Fix

A `TermClauseRule` -- consumed by `HebrewProfile.extract_definitions_
from_section`'s own union loop (`for block in all_blocks: for rule in
registry.term_clause_rules_for(...): ...`) against EVERY block (baseline's
own `:-` blocks included, not just this bundle's sibling `EntrySplitterRule`
blocks) -- scans each block's raw text for the same `(בפסקה זו - X)`
apposition grammar `il_adhoc_scope_triggers.py` already trusts for the
ordinary-article path: same <=4-token cap and citation-shaped-term guard,
same `scope="paragraph"`/`scope_value=None` stamp as that rule's own
`בפסקה זו` branch and `il_paragraph_scope_triggers.py`'s quote-first
sibling (M-D3: reusing an already-measured convention for this exact
trigger word, not inventing a new one). Deliberately NOT importing from
`il_adhoc_scope_triggers.py` (a D-1a-owned file this bundle must not
touch/couple to, per the brief) -- the small trigger regex is duplicated
here instead.

Only `בפסקה זו` is handled (this bundle's one RED test); the other
`(TRIGGER - X)` trigger words item 4/10 already widened for the ordinary-
article path are NOT duplicated here -- no observed real occurrence of any
of them embedded inside a definitions-section entry body was found or
required by this bundle (out of scope; not claimed exhaustive).

## Regression scan (this session, read-only, before committing)

Scanned every definitions-heading article body in `backend/tests/fixtures/
wiki_laws/*.wiki` for a parenthesized `(בפסקה זו - X)` span: exactly 1
hit, this bundle's own target fixture -- zero other fixture is affected.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import TermClauseRule, register_term_clause_rule

_TRIGGER_RE = re.compile(r"\(\s*בפסקה זו\s*[-:]\s*([^)]+?)\s*\)")

# Same narrow, false-positive-proof guard `il_adhoc_scope_triggers.py`
# already established for this exact trigger family (QA cycle 1's
# precision fix) -- a captured term that is JUST a bare section citation
# is a cross-reference shorthand, never a substantive defined term.
_CITATION_SHAPED_TERM_RE = re.compile(r"^סעיף\s+\d+[א-ת]*$")


def _parse(block_text: str) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for match in _TRIGGER_RE.finditer(block_text):
        term = match.group(1).strip()
        if term.startswith('"') and term.endswith('"') and len(term) >= 2:
            term = term[1:-1].strip()
        if not term or len(term.split()) > 4:
            continue
        if _CITATION_SHAPED_TERM_RE.match(term):
            continue
        results.append(
            DefinitionCandidate(
                terms=(term,),
                definition_text=term,
                scope="paragraph",
                scope_value=None,
            )
        )
    return results


register_term_clause_rule(TermClauseRule(jurisdiction_codes=("IL",), parse=_parse))
