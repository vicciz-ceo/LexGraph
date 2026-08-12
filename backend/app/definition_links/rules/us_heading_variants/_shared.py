"""Shared primitives for the `us_heading_variants` rule family (sprint
2026-08-04-defs-us-headings). Own copies of `us_profile.py`'s private
regexes/sets (ruling H-R4) -- section-label/number-token strip, trailing-
bracket strip, tail tokenizer, and preposition-exclusion guard -- plus the
mojibake normalization helper cycle 5 (items 11/14) added. See the package
`__init__.py` module docstring for the full per-rule/per-cycle design
history.

Every regex here is a fixed alternation of literal words/characters, or a
single quantifier over a fixed character class -- never nested inside an
alternation -- so each is unconditionally linear-time, matching
`us_profile.py`'s house style.
"""

from __future__ import annotations

import re

# --- Section-label / number-token primitives ------------------------------

_SEGMENT_RE = r"\d+[A-Za-z]*"
_NUMBER_CHAIN_RE = rf"{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?"

# ASCII-only (same rationale as `us_profile._LEADING_NOISE_RE`): the
# scrape-corpus's mojibake accented-Latin noise bytes ARE Unicode *letters*
# by category, so a Unicode-aware negated class would fail to skip them.
_LEADING_NOISE_RE = re.compile(r"^[^A-Za-z0-9]+")

# R-SEC's own label: the ABBREVIATED forms baseline's `_SECTION_LABEL_RE`
# does not accept (only the spelled-out word "Section").
_SEC_LABEL_RE = re.compile(rf"(?:Sec|Secs|Art|Article)\.?\s+{_NUMBER_CHAIN_RE}", re.IGNORECASE)

# Same rule baseline uses for "is 'Definition(s)' the whole word here".
_FIRST_WORD_DEFINITIONS_RE = re.compile(r"Definitions?\b", re.IGNORECASE)
_LAST_WORD_DEFINITIONS_RE = re.compile(r"^Definitions?$", re.IGNORECASE)

# Same trailing-annotation-and-period tolerance as
# `us_profile._TRAILING_BRACKET_RE`.
_TRAILING_BRACKET_RE = re.compile(r"\s*\[[^\]]*\]\.?\s*$")

# Same separator set as `us_profile._TAIL_TOKEN_SPLIT_RE`, PLUS (cycle 2,
# BUG1/BUG4/BUG5) an interior `.`, `/`, `(`, `)`.
_TAIL_SPLIT_CHARS = r"\s\-–—:;,./()"
_TAIL_TOKEN_SPLIT_RE = re.compile(rf"[{_TAIL_SPLIT_CHARS}]+")
_TAIL_TOKEN_CAPTURE_RE = re.compile(rf"([{_TAIL_SPLIT_CHARS}]+)")
_DASH_CHARS = "-–—"

# Own copy of baseline's preposition/function-word exclusion set (a
# preposition immediately before "Definitions" makes it a grammatical
# OBJECT, e.g. "Repeal of Definitions", not this heading's own subject).
_PRECEDING_EXCLUSION_WORDS = frozenset(
    {"of", "to", "for", "under", "in", "by", "from", "with", "on", "as", "than",
     "regarding", "concerning", "including", "except", "about", "into", "upon",
     "within", "without", "between", "among", "through"}
)

# Cycle 2, the ME false-positive fix: a single article is transparent to
# the preposition guard.
_ARTICLES = frozenset({"the", "a", "an"})

# R-TRUNC's target set: verified strict prefixes of "definitions".
_TRUNC_PREFIXES = frozenset({"defin", "defini", "definit", "definiti", "definitio"})

# R-MISSPELL's target set: the exact scrape-corpus misspellings.
_MISSPELL_RE = re.compile(r"^(?:defintions?|definitons?|defintion)$", re.IGNORECASE)


def strip_leading_noise(heading: str) -> str:
    m = _LEADING_NOISE_RE.match(heading)
    return heading[m.end() :] if m else heading


def tail_tokens_core(heading: str) -> list[tuple[str, bool]]:
    """Strip a trailing bracketed annotation and trailing period/
    whitespace, then split on the widened separator set. Each token is
    paired with whether a DASH occurred in the separator run immediately
    before it -- a hard CLAUSE boundary `preposition_governs` uses to tell
    a genuine predecessor from a word that merely ended the PREVIOUS
    clause."""
    trimmed = _TRAILING_BRACKET_RE.sub("", heading)
    trimmed = trimmed.rstrip(" \t\r\n.")
    tokens: list[tuple[str, bool]] = []
    dash = False
    for part in _TAIL_TOKEN_CAPTURE_RE.split(trimmed):
        if not part:
            continue
        if _TAIL_TOKEN_SPLIT_RE.fullmatch(part):
            dash = dash or any(c in _DASH_CHARS for c in part)
        else:
            tokens.append((part, dash))
            dash = False
    return tokens


def tail_tokens(heading: str) -> list[str]:
    """Plain token list for rules that only inspect the last token."""
    return [word for word, _ in tail_tokens_core(heading)]


def preposition_governs(tokens: list[tuple[str, bool]], i: int) -> bool:
    """True when a real preposition/function word grammatically governs
    `tokens[i]`, so the match at `i` must be suppressed. A dash right
    before `tokens[i]` always defeats this (a fresh clause). A single
    intervening article is transparent to the check: look past it to the
    word before, not just the immediately-preceding one."""
    if tokens[i][1] or i == 0:
        return False
    prev_word, _prev_dash = tokens[i - 1]
    prev_word = prev_word.lower()
    if prev_word in _ARTICLES:
        if i < 2 or tokens[i - 1][1]:
            return False
        prev_word = tokens[i - 2][0].lower()
    return prev_word in _PRECEDING_EXCLUSION_WORDS


def first_or_last_word_definitions(rest: str) -> bool:
    """Own copy of baseline's rule-3/rule-4 decision: match if
    "Definition(s)" is the first word of `rest`, or its last substantive
    word, guarded by `preposition_governs`."""
    if _FIRST_WORD_DEFINITIONS_RE.match(rest):
        return True
    tokens = tail_tokens_core(rest)
    if not tokens or not _LAST_WORD_DEFINITIONS_RE.match(tokens[-1][0]):
        return False
    last = len(tokens) - 1
    return last == 0 or not preposition_governs(tokens, last)


# --- Mojibake normalization (cycle 5, items 11/14) -------------------------
#
# Real dash/curly-quote characters standing in as CP1252-artifact byte
# sequences after this corpus's scrape/decode pipeline mangled them: RI's
# `\x80\x94` (em-dash) / `\x80\x9c` / `\x80\x9d` (curly double quotes), and
# AK's bare `\x97` (CP1252's own em-dash code point, decoded as a lone C1
# control character U+0097 -- never a legitimate heading character on its
# own). Blanket-replacing all four with their real Unicode counterparts
# lets the EXISTING dash-aware regexes (`_TAIL_SPLIT_CHARS`, R-VERB-
# extended, the scope-range parser) handle mojibake and clean text
# identically, without each rule needing its own byte-sequence special
# case -- same class as R-TRUNC's existing corpus-defect handling.
_MOJIBAKE_MAP = {
    "\x80\x94": "—",  # RI em-dash
    "\x80\x9c": "“",  # RI left curly double quote
    "\x80\x9d": "”",  # RI right curly double quote
    "\x97": "—",  # AK em-dash (bare CP1252 byte)
}
_MOJIBAKE_RE = re.compile("|".join(re.escape(k) for k in _MOJIBAKE_MAP))


def normalize_mojibake(heading: str) -> str:
    return _MOJIBAKE_RE.sub(lambda m: _MOJIBAKE_MAP[m.group(0)], heading)
