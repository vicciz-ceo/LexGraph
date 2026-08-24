"""Item 4 (sprint 2026-08-23-defs-debt-31) per-row ledger: for each of the
101 ceiling-tripped candidates measure_item4_fx7_remainder_census.py
found, determine whether it is NOW recovered (the term is captured by
the REAL, current pipeline with reasonable bounds via SOME path -- not
necessarily the ceiling-bypassing ones this census used) or still
genuinely absent, and classify the absent ones into the two named
families (no-next-quoted-term / citation-noise / other) from the real
row's own text shape.

"Recovered" here means: the term appears in `profile.extract_
definitions_from_section`'s own REAL (ceiling-respecting) output --
i.e. some OTHER mechanism (a hard-stop closing it before the ceiling,
Item 1's own trim making an unbounded candidate now bounded, etc.)
captures it today, independent of this census's own unbounded-ceiling
probe.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

import pyarrow.parquet as pq  # noqa: E402

import app.definition_links.rules.us_body_preamble  # noqa: F401,E402
from app.definition_links.normalize import strip_wikilinks  # noqa: E402
from app.definition_links.profiles import get_profile  # noqa: E402

SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
CENSUS_DIR = Path(__file__).resolve().parent / "item4_census_run"
OUT_PATH = Path(__file__).resolve().parent / "item4_ledger.jsonl"


def parquet_file_for(jurisdiction: str) -> str:
    code = jurisdiction.removeprefix("US-").lower()
    return "us_federal_statutes.parquet" if code == "fed" else f"us_{code}_statutes.parquet"


def load_targets() -> list[dict]:
    targets = []
    for path in sorted(CENSUS_DIR.glob("US-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    targets.append(json.loads(line))
    return targets


def classify_family(text: str, quote_end: int) -> str:
    # Bounded to the SAME idiom-lookahead scope _MEANS_IDIOM_GAP_RE/
    # _TIGHT_IDIOM_RE themselves use (200 chars) -- the question is
    # "does a normal idiom scan ever see another quote at all", not
    # "does the rest of the whole document have one somewhere" (which
    # for any real document is trivially always true).
    remainder = text[quote_end : quote_end + 200]
    if not re.search(r'["“”]', remainder):
        return "no-next-quoted-term"
    tail = text[quote_end : quote_end + 30]
    if re.match(r"\s*P\.?L\.?\s*\d{4}", tail) or "Pub. L." in text[quote_end : quote_end + 40]:
        return "citation-noise"
    return "other"


def main() -> None:
    targets = load_targets()
    print(f"{len(targets)} targets to adjudicate")

    by_file: dict[str, list[dict]] = {}
    for t in targets:
        by_file.setdefault(t["jurisdiction"], []).append(t)

    ledger: list[dict] = []
    for jurisdiction, rows in by_file.items():
        fname = parquet_file_for(jurisdiction)
        profile = get_profile(jurisdiction)
        act_ids = {r["act_id"] for r in rows}
        found_rows: dict[str, dict] = {}
        pf = pq.ParquetFile(SNAPSHOT / fname)
        for batch in pf.iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"]
        ):
            for row in batch.to_pylist():
                if row["act_id"] in act_ids:
                    found_rows[row["act_id"]] = row
            if len(found_rows) == len(act_ids):
                break

        for t in rows:
            row = found_rows.get(t["act_id"])
            if row is None:
                ledger.append({**t, "verdict": "ERROR", "reason": "row not found in re-fetch"})
                continue
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
            scope = profile.determine_scope(body)
            heading_was_derived = (derived is not None) or recognized_by_rule
            if b1_winner:
                candidates = profile.extract_definitions_from_section(
                    body, scope=scope, heading_was_derived=True,
                    raw_source=unescaped, b1_winner=True,
                )
            else:
                candidates = profile.extract_definitions_from_section(
                    body, scope=scope, heading_was_derived=heading_was_derived,
                )
            match = None
            for c in candidates:
                if t["term"] in c.terms:
                    match = c
                    break
            if match is not None:
                ledger.append(
                    {
                        **t,
                        "verdict": "RECOVERED",
                        "recovered_len": len(match.definition_text),
                        "recovered_tail": match.definition_text[-100:],
                    }
                )
                continue

            # Not recovered -- classify family from the real row text.
            quote_pattern = re.compile(r'["“]' + re.escape(t["term"][:40]))
            m = quote_pattern.search(body)
            if m is None:
                # term may have different casing/whitespace in body; fall back
                m = re.search(re.escape(t["term"][:20]), body, re.IGNORECASE)
            family = "unknown-term-not-relocatable"
            if m is not None:
                family = classify_family(body, m.end())
            ledger.append(
                {
                    **t,
                    "verdict": "UNRECOVERABLE",
                    "family": family,
                    "reason": (
                        "term absent from current real (ceiling-respecting) "
                        "extract_definitions_from_section output; census's own "
                        "unbounded-ceiling probe is the only path that finds it"
                    ),
                }
            )

    with OUT_PATH.open("w", encoding="utf-8") as handle:
        for row in ledger:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    recovered = sum(1 for r in ledger if r["verdict"] == "RECOVERED")
    unrecoverable = sum(1 for r in ledger if r["verdict"] == "UNRECOVERABLE")
    errors = sum(1 for r in ledger if r["verdict"] == "ERROR")
    print(f"RECOVERED: {recovered}, UNRECOVERABLE: {unrecoverable}, ERROR: {errors}")
    families: dict[str, int] = {}
    for r in ledger:
        if r["verdict"] == "UNRECOVERABLE":
            families[r["family"]] = families.get(r["family"], 0) + 1
    print("families:", families)


if __name__ == "__main__":
    main()
