"""Cycle-5 item 14 -- matcher-level live-path proof that the merged seam's
generic `(unit_kind, unit_value)` / M9 tuple mechanism correctly enforces
scope for TWO of the U2 known-limitation rows, using their REAL declared
scope values (not synthetic placeholders): `STATE_AK_T13_C13.06_S13.06.050`
(chapter RANGE) and `STATE_KY_TXIII_C156_S156.106` (enumerated LOCAL, "for
section and KRS 161.605").

**Honesty note on RED status (per the Planner's brief, report every test's
failure mode truthfully).** These two tests are **NOT RED** -- QA cycle 3
already confirmed the tuple-valued `source_chapter`/`source_article_number`
mechanism is LIVE and merged (`matcher._value_matches`/`_in_scope`,
proven generically by the existing `test_link_articles_to_definitions_
respects_enumerated_local_scope` SD test). Re-running that exact,
already-shipped mechanism against THESE SPECIFIC real values is expected
to pass TODAY, with zero code changes -- that is precisely what "AK's
multi-chapter range ... expressible TODAY with no new scope-kind
registration" means. Included here as REQUIRED, REAL-DATA-ANCHORED PROOF
(not a generic Hebrew placeholder) that these two of the ten U2 rows are
genuinely expressible, per the contract's "measure each of the 10
individually" instruction -- a live-path pin, not a capture RED. The
genuinely NEW, RED part of item 14 (parsing the tuple VALUES out of real
heading text, and the escalated question of how a definitions-SECTION's
scope KIND ever becomes anything other than baseline's 2-way `chapter`/
`law-wide`) is in the companion file
`test_definition_links_us_heading_variants_cycle5_scope_parse.py` and the
Planner's report.

## AK's real chapter membership (verified against the real corpus, not
invented)

`STATE_AK_T13_C13.06_S13.06.050`'s heading is `General definitions for AS
13.06  AS 13.36.` (the em-dash between the two bounds is itself mojibake
in this row -- irrelevant to this file, which uses the ALREADY-EXTRACTED
boundary values, not the raw heading string). Querying the real
`us_ak_statutes.parquet` for every distinct `chapter` value under
`title_number == "13"` between the two named bounds (inclusive) gives
NINE real chapters, not an arithmetic range (`13.07`-`13.11` etc do not
exist): `13.06, 13.12, 13.16, 13.21, 13.26, 13.27, 13.28, 13.33, 13.36`
(this is Alaska's real Uniform Probate Code chapter structure). Both
directions below use one member chapter (`13.16`, a genuine mid-range
member NOT touching either literal boundary, proving this isn't an
accidental prefix/substring match on `"13.06"`/`"13.36"`) and one real
non-member AK chapter from the SAME title (`13.90`, Alaska's Health Care
Decisions Act chapter -- outside the named probate-code range).

## KY_156.106's real enumerated scope

Body: `(1) For purposes of this section and KRS 161.605, "critical
shortage area" means a lack of certified teachers...` -- LOCAL scope,
enumerated over exactly two article numbers: `156.106` (itself) and
`161.605` (a different KY chapter's section). The third direction proven
is a real, uninvolved KY article number (`139.486`, one of the OTHER U2
rows, deliberately reused here to prove it is NOT swept in).
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.matcher import link_articles_to_definitions
from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

# Real, corpus-verified AK Title 13 chapter membership between the named
# heading bounds "AS 13.06" and "AS 13.36" inclusive (see module docstring).
_AK_PROBATE_CODE_CHAPTERS = (
    "13.06", "13.12", "13.16", "13.21", "13.26", "13.27", "13.28", "13.33", "13.36",
)


def _ak_profile():
    return get_profile("US-AK")


def _ky_profile():
    return get_profile("US-KY")


def test_ak_multi_chapter_range_definition_links_a_mention_in_a_member_chapter():
    """In-scope direction: a mention of "agent" (one of the real AK
    13.06.050 body's own defined terms -- '(1) agent means a person
    granted authority to act for a principal under a power of attorney...')
    in a DIFFERENT article that merely SHARES a member chapter (13.16, not
    13.06 itself) must still link -- this is what "chapter RANGE", not
    "this one chapter", requires."""
    definition = DefinitionCandidate(
        terms=("agent",),
        definition_text="a person granted authority to act for a principal",
        scope="chapter",
        source_chapter=_AK_PROBATE_CODE_CHAPTERS,
    )
    member_article = MatcherArticle(
        number="13.16.005",
        heading="Applicability",
        body="An agent appointed under this chapter must act in good faith.",
        chapter="13.16",
    )

    edges = link_articles_to_definitions(
        [definition], [member_article], profile=_ak_profile()
    )
    linked = {e.article_number for e in edges}
    assert "13.16.005" in linked, (
        "a chapter-range-scoped definition must link a mention in ANY member "
        "chapter of the named range, not just its own home chapter"
    )


def test_ak_multi_chapter_range_definition_does_not_link_a_mention_outside_the_range():
    """Out-of-scope direction: the SAME term, mentioned in a real AK
    chapter (13.90, the Health Care Decisions Act) that is NOT a member of
    the "AS 13.06 -- AS 13.36" range, must NOT link -- proving the range is
    enforced as a genuine boundary, not silently widened to law-wide."""
    definition = DefinitionCandidate(
        terms=("agent",),
        definition_text="a person granted authority to act for a principal",
        scope="chapter",
        source_chapter=_AK_PROBATE_CODE_CHAPTERS,
    )
    non_member_article = MatcherArticle(
        number="13.90.010",
        heading="Health care decisions",
        body="An agent named in a health care directive has specific duties.",
        chapter="13.90",
    )

    edges = link_articles_to_definitions(
        [definition], [non_member_article], profile=_ak_profile()
    )
    linked = {e.article_number for e in edges}
    assert "13.90.010" not in linked, (
        "a mention in a chapter OUTSIDE the named range must not link, even though "
        "it shares Title 13 and the same term"
    )


def test_ky_enumerated_local_scope_links_mentions_in_both_named_sections():
    """In-scope direction, both members: KY 156.106's real declared scope
    is "this section AND KRS 161.605" -- an M9 enumerated LOCAL scope over
    two specific article numbers, the same mechanism already proven
    generically by the SD `3-14-3`/`3-14-4` test. A mention in EITHER named
    section must link."""
    definition = DefinitionCandidate(
        terms=("critical shortage area",),
        definition_text=(
            "a lack of certified teachers in particular subject areas, in grade "
            "levels, or in geographic locations at the elementary and secondary level"
        ),
        scope="local",
        source_article_number=("156.106", "161.605"),
    )
    home_article = MatcherArticle(
        number="156.106",
        heading="Critical shortage areas",
        body="A critical shortage area is determined annually by the commissioner.",
    )
    enumerated_sibling_article = MatcherArticle(
        number="161.605",
        heading="Appointment of retired teachers",
        body="Appointment to a critical shortage area follows the procedures below.",
    )

    edges = link_articles_to_definitions(
        [definition],
        [home_article, enumerated_sibling_article],
        profile=_ky_profile(),
    )
    linked = {e.article_number for e in edges}
    assert linked == {"156.106", "161.605"}, (
        "both named sections must link -- this is a two-member enumeration, not a "
        "single-article local scope"
    )


def test_ky_enumerated_local_scope_does_not_link_a_mention_in_an_uninvolved_section():
    """Out-of-scope direction: a real, uninvolved KY article (139.486 --
    one of the OTHER U2 rows) that happens to share the same defined term
    in its own body text must NOT link, proving the enumeration is a
    closed set, not silently broadened to the whole chapter/title."""
    definition = DefinitionCandidate(
        terms=("critical shortage area",),
        definition_text=(
            "a lack of certified teachers in particular subject areas, in grade "
            "levels, or in geographic locations at the elementary and secondary level"
        ),
        scope="local",
        source_article_number=("156.106", "161.605"),
    )
    uninvolved_article = MatcherArticle(
        number="139.486",
        heading='Sale, use, storage, or consumption of "industrial machinery"',
        body="A critical shortage area is not defined or relevant in this section.",
    )

    edges = link_articles_to_definitions(
        [definition], [uninvolved_article], profile=_ky_profile()
    )
    linked = {e.article_number for e in edges}
    assert "139.486" not in linked, (
        "a real KY article outside the two-member enumeration must not link, even "
        "though its own body text happens to mention the same term"
    )
