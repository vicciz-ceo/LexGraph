"""Rule: two US-NY-only "apposition" family-3 shapes -- family collapse of
family 3's NY-specific residual (sprint 2026-08-04-defs-us-markers,
phase-2 Developer B; see the sprint log `## PA1`, items A2/A4/A5). Both
shapes name the defined term immediately after a numbered/lettered marker,
end it with a bare PERIOD, and then state the definition as an ordinary
declarative sentence -- NO defining verb ("means"/"shall mean"/"has the
meaning") ever appears, so neither `us_markers_boundary.
extract_quote_anchored_entries` (its `_TIGHT_IDIOM_RE` gate requires one)
nor `us_markers_unquoted_terms.py` (AL/NC/DC-specific regexes, none
matching a QUOTED term + bare period) recognizes either shape. Scoped to
`"US-NY"` only -- both are real, narrow NY drafting conventions confirmed
against real vendored rows, not a general-purpose "quote+period" rule that
would risk matching unrelated punctuation elsewhere in the corpus.

- **Quote-period** (`_split_quote_period`, `STATE_NY_ADEA_A6_S80`):
  `N. "Term." Definition sentence.` -- a bare digit-dot marker directly
  followed by a QUOTED term ending in a period (either inside or outside
  the closing quote mark, both spellings occur in the real corpus per this
  panel's own Planner measurement), then a capitalized definition
  sentence. Architecturally the same family as AL's `(N) ALLCAPS TERM.
  Definition` / NC's `(N) TermName.--Definition` (`us_markers_unquoted_
  terms.py`) -- only the term is QUOTED here and the separator is a single
  period, not `.--`.
- **Lettered-paragraph** (`_split_lettered_paragraph`,
  `STATE_NY_ARPP_A8_S280-D`): a bare `(a)`/`(b)`/`(c)` letter-paren marker
  followed by an UNQUOTED Title-Case term ending in a period, then a
  capitalized definition sentence (`(a) Reverse mortgage loan. A reverse
  mortgage loan as defined in ...`). The Title-Case-first-letter
  requirement is what keeps this rule from also matching the SAME row's
  own unrelated `(a) monthly surplus income;` bullet list later in the
  body (real, confirmed live) -- that list's items all start lowercase, so
  they never match `[A-Z]` and are correctly left alone.
"""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    MAX_CLEAN_DEFINITION_LENGTH,
    TRAILING_STOP_RE,
)

# Marker + quoted term (optional period inside OR outside the closing
# quote) + mandatory trailing period + a capitalized definition sentence
# starting immediately after.
_QUOTE_PERIOD_ENTRY_RE = re.compile(
    r'(?:^|\n)[ \t]*\d{1,3}\.[ \t]+["“]([^"”]{1,80}?)\.?["”]\.?[ \t]+(?=[A-Z])'
)

# Marker + Title-Case term (no quote) + mandatory trailing period + a
# capitalized definition sentence. `[A-Z]` on the term's first letter is
# the load-bearing guard against this row's own unrelated lowercase bullet
# list (see module docstring).
_LETTERED_PARAGRAPH_ENTRY_RE = re.compile(
    r"(?:^|\n)[ \t]*\([a-z]\)[ \t]+([A-Z][A-Za-z '\-]{0,60}?)\.[ \t]+(?=[A-Z])"
)


def _entries_for(text: str, entry_re: re.Pattern[str]) -> list[tuple[str, str]]:
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


def _split_quote_period(text: str) -> list[str]:
    return [
        f'"{term}" {definition_text}'
        for term, definition_text in _entries_for(text, _QUOTE_PERIOD_ENTRY_RE)
    ]


def _split_lettered_paragraph(text: str) -> list[str]:
    return [
        f'"{term}" {definition_text}'
        for term, definition_text in _entries_for(text, _LETTERED_PARAGRAPH_ENTRY_RE)
    ]


def _split(text: str) -> list[str]:
    return _split_quote_period(text) + _split_lettered_paragraph(text)


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-NY",), split=_split))
