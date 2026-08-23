"""Item 1 (sprint 2026-08-23-defs-debt-31) population measurement.

Gate 1: "Every population the trailing-stop change can reach is
enumerated and measured, not just the +27,568 wave (standing single-
letter lesson)." This script runs the REAL, current `USProfile.
extract_definitions_from_section` over every row of the named target
populations -- the 9 no-newline jurisdictions (NH/SC/PR/NY/UT/OH/IL/WA/
NJ) plus US-FED (furlough's own jurisdiction) -- and measures the trim's
actual reach by instrumenting `_trim_fallback_candidate_bleed` in place
(monkeypatched to record before/after `definition_text` for every call),
rather than requiring a separate baseline checkout: this measures the
SAME code path production uses, with the trim's own before/after delta
captured directly, not re-derived.

Raw-vs-ingest trap (known trap, this sprint's contract): NY's raw
parquet `text` is escaped-`\\n` by design; unescaped here exactly as
`ingest_us_statute_rows` does (`text.replace("\\\\n", "\\n")`) before
extraction, matching post-ingest production text, never measured raw.

Chunked per file, resumable: writes one `<jurisdiction>.jsonl` (per-
candidate trim record) plus a running `summary.json` after each file;
already-completed files are skipped on re-run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

import pyarrow.parquet as pq  # noqa: E402

import app.definition_links.rules.us_body_preamble  # noqa: F401,E402
from app.definition_links.normalize import strip_wikilinks  # noqa: E402
from app.definition_links.profiles import get_profile  # noqa: E402
from app.definition_links import us_profile  # noqa: E402

SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
OUT_DIR = Path(__file__).resolve().parent / "item1_population_run"

TARGET_FILES = [
    "us_nh_statutes.parquet",
    "us_sc_statutes.parquet",
    "us_pr_statutes.parquet",
    "us_ny_statutes.parquet",
    "us_ut_statutes.parquet",
    "us_oh_statutes.parquet",
    "us_il_statutes.parquet",
    "us_wa_statutes.parquet",
    "us_nj_statutes.parquet",
    "us_federal_statutes.parquet",
]


def jurisdiction_for(fname: str) -> str:
    code = fname.removeprefix("us_").removesuffix("_statutes.parquet")
    return "US-FED" if code == "federal" else f"US-{code.upper()}"


# --- instrumentation: wrap the real trim fns to record before/after ------

_records: list[dict] = []
_current_row_ctx: dict = {}

_orig_trim = us_profile._trim_fallback_candidate_bleed


def _instrumented_trim(text: str, candidate) -> None:
    before = candidate.definition_text
    _orig_trim(text, candidate)
    after = candidate.definition_text
    if after != before:
        _records.append(
            {
                **_current_row_ctx,
                "term": candidate.terms,
                "before_len": len(before),
                "after_len": len(after),
                "before_tail": before[-160:],
                "after_tail": after[-160:],
                "term_dropped": not after.strip(),
            }
        )


us_profile._trim_fallback_candidate_bleed = _instrumented_trim


def process_file(path: Path) -> dict:
    jurisdiction_code = jurisdiction_for(path.name)
    profile = get_profile(jurisdiction_code)
    global _records
    _records = []

    total_rows = 0
    total_candidates = 0
    no_newline_rows = 0

    out_path = OUT_DIR / f"{jurisdiction_code}.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for batch_number, batch in enumerate(
            pq.ParquetFile(path).iter_batches(
                columns=["act_id", "section_title", "text", "chapter", "section_number"],
                batch_size=4096,
            )
        ):
            for offset, row in enumerate(batch.to_pylist()):
                row_number = batch_number * 4096 + offset
                total_rows += 1
                raw = row["text"] or ""
                # M14/I8 (ingest_us_statutes.py): unescape literal `\n`
                # before this text is treated as post-ingest quote_text --
                # matches `ingest_us_statute_rows`, never measured raw.
                unescaped = raw.replace("\\n", "\n")
                if "\n" not in unescaped:
                    no_newline_rows += 1
                body, _hints = strip_wikilinks(profile.normalize_for_parsing(unescaped))
                heading = row["section_title"] or ""
                recognized = profile.is_definitions_heading(heading, body)
                rule_only = getattr(profile, "heading_recognized_only_by_rule", None)
                recognized_by_rule = bool(
                    recognized and callable(rule_only) and rule_only(heading, body)
                )
                derived = None
                b1_winner = False
                if not recognized:
                    derive_b1 = getattr(profile, "derive_body_preamble_match", None)
                    if callable(derive_b1):
                        derived = derive_b1(
                            heading,
                            body,
                            raw_source=unescaped,
                            article_number=row["section_number"] or "",
                            chapter=row["chapter"],
                        )
                        b1_winner = bool(getattr(derived, "b1_winner", False))
                if not recognized and derived is None:
                    continue
                scope = profile.determine_scope(body)
                heading_was_derived = (derived is not None) or recognized_by_rule
                _current_row_ctx.clear()
                _current_row_ctx.update(
                    {
                        "jurisdiction": jurisdiction_code,
                        "source_file": path.name,
                        "source_row": row_number,
                        "act_id": row["act_id"],
                    }
                )
                if b1_winner:
                    candidates = profile.extract_definitions_from_section(
                        body,
                        scope=scope,
                        heading_was_derived=True,
                        raw_source=unescaped,
                        b1_winner=True,
                    )
                else:
                    candidates = profile.extract_definitions_from_section(
                        body, scope=scope, heading_was_derived=heading_was_derived
                    )
                total_candidates += len(candidates)
            # flush per-batch to keep memory bounded
            for rec in _records:
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _records.clear()

    return {
        "jurisdiction": jurisdiction_code,
        "file": path.name,
        "total_rows": total_rows,
        "no_newline_rows": no_newline_rows,
        "total_candidates_seen": total_candidates,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUT_DIR / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}

    for fname in TARGET_FILES:
        jurisdiction_code = jurisdiction_for(fname)
        if jurisdiction_code in summary:
            print(f"SKIP {jurisdiction_code} (already done)")
            continue
        path = SNAPSHOT / fname
        print(f"RUN {jurisdiction_code} ({fname}) ...")
        stats = process_file(path)
        trim_records_path = OUT_DIR / f"{jurisdiction_code}.jsonl"
        trimmed_count = sum(1 for _ in trim_records_path.open(encoding="utf-8"))
        stats["trimmed_count"] = trimmed_count
        summary[jurisdiction_code] = stats
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(f"  -> {stats}")


if __name__ == "__main__":
    main()
