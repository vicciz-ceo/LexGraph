"""Sprint 2026-08-04-defs-il, Planner-authored RED test for gate I3 --
scoped definitions must assert USES_DEFINITION only within their declared
scope, proven live-path in BOTH directions (in-scope mention links;
out-of-scope mention does not).

This test is deliberately coupled to class (a) (see
`test_definition_links_il_missed_classes_live.py`): today
`extract_local_definitions` never recognizes the `בפרק זה` trigger at all,
so ZERO `Definition` rows are produced for this fixture and the assertion
that at least one in-scope USES_DEFINITION edge exists fails immediately.
That is the correct RED signal for gate I3, not a fixture bug -- I3 cannot
be proven until class (a) content lands.

Design note for whoever implements class (a) (recorded here AND in the
sprint log): naively adding `בפרק זה` to `_LOCAL_TRIGGER_RE`'s trigger
alternation WITHOUT ALSO changing the `scope=` this function hardcodes
would still fail this test. `extract_local_definitions` currently stamps
every match `scope="local"` unconditionally (extract.py:196), and
`matcher._in_scope`'s `"local"` branch restricts to the SAME ARTICLE NUMBER
only (matcher.py:108-109) -- that is much narrower than what `בפרק זה`
("in this chapter") means. A definition triggered by `בפרק זה` must be
stamped `scope="chapter"` (matched against `Article.chapter`, matcher.py:
106-107), not `scope="local"`, or every use outside the DEFINING article
itself -- even other articles in the very same chapter -- would be wrongly
left unlinked.
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_beperek_zeh_definition_links_within_chapter_and_not_outside_it(
    db_session, matter_with_users
):
    """`חוק זכות מטפחים של זני צמחים` (real excerpt, פרק ג'+ד'): article 15
    defines `"בקשה"` scoped `בפרק זה` under `פרק ג': המועצה, הרשם והועדה
    לזכויות מטפחים`. The SAME word `בקשה` also appears, live, in:

    - articles 13, 16, 17 -- SAME chapter (פרק ג') as the defining
      article 15 -- each of these mentions MUST get a USES_DEFINITION
      edge once class (a) is implemented with correct chapter scope.
    - article 20 -- a DIFFERENT chapter (פרק ד': הליכי רישום) -- this
      mention must NEVER get a USES_DEFINITION edge; scope enforcement
      must not leak the chapter-scoped definition into a sibling
      chapter just because the same surface form appears there too.

    Both directions are asserted in one test (manager instruction: "proven
    live-path in both directions").
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.article import Article
    from app.models.assertion import Assertion

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק זכות מטפחים של זני צמחים, התשל״ג-1973",
        wiki_text=_read("חוק זכות מטפחים של זני צמחים_ch3_ch4_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    bakasha_defs = [d for d in result["created_definitions"] if "בקשה" in d["terms"]]
    assert len(bakasha_defs) == 1, (
        f'expected exactly one Definition row for "בקשה" (article 15, '
        f'scope should be "chapter"); got {result["created_definitions"]!r}'
    )
    definition_id = bakasha_defs[0]["id"]

    uses_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
    ]
    using_article_ids = set()
    for edge in uses_edges:
        assertion_row = db_session.get(Assertion, edge["id"])
        if assertion_row.object_entity_id == definition_id:
            using_article_ids.add(assertion_row.subject_entity_id)

    using_article_numbers = {
        db_session.get(Article, article_id).number for article_id in using_article_ids
    }

    # Direction 1: in-scope mentions (same chapter, פרק ג') DO get linked.
    assert using_article_numbers & {"13", "16", "17"}, (
        f'expected at least one of articles 13/16/17 (same chapter as the '
        f'defining article 15) to use the "בקשה" definition; got '
        f"using_article_numbers={using_article_numbers!r}"
    )

    # Direction 2: out-of-scope mention (different chapter, פרק ד') does
    # NOT get linked, even though the same surface form "בקשה" appears
    # there too (article 20's body mentions בקשה repeatedly).
    assert "20" not in using_article_numbers, (
        f'article 20 is in a DIFFERENT chapter (פרק ד\') from the '
        f'chapter-scoped definition (defined in article 15, פרק ג\') -- '
        f"it must not receive a USES_DEFINITION edge; "
        f"using_article_numbers={using_article_numbers!r}"
    )
