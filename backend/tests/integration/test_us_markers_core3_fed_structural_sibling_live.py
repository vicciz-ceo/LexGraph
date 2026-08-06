"""Held core-3 RED for `USC_T8_C12_S1101`'s Roman structural sibling.

The fixture is a byte-verbatim excerpt of the real corpus row, with source
revision, full-row SHA-256, and offsets recorded beside the row.  This is the
real ingest -> `run_definition_linking` -> persisted `Definition` path; an API
or E2E tier adds no parser coverage beyond that persistence call site.
"""

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
    / "us_markers_core3_pd2_real_row_excerpts.json"
)


def _load_fed_row() -> dict:
    return next(
        row
        for row in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        if row["act_id"] == "USC_T8_C12_S1101"
    )


def test_core3_fed_fixture_is_a_provenanced_verbatim_real_row_excerpt():
    row = _load_fed_row()
    provenance = row["_fixture_provenance"]
    assert provenance["source"] == "vaquill/open-us-law"
    assert provenance["text_is_verbatim_excerpt"] is True
    assert row["section_title"] == "Definitions"


def test_core3_held_real_pipeline_stops_before_roman_structural_sibling(
    db_session, matter_with_users
):
    """HELD RED — core-3 owns classification of the Roman sibling `(i)`.

    The real FED term ends after its enumerated offense clause.  It must
    retain the in-definition section citation and `(1)`--`(3)` list, but not
    swallow the next `(i) With respect ...` provision or later annotation
    material.  This deliberately does not prescribe the core-3 generic marker
    algorithm; it asserts the persisted observable boundary only."""
    row = _load_fed_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="core-3 real FED structural-sibling excerpt",
        rows=[{key: value for key, value in row.items() if not key.startswith("_")}],
        jurisdiction="US-FED",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    serious = next(definition for definition in definitions if "serious criminal offense" in definition.terms)

    assert serious.definition_text == (
        "—\n\n(1) any felony;\n\n(2) any crime of violence, as defined in section 16 of title 18; "
        "or\n\n(3) any crime of reckless driving or of driving while intoxicated or under the "
        "influence of alcohol or of prohibited substances if such crime involves personal injury to another."
    )
    assert "With respect to each nonimmigrant alien" not in serious.definition_text
    assert "Editorial Notes" not in serious.definition_text
