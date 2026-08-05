"""Sprint 2026-08-05-defs-core-follow-on-2, gate G9 (breadcrumbs data
source). Planner (plan6). P-R8 live-path consumption proof, re-authored
(not cherry-picked) from the finding `claude/defs-il`'s D-1b Planner first
surfaced (commit bc54e1a) and this sprint's manager accepted as gate G9
(`docs/sprint/sprints/2026-08-05-defs-core-follow-on-2-log.md`, "Phase 1b").

## What this file proves that the unit-level file does not

`test_definition_links_g9_heading_breadcrumbs.py` (unit) pins that
`sections.parse_articles` CAPTURES full-depth breadcrumbs -- necessary but
not sufficient. Per this gate's own quality bar (P-R8): "a RED must show a
`StructuralUnitRule` actually RECEIVING non-empty breadcrumbs and changing
an observable ANSWER -- not merely that the field is populated." This file
proves that, end to end, through the REAL public entry points
(`ingest_wiki_law` + `run_definition_linking`) -- no stub `SimpleNamespace`
article, no direct call to `pipeline._structural_ctx`-shaped internals.

Today, both directions of this proof fail for the SAME two reasons named
in the gate brief:
1. `pipeline.py`'s one `StructuralContext(...)` construction site hardcodes
   `heading_breadcrumbs=()` -- so even once `sections.py` captures the real
   text (see the unit-level file), nothing threads it from the ingested
   `Article` row into the context a registered `StructuralUnitRule` reads.
2. Until (1) is fixed, `sections.py`'s own capture is moot for this
   specific live path -- there is no persisted column carrying it from
   ingest-time to pipeline-time either (see this file's "What must NOT
   change" note below); today `StructuralUnitRule.derive` is dispatched
   (proven live already by QA gate A2,
   `test_dispatch_qa_gate_a2_structural_unit_rule_live.py`) but always
   fed an EMPTY `heading_breadcrumbs` tuple, so it always returns `()` and
   never stamps a `ScopeUnit` -- "live dispatch over an empty input is not
   live capability."

## Registry-pollution safety (why jurisdiction code `US-HI`)

`registry.py`'s rule lists are process-global with no teardown -- every
prior QA/dispatch test in this sprint's lineage that registers a
throwaway rule picks an otherwise-unused jurisdiction code for exactly
this reason (see `test_dispatch_qa_gate_a2_structural_unit_rule_live.py`'s
own `"US-NV"`, `test_dispatch_qa_gate_d2_level_tie_probe.py`'s `"US-MS"`).
`"US-HI"` (Hawaii) was verified, this session, to be used by NO
`register_structural_unit_rule`/`register_scope_trigger_rule`/any other
rule-registration call anywhere in this branch's `backend/tests` or
`backend/app` (`git grep -c "US-HI"` -> 0 hits in both trees) -- safe,
will not affect any other test's dispatch, and will not touch the real
`"IL"` jurisdiction's own registered rules (a named regression surface
this gate must not risk). `ingest_wiki_law`'s own `parse_articles` call is
jurisdiction-agnostic (confirmed by reading `ingest.py`: `jurisdiction` is
stored on `Document` and used only for LATER profile dispatch, never for
parsing) -- so real, byte-verified Hebrew wiki-format fixture text can be
ingested under this synthetic code exactly as gate-A2's own precedent
ingests wiki-format text under a non-`"IL"` code.

## Fixture

`חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki` -- the SAME fixture the
unit-level file byte-verified (provenance documented there; not repeated
here). The term `"מוצרי חלב"` ("dairy products") is a REAL word genuinely
present, unmodified, in articles 3 (the defining article, סימן א'), 12
(same סימן א', the same-unit mention that must link) and 15 (סימן ב', a
genuinely DIFFERENT unit of the SAME chapter, the mention that must NOT
link) -- verified by direct substring search of the fixture file, not
assumed.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"

_CODE = "US-HI"  # unused by any other rule-registration test on this branch


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_a_structural_unit_rule_receives_real_siman_breadcrumbs_and_containment_holds_in_both_directions_live(
    db_session, matter_with_users
):
    """Registers a `ScopeTriggerRule` that stamps a `"siman"`-scoped
    Definition for `"מוצרי חלב"` from article 3's real body, and a
    `StructuralUnitRule` whose `.derive` reads `ctx.heading_breadcrumbs`
    (NOT `ctx.article_number` -- unlike QA gate A2's own probe, which
    deliberately used `article_number` because `heading_breadcrumbs` was
    already known dead at the time) for a depth-3 entry and stamps a
    matching `ScopeUnit`. Runs the REAL `ingest_wiki_law` +
    `run_definition_linking` against the byte-verified fixture and
    inspects the REAL created `USES_DEFINITION` assertions.

    Expected RED today: `pipeline.py`'s hardcoded `heading_breadcrumbs=()`
    means `_derive` below always sees an empty tuple regardless of which
    article it is called for, so it always returns `()`, no `"siman"`
    `ScopeUnit` is EVER stamped on ANY article, and `matcher._in_scope`'s
    generic branch can never find a match -- ZERO `USES_DEFINITION`
    assertions for `"מוצרי חלב"` at all, for either direction.
    """
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

    term = "מוצרי חלב"
    defining_siman = "סימן א': הסדרת הייצור והשיווק"

    # ScopeTriggerRule: stamps a Definition scoped to the GENERIC "siman"
    # kind (no dedicated field on Definition -- goes through matcher.
    # _in_scope's generic-kind branch, the branch M-D1/this gate makes
    # genuinely reachable) when it sees article 3's own real content.
    def _extract_def(article_body, ctx):
        if ctx.article_number != "3":
            return []
        assert term in article_body  # sanity: this IS article 3's real body
        return [
            DefinitionCandidate(
                terms=(term,),
                definition_text=(
                    'לעניין סעיף זה, "מוצר חלב" - מוצר שאינו חומרי גלם '
                    "חלביים, המכיל חלב גולמי או חומרי גלם חלביים בשיעור "
                    "העולה על 50 אחוזים ממשקלו."
                ),
                scope="siman",
                scope_value=defining_siman,
            )
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=(_CODE,), extract=_extract_def)
    )

    # StructuralUnitRule: THE LOAD-BEARING PART OF THIS PROOF. Reads
    # ctx.heading_breadcrumbs (populated per-article by pipeline.py's own
    # construction site, gate G9's fix target) for the depth-3 ("siman")
    # entry and stamps it generically -- dynamic, not hardcoded per
    # article, exactly how a real IL siman/chelek rule would eventually
    # work (that build itself stays the IL panel's own future work, per
    # this gate's brief -- this probe only proves core's data now reaches
    # it and is correct).
    def _derive(ctx):
        for depth, text in ctx.heading_breadcrumbs:
            if depth == 3:
                return (ScopeUnit(kind="siman", value=text),)
        return ()

    register_structural_unit_rule(StructuralUnitRule(jurisdiction_codes=(_CODE,), derive=_derive))

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="G9 Live Structural-Unit Breadcrumbs Probe Statute",
        wiki_text=_read("חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki"),
        jurisdiction=_CODE,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    term_defs = [d for d in result["created_definitions"] if term in d["terms"]]
    assert len(term_defs) == 1, (
        f'expected exactly one siman-scoped Definition row for "{term}" '
        f"(article 3, capture already reachable via the registered "
        f"ScopeTriggerRule regardless of this gate's own fix); got "
        f"{result['created_definitions']!r}"
    )
    assert term_defs[0]["scope"] == "siman", term_defs[0]

    uses_props = [
        a["proposition"]
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert any("Article 12" in p for p in uses_props), (
        "expected article 12 (SAME סימן א' as the defining article 3) to "
        'get a USES_DEFINITION edge for its genuine mention of "מוצרי '
        'חלב" in its own body -- this requires a live StructuralUnitRule '
        "to have received article 12's real depth-3 breadcrumb "
        f'("{defining_siman}") through ctx.heading_breadcrumbs and '
        f"stamped a matching ScopeUnit; got uses_props={uses_props!r}, "
        f"created_assertions={result['created_assertions']!r}. If this is "
        "empty, pipeline.py's StructuralContext(heading_breadcrumbs=()) "
        "hardcode (or sections.py's discarded 3+-equals heading text) is "
        "still starving StructuralUnitRule.derive of real data."
    )
    assert not any("Article 15" in p for p in uses_props), (
        "expected article 15 (סימן ב', a genuinely DIFFERENT structural "
        'unit of the SAME chapter) to get NO USES_DEFINITION edge for '
        'its own genuine mention of "מוצרי חלב" -- a siman-scoped '
        "definition must not leak across siman boundaries even once "
        f"containment starts working; got uses_props={uses_props!r}"
    )
