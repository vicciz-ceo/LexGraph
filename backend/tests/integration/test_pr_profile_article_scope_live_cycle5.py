r"""Cycle-5 Planner, item 28 (gate P3, article-scope half only -- the
chapter-scope half stays HELD, see `test_pr_profile_scope_cycle4.py`, all
6 REDs there target `determine_scope`, which has NO rule seam of any
kind, confirmed live-read against `us_profile.py:1003`).

Per the escalation-ruling table (`## ESCALATION -- RULED (P-R8)` in the
contract), P3's article-scope direction is LIVE today via the same
`ScopeTriggerRule` seam item 26 wires up -- **P3's article-scope half has
NO existing test** (all 6 REDs in `test_pr_profile_scope_cycle4.py`
target `determine_scope`/chapter scope), so this is a genuinely NEW
live-path test, not a realignment.

Proves BOTH directions of the director's standing scoped-definitions
constraint, live, through the REAL `run_definition_linking` path:
"A los fines de este Artículo ..." -> `scope="local"`, contained by
`matcher._in_scope` (`article.number == definition.source_article_number`,
`matcher.py:144-145`) -- an in-scope mention (same article) links; an
out-of-scope mention (a DIFFERENT article, identical term surface form)
does NOT link. Mirrors core's own `test_an_enumerated_local_scope_links_
every_member_article_and_excludes_a_non_member_live` template exactly,
adapted to a single-article (non-enumerated) local scope and real Spanish
content -- synthetic-but-realistic body text, the SAME convention core's
own mechanism-proof tests use (vendored-fixture-byte-fidelity is this
panel's standard for CORPUS-CAPTURE proofs, not for wiring/mechanism
proofs, which have always used synthetic content in this codebase, e.g.
"Enumerated widget"/"Local widget").
"""

from __future__ import annotations


def test_a_local_scope_definition_links_a_mention_in_its_own_article_but_not_an_identical_term_mention_in_a_different_article_live(
    db_session, matter_with_users
):
    """`"término de prueba"` is defined via `A los fines de este Artículo`
    inside Article 5 -- article-scoped by construction (`extract_local_
    definitions` never sets its own `source_article_number`; `USProfile.
    extract_local_scope_definitions` defaults it to the CALLING article's
    own number, `us_profile.py:1179-1180`). A second, later sentence in
    the SAME Article 5 re-mentions the term (must link); Article 9, a
    wholly separate provision, mentions the IDENTICAL term surface form
    (must NOT link -- the director's standing scoped-definitions
    constraint, proven in both directions)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    wiki_text = (
        '@ 5. Disposiciones generales sobre el programa\n'
        'A los fines de este Artículo, "término de prueba" significa el '
        "período inicial de evaluación de un empleado nuevo. El período "
        "de término de prueba no podrá exceder los seis meses conforme a "
        "esta sección.\n"
        "@ 9. Disposiciones sobre otro programa no relacionado\n"
        "El término de prueba mencionado en otras disposiciones de esta "
        "ley no aplica a este programa distinto.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test PR Statute (item 28, P3 article-scope, both directions)",
        wiki_text=wiki_text,
        jurisdiction="US-PR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    linked_propositions = " | ".join(e["proposition"] for e in uses_edges)

    assert "Article 5" in linked_propositions, (
        "IN-SCOPE direction: the same-article re-mention of the defined "
        "term must be linked -- created assertions were: "
        f"{linked_propositions!r}"
    )
    assert "Article 9" not in linked_propositions, (
        "OUT-OF-SCOPE direction: Article 9's mention of the identical "
        "term surface form must NOT be linked -- the definition's scope "
        "is local to Article 5 only (M-R12/D-E1 containment, "
        "matcher._in_scope). Created assertions were: "
        f"{linked_propositions!r}"
    )


def test_a_local_scope_definition_never_reaches_a_different_document_even_when_the_term_repeats_live(
    db_session, matter_with_users
):
    """A second, independently-ingested PR document (a different law
    entirely) that happens to reuse the identical defined-term surface
    form in its own Article 5 must NOT be linked to the first document's
    definition -- "law-wide" (Stage 1) means scoped to the single law/
    Document an article belongs to (`pipeline.py`'s own module docstring,
    "Scoping note"), and "local" is narrower still. Guards against a
    same-number-coincidence false link across two unrelated laws."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    wiki_text_a = (
        '@ 5. Disposiciones generales sobre el programa\n'
        'A los fines de este Artículo, "término de prueba" significa el '
        "período inicial de evaluación de un empleado nuevo.\n"
    )
    wiki_text_b = (
        "@ 5. Un artículo con el mismo número en otra ley distinta\n"
        "El término de prueba en este contexto se refiere a un asunto "
        "completamente distinto de la primera ley.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test PR Statute A (item 28, cross-document isolation)",
        wiki_text=wiki_text_a,
        jurisdiction="US-PR",
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test PR Statute B (item 28, cross-document isolation)",
        wiki_text=wiki_text_b,
        jurisdiction="US-PR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    definitions = [d for d in result["created_definitions"] if "término de prueba" in d["terms"]]
    assert len(definitions) == 1, (
        "exactly one Definition row expected, from Statute A's own Article "
        f"5 -- got {definitions!r}"
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert len(uses_edges) == 0, (
        "Statute B's Article 5 shares the SAME article number as Statute "
        "A's defining article, but is a DIFFERENT document -- it must not "
        f"be linked to Statute A's local-scoped definition. Got: {uses_edges!r}"
    )
