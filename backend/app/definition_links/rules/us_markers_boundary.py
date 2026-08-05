"""Shared boundary-detection ENGINE for the `defs-us-markers` family (family
3 -- "the Definitions heading IS recognized, but the extractor yields zero
(or garbage)"). No registration happens here; this module is imported by
the sibling rule modules in this package (`us_markers_inline_quote.py`,
`us_markers_unquoted_terms.py`, `us_markers_mojibake.py`,
`us_markers_fl_scope_trigger.py`) and holds ONLY the pure-function core they
all share, kept separate to stay under the 300-line-per-file convention.

Manager ruling U-R1 ("captured" means captured CLEANLY -- right term AND
right boundary) drives every design choice below; each guard here closes a
REAL defect confirmed live against a real vendored row (see the sprint log
`## P1`/`## P2` and each fixture's own docstring):

- `_TIGHT_IDIOM_RE` requires the defining idiom (means/shall mean/has the
  meaning) to sit essentially IMMEDIATELY after a quoted term's closing
  quote (only a short punctuation/marker/"and its variants" gap is
  tolerated), except for a bounded statutory relative qualifier ("when
  used in reference to ...", "when used to indicate ...", or "with
  respect to ...") ending in a comma -- never merely "means" appearing
  anywhere within an unbounded lookahead window, which is exactly the bug that collapsed
  `STATE_VA_T4.1_SII_C6_S4.1-600`'s `"sell"` (inside `"Sale" and "sell"
  includes ... by any means.`) to a 1-char definition: the word "means"
  legitimately appears later in that sentence ("by any means") but is not
  SELL's own defining idiom. The same tight gate correctly rejects
  `STATE_WA_T9A_C04_S110`'s nested `"motor vehicle"` (inside `"Vehicle"
  means a "motor vehicle" as defined in the vehicle and traffic laws, ...
  by mechanical means or by sail;`) as a phantom top-level term.
- When several quoted terms share ONE defining clause via "or"
  (`STATE_VA_T23.1_SI_C3_S23.1-300`'s `"Enrollment" or "student
  enrollment" means ...`), only the LAST quote before the idiom is
  recognized -- per-term multiterm fan-out is `defs-us-multiterm`
  territory (seam doc constraint #4), not this family's.
- `_DIGIT_MARKER_RE`/`_LETTER_MARKER_RE` hard-stop detection closes a
  block at a numbered/lettered marker EVEN WHEN that marker's own entry
  doesn't use a recognized idiom -- required so
  `STATE_UT_T75B_S75B_1_301`'s `"Insolvent"` does not swallow the
  following `"Paid and delivered"`/`"Personal property"` entries (real
  idiom "does not include"/"includes", not yet supported). The digit
  marker is boundary-worthy when followed by an uppercase letter or a
  quote (a new top-level clause); the LETTER marker additionally requires
  a quote within a short lookahead (with no intervening period) --
  otherwise a genuinely nested, non-defining sub-item like
  `STATE_TX_Cfi_C37_S37.001`'s `(1) fire, flood, ...` (a lowercase
  continuation of "including:") or `STATE_WA_T9A_C04_S110`'s `(a) To
  cause bodily injury ...` (an uppercase-but-non-defining infinitive
  sub-clause of "Threat") would be wrongly treated as a sibling entry
  boundary. Adjacent marker CHAINS (`STATE_FL_TXXXIII_C540_S540.11`'s
  `(2)(a) It is unlawful:`) are walked through as one unit before this
  check, mirroring `us_profile.py`'s own `_strip_marker_chain_before_
  quote` chain philosophy.
- `_DIGIT_DOT_MARKER_RE`/`_LETTER_DOT_MARKER_RE` close a block at a bare
  `N.`/`X.` (no parens) marker at the START of its own line -- the SAME
  hard-stop philosophy as the paren-wrapped case, for shapes parens don't
  cover (a digit-dot top-level entry marker, e.g. AZ's own convention; a
  single-uppercase-letter-dot top-level SUBSECTION marker, e.g. "F. The
  following apply to ..."). Corpus self-verification (this sprint's own
  required measurement, not a fixture) caught the real defect
  `_DIGIT_DOT_MARKER_RE` closes: `STATE_AZ_T20_C3_A1_S510`'s second
  `"qualified actuary"` entry, lacking this guard, ran 20,925 chars past
  its own ~120-char real definition -- through an entirely unrelated
  `"F. ... 1. Every company with outstanding life insurance contracts,
  ..."` block -- because nothing bounded it before the next tight-idiom
  quote match, many paragraphs away. Line-anchored (`(?:^|\n)`), not
  "anywhere in the text": AZ's own real numbered sub-items inside a
  definition's own body (`STATE_AZ_T15_C14_A7_S1871`'s `(a)`/`(b)`/roman
  numerals) never sit at the start of a line the same way, so this cannot
  fire on legitimate nested content.
- **The list-introducer exclusion** -- applied to EVERY marker check
  above, not only the dot-marker ones -- is what makes hard-stop
  detection safe at all: a marker is NEVER treated as a hard-stop when
  the text immediately before it (skipping only whitespace) ends in `:`
  or an em dash `—`, because that punctuation itself says "the following
  list IS this clause's own content." Two real, otherwise-indistinguishable
  corpus rows prove why this must be a text-level check, not a marker-shape
  rule: `STATE_AZ_T20_C3_A1_S510`'s pathological `"qualified actuary"`
  case ends its OWN sentence with a period BEFORE the unrelated "F. ..."
  begins (no colon/dash immediately before "F." -- hard-stop correctly
  fires), while `STATE_AZ_T28_C16_A4_S5857`'s legitimate `"agricultural
  products" means either:\n\n1. Crops, livestock, ...` (colon immediately
  before "1." -- hard-stop correctly suppressed, so "1. Crops, ..." stays
  part of the definition) and a real FED em-dash case,
  `USC_T21_C9_S321`'s `"new drug" means—\n\n(1) Any drug ...` (em dash
  immediately before "(1)" -- suppressed for the same reason, even though
  "(1)" is otherwise a perfectly ordinary digit-paren hard-stop shape).
  Both punctuation marks are genuine, real US statutory list-introducer
  conventions confirmed on real rows, not a guess.
- `_TRAILING_MARKER_CHAIN_RE` strips a marker fragment that leaks onto the
  END of the PRECEDING entry (`STATE_SC_T5_C1_S5-1-20`'s `"Municipality"`
  ending in a literal `"(2)"`; `STATE_AZ_T15_C14_A7_S1871`'s "Qualified
  higher education expenses" ending in a literal `"13."`) -- the marker
  belongs to the NEXT entry, not this one. The `\\d{1,3}\\.` alternative
  carries a `(?<![\\d.])` guard immediately before each digit-dot token: a
  genuine statutory citation of the shape `NNN.NNN.` (e.g. `STATE_TX_
  Cgv_C2009_S2009.003`'s `"Governmental body" has the meaning assigned by
  Section 552.003.`) is, without the guard, INDISTINGUISHABLE from two
  back-to-back digit-dot marker tokens ("552." then "003.", glued with no
  separating whitespace the way real leaked markers always have) -- the
  guard blocks a digit-dot token from starting immediately after another
  digit or a bare dot, so a dotted citation number is never partially or
  wholly consumed as marker-chain noise, while a real trailing single
  marker (preceded by whitespace, per the SC/AZ examples above) or a
  whitespace-separated chain (`"... (a) (b)"`) still strips correctly.
- `MAX_CLEAN_DEFINITION_LENGTH` is a last-resort safety net for the
  UNBOUNDED shape specifically, not a bare across-the-board precision
  boundary: corpus self-verification (the required before/after
  measurement, not any fixture) found dozens of real rows where a
  genuinely LAST-in-section entry -- no next quote+idiom match anywhere
  further in the body, and no marker hard-stop nearby either (an
  architecturally identical shape to the FED baseline-splitter "unbounded
  last entry" defect this sprint's own test file documents as
  unreachable without a shared-module edit, see `us_markers_unbounded_
  last_entry.py`) -- swallows tens of thousands of unrelated trailing
  characters (e.g. a real FED "State" entry reaching 22,880 chars). A
  SEPARATE QA pass (QA1 Q4) proved a bare "drop anything over 3000"
  ceiling is not harmless either: it silently discarded genuine long
  definitions that ARE structurally closed by a real boundary --
  `STATE_VA_T47.1_C1_S47.1-2`'s "Satisfactory evidence of identity"
  (~3,020-3,332 chars, correctly bounded by the real next `"Seal" means`
  term, one coherent notary-law provision throughout) was captured by NO
  path at all (dropped by the ceiling; no baseline candidate exists for
  this body shape either). The ceiling therefore applies ONLY to
  candidates with NO real closing boundary found (`bounded` is `False`
  in `extract_quote_anchored_entries`: no hard-stop marker AND no
  subsequent quoted+idiom term) -- exactly the FED/TN/AZ "ran off the end
  of the text with nothing to close it" shape the 3,000-char measurement
  above documents. A candidate closed by a real hard-stop marker or a
  real next term is exempt regardless of length: its length reflects
  genuine statutory content up to a real boundary, not a runaway swallow
  -- the right side of ruling U-R1's "captured cleanly, or not captured
  at all" bar, now for BOTH failure directions (false swallow AND false
  miss) rather than trading one for the other.
- `_TRAILING_STOP_RE` truncates the whole working text at the first
  non-operative annotation tail (FED's "Editorial Notes"/"References in
  Text"/"(Pub. L. ...)" citation block, SC's "Effect of Amendment", TN's
  "Added by <year>") -- confirmed live on `USC_T16_C65_S4503d`,
  `USC_T15_C12_S431`, `STATE_SC_T5_C1_S5-1-20`, `STATE_TN_T50_C2_
  S50-2-115` -- so no entry can swallow commentary appended after the
  operative text.
"""

from __future__ import annotations

import re

_LEADING_QUOTE_TERM_RE = re.compile(r'["“]([^"”]{1,200})["”]')

# Optional trailing punctuation, an optional single-letter-paren marker
# (AZ's "12. "Qualified higher education expenses":\n\n(a) Means:" shape),
# and an optional "and its variants" connector (RI's `"System of
# registration" and its variants means ...`) may sit between the closing
# quote and the idiom itself -- but nothing else. This is what makes the
# gate TIGHT: an idiom found only because it happens to occur somewhere
# later in an unrelated sentence never qualifies.
_TIGHT_IDIOM_RE = re.compile(
    r'[,;:]?\s*(?:\([a-zA-Z]\)\s*)?(?:and its variants\s+)?'
    r'(?:(?:when used (?:in reference to|to indicate)|with respect to)\s+'
    r'[^.\n]{1,300}?,\s*)?'
    r'(?:means|shall mean|has the meaning)\b:?\s*',
    re.IGNORECASE,
)

_DIGIT_MARKER_RE = re.compile(r"\(\d{1,3}\)\s*")
_LETTER_MARKER_RE = re.compile(r"\([A-Za-z]{1,4}\)\s*")
_ANY_MARKER_TOKEN_RE = re.compile(r"\(\w{1,4}\)\s*")
_DIGIT_DOT_MARKER_RE = re.compile(r"(?:^|\n)[ \t]*\d{1,3}\.[ \t]+")
# A bare single-uppercase-letter-dot top-level subsection marker at the
# start of its own line (e.g. AZ's "F. The following apply to ...") --
# the SAME line-anchored shape as `_DIGIT_DOT_MARKER_RE`, for the
# letter-dot convention rather than digit-dot.
_LETTER_DOT_MARKER_RE = re.compile(r"(?:^|\n)[ \t]*[A-Z]\.[ \t]+")
# Minnesota's statutory subsection headings bound the preceding definition
# even when the following heading does not itself contain a recognized idiom.
_MN_SUBD_HEADER_RE = re.compile(r"(?:^|\n\n)§\s*Subd\.\s+\d{1,3}\.\s+")
_AFTER_MARKER_UPPER_OR_QUOTE_RE = re.compile(r'^[A-Z"“]')
_QUOTE_WITHIN_LOOKAHEAD_RE = re.compile(r'^[^.\n"“]{0,40}["“]')
# See this module's own docstring, "The list-introducer exclusion".
_LIST_INTRODUCER_BEFORE_RE = re.compile(r"[:—]\s*$")


def _preceded_by_list_introducer(text: str, marker_start: int) -> bool:
    return bool(_LIST_INTRODUCER_BEFORE_RE.search(text[:marker_start]))

_TRAILING_MARKER_CHAIN_RE = re.compile(
    r"(?:\s*(?:\([\w]{1,4}\)|(?<![\d.])\d{1,3}\.)\s*)+$"
)

# See this module's own docstring for why this exists and why 3000 -- a
# last-resort defensive ceiling for the UNBOUNDED shape only (see
# `extract_quote_anchored_entries`'s own `bounded` check), not a bare
# across-the-board precision boundary rule.
MAX_CLEAN_DEFINITION_LENGTH = 3000

TRAILING_STOP_RE = re.compile(
    r"\bEditorial Notes\b"
    r"|\bReferences in Text\b"
    r"|\bStatutory Notes\b"
    r"|\bCongressional Findings\b"
    r"|\bEffect of Amendment\b"
    r"|\bHistory:"
    r"|\bAdded by \d{4}\b"
    r"|\n\n\(Pub\. L\."
    r"|\n\n\([A-Z][a-z]{2,8}\.\s+\d{1,2},\s+\d{4}"
)


def extract_quote_anchored_entries(text: str) -> list[tuple[str, str]]:
    """`text` (an already-mojibake-repaired, if applicable, section/article
    body) -> `[(term, definition_text), ...]`, each boundary-clean per this
    module's docstring. Pure text in, pure data out -- callers (this
    package's other rule modules) decide how to wrap the result for their
    own registered rule kind."""
    stop = TRAILING_STOP_RE.search(text)
    limit = stop.start() if stop else len(text)

    starts: list[tuple[int, str, int]] = []
    for m in _LEADING_QUOTE_TERM_RE.finditer(text, 0, limit):
        idiom_m = _TIGHT_IDIOM_RE.match(text, m.end(), limit)
        if idiom_m is None:
            continue
        term = m.group(1).strip().removesuffix(",").rstrip()
        if not term:
            continue
        starts.append((m.start(), term, idiom_m.end()))

    hard_stops: list[int] = []
    for m in _DIGIT_MARKER_RE.finditer(text, 0, limit):
        if _preceded_by_list_introducer(text, m.start()):
            continue
        chain_end = m.end()
        while True:
            chain_m = _ANY_MARKER_TOKEN_RE.match(text, chain_end, limit)
            if chain_m is None:
                break
            chain_end = chain_m.end()
        if _AFTER_MARKER_UPPER_OR_QUOTE_RE.match(text[chain_end : chain_end + 1]):
            hard_stops.append(m.start())
    for m in _LETTER_MARKER_RE.finditer(text, 0, limit):
        if _preceded_by_list_introducer(text, m.start()):
            continue
        if _QUOTE_WITHIN_LOOKAHEAD_RE.match(text[m.end() : limit]):
            hard_stops.append(m.start())
    for pattern in (_DIGIT_DOT_MARKER_RE, _LETTER_DOT_MARKER_RE):
        for m in pattern.finditer(text, 0, limit):
            if _preceded_by_list_introducer(text, m.start()):
                continue
            if _AFTER_MARKER_UPPER_OR_QUOTE_RE.match(text[m.end() : m.end() + 1]):
                hard_stops.append(m.start())
    hard_stops.extend(m.start() for m in _MN_SUBD_HEADER_RE.finditer(text))

    entries: list[tuple[str, str]] = []
    for idx, (_qstart, term, dstart) in enumerate(starts):
        has_next_term = idx + 1 < len(starts)
        next_start = starts[idx + 1][0] if has_next_term else limit
        candidate_stops = [hs for hs in hard_stops if dstart < hs < next_start]
        end = min([next_start, *candidate_stops])
        # A candidate is structurally BOUNDED when something REAL closes
        # it -- an explicit marker hard-stop, or a genuine subsequent
        # quoted+idiom term -- rather than the candidate simply running off
        # the end of the working `text`/section with nothing found to
        # close it. MAX_CLEAN_DEFINITION_LENGTH guards ONLY the latter,
        # UNBOUNDED shape (the same "unbounded last entry" defect family
        # as the FED/TN/AZ swallows this module's docstring documents): a
        # bounded candidate's length reflects real content up to a real
        # boundary -- long because the statute is long, not because it
        # swallowed a neighbour -- so the ceiling does not apply to it
        # (`STATE_VA_T47.1_C1_S47.1-2`'s genuine ~3,020-3,332-char
        # "Satisfactory evidence of identity", bounded by the real next
        # `"Seal" means` term, is exactly this shape).
        bounded = bool(candidate_stops) or has_next_term
        raw = _TRAILING_MARKER_CHAIN_RE.sub("", text[dstart:end])
        definition_text = raw.strip()
        if not definition_text:
            continue
        if not bounded and len(definition_text) > MAX_CLEAN_DEFINITION_LENGTH:
            continue
        entries.append((term, definition_text))
    return entries


def entries_to_quoted_blocks(entries: list[tuple[str, str]]) -> list[str]:
    """`[(term, definition_text), ...]` -> synthetic `'"term" definition_text'`
    strings -- the shape `us_profile._leading_quote_candidate` (baseline,
    already applied to every `EntrySplitterRule`-contributed block per
    `USProfile.extract_definitions_from_section`) already knows how to
    parse. Reusing that shared helper -- rather than each rule module
    building its own `DefinitionCandidate` -- is what threads the SECTION's
    real `scope` value through automatically (baseline calls `_leading_
    quote_candidate(block, scope=scope)` with the actual per-call scope;
    an `EntrySplitterRule` has no `scope` parameter of its own to get
    right or wrong)."""
    return [f'"{term}" {definition_text}' for term, definition_text in entries]
