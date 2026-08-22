"""Round-2 Task 3: classify all 64 pure-removed anchors against source text.

Reproduces the Developer's programmatic filter-shape check using the REAL,
unmodified production `_is_implausible_fallback_capture` (imported directly,
not re-implemented), then additionally fetches each row's actual source text
from the pinned snapshot and prints enough surrounding context to eyeball
whether the removed "term" was ever a genuine definiendum -- per the task's
explicit instruction not to take the shape match on faith.

Read-only: imports backend/app code but does not modify it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend"))

import pyarrow.parquet as pq  # noqa: E402

from app.definition_links.extract import DefinitionCandidate  # noqa: E402
from app.definition_links.us_profile import _is_implausible_fallback_capture  # noqa: E402

HERE = Path(__file__).resolve().parent
PURE_REMOVED = HERE / "run" / "round2" / "pure_removed.jsonl"
SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)

_row_cache: dict[tuple[str, int], dict] = {}


def get_row(fname: str, row_number: int) -> dict:
    key = (fname, row_number)
    if key in _row_cache:
        return _row_cache[key]
    path = SNAPSHOT / fname
    pf = pq.ParquetFile(path)
    batch_size = 4096
    batch_number = row_number // batch_size
    offset = row_number % batch_size
    for i, batch in enumerate(pf.iter_batches(
        columns=["act_id", "section_title", "text"], batch_size=batch_size
    )):
        if i == batch_number:
            row = batch.to_pylist()[offset]
            _row_cache[key] = row
            return row
    raise ValueError(f"row {row_number} not found in {fname}")


def context_around(text: str, needle: str, radius: int = 120) -> str:
    idx = text.find(needle)
    if idx == -1:
        # try a shortened prefix (terms can be long / punctuation-heavy)
        idx = text.find(needle[:40])
        if idx == -1:
            return "<TERM NOT FOUND VERBATIM IN SOURCE TEXT>"
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return text[start:end].replace("\n", "\\n")


def main() -> None:
    rows = [json.loads(l) for l in PURE_REMOVED.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Total pure-removed anchors: {len(rows)}\n")

    results = []
    for i, row in enumerate(rows, 1):
        term = row["term"]
        candidate = DefinitionCandidate(terms=(term,), definition_text=row["definition_text"], scope=row["scope"])
        filter_says_reject = _is_implausible_fallback_capture(candidate)

        src = get_row(row["source_file"], row["source_row"])
        text = src["text"] or ""
        ctx = context_around(text, term)

        result = {
            "i": i,
            "jurisdiction": row["jurisdiction"],
            "source_row_id": row["source_row_id"],
            "source_file": row["source_file"],
            "source_row": row["source_row"],
            "term": term,
            "filter_rejects": filter_says_reject,
            "context": ctx,
        }
        results.append(result)
        print(f"[{i}/64] {row['jurisdiction']} {row['source_row_id']} term={term!r}")
        print(f"    filter_rejects={filter_says_reject}")
        print(f"    ctx: {ctx[:300]}")
        print()

    n_reject = sum(1 for r in results if r["filter_rejects"])
    print(f"\nSUMMARY: {n_reject}/{len(results)} match the shipped filter's rejection rule")
    (HERE / "run" / "round2" / "removals_verified.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
