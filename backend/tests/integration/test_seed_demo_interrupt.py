"""One Ctrl-C stops `python -m app.seed_demo` at once (acceptance run, release candidate).

The seeder used to let Python turn SIGINT into a KeyboardInterrupt. When that
landed while Starlette's TestClient was starting the event-loop thread of a
request, the main thread went on to join a thread that never stops, so the
seed (and scripts/demo.sh, which waits for it) hung until a second Ctrl-C.
`tests/integration/_held_seed.py` holds the seeder in that window, so the
interrupt lands there every time instead of now and then.

The seeder now dies of the SIGINT at once, as an uncaught KeyboardInterrupt
would make it, so the shell that started it sees an interrupted command.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration._held_seed import wait_until_held, write_hold_script

BACKEND = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(os.name != "posix", reason="sends SIGINT to a process group")


def test_ctrl_c_while_a_request_starts_stops_the_seed_at_once(tmp_path):
    marker = tmp_path / "held"
    process = subprocess.Popen(
        [sys.executable, str(write_hold_script(tmp_path)), str(marker),
         "-m", "app.seed_demo", "--db", str(tmp_path / "demo.db")],
        cwd=BACKEND, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        wait_until_held(marker, process)
        os.killpg(process.pid, signal.SIGINT)  # Ctrl-C reaches the terminal's whole process group
        try:
            _, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            pytest.fail("the seed was still running 15 s after Ctrl-C")
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()

    assert process.returncode == -signal.SIGINT, (process.returncode, stderr)
