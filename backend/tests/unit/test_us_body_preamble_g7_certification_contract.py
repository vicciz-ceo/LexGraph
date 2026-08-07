"""Contract checks for permanent G7 / D-PFP-400 certification evidence.

These tests deliberately name the clean-checkout QA surface.  They were
committed RED before the harness exists so a future deletion cannot silently
recreate the scratchpad-only Q-D1/Q-D2/Q-D3 failure.
"""

from __future__ import annotations

import importlib
import json
import sys
from copy import deepcopy
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


def test_certification_hashes_exclude_run_metadata_but_qd3_verifies_schema():
    """Timing may be reported, but never change a Q-D1/Q-D2 certification hash."""
    common = _load("qa_g7_common.py")
    d1 = _load("qa_d1_measure.py")
    d2 = _load("qa_d2_independent_denominator.py")
    d3 = _load("qa_d3_crosscheck.py")
    result = {"schema": "test", "value": 7, "run_metadata": {"elapsed_seconds": 1.0}}
    changed_duration = deepcopy(result)
    changed_duration["run_metadata"]["elapsed_seconds"] = 999.0
    assert common.certification_hash(result) == common.certification_hash(changed_duration)
    assert d1.certification_payload(result) == d2.certification_payload(changed_duration)
    signed = {**result, "summary_hash": common.certification_hash(result)}
    d3.verify_certification_hash(signed, "test artifact")
    signed["run_metadata"] = {"elapsed_seconds": 2.0}
    d3.verify_certification_hash(signed, "test artifact")


def test_qd3_fail_closed_validators_reject_accounting_identity_coverage_and_byte_mutations():
    """Every independent Q-D2/D-PFP artifact family has a direct mutation tripwire."""
    d3 = _load("qa_d3_crosscheck.py")
    population = [{
        "jurisdiction": "US-AA", "source_file": "us_aa_statutes.parquet", "source_row": 1,
        "source_row_id": "A", "term": "Term", "definition_text": "Term means X.",
        "scope": "law-wide", "scope_value": None, "route": "fallback", "rule_family": "r",
        "source_row_sha256": "hash", "section_number": "1", "chapter": None,
    }]
    sample = deepcopy(population)
    unreviewed = [{**population[0], "qa_status": "unreviewed", "false_capture": None,
                   "ambiguous": None, "adjudicator": None,
                   "source_location": {"file": "us_aa_statutes.parquet", "row": 1, "act_id": "A"}}]
    byte = [{key: population[0][key] for key in (
        "jurisdiction", "source_file", "source_row", "source_row_id", "term", "definition_text",
        "scope", "source_row_sha256",
    )} | {"claimed_definition_bytes": 13, "source_location": {"file": "us_aa_statutes.parquet", "row": 1, "act_id": "A"},
          "qa_boundary_status": "unreviewed", "informational_only": True}]
    d3.validate_dpfp_artifacts(population, sample, unreviewed, byte, expected_sample_count=1)
    for mutator in (
        lambda: d3.validate_dpfp_artifacts(population, sample + sample, unreviewed, byte, expected_sample_count=1),
        lambda: d3.validate_dpfp_artifacts(population, sample, [{**unreviewed[0], "route": "primary"}], byte, expected_sample_count=1),
        lambda: d3.validate_dpfp_artifacts(population, sample, unreviewed, [{**byte[0], "informational_only": False}], expected_sample_count=1),
    ):
        with pytest.raises(Exception):
            mutator()
    states = {"US-AA": {"candidate_rows": 1, "already_captured": 1, "uncaptured": 0}}
    candidates = [{"jurisdiction": "US-AA", "source_file": "us_aa_statutes.parquet", "source_row": 1,
                   "source_row_id": "A", "components": ["quoted_broad_verb"], "captured": True}]
    d3.validate_qd2_accounting(states, states["US-AA"], candidates)
    with pytest.raises(Exception):
        d3.validate_qd2_accounting({"US-AA": {"candidate_rows": 1, "already_captured": 0, "uncaptured": 0}}, states["US-AA"], candidates)


def test_g7_qa_finalizer_is_separate_fail_closed_and_never_rewrites_ledger(tmp_path):
    finalizer_path = SCRIPTS / "qa_finalize_adjudication.py"
    assert finalizer_path.is_file()
    finalizer = _load("qa_finalize_adjudication.py")
    sample = [{
        "jurisdiction": "US-AA", "source_file": "us_aa_statutes.parquet", "source_row": 1,
        "source_row_id": "A", "term": "Term", "definition_text": "Term means X.", "scope": "law-wide",
        "scope_value": None, "route": "primary", "rule_family": "r", "source_row_sha256": "hash",
        "section_number": "1", "chapter": None,
    }]
    ledger = [{**sample[0], "qa_status": "reviewed", "false_capture": False, "ambiguous": False,
               "adjudicator": "QA reviewer", "source_location": {"file": "us_aa_statutes.parquet", "row": 1, "act_id": "A"}}]
    sample_path, ledger_path = tmp_path / "sample.jsonl", tmp_path / "ledger.jsonl"
    sample_path.write_text("\n".join(json.dumps(row) for row in sample) + "\n")
    ledger_path.write_text("\n".join(json.dumps(row) for row in ledger) + "\n")
    before = ledger_path.read_bytes()
    verdict = finalizer.finalize(sample_path, ledger_path, tmp_path / "verdict.json")
    assert verdict["status"] == "PASS"
    assert ledger_path.read_bytes() == before
    bad = deepcopy(ledger)
    bad[0]["ambiguous"] = True
    with pytest.raises(Exception):
        finalizer.validate_reviewed_ledger(sample, bad)


def test_g7_source_retrieval_helper_is_a_committed_qa_entrypoint():
    helper = SCRIPTS / "qa_retrieve_source.py"
    assert helper.is_file()
    source = helper.read_text()
    assert "source_row_sha256" in source
    assert "validate_corpus" in source
