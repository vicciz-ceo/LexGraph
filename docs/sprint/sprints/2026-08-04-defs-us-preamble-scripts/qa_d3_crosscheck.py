"""Q-D3: artifact-only independent, fail-closed cross-check for G7/D-PFP-400."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qa_g7_common import (
    EXPECTED_FILE_COUNT, EXPECTED_ROW_COUNT, INTEGRATION_SHA, SNAPSHOT_ID,
    CertificationError, certification_hash, jsonl_hash, read_json, tuple_key, write_json,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        raise CertificationError(f"cannot read canonical JSONL {path}: {exc}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise CertificationError(message)


def verify_certification_hash(artifact: dict[str, Any], label: str) -> None:
    """Verify the Q-D1/Q-D2/Q-D3 signed schema, excluding only run metadata."""
    _assert(artifact.get("summary_hash") == certification_hash(artifact), f"{label} canonical hash disagreement")


def _candidate_key(record: dict[str, Any]) -> tuple[str, str, int]:
    return (record["jurisdiction"], record["source_file"], record["source_row"])


def validate_qd2_accounting(
    states: dict[str, dict[str, int]], totals: dict[str, int], candidates: list[dict[str, Any]],
) -> None:
    """Validate Q-D2's own row ledger; component overlap is intentionally allowed."""
    keys = [_candidate_key(record) for record in candidates]
    _assert(len(keys) == len(set(keys)), "Q-D2 candidate ledger has duplicate stable rows")
    counted = Counter(record["jurisdiction"] for record in candidates)
    captured = Counter(record["jurisdiction"] for record in candidates if record.get("captured") is True)
    for jurisdiction, state in states.items():
        for field in ("candidate_rows", "already_captured", "uncaptured", "quoted_broad_verb", "unquoted_broad_verb"):
            _assert(field in state and isinstance(state[field], int), f"Q-D2 missing {field} for {jurisdiction}")
        _assert(state["candidate_rows"] == state["already_captured"] + state["uncaptured"], f"Q-D2 partition disagreement for {jurisdiction}")
        _assert(state["candidate_rows"] == counted[jurisdiction], f"Q-D2 ledger count disagreement for {jurisdiction}")
        _assert(state["already_captured"] == captured[jurisdiction], f"Q-D2 captured count disagreement for {jurisdiction}")
        _assert(state["uncaptured"] == state["candidate_rows"] - state["already_captured"], f"Q-D2 uncaptured count disagreement for {jurisdiction}")
    for field in ("candidate_rows", "already_captured", "uncaptured", "quoted_broad_verb", "unquoted_broad_verb"):
        _assert(totals.get(field) == sum(state[field] for state in states.values()), f"Q-D2 per-state sum disagreement for {field}")
    _assert(totals["candidate_rows"] == totals["already_captured"] + totals["uncaptured"], "Q-D2 total candidate partition disagreement")
    # quoted/unquoted components are intentionally not a partition: one row may have both.


def validate_dpfp_artifacts(
    population: list[dict[str, Any]], sample: list[dict[str, Any]], adjudication: list[dict[str, Any]],
    byte_ledger: list[dict[str, Any]], *, expected_sample_count: int,
) -> None:
    """Check D-PFP population/sample/raw-ledger invariants without sampling logic."""
    population_keys = [tuple_key(record) for record in population]
    _assert(len(population_keys) == len(set(population_keys)), "stable population tuple identity is not unique")
    sample_keys = [tuple_key(record) for record in sample]
    _assert(len(sample) == expected_sample_count, "D-PFP sample count is not min(400, population)")
    _assert(len(sample_keys) == len(set(sample_keys)), "sample tuples are not unique")
    _assert(set(sample_keys) <= set(population_keys), "sample contains a non-population tuple")
    for field in ("jurisdiction", "route", "rule_family"):
        _assert({record[field] for record in sample} == {record[field] for record in population}, f"sample lacks non-empty population {field} coverage")
    _assert(len(adjudication) == len(sample), "unreviewed Planner ledger count is not one-to-one with sample")
    sample_by_key = {tuple_key(record): record for record in sample}
    ledger_keys = [tuple_key(record) for record in adjudication]
    _assert(len(ledger_keys) == len(set(ledger_keys)) and set(ledger_keys) == set(sample_by_key), "unreviewed Planner ledger sample identity mismatch")
    for record in adjudication:
        source = sample_by_key[tuple_key(record)]
        _assert({key: record.get(key) for key in source} == source, "unreviewed Planner ledger immutable projection mismatch")
        _assert(record.get("qa_status") == "unreviewed", "Planner evidence must remain unadjudicated")
        _assert(record.get("false_capture") is None and record.get("ambiguous") is None and record.get("adjudicator") is None, "Planner ledger has review data")
    fallback = {tuple_key(record): record for record in population if record["route"] == "fallback"}
    byte_keys = [tuple_key(record) for record in byte_ledger]
    _assert(len(byte_ledger) == min(50, len(fallback)), "byte ledger count is not min(50, fallback population)")
    _assert(len(byte_keys) == len(set(byte_keys)), "byte ledger tuples are not unique")
    _assert(set(byte_keys) <= set(fallback), "byte ledger includes a non-fallback/non-population tuple")
    for record in byte_ledger:
        source = fallback[tuple_key(record)]
        _assert(record.get("source_row_sha256") == source["source_row_sha256"], "byte ledger source-row hash changed")
        _assert(record.get("informational_only") is True, "byte ledger is not explicitly informational")


def crosscheck(out: Path) -> dict[str, Any]:
    d1 = read_json(out / "qd1_summary.json")
    d2 = read_json(out / "qd2_summary.json")
    population = _read_jsonl(out / "dpfp400_population.jsonl")
    sample = _read_jsonl(out / "dpfp400_sample.jsonl")
    adjudication = _read_jsonl(out / "dpfp400_adjudication_ledger.jsonl")
    byte_ledger = _read_jsonl(out / "new_fallback_byte_quality_ledger.jsonl")
    candidates = _read_jsonl(out / "qd2_candidate_ledger.jsonl")
    for label, artifact in (("Q-D1", d1), ("Q-D2", d2)):
        _assert(artifact.get("snapshot_id") == SNAPSHOT_ID, f"{label} snapshot identity disagreement")
        _assert(artifact.get("integration_sha") == INTEGRATION_SHA, f"{label} integration SHA disagreement")
        _assert(artifact.get("files") == EXPECTED_FILE_COUNT, f"{label} file census disagreement")
        _assert(artifact.get("rows") == EXPECTED_ROW_COUNT, f"{label} row census disagreement")
        verify_certification_hash(artifact, label)
    states = d1.get("per_jurisdiction", {})
    totals = d1.get("totals", {})
    _assert(len(states) == EXPECTED_FILE_COUNT, "D1 per-state table does not have 53 jurisdictions")
    for field in ("rows", "before", "after", "new", "new_primary", "new_fallback", "new_definition_tuples"):
        _assert(sum(item.get(field, 0) for item in states.values()) == totals.get(field), f"D1 per-state sum disagreement for {field}")
    for code, item in states.items():
        _assert(item["new"] == item["after"] - item["before"], f"before/after/new partition disagreement for {code}")
        _assert(item["new"] == item["new_primary"] + item["new_fallback"], f"primary/fallback partition disagreement for {code}")
    _assert(states.get("US-GA", {}).get("after", 0) >= 2794, "GA G7 gate failed")
    _assert(totals.get("new_primary", 0) >= 23617, "new_primary G7 gate failed")
    _assert(len(candidates) == d2.get("candidate_ledger_count"), "Q-D2 candidate ledger count disagreement")
    _assert(jsonl_hash(candidates) == d2.get("candidate_ledger_hash"), "Q-D2 candidate ledger hash disagreement")
    validate_qd2_accounting(d2.get("per_jurisdiction", {}), d2.get("totals", {}), candidates)
    dpfp = d1.get("dpfp400", {})
    _assert(jsonl_hash(population) == dpfp.get("population_hash"), "population hash disagreement")
    _assert(len(population) == dpfp.get("population_count"), "population count disagreement")
    _assert(jsonl_hash(sample) == dpfp.get("sample_hash"), "sample hash disagreement")
    _assert(len(adjudication) == dpfp.get("adjudication_ledger_count"), "adjudication ledger count disagreement")
    _assert(jsonl_hash(adjudication) == dpfp.get("adjudication_ledger_hash"), "adjudication ledger hash disagreement")
    _assert(jsonl_hash(byte_ledger) == d1.get("byte_quality", {}).get("ledger_hash"), "byte-quality ledger hash disagreement")
    validate_dpfp_artifacts(population, sample, adjudication, byte_ledger, expected_sample_count=min(400, len(population)))
    result = {
        "schema": "lexgraph.g7.qd3.v2", "snapshot_id": SNAPSHOT_ID, "integration_sha": INTEGRATION_SHA,
        "files": EXPECTED_FILE_COUNT, "rows": EXPECTED_ROW_COUNT,
        "d1_summary_hash": d1["summary_hash"], "d2_summary_hash": d2["summary_hash"],
        "candidate_ledger_hash": d2["candidate_ledger_hash"], "population_hash": dpfp["population_hash"],
        "sample_hash": dpfp["sample_hash"], "planner_ledger_hash": dpfp["adjudication_ledger_hash"],
        "byte_ledger_hash": d1["byte_quality"]["ledger_hash"], "status": "PASS",
    }
    result["summary_hash"] = certification_hash(result)
    verify_certification_hash(result, "Q-D3")
    write_json(out / "qd3_crosscheck.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = crosscheck(args.out)
    print(f"Q-D3 PASS hash={result['summary_hash']}")


if __name__ == "__main__":
    main()
