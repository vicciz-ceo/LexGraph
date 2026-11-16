"""``scripts/contract_lint.sh`` must reach the same verdict under every awk.

CI's required ``sprint contract lint`` job runs the script with the runner's
awk, which is gawk. The ``Completed entry <= 3 lines`` check handed its entry
regexes to awk through ``-v``, and gawk applies C string-escape processing to
``-v`` values: it rewrote ``\\*\\*`` to ``**`` (printing ``warning: escape
sequence `\\*' treated as plain `*'``), so the ``- **A1** ...`` bullet rule
matched nothing and no bullet-style Completed entry was ever measured. mawk
keeps the backslash, so the same contract passed on CI and failed elsewhere;
seven contracts carried a ``lint: PASS`` stamp the check had not earned
(finding ops:0).

These tests run the real script under each awk installed here, on small
contracts written for the purpose and on every contract CI lints.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LINT = ROOT / "scripts" / "contract_lint.sh"
CONTRACTS = ROOT / "docs" / "sprint" / "sprints"


def _awk_implementations() -> list[tuple[str, str]]:
    """(name, path) for each distinct awk on PATH: the default one, gawk, mawk, BWK awk."""
    found: dict[str, tuple[str, str]] = {}
    for name in ("awk", "gawk", "mawk", "original-awk", "nawk"):
        path = shutil.which(name)
        if path:
            real = os.path.realpath(path)
            found.setdefault(real, (os.path.basename(real), path))
    return sorted(found.values())


AWKS = _awk_implementations()
pytestmark = pytest.mark.skipif(not AWKS or not shutil.which("bash"), reason="needs bash and an awk")


@pytest.fixture(params=AWKS, ids=[name for name, _ in AWKS])
def awk_path(request, tmp_path_factory) -> Path:
    """A PATH directory whose ``awk`` is the implementation under test."""
    _name, path = request.param
    bin_dir = tmp_path_factory.mktemp("awk-bin")
    (bin_dir / "awk").symlink_to(path)
    return bin_dir


def _lint(contract: Path, awk_bin: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PATH": f"{awk_bin}{os.pathsep}{os.environ.get('PATH', '')}"}
    return subprocess.run(
        ["bash", str(LINT), "-f", str(contract)],
        capture_output=True, text=True, env=env, timeout=60, check=False,
    )


FRONTMATTER = """---
id: "2026-01-01-example"
status: done
locked_at: null
last_updated: "2026-01-01T00:00:00Z"
total_items: 3
completed_items: 3
dev_complete_items: 0
---

# Sprint: example

## Dev Complete

## Completed

"""


def _contract(tmp_path: Path, completed: str) -> Path:
    path = tmp_path / "contract.md"
    path.write_text(FRONTMATTER + completed + "\n## Context Dump\n\nnothing\n")
    return path


def _completed_verdict(result: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in result.stdout.splitlines() if "Completed entry" in line]
    assert len(lines) == 1, result.stdout
    return lines[0]


LONG_BULLET = "- **A1** Did the thing.\n  QA: verified\n  in three\n  separate lines.\n"
LONG_HEADER = "#### A1 Did the thing\nQA: verified\nin three\nseparate lines.\n"
LONG_CHECKBOX = "- [x] **B1 — Did the thing.**\n  QA: verified\n  in three\n  separate lines.\n"


FIRST_ENTRY_LINE = FRONTMATTER.count("\n") + 1


@pytest.mark.parametrize(
    "completed",
    [LONG_BULLET, LONG_HEADER, LONG_CHECKBOX],
    ids=["bold-label-bullet", "item-header", "checkbox-bullet"],
)
def test_an_entry_longer_than_three_lines_fails_under_every_awk(tmp_path, awk_path, completed):
    result = _lint(_contract(tmp_path, completed), awk_path)

    assert result.stderr == "", "awk must not warn: a warning here means a regex was rewritten"
    assert _completed_verdict(result) == (
        f"FAIL: Completed entry — entries exceeding 3 lines: line {FIRST_ENTRY_LINE} (4 lines)"
    )
    assert result.returncode == 1
    assert result.stdout.splitlines()[-1].startswith("FAIL ")


def test_entries_of_at_most_three_lines_pass_under_every_awk(tmp_path, awk_path):
    completed = (
        "- **A1** Did the thing. QA: verified\n  on two lines.\n"
        "- **A2** Another thing, one line.\n"
        "#### A3 Header entry\nwith one line of detail\n"
        "- [x] **A4 — Checkbox entry.** One line.\n"
    )
    result = _lint(_contract(tmp_path, completed), awk_path)

    assert result.stderr == ""
    assert _completed_verdict(result) == "PASS: Completed entry (all entries <= 3 lines)"
    assert result.returncode == 0


def test_issue_number_labels_start_their_own_entries(tmp_path, awk_path):
    """``- **#22** ...`` is an entry like ``- **FX1** ...``, not a continuation.

    The label class used to be ``[A-Za-z0-9]``, so these one-line entries were
    counted as lines of the preceding entry (2026-08-10-green-the-suite: five
    one-line entries reported as one five-line entry).
    """
    completed = "".join(f"- **{label}** — one line.\n" for label in ("FX1", "#22", "#23 (AL half)", "#24", "#25"))
    result = _lint(_contract(tmp_path, completed), awk_path)

    assert result.stderr == ""
    assert _completed_verdict(result) == "PASS: Completed entry (all entries <= 3 lines)"


def _ci_contracts() -> list[Path]:
    """The files CI's contracts job lints: line 1 is ``---`` and the frontmatter has ``status:``."""
    selected = []
    for path in sorted(CONTRACTS.glob("*.md")):
        lines = path.read_text().splitlines()
        if not lines or lines[0].strip() != "---":
            continue
        frontmatter = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            frontmatter.append(line)
        if any(line.startswith("status:") for line in frontmatter):
            selected.append(path)
    return selected


def _verdicts(output: str) -> list[str]:
    # The summary line ends with the current time; everything else must match exactly.
    return [re.sub(r" \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", "", line) for line in output.splitlines()]


@pytest.mark.skipif(len(AWKS) < 2, reason="needs two awk implementations to compare")
def test_every_ci_contract_gets_the_same_verdict_under_every_awk(tmp_path):
    contracts = _ci_contracts()
    assert len(contracts) >= 20, "the contract selection no longer matches CI's"
    bins = {}
    for name, path in AWKS:
        bin_dir = tmp_path / name
        bin_dir.mkdir()
        (bin_dir / "awk").symlink_to(path)
        bins[name] = bin_dir
    for contract in contracts:
        results = {name: _lint(contract, bin_dir) for name, bin_dir in bins.items()}
        for name, result in results.items():
            assert result.stderr == "", f"{name} warned on {contract.name}: {result.stderr}"
        outputs = {name: (_verdicts(r.stdout), r.returncode) for name, r in results.items()}
        assert len({repr(o) for o in outputs.values()}) == 1, f"{contract.name}: {outputs}"
