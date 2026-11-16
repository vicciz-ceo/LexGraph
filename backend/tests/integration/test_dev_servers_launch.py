"""Starting `.claude/launch.json`'s servers as the preview does gives a working app (agent:14, ops:16).

The preview runs `runtimeExecutable runtimeArgs` from the project root with the
configuration's `env` and the assigned port in PORT, and rewrites a `--port` value in
`runtimeArgs` when it moves a server. The real backend keeps port 8000 (autoPort false);
here 8000 is remapped to a free test port in both configurations, so they stay paired.
The backend runs in a scratch project root holding the real script and app, so the
repository's own backend/dev.db is never created or read. LEXGRAPH_TEST_PORTS=first-last
picks the test ports from a range instead of letting the OS choose.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONFIGS = {config["name"]: config for config in
           json.loads((ROOT / ".claude" / "launch.json").read_text(encoding="utf-8"))["configurations"]}
INSTALL = "python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
VITE = ROOT / "frontend" / "node_modules" / ".bin" / "vite"
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))

pytestmark = pytest.mark.skipif(shutil.which("sh") is None, reason="the backend configuration runs sh")


def _free_port(*taken: int) -> int:
    first, _, last = os.environ.get("LEXGRAPH_TEST_PORTS", "").partition("-")
    candidates = range(int(first), int(last or first) + 1) if first else [0] * 5
    for candidate in candidates:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            port = probe.getsockname()[1]
        if port not in taken:
            return port
    pytest.skip("no free TCP port for the dev servers")


def _status(url: str, token: str | None = None) -> int:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with _DIRECT.open(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def _listening(port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _argv(config: dict, port: int) -> list[str]:
    """The configuration's command with its `--port` value moved to `port`, as the preview does."""
    args = list(config["runtimeArgs"])
    if "--port" in args:
        args[args.index("--port") + 1] = str(port)
    return [config["runtimeExecutable"], *args]


class Servers:
    """Start configurations like the preview does; every process group is stopped at teardown."""

    def __init__(self, logs: Path) -> None:
        self.logs, self.started = logs, []

    def start(self, name: str, cwd: Path, port: int, env: dict[str, str] | None = None) -> subprocess.Popen:
        config = CONFIGS[name]
        log = self.logs / f"{name}-{len(self.started)}.log"
        with log.open("w") as out:
            process = subprocess.Popen(
                _argv(config, port), cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
                env={**os.environ, **config.get("env", {}), "PORT": str(port), **(env or {})},
                start_new_session=True)
        process.log = log
        self.started.append(process)
        return process

    def stop_all(self) -> None:
        for process in self.started:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                    process.wait(15)
                    break
                except ProcessLookupError:
                    break
                except subprocess.TimeoutExpired:
                    continue


def _ready(process: subprocess.Popen, url: str, timeout: float = 120.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(f"exited with {process.returncode} before serving {url}:\n{process.log.read_text()}")
        try:
            return _status(url)
        except OSError:
            time.sleep(0.2)
    pytest.fail(f"nothing served {url} within {timeout}s:\n{process.log.read_text()}")


@pytest.fixture
def servers(tmp_path: Path):
    started = Servers(tmp_path)
    yield started
    started.stop_all()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project root with the real dev-backend script and app, and a venv wrapping this interpreter."""
    root = tmp_path / "LexGraph"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "dev-backend.sh", root / "scripts" / "dev-backend.sh")
    (root / "backend" / ".venv" / "bin").mkdir(parents=True)
    (root / "backend" / "app").symlink_to(ROOT / "backend" / "app", target_is_directory=True)
    _wrap(root, "python", "")
    _wrap(root, "uvicorn", " -m uvicorn")
    return root


def _wrap(root: Path, name: str, args: str, before: str = "") -> None:
    wrapper = root / "backend" / ".venv" / "bin" / name
    wrapper.write_text(f'#!/bin/sh\n{before}exec {shlex.quote(sys.executable)}{args} "$@"\n')
    wrapper.chmod(0o755)


def _run_backend(project: Path) -> subprocess.CompletedProcess:
    """Run the backend configuration to completion (for the cases where it must refuse to serve)."""
    port = _free_port()
    return subprocess.run(_argv(CONFIGS["backend"], port), cwd=project, env={**os.environ, "PORT": str(port)},
                          capture_output=True, text=True, timeout=120, check=False)


def test_backend_configuration_seeds_the_demo_workspace_then_serves_it(project, servers):
    port = _free_port()
    backend = servers.start("backend", project, port)
    assert _ready(backend, f"http://127.0.0.1:{port}/healthz") == 200
    database = project / "backend" / "dev.db"
    with closing(sqlite3.connect(database)) as db:
        users = db.execute("select count(*) from users").fetchone()[0]
        assert users > 0 and db.execute("select count(*) from assertions").fetchone()[0] > 0
    assert _status(f"http://127.0.0.1:{port}/api/v1/me", token="no-such-user") == 401
    assert f"sqlite:///{database}" in backend.log.read_text()
    assert sorted(p.name for p in database.parent.iterdir()) == [".venv", "app", "dev.db"]

    os.kill(backend.pid, signal.SIGTERM)  # the launched process itself is the server
    backend.wait(15)
    assert not _listening(port)

    again = servers.start("backend", project, port, env={"PORT": "1"})  # a stray PORT cannot move it
    assert _ready(again, f"http://127.0.0.1:{port}/healthz") == 200
    assert "seeding" not in again.log.read_text()
    with closing(sqlite3.connect(database)) as db:
        assert db.execute("select count(*) from users").fetchone()[0] == users


def test_backend_configuration_refuses_a_database_without_the_schema(project):
    database = project / "backend" / "dev.db"
    database.write_bytes(b"")
    result = _run_backend(project)
    assert result.returncode == 1, result
    assert f"{database} is not an initialized LexGraph database" in result.stderr, result.stderr
    assert database.read_bytes() == b""


def test_backend_configuration_keeps_no_half_seeded_database(project):
    _wrap(project, "python", "", before='case "$*" in *app.seed_demo*) echo partial > dev.db; exit 3;; esac\n')
    result = _run_backend(project)
    assert result.returncode != 0, result
    assert sorted(p.name for p in (project / "backend").iterdir()) == [".venv", "app"]


def test_backend_configuration_explains_a_missing_venv(project):
    shutil.rmtree(project / "backend" / ".venv")
    result = _run_backend(project)
    assert result.returncode == 1, result
    assert f'(cd "{project}/backend" && {INSTALL})' in result.stderr, result.stderr
    assert not (project / "backend" / "dev.db").exists()


@pytest.mark.skipif(not VITE.exists() or shutil.which("npm") is None, reason="frontend dependencies not installed")
def test_frontend_configuration_reaches_the_backend_configuration_through_its_proxy(project, servers):
    backend_port = _free_port()
    frontend_port = _free_port(backend_port)
    backend = servers.start("backend", project, backend_port)
    assert _ready(backend, f"http://127.0.0.1:{backend_port}/healthz") == 200
    target = CONFIGS["frontend"]["env"]["LEXGRAPH_API_PROXY"]
    paired = target.replace(f":{CONFIGS['backend']['port']}", f":{backend_port}")
    assert paired != target
    frontend = servers.start("frontend", ROOT, frontend_port, env={"LEXGRAPH_API_PROXY": paired})
    assert _ready(frontend, f"http://localhost:{frontend_port}/") == 200
    me = f"http://localhost:{frontend_port}/api/v1/me"
    assert _status(me, token="no-such-user") == 401  # answered by the backend, from its database

    os.killpg(backend.pid, signal.SIGTERM)
    backend.wait(15)
    assert _status(me, token="no-such-user") == 500  # a frontend without its backend: the defect
