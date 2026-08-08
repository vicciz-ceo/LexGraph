"""M-R106 live persistence REDs for occurrence-local B1 extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition


ROWS = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/us_statutes/us_b1_occurrence_local_rows.json").read_text()
)


@pytest.mark.parametrize("row_id", tuple(ROWS))
def test_b1_occurrence_boundary_controls_persisted_terms(row_id, db_session, matter_with_users):
    """The real ingest-to-persistence call site must enforce the same boundary."""
    row = ROWS[row_id]
    matter = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=f"M-R106 {row_id}",
        rows=[row],
        jurisdiction=row["jurisdiction"],
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}

    for false_term in row["false_terms"]:
        assert false_term not in by_term
    if genuine_term := row.get("genuine_term"):
        assert by_term[genuine_term].definition_text == row["genuine_definition_text"]
        assert by_term[genuine_term].scope == "law-wide"
