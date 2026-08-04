"""Rule: `בפסקה זו, "term" - definition` paragraph-scoped quoted
definitions (sprint 2026-08-04-defs-il, program
2026-08-04-definition-completeness, item 7; a fifth missed class, found
by the Planner sweeping the corpus for scope-trigger phrases beyond the
dossier's original four).

Same quote-first grammar as the chapter/siman/chelek triggers, trigger
word `בפסקה זו` ("in this paragraph") -- a granularity even NARROWER than
today's `"local"` (whole-article) scope: a single numbered paragraph/
sub-item within an ordinary article. Stamps the NEW generic kind
`scope="paragraph"`, `scope_value=None` -- best-effort only, not required
by this sprint's RED test.

QA cycle 1 (Group A test 7) widened the trigger alternation to also
recognize the alternate phrasing `לענין פסקה זו`/`לעניין פסקה זו`
("for/regarding this paragraph", both spellings) -- the SAME semantic
granularity as `בפסקה זו`, just a different preposition, 121 real
ordinary-article occurrences / 98 files (QA's sweep, both spellings
combined) not covered by the original exact-phrase regex.

CAPTURE ONLY, deliberately (escalation E7): containment for a below-
article granularity like this needs `profile.resolve_unit_path` to
recognize this fixture's own marker convention (colon-indented numbered/
lettered items, e.g. `(8)(א)`), but `HebrewProfile.resolve_unit_path`'s
only recognized IL below-article marker is the literal phrase `סעיף קטן
(X)`, which does not occur in this shape at all. Same open architecture
question as item 9's item-scoped class -- not a Planner/Developer
decision, escalated rather than guessed at.

Sprint 2026-08-04-defs-il Phase C (item C1): the trigger-to-quote
connector was hardcoded to a literal comma; the real corpus also uses a
bare space, colon, or dash. Widened via the shared `il_trigger_grammar`
connector/parser (program efficiency directive) -- which also correctly
handles the multi-term-before-dash shape a real fixture exercises
(`בפסקה זו - "מועצה אזורית" ו"תחום מועצה אזורית" - ...`).
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_trigger_grammar import (
    extract_quote_first_candidates,
    quote_first_re,
)
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_TRIGGER_RE = quote_first_re(r"(?:בפסקה זו|לענין פסקה זו|לעניין פסקה זו)")


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results = extract_quote_first_candidates(article_body, _TRIGGER_RE, scope="paragraph")
    for candidate in results:
        candidate.scope_value = None
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
