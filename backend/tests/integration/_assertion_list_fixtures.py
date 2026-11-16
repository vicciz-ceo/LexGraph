"""A small matter whose assertions differ on every spec §17 sort/filter axis.

Shared by the GET /api/v1/assertions list tests. Everything goes through the
real HTTP API (create, agent suggest, rate, review, revise, comment), except
the documents/spans the conftest seeds and the definition-link pipeline run.
"""

from __future__ import annotations

import pathlib
import uuid

from tests.conftest import assertion_payload, seed_document, seed_source_span

WIKI_LAWS = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def entity_id(n: int) -> str:
    """A UUID (the API requires one) whose string order follows ``n``."""
    return f"00000000-0000-4000-8000-{n:012d}"


def _create(client, m, headers, **overrides) -> str:
    response = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _rate(client, assertion_id, headers, strength, revision=1) -> None:
    response = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{revision}/rating",
        json={"strength": strength, "rationale": f"rated {strength}"},
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text


def build_varied_matter(client, m, db_session) -> dict[str, str]:
    """Return ``{key: assertion_id}`` for six assertions (insertion order):

    alpha    contributor, INTERPRETS, IL, effective 2026-01-01..2026-12-31,
             supporting evidence, proposed; rated 3 (author), 5 (rater), 4 (reviewer)
    bravo    rater, WEAKENS, no jurisdiction, effective from 2025-06-01,
             no object, no evidence, draft, unrated; commented on last
    charlie  reviewer, SUPPORTS, US-NY, contradicting evidence only;
             rated 2 (contributor); accepted with a recorded justification
             (an assertion that is not "evidenced" needs one, spec "Review
             decision rules")
    delta    contributor, CONFLICTS_WITH, US-CA, effective until 2027-03-31,
             primary-basis evidence; rated 3 (rater); disputed
    echo     agent suggestion (model_suggested, confidence 0.8) by the
             contributor about a Document; rated 4 (rater); proposed
    foxtrot  contributor, MODIFIES; rated 1 (rater) on revision 1, then
             revised by the reviewer, so revision 2 is unrated
    """
    matter_id, repository_id = m["matter_id"], m["repository_id"]
    contributor, rater, reviewer = m["contributor_headers"], m["rater_headers"], m["reviewer_headers"]
    document = seed_document(db_session, repository_id=repository_id, matter_id=matter_id, title="Services Agreement")
    span_a = seed_source_span(db_session, document_id=document, matter_id=matter_id, quote_text="Clause 8.2 ...")
    span_b = seed_source_span(db_session, document_id=document, matter_id=matter_id, quote_text="Schedule B ...")

    ids = {
        "alpha": _create(
            client, m, contributor, assertion_type="INTERPRETS", save_as="proposed",
            proposition="Alpha: clause 8.4 interprets clause 8.2.", jurisdiction="IL",
            effective_from="2026-01-01", effective_to="2026-12-31",
            subject_entity={"type": "Provision", "id": entity_id(200)},
            object_entity={"type": "Provision", "id": entity_id(100)},
            evidence=[{"source_span_id": span_a, "evidence_role": "supports"}],
        ),
        "bravo": _create(
            client, m, rater, assertion_type="WEAKENS", save_as="draft",
            proposition="Bravo: the waiver weakens clause 3.", effective_from="2025-06-01",
            subject_entity={"type": "Provision", "id": entity_id(50)}, object_entity=None,
        ),
        "charlie": _create(
            client, m, reviewer, assertion_type="SUPPORTS", save_as="proposed",
            proposition="Charlie: schedule B supports the indemnity.", jurisdiction="US-NY",
            subject_entity={"type": "Provision", "id": entity_id(300)},
            object_entity={"type": "Provision", "id": entity_id(310)},
            evidence=[{"source_span_id": span_b, "evidence_role": "contradicts"}],
        ),
        "delta": _create(
            client, m, contributor, assertion_type="CONFLICTS_WITH", save_as="proposed",
            proposition="Delta: clauses 9 and 12 conflict.", jurisdiction="US-CA", effective_to="2027-03-31",
            subject_entity={"type": "Provision", "id": entity_id(90)},
            object_entity={"type": "Clause", "id": entity_id(120)},
            evidence=[{"source_span_id": span_a, "evidence_role": "primary_basis"}],
        ),
    }
    agent = client.post(
        "/api/v1/agent/assertions",
        json={
            **assertion_payload(
                matter_id, repository_id, assertion_type="RELEVANT_TO", save_as="proposed",
                proposition="Echo: the agreement is relevant to the data-transfer issue.",
                subject_entity={"type": "Document", "id": document}, object_entity=None,
                evidence=[{"source_span_id": span_b, "evidence_role": "supports"}],
            ),
            "agent": {"platform": "pytest", "model": "fixture-model", "run_id": "run-1"},
            "confidence": 0.8,
        },
        headers=contributor,
    )
    assert agent.status_code == 201, agent.text
    ids["echo"] = agent.json()["id"]
    ids["foxtrot"] = _create(
        client, m, contributor, assertion_type="MODIFIES", save_as="proposed",
        proposition="Foxtrot: amendment 2 modifies clause 4.",
        subject_entity={"type": "Provision", "id": entity_id(40)},
        object_entity={"type": "Provision", "id": entity_id(41)},
    )

    _rate(client, ids["alpha"], contributor, 3)
    _rate(client, ids["alpha"], rater, 5)
    _rate(client, ids["alpha"], reviewer, 4)
    _rate(client, ids["charlie"], contributor, 2)
    _rate(client, ids["delta"], rater, 3)
    _rate(client, ids["echo"], rater, 4)
    _rate(client, ids["foxtrot"], rater, 1)
    revised = client.patch(
        f"/api/v1/assertions/{ids['foxtrot']}",
        json={"proposition": "Foxtrot: amendment 2 modifies clause 4(b).", "expected_revision_number": 1},
        headers=reviewer,
    )
    assert revised.status_code == 200, revised.text
    accepted = client.post(
        f"/api/v1/assertions/{ids['charlie']}/accept",
        json={"acceptance_justification": "Schedule B is read as supporting it despite the cited passage."},
        headers=reviewer,
    )
    assert accepted.status_code == 200, accepted.text
    disputed = client.post(f"/api/v1/assertions/{ids['delta']}/dispute", headers=reviewer)
    assert disputed.status_code == 200, disputed.text
    comment = client.post(
        f"/api/v1/assertions/{ids['bravo']}/comments", json={"comment_text": "Needs a source."}, headers=reviewer
    )
    assert comment.status_code == 201, comment.text
    return ids


def run_definition_link_pipeline(db_session, m) -> int:
    """Ingest the vendored laws and run the real definition-link pass once.

    Its rows are system_generated/accepted and share ONE created_at. The
    pipeline itself writes no assertion_revisions row; the persistence
    invariant (app.models.assertion_invariants) adds revision 1 at commit,
    with proposition_raw equal to the stored proposition. Returns how many
    it created (about 130).
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    for law in sorted(WIKI_LAWS.glob("*.wiki")):
        ingest_wiki_law(
            db_session,
            repository_id=m["repository_id"],
            matter_id=m["matter_id"],
            title=law.stem,
            wiki_text=law.read_text(encoding="utf-8"),
        )
    result = run_definition_linking(db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"])
    return len(result["created_assertions"])


def insert_legacy_row_without_revision(db_session, source_id: str) -> str:
    """Copy assertion ``source_id`` as a new row with a Core INSERT and return its id.

    No ORM hook sees a Core INSERT, so the copy has no assertion_revisions
    row: the state of a definition-link row written before the persistence
    invariant, in a database the 20261116_backfill_initial_assertion_revisions
    migration has not repaired yet. Readers must still serialize it.
    """
    from sqlalchemy import insert, select

    from app.models.assertion import Assertion

    table = Assertion.__table__
    row = db_session.execute(select(table).where(table.c.id == source_id)).mappings().one()
    new_id = str(uuid.uuid4())
    db_session.execute(
        insert(table).values({**row, "id": new_id, "proposition": f"{row['proposition']} (legacy row)"})
    )
    db_session.commit()
    return new_id
