"""QA regression coverage — sprint 2026-07-26-local-first-platform.

Independent QA pass (separate agent from every Developer on this sprint).
These tests close edge-case gaps not already exercised by the Developer's
per-item tests, following the existing patterns in
test_g1_fidelity_round_trip.py / test_assertion_raw_text_fidelity.py /
test_enrich_cli.py / test_mcp_search_fetch_tools.py / test_length_cap_api.py:

- Raw-fidelity edge cases the named-example round trip doesn't cover:
  unicode/emoji/CRLF propositions and comments (A2/A3, gate G1).
- At-cap boundary text (exactly 100,000 chars) that ALSO contains
  angle-bracket prose the sanitizer alters -- proves the length cap (A8)
  and the raw/sanitized split (A2) compose correctly at the boundary.
- Enrichment CLI on a matter with genuinely ZERO source spans (distinct
  from B2's existing "spans present but none match a pattern" case) --
  gate G5's "re-running it is idempotent... failures are reported
  clearly" implies a zero-span matter must also complete cleanly, not
  error.
- MCP `fetch` of a nonexistent assertion id through the real FastMCP
  `call_tool` dispatch (gate G7) -- the existing MCP tests never probe the
  not-found path.
- Gate G4 (rating rationale privacy): no test in the repo (either this
  sprint or the prior one) previously exercised a viewer WITHOUT
  `assertion:view_rating_rationales` fetching a RATING THAT ISN'T THEIRS
  and getting `rationale`/`rationale_raw` nulled -- verified live by QA
  against the real API before writing this pin; the underlying
  `routers/ratings.py::list_ratings` gate itself was correct, this only
  closes the coverage gap.
"""

from __future__ import annotations

import asyncio

from tests.conftest import assertion_payload, auth_header, seed_document, seed_matter_role, seed_source_span, seed_user


# --- Raw-fidelity edge cases (A2/A3, gate G1) -------------------------------

UNICODE_EMOJI_CRLF_TEXT = (
    "סעיף 8.4 — the clause \U0001F4DC applies "
    "中文段落\r\n"
    "second line after a CRLF\r\n"
    "third line éèê, quotes “fancy”, emoji \U0001F680\U0001F512."
)


def test_proposition_raw_round_trips_unicode_emoji_and_crlf_byte_exact(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(
        m["matter_id"], m["repository_id"], proposition=UNICODE_EMOJI_CRLF_TEXT
    )
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert created.status_code == 201
    assert created.json()["proposition_raw"] == UNICODE_EMOJI_CRLF_TEXT

    fetched = client.get(
        f"/api/v1/assertions/{created.json()['id']}", headers=m["contributor_headers"]
    )
    assert fetched.json()["proposition_raw"] == UNICODE_EMOJI_CRLF_TEXT


def test_comment_raw_round_trips_unicode_emoji_and_crlf_byte_exact(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]

    r = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": UNICODE_EMOJI_CRLF_TEXT},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201
    assert r.json()["comment_text_raw"] == UNICODE_EMOJI_CRLF_TEXT

    listing = client.get(
        f"/api/v1/assertions/{assertion_id}/comments", headers=m["contributor_headers"]
    )
    assert listing.json()[0]["comment_text_raw"] == UNICODE_EMOJI_CRLF_TEXT


# --- A8 x A2 composition at the exact boundary ------------------------------


def test_proposition_at_cap_boundary_containing_angle_brackets_round_trips_raw(
    client, matter_with_users
):
    """Exactly 100,000 chars, containing a shape the sanitizer alters --
    must be ACCEPTED (boundary, not over-cap) with `proposition_raw`
    byte-exact and the sanitized column still (correctly) altered.
    """
    m = matter_with_users
    marker = "see <appendix A> for details, "
    padding = "x" * (100_000 - len(marker))
    text = marker + padding
    assert len(text) == 100_000

    payload = assertion_payload(m["matter_id"], m["repository_id"], proposition=text)
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201, r.text
    assert r.json()["proposition_raw"] == text
    assert "<appendix A>" not in r.json()["proposition"]
    assert len(r.json()["proposition_raw"]) == 100_000


# --- B1: enrichment CLI on a matter with genuinely zero spans ---------------


def test_enrich_cli_on_matter_with_zero_spans_creates_nothing_and_exits_zero(
    matter_with_users, db_session
):
    from app.enrich.cli import main

    m = matter_with_users
    # No seed_document/seed_source_span call at all -- the matter has zero
    # spans, not merely spans that fail to match a heuristic pattern.
    exit_code = main(
        ["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]]
    )
    assert exit_code == 0


def test_run_enrichment_on_matter_with_zero_spans_returns_empty_list(
    db_session, matter_with_users
):
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    created = run_enrichment(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert created == []


# --- C1: MCP fetch of a nonexistent id, through the real dispatch path -----


def test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash(app):
    from app.mcp.server import create_server

    server = create_server(app.state.session_factory)
    result = asyncio.run(server.call_tool("fetch", {"assertion_id": "does-not-exist"}))

    if isinstance(result, dict):
        text = str(result)
    else:
        text = " ".join(getattr(block, "text", str(block)) for block in result)
    assert "not found" in text.lower() or "does-not-exist" in text


# --- G4: rating rationale privacy — the coverage gap QA found --------------


def test_rating_list_nulls_rationale_for_unauthorized_peer_but_not_for_rater_or_reviewer(
    client, db_session, matter_with_users
):
    """`assertion:view_rating_rationales` is granted to reviewer/admin only
    (app/services/permissions.py); a contributor who is neither the rater
    nor a reviewer must see `rationale`/`rationale_raw` nulled on someone
    else's rating, while the rater's own rating and a reviewer's view stay
    intact. No test anywhere in the repo previously exercised this specific
    unauthorized-peer-contributor path end-to-end.
    """
    m = matter_with_users
    # A second contributor with no special relationship to the rating.
    peer_id = seed_user(db_session, display_name="Peer contributor (no rationale access)")
    seed_matter_role(db_session, user_id=peer_id, matter_id=m["matter_id"], role="contributor")

    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]

    secret_rationale = "Confidential rationale text for the QA privacy probe."
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": secret_rationale},
        headers=m["rater_headers"],
    )

    unauthorized = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=auth_header(peer_id)
    )
    assert unauthorized.status_code == 200
    row = unauthorized.json()[0]
    assert row["rationale"] is None
    assert row["rationale_raw"] is None
    # Strength (non-text signal) stays visible even when rationale is gated.
    assert row["strength"] == 4

    own_view = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=m["rater_headers"]
    )
    assert own_view.json()[0]["rationale_raw"] == secret_rationale

    reviewer_view = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=m["reviewer_headers"]
    )
    assert reviewer_view.json()[0]["rationale_raw"] == secret_rationale
