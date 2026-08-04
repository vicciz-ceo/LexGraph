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


# --- Sprint 2026-08-04-defs-core-scope (gates C1-C3, seam spec v1/v2) --
# --- 5 new/changed JurisdictionProfile methods -------------------------
#
# `il_profile` (the fixture above) already resolves via `get_profile`, so
# these are AttributeError RED today (the methods don't exist yet), not
# ImportError -- a distinct, still-legitimate "this feature does not
# exist yet" signal per this file's own header convention.


def test_il_profile_determine_scope_matches_todays_chapter_scope_triggers(il_profile):
    """v1 Seam 1: `determine_scope` replaces the free function
    `pipeline._determine_scope` -- same 2-way contract (`"chapter"` /
    `"law-wide"`), now reached through the profile instead of a bare
    module-level tuple. IL's own trigger phrases must be byte-identical
    (C5 -- Hebrew is a regression surface)."""
    assert il_profile.determine_scope("בפרק זה, הוראה זו חלה.") == "chapter"
    assert il_profile.determine_scope("הוראה רגילה שאינה מוגבלת.") == "law-wide"


def test_il_profile_extract_local_scope_definitions_matches_todays_extract_local_and_adhoc(
    il_profile,
):
    """v1 Seam 1: replaces pipeline.py's direct, unconditional calls to
    `extract.extract_local_definitions`/`extract_adhoc_definitions` (the
    C2/C3 violation -- those are Hebrew-only functions reachable
    regardless of jurisdiction). Through the IL profile, behavior must be
    IDENTICAL to calling both existing functions directly and combining
    their output."""
    from app.definition_links import extract

    body = 'לענין זה, "נכס משועבד" - נכס שהוטל עליו שעבוד. (להלן - "הנכס")'
    profile_candidates = il_profile.extract_local_scope_definitions(
        body, article_number="9"
    )
    direct = list(extract.extract_local_definitions(body)) + list(
        extract.extract_adhoc_definitions(body)
    )
    assert len(profile_candidates) == len(direct)
    assert {c.terms for c in profile_candidates} == {c.terms for c in direct}


def test_il_profile_resolve_unit_path_returns_the_articles_own_base_path(il_profile):
    """v2.2 -- replaces v2.1's `split_into_subsections` (withdrawn, folded
    into the unified `UnitPath` model). With no `char_offset`,
    `resolve_unit_path` returns the article's OWN base path (this
    sprint's own retrieval seam for C1's scope containment AND, per
    director ruling E-2/Option C, sub-article `USES_DEFINITION`
    anchoring -- ONE mechanism serves both, as required). Exact step
    content for chapter/siman is Stage B/dev work; the METHOD's shape
    (returns a tuple of `UnitStep`-like objects, each with `.kind`/
    `.value`) is what this test pins."""
    from app.definition_links.sections import Article as MatcherArticle

    article = MatcherArticle(number="12", heading="נושא", body="גוף הסעיף.", chapter="פרק ב")
    path = il_profile.resolve_unit_path(article)
    assert isinstance(path, tuple)
    for step in path:
        assert hasattr(step, "kind")
        assert hasattr(step, "value")


def test_il_profile_resolve_unit_path_extends_to_sub_article_granularity_given_a_char_offset(
    il_profile,
):
    """The retrieval-seam contract (director E-2/Option C): given a
    `char_offset` inside the article's body, `resolve_unit_path` returns
    a LONGER path than the bare article-level call above -- the sub-
    article extension C1/E-2 both depend on. Asserted through the
    method's own return shape, never through a storage column name/type
    (E-2's explicit "do not pin the storage shape" instruction)."""
    from app.definition_links.sections import Article as MatcherArticle

    body = "סעיף קטן (א) קובע דבר אחד. סעיף קטן (ב) קובע דבר אחר."
    article = MatcherArticle(number="12", heading="נושא", body=body, chapter=None)
    base_path = il_profile.resolve_unit_path(article)
    mention_offset = body.index("קטן (ב)")
    mention_path = il_profile.resolve_unit_path(article, char_offset=mention_offset)
    assert len(mention_path) > len(base_path)
    assert mention_path[: len(base_path)] == base_path


def test_il_profile_derive_heading_from_body_is_trivially_none(il_profile):
    """v1 Seam 1: IL has no placeholder-heading concept (that is a US CA/
    IL[state]/GA-only wave-6 shape) -- must always return `None`, never
    invent a heading from Hebrew body text."""
    assert il_profile.derive_heading_from_body("כותרת", "גוף הסעיף.") is None


def test_il_profile_extract_definitions_from_section_accepts_the_new_heading_was_derived_kwarg(
    il_profile,
):
    """v1 Seam 1: `extract_definitions_from_section` gains a defaulted
    `heading_was_derived` kwarg (US-only fallback-chain gate); IL's own
    behavior must be UNCHANGED whether or not the kwarg is passed
    explicitly."""
    from app.definition_links import extract

    body = ':- "נכס" - מקרקעין ומיטלטלין.'
    with_kwarg = il_profile.extract_definitions_from_section(
        body, scope="law-wide", heading_was_derived=False
    )
    without_kwarg = il_profile.extract_definitions_from_section(body, scope="law-wide")
    direct = extract.extract_definitions_from_section(body, scope="law-wide")
    assert with_kwarg == without_kwarg == direct


# --- Sprint 2026-08-04-defs-core-scope, seam v2.4 (research-dossier-  --
# --- validated: docs/sprint/programs/2026-08-04-law-system-units.md) ---


def test_resolve_unit_path_supports_genuinely_deep_nesting_not_hard_coded_to_two_or_three_levels():
    """Dossier finding: US federal citations run a real, at-scale 8-level
    parenthetical ladder ((a)>(1)>(A)>(i)>(I)>(aa)>(AA)), confirmed down
    to (AA) with 443 real instances. A `resolve_unit_path` implementation
    that quietly assumes shallow (2-3 level) nesting would pass every
    IL-shaped test above and silently fail here -- this test's body has
    FOUR levels of nesting on purpose, not one or two."""
    from app.definition_links.profiles import get_profile
    from app.definition_links.sections import Article as MatcherArticle

    us_profile = get_profile("US-FED")
    body = (
        "(a) General rule. (1) In general. (A) Application. (i) A deeply "
        "nested provision lives here, four levels below the section itself."
    )
    article = MatcherArticle(number="1395x", heading="Definitions", body=body)
    deep_offset = body.index("A deeply nested provision")
    path = us_profile.resolve_unit_path(article, char_offset=deep_offset)
    assert len(path) >= 4, (
        f"expected a path at least 4 levels deep for a genuinely "
        f"4-level-nested position; got {path!r} (length {len(path)}) -- "
        f"the mechanism must not hard-code a depth cap of 2 or 3."
    )


def test_resolve_unit_path_never_represents_a_sub_unit_without_its_rooting_article():
    """Dossier §2's convergent, cross-system finding: no law system (IL/
    US-states/US-federal/PR) ever cites a bare sub-unit without its
    parent article/section -- pinned here as the invariant it is, not
    merely observed. A `UnitPath` is only ever meaningful together with
    the article it was resolved against; calling `resolve_unit_path`
    with no article is not a supported call shape at all."""
    from app.definition_links.profiles import get_profile

    il_profile = get_profile("IL")
    with pytest.raises(TypeError):
        il_profile.resolve_unit_path(char_offset=5)  # no article -- must be required, not optional
