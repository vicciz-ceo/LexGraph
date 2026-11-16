"""Every assertion has a revision row for its current revision number,
whichever writer created it (audit findings api:1, pipeline:2, pipeline:3,
ui:4).

The definition-links pass is a frozen certified seam that inserts accepted
`system_generated` assertions with `current_revision_number=1` and no
revision row. `app.models.assertion_invariants` enforces the invariant at
the persistence layer instead; these tests drive the REAL pipeline entry
points on the committed fixtures and then use the HTTP API the way the
Knowledge Base and the assertion detail page do.
"""

from __future__ import annotations

import pathlib

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models.assertion import Assertion
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload, new_id, seed_document, seed_source_span

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"
WIKI_LAW = FIXTURES / "wiki_laws" / "חוק להגנת רכוש מופקד.wiki"
DE_PARQUET = FIXTURES / "us_statutes" / "de_sample_rows.parquet"


def _ingest_wiki_law(db_session, m: dict) -> None:
    from app.definition_links.ingest import ingest_wiki_law

    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=WIKI_LAW.read_text(encoding="utf-8"),
    )


def _ingest_delaware_sample(m: dict) -> None:
    from app.definition_links import ingest_us_statutes_cli

    assert ingest_us_statutes_cli.main([
        "--input", str(DE_PARQUET), "--repository-id", m["repository_id"],
        "--matter-id", m["matter_id"], "--title", "Delaware Code -- Statutes",
        "--jurisdiction", "US-DE",
    ]) == 0


def _link_definitions(m: dict) -> None:
    from app.definition_links.cli import main

    assert main(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["reviewer_id"]]) == 0


def _system_generated(db_session, m: dict) -> list[Assertion]:
    db_session.expire_all()
    return list(db_session.scalars(select(Assertion).where(
        Assertion.matter_id == m["matter_id"], Assertion.origin == "system_generated",
    ).order_by(Assertion.created_at, Assertion.id)))


def _revisions(db_session, assertion_id: str) -> list[AssertionRevision]:
    return list(db_session.scalars(select(AssertionRevision).where(
        AssertionRevision.assertion_id == assertion_id,
    ).order_by(AssertionRevision.revision_number)))


def _events(db_session, assertion_id: str) -> list[AuditEvent]:
    return list(db_session.scalars(select(AuditEvent).where(AuditEvent.assertion_id == assertion_id)))


def test_definition_linking_writes_revision_one_and_a_creation_audit_event(db_session, matter_with_users):
    m = matter_with_users
    _ingest_wiki_law(db_session, m)
    _link_definitions(m)

    created = _system_generated(db_session, m)
    assert len(created) >= 3
    for a in created:
        revisions = _revisions(db_session, a.id)
        assert [r.revision_number for r in revisions] == [a.current_revision_number] == [1]
        rev = revisions[0]
        mirrored = ("proposition", "assertion_type", "subject_entity_type", "subject_entity_id",
                    "object_entity_type", "object_entity_id", "jurisdiction", "effective_from",
                    "effective_to")
        assert {f: getattr(rev, f) for f in mirrored} == {f: getattr(a, f) for f in mirrored}
        assert rev.proposition_raw == a.proposition
        assert rev.edited_by_user_id == a.author_user_id == m["reviewer_id"]
        assert rev.revision_reason == "initial creation (system-generated)"
        events = _events(db_session, a.id)
        assert [(e.event_type, e.assertion_revision_id, e.actor_user_id, e.new_value) for e in events] == [
            ("assertion_created", rev.id, m["reviewer_id"], "accepted")
        ]
    # One pipeline run is one transaction, traceable as one correlation id.
    assert len({_events(db_session, a.id)[0].correlation_id for a in created}) == 1


def test_definition_links_are_ratable_and_keep_their_original_text_through_the_api(
    client, db_session, matter_with_users
):
    m = matter_with_users
    _ingest_wiki_law(db_session, m)
    _link_definitions(m)

    listing = client.get("/api/v1/assertions", params={
        "matter_id": m["matter_id"], "origin": "system_generated",
    }, headers=m["rater_headers"])
    assert listing.status_code == 200
    item = next(i for i in listing.json()["items"] if i["assertion_type"] == "USES_DEFINITION")
    assert item["proposition_raw"] == item["proposition"]
    base = f"/api/v1/assertions/{item['id']}"

    # The rating widget's calls (Knowledge Base + detail page) all succeed.
    rated = client.put(base + "/revisions/1/rating", json={"strength": 4, "rationale": "Plain text."},
                       headers=m["rater_headers"])
    assert rated.status_code == 201, rated.text
    for path in ("/revisions/1/rating", "/revisions/1/ratings", "/revisions/1/ratings/summary"):
        assert client.get(base + path, headers=m["rater_headers"]).status_code == 200, path
    detail = client.get(base, headers=m["rater_headers"]).json()
    assert (detail["status"], detail["standing"]) == ("accepted", "accepted")
    assert detail["ratings_summary"]["count"] == 1
    assert [r["revision_number"] for r in detail["revision_history"]] == [1]

    # A review decision now names the revision it reviewed.
    assert client.post(base + "/dispute", headers=m["reviewer_headers"]).status_code == 200
    history = client.get(base + "/history", headers=m["reviewer_headers"]).json()
    assert [(e["event_type"], e["assertion_revision_number"]) for e in history
            if e["event_type"] in ("assertion_created", "assertion.dispute")] == [
        ("assertion_created", 1), ("assertion.dispute", 1),
    ]

    # The first edit no longer loses the generated text (spec section 3).
    original = item["proposition"]
    edited = client.patch(base, json={"proposition": original + " (reviewed)", "expected_revision_number": 1},
                          headers=m["reviewer_headers"])
    assert edited.status_code == 200, edited.text
    revisions = client.get(base + "/revisions", headers=m["reviewer_headers"]).json()
    assert [(r["revision_number"], r["proposition"]) for r in revisions] == [
        (1, original), (2, original + " (reviewed)"),
    ]
    assert client.get(base + "/revisions/1/ratings/summary", headers=m["reviewer_headers"]).json()["count"] == 1


def test_us_statute_definition_links_are_ratable(client, db_session, matter_with_users):
    m = matter_with_users
    _ingest_delaware_sample(m)
    _link_definitions(m)

    created = _system_generated(db_session, m)
    assert created
    for a in created:
        assert [r.revision_number for r in _revisions(db_session, a.id)] == [1]
        rated = client.put(f"/api/v1/assertions/{a.id}/revisions/1/rating", json={"strength": 3},
                           headers=m["rater_headers"])
        assert rated.status_code == 201, rated.text


def test_rerunning_definition_linking_adds_no_revisions_or_audit_events(db_session, matter_with_users):
    m = matter_with_users
    _ingest_wiki_law(db_session, m)
    _link_definitions(m)
    counts = (db_session.scalar(select(func.count()).select_from(AssertionRevision)),
              db_session.scalar(select(func.count()).select_from(AuditEvent)))
    assert counts[0] > 0

    _link_definitions(m)
    assert (db_session.scalar(select(func.count()).select_from(AssertionRevision)),
            db_session.scalar(select(func.count()).select_from(AuditEvent))) == counts


def test_writers_that_record_revision_one_themselves_get_exactly_one(client, db_session, matter_with_users):
    """The REST, agent and enrichment writers add their own revision 1; the
    hook must not add a second one or a second creation event."""
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                            quote_text="Clause 9 survives termination of this Agreement.")
    enriched = run_enrichment(db_session, matter_id=m["matter_id"], triggered_by_user_id=m["reviewer_id"])
    assert len(enriched) == 1
    human = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition="Human  <b>raw</b> proposition."),
        headers=m["contributor_headers"])
    agent = client.post("/api/v1/agent/assertions", json={
        "repository_id": m["repository_id"], "matter_id": m["matter_id"],
        "assertion_type": "SURVIVES_TERMINATION", "proposition": "Clause 9 survives (agent).",
        "subject_entity": {"type": "Document", "id": doc},
        "evidence": [{"source_span_id": span, "evidence_role": "supports"}],
        "agent": {"platform": "pytest"},
    }, headers=m["contributor_headers"])
    assert human.status_code == agent.status_code == 201, (human.text, agent.text)

    expected_reason = {
        human.json()["id"]: ("initial creation", "Human  <b>raw</b> proposition."),
        agent.json()["id"]: ("initial creation", "Clause 9 survives (agent)."),
        enriched[0]["id"]: ("model-suggested (offline enrichment)", enriched[0]["proposition"]),
    }
    db_session.expire_all()
    for assertion_id, (reason, raw) in expected_reason.items():
        revisions = _revisions(db_session, assertion_id)
        assert [(r.revision_number, r.revision_reason, r.proposition_raw) for r in revisions] == [(1, reason, raw)]
        created_events = [e for e in _events(db_session, assertion_id) if e.event_type == "assertion_created"]
        assert [e.assertion_revision_id for e in created_events] == [revisions[0].id]


def test_enrichment_writes_a_creation_audit_event(db_session, matter_with_users):
    """pipeline:3 (enrichment half): offline suggestions are audited like
    every other assertion creation (spec section 16)."""
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                     quote_text="Clause 9 survives termination of this Agreement.")
    created = run_enrichment(db_session, matter_id=m["matter_id"], triggered_by_user_id=m["reviewer_id"])
    assert len(created) == 1
    (event,) = _events(db_session, created[0]["id"])
    (revision,) = _revisions(db_session, created[0]["id"])
    assert (event.event_type, event.actor_user_id, event.assertion_revision_id, event.new_value) == (
        "assertion_created", m["reviewer_id"], revision.id, "draft")


def _bare_assertion(m: dict, **overrides) -> Assertion:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fields = dict(
        id=new_id(), organization_id=m["organization_id"], repository_id=m["repository_id"],
        matter_id=m["matter_id"], assertion_type="USES_DEFINITION", proposition="Article 2 uses X.",
        subject_entity_type="Article", subject_entity_id=new_id(), origin="system_generated",
        status="accepted", author_user_id=m["reviewer_id"], created_at=now, updated_at=now,
        current_revision_number=1,
    )
    fields.update(overrides)
    return Assertion(**fields)


def test_a_writer_that_autoflushes_before_adding_its_revision_keeps_only_its_own(app, matter_with_users):
    """The integrator's pitfall: an autoflush between add(assertion) and
    add(revision) must not make the hook invent a second revision 1."""
    m = matter_with_users
    session = sessionmaker(bind=app.state.engine, autoflush=True)()
    try:
        assertion = _bare_assertion(m, origin="imported")
        session.add(assertion)
        assert session.scalar(select(func.count()).select_from(Assertion)) == 1  # autoflushed
        session.add(AssertionRevision(
            id=new_id(), assertion_id=assertion.id, revision_number=1, proposition=assertion.proposition,
            proposition_raw="writer's own raw text", assertion_type=assertion.assertion_type,
            subject_entity_type="Article", subject_entity_id=assertion.subject_entity_id,
            revision_reason="writer's own revision", edited_by_user_id=m["reviewer_id"],
            created_at=assertion.created_at,
        ))
        session.commit()
        revisions = _revisions(session, assertion.id)
        assert [(r.revision_number, r.revision_reason) for r in revisions] == [(1, "writer's own revision")]
        assert _events(session, assertion.id) == []
    finally:
        session.close()


def test_rolled_back_inserts_get_no_revision_and_survivors_do(app, matter_with_users):
    m = matter_with_users
    session = app.state.session_factory()
    try:
        kept = _bare_assertion(m, proposition="Kept.")
        session.add(kept)
        session.flush()
        savepoint = session.begin_nested()
        dropped = _bare_assertion(m, proposition="Dropped.")
        session.add(dropped)
        session.flush()
        savepoint.rollback()
        session.commit()
        assert [r.proposition for r in _revisions(session, kept.id)] == ["Kept."]
        assert _revisions(session, dropped.id) == [] and session.get(Assertion, dropped.id) is None

        never = _bare_assertion(m, proposition="Never committed.")
        session.add(never)
        session.flush()
        session.rollback()
        assert session.scalar(select(func.count()).select_from(AssertionRevision)) == 1
    finally:
        session.close()
