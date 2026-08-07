"""QA RED: a B1-derived Hawaii body must not turn quoted policy clauses into terms.

This compact fixture preserves the exact quoted ``If any indemnity ...`` / ``; and``
shape from pinned ``STATE_HI_D2_T24_C431_S431``.  The real source row is a
2,404,155-character concatenation, so the test carries only the causal shape,
plus a genuine B1 definition that must survive the eventual extraction repair.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.models.definition import Definition


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "hi_contractual_quote_pfp_row.json"
PSEUDO_TERM = (
    "If any indemnity of this policy shall be payable to the estate of the insured, or to an insured "
    "or beneficiary who is a minor or otherwise not competent to give a valid release, the insurer may "
    "pay the indemnity, up to an amount not exceeding $2,000 to any relative by blood or connection by "
    "marriage of the insured or beneficiary who is deemed by the insurer to be equitably entitled thereto. "
    "Any payment made by the insurer in good faith pursuant to this provision shall fully discharge the "
    "insurer to the extent of the payment"
)


def _row() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _genuine_quoted_list_row(*, large: bool = False) -> dict:
    """A source-faithful B1 list control, including a real ``; and`` list.

    The Hawaii failure is not permission to suppress a jurisdiction, a long
    body, a quote, or a semicolon connector.  These are actual definition
    shapes: each quoted term is immediately followed by its defining verb;
    the second definition has a semicolon/list as part of its own substance.
    ``large`` simulates the concatenated-source-row size hazard without
    vendoring a multi-megabyte test fixture.
    """
    text = (
        "As used in this chapter, the term:\n"
        '(1) "genuine coverage" means coverage issued under this chapter.\n\n'
        '(2) "covered services" shall include: (A) hospital care; and (B) physician care.\n'
    )
    if large:
        text += "\n" + ("Operative insurance text that defines no quoted term. " * 20_000)
    return {
        "act_id": "TESTONLY_HI_GENUINE_QUOTED_LIST_LARGE" if large else "TESTONLY_HI_GENUINE_QUOTED_LIST",
        "section_number": "431:15-304-control",
        "section_title": ":15-304 Actions by and against rehabilitator.",
        "chapter": "431",
        "text": text,
    }


def _delimiter_free_genuine_b1_row() -> dict:
    """No validated source-section marker: legacy full-body extraction applies."""
    return {
        "act_id": "TESTONLY_B1_DELIMITER_FREE_GENUINE",
        "section_number": "test-delimiter-free",
        "section_title": "Placeholder",
        "chapter": "test",
        "text": (
            "As used in this chapter, the term:\n"
            '(1) "first genuine term" means the first genuine definition.\n\n'
            '(2) "second genuine term" means the second genuine definition.'
        ),
    }


def _raw_by_term(row: dict) -> dict[str, str]:
    profile = get_profile("US-HI")
    assert profile.derive_heading_from_body(row["section_title"], row["text"]) == "Definitions"
    raw = profile.extract_definitions_from_section(
        row["text"], scope="law-wide", heading_was_derived=True
    )
    return {term: candidate.definition_text for candidate in raw for term in candidate.terms}


def test_hi_contractual_quoted_policy_clause_is_not_a_raw_profile_definition():
    """The real US-HI profile/registry extraction must retain genuine coverage only."""
    row = _row()
    raw_by_term = _raw_by_term(row)
    assert raw_by_term["genuine coverage"] == "means coverage issued under this chapter."
    assert PSEUDO_TERM not in raw_by_term, (
        "P-FP: the Hawaii contractual clause is a quoted policy provision, not a definition term"
    )


def test_hi_body_derived_genuine_quoted_and_semicolon_list_definitions_remain_raw_profile_candidates():
    """A quote and ``; and`` inside a genuine B1 definition must survive."""
    raw_by_term = _raw_by_term(_genuine_quoted_list_row())

    assert raw_by_term["genuine coverage"] == "means coverage issued under this chapter."
    assert raw_by_term["covered services"] == "shall include: (A) hospital care; and (B) physician care."


def test_large_hawaii_body_with_genuine_quoted_definitions_is_not_suppressed():
    """The repair is not a Hawaii or large-body exclusion."""
    raw_by_term = _raw_by_term(_genuine_quoted_list_row(large=True))

    assert raw_by_term["genuine coverage"] == "means coverage issued under this chapter."
    assert raw_by_term["covered services"].startswith("shall include:")


def test_delimiter_free_b1_body_preserves_legacy_full_body_genuine_definitions():
    """No section enclosure must not activate the new bounded-span behavior."""
    raw_by_term = _raw_by_term(_delimiter_free_genuine_b1_row())

    assert raw_by_term == {
        "first genuine term": "means the first genuine definition.",
        "second genuine term": "means the second genuine definition.",
    }


def test_hi_contractual_quoted_policy_clause_is_not_persisted_as_a_definition_term(
    db_session, matter_with_users
):
    """The live US-HI ingest-to-persistence path must retain genuine coverage only."""
    row = _row()

    matter = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="US-HI contractual quoted-policy P-FP QA RED",
        rows=[row],
        jurisdiction="US-HI",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter["matter_id"],
        triggered_by_user_id=matter["contributor_id"],
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}

    assert by_term["genuine coverage"].definition_text == "means coverage issued under this chapter."
    assert PSEUDO_TERM not in by_term, (
        "P-FP: the Hawaii contractual clause is a quoted policy provision, not a term definition; "
        "live pipeline persisted the pseudo-definition"
    )


def test_hi_genuine_quoted_semicolon_list_definitions_remain_persisted(
    db_session, matter_with_users
):
    """The live ingest-to-persistence flow preserves both-sided controls."""
    row = _genuine_quoted_list_row()
    matter = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="US-HI genuine quoted-list preservation control",
        rows=[row],
        jurisdiction="US-HI",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter["matter_id"],
        triggered_by_user_id=matter["contributor_id"],
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}

    assert by_term["genuine coverage"].definition_text == "means coverage issued under this chapter."
    assert by_term["covered services"].definition_text == (
        "shall include: (A) hospital care; and (B) physician care."
    )
