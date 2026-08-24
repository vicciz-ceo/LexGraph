"""Item 8 (QA-fail cycle 1 re-certification) -- cross-check the v2 delta
against Item 4's own 101-row FX7-remainder ledger (`item4_ledger.jsonl`,
unaffected by this cycle's Items 6/7 fixes -- gate 8's own scope keeps
Item 1/6's trim away from ceiling-tripped rows by design). Must reproduce
the original run's own "0 overlap" finding: none of the 101 UNRECOVERABLE
rows may appear as a text change or true addition in the v2 delta.
"""
from __future__ import annotations

import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ADJ_DIR = SCRIPTS_DIR / "gate5-adjudication-v2"


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def main() -> None:
    ledger = load_jsonl(SCRIPTS_DIR / "item4_ledger.jsonl")
    ledger_keys = {(r["jurisdiction"], r["act_id"], r["term"]) for r in ledger}
    print(f"item4 ledger rows: {len(ledger)}, distinct anchors: {len(ledger_keys)}")

    text_changes = load_jsonl(ADJ_DIR / "text_changes.jsonl")
    true_additions = load_jsonl(ADJ_DIR / "true_additions.jsonl")
    true_removals = load_jsonl(ADJ_DIR / "true_removals.jsonl")

    tc_keys = {(r["anchor"][0], r["after"]["source_row_id"], r["anchor"][3]) for r in text_changes}
    ta_keys = {(r["jurisdiction"], r["source_row_id"], r["term"]) for r in true_additions}
    tr_keys = {(r["jurisdiction"], r["source_row_id"], r["term"]) for r in true_removals}

    overlap_tc = ledger_keys & tc_keys
    overlap_ta = ledger_keys & ta_keys
    overlap_tr = ledger_keys & tr_keys

    print(f"overlap with text_changes: {len(overlap_tc)}")
    print(f"overlap with true_additions: {len(overlap_ta)}")
    print(f"overlap with true_removals: {len(overlap_tr)}")
    if overlap_tc:
        print("  TEXT CHANGE OVERLAP:", sorted(overlap_tc)[:10])
    if overlap_ta:
        print("  TRUE ADDITION OVERLAP:", sorted(overlap_ta)[:10])
    if overlap_tr:
        print("  TRUE REMOVAL OVERLAP:", sorted(overlap_tr)[:10])

    total_overlap = len(overlap_tc) + len(overlap_ta) + len(overlap_tr)
    print(f"\nTOTAL OVERLAP: {total_overlap} (expected 0, per gate 8's ceiling-protection scope)")


if __name__ == "__main__":
    main()
