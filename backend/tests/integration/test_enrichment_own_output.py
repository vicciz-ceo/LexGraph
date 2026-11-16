"""Offline enrichment refuses ids it cannot honour (audit finding
pipeline:6): an unknown or unauthorized triggering user was recorded as the
author of the suggestions, and an unset database URL ended in a traceback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.enrich.cli import main as enrich_cli
from app.models.assertion import Assertion
from tests.conftest import new_id, seed_document, seed_matter_role, seed_source_span, seed_user

BACKEND = Path(__file__).resolve().parents[2]
SURVIVES = "Confidentiality survives termination of this Agreement."


def _span(db_session, m: dict, quote_text: str, document_id: str | None = None) -> str:
    document_id = document_id or seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    return seed_source_span(db_session, document_id=document_id, matter_id=m["matter_id"], quote_text=quote_text)


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
