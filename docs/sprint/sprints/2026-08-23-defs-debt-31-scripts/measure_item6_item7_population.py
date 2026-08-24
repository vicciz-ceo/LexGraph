"""QA-fail cycle 1 (sprint 2026-08-23-defs-debt-31) population re-
measurement for Items 6 (bleed-trim over-trim fix) and 7 (single-letter
adjacency fix). Run together per the brief's own sequencing note: "a fix
to one can shift the other's population."

Gate 1 (item 6): "Every population the trailing-stop change can reach is
enumerated and measured, not just the +27,568 wave." Gate 2 (item 7):
"enumerate all single-letter-term candidates corpus-wide, adjudicate each
admit/reject -- full population, not the wave alone."

Runs the REAL, current `USProfile.extract_definitions_from_section` over
EVERY row of all 53 registered US jurisdictions' own `*_statutes.parquet`
file (the same "all-53" population `run_gate5_certification.sh` uses,
listed directly from the snapshot directory rather than hand-typed, so
this can never silently drift from the certification's own scope) --
broader than the prior Item 1 pass's own 10-jurisdiction population
(9 no-newline states + FED), since neither the letter-paren/digit-dot
list shape (item 6) nor a single-letter defined term (item 7) is
structurally confined to those 9 states.

Two independent instrumentation points, both monkeypatched in place (same
technique as `measure_item1_bleed_trim_population.py`, so this measures
the SAME code path production uses, not a re-derived approximation):

  1. `us_profile._trim_fallback_candidate_bleed` (item 6) -- records every
     before/after `definition_text` change, PLUS whether the new `run_
     suppressed_starts` set (this pass's own addition) had any members at
     all reachable within this call's own `[start, end)` span, as a cheap
     signal for "did run-suppression plausibly change this outcome."
  2. `us_profile._single_letter_term_lacks_adjacent_idiom` (item 7) --
     records every call (term, gap distance, coordinated-clause match,
     verdict) -- the exact population gate 2 asks to be enumerated.

Raw-vs-ingest trap (known trap, this sprint's contract): NY's raw parquet
`text` is escaped-`\\n` by design; unescaped here exactly as `ingest_us_
statute_rows` does, matching post-ingest production text, never raw.

Chunked per file, resumable: writes `<jurisdiction>.trim.jsonl` and
`<jurisdiction>.letter.jsonl` plus a running `summary.json` after each
file; already-completed files are skipped on re-run.
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
OUT_DIR = Path(__file__).resolve().parent / "item6_item7_population_run"

TARGET_FILES = sorted(p.name for p in SNAPSHOT.glob("*_statutes.parquet"))
assert len(TARGET_FILES) == 53, f"expected all-53 statutes population, got {len(TARGET_FILES)}"


def jurisdiction_for(fname: str) -> str:
    code = fname.removeprefix("us_").removesuffix("_statutes.parquet")
    return "US-FED" if code == "federal" else f"US-{code.upper()}"


# --- instrumentation ---------------------------------------------------

_trim_records: list[dict] = []
_letter_records: list[dict] = []
_current_row_ctx: dict = {}

_orig_trim = us_profile._trim_fallback_candidate_bleed
_orig_single_letter = us_profile._single_letter_term_lacks_adjacent_idiom


def _instrumented_trim(text, candidate, hard_stops, run_suppressed_starts) -> None:
    before = candidate.definition_text
    start = text.find(before)
    span_had_suppressed_marker = False
    if start != -1 and text.find(before, start + 1) == -1:
        end = start + len(before)
        span_had_suppressed_marker = any(start <= p < end for p in run_suppressed_starts)
    _orig_trim(text, candidate, hard_stops, run_suppressed_starts)
    after = candidate.definition_text
    if after != before:
        _trim_records.append(
            {
                **_current_row_ctx,
                "term": candidate.terms,
                "before_len": len(before),
                "after_len": len(after),
                "before_tail": before[-160:],
                "after_tail": after[-160:],
                "term_dropped": not after.strip(),
                "span_had_suppressed_marker": span_had_suppressed_marker,
            }
        )


def _instrumented_single_letter(term, means_match):
    verdict = _orig_single_letter(term, means_match)
    if len(term) == 1:
        idiom_word = us_profile._IDIOM_WORD_ONLY_RE.search(means_match.group(0))
        gap_distance = idiom_word.start() if idiom_word is not None else None
        gap_prefix = means_match.group(0)[:gap_distance] if gap_distance is not None else ""
        coordinated = bool(
            us_profile._COORDINATED_CLAUSE_BEFORE_IDIOM_RE.search(gap_prefix)
        )
        _letter_records.append(
            {
                **_current_row_ctx,
                "term": term,
                "gap_distance": gap_distance,
                "gap_prefix": gap_prefix[-60:],
                "idiom_matched": means_match.group(0)[gap_distance:gap_distance + 20]
                if gap_distance is not None
                else None,
                "coordinated_clause_signal": coordinated,
                "over_threshold": bool(gap_distance is not None and gap_distance > 20),
                "rejected": bool(verdict),
            }
        )
    return verdict


us_profile._trim_fallback_candidate_bleed = _instrumented_trim
us_profile._single_letter_term_lacks_adjacent_idiom = _instrumented_single_letter


def process_file(path: Path) -> dict:
    jurisdiction_code = jurisdiction_for(path.name)
    profile = get_profile(jurisdiction_code)
    global _trim_records, _letter_records
    _trim_records = []
    _letter_records = []

    total_rows = 0
    total_candidates = 0

    trim_out = OUT_DIR / f"{jurisdiction_code}.trim.jsonl"
    letter_out = OUT_DIR / f"{jurisdiction_code}.letter.jsonl"
    with trim_out.open("w", encoding="utf-8") as trim_handle, letter_out.open(
        "w", encoding="utf-8"
    ) as letter_handle:
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
                unescaped = raw.replace("\\n", "\n")
                body, _hints = strip_wikilinks(profile.normalize_for_parsing(unescaped))
                heading = row["section_title"] or ""
                recognized = profile.is_definitions_heading(heading, body)
                rule_only = getattr(profile, "heading_recognized_only_by_rule", None)
                recognized_by_rule = bool(
                    recognized and callable(rule_only) and rule_only(heading, body)
                )
                _current_row_ctx.clear()
                _current_row_ctx.update(
                    {
                        "jurisdiction": jurisdiction_code,
                        "source_file": path.name,
                        "source_row": row_number,
                        "act_id": row["act_id"],
                    }
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
            for rec in _trim_records:
                trim_handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _trim_records.clear()
            for rec in _letter_records:
                letter_handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
            _letter_records.clear()

    return {
        "jurisdiction": jurisdiction_code,
        "file": path.name,
        "total_rows": total_rows,
        "total_candidates_seen": total_candidates,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUT_DIR / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}

    for fname in TARGET_FILES:
        jurisdiction_code = jurisdiction_for(fname)
        if jurisdiction_code in summary:
            print(f"SKIP {jurisdiction_code} (already done)", flush=True)
            continue
        path = SNAPSHOT / fname
        print(f"RUN {jurisdiction_code} ({fname}) ...", flush=True)
        stats = process_file(path)
        trim_path = OUT_DIR / f"{jurisdiction_code}.trim.jsonl"
        letter_path = OUT_DIR / f"{jurisdiction_code}.letter.jsonl"
        stats["trimmed_count"] = sum(1 for _ in trim_path.open(encoding="utf-8"))
        stats["single_letter_candidate_count"] = sum(1 for _ in letter_path.open(encoding="utf-8"))
        summary[jurisdiction_code] = stats
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(f"  -> {stats}", flush=True)

    print("ALL_53_DONE", flush=True)


if __name__ == "__main__":
    main()
