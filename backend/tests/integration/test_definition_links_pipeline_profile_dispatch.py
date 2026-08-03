"""RED tests for the pipeline's jurisdiction-profile dispatch wiring
(sprint 2026-08-02-us-state-law, director decision #1, gate G1) --
the live call-site proof that `app.definition_links.pipeline` actually
uses the new `profiles` registry (`test_definition_links_profiles.py`
covers the registry/profile objects themselves in isolation).

Design call this test pins (foundational plumbing shared with the
jurisdiction-STAMPING item, G5 -- recorded in the sprint contract's
parallelization section as a G1-before-G5 sequencing dependency, not
something G5 re-derives):

  - `Document` gains a `jurisdiction` column, NOT NULL, defaulting to
    `"IL"` (recon dossier §2: today NO document/article/definition model
    carries a jurisdiction field at all -- only `Assertion` does, and the
    pipeline never populates even that one, per dossier §6's last row,
    `pipeline.py:233`).
  - `ingest_wiki_law(session, *, repository_id, matter_id, title,
    wiki_text, jurisdiction="IL")` gains a NEW keyword-only parameter with
    an `"IL"` DEFAULT -- deliberately backward compatible: ~20 existing
    Hebrew integration tests call `ingest_wiki_law(...)` without this
    kwarg at all (grep-verified by the Planner across
    `backend/tests/integration/test_definition_links_*.py`,
    `test_qa_regression_*.py`, `test_assertion_standing_api.py`) and per
    ruling R2 must not be edited to add it. A default of `"IL"` (not a
    required kwarg) is the ONLY signature change that satisfies both "the
    pipeline must know a document's jurisdiction" and "zero Hebrew test
    edits".
  - `pipeline.py` Stage 2 (`is_definitions_heading` dispatch) resolves
    `get_profile(article's owning Document.jurisdiction)` PER DOCUMENT
    (not once per whole matter/pipeline run) -- a matter may hold
    documents from more than one jurisdiction side by side (e.g. an IL law
    and a US law being cross-referenced in the same matter), so dispatch
    must not be a single matter-wide setting.

Live-path requirement: drives the real `ingest_wiki_law` +
`run_definition_linking` entrypoints against a REAL Hebrew fixture file
(same fixture `test_definition_links_pipeline_live.py` already uses) --
this is a regression-fidelity proof, not a new synthetic scenario.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_ingest_wiki_law_defaults_jurisdiction_to_il_for_zero_edit_hebrew_call_sites(
    db_session, matter_with_users
):
    """Calling `ingest_wiki_law` exactly the way every existing Hebrew test
    already does (no `jurisdiction` kwarg at all) must keep working AND the
    persisted Document must default to `"IL"` -- proves the new parameter
    is additive, not a breaking signature change."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.models.document import Document

    m = matter_with_users
    result = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )
    document = db_session.get(Document, result["document_id"])
    assert document.jurisdiction == "IL"


def test_ingest_wiki_law_accepts_an_explicit_jurisdiction(db_session, matter_with_users):
    from app.definition_links.ingest import ingest_wiki_law
    from app.models.document import Document

    m = matter_with_users
    result = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Title 5 Chapter 7 (test)",
        wiki_text="",
        jurisdiction="US-DE",
    )
    document = db_session.get(Document, result["document_id"])
    assert document.jurisdiction == "US-DE"


def test_pipeline_produces_identical_hebrew_output_through_the_profile_dispatch_path(
    db_session, matter_with_users
):
    """Regression-fidelity proof (G1: "same definitions found, same links
    created, same cross-law references detected, on the same fixtures"):
    every number pinned here is IDENTICAL to the un-refactored pipeline's
    already-passing assertions in
    `test_definition_links_pipeline_live.py::
    test_run_definition_linking_creates_a_definition_and_links_using_articles`
    and `::test_run_definition_linking_preserves_unresolved_cross_law_derivation_with_null_target`
    -- if the profile-dispatch refactor changes ANY of these numbers, it
    has broken Hebrew behaviour, which ruling R2 forbids."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
        jurisdiction="IL",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    definitions = result["created_definitions"]
    asset_definitions = [d for d in definitions if "נכס" in d["terms"]]
    assert len(asset_definitions) == 1

    uses_edges = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    assert len(uses_edges) >= 1

    derives_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "DERIVES_FROM_LAW"
    ]
    assert len(derives_edges) == 1
    assert "האפוטרופוס הכללי" in derives_edges[0]["proposition"]
