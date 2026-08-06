"""G8 live dispatch RED for the US body-preamble B1/local-scope collision.

An ordinary ``As used in this section`` body is both a valid B1-derived
``Definitions`` heading and a valid local-scope definition.  Before this
repair, the former wins the mutually-exclusive Stage-2 branch: the
definitions-section extractor persists the last inline candidate as
``law-wide`` and includes its trailing notes.  The ordinary local extractor
would instead produce the clean, article-local candidate.

The test intentionally uses a small constructed row for the exact dispatch
shape; it is not represented as corpus evidence.  The paired chapter control
uses the byte-exact real GA B1 row, so neither suppressing B1 nor globally
relabeling scopes can make this gate green.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.definition_links.rules.us_body_preamble import _b1_trigger_colon_or_quote_means
from app.models.assertion import Assertion
from app.models.definition import Definition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_LOCAL_ACT_ID = "TESTONLY_G8_B1_LOCAL_SCOPE_DISPATCH"
_LOCAL_TERM = "Scope probe"
_CLEAN_LOCAL_TEXT = "a small mechanical device with a handle"
_TRAILING_NOTES = "Editorial Notes\nThis is trailing statutory-note text, not the definition."
_LOCAL_ROW = {
    "act_id": _LOCAL_ACT_ID,
    "section_number": "G8-LOCAL-1",
    "section_title": "Ordinary provision",
    "chapter": "G8",
    "text": (
        'As used in this section, "Scope probe" means a small mechanical device with a handle.\n'
        f"{_TRAILING_NOTES}"
    ),
}
_OUTSIDE_LOCAL_SCOPE_ROW = {
    "act_id": "TESTONLY_G8_B1_LOCAL_SCOPE_OUTSIDE_USE",
    "section_number": "G8-LOCAL-OUTSIDE",
    "section_title": "Ordinary outside provision",
    "chapter": "G8",
    "text": "This separate article uses Scope probe in a context outside the defining section.",
}
_LOCAL_SUBSET_ROW = {
    "act_id": "TESTONLY_G8_B1_LOCAL_SCOPE_SECTION_SUBSET",
    "section_number": "G8-LOCAL-SUBSET",
    "section_title": "Ordinary provision with additional section entry",
    "chapter": "G8",
    "text": (
        'As used in this section, "Scope probe" means a small mechanical device with a handle.\n'
        '(1) "Section companion" means an additional definition that B1 section extraction must retain.'
    ),
}

_GA_ACT_ID = "STATE_GA_T7_C8_S7-8-1"
_GA_ROW_TEXT_SHA256 = "fdafdae02f2457bf2f5bd673663e33b77576c40e1641bb29de3ab27e84c94b70"


def _real_ga_chapter_row() -> dict:
    rows = json.loads((FIXTURES / "ga_preamble_rows.json").read_text(encoding="utf-8"))
    row = next(row for row in rows if row["act_id"] == _GA_ACT_ID)
    assert hashlib.sha256(row["text"].encode()).hexdigest() == _GA_ROW_TEXT_SHA256
    return row


def _run_rows(db_session, matter_with_users, *, rows: list[dict], jurisdiction: str, title: str):
    matter = matter_with_users
    ingest_result = ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=title,
        rows=rows,
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter["matter_id"],
        triggered_by_user_id=matter["contributor_id"],
    )
    return ingest_result, result, [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]


def test_b1_derived_local_definition_persists_clean_and_local_through_live_ingest_linking(
    db_session, matter_with_users
):
    """Load-bearing RED: B1 recognition must remain live but cannot select
    the trailing law-wide definitions-section candidate over the ordinary
    local extractor's clean candidate.
    """
    profile = get_profile("US-GA")
    assert _b1_trigger_colon_or_quote_means(_LOCAL_ROW["text"]) == "Definitions"
    assert profile.derive_heading_from_body(_LOCAL_ROW["section_title"], _LOCAL_ROW["text"]) == "Definitions"
    assert profile.determine_scope(_LOCAL_ROW["text"]) == "law-wide"
    section_candidates = profile.extract_definitions_from_section(
        _LOCAL_ROW["text"], scope="law-wide", heading_was_derived=True
    )
    local_candidates = profile.extract_local_scope_definitions(
        _LOCAL_ROW["text"], article_number=_LOCAL_ROW["section_number"], chapter=_LOCAL_ROW["chapter"]
    )
    assert [(candidate.scope, candidate.definition_text) for candidate in section_candidates] == [
        ("law-wide", f"{_CLEAN_LOCAL_TEXT}.\n{_TRAILING_NOTES}")
    ]
    assert [(candidate.scope, candidate.definition_text) for candidate in local_candidates] == [
        ("local", _CLEAN_LOCAL_TEXT)
    ]

    ingest_result, result, definitions = _run_rows(
        db_session,
        matter_with_users,
        rows=[_LOCAL_ROW, _OUTSIDE_LOCAL_SCOPE_ROW],
        jurisdiction="US-GA",
        title="G8 B1 local-scope dispatch live probe",
    )
    matches = [definition for definition in definitions if definition.terms == [_LOCAL_TERM]]

    assert len(matches) == 1, f"expected one persisted {_LOCAL_TERM!r}, got {definitions!r}"
    persisted = matches[0]
    assert persisted.scope == "local", f"B1-derived local definition broadened to {persisted.scope!r}"
    assert persisted.definition_text == _CLEAN_LOCAL_TEXT, (
        "B1-derived definitions-section dispatch retained trailing text instead of the ordinary "
        f"local candidate: {persisted.definition_text!r}"
    )
    assert _TRAILING_NOTES not in persisted.definition_text
    outside_article_id = ingest_result["article_ids"][1]
    outside_edges = [
        db_session.get(Assertion, item["id"])
        for item in result["created_assertions"]
        if item["assertion_type"] == "USES_DEFINITION"
    ]
    assert not any(edge.subject_entity_id == outside_article_id for edge in outside_edges), (
        "a later law-wide same-key candidate linked an outside article to the Definition that was "
        "persisted as local; Stage 3 must use the persisted/narrow winner for same-key candidates"
    )


def test_b1_local_candidate_precedes_but_does_not_suppress_distinct_section_candidate(
    db_session, matter_with_users
):
    """Option-B control: the local rule has only ``Scope probe``; the B1
    section path also has ``Section companion``. Candidate union must retain
    both, so redirecting to local-only extraction cannot pass.
    """
    profile = get_profile("US-GA")
    assert _b1_trigger_colon_or_quote_means(_LOCAL_SUBSET_ROW["text"]) == "Definitions"
    assert profile.derive_heading_from_body(
        _LOCAL_SUBSET_ROW["section_title"], _LOCAL_SUBSET_ROW["text"]
    ) == "Definitions"
    assert [candidate.terms for candidate in profile.extract_local_scope_definitions(
        _LOCAL_SUBSET_ROW["text"],
        article_number=_LOCAL_SUBSET_ROW["section_number"],
        chapter=_LOCAL_SUBSET_ROW["chapter"],
    )] == [(_LOCAL_TERM,)]
    assert [candidate.terms for candidate in profile.extract_definitions_from_section(
        _LOCAL_SUBSET_ROW["text"], scope="law-wide", heading_was_derived=True
    )] == [("Section companion",)]

    _, _, definitions = _run_rows(
        db_session,
        matter_with_users,
        rows=[_LOCAL_SUBSET_ROW],
        jurisdiction="US-GA",
        title="G8 B1 local-plus-section candidate-union control",
    )
    by_term = {term: definition for definition in definitions for term in definition.terms}
    assert set(by_term) == {_LOCAL_TERM, "Section companion"}
    assert by_term[_LOCAL_TERM].scope == "local"
    assert by_term["Section companion"].scope == "law-wide"


def test_real_b1_chapter_preamble_remains_chapter_scoped_not_globally_local(
    db_session, matter_with_users
):
    """Real paired control: suppressing B1 loses this row; changing every
    B1-derived scope to local breaks its genuine chapter scope.
    """
    row = _real_ga_chapter_row()
    profile = get_profile("US-GA")
    assert _b1_trigger_colon_or_quote_means(row["text"]) == "Definitions"
    assert profile.derive_heading_from_body(row["section_title"], row["text"]) == "Definitions"

    _, _, definitions = _run_rows(
        db_session,
        matter_with_users,
        rows=[row],
        jurisdiction="US-GA",
        title="G8 real GA chapter B1 control",
    )
    matches = [definition for definition in definitions if "Access area" in definition.terms]

    assert len(matches) == 1, f"real GA B1 chapter definition was not uniquely persisted: {definitions!r}"
    assert matches[0].scope == "chapter", f"real GA chapter B1 scope changed to {matches[0].scope!r}"
