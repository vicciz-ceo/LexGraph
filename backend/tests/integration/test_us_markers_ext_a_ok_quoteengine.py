"""RED test -- sprint 2026-08-04-defs-us-markers, phase-2 Planner A, item
A4 -- US-OK's DOMINANT zero-yield shape (family collapse, item A3).

**Measured, not hypothesised.** US-OK's zero-yield Definitions-headed
population is dominated by the SAME "well-formed quoted-term" convention
already registered for VA/WA/US-FED/UT/TX/SC/AZ in
`us_markers_inline_quote.py` (`"Term" means ...`, either with no marker at
all or with a BARE digit-dot/letter-dot marker baseline's `(N)`-paren
splitter cannot anchor on) -- US-OK is simply not yet in that rule's
`jurisdiction_codes` tuple. Simulating registration (running
`us_markers_boundary.extract_quote_anchored_entries` directly against
EVERY real US-OK zero-yield row, corpus-wide, read-only, nothing written
to the tree) rescues **92.8% (1,063/1,146)** of US-OK's zero-yield population -- this
is the single largest lever for US-OK, not a new convention.

Real row `STATE_OK_T56_S56-1005.3` demonstrates it cleanly. `extract_quote_anchored_entries`
finds all its quoted `"Term" means ...` entries; the assertion below pins
only the subset independently verified byte-clean (no boundary-guard
false positive) -- US-OK rows that cite adjacent statute sections
(`section NNNN`) can occasionally trip the shared engine's
`_TRAILING_MARKER_CHAIN_RE` trailing-digit-dot stripper (measured
corpus-wide across all 5 C5 states' rescued population: 0.0-1.3% of
rescued definitions show this exact citation-truncation signature, MI
highest) -- a real, small, separately-fixable precision gap, not
asserted as correct by this test.

RED today: US-OK has ZERO family-3 rules registered (confirmed by grep
of `backend/app/definition_links/rules/` before writing this fixture) --
`STATE_OK_T56_S56-1005.3` yields 0 definitions via today's real pipeline even though its
body is textbook `"Term" means ...` prose."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_ext_a_quoteengine_ok_rows.json"
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_fixture_row_is_the_expected_real_ok_row():
    """Sanity: byte-verified against the real corpus row."""
    row = _load_row()
    assert row["act_id"] == "STATE_OK_T56_S56-1005.3"


def test_real_pipeline_recovers_ok_quote_anchored_definitions(db_session, matter_with_users):
    """Live path: real `ingest_us_statute_rows` -> real `run_definition_linking`
    (which internally calls `USProfile.extract_definitions_from_section`,
    not a stub). Today US-OK has no registered `EntrySplitterRule`/
    `TermClauseRule` at all, so this creates 0 `Definition` rows; the
    fix (per A3) is registering US-OK into the ALREADY-BUILT
    `us_markers_inline_quote.py` engine (or a thin US-OK-scoped sibling
    reusing the same shared `extract_quote_anchored_entries` /
    `entries_to_quoted_blocks` helpers), not a new convention."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="STATE_OK_T56_S56-1005.3 A4 quote-engine RED",
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

    expected_subset = ['Provider', 'Affiliate', 'Fetal body parts']
    assert set(expected_subset) <= set(by_term), (
        f"expected at least {expected_subset!r} to be captured from US-OK's real "
        f"quote-anchored Definitions body; today's real pipeline yields {sorted(by_term)!r} "
        "-- US-OK has zero family-3 rules registered (the A3 family-collapse fix, "
        "not a new convention)."
    )
    spot = by_term['Fetal body parts']
    assert spot.definition_text.strip() == 'tissue or cells obtained from a\n\ndead human embryo or fetus.', f"got {spot.definition_text!r}"
