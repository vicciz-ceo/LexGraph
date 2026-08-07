"""Fail-closed, QA-owned finalizer for a completed D-PFP-400 review ledger.

This is intentionally separate from Planner evidence generation.  It reads a
QA-edited copy and writes only a separate verdict; it never rewrites a ledger.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_g7_common import (
    INTEGRATION_SHA, SNAPSHOT_ID, CertificationError, certification_hash,
    jsonl_hash, read_json, tuple_key, write_json,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        raise CertificationError(f"cannot read QA JSONL {path}: {exc}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise CertificationError(message)


def validate_reviewed_ledger(sample: list[dict[str, Any]], ledger: list[dict[str, Any]]) -> tuple[int, int]:
    """Require an exact immutable projection plus an explicit QA decision."""
    sample_keys = [tuple_key(record) for record in sample]
    _assert(sample and len(sample_keys) == len(set(sample_keys)), "sample has missing or duplicate tuple identity")
    ledger_keys = [tuple_key(record) for record in ledger]
    _assert(len(ledger) == len(sample), "ledger must contain exactly one row per sample tuple")
    _assert(len(ledger_keys) == len(set(ledger_keys)) and set(ledger_keys) == set(sample_keys), "ledger has extra, missing, or duplicate tuples")
    sample_by_key = {tuple_key(record): record for record in sample}
    false_count = ambiguous_count = 0
    for row in ledger:
        source = sample_by_key[tuple_key(row)]
        _assert({key: row.get(key) for key in source} == source, "ledger tuple/source/rule/route/source hash identity changed")
        _assert(row.get("qa_status") == "reviewed", "ledger row lacks explicit reviewed decision")
        _assert(isinstance(row.get("adjudicator"), str) and row["adjudicator"].strip(), "ledger row lacks a nonempty adjudicator")
        _assert(type(row.get("false_capture")) is bool and type(row.get("ambiguous")) is bool, "false_capture and ambiguous must be booleans")
        false_count += int(row["false_capture"])
        ambiguous_count += int(row["ambiguous"])
    return false_count, ambiguous_count


def validate_qd1_summary(summary_path: Path, sample: list[dict[str, Any]]) -> dict[str, Any]:
    """Bind this QA review to the exact certified D-PFP-400 panel."""
    summary = read_json(summary_path)
    _assert(summary.get("summary_hash") == certification_hash(summary), "Q-D1 summary canonical hash disagreement")
    _assert(summary.get("snapshot_id") == SNAPSHOT_ID, "Q-D1 summary snapshot identity disagreement")
    _assert(summary.get("integration_sha") == INTEGRATION_SHA, "Q-D1 summary integration SHA disagreement")
    dpfp = summary.get("dpfp400")
    _assert(isinstance(dpfp, dict), "Q-D1 summary lacks D-PFP-400 identity")
    population_count, sample_count = dpfp.get("population_count"), dpfp.get("sample_count")
    _assert(type(population_count) is int and population_count > 0, "Q-D1 population count is invalid")
    _assert(type(sample_count) is int and sample_count == min(400, population_count), "Q-D1 sample count is not min(400, population)")
    _assert(sample_count == 400, "pinned D-PFP-400 panel must contain exactly 400 rows")
    _assert(len(sample) == sample_count, "actual sample count disagrees with Q-D1 summary")
    _assert(jsonl_hash(sample) == dpfp.get("sample_hash"), "actual sample hash disagrees with Q-D1 summary")
    return summary


def _write_failure(
    verdict_path: Path, sample_hash: str, ledger_hash: str, sample_count: int, failure: str,
    qd1: dict[str, Any] | None = None,
) -> None:
    dpfp = qd1.get("dpfp400", {}) if isinstance(qd1, dict) else {}
    verdict = {
        "schema": "lexgraph.g7.qa-adjudication.v1", "sample_hash": sample_hash, "ledger_hash": ledger_hash,
        "sample_count": sample_count, "false_capture_count": None, "ambiguous_count": None,
        "one_sided_95_zero_event_upper_bound": None, "status": "FAIL", "failure": failure,
        "qd1_summary_hash": qd1.get("summary_hash") if isinstance(qd1, dict) else None,
        "snapshot_id": qd1.get("snapshot_id") if isinstance(qd1, dict) else None,
        "integration_sha": qd1.get("integration_sha") if isinstance(qd1, dict) else None,
        "population_count": dpfp.get("population_count") if isinstance(dpfp, dict) else None,
    }
    verdict["summary_hash"] = certification_hash(verdict)
    write_json(verdict_path, verdict)


def finalize(sample_path: Path, ledger_path: Path, qd1_summary_path: Path, verdict_path: Path) -> dict[str, Any]:
    """Write a canonical QA verdict and fail nonzero unless both counts are zero."""
    sample = _read_jsonl(sample_path)
    ledger = _read_jsonl(ledger_path)
    sample_hash, ledger_hash = jsonl_hash(sample), jsonl_hash(ledger)
    qd1: dict[str, Any] | None = None
    try:
        qd1 = validate_qd1_summary(qd1_summary_path, sample)
        false_count, ambiguous_count = validate_reviewed_ledger(sample, ledger)
    except CertificationError as exc:
        _write_failure(verdict_path, sample_hash, ledger_hash, len(sample), str(exc), qd1)
        raise
    dpfp = qd1["dpfp400"]
    verdict = {
        "schema": "lexgraph.g7.qa-adjudication.v1", "sample_hash": sample_hash, "ledger_hash": ledger_hash,
        "sample_count": len(sample), "false_capture_count": false_count, "ambiguous_count": ambiguous_count,
        "one_sided_95_zero_event_upper_bound": 1 - 0.05 ** (1 / len(sample)),
        "status": "PASS" if false_count == 0 and ambiguous_count == 0 else "FAIL",
        "qd1_summary_hash": qd1["summary_hash"], "snapshot_id": qd1["snapshot_id"],
        "integration_sha": qd1["integration_sha"], "population_count": dpfp["population_count"],
    }
    verdict["summary_hash"] = certification_hash(verdict)
    write_json(verdict_path, verdict)
    if verdict["status"] != "PASS":
        raise CertificationError(f"QA adjudication FAIL false={false_count} ambiguous={ambiguous_count}")
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--qd1-summary", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path, help="QA-edited copy; it is never rewritten")
    parser.add_argument("--verdict", required=True, type=Path)
    args = parser.parse_args()
    try:
        verdict = finalize(args.sample, args.ledger, args.qd1_summary, args.verdict)
    except CertificationError as exc:
        print(f"QA ADJUDICATION FAIL: {exc}")
        raise SystemExit(1) from exc
    print(f"QA ADJUDICATION PASS sample={verdict['sample_count']} hash={verdict['summary_hash']}")


if __name__ == "__main__":
    main()
