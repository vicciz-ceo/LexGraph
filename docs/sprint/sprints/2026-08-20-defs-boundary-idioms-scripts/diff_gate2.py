"""Gate-2 raw delta for sprint 2026-08-20-defs-boundary-idioms (issue #27).

Diffs current/records.jsonl against baseline/records.jsonl using the SAME
key() tuple measure_actual_production_all_rows.py uses (jurisdiction,
source_file, source_row, term, definition_text, scope). Modeled directly on
the precedent in docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/
diff_gate2.py: no hard-coded certified-ledger hash, since there is no
pre-existing certificate for this item's incremental delta (P-R11: run,
then adjudicate; no hand-authored ledger).

Produces the raw removed/added set only. Adjudication at (row, term) anchor
granularity is QA's job, not this script's.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def key(row: dict) -> tuple:
    return (
        row["jurisdiction"], row["source_file"], row["source_row"], row["term"],
        row["definition_text"], row["scope"],
    )


def load(path: Path) -> dict[tuple, dict]:
    return {key(row): row for row in (json.loads(line) for line in path.read_text().splitlines() if line)}


def main() -> None:
    before = load(RUN / "baseline" / "records.jsonl")
    after = load(RUN / "current" / "records.jsonl")
    changed = [{"change": "removed", **before[item]} for item in sorted(before.keys() - after.keys())]
    changed += [{"change": "added", **after[item]} for item in sorted(after.keys() - before.keys())]
    changed.sort(key=lambda row: (row["jurisdiction"], row["source_file"], str(row["source_row"]), row["term"], row["definition_text"] + "\0" + row["scope"], row["change"]))

    out_dir = RUN / "compare"
    out_dir.mkdir(parents=True, exist_ok=True)
    changed_path = out_dir / "changed.jsonl"
    digest = hashlib.sha256()
    with changed_path.open("w", encoding="utf-8") as handle:
        for row in changed:
            line = canonical(row)
            handle.write(line.decode() + "\n")
            digest.update(line + b"\n")

    # Anchor-level grouping: decompose remove+add pairs on the same (row, term)
    # first, per gate 2's own text, before treating anything as a net change.
    anchors: dict[tuple, dict[str, list[dict]]] = {}
    for row in changed:
        anchor = (row["jurisdiction"], row["source_file"], row["source_row"], row["term"])
        bucket = anchors.setdefault(anchor, {"removed": [], "added": []})
        bucket[row["change"]].append(row)
    net_pure_removed = sum(1 for b in anchors.values() if b["removed"] and not b["added"])
    net_pure_added = sum(1 for b in anchors.values() if b["added"] and not b["removed"])
    net_both = sum(1 for b in anchors.values() if b["added"] and b["removed"])

    summary = {
        "changed": len(changed),
        "removed": sum(row["change"] == "removed" for row in changed),
        "added": sum(row["change"] == "added" for row in changed),
        "changed_sha256": digest.hexdigest(),
        "distinct_anchors_row_term": len(anchors),
        "anchors_pure_removed": net_pure_removed,
        "anchors_pure_added": net_pure_added,
        "anchors_both_removed_and_added": net_both,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
