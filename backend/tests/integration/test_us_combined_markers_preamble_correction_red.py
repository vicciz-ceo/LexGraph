"""Combined release-blocker REDs: NE/SD body recognition + unquoted
extraction, and the FED exact-splitter/boundary case.

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
from app.definition_links.us_profile import _extract_inline_quoted_definitions, _leading_quote_candidate
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
_NE_C43_ORDER = (
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
)
_NE_C44_ORDER = ("Health insurance plan", "Hearing aid", "Hearing impairment", "Insured child")


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


def _numbered_unquoted_source_oracle(row: dict, ordered_terms: tuple[str, ...]) -> dict[str, str]:
    """Independent, complete ground truth for a real numbered source body.

    This intentionally follows the row's literal, externally-vendored entry
    boundaries rather than the production splitters' grammar: every expected
    term begins at its fixed ``(N) term`` source marker and ends at the next
    fixed source marker (or the real ``Laws`` tail).  It therefore judges every
    persisted tuple without copying a proposed extraction regex into the test.
    """
    text = row["text"]
    expected: dict[str, str] = {}
    for index, term in enumerate(ordered_terms, start=1):
        start_token = f"({index}) {term} "
        start = text.find(start_token)
        assert start >= 0, f"fixture drift: missing source entry {start_token!r}"
        definition_start = start + len(start_token)
        if term == "Support":
            # C43's term is ``Support`` even though its source sentence reads
            # "Support in the definitions of ... means".  The intervening
            # qualifier establishes the defined-term context, not its
            # definition text; use the literal source verb boundary.
            definition_start = text.find("means", definition_start)
            assert definition_start > start, "fixture drift: missing C43 Support defining verb"
        if index < len(ordered_terms):
            end_token = f"\n\n({index + 1}) {ordered_terms[index]} "
        else:
            end_token = "\n\nLaws"
        end = text.find(end_token, definition_start)
        assert end > definition_start, f"fixture drift: missing source boundary {end_token!r}"
        expected[term] = text[definition_start:end].strip()
    return expected


def _sd_source_oracle(row: dict) -> dict[str, str]:
    term = "loan processor or underwriter"
    start_token = f"the term, {term}, "
    start = row["text"].find(start_token)
    assert start >= 0, f"fixture drift: missing source term {term!r}"
    definition_start = start + len(start_token)
    end = row["text"].find("\n\nNo individual engaging solely", definition_start)
    assert end > definition_start, "fixture drift: missing SD next-provision boundary"
    return {term: row["text"][definition_start:end].strip()}


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
    real registered extraction dispatch directly and proves the exact unquoted
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

    row = _rows()[act_id]
    expected_texts = (
        _numbered_unquoted_source_oracle(row, _NE_C43_ORDER)
        if act_id == "STATE_NE_C43_S43-3329"
        else _numbered_unquoted_source_oracle(row, _NE_C44_ORDER)
        if act_id == "STATE_NE_C44_S44-5003"
        else _sd_source_oracle(row)
    )
    assert {term: definition.definition_text for term, definition in by_term.items()} == expected_texts


def test_fed_existing_splitter_precondition_is_partial_before_exact_repair():
    """Current root cause, held green across the future repair: the real
    derived section has nonempty registered output without ``eligible``, while
    the existing inline fallback independently emits it.  A global fallback
    union is neither implied nor permitted by this evidence.
    """
    from app.definition_links.rules.us_markers_inline_quote import _split as existing_fed_split

    row = _rows()["USC_T43_C35_S1742a"]
    profile = get_profile("US-FED")
    body = profile.normalize_for_parsing(row["text"])
    assert profile.derive_heading_from_body(row["section_title"], body) == "Definitions"
    # Probe the existing ordinary splitter directly. Calling the public
    # profile method would become a stale pre-fix assertion once the new
    # priority exact splitter supplies ``eligible``. This preserves the
    # root-cause fact: the existing splitter's own emitted stream is partial.
    registered_terms = {
        term
        for block in existing_fed_split(body)
        for candidate in [_leading_quote_candidate(block, scope="law-wide")]
        if candidate is not None
        for term in candidate.terms
    }
    inline_terms = {
        term for candidate in _extract_inline_quoted_definitions(body, scope="law-wide") for term in candidate.terms
    }
    assert registered_terms == {"good Samaritan search-and-recovery mission", "Secretary"}
    assert _FED_TERMS <= inline_terms


def test_fed_live_exact_splitter_preserves_clean_three_term_result(db_session, matter_with_users):
    """One exact US-FED priority EntrySplitter must emit all three clean
    terms and stop Secretary inside subsection (a). This rejects an
    ``eligible``-only patch and any broad duplicate/long-tail parser.
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


def test_fed_exact_good_samaritan_rule_does_not_widen_to_trust_area_structural_shape(
    db_session, matter_with_users
):
    """Held-green mutation control for the accepted FED rule's exact guard.

    The same broad ``(N) Label`` + ``The term`` parser that repairs §1742a
    would replace this real registered ``substantially underserved trust
    area`` winner (1,852 chars) with a 172-char candidate.  That is a
    behavior change outside the three-term Good-Samaritan evidence, even if
    shorter text looks attractive.  The exact rule must leave this existing
    persisted tuple byte-for-byte untouched.
    """
    definitions = _live_definitions(
        db_session,
        matter_with_users,
        row=_rows()["USC_T7_C31_S936f"],
        jurisdiction="US-FED",
    )
    by_term = {term: definition for definition in definitions for term in definition.terms}
    assert {"eligible program", "substantially underserved trust area"} <= set(by_term)
    trust_area = by_term["substantially underserved trust area"]
    assert trust_area.scope == "law-wide"
    assert len(trust_area.definition_text) == 1852
    assert "(b) Initiative" in trust_area.definition_text
