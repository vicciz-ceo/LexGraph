"""Rule: the "well-formed quoted-term" family-3 shape -- a real Definitions-
headed US statute section whose body is a run of `"Term" means ...`
sentences with NO `(N)`-paragraph markers before each quote (VA/WA/FED), or
with markers that `USProfile`'s own `_split_into_numbered_blocks` cannot
anchor on because they sit mid-line rather than at the start of a line
(WA/UT/SC), a bare paren marker whose OWN entry the baseline splitter DOES
already reach cleanly (TX), or a bare digit-DOT marker (no parens) baseline
never recognizes at all (AZ). Confirmed live (sprint 2026-08-04-defs-
us-markers, planner passes 1-2): today's real `run_definition_linking`
creates ZERO `Definition` rows for every VA/WA/FED/UT/AZ row named below
(VA 97.2%, WA 98.8%, FED 83.3% of real Definitions-headed sections yield
zero candidates, full-corpus, per the sprint log's `## P1`; AZ 99.0%); SC
IS reached by the current `_extract_inline_quoted_definitions` once its
gate is removed, but not CLEANLY (a literal next-entry marker/amendment-
annotation leak, per `## P2`).

Registers ONE `EntrySplitterRule`, scoped to the codes actually verified
against real vendored rows this sprint -- not a blanket `"US-*"` -- so no
untested jurisdiction's baseline-working extraction can be perturbed by
this module (see `us_markers_boundary.py`'s own docstring for the exact
defects each guard in the shared engine closes, evidenced against these
same rows).

Phase-2 (sprint 2026-08-04-defs-us-markers, Developer C): NJ, MI, ND, NY,
and OK added to the wave-1 seven (VA/WA/FED/UT/TX/SC/AZ). Same shared
engine, same guards -- these five jurisdictions' quote-anchored bodies were
measured to hit the identical family-3 shape, with zero-yield rates
NJ 99.7%, MI 38.8%, ND 99.7%, NY 79.9% (post-ingest text, ruling U-R11),
OK 94.4% before this change (manager sweep, `## M22`/phase-2 log)."""

from __future__ import annotations

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    entries_to_quoted_blocks,
    extract_quote_anchored_entries,
)

_JURISDICTIONS = (
    "US-VA",
    "US-WA",
    "US-FED",
    "US-UT",
    "US-TX",
    "US-SC",
    "US-AZ",
    "US-NJ",
    "US-MI",
    "US-ND",
    "US-NY",
    "US-OK",
)


def _split(text: str) -> list[str]:
    return entries_to_quoted_blocks(extract_quote_anchored_entries(text))


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=_JURISDICTIONS, split=_split))
