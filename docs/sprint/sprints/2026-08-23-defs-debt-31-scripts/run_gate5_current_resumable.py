"""Item 8 (QA-fail cycle 1 re-certification) -- resumable driver for the
CURRENT side of `measure_actual_production.py`.

Why this exists: this session's own machine has slept mid-run three times
in a row, killing the plain `measure_actual_production.py --current`
invocation `run_gate5_certification.sh` uses -- that script accumulates
`members`/`records` for ALL 53 files in memory and writes to disk only
once, at the very end, so every interruption loses 100% of elapsed work
(one completed run, pre-interruption, took ~50 minutes). This wrapper
calls the EXACT SAME functions (`capture`, `key`, `member`, `registered_
b1_winner`, `jurisdiction`, `write_jsonl`, `load_production`, imported
from that script, never reimplemented -- P-R16: the harness must call/
track the real pipeline, and re-deriving its logic here would risk
silently measuring something else) but checkpoints after EVERY file,
resumable exactly like `measure_item1_bleed_trim_population.py`/
`measure_item6_item7_population.py` already are in this same scripts
directory.

Output: once every file is done, concatenates the per-file checkpoints in
the SAME sorted order `measure()` itself uses and writes `gate5-run/
current/{members,records,summary}.json[l]` byte-identical to what the
original monolithic run would have produced (verified: same `key()`/
`write_jsonl` functions, same sort keys, same B1-membership drift check).
Every other script in this directory (`adjudicate_gate5_delta_v2.py`,
`sample_and_verify_v2.py`, `crosscheck_item4_v2.py`) reads that same
final path and needs no changes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

MR118_QA_DIR = REPO_ROOT / "docs" / "sprint" / "sprints" / "2026-08-04-defs-us-preamble-scripts" / "mr118" / "qa"
sys.path.insert(0, str(MR118_QA_DIR))

import measure_actual_production as mp  # noqa: E402

SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
SOURCE_ROOT = REPO_ROOT
OUT_DIR = Path(__file__).resolve().parent / "gate5-run" / "current"
CHECKPOINT_DIR = OUT_DIR / "_checkpoints"


def process_one_file(path: Path, strip_wikilinks, get_profile, registry, b1_rule, legacy_derive) -> dict:
    """Mirrors `measure()`'s own inner loop for ONE file, `--current` mode
    only (this driver's only use case). Returns {"members": [...],
    "records": [...]} -- identical shape to what `measure()` accumulates
    per-file before its own final sort+write."""
    import pyarrow.parquet as pq

    profile = get_profile(mp.jurisdiction(path))
    members: list[dict] = []
    records: list[dict] = []
    for batch_number, batch in enumerate(
        pq.ParquetFile(path).iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=4096
        )
    ):
        for offset, row in enumerate(batch.to_pylist()):
            row_number = batch_number * 4096 + offset
            raw = row["text"] or ""
            body, _ = strip_wikilinks(profile.normalize_for_parsing(raw))
            if not mp.registered_b1_winner(
                legacy_derive=legacy_derive,
                registry=registry,
                b1_rule=b1_rule,
                jurisdiction_code=mp.jurisdiction(path),
                heading=row["section_title"] or "",
                parser_body=body,
            ):
                continue
            members.append(mp.member(path, row_number, row))
            for _, candidate in mp.capture(profile, body, raw, row, current=True):
                for term in candidate.terms:
                    records.append(
                        {
                            "jurisdiction": mp.jurisdiction(path),
                            "source_file": path.name,
                            "source_row": row_number,
                            "source_row_id": str(row["act_id"] or f"{path.name}:{row_number}"),
                            "term": term,
                            "definition_text": candidate.definition_text,
                            "scope": candidate.scope,
                        }
                    )
    return {"members": members, "records": records}


def main() -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    strip_wikilinks, get_profile, registry, b1_rule, legacy_derive = mp.load_production(SOURCE_ROOT)
    paths = mp.files(SNAPSHOT)  # raises if not exactly the certified 53-file/2,038,247-row population

    for path in paths:
        code = mp.jurisdiction(path)
        ckpt = CHECKPOINT_DIR / f"{code}.json"
        if ckpt.exists():
            print(f"SKIP {code} (checkpointed)", flush=True)
            continue
        print(f"RUN {code} ({path.name}) ...", flush=True)
        result = process_one_file(path, strip_wikilinks, get_profile, registry, b1_rule, legacy_derive)
        ckpt.write_text(json.dumps(result, ensure_ascii=False))
        print(f"  -> members={len(result['members'])} records={len(result['records'])}", flush=True)

    done = {p.stem for p in CHECKPOINT_DIR.glob("*.json")}
    expected = {mp.jurisdiction(p) for p in paths}
    if done != expected:
        print(f"NOT ALL FILES DONE YET: missing {sorted(expected - done)}", flush=True)
        return

    print("all 53 files checkpointed -- assembling final output...", flush=True)
    members: list[dict] = []
    records: list[dict] = []
    for path in paths:
        result = json.loads((CHECKPOINT_DIR / f"{mp.jurisdiction(path)}.json").read_text())
        members.extend(result["members"])
        records.extend(result["records"])

    members.sort(key=lambda item: (item["source_file"], item["source_row"]))
    records.sort(key=mp.key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    membership_hash = mp.write_jsonl(OUT_DIR / "members.jsonl", members)
    records_hash = mp.write_jsonl(OUT_DIR / "records.jsonl", records)
    summary = {
        "mode": "current",
        "files": mp.EXPECTED_FILES,
        "rows": mp.EXPECTED_ROWS,
        "members": len(members),
        "members_sha256": membership_hash,
        "records": len(records),
        "records_sha256": records_hash,
    }
    if len(members) != mp.EXPECTED_MEMBERS or membership_hash != mp.EXPECTED_MEMBERS_HASH:
        raise RuntimeError(f"B1 membership drift: {summary}")
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True), flush=True)
    print("GATE5_CURRENT_RESUMABLE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
