"""``scripts/demo.sh``: ports, start-up failures, shutdown, and its setup guards.

Before (findings ops:7, ops:8): the script hard-coded ports 8000/5173. When
uvicorn could not bind it exited and the script carried on, Vite moved to the
next free port, and ``/api`` was proxied to whatever owned 8000 (another
checkout's backend and database). SIGTERM stopped bash and uvicorn but left
``npm run dev`` -> ``vite`` listening. Setup was skipped whenever
``backend/.venv``, ``backend/dev.db`` or ``frontend/node_modules`` merely
existed: a ``dev.db`` created by ``app.bootstrap`` (the README's own
provisioning step) was served as if it were the demo, so every demo sign-in
failed, and an interrupted first install was never completed.

These tests run the real script in a scratch copy of the repository layout
with the real backend (uvicorn, the seeder, the migration runner, through
this interpreter). Only npm and the Vite dev server are stand-ins, so the
suite needs no Node.js install: the stand-in Vite records its arguments,
serves its port like ``vite --strictPort`` and forwards other paths to
``LEXGRAPH_API_PROXY`` the way the dev server proxies ``/api``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

import pytest

from app.seed_demo import DEMO_USERS

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT = BACKEND_DIR.parent
DEMO_SH = ROOT / "scripts" / "demo.sh"
BANNER = "The LexGraph demo is running."

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or os.name != "posix", reason="demo.sh is a bash script"
)

FAKE_VITE = f"""#!{sys.executable}
import http.server, json, os, sys, urllib.error, urllib.request
args = sys.argv[1:]
port = int(args[args.index("--port") + 1])
with open(os.path.join(os.environ["DEMO_TEST_RECORD"], "vite.json"), "w") as f:
    json.dump({{"argv": args, "proxy": os.environ.get("LEXGRAPH_API_PROXY"),
               "pid": os.getpid(), "cwd": os.getcwd()}}, f)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({{}}))
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            status, body = 200, b"<!doctype html><title>LexGraph</title>"
        else:
            try:
                with opener.open(os.environ["LEXGRAPH_API_PROXY"] + self.path, timeout=10) as r:
                    status, body = r.status, r.read()
            except urllib.error.HTTPError as e:
                status, body = e.code, e.read()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
try:
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
except OSError:
    sys.exit(f"error when starting dev server: Port {{port}} is already in use")
print(f"  VITE stand-in ready: http://localhost:{{port}}/", flush=True)
server.serve_forever()
"""

# `npm --prefix frontend ls --all` passes for a completed install; `ci` (and
# `install`) installs; `run dev -- ARGS` starts the dev server like npm does.
FAKE_NPM = """#!/bin/sh
echo "npm $*" >> "$DEMO_TEST_RECORD/calls.log"
prefix=.
if [ "$1" = "--prefix" ]; then prefix=$2; shift 2; fi
case "$1" in
  ls) [ -f "$prefix/node_modules/.package-lock.json" ] ;;
  ci|install) rm -rf "$prefix/node_modules" && mkdir -p "$prefix/node_modules/.bin" &&
      cp "$DEMO_TEST_FAKE_VITE" "$prefix/node_modules/.bin/vite" &&
      chmod +x "$prefix/node_modules/.bin/vite" && echo '{}' > "$prefix/node_modules/.package-lock.json" ;;
  run) shift 2; if [ "$1" = "--" ]; then shift; fi; cd "$prefix" && exec ./node_modules/.bin/vite "$@" ;;
  *) echo "fake npm: unexpected arguments: $*" >&2; exit 2 ;;
esac
"""

# A venv whose interpreter only sees site-packages once `pip install` has run.
VENV_PYTHON = f"""#!/bin/sh
venv=$(cd "$(dirname "$0")/.." && pwd)
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
  echo "pip $*" >> "$DEMO_TEST_RECORD/calls.log"
  if [ "$3" = "install" ]; then touch "$venv/installed"; fi
  exit 0
fi
if [ -f "$venv/installed" ]; then exec "{sys.executable}" "$@"; fi
exec "{sys.executable}" -S "$@"
"""

VENV_UVICORN = f"""#!/bin/sh
exec "{sys.executable}" -m uvicorn "$@"
"""

# `python3 -m venv DIR` creates the stand-in venv above (without dependencies).
FAKE_PYTHON3 = f"""#!/bin/sh
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  echo "python3 $*" >> "$DEMO_TEST_RECORD/calls.log"
  mkdir -p "$3/bin" && cp "$DEMO_TEST_VENV_PYTHON" "$3/bin/python" && cp "$DEMO_TEST_VENV_UVICORN" "$3/bin/uvicorn"
  chmod +x "$3/bin/python" "$3/bin/uvicorn"
  exit 0
fi
exec "{sys.executable}" "$@"
"""


def _write_exec(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)
    return path


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _listening(port: int) -> bool:
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family) as conn:
                conn.settimeout(0.5)
                conn.connect((host, port))
                return True
        except OSError:
            continue
    return False


def _get(url: str) -> tuple[int, bytes]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        with error:  # it holds the response open (ops-docs:1)
            return error.code, error.read()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _user_ids(db: Path) -> set[str]:
    # A connection's own `with` only commits; closing() closes it (ops-docs:1).
    with closing(sqlite3.connect(db)) as conn:
        return {row[0] for row in conn.execute("SELECT id FROM users")}


class Demo:
    """A scratch repository layout around a copy of the real scripts/demo.sh."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path / "repo"
        self.record = tmp_path / "record"
        self.record.mkdir()
        fake = tmp_path / "fake"
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(DEMO_SH, self.root / "scripts" / "demo.sh")
        backend = self.root / "backend"
        backend.mkdir()
        (backend / "app").symlink_to(BACKEND_DIR / "app", target_is_directory=True)
        shutil.copy2(BACKEND_DIR / "pyproject.toml", backend / "pyproject.toml")
        frontend = self.root / "frontend"
        frontend.mkdir()
        for name in ("package.json", "package-lock.json"):
            shutil.copy2(ROOT / "frontend" / name, frontend / name)
        self.venv_python = _write_exec(fake / "venv-python", VENV_PYTHON)
        self.venv_uvicorn = _write_exec(fake / "venv-uvicorn", VENV_UVICORN)
        self.fake_vite = _write_exec(fake / "vite", FAKE_VITE)
        self.bin = fake / "bin"
        _write_exec(self.bin / "npm", FAKE_NPM)
        _write_exec(self.bin / "python3", FAKE_PYTHON3)
        self.backend_port = _free_port()
        self.frontend_port = _free_port()
        self.db = backend / "dev.db"
        self.output: list[str] = []
        self.process: subprocess.Popen[str] | None = None
        self._reader: threading.Thread | None = None

    # --- layout states ------------------------------------------------------
    def install_backend(self, *, dependencies: bool = True) -> None:
        venv = self.root / "backend" / ".venv"
        (venv / "bin").mkdir(parents=True)
        shutil.copy2(self.venv_python, venv / "bin" / "python")
        shutil.copy2(self.venv_uvicorn, venv / "bin" / "uvicorn")
        if dependencies:
            (venv / "installed").touch()

    def install_frontend(self, *, completed: bool = True) -> None:
        bin_dir = self.root / "frontend" / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        shutil.copy2(self.fake_vite, bin_dir / "vite")
        if completed:
            (bin_dir.parent / ".package-lock.json").write_text("{}")

    def calls(self) -> list[str]:
        log = self.record / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def vite(self) -> dict | None:
        record = self.record / "vite.json"
        return json.loads(record.read_text()) if record.exists() else None

    # --- running ------------------------------------------------------------
    def env(self, **overrides: str) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("LEXGRAPH_")}
        env.update(
            PATH=f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            BACKEND_PORT=str(self.backend_port),
            FRONTEND_PORT=str(self.frontend_port),
            LEXGRAPH_FRONTEND_DIST="",  # API only: the stand-in Vite serves the page
            DEMO_TEST_RECORD=str(self.record),
            DEMO_TEST_FAKE_VITE=str(self.fake_vite),
            DEMO_TEST_VENV_PYTHON=str(self.venv_python),
            DEMO_TEST_VENV_UVICORN=str(self.venv_uvicorn),
        )
        env.pop("DEMO_DB", None)
        env.update(overrides)
        return env

    def run(self, **env: str) -> subprocess.CompletedProcess[str]:
        """Run to completion: for cases where the script must stop by itself.

        In its own session, so that a script which hangs instead (and may have
        started servers) is killed with everything it started.
        """
        process = subprocess.Popen(
            ["bash", str(self.root / "scripts" / "demo.sh")], cwd=self.root, env=self.env(**env),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            pytest.fail(f"demo.sh did not stop by itself:\n{stdout}\n{stderr}")
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

    def start(self, **env: str) -> None:
        self.process = subprocess.Popen(
            ["bash", str(self.root / "scripts" / "demo.sh")], cwd=self.root, env=self.env(**env),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
        )
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for line in self.process.stdout:
            self.output.append(line)

    def text(self) -> str:
        return "".join(self.output)

    def wait_until_running(self, timeout: float = 90) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if BANNER in self.text():
                return
            assert self.process is not None
            if self.process.poll() is not None:
                time.sleep(0.2)
                pytest.fail(f"demo.sh exited with {self.process.returncode}:\n{self.text()}")
            time.sleep(0.1)
        pytest.fail(f"demo.sh did not come up within {timeout}s:\n{self.text()}")

    def wait_for_exit(self, timeout: float = 30) -> int:
        assert self.process is not None
        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"demo.sh did not stop within {timeout}s:\n{self.text()}")

    def kill(self) -> None:
        """Kill whatever is left of the script's session, even after the script itself exited."""
        if self.process is None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=10)
        if self._reader is not None:
            self._reader.join(timeout=10)  # EOF once no process of the session holds the pipe
        if self.process.stdout is not None and not (self._reader and self._reader.is_alive()):
            self.process.stdout.close()  # else an unclosed-file ResourceWarning (ops-docs:1)

    def assert_ports_free(self) -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and (
            _listening(self.backend_port) or _listening(self.frontend_port)
        ):
            time.sleep(0.1)
        assert not _listening(self.backend_port), "the backend is still listening"
        assert not _listening(self.frontend_port), "the web app is still listening"


@pytest.fixture
def demo(tmp_path):
    instance = Demo(tmp_path)
    yield instance
    instance.kill()


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory) -> bytes:
    """A demo workspace from the real seeder, made once for the module."""
    db = tmp_path_factory.mktemp("seeded") / "dev.db"
    seeded = subprocess.run([sys.executable, "-m", "app.seed_demo", "--db", str(db)], cwd=BACKEND_DIR,
                            capture_output=True, text=True, timeout=120)
    assert seeded.returncode == 0, seeded.stdout + seeded.stderr
    return db.read_bytes()


def test_first_run_seeds_the_demo_and_serves_it_on_the_configured_ports(demo):
    demo.install_backend()
    demo.install_frontend()

    demo.start()
    demo.wait_until_running()

    assert "Seeding the demo workspace into backend/dev.db" in demo.text()
    assert {user[0] for user in DEMO_USERS} <= _user_ids(demo.db)
    assert not (demo.root / "backend" / ".dev.db.seeding").exists()
    assert _get(f"http://127.0.0.1:{demo.backend_port}/healthz")[0] == 200
    vite = demo.vite()
    assert vite is not None
    assert vite["argv"][:3] == ["--port", str(demo.frontend_port), "--strictPort"]
    assert Path(vite["cwd"]).name == "frontend"
    # The web app forwards to this demo's own backend, not to whatever owns :8000.
    assert vite["proxy"] == f"http://127.0.0.1:{demo.backend_port}"
    status, body = _get(f"http://127.0.0.1:{demo.frontend_port}/healthz")
    assert (status, json.loads(body)) == (200, {"status": "ok"})
    assert f"http://localhost:{demo.frontend_port}" in demo.text()

    assert demo.process is not None
    demo.process.send_signal(signal.SIGTERM)  # the script's pid only, as `kill <pid>` does

    assert demo.wait_for_exit() == 143
    demo.assert_ports_free()
    assert "Stopping the demo servers" in demo.text()


def test_ctrl_c_stops_both_servers_and_an_existing_demo_is_upgraded_not_reseeded(demo, seeded_db):
    demo.install_backend()
    demo.install_frontend()
    demo.db.write_bytes(seeded_db)

    demo.start()
    demo.wait_until_running()

    assert "Upgrading the existing demo workspace in backend/dev.db" in demo.text()
    assert "Seeding" not in demo.text()
    assert demo.calls() == ["npm --prefix frontend ls --all"]  # nothing reinstalled
    assert demo.process is not None
    os.killpg(demo.process.pid, signal.SIGINT)  # Ctrl-C reaches the terminal's whole process group

    assert demo.wait_for_exit() == 130
    demo.assert_ports_free()


@pytest.mark.parametrize("taken", ["backend", "frontend"])
def test_a_port_in_use_stops_the_demo_before_anything_starts(demo, taken):
    demo.install_backend()
    demo.install_frontend()
    port = demo.backend_port if taken == "backend" else demo.frontend_port
    with socket.socket() as squatter:
        squatter.bind(("127.0.0.1", port))
        squatter.listen()

        result = demo.run()

    assert result.returncode == 1
    assert f"port {port} is already in use" in result.stderr
    setting = "BACKEND_PORT" if taken == "backend" else "FRONTEND_PORT"
    assert f"{setting}=" in result.stderr
    assert demo.vite() is None
    assert not demo.db.exists()
    assert not _listening(demo.backend_port if taken == "frontend" else demo.frontend_port)


def test_a_workspace_that_is_not_the_demo_is_refused_and_left_untouched(demo):
    demo.install_backend()
    demo.install_frontend()
    bootstrapped = subprocess.run([sys.executable, "-m", "app.bootstrap", "--db", str(demo.db)],
                                  cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120)
    assert bootstrapped.returncode == 0, bootstrapped.stderr
    before = _sha256(demo.db)

    result = demo.run()

    assert result.returncode == 1
    assert "backend/dev.db is a LexGraph workspace but not the demo one" in result.stderr
    assert "DEMO_DB=backend/demo.db ./scripts/demo.sh" in result.stderr
    assert _sha256(demo.db) == before
    assert demo.vite() is None
    assert not _listening(demo.backend_port)


def test_a_file_that_is_not_a_database_is_refused_and_left_untouched(demo):
    demo.install_backend()
    demo.install_frontend()
    demo.db.write_text("not a database\n")

    result = demo.run()

    assert result.returncode == 1
    assert "backend/dev.db is not a LexGraph database" in result.stderr
    assert demo.db.read_text() == "not a database\n"
    assert demo.vite() is None


def test_demo_db_runs_the_demo_on_another_file(demo, seeded_db):
    demo.install_backend()
    demo.install_frontend()
    demo.db.write_bytes(b"")  # an empty dev.db must be left alone when DEMO_DB points elsewhere
    other = demo.root / "backend" / "demo.db"

    demo.start(DEMO_DB="backend/demo.db")
    demo.wait_until_running()

    assert {user[0] for user in DEMO_USERS} <= _user_ids(other)
    assert demo.db.read_bytes() == b""
    assert demo.process is not None
    demo.process.send_signal(signal.SIGTERM)
    assert demo.wait_for_exit() == 143


@pytest.mark.parametrize("venv_state", ["dependencies-missing", "no-interpreter"])
def test_an_interrupted_first_run_is_completed_by_the_next_one(demo, venv_state):
    venv = demo.root / "backend" / ".venv"
    if venv_state == "dependencies-missing":  # `pip install` was interrupted
        demo.install_backend(dependencies=False)
    else:  # `python3 -m venv` was interrupted
        (venv / "lib").mkdir(parents=True)
    demo.install_frontend(completed=False)  # `npm ci` was interrupted
    demo.db.write_bytes(b"")  # an empty file holds no data
    leftover = demo.root / "backend" / ".dev.db.seeding"
    leftover.mkdir()
    (leftover / "dev.db").write_bytes(b"half a seed")  # the seed was killed

    demo.start()
    demo.wait_until_running()

    calls = demo.calls()
    assert "pip -m pip install -e .[dev]" in calls
    assert ("python3 -m venv backend/.venv" in calls) == (venv_state == "no-interpreter")
    assert "npm --prefix frontend ci" in calls
    assert "backend/dev.db is an empty file" in demo.text()
    assert {user[0] for user in DEMO_USERS} <= _user_ids(demo.db)
    assert not leftover.exists()
    assert demo.process is not None
    demo.process.send_signal(signal.SIGTERM)
    assert demo.wait_for_exit() == 143
    demo.assert_ports_free()


def test_a_server_that_stops_takes_the_other_one_down(demo, seeded_db):
    demo.install_backend()
    demo.install_frontend()
    demo.db.write_bytes(seeded_db)
    demo.start()
    demo.wait_until_running()
    vite = demo.vite()
    assert vite is not None

    os.kill(vite["pid"], signal.SIGKILL)

    assert demo.wait_for_exit() == 1
    assert "the web app stopped unexpectedly" in demo.text()
    demo.assert_ports_free()


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"BACKEND_PORT": "eighty"}, "BACKEND_PORT must be a port number (1-65535), not 'eighty'"),
        ({"FRONTEND_PORT": "70000"}, "FRONTEND_PORT must be a port number (1-65535), not '70000'"),
        ({"FRONTEND_PORT": "same"}, "BACKEND_PORT and FRONTEND_PORT must differ"),
        ({"DEMO_DB": "nowhere/demo.db"}, "the directory for DEMO_DB does not exist"),
    ],
    ids=["non-numeric-port", "port-out-of-range", "same-ports", "missing-db-directory"],
)
def test_invalid_settings_are_rejected_before_any_setup(demo, settings, message):
    if settings.get("FRONTEND_PORT") == "same":
        settings = {"FRONTEND_PORT": str(demo.backend_port)}

    result = demo.run(**settings)

    assert result.returncode == 1
    assert message in result.stderr
    assert not any(call.startswith(("pip", "python3", "npm --prefix frontend ci")) for call in demo.calls())
