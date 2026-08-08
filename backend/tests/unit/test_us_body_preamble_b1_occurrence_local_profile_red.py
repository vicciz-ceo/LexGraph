"""M-R106 direct-profile REDs for B1's qualifying-occurrence boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile


ROWS = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/us_statutes/us_b1_occurrence_local_rows.json").read_text()
)


@pytest.mark.parametrize("row_id", tuple(ROWS))
def test_b1_extracts_from_its_qualifying_occurrence_not_the_start_of_the_row(row_id):
    """Source-faithful AR/ID/TX text before B1 must never become a term."""
    row = ROWS[row_id]
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
