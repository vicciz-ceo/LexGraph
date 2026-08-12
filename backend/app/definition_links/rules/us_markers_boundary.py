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
  tolerated). The default shared-engine path deliberately does not accept
  a relative qualifier, a trailing term comma cleanup, or an MN `Subd.`
  heading stop: those are explicit default-off options for MN's registered
  caller. With `allow_relative_qualifiers=True`, a bounded statutory
  relative qualifier ("when
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
- `clean_trailing_term_commas=True` removes a final comma from a quoted
  term, and `stop_at_mn_subd_headers=True` recognizes `§ Subd. N.` headings
  as hard stops. Both are MN-only opt-ins; callers that omit them preserve
  the pre-P-D2 shared-engine behavior byte-for-byte.
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
- `_EXCLUSION_CLAUSE_BRIDGE_RE` (issue #25, sprint 2026-08-10-green-the-
  suite) bridges the gap between a term's own closing quote and its own
  idiom ACROSS a `"Term," (as distinguished from|except as used in)
  "excluded phrase[s]," means ...` disambiguation aside -- NV UCC's own
  convention, confirmed live on `STATE_NV_T8_C104_S104.1201`/`...
  S104.9102` (Agreement/Contract/Party/Account/Accounting/Assignee/
  Record). Without this bridge, the tight gate skips the OUTER term (no
  idiom immediately after its own quote) and instead matches the INNER
  excluded quote (immediately followed by `," means`), capturing the real
  term's own definition text under the excluded phrase's WRONG name and
  losing the real term entirely -- an anchor LOSS, not a mere quality
  defect. Unlike `allow_relative_qualifiers`, this bridge is always on
  (not opt-in): its trigger is a specific, narrow phrase pair immediately
  followed by a QUOTED exclusion, structurally distinct from -- and far
  narrower than -- the "means somewhere later in the sentence" shape
  ruling U-R1 guards against, so it is safe as a default across every
  caller. Every quote consumed as part of a successful bridge is recorded
  in `excluded_spans` and skipped by the main loop, so the excluded
  phrase(s) never separately qualify as their own definiendum -- the
  actual fix, not just an addition alongside the old defect (see
  `extract_quote_anchored_entries`'s own loop).
- `trailing_stop_limit`/`compute_hard_stops`/`close_entries` are
  `extract_quote_anchored_entries`'s own three phases (trim to the
  trailing-stop limit; find marker hard-stops; close each `starts` entry
  against them) factored out as their own reusable functions (sprint
  2026-08-10-green-the-suite, item FX1) so a sibling rule module with its
  OWN idiom-recognition regex -- a quote-to-idiom gap shape this module's
  own tight gate structurally cannot bridge without corpus-wide risk (see
  `_TIGHT_IDIOM_RE`'s own entry above) -- still gets this module's
  already-proven boundary-closing behavior (hard-stop markers,
  `MAX_CLEAN_DEFINITION_LENGTH`'s unbounded-only ceiling,
  `_TRAILING_MARKER_CHAIN_RE`) instead of reinventing a weaker version of
  it. `us_markers_ok_gapidiom.py` (OK's `"X" as used in this <act|
  chapter|...>  <means|shall mean|has the meaning>` gap-idiom shape) is
  the first such caller. `extract_quote_anchored_entries` itself is
  unchanged in behavior -- it now simply calls these three phases in
  sequence rather than inlining them.
- **The citation-vs-marker discriminator** (issue #21, sprint 2026-08-10-
  green-the-suite) closes the NJ/ND/OK "class-B" boundary-defect cluster --
  a mid-citation digit misread as a hard-stop, a genuine internal
  enumeration misread as sibling entries, or a next entry's own marker
  leaking onto the end of the preceding one -- with three narrow,
  structural refinements to the machinery above, none of which key on a
  jurisdiction, term, section number, date, or title (manager ruling
  M-R107):
  - **The trailing-marker-chain strip's own scope**: `_TRAILING_MARKER_
    CHAIN_RE` now fires ONLY when an entry closes by reaching the next
    captured quote with ZERO hard-stops found in between (`not
    candidate_stops and has_next_term`). When a real hard-stop closed the
    entry instead, the marker that triggered it already sits outside the
    slice -- nothing genuine is left to strip, and stripping anyway risks
    eating a real trailing citation number that merely LOOKS like a marker
    token (`STATE_ND_T57_C57-02_S57-02-01`'s "...chapters 57-06 and
    57-32." bounded by the real next "3." entry -- its own "32." is not
    leaked debris). When there is no next term at all (a genuinely
    unbounded last entry, e.g. `STATE_NJ_T58_C22_S22-3`'s "facility"), the
    strip is equally out of scope -- it never had a "next entry's leaked
    marker" to remove in the first place.
  - **The digit-paren sentence/clause boundary requirement**
    (`_preceded_by_sentence_or_clause_boundary`): the digit-paren
    after-check's uppercase branch now additionally requires the marker
    itself to sit at a sentence/clause break, not mid-sentence -- checked
    by looking at the single character immediately before the marker
    (skipping only whitespace): a lowercase letter means "still inside a
    word" (`STATE_OK_T68_S68-701`'s "means one (1) United States standard
    gallon" -- the `(1)` sits mid-quantity, "United" being capitalized is
    coincidence, not a boundary), while anything else -- punctuation, the
    start of the text, OR another marker glued immediately before it
    (`USC_T8_C12_S1101`'s citation note "section (a)(15)(H)(i)", where
    "(15)" sits directly against "(a)"'s own closing paren) -- is a real
    boundary. The quote branch is unaffected (a quote immediately after a
    marker is already a far stronger signal and needs no extra check --
    `STATE_UT_T75B_S75B_1_301`'s "(5)" must keep hard-stopping regardless
    of what precedes it).
  - **The digit-paren run's membership** (`_digit_paren_run_internal_
    content_starts`): a colon/dash-introduced digit-paren run's own item 1
    decides, once, whether the WHOLE run is genuine sibling entries or one
    entry's own internal enumeration -- derived from what item 1 itself
    opens with, a quoted term or an ALL-CAPS label (`_ALL_CAPS_LABEL_OPEN_
    RE`, a corpus finding: `STATE_AL_T1_C21_S22-21-260`'s "(1) ACQUISITION."
    convention), never from the punctuation between later members
    (semicolon vs period is not a reliable signal on its own --
    `STATE_AK_T44_C44.42_S44.42.900`'s semicolon-joined TOP-LEVEL list
    would be wrongly suppressed by a punctuation-based rule, and this one
    is not). If item 1 opens with neither (ordinary prose, e.g.
    `STATE_ND_T51_C51-19_S51-19-02`'s "(1) A franchisee is granted the
    right ..."), every STRICTLY CONSECUTIVE successor (2, 3, 4, ...)
    inherits the "internal content" verdict as a FALLBACK ONLY (issue #28)
    -- inheritance never overrides a successor's own direct evidence: a
    successor whose own opener independently shows the same signal that
    would have made item 1 itself read as genuine (a quote or an ALL-CAPS
    label immediately after its marker) is judged on that evidence instead,
    regardless of what individually precedes it. `STATE_SC_T31_C3_A1_
    S31-3-20`'s item 1, "(1) The term "director" shall mean ...", is
    ordinary prose (no bare leading quote), so the run defaults to
    "internal" -- but item (16), "(16) "Obligee of the authority" or
    "obligee" shall include ...", opens with its own quote right after the
    marker and so keeps its hard-stop despite the inherited verdict, so it
    is no longer swallowed whole into the preceding "Persons of low income"
    entry (15). See `_digit_paren_run_internal_content_starts`'s own
    docstring for the full account, including why a successor's own idiom
    need not be one `_TIGHT_IDIOM_RE` recognizes ("shall include" is not)
    for this override to apply. Separately, the bare dot-marker chain-walk
    (`_walk_glued_dot_marker_chain`) now traverses a glued bare letter-dot
    sub-marker before its own after-check, so `STATE_ND_T51_C51-19_
    S51-19-02`'s "5. a. "Franchise" means ..."/"14. a. (1) "Sale" ..."
    shape hard-stops at "5."/"14." directly instead of leaking the glued
    "N. a." fragment onto the PRECEDING entry.
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
    r'(?:means|shall mean|has the meaning)\b:?\s*',
    re.IGNORECASE,
)
_TIGHT_IDIOM_WITH_RELATIVE_QUALIFIER_RE = re.compile(
    r'[,;:]?\s*(?:\([a-zA-Z]\)\s*)?(?:and its variants\s+)?'
    r'(?:(?:when used (?:in reference to|to indicate)|with respect to)\s+'
    r'[^.\n]{1,300}?,\s*)?'
    r'(?:means|shall mean|has the meaning)\b:?\s*',
    re.IGNORECASE,
)

# Issue #25 (NV UCC): `"Term," (as distinguished from|except as used in)
# "excluded phrase[, "phrase2", ... and "phraseN"]," means ...` -- a bounded,
# always-on bridge (unlike `allow_relative_qualifiers`, not opt-in) between a
# term's own closing quote and its own idiom, ONLY across this specific,
# recognizable disambiguation phrase pair immediately followed by at least
# one quoted exclusion. `[^.\n]{0,400}?` (lazy) deliberately excludes
# periods/newlines from the bridged span so an unrelated sentence boundary
# can never be silently swallowed -- confirmed against both real NV UCC rows
# (`STATE_NV_T8_C104_S104.1201`, `STATE_NV_T8_C104_S104.9102`), including
# `"Account"`'s own 7-quote exclusion list interspersed with non-quoted
# annotation text (`"commodity account" in paragraph (o), ...`) and
# `"Record"`'s `and`-joined final pair. Deliberately does NOT match
# `"Original debtor" means, except as used in subsection 3 of NRS
# 104.9310, ...` (idiom precedes the clause, and the clause names an
# unquoted subsection, not a quoted phrase) -- that shape is unaffected
# because the tight/relative-qualifier gate above already matches it
# directly (its own "means" sits immediately after the quote).
_EXCLUSION_CLAUSE_BRIDGE_RE = re.compile(
    r'[,;:]?\s*(?:as distinguished from|except as used in)\s+'
    r'["“][^.\n]{0,400}?["”]\s*'
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
_MN_SUBD_HEADER_RE = re.compile(r"(?:^|\n\n)§\s*Subd\.\s+\d{1,3}[a-z]?\.\s+")
_AFTER_MARKER_UPPER_OR_QUOTE_RE = re.compile(r'^[A-Z"“]')
_AFTER_MARKER_QUOTE_RE = re.compile(r'^["“]')
_AFTER_MARKER_UPPER_RE = re.compile(r"^[A-Z]")
_QUOTE_WITHIN_LOOKAHEAD_RE = re.compile(r'^[^.\n"“]{0,40}["“]')
# See this module's own docstring, "The list-introducer exclusion".
_LIST_INTRODUCER_BEFORE_RE = re.compile(r"[:—]\s*$")
# See this module's own docstring, "The digit-paren sentence/clause boundary
# requirement" -- the uppercase branch of the digit-paren after-check is
# only trustworthy when the marker itself sits at a sentence/clause break,
# not mid-sentence (a bare quantity like "one (1) United States standard
# gallon" is never a boundary just because "United" happens to be
# capitalized). The one structural signal that reliably tells the two
# apart, checked directly against a real FED citation-note regression this
# guard was written to fix: a marker embedded IN a lowercase word ("one
# (1)") is never a boundary, while a marker preceded by anything else --
# punctuation (AL's "law.", AK's ";"), the start of the text, OR another
# marker token glued immediately before it (`USC_T8_C12_S1101`'s citation
# note "section (a)(15)(H)(i)" -- "(15)" sits directly against "(a)"'s own
# closing paren, not inside a word) -- is. Checking the single character
# immediately preceding the marker (skipping only whitespace) generalizes
# correctly to both: a lowercase letter means "still inside a word/clause";
# anything else (including a closing paren from a glued prior marker) does
# not.
_LOWERCASE_LETTER_BEFORE_RE = re.compile(r"[a-z]\s*$")
# A bare single-letter-dot sub-marker (either case) glued onto a preceding
# digit-dot marker with no other content between them (ND's "5. a. " /
# "14. a. " shape) -- see this module's own docstring, "The dot-marker
# chain-walk".
_BARE_LETTER_DOT_SUBMARKER_RE = re.compile(r"[A-Za-z]\.[ \t]+")
# See this module's own docstring, "The digit-paren run's membership".
# A short run of uppercase letters/digits (plus the punctuation real
# statutory ALL-CAPS labels use, e.g. AL's "STATE HEALTH PLANNING AND
# DEVELOPMENT AGENCY (SHPDA).") terminated by a period, with NO lowercase
# letters anywhere in the span -- what distinguishes a genuine ALL-CAPS
# entry label from an ordinary capitalized sentence (which only capitalizes
# its FIRST letter, not every letter up to the period).
_ALL_CAPS_LABEL_OPEN_RE = re.compile(r"^[A-Z][A-Z0-9 ,/()'-]{0,78}\.")
# See this module's own docstring, "The compound-idiom prefix preservation".
# `_TIGHT_IDIOM_RE` universally strips the matched idiom token from the
# start of a captured entry -- correct, and relied on, for a SIMPLE idiom
# ("means the ..."). A COMPOUND idiom (NJ's "means and refers to ...",
# "means and includes ...", "shall mean and include ...") is two idiom
# words joined by "and <verb>", and stripping only the first leaves a
# dangling fragment ("and refers to ...") as the captured definition text
# instead of the real sentence. This pattern recognizes that continuation
# immediately after the idiom match so the whole compound idiom can be kept
# instead of only its tail.
_COMPOUND_IDIOM_CONTINUATION_RE = re.compile(r"and\s+[a-z]")


def _preceded_by_list_introducer(text: str, marker_start: int) -> bool:
    return bool(_LIST_INTRODUCER_BEFORE_RE.search(text[:marker_start]))


def _preceded_by_sentence_or_clause_boundary(text: str, marker_start: int) -> bool:
    before = text[:marker_start]
    if not before.strip():
        return True
    return not _LOWERCASE_LETTER_BEFORE_RE.search(before)


def _walk_glued_dot_marker_chain(text: str, pos: int, limit: int) -> int:
    """Starting right after a `_DIGIT_DOT_MARKER_RE` match, walk forward
    through any further GLUED marker tokens -- a bare single-letter-dot
    sub-marker (ND's "5. a. "/"14. a. " shape) or a paren-wrapped token
    (`_ANY_MARKER_TOKEN_RE`, ND's own "14. a. (1) " shape once the letter-dot
    step lands right before it) -- before the caller does its own
    after-marker check. Mirrors `_DIGIT_MARKER_RE`'s own glued-paren chain
    walk, extended to the shapes a bare digit-dot marker chains into."""
    while True:
        letter_m = _BARE_LETTER_DOT_SUBMARKER_RE.match(text, pos, limit)
        if letter_m is not None:
            pos = letter_m.end()
            continue
        paren_m = _ANY_MARKER_TOKEN_RE.match(text, pos, limit)
        if paren_m is not None:
            pos = paren_m.end()
            continue
        break
    return pos


def _digit_paren_run_internal_content_starts(text: str, limit: int) -> set[int]:
    """A digit-paren run's membership -- genuine sibling entries versus
    internal enumeration content of ONE entry -- is derived from what its
    own colon/dash-introduced item 1 opens with, not from the punctuation
    between later members (semicolon vs period is not a reliable signal --
    see AK's semicolon-joined TOP-LEVEL list, which must NOT be suppressed
    this way). If item 1 opens with a quoted term or an ALL-CAPS label
    (`_ALL_CAPS_LABEL_OPEN_RE` -- AL's "(1) ACQUISITION." convention), the
    run is genuine sibling entries and every member is judged individually,
    unchanged. If item 1 opens with neither (ordinary prose, e.g. ND's
    "(1) A franchisee is granted the right ..."), every STRICTLY CONSECUTIVE
    successor (2, 3, 4, ...) INHERITS that "internal content" verdict as a
    fallback -- but inheritance never overrides a successor's OWN direct
    evidence (issue #28): a successor whose own opener independently shows
    the SAME signal that would have made a run's own item 1 read as
    genuine -- a quoted term or an ALL-CAPS label immediately after its
    marker -- is judged on that evidence instead of inheriting item 1's
    verdict, whatever punctuation (comma, semicolon, period) precedes it.
    South Carolina's `STATE_SC_T31_C3_A1_S31-3-20` is the confirmed corpus
    case: item 1 opens with the prose `The term "director" shall mean ...`
    (neither a bare quote nor an ALL-CAPS label), so the run defaults to
    "internal" -- but item (16), `"Obligee of the authority" or "obligee"
    shall include ...`, opens with its own quote directly after the marker.
    Without this override (16) is swallowed whole into the preceding entry,
    "Persons of low income" (15); an entry's own idiom does not have to be
    one `_TIGHT_IDIOM_RE` recognizes ("shall include" is not) for its
    marker to still count as direct evidence here -- exactly the same
    "quote right after the marker is already a hard-stop-worthy signal on
    its own merits" principle `compute_hard_stops`'s own digit-marker loop
    already applies to every NON-suppressed digit marker (see UT's
    "Insolvent", whose own next entry "Paid and delivered" hard-stops it
    despite "does not include" being unrecognized too)."""
    suppressed: set[int] = set()
    run_active = False
    run_is_internal = False
    expected_number: int | None = None
    for m in _DIGIT_MARKER_RE.finditer(text, 0, limit):
        try:
            number = int(m.group(0).strip("() \t"))
        except ValueError:
            run_active = False
            continue
        if run_active and number == expected_number:
            if run_is_internal:
                opener = text[m.end() : m.end() + 80]
                has_own_direct_evidence = bool(
                    _AFTER_MARKER_QUOTE_RE.match(opener) or _ALL_CAPS_LABEL_OPEN_RE.match(opener)
                )
                if not has_own_direct_evidence:
                    suppressed.add(m.start())
            expected_number = number + 1
            continue
        run_active = False
        if number == 1 and _preceded_by_list_introducer(text, m.start()):
            opener = text[m.end() : m.end() + 80]
            run_is_internal = not (
                _AFTER_MARKER_QUOTE_RE.match(opener) or _ALL_CAPS_LABEL_OPEN_RE.match(opener)
            )
            run_active = True
            expected_number = 2
    return suppressed


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


def trailing_stop_limit(text: str) -> int:
    """The offset `extract_quote_anchored_entries` itself trims `text` to
    before doing anything else (the first non-operative annotation tail, if
    any -- see `TRAILING_STOP_RE`'s own docstring entry). Exposed so a
    sibling rule module with its OWN idiom-recognition regex (a quote-to-
    idiom gap shape this module's own tight gate does not reach, e.g. OK's
    `us_markers_ok_gapidiom.py`) can compute the identical working `limit`
    before calling `compute_hard_stops`/`close_entries` below, rather than
    re-deriving (or forgetting to derive) it independently."""
    stop = TRAILING_STOP_RE.search(text)
    return stop.start() if stop else len(text)


def compute_hard_stops(
    text: str, limit: int, *, stop_at_mn_subd_headers: bool = False
) -> tuple[list[int], set[int], set[int]]:
    """The marker hard-stop detection this module's own docstring
    documents (`_DIGIT_MARKER_RE`/`_LETTER_MARKER_RE`/`_DIGIT_DOT_MARKER_RE`/
    `_LETTER_DOT_MARKER_RE`, the list-introducer exclusion, and the MN
    `Subd.` opt-in) -- factored out of `extract_quote_anchored_entries` so a
    sibling rule with its own idiom regex (its OWN `starts` list, a
    different quote-to-idiom gap shape) still gets the exact same, already-
    proven-against-the-corpus boundary-closing behavior via `close_entries`
    below, rather than reinventing a weaker version of it. Returns
    `(hard_stops, mn_subd_stops, digit_based_stops)` -- `mn_subd_stops` is
    the subset of `hard_stops` that are MN `Subd.` header offsets
    specifically (needed by `close_entries` to decide whether `_TRAILING_
    MARKER_CHAIN_RE` applies at a given boundary, per this module's own
    existing behavior); `digit_based_stops` (issue #25) is the subset from
    `_DIGIT_MARKER_RE`/`_DIGIT_DOT_MARKER_RE` specifically, as opposed to
    the letter-marker patterns -- see `close_entries`'s own `skip_digit_
    hard_stops_for` for why the two marker families need to be
    distinguishable rather than treated as one undifferentiated set."""
    hard_stops: list[int] = []
    digit_based_stops: set[int] = set()
    internal_content_starts = _digit_paren_run_internal_content_starts(text, limit)
    for m in _DIGIT_MARKER_RE.finditer(text, 0, limit):
        if m.start() in internal_content_starts:
            continue
        if _preceded_by_list_introducer(text, m.start()):
            continue
        chain_end = m.end()
        while True:
            chain_m = _ANY_MARKER_TOKEN_RE.match(text, chain_end, limit)
            if chain_m is None:
                break
            chain_end = chain_m.end()
        after = text[chain_end : chain_end + 1]
        if _AFTER_MARKER_QUOTE_RE.match(after):
            hard_stops.append(m.start())
            digit_based_stops.add(m.start())
        elif _AFTER_MARKER_UPPER_RE.match(after) and _preceded_by_sentence_or_clause_boundary(
            text, m.start()
        ):
            hard_stops.append(m.start())
            digit_based_stops.add(m.start())
    for m in _LETTER_MARKER_RE.finditer(text, 0, limit):
        if _preceded_by_list_introducer(text, m.start()):
            continue
        if _QUOTE_WITHIN_LOOKAHEAD_RE.match(text[m.end() : limit]):
            hard_stops.append(m.start())
    for pattern in (_DIGIT_DOT_MARKER_RE, _LETTER_DOT_MARKER_RE):
        for m in pattern.finditer(text, 0, limit):
            if _preceded_by_list_introducer(text, m.start()):
                continue
            check_end = m.end()
            if pattern is _DIGIT_DOT_MARKER_RE:
                check_end = _walk_glued_dot_marker_chain(text, check_end, limit)
            if _AFTER_MARKER_UPPER_OR_QUOTE_RE.match(text[check_end : check_end + 1]):
                hard_stops.append(m.start())
                if pattern is _DIGIT_DOT_MARKER_RE:
                    digit_based_stops.add(m.start())
    mn_subd_stops: set[int] = set()
    if stop_at_mn_subd_headers:
        mn_subd_stops.update(m.start() for m in _MN_SUBD_HEADER_RE.finditer(text))
        hard_stops.extend(mn_subd_stops)
    return hard_stops, mn_subd_stops, digit_based_stops


def close_entries(
    text: str,
    limit: int,
    starts: list[tuple[int, str, int]],
    hard_stops: list[int],
    mn_subd_stops: set[int] | None = None,
    *,
    skip_digit_hard_stops_for: frozenset[int] = frozenset(),
    digit_based_stops: frozenset[int] = frozenset(),
) -> list[tuple[str, str]]:
    """Given `starts` (`(term_quote_start, term, definition_start)` tuples,
    IN TEXT ORDER -- the shape `extract_quote_anchored_entries`'s own
    quote+idiom loop produces, and the shape a sibling rule's OWN idiom
    regex must produce to reuse this), close each entry's boundary using
    `hard_stops`/`mn_subd_stops` from `compute_hard_stops` above. Factored
    out of `extract_quote_anchored_entries` unchanged -- see that function
    for the full boundary-closing rationale (bounded-vs-unbounded,
    `MAX_CLEAN_DEFINITION_LENGTH`, `_TRAILING_MARKER_CHAIN_RE`).

    `skip_digit_hard_stops_for`/`digit_based_stops` (issue #25, additive,
    both default empty -- every existing caller's behavior is unchanged): a
    set of `definition_start` offsets to close IGNORING `digit_based_stops`
    specifically (a paren-digit or bare-digit-dot marker, e.g. `"(2)"` or
    `"2. "`), while still respecting every OTHER hard-stop (letter markers,
    MN `Subd.` headers) exactly as before. `extract_quote_anchored_entries`
    passes its own exclusion-bridge-matched entries here (see `_EXCLUSION_
    CLAUSE_BRIDGE_RE`): a bridged entry's OWN body may contain a genuine
    internal DIGIT enumeration (`STATE_NV_T8_C104_S104.9102`'s
    `"Accounting"` -- `means a record: (1) Signed by a secured party; (2)
    Indicating ...; and (3) Identifying ...`), and digit-marker hard-stop
    detection cannot tell that "(2)"/"(3)" continue the SAME colon-
    introduced list from a genuine sibling entry marker (the exact
    citation-vs-marker ambiguity issue #21 scopes to core-follow-on-3, not
    this module -- see `close_entries`'s own module docstring entry).
    Narrowed to DIGIT markers only (not letter markers too) after corpus
    self-verification caught a real regression in an earlier, broader
    draft that skipped every hard-stop kind for a bridged entry:
    `STATE_NV_T8_C104_S104.1201`'s `"Contract"` is followed by `(m)
    "Creditor" includes ...`, `(n) "Defendant" includes ...`, and `(o)
    "Delivery" ... means ...` -- none captured as their own `starts` entry
    (`"includes"` is not a recognized idiom; `"Delivery"`'s own relative-
    qualifier gap is a SEPARATE, unrelated shape this rule does not
    bridge) -- so with ALL hard-stops skipped, `"Contract"` ran past its
    own real one-sentence definition straight through all three unrelated
    entries to the next actually-captured term, `"Document of title"`.
    NV's own convention keeps digit markers to internal enumeration and
    letter markers to top-level entries in both fixture rows, so
    preserving letter-marker hard-stops for bridged entries while skipping
    only digit-marker ones is correct for both real defects at once,
    verified directly against both rows (every one of the 7 named terms
    -- Agreement/Contract/Party/Account/Accounting/Assignee/Record --
    closes at its own real boundary, no swallowed neighbour, no truncated
    internal list)."""
    mn_subd_stops = mn_subd_stops or set()
    entries: list[tuple[str, str]] = []
    for idx, (_qstart, term, dstart) in enumerate(starts):
        has_next_term = idx + 1 < len(starts)
        next_start = starts[idx + 1][0] if has_next_term else limit
        if dstart in skip_digit_hard_stops_for:
            candidate_stops = [
                hs for hs in hard_stops if dstart < hs < next_start and hs not in digit_based_stops
            ]
        else:
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
        raw = text[dstart:end]
        # The trailing-marker-chain strip fires ONLY when this entry closes
        # by reaching the NEXT captured quote with ZERO hard-stops found
        # first (`not candidate_stops and has_next_term`, i.e. `end ==
        # next_start` for a genuine reason, not a marker). When a real
        # hard-stop closed the entry instead, the marker that triggered it
        # already sits OUTSIDE `raw` (the slice stops right before it) --
        # there is no leaked fragment left to strip, and running the strip
        # anyway risks eating a real trailing citation number that merely
        # LOOKS like a marker token (`STATE_ND_T57_C57-02_S57-02-01`'s
        # "...chapters 57-06 and 57-32." -- bounded by the real next "3."
        # entry marker, its own "32." is not leaked debris and must
        # survive). See this module's own docstring, "The trailing-marker-
        # chain strip's own scope".
        if not candidate_stops and has_next_term and end not in mn_subd_stops:
            raw = _TRAILING_MARKER_CHAIN_RE.sub("", raw)
        definition_text = raw.strip()
        if not definition_text:
            continue
        if not bounded and len(definition_text) > MAX_CLEAN_DEFINITION_LENGTH:
            continue
        entries.append((term, definition_text))
    return entries


def extract_quote_anchored_entries(
    text: str,
    *,
    allow_relative_qualifiers: bool = False,
    clean_trailing_term_commas: bool = False,
    stop_at_mn_subd_headers: bool = False,
) -> list[tuple[str, str]]:
    """`text` (an already-mojibake-repaired, if applicable, section/article
    body) -> `[(term, definition_text), ...]`, each boundary-clean per this
    module's docstring. Pure text in, pure data out -- callers (this
    package's other rule modules) decide how to wrap the result for their
    own registered rule kind."""
    limit = trailing_stop_limit(text)
    idiom_re = (
        _TIGHT_IDIOM_WITH_RELATIVE_QUALIFIER_RE
        if allow_relative_qualifiers
        else _TIGHT_IDIOM_RE
    )

    starts: list[tuple[int, str, int]] = []
    excluded_spans: list[tuple[int, int]] = []
    bridged_dstarts: set[int] = set()
    for m in _LEADING_QUOTE_TERM_RE.finditer(text, 0, limit):
        if any(span_start <= m.start() < span_end for span_start, span_end in excluded_spans):
            continue
        idiom_m = idiom_re.match(text, m.end(), limit)
        bridged_exclusion = False
        if idiom_m is None:
            bridge_m = _EXCLUSION_CLAUSE_BRIDGE_RE.match(text, m.end(), limit)
            if bridge_m is not None:
                idiom_m = bridge_m
                bridged_exclusion = True
                excluded_spans.append((m.end(), bridge_m.end()))
        if idiom_m is None:
            continue
        term = m.group(1).strip()
        if clean_trailing_term_commas or bridged_exclusion:
            term = term.removesuffix(",").rstrip()
        if not term:
            continue
        if bridged_exclusion:
            bridged_dstarts.add(idiom_m.end())
        dstart = idiom_m.end()
        if not bridged_exclusion and _COMPOUND_IDIOM_CONTINUATION_RE.match(
            text, idiom_m.end(), idiom_m.end() + 40
        ):
            dstart = idiom_m.start()
        starts.append((m.start(), term, dstart))

    hard_stops, mn_subd_stops, digit_based_stops = compute_hard_stops(
        text, limit, stop_at_mn_subd_headers=stop_at_mn_subd_headers
    )
    return close_entries(
        text,
        limit,
        starts,
        hard_stops,
        mn_subd_stops,
        skip_digit_hard_stops_for=frozenset(bridged_dstarts),
        digit_based_stops=frozenset(digit_based_stops),
    )


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
