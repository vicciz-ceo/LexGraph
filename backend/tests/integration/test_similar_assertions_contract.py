"""What a suggestion's similar-assertion warning carries (audit findings
agent:2 and ui:5).

A matter that has had the definition-linking pass holds hundreds of
generated 'Article N uses the definition of "X".' assertions, and an
ordinary definitional claim used to come back with every one of them: an
unbounded `similar_assertions` list (tens of thousands of entries, megabytes
on the agent CLI and in one MCP tool result) of bare `{assertion_id,
match_kind, score}` triples the web form rendered as raw UUIDs and empty
quotes. Now every surface (lawyer and agent REST create, the agent CLI, MCP
`suggest_assertion` and GET .../related) lists the strongest
SIMILAR_ASSERTIONS_LIMIT matches -- score descending, then assertion id --
each with the matched assertion's text, status and type, next to the count
of all matches. The exact-duplicate 409 also names the existing assertion as
data.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.definition_links.ingest import ingest_wiki_law
from app.definition_links.pipeline import run_definition_linking
from app.mcp.server import create_server
from app.models.assertion import Assertion
from app.services.duplicates import (
    SIMILAR_ASSERTIONS_LIMIT,
    SIMILAR_PROPOSITION_DISPLAY_LENGTH,
    SIMILARITY_THRESHOLD,
    find_related_assertions,
    surface_similar,
)
from tests.conftest import assertion_payload, new_id

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"
BACKEND = Path(__file__).resolve().parents[2]
CLAIM = 'Article 8 relies on the definition of "database" in Article 3.'
ENTRY_KEYS = {"assertion_id", "match_kind", "score", "proposition", "status", "assertion_type"}


@pytest.fixture
def linked_matter(db_session, matter_with_users):
    """A matter holding real definition-linking output for the wiki fixtures."""
    m = matter_with_users
    document_id = None
    for path in sorted(FIXTURES.glob("*.wiki")):
        result = ingest_wiki_law(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"],
                                 title=path.stem, wiki_text=path.read_text(encoding="utf-8"))
        document_id = document_id or result["document_id"]
    linked = run_definition_linking(db_session, matter_id=m["matter_id"], triggered_by_user_id=m["reviewer_id"])
    assert len(linked["created_assertions"]) > 3 * SIMILAR_ASSERTIONS_LIMIT
    return {**m, "document_id": document_id}


def _agent_claim(m: dict, proposition: str = CLAIM) -> dict:
    return dict(repository_id=m["repository_id"], matter_id=m["matter_id"], assertion_type="INTERPRETS",
                proposition=proposition, subject_entity={"type": "Document", "id": m["document_id"]},
                agent={"platform": "pytest"}, save_as="draft")


def _fields(a) -> dict:
    return {"id": a.id, "proposition": a.proposition, "assertion_type": a.assertion_type,
            "subject_entity": {"type": a.subject_entity_type, "id": a.subject_entity_id},
            "object_entity": ({"type": a.object_entity_type, "id": a.object_entity_id}
                              if a.object_entity_type else None)}


def _all_matches(db_session, matter_id: str, candidate: dict, *, exclude_id: str) -> list[dict]:
    """The uncapped matches, computed directly from the matter's rows."""
    rows = db_session.scalars(select(Assertion).where(Assertion.matter_id == matter_id,
                                                      Assertion.id != exclude_id)).all()
    return find_related_assertions(candidate, [_fields(a) for a in rows])


def _assert_capped_entries(client, headers, entries: list[dict]) -> None:
    assert 0 < len(entries) <= SIMILAR_ASSERTIONS_LIMIT
    assert all(ENTRY_KEYS <= set(entry) for entry in entries), entries[0]
    assert [(e["score"], e["assertion_id"]) for e in entries] == sorted(
        ((e["score"], e["assertion_id"]) for e in entries), key=lambda k: (-k[0], k[1]))
    for entry in entries[:3]:
        matched = client.get(f"/api/v1/assertions/{entry['assertion_id']}", headers=headers).json()
        assert (entry["proposition"], entry["status"], entry["assertion_type"]) == (
            matched["proposition"], matched["status"], matched["assertion_type"])


def test_agent_create_lists_the_strongest_matches_and_counts_all_of_them(client, db_session, linked_matter):
    m = linked_matter
    r = client.post("/api/v1/agent/assertions", json=_agent_claim(m), headers=m["contributor_headers"])

    assert r.status_code == 201, r.text
    body = r.json()
    _assert_capped_entries(client, m["reviewer_headers"], body["similar_assertions"])
    created = db_session.get(Assertion, body["id"])
    everything = _all_matches(db_session, m["matter_id"], _fields(created), exclude_id=body["id"])
    assert body["similar_assertions_total"] == len(everything) > SIMILAR_ASSERTIONS_LIMIT
    assert body["similar_assertions_truncated"] is True
    strongest = sorted(everything, key=lambda e: (-e["score"], e["assertion_id"]))[:SIMILAR_ASSERTIONS_LIMIT]
    assert [e["assertion_id"] for e in body["similar_assertions"]] == [e["assertion_id"] for e in strongest]
    assert len(r.content) < 20_000


def test_a_small_matter_lists_every_match_untruncated(client, matter_with_users):
    m = matter_with_users
    texts = ["Clause 8.4 creates a limited exception to the notification obligation in Clause 8.2.",
             "Clause 8.4 creates a narrow exception to the Clause 8.2 notice obligation."]
    first = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"],
                        proposition=texts[0], save_as="proposed"), headers=m["contributor_headers"]).json()

    r = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"],
                    proposition=texts[1]), headers=m["rater_headers"])

    assert r.status_code == 201, r.text
    body = r.json()
    (entry,) = body["similar_assertions"]
    assert entry["assertion_id"] == first["id"] and entry["match_kind"] == "similar"
    assert (entry["proposition"], entry["status"], entry["assertion_type"]) == (
        texts[0], "proposed", "CREATES_EXCEPTION_TO")
    assert (body["similar_assertions_total"], body["similar_assertions_truncated"]) == (1, False)
    lone = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"],
                       proposition="Nothing else in this matter reads like this."), headers=m["rater_headers"]).json()
    assert (lone["similar_assertions"], lone["similar_assertions_total"], lone["similar_assertions_truncated"]) == (
        [], 0, False)


def test_agent_cli_and_mcp_pass_the_bounded_list_through(app, linked_matter):
    m = linked_matter
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": str(app.state.engine.url),
           "LEXGRAPH_AGENT_USER_ID": m["contributor_id"]}
    cli = subprocess.run([sys.executable, "-m", "app.agent_cli", "suggest"], input=json.dumps(_agent_claim(m)),
                         capture_output=True, text=True, env=env, cwd=BACKEND, timeout=120)
    assert cli.returncode == 0, cli.stderr
    printed = json.loads(cli.stdout)
    assert len(printed["similar_assertions"]) == SIMILAR_ASSERTIONS_LIMIT < printed["similar_assertions_total"]

    server = create_server(app.state.session_factory, agent_user_id=m["contributor_id"])
    payload = _agent_claim(m, 'Article 9 relies on the definition of "database" in Article 3.')
    result = asyncio.run(server.call_tool("suggest_assertion", {"payload": payload}))
    assert not getattr(result, "isError", False), result
    text = "".join(getattr(block, "text", "") for block in getattr(result, "content", result))
    returned = json.loads(text)
    assert len(returned["similar_assertions"]) == SIMILAR_ASSERTIONS_LIMIT < returned["similar_assertions_total"]
    assert returned["similar_assertions_truncated"] is True
    assert len(text) < 20_000


def test_related_is_capped_and_gives_the_total_in_a_header(client, db_session, linked_matter):
    m = linked_matter
    uses = db_session.scalars(select(Assertion).where(Assertion.matter_id == m["matter_id"],
                                                      Assertion.assertion_type == "USES_DEFINITION")).first()

    r = client.get(f"/api/v1/assertions/{uses.id}/related", headers=m["reviewer_headers"])

    assert r.status_code == 200, r.text
    related = r.json()
    assert isinstance(related, list)
    _assert_capped_entries(client, m["reviewer_headers"], related)
    total = len(_all_matches(db_session, m["matter_id"], _fields(uses), exclude_id=uses.id))
    assert int(r.headers["X-Total-Count"]) == total > SIMILAR_ASSERTIONS_LIMIT
    assert uses.id not in {entry["assertion_id"] for entry in related}


def test_a_long_matched_proposition_is_shortened_for_display(client, db_session, matter_with_users):
    m = matter_with_users
    subject, obj = {"type": "Provision", "id": new_id()}, {"type": "Provision", "id": new_id()}
    long_text = "The indemnity in Clause 14 covers third-party claims. " * 100
    client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition=long_text, subject_entity=subject, object_entity=obj),
        headers=m["contributor_headers"])

    r = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition="Clause 14 excludes consequential loss.",
        subject_entity=subject, object_entity=obj), headers=m["contributor_headers"])

    (entry,) = r.json()["similar_assertions"]
    assert entry["match_kind"] == "same_subject_type_object"
    assert len(entry["proposition"]) <= SIMILAR_PROPOSITION_DISPLAY_LENGTH
    assert entry["proposition"].endswith("…")
    assert long_text.startswith(entry["proposition"][:-1])


def test_an_exact_duplicate_beyond_the_cap_still_blocks_and_names_the_existing_assertion(client, db_session,
                                                                                         linked_matter):
    m = linked_matter
    first = client.post("/api/v1/agent/assertions", json=_agent_claim(m), headers=m["contributor_headers"])
    assert first.status_code == 201, first.text
    existing = first.json()["id"]
    detail = f"duplicate: an identical proposition already exists in this matter (assertion {existing})"

    again = client.post("/api/v1/agent/assertions", json=_agent_claim(m, "  " + CLAIM.upper() + "  "),
                        headers=m["contributor_headers"])
    lawyer = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition=CLAIM.lower()), headers=m["contributor_headers"])

    for response in (again, lawyer):
        assert response.status_code == 409, response.text
        assert response.json() == {"detail": detail, "existing_assertion_id": existing}
    assert db_session.scalar(select(func.count()).select_from(Assertion).where(
        func.lower(Assertion.proposition).contains("relies on the definition"))) == 1


def test_edits_and_submissions_name_the_existing_assertion_and_other_errors_keep_their_shape(client,
                                                                                             matter_with_users):
    m = matter_with_users
    # Another user's draft does not block, so the twin is created first.
    twin = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition="Clause 3 governs renewals."),
        headers=m["rater_headers"]).json()["id"]
    live = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition="Clause 3 governs renewals.", save_as="proposed"),
        headers=m["contributor_headers"]).json()["id"]
    mine = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition="Clause 4 governs notices."),
        headers=m["reviewer_headers"]).json()["id"]
    expected = {"detail": f"duplicate: an identical proposition already exists in this matter (assertion {live})",
                "existing_assertion_id": live}

    patch = client.patch(f"/api/v1/assertions/{mine}", json={"proposition": "clause 3 governs renewals."},
                         headers=m["reviewer_headers"])
    revision = client.post(f"/api/v1/assertions/{mine}/revisions", json={"proposition": "CLAUSE 3 GOVERNS RENEWALS."},
                           headers=m["reviewer_headers"])
    submit = client.post(f"/api/v1/assertions/{twin}/submit", headers=m["rater_headers"])

    for response in (patch, revision, submit):
        assert (response.status_code, response.json()) == (409, expected)
    stale = client.patch(f"/api/v1/assertions/{mine}", json={"proposition": "Clause 4 governs all notices.",
                                                             "expected_revision_number": 7},
                         headers=m["reviewer_headers"])
    assert (stale.status_code, stale.json()) == (
        409, {"detail": "assertion has been modified since expected_revision_number"})
    missing = client.get(f"/api/v1/assertions/{new_id()}/related", headers=m["rater_headers"])
    assert (missing.status_code, missing.json()) == (404, {"detail": "assertion not found"})


def test_surface_similar_orders_by_score_then_id_and_counts_before_the_cap():
    class Row:
        def __init__(self, proposition):
            self.proposition, self.status, self.assertion_type = proposition, "proposed", "INTERPRETS"

    matches = [{"assertion_id": f"id-{i:02d}", "match_kind": "similar", "score": 0.6 + (i % 3) / 10}
               for i in range(30)]
    shown, total = surface_similar(matches, {m["assertion_id"]: Row(f"text {m['assertion_id']}") for m in matches})

    assert total == 30 and len(shown) == SIMILAR_ASSERTIONS_LIMIT
    assert [(e["score"], e["assertion_id"]) for e in shown] == sorted(
        ((m["score"], m["assertion_id"]) for m in matches), key=lambda k: (-k[0], k[1]))[:SIMILAR_ASSERTIONS_LIMIT]
    assert shown[0]["proposition"] == f"text {shown[0]['assertion_id']}"


def test_the_prefiltered_similarity_pass_finds_exactly_what_difflib_finds():
    """The length prefilter and the per-text memo (agent:2) change no
    result: every pair is compared with what an unfiltered difflib ratio
    over every row reports."""
    rng = random.Random(20261116)
    words = "the of a clause party notice shall survive termination liability fees data article term".split()
    texts = [" ".join(rng.choice(words) for _ in range(rng.randint(1, 30))) for _ in range(400)]
    texts += texts[:50]  # repeated wording, as generated rows have
    existing = [{"id": f"r{i:03d}", "proposition": text, "assertion_type": "INTERPRETS",
                 "subject_entity": {"type": "Provision", "id": f"p{i}"}, "object_entity": None}
                for i, text in enumerate(texts)]
    for claim in texts[:25] + ["clause", "the notice shall survive termination of the fees"]:
        candidate = {"proposition": claim, "assertion_type": "SUPPORTS",
                     "subject_entity": {"type": "Provision", "id": "x"}, "object_entity": None}
        expected = []
        for row in existing:
            a, b = claim.strip().lower(), row["proposition"].strip().lower()
            if a == b:
                expected.append((row["id"], "exact_proposition", 1.0))
                continue
            ratio = SequenceMatcher(None, a, b).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                expected.append((row["id"], "similar", round(ratio, 4)))
        expected.sort(key=lambda e: e[2], reverse=True)
        found = [(m["assertion_id"], m["match_kind"], m["score"]) for m in find_related_assertions(candidate, existing)]
        assert found == expected
