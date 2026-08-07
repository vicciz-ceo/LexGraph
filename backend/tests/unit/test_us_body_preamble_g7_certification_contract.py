"""Contract checks for permanent G7 / D-PFP-400 certification evidence.

These tests deliberately name the clean-checkout QA surface.  They were
committed RED before the harness exists so a future deletion cannot silently
recreate the scratchpad-only Q-D1/Q-D2/Q-D3 failure.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts"


def _load(name: str):
    path = SCRIPTS / name
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(path.stem)


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


def test_g7_harness_rejects_a_missing_or_malformed_corpus(tmp_path):
    common = _load("qa_g7_common.py")
    missing_snapshot = tmp_path / common.SNAPSHOT_ID
    missing_snapshot.mkdir()
    with pytest.raises(common.CertificationError, match="expected 53 statute files"):
        common.validate_corpus(missing_snapshot)


def test_g7_sample_allocation_and_canonical_hash_are_deterministic():
    d1 = _load("qa_d1_measure.py")
    population = [
        {
            "jurisdiction": f"US-X{i % 53:02d}", "source_file": "us_x_statutes.parquet",
            "source_row": i, "term": f"Term {i}", "definition_text": f"Text {i}",
            "scope": "law-wide", "route": "primary" if i % 2 else "fallback",
            "rule_family": "family_a" if i % 3 else "family_b",
        }
        for i in range(450)
    ]
    first, first_allocation = d1._allocate_sample(population)
    second, second_allocation = d1._allocate_sample(list(reversed(population)))
    assert first == second
    assert first_allocation == second_allocation
    assert len(first) == 400


def test_g7_harness_uses_the_real_profile_and_registry_seam():
    """A vendored real statutory row reaches the production profile; no mocks."""
    common = _load("qa_g7_common.py")
    fixture = ROOT / "backend/tests/fixtures/us_statutes/ga_preamble_rows.json"
    rows = {row["act_id"]: row for row in json.loads(fixture.read_text())}
    row = rows["STATE_GA_T7_C8_S7-8-1"]
    captured = common.capture_row(
        jurisdiction="US-GA", source_file="us_ga_statutes.parquet", source_row=0, row=row, after=True
    )
    assert {item.term for item in captured} >= {"Access area", "Access device"}
    assert all(item.rule_family != "none" for item in captured)


def test_qd2_does_not_depend_on_qd1_or_its_result_file():
    source = (SCRIPTS / "qa_d2_independent_denominator.py").read_text()
    assert "qa_d1_measure" not in source
    assert "qd1_summary.json" not in source
