"""Position/token-shape family-4 rules: R-SEC, R-MID, R-VERB-bare, R-TRUNC,
R-MISSPELL, plus cycle 5 item 12's pointer-table heading shape (D-MT-E1).
See the package `__init__.py` module docstring for the full design history
and the cycle-5 RED test module docstrings for per-item evidence.
"""

from __future__ import annotations

import re

from app.definition_links.rules.us_heading_variants._shared import (
    _MISSPELL_RE,
    _SEC_LABEL_RE,
    _TRUNC_PREFIXES,
    first_or_last_word_definitions,
    preposition_governs,
    strip_leading_noise,
    tail_tokens,
    tail_tokens_core,
)


def rule_sec(heading: str) -> bool:
    """R-SEC: strip an abbreviated `Sec.`/`Secs.`/`Art.`/`Article`
    section-label prefix, then apply baseline's own first-word/last-word
    decision to whatever remains."""
    rest = strip_leading_noise(heading)
    m = _SEC_LABEL_RE.match(rest)
    if not m:
        return False
    return first_or_last_word_definitions(rest[m.end() :].lstrip())


def rule_mid(heading: str) -> bool:
    """R-MID: an exact `Definition`/`Definitions` tail token, guarded by
    `preposition_governs`, at any position except the very first or very
    last per OUR OWN tokenizer. Falls back (cycle 2, BUG4/BUG5) to a
    first/last-word recheck with the same widened tokenizer."""
    tokens = tail_tokens_core(heading)
    for i in range(1, len(tokens) - 1):
        word, _dash = tokens[i]
        if word.lower() in ("definition", "definitions") and not preposition_governs(tokens, i):
            return True
    return first_or_last_word_definitions(strip_leading_noise(heading))


def rule_verb_bare(heading: str) -> bool:
    """R-VERB-bare: the last tail token is exactly `defined`."""
    tokens = tail_tokens(heading)
    return bool(tokens) and tokens[-1].lower() == "defined"


def rule_trunc(heading: str) -> bool:
    """R-TRUNC: the last tail token is a verified non-English strict
    prefix of "definitions" (source-data truncation, not a drafting
    convention)."""
    tokens = tail_tokens(heading)
    return bool(tokens) and tokens[-1].lower() in _TRUNC_PREFIXES


def rule_misspell(heading: str) -> bool:
    """R-MISSPELL: the last tail token is a known scrape-corpus
    misspelling of "definitions"."""
    tokens = tail_tokens(heading)
    return bool(tokens) and bool(_MISSPELL_RE.match(tokens[-1]))


# --- Item 12, D-MT-E1: pointer-table headings ------------------------------
#
# "Other defined terms" / "Index of definitions [in code/act/chapter/
# title]" -- a real, repeated drafting convention whose body is a
# cross-reference TABLE mapping each term to the section that actually
# defines it, not a definitions section proper. Neither R-MID (the
# preposition guard correctly suppresses "...Index of definitions in
# code") nor R-VERB-bare/extended (last tail token is "terms", not
# "defined") ever fire on either sub-family -- a genuinely new heading
# shape. UNCONDITIONAL: manager + Planner hand-verified all 9/9 rows as
# genuine cross-reference tables, none carrying D-DF's/item 13's
# precision-risk shape. Matched via `re.search` so a leading section-
# number label ("5-1-303.", "Sec. 36a-3.", "SECTION 37-3-103.") never
# blocks the match.
_POINTER_TABLE_RE = re.compile(
    r"\bother\s+defined\s+terms\b"
    r"|\bindex\s+of\s+definitions\b(?:\s+in\s+(?:code|act|chapter|title)\b)?",
    re.IGNORECASE,
)


def matches_pointer_table_heading(heading: str) -> bool:
    return bool(_POINTER_TABLE_RE.search(heading))
