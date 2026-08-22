"""Round-2 Task 2: deterministic stratified 100-item sample of population (c)
-- the pure-added anchors OUTSIDE round 1's 16-jurisdiction census scope.

Method: identical in spirit to round 1's `sample_design_b_expansion_wave.py`
-- proportional allocation by jurisdiction (largest-remainder rounding),
then `random.Random(f"{20260823}:{jurisdiction}")` (seed = this pass's own
run date, disclosed; distinct from round 1's 20260822 seed since the
population differs) sampling per-jurisdiction from a stable pre-sort order
(sorted by (source_file, source_row, term) for determinism).
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PURE_ADDED = HERE / "run" / "round2" / "pure_added.jsonl"
OUT = HERE / "run" / "round2"

SIXTEEN = {
    "US-WA", "US-VA", "US-FED", "US-UT", "US-TX", "US-SC", "US-AZ", "US-NJ",
    "US-MI", "US-ND", "US-NY", "US-OK", "US-NM", "US-NV", "US-OH", "US-ME",
}
SAMPLE_SIZE = 100
SEED_DATE = 20260823


def largest_remainder_allocation(counts: dict[str, int], total: int) -> dict[str, int]:
    grand_total = sum(counts.values())
    exact = {j: c * total / grand_total for j, c in counts.items()}
    floors = {j: int(v) for j, v in exact.items()}
    allocated = sum(floors.values())
    remainder = total - allocated
    # largest remainder wins remaining slots; tie-break alphabetically for determinism
    remainders = sorted(counts.keys(), key=lambda j: (-(exact[j] - floors[j]), j))
    for j in remainders[:remainder]:
        floors[j] += 1
    return floors


def main() -> None:
    rows = [json.loads(l) for l in PURE_ADDED.read_text(encoding="utf-8").splitlines() if l.strip()]
    outside = [r for r in rows if r["jurisdiction"] not in SIXTEEN]

    by_j: dict[str, list[dict]] = defaultdict(list)
    for r in outside:
        by_j[r["jurisdiction"]].append(r)
    counts = {j: len(v) for j, v in by_j.items()}

    allocation = largest_remainder_allocation(counts, SAMPLE_SIZE)

    sample: list[dict] = []
    for j in sorted(by_j.keys()):
        n = allocation.get(j, 0)
        if n <= 0:
            continue
        pool = sorted(by_j[j], key=lambda r: (r["source_file"], r["source_row"], r["term"]))
        rng = random.Random(f"{SEED_DATE}:{j}")
        chosen = rng.sample(pool, min(n, len(pool)))
        sample.extend(chosen)

    print(f"population (c) size: {len(outside)}; jurisdictions: {len(by_j)}")
    print(f"allocation: {dict(sorted(allocation.items(), key=lambda x: -x[1]))}")
    print(f"sample size: {len(sample)}")

    (OUT / "population_c_sample.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in sample) + "\n", encoding="utf-8"
    )
    (OUT / "population_c_allocation.json").write_text(
        json.dumps({"population_size": len(outside), "counts": counts, "allocation": allocation}, indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    main()
