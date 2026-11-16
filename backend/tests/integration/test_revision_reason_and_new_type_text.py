"""The revision reason and a proposed new assertion type follow the rules of
all other submitted text (review authoring:5).

Every other free-text field on the authoring path is length-capped on the
text as submitted and stored with active markup removed, keeping the exact
authored text next to it. `revision_reason` was copied verbatim into the
revision (a multi-megabyte reason with markup answered 200 and was served
to every viewer), and with `assertion_type_is_proposed_new` any text at all
was accepted as a type: markup, half a megabyte, or more than the 255
characters the column holds. A proposed new type must now have the shape
the Suggest form gives it (letters and digits in upper case, words joined
by single underscores, at most 100 characters); the reason is capped at
100,000 characters, stored sanitized, and its exact text kept in
`revision_reason_raw`.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.assertion import Assertion
from tests.conftest import assertion_payload, seed_document

OVER_CAP = "x" * 100_001
MARKUP_REASON = "<img src=x onerror=alert(1)><script>alert(2)</script>Fixed the clause number."


def _create(client, m, **overrides):
    return client.post("/api/v1/assertions", headers=m["contributor_headers"],
                       json=assertion_payload(m["matter_id"], m["repository_id"], **overrides))


def _created(client, m, **overrides) -> dict:
    r = _create(client, m, **overrides)
    assert r.status_code == 201, r.text
    return r.json()


def _revisions(client, m, assertion_id) -> list[dict]:
    r = client.get(f"/api/v1/assertions/{assertion_id}/revisions", headers=m["rater_headers"])
    assert r.status_code == 200, r.text
    return r.json()


# --- revision_reason ---------------------------------------------------------------------


@pytest.mark.parametrize("route", ["patch", "revisions"])
def test_a_reason_with_markup_is_stored_sanitized_with_its_exact_text_kept(client, matter_with_users, route):
    m = matter_with_users
    a = _created(client, m)
    body = {"proposition": "Clause 8.5 creates the exception.", "revision_reason": MARKUP_REASON}
    if route == "patch":
        r = client.patch(f"/api/v1/assertions/{a['id']}", json=body, headers=m["contributor_headers"])
        assert r.status_code == 200, r.text
    else:
        r = client.post(f"/api/v1/assertions/{a['id']}/revisions", json=body, headers=m["contributor_headers"])
        assert r.status_code == 201, r.text
        assert (r.json()["revision_reason"], r.json()["revision_reason_raw"]) == (
            "Fixed the clause number.", MARKUP_REASON)

    latest = _revisions(client, m, a["id"])[-1]
    assert latest["revision_number"] == 2
    assert latest["revision_reason"] == "Fixed the clause number."
    assert latest["revision_reason_raw"] == MARKUP_REASON
    detail = client.get(f"/api/v1/assertions/{a['id']}", headers=m["rater_headers"]).json()
    assert detail["revision_history"][-1]["revision_reason"] == "Fixed the clause number."


@pytest.mark.parametrize("route", ["patch", "revisions"])
def test_a_reason_over_the_cap_is_refused_and_creates_nothing(client, matter_with_users, route):
    m = matter_with_users
    a = _created(client, m)
    body = {"proposition": "Clause 8.5 creates the exception.", "revision_reason": OVER_CAP}
    send = client.patch if route == "patch" else client.post
    path = f"/api/v1/assertions/{a['id']}" + ("" if route == "patch" else "/revisions")

    r = send(path, json=body, headers=m["contributor_headers"])

    assert r.status_code == 422, r.text
    assert "revision_reason" in r.json()["detail"] and "100,000" in r.json()["detail"]
    assert [rev["revision_number"] for rev in _revisions(client, m, a["id"])] == [1]


def test_a_reason_at_the_cap_is_accepted(client, matter_with_users):
    m = matter_with_users
    a = _created(client, m)
    r = client.patch(f"/api/v1/assertions/{a['id']}", headers=m["contributor_headers"],
                     json={"proposition": "Clause 8.5 creates the exception.", "revision_reason": "y" * 100_000})
    assert r.status_code == 200, r.text
    assert _revisions(client, m, a["id"])[-1]["revision_reason"] == "y" * 100_000


def test_a_markup_only_or_blank_reason_stores_no_reason(client, matter_with_users):
    m = matter_with_users
    a = _created(client, m)
    for number, reason in ((2, "<script>alert(1)</script>"), (3, "   ")):
        r = client.patch(f"/api/v1/assertions/{a['id']}", headers=m["contributor_headers"],
                         json={"proposition": f"Clause 8.{number} creates the exception.", "revision_reason": reason})
        assert r.status_code == 200, r.text
    second, third = _revisions(client, m, a["id"])[1:]
    assert (second["revision_reason"], second["revision_reason_raw"]) == (None, "<script>alert(1)</script>")
    assert (third["revision_reason"], third["revision_reason_raw"]) == (None, None)


def test_a_reason_alone_over_the_cap_is_refused(client, matter_with_users):
    """A reason with nothing else is not a change, but it is still checked."""
    m = matter_with_users
    a = _created(client, m)
    r = client.patch(f"/api/v1/assertions/{a['id']}", json={"revision_reason": OVER_CAP},
                     headers=m["contributor_headers"])
    assert r.status_code == 422, r.text


def test_initial_revisions_have_no_authored_reason(client, matter_with_users):
    m = matter_with_users
    a = _created(client, m)
    (first,) = _revisions(client, m, a["id"])
    assert (first["revision_reason"], first["revision_reason_raw"]) == ("initial creation", None)


# --- proposed new assertion types ---------------------------------------------------------


@pytest.mark.parametrize("assertion_type", [
    "<script>alert(3)</script>" + "T" * 500_000,
    "<img src=x onerror=alert(9)>",
    "T" * 101,
    "cancelled_by",
    "CANCELLED BY",
    "CANCELLED__BY",
    "_CANCELLED_BY",
    "CANCELLED-BY",
])
@pytest.mark.parametrize("route", ["/api/v1/assertions", "/api/v1/agent/assertions"])
def test_a_proposed_new_type_must_have_the_vocabulary_s_shape(client, db_session, matter_with_users,
                                                             assertion_type, route):
    m = matter_with_users
    body = assertion_payload(m["matter_id"], m["repository_id"], assertion_type=assertion_type,
                             assertion_type_is_proposed_new=True)
    if route.startswith("/api/v1/agent"):  # agents name persisted entities only
        doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
        body.update(agent={"platform": "pytest"}, subject_entity={"type": "Document", "id": doc}, object_entity=None)

    r = client.post(route, json=body, headers=m["contributor_headers"])

    assert r.status_code == 422, r.text
    assert "proposed new assertion_type" in r.json()["detail"]
    assert db_session.scalar(select(func.count()).select_from(Assertion)) == 0


@pytest.mark.parametrize("assertion_type", ["CANCELLED_BY", "T" * 100, "SECTION_12A", "מבוטל_על_ידי", "ÜBERSCHREIBT"])
def test_a_well_formed_proposed_new_type_is_accepted(client, matter_with_users, assertion_type):
    m = matter_with_users
    created = _created(client, m, assertion_type=assertion_type, assertion_type_is_proposed_new=True)
    assert created["assertion_type"] == assertion_type


def test_an_edit_to_a_proposed_new_type_follows_the_same_rule(client, matter_with_users):
    m = matter_with_users
    a = _created(client, m)
    path = f"/api/v1/assertions/{a['id']}"
    refused = client.patch(path, headers=m["contributor_headers"],
                           json={"assertion_type": "<b>X</b>" + "Y" * 300, "assertion_type_is_proposed_new": True})
    assert refused.status_code == 422, refused.text
    assert "proposed new assertion_type" in refused.json()["detail"]
    accepted = client.patch(path, headers=m["contributor_headers"],
                            json={"assertion_type": "QUALIFIES", "assertion_type_is_proposed_new": True})
    assert (accepted.status_code, accepted.json()["assertion_type"]) == (200, "QUALIFIES")


def test_a_stored_type_that_predates_the_rule_is_kept_by_edits(client, db_session, matter_with_users):
    """An assertion keeps its own type, as before: the rule applies to a new type."""
    m = matter_with_users
    a = _created(client, m)
    db_session.execute(Assertion.__table__.update().where(Assertion.id == a["id"]).values(
        assertion_type="legacy type"))
    db_session.commit()
    r = client.patch(f"/api/v1/assertions/{a['id']}", headers=m["contributor_headers"],
                     json={"assertion_type": "legacy type", "proposition": "Clause 8.5 creates the exception."})
    assert (r.status_code, r.json()["assertion_type"]) == (200, "legacy type")
