"""Exact US-FED splitter for the reviewed Good-Samaritan definitions section."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule


_PREFIX = "(a) Definitions\n\nIn this section:"
_TOP_LEVEL_B_RE = re.compile(r"(?m)^\(b\)\s+[A-Z]")
_ENTRY_RE = re.compile(
    r'(?ms)^\((?P<number>\d+)\)\s+(?P<label>[^\n]+)\n\n'
    r'The term "(?P<term>[^"]+?)"(?:,\s*[^\n]+?)?\s+means\s+'
)
_REVIEWED = (
    ("1", "Eligible", "eligible"),
    ("2", "Good Samaritan search-and-recovery mission", "good Samaritan search-and-recovery mission"),
    ("3", "Secretary", "Secretary"),
)


def _reviewed_entries(text: str) -> list[re.Match[str]]:
    if not text.startswith(_PREFIX):
        return []
    end = _TOP_LEVEL_B_RE.search(text)
    if end is None:
        return []
    matches = list(_ENTRY_RE.finditer(text, 0, end.start()))
    observed = tuple((match.group("number"), match.group("label"), match.group("term")) for match in matches)
    return matches if observed == _REVIEWED else []


def _split(text: str) -> list[str]:
    matches = _reviewed_entries(text)
    if not matches:
        return []
    top_level_b = _TOP_LEVEL_B_RE.search(text)
    assert top_level_b is not None
    entries: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else top_level_b.start()
        definition_text = text[match.end() : end].strip()
        if not definition_text:
            return []
        entries.append(f'"{match.group("term")}" {definition_text}')
    return entries


register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("US-FED",), split=_split, priority_before_single_baseline=True)
)
