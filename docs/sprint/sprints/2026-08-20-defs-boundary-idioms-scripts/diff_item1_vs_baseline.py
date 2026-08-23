"""Round-2 cross-check: diff run/item1/records.jsonl (a51b1de, Item 1 alone)
against run/baseline/records.jsonl (d660849, pre-fix) using the SAME key/
anchor logic as diff_gate2.py, to independently reproduce the historical
6,309/134/1,141 figures and cross-validate the precise mechanism census's
"primary" bucket (6,309)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / "run"


def key(row: dict) -> tuple:
    return (row["jurisdiction"], row["source_file"], row["source_row"], row["term"], row["definition_text"], row["scope"])


def load(path: Path) -> dict[tuple, dict]:
    return {key(row): row for row in (json.loads(line) for line in path.read_text().splitlines() if line)}


def main() -> None:
    before = load(RUN / "baseline" / "records.jsonl")
    after = load(RUN / "item1" / "records.jsonl")
    changed = [{"change": "removed", **before[k]} for k in (before.keys() - after.keys())]
    changed += [{"change": "added", **after[k]} for k in (after.keys() - before.keys())]

    anchors: dict[tuple, dict[str, list]] = {}
    for row in changed:
        anchor = (row["jurisdiction"], row["source_file"], row["source_row"], row["term"])
        bucket = anchors.setdefault(anchor, {"removed": [], "added": []})
        bucket[row["change"]].append(row)
    pure_removed = sum(1 for b in anchors.values() if b["removed"] and not b["added"])
    pure_added = sum(1 for b in anchors.values() if b["added"] and not b["removed"])
    both = sum(1 for b in anchors.values() if b["added"] and b["removed"])

    print(json.dumps({
        "distinct_anchors": len(anchors),
        "pure_added": pure_added,
        "pure_removed": pure_removed,
        "both": both,
    }, indent=2))


if __name__ == "__main__":
    main()
