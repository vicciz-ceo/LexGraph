"""Rule: US-ME's dominant family-3 shape (sprint 2026-08-04-defs-us-markers,
phase-2 Developer B; see the sprint log `## PB1`, Planner B, item B1/B4).
ME's convention is a bare digit-dot marker (`1.` `2.` ...) opening each
entry with a `TermName.` mini-heading, immediately followed by the SAME
term re-quoted and a `means`/`shall mean`/`has the meaning` idiom
(`1. Alternative working hours employment. "Alternative working hours
employment" means ...`). This shape is already reachable by the shared
quote-anchored engine (`us_markers_boundary.extract_quote_anchored_
entries`, which anchors on the QUOTED term + idiom, ignoring the mini-
heading entirely) -- ME's real, NEW defect (confirmed live by Planner B
against `STATE_ME_T5_P2_C69_S902`, not asserted from prose) is that EVERY
entry carries a trailing bracketed legislative-history citation
(`[PL 1981, c. 270, §4 (NEW).]`) appended directly after its own defining
sentence, on the SAME line -- a shape `us_markers_boundary.
TRAILING_STOP_RE` has no entry for (it recognizes FED's "Editorial Notes"
family and a handful of other literal phrases, never a `[PL ...]`
citation), so the unmodified engine leaves it attached to the captured
`definition_text`.

This module therefore does not reimplement entry-splitting at all: it
reuses the shared engine's own `extract_quote_anchored_entries` UNMODIFIED
(imported, not edited -- `us_markers_boundary.py` is core's file this
cycle) and applies one ME-scoped post-processing pass that strips a
trailing `[PL ...]` citation (and any whitespace before it) off each
entry's `definition_text` before re-wrapping the result via the shared
`entries_to_quoted_blocks` helper. Scoped to `"US-ME"` only -- a `[PL ...]`
citation is ME's own legislative-drafting convention, not a general
US-wide pattern."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    entries_to_quoted_blocks,
    extract_quote_anchored_entries,
)

# A trailing `[PL <year>, c. <chapter>, ...]`-shaped legislative-history
# citation -- anchored at the END of the (already-stripped) definition
# text, optionally preceded by whitespace. `[^\]]*` stays within the
# brackets (never crosses into unrelated content) and `\Z` (not `$`)
# ensures only a citation that is genuinely the text's own last token is
# stripped, never one that merely happens to appear mid-sentence.
_PL_CITATION_TAIL_RE = re.compile(r"\s*\[PL[^\]]*\]\s*\Z")


def _split(text: str) -> list[str]:
    cleaned: list[tuple[str, str]] = []
    for term, definition_text in extract_quote_anchored_entries(text):
        stripped = _PL_CITATION_TAIL_RE.sub("", definition_text).strip()
        if stripped:
            cleaned.append((term, stripped))
    return entries_to_quoted_blocks(cleaned)


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-ME",), split=_split))
