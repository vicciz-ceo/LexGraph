"""P-D2 live persisted RED for MN `STATE_MN_P300_323A_C302A_S302A.011`."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_pd1_pd2_real_row_excerpts.json"
)


def _load_mn_row() -> dict:
    return next(
        row
        for row in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        if row["act_id"] == "STATE_MN_P300_323A_C302A_S302A.011"
    )


def test_real_pipeline_persists_mn_relative_idiom_definitions_separately(
    db_session, matter_with_users
):
    """Real ingest + `run_definition_linking` is the relevant live and
    persistence path for a parser defect; a synthetic HTTP/E2E wrapper would
    add no acceptance coverage.  The four named terms currently collapse into
    the long Affiliate candidate (or are absent) and must persist separately.
    """
    row = _load_mn_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="P-D2 real MN Affiliate idiom excerpt",
        rows=[{key: value for key, value in row.items() if not key.startswith("_")}],
        jurisdiction="US-MN",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}

    expected = {
        "Affiliate": "a person that directly or indirectly controls, is controlled by, or is under common control with, a specified person.",
        "Announcement date": "the date of the first public announcement of the final, definitive proposal for the business combination.",
        "Consummation date": "the date of consummation of the business combination or, in the case of a business combination as to which a shareholder vote is taken, the later of (1) the business day before the vote or (2) 20 days before the date of consummation of the business combination.",
    }
    for term, exact_text in expected.items():
        assert term in by_term, f"{term!r} missing from persisted terms: {sorted(by_term)!r}"
        assert by_term[term].definition_text == exact_text

    associate = by_term["Associate"].definition_text
    assert associate.startswith("any of the following: (1) any organization")
    assert associate.endswith("residing in the home of the person.")
    assert "§ Subd. 46." not in associate
