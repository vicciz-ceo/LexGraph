"""Runtime-only M-R109 persisted-tuple measures for two structural B1 proposals."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from qa_g7_common import (  # noqa: E402
    EXPECTED_FILE_COUNT,
    EXPECTED_ROW_COUNT,
    SNAPSHOT_ID,
    capture_row,
    jurisdiction_for,
    tuple_key,
    validate_corpus,
    write_json,
    write_jsonl,
)

# Statutory units, not source-row values.  The full census found each form in
# real B1 candidates; prose continuations such as manner/disclosure are not
# admitted.  Plural/dotted forms normalize through the trailing word boundary.
_UNIT_WORDS = frozenset({
    "section", "chapter", "article", "part", "title", "subtitle", "subchapter",
    "subsection", "division", "subdivision", "paragraph", "subparagraph", "clause",
    "subclause", "item", "subitem", "subpart", "subarticle", "code", "act", "compact",
    "constitution", "rule", "order", "provision",
})


def _in_this_unit(match_text: str) -> bool:
    """Whether an existing B1 trigger's `In this` continuation is statutory."""
    prefix = match_text.casefold()
    if not prefix.startswith("in this"):
        return True
    rest = prefix[len("in this") :].strip().split(maxsplit=1)
    if not rest:
        return False
    unit = rest[0].rstrip(".,:;()")
    return unit in _UNIT_WORDS


def _b1_match(body: str):
    """Return (heading, quote-start) using A's grammar and B's exact branch."""
    from app.definition_links.rules.us_body_preamble_b1 import (
        _B1_DIRECT_QUOTE_MEANS_RE,
        _B1_LOOKAHEAD,
        _B1_TRIGGER_RE,
        _b1_colon_list_branch,
        _b1_quote_means_branch,
    )

    direct = _B1_DIRECT_QUOTE_MEANS_RE.search(body)
    if direct is not None:
        return "Definitions", None
    for trigger in _B1_TRIGGER_RE.finditer(body):
        if not _in_this_unit(trigger.group()):
            continue
        after = body[trigger.end() : trigger.end() + _B1_LOOKAHEAD]
        if _b1_colon_list_branch(after):
            return "Definitions", None
        if _b1_quote_means_branch(after):
            # B begins at the defining quote, never at the generic trigger.
            quote = None
            if trigger.group().casefold().startswith("in this"):
                quote = trigger.end() + len(after) - len(after.lstrip(" ,\t\r\n"))
            return "Definitions", quote
    return None, None


def _potentially_changed(body: str, mode: str) -> bool:
    """Cheap prefilter; the later live-profile check remains authoritative."""
    from app.definition_links.rules.us_body_preamble_b1 import (
        _B1_LOOKAHEAD,
        _B1_TRIGGER_RE,
        _b1_colon_list_branch,
        _b1_quote_means_branch,
    )

    for trigger in _B1_TRIGGER_RE.finditer(body):
        after = body[trigger.end() : trigger.end() + _B1_LOOKAHEAD]
        colon = _b1_colon_list_branch(after)
        quote = _b1_quote_means_branch(after)
        if not (colon or quote):
            continue
        legal = _in_this_unit(trigger.group())
        if mode == "a" and not legal:
            return True
        is_in_this = trigger.group().casefold().startswith("in this")
        if mode == "b" and is_in_this and legal and quote:
            return True
        if mode == "union" and ((not legal) or (is_in_this and legal and quote)):
            return True
    return False


def _b1_wins(profile, heading: str, body: str) -> bool:
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import derive_heading_from_body

    if derive_heading_from_body(heading, body) is not None:
        return False
    for rule in registry.body_preamble_rules_for(profile.code):
        if rule.derive_heading(body) is not None:
            return rule.derive_heading is _b1_trigger_colon_or_quote_means
    return False


def _records_for_file(args):
    source_file, mode = args
    from app.definition_links.profiles import get_profile
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import USProfile, derive_heading_from_body

    path = Path(source_file)
    jurisdiction = jurisdiction_for(path)
    profile = get_profile(jurisdiction)
    original_derive = USProfile.derive_heading_from_body
    original_extract = USProfile.extract_definitions_from_section
    starts: dict[str, int] = {}

    def derive(self, heading: str, body: str):
        baseline = derive_heading_from_body(heading, body)
        if baseline is not None:
            return baseline
        starts.pop(body, None)
        for rule in registry.body_preamble_rules_for(self.code):
            if rule.derive_heading is _b1_trigger_colon_or_quote_means:
                heading_result, quote_start = _b1_match(body)
                if heading_result is not None and mode in {"b", "union"} and quote_start is not None:
                    starts[body] = quote_start
                if heading_result is not None:
                    return heading_result
                if mode == "b":
                    # B changes extraction only. Its legal-unit condition
                    # gates the new start metadata, never B1 recognition.
                    original = rule.derive_heading(body)
                    if original is not None:
                        return original
                continue
            result = rule.derive_heading(body)
            if result is not None:
                return result
        return None

    def extract(self, text: str, *, scope: str, heading_was_derived: bool = False):
        start = starts.get(text)
        if heading_was_derived and mode in {"b", "union"} and start is not None:
            return original_extract(self, text[start:], scope=scope, heading_was_derived=True)
        return original_extract(self, text, scope=scope, heading_was_derived=heading_was_derived)

    before: list[dict] = []
    after: list[dict] = []
    USProfile.derive_heading_from_body = derive
    USProfile.extract_definitions_from_section = extract
    try:
        source_row = 0
        for batch in pq.ParquetFile(path).iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=4096
        ):
            for row in batch.to_pylist():
                body = row["text"] or ""
                heading = row["section_title"] or ""
                # Proposals only alter rows for which current B1 wins.
                if not _potentially_changed(body, mode):
                    source_row += 1
                    continue
                USProfile.derive_heading_from_body = original_derive
                winner = _b1_wins(profile, heading, body)
                USProfile.derive_heading_from_body = derive
                if winner:
                    USProfile.derive_heading_from_body = original_derive
                    USProfile.extract_definitions_from_section = original_extract
                    before.extend(item.record() for item in capture_row(
                        jurisdiction=jurisdiction, source_file=path.name, source_row=source_row, row=row, after=True
                    ))
                    USProfile.derive_heading_from_body = derive
                    USProfile.extract_definitions_from_section = extract
                    after.extend(item.record() for item in capture_row(
                        jurisdiction=jurisdiction, source_file=path.name, source_row=source_row, row=row, after=True
                    ))
                starts.pop(body, None)
                source_row += 1
    finally:
        USProfile.derive_heading_from_body = original_derive
        USProfile.extract_definitions_from_section = original_extract

    before_by_key = {tuple_key(record): record for record in before}
    after_by_key = {tuple_key(record): record for record in after}
    changed = []
    for change, records in (("removed", before_by_key), ("added", after_by_key)):
        keys = records.keys() - (after_by_key if change == "removed" else before_by_key).keys()
        for key in keys:
            record = records[key]
            # HI/FED are source-held. Every other delta is exactly caused by
            # the proposal's structural gate; no identity/term allowlist.
            if record["jurisdiction"] == "US-HI":
                classification = "source_held_hi"
            elif record["jurisdiction"] == "US-FED":
                classification = "source_held_fed"
            elif mode == "a":
                classification = "a_nonstatutory_in_this_rejected"
            elif mode == "b":
                classification = "b_legal_unit_quote_local"
            else:
                classification = "union_structural_b1"
            changed.append({"change": change, "classification": classification, **record})
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--mode", choices=("a", "b", "union"), required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    args = parser.parse_args()
    files, rows, _ = validate_corpus(args.snapshot)
    assert len(files) == EXPECTED_FILE_COUNT and rows == EXPECTED_ROW_COUNT
    if not 0 <= args.shard_index < args.shard_count:
        raise ValueError("shard index must be within shard count")
    selected_files = files[args.shard_index :: args.shard_count]
    with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("fork")) as pool:
        changed = [record for result in pool.map(_records_for_file, ((str(path), args.mode) for path in selected_files)) for record in result]
    changed.sort(key=lambda record: (tuple_key(record), record["change"]))
    totals = Counter(record["classification"] for record in changed)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": "lexgraph.mr109.structural-b1.v1",
        "snapshot_id": SNAPSHOT_ID,
        "mode": args.mode,
        "files": len(files),
        "shard": [args.shard_index, args.shard_count],
        "selected_file_count": len(selected_files),
        "rows": rows,
        "changed_key_count": len(changed),
        "classification_totals": dict(sorted(totals.items())),
        "changed_key_ledger_sha256": write_jsonl(args.out / f"{args.mode}_changed_keys.jsonl", changed),
    }
    write_json(args.out / f"{args.mode}_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
