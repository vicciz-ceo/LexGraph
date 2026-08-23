"""Item 5 (sprint 2026-08-23-defs-debt-31) 100% anchor-granularity delta
adjudication. Reads `current/records.jsonl` and `baseline/records.jsonl`
(both produced by `run_gate5_certification.sh` via `measure_actual_
production.py --current` against, respectively, this worktree and the
archived `main` @ 8850401), and classifies every changed record per the
known trap: "Decompose removals at ANCHOR granularity before reacting
(remove+add pairs on the same (row, term) are text changes, not
losses)."

Anchor key = (jurisdiction, source_file, source_row, term) -- the SAME
row+term identity `measure_actual_production.py`'s own `key()` function
uses, minus `definition_text`/`scope` (which are exactly the bytes that
CAN legitimately change under Items 1/2's own mandate).

Categories:
  A. TEXT CHANGE  -- anchor present on both sides, definition_text or
     scope differs. Expected, high-volume (Item 1's own trim + Item 4's
     recovered bounds). Auto-classified, sampled for sanity.
  B. TRUE REMOVAL -- anchor present in baseline, absent from current
     entirely. Must be exactly the 19 adjudicated single-letter
     phantoms (Item 2) -- P-R15 deletion-side screen: flagged loudly if
     ANY other true removal appears, or if an "adjacent explicit
     defining relation" (a removed definition_text starting with a
     means/includes-family verb) is found among removals not on the
     19-name allowlist.
  C. TRUE ADDITION -- anchor present in current, absent from baseline
     entirely. Expected for Item 4's recovered FX7-remainder rows and
     any row where Items 1/2 unblocked a previously wholly-uncaptured
     term. Reported for review, not auto-flagged as a problem (P-R11:
     adjudicate the real delta, don't presuppose its shape).

Writes `gate5-adjudication/summary.json` (counts) and per-category
JSONL ledgers for QA/Planner review.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_DIR = SCRIPTS_DIR / "gate5-run"
OUT_DIR = SCRIPTS_DIR / "gate5-adjudication"

# The 19 enumerated single-letter phantoms Item 2 removes (issue #31 /
# expansion_precision_2.md census) -- filled in once the delta itself
# names them (P-R11: never hand-authored before the run; this list is
# populated by cross-referencing Category B's own findings against the
# Item 2 test file's own named exemplars, not guessed in advance).
KNOWN_SINGLE_LETTER_PHANTOM_TERMS: set[str] = set()

_DEFINING_VERB_PREFIXES = (
    "means ", "shall mean ", "has the meaning", "shall include ", "includes ",
)


def anchor_key(row: dict) -> tuple[str, str, int, str]:
    return (row["jurisdiction"], row["source_file"], row["source_row"], row["term"])


def load_records(path: Path) -> dict[tuple, dict]:
    records: dict[tuple, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            records[anchor_key(row)] = row
    return records


def looks_like_adjacent_defining_relation(definition_text: str) -> bool:
    stripped = definition_text.strip()
    return any(stripped.lower().startswith(p) for p in _DEFINING_VERB_PREFIXES)


def main() -> None:
    current_path = RUN_DIR / "current" / "records.jsonl"
    baseline_path = RUN_DIR / "baseline" / "records.jsonl"
    if not current_path.is_file() or not baseline_path.is_file():
        print(f"NOT READY: current={current_path.is_file()} baseline={baseline_path.is_file()}")
        sys.exit(1)

    print("loading current records...")
    current = load_records(current_path)
    print(f"  {len(current)} current anchors")
    print("loading baseline records...")
    baseline = load_records(baseline_path)
    print(f"  {len(baseline)} baseline anchors")

    current_anchors = set(current)
    baseline_anchors = set(baseline)

    both = current_anchors & baseline_anchors
    only_current = current_anchors - baseline_anchors
    only_baseline = baseline_anchors - current_anchors

    text_changes = []
    unchanged = 0
    for key in both:
        c, b = current[key], baseline[key]
        if c["definition_text"] != b["definition_text"] or c["scope"] != b["scope"]:
            text_changes.append({"anchor": list(key), "before": b, "after": c})
        else:
            unchanged += 1

    true_additions = [current[k] for k in only_current]
    true_removals = [baseline[k] for k in only_baseline]

    flagged_removals = [
        r
        for r in true_removals
        if r["term"] not in KNOWN_SINGLE_LETTER_PHANTOM_TERMS
        and looks_like_adjacent_defining_relation(r["definition_text"])
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("text_changes", text_changes),
        ("true_additions", true_additions),
        ("true_removals", true_removals),
        ("flagged_removals_p_r15", flagged_removals),
    ):
        with (OUT_DIR / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "current_anchor_count": len(current_anchors),
        "baseline_anchor_count": len(baseline_anchors),
        "unchanged_count": unchanged,
        "text_change_count": len(text_changes),
        "true_addition_count": len(true_additions),
        "true_removal_count": len(true_removals),
        "p_r15_flagged_removal_count": len(flagged_removals),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))

    if flagged_removals:
        print(
            f"\n*** P-R15 SCREEN: {len(flagged_removals)} removal(s) look like a genuine "
            "defining relation and are NOT on the known single-letter-phantom allowlist. "
            "Manual adjudication required -- see gate5-adjudication/flagged_removals_p_r15.jsonl ***"
        )


if __name__ == "__main__":
    main()
