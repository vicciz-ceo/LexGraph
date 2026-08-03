"""RED tests for the jurisdiction-profile seam (sprint 2026-08-02-us-state-law,
director decision #1, gate G1).

`app.definition_links.profiles` does not exist yet -- RED via `ImportError`.

Design this test pins down (evidence: recon dossier §1/§7, this repo's
`backend/app/definition_links/*.py` as read directly by the Planner):

  - The seam is an ADDITIVE registry layer, NOT a rename/relocation of the
    existing bare module-level functions (`sections.is_definitions_heading`,
    `normalize.normalize_for_parsing`, `matcher.find_term_uses`,
    `derivation.detect_cross_law_derivations`). Those functions are
    imported DIRECTLY BY NAME in ~20 existing unit/integration test files
    (see the sprint contract's stale-pin sweep) -- renaming, removing, or
    changing their signatures would force editing every one of those
    tests, which ruling R2 forbids. `HebrewProfile` (the `"IL"` profile)
    must be a THIN WRAPPER that delegates to those exact, unchanged
    functions -- proven here by literal identity/behavioral comparison,
    not merely "similar output".
  - `get_profile(code: str) -> JurisdictionProfile` is the registry
    entrypoint. `pipeline.py` becomes the ONE call site that switches from
    calling `sections.is_definitions_heading(...)` etc. directly to calling
    `profile.is_definitions_heading(...)` -- that pipeline-level wiring is
    covered by the companion integration test in
    `test_definition_links_pipeline_profile_dispatch.py`, not here.
  - Minimum surface a `JurisdictionProfile` must expose (mirrors the
    director's own wording: "sections/matcher/derivation/normalize rules
    live" behind the profile):
      `.code: str`
      `.is_definitions_heading(heading: str) -> bool`
      `.normalize_for_parsing(text: str) -> str`
      `.find_term_uses(term: str, text: str) -> list[re.Match[str]]`
      `.detect_cross_law_derivations(text, *, source_term, known_law_titles=None) -> list`
    Every one of these keeps the SAME parameter names/order/defaults as
    the module-level function it wraps -- a drop-in replacement at the
    pipeline call site, not a redesigned API.
  - `guards.is_bidi_degraded` and `extract.py`'s functions are
    deliberately OUT of this profile surface for now: the director's
    decision names only "sections/matcher/derivation/normalize"; RTL-bidi
    guarding and definition-block extraction stay Hebrew-only / shared
    for this sprint (extension is a later concern, not this gate).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.definition_links import derivation, matcher, normalize, sections

# RED: this module does not exist yet.
from app.definition_links.profiles import get_profile

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"
REAL_HEBREW_LAW = FIXTURES_DIR / "חוק להגנת רכוש מופקד.wiki"


def _real_hebrew_articles():
    text = REAL_HEBREW_LAW.read_text(encoding="utf-8")
    return sections.parse_articles(text)


@pytest.fixture()
def il_profile():
    return get_profile("IL")


def test_get_profile_il_returns_a_profile_tagged_il(il_profile):
    assert il_profile.code == "IL"


def test_get_profile_rejects_an_unregistered_code():
    with pytest.raises((KeyError, ValueError)):
        get_profile("US")  # not registered yet -- this item only ports Hebrew


@pytest.mark.parametrize(
    "heading",
    [
        "הגדרות",
        "הגדרת מונחים",
        "הגדרה",
        "הגדרות ופירוש",
        "הגדרות (תיקון: תשכ\"ה)",
        "הודעה על טיפול בנכס",  # NOT a definitions heading -- must stay False
        "",
    ],
)
def test_il_profile_is_definitions_heading_matches_the_existing_sections_module(
    il_profile, heading
):
    assert il_profile.is_definitions_heading(heading) == sections.is_definitions_heading(heading)


def test_il_profile_is_definitions_heading_matches_every_real_fixture_heading(il_profile):
    """Regression-fidelity proof over REAL Hebrew fixture data (G1: "same
    definitions found ... on the same fixtures"), not just synthetic
    strings."""
    articles = _real_hebrew_articles()
    assert len(articles) > 0  # sanity: the fixture actually parsed
    for article in articles:
        assert il_profile.is_definitions_heading(article.heading) == sections.is_definitions_heading(
            article.heading
        )


def test_il_profile_normalize_for_parsing_matches_the_existing_normalize_module(il_profile):
    articles = _real_hebrew_articles()
    for article in articles:
        assert il_profile.normalize_for_parsing(article.body) == normalize.normalize_for_parsing(
            article.body
        )


def test_il_profile_find_term_uses_matches_the_existing_matcher_module(il_profile):
    """Hebrew's agglutinative prefix-letter surface-form matching (the
    hardest-to-port coupling per the recon dossier §1) must behave
    IDENTICALLY through the profile -- proven against a real defined term
    from the fixture law ("נכס")."""
    articles = _real_hebrew_articles()
    term = "נכס"
    for article in articles:
        profile_matches = il_profile.find_term_uses(term, article.body)
        direct_matches = matcher.find_term_uses(term, article.body)
        assert [(m.start(), m.end()) for m in profile_matches] == [
            (m.start(), m.end()) for m in direct_matches
        ]


def test_il_profile_detect_cross_law_derivations_matches_the_existing_derivation_module(
    il_profile,
):
    """Real trigger phrase + law reference from the fixture: term
    "האפוטרופוס הכללי" is defined via `כמשמעותו [[חוק האפוטרופוס
    הכללי|בפקודת האפוטרופוס הכללי, 1944]]`."""
    text = 'כמשמעותו בפקודת האפוטרופוס הכללי, 1944'
    profile_edges = il_profile.detect_cross_law_derivations(
        text, source_term="האפוטרופוס הכללי", known_law_titles={}
    )
    direct_edges = derivation.detect_cross_law_derivations(
        text, source_term="האפוטרופוס הכללי", known_law_titles={}
    )
    assert profile_edges == direct_edges
    assert len(profile_edges) >= 1  # sanity: the trigger phrase actually matched
