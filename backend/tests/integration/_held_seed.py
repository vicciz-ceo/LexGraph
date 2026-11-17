"""Hold `python -m app.seed_demo` where a Ctrl-C used to hang it.

The seeder drives the API through Starlette's TestClient, which runs each
request on an event loop that it starts in a new thread (anyio's
``start_blocking_portal``). The main thread waits for that thread to start,
and a KeyboardInterrupt raised there left it joining a thread that never
stops: the seeder, and scripts/demo.sh with it, hung until a second Ctrl-C.
An acceptance run hit that window 3 times in 40 interrupts.

``HOLD_FIRST_REQUEST`` runs a module the way ``python -m`` does, but holds the
start of that thread for the first request for a few seconds and creates
MARKER when it does. A SIGINT sent once ``wait_until_held`` returns lands in
the window every time.

Usage: ``python HOLD_SCRIPT MARKER -m MODULE ARGS...``
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

HOLD_FIRST_REQUEST = """\
import os, runpy, sys, time
import anyio.from_thread

marker, flag, module, *args = sys.argv[1:]
assert flag == "-m", sys.argv
sys.argv = [module, *args]
sys.path[0] = os.getcwd()  # as python -m sets it
start_event_loop = anyio.from_thread.run_eventloop
held = []

def held_start(*args, **kwargs):
    if not held:
        held.append(True)
        open(marker, "w").close()
        time.sleep(5)
    return start_event_loop(*args, **kwargs)

anyio.from_thread.run_eventloop = held_start
runpy.run_module(module, run_name="__main__", alter_sys=True)
"""


def write_hold_script(directory: Path) -> Path:
    script = directory / "hold_first_request.py"
    script.write_text(HOLD_FIRST_REQUEST, encoding="utf-8")
    return script


def wait_until_held(marker: Path, process: subprocess.Popen, timeout: float = 60) -> None:
    """Return once the first request's event loop is held, with the main
    thread waiting for it."""
    deadline = time.monotonic() + timeout
    while not marker.exists():
        if process.poll() is not None:
            pytest.fail(
                f"exited with {process.returncode} before the seed's first request was held (when "
                "the seed itself finished, the hook no longer runs: did "
                "anyio.from_thread.run_eventloop change?)"
            )
        if time.monotonic() > deadline:
            pytest.fail(f"the first request was not held within {timeout}s")
        time.sleep(0.02)
    time.sleep(0.3)  # the main thread has reached its wait by now
