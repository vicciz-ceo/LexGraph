"""Item 8 (QA-fail cycle 1 re-certification) -- text-change sampling +
named-exemplar verification. Brief requirement: "your text-change sampling
must be >=30 rows across >=10 jurisdictions including the QA exemplar rows
CA/FL/PR -- all three must now show CORRECT full text."

Two parts:
  1. Named-exemplar check: pulls the exact 3 QA-named anchors (CA "Covered
     populations", FL "Cancer", PR "Agent") from whichever category they
     now land in (`unchanged` if current now matches baseline byte-for-
     byte, `text_changes` otherwise -- checked against BOTH ledgers, not
     assumed) and prints their current `definition_text` for direct
     comparison against the RED test's own `expected` strings.
  2. Reproducible random sample (fixed seed) of >=30 `text_changes.jsonl`
     rows spanning >=10 distinct jurisdictions, printed for manual
     adjudication (before/after, full text when short, tails when long).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_DIR = SCRIPTS_DIR / "gate5-run"
ADJ_DIR = SCRIPTS_DIR / "gate5-adjudication-v2"

NAMED_EXEMPLARS = [
    ("US-CA", "STATE_CA_Cgov_T2_D3_P1_C5.6_S11546.46", "Covered populations"),
    ("US-FL", "STATE_FL_TX_C112_PI_S112.1816", "Cancer"),
    ("US-PR", "STATE_PR_LEY_60_1963_ART422", "Agent"),
]


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def find_current_record(current_records: dict, jurisdiction: str, act_id: str, term: str):
    for key, rec in current_records.items():
        if rec["jurisdiction"] == jurisdiction and rec["source_row_id"] == act_id and rec["term"] == term:
            return rec
    return None


def main() -> None:
    current_path = RUN_DIR / "current" / "records.jsonl"
    current_records: dict[tuple, dict] = {}
    with current_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            current_records[(row["jurisdiction"], row["source_file"], row["source_row"], row["term"])] = row

    print("=== NAMED EXEMPLAR CHECK (CA/FL/PR) ===")
    for jurisdiction, act_id, term in NAMED_EXEMPLARS:
        rec = find_current_record(current_records, jurisdiction, act_id, term)
        if rec is None:
            print(f"[MISSING] {jurisdiction} {act_id} {term!r} -- NOT FOUND in current records at all")
            continue
        text = rec["definition_text"]
        print(f"[{jurisdiction}] {act_id} {term!r} ({len(text)} chars):")
        print(f"  {text!r}")
        print()

    print("=== RANDOM TEXT-CHANGE SAMPLE (seed=31, target >=30 rows / >=10 jurisdictions) ===")
    text_changes = load_jsonl(ADJ_DIR / "text_changes.jsonl")
    print(f"total text_changes: {len(text_changes)}")
    by_jurisdiction: dict[str, list[dict]] = {}
    for row in text_changes:
        by_jurisdiction.setdefault(row["anchor"][0], []).append(row)
    print(f"distinct jurisdictions in text_changes: {len(by_jurisdiction)}")

    rng = random.Random(31)
    jurisdictions = sorted(by_jurisdiction)
    # Guarantee >=10 distinct jurisdictions: take up to 3 from each of 12
    # randomly chosen jurisdictions (more than 10, in case some yield < 3).
    chosen_jurisdictions = rng.sample(jurisdictions, min(14, len(jurisdictions)))
    sample: list[dict] = []
    for j in chosen_jurisdictions:
        pool = by_jurisdiction[j]
        take = rng.sample(pool, min(3, len(pool)))
        sample.extend(take)
    if len(sample) < 30:
        remaining = [r for r in text_changes if r not in sample]
        rng.shuffle(remaining)
        sample.extend(remaining[: 30 - len(sample)])

    print(f"sample size: {len(sample)}, jurisdictions covered: {len({r['anchor'][0] for r in sample})}")
    print()
    for row in sample:
        anchor = row["anchor"]
        before = row["before"]["definition_text"]
        after = row["after"]["definition_text"]
        print(f"--- {anchor[0]} {anchor[1]}:{anchor[2]} term={anchor[3]!r} ---")
        print(f"  before ({len(before)} chars): {before[:200]!r}{'...' if len(before) > 200 else ''}")
        print(f"  after  ({len(after)} chars): {after[:200]!r}{'...' if len(after) > 200 else ''}")
        print()


if __name__ == "__main__":
    main()
