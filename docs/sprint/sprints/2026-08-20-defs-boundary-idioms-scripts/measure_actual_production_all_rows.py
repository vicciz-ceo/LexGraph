"""Gate-2 measurement for sprint 2026-08-20-defs-boundary-idioms (issue #27).

Corrected copy of docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/
mr118/qa/measure_actual_production.py per this sprint's log doc §7: the
original's `--current` branch bundles two things into one flag -- (a)
matching production's unconditional `recognized_by_registered_rule`
computation (kept here, the real trap) and (b) restricting the whole
population to B1-winner rows only (`registered_b1_winner(...)`), which
would exclude this item's entire affected population (STATE_NJ_T27_C1A_
S1A-3.1 "Department" is recognized by BASELINE `is_definitions_heading`,
not body-derived, and neither is any other row this item's family-3
widening touches). This copy drops that population restriction: every row
in the corpus is measured, `capture(..., current=True)` is unchanged. The
prior sprint's hard-coded EXPECTED_MEMBERS/EXPECTED_MEMBERS_HASH and
EXPECTED_CHANGED* / EXPECTED_BASELINE_HASH certificate constants are B1-
sprint-specific and do not apply to this item's population -- dropped
rather than carried forward unchecked (P-R11: run first, then adjudicate
the real delta; no hand-authored ledger). `compare()`'s certified-ledger
enforcement is likewise unused here -- diff_gate2.py in this sprint's
scripts dir does the actual comparison instead.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


EXPECTED_FILES = 53
EXPECTED_ROWS = 2_038_247


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_jsonl(path: Path, rows: list[dict]) -> str:
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            line = canonical(row)
            handle.write(line.decode() + "\n")
            digest.update(line + b"\n")
    return digest.hexdigest()


def key(row: dict) -> tuple[str, str, int, str, str, str]:
    return (
        row["jurisdiction"], row["source_file"], row["source_row"], row["term"],
        row["definition_text"], row["scope"],
    )


def files(snapshot: Path) -> list[Path]:
    paths = sorted(snapshot.glob("us_*_statutes.parquet"))
    if len(paths) != EXPECTED_FILES:
        raise RuntimeError(f"expected {EXPECTED_FILES} statute files, got {len(paths)}")
    total = sum(pq.ParquetFile(path).metadata.num_rows for path in paths)
    if total != EXPECTED_ROWS:
        raise RuntimeError(f"expected {EXPECTED_ROWS} rows, got {total}")
    return paths


def jurisdiction(path: Path) -> str:
    code = path.name.removeprefix("us_").removesuffix("_statutes.parquet")
    return "US-FED" if code == "federal" else f"US-{code.upper()}"


def load_production(root: Path):
    sys.path.insert(0, str(root / "backend"))
    # Registration is import-time in production; mirror pipeline startup.
    import app.definition_links.rules.us_body_preamble  # noqa: F401
    from app.definition_links.normalize import strip_wikilinks
    from app.definition_links.profiles import get_profile
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import derive_heading_from_body

    return strip_wikilinks, get_profile, registry, _b1_trigger_colon_or_quote_means, derive_heading_from_body


def prototype_context(enabled: bool):
    """Apply the current planner prototype without modifying production."""
    if not enabled:
        return contextlib.nullcontext()
    scripts = Path(__file__).resolve().parents[2]
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from measure_mr110_candidate_stream import default_preserve_runtime_patch

    return default_preserve_runtime_patch()


def member(path: Path, row_number: int, row: dict) -> dict:
    return {
        "source_file": path.name,
        "source_row": row_number,
        "source_row_id": str(row["act_id"] or f"{path.name}:{row_number}"),
    }


def capture(profile, body: str, raw: str, row: dict, *, current: bool) -> list[tuple[tuple[str, ...], object]]:
    heading = row["section_title"] or ""
    recognized = profile.is_definitions_heading(heading, body)
    # Mirror pipeline.py: a heading recognized ONLY by a registered HeadingRule
    # keeps the inline-quoted fallback reachable. Without this the harness
    # measures a different program than the one that ships -- it reported a
    # 3,311-record net LOSS on the merged headings tree purely because it
    # modelled the pre-fix behaviour.
    rule_only = getattr(profile, "heading_recognized_only_by_rule", None)
    recognized_by_registered_rule = bool(
        current and recognized and callable(rule_only) and rule_only(heading, body)
    )
    derived = None
    if not recognized:
        derive_b1 = getattr(profile, "derive_body_preamble_match", None)
        if current and callable(derive_b1):
            derived = derive_b1(
                heading,
                body,
                raw_source=raw,
                article_number=row["section_number"] or "",
                chapter=row["chapter"],
            )
        else:
            derived = profile.derive_heading_from_body(heading, body)
    if not recognized and derived is None:
        return []
    b1_winner = bool(getattr(derived, "b1_winner", False))
    scope = profile.determine_scope(body)
    if current and b1_winner:
        local = profile.extract_local_scope_definitions(
            body, article_number=row["section_number"] or "", chapter=row["chapter"], raw_source=raw, b1_winner=True,
        )
        section = profile.extract_definitions_from_section(
            body, scope=scope, heading_was_derived=True, raw_source=raw, b1_winner=True,
        )
    else:
        local = (
            profile.extract_local_scope_definitions(
                body, article_number=row["section_number"] or "", chapter=row["chapter"],
            )
            if (derived is not None or recognized_by_registered_rule) else []
        )
        section = profile.extract_definitions_from_section(
            body, scope=scope,
            heading_was_derived=(derived is not None) or recognized_by_registered_rule,
        )
    seen: set[tuple[str, ...]] = set()
    ordered: list[tuple[tuple[str, ...], object]] = []
    for candidate in [*local, *section]:
        candidate_key = tuple(sorted(candidate.terms))
        if candidate_key not in seen:
            seen.add(candidate_key)
            ordered.append((candidate_key, candidate))
    return ordered


def measure(args: argparse.Namespace) -> None:
    strip_wikilinks, get_profile, _registry, _b1_rule, _legacy_derive = load_production(args.source_root)
    selected = None
    if args.members:
        selected = {
            (record["source_file"], record["source_row"])
            for record in (json.loads(line) for line in args.members.read_text().splitlines() if line)
        }
    members: list[dict] = []
    records: list[dict] = []
    with prototype_context(args.prototype):
        for path in files(args.snapshot):
            profile = get_profile(jurisdiction(path))
            for batch_number, batch in enumerate(pq.ParquetFile(path).iter_batches(
                columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=4096
            )):
                for offset, row in enumerate(batch.to_pylist()):
                    row_number = batch_number * 4096 + offset
                    raw = row["text"] or ""
                    body, _ = strip_wikilinks(profile.normalize_for_parsing(raw))
                    if args.current:
                        # No registered_b1_winner population restriction here
                        # (see module docstring) -- every row is a member.
                        members.append(member(path, row_number, row))
                    elif (path.name, row_number) not in selected:
                        continue
                    for _, candidate in capture(profile, body, raw, row, current=args.current):
                        for term in candidate.terms:
                            records.append({
                                "jurisdiction": jurisdiction(path), "source_file": path.name,
                                "source_row": row_number, "source_row_id": str(row["act_id"] or f"{path.name}:{row_number}"),
                                "term": term, "definition_text": candidate.definition_text, "scope": candidate.scope,
                            })
    members.sort(key=lambda item: (item["source_file"], item["source_row"]))
    records.sort(key=key)
    args.out.mkdir(parents=True, exist_ok=True)
    membership_hash = write_jsonl(args.out / "members.jsonl", members) if args.current else None
    records_hash = write_jsonl(args.out / "records.jsonl", records)
    mode = "prototype" if args.prototype else ("current" if args.current else "baseline")
    summary = {"mode": mode, "files": EXPECTED_FILES,
               "rows": EXPECTED_ROWS, "members": len(members) if args.current else len(selected),
               "members_sha256": membership_hash, "records": len(records), "records_sha256": records_hash}
    (args.out / "summary.json").write_text(json.dumps(summary, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--current", action="store_true")
    parser.add_argument("--prototype", action="store_true")
    parser.add_argument("--members", type=Path)
    args = parser.parse_args()
    if args.prototype and not args.current:
        parser.error("--prototype requires --current")
    if (args.current and args.members) or (not args.current and not args.members):
        parser.error("current run needs no --members; baseline run requires it")
    measure(args)


if __name__ == "__main__":
    main()
