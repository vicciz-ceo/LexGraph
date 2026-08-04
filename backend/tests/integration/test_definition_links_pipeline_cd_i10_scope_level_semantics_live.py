"""I10 RED tests -- live-path proof, `scope="subsection"` LEVEL semantics
(sprint 2026-08-04-defs-core-dispatch, item I10, manager ruling M-D3, seam
v2.7).

Companion to `test_definition_links_cd_i10_scope_level_semantics.py`
(unit-level: `matcher.definition_covers_mention` called directly). That
file's own docstring explains why the FULL matrix is proven at that level
rather than here: constructing a real `ScopeTriggerRule` + wiki fixture +
DB ingest for every format/level combination would multiply this file's
already-real DB-pipeline cost across ~8 near-duplicate scenarios for little
additional confidence, since every one of them funnels through the exact
same two production calls (`link_articles_to_definitions` /
`definition_covers_mention`) the unit-level file already exercises
directly.

What genuinely needs a LIVE proof, and is not implied by the unit-level
file alone, is that `pipeline.py`'s Stage 3 wiring THREADS a `DefinitionCandidate`
carrying the new `scope_unit_kind` field all the way from a registered
`ScopeTriggerRule.extract()` call through to `definition_covers_mention`
unchanged -- i.e. that no shared file (`pipeline.py`, `matcher.py`) needs
family-panel-specific edits to make the new field's effect reach the real
`run_definition_linking` entry point (gate G5's "zero shared-file edits
required of family panels", restated for this new field). Two
representative scenarios are proven here, live, end to end:

1. A subparagraph-level (`scope_unit_kind='upper_alpha'`) declaration,
   federal-shaped body -- the LEVEL-matching mechanism itself, reached via
   the real pipeline.
2. A bare, NO-`scope_unit_kind` declaration on Oregon's real digit-outermost
   shape -- the backward-compatibility claim, on the SAME (different from
   the prior sprint's own lower_alpha-outermost-only C1 proof) real shape
   the unit-level file's own module docstring explains was NEVER live-path
   proven for a digit-outermost body before this item.

Both tests use the SAME directional discriminator the existing C1 live
tests in `test_definition_links_pipeline_scope_seam.py` established
(`_create_assertion`'s dedup key has no `char_offset` component, so only
the FIRST edge `link_articles_to_definitions` produces, in body-text order,
survives): the OUT-OF-SCOPE mention is placed BEFORE the in-scope mention
in each fixture's own text, so an over-inclusive containment bug would let
the wrong one win the race, and `get_mention_unit_paths` on the surviving
assertion catches that directly.
"""

from __future__ import annotations

import re

from sqlalchemy import select


def test_i10_live_subparagraph_level_scope_links_the_correct_subparagraph_and_excludes_its_sibling(
    db_session, matter_with_users
):
    """Federal-shaped body: `(a)` subsection > `(1)` paragraph > `(A)`/`(B)`
    sibling subparagraphs, both nested under the SAME subsection and
    paragraph -- differing ONLY at the subparagraph level. A
    `scope_unit_kind='upper_alpha'` declaration must link the `(A)` mention
    and exclude the `(B)` mention, through the REAL `run_definition_linking`
    path -- not merely at the unit level."""
    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.models.assertion import Assertion

    def _extract(article_body, ctx):
        pattern = re.compile(
            r'"([^"]+)" governs only within subparagraph A of paragraph one '
            r"of this section, and means (.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="A",
                scope_unit_kind="upper_alpha",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    term = "Subparagraph widget"
    wiki_text = (
        f'@ 40. Federal shaped subparagraph scope article\n'
        f'"{term}" governs only within subparagraph A of paragraph one of '
        f"this section, and means a specially restricted item.\n"
        f"(a) Opening subsection of this section.\n"
        f"(1) Paragraph one under subsection a.\n"
        f"(B) A {term} is mentioned here, inside subparagraph B -- a "
        f"sibling at the same depth, out of scope.\n"
        f"(A) A {term} is mentioned here too, inside subparagraph A -- the "
        f"mention actually in scope.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test Subparagraph Level Scope Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a scope_unit_kind='upper_alpha' definition must link AT LEAST the "
        f"mention inside its own subparagraph (A). created_assertions="
        f"{result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, (
        "expected exactly ONE USES_DEFINITION assertion (dedup key has no "
        f"char_offset component). Got {uses_edges!r}"
    )

    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], f"expected a non-empty unit path; got {paths!r}"
    resolved_path = paths[0]
    assert len(resolved_path) >= 3, (
        f"expected the genuine 3-level (a)(1)(A) nesting; got {resolved_path!r}"
    )
    assert resolved_path[2].value == "A", (
        "the surviving assertion's own recorded mention position must be "
        "anchored at subparagraph 'A' -- the ONLY in-scope sibling. If "
        "this resolves to 'B' (which appears FIRST in the fixture's own "
        "text), containment is over-inclusive at the subparagraph level -- "
        f"it let the out-of-scope sibling win instead. Got "
        f"resolved_path={resolved_path!r}"
    )


def test_i10_live_bare_stamp_backward_compat_on_a_digit_outermost_body_links_only_its_own_subsection(
    db_session, matter_with_users
):
    """Closes the exact gap this sprint's own manager report names: the
    prior sprint's C1 live proof
    (`test_a_subsection_scoped_definition_links_a_mention_inside_its_own_subsection_live`,
    `test_definition_links_pipeline_scope_seam.py`) used ONE marker shape
    (bare outermost `lower_alpha`) and that single-shape proof was
    generalized to "subsection containment works" for every shape. This
    test proves the SAME bare, no-`scope_unit_kind`, backward-compatible
    stamp on a DIGIT-outermost body (Oregon's real convention, not
    synthetic) -- through the full live `run_definition_linking` path, not
    merely the unit-level check in the companion file.

    The out-of-scope mention (subsection `(2)`) is placed FIRST in the
    fixture's own text, same discriminating discipline as the existing C1
    live tests -- but on THIS shape it produces an even blunter live
    failure than "the wrong mention wins the dedup race": whichever digit
    marker is textually FIRST becomes the permanent, mis-kinded `sub` step
    occupying `mention_path[0]` for the rest of the document (I11's own
    defect), so `mention_path[0].value` is `'2'` at BOTH offsets -- never
    `'1'`, even inside the genuinely in-scope `(1)` mention. Today this
    produces ZERO `USES_DEFINITION` assertions, not merely a mis-attributed
    one -- verified directly (this Planner ran this exact scenario against
    the live code before pinning it)."""
    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.models.assertion import Assertion

    def _extract(article_body, ctx):
        pattern = re.compile(
            r'"([^"]+)" applies only within subsection one of this section, '
            r"and means (.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="1",
                # Deliberately NO scope_unit_kind -- the backward-compat,
                # omitted-kind, outermost-comparison fallback path.
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    term = "Digit outermost widget"
    wiki_text = (
        f'@ 41. Digit outermost shaped article\n'
        f'"{term}" applies only within subsection one of this section, '
        f"and means a specially numbered item.\n"
        f"(2) A {term} is mentioned here, in subsection two -- a sibling, "
        f"out of scope.\n"
        f"(1) A {term} is mentioned here, in subsection one -- the "
        f"mention actually in scope.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test Digit Outermost Backward-Compat Statute",
        wiki_text=wiki_text,
        jurisdiction="US-OR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a bare, no-scope_unit_kind subsection-scoped definition on a "
        "digit-outermost body must link AT LEAST the mention inside its "
        f"own subsection (1). created_assertions={result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, (
        f"expected exactly ONE USES_DEFINITION assertion. Got {uses_edges!r}"
    )

    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], f"expected a non-empty unit path; got {paths!r}"
    resolved_path = paths[0]
    assert resolved_path[0].value == "1", (
        "the surviving assertion's own recorded mention position must be "
        "anchored at subsection '1' -- the ONLY in-scope sibling. If this "
        "resolves to '2' (which appears FIRST in the fixture's own text), "
        "containment is over-inclusive on this digit-outermost shape -- "
        "exactly the failure mode this Planner's report documents as "
        f"live TODAY, purely from I11's own resolver defect. Got "
        f"resolved_path={resolved_path!r}"
    )
