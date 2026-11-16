"""The CLI and the MCP server check their database before using it
(agent:3, ops:2, agent:4, review:21).

Opening SQLite creates a missing file, so a mistyped or relative URL used to
leave a stray 0-byte database and report "not initialized" (CLI) or start a
server whose every tool failed (MCP). Both now refuse with the resolved path,
create nothing, and the MCP server exits instead of looking Connected.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from tests.integration.agent_surface_helpers import agent_env, cli_error, cli_json, run_cli


@pytest.fixture
def workspace_db(app, matter_with_users) -> Path:
    """The fixture database (schema + one matter) as a file path."""
    return Path(app.state.engine.url.database)


def _files(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir())


@pytest.mark.parametrize("command", [["context"], ["suggest"]])
def test_cli_relative_url_from_another_directory_creates_nothing(tmp_path, workspace_db, matter_with_users, command):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = agent_env(f"sqlite:///{workspace_db.name}", matter_with_users["contributor_id"])
    body = cli_error(run_cli(*command, env=env, cwd=elsewhere, stdin=b"{}"))
    assert body["status"] == 500, body
    assert str(elsewhere / workspace_db.name) in body["error"] and "not found" in body["error"], body
    assert str(elsewhere) in body["error"] and "Nothing was created" in body["error"], body
    assert _files(elsewhere) == []


def test_cli_relative_url_from_the_database_directory_still_works(workspace_db, matter_with_users):
    env = agent_env(f"sqlite:///{workspace_db.name}", matter_with_users["contributor_id"])
    result = cli_json(run_cli("context", env=env, cwd=workspace_db.parent))
    assert [m["id"] for m in result["matters"]] == [matter_with_users["matter_id"]]


def test_cli_absolute_url_works_from_any_directory(tmp_path, workspace_db, matter_with_users):
    env = agent_env(f"sqlite:///{workspace_db}", matter_with_users["contributor_id"])
    assert cli_json(run_cli("context", env=env, cwd=tmp_path))["user"]["id"] == matter_with_users["contributor_id"]


def test_cli_mistyped_absolute_path_is_not_created(tmp_path, matter_with_users):
    missing = tmp_path / "typo_does_not_exist.db"
    body = cli_error(run_cli("context", env=agent_env(f"sqlite:///{missing}", "viewer"), cwd=tmp_path))
    assert body["status"] == 500 and str(missing) in body["error"], body
    assert not missing.exists()


def test_cli_empty_file_is_named_and_left_untouched(tmp_path):
    empty = tmp_path / "empty.db"
    empty.touch()
    body = cli_error(run_cli("context", env=agent_env(f"sqlite:///{empty}", "viewer"), cwd=tmp_path))
    assert body["status"] == 500 and str(empty) in body["error"], body
    assert "not an initialized LexGraph database" in body["error"], body
    assert empty.stat().st_size == 0


@pytest.mark.parametrize("url", [
    None, "", "sqlite://", "sqlite:///:memory:", "sqlite+pysqlite:///:memory:", "sqlite:///",
    "sqlite:///file::memory:?cache=shared&uri=true", "sqlite:///file:shared?mode=memory&uri=true",
])
def test_cli_refuses_every_in_memory_spelling(tmp_path, url):
    body = cli_error(run_cli("context", env=agent_env(url, "viewer"), cwd=tmp_path))
    assert body["status"] == 500 and "in-memory" in body["error"], body
    assert _files(tmp_path) == []


def test_cli_schema_needs_no_database(tmp_path):
    result = run_cli("schema", env=agent_env("sqlite:///not-there.db"), cwd=tmp_path)
    assert "schema" in cli_json(result) and _files(tmp_path) == []


def _server(env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "app.mcp.server"], stdin=subprocess.DEVNULL,
                          capture_output=True, env=env, cwd=cwd, timeout=120)


@pytest.mark.parametrize(("url", "fragment"), [
    (None, "in-memory"),
    ("", "in-memory"),
    ("sqlite:///lexgraph.db", "not found"),
])
def test_mcp_server_refuses_to_start_without_a_usable_database(tmp_path, url, fragment):
    result = _server(agent_env(url), tmp_path)
    stderr = result.stderr.decode("utf-8")
    assert result.returncode != 0 and result.stdout == b"", (result.returncode, stderr)
    assert stderr.startswith("lexgraph MCP server: ") and fragment in stderr, stderr
    assert "LEXGRAPH_DATABASE_URL" in stderr and "Traceback" not in stderr, stderr
    assert _files(tmp_path) == []


def test_mcp_server_refuses_an_uninitialized_file(tmp_path):
    empty = tmp_path / "lexgraph.db"
    empty.touch()
    result = _server(agent_env(f"sqlite:///{empty}"), tmp_path)
    stderr = result.stderr.decode("utf-8")
    assert result.returncode != 0 and "not an initialized LexGraph database" in stderr and str(empty) in stderr, stderr
    assert empty.stat().st_size == 0


def test_mcp_server_refuses_an_unknown_agent_user(tmp_path, workspace_db):
    result = _server(agent_env(f"sqlite:///{workspace_db}", "no-such-user"), tmp_path)
    stderr = result.stderr.decode("utf-8")
    assert result.returncode != 0 and "LEXGRAPH_AGENT_USER_ID" in stderr and "no-such-user" in stderr, stderr


@pytest.mark.parametrize("scoped", [False, True])
def test_mcp_server_with_absolute_url_serves_from_any_directory(tmp_path, workspace_db, matter_with_users, scoped):
    actor = matter_with_users["contributor_id"] if scoped else None
    elsewhere = tmp_path / "client-cwd"
    elsewhere.mkdir()
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp.server"], cwd=str(elsewhere),
                                   env=agent_env(f"sqlite:///{workspace_db}", actor))

    async def run():
        async with Client(params, read_timeout_seconds=60) as session:
            names = {tool.name for tool in (await session.list_tools()).tools}
            return names, await session.call_tool("search", {"query": "anything"})

    names, result = asyncio.run(run())
    assert {"explore", "search", "fetch", "assertion_guide"} <= names
    assert ({"agent_context", "suggest_assertion"} <= names) is scoped
    assert not result.is_error, result
    assert _files(elsewhere) == []
