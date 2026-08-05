"""G4 follow-on REDs and two-sided controls for cross-newline context.

All records are byte-verified against snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad` after the production ingest
normalization (literal ``\\n`` -> real newline). Tests never read the
corpus. DC and AK pin the narrow positive surface; NY, OK, KS, and HI pin
real continuation, abbreviation, and commentary shapes that broader
newline exceptions would corrupt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "core_follow_on_2_g4_newline_rows.json"
)


@pytest.fixture()
def rows() -> dict[str, dict]:
    return {
        row.get("fixture_id", row["act_id"]): row
        for row in json.loads(FIXTURE.read_text(encoding="utf-8"))
    }


def _article(row: dict) -> Article:
    return Article(
        number=row["section_number"],
        heading=row["section_title"],
        body=row["text"],
        chapter=row["chapter"],
    )


def _pairs(path) -> tuple[tuple[str, str], ...]:
    return tuple((step.kind, step.value) for step in path)


def test_dc_genuine_entry_after_cross_line_section_citation_advances_to_digit_three(rows):
    """Real `STATE_DC_T4_C2_S4-204.52`: the prior entry ends with
    ``§ 4-204.53`` and the next physical line opens genuine entry ``(3)``.
    Core-2 currently strips the newline as generic whitespace, rejects the
    genuine marker as a pin-cite, and leaves stale path ``digit:2``.
    """
    row = rows["STATE_DC_T4_C2_S4-204.52"]
    text = row["text"]
    assert "§ 4-204.53\n(3) “Medicaid” means" in text

    path = get_profile("US-DC").resolve_unit_path(
        _article(row), char_offset=text.index("“Medicaid” means")
    )

    assert _pairs(path) == (("digit", "3"),), (
        "the genuine cross-line (3) entry must replace open sibling (2); "
        f"got stale/corrupt path {path!r}"
    )


def test_ny_cross_line_section_year_parenthetical_remains_a_rejected_citation(rows):
    """Real `Section 112\n(1965), ...`: the comma proves the
    parenthetical continues the citation/year phrase, not a new entry.
    """
    row = rows["STATE_NY_AEXC_A19-G_T1_S501-E"]
    text = row["text"]
    anchor = "Section 112\n(1965), has authorized"
    assert anchor in text

    path = get_profile("US-NY").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert path == (), f"year parenthetical must not fabricate digit:1965; got {path!r}"


def test_ny_cross_line_section_subdivision_chain_remains_a_rejected_citation(rows):
    """Real `§ 1911\n(a) (1) of this act`: both chained pin-cites
    continue the reference and must remain invisible to the marker stack.
    """
    row = rows["STATE_NY_AUDC_A19_S1906-A"]
    text = row["text"]
    anchor = "§ 1911\n(a) (1) of this act"
    assert anchor in text

    path = get_profile("US-NY").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert path == (), f"cross-line (a)(1) pin-cite chain fabricated {path!r}"


def test_ny_soft_wrapped_structural_reference_remains_rejected(rows):
    """Real `paragraph\n(c) of subdivision ... of section 210.20`.
    This belongs to the 1,221 structural-word population, which the narrow
    citation-only proposal deliberately leaves byte-for-byte unchanged.
    """
    row = rows["STATE_NY_ACPL_P2_TI_A210_S210.35"]
    text = row["text"]
    anchor = "paragraph\n(c) of subdivision one of section 210.20"
    assert anchor in text

    path = get_profile("US-NY").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert path == (), f"soft-wrapped paragraph reference fabricated {path!r}"


def test_ak_section_word_blank_line_genuine_parenthesized_entry_advances(rows):
    """Real `Section 32\n\n(F)` is the second positive side of the
    deliberately narrow Section/§ + parenthesized exception.
    """
    row = rows["ak_section_word_parenthesized"]
    text = row["text"]
    anchor = "Section 32\n\n(F) Township 19 North"
    assert anchor in text

    path = get_profile("US-AK").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert _pairs(path) == (("upper_alpha", "F"),), path


def test_ok_blank_line_section_year_parenthetical_remains_rejected(rows):
    """The sixth real continuation is the blank-line version of the
    Crime Control Act `Section 112 ... (1965),` citation.
    """
    row = rows["STATE_OK_T10A_S10A-2-9-102"]
    text = row["text"]
    anchor = "Section 112\n\n(1965), has authorized"
    assert anchor in text

    path = get_profile("US-OK").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert path == (), f"blank-line year continuation fabricated {path!r}"


def test_ks_bare_state_code_year_label_remains_rejected_on_public_path(rows):
    """Real `BR\n\n12\n\n1972.` is date/table text, not a unit.
    Accepting the period token would fabricate `digit:1972`; the safe
    proposal leaves the broad bare-state-code arm unchanged.
    """
    row = rows["STATE_KS_C94_A0_S94-00"]
    text = row["text"]
    anchor = "BR\n\n12\n\n1972.\n\nA proposition"
    assert anchor in text

    path = get_profile("US-KS").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert path == (), f"year/date table text fabricated {path!r}"


def test_hi_commentary_period_heading_remains_rejected(rows):
    """Real `COMMENTARY ON §704-400\n\nI.` is commentary, not an
    operative statutory unit; all period-style cases stay closed.
    """
    row = rows["STATE_HI_D5_T37_C704_S704-400"]
    text = row["text"]
    anchor = "COMMENTARY ON §704-400\n\nI. Physical"
    assert anchor in text

    path = get_profile("US-HI").resolve_unit_path(
        _article(row), char_offset=text.index(anchor) + len(anchor)
    )

    assert path == (), f"commentary heading fabricated operative path {path!r}"
