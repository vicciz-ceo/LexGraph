"""RED integration test -- sprint 2026-08-04-defs-us-markers, phase-2
Planner B (B4), Ohio.

Family 3 sub-case: OH's DOMINANT convention -- confirmed live, full-corpus
sweep this pass (see `## PB1`) -- is `(A) As used in ...: (1) "term"
means ...` -- a lettered top-level grouping marker (`(A)`) introducing a
digit-paren entry list (`(1)`, `(2)`, ...), both shapes already
structurally supported by the shared engine's existing digit/letter
paren-marker hard-stops. Full-corpus OH: 950 Definitions-headed sections,
949 (99.9%) zero-candidate today. Of those: 0 already correctly-empty;
885 (93.3%) return >=1 candidate from the existing `extract_quote_
anchored_entries` unmodified (462/949 = 48.7% fully clean means-only,
423/949 = 44.6% a means+includes mix -- OH has the HIGHEST includes-idiom
share of all 5 states this pass measured -- 54/949 = 5.7% zero
means-idiom); 64 (6.7%) residual, not further classified this pass.

**This fixture row exposes a real, NEW boundary defect distinct from every
already-shipped guard**, found by this Planner running the unmodified
engine against the real body: OH's real rows commonly append ONE trailing
lettered clause AFTER the digit-paren definitions list that is NOT itself
a defined term (`(B) The department of health shall encourage ...`), plus
a `Last updated <date> at <time>` scrape-artifact stamp at the very end.
Neither is caught by any existing hard-stop: `_LETTER_MARKER_RE`'s guard
only fires when a QUOTE follows within a short lookahead (by design, to
avoid treating a genuinely nested non-defining sub-clause as a boundary --
see `us_markers_boundary.py`'s own docstring for the WA "Threat"/"(a) To
cause bodily injury" precedent this guard protects), and `(B) The
department...` has no quote anywhere near it, so the LAST digit-paren
entry's own definition swallows straight through `(B)`'s entire clause
plus the trailing timestamp. Confirmed live: "Umbilical cord blood"'s
captured definition_text is 415 chars (contains "(B) The department of
health..." and ends mid-sentence well short of "Last updated") instead of
the genuine ~95-char single-sentence definition.

Today's real pipeline (OH registered nowhere) creates 0 definitions for
this row -- RED for that reason first; the trailing-clause-swallow guard
is the SECOND assertion, proving a naive "just register OH" fix would
still fail this test, per ruling U-R1."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_ext_b_oh.json"
)


def _load_row(act_id: str) -> dict:
    rows = {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}
    return rows[act_id]


def _ingest_and_link(db_session, matter, *, jurisdiction: str, title: str, row: dict) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=title,
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    return [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]


def test_oh_fixture_heading_is_recognized_as_definitions_section():
    row = _load_row("STATE_OH_T21_C2108_S2108.61")
    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} must already be recognized as a Definitions heading"
    )


def test_real_pipeline_recovers_oh_definitions_without_swallowing_trailing_non_defining_clause(
    db_session, matter_with_users
):
    """`STATE_OH_T21_C2108_S2108.61` -- OH umbilical-cord-blood-donation
    statute. 3 real terms (Health care institution, Health care
    professional, Umbilical cord blood) inside an `(A) ...: (1)/(2)/(3)`
    grouping, followed by a real, genuinely non-defining `(B)` clause and a
    trailing `Last updated <date>` scrape stamp. The LAST entry
    ("Umbilical cord blood") must not swallow either."""
    row = _load_row("STATE_OH_T21_C2108_S2108.61")
    assert row["section_title"] == "§ 2108.61. Umbilical cord blood donation definitions"

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-OH", title="OH ext-b trailing-clause", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {
        "Health care institution",
        "Health care professional",
        "Umbilical cord blood",
    }, f"expected all 3 real OH terms, got {sorted(terms)!r}"

    by_term = {t: d for d in definitions for t in d.terms}
    cord_blood = by_term["Umbilical cord blood"]
    for forbidden in ("The department of health", "Last updated", "(B)"):
        assert forbidden not in cord_blood.definition_text, (
            f"'Umbilical cord blood' illegally swallowed trailing non-defining content "
            f"({forbidden!r} leaked in): {cord_blood.definition_text!r}"
        )
    assert 20 <= len(cord_blood.definition_text) <= 200, (
        f"'Umbilical cord blood' definition is {len(cord_blood.definition_text)} chars, "
        f"expected the genuine ~95-char single-sentence definition: "
        f"{cord_blood.definition_text!r}"
    )
