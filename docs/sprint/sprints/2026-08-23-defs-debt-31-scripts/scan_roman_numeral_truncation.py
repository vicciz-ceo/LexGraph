"""Item 8 (QA-fail cycle 1 re-certification) -- roman-numeral truncation
scan. Escalation artifact: this is the exact script used to find and
quantify the "5th" over-trim shape (roman-numeral internal enumeration
truncated to its first item) that triggered the manager-authorized
roman-numeral run-tracking fix (commit 457045b).

Scans a `gate5-adjudication-v2/text_changes.jsonl` (produced by
`adjudicate_gate5_delta_v2.py`) for the shape: the `after` (current)
definition_text starts with a roman-numeral marker (i)-(x), and the
`before` (baseline) text is a strict superset that continues, right where
`after` ends, with ANOTHER roman-numeral marker -- i.e. a roman-numeral
internal list visibly truncated to fewer items than baseline's own
(untrimmed) capture shows.

Run against the PRE-fix delta (gate5-adjudication-v2 as it stood before
commit 457045b): found 19 rows / 10 jurisdictions -- the population that
justified the fix. Re-run against the POST-fix delta (this file's own
default use, now): the count should collapse to ~0 for THIS specific
shape (confirming the fix's own narrow target is resolved) -- residual
rows found by other means (nested mixed-vocabulary enumerations, pre-
existing-in-baseline bleeds) are a SEPARATE, disclosed, deliberately
NOT-further-fixed gap (see item5_gate5_certification_v2.md's own
"Disclosed gap" section, manager hard-terminal-condition ruling).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ADJ_DIR = SCRIPTS_DIR / "gate5-adjudication-v2"

_ROMAN = r"(?:i|ii|iii|iv|v|vi|vii|viii|ix|x)"
ROMAN_MARKER_START_RE = re.compile(rf"\A\(({_ROMAN})\)\s", re.IGNORECASE)
NEXT_ROMAN_MARKER_RE = re.compile(rf"\n\n\(({_ROMAN})\)\s", re.IGNORECASE)


def main() -> None:
    hits: list[dict] = []
    total = 0
    with (ADJ_DIR / "text_changes.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            total += 1
            row = json.loads(line)
            after = row["after"]["definition_text"]
            before = row["before"]["definition_text"]
            if ROMAN_MARKER_START_RE.match(after) and before.startswith(after):
                remainder = before[len(after) :]
                if NEXT_ROMAN_MARKER_RE.match(remainder):
                    hits.append(
                        {
                            "jurisdiction": row["anchor"][0],
                            "source_file": row["anchor"][1],
                            "source_row": row["anchor"][2],
                            "term": row["anchor"][3],
                            "act_id": row["after"]["source_row_id"],
                            "after_len": len(after),
                            "before_len": len(before),
                        }
                    )

    print(f"total text_changes scanned: {total}")
    print(f"roman-numeral truncation-shaped hits: {len(hits)}")
    print(f"distinct jurisdictions: {len({h['jurisdiction'] for h in hits})}")
    out_path = SCRIPTS_DIR / "roman_numeral_truncation_scan.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for h in hits:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    for h in hits:
        print(h["jurisdiction"], h["act_id"], repr(h["term"]), h["after_len"], "->", h["before_len"])


if __name__ == "__main__":
    main()
