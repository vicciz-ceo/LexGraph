"""Rule: the `::-` nested-list-under-preamble SHAPE, generalized beyond
item 9's single hardcoded trigger word (sprint 2026-08-04-defs-il, QA
cycle 1 fix, Group B; program manager's binding efficiency directive --
build ONE mechanism serving ~2,288 occurrences, not eight per-trigger
clones).

`il_prat_zeh_item_scope_triggers.py` (item 9) already proved this SHAPE
-- a preamble line ending in a bare, standalone `-` immediately followed
by one or more `::-`-marked `"term" - definition` entry lines -- is
reachable via the live, wired `ScopeTriggerRule` mechanism, but hardcoded
its own detection to the single trigger word `בפרט זה`. QA cycle 1's
trigger-independent sweep found 2,300 real corpus occurrences of the bare
SHAPE (any preamble text ending `-`, followed immediately by `::-`
entries); only 12 (0.5%, item 9's own) were captured before this rule --
proof the miss is about the LIST SHAPE, not trigger-word coverage. Even
an ALREADY fully-implemented inline trigger (`בסעיף זה`, items 4/10)
still misses its own term when the quote sits on a separate `::-` line
instead of inline on the trigger's own line.

Detection is deliberately decoupled from any specific trigger word: ANY
line ending in a standalone `-` (preceded by whitespace, so a trailing
hyphenated token like `...-2012` never qualifies) opens a list; every
immediately-following line that is blank or `::-`-marked is consumed
(blank lines are skipped, not treated as the list's end); the first line
that is neither ends it -- same tolerant algorithm item 9 already proved
safe. This is intentionally broad at the DETECTION step because the
SECOND gate is the real precision filter: an entry line only ever
produces a candidate when it ALSO matches the unambiguous `"term" -
definition` quote-dash shape (`_TERM_DASH_RE` below) -- identically to
`_ADHOC_RE`/every other rule this sprint ships. A preamble ending in `-`
for an unrelated reason (e.g. a table row) can never fabricate a
definition on its own; it can only "activate" entries that already look
exactly like every other definition this codebase already trusts.

Scope is inferred from the preamble line's own text, reusing the SAME
trigger-phrase-to-scope vocabulary already established by every sibling
`ScopeTriggerRule` this sprint ships (longest/most-specific phrase
checked first, so e.g. `בתקנת משנה זו` is never shadowed by a shorter
phrase it happens to contain). A preamble whose text matches none of
these known phrases defaults to `scope="local"` -- the narrowest, safest
default (never overclaims chapter/law-wide reach), matching
`HebrewProfile.main_unit_kind`. `"chapter"` is the only kind requiring a
dedicated field (`source_chapter=ctx.chapter`, same requirement as every
other chapter-scoped rule this sprint ships); every other non-`"local"`
kind sets `scope_value=None` (capture only, same discipline as its own
single-line sibling rule -- and, per `il_subsection_scope_triggers.py`'s
own reasoning, safe-by-construction rather than merely incomplete).

Deliberately does NOT import item 9's private helpers (keeps this module
independently readable, avoids coupling two independently-shipped rule
files) -- the algorithm is the same one item 9 already proved, written
generically here.

Sprint 2026-08-04-defs-il Phase C (ruling M16 + item C4): the
preamble->scope vocabulary table (`_SCOPE_TRIGGER_WORDS`/`_infer_scope`)
and the candidate-building helper (`_make_candidate`) now live in the
SHARED `il_list_shape_scope.py` module -- reused verbatim by the NEW
single-colon `:-` sibling rule (`il_single_colon_list_scope_triggers.py`,
item C4) so the vocabulary is measured and maintained ONCE, not
duplicated per marker width (program efficiency directive). This module
itself is UNCHANGED behaviorally except for M16's own fix: an
instrument-naming preamble (`בחוק זה -`, `בתקנות אלה -`, ...) now
classifies `"law-wide"` instead of under-claiming `"local"` -- the SAME
vocabulary extension the new sibling rule needs, added to the shared
table rather than duplicated here.

Sprint 2026-08-04-defs-il, Phase D, D-1a bundle -- Class A fix: this
module used to keep its OWN private single-term-only `_TERM_DASH_RE`
copy despite this very docstring already claiming the candidate-building
logic was shared -- that regex was NEVER actually imported from `il_
list_shape_scope.py` (a doc/code mismatch, confirmed live before this
fix), so a `::-` entry naming >=2 terms (`"t1" ו"t2" - def`) silently
dropped the whole entry, exactly the FROZEN `extract._parse_terms_and_
qualifier`-adjacent bug this sprint's own single-term grammar had
everywhere else. Now genuinely shares `parse_entry` (multi-term-aware)
with the `:-` sibling, closing both the bug and the doc/code mismatch in
one change.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_list_shape_scope import infer_scope, make_candidate, parse_entry
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_PREAMBLE_RE = re.compile(r"\S.*\s-\s*$")
_ENTRY_LINE_RE = re.compile(r"^\s*::-\s*(.*)$")


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    lines = article_body.split("\n")
    n = len(lines)
    results: list[DefinitionCandidate] = []
    i = 0
    while i < n:
        if not _PREAMBLE_RE.search(lines[i].rstrip()):
            i += 1
            continue
        scope = infer_scope(lines[i])
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            entry_match = _ENTRY_LINE_RE.match(line)
            if not entry_match:
                break
            parsed = parse_entry(entry_match.group(1).strip())
            if parsed is not None:
                terms, definition_text = parsed
                results.append(
                    make_candidate(terms, definition_text.rstrip(";").strip(), scope, ctx)
                )
            i += 1
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
