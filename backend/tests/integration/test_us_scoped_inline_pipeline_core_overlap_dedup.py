"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 2, D10; ruling
S-R6). `rules/us_scope_trigger_proof.py` (core-authored, gate C2) already
registers, for `US-*`, `As used in this section, "Term" means ...` ->
`scope="local"` -- this family's single most common shape. `ScopeTriggerRule`
is a UNION kind (`registry.py`'s own docstring: "every matching rule's
candidates are kept -- zero-miss, rules never suppress each other"), so
once the Developer's own broader rule is registered it will ALSO match
this shape, each rule independently returning a `DefinitionCandidate` for
the SAME (owning article, term).

The seam spec claims this dedupes downstream on `(article_id, sorted(
terms))` (`pipeline.py` Stage 2, read directly: `key = (owning_art.id,
tuple(sorted(candidate.terms)))`; `definitions_by_key.get(key)` reuses the
FIRST-created `Definition` row for every later candidate sharing that same
key). That is a claim to TEST on the live path, not assume.

NOT deferred to Phase B: rather than wait for the not-yet-built
`us_scoped_inline` module to construct a real two-rule overlap, this test
registers its OWN second, throwaway `ScopeTriggerRule` at test time --
following the SAME `register_scope_trigger_rule` pattern core's own
`test_definition_links_rules_registry.py` already uses directly in test
bodies with no teardown. The throwaway rule's `extract` only ever fires on
a unique nonce string embedded in THIS test's own synthetic row body, so
it cannot affect (or be affected by) any other test's fixture text,
independent of execution order -- this is a live, present-tense proof of
the dedup claim, not a tripwire waiting on Phase A/B.
"""

from __future__ import annotations

_NONCE = "US-SCOPED-INLINE-D10-OVERLAP-PROOF-NONCE-7f3a2c1d"


def _synthetic_overlap_row() -> dict:
    return {
        "act_id": "STATE_UT_SYNTHETIC_CORE_OVERLAP_PROOF",
        "chapter": "1",
        "section_number": "99.99",
        "section_title": "§ 99.99. Synthetic core-overlap dedup proof (not a real statute).",
        "text": (
            f'As used in this section, "Widget" means a manufactured item '
            f"sold at retail (nonce {_NONCE}). A Widget must be inspected before sale."
        ),
    }


def _register_throwaway_duplicate_rule() -> None:
    """A second `ScopeTriggerRule`, registered independently of whatever
    the Developer eventually builds, that ALSO captures "Widget" from this
    test's own synthetic row -- constructing a real two-rule overlap on
    the live path right now. Gated on `_NONCE` so it is a pure no-op
    against every other test's real/synthetic fixture text."""
    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.rules.registry import (
        RuleContext,
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )

    def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
        if _NONCE not in article_body:
            return []
        return [
            DefinitionCandidate(
                terms=("Widget",),
                definition_text="a manufactured item sold at retail (duplicate candidate)",
                scope="local",
                source_article_number=ctx.article_number,
            )
        ]

    register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))


def test_core_proof_rule_and_a_second_overlapping_rule_dedupe_to_one_definition(
    db_session, matter_with_users
):
    """Both `us_scope_trigger_proof.py`'s core-authored rule AND this
    test's own throwaway rule match `'As used in this section, "Widget"
    means ...'` -- proves the pipeline's Stage-2 dedup key collapses the
    two resulting candidates to exactly ONE persisted `Definition` row,
    and that Stage 3 emits no duplicate `USES_DEFINITION` assertion for
    the single in-article reuse of the term."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    _register_throwaway_duplicate_rule()

    m = matter_with_users
    row = _synthetic_overlap_row()

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Utah Code (core-overlap dedup proof, synthetic)",
        rows=[row],
        jurisdiction="US-UT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    widget_defs = [d for d in result["created_definitions"] if "Widget" in d["terms"]]
    assert widget_defs, "neither rule captured the overlap-proof text at all"
    assert len(widget_defs) == 1, (
        "core's proof rule and this test's own throwaway rule both matched "
        'the SAME `As used in this section, "Widget" means ...` text -- the '
        "seam spec's dedup-on-(article_id, sorted(terms)) claim did not "
        f"hold; got {len(widget_defs)} Definition rows instead of 1: {widget_defs!r}"
    )

    widget_id = widget_defs[0]["id"]
    # object/subject ids live on the persisted `Assertion` row, not the
    # summary dict (see test_definition_links_pipeline_live.py's contract).
    uses_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == widget_id
    ]
    assert len(uses_edges) == 1, (
        "exactly one USES_DEFINITION assertion is expected for the single "
        f"in-article mention of 'Widget' -- got {len(uses_edges)}: {uses_edges!r}"
    )
