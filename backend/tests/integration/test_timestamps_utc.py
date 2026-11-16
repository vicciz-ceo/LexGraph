"""Every instant the API returns carries an explicit UTC offset (api:15, ui:3).

SQLite, the documented database, has no timezone-aware storage: a
``DateTime(timezone=True)`` column hands back NAIVE datetimes even though every
writer stores ``datetime.now(timezone.utc)``.  The responses then carried
``"2026-11-15T17:46:23.505167"`` with no offset, and browsers parse an
offset-less date-time as LOCAL time, so every timestamp was shown hours off for
anyone outside UTC (and on the wrong calendar day near midnight).

These tests walk the real HTTP surface through one assertion's whole life and
require an explicit zero UTC offset on every instant, while calendar dates
(``effective_from``/``effective_to``) must come back exactly as entered.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import assertion_payload, seed_document, seed_source_span

_INSTANT_KEYS = {"created_at", "updated_at", "submitted_at", "reviewed_at", "deleted_at", "timestamp"}


def _assert_utc_instant(value: str, where: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() == timedelta(0), f"{where}={value!r} has no explicit UTC offset"
    # The digits are UTC too, not some local wall clock that merely got a label.
    assert abs(parsed - datetime.now(timezone.utc)) < timedelta(minutes=10), f"{where}={value!r}"
    return parsed


def _walk(value, where: str, seen: list[str]) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            path = f"{where}.{key}"
            if key in _INSTANT_KEYS and inner is not None:
                _assert_utc_instant(inner, path)
                seen.append(path)
            else:
                _walk(inner, path, seen)
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            _walk(inner, f"{where}[{index}]", seen)


def _lifecycle(client, m, db_session):
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"])
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            m["matter_id"],
            m["repository_id"],
            save_as="proposed",
            effective_from="2026-01-01",
            effective_to="2026-12-31T00:00:00",
            evidence=[{"source_span_id": span, "evidence_role": "supports"}],
        ),
        headers=m["contributor_headers"],
    )
    assert created.status_code == 201, created.text
    assertion_id = created.json()["id"]
    comment = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "A second look at clause 8.4."},
        headers=m["rater_headers"],
    )
    assert comment.status_code == 201, comment.text
    rating = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": "Plain wording."},
        headers=m["rater_headers"],
    )
    assert rating.status_code == 201, rating.text
    disputed = client.post(f"/api/v1/assertions/{assertion_id}/dispute", headers=m["reviewer_headers"])
    assert disputed.status_code == 200, disputed.text
    edited = client.patch(
        f"/api/v1/assertions/{assertion_id}/comments/{comment.json()['id']}",
        json={"comment_text": "A second look at clause 8.4 (edited)."},
        headers=m["rater_headers"],
    )
    assert edited.status_code == 200, edited.text
    return assertion_id, created, edited, rating, disputed


def test_every_instant_in_every_response_has_an_explicit_utc_offset(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id, created, comment, rating, disputed = _lifecycle(client, m, db_session)
    headers = m["reviewer_headers"]
    responses = {
        "POST /assertions": created,
        "PATCH /comments": comment,
        "PUT /rating": rating,
        "POST /dispute": disputed,
        "GET /assertions": client.get(
            "/api/v1/assertions", params={"matter_id": m["matter_id"]}, headers=headers
        ),
        "GET /assertions/{id}": client.get(f"/api/v1/assertions/{assertion_id}", headers=headers),
        "GET /revisions": client.get(f"/api/v1/assertions/{assertion_id}/revisions", headers=headers),
        "GET /evidence": client.get(f"/api/v1/assertions/{assertion_id}/evidence", headers=headers),
        "GET /history": client.get(f"/api/v1/assertions/{assertion_id}/history", headers=headers),
        "GET /comments": client.get(f"/api/v1/assertions/{assertion_id}/comments", headers=headers),
        "GET /ratings": client.get(f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=headers),
        "GET /rating": client.get(
            f"/api/v1/assertions/{assertion_id}/revisions/1/rating", headers=m["rater_headers"]
        ),
        "GET /ratings/summary": client.get(
            f"/api/v1/assertions/{assertion_id}/revisions/1/ratings/summary", headers=m["rater_headers"]
        ),
        "PATCH /assertions/{id}": client.patch(
            f"/api/v1/assertions/{assertion_id}",
            json={"proposition": "Clause 8.4 narrows the notice duty in Clause 8.2."},
            headers=headers,
        ),
    }
    seen: list[str] = []
    for name, response in responses.items():
        assert response.status_code in (200, 201), f"{name}: {response.status_code} {response.text}"
        _walk(response.json(), name, seen)

    # The walk really covered each kind of instant (no vacuous pass).
    for expected in (
        "POST /assertions.created_at",
        "POST /assertions.submitted_at",
        "POST /dispute.reviewed_at",
        "GET /assertions.items[0].updated_at",
        "GET /assertions/{id}.evidence[0].created_at",
        "GET /assertions/{id}.revision_history[0].created_at",
        "GET /history[0].timestamp",
        "PATCH /comments.updated_at",
        "GET /comments[0].created_at",
        "GET /ratings[0].updated_at",
        "GET /ratings/summary.current_user_rating.updated_at",
    ):
        assert expected in seen, f"{expected} was not checked; saw {sorted(seen)}"


def test_calendar_dates_are_returned_exactly_as_entered(client, matter_with_users, db_session):
    """effective_from/effective_to are dates, not instants: stamping them UTC would
    render 1 January as 31 December for every viewer west of Greenwich."""
    m = matter_with_users
    assertion_id, created, *_ = _lifecycle(client, m, db_session)
    detail = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"]).json()
    for body in (created.json(), detail, detail["revision_history"][0]):
        assert body["effective_from"] == "2026-01-01T00:00:00"
        assert body["effective_to"] == "2026-12-31T00:00:00"
