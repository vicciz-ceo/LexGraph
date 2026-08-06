"""Rule: three distinct UNQUOTED defined-term conventions (family 3, no
quote character anywhere in the body, so neither the baseline `(N)`-block
splitter nor `_extract_inline_quoted_definitions` can see a term boundary
at all) -- confirmed live, sprint 2026-08-04-defs-us-markers, planner
passes 2-3:

- **AL** -- `(N) ALLCAPS TERM. Definition sentence.` (e.g.
  `STATE_AL_T1_C19_S22-19-141`'s `(1) ORGAN. Organs, tissues, ...`). AL's
  DOMINANT convention: 1,603/1,653 (97.0%) of AL's real Definitions-headed
  sections are zero-candidate, full corpus.
- **NC** -- `(N) TermName.--Definition text.` (ordinary-cased, not
  all-caps -- `STATE_NC_C41_S41-70`'s `(1) Conveyance.--A transfer of
  title ...`; sometimes a stray space before `.--`, e.g. `Board .--`, per
  the sprint log). Full-corpus NC: 522/1,007 (51.8%) zero-candidate.
- **DC** -- the defined term is the grammatical SUBJECT of a
  `"A <term>[, ...,] means ..."` / `"An <term> means ..."` sentence, no
  marker at all (`STATE_DC_T28_C25_S28-2501`'s `"A bond, when required by
  or referred to in this Code, means ..."` / `"An undertaking means
  ..."`).

Each is jurisdiction-scoped to its own single state (never `"US-*"`) --
these are real, but narrow, per-state drafting conventions; a false match
on some OTHER state's ordinary "A/An ..." sentence structure is exactly
the corpus-wide false-positive risk narrow scoping avoids.

Corpus self-verification found the same "genuinely-last-entry-has-no-
closing-boundary" defect class here as in `us_markers_boundary.py` (e.g.
a real AL "GROSS RECEIPTS" entry swallowing thousands of unrelated
trailing chars) -- reuses that module's own `MAX_CLEAN_DEFINITION_LENGTH`
defensive ceiling rather than inventing a second threshold."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    MAX_CLEAN_DEFINITION_LENGTH,
    TRAILING_STOP_RE,
)

_AL_ENTRY_RE = re.compile(r"\(\d+\)\s+([A-Z][A-Z \-]{1,60})\.\s+(?=[A-Z])")
_NC_ENTRY_RE = re.compile(r"\(\d+\)\s+([A-Z][a-zA-Z \-']{1,80}?)\s*\.--\s*")
_DC_ENTRY_RE = re.compile(
    r"(?:^|\n)(?:A|An)\s+([a-z][a-zA-Z\- ]*?)(?:,\s*[^.\n]*?)?\s+means\s+", re.MULTILINE
)


def _extract_marker_anchored(text: str, entry_re: re.Pattern[str]) -> list[tuple[str, str]]:
    stop = TRAILING_STOP_RE.search(text)
    limit = stop.start() if stop else len(text)
    matches = list(entry_re.finditer(text, 0, limit))
    entries: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else limit
        term = m.group(1).strip()
        definition_text = text[m.end() : end].strip()
        if term and definition_text and len(definition_text) <= MAX_CLEAN_DEFINITION_LENGTH:
            entries.append((term, definition_text))
    return entries


def _quoted_blocks(entries: list[tuple[str, str]]) -> list[str]:
    return [f'"{term}" {definition_text}' for term, definition_text in entries]


def _split_al(text: str) -> list[str]:
    return _quoted_blocks(_extract_marker_anchored(text, _AL_ENTRY_RE))


def _split_nc(text: str) -> list[str]:
    return _quoted_blocks(_extract_marker_anchored(text, _NC_ENTRY_RE))


def _split_dc(text: str) -> list[str]:
    return _quoted_blocks(_extract_marker_anchored(text, _DC_ENTRY_RE))


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-AL",), split=_split_al))
register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-NC",), split=_split_nc))
register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-DC",), split=_split_dc))
