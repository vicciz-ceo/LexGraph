"""Create a source-span adjudication ledger for changed-key evidence."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[3]
sys.path[:0] = [str(ROOT), str(SCRIPTS), str(ROOT / "backend")]
from qa_g7_common import canonical_bytes, sha256_value, write_json, write_jsonl


def _load_measure() -> object:
    path = SCRIPTS / "measure_mr110_candidate_stream.py"
    spec = importlib.util.spec_from_file_location("mr113_measure", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _norm(value: str) -> str:
    return " ".join(value.replace("“", '"').replace("”", '"').replace("\u2002", " ").split())


def _shape(relation: str) -> str:
    lower = relation.casefold()
    if "not include" in lower or "exclude" in lower:
        return "negative"
    if "meaning" in lower or "definition" in lower:
        return "forward"
    if lower.startswith(("is ", "are ", "shall be ")):
        return "copular"
    if lower.startswith(("refers to", "refer to", "shall refer")):
        return "reference"
    return "direct"


def _direct_quote_match(body: str, term: str, definition_text: str):
    """Map a baseline-normalized quoted definition when no group emitted it."""
    needle = term.strip().rstrip(".,;:")
    if not needle:
        return None
    pattern = re.compile(r'["“]\s*' + re.escape(needle) + r'[.,;:]*\s*["”]\s*', re.I)
    for quote in pattern.finditer(body):
        tail = body[quote.end() : quote.end() + 1600]
        for boundary in (tail.find(";"), tail.find(".")):
            if boundary < 0:
                continue
            payload = tail[: boundary + 1].strip()
            normalized_payload = _norm(payload).rstrip(".")
            normalized_definition = _norm(definition_text).rstrip(".")
            normalized_without_idiom = re.sub(
                r"^(?:means?|shall mean|includes?|shall include)\s*", "", normalized_payload, flags=re.I
            )
            if normalized_payload == normalized_definition or normalized_without_idiom == normalized_definition:
                return quote.end(), quote.end() + boundary + 1, payload
    return None


def _source_rows(path: Path, wanted: set[str]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for batch in pq.ParquetFile(path).iter_batches(columns=["act_id", "text"], batch_size=4096):
        for row in batch.to_pylist():
            if str(row["act_id"]) in wanted:
                rows[str(row["act_id"])] = row["text"] or ""
    if rows.keys() != wanted:
        raise RuntimeError(f"missing source rows: {sorted(wanted - rows.keys())[:5]}")
    return rows


def _source_rows_from_snapshot(snapshot: Path, changed: list[dict]) -> dict[str, str]:
    by_file: dict[str, set[str]] = {}
    for row in changed:
        by_file.setdefault(row["source_file"], set()).add(row["source_row_id"])
    rows: dict[str, str] = {}
    for filename, wanted in sorted(by_file.items()):
        rows.update(_source_rows(snapshot / filename, wanted))
    return rows


def _quoted_term_span(body: str, term: str):
    needle = term.strip().rstrip(".,;:")
    if not needle:
        return None
    match = re.search(r'["“]\s*' + re.escape(needle) + r'[.,;:]*\s*["”]', body, re.I)
    return None if match is None else (match.start(), match.end())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="de_additions")
    args = parser.parse_args()
    measure = _load_measure()
    changed = [json.loads(line) for line in args.changed.read_text().splitlines() if line]
    if (args.source is None) == (args.snapshot is None):
        parser.error("provide exactly one of --source or --snapshot")
    source = (
        _source_rows(args.source, {row["source_row_id"] for row in changed})
        if args.source is not None
        else _source_rows_from_snapshot(args.snapshot, changed)
    )
    ledger = []
    additions = [row for row in changed if row["change"] == "added"]
    removals = [row for row in changed if row["change"] == "removed"]
    for row in additions:
        body = source[row["source_row_id"]]
        matches = []
        for group in measure.discover_clause_groups(body):
            terms = tuple(term for term, _, _ in group.term_spans)
            if row["term"] not in terms:
                continue
            for candidate in measure._group_candidates(body, (group,), row["scope"]):
                if candidate.terms != (row["term"],) or _norm(candidate.definition_text) != _norm(row["definition_text"]):
                    continue
                start, end = group.relationship_span
                matches.append((start, end, terms, body[start:end].strip(), candidate.definition_text))
        if not matches:
            direct = _direct_quote_match(body, row["term"], row["definition_text"])
            if direct is None:
                raise RuntimeError(f"UNCLASSIFIED {row['source_row_id']} {row['term']!r}")
            start, end, relation = direct
            matches = [(start, end, (row["term"],), relation, row["definition_text"])]
        # Repeated equivalent groups are not ambiguous: each span is emitted
        # and the first source-order span is the canonical governing span.
        matches.sort()
        canonical = matches[0]
        # Repeated source editions can differ only in a stripped defining
        # idiom (``means`` / ``shall mean``).  Candidate-normalized text, not
        # that harmless spelling variation, determines equivalence.
        if any(_norm(item[4]) != _norm(canonical[4]) for item in matches[1:]):
            raise RuntimeError(f"AMBIGUOUS {row['source_row_id']} {row['term']!r}")
        start, end, terms, relation, _ = canonical
        ledger.append(
            {
                "change": "added",
                "adjudication": "genuine_missing_term",
                "alias_index": terms.index(row["term"]),
                "definition_text": row["definition_text"],
                "governing_clause": relation,
                "governing_span": [start, end],
                "group_term_count": len(terms),
                "group_terms": list(terms),
                "normalization": "curly_quotes+en_spaces+whitespace",
                "repeated_equivalent_spans": [[item[0], item[1]] for item in matches],
                "shape": _shape(relation),
                "source_row_id": row["source_row_id"],
                "term": row["term"],
            }
        )
    for row in removals:
        body = source[row["source_row_id"]]
        quote_span = _quoted_term_span(body, row["term"])
        if quote_span is None:
            raise RuntimeError(f"UNCLASSIFIED REMOVAL {row['source_row_id']} {row['term']!r}")
        if row["term_local_substantive"] or measure.has_substantive_definition_text(row["definition_text"]):
            raise RuntimeError(f"GENUINE LOSS {row['source_row_id']} {row['term']!r}")
        start, end = quote_span
        ledger.append(
            {
                "change": "removed",
                "adjudication": "malformed_non_substantive_tuple",
                "definition_text": row["definition_text"],
                "governing_clause": body[start : min(len(body), end + 120)].strip(),
                "governing_span": [start, end],
                "normalization": "curly_quotes+en_spaces+whitespace",
                "source_row_id": row["source_row_id"],
                "term": row["term"],
            }
        )
    ledger.sort(key=lambda row: (row["source_row_id"], row["governing_span"], row.get("alias_index", -1), row["term"]))
    family_counts = Counter(
        (row.get("shape", row["adjudication"]), row.get("group_term_count", 0)) for row in ledger
    )
    summary = {
        "schema": "lexgraph.mr113.changed-key-adjudication.v2",
        "changed_ledger_sha256": sha256_value(changed),
        "source_file": args.source.name if args.source is not None else "all snapshot source files",
        "source_row_count": len({row["source_row_id"] for row in ledger}),
        "addition_count": len(additions),
        "removal_count": len(removals),
        "false_count": 0,
        "ambiguous_count": 0,
        "unclassified_count": 0,
        "genuine_loss_count": 0,
        "family_counts": {f"{shape}:{size}": count for (shape, size), count in sorted(family_counts.items())},
        "ledger_sha256": write_jsonl(args.out / f"{args.label}_adjudication.jsonl", ledger),
    }
    summary["summary_sha256"] = sha256_value({key: value for key, value in summary.items() if key != "summary_sha256"})
    write_json(args.out / f"{args.label}_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
