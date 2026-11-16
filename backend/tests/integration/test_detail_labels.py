"""Assertion detail names what it links to (finding ui:30, detail-page part).

The detail page used to show the subject/object entities and the related
assertions by UUID only, even when the author had picked a Document or an
Article by title. GET /assertions/{id} now gives each referenced entity a
human ``label`` (persisted entities of the assertion's own matter only), and
GET /assertions/{id}/related gives each match the related assertion's
``proposition`` and ``status``. Both additions are additive: every existing
key keeps its value.
"""

from __future__ import annotations

from tests.conftest import (
    assertion_payload,
    seed_article,
    seed_definition,
    seed_document,
    seed_matter,
    seed_matter_role,
    seed_source_span,
)


def _create(client, m, **overrides) -> dict:
    response = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=m["contributor_headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def _detail(client, m, assertion_id: str) -> dict:
    response = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["contributor_headers"])
    assert response.status_code == 200, response.text
    return response.json()


def test_document_and_article_entities_carry_their_titles(client, matter_with_users, db_session):
    m = matter_with_users
    doc = seed_document(
        db_session, repository_id=m["repository_id"], matter_id=m["matter_id"],
        title="Master Services Agreement",
    )
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"])
    article = seed_article(
        db_session, document_id=doc, matter_id=m["matter_id"], source_span_id=span,
        number="8.4", heading="Public-domain exception",
    )
    created = _create(
        client, m,
        subject_entity={"type": "Document", "id": doc},
        object_entity={"type": "Article", "id": article},
    )

    body = _detail(client, m, created["id"])

    assert body["subject_entity"] == {
        "type": "Document", "id": doc, "label": "Master Services Agreement",
    }
    assert body["object_entity"] == {
        "type": "Article", "id": article,
        "label": "Master Services Agreement / 8.4 Public-domain exception",
    }


def test_definition_span_and_assertion_entities_are_labelled(client, matter_with_users, db_session):
    m = matter_with_users
    doc = seed_document(
        db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title="Delaware Code",
    )
    span = seed_source_span(
        db_session, document_id=doc, matter_id=m["matter_id"],
        quote_text="A branch office is any place of business other than the main office.",
    )
    article = seed_article(
        db_session, document_id=doc, matter_id=m["matter_id"], source_span_id=span,
        number="796", heading="Definitions",
    )
    definition = seed_definition(
        db_session, document_id=doc, matter_id=m["matter_id"], article_id=article,
        terms=["Branch office", "Branch"],
    )
    first = _create(
        client, m,
        proposition="The definition of branch office covers every secondary place of business.",
        subject_entity={"type": "Definition", "id": definition},
        object_entity={"type": "SourceSpan", "id": span},
    )
    second = _create(
        client, m,
        proposition="An assertion about the branch-office definition is itself contested.",
        subject_entity={"type": "Assertion", "id": first["id"]},
        object_entity=None,
    )

    body = _detail(client, m, first["id"])
    assert body["subject_entity"]["label"] == '"Branch office", "Branch" (Delaware Code / 796 Definitions)'
    assert body["object_entity"]["label"] == (
        "A branch office is any place of business other than the main office."
    )

    nested = _detail(client, m, second["id"])
    assert nested["subject_entity"]["label"] == first["proposition"]
    assert nested["object_entity"] is None


def test_legacy_and_cross_matter_references_get_no_label(client, matter_with_users, db_session):
    m = matter_with_users
    other_matter = seed_matter(db_session, repository_id=m["repository_id"], name="Other matter")
    seed_matter_role(db_session, user_id=m["contributor_id"], matter_id=other_matter, role="contributor")
    foreign_doc = seed_document(
        db_session, repository_id=m["repository_id"], matter_id=other_matter, title="Secret other-matter title",
    )
    # A legacy opaque reference (no persisted table) is stored as given.
    created = _create(client, m)
    body = _detail(client, m, created["id"])
    assert body["subject_entity"]["type"] == "Provision"
    assert body["subject_entity"]["label"] is None
    assert body["object_entity"]["label"] is None

    # A row that names another matter's document (written directly, as only
    # a raw insert could) must not leak that document's title.
    from sqlalchemy import text

    db_session.execute(
        text("UPDATE assertions SET subject_entity_type = 'Document', subject_entity_id = :doc WHERE id = :id"),
        {"doc": foreign_doc, "id": created["id"]},
    )
    db_session.commit()
    leaked = _detail(client, m, created["id"])
    assert leaked["subject_entity"] == {"type": "Document", "id": foreign_doc, "label": None}
    assert "Secret other-matter title" not in str(leaked)


def test_long_labels_are_shortened(client, matter_with_users, db_session):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"], quote_text="word " * 400)
    created = _create(client, m, subject_entity={"type": "SourceSpan", "id": span})

    label = _detail(client, m, created["id"])["subject_entity"]["label"]

    assert len(label) <= 240
    assert label.endswith("…")
    assert label.startswith("word word")


def test_related_matches_carry_proposition_and_status(client, matter_with_users):
    m = matter_with_users
    first = _create(
        client, m, proposition="Clause 8.4 creates a limited exception to the notification obligation in Clause 8.2.",
    )
    second = _create(
        client, m, proposition="Clause 8.4 creates a narrow exception to the Clause 8.2 notice obligation.",
    )

    response = client.get(f"/api/v1/assertions/{second['id']}/related", headers=m["contributor_headers"])

    assert response.status_code == 200
    matches = response.json()
    assert [match["assertion_id"] for match in matches] == [first["id"]]
    match = matches[0]
    assert match["proposition"] == first["proposition"]
    assert match["status"] == "draft"
    # The pre-existing keys are unchanged.
    assert match["match_kind"] == "similar"
    assert isinstance(match["score"], float)
