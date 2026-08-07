"""Q-D3: artifact-only independent, fail-closed cross-check for G7/D-PFP-400."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_g7_common import (
    EXPECTED_FILE_COUNT, EXPECTED_ROW_COUNT, INTEGRATION_SHA, SNAPSHOT_ID,
    CertificationError, canonical_bytes, jsonl_hash, read_json, sha256_value, tuple_key, write_json,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        raise CertificationError(f"cannot read canonical JSONL {path}: {exc}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise CertificationError(message)


def crosscheck(out: Path) -> dict[str, Any]:
    d1 = read_json(out / "qd1_summary.json")
    d2 = read_json(out / "qd2_summary.json")
    population = _read_jsonl(out / "dpfp400_population.jsonl")
    sample = _read_jsonl(out / "dpfp400_sample.jsonl")
    ledger = _read_jsonl(out / "new_fallback_byte_quality_ledger.jsonl")
    for artifact in (d1, d2):
        _assert(artifact.get("snapshot_id") == SNAPSHOT_ID, "snapshot identity disagreement")
        _assert(artifact.get("integration_sha") == INTEGRATION_SHA, "integration SHA disagreement")
        _assert(artifact.get("files") == EXPECTED_FILE_COUNT, "file census disagreement")
        _assert(artifact.get("rows") == EXPECTED_ROW_COUNT, "row census disagreement")
        saved = artifact.get("summary_hash")
        unsigned = dict(artifact)
        unsigned.pop("summary_hash", None)
        _assert(saved == sha256_value(unsigned), "summary canonical hash disagreement")
    states = d1.get("per_jurisdiction", {})
    totals = d1.get("totals", {})
    _assert(len(states) == EXPECTED_FILE_COUNT, "D1 per-state table does not have 53 jurisdictions")
    for field in ("rows", "before", "after", "new", "new_primary", "new_fallback"):
        _assert(sum(item.get(field, 0) for item in states.values()) == totals.get(field), f"per-state sum disagreement for {field}")
    for code, item in states.items():
        _assert(item["new"] == item["after"] - item["before"], f"before/after/new partition disagreement for {code}")
        _assert(item["new"] == item["new_primary"] + item["new_fallback"], f"primary/fallback partition disagreement for {code}")
    _assert(states.get("US-GA", {}).get("after", 0) >= 2794, "GA G7 gate failed")
    _assert(totals.get("new_primary", 0) >= 23617, "new_primary G7 gate failed")
    keys = [tuple_key(record) for record in population]
    _assert(len(keys) == len(set(keys)), "stable population tuple identity is not unique")
    _assert(jsonl_hash(population) == d1["dpfp400"]["population_hash"], "population hash disagreement")
    _assert(len(population) == d1["dpfp400"]["population_count"], "population count disagreement")
    _assert(jsonl_hash(sample) == d1["dpfp400"]["sample_hash"], "sample hash disagreement")
    _assert(len(sample) == d1["dpfp400"]["sample_count"], "sample count disagreement")
    _assert(set(tuple_key(record) for record in sample) <= set(keys), "sample contains a non-population tuple")
    _assert(len({tuple_key(record) for record in sample}) == len(sample), "sample tuples are not unique")
    _assert(jsonl_hash(ledger) == d1["byte_quality"]["ledger_hash"], "byte-quality ledger hash disagreement")
    _assert(all(item.get("informational_only") is True for item in ledger), "byte ledger is not explicitly informational")
    result = {
        "schema": "lexgraph.g7.qd3.v1", "snapshot_id": SNAPSHOT_ID, "integration_sha": INTEGRATION_SHA,
        "files": EXPECTED_FILE_COUNT, "rows": EXPECTED_ROW_COUNT,
        "d1_summary_hash": d1["summary_hash"], "d2_summary_hash": d2["summary_hash"],
        "population_hash": d1["dpfp400"]["population_hash"], "sample_hash": d1["dpfp400"]["sample_hash"],
        "ledger_hash": d1["byte_quality"]["ledger_hash"], "status": "PASS",
    }
    result["summary_hash"] = sha256_value(result)
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
