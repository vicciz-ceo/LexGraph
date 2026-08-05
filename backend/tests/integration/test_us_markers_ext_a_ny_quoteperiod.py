"""RED test -- sprint 2026-08-04-defs-us-markers, phase-2 Planner A, item
A4 -- NY's SECOND-largest post-quote-engine residual shape.

**Coverage arithmetic (A2).** After simulating registration into the
ALREADY-BUILT quote-anchored engine (see `test_us_markers_ext_a_ny_
quoteengine.py`, the dominant shape, 82.9% of NY's post-ingest zero-yield
population), NY's remaining residual is 216 rows (1,262 - 1,046). Of
those 216, classifying by regex against the real remaining text: **58
rows (26.9%) share THIS shape** -- a numbered/lettered marker followed
immediately by a QUOTED term ending in a PERIOD (either inside or outside
the closing quote mark, both spellings occur in the real corpus), then a
capitalized definition sentence with NO defining verb at all ("means"/
"shall mean"/etc never appears) -- pure apposition, punctuation-only
signal. Real row `STATE_NY_ADEA_A6_S80`:

    1. "Highway." Any private or public highway, street, way, waterway, or
    other place used for travel.
    2. "Commissioner." The state commissioner of transportation.

Architecturally this is the SAME family as AL's `(N) ALLCAPS TERM.
Definition` and NC's `(N) TermName.--Definition` (already registered in
`us_markers_unquoted_terms.py`, reusing `_extract_marker_anchored`) --
the only difference is the term is QUOTED here (AL/NC's terms are bare),
and the separator is a single period (not `.--`). A likely cheap fix:
a new NY-scoped entry regex following `_extract_marker_anchored`'s own
shape, not a new engine.

RED today: neither the quote-anchored engine (which requires an idiom
word like "means" immediately after the quote -- absent here) nor
`us_markers_unquoted_terms.py` (whose 3 registered regexes are AL/NC/DC-
specific, none matching a QUOTED term + bare period) recognizes this
shape -- confirmed by grep of `backend/app/definition_links/rules/`
before writing this fixture. U-R11 applied: fixture stores RAW corpus
bytes (literal `\\n`); this test's live `ingest_us_statute_rows` call
applies the same transform production does."""

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
    / "us_markers_ext_a_ny_quoteperiod_rows.json"
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_fixture_row_is_the_expected_real_ny_row():
    row = _load_row()
    assert row["act_id"] == "STATE_NY_ADEA_A6_S80"
    assert "\\n" in row["text"]
    assert "\n" not in row["text"], "fixture must store RAW corpus bytes, per U-R11"


def test_real_pipeline_recovers_ny_quoted_period_no_idiom_definitions(db_session, matter_with_users):
    """Live path: real `ingest_us_statute_rows` (applies the U-R11
    `text.replace("\\n","\n")` transform) -> real `run_definition_linking`
    (internally calls `USProfile.extract_definitions_from_section`, not a
    stub). Today creates 0 `Definition` rows for this act_id."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="STATE_NY_ADEA_A6_S80 A4 quote-period RED",
        rows=[row],
        jurisdiction="US-NY",
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

    expected_subset = {"Highway", "Commissioner"}
    assert expected_subset <= set(by_term), (
        f"expected at least {sorted(expected_subset)!r} captured from NY's real "
        f"quoted-period-no-idiom Definitions body; today's real pipeline yields "
        f"{sorted(by_term)!r} -- no registered rule recognizes a numbered marker + "
        "quoted term + bare period (no defining verb) entry boundary."
    )
    spot = by_term["Commissioner"]
    assert spot.definition_text.strip() == "The state commissioner of transportation.", (
        f"got {spot.definition_text!r}"
    )
