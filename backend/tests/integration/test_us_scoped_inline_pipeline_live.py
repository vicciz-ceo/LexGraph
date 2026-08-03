"""Sprint 2026-08-04-defs-us-scoped-inline (Planner, D5, target 2: pipeline
live path). Ruling S-R1: this target is chosen because it proves BEHAVIOR
through the real production entry point (`run_definition_linking`,
`pipeline.py:311`), not an API surface core's still-unpublished `## Seam
spec` could invalidate -- once core merges and the Developer wires the new
`app.definition_links.rules.us_scoped_inline` module into `pipeline.py`'s
`else:` branch (Phase B), these tests go GREEN without being rewritten.

RED TODAY, and legitimately so: `pipeline.py`'s `else:` branch (pipeline.py
:436-442) calls the Hebrew-only `extract_local_definitions`/
`extract_adhoc_definitions` (extract.py:28-33) for EVERY profile including
US, so a real US "As used in this section/chapter..." article yields ZERO
`DefinitionCandidate`s today (independently re-verified live by the
Planner, matching the manager's architecture read in the sprint log). Every
assertion below fails against the CURRENT, unmodified pipeline -- an
assertion failure, not an import error, since `run_definition_linking`
itself already exists; only its Stage-2 candidate list is empty for this
family.

Gate U2 requires proof in BOTH directions: an in-scope mention LINKS via a
`USES_DEFINITION` assertion, and an out-of-scope mention does NOT. Two
scope units are proven live-path here -- "local" (`this section`,
`matcher._in_scope`'s `article.number == definition.source_article_number`
branch) and "chapter" (`this chapter`, the `article.chapter ==
definition.source_chapter` branch) -- the only two units today's
`matcher._in_scope` (matcher.py:104-110) actually enforces (see the sprint
log's D3 section for the full scope-unit gap table and the coordination ask
to core for the rest).

Drives the real `ingest_us_statute_rows` -> `run_definition_linking`
entrypoints, following the exact pattern already established in
`test_qa_regression_us_state_law.py`'s live-path tests. The chapter-scope
test's "in-scope"/"out-of-scope" SIBLING articles are constructed rows
(same convention as `test_definition_links_pipeline_jurisdiction_stamping
.py`'s "Minimal marker-format body ... this test only cares about the
STAMPED jurisdiction" sibling-document row, and as
`test_qa_regression_us_state_law.py`'s collision-probe rows that copy+modify
real row fields for a deterministic scenario) -- the DEFINING row itself
(row 0 in every test below) is always the real, unmodified, vendored corpus
row.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)


def _row(act_id: str) -> dict:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == act_id)


def _clean(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def test_a_real_scoped_inline_definition_is_captured_with_the_correct_scope(
    db_session, matter_with_users
):
    """Smoke test: `STATE_UT_T61_S61_1_18.8` ("For purposes of this
    section, "concurrence" means...") must be captured at all, with
    `Definition.scope == "local"` persisted -- today it captures nothing
    (the else-branch's Hebrew-only extractors return []`)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row("STATE_UT_T61_S61_1_18.8")

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Utah Code (scoped-inline live-path smoke test)",
        rows=[_clean(row)],
        jurisdiction="US-UT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    concurrence_defs = [d for d in result["created_definitions"] if "concurrence" in d["terms"]]
    assert concurrence_defs, (
        "the real production pipeline recognized ZERO definitions in a real Utah "
        "'For purposes of this section, \"concurrence\" means...' article -- "
        f"got {result['created_definitions']!r} definitions from "
        f"{result['created_assertions']!r} assertions"
    )
    definition_row = db_session.get(Definition, concurrence_defs[0]["id"])
    assert definition_row.scope == "local"


def test_local_scope_links_a_mention_within_the_same_article_only(db_session, matter_with_users):
    """Both directions of gate U2 for `scope="local"` ("this section"):
    - IN-scope: `STATE_UT_T61_S61_1_18.8`'s OWN body reuses "concurrence"
      again later, outside its defining entry ("(2) ... if a provision of
      this chapter requires concurrence between..." -- real, unmodified
      text) -- this mention must get a `USES_DEFINITION` edge from the
      SAME article that defines the term.
    - OUT-of-scope: a sibling article (different section number, same
      document) that also mentions "concurrence" in ordinary prose must
      NOT get any `USES_DEFINITION` edge -- `matcher._in_scope`'s "local"
      branch only matches `article.number == definition
      .source_article_number`, so a DIFFERENT article's mention is
      structurally excluded regardless of content.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion
    from app.models.definition import Definition

    m = matter_with_users
    defining_row = _row("STATE_UT_T61_S61_1_18.8")
    assert defining_row["text"].count("concurrence") >= 2, (
        "fixture must reproduce the real row's own in-article reuse of the term"
    )

    sibling_row = dict(defining_row)
    sibling_row["act_id"] = "STATE_UT_T61_S61_1_18.9_SYNTHETIC_SIBLING"
    sibling_row["section_number"] = "61-1-18.9"
    sibling_row["section_title"] = "§ 61-1-18.9. Reporting requirements (synthetic sibling for scope-isolation proof)."
    sibling_row["text"] = (
        "The division shall obtain concurrence from the commission before filing "
        "the annual report required under this part."
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Utah Code (local-scope isolation test)",
        rows=[_clean(defining_row), sibling_row],
        jurisdiction="US-UT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    concurrence_defs = [d for d in result["created_definitions"] if "concurrence" in d["terms"]]
    assert concurrence_defs, "the defining article's own term was never captured at all"
    definition_id = concurrence_defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "local"

    uses_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION" and a["object_entity_id"] == definition_id
    ]
    assert uses_edges, "no USES_DEFINITION edge was created for the in-article reuse"

    linked_article_ids = {a["subject_entity_id"] for a in uses_edges}
    assert linked_article_ids == {
        definition_row.article_id
    }, (
        "a local-scoped definition must only ever link its OWN defining "
        f"article, but linked {linked_article_ids!r} while the definition's "
        f"owning article is {definition_row.article_id!r} -- the synthetic "
        "sibling article's mention of the same term leaked across scope"
    )


def test_chapter_scope_links_a_sibling_article_in_the_same_chapter_but_not_a_different_one(
    db_session, matter_with_users
):
    """Both directions of gate U2 for `scope="chapter"` ("this chapter"):
    `STATE_VT_T3_C45_S2291` (real chapter `"45"`) defines "State
    facilities" via `"“State facilities,” when used in this chapter,
    shall mean..."`. Two synthetic sibling articles in the SAME document:
    one sharing chapter `"45"` (must link), one with a DIFFERENT chapter
    `"99"` (must not) -- proving `matcher._in_scope`'s `article.chapter ==
    definition.source_chapter` branch is reachable end-to-end for a real
    US chapter-scoped definition, which it is not today (zero candidates
    are ever produced for this family, so this branch is never even
    exercised for English text)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    defining_row = _row("STATE_VT_T3_C45_S2291")
    assert defining_row["chapter"] == "45"

    same_chapter_sibling = dict(defining_row)
    same_chapter_sibling["act_id"] = "STATE_VT_T3_C45_SYNTHETIC_SAME_CHAPTER"
    same_chapter_sibling["section_number"] = "2292"
    same_chapter_sibling["section_title"] = "§ 2292. Reporting (synthetic same-chapter sibling)."
    same_chapter_sibling["chapter"] = "45"
    same_chapter_sibling["text"] = (
        "The Commissioner shall include State facilities in the annual energy report."
    )

    different_chapter_sibling = dict(defining_row)
    different_chapter_sibling["act_id"] = "STATE_VT_T3_C99_SYNTHETIC_DIFFERENT_CHAPTER"
    different_chapter_sibling["section_number"] = "9901"
    different_chapter_sibling["section_title"] = "§ 9901. Unrelated provision (synthetic different-chapter sibling)."
    different_chapter_sibling["chapter"] = "99"
    different_chapter_sibling["text"] = (
        "For purposes of an unrelated program, State facilities must be inspected annually."
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Vermont Statutes (chapter-scope isolation test)",
        rows=[_clean(defining_row), same_chapter_sibling, different_chapter_sibling],
        jurisdiction="US-VT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    facility_defs = [d for d in result["created_definitions"] if "State facilities" in d["terms"]]
    assert facility_defs, "the real chapter-scoped 'State facilities' definition was never captured"
    definition_id = facility_defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "chapter"

    uses_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION" and a["object_entity_id"] == definition_id
    ]
    linked_article_ids = {a["subject_entity_id"] for a in uses_edges}

    from app.models.article import Article

    same_chapter_article = (
        db_session.query(Article)
        .filter(Article.matter_id == m["matter_id"], Article.number == "2292")
        .one()
    )
    different_chapter_article = (
        db_session.query(Article)
        .filter(Article.matter_id == m["matter_id"], Article.number == "9901")
        .one()
    )

    assert same_chapter_article.id in linked_article_ids, (
        "a same-chapter mention of a chapter-scoped term must LINK -- it did not"
    )
    assert different_chapter_article.id not in linked_article_ids, (
        "a different-chapter mention of a chapter-scoped term must NOT link -- it did"
    )


def test_a_scope_unit_not_yet_enforced_by_matcher_is_still_stamped_faithfully(
    db_session, matter_with_users
):
    """D3 (scope-unit gap): `STATE_ME_T38_C3_S464` defines "designated
    use" via `"For the purposes of this subsection..."` -- `"subsection"`
    is NOT one of the two units `matcher._in_scope` enforces today (only
    `"local"`/`"chapter"` are), so this candidate's scope is stamped
    faithfully as `"subsection"` (never silently coerced to `"local"`,
    `"chapter"`, or `"law-wide"`) even though core has not yet added
    `Article`-level subsection granularity to enforce it. This is the
    exact, documented, escalated gap D3 hands to core -- this test proves
    the STAMPING half of that gap (the ENFORCEMENT half is core's, and out
    of scope for `matcher.py`, which ruling S-R2 forbids this sprint from
    editing)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row("STATE_ME_T38_C3_S464")

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Maine Revised Statutes (subsection-scope stamping test)",
        rows=[_clean(row)],
        jurisdiction="US-ME",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    du_defs = [d for d in result["created_definitions"] if "designated use" in d["terms"]]
    assert du_defs, "the real Maine subsection-scoped definition was never captured"
    definition_row = db_session.get(Definition, du_defs[0]["id"])
    assert definition_row.scope == "subsection"
