"""Round-2 Task 2: fetch source context + shipped-filter check for the
100-item population-(c) sample, to support manual GENUINE/FALSE POSITIVE/
AMBIGUOUS classification against real source text.
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
SAMPLE = HERE / "run" / "round2" / "population_c_sample.jsonl"
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


def find_term_context(text: str, term: str, radius: int = 200) -> tuple[str, bool]:
    idx = text.find(term)
    found = True
    if idx == -1:
        idx = text.find(term[:30])
        found = False
        if idx == -1:
            return "<TERM NOT FOUND>", False
    start = max(0, idx - radius)
    end = min(len(text), idx + len(term) + radius)
    return text[start:end], found


def main() -> None:
    rows = [json.loads(l) for l in SAMPLE.read_text(encoding="utf-8").splitlines() if l.strip()]
    results = []
    for i, row in enumerate(rows, 1):
        term = row["term"]
        candidate = DefinitionCandidate(terms=(term,), definition_text=row["definition_text"], scope=row["scope"])
        filter_rejects = _is_implausible_fallback_capture(candidate)
        src = get_row(row["source_file"], row["source_row"])
        text = src["text"] or ""
        ctx, term_found_verbatim = find_term_context(text, term)
        def_start = row["definition_text"][:200]
        results.append({
            "i": i,
            "jurisdiction": row["jurisdiction"],
            "source_row_id": row["source_row_id"],
            "source_file": row["source_file"],
            "source_row": row["source_row"],
            "term": term,
            "def_len": len(row["definition_text"]),
            "def_preview": def_start,
            "filter_rejects": filter_rejects,
            "term_found_verbatim_in_source": term_found_verbatim,
            "source_context": ctx,
        })
    n_reject = sum(1 for r in results if r["filter_rejects"])
    print(f"Sample size: {len(results)}; shipped-filter would reject: {n_reject}")
    (HERE / "run" / "round2" / "population_c_sample_classified.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
