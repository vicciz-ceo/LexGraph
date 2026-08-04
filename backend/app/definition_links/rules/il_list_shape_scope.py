"""Shared list-shape ("preamble line ending in a bare `-`, followed by N
`:-`/`::-`-marked entry lines") scope-inference vocabulary and candidate-
building logic (sprint 2026-08-04-defs-il, Phase C, item C4 + ruling M16
-- program efficiency directive): used by BOTH `il_colon_dash_nested_
list_scope_triggers.py` (double-colon `::-` marker) and
`il_single_colon_list_scope_triggers.py` (single-colon `:-` marker) so
the trigger->scope vocabulary table is defined and measured ONCE, not
duplicated per marker width.

Ruling M16 (law-wide scope under-claim): a preamble that explicitly names
the WHOLE instrument (`בחוק זה -`, `בתקנות אלה -`, ...) must classify
`"law-wide"`, not the narrowest-safe `"local"` default -- parity with a
RECOGNIZED הגדרות section, which already defaults to `"law-wide"` via
`HebrewProfile.determine_scope`. See `il_trigger_grammar.LAW_WIDE_WORDS`'s
docstring for the full measured INCLUDE/EXCLUDE vocabulary and the
sprint log's Phase C round 2 entry for the per-phrase verification
transcript. The unrecognized-preamble default stays `"local"` (the
narrowest, safest choice, unchanged).
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_trigger_grammar import law_wide_preamble_phrases
from app.definition_links.rules.registry import RuleContext

PREAMBLE_RE = re.compile(r"\S.*\s-\s*$")
ENTRY_TERM_DASH_RE = re.compile(r'^"([^"]+)"\s*-\s*(.*)$')

# Longest/most-specific phrase first, so a phrase that CONTAINS a
# shorter sibling as a substring is never shadowed by checking the
# shorter one first (established discipline, unchanged from the
# original `::-`-only table this was extracted from).
_LOCAL_AND_BELOW_WORDS: tuple[tuple[str, str], ...] = (
    ("בסעיף קטן זה", "subsection"),
    ("בתקנת משנה זו", "subsection"),
    ("לענין תקנת משנה זו", "subsection"),
    ("לעניין תקנת משנה זו", "subsection"),
    ("בפסקת משנה זו", "subsection"),
    ("בפרק זה", "chapter"),
    ("בסימן זה", "siman"),
    ("בחלק זה", "chelek"),
    ("בתקנה זו", "local"),
    ("לענין תקנה זו", "local"),
    ("לעניין תקנה זו", "local"),
    ("בסעיף זה", "local"),
    ("לענין זה", "local"),
    ("לעניין זה", "local"),
    ("בפסקה זו", "paragraph"),
    ("לענין פסקה זו", "paragraph"),
    ("לעניין פסקה זו", "paragraph"),
    ("בפרט זה", "item"),
)

# M16: instrument-naming phrases classify "law-wide" -- measured,
# hand-verified vocabulary shared with the quote-first M17 rule (see
# `il_trigger_grammar.LAW_WIDE_WORDS`).
_LAW_WIDE_ENTRIES: tuple[tuple[str, str], ...] = tuple(
    (phrase, "law-wide") for phrase in law_wide_preamble_phrases()
)

SCOPE_TRIGGER_WORDS: tuple[tuple[str, str], ...] = _LOCAL_AND_BELOW_WORDS + _LAW_WIDE_ENTRIES


def infer_scope(preamble_line: str) -> str:
    for phrase, scope in SCOPE_TRIGGER_WORDS:
        if phrase in preamble_line:
            return scope
    return "local"


def make_candidate(
    term: str, definition_text: str, scope: str, ctx: RuleContext
) -> DefinitionCandidate:
    if scope == "chapter":
        return DefinitionCandidate(
            terms=(term,),
            definition_text=definition_text,
            scope=scope,
            source_chapter=ctx.chapter,
        )
    if scope in ("local", "law-wide"):
        return DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
    return DefinitionCandidate(
        terms=(term,), definition_text=definition_text, scope=scope, scope_value=None
    )
