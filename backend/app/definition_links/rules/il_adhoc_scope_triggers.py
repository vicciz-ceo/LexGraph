"""Rule: ad-hoc parenthetical `(TRIGGER - term)` markers, widened beyond
today's `להלן`-only `extract_adhoc_definitions` (sprint 2026-08-04-defs-il,
program 2026-08-04-definition-completeness, item 4 + item 10 "round 2";
gate I2(c)).

Same unquoted-apposition grammar as `extract._ADHOC_RE`
(`\\(\\s*TRIGGER\\s*[-:]\\s*term\\s*\\)`), NEW trigger words `בפרק זה`/
`בסימן זה`/`בחלק זה`/`בסעיף זה`/`בפסקה זו` -- this is an ADDITIONAL rule,
distinct from (and does not touch) the existing `להלן`-triggered
`il_scope_triggers.py` registration.

Round 2 (item 10, manager-requested): `בסעיף זה` (2,335 real occurrences /
572 files corpus-wide -- the single largest population found in this
sprint's whole re-spec pass, live-measured through `sections.
parse_articles`, not raw grep) and `בפסקה זו` (221/117) recur in this same
unquoted-apposition grammar, uncaptured by either `_ADHOC_RE` or this
rule's original 3-word trigger set. Only the 2,328/213 occurrences sitting
inside ORDINARY (non-הגדרות-headed) articles are reachable by widening
this rule -- occurrences embedded inside a definitions-heading section's
own entry body are a separate, E6-blocked gap (item 11) this rule cannot
fix (`ScopeTriggerRule` is never invoked for that dispatch branch).

Scope is dispatched BY TRIGGER WORD, not uniform:
- `בפרק זה` -> `scope="chapter"`, `source_chapter=ctx.chapter` (same
  containment-enabling requirement as `il_chapter_scope_triggers.py`'s
  quote-first sibling -- this sub-case also serves gate I3).
- `בסימן זה`/`בחלק זה` -> `scope="siman"`/`"chelek"`, `scope_value=None`
  (same capture-only limitation as `il_siman_chelek_scope_triggers.py` --
  containment is a separate, unwired architecture gap, not something this
  rule can fix).
- `בסעיף זה` -> `scope="local"` -- same granularity as the already-
  trusted quote-first `בסעיף זה`/`לענין זה` triggers; `source_article_
  number` is left unset here and auto-defaulted to the current article by
  `HebrewProfile.extract_local_scope_definitions`, giving this sub-case
  correct containment for free, same as item 3's rule.
- `בפסקה זו` -> `scope="paragraph"` (the SAME generic kind
  `il_paragraph_scope_triggers.py` already registers for the quote-first
  grammar, item 7), `scope_value=None` -- same capture-only limitation.

Reuses the existing <=4-token safety cap on the captured term (Planner's
corpus scan: only 46/1041 sampled real parentheticals exceed it; 0/1041
verb-shaped false positives; round 2's own 25-sample manual check found
zero verb-shaped/citation-shaped false positives for `בסעיף זה`) -- same
discipline as `extract_adhoc_definitions`, applied here independently
since that function is frozen and not called by this new rule.

QA cycle 1 precision fix: confirmed false positives (`(בסעיף זה - סעיף
9)` / `(בסעיף זה – סעיף 149א)` / `(בסעיף זה - סעיף 51טו)`) are all the
SAME citation-shorthand-naming idiom -- "hereinafter in this section,
'section N'" -- a cross-reference convention riding the identical
apposition grammar this rule trusts for substantive terms, not a
substantive definition itself. `_CITATION_SHAPED_TERM_RE` rejects a
captured term that is EXACTLY the literal word `סעיף` followed by a
number (optionally with a trailing Hebrew-letter section suffix, e.g.
`149א`/`51טו`) and nothing else -- narrow by construction so it can only
ever match a bare section-number label, never a genuine multi-word
substantive term like `"יום התחילה"`/`"מענק נוסף"`/`"תמורה"` (none start
with `סעיף`). Applied uniformly across every trigger word, since a
citation-shaped label is never a legitimate definition regardless of
which trigger introduced it.
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
    r"\(\s*(בפרק זה|בסימן זה|בחלק זה|בסעיף זה|בפסקה זו)\s*[-:]\s*([^)]+?)\s*\)"
)

_SCOPE_BY_TRIGGER = {
    "בפרק זה": "chapter",
    "בסימן זה": "siman",
    "בחלק זה": "chelek",
    "בסעיף זה": "local",
    "בפסקה זו": "paragraph",
}

# QA cycle 1 precision fix: a captured term that is JUST a bare section
# citation ("סעיף 9" / "סעיף 149א" / "סעיף 51טו") is a cross-reference
# shorthand, never a substantive defined term -- narrow by construction
# (literal "סעיף" + a number + an optional trailing Hebrew-letter
# suffix, nothing else) so it can never reject a genuine multi-word term.
_CITATION_SHAPED_TERM_RE = re.compile(r"^סעיף\s+\d+[א-ת]*$")


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for match in _TRIGGER_RE.finditer(article_body):
        trigger, raw_term = match.group(1), match.group(2).strip()
        term = raw_term
        if term.startswith('"') and term.endswith('"') and len(term) >= 2:
            term = term[1:-1].strip()
        if not term or len(term.split()) > 4:
            continue
        if _CITATION_SHAPED_TERM_RE.match(term):
            continue

        scope = _SCOPE_BY_TRIGGER[trigger]
        if scope == "chapter":
            candidate = DefinitionCandidate(
                terms=(term,),
                definition_text=term,
                scope=scope,
                source_chapter=ctx.chapter,
            )
        elif scope == "local":
            # `source_article_number` left unset -- auto-defaulted to the
            # current article by `HebrewProfile.extract_local_scope_
            # definitions`, same as item 3's 3-word-trigger rule.
            candidate = DefinitionCandidate(
                terms=(term,),
                definition_text=term,
                scope=scope,
            )
        else:
            candidate = DefinitionCandidate(
                terms=(term,),
                definition_text=term,
                scope=scope,
                scope_value=None,
            )
        results.append(candidate)
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
