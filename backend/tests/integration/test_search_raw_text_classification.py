"""Track A, item A6 — read-path classification: search matches against raw
text, not the (possibly lossy) sanitized column (issue #2: "raw for
diff/compare/export/audit/search").

`sanitize_for_storage("see <appendix A> for details")` drops "appendix A"
(this is the exact example from issue #2's Problem section, and it is NOT
weakened by this sprint -- the sanitized column still loses it). A search
for "appendix A" must still find the assertion once search reads the raw
column via the current revision.
"""

from __future__ import annotations

from tests.conftest import assertion_payload

LOSSY_TEXT = "see <appendix A> for details, per Clause 9.1."


def test_search_matches_a_term_the_sanitizer_drops_from_the_sanitized_column(
    client, matter_with_users
):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=LOSSY_TEXT)
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert created.status_code == 201
    assertion_id = created.json()["id"]

    # Sanity check: the sanitized column genuinely no longer contains the
    # search term (otherwise this test would not be distinguishing raw-
    # vs-sanitized search at all).
    assert "appendix A" not in created.json()["proposition"]

    results = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "q": "appendix A"},
        headers=m["contributor_headers"],
    )
    assert results.status_code == 200
    ids = [item["id"] for item in results.json()["items"]]
    assert assertion_id in ids
