"""Rule: US-MN's dominant family-3 shape (sprint 2026-08-04-defs-us-markers,
phase-2 Developer B; see the sprint log `## PB1`, Planner B, item B1/B4).
MN's convention is a section-sign-prefixed, pilcrow-numbered mini-heading
naming the term (`§ Subd. N. TermName.` / `§ Subd. Na. TermName.`
for a lettered sub-subdivision), immediately followed by the SAME term
re-quoted and a `means` idiom (`§ Subd. 3a. Freeze branding. "Freeze
branding" means ...`). This shape is already reachable by the shared
quote-anchored engine (`us_markers_boundary.extract_quote_anchored_
entries`, which anchors on the QUOTED term + idiom, ignoring the mini-
heading entirely) -- MN's real, NEW defect (confirmed live by Planner B
against `STATE_MN_P17_43_C35_S35.821`, not asserted from prose) is that
its own `§ Subd. N. TermName.` marker is not a shape ANY of
`us_markers_boundary.py`'s existing hard-stop regexes recognize (only
`(N)`, `(letter)`, bare digit-dot, and bare single-letter-dot are
covered), so an entry whose own definition sentence ends right before the
NEXT entry's `§ Subd. N. TermName.` marker swallows that marker text
whole (confirmed live: "Freeze branding"'s raw captured definition_text
ends `'...hide of a live animal.\\n\\n§ Subd. 4. Mark.'` instead of
the genuine clean sentence).

This module therefore does not reimplement entry-splitting at all: it
reuses the shared engine's own `extract_quote_anchored_entries` UNMODIFIED
(imported, not edited -- `us_markers_boundary.py` is core's file this
cycle) and applies one MN-scoped post-processing pass that strips a
trailing `§ Subd. N[a]. TermName.` marker (and any whitespace before
it) off each entry's `definition_text` before re-wrapping the result via
the shared `entries_to_quoted_blocks` helper -- the SAME defect class as
`us_markers_boundary.py`'s own documented `_TRAILING_MARKER_CHAIN_RE`
guard (SC's `"(2)"` leak, AZ's `"13."` leak), for a marker shape neither
existing regex covers. Scoped to `"US-MN"` only -- the section-sign
pilcrow-numbered `Subd.` marker is MN's own drafting convention, not a
general US-wide pattern."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    entries_to_quoted_blocks,
    extract_quote_anchored_entries,
)

# A trailing `§ Subd. N[a]. TermName.` mini-heading -- anchored at the
# END of the (already-stripped) definition text, optionally preceded by
# whitespace. The Title-Case term span is non-greedy and itself terminated
# by its own period, so this only ever consumes the NEXT entry's own
# leaked marker, never rewinding into genuine prior sentence content.
_TRAILING_SUBD_MARKER_RE = re.compile(
    r"\s*§\s*Subd\.?\s*\d{1,3}[a-z]?\.\s*[A-Z][A-Za-z \-]{0,60}?\.\s*\Z"
)


def _split(text: str) -> list[str]:
    cleaned: list[tuple[str, str]] = []
    for term, definition_text in extract_quote_anchored_entries(text):
        stripped = _TRAILING_SUBD_MARKER_RE.sub("", definition_text).strip()
        if stripped:
            cleaned.append((term, stripped))
    return entries_to_quoted_blocks(cleaned)


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-MN",), split=_split))
