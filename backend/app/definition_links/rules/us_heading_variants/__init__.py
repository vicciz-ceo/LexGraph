"""Family-4 "heading variants" rule package (sprint 2026-08-04-defs-us-headings,
gates U1/U3/U4).

`us_profile.is_definitions_heading` (see that module's header comment)
recognizes a Definitions heading only when "Definition(s)" is literally its
own FIRST word, or its LAST substantive word (preposition-exclusion guard).
Real corpus rows defeat both in many distinct, evidenced shapes -- see the
sprint contract's Mandate and the RED unit test module docstrings for the
full rule specs, recall/precision numbers, and fixture provenance.

  - R-SEC (`_positional_rules.rule_sec`): an abbreviated `Sec.`/`Secs.`/
    `Art.`/`Article` section-label -- strip it, apply baseline's own
    first-word/last-word decision.
  - R-MID (`_positional_rules.rule_mid`): `Definition`/`Definitions` as an
    exact, standalone TAIL TOKEN at any position except the very first or
    last, guarded by the same preposition-exclusion semantics as baseline.
  - R-VERB-bare (`_positional_rules.rule_verb_bare`): the heading's last
    tail token is exactly `defined` -- the "`X` defined" drafting
    convention baseline has no notion of at all.
  - R-VERB-extended (`_verb_extended.rule_verb_extended*`): `defined`
    immediately followed by punctuation, a dash, or a whitelisted
    connector word/phrase -- the whitelist has grown every cycle (BUG1-5 in
    cycle 2; `for`/`as`/`term` in cycle 3, H-R9; D-DF's body-gated split of
    `for` in cycle 4; `and` (item 10), RI mojibake dash tolerance (item 11),
    and `further`/`when`/`in case of`/a trailing numeric-artifact strip
    (item 15) in cycle 5 -- see `_verb_extended.py`'s own module docstring
    for the full per-branch evidence).
  - R-TRUNC (`_positional_rules.rule_trunc`): the last tail token is a
    verified non-English strict prefix of "definitions" (a real corpus
    truncation defect, Colorado-specific).
  - R-MISSPELL (`_positional_rules.rule_misspell`): the last tail token is
    a known scrape-corpus misspelling of "definitions".
  - R-POINTER (`_positional_rules.matches_pointer_table_heading`, cycle 5
    item 12, D-MT-E1): "Other defined terms" / "Index of definitions [in
    code/act/chapter/title]" -- a repeated drafting convention whose body
    is a cross-reference TABLE, not neither R-MID nor R-VERB reach.

Per the seam published by `claude/defs-core-scope` (`## Seam spec
(published)`, "Seam 2 -- per-jurisdiction rule registry"), a registered
`HeadingRule.matches` callable is consulted ONLY after baseline's own
`is_definitions_heading` has already returned False for the same heading.
Every rule can therefore only ever flip a currently-False verdict to True
-- except through the preposition guard, which is existing negative-
evidence logic, not a narrowing of positive evidence.

Self-contained (ruling H-R4): this package owns its own leading-noise
strip, section-label strip, number-token strip, trailing-bracket strip,
tail tokenizer, preposition-exclusion set, and mojibake normalization --
independent copies of `us_profile.py`'s private regexes/sets
(`_shared.py`).

Cycle 4 (director ruling D-DF, program ruling P-R8): `defined for` ships
capture-worthy only when the BODY also carries a self-definition marker.
`matches_heading_variant_unconditional` is the family-4 union with the
`for` alternation removed; `matches_defined_for_heading` is that
alternation alone; `defines_in_body` (`_self_definition.py`) is the gate,
consumed via `HeadingRule.body_confirms`. `matches_heading_variant` keeps
its full historical meaning unchanged -- pinned equal to
`matches_heading_variant_unconditional(h) or matches_defined_for_heading(h)`
for every heading (re-confirmed after cycle 5's additions, which widen the
SAME regexes both compositions share, in lockstep).

Cycle 5, item 13 (`_qualifier.py`): `defined (qualifier)` / `defined to
[verb]` ships as a THIRD, independently GATED `HeadingRule` (own
`matches_defined_qualifier_heading` + `defines_qualifier_in_body` pair) --
a real, evidenced precision risk (the VA "Evidence of habit or routine
practice; defined..." row) means this shape cannot ship unconditional
either. Deliberately EXCLUDED from `matches_heading_variant`'s union: unlike
`for` (already inside the original whitelist before D-DF split it out),
this shape was never part of that predicate's historical meaning.

Cycle 5, item 14 (`_scope_parse.py`): pure heading-text scope-VALUE
extraction (`chapter_range_scope_bounds`, `enumerated_local_scope_targets`)
for the two U2 rows measured as containment-mechanism-ready today. Not
registered as a `HeadingRule` -- these are plain functions consumed
directly by callers that already have a recognized definitions-section
heading in hand; no shared-module wiring (U3).

MODULE SPLIT (cycle 5, style gate -- the pre-split single file was 479
lines against the repo's 300-line convention): split along rule-family/
responsibility boundaries into sibling modules, each comfortably under 300
lines -- `_shared.py` (primitives/tokenizer/preposition-guard/mojibake),
`_positional_rules.py` (R-SEC/R-MID/R-VERB-bare/R-TRUNC/R-MISSPELL +
R-POINTER), `_verb_extended.py` (R-VERB-extended's full connector/artifact
whitelist), `_self_definition.py` (D-DF's `defines_in_body`, UNCHANGED),
`_qualifier.py` (item 13's gated pair), `_scope_parse.py` (item 14's pure
parsers). THIS file re-exports the full public API and owns all THREE
`register_heading_rule` calls, so `app.definition_links.rules.
us_heading_variants` keeps importing and behaving exactly as before the
split: the parent `rules/__init__.py`'s auto-discovery (core-owned, NOT
edited here) imports sibling modules of `rules/` by name via
`pkgutil.iter_modules` -- since this split turned the single file into a
package, auto-discovery now imports THIS `__init__.py` (one name,
"us_heading_variants", exactly as before), which in turn imports every
sibling module below at package-import time. Registration therefore still
fires exactly three times, once each, the first time this package is
imported (Python's module cache makes every subsequent import of any
sibling module -- whether reached via this file or directly by a test --
a no-op, so there is no risk of double-registration).
"""

from __future__ import annotations

from app.definition_links.rules.registry import HeadingRule, register_heading_rule
from app.definition_links.rules.us_heading_variants._positional_rules import (
    matches_pointer_table_heading,
    rule_mid,
    rule_misspell,
    rule_sec,
    rule_trunc,
    rule_verb_bare,
)
from app.definition_links.rules.us_heading_variants._qualifier import (
    defines_qualifier_in_body,
    matches_defined_qualifier_heading,
)
from app.definition_links.rules.us_heading_variants._scope_parse import (
    chapter_range_scope_bounds,
    enumerated_local_scope_targets,
)
from app.definition_links.rules.us_heading_variants._self_definition import defines_in_body
from app.definition_links.rules.us_heading_variants._verb_extended import (
    matches_defined_for_heading,
    rule_verb_extended,
    rule_verb_extended_unconditional,
)

__all__ = [
    "matches_heading_variant",
    "matches_heading_variant_unconditional",
    "matches_defined_for_heading",
    "defines_in_body",
    "matches_pointer_table_heading",
    "matches_defined_qualifier_heading",
    "defines_qualifier_in_body",
    "chapter_range_scope_bounds",
    "enumerated_local_scope_targets",
]


def matches_heading_variant(heading: str) -> bool:
    """True when `heading` matches any of the family-4 rules above, UNCHANGED
    historical meaning (cycle 4, D-DF; re-confirmed cycle 5) -- the full
    union, still INCLUDING the `for` connector alternation. Pinned equal to
    `matches_heading_variant_unconditional(h) or matches_defined_for_heading(h)`
    for every heading. Callers are expected (per the seam's baseline-first/
    registry-second contract) to consult this only after `us_profile.
    is_definitions_heading` has already returned False for the same
    heading."""
    return (
        rule_sec(heading)
        or rule_mid(heading)
        or rule_verb_bare(heading)
        or rule_verb_extended(heading)
        or rule_trunc(heading)
        or rule_misspell(heading)
        or matches_pointer_table_heading(heading)
    )


def matches_heading_variant_unconditional(heading: str) -> bool:
    """Cycle 4, D-DF: the union of R-SEC, R-MID, R-VERB-bare,
    R-VERB-extended-minus-`for`, R-TRUNC, R-MISSPELL, R-POINTER -- every
    family-4 shape EXCEPT the `defined for` connector, which is gated on
    `defines_in_body` instead (see `matches_defined_for_heading`, registered
    separately below). This is the rule actually registered with
    `body_confirms=None`."""
    return (
        rule_sec(heading)
        or rule_mid(heading)
        or rule_verb_bare(heading)
        or rule_verb_extended_unconditional(heading)
        or rule_trunc(heading)
        or rule_misspell(heading)
        or matches_pointer_table_heading(heading)
    )


# THREE registrations, in this exact order -- unconditional first (every
# family-4 shape except `defined for`/item 13's qualifier shape,
# body_confirms left at its default None), then D-DF's gated `defined for`
# rule, then cycle-5 item 13's gated `defined (qualifier)`/`defined to
# [verb]` rule. Order and narrowness both matter for dispatch safety under
# either plausible "first-positive-wins" reading -- see the D-DF and
# cycle-5 item-13 RED test files' module docstrings for the full rationale.
register_heading_rule(
    HeadingRule(jurisdiction_codes=("US-*",), matches=matches_heading_variant_unconditional)
)
register_heading_rule(
    HeadingRule(
        jurisdiction_codes=("US-*",),
        matches=matches_defined_for_heading,
        body_confirms=defines_in_body,
    )
)
register_heading_rule(
    HeadingRule(
        jurisdiction_codes=("US-*",),
        matches=matches_defined_qualifier_heading,
        body_confirms=defines_qualifier_in_body,
    )
)
