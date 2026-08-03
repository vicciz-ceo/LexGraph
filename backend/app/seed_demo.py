"""Seed a runnable demo workspace so a fresh clone can use the full web UI.

Usage (from ``backend/``, after ``pip install -e '.[dev]'`` — the seeder
drives the real HTTP API via Starlette's TestClient, which needs httpx):

    .venv/bin/python -m app.seed_demo            # writes ./dev.db
    .venv/bin/python -m app.seed_demo --reset    # start over

Then serve it:

    LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000

Sign in from the frontend with one of the seeded user ids (the bearer
token IS the user id — ``app/auth.py`` test-token seam):

    admin · reviewer · contributor · viewer

Everything domain-side (assertions, submissions, reviews, ratings,
comments, evidence) is created through the real API endpoints, so
notifications, audit events, revisions, and permission checks are all
exercised exactly as the UI would. Only the identity scaffolding (org,
repository, matters, users, roles, documents, source spans) is inserted
directly — there are deliberately no HTTP endpoints for provisioning
those.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

DEMO_USERS = [
    ("admin", "ada.admin@demo.lexgraph", "Ada Admin", "admin"),
    ("reviewer", "riva.reviewer@demo.lexgraph", "Riva Reviewer", "reviewer"),
    ("contributor", "caleb.contributor@demo.lexgraph", "Caleb Contributor", "contributor"),
    ("viewer", "vera.viewer@demo.lexgraph", "Vera Viewer", "viewer"),
]

MSA_QUOTES = [
    "Either party may terminate this Agreement for convenience upon ninety (90) days' prior written notice.",
    "Supplier shall notify Customer of any Data Incident without undue delay, and in any event within 72 hours.",
    "Sections 8 (Confidentiality), 10 (Indemnification) and 12 (Limitation of Liability) survive termination.",
    "Except where prohibited by law, each party's aggregate liability shall not exceed the fees paid in the preceding 12 months.",
    "Clause 8.4: the notification obligation in Clause 8.2 does not apply to information already in the public domain.",
    "Customer data shall be processed exclusively within the agreed jurisdictions listed in Annex 2.",
]

DPA_QUOTES = [
    "The processor shall implement appropriate technical and organisational measures pursuant to Article 32 GDPR.",
    "Sub-processors may be engaged only with the controller's prior specific or general written authorisation.",
]


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


def _entity(kind: str) -> dict:
    return {"type": kind, "id": str(uuid.uuid4())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default="dev.db", help="SQLite file to create (default: dev.db)")
    parser.add_argument("--reset", action="store_true", help="delete the DB file first")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if args.reset and db_path.exists():
        db_path.unlink()
    if db_path.exists():
        print(f"{db_path} already exists — pass --reset to reseed from scratch.")
        return 1

    os.environ["LEXGRAPH_DATABASE_URL"] = f"sqlite:///{db_path}"

    # Imports happen after the env var is set so create_app() binds to the
    # demo database.
    from fastapi.testclient import TestClient

    from app.db import Base
    from app.main import create_app
    from app.models.assertion import Assertion
    from app.models.document import Document
    from app.models.matter import Matter
    from app.models.matter_role import MatterRole
    from app.models.organization import Organization
    from app.models.repository import Repository
    from app.models.source_span import SourceSpan
    from app.models.user import User

    app = create_app()
    Base.metadata.create_all(bind=app.state.engine)
    session = app.state.session_factory()

    # --- Identity scaffolding (no provisioning API exists — direct ORM) ----
    org = Organization(id=str(uuid.uuid4()), name="Demo Legal Group")
    repo = Repository(id=str(uuid.uuid4()), organization_id=org.id, name="Contract Repository")
    msa = Matter(
        id=str(uuid.uuid4()),
        repository_id=repo.id,
        name="MSA — Acme ↔ Blue Ridge Logistics",
    )
    dpa = Matter(
        id=str(uuid.uuid4()),
        repository_id=repo.id,
        name="Data Processing Addendum — Acme",
    )
    session.add_all([org, repo, msa, dpa])

    for user_id, email, display_name, _role in DEMO_USERS:
        session.add(User(id=user_id, email=email, display_name=display_name))
    for user_id, _email, _display_name, role in DEMO_USERS:
        session.add(
            MatterRole(id=str(uuid.uuid4()), user_id=user_id, matter_id=msa.id, role=role)
        )
    # Second matter: smaller team, so the matter switcher shows different rosters.
    session.add(
        MatterRole(id=str(uuid.uuid4()), user_id="admin", matter_id=dpa.id, role="admin")
    )
    session.add(
        MatterRole(id=str(uuid.uuid4()), user_id="reviewer", matter_id=dpa.id, role="reviewer")
    )

    msa_doc = Document(
        id=str(uuid.uuid4()), repository_id=repo.id, matter_id=msa.id,
        title="Master Services Agreement (executed 2025-11-02)",
    )
    dpa_doc = Document(
        id=str(uuid.uuid4()), repository_id=repo.id, matter_id=dpa.id,
        title="Data Processing Addendum (draft v3)",
    )
    session.add_all([msa_doc, dpa_doc])

    msa_spans: list[str] = []
    for quote in MSA_QUOTES:
        span = SourceSpan(
            id=str(uuid.uuid4()), document_id=msa_doc.id, matter_id=msa.id, quote_text=quote
        )
        msa_spans.append(span.id)
        session.add(span)
    dpa_spans: list[str] = []
    for quote in DPA_QUOTES:
        span = SourceSpan(
            id=str(uuid.uuid4()), document_id=dpa_doc.id, matter_id=dpa.id, quote_text=quote
        )
        dpa_spans.append(span.id)
        session.add(span)
    session.commit()

    # --- Domain data through the real API ----------------------------------
    client = TestClient(app)

    def create(
        author: str,
        proposition: str,
        assertion_type: str,
        *,
        matter: Matter = msa,
        save_as: str = "proposed",
        evidence: list[dict] | None = None,
        explanation: str | None = None,
        jurisdiction: str | None = None,
        object_entity: dict | None = None,
    ) -> str:
        response = client.post(
            "/api/v1/assertions",
            json={
                "repository_id": repo.id,
                "matter_id": matter.id,
                "assertion_type": assertion_type,
                "proposition": proposition,
                "subject_entity": _entity("Provision"),
                "object_entity": object_entity or _entity("Provision"),
                "jurisdiction": jurisdiction,
                "evidence": evidence or [],
                "explanation": explanation,
                "save_as": save_as,
            },
            headers=_auth(author),
        )
        assert response.status_code == 201, f"create failed: {response.status_code} {response.text}"
        return response.json()["id"]

    def act(user: str, assertion_id: str, action: str, body: dict | None = None) -> None:
        response = client.post(
            f"/api/v1/assertions/{assertion_id}/{action}", json=body, headers=_auth(user)
        )
        assert response.status_code == 200, (
            f"{action} failed: {response.status_code} {response.text}"
        )

    def rate(user: str, assertion_id: str, strength: int, rationale: str | None = None) -> None:
        detail = client.get(f"/api/v1/assertions/{assertion_id}", headers=_auth(user)).json()
        revision = detail["current_revision_number"]
        response = client.put(
            f"/api/v1/assertions/{assertion_id}/revisions/{revision}/rating",
            json={"strength": strength, "rationale": rationale},
            headers=_auth(user),
        )
        assert response.status_code in (200, 201), (
            f"rating failed: {response.status_code} {response.text}"
        )

    def comment(user: str, assertion_id: str, text: str) -> None:
        response = client.post(
            f"/api/v1/assertions/{assertion_id}/comments",
            json={"comment_text": text},
            headers=_auth(user),
        )
        assert response.status_code == 201, (
            f"comment failed: {response.status_code} {response.text}"
        )

    def mark_model_suggested(assertion_id: str, confidence: float) -> None:
        """Origin is server-assigned on the API path; the enrichment pipeline
        that produces model_suggested assertions is out of scope for a seed,
        so flip the two provenance fields directly."""
        row = session.get(Assertion, assertion_id)
        row.origin = "model_suggested"
        row.confidence = confidence
        session.commit()

    # Accepted knowledge (the Knowledge Base view).
    a_survival = create(
        "contributor",
        "Sections 8, 10 and 12 survive termination of the MSA.",
        "SURVIVES_TERMINATION",
        evidence=[{"source_span_id": msa_spans[2], "evidence_role": "supports"}],
        explanation="Survival clause enumerates the surviving sections explicitly.",
    )
    rate("reviewer", a_survival, 5, "Verbatim in the survival clause.")
    rate("admin", a_survival, 5, None)
    act("reviewer", a_survival, "accept")

    a_termination = create(
        "contributor",
        "Either party may terminate for convenience on 90 days' written notice.",
        "APPLIES_TO",
        evidence=[{"source_span_id": msa_spans[0], "evidence_role": "supports"}],
    )
    rate("reviewer", a_termination, 4, "Clear text; note the notice must be written.")
    act("reviewer", a_termination, "accept")

    a_incident = create(
        "reviewer",
        "Supplier must notify Acme of a Data Incident within 72 hours.",
        "APPLIES_TO",
        evidence=[{"source_span_id": msa_spans[1], "evidence_role": "supports"}],
        jurisdiction="IL",
    )
    mark_model_suggested(a_incident, 0.92)
    rate("contributor", a_incident, 4, "Matches the notification clause.")
    rate("admin", a_incident, 4, None)
    act("admin", a_incident, "accept")

    # Superseded pair: the older liability cap reading was replaced.
    a_cap_old = create(
        "contributor",
        "The liability cap equals the total fees paid under the agreement.",
        "INTERPRETS",
        evidence=[{"source_span_id": msa_spans[3], "evidence_role": "supports"}],
    )
    act("reviewer", a_cap_old, "accept")
    a_cap_new = create(
        "reviewer",
        "The liability cap equals the fees paid in the 12 months preceding the claim, except where prohibited by law.",
        "INTERPRETS",
        evidence=[{"source_span_id": msa_spans[3], "evidence_role": "supports"}],
        explanation="The cap is time-boxed to the preceding 12 months — the earlier reading missed the look-back window.",
    )
    rate("admin", a_cap_new, 5, "Corrects the earlier overbroad reading.")
    act("admin", a_cap_new, "accept")
    act("reviewer", a_cap_old, "supersede", {"superseded_by_assertion_id": a_cap_new})

    # The review queue (proposed, mixed origins).
    a_exception = create(
        "contributor",
        "Clause 8.4 creates an exception to the Clause 8.2 notification obligation for public-domain information.",
        "CREATES_EXCEPTION_TO",
        evidence=[{"source_span_id": msa_spans[4], "evidence_role": "supports"}],
        explanation="8.4 expressly carves public-domain information out of 8.2.",
    )
    rate("reviewer", a_exception, 4, "Carve-out is explicit; scope of 'public domain' is the open question.")
    rate("admin", a_exception, 3, "Plausible, but check interplay with Annex 2.")
    comment("reviewer", a_exception, "Does 8.4 also cover information that becomes public after disclosure?")
    comment("contributor", a_exception, "Good question — the clause text is silent; flagging for outside counsel.")

    a_jurisdiction = create(
        "contributor",
        "Customer data may only be processed in the jurisdictions listed in Annex 2.",
        "APPLIES_TO",
        evidence=[{"source_span_id": msa_spans[5], "evidence_role": "supports"}],
        jurisdiction="IL",
    )
    mark_model_suggested(a_jurisdiction, 0.78)
    rate("reviewer", a_jurisdiction, 4, None)

    a_weak = create(
        "contributor",
        "The 72-hour incident notification window conflicts with the 90-day termination notice mechanics.",
        "CONFLICTS_WITH",
        explanation="Filed for discussion — the two clauses address different obligations.",
    )
    rate("reviewer", a_weak, 2, "These clauses govern unrelated obligations; no real conflict.")
    rate("admin", a_weak, 1, "No textual basis for a conflict.")

    # Unsupported (no supporting evidence) — exercises the acceptance-justification flow.
    a_unsupported = create(
        "reviewer",
        "The parties intended the liability cap to exclude indemnification obligations.",
        "INTERPRETS",
        explanation="Based on negotiation-call notes; no documentary span identified yet.",
    )
    mark_model_suggested(a_unsupported, 0.55)

    # Disputed queue.
    a_disputed1 = create(
        "contributor",
        "The public-domain exception in 8.4 extends to information disclosed in breach and later republished.",
        "INTERPRETS",
        evidence=[{"source_span_id": msa_spans[4], "evidence_role": "supports"}],
    )
    rate("reviewer", a_disputed1, 2, "Breach-then-republish is the classic carve-out fight; the text doesn't settle it.")
    rate("admin", a_disputed1, 3, None)
    comment("admin", a_disputed1, "Split authority on this; needs a ruling.")
    act("reviewer", a_disputed1, "dispute")

    a_disputed2 = create(
        "reviewer",
        "The 12-month look-back cap weakens the indemnification protections in Section 10.",
        "WEAKENS",
        evidence=[{"source_span_id": msa_spans[3], "evidence_role": "contradicts"}],
    )
    rate("contributor", a_disputed2, 3, None)
    act("admin", a_disputed2, "dispute")

    # Rejected + revision-requested + draft + withdrawn.
    a_rejected = create(
        "contributor",
        "The MSA automatically renews for successive one-year terms.",
        "APPLIES_TO",
        explanation="Could not locate a renewal clause; submitting to confirm.",
    )
    act("reviewer", a_rejected, "reject")

    a_revision = create(
        "contributor",
        "Termination for convenience requires payment of a termination fee.",
        "MODIFIES",
    )
    act("reviewer", a_revision, "request-revision", {"comment": "Cite the fee clause — the convenience-termination text mentions notice only."})

    create(
        "contributor",
        "Annex 2 jurisdiction list implicitly includes sub-processor locations.",
        "RELEVANT_TO",
        save_as="draft",
        explanation="Draft — still collecting spans from Annex 2.",
    )

    a_withdrawn = create(
        "contributor",
        "Section 12 caps only direct damages.",
        "INTERPRETS",
    )
    response = client.post(
        f"/api/v1/assertions/{a_withdrawn}/withdraw", headers=_auth("contributor")
    )
    assert response.status_code == 200, response.text

    # Second matter gets a small seed so switching matters visibly changes data.
    a_dpa = create(
        "admin",
        "Sub-processors require prior written authorisation from the controller.",
        "APPLIES_TO",
        matter=dpa,
        evidence=[{"source_span_id": dpa_spans[1], "evidence_role": "supports"}],
        jurisdiction="IL",
    )
    act("reviewer", a_dpa, "accept")
    a_dpa2 = create(
        "admin",
        "Article 32 GDPR measures are contractually incorporated by reference.",
        "INTERPRETS",
        matter=dpa,
        evidence=[{"source_span_id": dpa_spans[0], "evidence_role": "supports"}],
        jurisdiction="IL",
    )
    mark_model_suggested(a_dpa2, 0.81)

    session.close()

    total = len(MSA_QUOTES) + len(DPA_QUOTES)
    print(f"Seeded {db_path} — 2 matters, {len(DEMO_USERS)} users, {total} source spans.")
    print("Serve it:")
    print(f"  LEXGRAPH_DATABASE_URL=sqlite:///{db_path} .venv/bin/uvicorn app.main:app --port 8000")
    print("Sign-in ids (token = user id): " + ", ".join(u for u, *_ in DEMO_USERS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
