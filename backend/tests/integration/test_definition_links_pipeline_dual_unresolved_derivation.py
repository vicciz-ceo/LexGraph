"""QA regression — sprint 2026-07-29-definition-links, item DL8.

Manager-flagged edge case (QA brief step 5): the review doc's Stage 4
worked example is explicit that cross-law derivation detection emits
"one law_derives_definition edge per term" -- i.e. every DETECTED
derivation gets its own edge. `detect_cross_law_derivations` (DL6,
`app/definition_links/derivation.py`) already returns one
`LawDerivesDefinitionEdge` per trigger-phrase occurrence it recognizes,
so a single definition body that derives from TWO different,
independently-unresolved laws must produce TWO `DERIVES_FROM_LAW`
assertions.

`run_definition_linking` (DL8, `app/definition_links/pipeline.py`)
de-duplicates newly-created assertions via an idempotency key of
`(assertion_type, subject_entity_type, subject_entity_id,
object_entity_type, object_entity_id)`. For an UNRESOLVED derivation,
`object_entity_type`/`object_entity_id` are always `(None, None)` and
`subject_entity_id` is the same `Definition` row for every trigger
found in that definition's own body -- so two distinct unresolved
derivations from the SAME definition collide on an IDENTICAL key. The
second `_create_assertion(...)` call is silently dropped (`if key in
existing_keys: return`), collapsing two edges into one. This test pins
the SPEC'D behavior (two edges) and is expected to FAIL against the
current pipeline.py, proving the collapse rather than asserting it.

Reproduction body (law-wide הגדרות section, single term, but two
distinct, independently-unresolved cross-law derivation triggers ---
neither "חוק הראשון" nor "חוק השני" is ingested as a Document in this
matter, so both resolve to `target_law_id=None`):

    :- "מונח משותף" - כהגדרתו בחוק הראשון, וכהגדרתה בחוק השני;
"""

from __future__ import annotations

from tests.conftest import seed_article, seed_document, seed_source_span

_ARTICLE_BODY = (
    ': בחוק זה -\n'
    ':- "מונח משותף" - כהגדרתו בחוק הראשון, וכהגדרתה בחוק השני;'
)


def test_two_distinct_unresolved_cross_law_derivations_in_one_definition_both_emit_edges(
    db_session, matter_with_users
):
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text=_ARTICLE_BODY
    )
    seed_article(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        source_span_id=span_id,
        number="1",
        heading="הגדרות",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    derives_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "DERIVES_FROM_LAW"
    ]

    # Spec (review doc Stage 4 worked example): each DETECTED derivation
    # emits its own edge -- two distinct unresolved law references in one
    # definition body must produce two DERIVES_FROM_LAW assertions, not
    # one collapsed by the idempotency dedup key.
    assert len(derives_edges) == 2, (
        "expected 2 DERIVES_FROM_LAW assertions (one per distinct unresolved "
        f"cross-law derivation), got {len(derives_edges)}: "
        f"{[a['proposition'] for a in derives_edges]}"
    )

    propositions = {a["proposition"] for a in derives_edges}
    assert any("חוק הראשון" in p for p in propositions)
    assert any("חוק השני" in p for p in propositions)

    for edge in derives_edges:
        row = db_session.get(Assertion, edge["id"])
        assert row.object_entity_id is None
        assert row.object_entity_type is None
