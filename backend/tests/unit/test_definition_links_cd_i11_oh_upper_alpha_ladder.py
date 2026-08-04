"""I11 follow-on RED tests -- `resolve_unit_path` mis-kinds (actually:
DROPS entirely) a document whose OWN outermost sub-article convention is
`upper_alpha` (Ohio's real, dominant convention) -- sprint
2026-08-04-defs-core-dispatch, item I11, manager ruling M-D3, seam v2.7's
own ERRATUM to M-D3 §2.

**The defect this file pins, precisely.** `1645a34` (I9+I11 landed)
chooses between exactly TWO ladders per call, from the shape of the FIRST
genuine marker seen: `_DIGIT_OUTERMOST_UNIT_PATH_LADDER` if it is
digit-shaped, else the federal `_UNIT_PATH_LADDER` (whose position 0
expects `lower_alpha`). A document whose first genuine marker is
`upper_alpha`-shaped (e.g. Ohio's real `(A)`) matches NEITHER selection
branch's expectation at position 0 of the ladder it falls into (federal),
and the stack is empty (no open ancestor to match either) -- so it is
SKIPPED, per I9's own "skip unclassifiable, never push a generic 'sub'"
fix. The resolver's own docstring names this exact gap ("Honesty note (no
test pins this): ... e.g. Ohio's real `(A)(1)(a)(i)`"). This file is that
pin.

**Step-1 corpus measurement (this Planner, signal-agnostic denominator per
program ruling P-R7).** `subsection_count` (a corpus-provided column,
independent of anything this sprint's code computes) was checked FIRST as
a candidate independent-signal denominator and found uniformly `0` for
every one of the 33,161 real `us_oh_statutes.parquet` rows -- unusable.
The measurement below instead uses the FULL, UNCONDITIONAL row population
(33,161 rows, no filtering by whether any resolver code "succeeds" on a
row, and no filtering derived from `_US_UNIT_MARKER_RE`/
`_marker_matches_kind`, the mechanism under test) as the denominator, with
a STRICTER-than-production, independently-written classifier: a kind only
counts as "genuine structure" if at least two SAME-KIND tokens appear in
INCREASING sequence somewhere in the document (e.g. real `(A)` followed
later by real `(B)`) -- an isolated shape match (a single citation aside
or annotation token) never counts. Full results (script:
`dispatch-plan-marker-measure.py`, this Planner's scratchpad):

    total OH rows (unconditional): 33,161
    rows with NO genuine same-kind incrementing marker run at all: 15,210 (45.9%)
    outermost genuine-run kind, of the 17,951 rows that DO have one:
        upper_alpha:  17,849 (99.4% of structured rows / 53.8% of all rows)
        digit:            79 (0.4% of structured rows / 0.2% of all rows)
        lower_alpha:      20 (0.1% of structured rows / 0.1% of all rows)
        lower_roman:       3 (0.0%)

Ohio's real, dominant, outermost sub-article convention is decisively
`upper_alpha` -- the seam v2.7 erratum's claim is CONFIRMED, not
contradicted, by this measurement (contrast with the Planner brief's own
warning to check rather than trust the premise). The full observed ladder
order below `upper_alpha`, measured the same way over the 17,849
upper_alpha-outermost rows (script: `dispatch-plan-oh-ladder-order.py`,
tallying every distinct genuine-run kind in first-appearance document
order):

    (upper_alpha, digit):                                 6,711
    (upper_alpha,) alone:                                  6,530
    (upper_alpha, digit, lower_alpha):                     3,474
    (upper_alpha, digit, lower_alpha, lower_roman):          996
    (upper_alpha, digit, lower_alpha, lower_roman, upper_roman): 40
    (upper_alpha, lower_alpha, digit):                        27
    ... (long tail, each <30 rows)

The dominant, consistent order is `upper_alpha > digit > lower_alpha >
lower_roman > upper_roman` -- i.e. real Ohio drafting IS `(A)(1)(a)(i)`,
confirming the sprint doc's synthetic premise exactly (this Planner
verified rather than assumed this, per the brief's own instruction --
several other candidate orders appear in the long tail at negligible
frequency and are NOT what this file pins). This is a THIRD ladder,
distinct from both ladders already in `us_profile.py`:

    federal:         (lower_alpha, digit, upper_alpha, lower_roman, ...)
    digit-outermost:  (digit, lower_alpha, upper_alpha, lower_roman, ...)
    OH (NOT YET IMPLEMENTED, this file's own gap): (upper_alpha, digit, lower_alpha, lower_roman, upper_roman, ...)

**Step-1.3 quick scan of other jurisdictions (SAMPLE, not a census -- the
seam v2.7 erratum explicitly routes the full jurisdiction-by-jurisdiction
census to program close, not this sprint).** The same independent
methodology, run over a modest, arbitrarily-picked cross-section of 8
other state files not already characterized by this sprint's own docs
(GA, IL, WA, AZ, NC, VA, WI, IN -- 3,000-row random sample each, full
corpus for OH/OR/DE): NONE of the 8 shows `upper_alpha` as its DOMINANT
outermost convention (max seen: IL 0.2%, VA 0.0% -- both single-digit row
counts, clearly incidental, not a state convention) -- confirming Ohio is
a genuine outlier among this sample, not representative of "most states"
(which lean `lower_alpha` or `digit`, matching the two ladders already
implemented). This is a sample; it does NOT prove Ohio is the ONLY
upper_alpha-outermost jurisdiction in the 53-jurisdiction corpus -- see
"What this file does NOT prove" at the bottom.

**Fixture provenance.** `cd_i11_oh_upper_alpha_outermost_row.json` is a
byte-for-byte vendored copy of ONE real row, `STATE_OH_T15_C1531_S1531.132`
("Restriction on employment" -- Ohio Revised Code § 1531.132, Division of
Wildlife game protectors), read directly via `pyarrow.parquet.read_table`
from this Planner's own local snapshot of `vaquill/open-us-law`
(`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/
301000fc3465374ee0f23c3c6953a8a861e95cad/us_oh_statutes.parquet`), all 24
original columns, values unmodified. Verified byte-identical by re-loading
the written JSON and comparing it dict-for-dict against a freshly re-read
parquet row (`dispatch-plan-write-fixture-v2.py`, this Planner's
scratchpad) before being committed here.

**Why this row, not another (a real, measured, non-trivial search --
recorded honestly because the first row this Planner picked, a sibling
Ohio statute about park-district employees, had to be REJECTED after
failing this exact check).** A row is usable here only if it (a) genuinely
nests 4 real levels under Ohio's own convention, AND (b) contains no
citation/cross-reference noise token (e.g. "division (B) of this
section", a self-reference to a DIFFERENT part of the same section) that
would corrupt an already-open ancestor's VALUE before the deepest offset
under test is reached -- `_US_UNIT_MARKER_RE` cannot distinguish a genuine
structural marker from a same-shaped cross-reference, and a sibling-
replacement bug in a NOT-YET-BUILT third ladder could silently overwrite a
correct ancestor with a cross-reference's value, producing a test that
looks green today but pins a WRONG value once a fix lands. This Planner
built a strict, independent simulator (`dispatch-plan-find-clean-oh-row-
v2.py`) that (1) identifies, PER KIND, exactly which token occurrences
belong to a genuine strictly-incrementing run (1,2,3... or a,b,c...) vs.
every other same-shaped occurrence (citation noise), then (2) replays the
production push/replace algorithm and flags any candidate where a noise
token is ever CONSUMED (pushed or used to replace an ancestor) before the
deepest offset under test. Of 944 real OH rows in the 400-4,500 char range
with genuine `upper_alpha > digit > lower_alpha > lower_roman` structure,
518 (54.9%) are clean by this test; `STATE_OH_T15_C1531_S1531.132` is one
of them, additionally verified end-to-end against every one of this
file's own 8 specific offsets via a full monkeypatched simulation of a
plausible correct 3-ladder fix (`dispatch-plan-sanity-monkeypatch-v2.py`)
-- every expected value below was confirmed reachable by SOME correct
implementation before being pinned, not merely asserted.

It genuinely nests FOUR real levels deep under Ohio's own real
convention -- `(A)` (a single, self-contained top-level division with no
nested paragraphs of its own) then `(B)` (upper_alpha, a sibling division)
> `(B)(1)`/`(B)(2)`/`(B)(3)`/`(B)(4)` (digit, paragraphs under division B)
> `(2)(a)`/`(2)(b)` (lower_alpha, subparagraphs under paragraph 2) >
`(a)(i)`/`(a)(ii)` (lower_roman, sub-subparagraphs under subparagraph a)
-- a REAL four-level chain, so no synthetic body is needed for the
deep-nesting guard (Standards note in the Planner brief: "Real rows over
synthetic"). Every offset pinned below is verified in a CLEAN window
(inline `assert text[offset-N:offset] == "(X) "` anchors on every test, so
fixture drift fails loudly), and additionally proven noise-free THROUGH
that offset by the simulator above -- both checks the OR fixture's own
test file already does informally; this file adds the second, automated
one because the first real row this Planner tried
(`STATE_OH_T5_C511_S511.232`, same legislative template, park-district
employees instead of game protectors) FAILED it: a `"division (B) of this
section"` cross-reference inside paragraph `(1)`'s own text would have
silently corrupted the outermost `upper_alpha` ancestor from `'C'` to
`'B'` before reaching the `(2)(a)` offset under a correct 3-ladder
implementation, which this Planner's monkeypatch sanity check caught
(recorded, not hidden, per the brief's honesty standard) before any
assertion below was written against it.

**What this file does NOT prove** (stated explicitly, per the brief):

- It does NOT prove Ohio is the only upper_alpha-outermost jurisdiction in
  the 53-jurisdiction corpus -- Step 1.3 above is a sample, not a census
  (the erratum itself routes the full census to program close).
  `double_lower_alpha`/`double_upper_alpha` ladder positions are NOT
  exercised by any test below -- no real OH row measured reaches that
  depth (the deepest confirmed real chain is 5 levels, 40 rows, and this
  fixture's own row reaches 4) -- those two rungs are asserted by ANALOGY
  to the other two ladders' own existing convention (append them in the
  same relative order), not independently corpus-verified for Ohio.
- It does NOT fix anything -- these tests are RED against `1645a34` (see
  each test's own docstring for the exact current, wrong output) and MUST
  stay failing until a Developer implements a THIRD ladder-selection
  branch. Per this Planner's role boundary, no production code is touched
  here. The monkeypatch "sanity" simulation described above ran ONLY in a
  throwaway scratchpad script, in-process, against a runtime-patched
  module attribute -- it never wrote to, nor imported a modified copy of,
  any file under `backend/app/`.
- It does NOT re-prove the digit-outermost (Oregon) or federal (Delaware)
  ladders already covered by `test_definition_links_cd_i11_resolver_kind_
  correctness.py` / `test_definition_links_cd_i9_unit_path_annotations.py`
  -- this file is Ohio-only.
- None of the 8 tests below are expected to be GREEN today -- there is no
  currently-passing "guard" in this file to mutation-prove (the capability
  it tests does not exist yet in `1645a34`). Each test's own docstring
  instead documents the EXACT current wrong output, verified by an actual
  `pytest` run against `1645a34`, as the substitute honesty check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.matcher import definition_covers_mention
from app.definition_links.profiles import get_profile
from app.definition_links.rules.registry import UnitStep
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


@pytest.fixture()
def oh_row() -> dict:
    rows = json.loads(
        (FIXTURES_DIR / "cd_i11_oh_upper_alpha_outermost_row.json").read_text(encoding="utf-8")
    )
    assert len(rows) == 1 and rows[0]["act_id"] == "STATE_OH_T15_C1531_S1531.132"
    return rows[0]


@pytest.fixture()
def us_oh():
    return get_profile("US-OH")


@pytest.fixture()
def oh_article(oh_row) -> MatcherArticle:
    return MatcherArticle(
        number="1531.132",
        heading="1531.132 Restriction on employment.",
        body=oh_row["text"],
        chapter="1531",
    )


# --- 1: the outermost marker itself ------------------------------------


def test_i11_oh_outermost_upper_alpha_marker_resolves_with_upper_alpha_kind_not_skipped(
    oh_row, us_oh, oh_article
):
    """The row's very first parenthesized token is the genuine top-level
    division marker `(A)` (`"...124th General Assembly (A) As used in this
    section..."`). An offset immediately inside it must resolve to a
    SINGLE-element path whose one step is kind `"upper_alpha"` -- not
    dropped entirely. Division `(A)` is self-contained (a single sentence,
    no nested paragraphs of its own in this row's real text) before
    division `(B)` opens.

    Today (`1645a34`) this returns `()`: `(A)` is upper_alpha-shaped, the
    first-marker-shape ladder-selection dispatch (I11) only ever picks
    digit-outermost or federal (lower_alpha-outermost), so `(A)` matches
    neither the federal ladder's position-0 expectation (`lower_alpha`)
    nor any open ancestor (the stack is empty) -- SKIPPED, per I9's own
    fix. Zero recall on Ohio's real, dominant convention."""
    text = oh_row["text"]
    offset = text.index("As used in this section")
    assert text[offset - 4 : offset] == "(A) ", "fixture text/offset drifted"

    path = us_oh.resolve_unit_path(oh_article, char_offset=offset)

    assert path == (UnitStep(kind="upper_alpha", value="A"),), (
        f"an upper_alpha-shaped outermost marker (Ohio's real, dominant "
        f"convention -- 53.8% of all 33,161 real OH rows, 99.4% of rows "
        f"with any genuine structure at all) must resolve with "
        f"kind='upper_alpha'; got {path!r} (today's bug drops it entirely "
        f"-- neither ladder currently selectable by `resolve_unit_path` "
        f"expects upper_alpha at position 0)"
    )


# --- 2: sibling replacement at the outermost level, plus first nesting --


def test_i11_oh_sibling_at_outermost_level_replaces_its_predecessor_not_nests(
    oh_row, us_oh, oh_article
):
    """The row's second top-level marker, division `(B)`, is a SIBLING of
    `(A)` -- an ordinary second top-level subdivision of section 1531.132,
    not nested inside `(A)`. Division `(B)` opens directly into its own
    first paragraph, `(B)(1)` (no bare `(B)`-only text of its own in this
    row's real shape, mirroring how `(A)` had none either). An offset
    inside `(B)(1)`'s own text must resolve to `(upper_alpha:'B',
    digit:'1')` -- `(B)` REPLACING `(A)` at the SAME (outermost) depth
    (not accumulating into a 2-element upper_alpha path), with `(1)`
    nested one level below it.

    Today (`1645a34`) this resolves to `()`: every marker in this document
    is skipped from the very first one onward, since the ladder locked
    onto the federal (lower_alpha-outermost) shape at `(A)` and
    upper_alpha never matches position 0 or any (nonexistent) ancestor."""
    text = oh_row["text"]
    offset_b1 = text.index(
        "The chief of the division of wildlife shall not designate"
    )
    assert text[offset_b1 - 4 : offset_b1] == "(1) ", "fixture text/offset drifted"

    path_b1 = us_oh.resolve_unit_path(oh_article, char_offset=offset_b1)
    assert path_b1 == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="1"),
    ), (
        f"(B) must replace (A) at the outermost level (not accumulate "
        f"alongside it), with paragraph (1) nested one level below it; "
        f"got {path_b1!r} (today's bug: empty, both (A) and (B) are "
        f"dropped)"
    )


# --- 3: genuine multi-level nesting, each level its own correct kind ----


def test_i11_oh_genuine_four_level_nesting_keeps_each_levels_own_correct_kind(
    oh_row, us_oh, oh_article
):
    """Real Ohio nesting for this row: division `(B)`'s second paragraph,
    `(B)(2)`, opens subparagraph `(a)`, which itself opens
    sub-subparagraphs `(i)` and `(ii)` -- a genuine FOUR-level chain,
    `upper_alpha > digit > lower_alpha > lower_roman`, exactly the
    dominant real order this Planner measured (996/17,849 upper_alpha-
    outermost rows share this exact 4-level shape; the full 5-level
    extension, `... > upper_roman`, occurs in 40 rows but not in this
    particular one). An offset inside `(a)`'s own text (between where
    `(a)` opens and `(i)` opens) must resolve to the 3-element path; an
    offset inside `(i)` must resolve to the full 4-element path.

    Today (`1645a34`), because `(A)`/`(B)`/`(1)`/`(2)` are ALL skipped
    (the ladder locked onto federal at `(A)` and nothing at positions 0-1
    of that ladder ever matches an upper_alpha/digit token), `(a)` is the
    FIRST token in the entire document that ever matches ANYTHING
    (federal ladder position 0 = lower_alpha, and `(a)` genuinely is
    lower_alpha-shaped) -- so `(a)` gets wrongly pushed as if it were the
    document's own OUTERMOST unit, and `(i)` then wrongly REPLACES it as
    an (incorrect) sibling, rather than nesting beneath it -- collapsing
    what should be a real 4-level chain down to a single, wrongly-kinded,
    wrongly-valued 1-element path."""
    text = oh_row["text"]
    offset_a = text.index("The chief of the division of wildlife shall terminate")
    assert text[offset_a - 4 : offset_a] == "(a) ", "fixture text/offset drifted"
    offset_i = text.index("Pleads guilty to a felony")
    assert text[offset_i - 4 : offset_i] == "(i) ", "fixture text/offset drifted"

    path_a = us_oh.resolve_unit_path(oh_article, char_offset=offset_a)
    assert path_a == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="2"),
        UnitStep(kind="lower_alpha", value="a"),
    ), f"expected the real 3-level (B)(2)(a) chain; got {path_a!r}"

    path_i = us_oh.resolve_unit_path(oh_article, char_offset=offset_i)
    assert path_i == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="2"),
        UnitStep(kind="lower_alpha", value="a"),
        UnitStep(kind="lower_roman", value="i"),
    ), f"expected the real 4-level (B)(2)(a)(i) chain; got {path_i!r}"


# --- 4: sibling replacement generalizes to every deeper level, and -------
# --- correctly POPS back when a SHALLOWER sibling replaces its own -------
# --- ancestor (proving the fix isn't merely "handle upper_alpha at ------
# --- position 0" but generalizes the whole mechanism, same discipline ---
# --- as the existing OR/I11 file's own second test). ---------------------


def test_i11_oh_sibling_replacement_generalizes_to_every_deeper_level_and_pops_correctly(
    oh_row, us_oh, oh_article
):
    """Four further real sibling relationships in this same row, each
    proving a DIFFERENT depth of the mechanism:

    - `(ii)` replaces `(i)` as a sibling at the DEEPEST (lower_roman)
      level -- the three ancestor levels above it (B, 2, a) are
      unchanged.
    - `(b)` replaces `(a)` as a sibling at the lower_alpha level -- and
      the lower_roman level `(a)` had opened beneath it (`i`/`ii`) is
      correctly DROPPED (not carried over to `(b)`), since `(b)` has no
      roman sub-items of its own in this row's real text.
    - `(3)` replaces `(2)` as a sibling at the digit level -- popping back
      to just `(B, 3)`, dropping BOTH the lower_alpha AND lower_roman
      levels `(2)` had accumulated (`a`/`b`, `i`/`ii`), since `(3)` opens
      no sub-items of its own.
    - `(4)` replaces `(3)` as a sibling at the digit level, same shape.

    Today (`1645a34`), every one of these resolves from the SAME wrongly-
    collapsed baseline described in the previous test's docstring --
    `(b)` wrongly replaces `(i)` as a FIRST-level sibling (both are
    lower_alpha-shaped under the locked federal ladder), and `(3)`/`(4)`
    then get wrongly pushed ONE level DEEPER than `(b)` (federal ladder
    position 1 = digit) instead of nesting under a correctly-tracked
    `(B)` ancestor two levels up."""
    text = oh_row["text"]
    offset_ii = text.index("Pleads guilty to a misdemeanor")
    assert text[offset_ii - 5 : offset_ii] == "(ii) ", "fixture text/offset drifted"
    offset_b = text.index("The chief shall suspend from employment")
    assert text[offset_b - 4 : offset_b] == "(b) ", "fixture text/offset drifted"
    offset_3 = text.index("Division (B) of this section does not apply")
    assert text[offset_3 - 4 : offset_3] == "(3) ", "fixture text/offset drifted"
    offset_4 = text.index("The suspension from employment, or the termination")
    assert text[offset_4 - 4 : offset_4] == "(4) ", "fixture text/offset drifted"

    path_ii = us_oh.resolve_unit_path(oh_article, char_offset=offset_ii)
    assert path_ii == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="2"),
        UnitStep(kind="lower_alpha", value="a"),
        UnitStep(kind="lower_roman", value="ii"),
    ), f"(ii) must replace (i) at the deepest level only; got {path_ii!r}"

    path_b = us_oh.resolve_unit_path(oh_article, char_offset=offset_b)
    assert path_b == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="2"),
        UnitStep(kind="lower_alpha", value="b"),
    ), (
        f"(b) must replace (a) at the lower_alpha level, dropping the "
        f"roman level (a) had opened beneath it; got {path_b!r}"
    )

    path_3 = us_oh.resolve_unit_path(oh_article, char_offset=offset_3)
    assert path_3 == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="3"),
    ), (
        f"(3) must replace (2) at the digit level, popping back to just "
        f"(B, 3) since (3) opens no sub-items of its own; got {path_3!r}"
    )

    path_4 = us_oh.resolve_unit_path(oh_article, char_offset=offset_4)
    assert path_4 == (
        UnitStep(kind="upper_alpha", value="B"),
        UnitStep(kind="digit", value="4"),
    ), f"(4) must replace (3) at the digit level; got {path_4!r}"


# --- 5: containment at the matcher.definition_covers_mention level ------


def test_i11_oh_containment_bare_outermost_scope_covers_and_excludes_correctly(
    oh_row, us_oh, oh_article
):
    """The live consequence (sprint doc's own zero-miss framing): a
    `scope="subsection"` definition bare-stamped `scope_value='A'` (no
    declared `scope_unit_kind` -- M-D3's outermost-comparison fallback)
    must COVER a mention genuinely inside division `(A)` and EXCLUDE a
    mention genuinely inside sibling division `(B)`, in BOTH directions.

    Today (`1645a34`) this is a TOTAL MISS in the safe direction only:
    `definition_covers_mention` returns `False` for EVERY offset in this
    document (matching this Planner's own live-path measurement in the
    sprint doc's background section: `AFTER: covered=False at a mention
    inside (A) -- zero recall, a MISS` -- not merely under-covering, but
    covering NOTHING, since `resolve_unit_path` returns `()` for `(A)`'s
    own offset and an empty path can never contain a non-empty scope
    value)."""
    text = oh_row["text"]
    offset_a = text.index("As used in this section")
    assert text[offset_a - 4 : offset_a] == "(A) ", "fixture text/offset drifted"
    offset_b1 = text.index(
        "The chief of the division of wildlife shall not designate"
    )
    assert text[offset_b1 - 4 : offset_b1] == "(1) ", "fixture text/offset drifted"

    candidate = DefinitionCandidate(
        terms=("Felony",),
        definition_text="an act or omission punishable as a felony",
        scope="subsection",
        source_article_number="1531.132",
        scope_value="A",
    )

    assert definition_covers_mention(
        candidate, oh_article, offset_a, profile=us_oh
    ), "bare scope_value='A' must cover a mention genuinely inside division (A)"
    assert not definition_covers_mention(
        candidate, oh_article, offset_b1, profile=us_oh
    ), "bare scope_value='A' must NOT cover a mention inside sibling division (B)"


def test_i11_oh_containment_declared_digit_level_scope_covers_nested_and_excludes_siblings(
    oh_row, us_oh, oh_article
):
    """The LEVEL-matching half of M-D3, on Ohio's real ladder: a
    definition declaring `scope_unit_kind='digit', scope_value='2'` (the
    genuine paragraph level under division B, per this row's real
    structure) must cover EVERY mention nested below paragraph `(2)` --
    `(2)(a)`, `(2)(a)(i)`, `(2)(a)(ii)`, `(2)(b)` -- regardless of how
    much deeper each one nests, and must EXCLUDE mentions inside sibling
    paragraphs `(1)`, `(3)`, `(4)` (same digit level, different value).

    Today (`1645a34`) every one of these returns `False` -- the same
    total-miss defect as the previous test, now proven at every depth
    beneath the declared level, not merely the outermost one."""
    text = oh_row["text"]
    offset_1 = text.index(
        "The chief of the division of wildlife shall not designate"
    )
    offset_2a = text.index("The chief of the division of wildlife shall terminate")
    offset_2a_i = text.index("Pleads guilty to a felony")
    offset_2a_ii = text.index("Pleads guilty to a misdemeanor")
    offset_2b = text.index("The chief shall suspend from employment")
    offset_3 = text.index("Division (B) of this section does not apply")
    offset_4 = text.index("The suspension from employment, or the termination")

    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially numbered paragraph",
        scope="subsection",
        source_article_number="1531.132",
        scope_value="2",
        scope_unit_kind="digit",
    )

    for label, offset in [
        ("(2)(a)", offset_2a),
        ("(2)(a)(i)", offset_2a_i),
        ("(2)(a)(ii)", offset_2a_ii),
        ("(2)(b)", offset_2b),
    ]:
        assert definition_covers_mention(candidate, oh_article, offset, profile=us_oh), (
            f"digit-level scope '2' must cover the {label} mention -- nested "
            f"below paragraph (2) regardless of depth"
        )

    for label, offset in [("(1)", offset_1), ("(3)", offset_3), ("(4)", offset_4)]:
        assert not definition_covers_mention(candidate, oh_article, offset, profile=us_oh), (
            f"digit-level scope '2' must NOT cover the {label} mention -- a "
            f"sibling paragraph at the same digit level, different value"
        )
