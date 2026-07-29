"""Sprint 2026-07-29-definition-links, item DL8 — definition-linker
persistence pipeline (rulings M2, M5, M7).

`app.definition_links.pipeline` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

Mirrors `app/enrich/pipeline.py::run_enrichment`'s shape and philosophy:
reads real `Article` rows already ingested for a matter (via
`app.definition_links.ingest.ingest_wiki_law`, DL7), runs them through the
deterministic Stage 2-5 extractor/matcher/derivation-detector, and writes
REAL `Definition` rows plus `Assertion` rows -- never mock objects, never a
model call.

Public API pinned:
- `run_definition_linking(session, *, matter_id, triggered_by_user_id) ->
  dict` returns `{"created_assertions": [...], "created_definitions": [...],
  "skipped_degraded_article_ids": [...]}`.
  - Each `created_assertions` item is `{"id", "assertion_type",
    "proposition", "status", "origin"}` (same shape as
    `run_enrichment`'s return value).
  - Each `created_definitions` item is `{"id", "terms", "scope"}` where
    `"terms"` is the list of defined term strings (Stage 2's multi-term
    case: membership-tested via `"term" in item["terms"]`, not equality).
  - `USES_DEFINITION` assertions: subject=Article, object=Definition,
    origin="system_generated", status="proposed", confidence >= 0.9
    (structural, ruling M2).
  - `DERIVES_FROM_LAW` assertions: subject=Definition, object=Document
    (target law) when resolved, or object_entity_type/id both `None` when
    unresolved (ruling M5) -- confidence is materially LOWER when
    unresolved than when resolved (M2's "structural >= 0.9 / prose-derived
    lower" tiering).
  - Idempotent: a re-run creates no additional assertions/definitions for
    unchanged input (mirrors `run_enrichment`'s idempotency contract).
  - `UnknownMatterError` (ValueError subclass) for a matter that doesn't
    exist, mirroring `app.enrich.pipeline.UnknownMatterError`.

Uses the vendored fixtures (ruling M3) via `ingest_wiki_law` -- no
placeholder text.
"""

from __future__ import annotations

import pathlib

import pytest

from tests.conftest import seed_article, seed_document, seed_source_span

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_run_definition_linking_creates_a_definition_and_links_using_articles(
    db_session, matter_with_users
):
    """חוק להגנת רכוש מופקד.wiki: term "נכס" is defined in §1 and used
    (bare or simply prefixed) in §2, §3, §7."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    definitions = result["created_definitions"]
    asset_definitions = [d for d in definitions if "נכס" in d["terms"]]
    assert len(asset_definitions) == 1

    uses_edges = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    assert len(uses_edges) >= 1
    assert all(a["origin"] == "system_generated" for a in uses_edges)
    assert all(a["status"] == "proposed" for a in uses_edges)


def test_run_definition_linking_preserves_unresolved_cross_law_derivation_with_null_target(
    db_session, matter_with_users
):
    """ruling M5: "האפוטרופוס הכללי" derives from "חוק האפוטרופוס הכללי",
    which is NOT ingested into this matter -- the DERIVES_FROM_LAW
    assertion must still be created, with a null object entity, and the raw
    matched law-reference text preserved in the proposition (never
    dropped, never a fabricated resolution)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    derives_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "DERIVES_FROM_LAW"
    ]
    assert len(derives_edges) == 1
    edge = derives_edges[0]
    assert "האפוטרופוס הכללי" in edge["proposition"]
    # target_law_id unresolved -- preserved as a null object entity, not dropped.
    from app.models.assertion import Assertion

    assertion_row = db_session.get(Assertion, edge["id"])
    assert assertion_row.object_entity_id is None


def test_run_definition_linking_resolves_a_cross_law_derivation_to_a_known_document(
    db_session, matter_with_users
):
    """חוק הגנת הפרטיות_excerpt.wiki derives "חומר מחשב"/"מחשב"/"פלט" from
    "בחוק המחשבים" -- when that second law is ALSO ingested into the same
    matter (חוק המחשבים_stub.wiki), the DERIVES_FROM_LAW assertion must
    resolve target_law_id to that second Document's id, at a HIGHER
    confidence than the unresolved case above."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הגנת הפרטיות, התשמ"א-1981',
        wiki_text=_read("חוק הגנת הפרטיות_excerpt.wiki"),
    )
    computers_law = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק המחשבים, התשנ"ה-1995',
        wiki_text=_read("חוק המחשבים_stub.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    derives_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "DERIVES_FROM_LAW"
    ]
    resolved = [
        a
        for a in derives_edges
        if db_session.get(Assertion, a["id"]).object_entity_id == computers_law["document_id"]
    ]
    assert len(resolved) >= 1
    resolved_confidence = db_session.get(Assertion, resolved[0]["id"]).confidence

    unresolved = [
        a for a in derives_edges if db_session.get(Assertion, a["id"]).object_entity_id is None
    ]
    if unresolved:
        unresolved_confidence = db_session.get(Assertion, unresolved[0]["id"]).confidence
        assert resolved_confidence > unresolved_confidence


def test_run_definition_linking_is_idempotent_on_rerun(db_session, matter_with_users):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )

    first = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(first["created_assertions"]) > 0

    second = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert second["created_assertions"] == []
    assert second["created_definitions"] == []


def test_run_definition_linking_handles_a_matter_with_no_articles_gracefully(
    db_session, matter_with_users
):
    """Malformed/unstructured input error path: a matter with zero ingested
    Articles (e.g. wiki text with no recognizable `@ N.` markers at all)
    must not raise -- it simply has nothing to link."""
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert result["created_assertions"] == []
    assert result["created_definitions"] == []


def test_run_definition_linking_handles_an_empty_definitions_section_gracefully(
    db_session, matter_with_users
):
    """An article whose heading matches a definitions-heading form but
    whose body is blank must not raise -- zero definitions are extracted
    from it, not an error."""
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text="")
    seed_article(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        source_span_id=span_id,
        number="1",
        heading="הגדרות",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert result["created_definitions"] == []
    assert result["created_assertions"] == []


def test_run_definition_linking_skips_bidi_degraded_articles_without_raising(
    db_session, matter_with_users
):
    """Ruling M7: a degraded article is flagged and SKIPPED, never
    auto-corrected or parsed. Uses the synthetic scrambled-word-order
    fixture (`degraded_bidi_sample.wiki`, hand-derived from the already-
    vendored clean fixture -- see tests/unit/test_definition_links_guards.py
    for provenance) as this article's raw body text."""
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    degraded_text = (FIXTURES / "degraded_bidi_sample.wiki").read_text(encoding="utf-8")
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text=degraded_text
    )
    article_id = seed_article(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        source_span_id=span_id,
        number="1",
        heading="הגדרות",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert article_id in result["skipped_degraded_article_ids"]
    assert result["created_definitions"] == []


def test_run_definition_linking_raises_a_clear_error_for_an_unknown_matter(db_session):
    from app.definition_links.pipeline import UnknownMatterError, run_definition_linking

    with pytest.raises(UnknownMatterError):
        run_definition_linking(
            db_session,
            matter_id="00000000-0000-0000-0000-000000000000",
            triggered_by_user_id="00000000-0000-0000-0000-000000000001",
        )
