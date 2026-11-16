"""What the Suggest Assertion page and the revision editor rely on.

The web form (frontend/src/pages/SuggestAssertionPage.tsx,
components/AssertionSuggestionForm.tsx, components/AssertionEditor.tsx)
reads these API behaviours; each test pins one so a backend change that
would silently break the form fails here instead:

- the exact-duplicate 409 names the existing assertion, so the page links
  to it (ui:5);
- every similar-assertion entry carries the id the page links to (ui:5);
- the entity listing gives each source its type, so a deep-linked subject
  is sent with its real type (review:10), and an empty matter lists none,
  which the page answers with its no-sources state (ui:33);
- a proposed new type is stored as named when flagged (ui:21);
- the explanation, which carries the "Further evidence needed" note, is
  stored as the first comment, byte for byte (ui:21);
- the frontend's assertion-type list mirrors the backend vocabulary.
"""

from __future__ import annotations

import pathlib
import re

from app.services.validation import ALLOWED_ASSERTION_TYPES
from tests.conftest import assertion_payload, seed_article, seed_document, seed_source_span

FRONTEND_ASSERTION_TYPES_TS = (
    pathlib.Path(__file__).resolve().parents[3] / "frontend" / "src" / "constants" / "assertionTypes.ts"
)

# The pattern frontend/src/constants/apiConflicts.ts reads the id with.
DUPLICATE_ID = re.compile(r"\(assertion ([^)\s]+)\)")


def _document(db_session, m, title="Master Services Agreement"):
    return seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title=title)


def _create(client, m, **overrides):
    response = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=m["contributor_headers"],
    )
    return response


def test_exact_duplicate_conflict_names_the_existing_assertion(client, db_session, matter_with_users):
    m = matter_with_users
    doc = _document(db_session, m)
    subject = {"type": "Document", "id": doc}
    first = _create(client, m, subject_entity=subject, object_entity=None, save_as="proposed")
    assert first.status_code == 201, first.text

    duplicate = _create(client, m, subject_entity=subject, object_entity=None, save_as="proposed")

    assert duplicate.status_code == 409
    body = duplicate.json()
    assert isinstance(body["detail"], str)
    assert body["detail"].startswith("duplicate:")
    found = DUPLICATE_ID.search(body["detail"])
    assert found is not None, body["detail"]
    assert found.group(1) == first.json()["id"]
    # A structured id, if the API adds one, must name the same assertion.
    assert body.get("existing_assertion_id", first.json()["id"]) == first.json()["id"]


def test_similar_assertions_carry_the_id_the_page_links_to(client, db_session, matter_with_users):
    m = matter_with_users
    doc = _document(db_session, m)
    subject = {"type": "Document", "id": doc}
    existing = _create(
        client, m, subject_entity=subject, object_entity=None, assertion_type="INTERPRETS",
        proposition="Section 12 caps liability at twelve months of fees.", save_as="proposed",
    )
    assert existing.status_code == 201, existing.text

    created = _create(
        client, m, subject_entity=subject, object_entity=None, assertion_type="INTERPRETS",
        proposition="The cap in Section 12 excludes indemnities.",
    )

    assert created.status_code == 201, created.text
    body = created.json()
    entries = [e for e in body["similar_assertions"] if e["assertion_id"] == existing.json()["id"]]
    assert len(entries) == 1
    entry = entries[0]
    assert {"assertion_id", "match_kind", "score"} <= set(entry)
    assert isinstance(entry["score"], (int, float))
    # Display fields are optional for the page (it loads them when absent),
    # but when present they must describe the linked assertion.
    if "proposition" in entry:
        assert entry["proposition"] == existing.json()["proposition"]
    if "status" in entry:
        assert entry["status"] == "proposed"
    if "similar_assertions_total" in body:
        assert body["similar_assertions_total"] >= len(body["similar_assertions"])


def test_entity_listing_gives_each_source_its_type_and_pages_completely(client, db_session, matter_with_users):
    m = matter_with_users
    doc = _document(db_session, m)
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"], quote_text="Notices must be written.")
    article = seed_article(
        db_session, document_id=doc, matter_id=m["matter_id"], source_span_id=span, number="8", heading="Notices"
    )
    path = f"/api/v1/matters/{m['matter_id']}/entities"

    listing = client.get(path, headers=m["contributor_headers"])

    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] == 2
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id[doc]["type"] == "Document"
    assert by_id[article]["type"] == "Article"
    assert all(item["label"] for item in body["items"])
    # The page looks a linked id up page by page (offset += len(items)).
    seen = []
    offset = 0
    while offset < body["total"]:
        page = client.get(path, params={"limit": 1, "offset": offset}, headers=m["contributor_headers"]).json()
        assert page["items"], page
        seen += [item["id"] for item in page["items"]]
        offset += len(page["items"])
    assert sorted(seen) == sorted([doc, article])


def test_a_matter_without_documents_lists_no_entities(client, matter_with_users):
    m = matter_with_users
    listing = client.get(f"/api/v1/matters/{m['matter_id']}/entities", headers=m["contributor_headers"])
    assert listing.status_code == 200, listing.text
    assert listing.json() == {"items": [], "total": 0}


def test_a_flagged_new_assertion_type_is_stored_as_named(client, db_session, matter_with_users):
    m = matter_with_users
    subject = {"type": "Document", "id": _document(db_session, m)}

    refused = _create(client, m, subject_entity=subject, assertion_type="CANCELLED_BY")
    accepted = _create(
        client, m, subject_entity=subject, assertion_type="CANCELLED_BY", assertion_type_is_proposed_new=True
    )

    assert refused.status_code == 422
    assert "assertion_type_is_proposed_new" in refused.json()["detail"]
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["assertion_type"] == "CANCELLED_BY"
    detail = client.get(f"/api/v1/assertions/{accepted.json()['id']}", headers=m["contributor_headers"]).json()
    assert detail["assertion_type"] == "CANCELLED_BY"


def test_the_explanation_with_the_further_evidence_note_is_the_first_comment(client, db_session, matter_with_users):
    m = matter_with_users
    explanation = (
        "Clause 12 is the only cap.\n\n"
        "Further evidence needed: the author marked this assertion as needing more supporting evidence."
    )
    created = _create(
        client, m, subject_entity={"type": "Document", "id": _document(db_session, m)}, explanation=explanation
    )
    assert created.status_code == 201, created.text

    detail = client.get(f"/api/v1/assertions/{created.json()['id']}", headers=m["reviewer_headers"]).json()

    assert [c["comment_text_raw"] for c in detail["comments"]] == [explanation]


def test_frontend_assertion_type_list_mirrors_the_backend_vocabulary():
    source = FRONTEND_ASSERTION_TYPES_TS.read_text(encoding="utf-8")
    block = re.search(r"export const ASSERTION_TYPES[^=]*=\s*\[(.*?)\];", source, re.S)
    assert block is not None, "ASSERTION_TYPES not found in frontend/src/constants/assertionTypes.ts"
    frontend = re.findall(r'"([A-Z_]+)"', block.group(1))
    assert len(frontend) == len(set(frontend))
    assert set(frontend) == set(ALLOWED_ASSERTION_TYPES)
