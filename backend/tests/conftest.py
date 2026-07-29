"""Shared pytest fixtures for the LexGraph backend test suite.

Planner-authored scaffolding (sprint 2026-07-25-collaborative-assertions).
Two RED shapes appear throughout this suite, both legitimate per the
sprint contract ("fail on assertions ... never on collection/import
errors"):

1. Pure route/assertion RED — a test calls the real API (via the `client`
   fixture, built from the real `app.main.create_app()`) with a plausible
   payload and asserts the eventually-correct status code / response
   shape. Today every `/api/v1/...` route 404s because no router is
   registered yet (see app/main.py) — routing happens before any DB
   dependency runs, so these tests need NO seeded data to fail correctly
   right now, and need no changes later once routes+DB exist.

2. Schema RED — a test uses the `matter_with_users` fixture (or the raw
   seed_* helpers directly), which INSERTs into tables documented in the
   sprint contract's "Data model reference" (organizations, repositories,
   matters, users, matter_roles, documents, source_spans, ...). None of
   those tables exist until a Developer track registers the matching
   ORM models against `app.db.Base` (tracked as item F1). Until then,
   every seed_* call raises `sqlalchemy.exc.OperationalError: no such
   table: ...` — a genuine missing-schema signal raised at fixture setup
   (visible as pytest ERROR, not FAILED), not an import/collection error.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import Base
from app.main import create_app


# --- Core app/client/db fixtures -----------------------------------------


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    application = create_app()
    # Zero-op today (no models registered against Base yet); starts
    # creating real tables the moment a Developer track adds models.
    Base.metadata.create_all(bind=application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session(app) -> Iterator[Session]:
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


# --- Auth header helper (app/auth.py test-token seam) ---------------------


def auth_header(user_id: str) -> dict[str, str]:
    """Build a test-scheme Authorization header for `user_id` (app/auth.py)."""
    return {"Authorization": f"Bearer {user_id}"}


def new_id() -> str:
    return str(uuid.uuid4())


# --- Raw-SQL seed helpers ---------------------------------------------
# Column names are lifted directly from spec §2-4/§9/§16 and the sprint
# contract's "Data model reference". Planner does NOT define ORM models
# (Developer work) — these helpers talk to the tables Developer tracks
# will create, via raw SQL only, so this file itself has zero business
# logic and no forbidden model imports.


def seed_organization(session: Session, *, id: str | None = None, name: str = "Test Org") -> str:
    org_id = id or new_id()
    session.execute(
        text("INSERT INTO organizations (id, name) VALUES (:id, :name)"),
        {"id": org_id, "name": name},
    )
    session.commit()
    return org_id


def seed_repository(
    session: Session, *, organization_id: str, id: str | None = None, name: str = "Test Repo"
) -> str:
    repo_id = id or new_id()
    session.execute(
        text(
            "INSERT INTO repositories (id, organization_id, name) "
            "VALUES (:id, :organization_id, :name)"
        ),
        {"id": repo_id, "organization_id": organization_id, "name": name},
    )
    session.commit()
    return repo_id


def seed_matter(
    session: Session, *, repository_id: str, id: str | None = None, name: str = "Test Matter"
) -> str:
    matter_id = id or new_id()
    session.execute(
        text("INSERT INTO matters (id, repository_id, name) VALUES (:id, :repository_id, :name)"),
        {"id": matter_id, "repository_id": repository_id, "name": name},
    )
    session.commit()
    return matter_id


def seed_user(
    session: Session,
    *,
    id: str | None = None,
    email: str | None = None,
    display_name: str = "Test User",
) -> str:
    user_id = id or new_id()
    session.execute(
        text("INSERT INTO users (id, email, display_name) VALUES (:id, :email, :display_name)"),
        {"id": user_id, "email": email or f"{user_id}@example.test", "display_name": display_name},
    )
    session.commit()
    return user_id


def seed_matter_role(
    session: Session, *, user_id: str, matter_id: str, role: str, id: str | None = None
) -> str:
    role_id = id or new_id()
    session.execute(
        text(
            "INSERT INTO matter_roles (id, user_id, matter_id, role) "
            "VALUES (:id, :user_id, :matter_id, :role)"
        ),
        {"id": role_id, "user_id": user_id, "matter_id": matter_id, "role": role},
    )
    session.commit()
    return role_id


def seed_document(
    session: Session,
    *,
    repository_id: str,
    matter_id: str,
    id: str | None = None,
    title: str = "Test Document",
) -> str:
    doc_id = id or new_id()
    session.execute(
        text(
            "INSERT INTO documents (id, repository_id, matter_id, title) "
            "VALUES (:id, :repository_id, :matter_id, :title)"
        ),
        {"id": doc_id, "repository_id": repository_id, "matter_id": matter_id, "title": title},
    )
    session.commit()
    return doc_id


def seed_source_span(
    session: Session,
    *,
    document_id: str,
    matter_id: str,
    id: str | None = None,
    quote_text: str = "Sample quoted text.",
) -> str:
    span_id = id or new_id()
    session.execute(
        text(
            "INSERT INTO source_spans (id, document_id, matter_id, quote_text) "
            "VALUES (:id, :document_id, :matter_id, :quote_text)"
        ),
        {"id": span_id, "document_id": document_id, "matter_id": matter_id, "quote_text": quote_text},
    )
    session.commit()
    return span_id


# --- Sprint 2026-07-29-definition-links (ruling M1: additive `articles` +
# `definitions` tables) -----------------------------------------------------
#
# Column lists below are the Planner's schema design for the new tables (M1
# authorizes "new Article + Definition tables" generically; exact columns
# are this sprint's Planner's call, same as the assertion-type NAMES were
# under M2). `articles.source_span_id` is NON-NULL by design: every
# ingested article always gets a backing `SourceSpan` row created alongside
# it (item DL7's `ingest_wiki_law`), so `AssertionEvidence.source_span_id`
# (which FKs to `source_spans.id`, not to anything new) can point at an
# article's text exactly the way it already points at any other quoted
# span -- no change to `source_spans`/`assertion_evidence` needed.
# `definitions.terms` is stored as a JSON-encoded list of strings (Stage 2's
# "multi-term single definition" case: one dash, N terms sharing one
# definition body) rather than a separate join table -- a deliberately
# minimal, additive design for this sprint's scope.


def seed_article(
    session: Session,
    *,
    document_id: str,
    matter_id: str,
    source_span_id: str,
    id: str | None = None,
    number: str = "1",
    heading: str = "Test Article",
    chapter: str | None = None,
) -> str:
    article_id = id or new_id()
    session.execute(
        text(
            "INSERT INTO articles (id, document_id, matter_id, source_span_id, number, heading, chapter) "
            "VALUES (:id, :document_id, :matter_id, :source_span_id, :number, :heading, :chapter)"
        ),
        {
            "id": article_id,
            "document_id": document_id,
            "matter_id": matter_id,
            "source_span_id": source_span_id,
            "number": number,
            "heading": heading,
            "chapter": chapter,
        },
    )
    session.commit()
    return article_id


def seed_definition(
    session: Session,
    *,
    document_id: str,
    matter_id: str,
    article_id: str,
    id: str | None = None,
    terms: list[str] | None = None,
    definition_text: str = "Sample definition text.",
    scope: str = "law-wide",
    qualifier: str | None = None,
    parent_definition_id: str | None = None,
) -> str:
    import json

    definition_id = id or new_id()
    session.execute(
        text(
            "INSERT INTO definitions (id, document_id, matter_id, article_id, terms, "
            "definition_text, scope, qualifier, parent_definition_id) "
            "VALUES (:id, :document_id, :matter_id, :article_id, :terms, "
            ":definition_text, :scope, :qualifier, :parent_definition_id)"
        ),
        {
            "id": definition_id,
            "document_id": document_id,
            "matter_id": matter_id,
            "article_id": article_id,
            "terms": json.dumps(terms if terms is not None else ["Sample Term"]),
            "definition_text": definition_text,
            "scope": scope,
            "qualifier": qualifier,
            "parent_definition_id": parent_definition_id,
        },
    )
    session.commit()
    return definition_id


@pytest.fixture()
def matter_with_users(db_session: Session) -> dict:
    """Seed one org/repo/matter plus a contributor, a second contributor
    (rater), a reviewer, and an outsider with NO matter role at all.

    Raises `sqlalchemy.exc.OperationalError: no such table: organizations`
    until item F1 registers the ORM models — that is expected RED, not a
    fixture bug.
    """
    org_id = seed_organization(db_session)
    repo_id = seed_repository(db_session, organization_id=org_id)
    matter_id = seed_matter(db_session, repository_id=repo_id)

    contributor_id = seed_user(db_session, display_name="Contributor A")
    rater_id = seed_user(db_session, display_name="Contributor B (rater)")
    reviewer_id = seed_user(db_session, display_name="Reviewer")
    outsider_id = seed_user(db_session, display_name="Outsider (no matter access)")

    seed_matter_role(db_session, user_id=contributor_id, matter_id=matter_id, role="contributor")
    seed_matter_role(db_session, user_id=rater_id, matter_id=matter_id, role="contributor")
    seed_matter_role(db_session, user_id=reviewer_id, matter_id=matter_id, role="reviewer")
    # outsider intentionally gets no matter_roles row (proves G9 isolation)

    return {
        "organization_id": org_id,
        "repository_id": repo_id,
        "matter_id": matter_id,
        "contributor_id": contributor_id,
        "rater_id": rater_id,
        "reviewer_id": reviewer_id,
        "outsider_id": outsider_id,
        "contributor_headers": auth_header(contributor_id),
        "rater_headers": auth_header(rater_id),
        "reviewer_headers": auth_header(reviewer_id),
        "outsider_headers": auth_header(outsider_id),
    }


# --- Payload builders -------------------------------------------------


def assertion_payload(matter_id: str, repository_id: str, **overrides) -> dict:
    """A spec-§13-shaped user-suggested-assertion request body."""
    payload = {
        "repository_id": repository_id,
        "matter_id": matter_id,
        "assertion_type": "CREATES_EXCEPTION_TO",
        "proposition": "Clause 8.4 creates a limited exception to the notification obligation in Clause 8.2.",
        "subject_entity": {"type": "Provision", "id": new_id()},
        "object_entity": {"type": "Provision", "id": new_id()},
        "jurisdiction": None,
        "effective_from": None,
        "effective_to": None,
        "evidence": [],
        "explanation": "The phrase 'except where prohibited by law' appears to qualify the general notification requirement.",
        "save_as": "draft",
    }
    payload.update(overrides)
    return payload


def rating_payload(strength: int = 4, rationale: str | None = "Strong textual support.") -> dict:
    return {"strength": strength, "rationale": rationale}
