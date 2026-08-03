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
    check.
  - R-VERB-bare: the heading's last tail token is exactly `defined` --
    the "`X` defined" drafting convention baseline has no notion of at
    all (no "Definitions" token anywhere).
  - R-VERB-extended: `defined` immediately followed by `;` or `:` (optional
    whitespace) and more clause text -- same convention, mid-heading.
  - R-TRUNC: the source data itself is truncated mid-word (a real corpus
    defect, Colorado-specific) -- the last tail token is a verified
    non-English strict prefix of "definitions".
  - R-MISSPELL: the last tail token is a known scrape-corpus misspelling
    of "definitions".

Per the seam published by `claude/defs-core-scope` (`## Seam spec
(published)`, "Seam 2 -- per-jurisdiction rule registry"), a registered
`HeadingRule.matches` callable is consulted ONLY after baseline's own
`is_definitions_heading` has already returned False for the same heading.
That ordering means every rule below can only ever flip a currently-False
verdict to True -- it is structurally incapable of overriding a heading
baseline already (correctly) recognizes. Every rule here is therefore
phrased as "match X", never as "stop excluding Y" (ruling H-R4): none of
them re-implements or narrows baseline's own preposition-exclusion guard,
they each add independent NEW positive evidence.

Self-contained (ruling H-R4): this module owns its own leading-noise
strip, section-label strip, number-token strip, trailing-bracket strip,
tail tokenizer, and preposition-exclusion set. It does not import
`us_profile.py`'s private `_SECTION_LABEL_RE`, `_SECTION_NUMBER_TOKEN_RE`,
`_TAIL_TOKEN_SPLIT_RE`, or `_PRECEDING_EXCLUSION_WORDS` -- the regexes
below are independently-defined copies of the same semantics, not shared
objects, so a future edit to `us_profile.py` cannot silently change this
module's behavior (or vice versa).

Every regex below is a fixed alternation of literal words, or a single
quantifier over a fixed character class -- no quantifier is ever nested
inside an alternation -- so each is unconditionally linear-time in the
length of the heading, matching the house style `us_profile.py` documents
and validates (see that module's own header comment for why this matters
on a ~2M-row bulk-ingest call path).

Phase B note (not this module's concern yet): the `register_heading_rule`
self-registration call that wires this function into the real registry
lands separately, once `app.definition_links.rules.registry` exists on
this branch (ruling H-R5) -- this file intentionally contains ONLY the
pure function.
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
# separator (measured redundant with R-MID for every real row that would
# need it -- see module docstring's R-MID entry and the RED test's
# R-COLON note; baseline's own tail tokenizer already splits on `:`,
# which is the mechanism R-MID relies on instead).
_SEGMENT_RE = r"\d+[A-Za-z]*"
_NUMBER_CHAIN_RE = rf"{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?"

# R-SEC's own label: the ABBREVIATED forms baseline's `_SECTION_LABEL_RE`
# does not accept (that regex only matches the spelled-out word
# "Section"). Four fixed literal alternatives, each tried at most once at
# a given start position -- no repetition inside the alternation, so this
# stays a bounded, linear scan regardless of how many alternatives fail
# before one succeeds (the required `\s+` right after the optional `.`
# also means a longer unrelated word that merely starts with "Sec"/"Art"
# -- e.g. "Section", "Secondary", "Article-adjacent-but-not-this" --
# cannot accidentally match: the whitespace requirement forces the label
# word to end exactly where the alternative says it does).
_SEC_LABEL_RE = re.compile(
    rf"(?:Sec|Secs|Art|Article)\.?\s+{_NUMBER_CHAIN_RE}", re.IGNORECASE
)

# Same rule baseline uses for "is 'Definition(s)' the whole word here".
_FIRST_WORD_DEFINITIONS_RE = re.compile(r"Definitions?\b", re.IGNORECASE)
_LAST_WORD_DEFINITIONS_RE = re.compile(r"^Definitions?$", re.IGNORECASE)

# Same trailing-annotation-and-period tolerance as
# `us_profile._TRAILING_BRACKET_RE`.
_TRAILING_BRACKET_RE = re.compile(r"\s*\[[^\]]*\]\.?\s*$")

# Same separator set as `us_profile._TAIL_TOKEN_SPLIT_RE`: whitespace or
# hyphen/en-dash/em-dash/colon/semicolon/comma, so a no-space
# "Topic-Definitions" heading tokenizes the same as a spaced one, and a
# colon-numbered heading (DC's real UCC `28:2A-103` shape) still splits
# its number away from the word tokens that follow it.
_TAIL_TOKEN_SPLIT_RE = re.compile(r"[\s\-–—:;,]+")

# Own copy of baseline's preposition/function-word exclusion set -- see
# `us_profile._PRECEDING_EXCLUSION_WORDS` for the rationale (a preposition
# immediately before "Definitions" makes it a grammatical OBJECT, e.g.
# "Repeal of Definitions", not this heading's own subject).
_PRECEDING_EXCLUSION_WORDS = frozenset(
    {
        "of",
        "to",
        "for",
        "under",
        "in",
        "by",
        "from",
        "with",
        "on",
        "as",
        "than",
        "regarding",
        "concerning",
        "including",
        "except",
        "about",
        "into",
        "upon",
        "within",
        "without",
        "between",
        "among",
        "through",
    }
)

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

# R-VERB-extended: the word "defined" immediately followed (after
# optional whitespace) by a clause-separator punctuation mark. Single
# fixed literal plus one bounded `\s*` plus one fixed character class --
# no nesting, unconditionally linear.
_VERB_EXTENDED_RE = re.compile(r"\bdefined\b\s*[;:]", re.IGNORECASE)


def _strip_leading_noise(heading: str) -> str:
    m = _LEADING_NOISE_RE.match(heading)
    return heading[m.end() :] if m else heading


def _tail_tokens(heading: str) -> list[str]:
    """Same tokenization baseline's own last-word check uses: strip a
    trailing bracketed annotation and any trailing period/whitespace, then
    split on the shared separator set. Used directly on the full heading
    (not a label/number-stripped remainder) -- R-MID's "except the very
    first or very last" carve-out is self-referential to this same list,
    so it needs no separate normalization step to line up with it, and
    every rule that only cares about the LAST token (R-TRUNC, R-VERB-bare,
    R-MISSPELL) is unaffected by whatever a leading label/number looks
    like."""
    trimmed = _TRAILING_BRACKET_RE.sub("", heading)
    trimmed = trimmed.rstrip(" \t\r\n.")
    return [t for t in _TAIL_TOKEN_SPLIT_RE.split(trimmed) if t]


def _first_or_last_word_definitions(rest: str) -> bool:
    """Own copy of baseline's rule-3/rule-4 decision (see
    `us_profile.is_definitions_heading`'s header comment): match if
    "Definition(s)" is the first word of `rest`, or its last substantive
    word with a non-preposition predecessor."""
    if _FIRST_WORD_DEFINITIONS_RE.match(rest):
        return True
    tokens = _tail_tokens(rest)
    if not tokens or not _LAST_WORD_DEFINITIONS_RE.match(tokens[-1]):
        return False
    if len(tokens) == 1:
        return True
    preceding = tokens[-2]
    return preceding.lower() not in _PRECEDING_EXCLUSION_WORDS


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
    """R-MID: an exact `Definition`/`Definitions` tail token at any
    position except the first or the last, whose immediately preceding
    token is not a preposition/function word."""
    tokens = _tail_tokens(heading)
    for i in range(1, len(tokens) - 1):
        if tokens[i].lower() in ("definition", "definitions"):
            if tokens[i - 1].lower() not in _PRECEDING_EXCLUSION_WORDS:
                return True
    return False


def _rule_verb_bare(heading: str) -> bool:
    """R-VERB-bare: the last tail token is exactly `defined`."""
    tokens = _tail_tokens(heading)
    return bool(tokens) and tokens[-1].lower() == "defined"


def _rule_verb_extended(heading: str) -> bool:
    """R-VERB-extended: `defined` immediately followed by `;` or `:`
    (optional whitespace) and more clause text."""
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
