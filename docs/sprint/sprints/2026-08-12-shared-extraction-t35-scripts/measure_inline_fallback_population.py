"""Sprint `2026-08-12-shared-extraction-t35`, Planner deliverable: the gate-3
blast-radius tool ("nothing else is lost. Corpus-wide, measured: no term
that is captured today may disappear" -- M-R64's own gate).

**What this measures.** `USC_T35_C4_S41`'s phantom `'SEC. 804. DEFINITION.'`
term and its missing genuine `'Director'` term BOTH originate in ONE function,
`_extract_inline_quoted_definitions` (`backend/app/definition_links/
us_profile.py:995`) -- specifically `_QUOTE_TERM_RE` (line 924), which pairs
the FIRST `"`/`"` character after a candidate term-start with the NEXT such
character, with no awareness that a multi-paragraph quoted excerpt re-opens
`"` at the start of EVERY paragraph (only the last one closes) and no support
for a definiendum delimited by single `'...'` quotes nested inside such a
block. A fix scoped to that one function/regex can only ever change output
for rows where that function contributes >=1 candidate to `created_definitions`
TODAY -- this script finds exactly that population, corpus-wide, mirroring
`pipeline.py`'s own Stage-2 dispatch (this worktree's HEAD, `pipeline.py`
lines 246-347) rather than reimplementing it, the same discipline
`measure_shapes_corpus_wide.py` (sprint 2026-08-04-defs-us-preamble)
established for exactly this kind of measurement.

**Two-stage cost control (Planner timing finding, this sprint).** The real
per-row gate (`is_definitions_heading` -> `derive_body_preamble_match`,
which walks every registered `BodyPreambleRule` including B1 -> `determine_
scope` -> `extract_definitions_from_section`) costs ~32ms/row measured live
on 4,000 real `us_federal_statutes.parquet` rows (128.8s/4,000). Corpus-wide
(~2.05M rows across all 105 files, per prior sprints' own measurement) that
is dozens of hours unoptimized -- not tractable as a single pass. Calling
`_extract_inline_quoted_definitions` DIRECTLY (no gating) on every row's body
is ~85x cheaper (~0.38ms/row, 1.5s/4,000 measured live, same sample) and is a
provable SUPERSET of the true population (the gated call can only ever
subtract rows the cheap call already flagged, never add new ones -- the real
pipeline calls the SAME function with a SUBSET of the inputs this direct call
uses). Stage 1 (cheap, full corpus) narrows ~2.05M rows to the much smaller
set where the ungated function alone returns something; Stage 2 (the real,
expensive gate) runs ONLY on that narrowed set to confirm which of them the
real pipeline actually reaches and persists from.

**Usage**
    backend/.venv/bin/python measure_inline_fallback_population.py \
        --out /path/to/before.jsonl [--files us_federal_statutes.parquet ...]

Emits one JSON object per row where the real, gated pipeline path persists
>=1 term sourced from `_extract_inline_quoted_definitions`:
`{"file": ..., "code": ..., "act_id": ..., "terms": [...]}`. Run once BEFORE
the Developer's fix and once AFTER (same flags), then diff with
`diff_before_after.py` in this directory -- ANY term present in `before` and
absent from `after` for the same `(code, act_id)` is a Gate-3 regression by
definition (M-R64), independent of whether the row's OTHER terms changed.

No test imports this file or reads the parquet snapshot (program rule) --
this is a measurement script, not a test.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

BACKEND = "/Users/nerya/LexGraph-wt/shared-extraction/backend"
sys.path.insert(0, BACKEND)

import pyarrow.parquet as pq  # noqa: E402

import app.definition_links.us_profile as usp  # noqa: E402
from app.definition_links.us_profile import USProfile  # noqa: E402

SNAPSHOT = (
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)

_orig_inline = usp._extract_inline_quoted_definitions
_call_log: list[list] = []


def _spy(text, *, scope):
    """Records `_extract_inline_quoted_definitions`'s real output without
    changing it (pure pass-through) -- lets Stage 2 attribute a row's
    candidates to THIS function specifically, since `extract_definitions_
    from_section` itself does not tag provenance on its returned
    `DefinitionCandidate`s."""
    result = _orig_inline(text, scope=scope)
    _call_log.append(result)
    return result


usp._extract_inline_quoted_definitions = _spy


def _code_for_filename(fname: str) -> str:
    base = os.path.basename(fname)
    stem = base[len("us_"):].split("_")[0]
    return "US-FED" if stem == "federal" else f"US-{stem.upper()}"


def _stage1_prefilter(path: str) -> list[dict]:
    """Cheap superset pass: every row where the UNGATED function alone
    returns >=1 candidate. No `USProfile` dispatch, no registered-rule
    walk -- just `normalize_for_parsing` + one direct call."""
    candidates = []
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(
        batch_size=4000, columns=["act_id", "section_title", "text", "chapter", "section_number"]
    ):
        cols = batch.to_pydict()
        for i in range(len(cols["act_id"])):
            raw_text = cols["text"][i] or ""
            if not raw_text:
                continue
            body = usp.normalize_for_parsing(raw_text)
            if _orig_inline(body, scope="law-wide"):
                candidates.append(
                    {
                        "act_id": cols["act_id"][i],
                        "heading": cols["section_title"][i] or "",
                        "raw_text": raw_text,
                        "chapter": cols["chapter"][i] if "chapter" in cols else None,
                        "number": cols["section_number"][i] if "section_number" in cols else cols["act_id"][i],
                    }
                )
    return candidates


def _stage2_real_gate(row: dict, profile: USProfile) -> list[str] | None:
    """The REAL pipeline dispatch (mirrors `pipeline.py` lines 246-347,
    Stage-2 heading recognition through `extract_definitions_from_section`)
    -- returns the terms sourced from `_extract_inline_quoted_definitions`
    for this row if the real gate reaches and uses it, else `None`."""
    body = usp.normalize_for_parsing(row["raw_text"])
    is_definitions_section = profile.is_definitions_heading(row["heading"], body)
    used_body_derived_heading = False
    b1_winner = False
    if not is_definitions_section:
        try:
            derived = profile.derive_body_preamble_match(
                row["heading"], body, raw_source=row["raw_text"],
                article_number=str(row["number"]), chapter=row["chapter"],
            )
        except Exception:
            derived = None
        if derived is not None and profile.is_definitions_heading(derived, body):
            is_definitions_section = True
            used_body_derived_heading = True
            b1_winner = bool(getattr(derived, "b1_winner", False))
    if not is_definitions_section:
        return None

    recognized_by_registered_rule = False
    if not used_body_derived_heading:
        rule_only = getattr(profile, "heading_recognized_only_by_rule", None)
        if callable(rule_only):
            recognized_by_registered_rule = bool(rule_only(row["heading"], body))
    heading_was_derived = used_body_derived_heading or recognized_by_registered_rule
    if not heading_was_derived:
        return None

    scope = profile.determine_scope(body)
    _call_log.clear()
    try:
        if b1_winner:
            profile.extract_definitions_from_section(
                body, scope=scope, heading_was_derived=True, raw_source=row["raw_text"], b1_winner=True,
            )
        else:
            profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=True)
    except Exception:
        return None

    terms = [t for cands in _call_log for c in cands for t in c.terms]
    return terms or None


def scan_file(path: str, profile_cache: dict, out_fh) -> dict:
    code = _code_for_filename(path)
    profile = profile_cache.setdefault(code, USProfile(code=code))

    t0 = time.time()
    stage1 = _stage1_prefilter(path)
    t1 = time.time()

    written = 0
    for row in stage1:
        terms = _stage2_real_gate(row, profile)
        if terms:
            out_fh.write(
                json.dumps(
                    {"file": os.path.basename(path), "code": code, "act_id": row["act_id"], "terms": terms}
                )
                + "\n"
            )
            written += 1
    t2 = time.time()
    return {
        "code": code,
        "stage1_candidates": len(stage1),
        "written": written,
        "stage1_s": round(t1 - t0, 1),
        "stage2_s": round(t2 - t1, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output JSONL path")
    ap.add_argument("--files", nargs="*", default=None, help="parquet basenames to scan (default: all 105)")
    args = ap.parse_args()

    all_files = sorted(glob.glob(os.path.join(SNAPSHOT, "*.parquet")))
    if args.files:
        wanted = set(args.files)
        files = [f for f in all_files if os.path.basename(f) in wanted]
    else:
        files = all_files
    print(f"scanning {len(files)} file(s)", flush=True)

    profile_cache: dict = {}
    grand_written = 0
    with open(args.out, "w", encoding="utf-8") as out_fh:
        for idx, path in enumerate(files, 1):
            stats = scan_file(path, profile_cache, out_fh)
            grand_written += stats["written"]
            print(
                f"[{idx}/{len(files)}] {os.path.basename(path)} code={stats['code']} "
                f"stage1_candidates={stats['stage1_candidates']} written={stats['written']} "
                f"(stage1={stats['stage1_s']}s stage2={stats['stage2_s']}s)",
                flush=True,
            )
    print(f"=== done: {grand_written} rows written to {args.out} ===", flush=True)


if __name__ == "__main__":
    main()
