"""`.claude/launch.json` pairs a backend with a frontend that proxies /api to it (agent:14, ops:16).

Claude Code's preview starts each configuration from the project root with its `env` and
the assigned port in PORT. With `autoPort` true it moves a busy server to a free port and
rewrites a `--port` value in `runtimeArgs`; with false it refuses to start. The frontend's
/api proxy target is fixed, so the backend must keep its port, and the frontend must let
the preview move it without Vite silently picking yet another port.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
LAUNCH = json.loads((ROOT / ".claude" / "launch.json").read_text(encoding="utf-8"))
CONFIGS = {config["name"]: config for config in LAUNCH["configurations"]}


def test_launch_config_defines_one_backend_and_one_frontend():
    names = [config["name"] for config in LAUNCH["configurations"]]
    assert LAUNCH["version"] == "0.0.1"
    assert sorted(names) == ["backend", "frontend"], names


def test_frontend_proxies_api_calls_to_the_backend_configuration():
    backend, frontend = CONFIGS["backend"], CONFIGS["frontend"]
    assert backend["autoPort"] is False, "a moved backend would leave the /api proxy pointing at the old port"
    target = frontend["env"]["LEXGRAPH_API_PROXY"]
    proxy = urlsplit(target)
    assert (proxy.scheme, proxy.hostname, proxy.port, proxy.path) == ("http", "127.0.0.1", backend["port"], "")
    vite = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    default = re.search(r'process\.env\.LEXGRAPH_API_PROXY \?\? "([^"]+)"', vite)
    assert default and default.group(1) == target, "plain `npm run dev` must reach the same backend"


def test_frontend_port_can_be_moved_by_the_preview_but_not_by_vite():
    frontend = CONFIGS["frontend"]
    args = frontend["runtimeArgs"]
    assert [frontend["runtimeExecutable"], *args[:4]] == ["npm", "--prefix", "frontend", "run", "dev"]
    assert args[args.index("--port") + 1] == str(frontend["port"]) and "--strictPort" in args
    assert frontend["autoPort"] is True


def test_backend_configuration_runs_the_dev_backend_script_on_its_own_port():
    backend = CONFIGS["backend"]
    command = [backend["runtimeExecutable"], *backend["runtimeArgs"]]
    assert command == ["sh", "scripts/dev-backend.sh", "--port", str(backend["port"])], command
    assert "cwd" not in backend, "the script is resolved against the project root"


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs sh")
def test_dev_backend_script_is_valid_posix_sh():
    script = ROOT / "scripts" / "dev-backend.sh"
    result = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
