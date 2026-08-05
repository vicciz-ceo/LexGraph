"""Rule: `EntrySplitterRule`s for two class-(d) structural sub-shapes of a
recognized הגדרות/הגדרה section body that baseline `extract._split_into_
blocks` cannot turn into ANY block at all (sprint 2026-08-04-defs-il,
Phase D / D-1b bundle, contract item 5's `test_class_d_prose_body_
definitions_section_yields_zero_today` / `test_class_d_minimal_single_
sentence_variant_is_captured` / `test_class_d_variant_double_colon_entry_
list_under_a_trigger_preamble_is_captured`).

## Root cause (re-confirmed live this session, matches the Planner's and
manager's own prior positive-control transcripts, log entries "Planner
D-1b" / "M20")

`HebrewProfile.extract_definitions_from_section` (profiles.py:210, FROZEN)
unions baseline's own `extract._split_into_blocks(text)` output with every
registered `EntrySplitterRule`'s blocks, then hands EVERY block (baseline
or rule-contributed) to baseline's OWN, unchanged `extract._parse_block`.
`_split_into_blocks` requires a line matching `^\\s*:-` to start ANY
block -- a body with no such line produces ZERO blocks, so the per-block
parse loop never even runs, regardless of how well-formed the body's own
prose is. This is a missing-BLOCK gap, not a clause-parsing gap: baseline
`_parse_block` already correctly extracts a `"term" - definition` sentence
once it is HANDED one -- proven live, unaided, by simply registering a
probe splitter that returns the whole body as one block (see the sprint
log's Job-1 transcript for both this shape and the `::-` shape below).

## Two independent sub-shapes, two independent rules

1. `_split_marker_less_prose` -- a body with NO `:-`-prefixed line
   anywhere (the single-sentence minimal variant) -- returns the WHOLE
   body as one block, letting baseline's own `_parse_block` read its
   first line. Only the FIRST line's `"term" - definition` sentence is
   ever extracted this way (`_parse_block` never re-scans later lines for
   a second entry) -- deliberately narrow, matching exactly what this
   bundle's two RED tests need and what the Planner's own positive
   control proved, not a general multi-entry marker-less-prose parser
   (that is a materially bigger, unauthorized design -- ruling M7's own
   two-pass numbered-continuation guard is future work for a different,
   larger effort, not this bundle's job).
2. `_split_double_colon_dash_entries` -- a body whose real entries are
   marked `::-` (double colon-dash) rather than the single `:-` baseline
   requires (e.g. a `(א) בתקנות אלה -` preamble line followed by `::-`-
   marked entries) -- mirrors baseline's own `_split_into_blocks`
   algorithm exactly, keyed on `::-` instead of `:-`, EXCEPT continuation
   collection stops (flushing the current block, not accumulating) the
   moment a line drops back to a shallower marker depth (anything not
   itself `::`-prefixed) -- deliberately stricter than baseline's own
   "accumulate everything until the next top-level marker" rule, so a
   trailing single-colon closing sentence (e.g. this fixture's own
   `: (ב) בתקנות אלה תהא ...`) is never silently appended to the last
   nested entry's own definition text.

Both rules are pure block-producers -- neither parses a term or builds a
`DefinitionCandidate` itself; baseline's own frozen `_parse_block` (via
`HebrewProfile.extract_definitions_from_section`'s union loop) does that
work, unaided, for every block either rule contributes. This is why the
multi-quote entry inside sub-shape 2's own real fixture (`"מס שבח מקרקעין"
ו"זכות במקרקעין" - ...`) is captured correctly with no extra code here --
baseline's existing `_parse_terms_and_qualifier` already handles N>=1
quoted terms per block, unaided.

## Regression scan (this session, read-only, before committing)

Scanned every `*.wiki` fixture under `backend/tests/fixtures/wiki_laws/`
for a definitions-heading (`sections.is_definitions_heading`) article
whose body either has zero `:-`-prefixed lines or has any `::-`-prefixed
line: exactly 3 hits, all 3 this bundle's own target fixtures (the two
single-sentence ones plus the `::-` one) -- zero other fixture is
affected by either rule. (No IL `HeadingRule`/`BodyPreambleRule` is
registered anywhere in this codebase today, confirmed by grep, so
`is_definitions_section` reduces exactly to `sections.
is_definitions_heading`'s own baseline regex; every OTHER
definitions-heading fixture in the whole suite already has a `:-` line
and no `::-` line, so neither new rule changes its block set at all.)
"""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule

_TOP_LEVEL_ENTRY_RE = re.compile(r"^\s*:-\s?")
_DOUBLE_COLON_DASH_RE = re.compile(r"^\s*::-\s?")
_DOUBLE_COLON_RE = re.compile(r"^\s*::")


def _split_marker_less_prose(text: str) -> list[str]:
    """Whole-body-as-one-block fallback, ONLY when no line anywhere in
    `text` starts a baseline `:-` block -- see module docstring sub-shape
    1. Returns `[]` (no extra block) whenever baseline would already have
    something to work with on its own, so this can never duplicate or
    interfere with an already-working `:-` section."""
    if any(_TOP_LEVEL_ENTRY_RE.match(line) for line in text.split("\n")):
        return []
    if not text.strip():
        return []
    return [text]


def _split_double_colon_dash_entries(text: str) -> list[str]:
    """Mirrors baseline `extract._split_into_blocks`, keyed on `::-`
    instead of `:-` -- see module docstring sub-shape 2 for why
    continuation collection stops at the first non-`::`-prefixed line
    instead of running to the next top-level marker."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if _DOUBLE_COLON_DASH_RE.match(line):
            if current is not None:
                blocks.append(current)
            current = [_DOUBLE_COLON_DASH_RE.sub("", line, count=1)]
        elif _DOUBLE_COLON_RE.match(line) and current is not None:
            current.append(line)
        else:
            if current is not None:
                blocks.append(current)
            current = None
    if current is not None:
        blocks.append(current)
    return ["\n".join(b) for b in blocks]


register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("IL",), split=_split_marker_less_prose)
)
register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("IL",), split=_split_double_colon_dash_entries)
)
