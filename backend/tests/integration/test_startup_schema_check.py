"""The API server refuses to serve a database it cannot use, and names the fix
(findings api:3, ops:1, pipeline:7: the server half of the upgrade path).

Before: uvicorn started against a workspace provisioned before 2026-08-05,
``/healthz`` answered 200, and every assertion endpoint answered 500
(``no such column: assertions.subject_unit_path``, then
``documents.jurisdiction``). Now startup fails with the exact
``python -m app.migrate --db PATH`` command, and after that command the same
workspace, with its existing data, is served normally.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.main import create_app
from app.migrate import SchemaNotCurrentError
from app.migrate import main as migrate_main
from tests.conftest import assertion_payload, seed_document, seed_source_span
from tests.schema_history import PRE_AUGUST, build_fresh_db, build_historical_db, rows

BACKEND = Path(__file__).resolve().parents[2]


def _start(monkeypatch, url: str | None) -> int:
    """Run the app's real lifespan (as uvicorn does) against ``url``."""
    if url is None:
        monkeypatch.delenv("LEXGRAPH_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("LEXGRAPH_DATABASE_URL", url)
    application = create_app()
    try:
        with TestClient(application) as client:
            return client.get("/healthz").status_code
    finally:
        application.state.engine.dispose()


def test_pre_august_database_fails_fast_with_the_exact_migrate_command(tmp_path, monkeypatch):
    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    with pytest.raises(SchemaNotCurrentError) as excinfo:
        _start(monkeypatch, f"sqlite:///{db}")
    message = str(excinfo.value)
    assert f"{sys.executable} -m app.migrate --db {db}" in message
    for missing in (
        "column documents.jurisdiction",
        "column assertions.subject_unit_path",
        "column articles.heading_breadcrumbs",
    ):
        assert missing in message


def test_server_starts_once_the_old_database_is_migrated(tmp_path, monkeypatch):
    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    assert migrate_main(["--db", str(db)]) == 0
    assert _start(monkeypatch, f"sqlite:///{db}") == 200


def test_server_starts_on_a_freshly_created_database(tmp_path, monkeypatch):
    db = build_fresh_db(tmp_path / "fresh.db")
    assert _start(monkeypatch, f"sqlite:///{db}") == 200


def test_database_without_lexgraph_tables_points_to_bootstrap(tmp_path, monkeypatch):
    db = tmp_path / "empty.db"
    db.touch()
    with pytest.raises(SchemaNotCurrentError, match=rf"-m app\.bootstrap --db {db}"):
        _start(monkeypatch, f"sqlite:///{db}")


def test_missing_database_file_is_reported_and_not_created(tmp_path, monkeypatch):
    db = tmp_path / "typo.db"
    with pytest.raises(SchemaNotCurrentError, match="no database file at"):
        _start(monkeypatch, f"sqlite:///{db}")
    assert not db.exists()


def test_in_memory_default_is_refused(monkeypatch):
    with pytest.raises(SchemaNotCurrentError, match="LEXGRAPH_DATABASE_URL is not set"):
        _start(monkeypatch, None)


def test_uvicorn_exits_on_an_old_database_and_prints_the_migrate_command(tmp_path):
    """The real process: no port is ever bound, the exit is immediate."""
    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": f"sqlite:///{db}"}
    proc = subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "0"],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60,
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert "Application startup failed" in output
    assert f"-m app.migrate --db {db}" in output


# What a workspace looked like before each historical change, applied to a
# database populated by today's fixtures (so its users authenticate exactly as
# every other test's do).
_RESHAPE_TO = {
    "2026-07-26": [
        "DROP TABLE definitions",
        "DROP TABLE articles",
        "ALTER TABLE documents DROP COLUMN jurisdiction",
        "ALTER TABLE assertions DROP COLUMN subject_unit_path",
        "ALTER TABLE assertion_revisions DROP COLUMN proposition_raw",
        "ALTER TABLE assertion_comments DROP COLUMN comment_text_raw",
        "ALTER TABLE assertion_ratings DROP COLUMN rationale_raw",
    ],
    "2026-07-31": [
        "ALTER TABLE articles DROP COLUMN heading_breadcrumbs",
        "ALTER TABLE documents DROP COLUMN jurisdiction",
        "ALTER TABLE assertions DROP COLUMN subject_unit_path",
    ],
}


@pytest.mark.parametrize("provisioned", sorted(_RESHAPE_TO))
def test_existing_workspace_is_served_again_after_app_migrate(
    app, client, db_session, matter_with_users, provisioned
):
    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text="Either party may terminate."
    )
    payload = assertion_payload(
        m["matter_id"], m["repository_id"], evidence=[{"source_span_id": span_id, "evidence_role": "supports"}]
    )
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert created.status_code == 201, created.text
    assertion_id = created.json()["id"]
    commented = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "Agreed, see Clause 8.4."},
        headers=m["rater_headers"],
    )
    assert commented.status_code == 201
    db_session.close()

    db_path = make_url(app.state.settings.database_url).database
    conn = sqlite3.connect(db_path)
    try:
        for statement in _RESHAPE_TO[provisioned]:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()

    listing = f"/api/v1/assertions?matter_id={m['matter_id']}"
    with pytest.raises(OperationalError, match="no such column"):  # the reported HTTP 500
        client.get(listing, headers=m["reviewer_headers"])

    assert migrate_main(["--db", db_path]) == 0

    listed = client.get(listing, headers=m["reviewer_headers"])
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [assertion_id]
    detail = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"])
    assert detail.status_code == 200
    body = detail.json()
    assert body["proposition_raw"] == payload["proposition"]
    assert [(e["source_span_id"], e["quote_text"]) for e in body["evidence"]] == [
        (span_id, "Either party may terminate.")
    ]
    comments = client.get(f"/api/v1/assertions/{assertion_id}/comments", headers=m["reviewer_headers"])
    assert comments.status_code == 200
    assert "Agreed, see Clause 8.4." in comments.text
    for path in (
        f"/api/v1/assertions/{assertion_id}/evidence",
        f"/api/v1/assertions/{assertion_id}/revisions",
        f"/api/v1/matters/{m['matter_id']}/graph",
        f"/api/v1/matters/{m['matter_id']}/entities",
    ):
        assert client.get(path, headers=m["reviewer_headers"]).status_code == 200, path
    another = client.post(
        "/api/v1/assertions",
        json=assertion_payload(
            m["matter_id"],
            m["repository_id"],
            proposition="Clause 9 survives termination of the agreement.",
            evidence=[{"source_span_id": span_id, "evidence_role": "supports"}],
        ),
        headers=m["contributor_headers"],
    )
    assert another.status_code == 201, another.text
    assert rows(Path(db_path), "SELECT jurisdiction FROM documents") == [("IL",)]
