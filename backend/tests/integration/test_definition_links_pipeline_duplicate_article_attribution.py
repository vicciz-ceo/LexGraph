"""Sprint 2026-07-29-definition-links, cycle 2, item DL11 (G5, POC finding 1,
ruling M9(a)).

`run_definition_linking` (`app/definition_links/pipeline.py`) previously
attributed a `USES_DEFINITION` edge to a using article via a plain
`{article.number: article}` dict built per document
(`number_to_article = {art.number: art for art, _ in doc_articles}`).
When a document's wiki source contains more than one `@ N.` marker sharing
the same `N` (schedules/appendices/numbered sub-lists reusing the marker
syntax -- confirmed corpus-wide at 703/6,133 documents, poc-run.md §8 Issue
1), only the LAST-parsed Article row survives in the dict; any edge found
in ANY duplicate-numbered article gets attributed to whichever row
currently occupies that number slot, which may not be the article where
the match actually occurred.

Reproduction fixture (`wiki_laws/צו איסור הלבנת הון (מפעיל מערכת
לתיווך)_excerpt.wiki`, trimmed verbatim from the real POC-corpus law
poc-run.md §8 names concretely -- `צו איסור הלבנת הון (חובות זיהוי, דיווח
וניהול רישומים של מפעיל מערכת לתיווך באשראי למניעת הלבנת הון ומימון
טרור)`): article `17` ("ניהול רישומים ושמירתם") genuinely uses the bare
term "פעולה" multiple times in its real body; a LATER numbered schedule
list reuses `@ 17.` for an unrelated item whose marker-parsed body is
EMPTY (the wiki syntax puts the whole item's text into the mis-parsed
`heading` field, exactly matching poc-run.md §8's concrete finding for
this exact law). Pre-fix, the dict-based lookup collapses onto the LAST
one seen (the empty duplicate) and misattributes every "פעולה" edge to
it -- confirmed via a standalone probe against this exact fixture before
writing this test (see the cycle-2 Planner log).

The fix (M9(a)): an additive `.article_index` on `ArticleUsesTermEdge`
(see `tests/unit/test_definition_links_matcher.py`, DL11) identifies the
article by POSITION within the per-document `doc_articles` zip, not by
number; `pipeline.py` must map edges back to ORM `Article` rows via that
index, keeping `.number` as provenance only.
"""

from __future__ import annotations

import pathlib

from sqlalchemy import select

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_run_definition_linking_attributes_use_to_the_article_whose_span_actually_contains_the_match(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.article import Article
    from app.models.assertion import Assertion
    from app.models.source_span import SourceSpan

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=(
            "צו איסור הלבנת הון (חובות זיהוי, דיווח וניהול רישומים של מפעיל "
            'מערכת לתיווך באשראי למניעת הלבנת הון ומימון טרור), התשע"ט-2019'
        ),
        wiki_text=_read("צו איסור הלבנת הון (מפעיל מערכת לתיווך)_excerpt.wiki"),
    )

    # Sanity-check the reproduction shape: two Article rows really do share
    # number "17" -- one with a real, populated body, one whose marker-
    # parsed body is empty (the schedule-list mis-parse poc-run.md §8
    # describes).
    duplicate_rows = (
        db_session.execute(
            select(Article).where(Article.matter_id == m["matter_id"], Article.number == "17")
        )
        .scalars()
        .all()
    )
    assert len(duplicate_rows) == 2

    spans_by_article = {a.id: db_session.get(SourceSpan, a.source_span_id) for a in duplicate_rows}
    real_article = next(
        a for a in duplicate_rows if "פעולה כספית שבוצעה" in spans_by_article[a.id].quote_text
    )
    empty_article = next(a for a in duplicate_rows if a.id != real_article.id)
    assert spans_by_article[empty_article.id].quote_text == ""

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION" and '"פעולה"' in a["proposition"]
    ]
    assert len(uses_edges) >= 1

    # Every persisted edge naming "פעולה" must cite an Article whose OWN
    # SourceSpan text actually contains the matched term -- verified via
    # quote_text containment (the brief's explicit requirement), not merely
    # id inequality from the empty duplicate.
    cited_article_ids = set()
    for edge in uses_edges:
        row = db_session.get(Assertion, edge["id"])
        cited_article_ids.add(row.subject_entity_id)
        cited_article = db_session.get(Article, row.subject_entity_id)
        cited_span = db_session.get(SourceSpan, cited_article.source_span_id)
        assert "פעולה" in cited_span.quote_text, (
            f"assertion {edge['id']!r} cites article {cited_article.id!r} "
            f"(number={cited_article.number!r}) whose span text does not "
            "contain the matched term -- misattributed via the old "
            "number-keyed lookup"
        )

    assert real_article.id in cited_article_ids
    assert empty_article.id not in cited_article_ids
