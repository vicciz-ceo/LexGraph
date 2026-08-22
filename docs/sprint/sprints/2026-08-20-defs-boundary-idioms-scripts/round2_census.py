"""Round-2 precision sampler (sprint 2026-08-20-defs-boundary-idioms).

Read-only analysis over the already-computed gate-2 combined-run evidence
(`run/compare/changed.jsonl`, current f267644 vs baseline d660849). Buckets
every (jurisdiction, source_file, source_row, term) anchor into pure_added /
pure_removed / both, per the same key diff_gate2.py itself used. Writes:

- run/round2/pure_added.jsonl   (one row per pure-added anchor; if an anchor
  had multiple "added" records -- same term, different definition_text --
  every one is included, tagged with an index)
- run/round2/pure_removed.jsonl (all 64 pure-removed anchors, full record)
- run/round2/both.jsonl         (1,022 both-anchors: removed-side + added-side
  records paired by anchor)
- run/round2/census_by_jurisdiction.json (per-jurisdiction pure_added counts)

No backend/frontend files touched. Pure aggregation over existing evidence.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHANGED = HERE / "run" / "compare" / "changed.jsonl"
OUT = HERE / "run" / "round2"


def anchor_key(row: dict) -> tuple:
    return (row["jurisdiction"], row["source_file"], row["source_row"], row["term"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    buckets: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: {"added": [], "removed": []})
    with CHANGED.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            buckets[anchor_key(row)][row["change"]].append(row)

    pure_added: list[dict] = []
    pure_removed: list[dict] = []
    both: list[dict] = []
    by_jurisdiction_added = defaultdict(int)
    for anchor, bucket in buckets.items():
        added, removed = bucket["added"], bucket["removed"]
        if added and not removed:
            pure_added.extend(added)
            by_jurisdiction_added[anchor[0]] += 1  # count the ANCHOR once
        elif removed and not added:
            pure_removed.extend(removed)
        else:
            both.append({"anchor": list(anchor), "removed": removed, "added": added})

    (OUT / "pure_added.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in pure_added) + "\n", encoding="utf-8"
    )
    (OUT / "pure_removed.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in pure_removed) + "\n", encoding="utf-8"
    )
    (OUT / "both.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in both) + "\n", encoding="utf-8"
    )

    n_anchors_added = sum(1 for b in buckets.values() if b["added"] and not b["removed"])
    n_anchors_removed = sum(1 for b in buckets.values() if b["removed"] and not b["added"])
    n_anchors_both = sum(1 for b in buckets.values() if b["added"] and b["removed"])

    summary = {
        "distinct_anchors_pure_added": n_anchors_added,
        "distinct_anchors_pure_removed": n_anchors_removed,
        "distinct_anchors_both": n_anchors_both,
        "pure_added_records": len(pure_added),
        "pure_removed_records": len(pure_removed),
        "by_jurisdiction_pure_added_anchors": dict(sorted(by_jurisdiction_added.items())),
    }
    (OUT / "census_by_jurisdiction.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
