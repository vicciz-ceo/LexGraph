"""Round-2 Task 4: seeded 30-item sample of the 1,022 both-removed-and-added
(re-bounded) anchors -- same method as round 1's Developer-pass 15-item
spot check (random.Random(seed).sample over a stable sort order), just a
larger n and this round's own disclosed seed.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOTH = HERE / "run" / "round2" / "both.jsonl"
OUT = HERE / "run" / "round2" / "both_sample_30.json"

SEED = 20260823  # this pass's own run date, disclosed (same convention as round 1)
N = 30


def main() -> None:
    rows = [json.loads(l) for l in BOTH.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: (r["anchor"][1], r["anchor"][2], r["anchor"][3]))  # (source_file, source_row, term)
    rng = random.Random(SEED)
    sample = rng.sample(rows, N)
    print(f"population: {len(rows)}; sample: {len(sample)}")
    OUT.write_text(json.dumps(sample, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
