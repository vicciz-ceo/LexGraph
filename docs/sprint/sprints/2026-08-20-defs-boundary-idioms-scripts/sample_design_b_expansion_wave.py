"""Deterministic stratified precision sample of the design (b) expansion
wave, sprint 2026-08-20-defs-boundary-idioms.

Reads run/design_b/expansion_wave.jsonl (produced by
measure_design_b_expansion_wave.py), draws a stratified sample of
SAMPLE_SIZE items (proportional allocation by jurisdiction, largest-
remainder rounding -- same method Q2/Q3 of investigation.md used), then a
seeded deterministic draw per jurisdiction stratum from a stable pre-sort
order. Seed is disclosed: f"{SEED_DATE}:{jurisdiction}" (this task's own
run date, 2026-08-22 -- distinct from the Planner's 2026-08-20/2026-08-21
seeds so this sample is not a re-derivation of theirs, even though the
underlying population differs anyway: theirs was a 200-row sample, this is
a full census within the same 16-jurisdiction scope).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SAMPLE_SIZE = 100
SEED_DATE = 20260822

RUN = Path(__file__).resolve().parent / "run" / "design_b"


def main() -> None:
    items = [json.loads(line) for line in (RUN / "expansion_wave.jsonl").read_text().splitlines() if line]
    by_jurisdiction: dict[str, list[dict]] = {}
    for item in items:
        by_jurisdiction.setdefault(item["jurisdiction"], []).append(item)

    total = len(items)
    # Largest-remainder proportional allocation across jurisdictions present.
    raw_alloc = {j: len(v) * SAMPLE_SIZE / total for j, v in by_jurisdiction.items()}
    alloc = {j: int(v) for j, v in raw_alloc.items()}
    remainder = SAMPLE_SIZE - sum(alloc.values())
    remainders = sorted(raw_alloc.items(), key=lambda kv: (kv[1] - int(kv[1])), reverse=True)
    i = 0
    while remainder > 0 and i < len(remainders):
        j, _ = remainders[i]
        alloc[j] += 1
        remainder -= 1
        i += 1

    sample: list[dict] = []
    for jurisdiction, n in sorted(alloc.items()):
        if n <= 0:
            continue
        pool = sorted(
            by_jurisdiction[jurisdiction],
            key=lambda it: (it["source_file"], it["source_row"], it["term"]),
        )
        rng = random.Random(f"{SEED_DATE}:{jurisdiction}")
        n = min(n, len(pool))
        chosen = rng.sample(pool, n)
        sample.extend(chosen)

    sample.sort(key=lambda it: (it["jurisdiction"], it["source_file"], it["source_row"], it["term"]))

    print(f"population={total}")
    print(f"allocation={dict(sorted(alloc.items()))}")
    print(f"sample_size={len(sample)}")
    (RUN / "precision_sample.jsonl").write_text(
        "\n".join(json.dumps(it, sort_keys=True, ensure_ascii=False) for it in sample) + "\n"
    )
    for idx, it in enumerate(sample, 1):
        print(f"{idx}\t{it['jurisdiction']}\t{it['source_file']}\t{it['source_row']}\t{it['act_id']}\t{it['term']!r}")


if __name__ == "__main__":
    main()
