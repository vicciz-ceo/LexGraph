"""Track A, item A5 — gate G1 acceptance criterion 1: the three example
strings named in issue #2 round-trip byte-exact through
create -> fetch -> PATCH (new revision) -> revision history, via the
`proposition_raw` columns added by A1/A2.

Each example is a real quote from issue #2's "Problem" section, chosen
because `sanitize_for_storage` legitimately (and, per ruling R18,
correctly/browser-faithfully) alters or drops part of it -- proving these
round-trip byte-exact via the RAW column, independent of whatever the
sanitized column does.
"""

from __future__ import annotations

import pytest

from tests.conftest import assertion_payload

EXAMPLES = [
    "Signatory: <Title> of the Company.",
    "see <appendix A> for details",
    "Pre <img plaintail <b>Y</b> Z",
]


@pytest.mark.parametrize("text", EXAMPLES, ids=["title_placeholder", "appendix_ref", "img_plaintail"])
def test_named_example_round_trips_byte_exact_through_create_fetch_patch_history(
    client, matter_with_users, text
):
    m = matter_with_users

    # create
    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=text)
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert created.status_code == 201
    assertion_id = created.json()["id"]
    assert created.json()["proposition_raw"] == text

    # fetch
    fetched = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["contributor_headers"])
    assert fetched.status_code == 200
    assert fetched.json()["proposition_raw"] == text

    # PATCH creates a new revision with a DIFFERENT raw text; the ORIGINAL
    # revision's raw text must remain intact in revision history.
    patch = client.patch(
        f"/api/v1/assertions/{assertion_id}",
        json={"proposition": "A distinct follow-up proposition."},
        headers=m["contributor_headers"],
    )
    assert patch.status_code == 200

    history = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions", headers=m["contributor_headers"]
    )
    assert history.status_code == 200
    revisions = history.json()
    assert revisions[0]["proposition_raw"] == text
    assert revisions[1]["proposition_raw"] == "A distinct follow-up proposition."
