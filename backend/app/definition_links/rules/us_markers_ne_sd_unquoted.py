"""Exact source-bound unquoted definition entries for Nebraska and South Dakota."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule


_NE_C43_RE = re.compile(
    r"^For purposes of sections 43-3328 to 43-3339\s*,\s*the following definitions apply:",
    re.IGNORECASE,
)
_NE_C43_TERMS = (
    "Account",
    "Authorized attorney",
    "Child support",
    "Department",
    "Financial institution",
    "Match",
    "Medical support",
    "Obligor",
    "Payor",
    "Spousal support",
    "Support",
    "Support order",
)
_NE_C44_RE = re.compile(r"^For purposes of the Children of Nebraska Hearing Aid Act:\s*\n\s*\(1\)")
_NE_C44_TERMS = ("Health insurance plan", "Hearing aid", "Hearing impairment", "Insured child")
_SD_TERM_RE = re.compile(
    r"^For the purposes of this chapter, the term,\s+(?P<term>loan processor or underwriter),\s+(?P<verb>means)\s+",
    re.IGNORECASE,
)


def _numbered_entries(text: str, *, guard: re.Pattern[str], terms: tuple[str, ...]) -> list[str]:
    """Emit only this reviewed statute shape, bounded by its literal entries."""
    if guard.match(text) is None:
        return []

    starts: list[tuple[str, int]] = []
    for number, term in enumerate(terms, start=1):
        marker = f"({number}) {term} "
        start = text.find(marker)
        if start < 0:
            return []
        starts.append((term, start + len(marker)))

    entries: list[str] = []
    for index, (term, definition_start) in enumerate(starts):
        if term == "Support":
            verb_start = text.find("means", definition_start)
            if verb_start < 0:
                return []
            definition_start = verb_start
        definition_end = starts[index + 1][1] - len(f"({index + 2}) {terms[index + 1]} ") if index + 1 < len(starts) else text.find("\n\nLaws", definition_start)
        if definition_end <= definition_start:
            return []
        entries.append(f'"{term}" {text[definition_start:definition_end].strip()}')
    return entries


def _split_ne(text: str) -> list[str]:
    return _numbered_entries(text, guard=_NE_C43_RE, terms=_NE_C43_TERMS) or _numbered_entries(
        text, guard=_NE_C44_RE, terms=_NE_C44_TERMS
    )


def _split_sd(text: str) -> list[str]:
    match = _SD_TERM_RE.match(text)
    if match is None:
        return []
    end = text.find("\n\nNo individual engaging solely", match.end())
    if end < 0:
        return []
    return [f'"{match.group("term")}" {text[match.start("verb") : end].strip()}']


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-NE",), split=_split_ne))
register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-SD",), split=_split_sd))
