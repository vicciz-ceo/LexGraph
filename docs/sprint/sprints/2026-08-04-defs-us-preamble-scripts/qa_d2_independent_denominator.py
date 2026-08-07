"""Q-D2: independently derive the P-R7 signal-agnostic candidate denominator.

This program owns its raw corpus read and broad candidate recognisers.  It
does not import Q-D1, its counting helpers, or its output files.
"""

from __future__ import annotations

import argparse
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from qa_g7_common import (
    EXPECTED_FILE_COUNT, EXPECTED_ROW_COUNT, INTEGRATION_SHA, SNAPSHOT_ID,
    CertificationError, capture_row, jurisdiction_for, sha256_value,
    validate_corpus, validate_integration, write_json,
)

# Deliberately unrelated to body-preamble intro phrases.  These broad raw-text
# detectors reproduce the ratified quoted/unquoted term population definition.
_VERB = r"(?:shall\s+mean|shall\s+have\s+the\s+meaning|has\s+the\s+(?:same\s+)?meaning|is\s+defined\s+as|are\s+defined\s+as|means)"
_QUOTED = re.compile(r"[\"“][^\"”\n]{1,240}[\"”][^\n]{0,280}?\b" + _VERB + r"\b", re.I)
_UNQUOTED_COMMA = re.compile(r"\bthe\s+term\s*,\s*[A-Za-z][A-Za-z0-9 '\-]{1,120},\s*" + _VERB + r"\b", re.I)
_UNQUOTED_CAPITAL = re.compile(r"(?:^|[;:\n])\s*[A-Z][A-Za-z0-9 '\-]{2,120}\s+" + _VERB + r"\b", re.I)


def _candidate_components(body: str) -> list[str]:
    window = body[:600]
    components: list[str] = []
    if _QUOTED.search(window):
        components.append("quoted_broad_verb")
    if _UNQUOTED_COMMA.search(window) or _UNQUOTED_CAPITAL.search(window):
        components.append("unquoted_broad_verb")
    return components


def measure(snapshot: Path, out: Path) -> dict[str, Any]:
    validate_integration()
    files, rows, file_rows = validate_corpus(snapshot)
    from app.definition_links.us_profile import is_definitions_heading

    started = time.monotonic()
    states: dict[str, dict[str, int]] = {}
    candidates: list[dict[str, Any]] = []
    for path in files:
        jurisdiction = jurisdiction_for(path)
        counts = defaultdict(int)
        parquet = pq.ParquetFile(path)
        index = 0
        for batch in parquet.iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=2_048
        ):
            for row in batch.to_pylist():
                # The ORIGINAL heading gate is purposely bare and signal-agnostic
                # with respect to post-preamble recognition.
                if not is_definitions_heading(row["section_title"] or ""):
                    components = _candidate_components(row["text"] or "")
                    if components:
                        counts["candidate_rows"] += 1
                        for component in components:
                            counts[component] += 1
                        captured = bool(capture_row(
                            jurisdiction=jurisdiction, source_file=path.name, source_row=index, row=row, after=True
                        ))
                        counts["already_captured" if captured else "uncaptured"] += 1
                        candidates.append({
                            "jurisdiction": jurisdiction, "source_file": path.name, "source_row": index,
                            "source_row_id": row["act_id"], "components": components, "captured": captured,
                        })
                index += 1
        states[jurisdiction] = dict(counts)
    total = defaultdict(int)
    for state in states.values():
        for key, value in state.items():
            total[key] += value
    if rows != EXPECTED_ROW_COUNT or len(states) != EXPECTED_FILE_COUNT:
        raise CertificationError("D2 did not independently cover the full fixed census")
    result = {
        "schema": "lexgraph.g7.qd2.v1", "snapshot_id": SNAPSHOT_ID, "integration_sha": INTEGRATION_SHA,
        "files": EXPECTED_FILE_COUNT, "rows": rows, "per_jurisdiction": {k: states[k] for k in sorted(states)},
        "totals": dict(sorted(total.items())),
        "method": {"original_heading_must_fail_bare_detector": True, "window_chars": 600, "components": ["quoted_broad_verb", "unquoted_broad_verb"], "signal_agnostic_denominator": True},
        "candidate_population_hash": sha256_value(sorted(candidates, key=lambda r: (r["source_file"], r["source_row"]))),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    result["summary_hash"] = sha256_value(result)
    write_json(out / "qd2_summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = measure(args.snapshot, args.out)
    print(f"Q-D2 PASS rows={result['rows']} candidates={result['totals'].get('candidate_rows', 0)} hash={result['summary_hash']}")


if __name__ == "__main__":
    main()
