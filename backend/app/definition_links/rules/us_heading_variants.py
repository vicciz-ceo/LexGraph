"""Family-4 "heading variants" rule (sprint 2026-08-04-defs-us-headings,
gates U1/U3).

`us_profile.is_definitions_heading` (see that module's own header comment)
recognizes a Definitions heading only when "Definition(s)" is literally the
heading's own FIRST word, or its LAST substantive word (with a
preposition-exclusion guard). Real corpus rows defeat both of those in six
distinct, evidenced shapes -- see the sprint contract's Mandate and the
companion RED unit test's module docstring
(`backend/tests/unit/test_definition_links_us_heading_variants.py`) for the
full rule spec, per-rule recall/precision numbers, and fixture provenance.
This module is the pure-function implementation of that spec:

  - R-SEC: an abbreviated `Sec.`/`Secs.`/`Art.`/`Article` section-label
    (baseline only recognizes the spelled-out word `Section`) -- strip it,
    then apply the SAME first-word/last-word decision baseline uses.
  - R-MID: `Definition`/`Definitions` as an exact, standalone TAIL TOKEN at
    any position except the very first or the very last (those two
    positions are baseline's own job) -- guarded by the same
    preposition-exclusion semantics baseline applies to its last-word
    check. Falls back to a first/last-word recheck (cycle 2 below) when no
    interior token matches.
  - R-VERB-bare: the heading's last tail token is exactly `defined` --
    the "`X` defined" drafting convention baseline has no notion of at
    all (no "Definitions" token anywhere).
  - R-VERB-extended: `defined` immediately followed by `;`/`:`, or a dash,
    and more clause text -- same convention, mid-heading.
  - R-TRUNC: the source data itself is truncated mid-word (a real corpus
    defect, Colorado-specific) -- the last tail token is a verified
    non-English strict prefix of "definitions".
  - R-MISSPELL: the last tail token is a known scrape-corpus misspelling
    of "definitions".

Cycle 2 (QA bounce, ruling H-R7 -- tokenizer/guard gaps in the above rules,
not new rules): the tail-tokenizer's separator class now also splits on an
interior `.`, `/`, `(`, `)`, recovering an interior clause-ending
"Definitions." token (BUG1, CT), a `/`-joined token (BUG4, NC), and a
parenthetical `(Definitions)` (BUG5, WI) -- the last two via R-MID's new
first/last-word fallback, since exposing the word this way makes it a
first/last token, not an interior one. The preposition guard
(`_preposition_governs`) is now boundary-aware: a dash immediately before
the candidate always defeats it (BUG3, MO's "clause — clause — clause"
convention: a preposition ending the PREVIOUS clause cannot govern a new
one right after a dash), and a single intervening article is transparent
to it (the ME false-positive fix: "in the definition of ..." -- the old
guard only ever looked at the immediately-preceding token, so "the" hid
the real governing preposition "in"). R-VERB-extended now also accepts a
dash (BUG2, "TERM defined — more clauses" / "defined--more"), still
excluding a bare hyphenated compound like "defined-benefit plan" (pension
jargon) by requiring either an en/em-dash, a doubled hyphen, or a single
hyphen preceded by whitespace.

Per the seam published by `claude/defs-core-scope` (`## Seam spec
(published)`, "Seam 2 -- per-jurisdiction rule registry"), a registered
`HeadingRule.matches` callable is consulted ONLY after baseline's own
`is_definitions_heading` has already returned False for the same heading.
Every rule can therefore only ever flip a currently-False verdict to True
-- except through the guard, which is how the ME fix flips one currently-
True verdict to False (H-R7: the guard is existing negative-evidence
logic, not a narrowing of positive evidence).

Self-contained (ruling H-R4): this module owns its own leading-noise
strip, section-label strip, number-token strip, trailing-bracket strip,
tail tokenizer, and preposition-exclusion set -- independent copies of
`us_profile.py`'s private regexes/sets, not shared objects, per H-R4.

Every regex below is a fixed alternation of literal words/characters, or a
single quantifier over a fixed character class -- no quantifier is ever
nested inside an alternation -- so each is unconditionally linear-time,
matching `us_profile.py`'s house style; `_tail_tokens_core`'s single pass
over `_TAIL_TOKEN_CAPTURE_RE.split(...)` is likewise linear.

Phase B note (not this module's concern yet): the `register_heading_rule`
self-registration call lands separately, once
`app.definition_links.rules.registry` exists (ruling H-R5) -- this file
intentionally contains ONLY the pure function.
"""

from __future__ import annotations

import re

# --- Shared primitives (own copies -- see module docstring, ruling H-R4) ---

# Same rationale as `us_profile._LEADING_NOISE_RE`: ASCII-only so the
# scrape-corpus's mojibake accented-Latin noise bytes (which ARE Unicode
# *letters* by category) don't stop the noise-skip early. Single
# quantifier over a fixed negated class -- unconditionally linear.
_LEADING_NOISE_RE = re.compile(r"^[^A-Za-z0-9]+")

# A section number is a chain of digit-run(-plus-letters) "segments"
# joined by "." or "-" -- same shape as `us_profile._SEGMENT_RE` /
# `_SECTION_NUMBER_TOKEN_RE`. Deliberately NOT widened to accept `:` as a
# separator (redundant with R-MID -- baseline's own tail tokenizer
# already splits on `:`, which is what R-MID relies on instead).
_SEGMENT_RE = r"\d+[A-Za-z]*"
_NUMBER_CHAIN_RE = rf"{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?"

# R-SEC's own label: the ABBREVIATED forms baseline's `_SECTION_LABEL_RE`
# does not accept (only the spelled-out word "Section"). Four fixed
# literal alternatives, no repetition inside the alternation -- bounded,
# linear scan; the required `\s+` after the optional `.` also means a
# longer unrelated word merely starting with "Sec"/"Art" (e.g. "Section",
# "Secondary") cannot accidentally match.
_SEC_LABEL_RE = re.compile(
    rf"(?:Sec|Secs|Art|Article)\.?\s+{_NUMBER_CHAIN_RE}", re.IGNORECASE
)

# Same rule baseline uses for "is 'Definition(s)' the whole word here".
_FIRST_WORD_DEFINITIONS_RE = re.compile(r"Definitions?\b", re.IGNORECASE)
_LAST_WORD_DEFINITIONS_RE = re.compile(r"^Definitions?$", re.IGNORECASE)

# Same trailing-annotation-and-period tolerance as
# `us_profile._TRAILING_BRACKET_RE`.
_TRAILING_BRACKET_RE = re.compile(r"\s*\[[^\]]*\]\.?\s*$")

# Same separator set as `us_profile._TAIL_TOKEN_SPLIT_RE`, PLUS (cycle 2,
# BUG1/BUG4/BUG5) an interior `.`, `/`, `(`, `)` -- an interior
# clause-ending period, a `/`-joined pair, and a parenthetical each now
# expose their inner word as an ordinary token. `_TAIL_TOKEN_CAPTURE_RE`
# is the same class with a capturing group, used by `_tail_tokens_core`
# to recover which separator run (dash or not) precedes each token.
_TAIL_SPLIT_CHARS = r"\s\-–—:;,./()"
_TAIL_TOKEN_SPLIT_RE = re.compile(rf"[{_TAIL_SPLIT_CHARS}]+")
_TAIL_TOKEN_CAPTURE_RE = re.compile(rf"([{_TAIL_SPLIT_CHARS}]+)")
_DASH_CHARS = "-–—"

# Own copy of baseline's preposition/function-word exclusion set (a
# preposition immediately before "Definitions" makes it a grammatical
# OBJECT, e.g. "Repeal of Definitions", not this heading's own subject).
_PRECEDING_EXCLUSION_WORDS = frozenset(
    {
        "of", "to", "for", "under", "in", "by", "from", "with", "on", "as",
        "than", "regarding", "concerning", "including", "except", "about",
        "into", "upon", "within", "without", "between", "among", "through",
    }
)

# Cycle 2, the ME false-positive fix: a single article is transparent to
# the preposition guard -- "in the definition of ..." must still be seen
# as governed by "in", not waved through just because "the" sits in
# between it and the candidate token.
_ARTICLES = frozenset({"the", "a", "an"})

# R-TRUNC's target set: verified strict prefixes of "definitions" (length
# >= 5) that are NOT themselves real English words (checked against
# `/usr/share/dict/words` per the RED test's module docstring) -- so
# matching one of these as a heading's very last token is confident
# evidence of source-data truncation, not an unrelated short word.
_TRUNC_PREFIXES = frozenset({"defin", "defini", "definit", "definiti", "definitio"})

# R-MISSPELL's target set: the exact scrape-corpus misspellings measured
# against the full 52-file token-frequency census (see the RED test's
# module docstring) -- a missing second "i" ("Defintions"/"Defintion") or
# a missing "i" before the final syllable ("Definitons"/"Definiton").
_MISSPELL_RE = re.compile(r"^(?:defintions?|definitons?|defintion)$", re.IGNORECASE)

# R-VERB-extended: "defined" immediately followed (after optional
# whitespace) by `;`/`:`, OR (cycle 2, BUG2) a dash. An en/em-dash or a
# DOUBLED ASCII hyphen ("--") is unambiguous clause-separator punctuation
# regardless of surrounding whitespace (MO/SD/NV/KY/TN/ND/OK/UT); no real
# compound adjective is typeset that way. A SINGLE ASCII hyphen is
# ambiguous (also how "defined-benefit" pension jargon is written), so
# that branch requires a preceding whitespace char to distinguish "TERM
# defined - more" from "defined-benefit" (zero whitespace, excluded).
_VERB_EXTENDED_RE = re.compile(
    r"\bdefined\b(?:\s*[;:]|\s*(?:[–—]|-{2,})|\s+-(?!-))", re.IGNORECASE
)


def _strip_leading_noise(heading: str) -> str:
    m = _LEADING_NOISE_RE.match(heading)
    return heading[m.end() :] if m else heading


def _tail_tokens_core(heading: str) -> list[tuple[str, bool]]:
    """Strip a trailing bracketed annotation and trailing period/
    whitespace, then split on the widened separator set. Each token is
    paired with whether a DASH occurred in the separator run immediately
    before it -- a hard CLAUSE boundary (BUG3) `_preposition_governs`
    uses to tell a genuine predecessor from a word that merely ended the
    PREVIOUS clause."""
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


def _tail_tokens(heading: str) -> list[str]:
    """Plain token list for rules that only inspect the last token."""
    return [word for word, _ in _tail_tokens_core(heading)]


def _preposition_governs(tokens: list[tuple[str, bool]], i: int) -> bool:
    """True when a real preposition/function word grammatically governs
    `tokens[i]`, so the match at `i` must be suppressed. A dash right
    before `tokens[i]` always defeats this (BUG3: a fresh clause). A
    single intervening article is transparent to the check (ME fix): look
    past it to the word before, not just the immediately-preceding one."""
    if tokens[i][1] or i == 0:
        return False
    prev_word, _prev_dash = tokens[i - 1]
    prev_word = prev_word.lower()
    if prev_word in _ARTICLES:
        if i < 2 or tokens[i - 1][1]:
            return False
        prev_word = tokens[i - 2][0].lower()
    return prev_word in _PRECEDING_EXCLUSION_WORDS


def _first_or_last_word_definitions(rest: str) -> bool:
    """Own copy of baseline's rule-3/rule-4 decision: match if
    "Definition(s)" is the first word of `rest`, or its last substantive
    word, guarded by `_preposition_governs`."""
    if _FIRST_WORD_DEFINITIONS_RE.match(rest):
        return True
    tokens = _tail_tokens_core(rest)
    if not tokens or not _LAST_WORD_DEFINITIONS_RE.match(tokens[-1][0]):
        return False
    last = len(tokens) - 1
    return last == 0 or not _preposition_governs(tokens, last)


def _rule_sec(heading: str) -> bool:
    """R-SEC: strip an abbreviated `Sec.`/`Secs.`/`Art.`/`Article`
    section-label prefix, then apply baseline's own first-word/last-word
    decision to whatever remains."""
    rest = _strip_leading_noise(heading)
    m = _SEC_LABEL_RE.match(rest)
    if not m:
        return False
    return _first_or_last_word_definitions(rest[m.end() :].lstrip())


def _rule_mid(heading: str) -> bool:
    """R-MID: an exact `Definition`/`Definitions` tail token, guarded by
    `_preposition_governs`, at any position except the very first or very
    last per OUR OWN tokenizer. Falls back (cycle 2, BUG4/BUG5) to a
    first/last-word recheck with the same widened tokenizer, for headings
    where `/` or parentheses glued the real first/last word together in a
    way baseline's own narrower tokenizer never split apart."""
    tokens = _tail_tokens_core(heading)
    for i in range(1, len(tokens) - 1):
        word, _dash = tokens[i]
        if word.lower() in ("definition", "definitions") and not _preposition_governs(tokens, i):
            return True
    return _first_or_last_word_definitions(_strip_leading_noise(heading))


def _rule_verb_bare(heading: str) -> bool:
    """R-VERB-bare: the last tail token is exactly `defined`."""
    tokens = _tail_tokens(heading)
    return bool(tokens) and tokens[-1].lower() == "defined"


def _rule_verb_extended(heading: str) -> bool:
    """R-VERB-extended: `defined` immediately followed by `;`/`:`, or by
    whitespace then a dash, and more clause text."""
    return bool(_VERB_EXTENDED_RE.search(heading))


def _rule_trunc(heading: str) -> bool:
    """R-TRUNC: the last tail token is a verified non-English strict
    prefix of "definitions" (source-data truncation, not a drafting
    convention)."""
    tokens = _tail_tokens(heading)
    return bool(tokens) and tokens[-1].lower() in _TRUNC_PREFIXES


def _rule_misspell(heading: str) -> bool:
    """R-MISSPELL: the last tail token is a known scrape-corpus
    misspelling of "definitions"."""
    tokens = _tail_tokens(heading)
    return bool(tokens) and bool(_MISSPELL_RE.match(tokens[-1]))


def matches_heading_variant(heading: str) -> bool:
    """True when `heading` matches any of the six family-4 rules above.
    Callers are expected (per the seam's baseline-first/registry-second
    contract) to consult this only after `us_profile.is_definitions_heading`
    has already returned False for the same heading -- see module
    docstring."""
    return (
        _rule_sec(heading)
        or _rule_mid(heading)
        or _rule_verb_bare(heading)
        or _rule_verb_extended(heading)
        or _rule_trunc(heading)
        or _rule_misspell(heading)
    )
