"""Combined release-blocker REDs: NE/SD body recognition + unquoted
extraction, and the FED partial-union/boundary case.

All rows are existing byte-vendored statutory fixtures.  The NE/SD gates are
deliberately split into recognition, scope, extraction, and persisted-live
assertions: adding only a BodyPreambleRule, only an EntrySplitterRule, or only
a scope rule cannot turn this file green.  The FED precondition records the
two currently competing real sources; its live gate requires the clean,
persisted three-term result rather than merely an added ``eligible`` key.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.definition_links.us_profile import _extract_inline_quoted_definitions
from app.models.definition import Definition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_NE_C43_TERMS = {
    "Account",
    "Authorized attorney",
    "Child support",
    "Department",
    "Financial institution",
    "Match",
    "Medical support",
    "Obligor",
    "Payor",
    "Spousal support",
    "Support",
    "Support order",
}
_NE_C44_TERMS = {"Health insurance plan", "Hearing aid", "Hearing impairment", "Insured child"}
_FED_TERMS = {"eligible", "good Samaritan search-and-recovery mission", "Secretary"}


def _rows() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for filename in (
        "us_preamble_rows.json",
        "ne_preamble_rows.json",
        "sd_preamble_rows.json",
        "cycle7_pr7_shapes_rows.json",
    ):
        source = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
        entries = source.values() if isinstance(source, dict) else source
        result.update({row["act_id"]: row for row in entries})
    return result


def _live_definitions(db_session, matter_with_users, *, row: dict, jurisdiction: str) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"combined correction live probe {row['act_id']}",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    return [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]


@pytest.mark.parametrize(
    ("act_id", "jurisdiction"),
    [
        ("STATE_NE_C43_S43-3329", "US-NE"),
        ("STATE_NE_C44_S44-5003", "US-NE"),
        ("STATE_SD_T54_C14_S54-14-12.1", "US-SD"),
    ],
)
def test_ne_sd_raw_body_preamble_recognition_is_independently_required(act_id, jurisdiction):
    """A splitter-only change must not pass: the actual profile dispatcher
    has to derive a Definitions heading from each real body.
    """
    row = _rows()[act_id]
    profile = get_profile(jurisdiction)
    body = profile.normalize_for_parsing(row["text"])
    assert profile.derive_heading_from_body(row["section_title"], body) == "Definitions"


def test_sd_for_the_purposes_of_this_chapter_is_chapter_scoped_before_extraction():
    """Recognition alone must not leave SD's real chapter-local meaning
    law-wide.  The established generic spelling lacks the article ``the``;
    this is an exact US-SD scope-rule requirement, not authorization to widen
    every jurisdiction's baseline predicate.
    """
    row = _rows()["STATE_SD_T54_C14_S54-14-12.1"]
    profile = get_profile("US-SD")
    assert profile.determine_scope(profile.normalize_for_parsing(row["text"])) == "chapter"


@pytest.mark.parametrize(
    ("act_id", "jurisdiction", "scope", "expected_terms"),
    [
        ("STATE_NE_C43_S43-3329", "US-NE", "law-wide", _NE_C43_TERMS),
        ("STATE_NE_C44_S44-5003", "US-NE", "law-wide", _NE_C44_TERMS),
        ("STATE_SD_T54_C14_S54-14-12.1", "US-SD", "chapter", {"loan processor or underwriter"}),
    ],
)
def test_ne_sd_raw_unquoted_extraction_is_independently_required(
    act_id, jurisdiction, scope, expected_terms
):
    """A recognizer-only change must not pass.  This drives the profile's
    real registered extraction union directly and proves the exact unquoted
    term population required from the future jurisdiction-scoped rule.
    """
    row = _rows()[act_id]
    profile = get_profile(jurisdiction)
    candidates = profile.extract_definitions_from_section(
        profile.normalize_for_parsing(row["text"]), scope=scope, heading_was_derived=True
    )
    assert {term for candidate in candidates for term in candidate.terms} == expected_terms


@pytest.mark.parametrize(
    ("act_id", "jurisdiction", "expected_terms", "expected_scope"),
    [
        ("STATE_NE_C43_S43-3329", "US-NE", _NE_C43_TERMS, "law-wide"),
        ("STATE_NE_C44_S44-5003", "US-NE", _NE_C44_TERMS, "law-wide"),
        ("STATE_SD_T54_C14_S54-14-12.1", "US-SD", {"loan processor or underwriter"}, "chapter"),
    ],
)
def test_ne_sd_live_persisted_rows_are_complete_clean_and_correctly_scoped(
    db_session, matter_with_users, act_id, jurisdiction, expected_terms, expected_scope
):
    """Load-bearing live gate: actual ingest -> profile dispatch ->
    persistence must retain every real term, a narrow scope, and boundaries
    that do not absorb the next statutory entry or trailing source note.
    """
    definitions = _live_definitions(
        db_session, matter_with_users, row=_rows()[act_id], jurisdiction=jurisdiction
    )
    by_term = {term: definition for definition in definitions for term in definition.terms}
    assert set(by_term) == expected_terms
    assert {definition.scope for definition in definitions} == {expected_scope}

    if act_id == "STATE_NE_C43_S43-3329":
        account = by_term["Account"].definition_text
        assert account.startswith("means a demand deposit account")
        assert account.endswith("money-market mutual fund account;")
        assert "Authorized attorney" not in account
    elif act_id == "STATE_NE_C44_S44-5003":
        plan = by_term["Health insurance plan"].definition_text
        assert plan.startswith("means a plan which includes dependent coverage")
        assert plan.endswith("other limited-benefit coverage;")
        assert "Hearing aid means" not in plan
        insured_child = by_term["Insured child"].definition_text
        assert insured_child.endswith("less than nineteen years of age.")
        assert "Laws 2019" not in insured_child
    else:
        loan_processor = by_term["loan processor or underwriter"].definition_text
        assert loan_processor.startswith("means any individual who performs clerical or support duties")
        assert loan_processor.endswith("person exempt according to this chapter.")
        assert "No individual engaging solely" not in loan_processor


def test_fed_partial_union_precondition_has_a_distinct_inline_candidate():
    """Current root cause, held green across the future repair: the real
    derived section has nonempty registered output without ``eligible``, while
    the existing inline fallback independently emits it.  A global fallback
    union is neither implied nor permitted by this evidence.
    """
    row = _rows()["USC_T43_C35_S1742a"]
    profile = get_profile("US-FED")
    body = profile.normalize_for_parsing(row["text"])
    assert profile.derive_heading_from_body(row["section_title"], body) == "Definitions"
    registered_terms = {
        term
        for candidate in profile.extract_definitions_from_section(
            body, scope="law-wide", heading_was_derived=True
        )
        for term in candidate.terms
    }
    inline_terms = {
        term for candidate in _extract_inline_quoted_definitions(body, scope="law-wide") for term in candidate.terms
    }
    assert registered_terms == {"good Samaritan search-and-recovery mission", "Secretary"}
    assert _FED_TERMS <= inline_terms


def test_fed_live_partial_union_preserves_exact_clean_three_term_result(db_session, matter_with_users):
    """The profile union must add only the missing valid key, preserve
    first-key registered candidates, and coexist with the US-FED structural
    splitter that keeps Secretary inside subsection (a).  This rejects an
    ``eligible``-only patch and an unsafe duplicate/long-tail fallback.
    """
    definitions = _live_definitions(
        db_session,
        matter_with_users,
        row=_rows()["USC_T43_C35_S1742a"],
        jurisdiction="US-FED",
    )
    by_term = {term: definition for definition in definitions for term in definition.terms}
    assert set(by_term) == _FED_TERMS
    assert {definition.scope for definition in definitions} == {"law-wide"}

    assert by_term["eligible"].definition_text.startswith(
        "that the organization or individual, respectively, is—"
    )
    assert by_term["eligible"].definition_text.endswith("where the mission takes place.")
    assert by_term["good Samaritan search-and-recovery mission"].definition_text == (
        "a search conducted by an eligible organization or individual for 1 or more missing "
        "individuals believed to be deceased at the time that the search is initiated."
    )
    assert by_term["Secretary"].definition_text == (
        "the Secretary or the Secretary of Agriculture, as applicable."
    )
    assert "(b) Process" not in by_term["Secretary"].definition_text
