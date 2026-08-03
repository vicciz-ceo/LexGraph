"""Mandatory false-positive guard tests for US family 2 (sprint
2026-08-04-defs-us-preamble, gate U5): "false positives are this family's
known hazard" (sprint contract, D3). A body that merely CONTAINS an "As
used in this X" / "For purposes of this X" / "shall have the meaning"
phrase, without actually introducing a locally-defined term, must NOT
produce a captured Definition -- e.g. a cross-reference to another
section's definition, or an operative/administrative sentence that happens
to share the trigger phrase's vocabulary.

These are GREEN today (nothing is captured for ANY US body under this
family yet -- see `test_us_body_preamble_capture_red.py`) and must STAY
GREEN once `us_body_preamble.py` exists; that persistence, not today's
pass, is what each test is actually pinning. Every row is REAL and
VERBATIM, picked by live corpus scan specifically because it contains the
family's trigger vocabulary WITHOUT defining anything
(`backend/tests/fixtures/us_statutes/{ga,md,ne,ms}_preamble_rows.json`,
second row in each file; SD's negative is its own third row).

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _rows(state: str) -> dict[str, dict]:
    data = json.loads((FIXTURES / f"{state}_preamble_rows.json").read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in data}


def _ingest_and_link(db_session, matter_with_users, *, state: str, act_id: str, title: str):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _rows(state)[act_id]
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        rows=[row],
        jurisdiction=f"US-{state.upper()}",
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


def test_ga_for_the_purposes_of_this_chapter_administrative_sentence_not_captured(
    db_session, matter_with_users
):
    """STATE_GA_T42_C10_S42-10-3: 'For the purposes of this chapter, the
    Board of Corrections shall constitute, ex officio, the Georgia
    Correctional Industries Administration.' -- names an entity, defines
    NO term. Must produce zero Definitions."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ga", act_id="STATE_GA_T42_C10_S42-10-3", title="GA T42 (test)"
    )
    assert result["created_definitions"] == []


def test_md_for_the_purposes_of_this_title_the_state_is_the_employer_not_captured(
    db_session, matter_with_users
):
    """STATE_MD_Agle_T9_S2_S9-213: '(b) For the purposes of this title, the
    State is the employer of an individual who is a covered employee under
    this section.' -- states a legal fact, defines NO term."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="md", act_id="STATE_MD_Agle_T9_S2_S9-213", title="MD T9-213 (test)"
    )
    assert result["created_definitions"] == []


def test_ne_shall_have_the_meaning_found_in_section_is_a_forwarding_reference_not_captured(
    db_session, matter_with_users
):
    """STATE_NE_C60_S60-643: "Operator's license shall have the meaning
    found in section 60-474." -- a pure forward pointer to ANOTHER
    section's definition, with no definition text of its own at all."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ne", act_id="STATE_NE_C60_S60-643", title="NE C60 (test)"
    )
    assert result["created_definitions"] == []


def test_ms_for_purposes_of_this_chapter_conditional_rule_not_captured(db_session, matter_with_users):
    """STATE_MS_T27_C41_S106-7: 'For purposes of this chapter, a person
    engages in investment activities in Iran if the person provides goods
    or services valued at Twenty Million Dollars...' -- an eligibility
    RULE (if/then), not a term definition; no quoted or capitalized defined
    term anywhere in the body."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ms", act_id="STATE_MS_T27_C41_S106-7", title="MS T27 (test)"
    )
    assert result["created_definitions"] == []


def test_sd_for_the_purposes_of_this_chapter_operative_duty_not_captured(db_session, matter_with_users):
    """STATE_SD_T32_C36_S32-36-5: 'For the purposes of this chapter, the
    Department of Revenue shall cooperate with any removal agency by
    providing the last known address...' -- imposes a duty, defines NO
    term."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="sd", act_id="STATE_SD_T32_C36_S32-36-5", title="SD T32 (test)"
    )
    assert result["created_definitions"] == []
