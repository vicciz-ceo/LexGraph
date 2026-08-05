"""Rule: US-OH's dominant family-3 shape (sprint 2026-08-04-defs-us-markers,
phase-2 Developer B; see the sprint log `## PB1`, Planner B, item B1/B4).
OH's convention is `(A) As used in ...: (1) "term" means ...` -- a
lettered top-level grouping marker introducing a digit-paren entry list,
both shapes already structurally supported by the shared quote-anchored
engine's existing hard-stops (`us_markers_boundary.extract_quote_
anchored_entries`, whose `_DIGIT_MARKER_RE` guard already bounds the
transition from one `(N)` entry to the next cleanly).

OH's real, NEW defect (confirmed live by Planner B against
`STATE_OH_T21_C2108_S2108.61`, not asserted from prose): OH commonly
appends ONE trailing lettered clause AFTER the digit-paren definitions
list that is NOT itself a defined term (`(B) The department of health
shall encourage ...`), plus a `Last updated <date> at <time>`
scrape-artifact stamp at the very end. Neither is caught by the shared
engine's own `_LETTER_MARKER_RE` hard-stop, which DELIBERATELY only fires
when a quote follows within a short lookahead (protecting a genuinely
nested non-defining sub-clause like WA's own `"Threat"`/`"(a) To cause
bodily injury"` precedent, per that module's own docstring) -- `(B) The
department...` has no quote anywhere near it, so the LAST digit-paren
entry's own definition swallows straight through `(B)`'s entire clause
plus the trailing timestamp (confirmed live: "Umbilical cord blood"'s raw
captured definition_text runs 415 chars instead of the genuine ~95-char
single-sentence definition).

This module therefore does not reimplement entry-splitting at all: it
reuses the shared engine's own `extract_quote_anchored_entries` UNMODIFIED
(imported, not edited -- `us_markers_boundary.py` is core's file this
cycle) and applies one OH-scoped post-processing pass that truncates each
entry's `definition_text` at the first SENTENCE-BOUNDARY lettered clause
(a period immediately followed by a `(LETTER) ` marker and a capitalized
word -- i.e. a genuinely NEW top-level clause, not a mid-sentence nested
item) and strips a trailing `Last updated ...` scrape stamp regardless of
whether a lettered clause preceded it, before re-wrapping the result via
the shared `entries_to_quoted_blocks` helper. Deliberately narrower than
the shared engine's own letter-marker guard would need to be for a
general fix (this rule has no quote-nearby exception at all), so it stays
`"US-OH"`-scoped only -- never `"US-*"` -- exactly the risk `us_markers_
boundary.py`'s own docstring names for why that guard requires a nearby
quote in the first place."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    entries_to_quoted_blocks,
    extract_quote_anchored_entries,
)

# A sentence-ending period followed by a top-level `(LETTER)` marker and
# the start of a new capitalized clause -- OH's own "one trailing
# non-defining lettered clause" shape. The period itself is kept (index of
# the match start IS the period), only what follows is dropped.
_TRAILING_LETTER_CLAUSE_RE = re.compile(r"\.\s+\([A-Z]\)\s+(?=[A-Z])")

# A trailing `Last updated <date> at <time>` scrape-artifact stamp,
# applied independently of the lettered-clause guard above so a row
# carrying the stamp WITHOUT a preceding `(B)`-style clause is still
# cleaned.
_LAST_UPDATED_TAIL_RE = re.compile(r"\s*Last updated\b.*\Z", re.IGNORECASE | re.DOTALL)


def _split(text: str) -> list[str]:
    cleaned: list[tuple[str, str]] = []
    for term, definition_text in extract_quote_anchored_entries(text):
        clause_m = _TRAILING_LETTER_CLAUSE_RE.search(definition_text)
        if clause_m is not None:
            definition_text = definition_text[: clause_m.start() + 1].rstrip()
        definition_text = _LAST_UPDATED_TAIL_RE.sub("", definition_text).strip()
        if definition_text:
            cleaned.append((term, definition_text))
    return entries_to_quoted_blocks(cleaned)


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-OH",), split=_split))
