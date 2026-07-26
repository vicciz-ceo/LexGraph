"""Track B, item B3 — pluggable enricher interface (ruling R4: a declared
boundary seam). `app.enrich.base` does not exist yet -- ModuleNotFoundError
is the expected RED signal.

R4 explicitly allows a fake enricher implementation in tests -- this is the
ONE declared boundary seam in this sprint's self-mock ban. The built-in
offline `HeuristicEnricher` itself must still be tested live (see
test_enrichment_suggester.py / test_enrichment_pipeline_live.py), which this
file does not duplicate.
"""

from __future__ import annotations

from tests.conftest import seed_document, seed_source_span


class _FakeEnricher:
    """A test double satisfying the `Enricher` protocol -- the declared
    boundary seam (ruling R4), not a mock of the pipeline itself."""

    def suggest(self, spans):
        return [
            {
                "assertion_type": "RELEVANT_TO",
                "proposition": f"Fake candidate from {spans[0]['id']}",
                "evidence_span_ids": [spans[0]["id"]],
            }
        ]


def test_heuristic_enricher_satisfies_the_enricher_protocol():
    from app.enrich.base import Enricher
    from app.enrich.suggester import HeuristicEnricher

    enricher = HeuristicEnricher()
    assert isinstance(enricher, Enricher)


def test_pipeline_accepts_an_injected_fake_enricher_boundary_seam(db_session, matter_with_users):
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    seed_source_span(
        db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text="Irrelevant text."
    )

    created = run_enrichment(
        db_session,
        matter_id=m["matter_id"],
        triggered_by_user_id=m["contributor_id"],
        enricher=_FakeEnricher(),
    )
    assert len(created) == 1
    assert created[0]["assertion_type"] == "RELEVANT_TO"


def test_pipeline_default_enricher_is_the_real_offline_heuristic(db_session, matter_with_users):
    """No `enricher=` argument -- must use the REAL built-in offline
    enricher, not a mock, per the live-path requirement."""
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    seed_source_span(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        quote_text="This obligation shall survive termination of this Agreement.",
    )

    created = run_enrichment(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(created) >= 1
    assert created[0]["assertion_type"] == "SURVIVES_TERMINATION"
