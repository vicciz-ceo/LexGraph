"""Independent M-R118 current-vs-5753e11 production corpus measurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


EXPECTED_FILES = 53
EXPECTED_ROWS = 2_038_247
EXPECTED_MEMBERS = 193_827
EXPECTED_MEMBERS_HASH = "362b863878533a6dd8bb876e25b300bd88bd2fe5d34aedca180a2e690b6ae08d"


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


def key_record(row: dict) -> dict:
    return {"key": list(key(row))}


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


def member(path: Path, row_number: int, row: dict) -> dict:
    return {
        "source_file": path.name,
        "source_row": row_number,
        "source_row_id": str(row["act_id"] or f"{path.name}:{row_number}"),
    }


def capture(profile, body: str, raw: str, row: dict, *, current: bool) -> list[tuple[tuple[str, ...], object]]:
    heading = row["section_title"] or ""
    recognized = profile.is_definitions_heading(heading, body)
    derived = None if recognized else profile.derive_heading_from_body(heading, body)
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
            if derived is not None else []
        )
        section = profile.extract_definitions_from_section(
            body, scope=scope, heading_was_derived=derived is not None,
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
    strip_wikilinks, get_profile, registry, b1_rule, legacy_derive = load_production(args.source_root)
    selected = None
    if args.members:
        selected = {
            (record["source_file"], record["source_row"])
            for record in (json.loads(line) for line in args.members.read_text().splitlines() if line)
        }
    members: list[dict] = []
    records: list[dict] = []
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
                    if legacy_derive(row["section_title"] or "", body) is not None:
                        continue
                    winner = next(
                        (rule.derive_heading for rule in registry._body_preamble_rules
                         if registry._matches(rule.jurisdiction_codes, jurisdiction(path))
                         and rule.derive_heading(body) is not None),
                        None,
                    )
                    if winner is not b1_rule:
                        continue
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
    summary = {"mode": "current" if args.current else "baseline", "files": EXPECTED_FILES,
               "rows": EXPECTED_ROWS, "members": len(members) if args.current else len(selected),
               "members_sha256": membership_hash, "records": len(records), "records_sha256": records_hash}
    if args.current and (len(members) != EXPECTED_MEMBERS or membership_hash != EXPECTED_MEMBERS_HASH):
        raise RuntimeError(f"B1 membership drift: {summary}")
    (args.out / "summary.json").write_text(json.dumps(summary, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


def compare(args: argparse.Namespace) -> None:
    before = {key(row): row for row in (json.loads(line) for line in args.baseline.read_text().splitlines() if line)}
    after = {key(row): row for row in (json.loads(line) for line in args.current.read_text().splitlines() if line)}
    changed = [{"change": "removed", **before[item]} for item in before.keys() - after.keys()]
    changed += [{"change": "added", **after[item]} for item in after.keys() - before.keys()]
    changed.sort(key=lambda row: (row["change"], key(row)))
    args.out.mkdir(parents=True, exist_ok=True)
    changed_hash = write_jsonl(args.out / "changed.jsonl", changed)
    certified = {key(row) for row in (json.loads(line) for line in args.certified.read_text().splitlines() if line)}
    actual = {key(row) for row in changed}
    summary = {"changed": len(changed), "removed": sum(row["change"] == "removed" for row in changed),
               "added": sum(row["change"] == "added" for row in changed), "changed_sha256": changed_hash,
               "missing_certified": len(certified - actual), "extra_actual": len(actual - certified),
               "hi": sum(row["jurisdiction"] == "US-HI" for row in changed),
               "fed": sum(row["jurisdiction"] == "US-FED" for row in changed)}
    (args.out / "summary.json").write_text(json.dumps(summary, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    if summary["changed"] != 636 or summary["removed"] != 634 or summary["added"] != 2 or summary["missing_certified"] or summary["extra_actual"]:
        raise RuntimeError(f"M-R118 production delta mismatch: {summary}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--current", action="store_true")
    parser.add_argument("--members", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--certified", type=Path)
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    if args.compare:
        compare(args)
    else:
        if (args.current and args.members) or (not args.current and not args.members):
            parser.error("current run needs no --members; baseline run requires it")
        measure(args)


if __name__ == "__main__":
    main()
