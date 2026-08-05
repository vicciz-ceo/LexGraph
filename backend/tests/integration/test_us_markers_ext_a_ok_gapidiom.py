"""RED test -- sprint 2026-08-04-defs-us-markers, phase-2 Planner A, item
A4 -- the cross-state "idiom-GAP" shape (appears in NJ 15.4%, MI 13.7%,
NY 8.8%, OK 8.4% of each state's POST-quote-engine residual -- the
second-most-recurring shape across the whole C5 set after NY's own
quote-period convention).

**The gap.** `us_markers_boundary._TIGHT_IDIOM_RE` (the shared
quote-anchored engine's idiom gate) deliberately requires "means"/"shall
mean"/"has the meaning" to sit ESSENTIALLY IMMEDIATELY after a quoted
term's closing quote -- by design (its own docstring: this tightness is
what rejects phantom matches like WA's nested `"motor vehicle"`). But a
recurring real statutory idiom interposes an entire clause between the
quoted (or bare `the term X`) subject and its own verb:

    The term "person" as used in this act shall mean any individual,
    firm, partnership, corporation, or business entity of any kind or
    character, or the executor, administrator, trustee, receiver,
    assignee, or personal representative thereof.

(real row `STATE_OK_T47_S47-157.5`, Oklahoma). `"person" ... shall mean`
has a 20+ character gap ("as used in this act") the tight idiom gate
correctly refuses to bridge (bridging it unconditionally would risk the
exact false-positive class ruling U-R1 exists to prevent). This is
architecturally the SAME gap-idiom problem `us_markers_tn_idiom.py`
already solves for TN's "has the same meaning AS INTERPRETED BY" gap --
a narrow, state-or-phrase-scoped rule, not a further loosening of the
shared tight gate (which would risk corpus-wide false positives per that
module's own design rationale).

RED today: `extract_quote_anchored_entries`'s tight-idiom gate does not
bridge this gap (confirmed directly against this real row before writing
this fixture); no OK-scoped rule exists for it either (confirmed by grep
of `backend/app/definition_links/rules/`)."""

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
    / "us_markers_ext_a_ok_gapidiom_rows.json"
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_fixture_row_is_the_expected_real_ok_row():
    row = _load_row()
    assert row["act_id"] == "STATE_OK_T47_S47-157.5"


def test_real_pipeline_recovers_ok_gap_idiom_definition(db_session, matter_with_users):
    """Live path: real `ingest_us_statute_rows` -> real
    `run_definition_linking` (internally calls `USProfile.
    extract_definitions_from_section`, not a stub). Today creates 0
    `Definition` rows for this act_id -- the tight-idiom gate's own
    designed-in gap, not a marker/boundary defect."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="STATE_OK_T47_S47-157.5 A4 gap-idiom RED",
        rows=[row],
        jurisdiction="US-OK",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term = {}
    for d in definitions:
        for t in d.terms:
            by_term[t] = d

    assert "person" in by_term, (
        f"expected 'person' captured from OK's real 'term \"X\" as used in this act "
        f"shall mean ...' gap-idiom body; today's real pipeline yields "
        f"{sorted(by_term)!r} -- the tight-idiom gate does not bridge the "
        "interposed 'as used in this act' clause, and no OK-scoped gap rule exists."
    )
    spot = by_term["person"]
    assert spot.definition_text.strip() == (
        "any individual,\n\nfirm, partnership, corporation, or business entity of any kind or\n\n"
        "character, or the executor, administrator, trustee, receiver,\n\n"
        "assignee, or personal representative thereof."
    ), f"got {spot.definition_text!r}"
