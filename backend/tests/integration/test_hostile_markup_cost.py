"""Hostile nested markup cannot make one request burn seconds of CPU.

A proposition and an explanation of nested raw-text wrappers at the
100,000-character cap used to cost about 8 s of sanitizer CPU each, so one
create request took about 16 s. With the sanitizer's pass cap
(`_MAX_SANITIZE_PASSES`), such text fails closed: it sanitizes to nothing, and
the routes refuse it with the same 422 as any markup-only text.
"""

from __future__ import annotations

import time

from tests.conftest import assertion_payload

_HOSTILE = "<title>" * 14_285  # 99,995 characters, within the length cap
_BUDGET_SECONDS = 4.0  # about 0.3 s locally; generous for slow CI runners


def test_create_with_nested_wrappers_is_refused_quickly(client, matter_with_users) -> None:
    m = matter_with_users
    body = assertion_payload(m["matter_id"], m["repository_id"], proposition=_HOSTILE, explanation=_HOSTILE)
    started = time.perf_counter()
    response = client.post("/api/v1/assertions", json=body, headers=m["contributor_headers"])
    elapsed = time.perf_counter() - started
    assert response.status_code == 422
    assert response.json()["detail"] == "proposition cannot be empty"
    assert elapsed < _BUDGET_SECONDS, f"create took {elapsed:.2f}s"


def test_comment_with_nested_wrappers_is_refused_quickly(client, matter_with_users) -> None:
    m = matter_with_users
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assert created.status_code == 201
    started = time.perf_counter()
    response = client.post(
        f"/api/v1/assertions/{created.json()['id']}/comments",
        json={"comment_text": _HOSTILE},
        headers=m["rater_headers"],
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 422
    assert elapsed < _BUDGET_SECONDS, f"comment took {elapsed:.2f}s"
