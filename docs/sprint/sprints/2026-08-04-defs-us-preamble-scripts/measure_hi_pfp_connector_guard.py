"""Read-only, persisted-altitude mutation probe for M-R104's proposed guard.

This does not change production.  It temporarily wraps the live
``USProfile.extract_definitions_from_section`` method, writes exact before and
after persisted tuple/key ledgers outside the repository, then restores the
method in ``finally``.  The proposal is deliberately narrow: only a
body-derived extraction candidate with a clause-length quoted term (>150
characters) and a connector-only definition (``;``, ``; and``, or ``; or``)
is omitted.  It is not keyed by Hawaii, body size, a quote alone, or a
semicolon alone.
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
    certification_hash,
    jurisdiction_for,
    tuple_key,
    validate_corpus,
    write_json,
)

_CONNECTOR_STUBS = frozenset({";", "; and", "; or"})
_CLAUSE_TERM_MIN_CHARS = 151


def _is_proposed_connector_pseudo(candidate) -> bool:
    """The proposed extraction seam, expressed only for this runtime probe."""
    return (
        len(candidate.terms) == 1
        and len(candidate.terms[0]) >= _CLAUSE_TERM_MIN_CHARS
        and candidate.definition_text.strip().casefold() in _CONNECTOR_STUBS
    )


def _write_record(handle, digest, record: dict[str, Any]) -> None:
    """Append one deterministic JSONL record without retaining corpus output."""
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    handle.write(encoded)
    digest.update(encoded)


def _classify(record: dict[str, Any]) -> str:
    """Classify only source-verified changes; unknown keys fail the probe."""
    if (
        record["jurisdiction"] == "US-HI"
        and record["source_file"] == "us_hi_statutes.parquet"
        and record["source_row"] == 5
        and len(record["term"]) >= _CLAUSE_TERM_MIN_CHARS
        and record["definition_text"].strip().casefold() in _CONNECTOR_STUBS
    ):
        return "confirmed_hi_contractual_quote_connector_stub_false_capture"
    return "UNCLASSIFIED"


def measure(snapshot: Path, out: Path) -> dict[str, Any]:
    """Write full ledgers and fail closed if a proposed changed key is unknown."""
    from app.definition_links.us_profile import USProfile

    files, rows, _ = validate_corpus(snapshot)
    assert len(files) == EXPECTED_FILE_COUNT and rows == EXPECTED_ROW_COUNT
    out.mkdir(parents=True, exist_ok=True)
    original = USProfile.extract_definitions_from_section

    def proposed(self, text: str, *, scope: str, heading_was_derived: bool = False):
        candidates = original(self, text, scope=scope, heading_was_derived=heading_was_derived)
        if not heading_was_derived:
            return candidates
        return [candidate for candidate in candidates if not _is_proposed_connector_pseudo(candidate)]

    before_digest, after_digest = hashlib.sha256(), hashlib.sha256()
    before_key_digest, after_key_digest = hashlib.sha256(), hashlib.sha256()
    before_count = after_count = 0
    removed: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    USProfile.extract_definitions_from_section = proposed
    try:
        with (
            (out / "before_persisted_tuples.jsonl").open("wb") as before_tuples,
            (out / "after_persisted_tuples.jsonl").open("wb") as after_tuples,
            (out / "before_persisted_keys.jsonl").open("wb") as before_keys,
            (out / "after_persisted_keys.jsonl").open("wb") as after_keys,
        ):
            for path in files:
                jurisdiction = jurisdiction_for(path)
                index = 0
                parquet = pq.ParquetFile(path)
                for batch in parquet.iter_batches(
                    columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=2_048
                ):
                    for row in batch.to_pylist():
                        # Temporarily restore current production for the BEFORE
                        # call; the immediately following AFTER call is the
                        # proposal.  Both invoke the live profile/registry and
                        # persistence first-wins seam via ``capture_row``.
                        USProfile.extract_definitions_from_section = original
                        before = [item.record() for item in capture_row(
                            jurisdiction=jurisdiction, source_file=path.name,
                            source_row=index, row=row, after=True,
                        )]
                        USProfile.extract_definitions_from_section = proposed
                        after = [item.record() for item in capture_row(
                            jurisdiction=jurisdiction, source_file=path.name,
                            source_row=index, row=row, after=True,
                        )]
                        before_by_key = {tuple_key(record): record for record in before}
                        after_by_key = {tuple_key(record): record for record in after}
                        removed.extend(before_by_key[key] for key in before_by_key.keys() - after_by_key.keys())
                        added.extend(after_by_key[key] for key in after_by_key.keys() - before_by_key.keys())
                        for record in before:
                            _write_record(before_tuples, before_digest, record)
                            _write_record(before_keys, before_key_digest, {"key": list(tuple_key(record))})
                        for record in after:
                            _write_record(after_tuples, after_digest, record)
                            _write_record(after_keys, after_key_digest, {"key": list(tuple_key(record))})
                        before_count += len(before)
                        after_count += len(after)
                        index += 1
    finally:
        USProfile.extract_definitions_from_section = original

    changed = [{"change": "removed", "classification": _classify(record), **record} for record in sorted(removed, key=tuple_key)]
    changed.extend({"change": "added", "classification": _classify(record), **record} for record in sorted(added, key=tuple_key))
    classifications = Counter(record["classification"] for record in changed)
    if "UNCLASSIFIED" in classifications:
        raise RuntimeError(f"ESCALATION: {classifications['UNCLASSIFIED']} proposed changed keys are unclassified")

    changed_digest = hashlib.sha256()
    with (out / "changed_key_classification.jsonl").open("wb") as changed_ledger:
        for record in changed:
            _write_record(changed_ledger, changed_digest, record)
    result = {
        "schema": "lexgraph.mr104.hi-connector-guard.v1",
        "snapshot_id": SNAPSHOT_ID,
        "files": EXPECTED_FILE_COUNT,
        "rows": EXPECTED_ROW_COUNT,
        "proposal": {
            "runtime_monkeypatch_only": True,
            "body_derived_only": True,
            "min_term_chars": _CLAUSE_TERM_MIN_CHARS,
            "connector_stubs": sorted(_CONNECTOR_STUBS),
        },
        "before": {"tuple_count": before_count, "tuple_hash": before_digest.hexdigest(), "key_hash": before_key_digest.hexdigest()},
        "after": {"tuple_count": after_count, "tuple_hash": after_digest.hexdigest(), "key_hash": after_key_digest.hexdigest()},
        "changed": {
            "removed": len(removed), "added": len(added), "total": len(changed),
            "classification_totals": dict(sorted(classifications.items())), "ledger_hash": changed_digest.hexdigest(),
        },
    }
    result["summary_hash"] = certification_hash(result)
    write_json(out / "summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.snapshot, args.out), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
