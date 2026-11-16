"""The agent CLI's I/O contract (agent:5, agent:6).

JSON input and output are UTF-8 whatever the locale or PYTHONIOENCODING, and a
committed suggestion is never reported as a failure. Every error is exactly
one JSON object on stderr with exit 1: usage errors included, no warning text
before it, and environment failures are not labelled 422 ("fix the payload").
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models.assertion import Assertion
from app.models.assertion_revision import AssertionRevision
from tests.conftest import seed_document, seed_source_span
from tests.integration.agent_surface_helpers import BACKEND, agent_env, cli_error, cli_json, run_cli

LEGAL_TEXT = "§ 8 Confidentiality survives termination — per the “survival” clause (Acme ↔ Blue Ridge)."
C_LOCALE = {"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
ENCODINGS = [{"PYTHONIOENCODING": "latin-1"}, {"PYTHONIOENCODING": "cp1252"},
             {"PYTHONIOENCODING": "ascii"}, C_LOCALE]


@pytest.fixture
def cli(app, matter_with_users):
    def run(*args, stdin=None, cwd=None, **extra):
        env = agent_env(str(app.state.engine.url), matter_with_users["contributor_id"], **extra)
        return run_cli(*args, env=env, stdin=stdin, **({"cwd": cwd} if cwd else {}))
    return run


@pytest.fixture
def payload(db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"],
                        title="Vertrag über Übergabe — Acme ↔ Blue Ridge")
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"], quote_text="„Die Übergabe“ erfolgt §§ 3–5.")
    return {"repository_id": m["repository_id"], "matter_id": m["matter_id"], "assertion_type": "SURVIVES_TERMINATION",
            "proposition": LEGAL_TEXT, "subject_entity": {"type": "Document", "id": doc},
            "evidence": [{"source_span_id": span, "evidence_role": "primary_basis"}], "agent": {"platform": "probe"}}


def _stored(db_session) -> list[str]:
    db_session.expire_all()
    return list(db_session.scalars(select(AssertionRevision.proposition_raw)))


@pytest.mark.parametrize("encoding", ENCODINGS, ids=["latin-1", "cp1252", "ascii", "C-locale"])
def test_raw_utf8_stdin_is_stored_exactly(cli, db_session, payload, encoding):
    created = cli_json(cli("suggest", stdin=json.dumps(payload, ensure_ascii=False).encode("utf-8"), **encoding))
    assert created["proposition_raw"] == LEGAL_TEXT
    assert _stored(db_session) == [LEGAL_TEXT]


@pytest.mark.parametrize("encoding", ENCODINGS, ids=["latin-1", "cp1252", "ascii", "C-locale"])
def test_escaped_stdin_is_committed_once_and_reported_as_success(cli, db_session, payload, encoding):
    result = cli("suggest", stdin=json.dumps(payload).encode("ascii"), **encoding)
    assert cli_json(result)["id"] == db_session.scalar(select(Assertion.id))
    assert _stored(db_session) == [LEGAL_TEXT]


@pytest.mark.parametrize("bom", [False, True])
def test_utf8_input_file_is_read_as_utf8_under_the_c_locale(cli, db_session, payload, tmp_path, bom):
    path = tmp_path / "suggestion.json"
    path.write_bytes(("\ufeff" if bom else "").encode("utf-8") + json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    cli_json(cli("suggest", "--input", str(path), **C_LOCALE))
    assert _stored(db_session) == [LEGAL_TEXT]


def test_utf8_bom_on_stdin_is_accepted(cli, db_session, payload):
    cli_json(cli("suggest", stdin=b"\xef\xbb\xbf" + json.dumps(payload, ensure_ascii=False).encode("utf-8")))
    assert _stored(db_session) == [LEGAL_TEXT]


def test_non_utf8_input_is_rejected_without_storing(cli, db_session, payload, tmp_path):
    path = tmp_path / "cp1252.json"
    path.write_bytes(json.dumps(payload, ensure_ascii=False).replace("↔", "-").encode("cp1252"))
    body = cli_error(cli("suggest", "--input", str(path)))
    assert body["status"] == 422 and "UTF-8" in body["error"], body
    assert db_session.scalar(select(func.count()).select_from(Assertion)) == 0


@pytest.mark.parametrize("encoding", ENCODINGS, ids=["latin-1", "cp1252", "ascii", "C-locale"])
def test_context_output_is_utf8_json(cli, payload, matter_with_users, encoding):
    result = cli("context", "--matter-id", matter_with_users["matter_id"], **encoding)
    data = cli_json(result)
    assert data["entities"]["items"][0]["label"] == "Vertrag über Übergabe — Acme ↔ Blue Ridge"
    assert data["source_spans"]["items"][0]["quote_text"] == "„Die Übergabe“ erfolgt §§ 3–5."
    assert "Vertrag über Übergabe — Acme ↔ Blue Ridge".encode("utf-8") in result.stdout


def test_non_ascii_arguments_survive_a_c_locale(cli, payload, matter_with_users):
    # Under a C/ASCII locale Python decodes argv bytes as ASCII + surrogateescape.
    result = cli("context", "--matter-id", matter_with_users["matter_id"], "--query", "über übergabe", **C_LOCALE)
    assert cli_json(result)["entities"]["items"][0]["label"] == "Vertrag über Übergabe — Acme ↔ Blue Ridge"


@pytest.mark.parametrize("encoding", ENCODINGS, ids=["latin-1", "cp1252", "ascii", "C-locale"])
def test_error_messages_are_utf8_json(cli, payload, encoding):
    result = cli("suggest", stdin=json.dumps({**payload, "jurisdiction": "Übergabe ↔"}).encode(), **encoding)
    assert cli_error(result) == {"error": "jurisdiction 'Übergabe ↔' is not in the controlled vocabulary", "status": 422}


@pytest.mark.parametrize("change", [
    {"assertion_type": "IMPLIES"}, {"jurisdiction": "Israel"},
    {"effective_from": "2030-01-01", "effective_to": "2029-01-01"},
])
def test_semantic_errors_are_one_json_object_with_status_422(cli, payload, change):
    assert cli_error(cli("suggest", stdin=json.dumps({**payload, **change}).encode()))["status"] == 422


def test_pydantic_errors_name_the_failing_fields(cli, payload):
    body = cli_error(cli("suggest", stdin=json.dumps({**payload, "confidence": 1.5, "agent": None}).encode()))
    assert body["status"] == 422 and {issue["field"] for issue in body["issues"]} == {"confidence", "agent"}, body
    assert "confidence" in body["error"] and "agent" in body["error"], body


def test_library_warnings_never_precede_the_json(app, matter_with_users, tmp_path):
    # An unrecognised SQLite URL option makes SQLAlchemy warn on connect.
    url = f"{app.state.engine.url}?lexgraph_probe=1"
    result = run_cli("context", "--matter-id", "unknown", env=agent_env(url, matter_with_users["contributor_id"]))
    assert cli_error(result) == {"error": "no access to matter", "status": 403}


@pytest.mark.parametrize("args", [
    ["--user-id", "X", "context", "--limit", "abc"], [], ["bogus"], ["schema", "--bogus"], ["context", "--offset"],
])
def test_usage_errors_are_json_with_status_400(cli, args):
    body = cli_error(cli(*args))
    assert body["status"] == 400 and "\n" not in body["error"] and "--help" in body["error"], body


def test_user_id_is_accepted_after_the_subcommand(cli, matter_with_users):
    assert cli_json(cli("context", "--user-id", matter_with_users["reviewer_id"]))["user"]["id"] == matter_with_users["reviewer_id"]
    assert cli_error(cli("context", "--user-id", "nobody")) == {"error": "unknown user", "status": 401}


def test_missing_actor_is_401(app):
    body = cli_error(run_cli("context", env=agent_env(str(app.state.engine.url))))
    assert body["status"] == 401 and "LEXGRAPH_AGENT_USER_ID" in body["error"], body


def test_unreadable_input_file_is_400_not_422(cli, tmp_path):
    body = cli_error(cli("suggest", "--input", str(tmp_path / "missing.json")))
    assert body["status"] == 400 and "missing.json" in body["error"], body


@pytest.mark.parametrize("url", ["sqlite:////nonexistent-lexgraph-dir/x.db", "postgresql://localhost/lexgraph"])
def test_database_failures_are_500_json_without_traceback(tmp_path, url):
    body = cli_error(run_cli("context", env=agent_env(url, "viewer"), cwd=tmp_path))
    assert body["status"] == 500 and "Traceback" not in body["error"], body


def test_unopenable_database_is_500(tmp_path):
    (tmp_path / "dir.db").mkdir()
    body = cli_error(run_cli("context", env=agent_env(f"sqlite:///{tmp_path / 'dir.db'}", "viewer"), cwd=tmp_path))
    assert body["status"] == 500 and str(tmp_path / "dir.db") in body["error"], body


def test_help_is_plain_usage_on_stdout(cli):
    result = cli("--help")
    assert result.returncode == 0 and b"usage:" in result.stdout and result.stderr == b""


def test_output_failure_after_commit_reports_the_created_id(app, db_session, matter_with_users, payload):
    full = Path("/dev/full")
    if not full.exists():
        pytest.skip("needs /dev/full")
    env = agent_env(str(app.state.engine.url), matter_with_users["contributor_id"])
    with full.open("wb") as sink:
        result = subprocess.run([sys.executable, "-m", "app.agent_cli", "suggest"], input=json.dumps(payload).encode(),
                                stdout=sink, stderr=subprocess.PIPE, env=env, cwd=BACKEND, timeout=120)
    body = json.loads(result.stderr.decode("utf-8"))
    assert result.returncode == 1 and body["status"] == 500 and body["committed"] is True, body
    assert body["id"] == db_session.scalar(select(Assertion.id)), body
