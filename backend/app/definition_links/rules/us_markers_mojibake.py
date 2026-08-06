"""Rule: mojibake curly-quote repair for RI and AK (family 3 -- ruling
U-R8). `USProfile.normalize_for_parsing` (shared, `us_profile.py`) does
NOT touch these byte sequences (it only collapses the real-Unicode `“`/
`”` curly-quote CODEPOINTS, deliberately, per its own docstring) and
carries no registry seam a family panel can hook into for normalization --
confirmed live this sprint (no `NormalizeRule`/`register_normalize_rule`
kind exists in `rules/registry.py`). Ruling U-R8's directive: repair must
happen INSIDE this family's own rule callable.

**Two DIFFERENT byte sequences, verified live against the real vendored
rows (not the recon dossier's `\\x80\\x9c` description, which the sprint
log records as wrong for AK specifically):**

- RI (`STATE_RI_T35_C35-13_S35-13-2`): opening `\\x80\\x9c`, closing
  `\\x80\\x9d` -- 2-byte sequences.
- AK (`STATE_AK_T44_C44.42_S44.42.900`): opening `\\x93`, closing `\\x94`
  -- 1-byte cp1252 control-range sequences, ~32K occurrences corpus-wide
  per the program manager's relayed figure.

Repairing to a plain ASCII `"` BEFORE running the shared quote-anchored
engine (`us_markers_boundary.extract_quote_anchored_entries`) means the
extracted TERM string itself is clean ASCII -- this is what lets a
mojibake-body definition actually LINK to a plain-text mention elsewhere
in the same document (`matcher.find_term_uses` scans EVERY article's own
body, including ones with no mojibake at all, e.g.
`STATE_AK_T44_C44.42_S44.42.220`'s "...as requested by the commissioner
...") -- extraction without linking is not "captured" per ruling U-R1.
The MENTION side needs no repair of its own; only the defining term does."""

from __future__ import annotations

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    entries_to_quoted_blocks,
    extract_quote_anchored_entries,
)


def _repair_ri(text: str) -> str:
    return text.replace("\x80\x9c", '"').replace("\x80\x9d", '"')


def _repair_ak(text: str) -> str:
    return text.replace("\x93", '"').replace("\x94", '"')


def _split_ri(text: str) -> list[str]:
    return entries_to_quoted_blocks(extract_quote_anchored_entries(_repair_ri(text)))


def _split_ak(text: str) -> list[str]:
    return entries_to_quoted_blocks(extract_quote_anchored_entries(_repair_ak(text)))


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-RI",), split=_split_ri))
register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-AK",), split=_split_ak))
