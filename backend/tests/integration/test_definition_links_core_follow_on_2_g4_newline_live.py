"""Live-path RED for G4's cross-newline genuine-entry regression."""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "core_follow_on_2_g4_newline_rows.json"
)


def test_dc_cross_line_genuine_entry_records_digit_three_on_the_live_assertion_path(
    db_session, matter_with_users
):
    """Drive ingest -> extraction/rule dispatch -> mention linking ->
    persisted assertion path on the byte-verified full DC row.  A small
    throwaway rule supplies a deterministic term whose sole occurrence is
    inside genuine entry (3); production still owns path resolution.
    """
    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import TermClauseRule, register_term_clause_rule
    from app.models.assertion import Assertion

    row = next(
        row
        for row in json.loads(FIXTURE.read_text(encoding="utf-8"))
        if row["act_id"] == "STATE_DC_T4_C2_S4-204.52"
    )
    term = "medical assistance programs"
    assert row["text"].count(term) == 1

    def _parse(block):
        if term not in block:
            return []
        return [
            DefinitionCandidate(
                terms=(term,),
                definition_text="programs used by the live-path probe",
                scope="law-wide",
            )
        ]

    register_term_clause_rule(
        TermClauseRule(jurisdiction_codes=("US-DC",), parse=_parse)
    )
    matter = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="DC G4 newline live-path fixture",
        rows=[row],
        jurisdiction="US-DC",
    )

    result = run_definition_linking(
        db_session,
        matter_id=matter["matter_id"],
        triggered_by_user_id=matter["contributor_id"],
    )
    uses = [
        item
        for item in result["created_assertions"]
        if item["assertion_type"] == "USES_DEFINITION"
        and f'"{term}"' in item["proposition"]
    ]
    assert len(uses) == 1, result

    assertion = db_session.get(Assertion, uses[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion.id)
    assert len(paths) == 1
    assert tuple((step.kind, step.value) for step in paths[0]) == (("digit", "3"),), paths
