"""Family-4 "heading variants" rule (sprint 2026-08-04-defs-us-headings,
gates U1/U3).

`us_profile.is_definitions_heading` (see that module's header comment)
recognizes a Definitions heading only when "Definition(s)" is literally its
own FIRST word, or its LAST substantive word (preposition-exclusion guard).
Real corpus rows defeat both in six distinct, evidenced shapes -- see the
sprint contract's Mandate and the companion RED unit test's module docstring
(`backend/tests/unit/test_definition_links_us_heading_variants.py`) for the
full rule spec, recall/precision numbers, and fixture provenance. This
module is the pure-function implementation of that spec:

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
  - R-VERB-extended: `defined` immediately followed by `;`/`:`/`,`/`.`, a
    dash, or connector word `for`/`as`/`term` (cycle 3, H-R9) -- same rule.
  - R-TRUNC: the source data itself is truncated mid-word (a real corpus
    defect, Colorado-specific) -- the last tail token is a verified
    non-English strict prefix of "definitions".
  - R-MISSPELL: the last tail token is a known scrape-corpus misspelling
    of "definitions".

Cycle 2 (QA bounce, ruling H-R7 -- tokenizer/guard gaps in the above rules, not new
rules): the tail-tokenizer's separator class now also splits on an interior `.`,
`/`, `(`, `)`, recovering an interior clause-ending "Definitions." token (BUG1, CT),
a `/`-joined token (BUG4, NC), and a parenthetical `(Definitions)` (BUG5, WI) -- the
last two via R-MID's new first/last-word fallback, since exposing the word this way
makes it a first/last token, not an interior one. The preposition guard
(`_preposition_governs`) is now boundary-aware: a dash immediately before the
candidate always defeats it (BUG3, MO's "clause — clause — clause" convention: a
preposition ending the PREVIOUS clause cannot govern a new one right after a dash),
and a single intervening article is transparent to it (the ME false-positive fix:
"in the definition of ..." -- the old guard only ever looked at the immediately-
preceding token, so "the" hid the real governing preposition "in"). R-VERB-extended
now also accepts a dash (BUG2, "TERM defined — more clauses" / "defined--more"),
still excluding a bare hyphenated compound like "defined-benefit plan" (pension
jargon) by requiring either an en/em-dash, a doubled hyphen, or a single hyphen
preceded by whitespace.

Cycle 3 (QA bounce, ruling H-R9 -- sixth gap, same class): R-VERB-extended
still missed `"Mattress" defined for KRS 214.290...`, `"X" defined, more`,
`Suitable work defined. Duties of...`, and leading `Defined term`
(USC_T15_C122_S9801). Fix widens one regex: `,`/`.` join `;`/`:`, and
`for`/`as`/`term` join the dash as WORD connectors -- a closed whitelist,
not "any word", so `defined in`/`by` (cross-reference/delegation, H-R9
bars chasing these) and pension nouns (`benefit`/`contribution`/`cost`/
`area`) stay unmatched for free -- none are in the whitelist, same
mechanism that already excluded "defined-benefit". A dev-cycle-3 precision
read surfaced a real "NOT/never/no longer defined" negation false-positive
(3/25 of `defined as`, e.g. "plans not defined as pyramid promotional
schemes") -- the leading lookbehinds on `_VERB_EXTENDED_RE` fix it. `for`
independently measures ~89% precision (P-R2 trade, dev cycle-3 report,
consistent with QA's own ~86%) -- shipped, not materially below H-R9's bar.

Cycle 4 (director ruling D-DF, program ruling P-R8): `defined for` -- one
alternation of R-VERB-extended's `for|as|term` connector whitelist -- is
capture-worthy only when the BODY also carries a self-definition marker
(two independent human reads plus the manager's own full-population scan
all landed the bare `for` shape below every other shipped rule's ~90%+
precision floor). `matches_heading_variant_unconditional` is today's
family-4 union with the `for` alternation removed; `matches_defined_for_
heading` is that alternation alone (same leading negation lookbehinds);
`defines_in_body` is the new gate, consumed via the now-shipped
`HeadingRule.body_confirms` field. `matches_heading_variant` keeps its
full historical meaning unchanged (`_VERB_EXTENDED_RE` still includes
`for`) -- it is no longer what gets registered directly, but stays a
correct "is this heading a family-4 shape at all" predicate, pinned equal
to `matches_heading_variant_unconditional(h) or matches_defined_for_heading(h)`
for every heading. See `test_definition_links_us_heading_variants_d_df.py`'s
module docstring for the full design rationale (why two rules not one, why
registration order/narrowness matters under either "first-positive-wins"
dispatch reading).

Per the seam published by `claude/defs-core-scope` (`## Seam spec (published)`,
"Seam 2 -- per-jurisdiction rule registry"), a registered `HeadingRule.matches`
callable is consulted ONLY after baseline's own `is_definitions_heading` has
already returned False for the same heading. Every rule can therefore only ever
flip a currently-False verdict to True -- except through the guard, which is how
the ME fix flips one currently-True verdict to False (H-R7: the guard is
existing negative-evidence logic, not a narrowing of positive evidence).

Self-contained (ruling H-R4): this module owns its own leading-noise strip,
section-label strip, number-token strip, trailing-bracket strip, tail
tokenizer, and preposition-exclusion set -- independent copies of `us_profile.py`'s
private regexes/sets.

Every regex below is a fixed alternation of literal words/characters, or a single
quantifier over a fixed character class (lookbehinds included -- each a fixed-width
literal) -- never nested inside an alternation -- so each is unconditionally linear-
time, matching `us_profile.py`'s house style; `_tail_tokens_core`'s single pass over
`_TAIL_TOKEN_CAPTURE_RE.split(...)` is likewise linear.

Phase B (ruling H-R5): `register_heading_rule` self-registers at the bottom of
this file, now that `app.definition_links.rules.registry` exists -- Phase A
deliberately deferred that call until then.
"""

from __future__ import annotations

import re

from app.definition_links.rules.registry import HeadingRule, register_heading_rule

# --- Shared primitives (own copies -- see module docstring, ruling H-R4) ---

# Same rationale as `us_profile._LEADING_NOISE_RE`: ASCII-only so the
# scrape-corpus's mojibake accented-Latin noise bytes (which ARE Unicode
# *letters* by category) don't stop the noise-skip early. Single
# quantifier over a fixed negated class -- unconditionally linear.
_LEADING_NOISE_RE = re.compile(r"^[^A-Za-z0-9]+")

# A section number is a chain of digit-run(-plus-letters) "segments"
# joined by "." or "-" -- same shape as `us_profile._SEGMENT_RE` /
# `_SECTION_NUMBER_TOKEN_RE`. Deliberately NOT widened to accept `:` as a
# separator (redundant with R-MID, whose own tail tokenizer already splits on `:`).
_SEGMENT_RE = r"\d+[A-Za-z]*"
_NUMBER_CHAIN_RE = rf"{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?"

# R-SEC's own label: the ABBREVIATED forms baseline's `_SECTION_LABEL_RE` does not
# accept (only the spelled-out word "Section"). Four fixed literal alternatives, no
# repetition inside the alternation -- bounded, linear; the required `\s+` after the
# optional `.` also means a longer word merely starting "Sec"/"Art" can't match.
_SEC_LABEL_RE = re.compile(rf"(?:Sec|Secs|Art|Article)\.?\s+{_NUMBER_CHAIN_RE}", re.IGNORECASE)

# Same rule baseline uses for "is 'Definition(s)' the whole word here".
_FIRST_WORD_DEFINITIONS_RE = re.compile(r"Definitions?\b", re.IGNORECASE)
_LAST_WORD_DEFINITIONS_RE = re.compile(r"^Definitions?$", re.IGNORECASE)

# Same trailing-annotation-and-period tolerance as
# `us_profile._TRAILING_BRACKET_RE`.
_TRAILING_BRACKET_RE = re.compile(r"\s*\[[^\]]*\]\.?\s*$")

# Same separator set as `us_profile._TAIL_TOKEN_SPLIT_RE`, PLUS (cycle 2,
# BUG1/BUG4/BUG5) an interior `.`, `/`, `(`, `)` -- an interior clause-ending
# period, a `/`-joined pair, and a parenthetical each now expose their inner word
# as an ordinary token. `_TAIL_TOKEN_CAPTURE_RE` is the same class with a
# capturing group, used by `_tail_tokens_core` to recover which separator run
# (dash or not) precedes each token.
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
# the preposition guard -- "in the definition of ..." must still be seen
# as governed by "in", not waved through just because "the" sits in
# between it and the candidate token.
_ARTICLES = frozenset({"the", "a", "an"})

# R-TRUNC's target set: verified strict prefixes of "definitions" (length >= 5)
# that are NOT themselves real English words (checked against `/usr/share/dict/words`
# per the RED test's module docstring) -- so matching one as a heading's very last
# token is confident evidence of source-data truncation, not an unrelated word.
_TRUNC_PREFIXES = frozenset({"defin", "defini", "definit", "definiti", "definitio"})

# R-MISSPELL's target set: the exact scrape-corpus misspellings measured against the
# full 52-file token-frequency census (see the RED test's module docstring) -- a
# missing second "i" ("Defintions"/"Defintion") or missing "i" before the final
# syllable ("Definitons"/"Definiton").
_MISSPELL_RE = re.compile(r"^(?:defintions?|definitons?|defintion)$", re.IGNORECASE)

# R-VERB-extended: "defined" immediately followed by `;`/`:`/`,`/`.`, a dash
# (cycle 2, BUG2), or (cycle 3, H-R9) the literal connector word `for`/`as`/`term`
# -- a closed whitelist, not "any word" (see module docstring's "Cycle 3"
# paragraph). The leading negative lookbehinds guard against "NOT/never/no longer
# defined" (a grammatical negation, found live in the `defined as` sub-shape --
# see dev cycle-3 report).
_VERB_EXTENDED_RE = re.compile(
    r"(?<!not )(?<!never )(?<!longer )\bdefined\b(?:\s*[;:,.]|\s*(?:[–—]|-{2,})|\s+-(?!-)|\s+(?:for|as|term)\b)", re.IGNORECASE
)

# Cycle 4, D-DF: the SAME alternation as `_VERB_EXTENDED_RE` with the `for`
# branch removed -- `as`/`term`/punctuation/dash forms are untouched. This is
# what `matches_heading_variant_unconditional` uses in place of the full
# `_VERB_EXTENDED_RE` (see module docstring's "Cycle 4" paragraph).
_VERB_EXTENDED_UNCONDITIONAL_RE = re.compile(
    r"(?<!not )(?<!never )(?<!longer )\bdefined\b(?:\s*[;:,.]|\s*(?:[–—]|-{2,})|\s+-(?!-)|\s+(?:as|term)\b)",
    re.IGNORECASE,
)

# Cycle 4, D-DF: exactly the alternation split OUT of R-VERB-extended above
# -- `defined` immediately followed by the literal connector word `for`.
# Same leading negation lookbehinds as `_VERB_EXTENDED_RE` (H-R9 -- they
# fixed three real false positives and must keep applying to this shape).
_VERB_FOR_RE = re.compile(r"(?<!not )(?<!never )(?<!longer )\bdefined\b\s+for\b", re.IGNORECASE)

# --- D-DF's `defines_in_body` self-definition-marker predicate ----------
#
# A quoted TERM -- straight or curly DOUBLE quotes, or curly single quotes --
# directly followed, or after a short intervening gap (see `_AFTER_QUOTE_
# GAP_RE` below) and/or a whitelisted "as used in .../for (the) purpose(s)
# of ..." lead-in clause BEFORE the quote, by the defining verb
# `means`/`mean`/`shall mean` or the phrase `is defined as`. A straight
# apostrophe (') is deliberately EXCLUDED from the quote-char classes: it
# is indistinguishable from a contraction/possessive in running prose
# ("individual's", "owner's"), and the RED test's own "Known limits"
# section confirms single-quote forms are untested by the pinned fixture --
# so narrowing to double quotes (plus unambiguous curly single quotes) costs
# no pinned behavior while avoiding a real false-positive source.
#
# The BEFORE-quote lead-in covers "As used in KRS 214.290 to 214.310,
# "mattress" means ...". `shall mean` (cycle-4 bounce, gap 1) joins
# `means`/`mean`/`is defined as` -- the same defining-idiom set already
# established by `us_profile._MEANS_IDIOM_GAP_RE` (`\b(?:means|shall
# mean|has the meaning)\b`); omitting it here was an inconsistency with
# that convention, not a deliberate narrowing. `has the meaning` is
# deliberately NOT copied from that idiom set -- it is precisely the
# cross-reference shape D-DF exists to exclude ("has the meaning ascribed
# to it in NRS 459.7024"), not a self-definition.
#
# Deliberately conservative (see module docstring / RED test's "Known,
# honestly-stated limits"): a cross-reference verb ("has the meaning
# ascribed to...", "is defined IN ...") never itself contains `means`/
# `shall mean`/`is defined as` as a whole word, so it still never matches.
# Misses defining verbs other than `means`/`mean`/`shall mean`/`is defined
# as` (`includes`, `refers to`, `is a`, ...) by design -- not pinned either
# direction, a real implementation may reasonably go either way.
_QUOTE_OPEN_CHARS = "\"‘“"
_QUOTE_CLOSE_CHARS = "\"’”"
_LEAD_IN_CLAUSE_RE = (
    rf"(?:as used in|for (?:the )?purposes? of)\b[^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS},]{{0,60}}"
)
_DEFINING_VERB_RE = r"(?:means?|shall\s+mean|is\s+defined\s+as)\b"

# Cycle-4 bounce (H-R7/H-R9-class gap fix, gap 2): the AFTER-quote gap
# between the term's closing quote and the defining verb used to be a
# whitelisted lead-in clause only. Real drafting puts arbitrary SHORT
# qualifiers there instead ("... with a public utility means:", "... when
# referring to an Oregon commercial bank, means ..."). Same shape as
# `us_profile.py`'s proven `_MEANS_IDIOM_GAP_RE` (`^[^"...]{0,200}?
# \b(?:means|shall mean|has the meaning)\b`, minus the `has the meaning`
# branch -- see above): a bounded, NON-GREEDY run of any characters EXCEPT
# quote characters. Forbidding intervening quote characters is
# load-bearing, the same way it is there -- it stops a later quoted phrase
# belonging to a DIFFERENT (usually the NEXT) entry's own term from ever
# bridging a match across it. Bounded (not `*`/`+`) so it stays
# unconditionally linear-time, same house style as every other regex in
# this module.
#
# Bound is 80, NOT `_MEANS_IDIOM_GAP_RE`'s 200 -- a deliberate divergence,
# not a copy-paste miss. That regex runs against a `gap` already sliced
# from an individually-segmented definition entry; this one runs
# `re.search` over a WHOLE section body, where a long `includes:` list can
# sit between an unrelated quoted term and a later, unrelated `means`
# defining a different nested sub-term. Measured over the real 110-row
# `defined for` population (manager re-measurement, cycle-4 bounce): 80 is
# the smallest bound that still clears both genuine intervening-qualifier
# gaps this fix targets (28 chars, OR 757.015; 51 chars, OR 708A.290) while
# excluding the one false-positive bridge 200 let through (103 chars,
# WA 41.04.005, bridging "period of war" across an `includes:` list to a
# `means` that actually defines "the Vietnam era", not "period of war").
_AFTER_QUOTE_GAP_RE = rf"[^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS}]{{0,80}}?"
_SELF_DEFINITION_RE = re.compile(
    rf"(?:{_LEAD_IN_CLAUSE_RE}\s*,?\s*)?"
    rf"[{_QUOTE_OPEN_CHARS}][^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS}]{{1,80}}[{_QUOTE_CLOSE_CHARS}]"
    rf"{_AFTER_QUOTE_GAP_RE}"
    rf"{_DEFINING_VERB_RE}",
    re.IGNORECASE,
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
    """R-VERB-extended: `defined` immediately followed by punctuation, a
    dash, or a whitelisted connector word -- see `_VERB_EXTENDED_RE`."""
    return bool(_VERB_EXTENDED_RE.search(heading))


def _rule_verb_extended_unconditional(heading: str) -> bool:
    """Cycle 4, D-DF: same as `_rule_verb_extended` but via
    `_VERB_EXTENDED_UNCONDITIONAL_RE` -- every R-VERB-extended shape except
    the `for` connector, which is gated separately (`matches_defined_for_
    heading` below)."""
    return bool(_VERB_EXTENDED_UNCONDITIONAL_RE.search(heading))


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
    """True when `heading` matches any of the six family-4 rules above,
    UNCHANGED historical meaning (cycle 4, D-DF): the full union, still
    INCLUDING the `for` connector alternation via `_rule_verb_extended`. No
    longer what gets registered directly (see `matches_heading_variant_
    unconditional` / `matches_defined_for_heading` below and module
    docstring's "Cycle 4" paragraph) but kept as a correct, useful "is this
    heading a family-4 shape at all" predicate -- pinned equal to
    `matches_heading_variant_unconditional(h) or matches_defined_for_heading(h)`
    for every heading. Callers are expected (per the seam's baseline-first/
    registry-second contract) to consult this only after `us_profile.
    is_definitions_heading` has already returned False for the same
    heading -- see module docstring."""
    return (
        _rule_sec(heading)
        or _rule_mid(heading)
        or _rule_verb_bare(heading)
        or _rule_verb_extended(heading)
        or _rule_trunc(heading)
        or _rule_misspell(heading)
    )


def matches_heading_variant_unconditional(heading: str) -> bool:
    """Cycle 4, D-DF: the union of R-SEC, R-MID, R-VERB-bare,
    R-VERB-extended-minus-`for`, R-TRUNC, R-MISSPELL -- every family-4 shape
    EXCEPT the `defined for` connector, which is gated on `defines_in_body`
    instead (see `matches_defined_for_heading`, registered separately
    below). This is the rule actually registered with `body_confirms=None`."""
    return (
        _rule_sec(heading)
        or _rule_mid(heading)
        or _rule_verb_bare(heading)
        or _rule_verb_extended_unconditional(heading)
        or _rule_trunc(heading)
        or _rule_misspell(heading)
    )


def matches_defined_for_heading(heading: str) -> bool:
    """Cycle 4, D-DF: NARROW predicate, true iff `defined` is immediately
    followed by the literal connector word `for` -- exactly the alternation
    split out of `matches_heading_variant_unconditional`. Registered with
    `body_confirms=defines_in_body`, so a match here only counts once the
    body also carries a self-definition marker."""
    return bool(_VERB_FOR_RE.search(heading))


def defines_in_body(body: str) -> bool:
    """Cycle 4, D-DF's self-definition-marker predicate -- see the
    `_SELF_DEFINITION_RE` block above and the RED test file's module
    docstring for the full behavioral spec this reproduces. Scans the FULL
    body via `re.search` (not anchored or prefix-limited): a real pinned
    marker can sit ~1500 chars in (the CT `31-232l` "suitable work" row)."""
    return bool(_SELF_DEFINITION_RE.search(body))


# Cycle 4, D-DF: TWO registrations, in this exact order -- unconditional
# first (every family-4 shape except `defined for`, body_confirms left at
# its default None), then gated second (the `defined for` shape alone,
# body_confirms=defines_in_body). Order and rule-2 narrowness both matter
# for dispatch safety under either plausible "first-positive-wins" reading
# -- see module docstring's "Cycle 4" paragraph and the RED test files'
# module docstrings for the full rationale. Replaces the single
# `register_heading_rule(HeadingRule(..., matches=matches_heading_variant))`
# call this module shipped before D-DF.
register_heading_rule(
    HeadingRule(jurisdiction_codes=("US-*",), matches=matches_heading_variant_unconditional)
)
register_heading_rule(
    HeadingRule(
        jurisdiction_codes=("US-*",),
        matches=matches_defined_for_heading,
        body_confirms=defines_in_body,
    )
)
