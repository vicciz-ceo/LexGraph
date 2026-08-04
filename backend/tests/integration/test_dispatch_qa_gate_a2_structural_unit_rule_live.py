"""QA cycle 1 (sprint 2026-08-04-defs-core-dispatch), gate A2 -- INDEPENDENT
live-path proof that `StructuralUnitRule` (item I4, manager ruling M-D1) is
genuinely wired on the production path, not merely unit-tested against a
`SimpleNamespace` stub.

**Why this file exists, in QA's own words.** The shipped
`test_definition_links_rule_dispatch_structural_units.py` (Developer/Planner
authored) proves the UNION mechanism (`registry.structural_unit_rules_for`
+ each rule's `.derive(ctx)`, summed) and then calls
`matcher.definition_covers_mention` against a `SimpleNamespace` stub article
carrying a hand-built `.structural_units` tuple -- via its own test-local
`_union_structural_units` helper. That is EXACTLY the stub-based pattern
that produced the prior sprint's C1 bounce (a green unit test proving the
wrong thing because the real production `MatcherArticle` never carried the
attribute the stub had). This file does not trust that green: it registers
a real `StructuralUnitRule`, runs the REAL `run_definition_linking` against
a REAL DB-backed matter, and inspects the REAL `Assertion` rows it creates
-- proving the actual population site (`pipeline.py`, the `structural_units
= (ScopeUnit(kind="chapter", ...),) + tuple(... registry.structural_unit_
rules_for(profile.code) ...)` computation feeding `MatcherArticle(...,
structural_units=structural_units)`) is genuinely reached, and that
`matcher._in_scope`'s generic-kind branch genuinely consumes what lands
there -- end to end, both directions (a definition scoped to the rule's own
kind links a mention in an article the rule stamps that kind onto; it does
NOT link a mention in a sibling article the rule does not).
"""

from __future__ import annotations

import re


def test_qa_live_structural_unit_rule_dispatch_links_only_the_article_it_was_stamped_onto(
    db_session, matter_with_users
):
    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.rules.registry import (
        ScopeUnit,
        StructuralUnitRule,
        ScopeTriggerRule,
        register_structural_unit_rule,
        register_scope_trigger_rule,
    )
    from app.models.assertion import Assertion

    code = "US-NV"  # a code not used by any other structural-unit test in this sprint

    # ScopeTriggerRule: stamps a definition scoped to the GENERIC "part" kind
    # (a kind with no dedicated field -- goes through matcher._in_scope's
    # generic-kind branch, the one this item makes live).
    def _extract_def(article_body, ctx):
        if "ZZZ_QA_STRUCT_TRIGGER" not in article_body:
            return []
        return [
            DefinitionCandidate(
                terms=("Regulated widget",),
                definition_text="a specially regulated item under this part",
                scope="part",
                scope_value="II",
            )
        ]

    register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=(code,), extract=_extract_def))

    # StructuralUnitRule: stamps ScopeUnit(kind="part", value="II") onto
    # article "1" ONLY -- article "2" gets nothing, proving the negative
    # direction (an article the rule does not touch must NOT be in scope).
    def _derive(ctx):
        if ctx.article_number == "1":
            return (ScopeUnit(kind="part", value="II"),)
        return ()

    register_structural_unit_rule(StructuralUnitRule(jurisdiction_codes=(code,), derive=_derive))

    m = matter_with_users
    term = "Regulated widget"
    wiki_text = (
        f"@ 1. First article, inside part II\n"
        f'ZZZ_QA_STRUCT_TRIGGER "{term}" as used in this part means a '
        f"specially regulated item under this part.\n"
        f"A {term} is mentioned here, in article one.\n"
        f"@ 2. Second article, NOT inside part II\n"
        f"A {term} is mentioned here too, in article two -- out of scope.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="QA Test StructuralUnitRule Live Dispatch Statute",
        wiki_text=wiki_text,
        jurisdiction=code,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a StructuralUnitRule-derived generic-kind ('part') scope must "
        "link the mention in the article it was actually stamped onto -- "
        f"got ZERO USES_DEFINITION assertions. created_assertions="
        f"{result['created_assertions']!r}. If this is empty, either the "
        "population site (pipeline.py's structural_units computation) or "
        "matcher._in_scope's generic-kind branch is dead on the live path."
    )

    from app.models.article import Article

    # Resolve which article each surviving assertion's subject points at.
    articles = {
        art.id: art.number
        for art in db_session.query(Article).filter(Article.matter_id == m["matter_id"]).all()
    }

    linked_numbers = set()
    for edge in uses_edges:
        assertion_row = db_session.get(Assertion, edge["id"])
        linked_numbers.add(articles.get(assertion_row.subject_entity_id))

    assert linked_numbers == {"1"}, (
        "the StructuralUnitRule-derived 'part' scope must link article "
        "'1' (the one the rule stamped ScopeUnit(kind='part', value='II') "
        "onto) and must NOT link article '2' (the rule returns () for "
        f"it -- out of scope). Got linked_numbers={linked_numbers!r}, "
        f"uses_edges={uses_edges!r}"
    )
