"""RED tests for gate P5 "Nothing regresses: English-state behavior
untouched (PR rules must not fire on English text)" -- sprint
2026-08-04-defs-us-pr, manager ruling M-R4.

M-R4 is explicit: "PR rules must never fire on English text" needs a test
that would FAIL if the Spanish rules were made language-blind -- i.e. a REAL
English-state row fed through the PR rule path, proving no extra capture --
"existing English tests still pass" is NOT sufficient on its own. This file
feeds the real Delaware fixture (`STATE_DE_T5_C7_SVIII_S796`, one of the
program's working-baseline states: IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK)
through `PRProfile` directly.

This is a real, concrete risk, not a formality: the sprint's own heading
survey (`test_pr_profile_headings.py`) found that a NAIVE Spanish heading
check built on the generic substring `defin` (rather than the specific
Spanish stem `definici(ón|ones)`) would ALSO match the English word
"Definitions" itself (it contains `defin` as a substring) -- exactly the
kind of accidental cross-language collision M-R4 exists to catch before it
ships, not after.

`app.definition_links.pr_profile` does not exist yet -- `ModuleNotFoundError`
is the expected RED signal for every test in this file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# RED: `pr_profile` does not exist yet.
from app.definition_links.pr_profile import PRProfile

DE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _load_de_fixture_rows() -> dict[str, dict]:
    rows = json.loads(DE_FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_profile():
    return PRProfile(code="US-PR")


@pytest.fixture()
def de_rows():
    return _load_de_fixture_rows()


def test_pr_profile_does_not_recognize_the_real_english_definitions_heading(pr_profile, de_rows):
    """The real DE `"§ Â\\r\\n 796. Definitions."` heading (scrape-noise
    included, unmodified) that `USProfile.is_definitions_heading` correctly
    recognizes MUST NOT be recognized by the Spanish-only `PRProfile` --
    "Definitions" contains the substring "defin" but is not the Spanish
    stem "definici(ón|ones)"."""
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    assert "Definitions" in row["section_title"]  # sanity: real English heading
    assert pr_profile.is_definitions_heading(row["section_title"]) is False


def test_pr_profile_does_not_recognize_the_singular_english_definition_heading(pr_profile, de_rows):
    row = de_rows["STATE_DE_T31_C52_SIII_S5227"]
    assert pr_profile.is_definitions_heading(row["section_title"]) is False


@pytest.mark.parametrize(
    "heading",
    ["Definitions", "Definitions.", "Definitions and Interpretation", "Section 101. Definitions."],
)
def test_pr_profile_does_not_recognize_clean_synthetic_english_headings(pr_profile, heading):
    assert pr_profile.is_definitions_heading(heading) is False


def test_pr_profile_extracts_nothing_from_the_real_english_definitions_body(pr_profile, de_rows):
    """Even if (hypothetically) told this real DE body IS a definitions
    section, the Spanish extractor must find zero candidates -- none of the
    English body's idioms (`"has the meaning specified in"`) match any
    Spanish defining idiom (`significa`/`tendrá el significado`/etc.)."""
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    candidates = pr_profile.extract_definitions_from_section(row["text"], scope="law-wide")
    assert candidates == []


def test_pr_profile_detects_no_cross_law_derivation_from_real_english_idiom_text(pr_profile):
    """The real fixture's English cross-law idiom ("has the meaning
    specified in 12 U.S.C. § 1813(c)") must not trigger PRProfile's Spanish
    idiom set (`según se define en`/`tiene el significado que se le asigna
    en`/etc.)."""
    entry_text = (
        '"Insured depository institution" has the meaning specified in 12 U.S.C. § 1813(c).'
    )
    edges = pr_profile.detect_cross_law_derivations(
        entry_text, source_term="Insured depository institution", known_law_titles={}
    )
    assert edges == []


def test_registering_us_pr_does_not_change_what_us_de_resolves_to():
    """Pending the core sprint's registry seam (M-R3): once `profiles.py`'s
    `_REGISTRY` maps `"US-PR"` to `PRProfile`, `get_profile("US-DE")` (and
    every other working-baseline US-* code) must still resolve to the
    ordinary `USProfile`, unaffected. Marked xfail (not a hard failure)
    until the registry wiring lands -- `profiles.py` is a shared module this
    sprint does not edit before core publishes its seam spec (see sprint
    contract Coordination clause and item plan)."""
    pytest.importorskip(
        "app.definition_links.pr_profile",
        reason="pr_profile module not implemented yet (expected pre-core RED)",
    )
    from app.definition_links.profiles import get_profile
    from app.definition_links.pr_profile import PRProfile
    from app.definition_links.us_profile import USProfile

    us_de_profile = get_profile("US-DE")
    assert isinstance(us_de_profile, USProfile)
    assert not isinstance(us_de_profile, PRProfile)
