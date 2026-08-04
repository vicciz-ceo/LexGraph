"""Live-path RED integration tests for sprint 2026-08-04-defs-core-scope
(gates C1, C4, M8(a); seam spec `## Seam spec (published)` in the sprint
contract).

Unlike `test_definition_links_us_profile_definitions_section_end_to_end.py`
(profile-methods chained directly), every test here drives the REAL
production entry point, `run_definition_linking`, against a REAL
DB-backed matter -- the structural-wiring-gate requirement that a new
module/function/dispatcher branch has a live call-site test proving the
production path actually reaches it, not merely a unit test on the new
piece in isolation.
"""

from __future__ import annotations

import pathlib

from sqlalchemy import select

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- M8(a): a bare-`@`-marked section must not lose its definitions on the
# --- REAL `run_definition_linking` path (unit-level RED already pins the
# --- `parse_articles` gap directly; this proves it is not silently masked
# --- or recovered somewhere downstream in the full pipeline). -------------


def test_run_definition_linking_does_not_lose_a_definition_behind_a_bare_at_marker(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    wiki_text = (
        "@\n"
        "פרשנות\n"
        ':- "מונח יסודי" - הגדרה שאף פעם לא נקלטת בעולם האמיתי.\n'
        "@ 2. הוראה נוספת\n"
        "התוכן מזכיר מונח יסודי כאן.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק לדוגמה עם סימון @ חסר",
        wiki_text=wiki_text,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {tuple(d["terms"]) for d in result["created_definitions"]}
    assert ("מונח יסודי",) in created_terms, (
        "the bare-`@`-marked section's own definition ('מונח יסודי') must "
        "be captured by the real run_definition_linking path -- today it "
        "is silently unreachable because sections.parse_articles never "
        "attaches it to any Article at all (M8(a))."
    )


# --- C4: a rule module registered into `app.definition_links.rules` must
# --- be reachable through the REAL `run_definition_linking` path, not
# --- just importable/callable in isolation. -------------------------------


def test_a_registered_scope_trigger_rule_is_reached_by_the_real_pipeline(
    db_session, matter_with_users
):
    """C4's structural-wiring proof: register a throwaway English
    scope-trigger rule (mirroring the seam spec's own worked example) and
    confirm `run_definition_linking`, run over a REAL US-jurisdiction
    document, actually produces a `Definition` row from it -- proving the
    rule registry is consumed by the production path (`profile.
    extract_local_scope_definitions`), not merely constructible."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    # This import is expected to fail today (module doesn't exist) --
    # the RED signal for this test.
    from app.definition_links.rules.registry import (  # noqa: F401
        RuleContext,
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate

    def _extract(article_body, ctx):
        import re

        pattern = re.compile(
            r'As used in this section,\s*"([^"]+)"\s*means\s+(.*?)(?=\.\s|$)',
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="local",
                source_article_number=ctx.article_number,
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    wiki_text = (
        '@ 5. Ordinary provision\n'
        'As used in this section, "Local widget" means a widget sold '
        "only within city limits.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test US Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    rows = (
        db_session.execute(
            select(Definition).where(Definition.matter_id == m["matter_id"])
        )
        .scalars()
        .all()
    )
    assert any("Local widget" in row.terms for row in rows), (
        "a ScopeTriggerRule registered for 'US-*' must be reached by the "
        "REAL run_definition_linking path via profile."
        "extract_local_scope_definitions -- today no such method/registry "
        "exists, so this English scoped-inline definition is never "
        "captured for a US document (C2/C4)."
    )
