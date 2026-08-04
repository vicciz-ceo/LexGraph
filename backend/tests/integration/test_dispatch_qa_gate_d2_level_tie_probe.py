"""QA cycle 1 (sprint 2026-08-04-defs-core-dispatch), gate D2 -- INDEPENDENT
live-path verification of the manager's finding #2: two `scope="subsection"`
definitions declared at DIFFERENT LEVELS (one at the outermost step, one
narrower via `scope_unit_kind`) both cover the same mention and both survive
the "narrowest governs" precedence filter, because `matcher.scope_rank`
only inspects the SCOPE KIND STRING ("subsection") -- it has no notion of
`scope_unit_kind`'s own depth, so two subsection-scoped definitions always
tie at `rank=0` regardless of how deep their declared level actually is.

This is NOT a synthetic-only claim -- this test drives the REAL
`run_definition_linking` path and inspects the REAL persisted `Assertion`
rows, proving TWO USES_DEFINITION assertions are genuinely created for the
SAME mention, pointing at TWO DIFFERENT `Definition` rows -- not merely
that `definition_covers_mention` returns True twice in isolation."""

from __future__ import annotations

import re


def test_qa_live_two_subsection_definitions_at_different_levels_both_link_the_same_mention(
    db_session, matter_with_users
):
    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )

    code = "US-MS"  # not used by any other test in this sprint's dispatch suite

    # Housed in TWO DIFFERENT owning articles (mirroring the established
    # M10 tie-test pattern, test_two_same_rank_local_scoped_definitions_
    # that_tie_both_get_a_uses_definition_assertion_live in
    # test_definition_links_pipeline_scope_seam.py): pipeline.py's
    # Definition-row dedup key is (article_id, sorted(terms)) -- if BOTH
    # candidates were extracted from the SAME owning article, they would
    # collapse into ONE Definition row regardless of their different scope/
    # scope_unit_kind, which would silently defeat this probe (QA's own
    # first draft of this test hit exactly that and had to be corrected).
    # Housing them in separate articles, both targeting the SAME article
    # (60, via source_article_number) where the mention actually lives,
    # produces two genuinely DISTINCT Definition rows -- the real shape a
    # family panel would hit if two DIFFERENT rules stamp two DIFFERENT
    # levels of the same term.
    def _extract_broad(article_body, ctx):
        m = re.search(
            r'"([^"]+)" governs broadly within subsection a of section 60, '
            r"and means (.*?)(?=\.\s|$)",
            article_body,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return []
        return [
            DefinitionCandidate(
                terms=(m.group(1).strip(),),
                definition_text=m.group(2).strip(),
                scope="subsection",
                source_article_number="60",
                scope_value="a",
            )
        ]

    def _extract_narrow(article_body, ctx):
        m = re.search(
            r'"([^"]+)" governs narrowly within subparagraph A of section '
            r"60, and means (.*?)(?=\.\s|$)",
            article_body,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return []
        return [
            DefinitionCandidate(
                terms=(m.group(1).strip(),),
                definition_text=m.group(2).strip(),
                scope="subsection",
                source_article_number="60",
                scope_value="A",
                scope_unit_kind="upper_alpha",
            )
        ]

    register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=(code,), extract=_extract_broad))
    register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=(code,), extract=_extract_narrow))

    m = matter_with_users
    term = "Level tie widget"
    wiki_text = (
        f"@ 50. Broad rule housing article\n"
        f'"{term}" governs broadly within subsection a of section 60, and '
        f"means a broadly scoped item.\n"
        f"@ 51. Narrow rule housing article\n"
        f'"{term}" governs narrowly within subparagraph A of section 60, '
        f"and means a narrowly scoped item.\n"
        f"@ 60. Target section\n"
        f"(a) Opening subsection.\n"
        f"(1) Opening paragraph.\n"
        f"(A) Opening subparagraph. A {term} is mentioned here, nested "
        f"three levels deep.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="QA Test Level Tie Statute",
        wiki_text=wiki_text,
        jurisdiction=code,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    from app.models.assertion import Assertion

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    object_ids = {
        db_session.get(Assertion, a["id"]).object_entity_id for a in uses_edges
    }

    assert len(result["created_definitions"]) == 2, (
        f"expected both the broad and narrow candidates to persist as "
        f"separate Definition rows. Got {result['created_definitions']!r}"
    )
    assert len(uses_edges) == 2 and len(object_ids) == 2, (
        "QA finding D2 (independently reproduced): a mention nested inside "
        "(a)(1)(A) is covered by BOTH the outermost-level ('a') and the "
        "upper_alpha-level ('A') subsection-scoped definitions, and BOTH "
        "get a USES_DEFINITION assertion -- because matcher.scope_rank only "
        "inspects the scope KIND string ('subsection'), never the declared "
        "scope_unit_kind's own depth, so the two candidates tie at rank=0 "
        "and M10's tie-survival rule keeps both. If this now returns "
        "exactly ONE edge, the ranking mechanism has changed to account "
        f"for scope_unit_kind depth. Got uses_edges={uses_edges!r}"
    )
