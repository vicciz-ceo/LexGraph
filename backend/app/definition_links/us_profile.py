"""US jurisdiction profile (sprint 2026-08-02-us-state-law, item 3, gates
G2 "a real US statute parses", G3 "English term linking works", G4 "US
citations are recognised").

Design decision (documented per the item brief): **ONE `"US"`-family profile
class (`USProfile`) serves every `US-*`/`US-FED` jurisdiction code**, not a
per-state profile. Evidence: the RED unit test (`test_definition_links_us_
profile.py`) instantiates the profile via `get_profile("US-DE")` and every
assertion in it exercises pure English statutory-drafting conventions
(`"Definitions"` headings, `has the meaning specified in` / `as defined in`
idioms, `Section N` / `§ N` / `N U.S.C. § N` citation grammar) that are not
Delaware-specific -- nothing in the fixture data or the gate text (G2-G4)
calls for state-specific parsing rules. `profiles.py` registers the SAME
`USProfile()` instance under every one of the 53 non-`"IL"` codes in
`app.services.jurisdiction.JURISDICTION_CODES` (`US-<postal>`, `US-DC`,
`US-PR`, `US-FED`). A later sprint can split this into per-state profiles
if state-specific drafting conventions are ever found to diverge; nothing
in this module's public surface assumes a single profile instance, so that
split is additive whenever it is needed.

Inputs to every function/method here are plain, NOT Stage-0-normalized in
the Hebrew-engine's full sense (`normalize_for_parsing` does NOT do NFC
normalization, niqqud stripping, or dash-variant collapsing -- see its own
docstring for the one thing it DOES do) -- English statute text needs no
wikilink-bracket stripping or bidi handling. `is_definitions_heading` in
particular is deliberately a CONTAINS/substring check, not an
anchored-at-start check like Hebrew's
`sections._DEFINITIONS_HEADING_RE`: real Delaware `section_title` values
carry scrape-noise (mojibake `Â`, a raw CRLF, leading whitespace) BEFORE the
actual heading text (see `backend/tests/fixtures/us_statutes/README.md`),
so anchoring at the start of the raw string would fail on 100% of that real
dataset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.definition_links.derivation import LawDerivesDefinitionEdge
from app.definition_links.extract import DefinitionCandidate

# --- G2: Definitions-heading detection --------------------------------------
#
# History / rationale (wave-4 QA cycle-2 fix, items Q3a/Q3b):
#
# The wave-3 implementation was a single regex,
# `^(?:[^A-Za-z]+|Section\s+\d+\.?)*Definitions?\b`, with a nested
# quantifier (`(?:...)*`) wrapped around an alternation. That shape is the
# textbook catastrophic-backtracking (ReDoS) construct: on any heading
# whose leading non-letter run does NOT end in "Definitions", the engine
# tries exponentially many ways to partition that run between the two
# alternatives before giving up. Manager-measured wall-clock time exploded
# from 58.7ms (21-char noise run) to 15.8s (29-char run) on inputs that are
# NOT pathological -- they're the dataset's ordinary scrape-noise shape.
# This sits on `pipeline.py` Stage 2's real per-article call path, so one
# bad heading could hang a ~2M-row bulk ingest indefinitely.
#
# It was also wrong: real Delaware section numbers routinely embed a
# letter (`12D-102`, `4A-103`, `9002B`, `2502H`) -- the `[^A-Za-z]+`
# noise-skipper halts at that letter and never reaches "Definitions",
# silently under-matching 15.6% (152/973) of the real dataset's genuine
# Definitions headings.
#
# This rewrite is a short chain of linear-time, non-nested-quantifier
# regexes plus a `str.split()` tokenization -- no step re-scans a range of
# the input under a different alternative, so there is no backtracking
# blowup regardless of input shape (proved in the module's test/validation
# run, not just asserted here).
#
# The matching rule (works out the "subject vs. mentioned" tension R6/Q3b
# demands -- see docstring examples below):
#
#   1. Strip any leading run of non-letter/non-digit scrape noise (mojibake,
#      §, CR/LF, whitespace).
#   2. Strip a section-number label immediately after that noise: either
#      the spelled-out `"Section <N>."` form, or a bare number token made of
#      one or more `.`/`-`-joined segments (each a digit run optionally
#      followed by letters), covering real DE (`12D-102.`, `4A-103.`,
#      `9002B.`), real FL/OH dotted numbers (`941.34`, `4513.01`), and real
#      TX letter-then-dot numbers (`2A.103.`) alike -- see `_SEGMENT_RE`.
#   3. MATCH if "Definition(s)" is the FIRST WORD of whatever remains --
#      i.e. it is the heading's own immediate subject
#      ("Definitions", "Definitions and Interpretation", "796. Definitions.").
#   4. OTHERWISE, MATCH if "Definition(s)" is the LAST substantive word
#      (ignoring a trailing "[...]" annotation and trailing punctuation),
#      tokenizing on whitespace AND separator punctuation (`-`, en/em dash,
#      `:`, `;`, `,`) so a no-space "Topic-Definitions" heading still
#      splits into separate tokens the same as a spaced one -- AND the
#      token immediately before it is not a preposition/function word
#      (`_PRECEDING_EXCLUSION_WORDS`, e.g. "of", "to", "for"). A preposition
#      means "Definitions" is a grammatical OBJECT ("Repeal of Definitions",
#      "Application of Definitions to Prior Acts" -- QA cycle-1's
#      over-match probe, must stay False); anything else immediately
#      before it -- an adjective ("General Definitions", "Other
#      Definitions"), a dash/colon separator ("Payment Order-Definitions"),
#      or the corpus's mojibake dash artifact `â`/`Â`
#      ("Payment order â Definitions.") -- means "Definitions" is the
#      heading's own subject, just introduced/qualified rather than being
#      the literal first word.
#
# Real-data validation (2026-08-02, wave-4 fix): see the developer report
# for miss-rate/false-positive numbers against the full `us_de_statutes`,
# `us_ny_statutes`, `us_tx_statutes`, and `us_ca_statutes` real datasets.

# Wave-5 rewrite: a section number is now a CHAIN of "segments" (digits
# optionally followed by letters) joined by "." or "-", e.g. Delaware's
# `12D-102`/`4A-103`/`9002B` (letters, dash-continuation), Florida/Ohio's
# `941.34`/`4513.01` (dot-continuation), and Texas's `2A.103` (a letter
# segment continued by a DOT, a combination none of the earlier per-state
# fixtures exercised on their own). `_SEGMENT_RE` is the single repeated
# unit; the outer group repeats it for as many `.`/`-`-joined segments as
# are present, and a final optional bare `.` is the label-ending period
# (distinguished from a dot-continuation only by NOT being followed by a
# digit, which the greedy `(?:[.-]{_SEGMENT_RE})*` already consumes first).
# Every group is gated on a distinct leading token (digit run, letter run,
# a literal separator) with no alternation between them, so the engine
# never has more than one way to partition the string -- a single
# deterministic left-to-right scan, still unconditionally linear-time.
_SEGMENT_RE = r"\d+[A-Za-z]*"
_SECTION_NUMBER_TOKEN_RE = re.compile(rf"{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?")
_SECTION_LABEL_RE = re.compile(
    rf"Section\s+{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?", re.IGNORECASE
)
# Wave-5 addition: `re.IGNORECASE` on both -- Texas's real standard
# convention is ALL CAPS (`DEFINITIONS.`), Ohio's is lowercase mid-sentence
# (`...load definitions`); the DE/PA capital-D convention these were
# originally validated against is just one case variant among several real
# state drafting conventions, not the norm. Case-folding a fixed literal
# word is still a bounded, linear check (no new backtracking surface).
_FIRST_WORD_DEFINITIONS_RE = re.compile(r"Definitions?\b", re.IGNORECASE)
_LAST_WORD_DEFINITIONS_RE = re.compile(r"^Definitions?$", re.IGNORECASE)
# Wave-5 fix: allow ONE trailing `.` after the closing `]` -- real DE rows
# routinely have the section's own terminal period AFTER a trailing
# "[Effective ...]"/"[Transferred]"/"[For application ...]" annotation
# (`"...definitions [Effective May 22, 2026]."`), which the un-widened
# anchor (`\]\s*$`) never matched (the string doesn't end in `]`, it ends
# in `].`) -- silently leaving the bracket AND a bogus final token
# (`"2026]"` or similar) in the tail-token list, defeating the last-word
# rule even though "Definitions" genuinely is the heading's own subject
# once the annotation is disregarded. Still a single bounded scan.
_TRAILING_BRACKET_RE = re.compile(r"\s*\[[^\]]*\]\.?\s*$")

# Splits the tail of a heading into tokens on whitespace OR separator
# punctuation (hyphen, en dash, em dash, colon, semicolon, comma), so
# "Payment Order-Definitions" (no space around the hyphen) tokenizes the
# same as "Payment order â Definitions" (mojibake dash WITH surrounding
# spaces) -- single quantifier over a fixed character class, no
# alternation-nesting, unconditionally linear.
_TAIL_TOKEN_SPLIT_RE = re.compile(r"[\s\-–—:;,]+")

# Function words that, immediately before "Definitions", mark it as the
# grammatical OBJECT of the preceding word rather than this heading's own
# subject (e.g. "Repeal **of** Definitions"). Deliberately small and
# preposition-only -- an adjective, dash, colon, or foreign/mojibake token
# immediately before "Definitions" is treated as introducing/qualifying
# the subject, not governing it, and is therefore NOT excluded.
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

# Deliberately `[A-Za-z0-9]`, NOT `\w`/`.isalpha()`: the real scrape-noise
# mojibake characters (`Â`, `â`, ...) are Unicode *letters* by category
# (accented Latin), so a Unicode-aware "is this a letter" test stops the
# noise-skip too early and leaves the mojibake byte stuck in front of the
# section number. ASCII-only is also what real English statute text is
# expected to be once past the scrape-noise prefix. Single quantifier over
# a fixed negated character class -- no alternation, no nesting, so this
# is unconditionally linear-time.
_LEADING_NOISE_RE = re.compile(r"^[^A-Za-z0-9]+")


def _strip_leading_noise(s: str) -> str:
    """Skip a leading run of characters that are neither ASCII letters nor
    digits (scrape-noise mojibake, `§`, CR/LF, whitespace) -- a single
    bounded regex match, no backtracking possible (see `_LEADING_NOISE_RE`
    comment for why this is ASCII-only, not Unicode-`isalpha`)."""
    m = _LEADING_NOISE_RE.match(s)
    return s[m.end() :] if m else s


def is_definitions_heading(heading: str) -> bool:
    """True when `heading`'s own operative subject is "Definition(s)" --
    see the module-level comment above for the exact rule and its
    rationale. Every step is a bounded linear-time scan (no nested
    quantifier over an alternation anywhere in this function), so runtime
    is proportional to `len(heading)` regardless of input shape.
    """
    rest = _strip_leading_noise(heading)

    label_match = _SECTION_LABEL_RE.match(rest)
    if label_match:
        rest = rest[label_match.end() :]
    else:
        number_match = _SECTION_NUMBER_TOKEN_RE.match(rest)
        if number_match:
            rest = rest[number_match.end() :]

    rest = rest.lstrip()

    if _FIRST_WORD_DEFINITIONS_RE.match(rest):
        return True

    trimmed = _TRAILING_BRACKET_RE.sub("", rest)
    trimmed = trimmed.rstrip(" \t\r\n.")

    tokens = [t for t in _TAIL_TOKEN_SPLIT_RE.split(trimmed) if t]
    if not tokens or not _LAST_WORD_DEFINITIONS_RE.match(tokens[-1]):
        return False
    if len(tokens) == 1:
        return True  # unreachable in practice (rule 3 above already caught
        # a lone "Definitions" token), kept for defensiveness.
    preceding = tokens[-2]
    if preceding.lower() in _PRECEDING_EXCLUSION_WORDS:
        return False  # a preposition (e.g. "of") -- "Definitions" is a
        # grammatical object here, not this heading's own subject.
    return True


# --- G2 (continued): extracting defined terms out of a Definitions section --

# The real fixture uses CURLY quotes (“/”) around each defined
# term, not straight ASCII quotes -- both accepted here since a clean/
# synthetic input might reasonably use either.
_LEADING_QUOTE_RE = re.compile(r'^[“"]([^”"]+)[”"]')

# Wave-7 fix (QA cycle 4, item 3 -- "one term swallows three others"):
#
# A numbered-paragraph entry marker is NOT always a single digit in
# parens. The original rule (a bare `\(\d+\)` at the start of a line)
# matches DE's real fixture shape ("(1) ... (2) ... (3) ...") but real
# California drafting nests a top-level single-LETTER marker with a
# digit sub-marker immediately after it on the SAME line
# ("(d) (1) “Dispose” means ..."), and later top-level entries
# in that same section switch to a BARE letter marker with no digit at
# all ("(e) “Open-space purposes” means ..."). The digit-only
# rule never recognizes a letter-only line as a new entry, so once the
# last digit-marked sub-entry is opened, every following line -- no
# matter its own top-level marker -- was silently appended to that SAME
# block all the way to the end of the section: the real defect, a single
# 26,715-character "Dispose" block absorbing 3 other terms
# ("Open-space purposes", "Sectional planning area", "Sectional planning
# area document").
#
# Fix: an entry starts wherever a line, after stripping a leading CHAIN
# of one or more parenthesized marker tokens (each `\(\w+\)` -- digit,
# single letter, or roman numeral, however many chain together, e.g.
# "(d) (1)"), is immediately followed by a quoted term. This covers
# DE's plain "(1) "Term"..." shape (a one-token chain) AND CA's nested
# "(d) (1) "Term"..."/bare "(e) "Term"..." shapes (chains of 1 or more
# tokens) with the SAME rule, while a marker chain NOT immediately
# followed by a quote (an ordinary un-quoted sub-item, e.g. "(A) The
# sale of the surplus land.") never starts a spurious new entry on its
# own.
#
# A bare digit marker (`\(\d+\)`, e.g. "(2)", "(32)") is ADDITIONALLY
# always treated as an entry boundary even with no quote immediately
# after it -- this is the ORIGINAL rule, kept unconditionally: real
# sections routinely interleave several non-defining numbered
# paragraphs ("(b) For each fiscal year ...", "(d) (1) Except as
# otherwise provided ...") between one lettered defining entry and the
# next, with NO further quote for hundreds/thousands of characters: a
# quote-only rule would run the current block all the way to the next
# actual quoted term, re-inflating exactly the bloat this fix exists to
# remove. Keeping the original unconditional-digit boundary means a
# later bare "(N)" -- defining or not -- still closes out whatever
# block is currently open, bounding it the same way it always has for
# DE/TX's pure-digit convention, while the new quote-anchored chain
# rule additionally catches the letter-marked entries the original
# rule could never see at all.
#
# Each token in the chain is matched by its own single, bounded,
# non-nested quantifier (`\(\w+\)\s*`, no alternation inside it) -- the
# loop below just repeats that ONE match call token-by-token, so there
# is no nested quantifier over an alternation anywhere and no
# possibility of the earlier ReDoS shape (see the module-level comment
# on `is_definitions_heading`): stripping an N-token chain is exactly N
# bounded match calls, and there is no ambiguity in how a chain
# partitions into tokens (each one is delimited by literal parens), so
# there is nothing for the engine to backtrack over -- unconditionally
# linear in the length of `text`.
_MARKER_TOKEN_RE = re.compile(r"\(\w+\)\s*")
_BARE_DIGIT_MARKER_RE = re.compile(r"^\s*\(\d+\)\s*")


def _strip_marker_chain_before_quote(line: str) -> str | None:
    """If `line`, once a leading run of whitespace and parenthesized
    marker tokens is stripped, begins directly with a quoted term,
    return the remainder (marker chain removed) -- this line starts a
    new definition entry. Otherwise return `None`.
    """
    rest = line.lstrip()
    stripped_any = False
    while True:
        match = _MARKER_TOKEN_RE.match(rest)
        if match is None:
            break
        rest = rest[match.end() :]
        stripped_any = True
    if not stripped_any or not _LEADING_QUOTE_RE.match(rest):
        return None
    return rest


def _entry_start_remainder(line: str) -> str | None:
    """Return the remainder of `line` with its leading entry marker(s)
    stripped if `line` starts a new definition entry, else `None`. Tries
    the (quote-anchored) marker-chain rule first; falls back to the
    original unconditional bare-digit-marker rule so a later bare
    "(N)" still closes out an open block even with no quote right after
    it (see the rationale comment above `_MARKER_TOKEN_RE`).
    """
    chain_remainder = _strip_marker_chain_before_quote(line)
    if chain_remainder is not None:
        return chain_remainder
    digit_match = _BARE_DIGIT_MARKER_RE.match(line)
    if digit_match is not None:
        return line[digit_match.end() :]
    return None


def _split_into_numbered_blocks(text: str) -> list[str]:
    lines = text.split("\n")
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        new_entry_start = _entry_start_remainder(line)
        if new_entry_start is not None:
            if current is not None:
                blocks.append(current)
            current = [new_entry_start]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)
    return ["\n".join(b).strip() for b in blocks]


# --- Moved from pipeline.py verbatim (sprint 2026-08-04-defs-core-scope,
# gate C3 -- pipeline.py retains no jurisdiction-specific literals), wave 6
# (sprint 2026-08-02-us-state-law, ruling R12): placeholder-heading
# jurisdictions (California, Illinois, Georgia) -----------------------------
#
# For these three states `Article.heading` (sourced from the dataset's
# `section_title` column) is a bare placeholder that carries NO real
# heading text at all -- real examples:
#
#   Illinois:   "Section 15"
#   California: "Section 22970.21"
#   Georgia:    "Georgia Code Title 45. Public Officers and Employees
#                 § 45-2-20"    (a reconstructed citation breadcrumb --
#                 "Public Officers and Employees" is the TITLE's name,
#                 repeated verbatim across every section under that
#                 title, not this section's own heading)
#
# The genuine heading, when one exists, lives at the START of the
# article's own body text instead -- real Illinois shape:
#
#   "(325 ILCS 7/15) (Section scheduled to be repealed on January 1,
#    2027) Sec. 15. Definitions. As used in this Act: \"Bias-free\"
#    means ..."
#
# `_is_placeholder_heading` recognizes ONLY the bare-placeholder shape
# itself (never a genuine, even terse, heading like DE's "Employer Match
# Plan" or FL's "941.34 Definition of “state.”" -- both carry
# real words of their own and never match either pattern below), so the
# body-derivation fallback below can NEVER fire for a heading that
# already means something -- it is only ever attempted after the
# ordinary `is_definitions_heading(heading)` check has already returned
# False AND the heading itself is proven to carry no information. This is
# what keeps the 7 states already working off `section_title` (DE/NY/TX/
# FL/OH/PA/WA, 0.5-10.3% miss, 0 false positives) byte-for-byte unaffected
# (verified against all 4 real files' full section_title columns, not
# merely asserted).
_BARE_SECTION_LABEL_RE = re.compile(r"^Section\s+\d[\w.\-]*\.?$", re.IGNORECASE)
_BARE_CITATION_LABEL_RE = re.compile(
    r"^.+\bCode Title\s+\d+[A-Za-z]?\.\s+.+§\s*[\w.\-]+\.?$", re.IGNORECASE
)


def _is_placeholder_heading(heading: str) -> bool:
    """True when `heading` carries no real descriptive text of its own --
    either a bare `"Section 15"` / `"Section 22970.21"` label (real
    Illinois/California shape -- the token right after "Section" must
    start with a digit, so a genuine heading that merely happens to start
    with the word "Section", e.g. a real NY row's `"Section Captions"`,
    is never mistaken for a placeholder), or a reconstructed
    `"<Jurisdiction> Code Title <N>. <Title name> § <section>"` citation
    breadcrumb (real Georgia shape). Both regexes are anchored/bounded
    with no nested quantifier over an alternation, so this stays a single
    linear-time scan of `heading` regardless of input shape.
    """
    if not heading:
        return False
    return bool(_BARE_SECTION_LABEL_RE.match(heading) or _BARE_CITATION_LABEL_RE.match(heading))


# Bounds how far into the body `_derive_heading_from_body` looks -- a
# fixed, small window keeps this a bounded-cost scan regardless of how
# long the article's full body text is (the body of a real US statute
# section can run to several KB).
_BODY_HEADING_SEARCH_WINDOW = 400

# Real Illinois/scrape-noise bodies open with one or more parenthetical
# asides before the genuine "Sec. N. Heading." sentence -- e.g.
# "(325 ILCS 7/15) (Section scheduled to be repealed on January 1, 2027)
#  Sec. 15. Definitions. ...". A single quantifier over a fixed,
# non-nested group (bounded to 4 repeats, each aside capped at 200 chars)
# -- no alternation-in-nested-quantifier, so no backtracking blowup.
_LEADING_PARENTHETICAL_RE = re.compile(r"^\s*(?:\([^()]{0,200}\)\s*){0,4}")

# The genuine embedded heading convention (Illinois): "Sec[tion] <N>.
# Definitions[.]" -- matched only immediately after the leading-
# parenthetical noise at the very START of the body (via `.match(window,
# pos)`, not `.search`), so a MID-body reference to some OTHER section's
# definitions ("...as required by Sec. 10. Definitions...") is never
# mistaken for this article's own heading.
_BODY_EMBEDDED_HEADING_RE = re.compile(
    r"Sec(?:tion)?\.?\s+[\w.\-]+\.\s*Definitions?\b\.?",
    re.IGNORECASE,
)

# The definitions-PREAMBLE convention (California/Georgia real shape --
# these two states have no embedded "Sec. N. Heading." sentence at all;
# the body opens directly with the substantive preamble), e.g. real:
#   "Unless the context otherwise requires, the definitions in this
#    article govern the construction of this chapter."
#   "For purposes of this chapter, the following definitions apply: ..."
# Bounded, non-greedy quantifiers (`.{0,80}?`, `.{0,120}?`) cap the total
# scan cost at a small constant regardless of body length -- no unbounded
# `.*`, so no catastrophic-backtracking surface. The lookahead requires
# "definition(s)" to be followed, within a short bounded gap, by a verb
# that only shows up in a genuine "these ARE the definitions for this
# text" preamble (appl(y/ies/ied), govern, shall apply) -- a passing
# mention like "...meets the definition of a licensee..." (no such verb
# nearby) correctly does NOT match. The captured span ends at
# "definition(s)" itself (not the verb), so the returned string's own
# LAST word is "Definitions" -- exactly what `is_definitions_heading`'s
# last-word rule checks.
_BODY_DEFINITIONS_PREAMBLE_RE = re.compile(
    r"^.{0,80}?\bDefinitions?\b(?=.{0,120}?\b(?:appl(?:y|ies|ied)|govern|shall\s+apply)\b)",
    re.IGNORECASE | re.DOTALL,
)


def _derive_heading_from_body(body: str) -> str | None:
    """Derive the article's real heading from the START of `body`, for a
    jurisdiction whose `section_title` is a bare placeholder (wave 6,
    ruling R12).

    Tries, in order:

    1. The Illinois embedded-heading convention -- real:
       `"(325 ILCS 7/15) (Section scheduled to be repealed on January 1,
        2027) Sec. 15. Definitions."` -> returns everything through
       "Definitions." (this substring, fed to `is_definitions_heading`,
       matches via its last-word rule regardless of the messy prefix,
       since only the token immediately before "Definitions" is checked
       against a small preposition list).
    2. The California/Georgia definitions-preamble convention -- real:
       `"Unless the context otherwise requires, the definitions"` (from
       "...the definitions in this article govern the construction of
       this chapter.") or `"For purposes of this chapter, the following
       definitions"` (from "...the following definitions apply: ...").

    Returns `None` when neither convention is found in the leading
    `_BODY_HEADING_SEARCH_WINDOW` characters of `body` -- e.g. an ordinary
    (non-definitions) placeholder-headed section never derives a
    heading, so it falls through to the ordinary local/adhoc fallback an
    ordinary non-definitions article always has.
    """
    window = body[:_BODY_HEADING_SEARCH_WINDOW]

    noise_match = _LEADING_PARENTHETICAL_RE.match(window)
    embedded_match = _BODY_EMBEDDED_HEADING_RE.match(window, noise_match.end())
    if embedded_match is not None:
        return window[: embedded_match.end()]

    preamble_match = _BODY_DEFINITIONS_PREAMBLE_RE.match(window)
    if preamble_match is not None:
        return window[: preamble_match.end()]

    return None


def derive_heading_from_body(heading: str, body: str) -> str | None:
    """`JurisdictionProfile.derive_heading_from_body` for US -- combines
    the placeholder-heading gate (`_is_placeholder_heading`) with the
    body-scan (`_derive_heading_from_body`): only ATTEMPTS to derive a
    heading from body text when `heading` is proven to carry no
    information of its own, exactly today's pipeline.py ordering (C3:
    this behavior moved here verbatim, nothing about it changed)."""
    if not _is_placeholder_heading(heading):
        return None
    return _derive_heading_from_body(body)


# A quoted defined term (straight or curly double quotes), real US
# statutory drafting shape for CA/IL/GA's placeholder-heading bodies --
# these have NO "(N)"-numbered-paragraph structure at all (unlike DE's
# fixture shape, which `extract_definitions_from_section` already
# handles), just an inline run of `"Term" means ...` sentences, e.g. real
# Illinois:
#   "... As used in this Act: \"Bias-free\" means to review a case file
#    ... \"BIPOC\" means people who are members of ..."
# Bounded to 200 chars per term so a single unterminated quote can't force
# an unbounded scan.
_QUOTE_TERM_RE = re.compile(r'["“]([^"”]{1,200})["”]')

# Whether a quoted span is a genuine defined-TERM marker (as opposed to a
# quoted phrase appearing somewhere INSIDE another entry's own definition
# text) -- checked by looking for a "means"/"shall mean"/"has the
# meaning" idiom within a bounded gap after the closing quote, with NO
# other quote character in between (so a later quoted phrase belonging to
# the CURRENT entry's own definition text is never mistaken for the next
# entry's term). Real Illinois shape has both the immediate case
# (`"BIPOC" means ...`) and a delayed case with an intervening clause
# (`"Immediate and urgent necessity", in accordance with Section 5 ...,
#  means (i) ...`) -- the bounded, non-greedy `{0,200}?` gap covers both
# without unbounded backtracking.
_MEANS_IDIOM_GAP_RE = re.compile(
    r'^[^"“”]{0,200}?\b(?:means|shall mean|has the meaning)\b:?\s*',
    re.IGNORECASE,
)


def _extract_inline_quoted_definitions(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Extract `(term, definition)` pairs from a placeholder-heading
    jurisdiction's Definitions-section body composed of inline `"Term"
    means ...` sentences with NO numbered-paragraph markers -- the real
    Illinois/California/Georgia shape that `extract_definitions_from_
    section`'s `"(N)"`-block splitter cannot parse (there are no `"(N)"`
    markers to split on at all).

    Only used as a FALLBACK, after the `"(N)"`-block splitter has already
    been tried and returned nothing for this body, AND only when
    `heading_was_derived=True` -- some real CA/GA sections DO use a
    numbered-paragraph structure the block splitter already handles; this
    only covers the remaining inline-sentence shape, and only for
    articles reached via `derive_heading_from_body` (never for the 7
    states already working off their own `section_title`, so this is
    zero-risk for them).

    A quoted span only starts a new entry when it is followed (within a
    bounded gap, no intervening quote) by a defining idiom
    (`_MEANS_IDIOM_GAP_RE`) -- a quoted phrase inside another entry's own
    definition prose is correctly left alone. Each entry runs from its own
    term through to the START of the next recognized entry (or end of
    text).
    """
    entries: list[tuple[str, int, int]] = []
    for term_match in _QUOTE_TERM_RE.finditer(text):
        gap = text[term_match.end() : term_match.end() + 200]
        means_match = _MEANS_IDIOM_GAP_RE.match(gap)
        if means_match is None:
            continue
        term = term_match.group(1).strip()
        if not term:
            continue
        entries.append((term, term_match.start(), term_match.end() + means_match.end()))

    candidates: list[DefinitionCandidate] = []
    for index, (term, start, definition_start) in enumerate(entries):
        end = entries[index + 1][1] if index + 1 < len(entries) else len(text)
        definition_text = text[definition_start:end].strip()
        if not definition_text:
            continue
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
        )
    return candidates


def _leading_quote_candidate(block: str, *, scope: str) -> DefinitionCandidate | None:
    """One numbered/quote-anchored block -> a `DefinitionCandidate`, or
    `None` if the block has no leading quoted term (not a recognizable
    defined-term entry). Factored out so `USProfile.extract_definitions_
    from_section` (sprint 2026-08-04-defs-core-dispatch, item I3) can apply
    the SAME per-block parsing rule to blocks contributed by a registered
    `EntrySplitterRule`, not just baseline's own numbered blocks."""
    term_match = _LEADING_QUOTE_RE.match(block)
    if not term_match:
        return None
    term = term_match.group(1)
    definition_text = block[term_match.end() :].strip()
    return DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)


def extract_definitions_from_section(
    text: str, *, scope: str, heading_was_derived: bool = False
) -> list[DefinitionCandidate]:
    """Extract every (term, definition) pair from a located Definitions
    section's body composed of `(N) "Term" ...` numbered entries (the real
    DE fixture's shape).

    Each entry's leading quoted span is the defined term; the remainder of
    the entry (after the closing quote) is the definition text. Entries
    with no leading quoted term are skipped (not a recognizable defined-
    term entry).

    `heading_was_derived` (sprint 2026-08-04-defs-core-scope, seam spec
    Seam 1 -- defaulted, existing call sites/tests unaffected): when the
    `"(N)"`-block splitter above finds NOTHING and this section's heading
    was itself derived from body text (`derive_heading_from_body`, wave 6
    CA/IL[state]/GA shape), falls back to the inline-quoted-sentence
    extractor (`_extract_inline_quoted_definitions`) -- preserves the
    exact "zero-risk for the 7 already-working states" guarantee, since
    `heading_was_derived` is always False for them.

    Baseline-only: this bare function never consults the rule registry --
    `USProfile.extract_definitions_from_section` (the profile method) is
    the one that additionally unions in registered `EntrySplitterRule`/
    `TermClauseRule` output (sprint 2026-08-04-defs-core-dispatch, item
    I3), matching every existing direct caller/test of this function.
    """
    candidates: list[DefinitionCandidate] = []
    for block in _split_into_numbered_blocks(text):
        candidate = _leading_quote_candidate(block, scope=scope)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates and heading_was_derived:
        candidates = _extract_inline_quoted_definitions(text, scope=scope)
    return candidates


# --- G3: English word-boundary term matching --------------------------------

# Sprint 2026-08-04-defs-core-scope, QA-fail cycle 2, item I10, director
# ruling D-CF: structural-context guard on the M8(b)/I6 case-fold fix ------
#
# The defect D-CF names: a statute defines a term that happens to BE one of
# English legal drafting's own structural/navigation nouns (a real, common
# shape -- e.g. a statute defining "Division" as an agency name). Once
# `find_term_uses` case-folds (M8(b)), every ORDINARY structural cross-
# reference of the form "...pursuant to this division (i)..." /
# "...Part (a) shall..." / "...under Title 1 of..." also matches as a USE
# of that defined term -- it is not one; it is the drafter navigating to
# another part of the same body of law, using the same word that happens to
# also be defined elsewhere. D-CF's ruling: case-folding stays (I6 is not
# reverted), but a match sitting inside exactly this shape -- a STRUCTURAL
# UNIT WORD immediately followed by a NUMBERING token -- is suppressed.
#
# `_STRUCTURAL_UNIT_WORDS` is the closed, small set of nouns that name a
# structural division of a US statute (the same vocabulary
# `resolve_unit_path`'s own citation ladder navigates), measured directly
# against the real corpus before this guard was written (P-R7-compliant
# denominator -- population built from definition idioms in the prose,
# never from this code's own trigger regexes): of 106,275 rows containing a
# quoted-term definition idiom, exactly 1,157 (1.09%) define one of these
# words as a term at all, "division" alone accounting for 932 of them (81%)
# -- so this guard can only ever fire on a small, known-bounded slice of
# real definition-bearing rows, never on an arbitrary defined term like
# "Access area" or "Affiliate".
#
# Design point (deliberately made explicit here, not left implicit -- flag
# raised upward per the sprint QA process, this is the documented decision
# taken): the guard below is CONTEXT-based, not CASE-based. It suppresses a
# structural-reference match regardless of the matched text's own case --
# including an EXACT-CASE match, e.g. "Part (a)" with a capital P against a
# defined term "Part". That match pre-dates I6/M8(b) entirely (case-folding
# is irrelevant to it) and would keep matching even if M8(b) were fully
# reverted. This is broader than D-CF's literal phrasing ("a case-fold
# match is SUPPRESSED where the hit sits inside a structural-reference
# pattern"), which read narrowly could be limited to matches that ONLY
# exist because of the case-fold. The context-based reading is taken
# instead because it is the semantically correct one: "Part (a) shall be
# at the rate..." is a structural cross-reference whether or not "Part" is
# capitalized -- the drafter is pointing at a subdivision of the section,
# not using a defined term, and that fact does not depend on case. Given
# the measured blast radius above (~1.1% of definition-bearing rows can
# ever be touched at all, and the dominant "division" case is lowercase in
# its structural form anyway, so the case question does not even arise for
# 81% of the affected population), reading D-CF context-based costs
# essentially nothing beyond the literal reading while closing a gap the
# literal reading would otherwise leave open.
_STRUCTURAL_UNIT_WORDS = frozenset(
    {
        "division",
        "subdivision",
        "article",
        "part",
        "section",
        "title",
        "chapter",
        "paragraph",
        "subsection",
        "subchapter",
    }
)

# The "numbering token" half of the structural-reference shape -- matched
# immediately (whitespace only in between) after a structural unit word:
#
#   - a parenthesized marker shaped like a genuine sub-article numbering
#     token -- a digit run ("(1)"), a single or double letter of either
#     case ("(a)", "(b)", "(aa)"), or a run of roman-numeral characters
#     ("(i)", "(ii)"), mirroring the same marker shapes
#     `resolve_unit_path`'s own ladder recognizes below (kept as an
#     independent, local regex rather than calling into that function --
#     deliberately no coupling between the two features, so a future
#     change to the unit-path ladder can never silently change this
#     guard's behavior or vice versa); or
#   - a BARE number with no parens at all ("Title 1", D-CF's own third
#     named example shape).
#
# Both alternatives are single, non-nested quantifiers over fixed
# character classes -- no alternation-in-nested-quantifier, so this is
# unconditionally linear-time, same discipline as every other regex in
# this module.
_STRUCTURAL_NUMBERING_TOKEN_RE = re.compile(
    r"\s+(?:\((?:\d+|[A-Za-z]{1,2}|[ivxlcdmIVXLCDM]{1,7})\)|\d+)"
)


def _is_structural_reference(term: str, text: str, match_end: int) -> bool:
    """D-CF guard: True when the case-fold match of `term` in `text` ending
    at `match_end` sits inside a structural-reference pattern -- `term`
    itself is one of `_STRUCTURAL_UNIT_WORDS`, immediately followed by a
    numbering token (see `_STRUCTURAL_NUMBERING_TOKEN_RE`). Deliberately
    scoped to the exact term matched, not any word anywhere near it: an
    unrelated defined term (e.g. "Access area") is never eligible for
    suppression no matter what follows it in the text, since it is never a
    member of the closed unit-word set to begin with.
    """
    if term.strip().lower() not in _STRUCTURAL_UNIT_WORDS:
        return False
    return bool(_STRUCTURAL_NUMBERING_TOKEN_RE.match(text, match_end))


def find_term_uses(term: str, text: str) -> list[re.Match[str]]:
    """Every non-overlapping occurrence of the literal `term` in `text`,
    using ordinary `\\b`-word-boundary matching -- NO Hebrew-style prefix-
    letter surface-form expansion. A defined term never false-matches as a
    substring of a longer word (`\\b` handles this natively: e.g. `term=
    "Affiliate"` will not match inside `"Affiliates"` or `"disaffiliated"`,
    since there is no word-boundary at that position).

    Case-insensitive (sprint 2026-08-04-defs-core-scope, manager ruling
    M8(b)): real US rows re-mention a capitalized defined term in lowercase
    later in the same law (e.g. "Access area" defined, later used as
    "access area" in running text), and today's exact-case matching misses
    that mention entirely. The fix is narrowly scoped to case-folding the
    literal term ONLY -- `\\b`-word-boundary anchoring is unchanged, so this
    stays a case-insensitive EXACT match, never a fuzzy/substring one.

    Structural-context guard (sprint 2026-08-04-defs-core-scope, director
    ruling D-CF, QA-fail cycle 2 item I10): a match is additionally
    suppressed when it sits inside a structural cross-reference -- a unit
    word (`_STRUCTURAL_UNIT_WORDS`) immediately followed by a numbering
    token, e.g. "division (ii)", "Part (a)", "Title 1". See the module
    comment above `_STRUCTURAL_UNIT_WORDS` for the defect this closes, the
    measured blast radius, and why the guard is context-based (fires
    regardless of the match's own case) rather than limited to matches that
    exist only because of the case-fold.
    """
    pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    return [
        m for m in pattern.finditer(text) if not _is_structural_reference(term, text, m.end())
    ]


# Sprint 2026-08-04-defs-core-scope, item I9 (ruling M15, program-manager
# option 1): real-Unicode curly-quote variants (U+201C LEFT / U+201D RIGHT
# DOUBLE QUOTATION MARK) collapsed to a plain ASCII `"` -- deliberate US
# normalization, not the Hebrew engine's full Stage 0 (no NFC, no niqqud
# stripping, no dash-variant collapsing; see the module docstring). Restores,
# through the profile layer instead of as a side effect of dead dispatch,
# the sprint-2026-08-02-us-state-law QA cycle-4 fix for a real CA row whose
# defined term uses the SAME left-curly-quote character on both sides
# ("Adjustment factor" means ...) -- collapsing both to `"` makes the pair
# consistent again for `_LEADING_QUOTE_RE`/`_QUOTE_TERM_RE` below. Matches
# ONLY the two genuine Unicode codepoints, never a mojibake byte sequence
# that merely LOOKS similar after a mis-decode (e.g. UTF-8 curly-quote bytes
# read back as latin-1) -- that is a different defect family (recon dossier
# family 3, AK's cp1252 mojibake), left for a jurisdiction-specific
# `normalize_for_parsing` override to repair, exactly the dispatch seam I9
# exists to make reachable.
_CURLY_QUOTE_VARIANTS_RE = re.compile("[“”]")


def normalize_for_parsing(text: str) -> str:
    """Collapse real-Unicode curly-quote variants to a plain ASCII `"` --
    see `_CURLY_QUOTE_VARIANTS_RE` above for exactly what this does and
    does not touch. Otherwise a no-op: no wikilink-bracket stripping, no
    RTL-bidi handling, no NFC normalization -- those stay Hebrew-engine-only
    concerns this profile has no use for."""
    return _CURLY_QUOTE_VARIANTS_RE.sub('"', text)


# --- G4: US citation grammar -------------------------------------------------

# Most specific first: a full `N U.S.C. § N(...)` federal citation, so its
# "§ N" portion is claimed before the bare `§ N` pattern below can grab it.
_USC_CITATION_RE = re.compile(r"\d+\s+U\.S\.C\.\s+§\s*\d+(?:\([^\s()]+\))*")

# `Section N` (spelled out). Sprint 2026-08-04-defs-core-scope, manager
# ruling M12, verified defect (ii): a DECIMAL section number (real TX/OR
# shape, e.g. "Section 552.003") must not truncate at the decimal point --
# `(?:\.\d+)*` extends the match through every `.digit` continuation, so
# "Section 552.003" resolves whole rather than to the WRONG, different,
# real section "Section 552". Purely additive: a plain integer section
# number (no decimal) matches exactly as before (`(?:\.\d+)*` matches
# zero times).
_SECTION_WORD_RE = re.compile(r"\bSection\s+\d+(?:\.\d+)*\b")

# Bare `§ N` (optionally followed by parenthetical subdivisions).
_SECTION_SYMBOL_RE = re.compile(r"§\s*\d+(?:\([^\s()]+\))*")

# Sprint 2026-08-04-defs-core-scope, manager ruling M12, verified defect
# (i): a generic `<CODE> <n>.<n>` state-code citation shape (covers
# Oregon's "ORS 153.005" and similarly-shaped codes) -- invisible to
# baseline before this fix. `[A-Z]{2,6}` is an ALL-CAPS code abbreviation
# (never matches a mixed-case word like "Section"), followed by a
# decimal-dotted number. A genuinely idiosyncratic state citation grammar
# this can't generalize to is still reachable via a registered
# `CitationRule` (v2.3 M12) -- this is baseline coverage only.
_STATE_CODE_CITATION_RE = re.compile(r"\b[A-Z]{2,6}\s+\d+(?:\.\d+)+\b")

# Tried in priority order; a later pattern's match is discarded if it
# overlaps a span already claimed by an earlier (more specific) pattern.
_CITATION_PATTERNS = (_USC_CITATION_RE, _SECTION_WORD_RE, _SECTION_SYMBOL_RE, _STATE_CODE_CITATION_RE)


def _find_citations_with_positions(text: str) -> list[tuple[int, int, str]]:
    """Every citation-shaped span baseline recognizes: `(start, end,
    matched_text)`, in priority order, non-overlapping (a later, lower-
    priority pattern's match is discarded if it overlaps a span an
    earlier pattern already claimed). Factored out of `find_citations` so
    `USProfile.find_citations` (v2.3 M12 -- rule-extensible) can union in
    registered `CitationRule` output using the SAME overlap-claiming
    discipline, without re-deriving baseline's own claimed spans."""
    claimed: list[tuple[int, int]] = []
    found: list[tuple[int, int, str]] = []
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            if any(not (end <= s or e <= start) for s, e in claimed):
                continue
            claimed.append((start, end))
            found.append((start, end, match.group(0)))
    return found


def find_citations(text: str) -> list[str]:
    """Every citation-shaped substring in `text`: `Section N` (including
    decimal-numbered), `§ N`, `N U.S.C. § N` federal citations, and a
    generic `<CODE> <n>.<n>` state-code shape. Returned in the order they
    appear in `text`. Baseline only -- `USProfile.find_citations` (the
    profile method) additionally unions in any registered `CitationRule`s
    for its own jurisdiction code (v2.3 M12); this bare function stays
    baseline-only, matching every existing direct caller/test.
    """
    found = _find_citations_with_positions(text)
    found.sort(key=lambda item: item[0])
    return [matched for _, _, matched in found]


# English defining idioms that introduce a cross-law derivation (the real
# fixture text uses the first form, not "means"). Sprint
# 2026-08-04-defs-core-scope, seam spec v2.3, the THIRD M12 defect: the
# three real idioms below (OR "Enforcement officer" / TX "Governmental
# body" singular and plural shared-parent-clause forms) were entirely
# invisible to `detect_cross_law_derivations` -- not merely mis-parsed,
# not detected at all -- until this addition. Longest-first (via the sort
# below) so a suffixed/longer idiom is preferred if both could match at a
# position.
_TRIGGER_PHRASES = (
    "has the meaning specified in",
    "as defined in",
    "has the meaning given that term in",
    "has the meaning assigned by",
    "have the meanings assigned by",
)
_TRIGGER_RE = re.compile(
    "|".join(re.escape(p) for p in sorted(_TRIGGER_PHRASES, key=len, reverse=True)),
    re.IGNORECASE,
)

# A same-document/same-chapter internal reference immediately following the
# matched citation (mirrors Hebrew derivation.py's `_BESAIF_RE` same-law
# exclusion philosophy) -- excluded from cross-law derivations.
_SAME_LAW_RE = re.compile(
    r"^\s*of this (chapter|title|subchapter|part|section|act)\b", re.IGNORECASE
)

_LEADING_WS_RE = re.compile(r"^\s*")

# Sprint 2026-08-04-defs-core-scope, seam spec v2.1 §4 (pointer
# definitions, internal same-law targets): pulls the bare citation NUMBER
# (e.g. "5" out of "Section 5", "552.003" out of "Section 552.003") out of
# a matched citation string, so a whole-definition internal pointer can
# carry the target ARTICLE NUMBER forward for `pipeline.py`'s Stage 4 to
# resolve into a real same-document Article row.
_CITATION_NUMBER_RE = re.compile(r"\d+(?:\.\d+)*")


def _citation_number(citation_text: str) -> str | None:
    match = _CITATION_NUMBER_RE.search(citation_text)
    return match.group(0) if match else None


def detect_cross_law_derivations(
    text: str, *, source_term: str, known_law_titles: dict[str, str] | None = None
) -> list[LawDerivesDefinitionEdge]:
    """Scan `text` for `_TRIGGER_PHRASES` occurrences immediately followed
    by a recognizable citation (`find_citations`' grammar). A same-
    document/same-chapter reference (`"...of this chapter"` etc.
    immediately after the citation) is Stage-3/mention territory, not an
    ordinary cross-law derivation -- EXCEPT (seam spec v2.1 §4) when the
    trigger+citation+same-law-reference match consumes the candidate's
    ENTIRE `text` (a "whole-definition pointer", not an incidental
    same-law aside inside a longer substantive definition): that case
    redirects to an internal-target edge (`.internal_article_number` set)
    instead of being silently dropped -- `pipeline.py` resolves it into an
    Article-targeted `DERIVES_FROM_LAW` edge. An ordinary substantive
    definition that merely MENTIONS a same-law section in passing (leading
    or trailing prose beyond the trigger+citation+reference) is completely
    unaffected -- still excluded, exactly as before.

    `known_law_titles` is accepted for Protocol-shape parity with the
    Hebrew engine; US citations resolve to a `target_law_id` only via an
    exact key match, same "never a fabricated guess" discipline as
    `derivation.py` (ruling M5, ported): an unresolved reference is still
    emitted, with `target_law_id=None`.
    """
    known = known_law_titles or {}
    edges: list[LawDerivesDefinitionEdge] = []

    for trigger_match in _TRIGGER_RE.finditer(text):
        trigger = trigger_match.group(0)
        rest = text[trigger_match.end() :]
        ws_end = _LEADING_WS_RE.match(rest).end()
        rest = rest[ws_end:]

        citation_match = None
        for pattern in _CITATION_PATTERNS:
            citation_match = pattern.match(rest)
            if citation_match:
                break
        if citation_match is None:
            continue  # trigger not followed by a recognizable citation

        after_citation = rest[citation_match.end() :]
        matched_text = citation_match.group(0)
        same_law_match = _SAME_LAW_RE.match(after_citation)
        if same_law_match:
            consumed_end = (
                trigger_match.end() + ws_end + citation_match.end() + same_law_match.end()
            )
            leading_text = text[: trigger_match.start()].strip()
            trailing_text = text[consumed_end:].strip(" .")
            if not leading_text and not trailing_text:
                article_number = _citation_number(matched_text)
                if article_number is not None:
                    edges.append(
                        LawDerivesDefinitionEdge(
                            source_term=source_term,
                            trigger_phrase=trigger,
                            matched_text=matched_text,
                            target_law_name=None,
                            target_law_id=None,
                            internal_article_number=article_number,
                        )
                    )
            continue  # same-document/same-chapter reference -- never cross-law

        edges.append(
            LawDerivesDefinitionEdge(
                source_term=source_term,
                trigger_phrase=trigger,
                matched_text=matched_text,
                target_law_name=None,
                target_law_id=known.get(matched_text),
            )
        )

    return edges


# --- Sprint 2026-08-04-defs-core-scope, seam spec Seam 1 (C2, C3) ----------
#
# `determine_scope`: replaces the free function `pipeline._determine_scope`
# for the US side -- same 2-way contract (`"chapter"` / `"law-wide"`),
# reached through the profile instead of pipeline.py's own literal tuple
# (which was Hebrew-only anyway). Used ONLY for the Definitions-SECTION
# path (a whole section's default scope) -- a rule never sees/calls this.
_US_CHAPTER_SCOPE_TRIGGERS = (
    "for purposes of this chapter",
    "in this chapter",
    "for purposes of this part",
    "in this part",
)


def determine_scope(body_text: str) -> str:
    first_line = next((ln for ln in body_text.splitlines() if ln.strip()), "")
    lowered = first_line.lower()
    if any(trigger in lowered for trigger in _US_CHAPTER_SCOPE_TRIGGERS):
        return "chapter"
    return "law-wide"


# --- Sprint 2026-08-04-defs-core-scope, seam spec v2.2/v2.4 -- `resolve_
# unit_path`: the sub-article marker-sequence retrieval seam. Adapts this
# module's own `_MARKER_TOKEN_RE` chain-parsing philosophy (bounded,
# non-nested-quantifier, one token at a time) to a STACK of currently-open
# markers, classified against the real federal citation ladder (dossier-
# confirmed, v2.4 §3): lower-alpha > digit > upper-alpha > lower-roman >
# upper-roman > double-lower-alpha > double-upper-alpha, e.g.
# (a) > (1) > (A) > (i) > (I) > (aa) > (AA) -- 7 sub-article levels, no
# hard-coded cap at 2 or 3. A marker matching an ALREADY-open ancestor
# level's shape pops back to (and replaces) that level (a sibling, not a
# deeper nesting); a marker matching neither the next expected rung nor
# any open ancestor still pushes (as a generic "sub" step) rather than
# being silently dropped -- genuinely unbounded depth, never a cap. -----

_US_UNIT_MARKER_RE = re.compile(r"\(([A-Za-z]+|\d+)\)")
_LOWER_ROMAN_CHARS_RE = re.compile(r"^[ivxlcdm]+$")
_UPPER_ROMAN_CHARS_RE = re.compile(r"^[IVXLCDM]+$")
_UNIT_PATH_LADDER = (
    "lower_alpha",
    "digit",
    "upper_alpha",
    "lower_roman",
    "upper_roman",
    "double_lower_alpha",
    "double_upper_alpha",
)


def _marker_matches_kind(token: str, kind: str) -> bool:
    if kind == "digit":
        return token.isdigit()
    if kind == "lower_alpha":
        return len(token) == 1 and token.islower()
    if kind == "upper_alpha":
        return len(token) == 1 and token.isupper()
    if kind == "lower_roman":
        return bool(_LOWER_ROMAN_CHARS_RE.match(token))
    if kind == "upper_roman":
        return bool(_UPPER_ROMAN_CHARS_RE.match(token))
    if kind == "double_lower_alpha":
        return len(token) == 2 and token.isalpha() and token.islower()
    if kind == "double_upper_alpha":
        return len(token) == 2 and token.isalpha() and token.isupper()
    return False


def resolve_unit_path(article, char_offset: int | None = None):
    """`JurisdictionProfile.resolve_unit_path` for US -- see the module
    comment above. `char_offset=None` returns `()` (the article's own
    base path -- v2.4 correction: `UnitPath` is BELOW-article only, never
    chapter/part information, which callers read off the article's own
    metadata fields instead)."""
    from app.definition_links.rules.registry import UnitStep

    if char_offset is None:
        return ()

    stack: list = []
    for match in _US_UNIT_MARKER_RE.finditer(article.body):
        if match.end() > char_offset:
            break
        token = match.group(1)
        expected_kind = _UNIT_PATH_LADDER[len(stack)] if len(stack) < len(_UNIT_PATH_LADDER) else None
        if expected_kind is not None and _marker_matches_kind(token, expected_kind):
            stack.append(UnitStep(kind=expected_kind, value=token))
            continue
        replaced = False
        for i, step in enumerate(stack):
            if _marker_matches_kind(token, step.kind):
                stack = stack[: i + 1]
                stack[i] = UnitStep(kind=step.kind, value=token)
                replaced = True
                break
        if not replaced:
            stack.append(UnitStep(kind="sub", value=token))
    return tuple(stack)


@dataclass(frozen=True)
class USProfile:
    """The `"US-*"`/`"US-FED"` profile family -- ONE instance serves every
    US jurisdiction code (see module docstring for the per-state-vs-single
    decision). `.code` is set per-registration in `profiles.py`, not fixed
    here, since the same behavior applies under every US code.
    """

    code: str

    # Sprint 2026-08-04-defs-core-scope, seam spec v2.4 §4 -- taken
    # verbatim from the research dossier's §1 table: the FORMAL main unit
    # is Section for every US code including federal (deep sub-article
    # paths are still fully addressable via `resolve_unit_path`; they
    # just aren't the DECLARED default).
    main_unit_kind: str = "local"

    def is_definitions_heading(self, heading: str, body: str = "") -> bool:
        """Baseline (the bare `is_definitions_heading` function above,
        unchanged) first -- a baseline positive is never overridden. Only
        when baseline returns False are registered `HeadingRule`s for this
        profile's own code tried, first-positive-wins (sprint
        2026-08-04-defs-core-dispatch, item I1); a rule's optional
        `body_confirms` (I6) additionally gates its own match on `body`."""
        from app.definition_links.rules import registry

        if is_definitions_heading(heading):
            return True
        for rule in registry.heading_rules_for(self.code):
            if rule.matches(heading) and (rule.body_confirms is None or rule.body_confirms(body)):
                return True
        return False

    def normalize_for_parsing(self, text: str) -> str:
        return normalize_for_parsing(text)

    def find_term_uses(self, term: str, text: str) -> list[re.Match[str]]:
        return find_term_uses(term, text)

    def find_citations(self, text: str) -> list[str]:
        """Baseline first, then (v2.3 M12) union in every registered
        `CitationRule` for this profile's own code -- a rule's match
        overlapping an already-claimed span is discarded, not double-
        counted, the same overlap discipline baseline already applies
        internally."""
        from app.definition_links.rules import registry

        found = _find_citations_with_positions(text)
        claimed = [(start, end) for start, end, _ in found]
        for rule in registry.citation_rules_for(self.code):
            for citation in rule.find(text):
                idx = text.find(citation)
                if idx == -1:
                    continue
                span = (idx, idx + len(citation))
                if any(not (span[1] <= s or e <= span[0]) for s, e in claimed):
                    continue
                claimed.append(span)
                found.append((idx, span[1], citation))
        found.sort(key=lambda item: item[0])
        return [matched for _, _, matched in found]

    def extract_definitions_from_section(
        self, text: str, *, scope: str, heading_was_derived: bool = False
    ) -> list[DefinitionCandidate]:
        """Sprint 2026-08-04-defs-core-dispatch, item I3: `EntrySplitterRule`/
        `TermClauseRule` are UNION kinds -- baseline's own numbered blocks
        (`_split_into_numbered_blocks`) are unioned with every registered
        `EntrySplitterRule`'s own raw blocks for this profile's code, then
        EVERY block (baseline or rule-contributed) is run through
        baseline's own per-block leading-quote parser AND every registered
        `TermClauseRule.parse` -- zero-miss, no rule suppresses another.
        The `heading_was_derived` inline-quoted fallback still runs last,
        only when the union above produced nothing, preserving the exact
        "zero-risk for the 7 already-working states" guarantee (baseline-
        only behavior, no rules registered, is byte-identical to calling
        the bare `extract_definitions_from_section` function directly)."""
        from app.definition_links.rules import registry

        baseline_blocks = _split_into_numbered_blocks(text)
        extra_blocks: list[str] = []
        for rule in registry.entry_splitter_rules_for(self.code):
            extra_blocks.extend(rule.split(text))
        all_blocks = baseline_blocks + extra_blocks

        candidates: list[DefinitionCandidate] = []
        for block in all_blocks:
            candidate = _leading_quote_candidate(block, scope=scope)
            if candidate is not None:
                candidates.append(candidate)
        for block in all_blocks:
            for rule in registry.term_clause_rules_for(self.code):
                candidates.extend(rule.parse(block))

        if not candidates and heading_was_derived:
            candidates = _extract_inline_quoted_definitions(text, scope=scope)
        return candidates

    def detect_cross_law_derivations(
        self,
        text: str,
        *,
        source_term: str,
        known_law_titles: dict[str, str] | None = None,
    ) -> list[LawDerivesDefinitionEdge]:
        return detect_cross_law_derivations(
            text, source_term=source_term, known_law_titles=known_law_titles
        )

    def determine_scope(self, body_text: str) -> str:
        """Baseline (the bare `determine_scope` function above, unchanged)
        wins whenever it already detects `"chapter"` -- never overridden.
        Only when baseline falls through to its `"law-wide"` default are
        registered `ScopeKindRule`s for this profile's own code tried,
        first-non-None-wins in registration order (sprint
        2026-08-04-defs-core-dispatch, item I5/I8, manager ruling M-D2)."""
        from app.definition_links.rules import registry

        baseline = determine_scope(body_text)
        if baseline == "chapter":
            return baseline
        for rule in registry.scope_kind_rules_for(self.code):
            detected = rule.detect(body_text)
            if detected is not None:
                return detected
        return baseline

    def derive_heading_from_body(self, heading: str, body: str) -> str | None:
        """Baseline (the bare `derive_heading_from_body` function above,
        unchanged -- still gated on `_is_placeholder_heading`, which is
        what keeps the 7 already-working states and CA/IL[state]/GA
        byte-for-byte unaffected) first -- a baseline non-`None` result is
        never overridden. Only when baseline yields `None` (either because
        `heading` isn't a placeholder at all, or it is but the body-scan
        found nothing) are registered `BodyPreambleRule`s for this
        profile's own code tried, first-non-None-wins in registration
        order (sprint 2026-08-04-defs-core-dispatch, item I2, seam v2 M6,
        director ruling D-PREAMBLE-ALL)."""
        from app.definition_links.rules import registry

        baseline = derive_heading_from_body(heading, body)
        if baseline is not None:
            return baseline
        for rule in registry.body_preamble_rules_for(self.code):
            derived = rule.derive_heading(body)
            if derived is not None:
                return derived
        return None

    def extract_local_scope_definitions(
        self, article_body: str, *, article_number: str, chapter: str | None = None
    ) -> list[DefinitionCandidate]:
        """Unions candidates from every registered `ScopeTriggerRule` for
        this profile's own code (initially the one core-authored proof
        rule, `rules/us_scope_trigger_proof.py`; family panels add more,
        C2/C4) over an ORDINARY (non-Definitions-heading) article body.
        A rule that leaves `.source_article_number` unset (the common
        "local to THIS article" case) gets it defaulted here to
        `article_number`; a rule that stamps its OWN target (e.g. an
        enumerated/cross-article scope, M9) is respected unchanged."""
        from app.definition_links.rules import registry

        ctx = registry.RuleContext(article_number=article_number, chapter=chapter, unit_path=())
        candidates: list[DefinitionCandidate] = []
        for rule in registry.scope_trigger_rules_for(self.code):
            for candidate in rule.extract(article_body, ctx):
                if candidate.source_article_number is None:
                    candidate.source_article_number = article_number
                candidates.append(candidate)
        return candidates

    def resolve_unit_path(self, article, char_offset: int | None = None):
        return resolve_unit_path(article, char_offset)
