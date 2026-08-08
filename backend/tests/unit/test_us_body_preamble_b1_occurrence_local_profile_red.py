"""M-R106 direct-profile REDs for B1's qualifying-occurrence boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile


ROWS = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/us_statutes/us_b1_occurrence_local_rows.json").read_text()
)


@pytest.mark.parametrize(
    "row_id", ("STATE_AR_T23_C81_S8_S23-81-810", "STATE_ID_T48_C18_S48-1805")
)
def test_b1_rejects_non_structural_in_this_prose(row_id):
    """A colon after ordinary prose is not a definitions preamble."""
    row = ROWS[row_id]
    profile = get_profile(row["jurisdiction"])
    assert profile.derive_heading_from_body(row["section_title"], row["text"]) is None


def test_b1_keeps_tx_later_quote_and_defining_verb_occurrence_local():
    """Only TX's later legal-unit quote-and-verb clause is a definition."""
    row = ROWS["STATE_TX_Clg_C111_S111.068"]
    profile = get_profile(row["jurisdiction"])
    assert profile.derive_heading_from_body(row["section_title"], row["text"]) == "Definitions"
    candidates = profile.extract_definitions_from_section(
        row["text"], scope="law-wide", heading_was_derived=True
    )
    by_term = {term: candidate for candidate in candidates for term in candidate.terms}

    for false_term in row["false_terms"]:
        assert false_term not in by_term
    if genuine_term := row.get("genuine_term"):
        assert by_term[genuine_term].definition_text == row["genuine_definition_text"]
        assert by_term[genuine_term].scope == "law-wide"
