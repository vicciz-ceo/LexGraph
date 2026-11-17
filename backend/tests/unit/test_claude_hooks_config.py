"""`.claude/settings.json` hooks reach the agent and warn correctly from any directory.

agent:13 / ops:16. Claude Code runs a command hook with `sh -c` in the session's current
directory, which follows `cd` and worktrees, and passes the event as JSON on stdin. A
SessionStart hook's plain stdout is added to Claude's context. A PostToolUse hook's stdout
is not when it exits 0, so the line-count advisory has to be JSON
`hookSpecificOutput.additionalContext`. These tests run the committed commands that way,
in throwaway git checkouts with an isolated git configuration.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOKS = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
INSTALL = "python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
NOREPLY = "12345+tester@users.noreply.github.com"

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("sh", "git", "jq", "awk")),
    reason="the hook commands need sh, git, jq and awk")


def _command(event: str) -> str:
    (entry,) = HOOKS[event]
    (hook,) = entry["hooks"]
    assert hook["type"] == "command"
    return hook["command"]


@dataclass
class Checkout:
    root: Path
    env: dict[str, str]

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.root), *args], env=self.env, check=True, capture_output=True)

    def write(self, relative: str, lines: int) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"line_{i} = {i}\n" for i in range(lines)), encoding="utf-8")
        return path


@pytest.fixture
def checkout(tmp_path: Path) -> Checkout:
    """A LexGraph-shaped git checkout with a backend venv and a noreply commit address."""
    global_config = tmp_path / "global.gitconfig"
    global_config.touch()
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "CLAUDE_"))}
    env.update(HOME=str(tmp_path), GIT_CONFIG_GLOBAL=str(global_config), GIT_CONFIG_NOSYSTEM="1",
               GIT_CEILING_DIRECTORIES=str(tmp_path))
    root = tmp_path / "LexGraph"
    for directory in ("backend/.venv/bin", "frontend/src", "docs"):
        (root / directory).mkdir(parents=True)
    (root / "backend" / "pyproject.toml").write_text("[project]\nname = 'lexgraph-backend'\n")
    python = root / "backend" / ".venv" / "bin" / "python"
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    repo = Checkout(root, env)
    repo.git("init", "-q")
    repo.git("config", "user.name", "Tester")
    repo.git("config", "user.email", NOREPLY)
    return repo


def _run(event: str, cwd: Path, env: dict[str, str], fields: dict | None = None, raw: str | None = None):
    stdin = raw if raw is not None else json.dumps({"hook_event_name": event, "cwd": str(cwd), **(fields or {})})
    return subprocess.run(["sh", "-c", _command(event)], cwd=cwd, input=stdin, env=env,
                          capture_output=True, text=True, timeout=60, check=False)


def _session_start(cwd: Path, env: dict[str, str]):
    return _run("SessionStart", cwd, env, {"source": "startup"})


# --- SessionStart --------------------------------------------------------------------------

@pytest.mark.parametrize("subdir", ["", "backend", "frontend/src", "docs"])
def test_session_start_is_silent_in_a_ready_checkout_from_any_directory(checkout, subdir):
    result = _session_start(checkout.root / subdir, checkout.env)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("subdir", ["", "backend", "frontend/src"])
def test_session_start_reports_the_missing_venv_of_this_checkout(checkout, subdir):
    (checkout.root / "backend" / ".venv" / "bin" / "python").unlink()
    result = _session_start(checkout.root / subdir, checkout.env)
    assert result.returncode == 0 and result.stderr == ""
    (line,) = result.stdout.splitlines()
    assert line.startswith("WARN: no backend virtualenv") and f"({checkout.root}/backend/.venv)" in line
    assert f'(cd "{checkout.root}/backend" && {INSTALL})' in line, line


def test_session_start_email_warning_names_the_address_and_states_when_a_push_fails(checkout):
    checkout.git("config", "user.email", "dev@example.com")
    result = _session_start(checkout.root / "backend", checkout.env)
    assert result.returncode == 0
    (line,) = result.stdout.splitlines()
    assert "dev@example.com" in line and "noreply" in line and "GH007" in line
    assert "If the GitHub account you push with blocks" in line and "will fail" not in line


@pytest.mark.parametrize("other_repository", [False, True], ids=["plain directory", "other git repository"])
def test_session_start_outside_the_checkout_checks_the_session_project(checkout, tmp_path, other_repository):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if other_repository:
        subprocess.run(["git", "init", "-q", str(elsewhere)], env=checkout.env, check=True)
    env = {**checkout.env, "CLAUDE_PROJECT_DIR": str(checkout.root)}
    assert _session_start(elsewhere, env).stdout == ""
    (checkout.root / "backend" / ".venv" / "bin" / "python").unlink()
    assert f"({checkout.root}/backend/.venv)" in _session_start(elsewhere, env).stdout


# --- PostToolUse ---------------------------------------------------------------------------

def _edited(checkout: Checkout, path: Path, cwd: Path | None = None, tool: str = "Edit", raw: str | None = None):
    fields = {"tool_name": tool, "tool_response": {"filePath": str(path)}}
    if tool == "Edit":
        fields["tool_input"] = {"file_path": str(path), "old_string": "a", "new_string": "b"}
    return _run("PostToolUse", cwd or checkout.root, checkout.env, fields, raw)


def _advice(result) -> str:
    """The text Claude Code adds to Claude's context next to the tool result."""
    assert result.returncode == 0 and result.stderr == "", result
    output = json.loads(result.stdout)
    assert list(output) == ["hookSpecificOutput"]
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    return output["hookSpecificOutput"]["additionalContext"]


def _assert_silent(result) -> None:
    assert (result.returncode, result.stdout, result.stderr) == (0, "", ""), result


@pytest.fixture
def committed(checkout: Checkout) -> Checkout:
    checkout.write("backend/app/long_module.py", 310)
    checkout.write("frontend/src/short.ts", 290)
    checkout.write("docs/notes.md", 400)
    checkout.git("add", "-A")
    checkout.git("commit", "-q", "-m", "baseline")
    return checkout


def test_post_tool_use_advice_reaches_claude_from_any_directory(committed, tmp_path):
    path = committed.write("frontend/src/short.ts", 301)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    for cwd in (committed.root, committed.root / "backend", elsewhere):
        advice = _advice(_edited(committed, path, cwd=cwd))
        assert advice.startswith(f"{path}: 301 lines (290 at HEAD) exceeds"), advice
        assert "300-line" in advice and "do not split or restructure existing code" in advice


def test_post_tool_use_reports_a_new_file_and_growth_of_a_long_one(committed):
    new = committed.write("backend/app/new_module.py", 320)
    assert f"{new}: 320 lines (not in HEAD)" in _advice(_edited(committed, new, tool="Write"))
    grown = committed.write("backend/app/long_module.py", 312)
    assert f"{grown}: 312 lines (310 at HEAD)" in _advice(_edited(committed, grown))


def test_post_tool_use_ignores_unchanged_long_files_and_non_code(committed, tmp_path):
    _assert_silent(_edited(committed, committed.root / "backend/app/long_module.py"))
    _assert_silent(_edited(committed, committed.write("backend/app/long_module.py", 305)))
    _assert_silent(_edited(committed, committed.root / "docs/notes.md"))
    _assert_silent(_edited(committed, committed.write("backend/app/at_limit.py", 300)))
    _assert_silent(_edited(committed, committed.root / "backend/app/missing.py"))
    outside = tmp_path / "scratch" / "probe.py"
    outside.parent.mkdir()
    outside.write_text("x = 1\n" * 400)
    _assert_silent(_edited(committed, outside))


@pytest.mark.parametrize("raw", ["", "not json", "{}", '{"tool_input": {"file_path": null}}'])
def test_post_tool_use_ignores_malformed_events(committed, raw):
    _assert_silent(_edited(committed, committed.root / "frontend/src/short.ts", raw=raw))


def test_post_tool_use_still_matches_edit_and_write():
    assert HOOKS["PostToolUse"][0]["matcher"] == "Edit|Write"
