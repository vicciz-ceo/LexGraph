"""Rule: `לענין זה`/`בסעיף זה` (YOD spelling) -- an ADDITIVE sibling of the
FROZEN `extract._LOCAL_TRIGGER_RE` fixing two of its independently-found
defects at once (sprint 2026-08-04-defs-il, Phase C, items C1 + C2).

**C1 -- punctuation-variant widening.** `_LOCAL_TRIGGER_RE` hardcodes a
literal comma between the trigger phrase and the opening quote; the real
corpus also uses a bare space (e.g. `חוק שירות הציבור...` art.7's
`ולענין זה "חבר הנהלה"`) or a colon. Per ruling M15 (binding): this lives
in the FROZEN `extract` module, so the fix MUST be an additive sibling
rule, never an edit to `_LOCAL_TRIGGER_RE` itself.

**C2 -- same-line-swallow bug.** `_LOCAL_TRIGGER_RE` alternates `לענין
זה|בסעיף זה` in ONE pattern whose definition-text capture is `(.*)$` --
greedy, bounded only by end-of-line. When the same regex object fires
TWICE on one physical line, the first match's greedy capture swallows
the second trigger+quote before `finditer` can reach it (e.g. `חוק
הסדרת מקומות רחצה` art.5א: `בסעיף זה, "מקום מרפא" - ...; לענין זה, "בית
מלון" - ...` -- only `"מקום מרפא"` is captured today).

**Design decision (this Developer's call, per the Planner's log's
explicit "not decided by this Planner" note):** rather than build two
separate additive fixes (one per defect), ONE sibling rule using the
shared `il_trigger_grammar.extract_quote_first_candidates` helper solves
BOTH: that helper's trigger regex matches ONLY the trigger phrase +
connector (never a greedy to-end-of-line capture), so `finditer`'s scan
position after one match is never affected by how far the wrapper reads
ahead for ITS OWN definition text -- a second same-line trigger
occurrence is always found independently, regardless of what the first
one's own (best-effort) definition text swallowed. Widening the
connector and fixing the swallow are therefore the SAME code change,
not two.

**Non-overlap / dedup-hazard reasoning (per the manager's explicit
ask):** this rule's own trigger text (`לענין זה`/`בסעיף זה`, no
`סעיף`/`תקנה`/`קטן`/`משנה` word inserted) can never be a substring match
inside any OTHER sibling rule's longer trigger phrase (e.g. `לענין סעיף
זה` is NOT contained by `לענין זה` as a contiguous substring -- `סעיף`
sits in between), so no cross-rule double-capture risk exists against
any OTHER rule module.

Against the FROZEN rule itself, this sibling explicitly de-duplicates
by TERM against `extract.extract_local_definitions`'s own baseline
output for the same body, rather than relying on `pipeline.py`'s
downstream `(article_id, sorted(terms))` dedup to paper over a redundant
candidate (both would have been safe -- BOTH the frozen rule and this
sibling stamp `scope="local"` for this exact trigger vocabulary, so a
same-key duplicate could never silently swap in a different scope --
but a committed unit test,
`test_il_profile_extract_local_scope_definitions_matches_todays_extract_
local_and_adhoc`, asserts the IL profile's raw (pre-pipeline-dedup)
candidate list stays byte-identical in COUNT to calling
`extract_local_definitions`/`extract_adhoc_definitions` directly for a
body this sibling would otherwise also capture -- explicit de-dup keeps
that invariant true while still catching every genuinely-missed
occurrence, since a bare-space/colon/dash variant or a swallowed
second-same-line occurrence never appears in the frozen function's own
term set at all).
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate, extract_local_definitions
from app.definition_links.rules.il_trigger_grammar import (
    extract_quote_first_candidates,
    quote_first_re,
)
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = quote_first_re(r"(?:לענין זה|בסעיף זה)")


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    baseline_terms = {
        term for candidate in extract_local_definitions(article_body) for term in candidate.terms
    }
    candidates = extract_quote_first_candidates(article_body, _TRIGGER_RE, scope="local")
    return [c for c in candidates if not any(term in baseline_terms for term in c.terms)]


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
