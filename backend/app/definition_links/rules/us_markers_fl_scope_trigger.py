"""Rule: FL's ordinary-article (NOT Definitions-headed) inline scope
trigger -- `"(1) As used in this section, unless the context otherwise
requires: (a) "Term" means ..."` -- part of the sprint's `##
Next Steps`-flagged "unbounded last entry" corpus fact 3 (relayed rate:
last quoted term's definition swallows ~88% unrelated trailing content).

`STATE_FL_TXXXIII_C540_S540.11` is NOT itself Definitions-headed
(`is_definitions_heading` is False for its own heading -- confirmed
live), so it reaches the pipeline via the ORDINARY-article
`extract_local_scope_definitions`/`ScopeTriggerRule` path, not this
sprint's own Definitions-HEADING family-3 mandate -- flagged to the
program manager as a family-boundary question the same way pass 1 flagged
VT (this is `defs-us-scoped-inline` territory per the seam doc's own
module inventory), but authored here anyway per the sprint's explicit
brief instruction to include the FL example, since the required BEHAVIOR
(no last-entry-swallows-the-rest-of-the-article defect) is identical
regardless of which family ships the fix. Core's own proof rule
(`us_scope_trigger_proof.py`) does not match this row (its regex requires
the quoted term immediately after "As used in this section,"; FL
interposes "unless the context otherwise requires:" first).

Reuses the SAME quote-anchored boundary engine the Definitions-heading
family uses (`us_markers_boundary.extract_quote_anchored_entries`) --
the underlying defect (a last entry with no closing boundary swallowing
unrelated trailing content, here subsection (2)'s substantive criminal-law
text) is the identical shape; the engine's marker-chain hard-stop already
handles FL's own `(2)(a)` immediately-adjacent-marker shape (see
`us_markers_boundary.py`'s own docstring). Scoped to `US-FL` only, not
`"US-*"` -- this is one confirmed row's preamble shape, not a
corpus-verified general FL (or other-state) trigger phrase."""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)
from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries

_TRIGGER_RE = re.compile(
    r"As used in this section,\s*unless the context otherwise requires:\s*", re.IGNORECASE
)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    trigger = _TRIGGER_RE.search(article_body)
    if trigger is None:
        return []
    entries = extract_quote_anchored_entries(article_body[trigger.end() :])
    return [
        DefinitionCandidate(
            terms=(term,),
            definition_text=definition_text,
            scope="local",
            source_article_number=ctx.article_number,
        )
        for term, definition_text in entries
    ]


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-FL",), extract=_extract))
