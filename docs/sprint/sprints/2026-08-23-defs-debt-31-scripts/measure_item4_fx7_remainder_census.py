"""Item 4 (sprint 2026-08-23-defs-debt-31) FX7-remainder census.

P-R11: no hand-authored expected-change ledger. The prior sprint's own
118-row FX7-ceiling-tripped population was never persisted anywhere in
the committed repo (its source artifacts were a deliberately-
uncommitted throwaway probe -- confirmed by direct research of
`docs/sprint/sprints/2026-08-20-defs-boundary-idioms-log.md` and
`-scripts/investigation.md`). This script LIVE-RE-DERIVES the same
population, on THIS worktree's current code, using the prior sprint's
own documented two-stage methodology: real-ceiling vs monkeypatched-
unbounded-ceiling comparison across the same 14 registered jurisdictions
(`_OTHER_JURISDICTIONS` + US-WA from `us_markers_inline_quote.py`), then
verifies each candidate against the REAL, full `ingest_us_statute_rows`
-> `run_definition_linking` pipeline.

Chunked per jurisdiction, resumable: writes `<jurisdiction>.jsonl` (one
row per ceiling-tripped candidate found) plus a running `summary.json`.
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
from app.definition_links.rules import us_markers_boundary  # noqa: E402

SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
OUT_DIR = Path(__file__).resolve().parent / "item4_census_run"

# The 14 jurisdictions us_markers_inline_quote.py registers -- the ONLY
# ones whose primary engine ever passes through close_entries's own
# MAX_CLEAN_DEFINITION_LENGTH ceiling (the FX7 ceiling itself).
JURISDICTIONS = [
    "VA", "FED", "UT", "TX", "SC", "AZ", "NJ", "MI", "ND", "NY", "OK", "NM", "NV", "WA",
]


def parquet_file_for(jurisdiction: str) -> str:
    code = jurisdiction.lower()
    return "us_federal_statutes.parquet" if code == "fed" else f"us_{code}_statutes.parquet"


def process_jurisdiction(jurisdiction: str) -> dict:
    jurisdiction_code = f"US-{jurisdiction}"
    profile = get_profile(jurisdiction_code)
    fname = parquet_file_for(jurisdiction)
    path = SNAPSHOT / fname

    total_rows = 0
    definitions_rows = 0
    ceiling_tripped_records: list[dict] = []

    for batch in pq.ParquetFile(path).iter_batches(
        columns=["act_id", "section_title", "text", "chapter", "section_number"],
        batch_size=4096,
    ):
        for row in batch.to_pylist():
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
            derived = None
            b1_winner = False
            if not recognized:
                derive_b1 = getattr(profile, "derive_body_preamble_match", None)
                if callable(derive_b1):
                    derived = derive_b1(
                        heading, body, raw_source=unescaped,
                        article_number=row["section_number"] or "", chapter=row["chapter"],
                    )
                    b1_winner = bool(getattr(derived, "b1_winner", False))
            if not recognized and derived is None:
                continue
            definitions_rows += 1
            scope = profile.determine_scope(body)
            heading_was_derived = (derived is not None) or recognized_by_rule

            # Stage A: REAL ceiling (current MAX_CLEAN_DEFINITION_LENGTH).
            if b1_winner:
                real_candidates = profile.extract_definitions_from_section(
                    body, scope=scope, heading_was_derived=True,
                    raw_source=unescaped, b1_winner=True,
                )
            else:
                real_candidates = profile.extract_definitions_from_section(
                    body, scope=scope, heading_was_derived=heading_was_derived,
                )
            real_terms = {t for c in real_candidates for t in c.terms}

            # Stage B: UNBOUNDED ceiling (monkeypatch, matching the prior
            # sprint's own documented methodology exactly).
            original_ceiling = us_markers_boundary.MAX_CLEAN_DEFINITION_LENGTH
            us_markers_boundary.MAX_CLEAN_DEFINITION_LENGTH = 10**9
            try:
                if b1_winner:
                    unbounded_candidates = profile.extract_definitions_from_section(
                        body, scope=scope, heading_was_derived=True,
                        raw_source=unescaped, b1_winner=True,
                    )
                else:
                    unbounded_candidates = profile.extract_definitions_from_section(
                        body, scope=scope, heading_was_derived=heading_was_derived,
                    )
            finally:
                us_markers_boundary.MAX_CLEAN_DEFINITION_LENGTH = original_ceiling
            unbounded_by_term = {t: c for c in unbounded_candidates for t in c.terms}

            missing_terms = set(unbounded_by_term) - real_terms
            for term in missing_terms:
                candidate = unbounded_by_term[term]
                ceiling_tripped_records.append(
                    {
                        "jurisdiction": jurisdiction_code,
                        "act_id": row["act_id"],
                        "term": term,
                        "unbounded_definition_text_len": len(candidate.definition_text),
                        "unbounded_definition_text_tail": candidate.definition_text[-200:],
                    }
                )

    out_path = OUT_DIR / f"{jurisdiction_code}.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for rec in ceiling_tripped_records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "jurisdiction": jurisdiction_code,
        "file": fname,
        "total_rows": total_rows,
        "definitions_rows": definitions_rows,
        "ceiling_tripped_count": len(ceiling_tripped_records),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUT_DIR / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}

    for jurisdiction in JURISDICTIONS:
        jurisdiction_code = f"US-{jurisdiction}"
        if jurisdiction_code in summary:
            print(f"SKIP {jurisdiction_code} (already done)")
            continue
        print(f"RUN {jurisdiction_code} ...")
        stats = process_jurisdiction(jurisdiction)
        summary[jurisdiction_code] = stats
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(f"  -> {stats}")


if __name__ == "__main__":
    main()
