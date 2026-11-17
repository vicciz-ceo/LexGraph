"""Helpers for the local agent surface tests: the JSON CLI as a real subprocess
and the MCP server through the official client (what an MCP client receives).
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from mcp import Client

BACKEND = Path(__file__).resolve().parents[2]
_ISOLATED = ("LEXGRAPH_", "PYTHONIOENCODING", "PYTHONUTF8", "PYTHONWARNINGS", "PYTHONCOERCECLOCALE")


def agent_env(database_url: str | None = None, actor: str | None = None, **extra: str) -> dict[str, str]:
    """Environment without inherited LexGraph/encoding overrides; `app` importable from any cwd."""
    env = {key: value for key, value in os.environ.items() if not key.startswith(_ISOLATED)}
    env["PYTHONPATH"] = str(BACKEND)
    if database_url is not None:
        env["LEXGRAPH_DATABASE_URL"] = database_url
    if actor is not None:
        env["LEXGRAPH_AGENT_USER_ID"] = actor
    env.update(extra)
    return env


def run_cli(*args: str, env: dict[str, str], cwd: Path = BACKEND, stdin: bytes | None = None):
    return subprocess.run([sys.executable, "-m", "app.agent_cli", *args], input=stdin,
                          capture_output=True, env=env, cwd=cwd, timeout=120)


def cli_json(result) -> dict:
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return json.loads(result.stdout.decode("utf-8"))


def cli_error(result) -> dict:
    """The CLI error contract: exit 1, empty stdout, stderr is exactly one JSON object."""
    stderr = result.stderr.decode("utf-8")
    assert result.returncode == 1, (result.returncode, stderr)
    assert result.stdout == b"", result.stdout
    body = json.loads(stderr)
    assert isinstance(body["error"], str) and isinstance(body["status"], int), body
    return body


def call_tool(server, name: str, arguments: dict | None = None) -> tuple[bool, str]:
    async def run():
        async with Client(server) as client:
            return await client.call_tool(name, arguments or {})
    result = asyncio.run(run())
    return result.is_error, " ".join(getattr(block, "text", "") for block in result.content)


def tool_json(server, name: str, arguments: dict | None = None) -> dict:
    is_error, text = call_tool(server, name, arguments)
    assert not is_error, text
    return json.loads(text)


def tool_error(server, name: str, arguments: dict | None = None) -> dict:
    """An anticipated MCP failure: is_error plus the SDK prefix and one JSON object."""
    is_error, text = call_tool(server, name, arguments)
    prefix = f"Error executing tool {name}: "
    assert is_error and text.startswith(prefix), text
    body = json.loads(text[len(prefix):])
    assert isinstance(body["error"], str) and isinstance(body["status"], int), body
    return body
