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
the Hebrew-engine sense (`normalize_for_parsing` is a passthrough -- see its
docstring) -- English statute text needs no wikilink-bracket stripping or
bidi handling. `is_definitions_heading` in particular is deliberately a
CONTAINS/substring check, not an anchored-at-start check like Hebrew's
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


def extract_definitions_from_section(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Extract every (term, definition) pair from a located Definitions
    section's body composed of `(N) "Term" ...` numbered entries (the real
    DE fixture's shape).

    Each entry's leading quoted span is the defined term; the remainder of
    the entry (after the closing quote) is the definition text. Entries
    with no leading quoted term are skipped (not a recognizable defined-
    term entry).
    """
    candidates: list[DefinitionCandidate] = []
    for block in _split_into_numbered_blocks(text):
        term_match = _LEADING_QUOTE_RE.match(block)
        if not term_match:
            continue
        term = term_match.group(1)
        definition_text = block[term_match.end() :].strip()
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
        )
    return candidates


# --- G3: English word-boundary term matching --------------------------------


def find_term_uses(term: str, text: str) -> list[re.Match[str]]:
    """Every non-overlapping occurrence of the literal `term` in `text`,
    using ordinary `\\b`-word-boundary matching -- NO Hebrew-style prefix-
    letter surface-form expansion. A defined term never false-matches as a
    substring of a longer word (`\\b` handles this natively: e.g. `term=
    "Affiliate"` will not match inside `"Affiliates"` or `"disaffiliated"`,
    since there is no word-boundary at that position).
    """
    pattern = re.compile(r"\b" + re.escape(term) + r"\b")
    return list(pattern.finditer(text))


def normalize_for_parsing(text: str) -> str:
    """No normalization needed for plain English statute text (no
    wikilink-bracket stripping, no RTL-bidi handling) -- passthrough."""
    return text


# --- G4: US citation grammar -------------------------------------------------

# Most specific first: a full `N U.S.C. § N(...)` federal citation, so its
# "§ N" portion is claimed before the bare `§ N` pattern below can grab it.
_USC_CITATION_RE = re.compile(r"\d+\s+U\.S\.C\.\s+§\s*\d+(?:\([^\s()]+\))*")

# `Section N` (spelled out).
_SECTION_WORD_RE = re.compile(r"\bSection\s+\d+\b")

# Bare `§ N` (optionally followed by parenthetical subdivisions).
_SECTION_SYMBOL_RE = re.compile(r"§\s*\d+(?:\([^\s()]+\))*")

# Tried in priority order; a later pattern's match is discarded if it
# overlaps a span already claimed by an earlier (more specific) pattern.
_CITATION_PATTERNS = (_USC_CITATION_RE, _SECTION_WORD_RE, _SECTION_SYMBOL_RE)


def find_citations(text: str) -> list[str]:
    """Every citation-shaped substring in `text`: `Section N`, `§ N`, and
    `N U.S.C. § N` federal citations. Returned in the order they appear in
    `text`.
    """
    claimed: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            if any(not (end <= s or e <= start) for s, e in claimed):
                continue
            claimed.append((start, end))
            found.append((start, match.group(0)))
    found.sort(key=lambda item: item[0])
    return [text for _, text in found]


# English defining idioms that introduce a cross-law derivation (the real
# fixture text uses the first form, not "means"). Longest-first so a
# suffixed/longer idiom is preferred if both could match at a position.
_TRIGGER_PHRASES = ("has the meaning specified in", "as defined in")
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


def detect_cross_law_derivations(
    text: str, *, source_term: str, known_law_titles: dict[str, str] | None = None
) -> list[LawDerivesDefinitionEdge]:
    """Scan `text` for `_TRIGGER_PHRASES` occurrences immediately followed
    by a recognizable citation (`find_citations`' grammar). A same-
    document/same-chapter reference (`"...of this chapter"` etc.
    immediately after the citation) is EXCLUDED -- Stage-3 territory, not a
    cross-law derivation.

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
        if _SAME_LAW_RE.match(after_citation):
            continue  # same-document/same-chapter reference -- not cross-law

        matched_text = citation_match.group(0)
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


@dataclass(frozen=True)
class USProfile:
    """The `"US-*"`/`"US-FED"` profile family -- ONE instance serves every
    US jurisdiction code (see module docstring for the per-state-vs-single
    decision). `.code` is set per-registration in `profiles.py`, not fixed
    here, since the same behavior applies under every US code.
    """

    code: str

    def is_definitions_heading(self, heading: str) -> bool:
        return is_definitions_heading(heading)

    def normalize_for_parsing(self, text: str) -> str:
        return normalize_for_parsing(text)

    def find_term_uses(self, term: str, text: str) -> list[re.Match[str]]:
        return find_term_uses(term, text)

    def find_citations(self, text: str) -> list[str]:
        return find_citations(text)

    def extract_definitions_from_section(
        self, text: str, *, scope: str
    ) -> list[DefinitionCandidate]:
        return extract_definitions_from_section(text, scope=scope)

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
