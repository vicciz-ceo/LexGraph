"""QA bounce evidence — sprint 2026-08-02-us-state-law, QA cycle 3.

These tests are INTENTIONALLY RED. Each proves a real, new defect (found by
independently testing real state files the Developer never used) that
bounces its item back to `## Next Steps` in the sprint contract. Do not
"fix" them by loosening the assertion -- fix the implementation, then this
file goes green on its own.

Cycle 2's three bounce-proofs (Q2 empty-chapter drop, Q3a ReDoS, Q3b
letter-in-section-number under-match) all now PASS against the wave-4
fixes and have been folded into `test_qa_regression_us_state_law.py`.
This file holds ONLY cycle 3's fresh findings, all reproduced from REAL
rows in `backend/tests/fixtures/us_statutes/qa_cycle3_rows.json` (full
provenance/derivation in that fixture directory's README.md), pulled from
6 real state files (IL, TX, FL, OH, PA, CA) beyond the DE/NY pair the
Developer verified against.

[QA-FAIL] Item 3 -- US jurisdiction profile [G2], heading matcher still
badly broken on real data outside DE/NY, three distinct root causes:

  1. `test_is_definitions_heading_cannot_recognize_a_state_whose_section_title_carries_no_heading_text`
     (structural defect, no regex can fix it): for real Illinois rows (and
     verified separately for California/Georgia -- see fixture README),
     `section_title` is ALWAYS a generic `"Section N"` placeholder; the
     genuine "Sec. 15. Definitions." heading exists only inside the row's
     `text` body, which `is_definitions_heading` never sees. 100% miss,
     state-wide, for at least 3 of ~53 real jurisdictions.

  2. `test_is_definitions_heading_misses_all_caps_texas_definitions_headings`
     (case-sensitivity defect): Texas's real, standard heading convention
     is ALL CAPS (`"DEFINITION."`/`"DEFINITIONS."`). `is_definitions_heading`
     requires an exact-case `Definitions?` (capital D, lowercase rest) --
     0 of 5,033 real Texas Definitions headings match. 100% miss for the
     entire state.

  3. `test_is_definitions_heading_misses_lowercase_definitions_in_normal_sentence_case_headings`
     (same case-sensitivity defect, different real-data shape): Ohio's real
     headings routinely end in lowercase `"...load definitions"` (normal
     sentence case, not the DE/PA capital-D convention the fix was verified
     against) -- 747 of 970 (77%) of real OH "definition"-containing
     headings use this shape and can never match.

  4. `test_is_definitions_heading_misses_dotted_section_numbers_like_florida_and_ohio`
     (number-stripping defect): `_SECTION_NUMBER_TOKEN_RE` does not consume
     a dot-separated section number (`"941.34"`, Florida's and Ohio's real
     convention) past the first period, leaving a numeric fragment stuck in
     front of "Definition" and breaking both the first-word and last-word
     rules. 127 of 748 (17%) of real FL capital-D "Definition(s)" headings
     are under-matched this way.

[QA-FAIL] Item 5 -- US dataset ingester [G6], the wave-4 idempotency key
`(section_number, section_title, text)` is NOT collision-free on real data
beyond the one file (DE) it was checked against -- it silently merges
genuinely different sections whenever they share byte-identical
cross-title boilerplate text, which is common, not rare:

  5. `test_ingest_us_statute_rows_silently_merges_two_different_real_pennsylvania_sections`
     two REAL, different PA sections (`74 Pa.C.S. § 7` vs `51 Pa.C.S. § 7`)
     collide and merge into ONE Article. Verified: 9 collision groups / 11
     rows silently lost in the real 14,547-row PA file alone.

  6. `test_ingest_us_statute_rows_silently_merges_two_different_real_california_sections`
     same defect, worse on California (which ALSO has the item-3 "generic
     section_title" defect, compounding both bugs): 2 REAL sections
     (`Cal. WIC § 7` vs `Cal. INS § 7`) collide. Verified: 83 collision
     groups / 176 rows silently lost in the real 161,429-row CA file (the
     single largest file in the whole corpus) -- discovered independently
     by re-running the bulk CLI end-to-end and cross-checking the reported
     "rows ingested" count against the database's real Article count (they
     disagreed by 11 on a single real PA file, which is what led to this
     finding -- see the cycle-3 QA report for the full bulk-mode trace).
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "qa_cycle3_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


# --- Item 3, defect 1: section_title carries no heading text at all --------


def test_is_definitions_heading_cannot_recognize_a_state_whose_section_title_carries_no_heading_text():
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_rows()
    row = rows["STATE_IL_C325_A7_S15"]
    assert row["section_title"] == "Section 15", (
        "fixture must reproduce the real IL shape: section_title is a bare "
        "'Section N' placeholder, never a descriptive heading"
    )
    assert "Definitions" in row["text"], (
        "the real body DOES contain a genuine 'Sec. 15. Definitions.' heading -- "
        "it just isn't in section_title, which is all is_definitions_heading sees"
    )
    assert is_definitions_heading(row["section_title"]) is True, (
        f"is_definitions_heading({row['section_title']!r}) returned False -- this "
        "real Illinois row IS a genuine Definitions section, but section_title "
        "carries no heading text at all (verified: 99.6% of all 72,456 real IL "
        "rows, and 100% of all 161,429 real CA rows, and 100% of all 28,154 real "
        "GA rows, share this exact shape). No regex fix to is_definitions_heading "
        "can recover this on its own -- the input field it is called on "
        "(Article.heading, sourced from section_title in pipeline.py Stage 2) "
        "never carries the real heading text for these states"
    )


def test_real_pipeline_misses_a_real_illinois_definitions_section_end_to_end(
    db_session, matter_with_users
):
    """Live-path confirmation (not just the unit-level miss above): the real
    production pipeline creates ZERO definitions from a real, genuine
    Illinois Definitions row."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_rows()
    row = rows["STATE_IL_C325_A7_S15"]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Illinois Compiled Statutes (QA cycle3 probe)",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-IL",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(result["created_definitions"]) > 0, (
        "the real production pipeline recognized ZERO definitions in a real "
        "Illinois 'Sec. 15. Definitions.' section (5 real defined terms: "
        "'Bias-free', 'BIPOC', 'Child', 'Child welfare court personnel', "
        "'Department', ...) -- G2 fails completely for this real jurisdiction"
    )


# --- Item 3, defect 2: ALL-CAPS convention (Texas) never matches ------------


def test_is_definitions_heading_misses_all_caps_texas_definitions_headings():
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_rows()
    row = rows["STATE_TX_Ctn_C452_S452.351"]
    assert row["section_title"] == "§ 452.351. DEFINITION."

    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} is a real, genuine one-term Texas Definitions "
        "section ('bond' includes a note) using Texas's real, standard ALL-CAPS "
        "heading convention -- but is_definitions_heading's case-sensitive "
        "Definitions? check (capital D, lowercase rest) never matches ALL-CAPS "
        "'DEFINITION'/'DEFINITIONS'. Verified: 0 of 5,033 real Texas headings "
        "containing the word 'definition' match -- a complete, state-wide G2 miss"
    )


# --- Item 3, defect 3: lowercase mid-sentence convention (Ohio) -------------


def test_is_definitions_heading_misses_lowercase_definitions_in_normal_sentence_case_headings():
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_rows()
    row = rows["STATE_OH_T45_C4513_S4513.01"]
    assert row["section_title"] == "§ 4513.01. Traffic laws - equipment - load definitions"

    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} is a real Ohio section whose own operative "
        "subject is definitions (it cross-references another section's "
        "definitions), ending in lowercase 'definitions' -- Ohio's real normal "
        "sentence-case convention, not the DE/PA capital-D convention the fix "
        "was validated against. Verified: 747 of 970 (77%) of real Ohio "
        "'definition'-containing headings use this lowercase shape and can "
        "never match is_definitions_heading's case-sensitive check"
    )


# --- Item 3, defect 4: dotted section numbers (Florida, Ohio, ...) ----------


def test_is_definitions_heading_misses_dotted_section_numbers_like_florida_and_ohio():
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_rows()
    row = rows["STATE_FL_TXLVII_C941_PI_S941.34"]
    assert row["section_title"] == "941.34 Definition of “state.”"

    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} is a real, genuine one-term Florida "
        "Definitions section -- but Florida's (and Ohio's) real dot-separated "
        "section-number convention ('941.34') is not fully consumed by "
        "_SECTION_NUMBER_TOKEN_RE (which stops after the first '.', at '941.'), "
        "leaving the fragment '34' stuck in front of 'Definition' and breaking "
        "both the first-word and last-word match rules. Verified: 127 of 748 "
        "(17%) of real Florida capital-D 'Definition(s)' headings are "
        "under-matched this exact way"
    )


# --- Item 5, defect 5: real PA cross-title text collision -------------------


def test_ingest_us_statute_rows_silently_merges_two_different_real_pennsylvania_sections(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows

    m = matter_with_users
    rows = _load_rows()
    row_a = rows["STATE_PA_T74_C7_S7"]
    row_b = rows["STATE_PA_T51_C7_S7"]
    assert row_a["citation"] != row_b["citation"], "must be two genuinely different sections"
    assert row_a["text"] == row_b["text"], (
        "fixture must reproduce the real cross-title boilerplate collision: "
        "byte-identical body text across two different PA titles"
    )

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Pennsylvania Consolidated Statutes (QA cycle3 collision probe)",
        rows=[
            {k: v for k, v in row_a.items() if not k.startswith("_")},
            {k: v for k, v in row_b.items() if not k.startswith("_")},
        ],
        jurisdiction="US-PA",
    )

    assert len(result["skipped_rows"]) == 0, "neither row was reported skipped either"
    assert len(set(result["article_ids"])) == 2, (
        f"row_b ({row_b['citation']}) was silently merged into row_a's "
        f"({row_a['citation']}) Article because both real, genuinely DIFFERENT "
        "Pennsylvania sections share an identical (section_number, "
        "section_title, text) triple -- byte-identical cross-title boilerplate "
        "text, which the wave-4 fix's own docstring claimed 'essentially never' "
        "happens on real data. Verified: 9 such collision groups / 11 rows "
        "silently merged in the real 14,547-row us_pa_statutes.parquet file "
        "alone, a file the Developer never checked"
    )


# --- Item 5, defect 6: real CA cross-title text collision (worse: also -----
# --- has the item-3 generic-section_title defect) ---------------------------


def test_ingest_us_statute_rows_silently_merges_two_different_real_california_sections(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows

    m = matter_with_users
    rows = _load_rows()
    row_a = rows["STATE_CA_Cwic_S7"]
    row_b = rows["STATE_CA_Cins_S7"]
    assert row_a["citation"] != row_b["citation"], "must be two genuinely different sections"
    assert row_a["section_title"] == row_b["section_title"] == "Section 7"
    assert row_a["text"] == row_b["text"], (
        "fixture must reproduce the real cross-code boilerplate collision"
    )

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="California Codes (QA cycle3 collision probe)",
        rows=[
            {k: v for k, v in row_a.items() if not k.startswith("_")},
            {k: v for k, v in row_b.items() if not k.startswith("_")},
        ],
        jurisdiction="US-CA",
    )

    assert len(result["skipped_rows"]) == 0
    assert len(set(result["article_ids"])) == 2, (
        f"row_b ({row_b['citation']}) was silently merged into row_a's "
        f"({row_a['citation']}) Article. Verified: 83 collision groups / 176 "
        "rows silently merged in the real 161,429-row us_ca_statutes.parquet "
        "file (the single largest file in the whole ~2M-row corpus) -- found by "
        "re-running the bulk-ingest CLI end-to-end on a real file and "
        "cross-checking its reported 'rows ingested' count against the "
        "database's actual Article count (they disagreed)"
    )
