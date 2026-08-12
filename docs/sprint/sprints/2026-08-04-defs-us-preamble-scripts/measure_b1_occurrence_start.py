"""Runtime-only M-R106 measurement for B1 occurrence-start extraction.

The production tree is not edited.  The probe records the same normalized,
first-wins persisted tuples as Q-D1 while monkeypatching only the proposed B1
start metadata flow: extraction begins at B1's first qualifying occurrence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from qa_g7_common import (  # noqa: E402
    EXPECTED_FILE_COUNT,
    EXPECTED_ROW_COUNT,
    SNAPSHOT_ID,
    capture_row,
    jurisdiction_for,
    tuple_key,
    validate_corpus,
    write_json,
    write_jsonl,
)


def _b1_start(body: str) -> int | None:
    """The candidate start B1 would provide through the authorized metadata."""
    from app.definition_links.rules.us_body_preamble_b1 import (
        _B1_DIRECT_QUOTE_MEANS_RE,
        _B1_LOOKAHEAD,
        _B1_TRIGGER_RE,
        _b1_colon_list_branch,
        _b1_quote_means_branch,
    )

    if direct := _B1_DIRECT_QUOTE_MEANS_RE.search(body):
        return direct.start()
    for match in _B1_TRIGGER_RE.finditer(body):
        after = body[match.end() : match.end() + _B1_LOOKAHEAD]
        if _b1_colon_list_branch(after) or _b1_quote_means_branch(after):
            return match.start()
    return None


def _classification(record: dict[str, Any]) -> str:
    """Every expected delta has a source-ownership judgement; unknown fails."""
    row_id = record["source_row_id"]
    if row_id == "STATE_AR_T23_C81_S8_S23-81-810":
        return "downstream_false_capture_ar"
    if row_id == "STATE_ID_T48_C18_S48-1805":
        return "downstream_false_capture_id"
    if row_id in {
        "STATE_TX_Clg_C111_S111.068",
        "STATE_TX_Clg_C111_S111.039",
        "STATE_TX_Clg_C111_S111.008",
        "STATE_TX_Clg_C102_S102.007",
    }:
        return "downstream_false_capture_tx"
    if record["jurisdiction"] == "US-HI":
        return "source_held_hi"
    if record["jurisdiction"] == "US-FED":
        return "source_held_fed"
    return "UNCLASSIFIED"


def measure(snapshot: Path, out: Path) -> dict[str, Any]:
    from app.definition_links.profiles import get_profile
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import USProfile, derive_heading_from_body

    files, rows, _ = validate_corpus(snapshot)
    assert len(files) == EXPECTED_FILE_COUNT and rows == EXPECTED_ROW_COUNT
    starts: dict[str, int] = {}
    original_derive = USProfile.derive_heading_from_body
    original_extract = USProfile.extract_definitions_from_section

    def derive(self, heading: str, body: str) -> str | None:
        result = original_derive(self, heading, body)
        starts.pop(body, None)
        if result is None or derive_heading_from_body(heading, body) is not None:
            return result
        for rule in registry.body_preamble_rules_for(self.code):
            if rule.derive_heading(body) is not None:
                if rule.derive_heading is _b1_trigger_colon_or_quote_means:
                    start = _b1_start(body)
                    if start is None:
                        raise RuntimeError("B1 won without a qualifying start")
                    starts[body] = start
                return result
        raise RuntimeError("body-derived heading has no registered winner")

    def extract(self, text: str, *, scope: str, heading_was_derived: bool = False):
        start = starts.get(text)
        if heading_was_derived and start is not None:
            return original_extract(self, text[start:], scope=scope, heading_was_derived=True)
        return original_extract(self, text, scope=scope, heading_was_derived=heading_was_derived)

    USProfile.derive_heading_from_body = derive
    USProfile.extract_definitions_from_section = extract
    before: list[dict[str, Any]] = []
    after: list[dict[str, Any]] = []
    try:
        for path in files:
            jurisdiction = jurisdiction_for(path)
            parquet = pq.ParquetFile(path)
            index = 0
            for batch in parquet.iter_batches(
                columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=2_048
            ):
                for row in batch.to_pylist():
                    profile = get_profile(jurisdiction)
                    # Capture production before restoring extraction for this row only.
                    USProfile.extract_definitions_from_section = original_extract
                    before.extend(item.record() for item in capture_row(
                        jurisdiction=jurisdiction, source_file=path.name, source_row=index, row=row, after=True
                    ))
                    USProfile.extract_definitions_from_section = extract
                    after.extend(item.record() for item in capture_row(
                        jurisdiction=jurisdiction, source_file=path.name, source_row=index, row=row, after=True
                    ))
                    starts.pop(row["text"] or "", None)
                    index += 1
    finally:
        USProfile.derive_heading_from_body = original_derive
        USProfile.extract_definitions_from_section = original_extract

    before_by_key = {tuple_key(record): record for record in before}
    after_by_key = {tuple_key(record): record for record in after}
    changed = [
        {"change": "removed", "classification": _classification(before_by_key[key]), **before_by_key[key]}
        for key in sorted(before_by_key.keys() - after_by_key.keys())
    ] + [
        {"change": "added", "classification": _classification(after_by_key[key]), **after_by_key[key]}
        for key in sorted(after_by_key.keys() - before_by_key.keys())
    ]
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "lexgraph.mr106.b1-occurrence-start.v1",
        "snapshot_id": SNAPSHOT_ID,
        "files": len(files),
        "rows": rows,
        "proposal": "runtime-only B1 qualifying extraction_start; full-body scope/provenance retained",
        "before_tuple_count": len(before),
        "after_tuple_count": len(after),
        "changed_key_count": len(changed),
        "classification_totals": dict(sorted(Counter(item["classification"] for item in changed).items())),
        "changed_key_ledger_sha256": write_jsonl(out / "changed_key_classification.jsonl", changed),
    }
    write_json(out / "summary.json", result)
    if result["classification_totals"].get("UNCLASSIFIED"):
        raise RuntimeError(f"ESCALATION: {result['classification_totals']['UNCLASSIFIED']} unclassified keys")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.snapshot, args.out), sort_keys=True))


if __name__ == "__main__":
    main()
