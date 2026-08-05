"""G4 RED tests, cases 3-4 + non-regression guard -- sprint
2026-08-05-defs-core-follow-on-2, gate G4 ("citation pin-cite stack
corruption"). Split out of `test_definition_links_core_follow_on_2_g4_
citation_pincite_stack.py` (which carries the full defect writeup and
cases 1-2) purely to respect this program's 300-line-per-file style gate
-- see that sibling module's docstring for the complete G4 design
rationale, the fix specification, and what does/does not change.

Case 3 (ME) demonstrates a federal-citation pin-cite fabricating a WRONG
non-empty path where the correct answer is EMPTY (no genuine marker has
opened yet at all) -- the sprint doc's "worse than the empty-path S-R16
class". Case 4 (OR, the S-R14-validation-row latch) demonstrates a
DIFFERENT corruption shape from cases 1-3: an ORDINARY in-prose
cross-reference with NO citation-looking section number anywhere near it
-- a discriminator built only around "Section N"/"§"/USC/CFR patterns
will not catch this one; it needs the structural-unit-word half of the
discriminator (see sibling module).
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
def us_sc():
    return get_profile("US-SC")


@pytest.fixture()
def us_tx():
    return get_profile("US-TX")


@pytest.fixture()
def us_me():
    return get_profile("US-ME")


@pytest.fixture()
def us_or():
    return get_profile("US-OR")


# --- Case 3: ME federal-citation pin-cite fabricates a path from nothing -


def test_me_federal_citation_pincite_does_not_fabricate_a_path_before_any_genuine_marker(
    core_rows, us_me
):
    """Real `STATE_ME_T30-A_P2_C141_S3010`. The row's very first
    parenthesized token in the whole document is the federal citation
    pin-cite in `"...a multichannel video programming distributor as
    defined in 47 United States Code, Section 522(13)."` -- appearing
    BEFORE the document's own first genuine top-level marker ("1. Credits
    and refunds..."). No genuine sub-article unit is open at any point in
    between; the correct path throughout that span is `()`. Confirmed
    today's actual output immediately before the genuine "1." marker is
    `(digit:'13',)` -- a wholly fabricated, non-empty, WRONG path (the
    sprint doc's "worse than the empty-path S-R16 class")."""
    row = core_rows["STATE_ME_T30-A_P2_C141_S3010"]
    text = row["text"]
    assert "Section 522(13)" in text, (
        "fixture text changed -- the ME federal-citation pin-cite is no longer present verbatim"
    )
    marker_anchor = "1. Credits and refunds"
    assert marker_anchor in text
    offset = text.index(marker_anchor) - 5
    assert "Section 522(13)" in text[: text.index(marker_anchor)], (
        "the citation must precede the genuine marker for this test to isolate the defect"
    )
    article = MatcherArticle(
        number="3010", heading="Franchisee obligations", body=text, chapter="141"
    )

    path = us_me.resolve_unit_path(article, char_offset=offset)

    assert path == (), (
        f"no genuine sub-article marker has opened yet at this offset (only the "
        f"federal citation's own pin-cite precedes it) -- expected the empty path, "
        f"got a fabricated {path!r}"
    )


# --- Case 4: OR in-prose cross-reference latches the stack (no citation) -


def test_or_in_prose_subsection_cross_reference_does_not_latch_the_stack(core_rows, us_or):
    """Real `STATE_OR_T22_C238_S238.300` (the S-R14-validation-row latch).
    Genuine context is `(digit:'2', lower_alpha:'a')`. The row's own text
    reads: `"...subject to paragraph (b) of this subsection, shall be an
    amount which, when added to the sum of the annuity, if any, under
    subsection (1) of this section and the annuity..."` -- an ORDINARY
    cross-reference to elsewhere in the SAME section, not a citation to a
    numbered section at all (no "Section"/"§"/USC/CFR anywhere near it).
    Both "paragraph (b)" (a forward reference to a paragraph not yet
    opened) and "subsection (1)" must be ignored. Confirmed today's
    actual output right after "under subsection (1) of this section" is
    `(digit:'1',)` -- the genuine (2)(a) context is discarded entirely,
    latched onto the cross-reference's own bare digit instead."""
    row = core_rows["STATE_OR_T22_C238_S238.300"]
    text = row["text"]
    phrase = "under subsection (1) of this section"
    assert phrase in text, "fixture text changed -- the OR cross-reference phrase is no longer present"
    article = MatcherArticle(
        number="238.300", heading="Service retirement allowance", body=text, chapter="238"
    )

    offset = text.index(phrase) + len(phrase) + 5
    path = us_or.resolve_unit_path(article, char_offset=offset)

    assert len(path) == 2, (
        f"expected the genuine 2-level (2)(a) path to survive the cross-reference "
        f"untouched; got {path!r}"
    )
    assert path[0].kind == "digit"
    assert path[0].value == "2", (
        f"top-level digit was latched onto the cross-reference's own bare '(1)'; "
        f"expected the genuinely-open '2', got {path[0].value!r}"
    )
    assert path[1].kind == "lower_alpha"
    assert path[1].value == "a"


# --- Non-regression: clean rows (no citation pin-cite at all) must be -----
# --- BYTE-FOR-BYTE unaffected. GREEN today; must stay green, identical. --


def test_sc_clean_row_without_any_pincite_is_unaffected(core_rows, us_sc):
    """Real `STATE_SC_T14_C7_A7_S14-7-845` -- byte-verified free of any
    citation pin-cite (every parenthesized token in this row is a
    genuine structural marker). Must resolve to `(upper_alpha:'B',)`
    BEFORE and AFTER this item, identically -- this is the SAME clean row
    the scoped-inline panel's own pass-7 fixture uses for the identical
    purpose on a sibling branch, re-verified here independently."""
    row = core_rows["STATE_SC_T14_C7_A7_S14-7-845"]
    text = row["text"]
    assert "school employee" in text
    article = MatcherArticle(number="14-7-845", heading="Jury service", body=text, chapter="7")

    path = us_sc.resolve_unit_path(article, char_offset=text.index("school employee"))

    assert len(path) == 1
    assert path[0].kind == "upper_alpha"
    assert path[0].value == "B"


def test_tx_clean_row_without_any_pincite_is_unaffected(core_rows, us_tx):
    """Real `STATE_TX_Coc_C2301_S2301.551` -- byte-verified free of any
    citation pin-cite. Must resolve to `(lower_alpha:'a',)` BEFORE and
    AFTER this item, identically."""
    row = core_rows["STATE_TX_Coc_C2301_S2301.551"]
    text = row["text"]
    anchor = '"fee" does not include'
    assert anchor in text
    article = MatcherArticle(
        number="2301.551", heading="Vehicle lessor fees", body=text, chapter="2301"
    )

    path = us_tx.resolve_unit_path(article, char_offset=text.index(anchor))

    assert len(path) == 1
    assert path[0].kind == "lower_alpha"
    assert path[0].value == "a"
