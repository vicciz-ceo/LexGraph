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

Sprint 2026-08-04-defs-il, Phase D, D-1a bundle -- Class A fix (`parse_
entry`, below): `ENTRY_TERM_DASH_RE` (kept for backward-compatible
external reference only, no longer consulted by either sibling rule)
matched a SINGLE quoted term only. When a real entry names >=2 terms
sharing one definition (`"t1", "t2" - def` / `"t1" ו"t2" - def` / a mixed
`"t1", "t2", ו"t3" - def`), the old regex's `term_match` failed silently
and the WHOLE entry was dropped, not partially -- root cause confirmed
live before this fix (see the sprint log's D-1a Developer entry): 392
lines / 963 terms / 207 files measured missing (Planner's own conservative
re-derivation; QA cycle 3 measured 479/1,173/239 with looser gap-
validation -- same real class, not reconciled to the exact number).
`parse_entry` generalizes to N>=1 leading quoted terms, each non-first one
introduced by a real separator (a comma and/or the Hebrew conjunction ו
prefixed directly to its own opening quote -- the two real corpus
sub-shapes, plus their natural combination: comma-only 83, vav-only 203,
mixed 72). Both list-shape rules (`il_colon_dash_nested_list_scope_
triggers.py` / `il_single_colon_list_scope_triggers.py`) now call this ONE
shared parser -- previously the `::-` rule kept its OWN private
single-term-only regex copy (`_TERM_DASH_RE`) despite its own docstring
already claiming to share `il_list_shape_scope.py`'s table; this fix also
closes that doc/code mismatch, not just the multi-term bug.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_trigger_grammar import law_wide_preamble_phrases
from app.definition_links.rules.registry import RuleContext

PREAMBLE_RE = re.compile(r"\S.*\s-\s*$")
# Kept for backward-compatible external reference (the D-1a RED tests'
# own docstrings cite this name as the root cause under test) -- no
# longer consulted by either sibling rule, which both now call
# `parse_entry` below instead.
ENTRY_TERM_DASH_RE = re.compile(r'^"([^"]+)"\s*-\s*(.*)$')

_QUOTE_RE = re.compile(r'"([^"]+)"')
# A non-first term's own separator, one of:
#   - a comma (optionally spaced), optionally followed by a connector
#     word directly prefixed to the quote: bare vav (`ו"..."`), hyphenated
#     vav (`ו-"..."`), or the standalone word `או` ("or", itself requiring
#     its own trailing whitespace before the quote since -- unlike vav --
#     it is never glued directly to it);
#   - OR the same connector-word set introduced by bare whitespace with no
#     comma at all (`"t1" ו"t2"` / `"t1" ו-"t2"` / `"t1" או "t2"`).
# Sprint 2026-08-04-defs-il, Phase D, or/vav-hyphen separator bundle
# (log `## M25` + the separator Planner's RED tests): extends D-1a's
# original comma/vav-direct alternation to also recognize `או` and the
# hyphenated `ו-` conjunction -- both real, measured (20 lines / 13 files),
# live-confirmed corpus shapes the original alternation silently dropped
# as a discarded "qualifier". Widens ONLY this alternation; does not touch
# `_find_dash_marker` or the dash-then-header boundary (the Planner's own
# precision analysis of 13 real post-dash-quote files depends on that
# boundary being untouched -- see this module's own docstring and the
# sprint log). Requires a REAL separator character/word either way, so two
# quoted spans can never be silently treated as adjacent terms with zero
# gap between them (not a real corpus shape).
_TERM_SEP_RE = re.compile(r'(?:\s*,\s*(?:או\s+|ו-?)?|\s+(?:או\s+|ו-?))"([^"]+)"')


def _find_dash_marker(text: str) -> int:
    """First standalone `-` (preceded/followed by whitespace or
    start/end) OUTSIDE any quoted span in `text`, or -1 if none exists --
    mirrors the FROZEN `extract._find_split_dash`'s own algorithm (a
    whole-line, quote-aware scan, not an immediately-after-the-last-quote
    match), so a Class-C/list-shape entry tolerates the SAME qualifier-
    between-term-and-dash shape (e.g. `"term" (English gloss) -
    definition`) the already-shipped definitions-SECTION path already
    handles via `extract._parse_terms_and_qualifier` -- parity, not new
    risk: this is porting an already-precision-proven algorithm, not
    inventing one."""
    in_quote = False
    n = len(text)
    for i, ch in enumerate(text):
        if ch == '"':
            in_quote = not in_quote
            continue
        if not in_quote and ch == "-":
            before_ok = i == 0 or text[i - 1].isspace()
            after_ok = i == n - 1 or text[i + 1].isspace()
            if before_ok and after_ok:
                return i
    return -1


def parse_entry(entry_text: str) -> tuple[tuple[str, ...], str] | None:
    """Parse ONE list-shape entry's own text (everything after its `:-`/
    `::-` marker, already stripped) into `(terms, definition_text)`.

    Finds the entry's own split marker (the first standalone `-` outside
    any quote) FIRST, then reads every leading quoted term from the
    header text before it -- any non-quote text between the last term and
    the dash (a qualifier, e.g. an English gloss in parens) is tolerated
    and discarded, not required to be empty. Returns `None` when no such
    dash exists at all (e.g. the entry uses a different defining-verb
    grammar with no dash, like `"X" פירושו ...`) or when the header does
    not start with a quoted term -- the SAME conservative failure mode
    `ENTRY_TERM_DASH_RE.match` already had for any non-matching line,
    never a wrong split.
    """
    dash_idx = _find_dash_marker(entry_text)
    if dash_idx == -1:
        return None
    header = entry_text[:dash_idx].rstrip()
    definition_text = entry_text[dash_idx + 1 :].strip()

    match = _QUOTE_RE.match(header)
    if match is None:
        return None
    terms = [match.group(1).strip()]
    pos = match.end()
    while True:
        sep_match = _TERM_SEP_RE.match(header, pos)
        if sep_match is None:
            break
        terms.append(sep_match.group(1).strip())
        pos = sep_match.end()
    return tuple(terms), definition_text

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
    terms: str | tuple[str, ...], definition_text: str, scope: str, ctx: RuleContext
) -> DefinitionCandidate:
    """`terms` accepts either a single bare string (every pre-D-1a call
    site) or a tuple of >=1 terms (D-1a's Class-A multi-term fix) -- a
    bare string is wrapped to a 1-tuple, so no existing caller needed to
    change its own call shape."""
    terms_tuple = (terms,) if isinstance(terms, str) else tuple(terms)
    if scope == "chapter":
        return DefinitionCandidate(
            terms=terms_tuple,
            definition_text=definition_text,
            scope=scope,
            source_chapter=ctx.chapter,
        )
    if scope in ("local", "law-wide"):
        return DefinitionCandidate(terms=terms_tuple, definition_text=definition_text, scope=scope)
    return DefinitionCandidate(
        terms=terms_tuple, definition_text=definition_text, scope=scope, scope_value=None
    )
