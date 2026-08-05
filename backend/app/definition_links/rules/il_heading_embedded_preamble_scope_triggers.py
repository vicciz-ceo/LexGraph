"""Rule: Class C -- preambles living in the article's own HEADING (sprint
2026-08-04-defs-il, Phase D, D-1a bundle). Root cause, live-confirmed
before this fix (see the sprint log's D-1a Developer entry): neither
`registry.RuleContext`, nor `HebrewProfile.extract_local_scope_
definitions`'s signature, nor its `pipeline.py` caller ever threads the
owning article's `.heading` text to a `ScopeTriggerRule` -- so a preamble
that sits ENTIRELY in the heading (`@ 8. (תיקון: תש"ף) : [[בתוספת זו]]
-`), with the body opening directly on `:-`/`::-`-marked entries and no
preamble line of its own, is reached by NEITHER list-shape sibling rule
(both scan only `article_body`'s own lines for a `PREAMBLE_RE` match).

## Detection

The article body's FIRST non-blank line is ALREADY a `:-`/`::-`-marked
entry -- i.e. no ordinary local preamble line precedes it anywhere in the
body at all, which is exactly what BOTH sibling list-shape rules already
require and already fail to find for this class (their own outer scan
never finds a `PREAMBLE_RE`-matching line in a Class-C body, so neither
ever starts a list). Whatever triggered this entry list, if anything,
therefore lives OUTSIDE the body -- most likely the heading. Every
subsequent `:-`/`::-` line is consumed the same tolerant way the sibling
rules already do (blank lines skipped, the first non-matching line ends
the list); each entry only ever produces a candidate when it ALSO matches
the shared, already-trusted `"term"[, "term2"...] - definition` entry
grammar (`il_list_shape_scope.parse_entry`, multi-term-aware per this
same session's Class-A fix) -- same precision argument as every other
list-shape rule this sprint ships: a body that happens to start with
something ending in `-`-shaped text for an unrelated reason (a recital
clause, a form letter, a malformed entry using a different defining verb)
still cannot fabricate a definition on its own, because `parse_entry`
conservatively returns `None` rather than guessing whenever the trusted
shape isn't there. Corpus-wide precision sanity sweep (this Developer,
scratchpad, read-only): 57 real corpus hits of this exact detection
shape; every hand-read non-definitional body (recital "והואיל:" clauses,
a stray `((,))` artifact line, "TERM פירושו definition" no-dash entries)
produces ZERO candidates because it fails `parse_entry`'s own quote/dash
requirements -- no false TERM capture found in the sweep.

## THE DESIGN DECISION -- scope semantics (this Developer's own call)

Reached via the ALREADY-WIRED ORDINARY-article `ScopeTriggerRule` path
(`HebrewProfile.extract_local_scope_definitions`), deliberately NOT via a
NEW `registry.HeadingRule` + definitions-SECTION dispatch, even though a
throwaway `HeadingRule` probe (D-1a Planner's own, independently
reproduced live by this Developer) proves that route is ALSO reachable
with zero frozen-file edits. Rejected because the section-dispatch route
forces every one of its candidates through the FROZEN `profiles.
HebrewProfile.determine_scope(body_text)` -- which NEVER receives heading
text (confirmed by direct read: `pipeline.py` calls it with `matcher_
article.body` only) and therefore falls through to its own unconditional
`return "law-wide"` default whenever the body itself carries no
recognized chapter/`ScopeKindRule` trigger, which is exactly the Class-C
case (the real trigger is invisible, sitting in the heading). Because
ruling M16 already, deliberately, EXCLUDES the exact schedule trigger
`בתוספת זו` from the law-wide vocabulary (it does NOT mean "the whole
law"), silently publishing `scope="law-wide"` here would directly
contradict the program's own established policy and manufacture real
false `USES_DEFINITION` edges reaching articles outside the defining
schedule/instrument-subpart.

This module instead builds its own `DefinitionCandidate`s directly --
scope is never delegated to `determine_scope` at all -- stamping the
conservative, narrowest-safe default `scope="local"` for EVERY instance,
uniformly, regardless of what its own (invisible-to-this-rule) heading
trigger actually says. This is the SAME default `il_list_shape_scope.
infer_scope` already falls back to for any unrecognized preamble, and
matches `HebrewProfile.main_unit_kind`. `"local"` UNDER-claims (a mention
in a SIBLING article of the same schedule/instrument will not link, and a
plain unqualified "definitions" heading that would ordinarily default to
"law-wide" also under-claims here -- both measured, real, and named
below) but never OVER-claims (no false link to an unrelated article
elsewhere in the law) -- the honest trade given there is genuinely no
live way, today, for ANY rule-module-only file to learn what a heading's
own trigger phrase says.

**Rejected alternatives** (per the brief's explicit ask):
1. `HeadingRule` + section dispatch, accepting whatever `determine_scope`
   computes -- rejected: contradicts M16 (see above), and there is no way
   to override or even inspect the scope `determine_scope` picks once the
   section-dispatch path is entered (`extract_definitions_from_section`
   stamps every one of its candidates with ONE scope string, uniformly,
   via `extract._parse_block(block, scope=scope, ...)`).
2. A NEW `scope_unit_kind` for "schedule"/"instrument-heading" (e.g.
   `"schedule"`) -- rejected per M-D3 (no MEASURED Hebrew structural
   convention gathered this session for what a "schedule" unit even
   is/how it nests) and moot regardless: it is the SAME "no live DATA
   SOURCE" gap M20 already found for סימן/חלק containment --
   `pipeline.py`'s `StructuralContext(..., heading_breadcrumbs=())` is
   hardcoded empty at its one production call site, so no
   `StructuralUnitRule` could ever populate a matching `ScopeUnit` even
   if this module declared the kind.
3. A module-level mutable side-channel (`HeadingRule.matches` stashing
   the heading string for a `ScopeKindRule.detect` call to read back) --
   rejected as a fragile, hidden coupling riding on `pipeline.py`'s own
   (frozen, not-this-panel's-contract) per-article call ordering, and it
   does not even answer the real question (WHICH scope a given heading
   trigger means) -- it would only relocate the guess, not remove it.
4. Escalating and leaving Class C red -- rejected: the brief frames this
   scope choice as this Developer's own call to make deliberately, and a
   legitimate, non-over-claiming rule-module-only path exists (this
   file), so there is no genuine blocker to escalate.

**Measured cost of the "local" default (honest, not hidden):** of the 57
corpus-wide hits of this detection shape, at least two real sub-populations
would ideally resolve broader than "local" if heading text were visible:
(a) headings whose own trigger IS an already-recognized law-wide phrase
(e.g. `: בצו זה -`, `: [[בתוספת זו]] -`) -- these get "local" here
instead of the schedule/instrument-wide reach their own words describe;
(b) a numbering-prefixed plain "הגדרות" heading baseline's own regex
doesn't recognize (e.g. `2.1. הגדרות`, `9.1.1 ... הגדרות ...`) -- these
would ordinarily default to "law-wide" (an unqualified definitions
heading) via `determine_scope`, but get "local" here too. Both are
UNDER-claims (recall gaps), never false links -- consistent with this
module's whole design, and a concrete, quantified starting point for
whoever eventually threads heading text through the frozen seam.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_list_shape_scope import make_candidate, parse_entry
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_DOUBLE_ENTRY_RE = re.compile(r"^\s*::-\s*(.*)$")
_SINGLE_ENTRY_RE = re.compile(r"^\s*:-\s*(.*)$")


def _first_content_line_index(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if line.strip():
            return i
    return None


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    lines = article_body.split("\n")
    start = _first_content_line_index(lines)
    if start is None:
        return []
    first_line = lines[start]
    if not (_DOUBLE_ENTRY_RE.match(first_line) or _SINGLE_ENTRY_RE.match(first_line)):
        return []

    results: list[DefinitionCandidate] = []
    n = len(lines)
    i = start
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        entry_match = _DOUBLE_ENTRY_RE.match(line) or _SINGLE_ENTRY_RE.match(line)
        if not entry_match:
            break
        parsed = parse_entry(entry_match.group(1).strip())
        if parsed is not None:
            terms, definition_text = parsed
            results.append(
                make_candidate(terms, definition_text.rstrip(";").strip(), "local", ctx)
            )
        i += 1
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
