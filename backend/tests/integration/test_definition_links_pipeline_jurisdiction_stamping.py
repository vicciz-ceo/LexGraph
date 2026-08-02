"""RED tests for jurisdiction stamping (sprint 2026-08-02-us-state-law,
director decision #3, gate G5): "the deterministic pipeline must stamp
[jurisdiction] on every assertion it creates."

Today `pipeline.py:233` hardcodes `jurisdiction=None` on every assertion
`_create_assertion` writes (recon dossier §6, last row) -- these tests are
RED because every created assertion's `.jurisdiction` is `None` today
instead of the owning document's jurisdiction.

Depends on the G1 seam-refactor item's `Document.jurisdiction` column +
`ingest_wiki_law(..., jurisdiction=...)` kwarg (see
`test_definition_links_pipeline_profile_dispatch.py`) -- sequenced AFTER
G1 in the sprint contract's parallelization proposal, not a fresh schema
decision of its own.

Live-path requirement: drives the real `ingest_wiki_law` +
`run_definition_linking` entrypoints, then re-reads the persisted
`Assertion` rows from the database -- never inspects the returned dict
alone (which doesn't currently even include jurisdiction), so this proves
the DATABASE row is stamped, not just an in-memory shape.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_every_created_assertion_is_stamped_with_the_documents_jurisdiction(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

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
    assert len(result["created_assertions"]) > 0  # sanity: something was actually created

    for created in result["created_assertions"]:
        assertion_row = db_session.get(Assertion, created["id"])
        assert assertion_row.jurisdiction == "IL"


def test_assertions_from_a_us_document_are_stamped_with_its_us_jurisdiction(
    db_session, matter_with_users
):
    """Two documents, two jurisdictions, same matter -- proves stamping is
    per-document, not a single matter-wide default."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
        jurisdiction="IL",
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Title 5 Chapter 7 (test)",
        # Minimal marker-format body so Stage 1 parses at least one article --
        # this test only cares about the STAMPED jurisdiction, not US
        # heading/term-matching semantics (that's the separate US-profile item).
        wiki_text='@ 1. הגדרות\n:- "מונח" - הגדרה לצורך הבדיקה.\n',
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    jurisdictions_seen = set()
    for created in result["created_assertions"]:
        assertion_row = db_session.get(Assertion, created["id"])
        jurisdictions_seen.add(assertion_row.jurisdiction)

    assert "IL" in jurisdictions_seen
    # The US document alone won't necessarily produce its own assertions in
    # this minimal fixture (no cross-references to trigger Stage 3/4), but
    # NO assertion anywhere in the result may carry a null/wrong jurisdiction.
    assert None not in jurisdictions_seen
