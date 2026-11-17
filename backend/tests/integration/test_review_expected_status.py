"""`expected_status` on review decisions (acceptance run 2, item 1).

A change of status creates no new revision, so `expected_revision_number`
alone let a decision sent from an out-of-date page overwrite another
reviewer's decision: reviewer A had X open as proposed at revision 1, a second
reviewer accepted X (still revision 1), and A's Reject then turned the
acceptance into a rejection without any warning. Every decision body
(accept, reject, dispute, request-revision, supersede) may now name the status
the reviewer saw as `expected_status`. When the assertion no longer has it, the
decision is refused with 409 before anything changes, also when the change
commits while the decision waits for the write lock. The field is optional,
like `expected_revision_number` (spec addendum "Review decision rules").
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.models.audit_event import AuditEvent
from tests.conftest import auth_header, seed_matter_role, seed_user
from tests.integration.test_review_decision_rules import (
    EVENT_TYPE,
    _author_notifications,
    _body_for,
    _comment_rows,
    _create,
    _history_event,
    _interleave_after_load,
    _post,
    _supported,
)

ACTIONS = ["accept", "reject", "dispute", "request-revision", "supersede"]
RESULT = {
    "accept": "accepted",
    "reject": "rejected",
    "dispute": "disputed",
    "request-revision": "revision_requested",
    "supersede": "superseded",
}
# What a second reviewer decides meanwhile: a status the action can still be
# recorded from, so only the status the first reviewer saw is out of date.
MEANWHILE = {
    "accept": "dispute",
    "reject": "accept",
    "dispute": "accept",
    "request-revision": "accept",
    "supersede": "accept",
}
STATUS_CHANGED = "assertion status has changed since expected_status"
ALL_STATUSES = {
    "draft", "proposed", "revision_requested", "accepted",
    "rejected", "disputed", "superseded", "withdrawn",
}


@pytest.fixture()
def other_reviewer(db_session, matter_with_users) -> dict:
    """Headers of a second reviewer of the matter."""
    user_id = seed_user(db_session, display_name="Second reviewer")
    seed_matter_role(
        db_session, user_id=user_id, matter_id=matter_with_users["matter_id"], role="reviewer"
    )
    return auth_header(user_id)


def _decision_body(client, db_session, m, action, **seen) -> dict:
    """A valid body for `action` that names what the reviewer saw (`seen`)."""
    body = _body_for(action, **seen)
    if action == "supersede":
        body["superseded_by_assertion_id"] = _supported(client, db_session, m)
    return body


def _decide_meanwhile(client, db_session, m, headers, assertion_id, action) -> str:
    """Another reviewer records `action`; returns the status it leaves."""
    r = _post(
        client, assertion_id, action, headers,
        _decision_body(client, db_session, m, action, expected_revision_number=1),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == RESULT[action]
    return RESULT[action]


def _state(db_session, assertion_id) -> dict:
    """Everything a decision writes on the assertion row."""
    row = db_session.execute(
        text(
            "SELECT status, reviewed_by, reviewed_at, updated_at, current_revision_number, "
            "superseded_by_assertion_id FROM assertions WHERE id = :id"
        ),
        {"id": assertion_id},
    ).mappings().one()
    return dict(row)


def _audit_ids(db_session, assertion_id) -> set[str]:
    return set(
        db_session.scalars(select(AuditEvent.id).where(AuditEvent.assertion_id == assertion_id))
    )


def _assert_nothing_changed(client, db_session, m, assertion_id, before: dict) -> None:
    assert _state(db_session, assertion_id) == before["state"]
    assert _audit_ids(db_session, assertion_id) == before["audit"], "no audit row"
    assert _comment_rows(db_session, assertion_id) == before["comments"], "no comment left behind"
    assert _author_notifications(client, m, assertion_id) == before["notifications"], (
        "no notification"
    )


def _snapshot(client, db_session, m, assertion_id) -> dict:
    return {
        "state": _state(db_session, assertion_id),
        "audit": _audit_ids(db_session, assertion_id),
        "comments": _comment_rows(db_session, assertion_id),
        "notifications": _author_notifications(client, m, assertion_id),
    }


# --- the acceptance failure: a decision from a page that shows an old status --


@pytest.mark.parametrize("action", ACTIONS)
def test_a_decision_on_a_status_that_changed_meanwhile_is_refused_and_changes_nothing(
    client, matter_with_users, db_session, other_reviewer, action
):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)  # the page shows it proposed, revision 1
    now = _decide_meanwhile(client, db_session, m, other_reviewer, assertion_id, MEANWHILE[action])
    body = _decision_body(
        client, db_session, m, action, expected_revision_number=1, expected_status="proposed"
    )
    before = _snapshot(client, db_session, m, assertion_id)

    r = _post(client, assertion_id, action, m["reviewer_headers"], body)

    assert r.status_code == 409, r.text
    assert r.json()["detail"] == f"{STATUS_CHANGED}: it is now '{now}'"
    _assert_nothing_changed(client, db_session, m, assertion_id, before)


@pytest.mark.parametrize("action", ACTIONS)
def test_a_decision_on_the_status_the_reviewer_saw_is_recorded(
    client, matter_with_users, db_session, action
):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)

    r = _post(
        client, assertion_id, action, m["reviewer_headers"],
        _decision_body(
            client, db_session, m, action, expected_revision_number=1, expected_status="proposed"
        ),
    )

    assert r.status_code == 200, r.text
    assert r.json()["status"] == RESULT[action]
    event = _history_event(client, m, assertion_id, EVENT_TYPE[action])
    assert event["previous_value"] == "proposed"
    assert event["assertion_revision_number"] == 1


@pytest.mark.parametrize("action", ACTIONS)
def test_a_reviewer_shown_the_new_status_can_decide_on_it(
    client, matter_with_users, db_session, other_reviewer, action
):
    """Re-review stays open: the refusal is about what the page showed."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    now = _decide_meanwhile(client, db_session, m, other_reviewer, assertion_id, MEANWHILE[action])

    r = _post(
        client, assertion_id, action, m["reviewer_headers"],
        _decision_body(client, db_session, m, action, expected_revision_number=1, expected_status=now),
    )

    assert r.status_code == 200, r.text
    assert r.json()["status"] == RESULT[action]


@pytest.mark.parametrize("action", ACTIONS)
def test_a_status_change_committed_while_the_decision_waits_for_the_lock_is_refused(
    client, app, matter_with_users, db_session, monkeypatch, action
):
    """The status the reviewer saw is checked again under the write lock: a
    decision that commits between this request's checks and its lock gets
    the same reason, not the generic "changed by another request"."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    body = _decision_body(
        client, db_session, m, action, expected_revision_number=1, expected_status="proposed"
    )
    before = _snapshot(client, db_session, m, assertion_id)
    now = RESULT[MEANWHILE[action]]
    # The other decision, committed right after this request loaded the row.
    _interleave_after_load(
        monkeypatch, app,
        "UPDATE assertions SET status = :now, reviewed_by = :other WHERE id = :id",
        {"id": assertion_id, "now": now, "other": m["rater_id"]},
    )

    r = _post(client, assertion_id, action, m["reviewer_headers"], body)

    assert r.status_code == 409, r.text
    assert r.json()["detail"] == f"{STATUS_CHANGED}: it is now '{now}'"
    before["state"] = {**before["state"], "status": now, "reviewed_by": m["rater_id"]}
    _assert_nothing_changed(client, db_session, m, assertion_id, before)


@pytest.mark.parametrize("action", ACTIONS)
def test_expected_status_is_optional_and_null_checks_nothing(
    client, matter_with_users, db_session, other_reviewer, action
):
    """Like expected_revision_number: API clients that do not send it, or send
    null, keep moving an assertion between the reviewed statuses."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    _decide_meanwhile(client, db_session, m, other_reviewer, assertion_id, MEANWHILE[action])

    r = _post(
        client, assertion_id, action, m["reviewer_headers"],
        _decision_body(client, db_session, m, action, expected_revision_number=1, expected_status=None),
    )

    assert r.status_code == 200, r.text
    assert r.json()["status"] == RESULT[action]


@pytest.mark.parametrize("value", ["approved", "Proposed", ""])
@pytest.mark.parametrize("action", ACTIONS)
def test_expected_status_must_be_an_assertion_status(
    client, matter_with_users, db_session, action, value
):
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    body = _decision_body(client, db_session, m, action, expected_status=value)
    before = _snapshot(client, db_session, m, assertion_id)

    r = _post(client, assertion_id, action, m["reviewer_headers"], body)

    assert r.status_code == 422, r.text
    _assert_nothing_changed(client, db_session, m, assertion_id, before)


# --- where the new 409 ranks ---------------------------------------------------


def test_a_stale_status_ranks_after_404_and_403_and_before_422(
    client, matter_with_users, db_session, other_reviewer
):
    m = matter_with_users
    stale = {"expected_revision_number": 1, "expected_status": "proposed"}
    assert _post(client, str(uuid.uuid4()), "accept", m["reviewer_headers"], stale).status_code == 404

    # No supporting evidence, disputed meanwhile: an acceptance without a
    # justification would also be refused with 422.
    assertion_id = _create(client, m)
    assert _post(client, assertion_id, "dispute", other_reviewer).status_code == 200
    assert _post(client, assertion_id, "accept", m["outsider_headers"], stale).status_code == 403
    assert _post(client, assertion_id, "accept", m["contributor_headers"], stale).status_code == 403
    refused = _post(client, assertion_id, "accept", m["reviewer_headers"], stale)
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == f"{STATUS_CHANGED}: it is now 'disputed'"
    # Shown the current status, only the missing justification is left.
    current = _post(
        client, assertion_id, "accept", m["reviewer_headers"],
        {"expected_revision_number": 1, "expected_status": "disputed"},
    )
    assert current.status_code == 422, current.text
    assert _state(db_session, assertion_id)["status"] == "disputed"


def test_an_edit_is_reported_before_the_status_it_changed(
    client, matter_with_users, db_session, other_reviewer
):
    """A material edit returns an accepted assertion to proposed: the revision
    is the more telling reason, so a decision that is stale on both says it
    was edited."""
    m = matter_with_users
    assertion_id = _supported(client, db_session, m)
    assert _post(client, assertion_id, "accept", other_reviewer).status_code == 200
    edit = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": f"Edited after acceptance {uuid.uuid4()}.", "expected_revision_number": 1},
        headers=other_reviewer,
    )
    assert edit.status_code == 200, edit.text
    assert (edit.json()["status"], edit.json()["current_revision_number"]) == ("proposed", 2)

    r = _post(
        client, assertion_id, "reject", m["reviewer_headers"],
        {"expected_revision_number": 1, "expected_status": "accepted"},
    )

    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "assertion has been modified since expected_revision_number"
    assert _state(db_session, assertion_id)["status"] == "proposed"


def test_a_repeat_or_a_status_that_takes_no_decision_keeps_its_own_reason(
    client, matter_with_users, db_session, other_reviewer
):
    """The status-specific refusals name what happened more precisely, so they
    come first: the same decision made meanwhile, or a withdrawal."""
    m = matter_with_users
    seen = {"expected_revision_number": 1, "expected_status": "proposed"}
    accepted_id = _supported(client, db_session, m)
    assert _post(client, accepted_id, "accept", other_reviewer).status_code == 200
    repeat = _post(client, accepted_id, "accept", m["reviewer_headers"], seen)
    assert repeat.status_code == 409, repeat.text
    assert repeat.json()["detail"] == "assertion is already 'accepted'"

    withdrawn_id = _supported(client, db_session, m)
    withdraw = client.post(
        f"/api/v1/assertions/{withdrawn_id}/withdraw", headers=m["contributor_headers"]
    )
    assert withdraw.status_code == 200, withdraw.text
    refused = _post(client, withdrawn_id, "reject", m["reviewer_headers"], seen)
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == "cannot reject an assertion in status 'withdrawn'"


# --- the API docs ----------------------------------------------------------------


def _schema(spec: dict, node: dict) -> dict:
    """The object schema `node` names, through an optional-body anyOf."""
    for option in node.get("anyOf", [node]):
        ref = option.get("$ref")
        if ref:
            return spec["components"]["schemas"][ref.rsplit("/", 1)[1]]
    raise AssertionError(f"no schema reference in {node}")


@pytest.mark.parametrize("action", ACTIONS)
def test_the_api_docs_describe_both_fields_on_every_decision(client, action):
    spec = client.get("/openapi.json").json()
    operation = spec["paths"][f"/api/v1/assertions/{{assertion_id}}/{action}"]["post"]
    body = _schema(spec, operation["requestBody"]["content"]["application/json"]["schema"])
    status = body["properties"]["expected_status"]
    revision = body["properties"]["expected_revision_number"]

    assert "expected_status" not in body.get("required", [])
    enums = [option["enum"] for option in status["anyOf"] if "enum" in option]
    assert len(enums) == 1 and set(enums[0]) == ALL_STATUSES
    assert "409" in status["description"] and "status" in status["description"]
    assert "409" in revision["description"] and "revision" in revision["description"]


def _docs_example(spec: dict, schema: dict):
    """The example value /docs and /redoc show for `schema`, and that Swagger
    UI's "Try it out" starts from, for the shapes the decision bodies use.

    Both bundled pages (app/static/api-docs: Swagger UI 5, and Redoc 2 with
    openapi-sampler) take a schema's own example first, `examples[0]`;
    without one, the first alternative of an anyOf, an enum's first value,
    an integer's minimum (else 0) and "string" for text."""
    if schema.get("examples"):
        return schema["examples"][0]
    ref = schema.get("$ref")
    if ref:
        return _docs_example(spec, spec["components"]["schemas"][ref.rsplit("/", 1)[1]])
    for combined in ("oneOf", "anyOf"):
        if schema.get(combined):
            return _docs_example(spec, schema[combined][0])
    if schema.get("enum"):
        return schema["enum"][0]
    if "properties" in schema:
        return {name: _docs_example(spec, sub) for name, sub in schema["properties"].items()}
    return {"integer": int(schema.get("minimum", 0)), "string": "string"}.get(schema.get("type"))


@pytest.mark.parametrize("action", ACTIONS)
def test_the_api_docs_example_body_records_the_decision_on_a_new_proposal(
    client, matter_with_users, db_session, action
):
    """Acceptance run 2, second round: with no example of its own,
    expected_status was shown as the enum's first value, 'draft', a status no
    decision applies to. Try it out's body was therefore always refused with
    409 "assertion status has changed since expected_status: it is now
    'proposed'" although nothing had changed; before the field existed, the
    same body recorded the decision. The docs now name what a new proposal
    has: revision 1 and the status 'proposed'."""
    m = matter_with_users
    spec = client.get("/openapi.json").json()
    operation = spec["paths"][f"/api/v1/assertions/{{assertion_id}}/{action}"]["post"]
    body = _docs_example(spec, operation["requestBody"]["content"]["application/json"]["schema"])
    assertion_id = _supported(client, db_session, m)  # proposed, revision 1
    if action == "supersede":  # the docs can only show a placeholder id
        body["superseded_by_assertion_id"] = _supported(client, db_session, m)

    r = _post(client, assertion_id, action, m["reviewer_headers"], body)

    assert r.status_code == 200, (body, r.text)
    assert r.json()["status"] == RESULT[action]
    assert (body["expected_revision_number"], body["expected_status"]) == (1, "proposed")
