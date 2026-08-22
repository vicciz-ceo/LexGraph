"""Round-2 Task 1, precise mechanism classification for ALL 27,568
pure-added anchors. Calls TWO real, unmodified production entry points per
row:

  primary_terms  = {t for c in profile.extract_definitions_from_section(
                        body, scope=scope, heading_was_derived=False)
                    for t in c.terms}
  fallback_terms = {t for c in _extract_inline_quoted_definitions(body, scope=scope)
                    for t in c.terms}

`heading_was_derived=False` skips BOTH of the class method's own
`if heading_was_derived:` blocks (the Item-2 merge AND the B1-preamble
block) -- reading `USProfile.extract_definitions_from_section` (backend/
app/definition_links/us_profile.py ~2568-2650) confirms the primary
block-building loop itself does not otherwise depend on
`heading_was_derived`. So this is exactly "candidates" as they stand right
before the merge step would run in the real call with
`heading_was_derived=True` -- not a re-implementation, a direct call to the
real function with the flag that isolates the pre-merge state.

Classification per anchor:
  - term in primary_terms  -> mechanism "primary"  (Item 1 / baseline; the
    merge is a no-op for this term even if it also happens to appear in the
    fallback function's own output, since `_merge_fallback_candidates`
    skips any fallback candidate colliding with a primary term)
  - term in fallback_terms (and not primary) -> mechanism "fallback" (the
    term ONLY exists in the current output because Item 2's merge admitted
    it)
  - neither -> mechanism "other" (B1-preamble-derived, or unexplained --
    needs individual inspection)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend"))

import pyarrow.parquet as pq  # noqa: E402

from app.definition_links.normalize import strip_wikilinks  # noqa: E402
from app.definition_links.profiles import get_profile  # noqa: E402
from app.definition_links.us_profile import _extract_inline_quoted_definitions  # noqa: E402

HERE = Path(__file__).resolve().parent
PURE_ADDED = HERE / "run" / "round2" / "pure_added.jsonl"
OUT = HERE / "run" / "round2" / "pure_added_mechanism_precise.jsonl"
SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)


def jurisdiction_code(fname: str) -> str:
    code = fname.removeprefix("us_").removesuffix("_statutes.parquet")
    return "US-FED" if code == "federal" else f"US-{code.upper()}"


def main() -> None:
    rows = [json.loads(l) for l in PURE_ADDED.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_file: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_file[r["source_file"]].append(r)

    results = []
    for fi, (fname, file_rows) in enumerate(sorted(by_file.items()), 1):
        by_row_number: dict[int, list[dict]] = defaultdict(list)
        for r in file_rows:
            by_row_number[r["source_row"]].append(r)
        wanted = set(by_row_number.keys())

        profile = get_profile(jurisdiction_code(fname))
        path = SNAPSHOT / fname
        pf = pq.ParquetFile(path)
        found = 0
        for batch_number, batch in enumerate(pf.iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=4096
        )):
            if found >= len(wanted):
                break
            for offset, row in enumerate(batch.to_pylist()):
                row_number = batch_number * 4096 + offset
                if row_number not in by_row_number:
                    continue
                found += 1
                raw = row["text"] or ""
                body, _ = strip_wikilinks(profile.normalize_for_parsing(raw))
                scope = profile.determine_scope(body)

                primary_candidates = profile.extract_definitions_from_section(
                    body, scope=scope, heading_was_derived=False,
                )
                primary_terms = {t for c in primary_candidates for t in c.terms}
                fallback_candidates = _extract_inline_quoted_definitions(body, scope=scope)
                fallback_terms = {t for c in fallback_candidates for t in c.terms}

                for r in by_row_number[row_number]:
                    if r["term"] in primary_terms:
                        mechanism = "primary"
                    elif r["term"] in fallback_terms:
                        mechanism = "fallback"
                    else:
                        mechanism = "other"
                    results.append({
                        "jurisdiction": r["jurisdiction"], "source_file": r["source_file"],
                        "source_row": r["source_row"], "source_row_id": r["source_row_id"],
                        "term": r["term"], "mechanism": mechanism,
                    })
        print(f"[{fi}/{len(by_file)}] {fname}: {len(wanted)} rows processed", file=sys.stderr)

    counts = defaultdict(int)
    for r in results:
        counts[r["mechanism"]] += 1
    print(f"TOTAL: {len(results)} anchors -> {dict(counts)}")
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
