"""I11 RED tests -- `resolve_unit_path` mis-kinds the OUTERMOST sub-article
marker as generic `sub` when that marker is a DIGIT, instead of the correct
`"digit"` kind (sprint 2026-08-04-defs-core-dispatch, items I10/I11, manager
ruling M-D3, seam v2.7).

**The defect, precisely.** `us_profile._UNIT_PATH_LADDER` is a fixed,
POSITIONAL sequence -- `("lower_alpha", "digit", "upper_alpha",
"lower_roman", "upper_roman", "double_lower_alpha", "double_upper_alpha")`
-- baked into `resolve_unit_path` as "whatever kind the ladder expects at
THIS depth". Position 0 (the outermost/first-seen marker in a document)
always expects `"lower_alpha"`. That is the real, dossier-confirmed FEDERAL
convention (`(a) > (1) > (A) > (i) > ...`, v2.4 Section 3) -- but it is NOT
universal. Real US STATE drafting very commonly reverses the first two
rungs: subsections are numbered `(1)`, `(2)`, `(3)`... (DIGIT-outermost),
with lettered paragraphs `(a)`, `(b)`, `(c)` nested one level below them.

Manager-reproduced example (sprint doc, item I11): on real Oregon row
`STATE_OR_T22_C238_S238.300` (ORS Section 238.300), offsets inside `(1)`
yield `UnitStep(kind='sub', value='1')` -- not `UnitStep(kind='digit',
value='1')`. This Planner re-verified that exact finding directly against
the live code (see the report for the full offset-by-offset trace) and
additionally found the corruption COMPOUNDS: because the mis-kinded `'sub'`
step is a kind `_marker_matches_kind` never recognizes as a sibling match,
the very next genuine top-level digit marker (`(2)`) is pushed as a NEW,
DEEPER step instead of correctly REPLACING `(1)` as a sibling -- turning two
top-level subsections into a spurious 2-level-deep path.

**Fixture provenance.** `cd_i11_or_scoped_inline_row.json` is a byte-for-byte
vendored copy of ONE row (`STATE_OR_T22_C238_S238.300`) from
`backend/tests/fixtures/us_statutes/us_scoped_inline_rows.json` as it exists
on `claude/defs-us-scoped-inline` @ `79ee374` (read via `git show
79ee374:...`, read-only, per this Planner's brief -- prior ruling R6, no test
may read the live corpus). Verified identical to the source branch's own
JSON object by direct dict comparison (see the Planner's report) before
being committed here as this test file's own, independent fixture.

**Why real-shape offsets, not the whole row.** The row's own prose contains
several genuine, SEPARATE noise sources unrelated to this defect -- an
internal cross-reference ("...under subsection (1) of this section..." at
byte offset 1752), a cross-reference to a DIFFERENT statute's subsection
("...ORS 237.976 ... (2)..." at offset 4633), a bracketed-word aside
("(nonrefund)" at offset 1316) -- each of which `_US_UNIT_MARKER_RE` also
greedily consumes, since it has no way to distinguish "this document's own
structural marker" from "a parenthesized token that happens to look like
one". This is the SAME class of pre-existing, out-of-scope gap the I9
Planner already identified and declined to fold into their own tests (see
`test_definition_links_cd_i9_unit_path_annotations.py`'s module docstring,
"embedded external citations ... a pre-existing, unrelated gap, not
conflated into these tests"). Every offset pinned below is deliberately
chosen to sit in a CLEAN window of the real row -- before any such noise
token -- so these tests isolate the I11 kind-mis-classification defect
without silently also depending on that separate, unfixed defect.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile
from app.definition_links.rules.registry import UnitStep
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


@pytest.fixture()
def or_row() -> dict:
    rows = json.loads((FIXTURES_DIR / "cd_i11_or_scoped_inline_row.json").read_text(encoding="utf-8"))
    assert len(rows) == 1 and rows[0]["act_id"] == "STATE_OR_T22_C238_S238.300"
    return rows[0]


@pytest.fixture()
def us_or():
    return get_profile("US-OR")


@pytest.fixture()
def or_article(or_row) -> MatcherArticle:
    return MatcherArticle(
        number="238.300",
        heading="238.300 Service retirement allowance",
        body=or_row["text"],
        chapter="238",
    )


def test_i11_or_outermost_digit_marker_resolves_with_digit_kind_not_sub(
    or_row, us_or, or_article
):
    """The row's very first parenthesized token is the genuine top-level
    subsection marker `(1)` (`"...service retirement allowance which shall
    consist of the following annuity and pensions:\\n\\n(1) A refund
    annuity..."`). An offset immediately inside it, before any further
    marker or noise token appears anywhere earlier in the body, must
    resolve to a SINGLE-element path whose one step is kind `"digit"` --
    not `"sub"`."""
    text = or_row["text"]
    offset = text.index("A refund annuity")
    assert text[offset - 4 : offset] == "(1) ", "fixture text/offset drifted"

    path = us_or.resolve_unit_path(or_article, char_offset=offset)

    assert path == (UnitStep(kind="digit", value="1"),), (
        f"a digit-shaped outermost marker must resolve with kind='digit'; "
        f"got {path!r} (today's bug pushes it as a generic kind='sub' step "
        f"instead, because the ladder's position-0 slot only ever expects "
        f"'lower_alpha')"
    )


def test_i11_or_second_top_level_digit_marker_replaces_its_sibling_not_nests_beneath_it(
    or_row, us_or, or_article
):
    """The row's second top-level marker, `(2)` (`"...\\n\\n(2) Intentionally
    left blank..."`), is a SIBLING of `(1)` -- both are ordinary top-level
    subsections of section 238.300, not one nested inside the other. Once
    `(1)` is correctly kinded `digit` (the fix this file pins), the
    existing sibling-replacement logic in `resolve_unit_path` must
    recognize `(2)` as matching that SAME kind and replace it at the same
    (outermost) depth -- yielding a single-element path, not a spurious
    2-deep one. Today this fails compoundingly: `(1)` is mis-kinded `sub`
    (a kind `_marker_matches_kind` can never match against), so `(2)` gets
    pushed one level DEEPER instead of replacing it."""
    text = or_row["text"]
    offset = text.index("Intentionally left blank")
    assert text[offset - 4 : offset] == "(2) ", "fixture text/offset drifted"

    path = us_or.resolve_unit_path(or_article, char_offset=offset)

    assert path == (UnitStep(kind="digit", value="2"),), (
        f"the second top-level digit subsection must REPLACE its sibling "
        f"at the same (outermost) depth, not nest beneath it; got {path!r} "
        f"(today's bug: {{'sub':'1', 'digit':'2'}} -- two levels instead "
        f"of one, because the mis-kinded 'sub' step from (1) can never be "
        f"recognized as (2)'s sibling)"
    )


def test_i11_or_lower_alpha_paragraph_marker_keeps_its_correct_kind_beneath_the_digit_subsection(
    or_row, us_or, or_article
):
    """Real Oregon nesting for this row: subsection `(2)` contains lettered
    paragraphs `(a)`, `(b)`, `(c)` -- ONE level below the digit-kinded
    subsection, not the same level and not two levels down. An offset just
    inside `(a)` (`"...(2) Intentionally left blank -Ed.\\n\\n(a) A life
    pension (nonrefund) for current service..."`, taken BEFORE the
    "(nonrefund)" aside) must resolve to a genuine 2-element path: the
    digit subsection, then the lower_alpha paragraph -- both with their
    OWN correct kind, pinning that fixing the outermost step (I11's core
    claim) does not itself corrupt or mis-kind the correctly-classified
    deeper step."""
    text = or_row["text"]
    offset = text.index("A life pension")
    assert text[offset - 4 : offset] == "(a) ", "fixture text/offset drifted"
    assert text.index("(nonrefund)") > offset, "fixture no longer clean before the noise aside"

    path = us_or.resolve_unit_path(or_article, char_offset=offset)

    assert path == (
        UnitStep(kind="digit", value="2"),
        UnitStep(kind="lower_alpha", value="a"),
    ), (
        f"expected the real 2-level digit-then-lower_alpha nesting for "
        f"this row's (2)(a); got {path!r}"
    )


# --- Genuine deep nesting under a DIGIT-outermost ladder --------------------
#
# I9 already carries a mutation-proven guard
# (`test_i9_resolve_unit_path_still_resolves_the_real_federal_four_level_nesting`,
# `test_definition_links_cd_i9_unit_path_annotations.py`) that genuine 4-level
# nesting still resolves on a real FEDERAL row -- whose own outermost marker
# is `lower_alpha` (the shape `_UNIT_PATH_LADDER`'s position-0 slot already
# expects correctly). That test is not duplicated here. But it does NOT
# cover the case this file's own fixture proves is real and distinct: a
# body whose ladder ORDER is reversed at the top (digit-outermost,
# lower_alpha-second). A fix that merely "special-cases the very first
# marker" without generalizing the sibling-matching/replacement mechanism
# to every depth could pass the three tests above (which only reach depth
# 2) while still failing to resolve genuine DEEP nesting under a
# digit-first ladder. The real OR row's own deeper structure (its `(2)(b)`
# and `(2)(c)` branches) is NOT usable for this -- by the time the body
# reaches them it has already accumulated the SEPARATE citation/aside-noise
# corruption documented in this file's module docstring (offsets 1316,
# 1639, 1752 all fall before them). Proving deep nesting there would
# silently entangle two different defects.
#
# This test is therefore deliberately ONE LEVEL BELOW the live/real-corpus
# path: a hand-authored (not corpus-read) body, mirroring the REAL digit
# 	> lower_alpha > upper_alpha > lower_roman order this file's own fixture
# already demonstrates for its first two levels, extended synthetically to
# 4 levels -- the same discipline the EXISTING
# `test_resolve_unit_path_supports_genuinely_deep_nesting_not_hard_coded_to_two_or_three_levels`
# (`test_definition_links_profiles.py`) already uses for the federal shape.
def test_i11_synthetic_digit_outermost_body_still_resolves_genuine_four_level_nesting(us_or):
    """Hand-authored body (NOT corpus-read -- see note above), mirroring
    the real OR digit>lower_alpha>upper_alpha>lower_roman order this
    file's own fixture demonstrates for its first two levels: `(1)
    Subsection. (a) Paragraph. (A) Subparagraph. (i) A deeply nested
    provision lives here.` A resolver that hard-codes 'lower_alpha is
    always position 0' and merely swaps in 'digit' for position 0 without
    fixing the general sibling/ladder mechanism could plausibly still cap
    out at 1-2 levels for this shape even after fixing the outermost step
    alone -- this is the guard against that narrower fix."""
    body = (
        "(1) Subsection. (a) Paragraph. (A) Subparagraph. (i) A deeply "
        "nested provision lives here, four levels below the section "
        "itself, under a digit-outermost ladder."
    )
    article = MatcherArticle(number="1", heading="Definitions", body=body, chapter="1")
    deep_offset = body.index("A deeply nested provision")

    path = us_or.resolve_unit_path(article, char_offset=deep_offset)

    assert len(path) >= 4, (
        f"expected a path at least 4 levels deep for a genuinely 4-level "
        f"nested digit-outermost position; got {path!r} (length "
        f"{len(path)})"
    )
    kinds = tuple(step.kind for step in path[:4])
    values = tuple(step.value for step in path[:4])
    assert kinds == ("digit", "lower_alpha", "upper_alpha", "lower_roman"), kinds
    assert values == ("1", "a", "A", "i"), values
