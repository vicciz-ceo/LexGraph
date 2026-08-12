"""Gate-3 regression diff for sprint `2026-08-12-shared-extraction-t35`.

Consumes two JSONL files produced by `measure_inline_fallback_population.py`
(run once against `main`/pre-fix HEAD, once against the fix branch) and
reports every `(code, act_id, term)` triple present BEFORE and absent AFTER
-- exactly M-R64's gate ("no term that is captured today may disappear").
A term's `definition_text` CHANGING is not itself a regression (the fix is
expected to change boundaries); a term's PRESENCE disappearing is.

Usage:
    backend/.venv/bin/python diff_before_after.py before.jsonl after.jsonl
"""

from __future__ import annotations

import json
import sys


def _load(path: str) -> dict[tuple[str, str], set[str]]:
    rows: dict[tuple[str, str], set[str]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = (rec["code"], rec["act_id"])
            rows.setdefault(key, set()).update(rec["terms"])
    return rows


def main() -> None:
    before_path, after_path = sys.argv[1], sys.argv[2]
    before = _load(before_path)
    after = _load(after_path)

    regressions: list[tuple[str, str, str]] = []
    for (code, act_id), terms in before.items():
        after_terms = after.get((code, act_id), set())
        for term in terms:
            if term not in after_terms:
                regressions.append((code, act_id, term))

    before_total = sum(len(v) for v in before.values())
    after_total = sum(len(v) for v in after.values())
    print(f"before: {len(before)} rows, {before_total} terms")
    print(f"after:  {len(after)} rows, {after_total} terms")
    print(f"regressions (term present before, absent after): {len(regressions)}")
    for code, act_id, term in regressions[:50]:
        print(f"  REGRESSION {code} {act_id}: {term!r}")
    if len(regressions) > 50:
        print(f"  ... and {len(regressions) - 50} more")
    sys.exit(1 if regressions else 0)


if __name__ == "__main__":
    main()
