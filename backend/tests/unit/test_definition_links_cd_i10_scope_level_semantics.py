"""I10 RED tests -- `scope="subsection"` LEVEL semantics (sprint
2026-08-04-defs-core-dispatch, item I10, manager ruling M-D3, seam v2.7).

**The defect, restated from the sprint doc.** A family rule stamps
`scope_value='(c)'` -- the INNERMOST label it actually means, parenthesized,
per real family-panel practice. `matcher._subsection_contains_offset`
compares `mention_path[0].value` (the OUTERMOST step, exact string) against
`allowed = (definition.scope_value,)`. Three independent mismatches
compound in that one comparison: LEVEL (always outermost, regardless of
what the rule meant), FORMAT (`'(c)'` parenthesized vs a bare label), and
KIND (I11 -- the outermost step can be flatly mis-kinded). This file pins
the LEVEL and FORMAT halves (ruling M-D3); I11's own file
(`test_definition_links_cd_i11_resolver_kind_correctness.py`) pins the KIND
half, on which every test below that declares `scope_unit_kind` critically
depends (M-D3's own "I10 and I11 must land together" -- see the discovery
in the digit-outermost backward-compatibility test below, which shows I10's
"unchanged today" claim is ITSELF only true once I11 is fixed).

**Level: `M-D3` says: 'subsection' -> the outermost lettered/numbered unit,
'paragraph' -> the digit level, 'subparagraph' -> the upper-alpha level.**
This wording is written from the FEDERAL citation convention
((a)-subsection > (1)-paragraph > (A)-subparagraph, v2.4 Section 3's own
dossier-confirmed shape) -- most of the tests below use a body shaped
exactly that way, to match the spec's own literal wording unambiguously.
But (see this Planner's report, and the digit-outermost tests below,
reusing the SAME real Oregon row I11 vendored) a large share of real US
STATE conventions reverse the first two rungs: `(1)`-subsection >
`(a)`-paragraph > `(A)`-subparagraph. Under that shape 'paragraph' does NOT
mean the digit level -- digit IS the outermost/subsection level there, and
'paragraph' means `lower_alpha`. The MECHANISM this file pins (find the
step whose `.kind` equals the declared `scope_unit_kind`, compare its
`.value`) is jurisdiction-agnostic; the ENGLISH-WORD-to-kind-string
translation named in M-D3's prose is not, and the digit-outermost tests
below exist specifically to prove the mechanism still works correctly when
a rule author declares the CORRECT kind for their own jurisdiction's real
shape, not the federal one. See the Planner's report for the full escalation
-- this is flagged, not silently resolved by picking one convention for
every test.

**Level used here throughout: `.scope` is unconditionally `"subsection"`
for every test below** (that string is what routes `_in_scope`/
`_subsection_contains_offset` to the below-article containment check at
all -- see `matcher.py`); `scope_unit_kind` is the NEW, additive field that
narrows WHICH below-article depth within that check. This matches M-D3's
own text precisely ("a SUBSECTION-scoped definition declares which level it
means").

**Level of proof.** Every test in this file calls `matcher.
definition_covers_mention` directly against a real, non-stub
`sections.Article` (`MatcherArticle`) and the real `USProfile.
resolve_unit_path` (via `profile=us_profile`) -- the SAME two production
functions/objects `pipeline.py`'s Stage 3 actually calls
(`definition_covers_mention(candidate, using_matcher_article,
edge.char_offset, profile=profile)`, confirmed by direct read, v2.5's own
finding). This is deliberately ONE LEVEL BELOW the full `run_definition_
linking` DB pipeline (no ingest, no assertions, no term-matching/extraction
stage) -- chosen so each format/level combination can be pinned precisely
and independently without needing a bespoke `ScopeTriggerRule` + wiki
fixture per combination. Two representative combinations are ADDITIONALLY
proven on the full live `run_definition_linking` path in the companion
integration file, `test_definition_links_pipeline_cd_i10_scope_level_semantics_live.py`
-- see that file for why only two (not the whole matrix) are worth the
extra DB-pipeline cost.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.matcher import definition_covers_mention
from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


@pytest.fixture()
def us_profile():
    # Any "US-*" code shares the one USProfile instance/behavior (module
    # docstring, us_profile.py) -- US-DE matches the existing prior-sprint
    # live tests' own convention.
    return get_profile("US-DE")


# --- Federal-shaped body: (a) subsection > (1) paragraph > (A) subparagraph,
# --- matching M-D3's own literal wording unambiguously. Hand-authored, no
# --- parenthesized tokens anywhere outside the genuine markers themselves
# --- (same discipline the existing
# --- `test_a_subsection_scoped_definition_covers_a_mention_nested_three_levels_deep...`
# --- live test's own docstring explains: any incidental "(x)"-shaped prose
# --- text is indistinguishable from a real marker and corrupts the stack).


_FEDERAL_BODY = (
    "(a) Opening subsection of this section.\n"
    "(1) Paragraph one under subsection a. WIDGET_A1_MARK is here.\n"
    "(A) Subparagraph A under paragraph one. WIDGET_A1A_MARK is here.\n"
    "(B) Subparagraph B under paragraph one. WIDGET_A1B_MARK is here.\n"
    "(2) Paragraph two under subsection a. WIDGET_A2_MARK is here.\n"
    "(b) A different subsection entirely.\n"
    "(1) Paragraph one under subsection b. WIDGET_B1_MARK is here.\n"
)


@pytest.fixture()
def federal_article() -> MatcherArticle:
    return MatcherArticle(number="1", heading="Definitions", body=_FEDERAL_BODY, chapter=None)


def _offset(anchor: str) -> int:
    return _FEDERAL_BODY.index(anchor)


# --- Group A: format normalization (bare vs parenthesized), no declared ----
# --- scope_unit_kind -- the existing, already-live outermost-comparison ----
# --- mechanism, on the FEDERAL (already lower_alpha-outermost, already ----
# --- correctly-kinded-today) shape. -----------------------------------------


def test_i10_bare_outermost_stamp_on_the_federal_shape_already_links_and_excludes_correctly(
    us_profile, federal_article
):
    """Control/regression-guard, NOT a new-behavior RED: a bare label
    (`'a'`, no parens, no declared `scope_unit_kind`) on a body whose
    outermost marker is ALREADY correctly kinded today (federal shape,
    lower_alpha-outermost) must keep working exactly as the prior sprint's
    own live C1 proof already established -- this is the "backward
    compatible by construction" guarantee M-D3 rule 3 requires, pinned
    here at the unit level too so the whole matrix in this file has one
    consistent, explicit baseline to compare every other case against."""
    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially regulated item",
        scope="subsection",
        source_article_number="1",
        scope_value="a",
    )
    assert definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A1_MARK"), profile=us_profile
    ), "a bare outermost-label stamp must cover a mention inside its own subsection"
    assert not definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_B1_MARK"), profile=us_profile
    ), "a bare outermost-label stamp must NOT cover a mention inside a sibling subsection"


def test_i10_parenthesized_outermost_stamp_is_normalized_to_bare_and_behaves_identically(
    us_profile, federal_article
):
    """RULING M-D3 point 1: a rule that (against the bare-label contract)
    stamps `scope_value='(a)'` -- parenthesized, the real shape the sprint
    doc's own defect report cites (`'(c)'`) -- must be defensively
    normalized (surrounding parens/whitespace stripped) so it behaves
    IDENTICALLY to the bare `'a'` case above, not silently never-match.
    Today it always returns False for both offsets (format mismatch:
    `'(a)' != 'a'`), which is wrong in the SAME direction for both -- an
    under-inclusive bug, not an over-inclusive one, but still a bug."""
    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially regulated item",
        scope="subsection",
        source_article_number="1",
        scope_value="(a)",
    )
    assert definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A1_MARK"), profile=us_profile
    ), "a parenthesized outermost-label stamp must normalize and cover its own subsection's mention"
    assert not definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_B1_MARK"), profile=us_profile
    ), "a parenthesized outermost-label stamp must still exclude a sibling subsection's mention"


# --- Group B: LEVEL matching -- the core M-D3 mechanism, federal shape. ----
# --- Declaring scope_unit_kind must make containment compare at THAT ------
# --- level, not the outermost step, in BOTH directions. --------------------


def test_i10_scope_declared_at_the_paragraph_digit_level_matches_across_different_outer_subsections(
    us_profile, federal_article
):
    """The core LEVEL claim: `scope_unit_kind='digit'` (M-D3's own
    'paragraph' example) must make containment search for the step whose
    KIND is `'digit'` and compare ITS value -- not `mention_path[0]`
    (today's unconditional outermost comparison). Proof that this is
    genuinely LEVEL-based, not merely a different fixed position: paragraph
    `(1)` under subsection `(a)` and paragraph `(1)` under subsection `(b)`
    have DIFFERENT outermost steps ('a' vs 'b') but the SAME digit-level
    value ('1') -- a scope declared at the digit level must cover BOTH,
    something an outermost-only comparison could never do (today, this
    definition's own `scope_value='1'` compared against `mention_path[0]`
    -- 'a' or 'b' -- matches NEITHER, so today this returns False for
    every mention, not merely the wrong one)."""
    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially numbered item",
        scope="subsection",
        source_article_number="1",
        scope_value="1",
        scope_unit_kind="digit",
    )
    assert definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A1_MARK"), profile=us_profile
    ), "digit-level scope '1' must cover the (a)(1) mention"
    assert definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_B1_MARK"), profile=us_profile
    ), "digit-level scope '1' must ALSO cover the (b)(1) mention -- same paragraph level, different outer subsection: this is what proves LEVEL matching, not merely a different fixed position"
    assert not definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A2_MARK"), profile=us_profile
    ), "digit-level scope '1' must NOT cover the (a)(2) mention -- same outer subsection, different paragraph value"


def test_i10_scope_declared_at_the_subparagraph_upper_alpha_level_matches_only_its_own_subparagraph(
    us_profile, federal_article
):
    """M-D3's 'subparagraph' example (`scope_unit_kind='upper_alpha'`).
    `(a)(1)(A)` and `(a)(1)(B)` share the SAME outermost step ('a') AND
    the same paragraph step ('1') -- they differ ONLY at the subparagraph
    level. An outermost-only (or even paragraph-level) comparison could
    never discriminate between them; this pins that a subparagraph-level
    declaration does."""
    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially lettered item",
        scope="subsection",
        source_article_number="1",
        scope_value="A",
        scope_unit_kind="upper_alpha",
    )
    assert definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A1A_MARK"), profile=us_profile
    ), "subparagraph-level scope 'A' must cover the (a)(1)(A) mention"
    assert not definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A1B_MARK"), profile=us_profile
    ), "subparagraph-level scope 'A' must NOT cover the sibling (a)(1)(B) mention"
    assert not definition_covers_mention(
        candidate, federal_article, _offset("WIDGET_A1_MARK"), profile=us_profile
    ), "subparagraph-level scope 'A' must NOT cover a shallower mention that has no subparagraph step at all (interpretation this Planner is pinning explicitly, per this file's own module docstring's spec-completion note: a declared level absent from mention_path's own steps means out-of-scope, never a silent match)"


# --- Group C: the real, non-federal shape -- Oregon's digit-outermost -----
# --- convention (the SAME vendored row I11's own file uses). Reused here, --
# --- not re-vendored, per this Planner's report: the real-shapes matrix ---
# --- this item exists to build must include MORE than one ladder order, --
# --- and Oregon's is the one the sprint doc's own defect report is drawn --
# --- from. -------------------------------------------------------------


@pytest.fixture()
def or_row() -> dict:
    rows = json.loads((FIXTURES_DIR / "cd_i11_or_scoped_inline_row.json").read_text(encoding="utf-8"))
    assert len(rows) == 1 and rows[0]["act_id"] == "STATE_OR_T22_C238_S238.300"
    return rows[0]


@pytest.fixture()
def or_article(or_row) -> MatcherArticle:
    return MatcherArticle(
        number="238.300",
        heading="238.300 Service retirement allowance",
        body=or_row["text"],
        chapter="238",
    )


def test_i10_bare_outermost_stamp_on_the_digit_outermost_shape_is_broken_today_by_i11s_own_defect(
    us_profile, or_row, or_article
):
    """This is the test that surfaces WHY M-D3 requires I10 and I11 to land
    together: on the REAL Oregon (digit-outermost) shape, TODAY's bare,
    no-declared-kind, outermost-comparison path -- the exact mechanism the
    federal-shape control test above already proves is safe -- is ITSELF
    already broken, entirely because of I11's own resolver defect, with NO
    scope_unit_kind involved at all:

    - `resolve_unit_path` never lets the genuine second top-level marker
      `(2)` replace `(1)` as a sibling (I11: `(1)` is mis-kinded `sub`, a
      kind nothing can ever match against as a sibling) -- so
      `mention_path[0].value` stays the STRING `'1'` for every offset in
      the ENTIRE rest of the document, regardless of which real subsection
      the offset is actually inside.
    - Consequence 1 (over-inclusive): a definition bare-stamped
      `scope_value='1'` WRONGLY covers a mention genuinely inside
      subsection `(2)` too (`mention_path[0].value == '1'` is TRUE at that
      offset, even though the offset is nowhere near subsection 1).
    - Consequence 2 (under-inclusive): a definition bare-stamped
      `scope_value='2'` WRONGLY fails to cover a mention genuinely inside
      subsection `(2)` (`mention_path[0].value` is STILL `'1'`, never
      `'2'`, at that offset) -- including a mention nested even deeper,
      inside paragraph `(2)(a)`.

    Once I11 alone is fixed (this file's companion, I11's own test file),
    `resolve_unit_path` correctly makes `(2)` replace `(1)` as a sibling,
    and BOTH consequences above resolve themselves with ZERO changes
    needed to `_subsection_contains_offset`'s existing bare/no-kind
    fallback branch -- I10's own "unchanged, backward compatible" claim
    for THIS shape is therefore only true once I11 lands, exactly what
    M-D3's own "I10 and I11 must land together" states."""
    text = or_row["text"]
    offset_in_1 = text.index("A refund annuity")
    offset_in_2 = text.index("Intentionally left blank")
    offset_in_2a = text.index("A life pension")

    candidate_1 = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially numbered item",
        scope="subsection",
        source_article_number="238.300",
        scope_value="1",
    )
    assert definition_covers_mention(
        candidate_1, or_article, offset_in_1, profile=us_profile
    ), "bare scope_value='1' must cover the genuine subsection-(1) mention"
    assert not definition_covers_mention(
        candidate_1, or_article, offset_in_2, profile=us_profile
    ), (
        "bare scope_value='1' must NOT cover a mention genuinely inside "
        "sibling subsection (2) -- today this wrongly returns True "
        "(over-inclusive), because mention_path[0].value never advances "
        "past '1' anywhere in the document (I11's own defect)"
    )

    candidate_2 = DefinitionCandidate(
        terms=("Gadget",),
        definition_text="a different specially numbered item",
        scope="subsection",
        source_article_number="238.300",
        scope_value="2",
    )
    assert definition_covers_mention(
        candidate_2, or_article, offset_in_2, profile=us_profile
    ), (
        "bare scope_value='2' must cover a mention genuinely inside "
        "subsection (2) -- today this wrongly returns False "
        "(under-inclusive), same root cause"
    )
    assert definition_covers_mention(
        candidate_2, or_article, offset_in_2a, profile=us_profile
    ), (
        "bare scope_value='2' must ALSO cover a mention nested deeper "
        "still, inside paragraph (2)(a) -- a subsection-level scope "
        "governs everything nested below it"
    )


def test_i10_scope_declared_at_the_paragraph_lower_alpha_level_on_the_digit_outermost_shape(
    us_profile, or_row, or_article
):
    """The mechanism-generalizes-across-ladder-orders proof: on Oregon's
    real digit-outermost body, a rule scoping to "the (a)/(b)/(c)
    paragraph level" -- Oregon's OWN drafting convention's genuine meaning
    of 'paragraph', per this Planner's report -- must declare
    `scope_unit_kind='lower_alpha'` (NOT `'digit'`, which would be wrong
    for this jurisdiction -- see this file's module docstring escalation).
    Declared that way, it must match the `(2)(a)` mention (which has a
    genuine lower_alpha step) and must NOT match a shallower mention with
    no lower_alpha step at all (inside subsection `(1)` or bare `(2)`,
    before its own `(a)` opens)."""
    text = or_row["text"]
    offset_in_1 = text.index("A refund annuity")
    offset_in_2 = text.index("Intentionally left blank")
    offset_in_2a = text.index("A life pension")

    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially lettered item",
        scope="subsection",
        source_article_number="238.300",
        scope_value="a",
        scope_unit_kind="lower_alpha",
    )
    assert definition_covers_mention(
        candidate, or_article, offset_in_2a, profile=us_profile
    ), "paragraph(lower_alpha)-level scope 'a' must cover the (2)(a) mention"
    assert not definition_covers_mention(
        candidate, or_article, offset_in_1, profile=us_profile
    ), "paragraph(lower_alpha)-level scope 'a' must NOT cover a mention with no lower_alpha step at all (inside bare subsection (1))"
    assert not definition_covers_mention(
        candidate, or_article, offset_in_2, profile=us_profile
    ), "paragraph(lower_alpha)-level scope 'a' must NOT cover a mention inside bare subsection (2), before its own (a) paragraph opens"


def test_i10_scope_declared_at_the_digit_subsection_level_explicitly_on_the_digit_outermost_shape(
    us_profile, or_row, or_article
):
    """A rule MAY also declare the outermost level explicitly
    (`scope_unit_kind='digit'`, Oregon's own genuine subsection kind)
    rather than relying on the omitted-kind fallback -- this must produce
    the SAME discrimination as the fallback-based test above, proving the
    kind-string-matching mechanism is symmetric and does not secretly
    require omission to work correctly for the outermost level."""
    text = or_row["text"]
    offset_in_1 = text.index("A refund annuity")
    offset_in_2 = text.index("Intentionally left blank")

    candidate = DefinitionCandidate(
        terms=("Widget",),
        definition_text="a specially numbered item",
        scope="subsection",
        source_article_number="238.300",
        scope_value="1",
        scope_unit_kind="digit",
    )
    assert definition_covers_mention(
        candidate, or_article, offset_in_1, profile=us_profile
    ), "explicit digit-level scope '1' must cover the genuine subsection-(1) mention"
    assert not definition_covers_mention(
        candidate, or_article, offset_in_2, profile=us_profile
    ), "explicit digit-level scope '1' must NOT cover the sibling subsection-(2) mention"
