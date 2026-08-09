"""M-R121 uniform source-truth REDs and controls through real persistence."""

from __future__ import annotations

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition
from tests.unit.test_mr121_b1_source_truth_red import CASES


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["family"])
def test_mr121_source_truth_through_definition_persistence(case, db_session, matter_with_users):
    matter = matter_with_users
    act_id = f"MR121_{case['family'].upper()}"
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=f"M-R121 {case['family']}",
        rows=[
            {
                "act_id": act_id,
                "section_number": "121.901",
                "chapter": "qa-future",
                "section_title": "M-R121 novel source-truth section",
                "text": case["text"],
            }
        ],
        jurisdiction=case["jurisdiction"],
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter["matter_id"],
        triggered_by_user_id=matter["contributor_id"],
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}
    for term in case.get("absent", ()):
        assert term not in by_term
    for term, definition_text in case.get("expected", {}).items():
        assert by_term[term].definition_text == definition_text
        assert by_term[term].scope == "law-wide"
    for term, definition_prefix in case.get("expected_prefix", {}).items():
        assert by_term[term].definition_text.startswith(definition_prefix)
        assert by_term[term].scope == "law-wide"
    for term in case.get("unique", ()):
        assert sum(term in definition.terms for definition in definitions) == 1
    if forbidden := case.get("forbidden_text"):
        assert all(forbidden not in definition.definition_text for definition in definitions)
