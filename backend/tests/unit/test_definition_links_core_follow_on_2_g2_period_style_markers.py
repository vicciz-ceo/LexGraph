"""G2 RED tests -- sprint 2026-08-05-defs-core-follow-on-2, gate G2
("period-style markers"). Planner: plan1 (also owns G4 in the sibling
module `test_definition_links_core_follow_on_2_g4_citation_pincite_stack.py`
-- ONE designer for both per the sprint contract, so the fixes compose).

**The defect.** `us_profile._US_UNIT_MARKER_RE = re.compile(r"\\(([A-Za-z]+
|\\d+)\\)")` matches PARENTHESIZED tokens only. Real US state drafting
routinely uses a PERIOD-style top-level marker instead -- a digit run
(optionally hyphen-continued, e.g. Maine's "2-A.", "2-B." -- the real
convention for a section inserted between "2." and "3.") or a 1-2 letter
run, immediately followed by "." at the start of a paragraph -- e.g. Maine
"2-A."/"F.", Arizona "J.", Virginia "A.". None of this is parenthesized,
so `resolve_unit_path` never sees ANY marker on these rows and returns the
empty path `()` regardless of how deep real structure goes. Measured,
full 53-state-statutes census (`si_cycle2_plan7_subsection_trigger_rows.json`
population -- the SAME denominator that reproduces the known S-R16 figure,
see this Planner's report): 3,200/38,172 = 8.4% of all "subsection"-scope
trigger occurrences resolve to an empty path; Maine 81.0% (1,068/1,318),
Arizona 69.7% (426/611), nine states >= 25%.

**The fix this item specifies (byte-verified against real rows, prototyped
and corpus-measured by this Planner -- see the report for the full
before/after table):**

1. Recognize a period-style top-level marker ONLY when anchored at a
   paragraph boundary (start of body, or immediately after a newline, any
   amount of leading whitespace) -- never mid-sentence. This is the SAME
   "anchored, not free-floating" discipline this file already uses
   elsewhere for `_LEADING_PARENTHETICAL_RE`/`_BODY_EMBEDDED_HEADING_RE`.
   Token shape: `\\d+(?:-[A-Za-z]{1,2})?` (plain digit OR Maine's hyphen-
   continuation) OR `[A-Za-z]{1,2}`, followed by "." and whitespace.
2. `_marker_matches_kind` must classify a hyphen-continuation token
   (e.g. "2-A") as kind="digit" (same rung as a plain digit token, value
   is the full "2-A" string) -- today's `token.isdigit()` check is False
   for "2-A", so without this extension the token is silently I9-skipped
   even after (1) ships. Real evidence: `STATE_ME_T38_C3_S464`'s genuine
   "2-A."/"2-B." markers.
3. Ladder selection (which token's SHAPE decides digit-outermost vs.
   OH-upper_alpha-outermost vs. federal) must be DEFERRED past a token
   that shape-matches NONE of the three outermost rungs (digit,
   upper_alpha, lower_alpha) -- such a token cannot be a genuine opener
   for ANY of the three ladders and must not consume the "first marker"
   privilege; the loop moves on to the next candidate instead. Real
   evidence: `STATE_ME_T38_C3_S464`'s FIRST parenthesized token in the
   whole document is the revisor annotation "(NEW)" (3 letters -- matches
   neither digit nor upper_alpha, i.e. does NOT trigger the ladder's
   digit/upper_alpha special cases). Under today's "elif upper_alpha:
   ... else: ladder = federal" structure this STILL wrongly commits to
   the federal (lower_alpha-outermost) ladder for a document whose real
   convention is digit-outermost -- every genuine digit-shaped period
   marker that follows then fails to match federal's lower_alpha rung-0
   and, with no ancestor yet open, is ALSO skipped. Without step 3, step
   1 alone is silently defeated on any row where annotation/citation
   noise precedes the first genuine marker -- measured to be the
   difference between an 81.0% Maine degrade after step 1 alone and 0.2%
   after step 1+3 together (see report).

**What does NOT change (explicitly, so the Developer does not silently
touch it):** the 3-ladder selection mechanism itself (still exactly 3
named ladders); the "first genuine marker" ladder-selection PRINCIPLE
(still ONE shape decides the whole call -- step 3 only changes WHICH
token gets to be "first", not the principle); paren-style marker
recognition (`_US_UNIT_MARKER_RE` itself is unchanged, period-style is
ADDITIVE); G4's citation/cross-reference discriminator (a separate
sibling item -- see the G4 test module) is a DIFFERENT mechanism this
item does not implement, though (3) above narrowly overlaps it (both
care about "is this token noise") -- the Developer should keep these as
one coherent token-acceptance story per the sprint brief, not two
competing ones.

**Measured before/after (this Planner, full 53 `us_*_statutes.parquet`
census, same "subsection"-scope-trigger-occurrence population as the
known S-R16/pass-7 figure -- P-R10 reproduced: before = 3,200/38,172 =
8.38%, matches the cited 8.4% exactly):**

    TOTAL   before 3,200/38,172 (8.38%)  ->  after   244/38,172 (0.64%)
    ME      before 1,068/1,318  (81.0%)  ->  after     2/1,318  (0.2%)
    AZ      before   426/611    (69.7%)  ->  after     1/611    (0.2%)
    ND/NM/NV/OK/VA drop to 0.0%; NJ/MO/MI retain a residual (see report --
    these states' remaining empty-path rows were sampled and are a
    DIFFERENT, second-level-nesting or non-period shape, out of scope for
    this TOP-LEVEL-only item).

This was a prototype-and-measure exercise (throwaway script, not
committed) run against the REAL production `resolve_unit_path`/
`_marker_matches_kind` for the "before" half (byte-identical reproduction
of the known figure) and a faithful reimplementation of the SAME
stack-building algorithm, swapping only the marker source, for the
"after" half -- see this Planner's report for the full per-state table
and the script's location.

**Existing test that WILL need updating by the Developer, flagged here so
it is not silently regressed:**
`test_definition_links_cd_i9_unit_path_annotations.py::
test_i9_me_s751_body_with_only_annotations_produces_the_articles_own_base_path`
currently pins `resolve_unit_path(...) == ()` at end-of-body for
`STATE_ME_T30-A_P1_C3_S751`, whose real body opens with genuine top-level
period marker "1. Membership." -- under this item, that offset's correct
answer becomes non-empty (at least `(digit, '1')`). This is a legitimate,
INTENDED behavior change (that test's own docstring already says "never
parenthesized, so never in scope ... regardless of this defect" -- it was
pinning the ABSENCE this item exists to fix), not a silent regression, but
the assertion value must change as part of implementing this item.

**Non-regression tests** (paren-style states must stay byte-for-byte
unaffected) live in the sibling module
`test_definition_links_core_follow_on_2_g2_regression_guard.py` -- split
out purely for this program's 300-line-per-file style gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load_rows(filename: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def core_rows() -> dict[str, dict]:
    return _load_rows("core_follow_on_2_g2_g4_rows.json")


@pytest.fixture()
def me_annotation_rows() -> dict[str, dict]:
    # Reuses the ALREADY-committed, already byte-verified I9 fixture --
    # STATE_ME_T38_C3_S464 carries both the genuine "2-A." hyphen-
    # continuation marker AND the leading "(NEW)" annotation this item's
    # ladder-deferral fix (step 3) targets. No need to duplicate this
    # 43,969-char row in a second fixture file.
    return _load_rows("cd_i9_me_inline_annotation_rows.json")


@pytest.fixture()
def us_az():
    return get_profile("US-AZ")


@pytest.fixture()
def us_me():
    return get_profile("US-ME")


# --- Positive REDs: real period-style top-level markers must be seen ------


def test_az_letter_period_top_level_marker_c_is_recognized(core_rows, us_az):
    """Real `STATE_AZ_T41_C26_A1_S2814`: top-level letter-period markers
    "A." "B." "C." ... each starting a fresh paragraph. Today `(C)` is
    never parenthesized, so `resolve_unit_path` returns `()` for the
    ENTIRE row regardless of offset. After this fix, an offset inside
    subsection C's own paragraph must resolve to exactly one open step,
    `(upper_alpha, 'C')` (real convention here is letter-outermost, so
    the OH-upper_alpha ladder's rung 0)."""
    row = core_rows["STATE_AZ_T41_C26_A1_S2814"]
    text = row["text"]
    anchor = "C. Except as provided in subsection A of this section"
    assert anchor in text, "fixture text changed -- AZ subsection C anchor no longer present"
    article = MatcherArticle(
        number="41-2814", heading="Fingerprinting", body=text, chapter="26"
    )

    path = us_az.resolve_unit_path(article, char_offset=text.index(anchor) + 30)

    assert len(path) == 1, f"expected exactly one open top-level step; got {path!r}"
    assert path[0].kind == "upper_alpha"
    assert path[0].value == "C"


def test_az_letter_period_top_level_marker_j_is_recognized(core_rows, us_az):
    """Same real AZ row, subsection J -- the EXACT example named in the
    sprint contract's G2 gate text ("AZ `J.`"). Real text: "J. Except as
    provided in this subsection, the department may not allow an
    individual...". Must resolve to `(upper_alpha, 'J')`, not `()`."""
    row = core_rows["STATE_AZ_T41_C26_A1_S2814"]
    text = row["text"]
    anchor = "J. Except as provided in this subsection, the department"
    assert anchor in text, "fixture text changed -- AZ subsection J anchor no longer present"
    article = MatcherArticle(
        number="41-2814", heading="Fingerprinting", body=text, chapter="26"
    )

    path = us_az.resolve_unit_path(article, char_offset=text.index(anchor) + 40)

    assert len(path) == 1, f"expected exactly one open top-level step; got {path!r}"
    assert path[0].kind == "upper_alpha"
    assert path[0].value == "J"


def test_me_hyphen_continuation_marker_2a_is_recognized_as_digit_kind(
    me_annotation_rows, us_me
):
    """Real `STATE_ME_T38_C3_S464` (the SAME row I9's own committed
    fixture already carries): genuine top-level markers "1." "2." "2-A."
    "2-B." "3." ... -- "2-A."/"2-B." are Maine's real hyphen-continuation
    convention (a section inserted between "2." and "3." without
    renumbering everything after it), named verbatim in the sprint
    contract's G2 gate text ("ME `2-A.`"). An offset inside "2-A."'s own
    paragraph must resolve to `(digit, '2-A')` -- the FULL hyphenated
    string as the value, classified at the digit rung (same rung a plain
    "2." would occupy)."""
    row = me_annotation_rows["STATE_ME_T38_C3_S464"]
    text = row["text"]
    anchor = "2-A. Removal of designated uses"
    assert anchor in text, "fixture text changed -- ME 2-A. anchor no longer present"
    article = MatcherArticle(
        number="464", heading="Classification of Maine waters", body=text, chapter="3"
    )

    path = us_me.resolve_unit_path(article, char_offset=text.index(anchor) + 60)

    assert len(path) == 1, (
        f"expected exactly one open top-level step (this offset sits directly in "
        f"2-A.'s own paragraph, before any deeper marker); got {path!r}"
    )
    assert path[0].kind == "digit"
    assert path[0].value == "2-A"


def test_me_ladder_selection_is_not_hijacked_by_the_leading_new_annotation(
    me_annotation_rows, us_me
):
    """Isolates fix-step 3 specifically: `STATE_ME_T38_C3_S464`'s very
    FIRST parenthesized token in the whole document is the revisor
    annotation "(NEW)" (see `[PL 1985, c. 698, §15 (NEW).]` right after
    the opening sentence, BEFORE "1. Findings..." even begins). "NEW" is
    3 letters -- matches neither the digit nor the (single-char)
    upper_alpha ladder-selection special case, so under today's "else:
    ladder = federal" fallback it STILL wrongly claims the ladder as
    federal (lower_alpha-outermost) for a row whose real convention is
    digit-outermost. Symptom if step 3 is missing: even after step 1
    (period-marker recognition) ships, this SAME 2-A. offset resolves to
    `()` again, not `(digit, '2-A')`, because every genuine digit-shaped
    marker fails to match the (wrong) federal ladder's lower_alpha
    rung-0 and is skipped for lack of an open ancestor. This test and
    the one above assert the SAME offset/expectation; kept as two tests
    because they isolate two independently-implementable fix steps (1+2
    vs. 3) -- a Developer who ships only steps 1+2 makes THIS test fail
    while a naive manual trace of step 1 alone might look sufficient."""
    row = me_annotation_rows["STATE_ME_T38_C3_S464"]
    text = row["text"]
    assert "(NEW)" in text.split("2-A.")[0], (
        "fixture no longer has a (NEW) annotation before the 2-A. marker -- "
        "this test's premise (annotation noise precedes the first genuine marker) is gone"
    )
    anchor = "2-A. Removal of designated uses"
    article = MatcherArticle(
        number="464", heading="Classification of Maine waters", body=text, chapter="3"
    )

    path = us_me.resolve_unit_path(article, char_offset=text.index(anchor) + 60)

    assert path, (
        "ladder selection was hijacked by the leading (NEW) annotation noise -- "
        "the real digit-outermost convention never got a chance to apply, so "
        "every genuine digit-period marker (1., 2., 2-A., ...) was skipped"
    )
    assert path[-1].kind == "digit"
    assert path[-1].value == "2-A"


# Non-regression tests (paren-style states unaffected) live in the sibling
# module `test_definition_links_core_follow_on_2_g2_regression_guard.py`.
