"""I9 RED tests -- `resolve_unit_path` mis-parses inline legislative-history
annotations as sub-article markers (sprint 2026-08-04-defs-core-dispatch,
item I9).

**The defect.** `us_profile.resolve_unit_path`'s `_US_UNIT_MARKER_RE`
(`r"\\(([A-Za-z]+|\\d+)\\)"`) matches ANY parenthesized alnum token, with no
distinction between a genuine sub-article marker (`(a)`, `(1)`, `(A)`,
`(i)`...) and Maine's inline revisor annotations (`(NEW)`, `(AMD)`, `(AFF)`,
and siblings -- see measurement below). A token that fails every
`_marker_matches_kind` check (expected-next-rung AND every open ancestor)
falls through to `stack.append(UnitStep(kind="sub", value=token))` --
pushed unconditionally, never skipped. Verified directly against the real,
byte-faithful fixtures below (this Planner re-verified byte-identity
against the live corpus snapshot before writing anything -- see the report
for the diff-free confirmation): every one of NEW/AMD/AFF/RP/RPR/REV/COR's
REAL occurrences in the inherited `cd_i9_me_inline_annotation_rows.json`
fixture produces a spurious step (91/91 occurrences checked, zero
exceptions) -- worse than the sprint doc's own single hand-probed `(AMD)`
example suggested: because annotations routinely appear BEFORE any real
marker in a Maine section body (revisor notes on the preamble/findings
text), the garbage accumulates and can push the stack past the 7-rung
ladder's length, defeating `expected_kind` classification for every
marker -- real or annotation -- that follows. Not pinned exactly here
(entangled with a separate, out-of-scope defect: embedded external
citations like "Public Law 92-500, Section 101(a)(2)" ALSO feed
`_US_UNIT_MARKER_RE`, since it has no way to distinguish "this document's
own structure" from "a citation to a different law quoted inline" -- a
pre-existing, unrelated gap, not conflated into these tests). The tests
below instead pin the ANNOTATION-is-a-no-op invariant directly (before ==
after across the annotation's own span), which isolates the I9 defect
without depending on resolving that separate citation-noise question.

**Fixture provenance (verified by this Planner, not merely inherited):**
all 3 `backend/tests/fixtures/us_statutes/cd_i9_*.json` fixtures were
salvaged from a predecessor's crashed run (commit `b0d3993`) and are
UNREVIEWED work product per the manager's brief. Re-verified here field-by-
field against the live corpus snapshot
(`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/
301000fc3465374ee0f23c3c6953a8a861e95cad`) by exact `act_id` lookup:
  - `cd_i9_me_inline_annotation_rows.json` (3 ME rows: `STATE_ME_T38_C3_S464`,
    `STATE_ME_T24-A_C1_S14`, `STATE_ME_T30-A_P1_C3_S751`) -- BYTE-IDENTICAL
    to `us_me_statutes.parquet` on every shared column.
  - `cd_i9_federal_deep_nesting_row.json` (`USC_T15_C41_S1679g`) --
    BYTE-IDENTICAL to `us_federal_statutes.parquet`.
  - `cd_i9_ut_cross_state_annotation_row.json` (`STATE_UT_T15A_S15A_3_313`)
    -- BYTE-IDENTICAL to `us_ut_statutes.parquet`, but NOT used by any test
    below -- see the module-level note further down for why.

**Severity, reproduced independently:** under the program's zero-miss bar
this is wrong-path data (a real subsection-scope containment check can
silently pass or fail against a corrupted path), not missing data --
matches the sprint doc's own M12-citation-truncation comparison.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

# --- Fixture loading ---------------------------------------------------


def _load_rows(filename: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def me_rows() -> dict[str, dict]:
    return _load_rows("cd_i9_me_inline_annotation_rows.json")


@pytest.fixture()
def federal_rows() -> dict[str, dict]:
    return _load_rows("cd_i9_federal_deep_nesting_row.json")


@pytest.fixture()
def us_me():
    return get_profile("US-ME")


@pytest.fixture()
def us_fed():
    return get_profile("US-FED")


# NOTE on the third inherited fixture, `cd_i9_ut_cross_state_annotation_row.json`
# (`STATE_UT_T15A_S15A_3_313`) -- deliberately UNUSED by any test in this
# file. Investigated and dropped, not overlooked: its body opens with
# "(1) A new IPC, Section 1301.4.1, is added as follows: ..." -- UT's OWN
# top-level paragraph markers are bare digits "(1)".."(7)", not an
# alpha-first ladder, and its one parenthesized uppercase token, "(RP)",
# appears as a SUBSTANTIVE inline abbreviation ("a Reduced Pressure
# Principle Assembly (RP)") -- ordinary technical jargon inside a sentence,
# never inside a Maine-style "[PL ..., Section... (CODE).]" revisor
# bracket, and UT's corpus-wide `BRACKET`-anchored scan (see the Planner's
# report) found ZERO Maine-shaped annotation rows for `us_ut_statutes`.
# This is NOT the same class of defect as I9's inline legislative-history
# annotations -- it is a DIFFERENT, unaddressed gap (the ladder assumes
# alpha-first top-level nesting, which not every US jurisdiction's
# convention follows) that happens to share one coincidental token VALUE
# with one of Maine's own annotation codes. Recorded here, per the
# manager's brief, rather than built into a test that would conflate two
# different bugs.


# --- A: real ME rows where the ONLY parenthesized content is annotation --
# --- noise -- the current (buggy) path is pure garbage; the correct one --
# --- is the empty path (no genuine below-article structure exists to ----
# --- capture in these two small rows). ----------------------------------


def test_i9_me_s14_single_new_annotation_produces_no_spurious_unit_step(me_rows, us_me):
    """`STATE_ME_T24-A_C1_S14` is the cleanest possible case: its ENTIRE
    343-character body contains exactly ONE parenthesized token in the
    whole document -- the trailing revisor annotation `(NEW)` -- and zero
    genuine sub-article markers. `resolve_unit_path` at the end of the
    body must therefore return `()`, the same as if there were no
    parenthesized text at all. Today it does not: the annotation is
    consumed as a phantom `UnitStep(kind='sub', value='NEW')`."""
    row = me_rows["STATE_ME_T24-A_C1_S14"]
    text = row["text"]
    assert re.search(r"\(NEW\)", text), "fixture no longer carries the expected (NEW) annotation"
    article = MatcherArticle(number="14", heading="Definitions", body=text, chapter="1")

    path = us_me.resolve_unit_path(article, char_offset=len(text))

    assert path == (), (
        f"a lone trailing (NEW) revisor annotation, with no genuine "
        f"sub-article marker anywhere in the body, must resolve to the "
        f"empty path; got {path!r}"
    )


def test_i9_me_s751_body_with_only_annotations_produces_the_articles_own_base_path(
    me_rows, us_me
):
    """`STATE_ME_T30-A_P1_C3_S751` uses period-style top-level markers
    ("A.", "B.", "C." ...) -- never parenthesized, so never in scope for
    `_US_UNIT_MARKER_RE` regardless of this defect -- interleaved with 8
    real `(NEW)`/`(AMD)` revisor annotations and NO genuine parenthesized
    marker anywhere. `resolve_unit_path` at the end of the body must
    therefore still return `()` (this document has no below-article path
    for `_US_UNIT_MARKER_RE`'s own marker vocabulary to capture at all).
    Today it returns an 8-element tuple of nothing but garbage `sub`
    steps, one per annotation, in document order."""
    row = me_rows["STATE_ME_T30-A_P1_C3_S751"]
    text = row["text"]
    article = MatcherArticle(number="751", heading="Membership", body=text, chapter="3")

    path = us_me.resolve_unit_path(article, char_offset=len(text))

    assert path == (), (
        f"a body whose only parenthesized tokens are 8 revisor "
        f"annotations, with no genuine parenthesized sub-article marker "
        f"anywhere, must resolve to the empty path; got {path!r} "
        f"(length {len(path)})"
    )


# --- B: the annotation-is-a-no-op invariant, on real ME text, for every --
# --- annotation shape confirmed to occur in the inherited fixture -------
# --- (`STATE_ME_T38_C3_S464` carries all seven). Deliberately does NOT ---
# --- assert an absolute path value at these offsets (the surrounding ----
# --- real text also contains embedded external-law citations like ------
# --- "Public Law 92-500, Section 101(a)(2)", a separate, out-of-scope ---
# --- confound for `_US_UNIT_MARKER_RE` -- see module docstring) -- only -
# --- that stepping over the annotation's own span changes NOTHING. ------


_ANNOTATION_SHAPES = ("NEW", "AMD", "AFF", "RP", "RPR", "REV", "COR")


@pytest.mark.parametrize("token", _ANNOTATION_SHAPES)
def test_i9_me_s464_first_occurrence_of_each_annotation_shape_is_a_noop_on_the_unit_path(
    token, me_rows, us_me
):
    """Each of these 7 shapes genuinely occurs in the real
    `STATE_ME_T38_C3_S464` body (measured directly, not assumed -- see
    the Planner's report for the full corpus-wide token histogram, which
    also surfaced 3 further real Maine codes, RAL/REEN/RNU, not pinned
    here because no committed fixture carries them). None of NEW, AMD,
    AFF, RP, RPR, REV, or COR is a genuine sub-article marker; stepping
    the char_offset from immediately before the token's own parentheses
    to immediately after must leave `resolve_unit_path`'s return value
    UNCHANGED. Today every one of the 7 fails this -- each appends
    exactly one spurious `UnitStep(kind='sub', value=<token>)`."""
    row = me_rows["STATE_ME_T38_C3_S464"]
    text = row["text"]
    match = re.search(rf"\({token}\)", text)
    assert match is not None, f"fixture no longer carries a ({token}) annotation"
    article = MatcherArticle(
        number="464", heading="Classification of Maine waters", body=text, chapter="3"
    )

    before = us_me.resolve_unit_path(article, char_offset=match.start())
    after = us_me.resolve_unit_path(article, char_offset=match.end())

    assert after == before, (
        f"the ({token}) revisor annotation at offset {match.start()} must be "
        f"IGNORED (a no-op on the path) -- got before={before!r}, "
        f"after={after!r} (the real path before the annotation must "
        f"survive UNCHANGED, and no spurious step may be added)"
    )


# --- C: the load-bearing guard -- genuine deep nesting must keep working -
# --- no matter how the Developer fixes the above. This test is GREEN ----
# --- on arrival (no annotations anywhere in this fixture); it exists to -
# --- catch an over-broad exclusion that also swallows real upper_alpha/-
# --- lower_roman markers, which share their single/double-uppercase-----
# --- letter SHAPE with several of the annotation codes above. Mutation---
# --- -proven in the Planner's report (temporarily broke the ladder, ----
# --- confirmed this test catches it, restored via `git checkout --`). ---


def test_i9_resolve_unit_path_still_resolves_the_real_federal_four_level_nesting(
    federal_rows, us_fed
):
    """Real federal fixture `USC_T15_C41_S1679g` (15 U.S.C. Section 1679g),
    genuinely nested 4 levels deep: `(a) Liability established` >
    `(2) Punitive damages` > `(B) Class actions` > `(ii) the aggregate of
    the amount...`. This is the SAME dossier-confirmed federal ladder
    shape (v2.4 Section 3) the existing synthetic
    `test_resolve_unit_path_supports_genuinely_deep_nesting_not_hard_coded_to_two_or_three_levels`
    (`test_definition_links_profiles.py`) already pins -- this test adds
    REAL-corpus grounding for the SAME invariant, on the SAME fixture
    class the manager singled out as the one that would catch an
    over-broad annotation exclusion (a fix that rejects "any short
    uppercase-alpha parenthetical" would ALSO reject this row's genuine
    `(B)` step -- upper_alpha and Maine's own annotation codes overlap in
    raw character shape at length 1; the guard is that `(B)` must still
    resolve as a real ladder step here even after whatever the Developer
    builds to reject NEW/AMD/AFF/RP/RPR/REV/COR)."""
    row = federal_rows["USC_T15_C41_S1679g"]
    text = row["text"]
    anchor = "the aggregate of the amount which the court may allow for each other class member"
    assert anchor in text, "fixture text changed -- anchor no longer present"
    article = MatcherArticle(
        number="1679g", heading="Civil liability", body=text, chapter="41"
    )

    path = us_fed.resolve_unit_path(article, char_offset=text.index(anchor))

    assert len(path) >= 4, (
        f"expected a real 4-level-deep federal path (a > 2 > B > ii); "
        f"got {path!r} (length {len(path)})"
    )
    kinds = tuple(step.kind for step in path[:4])
    values = tuple(step.value for step in path[:4])
    assert kinds == ("lower_alpha", "digit", "upper_alpha", "lower_roman"), kinds
    assert values == ("a", "2", "B", "ii"), values
