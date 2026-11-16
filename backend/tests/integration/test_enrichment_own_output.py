"""Offline enrichment keys its idempotency on its own output, never stores
an exact duplicate, quotes long spans by the sentence that matched, and
refuses ids it cannot honour.

* review:16 / pipeline:11 -- agent submissions share the origin
  `model_suggested`, which enrichment used as "already suggested": a span an
  agent had cited (even as mere context) was never suggested by the
  heuristic. Enrichment rows are those whose revision 1 carries
  ENRICHMENT_REVISION_REASON; agent rows carry agent provenance.
* pipeline:11 -- two spans with one text gave two identical drafts, the
  API's exact-duplicate rule did not apply, an ingested statute section was
  suggested whole (34,157 characters) and the 100,000-character cap was
  never checked.
* pipeline:6 -- an unknown or unauthorized triggering user was recorded as
  the author, and an unset database URL ended in a traceback.
* new:enrich-foreign-evidence -- an injected enricher's span ids were
  attached as evidence even when they belonged to another matter.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

import app.enrich.pipeline as enrich_pipeline
from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.enrich.cli import main as enrich_cli
from app.enrich.pipeline import ENRICHMENT_REVISION_REASON, run_enrichment
from app.enrich.suggester import MAX_PROPOSITION_LENGTH
from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.source_span import SourceSpan
from tests.conftest import (assertion_payload, new_id, seed_document, seed_matter, seed_matter_role, seed_source_span,
                            seed_user)

BACKEND = Path(__file__).resolve().parents[2]
US_FIXTURES = BACKEND / "tests" / "fixtures" / "us_statutes"
SURVIVES = "Confidentiality survives termination of this Agreement."


def _span(db_session, m: dict, quote_text: str, document_id: str | None = None) -> str:
    document_id = document_id or seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    return seed_source_span(db_session, document_id=document_id, matter_id=m["matter_id"], quote_text=quote_text)


def _enrich(db_session, m: dict, user: str = "reviewer_id", **kwargs) -> list[dict]:
    created = run_enrichment(db_session, matter_id=m["matter_id"], triggered_by_user_id=m[user], **kwargs)
    db_session.expire_all()
    return created


def _agent_suggestion(m: dict, span_id: str, proposition: str, role: str = "contextualizes") -> dict:
    return {"repository_id": m["repository_id"], "matter_id": m["matter_id"], "assertion_type": "SURVIVES_TERMINATION",
            "proposition": proposition, "subject_entity": {"type": "SourceSpan", "id": span_id},
            "evidence": [{"source_span_id": span_id, "evidence_role": role}], "agent": {"platform": "pytest"}}


# --- review:16 / pipeline:11: idempotency keyed on enrichment's own output ----


@pytest.mark.parametrize("role", ["contextualizes", "primary_basis"])
def test_a_span_an_agent_cited_is_still_suggested_by_the_heuristic(client, db_session, matter_with_users, role):
    m = matter_with_users
    span = _span(db_session, m, SURVIVES)
    agent = client.post("/api/v1/agent/assertions", json=_agent_suggestion(
        m, span, "The confidentiality obligation outlives the agreement.", role), headers=m["contributor_headers"])
    assert agent.status_code == 201, agent.text

    created = _enrich(db_session, m)

    assert [(c["assertion_type"], c["proposition"]) for c in created] == [("SURVIVES_TERMINATION", SURVIVES)]
    assert _enrich(db_session, m) == []
    assert _enrich(db_session, m, user="contributor_id") == []


def test_enrichment_rows_and_agent_rows_are_told_apart(client, db_session, matter_with_users):
    m = matter_with_users
    span = _span(db_session, m, SURVIVES)
    agent = client.post("/api/v1/agent/assertions", json=_agent_suggestion(m, span, "Confidentiality outlives it."),
                        headers=m["contributor_headers"]).json()
    (enriched,) = _enrich(db_session, m)

    rows = {a["id"]: client.get(f"/api/v1/assertions/{a['id']}", headers=m["reviewer_headers"]).json()
            for a in (agent, enriched)}
    assert {a["origin"] for a in rows.values()} == {"model_suggested"}
    assert rows[enriched["id"]]["agent_provenance"] is None
    assert rows[enriched["id"]]["revision_history"][0]["revision_reason"] == ENRICHMENT_REVISION_REASON
    assert rows[agent["id"]]["agent_provenance"] == {"platform": "pytest", "model": None, "run_id": None}
    assert rows[agent["id"]]["revision_history"][0]["revision_reason"] == "initial creation"


# --- pipeline:11: exact duplicates ------------------------------------------------


@pytest.mark.parametrize("ending", ["withdraw", "reject"])
def test_two_spans_with_one_text_give_one_draft_across_runs_users_and_endings(client, db_session,
                                                                              matter_with_users, ending):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    twins = [_span(db_session, m, "Clause 9 survives termination of this Agreement.", doc) for _ in range(2)]

    (draft,) = _enrich(db_session, m)
    assert _enrich(db_session, m, user="contributor_id") == []
    path = f"/api/v1/assertions/{draft['id']}"
    if ending == "reject":
        assert client.post(path + "/submit", headers=m["reviewer_headers"]).status_code == 200
    assert client.post(f"{path}/{ending}", headers=m["reviewer_headers"]).status_code == 200
    assert _enrich(db_session, m) == []
    assert _enrich(db_session, m, user="contributor_id") == []

    evidence = db_session.scalars(select(AssertionEvidence.source_span_id)).all()
    assert len(evidence) == 1 and evidence[0] in twins
    assert db_session.scalar(select(func.count()).select_from(Assertion)) == 1


def test_a_live_assertion_blocks_and_another_users_draft_does_not(client, db_session, matter_with_users):
    m = matter_with_users
    proposed_text, drafted_text = SURVIVES, "This clause applies to all affiliates."
    _span(db_session, m, proposed_text)
    _span(db_session, m, drafted_text)
    for text, save_as in ((proposed_text, "proposed"), (drafted_text, "draft")):
        r = client.post("/api/v1/assertions", json=assertion_payload(
            m["matter_id"], m["repository_id"], proposition=text, save_as=save_as), headers=m["rater_headers"])
        assert r.status_code == 201, r.text

    created = _enrich(db_session, m)

    # Like a lawyer, enrichment may not copy a live proposal; another user's
    # draft is unsubmitted work and blocks no one but its author.
    assert [c["proposition"] for c in created] == [drafted_text]
    assert _enrich(db_session, m, user="rater_id") == []


def test_the_duplicate_check_holds_against_a_writer_that_commits_meanwhile(client, db_session, matter_with_users,
                                                                           monkeypatch):
    """The rule is re-checked under the write lock against committed state:
    a proposal stored after enrichment's first read still blocks."""
    m = matter_with_users
    _span(db_session, m, SURVIVES)
    original = enrich_pipeline.lock_assertion_writes

    def lock_after_a_competing_proposal(session, matter_id):
        r = client.post("/api/v1/assertions", json=assertion_payload(
            m["matter_id"], m["repository_id"], proposition=SURVIVES.upper(), save_as="proposed"),
            headers=m["rater_headers"])
        assert r.status_code == 201, r.text
        monkeypatch.setattr(enrich_pipeline, "lock_assertion_writes", original)
        original(session, matter_id)

    monkeypatch.setattr(enrich_pipeline, "lock_assertion_writes", lock_after_a_competing_proposal)

    assert _enrich(db_session, m) == []
    assert db_session.scalar(select(func.count()).select_from(Assertion)) == 1


# --- pipeline:11: what a candidate proposes ---------------------------------------


def test_an_ingested_statute_section_is_quoted_by_the_sentence_that_matched(client, db_session, matter_with_users):
    m = matter_with_users
    for name, jurisdiction in (("g3_guard_states_rows.json", "US-MT"), ("core_follow_on_2_g2_g4_rows.json", "US-ME")):
        rows = json.loads((US_FIXTURES / name).read_text(encoding="utf-8"))
        ingest_us_statute_rows(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"],
                               title=name, rows=rows if isinstance(rows, list) else rows["rows"],
                               jurisdiction=jurisdiction)
    short = "  This clause applies to all affiliates.  "
    _span(db_session, m, short)

    assert enrich_cli(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["reviewer_id"]]) == 0

    db_session.expire_all()
    created = db_session.scalars(select(Assertion).where(Assertion.origin == "model_suggested")).all()
    assert len(created) >= 3
    raw_by_id = dict(db_session.execute(select(AssertionRevision.assertion_id, AssertionRevision.proposition_raw).where(
        AssertionRevision.assertion_id.in_([a.id for a in created]))).all())
    for assertion in created:
        raw = raw_by_id[assertion.id]
        (quote,) = db_session.scalars(select(SourceSpan.quote_text).join(
            AssertionEvidence, AssertionEvidence.source_span_id == SourceSpan.id).where(
            AssertionEvidence.assertion_id == assertion.id)).all()
        assert len(raw) <= MAX_PROPOSITION_LENGTH and raw in quote
    raws = set(raw_by_id.values())
    assert "This section applies to every franchisee." in raws
    assert any(raw.startswith('(b) "Stop", "stopping", or "standing", when prohibited, means') for raw in raws)
    assert short in raws  # a short span is still suggested whole, byte-exact


class _Enricher:
    def __init__(self, *candidates: dict) -> None:
        self.candidates = candidates

    def suggest(self, spans):
        return list(self.candidates)


def test_the_api_length_cap_applies_to_every_enricher(db_session, matter_with_users):
    m = matter_with_users
    over, at = _span(db_session, m, "Over the cap."), _span(db_session, m, "At the cap.")
    created = _enrich(db_session, m, enricher=_Enricher(
        {"assertion_type": "RELEVANT_TO", "proposition": "x" * 100_001, "evidence_span_ids": [over]},
        {"assertion_type": "RELEVANT_TO", "proposition": "<b>y</b>" + "y" * 99_992, "evidence_span_ids": [at]},
        {"assertion_type": "RELEVANT_TO", "proposition": "<script>only markup</script>", "evidence_span_ids": [over]},
    ))

    (stored,) = created
    revision = db_session.scalars(select(AssertionRevision).where(AssertionRevision.assertion_id == stored["id"])).one()
    assert len(revision.proposition_raw) == 100_000 and revision.proposition_raw.startswith("<b>y</b>")
    assert stored["proposition"] == "y" * 99_993


def test_evidence_from_another_matter_is_never_attached(db_session, matter_with_users):
    m = matter_with_users
    own = _span(db_session, m, "Own span.")
    other_matter = seed_matter(db_session, repository_id=m["repository_id"])
    other_doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=other_matter)
    foreign = seed_source_span(db_session, document_id=other_doc, matter_id=other_matter, quote_text="Foreign span.")

    created = _enrich(db_session, m, enricher=_Enricher(
        {"assertion_type": "RELEVANT_TO", "proposition": "Cites only a foreign span.", "evidence_span_ids": [foreign]},
        {"assertion_type": "RELEVANT_TO", "proposition": "Cites both.", "evidence_span_ids": [foreign, own]},
    ))

    assert [c["proposition"] for c in created] == ["Cites both."]
    assert db_session.scalars(select(AssertionEvidence.source_span_id)).all() == [own]


# --- pipeline:6: the enrich CLI refuses what it cannot honour ----------------------


def _assertion_count(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(Assertion))


def test_the_cli_refuses_an_unknown_or_unauthorized_user(db_session, matter_with_users, capsys):
    m = matter_with_users
    _span(db_session, m, SURVIVES)
    viewer = seed_user(db_session)
    seed_matter_role(db_session, user_id=viewer, matter_id=m["matter_id"], role="viewer")

    for user, message in (("ghost-user", "user 'ghost-user' does not exist"),
                          (m["outsider_id"], "has no contributor, reviewer or admin role"),
                          (viewer, "has no contributor, reviewer or admin role")):
        assert enrich_cli(["--matter-id", m["matter_id"], "--triggered-by-user-id", user]) == 1
        assert message in capsys.readouterr().err
    assert _assertion_count(db_session) == 0
    assert enrich_cli(["--matter-id", new_id(), "--triggered-by-user-id", m["reviewer_id"]]) == 1
    assert "does not exist" in capsys.readouterr().err


@pytest.mark.parametrize("url", [None, "sqlite:///:memory:", "sqlite://"])
def test_the_cli_refuses_a_database_no_other_process_can_share(url, tmp_path):
    env = {key: value for key, value in os.environ.items() if key != "LEXGRAPH_DATABASE_URL"}
    if url is not None:
        env["LEXGRAPH_DATABASE_URL"] = url

    run = subprocess.run([sys.executable, "-m", "app.enrich.cli", "--matter-id", "m", "--triggered-by-user-id", "u"],
                         capture_output=True, text=True, env=env, cwd=BACKEND, timeout=120)

    assert run.returncode == 1
    assert run.stderr.startswith("enrichment failed: set LEXGRAPH_DATABASE_URL")
    assert "Traceback" not in run.stderr


def test_the_cli_refuses_a_database_without_lexgraph_tables(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{tmp_path / 'empty.db'}")

    assert enrich_cli(["--matter-id", "m", "--triggered-by-user-id", "u"]) == 1
    assert "not an initialized LexGraph database" in capsys.readouterr().err
