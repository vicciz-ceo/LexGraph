"""RED tests for jurisdiction validation at the API (sprint
2026-08-02-us-state-law, gate G5): "the API rejects a value outside the
controlled vocabulary."

Live-path requirement: every request below goes through the REAL
`POST /api/v1/assertions`, `PATCH /api/v1/assertions/{id}`, and
`POST /api/v1/assertions/{id}/revisions` routes via the `client` TestClient
fixture -- exactly `backend/app/routers/assertions.py`'s production code
path, never a mocked/stubbed validator.

Today (pre-Developer): `assertions.py` accepts ANY string for
`jurisdiction` with no allow-list at all (recon dossier §3) -- these tests
are RED because a currently-invalid-per-the-new-vocabulary value like
`"US-ZZ"` is currently ACCEPTED (2xx), not rejected (422).
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def test_create_assertion_rejects_jurisdiction_outside_the_vocabulary(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], jurisdiction="US-ZZ")
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 422
    assert "jurisdiction" in r.text.lower()


def test_create_assertion_accepts_a_real_controlled_vocabulary_code(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], jurisdiction="US-DE")
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201
    assert r.json()["jurisdiction"] == "US-DE"


def test_create_assertion_still_accepts_null_jurisdiction(client, matter_with_users):
    """Jurisdiction stays OPTIONAL (spec/model: nullable) -- the vocabulary
    constrains which non-null values are legal, it does not make the field
    required. This is a not-yet-broken guard: it should already pass
    today, and MUST keep passing once validation is added."""
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], jurisdiction=None)
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201
    assert r.json()["jurisdiction"] is None


def test_patch_assertion_rejects_jurisdiction_outside_the_vocabulary(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"jurisdiction": "not-a-real-code"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_create_revision_rejects_jurisdiction_outside_the_vocabulary(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/revisions",
        json={
            "proposition": "Revised proposition text for the jurisdiction revision test.",
            "jurisdiction": "XX-99",
        },
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_list_assertions_rejects_jurisdiction_query_param_outside_the_vocabulary(
    client, matter_with_users
):
    """`GET /api/v1/assertions?jurisdiction=...` (assertions.py:625/647)
    filters with no validation today -- an unknown code should 422, not
    silently return an (empty) result set that looks like "no matches"."""
    m = matter_with_users
    r = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "jurisdiction": "ZZ-ZZ"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 422


def test_jurisdictions_endpoint_serves_the_canonical_list(client, matter_with_users):
    """G5 + R5's frontend-drift-prevention call: the frontend gets the
    controlled vocabulary from a real endpoint (not a hand-maintained
    mirror) so it cannot drift from the backend's canonical list. Route
    does not exist yet today -- RED via 404."""
    m = matter_with_users
    r = client.get("/api/v1/jurisdictions", headers=m["contributor_headers"])
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert "IL" in body
    assert "US-DE" in body
    assert "US-FED" in body
    assert len(body) == 54
