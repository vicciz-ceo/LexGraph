"""M-R107 future-law controls through real ingest and persistence."""

from __future__ import annotations

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

from backend.tests.unit.test_us_body_preamble_b1_structural_future_law_red import CASES


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_b1_future_law_structure_at_live_persistence_altitude(case, db_session, matter_with_users):
    """The direct controls must hold after the pipeline's real dedup semantics."""
    matter = matter_with_users
    row = {
        "act_id": f"FUTURE_{case['name'].upper()}",
        "section_number": case["section_title"].split()[0],
        "chapter": "future",
        "section_title": case["section_title"],
        "text": case["text"],
    }
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=f"M-R107 future law {case['name']}",
        rows=[row],
        jurisdiction=case["jurisdiction"],
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}

    for false_term in case.get("false_terms", ()):
        assert false_term not in by_term
    if case["heading"] is None:
        assert not by_term
        return
    definition = by_term.get(case["term"])
    assert definition is not None
    assert definition.definition_text == case["definition_text"]
    assert definition.scope == "law-wide"
    for term, definition_text in case.get("additional_terms", {}).items():
        prior = by_term.get(term)
        assert prior is not None
        assert prior.definition_text == definition_text
        assert prior.scope == "law-wide"
