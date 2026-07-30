"""QA regression coverage — sprint 2026-07-30-deterministic-assertions,
item L1 (ruling R3: deterministic definition-linking assertions are
"accepted", never "proposed"; "proposed" stays reserved for model_suggested/
AI-deduced output awaiting human rating).

Independent QA pass (separate agent from the Developer of commit 6a0c0f5,
`backend/app/definition_links/pipeline.py`'s `_STATUS = "accepted"`).

Gap this closes: every existing test that checks the new status value reads
it off ONE of two places, and never across every assertion sub-type in a
single run:

- `test_definition_links_pipeline_live.py::test_run_definition_linking_creates_a_definition_and_links_using_articles`
  asserts `status == "accepted"` only for `USES_DEFINITION` edges.
- `test_definition_links_pipeline_live.py::test_run_definition_linking_preserves_unresolved_cross_law_derivation_with_null_target`
  and `..._resolves_a_cross_law_derivation_to_a_known_document` both create
  `DERIVES_FROM_LAW` edges (unresolved and resolved respectively) but NEITHER
  asserts anything about `status` at all.
- `test_definition_links_cli.py::test_link_definitions_cli_creates_accepted_assertions_from_ingested_articles`
  DOES assert `status == "accepted"` across both assertion types via the API
  listing, but only against a single-document matter (`חוק להגנת רכוש
  מופקד.wiki`) that never exercises a RESOLVED cross-law derivation — that
  fixture's only `DERIVES_FROM_LAW` edge is the unresolved
  "האפוטרופוס הכללי" case.

So a resolved `DERIVES_FROM_LAW` edge's `status` column has never been
checked anywhere, by any test in this repo, before or after ruling R3.

This test ingests all three vendored laws needed to hit all three live
sub-cases (`USES_DEFINITION`, `DERIVES_FROM_LAW` unresolved, `DERIVES_FROM_LAW`
resolved) in ONE matter/ONE pipeline run, then reads the persisted `Assertion`
rows straight from the database via the ORM (not the pipeline's returned
summary dict) and pins both directions explicitly: `status == "accepted"`
AND `status != "proposed"`, for every created assertion, regardless of
sub-type.
"""

from __future__ import annotations

import pathlib

from app.models.assertion import Assertion

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_definition_links_pipeline_never_persists_proposed_status_across_all_edge_subtypes(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users

    # USES_DEFINITION + an UNRESOLVED DERIVES_FROM_LAW edge ("האפוטרופוס
    # הכללי" derives from a law never ingested into this matter).
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )
    # A RESOLVED DERIVES_FROM_LAW edge: חוק הגנת הפרטיות's definitions
    # derive from חוק המחשבים, which IS ingested into this same matter.
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הגנת הפרטיות, התשמ"א-1981',
        wiki_text=_read("חוק הגנת הפרטיות_excerpt.wiki"),
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק המחשבים, התשנ"ה-1995',
        wiki_text=_read("חוק המחשבים_stub.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    created = result["created_assertions"]
    assert len(created) > 0

    # Sanity: this run really does exercise all three live sub-cases --
    # otherwise the assertions below would pass vacuously.
    by_type: dict[str, list[dict]] = {}
    for item in created:
        by_type.setdefault(item["assertion_type"], []).append(item)
    assert by_type.get("USES_DEFINITION"), "expected at least one USES_DEFINITION edge"
    derives = by_type.get("DERIVES_FROM_LAW", [])
    assert len(derives) >= 2, "expected both a resolved and an unresolved DERIVES_FROM_LAW edge"

    rows = [db_session.get(Assertion, item["id"]) for item in created]
    resolved_rows = [r for r in rows if r.assertion_type == "DERIVES_FROM_LAW" and r.object_entity_id is not None]
    unresolved_rows = [r for r in rows if r.assertion_type == "DERIVES_FROM_LAW" and r.object_entity_id is None]
    assert resolved_rows, "expected at least one RESOLVED DERIVES_FROM_LAW row"
    assert unresolved_rows, "expected at least one UNRESOLVED DERIVES_FROM_LAW row"

    # The actual pin (ruling R3): read straight off the persisted DB row
    # (not the pipeline's summary dict) for every created assertion,
    # regardless of sub-type -- "accepted", and explicitly never "proposed".
    for row in rows:
        assert row.origin == "system_generated"
        assert row.status == "accepted"
        assert row.status != "proposed"
        assert row.reviewed_by is None
        assert row.reviewed_at is None
