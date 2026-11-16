"""The certification freeze must cover exactly what a certification run measures.

Two certificates pin a commit and declare production frozen after it: the G7 /
D-PFP-400 harness (``qa_g7_common.INTEGRATION_SHA``, sprint
2026-08-04-defs-us-preamble) and the gate-2 certificate (``f267644``, sprint
2026-08-20-defs-boundary-idioms).  Both originally compared ALL of
``backend/app`` with the pinned tree, so a commit that only touched the REST
routers, the MCP server and the agent CLI (83efb55) turned ``main`` red and
fail-closed every certification run although no certification run imports
those modules.

``qa_g7_common`` now declares the measured seam once
(``MEASURED_PRODUCTION_PATHS`` + ``MEASURED_SHARED_SYMBOLS``) and
``measured_production_drift`` is the single comparison both pin tests and
``validate_integration`` use.  A narrower freeze is only sound if the
declaration cannot drift away from the code a run really loads (program ruling
P-R16's failure family), so these tests pin the declaration itself:

1. every ``app`` module a real harness capture imports is frozen;
2. the seam binds only the pinned names from a symbol-pinned shared module;
3. on a throwaway repository, seam / vocabulary / pinned-symbol edits are
   reported as drift while unrelated app edits are not, and a certification
   RUN additionally rejects uncommitted and untracked seam files.
"""

from __future__ import annotations

import ast
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
G7_SCRIPTS = ROOT / "docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts"
GATE2_SCRIPTS = ROOT / "docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts"
FIXTURE = ROOT / "backend/tests/fixtures/us_statutes/ga_preamble_rows.json"

# Runs in a fresh interpreter so the answer is the seam's own import closure,
# not whatever the rest of the test session already imported.
_SEAM_PROBE = """
import json, sys
from pathlib import Path
g7_scripts, gate2_scripts, fixture, act_id, root = sys.argv[1:6]
sys.path[:0] = [g7_scripts, gate2_scripts]
import qa_g7_common as common                      # G7 Q-D1 seam
import qa_d2_independent_denominator               # noqa: F401  G7 Q-D2 shares it
import measure_actual_production_all_rows as gate2  # gate-2 seam
row = {r["act_id"]: r for r in json.load(open(fixture))}[act_id]
assert common.capture_row(jurisdiction="US-GA", source_file="f", source_row=0, row=row, after=True)
common.capture_row(jurisdiction="US-GA", source_file="f", source_row=0, row=row, after=False)
strip_wikilinks, get_profile, *_ = gate2.load_production(Path(root))
profile = get_profile("US-GA")
body, _ = strip_wikilinks(profile.normalize_for_parsing(row["text"]))
assert gate2.capture(profile, body, row["text"], row, current=True)
print(json.dumps(sorted(
    module.__file__ for name, module in sys.modules.items()
    if (name == "app" or name.startswith("app.")) and getattr(module, "__file__", None)
)))
"""


def _common():
    if str(G7_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(G7_SCRIPTS))
    return importlib.import_module("qa_g7_common")


def _loaded_seam_files() -> set[str]:
    out = subprocess.run(
        [sys.executable, "-c", _SEAM_PROBE, str(G7_SCRIPTS), str(GATE2_SCRIPTS), str(FIXTURE),
         "STATE_GA_T7_C8_S7-8-1", str(ROOT)],
        check=True, capture_output=True, text=True,
    ).stdout
    return {Path(item).resolve().relative_to(ROOT).as_posix() for item in json.loads(out)}


def test_freeze_scope_covers_the_live_import_closure_of_both_certification_harnesses():
    """A new import edge out of the seam must fail here, not escape the certificate."""
    common = _common()
    loaded = _loaded_seam_files()
    assert "backend/app/definition_links/us_profile.py" in loaded
    assert "backend/app/definition_links/rules/us_markers_boundary.py" in loaded
    frozen = common.MEASURED_PRODUCTION_PATHS
    unfrozen = sorted(
        path for path in loaded - set(common.MEASURED_SHARED_SYMBOLS)
        if not any(path == entry or path.startswith(entry + "/") for entry in frozen)
    )
    assert unfrozen == [], f"certification imports production files outside the frozen seam: {unfrozen}"
    for path in (*frozen, *common.MEASURED_SHARED_SYMBOLS):
        assert (ROOT / path).exists(), f"frozen path is gone, so its freeze is vacuous: {path}"


def test_seam_binds_only_the_pinned_names_from_a_symbol_pinned_shared_module():
    """A shared module is frozen by symbol, so the seam may use ONLY those symbols."""
    common = _common()
    loaded = _loaded_seam_files()
    for path, names in common.MEASURED_SHARED_SYMBOLS.items():
        assert path in loaded, f"{path} is no longer imported by the seam; drop its symbol pin"
        module = path.removeprefix("backend/").removesuffix(".py").replace("/", ".")
        package, _, leaf = module.rpartition(".")
        bound: set[str] = set()
        for file in sorted(loaded - {path}):
            for node in ast.walk(ast.parse((ROOT / file).read_text())):
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == module:
                    bound |= {alias.name for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == package:
                    bound |= {"<whole module>" for alias in node.names if alias.name == leaf}
                elif isinstance(node, ast.Import):
                    bound |= {"<whole module>" for alias in node.names if alias.name == module}
        assert bound and bound <= set(names), (
            f"the seam binds {sorted(bound)} from {path}, but only {sorted(names)} is pinned"
        )


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=freeze-test", "-c", "user.email=freeze-test@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


_VALIDATION = "class ValidationError(ValueError):\n    pass\n\n\ndef validate_dates(a, b):\n    return a < b\n"


@pytest.fixture
def pinned_repo(tmp_path, monkeypatch):
    """A miniature checkout with the same layout, pinned at its first commit."""
    common = _common()
    files = {
        "backend/app/__init__.py": "",
        "backend/app/definition_links/us_profile.py": "RULE = 1\n",
        "backend/app/definition_links/rules/__init__.py": "",
        "backend/app/services/__init__.py": "",
        "backend/app/services/jurisdiction.py": "CODES = ('IL',)\n",
        "backend/app/services/validation.py": _VALIDATION,
        "backend/app/routers/assertions.py": "ROUTE = 1\n",
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "certified tree")
    base = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "INTEGRATION_SHA", base)

    def commit(name: str, text: str) -> None:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
        _git(tmp_path, "add", "--", name)
        _git(tmp_path, "commit", "-q", "-m", f"edit {name}")

    return common, tmp_path, base, commit


def test_unrelated_app_changes_do_not_move_the_certified_seam(pinned_repo):
    """The 83efb55 shape: routers, a new CLI module, and a non-pinned validator."""
    common, _repo, base, commit = pinned_repo
    commit("backend/app/routers/assertions.py", "ROUTE = 2\n")
    commit("backend/app/agent_cli.py", "CLI = 1\n")
    commit("backend/app/services/validation.py", _VALIDATION.replace("a < b", "a <= b"))
    assert common.measured_production_drift(base) == []
    assert common.measured_production_drift(base, include_worktree=True) == []
    common.validate_integration()


@pytest.mark.parametrize(
    ("name", "text", "expected"),
    [
        ("backend/app/definition_links/us_profile.py", "RULE = 2\n",
         "backend/app/definition_links/us_profile.py"),
        ("backend/app/definition_links/rules/us_new_rule.py", "X = 1\n",
         "backend/app/definition_links/rules/us_new_rule.py"),
        ("backend/app/services/jurisdiction.py", "CODES = ('IL', 'US-DE')\n",
         "backend/app/services/jurisdiction.py"),
        ("backend/app/services/validation.py", _VALIDATION.replace("(ValueError)", "(RuntimeError)"),
         "backend/app/services/validation.py::ValidationError"),
        ("backend/app/services/validation.py", "def validate_dates(a, b):\n    return a < b\n",
         "backend/app/services/validation.py::ValidationError"),
        ("backend/app/services/validation.py", _VALIDATION + "\n\nValidationError = RuntimeError\n",
         "backend/app/services/validation.py::ValidationError"),
        ("backend/app/services/validation.py", _VALIDATION + "\n\nValidationError.code = 422\n",
         "backend/app/services/validation.py::ValidationError"),
    ],
    ids=["extraction-module", "new-rule-module", "jurisdiction-vocabulary", "pinned-symbol-changed",
         "pinned-symbol-removed", "pinned-symbol-rebound", "pinned-symbol-mutated"],
)
def test_committed_seam_changes_are_reported_and_fail_certification_closed(pinned_repo, name, text, expected):
    common, _repo, base, commit = pinned_repo
    commit(name, text)
    assert common.measured_production_drift(base) == [expected]
    with pytest.raises(common.CertificationError, match="measured production changed"):
        common.validate_integration()


def test_a_certification_run_rejects_uncommitted_and_untracked_seam_files(pinned_repo):
    """HEAD is clean, but a run imports the working tree -- and ``rules/``
    auto-imports every module it finds, tracked or not."""
    common, repo, base, _commit = pinned_repo
    (repo / "backend/app/definition_links/us_profile.py").write_text("RULE = 3\n")
    (repo / "backend/app/definition_links/rules/zz_untracked_rule.py").write_text("X = 1\n")
    (repo / "backend/app/routers/assertions.py").write_text("ROUTE = 9\n")
    assert common.measured_production_drift(base) == []
    assert common.measured_production_drift(base, include_worktree=True) == [
        "backend/app/definition_links/rules/zz_untracked_rule.py",
        "backend/app/definition_links/us_profile.py",
    ]
    with pytest.raises(common.CertificationError, match="zz_untracked_rule.py"):
        common.validate_integration()


def test_a_deleted_shared_module_is_reported_as_drift_not_a_crash(pinned_repo):
    common, repo, base, _commit = pinned_repo
    (repo / "backend/app/services/validation.py").unlink()
    pinned_symbol = "backend/app/services/validation.py::ValidationError"
    assert common.measured_production_drift(base) == []  # HEAD still has the file
    assert common.measured_production_drift(base, include_worktree=True) == [pinned_symbol]
    _git(repo, "commit", "-q", "-am", "delete the shared module")
    assert common.measured_production_drift(base) == [pinned_symbol]
