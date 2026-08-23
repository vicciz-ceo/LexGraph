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
from types import SimpleNamespace

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


# Issue #23 (sprint 2026-08-10-green-the-suite, item 1): mirrors
# `us_markers_boundary.py`'s own already-proven "list-introducer exclusion"
# (see that module's docstring) -- a bare digit marker is never a hard
# entry boundary when the text immediately before it (skipping only
# whitespace/blank lines) ends in `:` or an em dash `—`, because that
# punctuation itself says "the following IS this clause's own content",
# not a new sibling entry. Deliberately narrower than the sibling engine's
# version: it gates ONLY the unconditional bare-digit FALLBACK below, never
# `_strip_marker_chain_before_quote`'s own quote-anchored path. A marker
# immediately followed by its own quote (e.g. TX's `(A) "contested case";`
# nested under a `(4) ... Section 2001.003:` redirect clause) is a real
# defined-term anchor of its own and must keep opening its own block --
# suppressing it here would merge it into the still-quote-less parent block
# and delete the term's own anchor entirely (the ORIGINAL AL/TX defect this
# item closes was already "term survives, content lost"; a naive universal
# suppression would regress that to "term lost too"). That shape -- an
# orphaned, colon-terminated introducer immediately followed by its own
# quote-anchored lettered children (TX's `(4) The following terms have the
# meanings assigned by Section 2001.003:` then `(A) "contested case";`) is
# STILL always split into its own sibling block here, unconditionally --
# `_entry_start_remainder` itself never suppresses this path. A first,
# naive fix that instead tried to suppress/merge at THIS level (fold the
# orphan's redirect text forward into every following quote-anchored
# child) was implemented and then WITHDRAWN once this item's own mandated
# corpus-wide blast-radius measurement (see the Developer report) found it
# corrupting real, already-complete, unrelated MI definitions -- a real MI
# corpus row is marker-structurally identical to TX's shape but
# semantically opposite, and no marker-KIND-only signal separates the two.
# Track TX (PR#20): the actual fix lives one level up, as an ADDITIVE
# post-processing pass in `_split_into_numbered_blocks` (see the comment
# above `_PUNCTUATION_STUB_RE`) -- it never touches this function or this
# split, it only optionally attaches the already-closed orphan's own text
# to a SEPARATE, additional copy of a child block, and only when that
# child's own capture turns out to carry no content of its own.
_LIST_INTRODUCER_TAIL_RE = re.compile(r"[:—]\s*$")


def _entry_start_remainder(line: str, *, preceded_by_list_introducer: bool = False) -> str | None:
    """Return the remainder of `line` with its leading entry marker(s)
    stripped if `line` starts a new definition entry, else `None`. Tries
    the (quote-anchored) marker-chain rule first -- ALWAYS, regardless of
    `preceded_by_list_introducer` (see the comment above
    `_LIST_INTRODUCER_TAIL_RE` for why); falls back to the original
    unconditional bare-digit-marker rule so a later bare "(N)" still closes
    out an open block even with no quote right after it (see the rationale
    comment above `_MARKER_TOKEN_RE`) -- UNLESS `preceded_by_list_
    introducer` is True, in which case this bare digit marker is this
    entry's own nested-list content (issue #23), not a boundary, and the
    caller folds it into whatever block is currently open instead.
    """
    chain_remainder = _strip_marker_chain_before_quote(line)
    if chain_remainder is not None:
        return chain_remainder
    if preceded_by_list_introducer:
        return None
    digit_match = _BARE_DIGIT_MARKER_RE.match(line)
    if digit_match is not None:
        return line[digit_match.end() :]
    return None


# --- G3 (sprint 2026-08-05-defs-core-follow-on-2): shared content-marker
# termination helper ----------------------------------------------------
#
# The defect: every block below is correctly bounded by the START of the
# next recognized entry marker -- EXCEPT the last one, which has no next
# marker to stop at and previously ran unconditionally to the literal end
# of the input text. Design decided by the Planner (both-sides corpus
# sampling, 24.62% of 27,051 real last entries measured contaminated): the
# fix is CONTENT-marker based, not structural -- a structural rule (e.g.
# "stop at the next blank line") either changes nothing, since these
# markers already sit inside the document's ordinary blank-line-separated
# paragraph shape, or risks cutting a genuine multi-paragraph final entry
# short (this sprint's non-regression guard, `test_us_core_g3_guard_
# states_no_regression.py`, pins exactly that risk across 12 real
# multi-entry rows).
#
# `_TRAILING_NOTES_MARKERS` is the extended 10-marker set independently
# confirmed against the real vaquill US-code dataset's own trailing-notes
# convention (citation histories, "Editorial Notes"/"Amendments" logs,
# "Statutory Notes and Related Subsidiaries", etc., bundled into the same
# `text` field after a section's real operative content).
#
# `_trailing_notes_boundary` is deliberately OFFSET-based (a text plus a
# candidate `[start, end)` span), NOT list-of-lines-based, so it is a
# SHARED helper usable by more than just `_split_into_numbered_blocks`'s
# own line-oriented block-builder below. `_extract_inline_quoted_
# definitions` (line ~551) carries the exact same unbounded-last-entry
# defect at its own `end = ... else len(text)` fallback, and has been
# ruled INTO this gate's scope -- but is FENCED here pending a both-sides
# sample on its own population (a named, separate, not-yet-satisfied
# condition; see this sprint's report). That function's entries are
# quote-anchored `(term, start, definition_start)` offset tuples into the
# ORIGINAL text, not a pre-built line list, so a line-list-shaped helper
# would not fit it without rework -- an offset-in/offset-out interface
# does: it can call `_trailing_notes_boundary(text, definition_start,
# end)` in place of its own literal `len(text)` fallback with no other
# change, whenever that fence lifts. NOT wired there yet in this pass.
_TRAILING_NOTES_MARKERS = (
    "Editorial Notes",
    "Amendments",
    "Statutory Notes",
    "References in Text",
    "Congressional Findings",
    "Pub. L.",
    "History:",
    "Amended by Act",
    "Source:",
    "Cited.",
)

# G13 (sprint 2026-08-05-defs-core-follow-on-2, program-manager ruling --
# item G13-1): a corpus census found 28 real rows where a bare substring
# match of `'Pub. L.'` or `'Amendments'` ANYWHERE in a line produced a
# FALSE trailing-notes trigger, wiping an entire genuine entry rather
# than trimming a tail. Both strings are ordinary US statutory-drafting
# vocabulary that routinely appears MID-SENTENCE inside a genuine
# definition's own substantive prose -- citing an act's own Public Law
# number inline ("... the Family First Prevention Services Act (Title
# VII, Div. E, Pub. L. No. 115-123) ...", real TX row
# STATE_TX_Cfa_C264_S264.152), or even as part of the DEFINED TERM's own
# real name ("Superfund Amendments and Reauthorization Act of 1986,
# Title III", real AR row STATE_AR_T12_C84_S12-84-103). All 28 drops were
# hand-checked and are false truncations; zero implicate any of the other
# 8 markers alone -- so this guard is scoped to EXACTLY these two marker
# strings, mirroring `_preceded_by_references_to`'s established shape
# (targeted, literal, positional), not widened to the rest.
#
# The rule: a line only counts as a trigger for one of these two markers
# if, after `lstrip()`, it STARTS WITH `'('` (a standalone citation/
# parenthetical block -- covers both the immediate `"(Pub. L. ..."` shape
# and a long semicolon-chained citation-history line, regardless of how
# far into that already-parenthetical line the marker text itself sits)
# OR STARTS WITH the marker text itself (a bare section-header line, e.g.
# a line that is just `"Amendments"`).
#
# A character-offset threshold (e.g. "only trigger if the marker sits
# within N chars of the line start") was tried and REJECTED with data:
# genuine citation lines legitimately place `'Pub. L.'` anywhere from
# offset 1 to offset 852 (real case USC_T7_C35_S1301, a long semicolon-
# chained date list inside a single `'('`-opened citation block) --
# distance from the line start does not separate genuine citation blocks
# from false mid-sentence hits. Whether the line itself IS a citation/
# header block -- signalled by what it starts with, not by how far into
# it the marker sits -- does. Every other marker keeps the original
# bare-substring-anywhere-in-line rule, byte-identical to before this
# gate.
_POSITIONALLY_GUARDED_MARKERS = frozenset({"Pub. L.", "Amendments"})


def _is_guarded_marker_line_trigger(line: str, marker: str) -> bool:
    """For one of `_POSITIONALLY_GUARDED_MARKERS`, whether `line` (already
    known to contain `marker` as a substring) genuinely opens a
    trailing-notes citation/header block -- see the G13 comment above
    `_POSITIONALLY_GUARDED_MARKERS` for the exact rule and the false-drop
    defect it closes."""
    stripped = line.lstrip()
    return stripped.startswith("(") or stripped.startswith(marker)


def _trailing_notes_boundary(text: str, start: int, end: int) -> int:
    """Where an entry spanning `text[start:end]` should ACTUALLY end, given
    that `end` is merely a provisional/unbounded bound (e.g. `len(text)`
    for a sequence's LAST entry, which -- unlike every other entry -- has
    no real "the next entry starts here" boundary at all).

    Scans `text[start:end]` LINE BY LINE for the first line that CONTAINS
    one of `_TRAILING_NOTES_MARKERS` as a substring, and returns the
    OFFSET of the START of that line (so a caller's own `text[start:
    boundary]` slice drops the marker line and everything after it, not
    merely the matched substring onward). Returns `end` unchanged if no
    such line is found -- the common case; most real Definitions sections
    carry no trailing notes at all.

    Line granularity (not the marker substring's own raw character
    offset) is deliberate: a marker can appear MID-line inside an
    otherwise-unrelated citation parenthetical that is itself part of the
    SAME trailing-notes block -- e.g. real FED row USC_T5_C34_S3401's own
    "(Added Pub. L. 95-437, ...)" amendment citation, which precedes
    "Editorial Notes"/"Amendments" and is not part of the entry's own
    substantive definition text. Truncating at the marker substring's own
    raw offset would leave that parenthetical's leading fragment
    ("(Added ") dangling in the kept text; dropping the whole line does
    not.

    G13 refinement: for exactly the two markers in
    `_POSITIONALLY_GUARDED_MARKERS` (`'Pub. L.'`, `'Amendments'`), a bare
    substring-anywhere-in-line match is NOT sufficient on its own -- see
    `_is_guarded_marker_line_trigger` and the comment above
    `_POSITIONALLY_GUARDED_MARKERS` for the false-drop defect this closes
    and why the additional check is positional (what the line STARTS
    with) rather than offset-based. Every other marker is unaffected --
    it still triggers on a bare substring match anywhere in the line,
    exactly as before this gate.
    """
    offset = start
    for line in text[start:end].split("\n"):
        for marker in _TRAILING_NOTES_MARKERS:
            if marker not in line:
                continue
            if marker in _POSITIONALLY_GUARDED_MARKERS and not _is_guarded_marker_line_trigger(
                line, marker
            ):
                continue
            return offset
        offset += len(line) + 1  # +1 for the "\n" `str.split` consumed
    return end


# Issue #23 continued -- TX's OWN mirror-image shape (an orphaned
# DIGIT-marked introducer clause, no leading quote of its own, immediately
# followed by its own LETTER-marked quote-anchored children: `(4) The
# following terms have the meanings assigned by Section 2001.003:` then
# `(A) "contested case";` / `(B) "party";` / ...). A first, naive fix --
# fold the orphan's own redirect text forward into EVERY following quote-
# anchored child, unconditionally -- was implemented and then WITHDRAWN
# once this item's own mandated corpus-wide blast-radius measurement (see
# the Developer report) found it corrupting real, already-complete,
# unrelated MI definitions: `STATE_MI_C206_AAct-281-of-1967_S206.278`'s
# subsections `(1)`-`(7)` are ordinary numbered provisions and `(8) As
# used in this section:` is followed by `(a) "Board" means...`, `(b)
# "Michigan strategic fund" means...`, etc. -- MARKER-STRUCTURALLY
# IDENTICAL to TX's own shape (an adjacent digit run ending in an
# orphaned, colon-terminated digit block, followed by lettered quote-
# anchored children), but semantically the OPPOSITE: TX's `(4)` genuinely
# redirects to external Section 2001.003 (its children have NO meaning
# without it); MI's `(8)` is ordinary "as used in this section"
# boilerplate in front of terms that are ALREADY fully self-contained --
# folding it forward unconditionally only appends noise to MI. No purely
# marker-KIND/position signal (the only kind M-R107 permits) tells these
# two real shapes apart; every version tried either missed MI (a whole-
# document "digit exists somewhere" check) or still hit it (a same-run
# "immediately adjacent digit sibling" check -- MI's `(8)` sits directly
# after digit-marked `(7)`, exactly like TX's `(4)` after `(3)`).
#
# Track TX (PR#20) safe variant, built and corpus-verified: fold forward
# ONLY when the child's OWN captured content (the block text after its
# own leading quoted term) is nothing but a punctuation artifact -- see
# `_PUNCTUATION_STUB_RE`/`_child_definition_is_punctuation_stub` below.
# This is a CONTENT-SHAPE signal (does the child's own capture carry any
# information beyond list punctuation?), not a marker-KIND/position
# signal, and it is keyed on NEITHER state: TX's 4 children each capture
# only trailing list punctuation (`;`, `;`, `; and`, `` -- their real
# content lives entirely in the parent redirect they were never attached
# to), so all 4 qualify and fold. MI's children each capture a genuine
# `means ...` sentence of their own, so NONE qualify -- `_child_
# definition_is_punctuation_stub` returns False for every one of them and
# the fold path never runs; MI is untouched. AL's own fix above (`_entry_
# start_remainder`'s bare-digit suppression) is a different mechanism
# entirely and is unaffected -- it only ever folds a nested list INTO its
# own already-open quote-anchored parent, never fans a redirect out to
# separate sibling candidates.
#
# The fold, when it fires, does not mutate the stub block in place -- it
# INSERTS a second, folded-content sibling block immediately ahead of the
# original, untouched stub block (see the expansion pass at the end of
# `_split_into_numbered_blocks`). Both are parsed by the ordinary
# `_leading_quote_candidate` path. Keeping the raw stub block intact
# (rather than replacing it) means every existing direct caller of
# `_split_into_numbered_blocks`/`extract_definitions_from_section` still
# sees it exactly as before -- while `pipeline.py`'s `(article, terms)`-
# keyed idempotent persistence, which always keeps whichever same-key
# candidate it enumerates FIRST, ends up persisting the folded one,
# because it is now the one enumerated first.
_PUNCTUATION_STUB_RE = re.compile(r"^[\s;:,.]*(?:and|or)?[\s;:,.]*$", re.IGNORECASE)


def _child_definition_is_punctuation_stub(block: str) -> bool:
    """True when `block` (an already-built, stripped block string from
    `_split_into_numbered_blocks`) opens with a quoted term whose OWN
    captured definition -- everything after the closing quote -- carries
    no information of its own: nothing but whitespace, list punctuation
    (`;`, `:`, `,`, `.`), and/or a single trailing "and"/"or" connector.
    False for a block with no leading quote at all (nothing to fold into)
    or whose captured content contains any other real word -- see the
    fold-eligibility comment above for why this, and only this, is the
    signal that tells TX's shape apart from MI's."""
    term_match = _LEADING_QUOTE_RE.match(block)
    if term_match is None:
        return False
    remainder = block[term_match.end() :].strip()
    return bool(_PUNCTUATION_STUB_RE.match(remainder))


def _fold_orphan_parent_into_stub_child(block: str, parent_text: str) -> str:
    """Return a NEW block string that inserts `parent_text` (an orphaned
    introducer's own already-closed text) between `block`'s leading
    quoted term and its own (punctuation-stub) captured content, so
    re-parsing the result with `_leading_quote_candidate` yields the SAME
    term with the parent's real redirect clause as its definition text
    instead of bare punctuation. Returns `block` unchanged if it has no
    leading quote, or if stripping `parent_text`'s own trailing list-
    introducer punctuation (`_LIST_INTRODUCER_TAIL_RE`) leaves nothing
    behind."""
    term_match = _LEADING_QUOTE_RE.match(block)
    if term_match is None:
        return block
    parent_clause = _LIST_INTRODUCER_TAIL_RE.sub("", parent_text).strip()
    if not parent_clause:
        return block
    return f"{block[:term_match.end()]} {parent_clause}{block[term_match.end():]}"


def _split_into_numbered_blocks(text: str) -> list[str]:
    lines = text.split("\n")
    blocks: list[list[str]] = []
    # Track TX (PR#20): parallel to `blocks` -- for each block, either
    # `None` (not fold-eligible) or the text of the orphaned introducer
    # currently "in scope" for it (see below). Only ever consulted for a
    # block that turns out, once fully built, to be a punctuation stub.
    block_fold_sources: list[str | None] = []
    current: list[str] | None = None
    current_opened_via_chain = False
    current_block_fold_source: str | None = None
    # The most recently closed orphaned introducer (no leading quote of
    # its own, own text ends in `:`/`—`) still "in scope" -- persists
    # across an entire RUN of quote-anchored chain-opened sibling blocks
    # (TX's (A)-(D), MI's (a)-(d)), since only the FIRST of those siblings
    # is itself immediately preceded by the introducer's own raw line;
    # later siblings are preceded by an earlier SIBLING's line instead.
    # Cleared the moment a bare-digit-fallback-opened block closes with no
    # list-introducer tail of its own (an ordinary, unrelated numbered
    # provision), so a later entry never inherits an earlier orphan's
    # redirect text across such a boundary.
    active_fold_source: str | None = None
    prev_nonblank = ""
    for line in lines:
        # Issue #23 correction (MI/PA blast-radius finding): suppression
        # only ever makes sense when there is an ALREADY-OPEN block for
        # the marker to fold forward into (AL's "(1)" right after "(a)
        # "Acquire" means:" -- `current` is that quote-anchored block).
        # With no open block yet (a bare digit marker is the very FIRST
        # thing seen, e.g. PA's own `"For the purposes of this
        # subchapter:\n\n(1) References to ..."` construction-clause
        # preamble), suppressing it doesn't fold it into anything -- it
        # just SILENTLY DROPS the line with nowhere to go, which is a
        # regression of its own (real PA guard: `_split_into_numbered_
        # blocks` must still yield that row's 3 real digit-marked blocks,
        # even though none of them carries a leading quote either way).
        preceded_by_list_introducer = current is not None and bool(
            _LIST_INTRODUCER_TAIL_RE.search(prev_nonblank)
        )
        new_entry_start = _entry_start_remainder(
            line, preceded_by_list_introducer=preceded_by_list_introducer
        )
        if new_entry_start is not None:
            if current is not None:
                blocks.append(current)
                block_fold_sources.append(current_block_fold_source)
                if not current_opened_via_chain:
                    # The block just closed was opened via the bare-digit
                    # FALLBACK path, so (by construction -- see
                    # `_entry_start_remainder`) it has no leading quote of
                    # its own. It becomes the new active fold source only
                    # if it also ends in a list-introducer tail (a genuine
                    # orphaned "the following ..." clause); otherwise it
                    # is an ordinary numbered provision and clears
                    # whatever fold source was previously in scope.
                    #
                    # Deliberately the block's OWN LAST non-blank raw line
                    # (mirroring `prev_nonblank`'s own convention just
                    # above), not its full accumulated multi-line text: a
                    # real corpus-wide blast-radius finding (NM row
                    # `STATE_NM_C61_A35_S61-35-2`) showed that when this
                    # splitter's OWN unrelated marker gap (bare `"A."`/
                    # `"C."`-style letter-period markers, which this
                    # splitter's paren-only `_MARKER_TOKEN_RE` never
                    # recognizes) lets several unrelated prior sentences
                    # accumulate into one block before it finally reaches
                    # a colon, using that whole accumulated blob as the
                    # fold source pulled in all of that unrelated leading
                    # text too. The introducer clause itself is always
                    # its OWN last sentence right before the colon --
                    # using just that line is byte-identical to using the
                    # whole block on every genuine single-line introducer
                    # (TX's `(4)`, MI's `(8)`/`(7)`), and correctly narrows
                    # to just the real introducer sentence on NM's shape.
                    last_nonblank_line = next(
                        (ln.strip() for ln in reversed(current) if ln.strip()), ""
                    )
                    active_fold_source = (
                        last_nonblank_line
                        if _LIST_INTRODUCER_TAIL_RE.search(last_nonblank_line)
                        else None
                    )
                # else: the block just closed was itself quote-anchored
                # (a sibling entry, not an introducer) -- whatever fold
                # source was already active stays active unchanged, so
                # the NEXT sibling in the same run still sees it too.
            current = [new_entry_start]
            current_opened_via_chain = bool(_LEADING_QUOTE_RE.match(new_entry_start))
            current_block_fold_source = active_fold_source if current_opened_via_chain else None
        elif current is not None:
            current.append(line)
        if line.strip():
            prev_nonblank = line
    if current is not None:
        blocks.append(current)
        block_fold_sources.append(current_block_fold_source)
    joined = ["\n".join(b) for b in blocks]
    if joined:
        # G3: only the LAST block has no natural next-entry boundary --
        # every other block above is already correctly bounded by the
        # START of the following recognized entry marker.
        last = joined[-1]
        joined[-1] = last[: _trailing_notes_boundary(last, 0, len(last))]
    stripped = [b.strip() for b in joined]
    # Track TX (PR#20) fold-forward expansion pass -- purely additive: a
    # block with no fold source, or whose own capture is not a
    # punctuation stub, passes through as the single entry it always was
    # (byte-identical to before this pass for every such block, which is
    # the overwhelming majority of the corpus). Only a fold-eligible stub
    # gets a second, folded-content block inserted immediately ahead of
    # its own untouched original -- see the comment above `_PUNCTUATION_
    # STUB_RE` for why insertion order (folded first) is what makes the
    # folded content win `pipeline.py`'s idempotent persistence.
    result: list[str] = []
    for index, block in enumerate(stripped):
        fold_source = block_fold_sources[index]
        if fold_source is not None and _child_definition_is_punctuation_stub(block):
            result.append(_fold_orphan_parent_into_stub_child(block, fold_source))
        result.append(block)
    return result


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
#
# G12 (sprint 2026-08-05-defs-core-follow-on-2, director ruling
# D-INCLUDES): adds `shall include` and `includes` -- these two forms
# EXACTLY, not a broader `include`-family (bare `include`, no trailing
# `-s`, deliberately stays unrecognized -- it is not one of D-INCLUDES's
# named forms). This regex is consumed solely by
# `_extract_inline_quoted_definitions` (the placeholder-heading fallback
# path); the primary `"(N)"`-block splitter (`_split_into_numbered_
# blocks`/`_leading_quote_candidate`) never reads it, so that path is
# untouched. Boundary and emission both fall out of this ONE change: the
# same `entries`-list index-slicing logic in
# `_extract_inline_quoted_definitions` already uses "does this quote's
# gap match the idiom regex" to decide both where the PRECEDING entry's
# `definition_text` stops and where the new entry's own candidate begins
# -- there is no separate boundary mechanism to also update. Measured
# corpus-wide (2,117 fallback-eligible rows: CA 442, GA 3, IL 1,672): of
# 11,960 quoted-term occurrences, 9,677 recognized today, 10,170 once
# widened -- +493 newly-recognized entries across 329 rows. See
# `_preceded_by_references_to` immediately below for the mandatory
# targeted guard D-INCLUDES also requires alongside this widening (the
# PA construction-clause shape, `References to "X" shall include Y`,
# which is not itself a definition).
_MEANS_IDIOM_GAP_RE = re.compile(
    r'^[^"“”]{0,200}?\b(?:means|shall mean|has the meaning|shall include|includes)\b:?\s*',
    re.IGNORECASE,
)

# Sprint 2026-08-23-defs-debt-31, Item 2 (issue #31 debt class 2 -- "19
# enumerated single-letter wave phantoms"). `_MEANS_IDIOM_GAP_RE`'s own
# 0-200-char non-greedy gap tolerance is what lets a genuine `"X" symbol
# means ...`-shaped definiendum (real NV 484B.307, 8-char gap) and a
# phantom `"e", subparagraph (2), eligible service includes ...`-shaped
# citation token (real IA 97B.49B, 37-char gap through an intervening
# noun phrase) BOTH match -- there is no positional/adjacency signal in
# that regex at all. This SEPARATE regex re-locates the idiom word's own
# start WITHIN an already-successful `_MEANS_IDIOM_GAP_RE` match (its
# `.group(0)` is exactly the consumed gap + idiom), giving the gap
# DISTANCE a caller can gate on -- narrower than adding a proximity
# requirement to `_MEANS_IDIOM_GAP_RE` itself, which would also narrow
# every ordinary multi-character term (director ruling D-INCLUDES already
# measured and rejected tightened idiom guards generally as pure recall
# loss; this stays scoped to single-letter terms only, see `_single_
# letter_term_lacks_adjacent_idiom` below).
_IDIOM_WORD_ONLY_RE = re.compile(
    r"\b(?:means|shall mean|has the meaning|shall include|includes)\b", re.IGNORECASE
)
# Corpus-verified boundary (this item's own real-row/synthetic exemplars,
# live-computed, not guessed): genuine adjacent shapes measure 8 chars
# (NV 484B.307's own "symbol means") and 11 chars (this item's own
# synthetic "Z" control's own "indicator means"); phantom distant shapes
# measure 37 chars (IA 97B.49B's own citation gap) and 93 chars (this
# item's own synthetic "K" control) -- a wide, unambiguous margin between
# the two sub-populations the corpus-wide census found (14/19 IA citation
# shape, 5/19 classification-label shape), so the exact cut point within
# that margin is not precision-sensitive.
_SINGLE_LETTER_ADJACENCY_MAX_GAP = 20


def _single_letter_term_lacks_adjacent_idiom(term: str, means_match: re.Match[str]) -> bool:
    """True when `term` is a single letter AND the idiom `means_match`
    matched sits DISTANT from the quote's own closing delimiter -- a
    lettered cross-reference citation or classification-letter label,
    never a genuine `"X" means ...`-shaped definiendum. Only ever narrows
    a SINGLE-LETTER term's own admission; a multi-character term's gap
    distance is never inspected (out of this item's scope, per gate 2 --
    D-INCLUDES already measured and rejected a general proximity
    tightening as pure recall loss)."""
    if len(term) != 1:
        return False
    idiom_word = _IDIOM_WORD_ONLY_RE.search(means_match.group(0))
    if idiom_word is None:
        return False
    return idiom_word.start() > _SINGLE_LETTER_ADJACENCY_MAX_GAP


# G12 mandatory guard (director ruling D-INCLUDES): a quoted span
# immediately preceded (within a small bounded, whitespace-tolerant
# lookback window) by "References to"/"Reference to" (case-insensitive)
# is a construction/interpretation clause about how OTHER text in the
# subchapter should be read (real PA shape: `References to "other
# enterprises" shall include employee benefit plans ...`), not a `"X"
# means/includes Y`-shaped definition -- suppressed from starting an
# entry boundary at all, same effect as if no idiom had matched.
#
# Deliberately a LITERAL TEXTUAL lookback, not idiom-absence and not any
# broader construction-clause heuristic: D-INCLUDES explicitly measured
# and rejected tightened guards as pure recall loss (32-56% of true
# definitions lost for no measured precision gain). This guard's own
# trigger rate in the 2,117-row fallback-eligible population is 0 of the
# 493 newly-recognized entries (none sit within 25 chars of "References
# to") -- it is nonetheless mandatory per the ruling's program-wide
# framing, not something to narrow further or drop because it doesn't
# currently fire.
_REFERENCES_TO_RE = re.compile(r"References?\s+to\s*$", re.IGNORECASE)
_REFERENCES_TO_LOOKBACK = 25


def _preceded_by_references_to(text: str, quote_start: int) -> bool:
    """True when `text[:quote_start]` ends (within a small bounded lookback
    window) in "References to"/"Reference to" (case-insensitive) --
    see `_REFERENCES_TO_RE` above for what this guards against and why
    it is a literal textual check rather than a heuristic."""
    window_start = max(0, quote_start - _REFERENCES_TO_LOOKBACK)
    return bool(_REFERENCES_TO_RE.search(text[window_start:quote_start]))


# Shared-extraction sprint 2026-08-12-shared-extraction-t35 (root cause,
# structural, not row-specific -- M-R107): real US statutory drafting, when
# quoting a multi-paragraph block of text verbatim (a historical/session-law
# note is the common case), re-opens a `"` at the start of EVERY paragraph
# of the quoted block and closes only once, at the very end. `_QUOTE_TERM_RE`
# has no notion of this -- it pairs an opening quote with whatever quote
# character comes next, so the FIRST paragraph's re-opening `"` gets
# consumed as if it were the real close of the block's OWN opening `"`,
# turning the block's leading text (often a heading-shaped fragment) into a
# spurious "definiendum" and leaving the block's real closing `"` to pair
# with some unrelated LATER quote in the document -- the source of both the
# phantom-term defect and the runaway definition-text bleed it produces.
#
# Structural signal used to detect this (not any literal heading/term/
# section text): a quote character immediately preceded, within a small
# bounded lookback window, by a blank line (a paragraph break) -- once any
# horizontal whitespace and OTHER quote characters immediately before it
# are stripped away -- is a per-paragraph re-opening quote, not a genuine
# close, WHENEVER it is encountered while still inside an already-open
# quoted span. The noise-stripping step is what lets this SAME check
# recognize a nested shape too: real drafting sometimes quotes a numbered
# sub-list INSIDE the outer block using single quotes for the sub-list's
# own per-paragraph re-opens (`"<nbsp>'(iii) ...`) -- immediately after
# the outer double-quote's own re-open, not immediately after a bare
# newline -- and that inner re-open must be recognized as noise too, or a
# nested single-quote scan (below) mistakes it for a genuine definiendum
# delimiter and pairs it with the next unrelated apostrophe it finds
# (confirmed against this exact shape in the real `USC_T35_C4_S41` body).
_PARAGRAPH_START_LOOKBACK = 40
_PARAGRAPH_BREAK_TAIL_RE = re.compile(r"\n[ \t]*\n[ \t]*\Z")
_QUOTE_TAIL_NOISE_RE = re.compile(r'[ \t "“”\']*\Z')


def _is_paragraph_start_quote(text: str, quote_pos: int) -> bool:
    """True when the quote character at `text[quote_pos]` sits at the
    start of a paragraph -- see the module note above for exactly what
    that means and why noise-stripping is required to detect it at both
    the outer and a nested inner quoting level."""
    window_start = max(0, quote_pos - _PARAGRAPH_START_LOOKBACK)
    window = text[window_start:quote_pos]
    noise_match = _QUOTE_TAIL_NOISE_RE.search(window)
    prefix = window[: noise_match.start()] if noise_match else window
    return bool(_PARAGRAPH_BREAK_TAIL_RE.search(prefix))


# Any double or curly quote character, used (unlike `_QUOTE_TERM_RE`) to
# scan forward one character at a time rather than to pair adjacent quotes
# -- needed to walk past an arbitrary run of per-paragraph re-opening
# quotes to find a block's real close, however many paragraphs it spans.
_DOUBLE_QUOTE_CHAR_RE = re.compile(r'["“”]')

# A single-quoted definiendum, same bounded shape as `_QUOTE_TERM_RE`
# (1-200 non-quote characters between delimiters) but for `'...'` rather
# than `"..."`/`"..."` -- real US drafting nests a single-quoted term
# inside a double-quoted block-quote (e.g. a quoted historical note whose
# own body reads `"...the term 'X' means ...`), which is otherwise
# entirely invisible to `_QUOTE_TERM_RE` (double/curly quotes only).
# Deliberately NOT registered as a general-purpose scan across all of
# `text` -- an apostrophe is far too common in ordinary prose ("the
# cadet's appointment") to bound safely on its own; this is only ever
# applied INSIDE an already-confirmed block-quote span below, where the
# same idiom-gap guard (`_MEANS_IDIOM_GAP_RE`) that protects the ordinary
# double-quote path also applies.
_SINGLE_QUOTE_TERM_RE = re.compile(r"'([^'\"]{1,200})'")


def _find_block_quote_close(text: str, after: int) -> int | None:
    """Starting at or after `after`, scan forward for the first double/
    curly quote character that is NOT itself a paragraph-reopening quote
    (`_is_paragraph_start_quote`) -- the real close of a multi-paragraph
    block quote, however many further per-paragraph re-opens it contains.
    Returns `None` if the block never actually closes (degrades to "no
    candidate from this branch", the same outcome an ordinary unterminated
    quote already produces today)."""
    for match in _DOUBLE_QUOTE_CHAR_RE.finditer(text, after):
        pos = match.start()
        if _is_paragraph_start_quote(text, pos):
            continue
        return pos
    return None


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

    G12 (director ruling D-INCLUDES): a quoted span immediately preceded
    by "References to"/"Reference to" (`_preceded_by_references_to`) is
    skipped before the idiom check even runs -- the real PA construction-
    clause shape (`References to "X" shall include Y`) describes how
    OTHER text should be read, not a definition of "X" itself.

    Shared-extraction sprint 2026-08-12-shared-extraction-t35: when
    `_QUOTE_TERM_RE`'s own "closing" quote for a candidate is itself a
    paragraph-reopening quote (`_is_paragraph_start_quote`), that pairing
    is a mis-pairing, not a real term -- see the module note above
    `_is_paragraph_start_quote`. Such a candidate is dropped (never
    emitted as its own entry) and replaced by scanning INSIDE the block
    quote's real span (through to its real close, `_find_block_quote_close`)
    for a nested single-quoted definiendum instead
    (`_SINGLE_QUOTE_TERM_RE`), under the exact same "References to" and
    idiom-gap guards as the ordinary path, with its own captured
    definition text hard-clipped at the block's real closing quote so it
    can never bleed into the unrelated content that follows the block.
    `last_block_close` guards against re-processing the SAME block twice
    when it spans more than two paragraphs (each additional re-opening
    quote would otherwise independently rediscover the same real close).
    """
    entries: list[tuple[str, int, int, int | None]] = []
    last_block_close = -1
    for term_match in _QUOTE_TERM_RE.finditer(text):
        if _is_paragraph_start_quote(text, term_match.end() - 1):
            if term_match.start() < last_block_close:
                continue  # already covered by an earlier re-open in this same block
            block_close = _find_block_quote_close(text, term_match.end())
            if block_close is None:
                continue
            last_block_close = block_close
            inner_start, inner_end = term_match.start() + 1, block_close
            for nested_match in _SINGLE_QUOTE_TERM_RE.finditer(text, inner_start, inner_end):
                # Real drafting sometimes nests a QUOTED SUB-LIST inside
                # the outer block, itself re-opening with a single quote
                # at the start of each of ITS OWN paragraphs (e.g. `"
                # '(iii) ...`, immediately after the outer `"`'s own
                # re-open). Such an apostrophe is nested-block noise, not
                # a definiendum delimiter -- pairing it with the next
                # unrelated apostrophe (an ordinary possessive, most
                # often) produces a sentence-fragment, not a term. Reject
                # a nested match on EITHER side if that delimiter itself
                # sits at the start of a paragraph.
                if _is_paragraph_start_quote(text, nested_match.start()) or _is_paragraph_start_quote(
                    text, nested_match.end() - 1
                ):
                    continue
                if _preceded_by_references_to(text, nested_match.start()):
                    continue
                gap = text[nested_match.end() : min(nested_match.end() + 200, inner_end)]
                means_match = _MEANS_IDIOM_GAP_RE.match(gap)
                if means_match is None:
                    continue
                nested_term = nested_match.group(1).strip()
                if not nested_term:
                    continue
                if _single_letter_term_lacks_adjacent_idiom(nested_term, means_match):
                    continue
                entries.append(
                    (
                        nested_term,
                        nested_match.start(),
                        nested_match.end() + means_match.end(),
                        block_close,
                    )
                )
            continue
        if _preceded_by_references_to(text, term_match.start()):
            continue
        gap = text[term_match.end() : term_match.end() + 200]
        means_match = _MEANS_IDIOM_GAP_RE.match(gap)
        if means_match is None:
            continue
        term = term_match.group(1).strip()
        if not term:
            continue
        if _single_letter_term_lacks_adjacent_idiom(term, means_match):
            continue
        entries.append((term, term_match.start(), term_match.end() + means_match.end(), None))

    candidates: list[DefinitionCandidate] = []
    for index, (term, start, definition_start, hard_end) in enumerate(entries):
        end = entries[index + 1][1] if index + 1 < len(entries) else len(text)
        if hard_end is not None and hard_end < end:
            end = hard_end
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
    # G1 (sprint 2026-08-05-defs-core-follow-on-2): `.strip()` the captured
    # quote-interior group, matching `_extract_inline_quoted_definitions`'s
    # own convention for the SAME `_LEADING_QUOTE_RE`/quote-capture
    # pattern (line ~581, `term_match.group(1).strip()`). Real drafting
    # sometimes pads the quote interior with whitespace (`"“ Conviction
    # ”"`, not `"“Conviction”"` -- real MS row STATE_MS_T45_C10_S34-1);
    # without this, `find_term_uses`' `re.escape(term)` (which does not
    # escape a plain space) turns that padding into a literal required
    # space in the match pattern, silently missing a real mention that
    # abuts punctuation with no space before it.
    term = term_match.group(1).strip()
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
# deeper nesting).
#
# Sprint 2026-08-04-defs-core-dispatch, items I9/I11, manager ruling M-D3,
# seam v2.7 (+ follow-on batch, seam v2.7 erratum) -- two fixes to the
# classifier surface, both explained in full in `resolve_unit_path`'s own
# docstring below:
#
#   I11: the ladder above is the FEDERAL convention only. Real US STATE
#   drafting diverges from it in more than one way -- digit-outermost
#   (Oregon's `(1)(2)(3)` subsections, lettered paragraphs one level
#   below) and, measured directly against the real corpus in the follow-on
#   batch (33,161-row `us_oh_statutes.parquet`, signal-agnostic
#   denominator, independent same-kind-incrementing-run classifier),
#   Ohio's own dominant convention -- upper_alpha-OUTERMOST,
#   `(A)(1)(a)(i)`, 99.4% of the 17,951 real OH rows with any genuine
#   marker structure at all. The ladder is now chosen PER CALL from the
#   shape of the first genuine marker actually seen, among the THREE named
#   variants below. This is still an ENUMERATED, closed set of ladders,
#   not a fully general per-depth-learned mechanism -- see
#   `resolve_unit_path`'s own docstring for why that trade was made
#   deliberately, not by default, and its honesty note on what a document
#   whose outermost convention is none of these three still gets.
#
#   I9: a marker matching neither the next expected rung nor any open
#   ancestor is SKIPPED, never pushed as a generic `"sub"` step. The
#   unconditional push was the root cause of Maine's inline revisor
#   annotations (`(NEW)`, `(AMD)`, `(AFF)`, `(RP)`, `(RPR)`, `(REV)`,
#   `(COR)`) polluting every below-article path they appear in. The
#   follow-on batch REMOVED an earlier, additional closed-word-list
#   exclusion for those 7 codes (program precedent P-E3, "machinery for a
#   phantom shape"): mutation-tested (emptied the list, reran the full
#   suite, all 10 I9 annotation tests -- including the `(RP)` case, the
#   one genuine shape collision with `double_upper_alpha` -- stayed green)
#   and independently reproduced here before removal. The word list was
#   unproven: this "skip unclassifiable" rule alone already accounts for
#   why none of the 7 codes ever survives as a path step -- see
#   `resolve_unit_path`'s own docstring for the per-code reasoning.

_US_UNIT_MARKER_RE = re.compile(r"\(([A-Za-z]+|\d+)\)")
_LOWER_ROMAN_CHARS_RE = re.compile(r"^[ivxlcdm]+$")
_UPPER_ROMAN_CHARS_RE = re.compile(r"^[IVXLCDM]+$")

# --- G2 (sprint 2026-08-05-defs-core-follow-on-2): period-style top-level
# markers -- real US drafting routinely opens a top-level unit with a
# digit or short letter run followed by "." instead of a parenthesized
# token (Maine "2-A."/"F.", Arizona "J.", Virginia "A."). Anchored at a
# paragraph boundary ONLY (start of body, or immediately after a newline,
# any amount of leading same-line whitespace) -- never mid-sentence, same
# "anchored, not free-floating" discipline `_LEADING_PARENTHETICAL_RE`/
# `_BODY_EMBEDDED_HEADING_RE` already use elsewhere in this module. Token
# shape: a digit run with Maine's optional hyphen-letter continuation
# ("2-A", the real convention for a section inserted between "2." and
# "3." without renumbering), or a bare 1-2 letter run -- followed by "."
# and whitespace (a trailing decimal, e.g. "12.5", never matches: the
# lookahead requires whitespace, not a digit, right after the ".").
# Captures the marker text only (group 1), never the "." itself.
_US_PERIOD_UNIT_MARKER_RE = re.compile(
    r"(?:\A|\n)[ \t]*(\d+(?:-[A-Za-z]{1,2})?|[A-Za-z]{1,2})\.(?=\s)"
)

# `_marker_matches_kind`'s "digit" rung extension: Maine's hyphen-
# continuation token ("2-A") classifies at the SAME rung a plain digit
# token would ("2-A." is the section inserted between "2." and "3.").
_DIGIT_HYPHEN_CONTINUATION_RE = re.compile(r"^\d+-[A-Za-z]{1,2}$")

# The federal-convention ladder (dossier-confirmed, v2.4 §3), used
# whenever the first genuine marker seen is neither digit- nor
# upper_alpha-shaped -- see `resolve_unit_path`'s docstring "Honesty note"
# for exactly what that residual default means for a fourth, unnamed
# convention.
_UNIT_PATH_LADDER = (
    "lower_alpha",
    "digit",
    "upper_alpha",
    "lower_roman",
    "upper_roman",
    "double_lower_alpha",
    "double_upper_alpha",
)
# I11: the digit-outermost variant -- swaps ONLY the first two rungs
# relative to `_UNIT_PATH_LADDER` (real US STATE convention, e.g. Oregon's
# `(1)(2)(3)` subsections with `(a)(b)(c)` paragraphs one level below).
# Every rung from position 2 onward is unchanged/shared with the federal
# ladder.
_DIGIT_OUTERMOST_UNIT_PATH_LADDER = (
    "digit",
    "lower_alpha",
    "upper_alpha",
    "lower_roman",
    "upper_roman",
    "double_lower_alpha",
    "double_upper_alpha",
)
# I11 follow-on: the upper_alpha-outermost variant -- Ohio's real,
# corpus-measured dominant order (`test_definition_links_cd_i11_oh_upper_
# alpha_ladder.py`'s module docstring carries the full measurement:
# `(upper_alpha, digit, lower_alpha, lower_roman, upper_roman)` measured
# directly over 17,849 real rows; the trailing `(double_lower_alpha,
# double_upper_alpha)` pair is NOT independently corpus-verified this deep
# for Ohio -- appended by ANALOGY to the other two ladders' own shared
# tail, since no real measured OH row reaches that depth). Every rung
# from position 3 onward is shared with both other ladders.
_OH_UPPER_ALPHA_OUTERMOST_UNIT_PATH_LADDER = (
    "upper_alpha",
    "digit",
    "lower_alpha",
    "lower_roman",
    "upper_roman",
    "double_lower_alpha",
    "double_upper_alpha",
)


def _marker_matches_kind(token: str, kind: str) -> bool:
    if kind == "digit":
        return token.isdigit() or bool(_DIGIT_HYPHEN_CONTINUATION_RE.match(token))
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


# --- G4 (sprint 2026-08-05-defs-core-follow-on-2): citation/cross-
# reference discriminator for `resolve_unit_path` ---------------------------
#
# The defect: a parenthesized (or, after G2, period-style) token that is
# shape-identical to a genuine marker but actually belongs to a CITATION
# pin-cite ("Section 58-9-576(C)", "47 United States Code, Section
# 522(13)") or an ordinary in-prose CROSS-REFERENCE ("under subsection
# (1) of this section", "paragraph (b) of this subsection") was, before
# this item, indistinguishable from a real structural marker -- silently
# resetting or relabeling the stack `resolve_unit_path` builds below.
#
# The fix: a token is a GENUINE marker unless it is immediately preceded
# (skipping only whitespace) by citation/cross-reference context --
# either (a) one of the SAME closed structural-unit-word vocabulary the
# D-CF guard above uses (`_STRUCTURAL_UNIT_WORDS`), reused here as an
# independent, non-coupled discriminator per that guard's own "no
# coupling between the two features" design note (same semantic story,
# not the same code path), or (b) a citation-number span ending right at
# the token -- mirrors `find_citations`' own patterns (`Section N`, bare
# `§ N`, a full `N U.S.C. § N` federal cite, a `CODE N.N` state-code
# cite), widened here to also accept a hyphen-continued section number
# (SC's own "58-9-576" self-citation shape, which `_SECTION_WORD_RE`
# itself does not match past the first dot-run -- that regex stays
# unchanged; this is an independent pattern for this discriminator only).
_STRUCTURAL_UNIT_WORD_SUFFIX_RE = re.compile(
    r"\b(?:" + "|".join(sorted(_STRUCTURAL_UNIT_WORDS)) + r")\Z",
    re.IGNORECASE,
)
_FULL_USC_CITATION_SUFFIX_RE = re.compile(
    r"\d+\s+U\.S\.C\.\s+§\s*\d+(?:[.\-]\d+)*\Z"
)
_SECTION_CITATION_SUFFIX_RE = re.compile(r"\bSection\s+\d+(?:[.\-]\d+)*\Z")
_LONE_SECTION_CITATION_SUFFIX_RE = re.compile(r"§\s*\d+(?:[.\-]\d+)*\Z")
_BARE_STATE_CODE_CITATION_SUFFIX_RE = re.compile(
    r"\b[A-Z]{2,6}\s+\d+(?:[.\-]\d+)*\Z"
)
# Kept for the committed G4 measurement runner, which scans the original
# undifferentiated citation surface while production selects a branch above.
_CITATION_NUMBER_SUFFIX_RE = re.compile(
    r"(?:"
    r"\d+\s+U\.S\.C\.\s+§\s*\d+(?:[.\-]\d+)*"
    r"|\bSection\s+\d+(?:[.\-]\d+)*"
    r"|§\s*\d+(?:[.\-]\d+)*"
    r"|\b[A-Z]{2,6}\s+\d+(?:[.\-]\d+)*"
    r")\Z"
)

# G4's post-QA newline exception is deliberately narrower than the general
# discriminator: only a parenthesized token after `Section N` or lone `§ N`
# can cross a physical line.  A leading comma, or a parenthetical pin-cite
# chain ending in "of this act", keeps the token on the citation side.
_CROSS_LINE_CITATION_CONTINUATION_RE = re.compile(
    r"[ \t]*(?:,|(?:\((?:[A-Za-z]+|\d+)\)[ \t]*)*of[ \t]+this[ \t]+act\b)",
    re.IGNORECASE,
)

# Chain continuation: once a token is rejected as citation/cross-reference
# context, subsequent tokens joined only by adjacency or a short connector
# (SC's real "(A)(1) or (A)(2)" -- comma and/or "or"/"and") are ALSO
# rejected without needing their own qualifying prefix, until the chain
# breaks. A newline anywhere in the gap always breaks the chain (a
# paragraph break is never "short") -- this is what keeps a genuine
# top-level marker opening the NEXT paragraph from being swept in behind
# an unrelated citation earlier in the previous one.
_CHAIN_CONNECTOR_GAP_RE = re.compile(
    r"[ \t]*,?[ \t]*(?:(?:or|and)[ \t]*)?", re.IGNORECASE
)


def _iter_us_unit_marker_tokens(body: str) -> list[tuple[int, int, str]]:
    """Every candidate marker token in `body`, in document order, merging
    parenthesized tokens (`_US_UNIT_MARKER_RE`) with G2's period-style
    top-level tokens (`_US_PERIOD_UNIT_MARKER_RE`). Each item is `(start,
    end, token)`: `start` is the position the G4 citation-context check
    looks immediately before -- the opening "(" for a parenthesized
    token (so a self-citation's own digits, e.g. "...576(C)", are seen as
    immediately adjacent), or the marker's own first character for a
    period-style token (no bracket to account for); `end` is the position
    right after the token's own closing character (")" or ".") -- used
    both for the caller's `char_offset` cutoff and as the "previous token
    end" a chained rejection continues counting from.
    """
    tokens = [
        (match.start(), match.end(), match.group(1))
        for match in _US_UNIT_MARKER_RE.finditer(body)
    ]
    tokens.extend(
        (match.start(1), match.end(), match.group(1))
        for match in _US_PERIOD_UNIT_MARKER_RE.finditer(body)
    )
    tokens.sort(key=lambda item: item[0])
    return tokens


# Every probe below is a suffix pattern anchored with `\Z` at `trimmed_end`,
# so a match can never start earlier than `trimmed_end - _SUFFIX_PROBE_
# WINDOW` chars back without the window being provably too small. Derived
# from the five patterns themselves (see each pattern's definition above),
# not guessed, and not copied from any test's own headroom constant:
#
#   - `_STRUCTURAL_UNIT_WORD_SUFFIX_RE`: a closed, finite alternation over
#     `_STRUCTURAL_UNIT_WORDS` with no quantifier -- its longest member,
#     "subdivision", is 11 characters. Fully bounded already.
#   - `_FULL_USC_CITATION_SUFFIX_RE`
#     (`\d+\s+U\.S\.C\.\s+§\s*\d+(?:[.\-]\d+)*\Z`), the longest of the four
#     citation-suffix patterns: literal "U.S.C." (6 chars) + "§" (1 char) =
#     7 fixed characters, plus four variable spans that are only ever a
#     *citation's own* digits/whitespace in real statute text (never
#     document-spanning prose) -- a leading title number (real US Code
#     titles run 1-54, so 2 digits; budgeted 4), three whitespace runs
#     between literal tokens (ordinarily one space each; budgeted 8 apiece
#     for stray formatting), and the trailing numeric pin-cite chain
#     (real citations chain at most a handful of dot/hyphen-separated
#     numeric components, e.g. "115-6-2" or "522.13"; budgeted 10
#     components x 5 chars = 50). Sum: 4 + 8 + 6 + 8 + 1 + 8 + 50 = 85.
#   - `_SECTION_CITATION_SUFFIX_RE`, `_LONE_SECTION_CITATION_SUFFIX_RE`,
#     `_BARE_STATE_CODE_CITATION_SUFFIX_RE` are each a strict subset of the
#     full-U.S.C. pattern's shape (shorter literal prefix, same bounded
#     digit-chain tail), so none exceeds 85 either.
#
# 85 chars is therefore a proven upper bound on every real citation shape
# these five patterns recognize -- corroborated independently by the sprint
# contract's own measurement ("a full-U.S.C. cite is the longest, well
# under 100 chars") and by the RED tests' 4096-char ceiling (~40x that same
# ~100-char figure). `_SUFFIX_PROBE_WINDOW` below is set to 512: ~6x this
# derived 85-char bound and ~5x the contract's independently measured
# ~100-char figure, generous headroom for formatting irregularities the
# corpus has not yet been observed to contain, while staying 8x under the
# RED tests' 4096-char ceiling and orders of magnitude below real document
# sizes -- so every probe's cost becomes a small O(1) constant instead of
# O(document position).
_SUFFIX_PROBE_WINDOW = 512


def _citation_or_xref_context(body: str, token_start: int) -> tuple[str | None, int]:
    """Return the immediate context identity and its whitespace-trimmed end.

    Structural words and the four citation suffix branches remain distinct so
    G4's measured cross-newline exception can be limited to `Section` and
    lone-`§` citations.  Uses `search(body, probe_start, trimmed_end)`
    (endpos, not a slice) so `\\Z` anchors at `trimmed_end` without copying
    `body`; `probe_start` is bounded to `_SUFFIX_PROBE_WINDOW` chars back
    from `trimmed_end` since every probe pattern is a suffix match that can
    never legitimately start further back than that (see
    `_SUFFIX_PROBE_WINDOW`'s own comment for the derivation) -- this bounds
    each probe's cost to O(1) instead of O(`trimmed_end`).
    """
    trimmed_end = token_start
    while trimmed_end > 0 and body[trimmed_end - 1].isspace():
        trimmed_end -= 1
    probe_start = max(0, trimmed_end - _SUFFIX_PROBE_WINDOW)
    if _STRUCTURAL_UNIT_WORD_SUFFIX_RE.search(body, probe_start, trimmed_end):
        return "structural", trimmed_end
    if _FULL_USC_CITATION_SUFFIX_RE.search(body, probe_start, trimmed_end):
        return "full_usc", trimmed_end
    if _SECTION_CITATION_SUFFIX_RE.search(body, probe_start, trimmed_end):
        return "section", trimmed_end
    if _LONE_SECTION_CITATION_SUFFIX_RE.search(body, probe_start, trimmed_end):
        return "lone_section", trimmed_end
    if _BARE_STATE_CODE_CITATION_SUFFIX_RE.search(body, probe_start, trimmed_end):
        return "bare_state_code", trimmed_end
    return None, trimmed_end


def _is_citation_or_xref_context(
    body: str, token_start: int, token_end: int, marker_form: str
) -> bool:
    """Whether a candidate marker remains citation/cross-reference context.

    Same-line decisions, structural words, full-U.S.C., bare-state-code, and
    period-style candidates retain the ordinary rejection.  The sole exception
    is a parenthesized candidate following `Section N` or lone `§ N` across a
    whitespace-only gap containing CR or LF, unless its right tail is a known
    citation continuation.
    """
    context, trimmed_end = _citation_or_xref_context(body, token_start)
    if context not in {"section", "lone_section"} or marker_form != "parenthesized":
        return context is not None

    gap = body[trimmed_end:token_start]
    if "\r" not in gap and "\n" not in gap:
        return True
    return bool(_CROSS_LINE_CITATION_CONTINUATION_RE.match(body, token_end))


def resolve_unit_path(article, char_offset: int | None = None):
    """`JurisdictionProfile.resolve_unit_path` for US -- see the module
    comment above. `char_offset=None` returns `()` (the article's own
    base path -- v2.4 correction: `UnitPath` is BELOW-article only, never
    chapter/part information, which callers read off the article's own
    metadata fields instead).

    Ladder selection (I11 + follow-on): chosen ONCE per call, from the
    shape of the first GENUINE marker encountered -- among THREE named
    variants: `_DIGIT_OUTERMOST_UNIT_PATH_LADDER` if it is digit-shaped,
    `_OH_UPPER_ALPHA_OUTERMOST_UNIT_PATH_LADDER` if it is upper_alpha-
    shaped (a single uppercase letter -- see the module comment above for
    why this is an enumerated set of three, not a general per-depth-
    learned mechanism), `_UNIT_PATH_LADDER` (federal) if it is
    lower_alpha-shaped (a single lowercase letter), else -- sprint
    2026-08-05-defs-core-follow-on-2, gate G2, fix step 3 -- ladder
    selection is DEFERRED past that token (it cannot open ANY of the
    three ladders, so it must not consume the "first marker" privilege)
    and the search continues at the next candidate. A token is a
    candidate for ladder selection (and for the stack below) at all only
    if it first survives the G4 citation/cross-reference discriminator --
    see `_is_citation_or_xref_context` above; a token rejected there is
    invisible to ladder selection too, same as it is to the stack.

    Honesty notes (see the Developer report's GENERALIZATION STATEMENT for
    the full enumeration; no test pins any of these, except where a
    sprint-2026-08-05-defs-core-follow-on-2 gate is named below). QA
    cycle 1's full-census scan (all 53 `us_*_statutes.parquet`, 2,038,247
    rows, signal-agnostic denominator) measured this precisely rather
    than leaving it asserted -- corrected here to match what was actually
    found, not what an earlier draft of this note assumed:

    - Genuinely double-alpha-outermost: measured ZERO real rows (the one
      raw shape-candidate found was a citation fragment, not a genuine
      enumeration) -- for THAT shape, a document's outermost marker is
      DEFERRED past for ladder-selection purposes (as of G2 fix step 3;
      previously it fell through to an implicit federal-ladder default
      and was then skipped at position 0 for failing to match any open
      ancestor -- same net non-participation in the returned path either
      way, but the mechanism changed, so this note is updated rather than
      left stale). Every marker after it is classified once a later
      token DOES match one of the three named shapes (which, per the
      measurement, appears not to happen in the real corpus at all for
      this specific shape).
    - Upper_roman-outermost is DIFFERENT, and NOT a skip: measured 5 real
      rows (0.00025% of the corpus) -- `STATE_IL_C820_A405_S1506.6`,
      `STATE_IL_C820_A405_S2101.1`, `STATE_IL_C820_A405_S403`,
      `STATE_NH_TXXI_C266-A_S19`, `STATE_PR_LEY_2_2017_ART2` -- all
      in-sentence PROSE enumerations ("...actuar: (I) recuperando... (II)
      abordando...", "...order: (I) A new charge; or (II) A new rule..."),
      spread across three unrelated jurisdictions, not a drafting
      convention any of them uses structurally. `(I)`/`(V)`/`(X)` are a
      single uppercase letter, so they satisfy the upper_alpha shape check
      above (this shape is inherently ambiguous between upper_alpha and
      upper_roman at length 1, same ambiguity as `i`/`v`/`x`/`l`/`c`/`d`/`m`
      at lower_alpha/lower_roman -- see `_marker_matches_kind`) and route
      the call to the Ohio ladder, where `(I)` IS captured -- as
      `UnitStep(kind='upper_alpha', value='I')` -- not skipped. Its
      genuine roman siblings (`(II)`, `(III)`, ...) are what get skipped
      afterward: they match neither the Ohio ladder's rung 1 (`digit`) nor
      the one open ancestor (`upper_alpha`, which needs length 1). Net
      effect on a real row: exactly ONE spurious `upper_alpha` step,
      frozen for the rest of the call -- bounded and non-cascading, but a
      wrong kind captured, not an absence. Left as a named limitation, not
      fixed here (unaffected by G2/G4 -- this token still passes the G4
      discriminator, since it is genuine prose, not citation context, and
      still shape-matches upper_alpha, so G2 step 3 does not defer past
      it either): the shape is vanishingly rare and prose-incidental
      rather than a jurisdiction convention, and reclassifying it would
      touch the marker-classification path a QA cycle has already signed
      off on.
    - Ladder selection reads only the first GENUINE token's shape (gates
      G2 fix step 3 and G4 narrow this from "first parenthesized token"
      to "first token that both survives the citation/cross-reference
      discriminator and shape-matches one of the three named rungs").
      Residual risk, still open: a token that is noise in some OTHER
      sense -- not citation/cross-reference context, not shape-mismatched
      -- can still wrongly seed the ladder if it happens to be the first
      thing in the body and is not the document's real convention-opener;
      no real corpus row exercising this residual was found while
      implementing G2/G4, but no full-census re-scan was run to confirm
      its absence either, so this is reported as an open risk, not a
      closed one.
    - G4 residual, newly observed while implementing this gate (not
      covered by any test in this sprint, reported per rule D-Q1 rather
      than silently left out): the citation/cross-reference discriminator
      only recognizes the CLOSED `_STRUCTURAL_UNIT_WORDS` vocabulary
      (division, subdivision, article, part, section, title, chapter,
      paragraph, subsection, subchapter) plus `Section`/`§`/U.S.C./state-
      code citation shapes. A cross-reference using a word OUTSIDE that
      vocabulary -- e.g. real SC text "under subitem (3) of this
      subsection" / "provided in item (8)" -- is NOT recognized as
      citation/cross-reference context and is treated as a genuine
      marker, which can transiently mis-set the stack's value until the
      next real marker at that rung overwrites it (bounded, non-cascading
      per row measured, but not zero -- an open gap, not silently closed).
    """
    from app.definition_links.rules.registry import UnitStep

    if char_offset is None:
        return ()

    stack: list = []
    ladder: tuple[str, ...] | None = None
    last_rejected_end: int | None = None
    for start, end, token in _iter_us_unit_marker_tokens(article.body):
        if end > char_offset:
            break
        # G4: citation pin-cite / in-prose cross-reference discriminator --
        # a token immediately continuing an already-rejected token's chain
        # (adjacency or a short connector, no newline in the gap) is
        # rejected without its own qualifying prefix; otherwise it is
        # rejected if IT is itself immediately preceded by citation/
        # cross-reference context. Either way, a rejected token never
        # touches the stack or ladder selection below.
        if last_rejected_end is not None and _CHAIN_CONNECTOR_GAP_RE.fullmatch(
            article.body[last_rejected_end:start]
        ):
            last_rejected_end = end
            continue
        marker_form = "parenthesized" if article.body[start] == "(" else "period"
        if _is_citation_or_xref_context(article.body, start, end, marker_form):
            last_rejected_end = end
            continue
        last_rejected_end = None
        if ladder is None:
            if _marker_matches_kind(token, "digit"):
                ladder = _DIGIT_OUTERMOST_UNIT_PATH_LADDER
            elif _marker_matches_kind(token, "upper_alpha"):
                ladder = _OH_UPPER_ALPHA_OUTERMOST_UNIT_PATH_LADDER
            elif _marker_matches_kind(token, "lower_alpha"):
                ladder = _UNIT_PATH_LADDER
            else:
                # G2 fix step 3: this token cannot open ANY of the three
                # ladders -- defer ladder selection to the next candidate
                # rather than defaulting to federal (real evidence: Maine's
                # leading "(NEW)" revisor annotation must not hijack the
                # ladder for a document whose real convention is
                # digit-outermost).
                continue
        expected_kind = ladder[len(stack)] if len(stack) < len(ladder) else None
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
            # I9: unclassifiable at this position -- SKIPPED, never pushed
            # as a garbage "sub" step (the cascade source this item
            # exists to close). This is the ONLY mechanism that keeps
            # Maine's inline revisor annotations (NEW/AMD/AFF/RP/RPR/REV/
            # COR) out of the path -- an earlier, additional closed-word
            # exclusion list was removed (follow-on batch, program
            # precedent P-E3) once mutation-testing proved it unproven: 6
            # of the 7 codes never shape-match any ladder kind at any
            # position (2-3 letter, non-roman strings), and the 7th,
            # `(RP)`, only shape-matches `double_upper_alpha`, a rung
            # real Maine annotation text never actually reaches (6 open
            # ancestor levels; measured real max nesting is 4) -- so it
            # falls through to here too, in practice, on every real row
            # measured. Citation/cross-reference noise is now caught
            # earlier, above, by the G4 discriminator instead of relying
            # on this fallback -- this branch still exists for the
            # residual, out-of-vocabulary cross-reference gap the
            # docstring's G4 honesty note names, and for any other
            # genuinely unclassifiable token.
            continue
    return tuple(stack)


class BodyPreambleMatch(str):
    """A derived heading carrying the registered rule that won dispatch."""

    def __new__(cls, heading: str, *, b1_winner: bool = False):
        instance = super().__new__(cls, heading)
        instance.b1_winner = b1_winner
        return instance


# Issue #22 (sprint 2026-08-10-green-the-suite, item 2): FED's real
# `USC_T8_C12_S1101` "serious criminal offense" over-captures the NEXT
# structural sibling -- `(h) ... the term "serious criminal offense"
# means-- (1) any felony; (2) ...; (3) ....` is correctly captured, but the
# capture keeps going straight through `(i) With respect to each
# nonimmigrant alien ...`, a completely different subsection at the SAME
# nesting depth as `(h)` itself, plus trailing "Editorial Notes" apparatus.
#
# Root cause: whichever engine produced this candidate (baseline's own
# `_split_into_numbered_blocks`, OR a registered `EntrySplitterRule` like
# `us_markers_inline_quote.py`'s quote-anchored engine -- for THIS row it
# is the latter, confirmed live) has no way to tell "(i)" apart from a
# genuinely NESTED sub-item: at length 1, "i" shape-matches BOTH
# `lower_alpha` (FED's own outermost per-subsection rung, same rung as
# "(h)") AND `lower_roman` (a legitimately DEEPER rung, 3 levels under
# `lower_alpha` per the federal ladder `resolve_unit_path` already uses --
# see that ladder's own module comment). Only the document's own marker
# HISTORY resolves the ambiguity: "(h)" already occupies the outermost
# rung, so a later "(i)" that shape-matches that SAME rung is a SIBLING
# popping the stack back to it, not a child. That is exactly
# `resolve_unit_path`'s own stack-popping semantics -- reused here
# read-only (never modified) rather than duplicated with different rules,
# so this fix and the citation-window discriminator it calls into
# (`_is_citation_or_xref_context`, QA-certified, sprint
# claude/core-g4-discriminator-perf -- NOT touched or re-tuned here) never
# drift apart.
#
# Deliberately a POST-PROCESSING refinement over the FINAL candidate text
# (applied uniformly to every candidate in `USProfile.extract_definitions_
# from_section` below, regardless of which engine produced it), not a
# change to either engine's own boundary logic -- `us_markers_boundary.py`
# and its sibling rule modules are owned by a concurrent sprint and out of
# this file's scope; baseline's own last-block trailing-notes handling
# (`_trailing_notes_boundary`) is untouched. A pure trim can only ever
# SHORTEN a candidate's `definition_text`, never lengthen or reshape it,
# and only fires when it can uniquely relocate that exact text inside the
# section body -- the safest shape available for a fix applied blindly to
# every candidate regardless of origin.
_ANY_UNIT_MARKER_HINT_RE = re.compile(r"\([A-Za-z]+\)|(?:^|\n)[ \t]*[A-Za-z0-9]{1,2}\.[ \t]")

# Supplementary to (never replacing or re-tuning) the certified
# `_is_citation_or_xref_context` -- two independent real-FED-corpus gaps
# in that function's own `_SECTION_CITATION_SUFFIX_RE`, both measured live
# during this item's own mandated corpus scan (see the Developer report):
#
# 1. It requires a capital-S "Section" immediately before a marker to
#    recognize it as citation context. Real USC prose routinely uses a
#    lowercase in-sentence "section" instead -- this item's own FED
#    fixture: `"(h) For purposes of section 1182(a)(2)(E) of this title,
#    the term ..."` -- invisible to that check, which let the citation's
#    own "(a)(2)(E)" pin-cite chain get misread as three genuine nested
#    markers, corrupting the stack this trim depends on (cut "serious
#    criminal offense" down to nothing but its own opening dash).
# 2. It requires the section NUMBER itself to be pure digits
#    (`\d+(?:[.\-]\d+)*`). Real USC section numbers routinely carry a
#    trailing letter suffix from later-inserted sections (`1396a`, `77c`,
#    `1437a`, `1395i–2`) -- invisible to EITHER capitalization, which
#    let citations like `"section 1396a(n)(2)"` get misread the same way
#    (cut "medicare cost-sharing" off mid-citation at "...1396a(n)").
#
# Both closed here, ADDITIVELY, as this function's own extra guard -- the
# certified perf window itself (`_citation_or_xref_context`/`_is_citation_
# or_xref_context`, sprint claude/core-g4-discriminator-perf) is not
# touched.
_CI_SECTION_CITATION_SUFFIX_RE = re.compile(
    r"\bsection\s+\d+[a-z]{0,3}(?:[.\-–]\d+[a-z]{0,3})*\Z", re.IGNORECASE
)


def _is_extra_citation_context(text: str, token_start: int) -> bool:
    trimmed_end = token_start
    while trimmed_end > 0 and text[trimmed_end - 1].isspace():
        trimmed_end -= 1
    probe_start = max(0, trimmed_end - _SUFFIX_PROBE_WINDOW)
    return bool(_CI_SECTION_CITATION_SUFFIX_RE.search(text, probe_start, trimmed_end))


def _next_sequence_value(kind: str, value: str) -> str | None:
    """The literal NEXT marker value after `value` (itself of KIND `kind`),
    for the two kinds cheap and unambiguous to compute -- `digit` (plain
    integer increment) and a single-char `lower_alpha`/`upper_alpha`
    (next letter, `None` past "z"/"Z"). `None` for every other kind
    (roman numerals need real numeral arithmetic, not attempted here) --
    callers that get `None` back simply skip the extra check, per its own
    call site's comment."""
    if kind == "digit" and value.isdigit():
        return str(int(value) + 1)
    if kind in ("lower_alpha", "upper_alpha") and len(value) == 1:
        nxt = chr(ord(value) + 1)
        if kind == "lower_alpha" and nxt.islower():
            return nxt
        if kind == "upper_alpha" and nxt.isupper():
            return nxt
    return None


def _trim_definition_at_structural_sibling(text: str, definition_text: str) -> str:
    """If `definition_text` is a uniquely locatable, contiguous slice of
    the full section `text`, AND this candidate has its own genuine LOCAL
    opening marker (the marker, if any, that starts the PARAGRAPH
    containing `definition_text`'s own start -- FED's real `"(h) For
    purposes of ... the term \"serious criminal offense\" means--"`),
    replay `resolve_unit_path`'s own marker-hierarchy classifier FROM that
    opening marker (never from the start of `text`) to find a later
    marker, still inside `definition_text`'s own span, that pops the
    stack back to that opening marker's own rung -- a structural SIBLING
    of the entry itself, not a nested sub-item of its own list -- and
    truncate right before it. Returns `definition_text` UNCHANGED (never
    longer, never reshaped) whenever it cannot be confidently located in
    `text` (not found, or found more than once), carries no marker-shaped
    token at all (cheap pre-filter), has no PARAGRAPH-ANCHORED opening
    marker of its own, or no sibling is found within its own span.

    The paragraph-anchor requirement is deliberate, not incidental: a
    whole-document scan from offset 0 (tried first, then withdrawn -- see
    the Developer report) mis-seeds on a document holding several
    independent, parallel quoted-term definitions that each carry their
    OWN internal `(i)/(ii)/...` sub-enumeration with no subsection
    lettering of their own at all (real IL shape: `"Alternative retail
    electric supplier"`, `"Base rates"`, `"Competitive service"` all sit
    in one giant unlettered paragraph) -- an EARLIER, wholly unrelated
    definition's own leftover marker state leaked onto a LATER one,
    measured live emptying "Competitive service" down to nothing. A
    candidate whose own paragraph does not itself open with a marker is
    not FED's shape at all and is left untouched.
    """
    if not _ANY_UNIT_MARKER_HINT_RE.search(definition_text):
        return definition_text
    start = text.find(definition_text)
    if start == -1 or text.find(definition_text, start + 1) != -1:
        return definition_text
    end = start + len(definition_text)

    para_start = text.rfind("\n\n", 0, start)
    para_start = 0 if para_start == -1 else para_start + 2
    marker_probe_start = para_start
    while marker_probe_start < start and text[marker_probe_start] in " \t":
        marker_probe_start += 1
    open_match = _MARKER_TOKEN_RE.match(text, marker_probe_start)
    if open_match is None or open_match.end() > start:
        return definition_text
    open_token = open_match.group(0).strip().strip("()")
    open_marker_form = "parenthesized" if text[marker_probe_start] == "(" else "period"
    if _is_citation_or_xref_context(
        text, marker_probe_start, open_match.end(), open_marker_form
    ) or _is_extra_citation_context(text, marker_probe_start):
        return definition_text

    if _marker_matches_kind(open_token, "digit"):
        ladder = _DIGIT_OUTERMOST_UNIT_PATH_LADDER
    elif _marker_matches_kind(open_token, "upper_alpha"):
        ladder = _OH_UPPER_ALPHA_OUTERMOST_UNIT_PATH_LADDER
    elif _marker_matches_kind(open_token, "lower_alpha"):
        ladder = _UNIT_PATH_LADDER
    else:
        return definition_text
    stack: list[str] = [ladder[0]]

    # Consume the REST of the opening marker CHAIN, if any (mirrors
    # `_strip_marker_chain_before_quote`'s own "(d) (1)" chain philosophy,
    # elsewhere in this module) -- a real FED row, `USC_T45_C9_S231`'s
    # `"(b)(1) The term "employee" means (i) any individual..."`, opens
    # with TWO adjacent marker tokens naming ONE combined position
    # (subsection (b), paragraph (1)), not "(b)" followed by a separately
    # NESTED "(1)" inside "employee"'s own content -- without this, the
    # chain's own second token was indistinguishable from genuine
    # within-content nesting and the roman items right after "means"
    # looked, wrongly, like a rung-0 sibling (measured live: emptied
    # "employee" down to nothing).
    chain_end = open_match.end()
    while True:
        next_match = _MARKER_TOKEN_RE.match(text, chain_end)
        if next_match is None or next_match.end() > start:
            break
        marker_form = "parenthesized" if text[chain_end] == "(" else "period"
        if _is_citation_or_xref_context(
            text, chain_end, next_match.end(), marker_form
        ) or _is_extra_citation_context(text, chain_end):
            break
        next_token = next_match.group(0).strip().strip("()")
        expected_kind = ladder[len(stack)] if len(stack) < len(ladder) else None
        if expected_kind is not None and _marker_matches_kind(next_token, expected_kind):
            stack.append(expected_kind)
        else:
            matched_depth = next(
                (i for i, kind in enumerate(stack) if _marker_matches_kind(next_token, kind)),
                None,
            )
            if matched_depth is None:
                break
            stack = stack[: matched_depth + 1]
        chain_end = next_match.end()

    stack_len_at_start: int | None = None
    last_rejected_end: int | None = None
    for tok_start, tok_end, token in _iter_us_unit_marker_tokens(text):
        if tok_start < chain_end:
            continue
        if tok_start >= end:
            break
        if last_rejected_end is not None and _CHAIN_CONNECTOR_GAP_RE.fullmatch(
            text[last_rejected_end:tok_start]
        ):
            last_rejected_end = tok_end
            continue
        marker_form = "parenthesized" if text[tok_start] == "(" else "period"
        if _is_citation_or_xref_context(
            text, tok_start, tok_end, marker_form
        ) or _is_extra_citation_context(text, tok_start):
            last_rejected_end = tok_end
            continue
        last_rejected_end = None

        if tok_start >= start and stack_len_at_start is None:
            # How deep the stack already was, from the opening marker
            # CHAIN alone, just before this candidate's own real content
            # (past `start`) contributes anything of its own.
            stack_len_at_start = len(stack)

        expected_kind = ladder[len(stack)] if len(stack) < len(ladder) else None
        if expected_kind is not None and _marker_matches_kind(token, expected_kind):
            stack.append(expected_kind)
            continue
        matched_depth = None
        for i, kind in enumerate(stack):
            if _marker_matches_kind(token, kind):
                matched_depth = i
                break
        if matched_depth is None:
            continue
        # A single-char token (e.g. "i") is ambiguous between `lower_alpha`
        # and `lower_roman` -- real FED rows measured BOTH real shapes for
        # it: a genuine sibling popping back to the opening rung (this
        # item's own gate, "(h)...(1)(2)(3)...(i) With respect..." -- a
        # DIGIT rung was genuinely pushed WITHIN the entry's own content)
        # and a genuine DEEPER roman-numeral list opening DIRECTLY under
        # the entry's own rung with no intermediate rung at all (real FED
        # row `USC_T5_C6_S601`'s own `"Specified agency heads"
        # means:\n\n(i) the Attorney General;\n\n(ii) ...` -- measured
        # live: without this guard, the trim emptied it down to its bare
        # idiom). Only a pop back to the opening rung (`matched_depth ==
        # 0`) AFTER the stack grew STRICTLY DEEPER than it already was at
        # `start` (i.e. something real, like FED's own `(1)(2)(3)` digit
        # list, was pushed by content INSIDE the entry, not merely by its
        # own opening marker chain) is treated as a sibling; anything
        # else cannot distinguish "sibling" from "first item of a
        # legitimately deep list" at all, so it is left alone.
        #
        # `sequence_ok` closes a THIRD real shape, also found by this
        # item's own corpus scan: `USC_T31_C38_S3801`'s `"obligation"` is
        # item `(11)` of subsection (a)'s own digit list; a SEPARATE,
        # SIBLING subsection `"(b) For purposes of paragraph (3) of
        # subsection (a)--\n\n(1) each voucher, ..."` follows -- its OWN
        # inner `(1)` shape-matches `digit` (the opening rung) and, having
        # been genuinely pushed one level deeper by "(b)" first, passed
        # the `len(stack) > stack_len_at_start` guard above too, cutting
        # "obligation" off mid-subsection. `(1)` is nowhere near "(11)"'s
        # own next real sibling ("(12)") -- for the two kinds cheap to
        # verify (plain digit increment; next single letter), the popped-
        # to token must be the LITERAL next value after the entry's own
        # opening marker to count as its sibling. Kinds `_next_sequence_
        # value` cannot compute (roman numerals) fall back to the guards
        # above alone, unchanged.
        next_expected = _next_sequence_value(ladder[0], open_token) if matched_depth == 0 else None
        sequence_ok = next_expected is None or token == next_expected
        if (
            tok_start >= start
            and matched_depth == 0
            and stack_len_at_start is not None
            and len(stack) > stack_len_at_start
            and sequence_ok
        ):
            return definition_text[: tok_start - start].rstrip()
        stack = stack[: matched_depth + 1]
    return definition_text


# Sprint 2026-08-20-defs-boundary-idioms, Item 2 (issue #27 amendment):
# `USProfile.extract_definitions_from_section`'s fallback-suppression guard
# (~line 2551) merges the broader `_extract_inline_quoted_definitions`
# fallback with the primary engine's own candidates instead of only running
# it when the primary engine found nothing. Every admitted fallback
# candidate must survive `_is_implausible_fallback_capture` below -- applied
# UNIFORMLY, whether the primary engine found zero candidates (the
# always-existed suppressed-fallback path) or some (the newly merged path).
_FALLBACK_STOPWORD_TERMS = frozenset(
    {"for", "and", "or", "the", "a", "an", "of", "in", "to", "with", "by"}
)
_FALLBACK_CAPTION_YEAR_RE = re.compile(r"^\d{4}[—–-]")
# Director ruling 2026-08-23 (expansion-wave precision sample,
# `2026-08-20-defs-boundary-idioms-scripts/expansion_precision.md`):
# extends the implausible-capture rejection to a fallback term containing
# the literal `"Pub. L."` or matching `Subsec\.\s*\(` -- the actual
# measured/shipped shape tolerates the real "Subsec. (" space seen in every
# sampled false positive (Planner micro-pass 3's precision correction to
# the ruling's own `Subsec.\(` shorthand).
_FALLBACK_SUBSEC_TERM_KEY_RE = re.compile(r"Subsec\.\s*\(")


def _is_implausible_fallback_capture(candidate: DefinitionCandidate) -> bool:
    """Reject an otherwise-admissible `_extract_inline_quoted_definitions`
    candidate that is not a real definiendum: a bare common-English-
    function-word term (closed list, matches the observed "for" phantom),
    a legislative-history amendment-caption shape (a 4-digit year
    immediately followed by an em/en dash or hyphen, matches the observed
    "2010—Subsec. ..." phantom), a term containing "Pub. L.", or a
    term matching `Subsec\\.\\s*\\(` (the director's 2026-08-23 extension,
    matching the sampler's garbage-term-key false positives)."""
    for term in candidate.terms:
        stripped = term.strip()
        if stripped.lower() in _FALLBACK_STOPWORD_TERMS:
            return True
        if _FALLBACK_CAPTION_YEAR_RE.match(stripped):
            return True
        if "Pub. L." in term:
            return True
        if _FALLBACK_SUBSEC_TERM_KEY_RE.search(term):
            return True
    return bool(_FALLBACK_CAPTION_YEAR_RE.match(candidate.definition_text.strip()))


# Sprint 2026-08-23-defs-debt-31, Item 1 (issue #31 debt class 1 -- "next-
# entry bleed on wave additions"). `_extract_inline_quoted_definitions`'s
# own entries run to the START of the next recognized quote+idiom entry
# or `len(text)`, with NO trailing-stop/ceiling of its own (confirmed by
# reading the whole function -- no such call exists); `_leading_quote_
# candidate` (the per-block leading-quote parser both baseline's own
# `_split_into_numbered_blocks` and every registered `EntrySplitterRule`'s
# blocks are parsed with) has the SAME gap -- `block[term_match.end():]
# .strip()`, no trailing-stop of its own either. `us_markers_boundary.
# close_entries`'s own `bounded`/`MAX_CLEAN_DEFINITION_LENGTH` ceiling
# calc is the FX7 ceiling itself (gate 4, already proven unsafe to widen)
# and is NEVER touched here -- everything below is an INDEPENDENT new
# trim path, TRIM-only (D-RECALL-FP: an anchor's TERM is never dropped;
# only `definition_text` bytes change, and only ever get shorter).
#
# Applied to EVERY block-derived candidate `USProfile.extract_definitions_
# from_section` builds AND every candidate `_merge_fallback_candidates`
# returns (primary-sourced or fallback-admitted alike): live corpus
# verification (this sprint's own real-row exemplars) found the identical
# unbounded-bleed shape on candidates the PRIMARY engine (baseline
# `_split_into_numbered_blocks`, or a registered `EntrySplitterRule` built
# on `us_markers_boundary.extract_quote_anchored_entries`) already
# produced -- real NY `STATE_NY_ASOS_A6_T1_S390` "Enrolled legally exempt
# provider" and real FED `USC_T5_C75_S7511` "furlough" BOTH reach their
# FINAL, persisted `Definition.definition_text` via baseline's own
# numbered-block splitter, not via `_extract_inline_quoted_definitions` at
# all -- and FED's own row is reached with `heading_was_derived=False`
# (`"Definitions; application"` is directly recognized, one of the 7
# already-`section_title`-working states), so scoping the trim to
# `_merge_fallback_candidates` alone (which only ever runs when `heading_
# was_derived`) would silently miss it. Only OH `STATE_OH_T49_C4905_
# S4905.331` "Proceeding" is genuinely fallback-sourced. Precision risk is
# bounded by requiring the relaxed marker checks below to sit at a REAL
# sentence end (a literal period immediately before, not merely "not a
# lowercase letter") -- see `_fallback_bleed_trim_end`'s own note -- which
# structurally excludes both a marker glued right after an idiom (real
# `"X" means (a) ...` -- the char before "(a)" is the idiom's own trailing
# lowercase letter, not a period) and a semicolon-joined internal
# enumeration that is genuinely part of ONE definition (real `"X" means
# (a) cash; (b) securities; and (c) real property.` -- the char before
# "(b)"/"(c)" is ";", not "."), the two shapes that would otherwise make a
# looser marker check unsafe to run this broadly.
#
# `compute_hard_stops` (imported, not reimplemented) already finds a
# marker hard-stop SAFELY for the shapes it covers -- reused unmodified
# via `_fallback_bleed_trim_end` below (its own internal-enumeration-run
# and list-introducer protections apply exactly as they do for the
# PRIMARY engine). Two gaps real bleeding rows hit, which `compute_hard_
# stops`'s own stricter gates do not reach on their own, get narrow,
# additive checks instead of a widened shared-engine rule (never touching
# the shared engine itself):
#   - a letter-paren marker (`(B)`/`(b)`) opening an ordinary prose
#     sentence, not itself another quoted defined term (OH's own "(B) No
#     electric distribution utility ..."; FED furlough's own "(b) This
#     subchapter does not apply..."; FED 12889's own "(c) The term...").
#     `compute_hard_stops`'s own letter-marker check additionally
#     requires a QUOTE within its own short lookahead (correct for the
#     PRIMARY engine, which must tell a genuine sibling ENTRY apart from
#     a nested non-defining sub-item -- see that module's own docstring);
#     irrelevant here, where the only question is "has this candidate's
#     own true content already ended", not "is what follows itself
#     another definition".
#   - a bare digit-dot marker (`2.`) NOT anchored to a physical line
#     start -- `compute_hard_stops`'s own `_DIGIT_DOT_MARKER_RE` is
#     `(?:^|\n)`-anchored, so it silently never fires for the 9
#     effectively-no-newline jurisdictions (NH/SC/PR/NY/UT/OH/IL/WA/NJ,
#     known trap; confirmed live against real NY `STATE_NY_ASOS_A6_T1_
#     S390`'s own "...services.\n  2. * (a) Child day care centers..."
#     and this sprint's own zero-newline structural control).
# Each relaxed check requires a literal period (optional trailing
# whitespace/newlines) immediately before the marker -- deliberately
# NARROWER than `us_markers_boundary._preceded_by_sentence_or_clause_
# boundary` (which only excludes "mid-word", not "mid-enumeration") --
# and additionally excludes a digit-dot token glued onto another digit or
# a bare dot (`(?<![\d.])`, the SAME citation-number guard `_TRAILING_
# MARKER_CHAIN_RE` already uses elsewhere in this module family), so a
# real citation like OH's own "Chapters 4909. and 4928." is never
# mistaken for a marker.
_FALLBACK_TRIM_LETTER_PAREN_RE = re.compile(r"\([A-Za-z]{1,4}\)")
_FALLBACK_TRIM_DIGIT_DOT_RE = re.compile(r"(?<![\d.])\d{1,3}\.(?=[ \t])")
_FALLBACK_TRIM_PRECEDING_PERIOD_RE = re.compile(r"\.\s*\Z")
# A short, SPACE-FREE token ending in a period (`Sec.`, `Subsec.`,
# `Pub.`, a lone word) is a citation-ABBREVIATION's own period or a bare
# label, not a genuine sentence end, even though it satisfies the plain
# period check above -- confirmed live on TWO independent real shapes:
# `test_us_markers_fallback_guard_term_key_negative_control.py`'s own
# `"Subsec. (b)(3). Some historical amendment note..."` synthetic term-
# key (quoted prose INSIDE a genuine, already-correct definition's own
# body -- the short word sits right after a QUOTE-open), and real FED
# `USC_T21_C13_S801`'s own baseline-block "(7) Director, Office of
# National Narcotics Intelligence, Department of Justice." candidate
# (itself a mis-split numbered clause from a quoted Executive Order, a
# separate, pre-existing primary-engine defect out of this item's own
# scope -- but its OWN definition_text starts "Sec. 5. The Attorney
# General..." with NOTHING before "Sec." at all, not even a quote, so
# the first check alone missed it: the short word sits right at
# `definition_start` itself). A REAL sentence this trim is meant to
# catch always has multiple words before its terminal period; a bare
# abbreviation/label never does, regardless of what (if anything)
# precedes it -- checked directly (a bounded lookback for the nearest
# quote/period CLAUSE boundary, deliberately NOT a newline: real
# statutory prose hard-wraps mid-sentence, e.g. NY's own "...family\n
# services." -- treating `\n` as a boundary here would wrongly exclude
# that real, validated stop) rather than enumerating specific
# abbreviation strings, so it generalizes to any short label, not just
# the two named above.
_CLAUSE_BOUNDARY_CHAR_RE = re.compile(r'["“”.]')
_WHITESPACE_RE = re.compile(r"\s")
_ABBREVIATION_LOOKBACK = 60


def _period_precedes_a_real_sentence(text: str, period_pos: int, definition_start: int) -> bool:
    window_start = max(definition_start, period_pos - _ABBREVIATION_LOOKBACK)
    window = text[window_start:period_pos]
    boundary_positions = [m.end() for m in _CLAUSE_BOUNDARY_CHAR_RE.finditer(window)]
    clause_start = boundary_positions[-1] if boundary_positions else 0
    clause = window[clause_start:]
    return bool(_WHITESPACE_RE.search(clause.strip()))

# A marker immediately preceded (skipping only whitespace) by a QUOTE
# character is a per-paragraph quote-REOPEN followed by an internal list
# item of the SAME quoted block -- e.g. real FED `USC_T50_C44_S3024`'s
# own "covered element of the intelligence community" means the
# following:\n\n"(1) The Office of the Director of National
# Intelligence.\n\n"(2) The Central Intelligence Agency.\n\n"(3) ..." --
# NOT a genuine sibling-entry boundary. `compute_hard_stops`'s own
# REUSED digit-marker check (its `_AFTER_MARKER_UPPER_RE` branch) is
# designed for the opposite, PRIMARY-engine direction -- MARKER then
# quote or uppercase word signals a NEW term -- and has no notion that a
# quote can come FIRST as a paragraph-reopen (the exact shape `_extract_
# inline_quoted_definitions`'s own `_is_paragraph_start_quote`/`_find_
# block_quote_close` already handle for TERM-pairing, but which this
# module's reused `compute_hard_stops` cannot see at all). Confirmed
# live: reusing `hard_stops` unfiltered here regressed 146 real FED/etc.
# candidates in a 10-jurisdiction scoped population sample alone (before
# fixing), each collapsed from a genuine multi-hundred/thousand-char
# enumerated definition down to ~11-17 chars ending right at the FIRST
# re-opened quote. Applied only to the REUSED `hard_stops` list -- this
# module's own two relaxed checks already require a literal PERIOD
# immediately before (never a quote) and so were never exposed to this.
_QUOTE_CHAR_IMMEDIATELY_BEFORE_RE = re.compile(r'["“”]\s*\Z')
_QUOTE_CHAR_LOOKBACK = 8


def _hard_stop_is_inside_quoted_block(text: str, pos: int) -> bool:
    window = text[max(0, pos - _QUOTE_CHAR_LOOKBACK) : pos]
    return bool(_QUOTE_CHAR_IMMEDIATELY_BEFORE_RE.search(window))


# A THIRD real gap, found the same way as the previous two (population-
# scale re-measurement, not speculated): a BASELINE-sourced candidate's
# own `definition_text` (via `_leading_quote_candidate`) is never idiom-
# stripped at all -- `block[term_match.end():].strip()` keeps "means"/
# "shall mean"/etc. as the LITERAL first word(s) of the text, unlike
# `_extract_inline_quoted_definitions`'s own candidates. When such a
# definition legitimately OPENS with an enumeration marker right after
# its own idiom (real NY `STATE_NY_ATAX_A8_S171-T`'s own `"Debt" means
# (i), for purposes of state debt, a "tax debt" as\ndefined in section
# ...`), `compute_hard_stops`'s own REUSED letter-marker check can find
# a quote shortly after that FIRST marker (here, `"tax debt"`, a nested
# quoted cross-reference within the SAME first enumerated item, not a
# sibling entry) and treat it as a hard-stop -- collapsing the whole
# candidate down to the bare idiom word itself ("means", 5 chars).
# `_period_precedes_a_real_sentence`'s OWN period requirement structurally
# guards this module's two relaxed checks (a period can never appear
# within a handful of characters of `definition_start`), but the REUSED
# `hard_stops` list has no such requirement of its own. Guarded here
# instead: a genuine definition is never just its own bare idiom word --
# a REUSED hard-stop landing within `_MIN_CONTENT_BEFORE_REUSED_STOP`
# characters of `definition_start` is untrusted (every real, validated
# stop this item's own tests exercise closes off SUBSTANTIALLY more
# content than this).
_MIN_CONTENT_BEFORE_REUSED_STOP = 20


def _whole_text_hard_stops(text: str) -> list[int]:
    """`compute_hard_stops(text, len(text))`'s own `hard_stops` list,
    computed ONCE for the FULL `text` -- a performance fix (not a
    behavior change): a per-CANDIDATE call inside a row with many
    candidates on a long body (real FED `USC_T5_C6_S601`, 403,285 chars,
    42 baseline candidates) cost 19.6s for that ONE row alone,
    `compute_hard_stops` being O(len(text)) and re-run from scratch per
    candidate. `compute_hard_stops`'s own marker-run tracking is a
    strictly sequential left-to-right scan of `text[0:limit]`, so a
    LARGER `limit` (the full text, a safe superset) never changes the
    classification of any marker at a position before a SMALLER
    candidate-specific `end` -- filtering this same precomputed list to
    `< end` per candidate (done by callers) is byte-identical to calling
    `compute_hard_stops(text, end)` fresh each time, just computed once
    per row instead of once per candidate."""
    from app.definition_links.rules.us_markers_boundary import compute_hard_stops

    hard_stops, _mn_subd_stops, _digit_based_stops = compute_hard_stops(text, len(text))
    return hard_stops


def _fallback_bleed_trim_end(
    text: str, definition_start: int, end: int, hard_stops: list[int]
) -> int:
    """The earliest position in `[definition_start, end)` where a
    structural marker signals this candidate's own true content has
    already ended -- `end` itself (unchanged) when no such position is
    found. `hard_stops` is `_whole_text_hard_stops(text)`, computed ONCE
    per row by the caller (performance -- see that function's own note).
    See the module note above for the exact checks and why each is
    safe."""
    stops: list[int] = [
        hs
        for hs in hard_stops
        if definition_start + _MIN_CONTENT_BEFORE_REUSED_STOP <= hs < end
        and not _hard_stop_is_inside_quoted_block(text, hs)
    ]
    for pattern in (_FALLBACK_TRIM_LETTER_PAREN_RE, _FALLBACK_TRIM_DIGIT_DOT_RE):
        for m in pattern.finditer(text, definition_start, end):
            period_match = _FALLBACK_TRIM_PRECEDING_PERIOD_RE.search(text, definition_start, m.start())
            if not period_match:
                continue
            if not _period_precedes_a_real_sentence(text, period_match.start(), definition_start):
                continue
            stops.append(m.start())
    return min(stops) if stops else end


# A trailing marker FRAGMENT leaked from the NEXT entry's own opening onto
# THIS candidate's tail -- `_extract_inline_quoted_definitions` bounds an
# entry at the next recognized entry's own QUOTE start, so a marker that
# precedes that quote (NY's own "\n  b. "Bakery tray" means...", "\n  e.
# "Egg basket" means...") leaks in as dangling debris. Newline-anchored
# (real line-start marker only, matching this module family's own
# line-anchored marker convention) so an ordinary trailing abbreviation or
# initial (`"...refer to Exhibit A."`) is never mistaken for one -- unlike
# `us_markers_boundary._TRAILING_MARKER_CHAIN_RE` (paren-wrapped or
# digit-dot tokens only), this also covers a bare LOWERCASE letter-dot
# token (`_TRAILING_MARKER_CHAIN_RE` only ever needs to strip primary-
# engine debris, which is case-insensitive already at that marker family;
# the fallback's own next-entry markers are frequently lowercase-lettered
# list items, e.g. NY's "a."/"b."/"c." container-term list).
_FALLBACK_TRAILING_MARKER_FRAGMENT_RE = re.compile(
    r"\n[ \t]*(?:\([\w]{1,4}\)|(?<![\d.])\d{1,3}\.|[A-Za-z]\.)[ \t]*\Z"
)

# A trailing sentence FRAGMENT with no terminal punctuation of its own --
# the shape a fallback-reached candidate's boundary produces when it is
# cut off by hitting the NEXT recognized entry's own quote mid-clause, not
# at a sentence end (real WA `STATE_WA_T10_C99_S080` "convicted": ends
# "...or the levying of a fine. For the purposes of this section," -- a
# dangling list-introducer-style stub belonging to the NEXT entry,
# "domestic violence", not to "convicted" itself; no marker token appears
# anywhere in it for either check above to find). Bounded to a short
# trailing fragment (`_FALLBACK_DANGLING_TAIL_MAX` chars) so a
# legitimately long definition that simply lacks a final period for some
# unrelated reason is never chopped mid-content -- only a SHORT dangling
# tail is ever removed, and only back to the end of the last complete
# sentence (period/semicolon/closing-quote) already inside the
# candidate's own text, never past it.
_SENTENCE_TERMINAL_CHARS = (".", ";", '"', "”", "'", "’")
_FALLBACK_DANGLING_TAIL_MAX = 120


def _clean_fallback_trailing_bleed(definition_text: str) -> str:
    """Post-process an already end-trimmed (`_fallback_bleed_trim_end`)
    candidate's `definition_text`: strip OH's own scrape-metadata tail
    (`_LAST_UPDATED_TAIL_RE`, reused unmodified -- OH's own `_split`
    already applies this on the PRIMARY path; a fallback-reached
    candidate bypassed it entirely until now), then a leaked next-entry
    marker fragment, then a short dangling non-terminal tail. Never
    returns an empty string when `definition_text` was non-empty
    (D-RECALL-FP): each step is skipped, not forced, when it would
    otherwise reduce the text to nothing."""
    from app.definition_links.rules.us_markers_oh_trailing_clause import (
        _LAST_UPDATED_TAIL_RE,
    )

    cleaned = definition_text
    without_tail = _LAST_UPDATED_TAIL_RE.sub("", cleaned).strip()
    if without_tail:
        cleaned = without_tail
    without_fragment = _FALLBACK_TRAILING_MARKER_FRAGMENT_RE.sub("", cleaned).strip()
    if without_fragment:
        cleaned = without_fragment
    if cleaned and cleaned[-1] not in _SENTENCE_TERMINAL_CHARS:
        best = -1
        for ch in _SENTENCE_TERMINAL_CHARS:
            idx = cleaned.rfind(ch)
            if idx > best:
                best = idx
        if best != -1 and best < len(cleaned) - 1:
            tail = cleaned[best + 1 :].strip()
            if tail and len(tail) <= _FALLBACK_DANGLING_TAIL_MAX:
                shortened = cleaned[: best + 1].strip()
                if shortened:
                    cleaned = shortened
    return cleaned


def _trim_fallback_candidate_bleed(
    text: str, candidate: DefinitionCandidate, hard_stops: list[int]
) -> None:
    """Mutates `candidate.definition_text` in place, TRIMMING (D-RECALL-FP:
    never dropping the candidate itself) trailing bleed per `_fallback_
    bleed_trim_end` and `_clean_fallback_trailing_bleed`. Only acts when
    `definition_text` is a UNIQUELY locatable, literal substring of `text`
    -- same safety precedent already established by `_trim_definition_at_
    structural_sibling` elsewhere in this module; left unchanged (never
    guessed at) when it is not found, or found more than once.
    `hard_stops` is `_whole_text_hard_stops(text)`, computed ONCE by the
    caller and shared across every candidate for this same `text`
    (performance -- see that function's own note)."""
    start = text.find(candidate.definition_text)
    if start == -1 or text.find(candidate.definition_text, start + 1) != -1:
        return
    end = start + len(candidate.definition_text)
    new_end = _fallback_bleed_trim_end(text, start, end, hard_stops)
    sliced = text[start:new_end].strip()
    if not sliced:
        return
    cleaned = _clean_fallback_trailing_bleed(sliced)
    if cleaned and cleaned != candidate.definition_text:
        candidate.definition_text = cleaned


def _merge_fallback_candidates(
    candidates: list[DefinitionCandidate], text: str, *, scope: str
) -> list[DefinitionCandidate]:
    """Item 2 (issue #27 amendment): merge, don't suppress. Always runs
    `_extract_inline_quoted_definitions` when called (the caller gates this
    on `heading_was_derived`) and admits a fallback candidate only when
    none of its own terms collide with a term already found by the primary
    engine on this row (`candidates`, as passed in -- per-term admission,
    design (b) in the Planner's pass-2 report), AND it survives
    `_is_implausible_fallback_capture`. When `candidates` is empty this
    reduces to "every filtered fallback candidate" -- the same population
    the always-existed zero-candidate path used to substitute unfiltered.

    Item 1 (sprint 2026-08-23-defs-debt-31): every NEWLY fallback-admitted
    candidate (appended below) gets an independent bleed trim (`_trim_
    fallback_candidate_bleed`) -- `_extract_inline_quoted_definitions`
    itself has no trailing-stop of its own at all (real OH `STATE_OH_
    T49_C4905_S4905.331` "Proceeding"). Deliberately NOT applied to the
    pre-existing `candidates` argument passed in: those already went
    through `USProfile.extract_definitions_from_section`'s own block-
    processing loop, which applies the SAME trim ONLY to its own
    BASELINE-sourced blocks (see that loop's own comment) -- a candidate
    from a registered `EntrySplitterRule` (already correctly bounded via
    `close_entries`) or a `TermClauseRule` (its own, separate extraction
    mechanism, out of this item's scope) must never be re-touched here;
    doing so once regressed `test_us_markers_fallback_guard_term_key_
    negative_control.py` (a WA `EntrySplitterRule`-sourced candidate) and
    `test_mr121_b1_source_truth_red.py` (a `TermClauseRule`-sourced R7
    designation candidate) during this item's own development -- both
    confirmed live, corrected by narrowing to this exact scope."""
    fallback_candidates = _extract_inline_quoted_definitions(text, scope=scope)
    primary_terms = {term for candidate in candidates for term in candidate.terms}
    merged = list(candidates)
    hard_stops: list[int] | None = None
    for candidate in fallback_candidates:
        if any(term in primary_terms for term in candidate.terms):
            continue
        if _is_implausible_fallback_capture(candidate):
            continue
        if hard_stops is None:
            # Computed once per row, lazily (only when at least one
            # candidate needs it), and shared across every candidate
            # below -- performance fix, see `_whole_text_hard_stops`'s
            # own note (a per-candidate call cost 19.6s for one real,
            # very long FED row alone).
            hard_stops = _whole_text_hard_stops(text)
        _trim_fallback_candidate_bleed(text, candidate, hard_stops)
        merged.append(candidate)
    return merged


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

    def heading_recognized_only_by_rule(self, heading: str, body: str = "") -> bool:
        """True when ONLY a registered `HeadingRule` recognizes this heading.

        The baseline literal check is authoritative when it fires, so this is
        false for the 7 states already working off `section_title` -- their
        behavior stays byte-for-byte unchanged. It is true for the class
        registered rules add (verb-form `"X" defined`, compound/mid-token
        headings), where the heading is a reliable signal but the body is
        inline prose the `(N)`-block splitter cannot parse. `pipeline.py` uses
        it to keep the inline-quoted fallback reachable for that class.
        """
        from app.definition_links.rules import registry

        if is_definitions_heading(heading):
            return False
        return any(
            rule.matches(heading) and (rule.body_confirms is None or rule.body_confirms(body))
            for rule in registry.heading_rules_for(self.code)
        )

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
        self, text: str, *, scope: str, heading_was_derived: bool = False, raw_source: str | None = None,
        b1_winner: bool | None = None
    ) -> list[DefinitionCandidate]:
        """Sprint 2026-08-04-defs-core-dispatch, item I3: `EntrySplitterRule`/
        `TermClauseRule` are UNION kinds -- baseline's own numbered blocks
        (`_split_into_numbered_blocks`) are unioned with every registered
        `EntrySplitterRule`'s own raw blocks for this profile's code, then
        EVERY block (baseline or rule-contributed) is run through
        baseline's own per-block leading-quote parser AND every registered
        `TermClauseRule.parse` -- zero-miss, no rule suppresses another.
        (Sprint 2026-08-05-defs-core-follow-on-2, gate G10, seam v2.9: a
        rule offering `parse_scoped` is dispatched with a `TermClauseContext`
        carrying this method's own `scope` instead, so the rule sees the
        section's real determined scope rather than being forced to guess
        or hardcode one -- `parse` itself is unchanged and still the
        dispatch target for every rule that does not opt in.)
        The `heading_was_derived` inline-quoted fallback still runs last,
        only when the union above produced nothing, preserving the exact
        "zero-risk for the 7 already-working states" guarantee (baseline-
        only behavior, no rules registered, is byte-identical to calling
        the bare `extract_definitions_from_section` function directly)."""
        from app.definition_links.rules import registry

        baseline_blocks = _split_into_numbered_blocks(text)
        priority_blocks: list[str] = []
        extra_blocks: list[str] = []
        for rule in registry.entry_splitter_rules_for(self.code):
            if rule.priority_before_single_baseline:
                priority_blocks.extend(rule.split(text))
            else:
                extra_blocks.extend(rule.split(text))
        if len(baseline_blocks) == 1:
            all_blocks = priority_blocks + baseline_blocks + extra_blocks
        else:
            all_blocks = baseline_blocks + priority_blocks + extra_blocks

        candidates: list[DefinitionCandidate] = []
        # Computed once per row, lazily (only when at least one baseline
        # block below actually needs the Item 1 trim), and shared across
        # every candidate in this loop -- performance fix: a per-
        # candidate `compute_hard_stops` call cost 19.6s for one real,
        # very long FED row alone (`USC_T5_C6_S601`, 403,285 chars, 42
        # candidates). See `_whole_text_hard_stops`'s own note.
        block_hard_stops: list[int] | None = None
        for block in all_blocks:
            candidate = _leading_quote_candidate(block, scope=scope)
            if candidate is not None:
                # Item 1 (sprint 2026-08-23-defs-debt-31): scoped to
                # BASELINE-sourced blocks (`block in baseline_blocks`,
                # not every block in `all_blocks` -- a registered
                # `EntrySplitterRule` built on `us_markers_boundary.
                # extract_quote_anchored_entries`, e.g. `us_markers_
                # inline_quote.py`, already produces a correctly-bounded
                # synthetic block via `close_entries`; only baseline's
                # own `_split_into_numbered_blocks` + this per-block
                # leading-quote parser has no trailing-stop of its own
                # at all), further gated to the TWO populations live
                # verification found this exact unbounded shape on:
                #   - `heading_was_derived` articles (NY/CA/IL/GA-style
                #     placeholder-heading states -- real NY `STATE_NY_
                #     ASOS_A6_T1_S390` "Enrolled legally exempt
                #     provider"), zero-risk for the 7 already-`section_
                #     title`-working states by construction (this flag
                #     is always False for them);
                #   - US-FED specifically (real `USC_T5_C75_S7511`
                #     "furlough", reached with `heading_was_derived=
                #     False` -- FED's own "Definitions" heading is
                #     directly recognized) -- the SAME scope `_trim_
                #     definition_at_structural_sibling` immediately below
                #     already uses, for the SAME reason its own docstring
                #     gives: corpus measurement found no marker-
                #     structure-only signal that separates a genuine FED
                #     over-capture from several OTHER jurisdictions' own
                #     PINNED, intentionally-kept baseline captures of the
                #     identical shape.
                # Confirmed live: broadening this to EVERY jurisdiction
                # (dropping this gate) regressed the `test_us_markers_
                # c5guard_{mi,nd,nj,ny,ok}.py` and `test_us_markers_qa_
                # q1_wa_newline_collapse_swallow.py` guard estate.
                if block in baseline_blocks and (heading_was_derived or self.code == "US-FED"):
                    if block_hard_stops is None:
                        block_hard_stops = _whole_text_hard_stops(text)
                    _trim_fallback_candidate_bleed(text, candidate, block_hard_stops)
                candidates.append(candidate)
        for block in all_blocks:
            for rule in registry.term_clause_rules_for(self.code):
                if rule.parse_scoped is not None:
                    candidates.extend(
                        rule.parse_scoped(block, registry.TermClauseContext(scope=scope))
                    )
                else:
                    candidates.extend(rule.parse(block))

        if heading_was_derived:
            candidates = _merge_fallback_candidates(candidates, text, scope=scope)
        if heading_was_derived:
            from app.definition_links.rules.us_body_preamble_b1 import (
                is_b1_rule,
                plural_anaphora_repairs,
                preserve_substantive_b1_candidates,
            )

            raw = raw_source if raw_source is not None else text
            if b1_winner is None:
                for rule in registry.body_preamble_rules_for(self.code):
                    if rule.derive_heading(text) is not None:
                        b1_winner = is_b1_rule(rule.derive_heading)
                        break
            if b1_winner:
                candidates = preserve_substantive_b1_candidates(candidates, raw)
                retained_terms = {term for candidate in candidates for term in candidate.terms}
                candidates.extend(
                    repair
                    for repair in plural_anaphora_repairs(
                        raw,
                        scope=scope,
                        candidate_factory=lambda term, definition_text, candidate_scope: DefinitionCandidate(
                            terms=(term,), definition_text=definition_text, scope=candidate_scope
                        ),
                    )
                    if all(term not in retained_terms for term in repair.terms)
                )

        # Issue #22 (item 2): applied LAST, regardless of which engine
        # above produced a given candidate -- see the trim function's own
        # module-level comment for why this lives here as a
        # post-processing refinement rather than inside any one engine.
        # US-FED ONLY (this profile serves every "US-*" code, sprint
        # 2026-08-02-us-state-law item 3): issue #22 and its own fixture
        # are entirely about a federal row, and this item's own corpus
        # measurement (see the Developer report) found the SAME marker
        # shape -- an opening letter/digit marker, then a later marker at
        # that same rung -- pinned as CORRECT, desired baseline capture by
        # several unrelated `test_us_markers_c5guard_*.py` regression
        # guards for MI/ND/NJ/OK ("Regression guard -- not a target"),
        # each explicitly out of THIS item's scope and reserved for the
        # still-RED, separately tracked `test_us_markers_c5guard_class_b_
        # boundary_defects.py` family. No marker-structure-only signal
        # found separates FED's real over-capture from those states' own
        # pinned (if arguably also imperfect) captures -- scoping to the
        # one jurisdiction this issue actually names is the safe
        # boundary, not row/term-specific (M-R107 bars keying on rows/
        # terms/sections/titles/sentences, not on jurisdiction code, which
        # this profile's own architecture already dispatches everything
        # else by, e.g. `resolve_unit_path`'s ladder selection).
        if self.code == "US-FED":
            for candidate in candidates:
                candidate.definition_text = _trim_definition_at_structural_sibling(
                    text, candidate.definition_text
                )
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

    def determine_scope_assignments(
        self, body_text: str, *, scope: str, article_number: str, chapter: str | None
    ) -> tuple[registry.ScopeAssignment, ...]:
        """(G6, sprint 2026-08-05-defs-core-follow-on-2, seam v2.8 §3):
        ADDITIVE -- does not change `determine_scope`'s own signature,
        contract, or return value. Replays `determine_scope`'s OWN
        baseline-first, first-non-None-wins dispatch exactly (same
        baseline free function, same registry walk, same order), so "the
        winning rule" is always identical between the two methods by
        construction. `scope` is the kind `determine_scope` already
        returned for this same `body_text` -- used only to build the
        narrow, self-referential DEFAULT assignment (never re-derived
        independently, never a broadening default, M9)."""
        from app.definition_links.rules import registry

        default = registry.default_scope_assignment(
            scope, article_number=article_number, chapter=chapter
        )
        if determine_scope(body_text) == "chapter":
            return (default,)
        for rule in registry.scope_kind_rules_for(self.code):
            detected = rule.detect(body_text)
            if detected is not None:
                if rule.detect_value is not None:
                    assignment = rule.detect_value(body_text)
                    if assignment is not None:
                        return assignment if isinstance(assignment, tuple) else (assignment,)
                return (default,)
        return (default,)

    def derive_body_preamble_match(
        self,
        heading: str,
        body: str,
        *,
        raw_source: str,
        article_number: str,
        chapter: str | None,
    ) -> str | None:
        """B1-capable pipeline entrypoint carrying raw source without widening other profiles."""
        return self.derive_heading_from_body(
            heading,
            body,
            raw_source=raw_source,
            article_number=article_number,
            chapter=chapter,
        )

    def derive_heading_from_body(
        self,
        heading: str,
        body: str,
        *,
        raw_source: str | None = None,
        article_number: str = "",
        chapter: str | None = None,
    ) -> str | None:
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
                from app.definition_links.rules.us_body_preamble_b1 import is_b1_rule

                if is_b1_rule(rule.derive_heading):
                    raw = raw_source if raw_source is not None else body
                    scope = self.determine_scope(body)
                    local_candidates = self.extract_local_scope_definitions(
                        body,
                        article_number=article_number,
                        chapter=chapter,
                        raw_source=raw,
                        b1_winner=True,
                    )
                    section_candidates = self.extract_definitions_from_section(
                        body,
                        scope=scope,
                        heading_was_derived=True,
                        raw_source=raw,
                        b1_winner=True,
                    )
                    if not local_candidates and not section_candidates:
                        return None
                    return BodyPreambleMatch(derived, b1_winner=True)
                return derived
        return None

    def extract_local_scope_definitions(
        self, article_body: str, *, article_number: str, chapter: str | None = None,
        raw_source: str | None = None, b1_winner: bool = False
    ) -> list[DefinitionCandidate]:
        """Unions candidates from every registered `ScopeTriggerRule` for
        this profile's own code (initially the one core-authored proof
        rule, `rules/us_scope_trigger_proof.py`; family panels add more,
        C2/C4) over an ORDINARY (non-Definitions-heading) article body.
        A rule that leaves `.source_article_number` unset (the common
        "local to THIS article" case) gets it defaulted here to
        `article_number`; a rule that stamps its OWN target (e.g. an
        enumerated/cross-article scope, M9) is respected unchanged.

        G5 (sprint 2026-08-05-defs-core-follow-on-2): `ctx.unit_path` is
        computed via the SAME bound resolver as `ctx.resolve_unit_path`
        (at `char_offset=None`, correctly `()` -- no match position exists
        yet at this whole-body-scan point), instead of a bare `()`
        literal, so a future change to `resolve_unit_path`'s own
        None-handling can never leave this stale. `ctx.resolve_unit_path`
        lets a rule ask for the REAL path at ITS OWN match offset (not
        known until the rule's own regex finds it) -- byte-identical to
        calling `self.resolve_unit_path(article, offset)` directly, zero
        duplicated logic."""
        from app.definition_links.rules import registry

        article_stub = SimpleNamespace(body=article_body)

        def _resolve(offset: int) -> registry.UnitPath:
            return self.resolve_unit_path(article_stub, offset)

        ctx = registry.RuleContext(
            article_number=article_number,
            chapter=chapter,
            unit_path=self.resolve_unit_path(article_stub, None),
            resolve_unit_path=_resolve,
        )
        candidates: list[DefinitionCandidate] = []
        for rule in registry.scope_trigger_rules_for(self.code):
            for candidate in rule.extract(article_body, ctx):
                if candidate.source_article_number is None:
                    candidate.source_article_number = article_number
                candidates.append(candidate)
        if b1_winner:
            from app.definition_links.rules.us_body_preamble_b1 import preserve_substantive_b1_candidates

            candidates = preserve_substantive_b1_candidates(
                candidates, raw_source if raw_source is not None else article_body
            )
        return candidates

    def resolve_unit_path(self, article, char_offset: int | None = None):
        return resolve_unit_path(article, char_offset)
