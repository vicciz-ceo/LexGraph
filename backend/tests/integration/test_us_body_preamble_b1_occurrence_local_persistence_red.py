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


@pytest.mark.parametrize(
    "row_id", ("STATE_AR_T23_C81_S8_S23-81-810", "STATE_ID_T48_C18_S48-1805")
)
def test_b1_non_structural_in_this_prose_does_not_dispatch_to_persistence(
    row_id, db_session, matter_with_users
):
    """The real pipeline must not create Definitions from AR/ID prose."""
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


def test_b1_tx_later_quote_and_defining_verb_persists_occurrence_local(
    db_session, matter_with_users
):
    """The real pipeline retains TX's later definition but not budget quotes."""
    row = ROWS["STATE_TX_Clg_C111_S111.068"]
    matter = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="M-R108 STATE_TX_Clg_C111_S111.068",
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
    genuine = by_term.get(row["genuine_term"])
    assert genuine is not None
    assert genuine.definition_text == row["genuine_definition_text"]
    assert genuine.scope == "law-wide"
