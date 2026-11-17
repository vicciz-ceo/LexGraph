"""The exact-duplicate re-check under the write lock (review authoring:3).

Writers check the exact-duplicate rule without the lock over the whole
matter, then again under `lock_assertion_writes` before they write. The
second pass used to re-read and re-normalize every row of the matter while
holding SQLite's database-wide write lock (0.35 s at 220,000 rows, seconds
under load). It now reads only what was committed after the first pass
began: rows inserted since, and assertions with an audit row since. These
tests pin both halves: the locked pass does not walk the matter, and it
still catches every way a blocking twin can appear between the two passes
-- a new assertion, an edit taking the proposition, a draft submitted, a
rejected assertion revived.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

import app.routers.assertions as assertions_router
import app.routers.review as review_router
from app.routers.assertions import DuplicateScan, recheck_duplicate
from tests.conftest import assertion_payload, auth_header, seed_matter_role, seed_user

WAIT = 30
PROPOSITION = "Clause 12 makes the agreement the entire agreement of the parties."
DUPLICATE = "duplicate: an identical proposition already exists in this matter (assertion {})"


class _Request(threading.Thread):
    def __init__(self, call):
        super().__init__(daemon=True)
        self._call, self.response, self.error = call, None, None
        self.start()

    def run(self) -> None:
        try:
            self.response = self._call()
        except BaseException as exc:
            self.error = exc

    def result(self):
        self.join(timeout=WAIT)
        assert not self.is_alive(), "request did not finish"
        if self.error is not None:
            raise self.error
        return self.response


def _hold_after_first_call(monkeypatch, module, name):
    original = getattr(module, name)
    reached, release, held = threading.Event(), threading.Event(), []

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        if not held:
            held.append(True)
            reached.set()
            assert release.wait(timeout=WAIT)
        return result

    monkeypatch.setattr(module, name, wrapper)
    return reached, release


def _create(client, m, proposition, *, headers=None, save_as="proposed"):
    return client.post("/api/v1/assertions", headers=headers or m["contributor_headers"], json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition=proposition, save_as=save_as, explanation=None))


def _created(client, m, proposition, **kwargs) -> str:
    r = _create(client, m, proposition, **kwargs)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture()
def second_author(db_session, matter_with_users) -> dict:
    user_id = seed_user(db_session, display_name="Second author")
    seed_matter_role(db_session, user_id=user_id, matter_id=matter_with_users["matter_id"], role="contributor")
    return {"id": user_id, "headers": auth_header(user_id)}


def _bulk_insert(app, m, count: int) -> None:
    """`count` accepted rows shaped like definition-linking output."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    rows = [{"id": str(uuid.uuid4()), "org": m["organization_id"], "repo": m["repository_id"],
             "m": m["matter_id"], "p": f'Article {k} uses the definition of "person".',
             "author": m["reviewer_id"], "now": now} for k in range(count)]
    with app.state.engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO assertions (id, organization_id, repository_id, matter_id, assertion_type, proposition, "
            "subject_entity_type, subject_entity_id, origin, status, author_user_id, created_at, updated_at, "
            "current_revision_number) VALUES (:id, :org, :repo, :m, 'USES_DEFINITION', :p, 'Article', :id, "
            "'system_generated', 'accepted', :author, :now, :now, 1)"), rows)


def test_the_locked_re_check_does_not_walk_the_matter(app, client, matter_with_users, monkeypatch):
    m = matter_with_users
    _bulk_insert(app, m, 3000)
    seen_under_lock: list[int] = []
    original = assertions_router.first_blocking_duplicate

    def counting(proposition, existing, **kwargs):
        existing = list(existing)
        seen_under_lock.append(len(existing))
        return original(proposition, existing, **kwargs)

    # A create calls it only from the locked re-check: the unlocked pass is
    # the related-assertion matcher over the whole matter.
    monkeypatch.setattr(assertions_router, "first_blocking_duplicate", counting)
    assert _create(client, m, PROPOSITION).status_code == 201
    assert seen_under_lock == [0], "nothing was written between the scan and the lock"


def test_an_identical_assertion_stored_after_the_scan_is_caught_under_the_lock(client, matter_with_users,
                                                                              monkeypatch):
    m = matter_with_users
    reached, release = _hold_after_first_call(monkeypatch, assertions_router, "find_related_assertions")

    held = _Request(lambda: _create(client, m, PROPOSITION))
    assert reached.wait(timeout=WAIT)
    other = _created(client, m, f"  {PROPOSITION.upper()}  ")  # the same proposition, as the rule compares it
    release.set()

    refused = held.result()
    assert (refused.status_code, refused.json()["detail"]) == (409, DUPLICATE.format(other)), refused.text


def test_an_edit_that_takes_the_proposition_after_the_scan_is_caught_under_the_lock(
        client, matter_with_users, monkeypatch):
    m = matter_with_users
    edited = _created(client, m, "Clause 9 governs notices.")
    reached, release = _hold_after_first_call(monkeypatch, assertions_router, "find_related_assertions")

    held = _Request(lambda: _create(client, m, PROPOSITION))
    assert reached.wait(timeout=WAIT)
    patch = client.patch(f"/api/v1/assertions/{edited}", headers=m["contributor_headers"],
                         json={"proposition": PROPOSITION, "expected_revision_number": 1})
    assert patch.status_code == 200, patch.text
    release.set()

    refused = held.result()
    assert (refused.status_code, refused.json()["detail"]) == (409, DUPLICATE.format(edited)), refused.text


def test_a_draft_submitted_after_the_scan_is_caught_under_the_lock(client, matter_with_users, second_author,
                                                                  monkeypatch):
    m = matter_with_users
    # Another author's draft does not block, until it is submitted.
    draft = _created(client, m, PROPOSITION, headers=second_author["headers"], save_as="draft")
    reached, release = _hold_after_first_call(monkeypatch, assertions_router, "find_related_assertions")

    held = _Request(lambda: _create(client, m, PROPOSITION))
    assert reached.wait(timeout=WAIT)
    submitted = client.post(f"/api/v1/assertions/{draft}/submit", headers=second_author["headers"])
    assert submitted.status_code == 200, submitted.text
    release.set()

    refused = held.result()
    assert (refused.status_code, refused.json()["detail"]) == (409, DUPLICATE.format(draft)), refused.text


def test_a_rejected_twin_revived_after_the_scan_is_caught_under_the_lock(client, matter_with_users,
                                                                        monkeypatch):
    m = matter_with_users
    rejected = _created(client, m, PROPOSITION)
    assert client.post(f"/api/v1/assertions/{rejected}/reject", headers=m["reviewer_headers"]).status_code == 200
    reached, release = _hold_after_first_call(monkeypatch, assertions_router, "find_related_assertions")

    held = _Request(lambda: _create(client, m, PROPOSITION))
    assert reached.wait(timeout=WAIT)
    revived = client.post(f"/api/v1/assertions/{rejected}/dispute", headers=m["reviewer_headers"])
    assert revived.status_code == 200, revived.text
    release.set()

    refused = held.result()
    assert (refused.status_code, refused.json()["detail"]) == (409, DUPLICATE.format(rejected)), refused.text


def test_two_authors_submitting_identical_drafts_at_once_submit_one(client, matter_with_users, second_author,
                                                                   monkeypatch):
    m = matter_with_users
    drafts = [_created(client, m, PROPOSITION, save_as="draft"),
              _created(client, m, PROPOSITION.lower(), headers=second_author["headers"], save_as="draft")]
    barrier = threading.Barrier(2)
    original = assertions_router.scan_for_duplicate

    def scanned_together(*args, **kwargs):
        result = original(*args, **kwargs)
        barrier.wait(timeout=WAIT)
        return result

    monkeypatch.setattr(assertions_router, "scan_for_duplicate", scanned_together)
    requests = [
        _Request(lambda: client.post(f"/api/v1/assertions/{drafts[0]}/submit", headers=m["contributor_headers"])),
        _Request(lambda: client.post(f"/api/v1/assertions/{drafts[1]}/submit", headers=second_author["headers"])),
    ]
    responses = [request.result() for request in requests]

    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    winner = next(r.json()["id"] for r in responses if r.status_code == 200)
    assert next(r for r in responses if r.status_code == 409).json()["detail"] == DUPLICATE.format(winner)


def test_a_revival_racing_a_new_live_twin_is_refused(client, matter_with_users, monkeypatch):
    m = matter_with_users
    rejected = _created(client, m, PROPOSITION)
    assert client.post(f"/api/v1/assertions/{rejected}/reject", headers=m["reviewer_headers"]).status_code == 200
    reached, release = _hold_after_first_call(monkeypatch, review_router, "scan_for_duplicate")

    revival = _Request(lambda: client.post(f"/api/v1/assertions/{rejected}/accept", headers=m["reviewer_headers"],
                                           json={"acceptance_justification": "Re-read clause 12."}))
    assert reached.wait(timeout=WAIT)
    twin = _created(client, m, PROPOSITION)  # a rejected assertion does not block its proposition
    release.set()

    refused = revival.result()
    assert (refused.status_code, refused.json()["detail"]) == (409, DUPLICATE.format(twin)), refused.text
    assert refused.json()["existing_assertion_id"] == twin


def test_a_watermark_the_database_has_gone_below_falls_back_to_the_whole_matter(app, client, matter_with_users):
    """Rowids that went backwards (rows deleted, or renumbered by a VACUUM)
    cannot tell what is new: the re-check then reads every row again."""
    m = matter_with_users
    existing = _created(client, m, PROPOSITION)
    scan = DuplicateScan(m["matter_id"], PROPOSITION, m["rater_id"], None, False, (10**9, 10**9))
    with app.state.session_factory() as session:
        assert recheck_duplicate(session, scan) == existing
