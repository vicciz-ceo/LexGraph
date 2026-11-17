"""GET /api/v1/assertions: pagination, batched serialization, embedded ratings.

Audit findings api:14 and ui:1: the list had no limit/offset, filtered and
sorted in Python, and serialized each row with 3-4 queries of its own, so a
matter holding one definition-link run (thousands of accepted rows) took
seconds to tens of seconds per request, and the Knowledge Base then fired one
rating-summary request per row.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import event

from tests.conftest import assertion_payload
from tests.integration._assertion_list_fixtures import (
    build_varied_matter,
    insert_legacy_row_without_revision,
    run_definition_link_pipeline,
)


def _list(client, m, headers=None, **params):
    response = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], **params},
        headers=headers or m["reviewer_headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def _ids(body) -> list[str]:
    return [item["id"] for item in body["items"]]


# --- limit / offset / total ----------------------------------------------------


def test_limit_and_offset_return_one_page_and_total_counts_every_match(client, matter_with_users, db_session):
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    everything = _list(client, m)
    assert everything["total"] == 6 and len(everything["items"]) == 6

    page = _list(client, m, limit=2, offset=1)
    assert page["total"] == 6
    assert page["limit"] == 2 and page["offset"] == 1
    assert _ids(page) == _ids(everything)[1:3]

    tail = _list(client, m, limit=4, offset=4)
    assert tail["total"] == 6 and _ids(tail) == _ids(everything)[4:]
    beyond = _list(client, m, limit=4, offset=50)
    assert beyond["total"] == 6 and beyond["items"] == []
    no_limit = _list(client, m, offset=5)
    assert no_limit["total"] == 6 and _ids(no_limit) == _ids(everything)[5:]


def test_without_limit_the_whole_match_set_comes_back_as_before(client, matter_with_users, db_session):
    """Backward compatibility: Review Queue, Contested, the CLI curl in the
    RUNBOOK and many tests call the list without limit and expect everything."""
    m = matter_with_users
    ids = build_varied_matter(client, m, db_session)
    body = _list(client, m)
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["limit"] is None and body["offset"] == 0
    # Insertion order, exactly what the unsorted list always returned.
    assert _ids(body) == list(ids.values())
    assert body["total"] == len(body["items"])


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 501}, {"limit": -3}, {"offset": -1}, {"limit": "ten"}],
)
def test_invalid_paging_is_rejected(client, matter_with_users, params):
    m = matter_with_users
    response = client.get(
        "/api/v1/assertions", params={"matter_id": m["matter_id"], **params}, headers=m["reviewer_headers"]
    )
    assert response.status_code == 422, response.text


def test_authentication_then_membership_are_still_checked_first(client, matter_with_users):
    m = matter_with_users
    for params, headers, expected in [
        ({"limit": 0}, {}, 401),
        ({"sort": "bogus", "bogus": 1}, {}, 401),
        ({}, m["outsider_headers"], 403),
        ({"limit": 5, "sort": "-average_rating"}, m["outsider_headers"], 403),
    ]:
        response = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"], **params}, headers=headers)
        assert response.status_code == expected, (params, response.text)


def test_q_with_limit_reports_the_full_match_total(client, matter_with_users):
    m = matter_with_users
    for i in range(5):
        r = client.post(
            "/api/v1/assertions",
            json=assertion_payload(m["matter_id"], m["repository_id"], proposition=f"Notice clause variant {i}."),
            headers=m["contributor_headers"],
        )
        assert r.status_code == 201
    client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], proposition="Unrelated indemnity text."),
        headers=m["contributor_headers"],
    )
    full = _list(client, m, q="NOTICE clause")
    page = _list(client, m, q="NOTICE clause", limit=2, offset=2)
    assert full["total"] == 5 and page["total"] == 5
    assert _ids(page) == _ids(full)[2:4]


def test_pages_over_one_pipeline_run_never_repeat_or_skip_rows(client, matter_with_users, db_session):
    """Every row of a definition-link run shares one created_at, so paging by
    created_at alone would repeat and skip rows across pages."""
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    created = run_definition_link_pipeline(db_session, m)
    assert created > 30
    for sort in (None, "-created_at", "created_at", "assertion_type", "-average_rating", "status,-proposition"):
        params = {"sort": sort} if sort else {}
        whole = _ids(_list(client, m, **params))
        assert len(whole) == created + 6 == len(set(whole))
        walked: list[str] = []
        offset = 0
        while True:
            page = _list(client, m, limit=7, offset=offset, **params)
            assert page["total"] == len(whole)
            if not page["items"]:
                break
            walked += _ids(page)
            offset += 7
        assert walked == whole, f"sort={sort!r}: pages disagree with the unpaginated order"


# --- one fixed number of statements per page -----------------------------------


class _StatementCounter:
    def __init__(self, engine):
        self.engine, self.count = engine, 0

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._hit)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._hit)

    def _hit(self, *args, **kwargs):
        self.count += 1


# Each query's page has the same make-up (a model_suggested row or not) on the
# 6-row and the 60-row matter, so only the row count differs between them.
_HEAVY_QUERIES = [
    {},
    {"limit": 50},
    {"limit": 50, "sort": "-average_rating,last_activity"},
    {"evidence_status": "awaiting_evidence", "limit": 30, "sort": "subject"},
    {"q": "clause", "limit": 20, "sort": "-my_rating"},
    {"min_average_rating": 1, "unrated_by_me": True, "sort": "author"},
]


def _statements(app, client, m, params) -> int:
    with _StatementCounter(app.state.engine) as counter:
        _list(client, m, headers=m["rater_headers"], **params)
    return counter.count


@pytest.mark.parametrize("in_limit", [500, 2], ids=["id-lists", "matter-scoped"])
def test_statement_count_does_not_grow_with_the_number_of_rows(
    app, client, matter_with_users, db_session, monkeypatch, in_limit
):
    """5-row and 60-row pages cost the same number of SQL statements (the old
    endpoint issued 3-4 per row); `in_limit=2` exercises the path used once a
    page holds more ids than one IN (...) list takes."""
    import app.services.assertion_listing as listing

    monkeypatch.setattr(listing, "_IN_LIMIT", in_limit)
    m = matter_with_users
    ids = build_varied_matter(client, m, db_session)
    small = {repr(p): _statements(app, client, m, p) for p in _HEAVY_QUERIES}
    for i in range(54):
        new_id = client.post(
            "/api/v1/assertions",
            json=assertion_payload(
                m["matter_id"], m["repository_id"], save_as="proposed", proposition=f"Bulk clause proposition {i}."
            ),
            headers=m["contributor_headers"],
        ).json()["id"]
        if i % 3 == 0:
            client.put(f"/api/v1/assertions/{new_id}/revisions/1/rating", json={"strength": 4}, headers=m["reviewer_headers"])
    assert _list(client, m)["total"] == len(ids) + 54
    large = {repr(p): _statements(app, client, m, p) for p in _HEAVY_QUERIES}
    assert large == small
    assert max(large.values()) <= 10


def test_bulk_lookup_path_serializes_exactly_like_the_id_list_path(client, matter_with_users, db_session, monkeypatch):
    import app.services.assertion_listing as listing

    m = matter_with_users
    build_varied_matter(client, m, db_session)
    run_definition_link_pipeline(db_session, m)
    by_ids = _list(client, m, headers=m["rater_headers"], sort="-last_activity")
    monkeypatch.setattr(listing, "_IN_LIMIT", 2)
    assert _list(client, m, headers=m["rater_headers"], sort="-last_activity") == by_ids


# --- list items keep the detail serializer's contract -----------------------------


def _without_entity_labels(detail: dict) -> dict:
    """GET /assertions/{id} alone names the subject/object entities (`label`,
    spec section 13, finding ui:30); every other serializer, the list's
    included, returns the bare {type, id} reference."""
    for key in ("subject_entity", "object_entity"):
        if detail[key] is not None:
            assert "label" in detail[key], detail[key]
            detail[key] = {k: v for k, v in detail[key].items() if k != "label"}
    return detail


def test_every_list_item_equals_the_single_assertion_response(client, matter_with_users, db_session):
    """The batched list serializer may not drift from `_serialize_assertion`,
    which GET /assertions/{id}, create, patch and the agent CLI still use; its
    embedded ratings_summary is the detail page's ratings_summary."""
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    run_definition_link_pipeline(db_session, m)
    pipeline_row = next(
        i["id"] for i in _list(client, m, origin="system_generated", limit=1)["items"]
    )
    legacy_row = insert_legacy_row_without_revision(db_session, pipeline_row)
    items = _list(client, m, headers=m["rater_headers"])["items"]
    kinds = set()
    for item in items:
        detail = client.get(f"/api/v1/assertions/{item['id']}", headers=m["rater_headers"]).json()
        for detail_only in ("evidence", "comments", "revision_history"):
            detail.pop(detail_only)
        assert {k: v for k, v in item.items() if k not in {"current_user_rating", "last_activity_at"}} == (
            _without_entity_labels(detail)
        )
        kinds.add((item["origin"], item["proposition_raw"] is None, item["agent_provenance"] is None))
    # model_suggested with provenance and user rows, both with their own
    # revision; pipeline rows with the revision 1 the persistence invariant
    # records; a legacy pipeline row (not yet backfilled) without any revision.
    assert ("model_suggested", False, False) in kinds
    assert ("user_suggested", False, True) in kinds
    assert ("system_generated", False, True) in kinds
    assert ("system_generated", True, True) in kinds
    assert legacy_row in {item["id"] for item in items}


def test_items_embed_the_current_revision_rating_summary(client, matter_with_users, db_session):
    m = matter_with_users
    ids = build_varied_matter(client, m, db_session)
    run_definition_link_pipeline(db_session, m)
    items = {item["id"]: item for item in _list(client, m, headers=m["rater_headers"])["items"]}

    alpha = items[ids["alpha"]]
    summary = client.get(
        f"/api/v1/assertions/{ids['alpha']}/revisions/1/ratings/summary", headers=m["rater_headers"]
    ).json()
    assert alpha["ratings_summary"] == {
        "assertion_id": ids["alpha"],
        "assertion_revision_id": summary["assertion_revision_id"],
        "average": summary["average"],
        "median": summary["median"],
        "count": summary["count"],
        "distribution": summary["distribution"],
    }
    # Like the summary endpoint the count includes the author's own rating (3);
    # `standing` still excludes it: median of 5 and 4 is "strong".
    assert alpha["ratings_summary"]["count"] == 3 and alpha["ratings_summary"]["average"] == 4.0
    assert alpha["standing"] == "strong"
    assert alpha["current_user_rating"]["strength"] == 5
    assert alpha["current_user_rating"]["rationale"] == "rated 5"

    assert items[ids["bravo"]]["ratings_summary"] is None  # never rated
    # Rated on revision 1 only: the revised assertion has not been rated yet.
    foxtrot = items[ids["foxtrot"]]
    assert foxtrot["current_revision_number"] == 2
    assert foxtrot["ratings_summary"] is None and foxtrot["current_user_rating"] is None
    # Pipeline rows are unrated; their revision 1 (persistence invariant)
    # holds the generated text as the raw text.
    pipeline_rows = [item for item in items.values() if item["origin"] == "system_generated"]
    assert pipeline_rows and all(
        item["ratings_summary"] is None and item["proposition_raw"] == item["proposition"]
        for item in pipeline_rows
    )

    # Another caller sees their own rating, never the rater's.
    as_reviewer = {item["id"]: item for item in _list(client, m)["items"]}
    assert as_reviewer[ids["alpha"]]["current_user_rating"]["strength"] == 4
    assert as_reviewer[ids["echo"]]["current_user_rating"] is None


def test_last_activity_is_the_latest_of_updated_at_and_the_audit_history(client, matter_with_users, db_session):
    m = matter_with_users
    ids = build_varied_matter(client, m, db_session)
    items = {item["id"]: item for item in _list(client, m)["items"]}
    for assertion_id in ids.values():
        history = client.get(f"/api/v1/assertions/{assertion_id}/history", headers=m["reviewer_headers"]).json()
        moments = [datetime.fromisoformat(e["timestamp"]) for e in history]
        moments.append(datetime.fromisoformat(items[assertion_id]["updated_at"]))
        assert datetime.fromisoformat(items[assertion_id]["last_activity_at"]) == max(moments)
    # The comment on bravo is the newest event in the matter; it is not an edit.
    bravo = items[ids["bravo"]]
    assert datetime.fromisoformat(bravo["last_activity_at"]) > datetime.fromisoformat(bravo["updated_at"])
