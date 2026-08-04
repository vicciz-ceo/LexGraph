"""QA cycle 1 (sprint 2026-08-04-defs-core-dispatch) -- INDEPENDENT gate B
probes, written by QA (not the Planner/Developer), through the REAL live
`run_definition_linking` path.

Purpose: the QA brief's gate B requires the containment matrix to be proven
"at the matcher.definition_covers_mention level AND at least twice through
the full live run_definition_linking path" across the three real emitted
marker shapes (Oregon digit-outermost / federal lower_alpha-outermost / Ohio
upper_alpha-outermost). The existing sprint test suite already live-proves
two scenarios (federal upper_alpha-level, Oregon bare/backward-compat) in
`test_definition_links_pipeline_cd_i10_scope_level_semantics_live.py` --
this file does NOT reuse those; it adds two INDEPENDENT scenarios QA
authored itself, deliberately choosing shapes/levels those tests do not
already cover:

1. Ohio's real upper_alpha-outermost convention (untested at the live-path
   level anywhere in the shipped suite) -- a `scope_unit_kind="digit"`
   (paragraph-level) declaration, proven to link a mention nested three
   levels deep and exclude a sibling paragraph.
2. Federal's real lower_alpha-outermost convention, at the DEEPEST
   (`lower_roman`) level -- discriminating two `(ii)`/`(iii)` siblings
   nested FOUR levels deep, which no existing live test reaches (the
   shipped federal live test stops at the upper_alpha/3rd level).

   NOTE (QA finding, independent of I10/I11): the sibling pair here is
   deliberately `(ii)`/`(iii)` -- both multi-character roman labels -- NOT
   `(i)`/`(ii)`. QA's first attempt used `(i)`/`(ii)` and found
   `resolve_unit_path`'s ancestor-fallback loop (the "does this token match
   an already-open ancestor's KIND" search in `resolve_unit_path`,
   `us_profile.py`) checks ancestors OUTERMOST-first and stops at the FIRST
   shape match. Every SINGLE-character roman numeral (`i`, `v`, `x`, `l`,
   `c`, `d`, `m` / their uppercase forms) is shape-ambiguous with
   `lower_alpha`/`upper_alpha` (`_marker_matches_kind` for both requires
   only `len(token) == 1`), so replacing an open multi-character roman
   sibling (e.g. `iv`) with a single-character one (`v`) incorrectly matches
   the OUTERMOST `lower_alpha` ancestor first and collapses the ENTIRE
   stack back to length 1 -- reproduced directly, see this file's sibling
   report. This is a REAL, separate defect from D1/D2 in the QA brief, not
   exercised by this test (which uses two-character roman labels to isolate
   the I10/I11 mechanism this file exists to prove) -- reported to the
   sprint manager as an independent finding, not silently routed around.

Same directional-proof discipline as the existing C1/I10 live tests: the
out-of-scope mention is placed textually BEFORE the in-scope one, so an
over-inclusive containment bug would let the wrong mention win
`_create_assertion`'s no-char-offset dedup race, and `get_mention_unit_paths`
on the surviving assertion catches that directly.
"""

from __future__ import annotations

import re


def test_qa_live_ohio_upper_alpha_outermost_digit_level_scope_links_only_its_own_paragraph(
    db_session, matter_with_users
):
    """Ohio's real convention: (A)/(B) upper_alpha-outermost > (1)/(2)
    digit > (a)/(b) lower_alpha. A `scope_unit_kind='digit'` declaration
    must link a mention nested inside paragraph (B)(2)(a) and exclude a
    sibling mention inside paragraph (B)(1) -- through the full live
    `run_definition_linking` path, on a shape no shipped live test
    exercises."""
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
            r'"([^"]+)" governs only within paragraph two of division B of '
            r"this section, and means (.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="2",
                scope_unit_kind="digit",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-OH",), extract=_extract)
    )

    m = matter_with_users
    term = "Game protector credential"
    wiki_text = (
        f'@ 132. Ohio shaped upper_alpha outermost article\n'
        f'"{term}" governs only within paragraph two of division B of this '
        f"section, and means a specially regulated credential.\n"
        f"(A) Opening division of this section.\n"
        f"(B)(1) A {term} is mentioned here, inside division B paragraph "
        f"one -- a sibling paragraph, out of scope.\n"
        f"(2)(a) A {term} is mentioned here too, inside division B "
        f"paragraph two -- the mention actually in scope.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="QA Test Ohio Upper-Alpha-Outermost Digit-Level Scope Statute",
        wiki_text=wiki_text,
        jurisdiction="US-OH",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a scope_unit_kind='digit' definition on Ohio's real "
        "upper_alpha-outermost shape must link AT LEAST the mention inside "
        f"its own paragraph (B)(2). created_assertions={result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, f"expected exactly ONE USES_DEFINITION assertion. Got {uses_edges!r}"

    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], f"expected a non-empty unit path; got {paths!r}"
    resolved_path = paths[0]
    assert len(resolved_path) >= 2, f"expected the genuine (B)(2)(a) nesting; got {resolved_path!r}"
    assert resolved_path[0].kind == "upper_alpha" and resolved_path[0].value == "B", (
        f"expected the outermost step to be upper_alpha='B' (Ohio's real "
        f"outermost convention); got {resolved_path!r}"
    )
    assert resolved_path[1].kind == "digit" and resolved_path[1].value == "2", (
        "the surviving assertion's own recorded mention position must be "
        "anchored at paragraph digit='2' -- the ONLY in-scope sibling. If "
        "this resolves to '1' (which appears FIRST in the fixture's own "
        "text), containment is over-inclusive at the digit level on "
        f"Ohio's shape. Got resolved_path={resolved_path!r}"
    )


def test_qa_live_federal_deep_lower_roman_level_scope_discriminates_four_level_siblings(
    db_session, matter_with_users
):
    """Federal's real convention, FOUR levels deep: (a) subsection > (2)
    paragraph > (B) subparagraph > (i)/(ii) clause. A
    `scope_unit_kind='lower_roman'` declaration must link the (a)(2)(B)(i)
    mention and exclude its (a)(2)(B)(ii) sibling -- proving the mechanism
    reaches genuine 4-level depth on the LIVE path, not merely the
    3-level (subparagraph) depth the shipped live suite already covers."""
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
            r'"([^"]+)" governs only within clause \(ii\) of paragraph two '
            r"of subsection a of this section, and means (.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="ii",
                scope_unit_kind="lower_roman",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-FED",), extract=_extract)
    )

    m = matter_with_users
    term = "Named plaintiff recovery"
    wiki_text = (
        f'@ 179. Federal shaped four level clause scope article\n'
        f'"{term}" governs only within clause (ii) of paragraph two of '
        f"subsection a of this section, and means a specially computed "
        f"amount.\n"
        f"(a) Liability established for this section.\n"
        f"(2) Punitive damages under this subsection.\n"
        f"(B) Class actions under this paragraph.\n"
        f"(iii) A {term} is mentioned here, inside clause (iii) -- a "
        f"sibling clause, out of scope.\n"
        f"(ii) A {term} is mentioned here too, inside clause (ii) -- the "
        f"mention actually in scope.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="QA Test Federal Deep Lower-Roman-Level Scope Statute",
        wiki_text=wiki_text,
        jurisdiction="US-FED",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a scope_unit_kind='lower_roman' definition on federal's real "
        "shape must link AT LEAST the mention inside its own clause "
        f"(a)(2)(B)(i). created_assertions={result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, f"expected exactly ONE USES_DEFINITION assertion. Got {uses_edges!r}"

    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], f"expected a non-empty unit path; got {paths!r}"
    resolved_path = paths[0]
    assert len(resolved_path) >= 4, (
        f"expected genuine 4-level (a)(2)(B)(i) nesting; got {resolved_path!r}"
    )
    kinds = tuple(step.kind for step in resolved_path[:4])
    values = tuple(step.value for step in resolved_path[:4])
    assert kinds == ("lower_alpha", "digit", "upper_alpha", "lower_roman"), kinds
    assert values[:3] == ("a", "2", "B"), values
    assert values[3] == "ii", (
        "the surviving assertion's own recorded mention position must be "
        "anchored at clause 'ii' -- the ONLY in-scope sibling. If this "
        "resolves to 'iii' (which appears FIRST in the fixture's own "
        "text), containment is over-inclusive at the deepest level. Got "
        f"resolved_path={resolved_path!r}"
    )
