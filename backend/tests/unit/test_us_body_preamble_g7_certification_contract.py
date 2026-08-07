"""Contract checks for permanent G7 / D-PFP-400 certification evidence.

These tests deliberately name the clean-checkout QA surface.  They were
committed RED before the harness exists so a future deletion cannot silently
recreate the scratchpad-only Q-D1/Q-D2/Q-D3 failure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts"


def _load(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_g7_canonical_harness_entrypoints_are_committed():
    """The three independent certification stages must exist in the repo."""
    for name in (
        "qa_d1_measure.py",
        "qa_d2_independent_denominator.py",
        "qa_d3_crosscheck.py",
        "run_g7_certification.py",
    ):
        assert (SCRIPTS / name).is_file(), name


def test_g7_harness_uses_live_production_seam_not_approximate_measure():
    """The acceptance path must never delegate to the non-gating helper."""
    d1 = _load("qa_d1_measure.py")
    assert d1.INTEGRATION_SHA == "4fa9e7b368801757039091646e06a832620a3a2c"
    assert "measure_fp_after_widening" not in (SCRIPTS / "qa_d1_measure.py").read_text()
    assert callable(d1.measure)


def test_g7_harness_declares_fail_closed_snapshot_contract():
    d1 = _load("qa_d1_measure.py")
    assert d1.EXPECTED_FILE_COUNT == 53
    assert d1.EXPECTED_ROW_COUNT == 2_038_247
    assert d1.SNAPSHOT_ID == "301000fc3465374ee0f23c3c6953a8a861e95cad"
