#!/usr/bin/env python3
"""Measure the source-bound G3-HEAL candidate-order proposal.

This is a read-only corpus instrument.  It replays the production ingest
normalization and Stage-0/Stage-2 definitions dispatch, but labels the
otherwise-unlabelled baseline and entry-splitter candidate streams.  It then
compares current ``baseline -> rules`` first-wins order with the proposed
``priority rules -> baseline -> ordinary rules`` order.

Only ``us_markers_inline_quote`` is treated as a proposed priority rule.  The
script does not infer quality from length or containment: it measures the
effect of that explicit source decision.  Term-clause candidates are retained
in the replay after all block candidates, matching ``USProfile`` dispatch.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import pyarrow.parquet as pq

from app.definition_links.normalize import strip_wikilinks
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry
from app.definition_links.us_profile import _leading_quote_candidate, _split_into_numbered_blocks


DEFAULT_CORPUS = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
_PRIORITY_MODULE = "app.definition_links.rules.us_markers_inline_quote"
_PRIORITY_CODES = frozenset({"US-WA"})


def _jurisdiction(path: Path) -> str:
    stem = path.stem.removeprefix("us_").removesuffix("_statutes")
    return "US-FED" if stem == "federal" else f"US-{stem.upper()}"


def _stream_for_section(text: str, scope: str, code: str):
    """Mirror USProfile dispatch while recording the producing stream."""
    baseline_blocks = _split_into_numbered_blocks(text)
    preferred_blocks: list[str] = []
    ordinary_blocks: list[str] = []
    for rule in registry.entry_splitter_rules_for(code):
        blocks = rule.split(text)
        if rule.split.__module__ == _PRIORITY_MODULE and code in _PRIORITY_CODES:
            preferred_blocks.extend(blocks)
        else:
            ordinary_blocks.extend(blocks)

    current = []
    proposed = []
    # The proposed production seam is deliberately narrower than source
    # precedence in general: priority is possible only when baseline made
    # ONE unbounded block for the section.  This is the newline-collapse
    # shape.  A normally split baseline section remains baseline-first,
    # including every AR G8 safety row.
    proposed_block_streams = (
        (("priority_rule", preferred_blocks), ("baseline", baseline_blocks))
        if len(baseline_blocks) == 1
        else (("baseline", baseline_blocks), ("priority_rule", preferred_blocks))
    )
    for source, blocks, into in (
        ("baseline", baseline_blocks, current),
        ("priority_rule", preferred_blocks, current),
        ("ordinary_rule", ordinary_blocks, current),
    ):
        for block_index, block in enumerate(blocks):
            candidate = _leading_quote_candidate(block, scope=scope)
            if candidate is not None:
                into.append((candidate, source, block_index, len(blocks)))
    for source, blocks in (*proposed_block_streams, ("ordinary_rule", ordinary_blocks)):
        for block_index, block in enumerate(blocks):
            candidate = _leading_quote_candidate(block, scope=scope)
            if candidate is not None:
                proposed.append((candidate, source, block_index, len(blocks)))

    # Match production's post-block TermClauseRule phase.  These rules have
    # no proposed priority and therefore remain after all block streams.
    for block in baseline_blocks + preferred_blocks + ordinary_blocks:
        for rule in registry.term_clause_rules_for(code):
            if rule.parse_scoped is not None:
                parsed = rule.parse_scoped(block, registry.TermClauseContext(scope=scope))
            else:
                parsed = rule.parse(block)
            for candidate in parsed:
                current.append((candidate, "term_clause", None, None))
                proposed.append((candidate, "term_clause", None, None))
    return current, proposed


def _candidates_for_row(row: dict, profile, code: str):
    """Replay pipeline's input transformation and definition dispatch."""
    ingested = row["text"].replace("\\n", "\n")
    body, _ = strip_wikilinks(profile.normalize_for_parsing(ingested))
    heading = row.get("section_title") or ""
    article_number = str(row.get("section_number"))
    chapter = row.get("chapter") or ""
    is_definitions = profile.is_definitions_heading(heading, body)
    derived = False
    if not is_definitions:
        derived_heading = profile.derive_heading_from_body(heading, body)
        if derived_heading is not None and profile.is_definitions_heading(derived_heading, body):
            is_definitions = True
            derived = True
    if not is_definitions:
        candidates = profile.extract_local_scope_definitions(
            body, article_number=article_number, chapter=chapter
        )
        return [(candidate, "local_scope", None, None) for candidate in candidates], None

    scope = profile.determine_scope(body)
    current, proposed = _stream_for_section(body, scope, code)
    if not current and derived:
        fallback = profile.extract_definitions_from_section(
            body, scope=scope, heading_was_derived=True
        )
        return [(candidate, "derived_fallback", None, None) for candidate in fallback], None

    def stamp(stream):
        output = []
        for candidate, source, block_index, block_count in stream:
            for assignment in profile.determine_scope_assignments(
                body, scope=scope, article_number=article_number, chapter=chapter
            ):
                stamped = replace(candidate, scope=assignment.kind)
                if assignment.kind == "chapter":
                    stamped.source_chapter = assignment.value
                elif assignment.kind == "local":
                    stamped.source_article_number = assignment.value
                else:
                    stamped.scope_value = assignment.value
                output.append((stamped, source, block_index, block_count))
        return output

    return stamp(current), stamp(proposed)


def _first_by_key(stream):
    winners = {}
    for index, item in enumerate(stream):
        candidate = item[0]
        winners.setdefault(tuple(sorted(candidate.terms)), (index, item))
    return winners


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--jurisdiction",
        action="append",
        help="repeatable US code filter (e.g. US-WA); omitted replays all 53 files",
    )
    args = parser.parse_args()
    started = time.monotonic()
    files = sorted(args.corpus.glob("us_*_statutes.parquet"))
    assert len(files) == 53, f"expected 53 statute files, got {len(files)}"
    if args.jurisdiction:
        requested = set(args.jurisdiction)
        files = [path for path in files if _jurisdiction(path) in requested]
        assert {_jurisdiction(path) for path in files} == requested

    counts = Counter()
    changed = []
    by_jurisdiction = defaultdict(Counter)
    for path in files:
        code = _jurisdiction(path)
        profile = get_profile(code)
        for batch in pq.ParquetFile(path).iter_batches(
            batch_size=5_000,
            columns=["act_id", "section_number", "section_title", "chapter", "text"],
        ):
            for row in batch.to_pylist():
                counts["rows"] += 1
                current, proposed = _candidates_for_row(row, profile, code)
                if proposed is None:
                    continue
                counts["section_candidates"] += len(current)
                current_winners = _first_by_key(current)
                proposed_winners = _first_by_key(proposed)
                for key, (current_index, current_item) in current_winners.items():
                    proposed_index, proposed_item = proposed_winners[key]
                    current_candidate, current_source, current_block, current_block_count = current_item
                    proposed_candidate, proposed_source, proposed_block, proposed_block_count = proposed_item
                    if current_candidate.definition_text == proposed_candidate.definition_text:
                        continue
                    counts["changed_persisted_keys"] += 1
                    by_jurisdiction[code]["changed_persisted_keys"] += 1
                    changed.append(
                        {
                            "file": path.name,
                            "jurisdiction": code,
                            "act_id": row["act_id"],
                            "terms": list(key),
                            "current_index": current_index,
                            "current_source": current_source,
                            "current_block_index": current_block,
                            "current_block_count": current_block_count,
                            "current_length": len(current_candidate.definition_text),
                            "proposed_index": proposed_index,
                            "proposed_source": proposed_source,
                            "proposed_block_index": proposed_block,
                            "proposed_block_count": proposed_block_count,
                            "proposed_length": len(proposed_candidate.definition_text),
                            "current_text": current_candidate.definition_text,
                            "proposed_text": proposed_candidate.definition_text,
                        }
                    )
                if any(item[1] == "priority_rule" for item in current):
                    counts["priority_rule_rows"] += 1

    result = {
        "corpus": str(args.corpus),
        "files": len(files),
        "dispatch": "production ingest normalization + Stage 0/2, with source labels only",
        "proposal": "US-WA-only us_markers_inline_quote priority stream before baseline only when baseline made one block; no text-length or containment preference",
        "denominator": dict(counts),
        "by_jurisdiction": {key: dict(value) for key, value in sorted(by_jurisdiction.items())},
        "changed_persisted_keys": changed,
        "wall_seconds": round(time.monotonic() - started, 3),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"denominator": result["denominator"], "by_jurisdiction": result["by_jurisdiction"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
