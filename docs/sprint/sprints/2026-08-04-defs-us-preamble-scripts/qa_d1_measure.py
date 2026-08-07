"""Q-D1/G7 binding before/after measurement and D-PFP-400 evidence producer.

Run only with the ratified 53-file snapshot.  This calls the real US profile,
registry and extraction seam; it never imports the approximate widening tool.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from qa_g7_common import (
    EXPECTED_FILE_COUNT, EXPECTED_ROW_COUNT, INTEGRATION_SHA, SNAPSHOT_ID,
    CertificationError, canonical_bytes, capture_row, certification_hash, certification_payload,
    jurisdiction_for, jsonl_hash, sort_records, tuple_key, validate_corpus, validate_integration,
    read_json, write_json, write_jsonl,
)

SAMPLE_SIZE = 400


def _rank(record: dict[str, Any]) -> str:
    seed = f"{SNAPSHOT_ID}\0{INTEGRATION_SHA}\0".encode()
    return hashlib.sha256(seed + canonical_bytes(record)).hexdigest()


def _allocate_sample(population: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deterministic conflict-free coverage plus proportional cell allocation.

    A tuple belongs to one `(jurisdiction, route, rule_family)` cell.  First,
    a greedy SHA-ranked set cover takes the candidate covering the most still-
    uncovered required dimension labels; this guarantees every non-empty
    jurisdiction, live route and rule family.  Remaining seats are assigned
    across cells proportionally (Hamilton largest remainder), taking all
    candidates in a cell when its allocation is larger than its remainder.
    """
    if len(population) <= SAMPLE_SIZE:
        selected = sorted(population, key=_rank)
        return selected, {"mode": "whole_population", "mandatory": len(selected), "cells": {}}
    cells: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    required: set[tuple[str, str]] = set()
    for record in population:
        cell = (record["jurisdiction"], record["route"], record["rule_family"])
        cells[cell].append(record)
        required.update((("jurisdiction", cell[0]), ("route", cell[1]), ("rule_family", cell[2])))
    for records in cells.values():
        records.sort(key=_rank)

    selected_keys: set[tuple[str, str, str, str, str]] = set()
    uncovered = set(required)
    # Greedy cover is deterministic: greatest newly-covered labels, then SHA,
    # then canonical identity.  It is bounded by the dimension universe.
    while uncovered:
        choices = []
        for cell, records in cells.items():
            for record in records:
                key = tuple_key(record)
                if key in selected_keys:
                    continue
                labels = {("jurisdiction", cell[0]), ("route", cell[1]), ("rule_family", cell[2])}
                gain = len(labels & uncovered)
                if gain:
                    choices.append((-gain, _rank(record), key, record, labels))
                break
        if not choices:
            raise CertificationError("cannot cover every non-empty sampling dimension")
        _, _, key, record, labels = min(choices)
        selected_keys.add(key)
        uncovered -= labels
    if len(selected_keys) > SAMPLE_SIZE:
        raise CertificationError("mandatory coverage exceeds the 400-seat D-PFP-400 sample")

    capacity = SAMPLE_SIZE - len(selected_keys)
    remaining = {cell: [r for r in records if tuple_key(r) not in selected_keys] for cell, records in cells.items()}
    allocation: dict[tuple[str, str, str], int] = {cell: 0 for cell in cells}
    # Repeated Hamilton rounds redistribute seats from exhausted (undersized)
    # cells without changing the deterministic order inside any cell.
    while capacity:
        eligible = {cell: rows for cell, rows in remaining.items() if rows}
        if not eligible:
            raise CertificationError("sample capacity remains but population is exhausted")
        total = sum(len(rows) for rows in eligible.values())
        raw = {cell: capacity * len(rows) / total for cell, rows in eligible.items()}
        base = {cell: min(len(eligible[cell]), int(math.floor(raw[cell]))) for cell in eligible}
        granted = sum(base.values())
        for cell, count in base.items():
            allocation[cell] += count
        if granted:
            capacity -= granted
            for cell, count in base.items():
                remaining[cell] = remaining[cell][count:]
            continue
        # At least one seat is due; largest fractional part then cell name is
        # the deterministic Hamilton tie breaker.  One-at-a-time also handles
        # every undersized cell by exhausting it before reallocation.
        cell = min(eligible, key=lambda c: (-(raw[c] - math.floor(raw[c])), c))
        allocation[cell] += 1
        remaining[cell] = remaining[cell][1:]
        capacity -= 1

    selected = [record for record in population if tuple_key(record) in selected_keys]
    for cell, count in allocation.items():
        if count:
            selected.extend(cells[cell][len([r for r in cells[cell] if tuple_key(r) in selected_keys]):][:count])
    # The previous slice is unsafe when mandatory picked a non-prefix cell row;
    # rebuild exactly from ranks with selected keys excluded.
    selected = [record for record in population if tuple_key(record) in selected_keys]
    for cell, count in allocation.items():
        selected.extend([r for r in cells[cell] if tuple_key(r) not in selected_keys][:count])
    selected = sorted({tuple_key(r): r for r in selected}.values(), key=_rank)
    if len(selected) != SAMPLE_SIZE:
        raise CertificationError(f"sample allocation produced {len(selected)}, not {SAMPLE_SIZE}")
    return selected, {
        "mode": "stratified_400", "mandatory": len(selected_keys),
        "cells": {"|".join(cell): allocation[cell] for cell in sorted(cells)},
    }


def _byte_quality_ledger(population: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Separate deterministic informational review list for fallback bytes."""
    fallback = [record for record in population if record["route"] == "fallback"]
    # A compact, reproducible 50-row slice retains bounds, hashes and claimed
    # bytes.  QA judges contamination; this never claims the sibling defect is fixed.
    selected = sorted(fallback, key=_rank)[: min(50, len(fallback))]
    return [{
        "jurisdiction": r["jurisdiction"], "source_file": r["source_file"],
        "source_row": r["source_row"], "source_row_id": r["source_row_id"],
        "term": r["term"], "definition_text": r["definition_text"], "scope": r["scope"],
        "source_row_sha256": r["source_row_sha256"], "claimed_definition_bytes": len(r["definition_text"].encode()),
        "source_location": {"file": r["source_file"], "row": r["source_row"], "act_id": r["source_row_id"]},
        "qa_boundary_status": "unreviewed", "informational_only": True,
    } for r in selected]


def _adjudication_ledger(sample: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A complete, deliberately unadjudicated QA ledger for all sample tuples."""
    return [{
        **record,
        "qa_status": "unreviewed",
        "false_capture": None,
        "ambiguous": None,
        "adjudicator": None,
        "source_location": {"file": record["source_file"], "row": record["source_row"], "act_id": record["source_row_id"]},
    } for record in sample]


def materialize_review_ledger(out: Path) -> dict[str, Any]:
    """Create/update the QA-owned ledger without recomputing corpus evidence."""
    sample = [__import__("json").loads(line) for line in (out / "dpfp400_sample.jsonl").read_text().splitlines() if line]
    ledger = _adjudication_ledger(sample)
    ledger_hash = write_jsonl(out / "dpfp400_adjudication_ledger.jsonl", ledger)
    summary = read_json(out / "qd1_summary.json")
    summary["dpfp400"]["adjudication_ledger_count"] = len(ledger)
    summary["dpfp400"]["adjudication_ledger_hash"] = ledger_hash
    summary["summary_hash"] = certification_hash(summary)
    write_json(out / "qd1_summary.json", summary)
    return summary


def export_compact_evidence(out: Path, evidence: Path) -> None:
    """Emit only reviewable summaries/sample/ledgers, never the full population."""
    materialize_review_ledger(out)
    evidence.mkdir(parents=True, exist_ok=True)
    for name in (
        "qd1_summary.json", "qd2_summary.json", "qd3_crosscheck.json",
        "dpfp400_sample.jsonl", "dpfp400_adjudication_ledger.jsonl",
        "new_fallback_byte_quality_ledger.jsonl",
    ):
        source = out / name
        if not source.is_file():
            raise CertificationError(f"cannot export missing evidence {source}")
        if name.endswith(".jsonl"):
            records = [__import__("json").loads(line) for line in source.read_text().splitlines() if line]
            write_jsonl(evidence / name, records)
        else:
            write_json(evidence / name, read_json(source))


def measure(snapshot: Path, out: Path) -> dict[str, Any]:
    validate_integration()
    files, rows, file_rows = validate_corpus(snapshot)
    started = time.monotonic()
    per_state: dict[str, dict[str, Any]] = {}
    population: list[dict[str, Any]] = []
    for path in files:
        jurisdiction = jurisdiction_for(path)
        before_rows: set[int] = set()
        after_rows: dict[int, str] = {}
        before_tuples: set[tuple[str, str, str, str, str]] = set()
        after_tuples: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        parquet = pq.ParquetFile(path)
        index = 0
        for batch in parquet.iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=2_048
        ):
            for row in batch.to_pylist():
                before = capture_row(jurisdiction=jurisdiction, source_file=path.name, source_row=index, row=row, after=False)
                after = capture_row(jurisdiction=jurisdiction, source_file=path.name, source_row=index, row=row, after=True)
                if before:
                    before_rows.add(index)
                if after:
                    after_rows[index] = after[0].route
                before_tuples.update(tuple_key(item.record()) for item in before)
                for item in after:
                    record = item.record()
                    after_tuples.setdefault(tuple_key(record), record)
                index += 1
        new_rows = set(after_rows) - before_rows
        primary = sum(after_rows[index] == "primary" for index in new_rows)
        fallback = sum(after_rows[index] == "fallback" for index in new_rows)
        new_tuples = [record for key, record in after_tuples.items() if key not in before_tuples]
        population.extend(new_tuples)
        per_state[jurisdiction] = {
            "rows": file_rows[path.name], "before": len(before_rows), "after": len(after_rows),
            "new": len(new_rows), "new_primary": primary, "new_fallback": fallback,
            "new_definition_tuples": len(new_tuples),
        }
    totals = {key: sum(state[key] for state in per_state.values()) for key in ("rows", "before", "after", "new", "new_primary", "new_fallback", "new_definition_tuples")}
    if totals["rows"] != EXPECTED_ROW_COUNT or len(per_state) != EXPECTED_FILE_COUNT:
        raise CertificationError("D1 accounting does not cover the exact corpus census")
    if per_state.get("US-GA", {}).get("after", 0) < 2794:
        raise CertificationError("G7 failed: US-GA after is below 2794")
    if totals["new_primary"] < 23617:
        raise CertificationError("G7 failed: total new_primary is below 23617")
    population = sort_records({tuple_key(record): record for record in population}.values())
    sample, allocation = _allocate_sample(population)
    ledger = _byte_quality_ledger(population)
    adjudication = _adjudication_ledger(sample)
    out.mkdir(parents=True, exist_ok=True)
    population_hash = jsonl_hash(population)
    sample_hash = write_jsonl(out / "dpfp400_sample.jsonl", sample)
    ledger_hash = write_jsonl(out / "new_fallback_byte_quality_ledger.jsonl", ledger)
    adjudication_hash = write_jsonl(out / "dpfp400_adjudication_ledger.jsonl", adjudication)
    write_jsonl(out / "dpfp400_population.jsonl", population)
    result = {
        "schema": "lexgraph.g7.qd1.v1", "snapshot_id": SNAPSHOT_ID, "integration_sha": INTEGRATION_SHA,
        "files": EXPECTED_FILE_COUNT, "rows": rows, "per_jurisdiction": {k: per_state[k] for k in sorted(per_state)},
        "totals": totals, "gates": {"ga_after_min": 2794, "new_primary_min": 23617, "ga_after_pass": per_state["US-GA"]["after"] >= 2794, "new_primary_pass": totals["new_primary"] >= 23617},
        "dpfp400": {"population_count": len(population), "population_hash": population_hash, "sample_count": len(sample), "sample_hash": sample_hash, "adjudication_ledger_count": len(adjudication), "adjudication_ledger_hash": adjudication_hash, "allocation": allocation, "one_sided_95_zero_event_upper_bound": 1 - 0.05 ** (1 / len(sample)), "qa_status": "unreviewed_no_pfp_pass_claim"},
        "byte_quality": {"route": "new_fallback", "ledger_count": len(ledger), "ledger_hash": ledger_hash, "status": "informational_unreviewed"},
        "run_metadata": {"elapsed_seconds": round(time.monotonic() - started, 3)},
    }
    result["summary_hash"] = certification_hash(result)
    write_json(out / "qd1_summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = measure(args.snapshot, args.out)
    print(f"Q-D1 PASS rows={result['rows']} population={result['dpfp400']['population_count']} hash={result['summary_hash']}")


if __name__ == "__main__":
    main()
