"""Independent M-R121 current-vs-5753e11 production corpus measurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


EXPECTED_FILES = 53
EXPECTED_ROWS = 2_038_247
EXPECTED_MEMBERS = 193_830
EXPECTED_MEMBERS_HASH = "851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a"
EXPECTED_CHANGED = 556
EXPECTED_REMOVED = 552
EXPECTED_ADDED = 4
EXPECTED_CHANGED_HASH = "17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a"
EXPECTED_BASELINE_HASH = "f065d8ee838effaba250ea13fb9c234904b3a63985893f0a921d856bc396b3f8"


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def key(row: dict) -> tuple[str, str, int, str, str, str]:
    return (
        row["jurisdiction"], row["source_file"], row["source_row"], row["term"],
        row["definition_text"], row["scope"],
    )


def key_record(row: dict) -> dict:
    return {"key": list(key(row))}


def changed_key(row: dict) -> tuple[str, str, str, int, str, str, str, str]:
    return (
        row["change"], row["jurisdiction"], row["source_file"], row["source_row"],
        row["source_row_id"], row["term"], row["definition_text"], row["scope"],
    )


def ledger_sort_key(row: dict) -> tuple[str, str, str, str, str, str]:
    """Match ``qa_g7_common.tuple_key`` plus the change direction."""
    return (
        row["jurisdiction"], row["source_file"], str(row["source_row"]), row["term"],
        row["definition_text"] + "\0" + row["scope"], row["change"],
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


def member(path: Path, row_number: int, row: dict) -> dict:
    return {
        "source_file": path.name,
        "source_row": row_number,
        "source_row_id": str(row["act_id"] or f"{path.name}:{row_number}"),
    }


def registered_b1_winner(*, legacy_derive, registry, b1_rule, jurisdiction_code: str, heading: str, parser_body: str) -> bool:
    """Measure the live first winner on the normalized, stripped parser body."""
    if legacy_derive(heading, parser_body) is not None:
        return False
    winner = next(
        (
            rule.derive_heading
            for rule in registry._body_preamble_rules
            if registry._matches(rule.jurisdiction_codes, jurisdiction_code)
            and rule.derive_heading(parser_body) is not None
        ),
        None,
    )
    return winner is b1_rule


def capture(profile, body: str, raw: str, row: dict, *, current: bool) -> list[tuple[tuple[str, ...], object]]:
    heading = row["section_title"] or ""
    recognized = profile.is_definitions_heading(heading, body)
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
                    if not registered_b1_winner(
                        legacy_derive=legacy_derive,
                        registry=registry,
                        b1_rule=b1_rule,
                        jurisdiction_code=jurisdiction(path),
                        heading=row["section_title"] or "",
                        parser_body=body,
                    ):
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
    baseline_hash = file_sha256(args.baseline)
    if baseline_hash != EXPECTED_BASELINE_HASH:
        raise RuntimeError(f"baseline hash drift: {baseline_hash}")
    before = {key(row): row for row in (json.loads(line) for line in args.baseline.read_text().splitlines() if line)}
    after = {key(row): row for row in (json.loads(line) for line in args.current_records.read_text().splitlines() if line)}
    changed = [{"change": "removed", **before[item]} for item in before.keys() - after.keys()]
    changed += [{"change": "added", **after[item]} for item in after.keys() - before.keys()]
    changed.sort(key=ledger_sort_key)
    args.out.mkdir(parents=True, exist_ok=True)
    changed_hash = write_jsonl(args.out / "changed.jsonl", changed)
    certified_rows = [
        json.loads(line) for line in args.certified.read_text().splitlines() if line
    ]
    certified = {changed_key(row) for row in certified_rows}
    actual = {changed_key(row) for row in changed}
    certified_digest = hashlib.sha256()
    for row in sorted(certified_rows, key=ledger_sort_key):
        certified_digest.update(canonical(row) + b"\n")
    certified_hash = certified_digest.hexdigest()
    expected_removed = sum(row["change"] == "removed" for row in certified_rows)
    expected_added = sum(row["change"] == "added" for row in certified_rows)
    if (
        len(certified_rows) != EXPECTED_CHANGED
        or expected_removed != EXPECTED_REMOVED
        or expected_added != EXPECTED_ADDED
        or certified_hash != EXPECTED_CHANGED_HASH
    ):
        raise RuntimeError(
            "M-R121 certificate drift: "
            f"count={len(certified_rows)} removed={expected_removed} added={expected_added} "
            f"hash={certified_hash}"
        )
    summary = {"changed": len(changed), "removed": sum(row["change"] == "removed" for row in changed),
               "added": sum(row["change"] == "added" for row in changed), "changed_sha256": changed_hash,
               "certified_sha256": certified_hash,
               "missing_certified": len(certified - actual), "extra_actual": len(actual - certified),
               "hi": sum(row["jurisdiction"] == "US-HI" for row in changed),
               "fed": sum(row["jurisdiction"] == "US-FED" for row in changed)}
    (args.out / "summary.json").write_text(json.dumps(summary, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    if (
        summary["changed"] != EXPECTED_CHANGED
        or summary["removed"] != EXPECTED_REMOVED
        or summary["added"] != EXPECTED_ADDED
        or summary["changed_sha256"] != summary["certified_sha256"]
        or summary["missing_certified"]
        or summary["extra_actual"]
    ):
        raise RuntimeError(f"M-R121 production delta mismatch: {summary}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--current", action="store_true")
    parser.add_argument("--current-records", type=Path)
    parser.add_argument("--members", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--certified", type=Path)
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    if args.compare:
        required = {
            "--baseline": args.baseline,
            "--current-records": args.current_records,
            "--certified": args.certified,
        }
        missing = [flag for flag, value in required.items() if value is None]
        if missing:
            parser.error(f"--compare requires {', '.join(missing)}")
        compare(args)
    else:
        if (args.current and args.members) or (not args.current and not args.members):
            parser.error("current run needs no --members; baseline run requires it")
        measure(args)


if __name__ == "__main__":
    main()
