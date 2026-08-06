"""RED integration test -- sprint 2026-08-04-defs-us-markers, planner pass
3, priority 4 (program-manager-relayed corpus fact 4, re-verified live this
pass).

Fact 4 as relayed: "NC and AL use unquoted-term conventions -- NC
`TermName.--definition`, AL `ALLCAPS TERM. definition` -- invisible to
quote-anchored extractors." AL is already covered (this sprint's own pass
2, `test_us_markers_not_yet_rescued_subcases.py::
test_real_pipeline_recovers_al_unquoted_allcaps_definitions`; its 97.0%
zero-candidate rate reproduces exactly, re-measured this pass, see the
sprint log's `## P3`). **NC is new this pass.**

Confirmed live (scanning `us_nc_statutes.parquet`'s Definitions-headed,
zero-candidate population): NC's dominant unquoted convention is
`(N) TermName.--Definition text.` (sometimes with a stray space before
`.--`, e.g. `Board .--`) -- a numbered marker immediately followed by a
bare (unquoted) term name, then a literal `.--` separator, then the
definition prose. Neither the baseline `(N)`-block splitter (which
requires a QUOTED leading term) nor the existing inline-quoted fallback
sees any of this -- zero quote characters appear anywhere in these
bodies. Full-corpus NC: 522/1,007 (51.8%) of NC's Definitions-headed
sections are zero-candidate (re-measured this pass).

Real, small, single-convention row picked for a clean minimal pin (no
nested lettered sub-clauses, no nested numbering restarts, no nested
`.--` collisions -- those exist elsewhere in NC's corpus and are noted in
the sprint log as further NC sub-shapes, not claimed as fully covered by
this one test)."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_nc_and_ak_mention_rows.json"
)


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def test_nc_fixture_heading_is_recognized_as_a_definitions_section():
    """Sanity: the miss is purely in extraction, not heading detection."""
    rows = _load_rows()
    row = rows["STATE_NC_C41_S41-70"]
    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} must already be recognized as a Definitions heading"
    )


def test_real_pipeline_recovers_nc_unquoted_dash_dash_definitions(db_session, matter_with_users):
    """`STATE_NC_C41_S41-70` -- real North Carolina real-property section,
    2 unquoted terms in the `(N) TermName.--Definition text.` convention,
    no quote characters anywhere in the body. Today's real pipeline
    creates 0 definitions here (same shape as AL's unquoted-ALL-CAPS
    convention, but NC's terms are ordinary-cased, not all-caps -- a
    distinct enough shape that an AL-only rule would not also cover it)."""
    rows = _load_rows()
    row = rows["STATE_NC_C41_S41-70"]

    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="NC unquoted dash-dash",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-NC",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"Conveyance", "Termination"}, f"got {sorted(by_term)!r}"

    conveyance = by_term["Conveyance"]
    assert conveyance.definition_text.strip() == (
        "A transfer of title to real or personal property by deed, devise, "
        "assignment, or other means of transferring title."
    ), f"got {conveyance.definition_text!r}"
    assert "Termination" not in conveyance.definition_text, (
        "Conveyance's definition must not swallow the next entry"
    )

    termination = by_term["Termination"]
    assert termination.definition_text.strip() == (
        "A severance of the right of survivorship resulting in the creation of "
        "a tenancy in common as provided in this Article. The term is used in "
        "the context of an estate with a joint tenancy with a right of "
        "survivorship."
    ), f"got {termination.definition_text!r}"
