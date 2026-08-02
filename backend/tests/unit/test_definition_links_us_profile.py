"""RED tests for the US jurisdiction profile (sprint 2026-08-02-us-state-law,
director decision #1, gates G2 "a real US statute parses", G3 "English
term linking works", G4 "US citations are recognised").

`get_profile("US-DE")` (and any other `US-*`/`US-FED` code) does not exist
yet -- RED via the registry lookup failing (`ImportError` for
`app.definition_links.profiles` itself if the G1 seam item hasn't landed
either, or a `KeyError`/`ValueError` from `get_profile` if the seam exists
but no US profile is registered -- either is a legitimate RED signal for
"this feature does not exist yet").

Fixture data: REAL rows from `vaquill/open-us-law`'s `us_de_statutes.parquet`
(ruling R6), committed at `backend/tests/fixtures/us_statutes/de_sample_rows.json`
-- see that file's sibling `README.md` for full provenance and why each row
was picked. Loaded as JSON here specifically so this test needs no
`pyarrow`/`huggingface_hub` install.

Design calls this test pins for the US profile (evidence: the real fixture
rows themselves, read directly by the Planner):

  - `is_definitions_heading` must tolerate the REAL scrape-artifact noise
    present in EVERY Delaware `section_title` value (`"§ Â\r\n innerhalb
    796. Definitions."` -- mojibake `Â`, a raw CRLF, leading whitespace,
    all BEFORE the actual number+heading) -- a heading matcher that only
    handles a clean `"796. Definitions"`-shaped string will fail on 100%
    of this real dataset's rows. It must therefore match on a
    substring/contains basis (unlike Hebrew's `sections.py`, which
    anchors at the START of an already marker-stripped heading) rather
    than assume clean input.
  - `find_term_uses` uses ordinary `\\b`-word-boundary matching (no
    Hebrew-style prefix-letter surface-form expansion) and must NOT match
    a defined term as a substring of a longer word (e.g. `"Affiliate"`
    inside `"Affiliates"`/`"disaffiliate"`).
  - `detect_cross_law_derivations` recognizes English defining idioms
    (`"has the meaning specified in"`, `"as defined in"`, at minimum --
    real fixture text uses the former, not `"means"`) followed by a law
    reference, and EXCLUDES same-document/same-chapter internal
    references (`"...of this chapter"`) from being reported as cross-law,
    mirroring Hebrew derivation.py's `_BESAIF_RE` same-law exclusion
    philosophy -- never a fabricated resolution (M5's discipline, ported):
    an unresolved federal/statutory reference is still emitted, with
    `target_law_id=None`.
  - `find_citations` is a NEW capability with no Hebrew analog (G4's gate
    text names bare citations -- "§ 101", "15 U.S.C. § 1" -- as
    something that must be "detected ... rather than silently dropped"
    even with NO defining trigger phrase nearby): every profile exposes
    `.find_citations(text) -> list[str]` (matched citation substrings);
    the Hebrew (`"IL"`) profile trivially returns `[]` (no citation
    grammar in scope for Hebrew this sprint) -- covered as a companion
    assertion in `test_definition_links_profiles.py`'s existing
    `il_profile` fixture usage is NOT required to change for this reason;
    that file is untouched by this item.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# RED: no US profile is registered yet (ImportError if `profiles` itself
# doesn't exist -- G1 not yet landed -- or KeyError/ValueError if it does
# exist but "US-DE" isn't a registered code yet).
from app.definition_links.profiles import get_profile

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def us_profile():
    return get_profile("US-DE")


@pytest.fixture()
def de_rows():
    return _load_fixture_rows()


# --- G2: Definitions-heading detection --------------------------------------


def test_us_profile_recognizes_the_real_de_definitions_heading_despite_scrape_noise(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    assert "Definitions" in row["section_title"]  # sanity: fixture really has this word
    assert us_profile.is_definitions_heading(row["section_title"]) is True


def test_us_profile_recognizes_the_singular_definition_heading_variant(us_profile, de_rows):
    row = de_rows["STATE_DE_T31_C52_SIII_S5227"]
    assert us_profile.is_definitions_heading(row["section_title"]) is True


def test_us_profile_does_not_flag_an_ordinary_heading_as_a_definitions_section(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T29_C60A_S6060"]
    assert us_profile.is_definitions_heading(row["section_title"]) is False


@pytest.mark.parametrize(
    "heading",
    [
        "Definitions",
        "Definitions.",
        "Definitions and Interpretation",
        "§ 101. Definitions",
        "Section 101. Definitions.",
    ],
)
def test_us_profile_recognizes_clean_synthetic_definitions_headings(us_profile, heading):
    assert us_profile.is_definitions_heading(heading) is True


# --- G3: English word-boundary term matching --------------------------------


def test_us_profile_find_term_uses_matches_a_real_defined_term_in_real_body_text(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    matches = us_profile.find_term_uses("Affiliate", row["text"])
    assert len(matches) >= 1


def test_us_profile_find_term_uses_does_not_false_match_inside_a_longer_word(us_profile):
    text = 'The "Affiliate" definition applies. Affiliates and disaffiliated parties are different concepts.'
    matches = us_profile.find_term_uses("Affiliate", text)
    matched_spans = [(m.start(), m.end()) for m in matches]
    for start, end in matched_spans:
        # Every match must be the bare word "Affiliate", never a substring
        # of "Affiliates" or "disaffiliated".
        assert text[start:end] == "Affiliate"
        before = text[start - 1] if start > 0 else " "
        after = text[end] if end < len(text) else " "
        assert not before.isalpha()
        assert not after.isalpha()


def test_us_profile_find_term_uses_matches_a_multi_word_term(us_profile, de_rows):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    matches = us_profile.find_term_uses("Branch office", row["text"])
    assert len(matches) >= 1


# --- G4: US citation grammar -------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_substring",
    [
        ("as defined in Section 5, the term applies.", "Section 5"),
        ("The threshold set by § 101 controls.", "§ 101"),
        ("Compliance follows 15 U.S.C. § 1 in all cases.", "15 U.S.C. § 1"),
    ],
)
def test_us_profile_find_citations_detects_named_reference_forms(
    us_profile, text, expected_substring
):
    citations = us_profile.find_citations(text)
    assert any(expected_substring in c for c in citations)


def test_us_profile_find_citations_detects_the_real_fixtures_federal_citation(us_profile, de_rows):
    row = de_rows["STATE_DE_T29_C60A_S6060"]
    citations = us_profile.find_citations(row["text"])
    assert any("U.S.C." in c for c in citations)


def test_us_profile_detect_cross_law_derivations_resolves_a_federal_cross_reference(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    entry_text = (
        '"Insured depository institution" has the meaning specified in 12 U.S.C. § 1813(c).'
    )
    edges = us_profile.detect_cross_law_derivations(
        entry_text, source_term="Insured depository institution", known_law_titles={}
    )
    assert len(edges) >= 1
    assert any("1813" in edge.matched_text or "U.S.C." in edge.matched_text for edge in edges)
    # M5's discipline, ported: unresolved (no matching known_law_titles entry)
    # is still emitted, never dropped, target_law_id stays None.
    assert all(edge.target_law_id is None for edge in edges)


def test_us_profile_detect_cross_law_derivations_excludes_a_same_chapter_reference(
    us_profile, de_rows
):
    """"Branch office" ... "has the meaning specified in § 770 OF THIS
    CHAPTER" -- an internal, same-document reference must NOT be reported
    as a cross-law derivation (mirrors Hebrew derivation.py's `_BESAIF_RE`
    same-law exclusion)."""
    entry_text = '"Branch office" has the meaning specified in § 770 of this chapter.'
    edges = us_profile.detect_cross_law_derivations(
        entry_text, source_term="Branch office", known_law_titles={}
    )
    assert edges == []


# --- G2 (continued): extracting DEFINED TERMS out of a located US
# Definitions section. NOT one of the 4 modules the director's decision
# text named ("sections/matcher/derivation/normalize") -- but G2's plain-
# language gate ("extracts its terms") is unsatisfiable without it: the
# real fixture's Definitions body is a numbered-paragraph list
# (`"(1) \"Term\" has the meaning specified in ..."`), structurally
# nothing like Hebrew's `:-`-prefixed entry markers (`extract.py`'s
# `_ENTRY_START_RE`). The Planner extends the profile surface to
# `.extract_definitions_from_section(text) -> list[DefinitionCandidate]`
# by necessity -- flagged as a deviation from the director's literal
# 4-module list in the sprint contract, not a silent scope change.


def test_us_profile_extracts_every_defined_term_from_the_real_definitions_section(
    us_profile, de_rows
):
    from app.definition_links.extract import DefinitionCandidate

    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    candidates = us_profile.extract_definitions_from_section(row["text"], scope="law-wide")
    assert all(isinstance(c, DefinitionCandidate) for c in candidates)

    all_terms = {term for c in candidates for term in c.terms}
    assert "Affiliate" in all_terms
    assert "Branch office" in all_terms
    assert "Insured depository institution" in all_terms
    assert len(candidates) == 3
