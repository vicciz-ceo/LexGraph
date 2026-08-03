"""Sprint 2026-08-04-defs-us-scoped-inline (Planner, D5: gate U5 regression
guard). Program working-baseline regression-guard states for every US
sprint: IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK.

These tests are GREEN TODAY (Phase A ships only a new, standalone rule
module -- ruling S-R2 forbids editing `pipeline.py` at all, so nothing
about the real pipeline's behavior changes yet). They exist as the
regression TRIPWIRE for Phase B (once the Developer wires the new rule
module into `pipeline.py`'s `else:` branch after core merges): every
assertion here must remain true unchanged.

Two directions, matching U5's own wording ("baseline states' capture rates
hold" + implicitly "and nothing new gets swept in that shouldn't be"):

1. A baseline state's ALREADY-WORKING Definitions-heading capture (DE,
   reusing the existing vendored `de_sample_rows.json` fixture and mirroring
   `test_qa_regression_us_state_law.py::
   test_real_pipeline_recognizes_a_real_us_definitions_section_for_a_us_document`
   byte-for-byte in spirit) must still work after this sprint's rule module
   exists and is wired in -- it operates on a DIFFERENT code path (the
   `if is_definitions_section:` branch, never the `else:` branch this
   sprint's rule module will occupy), so it must be provably unaffected.
2. Real baseline-state rows with NO family-1 trigger at all, run through
   the FULL real pipeline (not just the rule module in isolation --
   complementary to, not a duplicate of, this sprint's unit-level negative
   controls in `test_us_scoped_inline_rules_negative_controls.py`), must
   still produce zero definitions from those rows once Phase B lands.
"""

from __future__ import annotations

import json
import pathlib

US_SCOPED_INLINE_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)
DE_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _row(act_id: str) -> dict:
    rows = json.loads(US_SCOPED_INLINE_FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == act_id)


def _clean(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def test_baseline_delaware_definitions_section_still_captures_after_this_sprints_module_exists(
    db_session, matter_with_users
):
    """DE's real, already-working `"Definitions"`-headed section (the same
    `STATE_DE_T5_C7_SVIII_S796` row `test_qa_regression_us_state_law.py`'s
    own live-path trace uses) must keep producing its 3 real terms
    (Affiliate / Branch office / Insured depository institution) -- this
    goes through `pipeline.py`'s `if is_definitions_section:` branch, a
    code path this sprint's Phase A/B work never touches (S-R2 forbids
    editing `pipeline.py`'s existing branches; Phase B only adds a NEW call
    inside the `else:` branch)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = json.loads(DE_FIXTURE.read_text(encoding="utf-8"))

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (U5 baseline regression guard)",
        rows=rows,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "Affiliate" in all_terms
    assert "Branch office" in all_terms
    assert "Insured depository institution" in all_terms


def test_baseline_montana_row_with_no_family1_trigger_produces_no_definitions_end_to_end(
    db_session, matter_with_users
):
    """Full-pipeline companion to this sprint's unit-level negative
    controls: a real Montana row (one of the program's 12 baseline
    regression states) with no family-1 trigger at all must still produce
    zero definitions when driven through the REAL, complete
    `run_definition_linking` -- not just the rule module called in
    isolation."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row("STATE_MT_T76_C13_P1_S76-13-107")
    assert "as used in this" not in row["text"].lower()
    assert "for purposes of this" not in row["text"].lower()

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Montana Code Annotated (U5 baseline regression guard)",
        rows=[_clean(row)],
        jurisdiction="US-MT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert result["created_definitions"] == []


def test_baseline_new_york_and_indiana_rows_with_no_trigger_produce_no_definitions_end_to_end(
    db_session, matter_with_users
):
    """Same proof, two more baseline states (NY/IN) in one matter, to
    guard against a cross-document false positive too (e.g. a scope-unit
    word from one document's chapter number bleeding into another
    document's candidate scan)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ny_row = _row("STATE_NY_ATAX_A9_S197-D")
    in_row = _row("STATE_IN_T13_A23_C12_S13-23-12-3")

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="New York Tax Law (U5 baseline regression guard)",
        rows=[_clean(ny_row)],
        jurisdiction="US-NY",
    )
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Indiana Code (U5 baseline regression guard)",
        rows=[_clean(in_row)],
        jurisdiction="US-IN",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert result["created_definitions"] == []
