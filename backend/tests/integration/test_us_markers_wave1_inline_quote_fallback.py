"""RED integration tests -- sprint 2026-08-04-defs-us-markers, wave 1.

Family 3 sub-case: "no-marker inline-quote" -- a real Definitions-headed US
statute section whose body is a run of `"Term" means ...` sentences with NO
`(N)`-paragraph markers before each quote. `USProfile.extract_definitions_
from_section`'s `(N)`-block splitter yields ZERO candidates on this shape.
The existing `_extract_inline_quoted_definitions` fallback (pipeline.py:
246-289) CAN parse it, but is wired (pipeline.py:405-432) to fire only when
`used_body_derived_heading` is True -- never for VA/WA/FED, whose own real
`section_title` already says "Definitions" outright. Confirmed live
(planner pass 1): today's real `run_definition_linking` creates ZERO
`Definition` rows for every fixture row below (VA 97.2%, WA 98.8%, FED
83.3% of real Definitions-headed sections yield zero candidates,
full-corpus counts -- see the sprint log's `## P1` for the full
methodology, per-jurisdiction rates, and the fixture rows' provenance).

These tests exercise the REAL production call path end-to-end
(`ingest_us_statute_rows` -> `run_definition_linking`, imported unmodified),
never a re-implementation of the matching logic -- a fix landing anywhere
behind the seam turns these green with no test edits, as long as the
OBSERVABLE behavior matches.

Manager ruling U-R1 ("captured" means captured CLEANLY): a positive test
that only checks `len(created_definitions) > 0` would pass against a naive
"just delete the `used_body_derived_heading` gate" fix. The planner's own
live measurement (pass 1) proved that naive fix produces real defects on
these exact rows -- see each defect test's docstring below for the specific
mechanism, and the fixtures README / sprint log for full detail and
corpus-wide rates.

`DEGENERATE_THRESHOLD = 10` chars: the corpus-wide near-empty rate for
VA+WA+FED inline-fallback candidates is 8/36,694 (0.022%), all <= 9 chars;
the shortest GENUINE definition observed on these fixture rows is 22 chars
("Omission", WA T9A) -- 10 sits strictly between the two.
"""

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
    / "us_markers_wave1_rows.json"
)

DEGENERATE_THRESHOLD = 10  # chars; see module docstring for justification


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _ingest_and_link(
    db_session, matter, *, jurisdiction: str, title: str, row: dict
) -> list[Definition]:
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


def test_all_six_wave1_fixture_headings_are_recognized_as_definitions_sections():
    """Sanity: the miss is purely in extraction, not heading detection."""
    rows = _load_rows()
    for act_id, row in rows.items():
        assert is_definitions_heading(row["section_title"]) is True, (
            f"{act_id}: {row['section_title']!r} must already be recognized as a "
            "Definitions heading -- this sub-case is purely an extraction miss"
        )


def test_real_pipeline_recovers_all_nine_va_no_marker_definitions_end_to_end(
    db_session, matter_with_users
):
    """`STATE_VA_T23.1_SI_C3_S23.1-300` -- the recon dossier's own named VA
    example row. 9 real terms, each 44-658 chars (planner's live
    confirmation); today's pipeline creates 0 definitions here."""
    rows = _load_rows()
    row = rows["STATE_VA_T23.1_SI_C3_S23.1-300"]
    assert row["section_title"] == "Definitions"

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-VA", title="VA wave1 clean", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {
        "College degree",
        "Cost of education",
        "Educational and general fees",
        "Educational and general services",
        "student enrollment",
        "Fiscal year",
        "Peer institutions",
        "STEM",
        "Student",
    }, f"expected all 9 real VA terms, got {sorted(terms)!r}"

    for d in definitions:
        assert len(d.definition_text) >= DEGENERATE_THRESHOLD, (
            f"{d.terms!r} definition_text is only {len(d.definition_text)} chars: {d.definition_text!r}"
        )


def test_real_pipeline_recovers_both_wa_no_marker_definitions_end_to_end(
    db_session, matter_with_users
):
    """`STATE_WA_T47_C14_S020` (`RCW 47.14.020: Definitions.`) -- the exact
    row the recon dossier quotes for WA's dominant miss shape."""
    rows = _load_rows()
    row = rows["STATE_WA_T47_C14_S020"]
    assert row["section_title"] == "RCW 47.14.020: Definitions."

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-WA", title="WA wave1 clean", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {"Right-of-way", "Airspace"}, f"got {sorted(terms)!r}"


def test_real_pipeline_recovers_fed_no_marker_definitions_without_leaking_editorial_notes(
    db_session, matter_with_users
):
    """`USC_T16_C65_S4503d` -- small, real, 3-term FED section. Naively
    firing the unmodified fallback (confirmed live) swallows the row's
    appended "Editorial Notes"/"References in Text" tail into the LAST
    entry ("State", naive definition_text 626 chars, contains the literal
    string "Editorial Notes"). Not a clean capture -- the fix must stop at
    the operative-text boundary, not merely flip the gate."""
    rows = _load_rows()
    row = rows["USC_T16_C65_S4503d"]
    assert row["section_title"] == "Definitions"

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-FED", title="FED wave1 clean", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"Institutes of Tropical Forestry", "Secretary", "State"}, (
        f"got {sorted(by_term)!r}"
    )
    for term, d in by_term.items():
        for forbidden in ("Editorial Notes", "References in Text"):
            assert forbidden not in d.definition_text, (
                f"{term!r}'s definition_text illegally contains {forbidden!r} "
                f"({len(d.definition_text)} chars total): {d.definition_text!r}"
            )


def test_real_pipeline_never_produces_a_degenerate_near_empty_definition_on_the_va_defect_row(
    db_session, matter_with_users
):
    """`STATE_VA_T4.1_SII_C6_S4.1-600` -- real VA cannabis-law Definitions
    section, 48 genuine terms (32-1,108 chars each) plus one false-positive
    trap: "sell" (inside `"Sale" and "sell" includes ... by any means.`) is
    followed, well outside its own clause, by the literal word "means" --
    the naive fallback (confirmed live) collapses "sell"'s captured
    definition_text to a single "." character. Whatever the fix recovers
    from this row, it must never emit a definition that short."""
    rows = _load_rows()
    row = rows["STATE_VA_T4.1_SII_C6_S4.1-600"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-VA", title="VA wave1 defect", row=row
    )
    assert definitions, "this row has 48 real defined terms -- must not stay empty"

    degenerate = [
        (d.terms, d.definition_text)
        for d in definitions
        if len(d.definition_text) < DEGENERATE_THRESHOLD
    ]
    assert degenerate == [], (
        f"found degenerate (< {DEGENERATE_THRESHOLD}-char) definition(s), proving the "
        f"false-idiom-match collapse survived uncorrected: {degenerate!r}"
    )

    marijuana = next((d for d in definitions if "Marijuana" in d.terms), None)
    assert marijuana is not None, '"Marijuana" is a real, unambiguous term on this row'
    assert 500 < len(marijuana.definition_text) < 2000, (
        f'"Marijuana"\'s definition is {len(marijuana.definition_text)} chars -- expected a '
        "genuine single-paragraph definition, not truncated or swallowing a neighbour"
    )


def test_real_pipeline_never_produces_a_phantom_nested_term_on_the_wa_defect_row(
    db_session, matter_with_users
):
    """`STATE_WA_T9A_C04_S110` -- real WA criminal-code Definitions section.
    "Vehicle"'s own real definition contains a nested quoted phrase
    (`a "motor vehicle" as defined in ...`); the naive fallback (confirmed
    live) treats "motor vehicle" as a second, phantom top-level term (no
    defining sentence of its own in this statute), truncating "Vehicle"
    itself to a single "a" character. A clean capture must do neither."""
    rows = _load_rows()
    row = rows["STATE_WA_T9A_C04_S110"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-WA", title="WA wave1 defect", row=row
    )
    all_terms = {t for d in definitions for t in d.terms}

    assert "motor vehicle" not in all_terms, (
        '"motor vehicle" is a phrase INSIDE "Vehicle"\'s own definition on this real WA '
        "row, not a separately defined term -- it must not surface as its own "
        f"top-level Definition. Full term set: {sorted(all_terms)!r}"
    )

    vehicle = next((d for d in definitions if "Vehicle" in d.terms), None)
    assert vehicle is not None, '"Vehicle" (entry 29) is a real defined term on this row'
    assert 50 < len(vehicle.definition_text) < 400, (
        f'"Vehicle"\'s definition is {len(vehicle.definition_text)} chars -- expected the '
        "genuine single-sentence definition (~145 chars), not the 1-char collapse"
    )


def test_real_pipeline_never_swallows_editorial_notes_into_a_fed_definition(
    db_session, matter_with_users
):
    """`USC_T15_C12_S431` -- small (3,239-char) real FED section. Only
    entry (a) ("agricultural products") uses the recognized "means" idiom;
    entries (b)-(f) use idioms the fallback doesn't recognize as a
    boundary -- so the naive fallback (confirmed live) swallows ALL of
    (b)-(f) plus the row's appended "Editorial Notes"/"References in Text"
    tail into "agricultural products"'s definition_text (3,169/3,239
    chars). 83.0% of FED's zero-candidate Definitions sections carry this
    same appended-notes shape (planner pass 1, full-corpus) -- FED's
    dominant boundary hazard, distinct from the CA "swallow to end of
    section" precedent."""
    rows = _load_rows()
    row = rows["USC_T15_C12_S431"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-FED", title="FED wave1 defect", row=row
    )
    ag_products = next((d for d in definitions if "agricultural products" in d.terms), None)
    assert ag_products is not None, (
        '"agricultural products" is the one real term the fallback idiom recognizes'
    )

    text = ag_products.definition_text
    for forbidden in ("Editorial Notes", "References in Text", "board of trade"):
        assert forbidden not in text, (
            f'"agricultural products"\'s definition_text illegally contains {forbidden!r} -- '
            f"it swallowed forward past its own sentence boundary ({len(text)} chars total)"
        )
    assert len(text) < 500, (
        f'"agricultural products"\'s real definition is one sentence (~390 chars); got '
        f"{len(text)} chars, so it swallowed at least part of the next entry or the notes tail"
    )
