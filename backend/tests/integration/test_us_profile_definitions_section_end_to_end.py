"""RED integration test for the US profile's Stage-1-to-3 chain (sprint
2026-08-02-us-state-law, gates G2 + G3): "a real US statute parses" AND
"a term defined in a US statute and used later in that statute produces a
link".

Unlike the DB-backed `test_definition_links_pipeline_*.py` integration
tests, this drives the real US-family profile's methods CHAINED together
exactly the way `pipeline.py` Stages 1-3 chain the Hebrew module functions
today (`sections.is_definitions_heading` -> `extract.
extract_definitions_from_section` -> `matcher.find_term_uses`/
`link_articles_to_definitions`) -- proving the three US-profile
capabilities from `test_definition_links_us_profile.py` (tested there in
isolation) actually compose, not just individually pass. Full DB-backed
end-to-end ingestion of a real vaquill parquet file is the SEPARATE
dataset-ingester item's job (G6) -- that item's own ingestion path
(parquet rows -> Article/Document, not `ingest_wiki_law`'s `@ N.`
wiki-marker format) is what actually lands real US statute text in the
database; this test proves the deterministic-engine half of that pipeline
is ready for it.

RED signal: `app.definition_links.profiles.get_profile` does not exist yet
(same as the item's unit tests).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.matcher import link_articles_to_definitions
from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def test_definitions_section_terms_link_to_a_later_use_in_the_same_document():
    rows = {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}
    definitions_row = rows["STATE_DE_T5_C7_SVIII_S796"]

    us_profile = get_profile("US-DE")

    # Stage 1: this really is a Definitions section, no Hebrew rule involved.
    assert us_profile.is_definitions_heading(definitions_row["section_title"]) is True

    # Stage 2: extract every defined term.
    candidates = us_profile.extract_definitions_from_section(
        definitions_row["text"], scope="law-wide"
    )
    assert {term for c in candidates for term in c.terms} == {
        "Affiliate",
        "Branch office",
        "Insured depository institution",
    }

    # Stage 3: a LATER article/section using "Affiliate" (English
    # word-boundary rule, no Hebrew prefix-letter expansion) must link back
    # to its definition -- and must NOT false-match "Affiliated Persons"
    # (a longer phrase sharing the same leading word).
    definitions_article = MatcherArticle(
        number="796", heading=definitions_row["section_title"], body=definitions_row["text"]
    )
    using_article = MatcherArticle(
        number="797",
        heading="§ 797. Reporting requirements.",
        body=(
            "Each Affiliate shall file an annual report. Affiliated Persons "
            "are subject to a separate registration regime under § 800."
        ),
    )

    edges = link_articles_to_definitions(
        candidates, [definitions_article, using_article], profile=us_profile
    )

    using_edges = [e for e in edges if e.article_index == 1]
    assert len(using_edges) == 1
    assert using_edges[0].term == "Affiliate"
    matched_text = using_article.body[
        using_edges[0].char_offset : using_edges[0].char_offset + len("Affiliate")
    ]
    assert matched_text == "Affiliate"
