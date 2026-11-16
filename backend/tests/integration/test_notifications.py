"""B6 — in-app notifications (spec §15, ruling R4: in-app only, no email/push).

Owning track: B6. Read surface assumed at GET /api/v1/notifications
(scoped to the caller via the auth seam) — not enumerated verbatim in
spec §13; Planner assumption documented here for QA to reconcile against
whatever path B6 actually ships.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def test_submission_notifies_reviewers(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])

    r = client.get("/api/v1/notifications", headers=m["reviewer_headers"])
    assert r.status_code == 200
    kinds = [n["event_type"] for n in r.json()]
    assert "assertion_submitted" in kinds


def test_acceptance_notifies_author(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    client.post(f"/api/v1/assertions/{assertion_id}/accept", json={"acceptance_justification": "Accepted for test setup."}, headers=m["reviewer_headers"])

    r = client.get("/api/v1/notifications", headers=m["contributor_headers"])
    assert r.status_code == 200
    kinds = [n["event_type"] for n in r.json()]
    assert "assertion_accepted" in kinds


def test_every_individual_rating_does_not_generate_a_notification_by_default(client, matter_with_users, db_session):
    """Spec §15: 'Do not send a notification for every rating by default.'"""
    from tests.conftest import seed_user, seed_matter_role, auth_header

    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])

    for i in range(3):
        rater = seed_user(db_session, display_name=f"Rater {i}")
        seed_matter_role(db_session, user_id=rater, matter_id=m["matter_id"], role="contributor")
        client.put(
            f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
            json={"strength": 4, "rationale": None},
            headers=auth_header(rater),
        )

    r = client.get("/api/v1/notifications", headers=m["contributor_headers"])
    rating_notifications = [n for n in r.json() if n["event_type"] == "assertion_rated"]
    assert len(rating_notifications) == 0


def test_notifications_are_matter_scoped(client, matter_with_users):
    m = matter_with_users
    r = client.get("/api/v1/notifications", headers=m["outsider_headers"])
    assert r.status_code == 200
    assert r.json() == []


def test_reviewer_of_another_matter_does_not_see_this_matters_submission_notification(
    client, db_session
):
    """QA regression (2026-07-26): strengthens matter-scoping coverage --
    the existing test above only proves a user with NO role anywhere gets
    an empty list. This proves a reviewer WHO IS a real reviewer, just on
    a different matter, never receives a notification meant for a
    different matter's reviewers (app/notification_hooks.py derives
    recipients from `matter_roles WHERE matter_id = ...`)."""
    from tests.conftest import (
        seed_organization,
        seed_repository,
        seed_matter,
        seed_user,
        seed_matter_role,
        auth_header,
    )

    org = seed_organization(db_session)
    repo = seed_repository(db_session, organization_id=org)
    matter_a = seed_matter(db_session, repository_id=repo, name="Matter A")
    matter_b = seed_matter(db_session, repository_id=repo, name="Matter B")

    contributor_a = seed_user(db_session, display_name="Contributor A")
    reviewer_a = seed_user(db_session, display_name="Reviewer A")
    reviewer_b = seed_user(db_session, display_name="Reviewer B (matter B only)")

    seed_matter_role(db_session, user_id=contributor_a, matter_id=matter_a, role="contributor")
    seed_matter_role(db_session, user_id=reviewer_a, matter_id=matter_a, role="reviewer")
    seed_matter_role(db_session, user_id=reviewer_b, matter_id=matter_b, role="reviewer")

    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(matter_a, repo, save_as="draft"),
        headers=auth_header(contributor_a),
    )
    assertion_id = create.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=auth_header(contributor_a))

    r_a = client.get("/api/v1/notifications", headers=auth_header(reviewer_a))
    r_b = client.get("/api/v1/notifications", headers=auth_header(reviewer_b))
    assert any(n["event_type"] == "assertion_submitted" for n in r_a.json())
    assert not any(n["event_type"] == "assertion_submitted" for n in r_b.json())


# --- 2026-11-16: every submission path, the other spec §15 triggers, read
# state, link/context and the durable store (findings ui:6, ui:7, api:12,
# pipeline:4, pipeline:9). -------------------------------------------------

import pytest  # noqa: E402

from tests.conftest import (  # noqa: E402
    auth_header,
    seed_document,
    seed_matter,
    seed_matter_role,
    seed_source_span,
    seed_user,
)


@pytest.fixture()
def team(matter_with_users, db_session):
    """matter_with_users plus an admin, a persisted document and a source span."""
    m = dict(matter_with_users)
    admin_id = seed_user(db_session, display_name="Admin A")
    seed_matter_role(db_session, user_id=admin_id, matter_id=m["matter_id"], role="admin")
    document_id = seed_document(
        db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title="Master Agreement"
    )
    span_id = seed_source_span(
        db_session, document_id=document_id, matter_id=m["matter_id"], quote_text="Clause 8.4 applies."
    )
    m.update(admin_id=admin_id, admin_headers=auth_header(admin_id), document_id=document_id, span_id=span_id)
    return m


def _feed(client, headers, **params) -> list[dict]:
    r = client.get("/api/v1/notifications", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _about(client, headers, assertion_id: str) -> list[dict]:
    return [n for n in _feed(client, headers) if n["payload"].get("assertion_id") == assertion_id]


def _kinds(client, headers, assertion_id: str) -> list[str]:
    return [n["event_type"] for n in _about(client, headers, assertion_id)]


def _create(client, m, headers, *, proposition: str, save_as: str = "proposed", **overrides) -> dict:
    payload = assertion_payload(
        m["matter_id"], m["repository_id"], proposition=proposition, save_as=save_as, **overrides
    )
    r = client.post("/api/v1/assertions", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _unread(client, headers) -> int:
    r = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["unread_count"]


# --- every path that makes an assertion proposed notifies the reviewers ------


def test_creating_as_proposed_notifies_every_reviewer_and_admin_once(client, team):
    """The Suggest form's 'Submit for review' is ONE POST with save_as=proposed."""
    m = team
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    created = r.json()
    assert created["status"] == "proposed" and "similar_assertions" in created  # body intact

    assert _kinds(client, m["reviewer_headers"], created["id"]) == ["assertion_submitted"]
    assert _kinds(client, m["admin_headers"], created["id"]) == ["assertion_submitted"]
    for who in ("contributor_headers", "rater_headers", "outsider_headers"):
        assert _about(client, m[who], created["id"]) == []
    notice = _about(client, m["reviewer_headers"], created["id"])[0]
    assert notice["actor_user_id"] == m["contributor_id"]
    assert notice["payload"]["previous_status"] is None


def test_agent_endpoint_proposal_notifies_reviewers_but_an_agent_draft_does_not(client, team):
    m = team
    body = {
        "repository_id": m["repository_id"],
        "matter_id": m["matter_id"],
        "assertion_type": "APPLIES_TO",
        "proposition": "The survival clause covers confidentiality.",
        "subject_entity": {"type": "Document", "id": m["document_id"]},
        "evidence": [{"source_span_id": m["span_id"], "evidence_role": "supports"}],
        "agent": {"platform": "codex", "model": "test-model"},
    }
    proposed = client.post("/api/v1/agent/assertions", json=body, headers=m["contributor_headers"])
    assert proposed.status_code == 201, proposed.text
    assert proposed.json()["status"] == "proposed"
    assert _kinds(client, m["reviewer_headers"], proposed.json()["id"]) == ["assertion_submitted"]
    assert _kinds(client, m["admin_headers"], proposed.json()["id"]) == ["assertion_submitted"]

    draft = client.post(
        "/api/v1/agent/assertions",
        json={**body, "proposition": "An agent draft.", "save_as": "draft"},
        headers=m["contributor_headers"],
    )
    assert draft.status_code == 201, draft.text
    assert _about(client, m["reviewer_headers"], draft.json()["id"]) == []


def test_saving_a_draft_notifies_nobody(client, team):
    m = team
    draft = _create(client, m, m["contributor_headers"], proposition="Only a draft.", save_as="draft")
    for who in ("reviewer_headers", "admin_headers", "contributor_headers", "rater_headers"):
        assert _about(client, m[who], draft["id"]) == []


def test_refused_creations_notify_nobody(client, team):
    m = team
    first = _create(client, m, m["contributor_headers"], proposition="Clause 9 limits assignment.")
    duplicate = client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            m["matter_id"], m["repository_id"], proposition="Clause 9 limits assignment.", save_as="proposed"
        ),
        headers=m["contributor_headers"],
    )
    assert duplicate.status_code == 409
    outsider = client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            m["matter_id"], m["repository_id"], proposition="Outsider claim.", save_as="proposed"
        ),
        headers=m["outsider_headers"],
    )
    assert outsider.status_code == 403
    assert [n["payload"]["assertion_id"] for n in _feed(client, m["reviewer_headers"])] == [first["id"]]


def test_resubmitting_after_a_revision_request_notifies_the_reviewers_again(client, team):
    m = team
    draft = _create(client, m, m["contributor_headers"], proposition="Needs another pass.", save_as="draft")
    assert client.post(f"/api/v1/assertions/{draft['id']}/submit", headers=m["contributor_headers"]).status_code == 200
    r = client.post(
        f"/api/v1/assertions/{draft['id']}/request-revision",
        json={"comment": "Cite the clause."},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    assert _kinds(client, m["contributor_headers"], draft["id"]) == ["revision_requested"]

    assert client.post(f"/api/v1/assertions/{draft['id']}/submit", headers=m["contributor_headers"]).status_code == 200

    notices = _about(client, m["reviewer_headers"], draft["id"])
    assert [n["event_type"] for n in notices] == ["assertion_submitted", "assertion_submitted"]
    assert notices[0]["payload"]["previous_status"] == "revision_requested"  # newest first
    assert notices[1]["payload"]["previous_status"] == "draft"


def test_submitting_an_already_proposed_assertion_does_not_notify_again(client, team):
    m = team
    draft = _create(client, m, m["contributor_headers"], proposition="Submitted twice.", save_as="draft")
    for _ in range(2):
        assert client.post(
            f"/api/v1/assertions/{draft['id']}/submit", headers=m["contributor_headers"]
        ).status_code == 200
    assert _kinds(client, m["reviewer_headers"], draft["id"]) == ["assertion_submitted"]


def test_creation_as_proposed_stays_inside_its_matter(client, db_session, team):
    m = team
    other_matter = seed_matter(db_session, repository_id=m["repository_id"], name="Other matter")
    other_reviewer = seed_user(db_session, display_name="Other reviewer")
    seed_matter_role(db_session, user_id=other_reviewer, matter_id=other_matter, role="reviewer")
    created = _create(client, m, m["contributor_headers"], proposition="Matter-local claim.")
    assert _kinds(client, m["reviewer_headers"], created["id"]) == ["assertion_submitted"]
    assert _feed(client, auth_header(other_reviewer)) == []


# --- the actor is never notified about their own action -----------------------


def test_actors_are_not_notified_about_their_own_actions(client, team):
    m = team
    own = _create(
        client,
        m,
        m["reviewer_headers"],
        proposition="A reviewer's own claim.",
        evidence=[{"source_span_id": m["span_id"], "evidence_role": "supports"}],
    )
    assert _kinds(client, m["admin_headers"], own["id"]) == ["assertion_submitted"]
    r = client.post(f"/api/v1/assertions/{own['id']}/accept", json={}, headers=m["reviewer_headers"])
    assert r.status_code == 200
    assert _about(client, m["reviewer_headers"], own["id"]) == []


# --- the other spec §15 triggers ------------------------------------------------


def test_a_reviewer_edit_notifies_the_author_and_other_reviewers_while_proposed(client, team):
    m = team
    created = _create(client, m, m["contributor_headers"], proposition="Original wording.")
    r = client.patch(
        f"/api/v1/assertions/{created['id']}",
        json={"proposition": "Reviewer's wording.", "expected_revision_number": 1},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200 and r.json()["current_revision_number"] == 2

    author_notice = _about(client, m["contributor_headers"], created["id"])
    assert [n["event_type"] for n in author_notice] == ["revision_created"]
    assert author_notice[0]["payload"]["revision_number"] == 2
    assert author_notice[0]["payload"]["previous_revision_number"] == 1
    assert _kinds(client, m["admin_headers"], created["id"]) == ["revision_created", "assertion_submitted"]
    assert _kinds(client, m["reviewer_headers"], created["id"]) == ["assertion_submitted"]  # not their own edit

    r = client.post(
        f"/api/v1/assertions/{created['id']}/revisions",
        json={"proposition": "Third wording.", "revision_reason": "tighten"},
        headers=m["admin_headers"],
    )
    assert r.status_code == 201
    assert _kinds(client, m["contributor_headers"], created["id"]) == ["revision_created", "revision_created"]
    assert _kinds(client, m["reviewer_headers"], created["id"]) == ["revision_created", "assertion_submitted"]


def test_an_edit_that_creates_no_revision_notifies_nobody(client, team):
    m = team
    created = _create(client, m, m["contributor_headers"], proposition="Unchanged claim.")
    r = client.patch(f"/api/v1/assertions/{created['id']}", json={}, headers=m["reviewer_headers"])
    assert r.status_code == 200 and r.json()["current_revision_number"] == 1
    assert _about(client, m["contributor_headers"], created["id"]) == []


def test_editing_an_accepted_assertion_sends_it_back_to_the_reviewers(client, team):
    """Spec §3: editing an accepted assertion creates a new proposed revision."""
    m = team
    created = _create(
        client,
        m,
        m["contributor_headers"],
        proposition="Accepted, then edited.",
        evidence=[{"source_span_id": m["span_id"], "evidence_role": "supports"}],
    )
    assert client.post(f"/api/v1/assertions/{created['id']}/accept", json={}, headers=m["reviewer_headers"]).status_code == 200
    r = client.patch(
        f"/api/v1/assertions/{created['id']}",
        json={"proposition": "Accepted, then edited by the admin."},
        headers=m["admin_headers"],
    )
    assert r.status_code == 200 and r.json()["status"] == "proposed"

    to_reviewer = _about(client, m["reviewer_headers"], created["id"])[0]
    assert to_reviewer["event_type"] == "revision_created"
    assert (to_reviewer["payload"]["previous_status"], to_reviewer["payload"]["status"]) == ("accepted", "proposed")
    assert _kinds(client, m["contributor_headers"], created["id"]) == ["revision_created", "assertion_accepted"]


def test_added_evidence_notifies_participants_and_reviewers_while_proposed(client, team):
    m = team
    created = _create(client, m, m["contributor_headers"], proposition="Evidence will follow.")
    r = client.post(
        f"/api/v1/assertions/{created['id']}/evidence",
        json={"source_span_id": m["span_id"], "evidence_role": "supports"},
        headers=m["rater_headers"],
    )
    assert r.status_code == 201
    evidence_id = r.json()["id"]

    notice = _about(client, m["contributor_headers"], created["id"])
    assert [n["event_type"] for n in notice] == ["evidence_added"]
    assert notice[0]["payload"]["evidence_id"] == evidence_id
    assert notice[0]["payload"]["evidence_role"] == "supports"
    assert _kinds(client, m["reviewer_headers"], created["id"]) == ["evidence_added", "assertion_submitted"]
    assert _about(client, m["rater_headers"], created["id"]) == []  # their own action

    # The author attaching evidence to their own draft tells nobody.
    draft = _create(client, m, m["contributor_headers"], proposition="Private draft.", save_as="draft")
    r = client.post(
        f"/api/v1/assertions/{draft['id']}/evidence",
        json={"source_span_id": m["span_id"], "evidence_role": "supports"},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    for who in ("reviewer_headers", "admin_headers", "rater_headers"):
        assert _about(client, m[who], draft["id"]) == []


def test_comments_notify_participants_and_the_comment_replied_to(client, team):
    m = team
    created = _create(client, m, m["contributor_headers"], proposition="Open to discussion.")
    r = client.post(
        f"/api/v1/assertions/{created['id']}/comments",
        json={"comment_text": "Does this cover public information?"},
        headers=m["rater_headers"],
    )
    assert r.status_code == 201
    question_id = r.json()["id"]
    notice = _about(client, m["contributor_headers"], created["id"])
    assert [n["event_type"] for n in notice] == ["comment_added"]
    assert notice[0]["payload"]["comment_id"] == question_id
    assert "Does this cover" not in str(notice[0])  # no comment text is copied into notices
    # A reviewer who has not taken part is not told about every comment.
    assert _kinds(client, m["reviewer_headers"], created["id"]) == ["assertion_submitted"]

    r = client.post(
        f"/api/v1/assertions/{created['id']}/comments",
        json={"comment_text": "Yes, see clause 8.4.", "parent_comment_id": question_id},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 201
    reply_notice = _about(client, m["rater_headers"], created["id"])
    assert [n["event_type"] for n in reply_notice] == ["comment_added"]
    assert reply_notice[0]["payload"]["parent_comment_id"] == question_id
    assert _kinds(client, m["contributor_headers"], created["id"]) == ["comment_added", "comment_added"]


def test_superseding_an_assertion_notifies_its_author(client, team):
    m = team
    old = _create(client, m, m["contributor_headers"], proposition="Old reading.")
    new = _create(client, m, m["reviewer_headers"], proposition="Better reading.")
    r = client.post(
        f"/api/v1/assertions/{old['id']}/supersede",
        json={"superseded_by_assertion_id": new["id"]},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    notice = _about(client, m["contributor_headers"], old["id"])
    assert [n["event_type"] for n in notice] == ["assertion_superseded"]
    assert notice[0]["payload"]["superseded_by_assertion_id"] == new["id"]


def test_a_repeated_decision_that_changes_nothing_is_not_notified_again(client, team):
    m = team
    created = _create(
        client,
        m,
        m["contributor_headers"],
        proposition="Accepted twice.",
        evidence=[{"source_span_id": m["span_id"], "evidence_role": "supports"}],
    )
    for _ in range(2):
        r = client.post(f"/api/v1/assertions/{created['id']}/accept", json={}, headers=m["reviewer_headers"])
        assert r.status_code in (200, 409)
    assert _kinds(client, m["contributor_headers"], created["id"]) == ["assertion_accepted"]


# --- ratings are opt-in; preferences ---------------------------------------------


def test_rating_notifications_are_opt_in(client, team):
    m = team
    created = _create(client, m, m["contributor_headers"], proposition="Rate me.")
    client.put(
        f"/api/v1/assertions/{created['id']}/revisions/1/rating",
        json={"strength": 4, "rationale": None},
        headers=m["rater_headers"],
    )
    assert _about(client, m["contributor_headers"], created["id"]) == []

    r = client.put(
        "/api/v1/notifications/preferences",
        json={"preferences": {"assertion_rated": True}},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    r = client.put(
        f"/api/v1/assertions/{created['id']}/revisions/1/rating",
        json={"strength": 2, "rationale": "On reflection, weaker."},
        headers=m["rater_headers"],
    )
    assert r.status_code == 200
    notice = _about(client, m["contributor_headers"], created["id"])
    assert [n["event_type"] for n in notice] == ["assertion_rated"]
    assert notice[0]["payload"]["strength"] == 2
    assert notice[0]["payload"]["revision_number"] == 1


def test_preferences_default_to_everything_but_ratings_and_can_be_changed(client, team):
    m = team
    r = client.get("/api/v1/notifications/preferences", headers=m["reviewer_headers"])
    assert r.status_code == 200
    prefs = {p["event_type"]: p for p in r.json()}
    assert prefs["assertion_rated"] == {"event_type": "assertion_rated", "enabled": False, "default": False}
    assert all(p["enabled"] and p["default"] for e, p in prefs.items() if e != "assertion_rated")
    assert {"assertion_submitted", "revision_created", "evidence_added", "comment_added"} <= set(prefs)

    r = client.put(
        "/api/v1/notifications/preferences",
        json={"preferences": {"comment_added": False}},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 200
    assert {p["event_type"]: p["enabled"] for p in r.json()}["comment_added"] is False

    r = client.put(
        "/api/v1/notifications/preferences",
        json={"preferences": {"comment_added": True, "no_such_event": True}},
        headers=m["reviewer_headers"],
    )
    assert r.status_code == 422
    current = client.get("/api/v1/notifications/preferences", headers=m["reviewer_headers"]).json()
    assert {p["event_type"]: p["enabled"] for p in current}["comment_added"] is False  # nothing applied
    # Preferences are per user.
    other = client.get("/api/v1/notifications/preferences", headers=m["admin_headers"]).json()
    assert {p["event_type"]: p["enabled"] for p in other}["comment_added"] is True


def test_a_switched_off_event_type_is_not_delivered(client, team):
    m = team
    client.put(
        "/api/v1/notifications/preferences",
        json={"preferences": {"assertion_submitted": False}},
        headers=m["reviewer_headers"],
    )
    created = _create(client, m, m["contributor_headers"], proposition="Quiet submission.")
    assert _about(client, m["reviewer_headers"], created["id"]) == []
    assert _kinds(client, m["admin_headers"], created["id"]) == ["assertion_submitted"]


# --- read state ---------------------------------------------------------------------


def _rejected(client, m, proposition: str) -> dict:
    created = _create(client, m, m["contributor_headers"], proposition=proposition)
    assert client.post(f"/api/v1/assertions/{created['id']}/reject", headers=m["reviewer_headers"]).status_code == 200
    return created


def test_marking_one_notification_read_clears_it_from_the_unread_count(client, team):
    m = team
    _rejected(client, m, "Rejected claim.")
    assert _unread(client, m["contributor_headers"]) == 1
    notice = _feed(client, m["contributor_headers"])[0]
    assert notice["read"] is False and notice["read_at"] is None

    r = client.post(f"/api/v1/notifications/{notice['id']}/read", headers=m["contributor_headers"])
    assert r.status_code == 200
    assert r.json()["id"] == notice["id"] and r.json()["read"] is True
    first_read_at = r.json()["read_at"]
    assert first_read_at.endswith("+00:00")
    assert _unread(client, m["contributor_headers"]) == 0
    assert _feed(client, m["contributor_headers"])[0]["read"] is True
    assert _feed(client, m["contributor_headers"], unread_only="true") == []

    again = client.post(f"/api/v1/notifications/{notice['id']}/read", headers=m["contributor_headers"])
    assert again.status_code == 200 and again.json()["read_at"] == first_read_at


def test_mark_all_read_then_a_later_notification_is_unread(client, team):
    m = team
    _rejected(client, m, "First rejected claim.")
    _rejected(client, m, "Second rejected claim.")
    assert _unread(client, m["contributor_headers"]) == 2

    r = client.post("/api/v1/notifications/read-all", headers=m["contributor_headers"])
    assert r.status_code == 200
    assert r.json() == {"marked_read": 2, "unread_count": 0}
    assert all(n["read"] for n in _feed(client, m["contributor_headers"]))

    _rejected(client, m, "Third rejected claim.")
    assert _unread(client, m["contributor_headers"]) == 1
    assert [n["read"] for n in _feed(client, m["contributor_headers"])] == [False, True, True]


def test_mark_all_read_up_to_what_was_shown_leaves_newer_ones_unread(client, team):
    m = team
    _rejected(client, m, "Shown to the user.")
    shown = _feed(client, m["contributor_headers"])[0]
    _rejected(client, m, "Arrived after the panel was rendered.")

    r = client.post(
        "/api/v1/notifications/read-all",
        json={"last_read_at": shown["created_at"]},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert r.json() == {"marked_read": 1, "unread_count": 1}
    newest, oldest = _feed(client, m["contributor_headers"])
    assert (newest["read"], oldest["read"]) == (False, True)
    assert oldest["id"] == shown["id"]


def test_last_read_at_with_another_utc_offset_means_the_same_instant(client, team):
    from datetime import datetime, timedelta, timezone

    m = team
    _rejected(client, m, "Shown at a +02:00 wall clock.")
    shown = _feed(client, m["contributor_headers"])[0]
    local = datetime.fromisoformat(shown["created_at"]).astimezone(timezone(timedelta(hours=2)))
    assert not local.isoformat().endswith("+00:00")

    r = client.post(
        "/api/v1/notifications/read-all",
        json={"last_read_at": local.isoformat()},
        headers=m["contributor_headers"],
    )
    assert r.json() == {"marked_read": 1, "unread_count": 0}


def test_nobody_can_read_or_mark_another_users_notifications(client, team):
    m = team
    _rejected(client, m, "The contributor's notice.")
    theirs = _feed(client, m["contributor_headers"])[0]

    r = client.post(f"/api/v1/notifications/{theirs['id']}/read", headers=m["reviewer_headers"])
    assert r.status_code == 404
    r = client.post("/api/v1/notifications/no-such-id/read", headers=m["reviewer_headers"])
    assert r.status_code == 404
    assert client.post("/api/v1/notifications/read-all", headers=m["reviewer_headers"]).status_code == 200
    assert _feed(client, m["contributor_headers"])[0]["read"] is False
    assert all(n["recipient_user_id"] == m["reviewer_id"] for n in _feed(client, m["reviewer_headers"]))


def test_notification_routes_require_authentication(client):
    for method, path in (
        ("get", "/api/v1/notifications"),
        ("get", "/api/v1/notifications/unread-count"),
        ("post", "/api/v1/notifications/read-all"),
        ("post", "/api/v1/notifications/some-id/read"),
        ("get", "/api/v1/notifications/preferences"),
    ):
        assert getattr(client, method)(path).status_code == 401, path
    r = client.put("/api/v1/notifications/preferences", json={"preferences": {}})
    assert r.status_code == 401


def test_feed_pages_newest_first_and_bounds_the_page_size(client, team):
    m = team
    for i in range(3):
        _rejected(client, m, f"Paged claim {i}.")
    full = _feed(client, m["contributor_headers"])
    assert [n["context"]["proposition"] for n in full] == [f"Paged claim {i}." for i in (2, 1, 0)]
    assert _feed(client, m["contributor_headers"], limit=2) == full[:2]
    assert _feed(client, m["contributor_headers"], limit=2, offset=2) == full[2:]
    for bad in ({"limit": 0}, {"limit": 201}, {"offset": -1}):
        r = client.get("/api/v1/notifications", headers=m["contributor_headers"], params=bad)
        assert r.status_code == 422, bad


# --- link and context --------------------------------------------------------------


def test_a_notification_carries_the_assertion_id_a_link_and_context(client, team):
    m = team
    created = _rejected(client, m, "Clause 12 caps only direct damages.")
    notice = _about(client, m["contributor_headers"], created["id"])[0]

    assert notice["event_type"] == "assertion_rejected"
    assert notice["assertion_id"] == created["id"]
    assert notice["matter_id"] == m["matter_id"]
    assert notice["link"] == f"/assertions/{created['id']}"
    assert notice["payload"]["assertion_id"] == created["id"]
    assert notice["payload"]["matter_id"] == m["matter_id"]
    assert (notice["payload"]["previous_status"], notice["payload"]["status"]) == ("proposed", "rejected")
    assert notice["context"] == {
        "proposition": "Clause 12 caps only direct damages.",
        "assertion_status": "rejected",
        "assertion_origin": "user_suggested",
        "matter_name": "Test Matter",
        "actor_display_name": "Reviewer",
    }
    assert notice["created_at"].endswith("+00:00")


def test_context_and_link_are_withheld_once_matter_access_is_revoked(client, db_session, team):
    from sqlalchemy import text

    m = team
    created = _rejected(client, m, "Confidential reading.")
    db_session.execute(
        text("DELETE FROM matter_roles WHERE user_id = :u AND matter_id = :m"),
        {"u": m["contributor_id"], "m": m["matter_id"]},
    )
    db_session.commit()
    notice = _about(client, m["contributor_headers"], created["id"])[0]
    assert notice["event_type"] == "assertion_rejected"
    assert notice["link"] is None and notice["context"] is None
    assert "Confidential" not in str(notice)


def test_a_long_proposition_is_excerpted(client, team):
    m = team
    long_text = "The supplier shall " + "keep records " * 60 + "for seven years."
    _rejected(client, m, long_text)
    excerpt = _feed(client, m["contributor_headers"])[0]["context"]["proposition"]
    assert 270 < len(excerpt) <= 280 and excerpt.endswith("…")
    assert long_text.startswith(excerpt[:-1])


# --- durable store -------------------------------------------------------------------


def test_notifications_survive_a_restart_and_are_shared_between_app_instances(client, app, team):
    """pipeline:9: a second app on the same database (a restarted server or
    another worker) serves the same feed and the same read state."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    m = team
    created = _create(client, m, m["contributor_headers"], proposition="Durable claim.")
    second = create_app()  # same LEXGRAPH_DATABASE_URL as the `app` fixture
    try:
        with TestClient(second) as other:
            notices = [n for n in _feed(other, m["reviewer_headers"]) if n["assertion_id"] == created["id"]]
            assert [n["event_type"] for n in notices] == ["assertion_submitted"]
            assert other.post(f"/api/v1/notifications/{notices[0]['id']}/read", headers=m["reviewer_headers"]).status_code == 200
        assert _about(client, m["reviewer_headers"], created["id"])[0]["read"] is True
    finally:
        second.state.engine.dispose()


def _agent_body(m, proposition: str, **extra) -> dict:
    return {
        "repository_id": m["repository_id"],
        "matter_id": m["matter_id"],
        "assertion_type": "APPLIES_TO",
        "proposition": proposition,
        "subject_entity": {"type": "Document", "id": m["document_id"]},
        "agent": {"platform": "cli-test"},
        **extra,
    }


def test_a_proposal_made_outside_http_can_notify_through_the_service(client, app, team):
    """The agent CLI / MCP path: the same shared creation function on its
    own session, no HTTP request. notify_submission writes into the same
    feed, and a second call for the same submission adds nothing."""
    from app import notifications
    from app.routers.agents import AgentAssertionCreate, suggest_assertion

    m = team
    with app.state.session_factory() as session:
        body = AgentAssertionCreate.model_validate(_agent_body(m, "Proposed from the command line."))
        result = suggest_assertion(body, session, m["contributor_id"])
        assert notifications.notify_submission(session, result["id"], m["contributor_id"]) == 2
        assert notifications.notify_submission(session, result["id"], m["contributor_id"]) == 0

        draft = suggest_assertion(
            AgentAssertionCreate.model_validate(_agent_body(m, "A CLI draft.", save_as="draft")),
            session,
            m["contributor_id"],
        )
        assert notifications.notify_submission(session, draft["id"], m["contributor_id"]) == 0
        assert notifications.notify_submission(session, "no-such-assertion", m["contributor_id"]) == 0

    assert _kinds(client, m["reviewer_headers"], result["id"]) == ["assertion_submitted"]
    assert _kinds(client, m["admin_headers"], result["id"]) == ["assertion_submitted"]
    assert _about(client, m["reviewer_headers"], draft["id"]) == []


def test_notify_submission_adds_nothing_where_the_http_hook_already_notified(client, app, team):
    """Safe to call from the shared agent function too: the REST agent
    endpoint is already covered by the hook, and no duplicate appears."""
    from app import notifications

    m = team
    r = client.post("/api/v1/agent/assertions", json=_agent_body(m, "Proposed over REST."), headers=m["contributor_headers"])
    assert r.status_code == 201
    with app.state.session_factory() as session:
        assert notifications.notify_submission(session, r.json()["id"], m["contributor_id"]) == 0
    assert _kinds(client, m["reviewer_headers"], r.json()["id"]) == ["assertion_submitted"]


def test_notify_submission_never_raises(app, team, monkeypatch, caplog):
    from app import notifications
    from app.routers.agents import AgentAssertionCreate, suggest_assertion

    def broken(*args, **kwargs):
        raise RuntimeError("notification store unavailable")

    m = team
    with app.state.session_factory() as session:
        result = suggest_assertion(
            AgentAssertionCreate.model_validate(_agent_body(m, "Stored even if notifying fails.")),
            session,
            m["contributor_id"],
        )
        monkeypatch.setattr(notifications, "notify_assertion_submitted", broken)
        assert notifications.notify_submission(session, result["id"], m["contributor_id"]) == 0
        assert "could not notify reviewers" in caplog.text
        from app.models.assertion import Assertion

        assert session.get(Assertion, result["id"]).status == "proposed"  # session still usable


def test_a_notification_failure_never_breaks_the_mutation(client, team, monkeypatch, caplog):
    from app import notifications

    def broken(*args, **kwargs):
        raise RuntimeError("notification store unavailable")

    monkeypatch.setattr(notifications, "notify_assertion_submitted", broken)
    m = team
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], proposition="Still created.", save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    assert r.json()["proposition"] == "Still created."
    assert "notification hook failed" in caplog.text
