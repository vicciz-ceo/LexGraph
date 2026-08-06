#!/usr/bin/env python3
"""Replay persisted Stage-2 winners for the combined-correction proposals.

This read-only instrument follows ingest normalization, heading/body-derivation
dispatch, scope stamping, and pipeline first-by-(article, sorted-terms) winner
selection.  It records the persisted tuple altitude used by the actual
pipeline: ``(act_id, sorted terms, definition_text, scope)``.  It compares
three US-FED alternatives over every 53-file corpus row:

* ``inline_fallback_append``: only a derived US-FED section adds inline fallback keys
  not already emitted by registered extraction;
* ``structural_rule``: the historical broad US-FED numbered-label replay,
  restricted to body-derived sections; it is retained as a rejected lower
  bound with a reproducible ledger hash, not a full callable-seam result;
* ``structural_rule_exact``: the same parser but only when the three
  evidenced Good-Samaritan terms are all present, testing the narrowest
  jurisdiction-and-shape rule that the EntrySplitter API can express;
* ``composite``: both mechanisms.

The structural parser is a proposal model, not production code.  Its narrowly
specified shape is the demonstrated ``(N) Label`` + ``The term "X" ...`` FED
format and its top-level subsection boundary.  Any changed persisted key is
written in full for human classification; the script never declares text
quality from a length heuristic.

The historical CLI alias ``profile_union`` remains accepted solely to reproduce
the rejected full-ledger SHA recorded in the compact evidence; it is not an
accepted architecture or developer seam.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import pyarrow.parquet as pq

from app.definition_links.normalize import strip_wikilinks
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry
from app.definition_links.us_profile import (
    _extract_inline_quoted_definitions,
    _leading_quote_candidate,
    _split_into_numbered_blocks,
)

DEFAULT_CORPUS = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
_FED_LABEL_TERM_RE = re.compile(
    r'(?ms)^\(\d+\)\s+[^\n]{1,180}\n+\s*The term\s+"(?P<term>[^"]{1,180})"'
    r'(?:,\s*[^\n]{0,220}?)?\s+(?:means|includes|shall\s+mean)\s+'
)
_FED_TOP_LEVEL_SUBSECTION_RE = re.compile(r"(?m)^\([a-z]\)\s+[A-Z]")
_FED_GOOD_SAMARITAN_PREFIX = "(a) Definitions\n\nIn this section:"
_FED_GOOD_SAMARITAN_TERMS = frozenset(
    {"eligible", "good Samaritan search-and-recovery mission", "Secretary"}
)


def _jurisdiction(path: Path) -> str:
    state = path.stem.removeprefix("us_").removesuffix("_statutes")
    return "US-FED" if state == "federal" else f"US-{state.upper()}"


def _proposed_fed_structural_candidates(text: str, *, scope: str):
    """Return quoted blocks so the real leading-quote parser supplies the
    same DefinitionCandidate shape as every EntrySplitterRule.
    """
    matches = list(_FED_LABEL_TERM_RE.finditer(text))
    blocks: list[str] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        next_subsection = _FED_TOP_LEVEL_SUBSECTION_RE.search(text, match.end(), next_start)
        end = next_subsection.start() if next_subsection is not None else next_start
        definition_text = text[match.end() : end].strip()
        if definition_text:
            blocks.append(f'"{match.group("term").strip()}" {definition_text}')
    return [_leading_quote_candidate(block, scope=scope) for block in blocks]


def _base_stream(profile, code: str, text: str, scope: str, derived: bool):
    """Materialize actual USProfile source order, retaining source labels."""
    baseline_blocks = _split_into_numbered_blocks(text)
    priority_blocks: list[str] = []
    ordinary_blocks: list[str] = []
    for rule in registry.entry_splitter_rules_for(code):
        if rule.priority_before_single_baseline:
            priority_blocks.extend(rule.split(text))
        else:
            ordinary_blocks.extend(rule.split(text))
    ordered = (
        [("baseline", block) for block in baseline_blocks]
        + [("priority_registered", block) for block in priority_blocks]
        + [("registered", block) for block in ordinary_blocks]
        if len(baseline_blocks) != 1
        else [("priority_registered", block) for block in priority_blocks]
        + [("baseline", block) for block in baseline_blocks]
        + [("registered", block) for block in ordinary_blocks]
    )
    candidates = []
    for source, block in ordered:
        candidate = _leading_quote_candidate(block, scope=scope)
        if candidate is not None:
            candidates.append((candidate, source))
    for _source, block in ordered:
        for rule in registry.term_clause_rules_for(code):
            parsed = (
                rule.parse_scoped(block, registry.TermClauseContext(scope=scope))
                if rule.parse_scoped is not None
                else rule.parse(block)
            )
            candidates.extend((candidate, "term_clause") for candidate in parsed)
    if not candidates and derived:
        candidates.extend(
            (candidate, "inline_fallback")
            for candidate in _extract_inline_quoted_definitions(text, scope=scope)
        )
    return candidates, baseline_blocks


def _with_proposal(profile, code: str, text: str, scope: str, derived: bool, proposal: str):
    current, baseline_blocks = _base_stream(profile, code, text, scope, derived)
    if code != "US-FED":
        return current, current

    proposed = list(current)
    # Preserve the historical broad-replay semantics for its compact rejected
    # ledger: that seam was body-derived only. The accepted exact splitter has
    # no heading-provenance input and is measured at its real callable seam.
    structural_enabled = proposal == "structural_rule_exact" or (
        proposal in {"structural_rule", "composite"} and derived
    )
    if structural_enabled:
        structural = [candidate for candidate in _proposed_fed_structural_candidates(text, scope=scope) if candidate]
        if proposal == "structural_rule_exact" and not (
            text.startswith(_FED_GOOD_SAMARITAN_PREFIX)
            and {term for candidate in structural for term in candidate.terms}
            == _FED_GOOD_SAMARITAN_TERMS
        ):
            structural = []
        # The proposed rule is priority_before_single_baseline.  When baseline
        # yields >1 block its normal position is after baseline but before the
        # existing ordinary US-FED splitter; when it yields one, it comes first.
        insertion = 0 if len(baseline_blocks) == 1 else sum(
            1 for _candidate, source in current if source == "baseline"
        )
        proposed[insertion:insertion] = [(candidate, "proposed_fed_structural") for candidate in structural]
    # This rejected alternative models the profile method's actual fallback
    # seam, which is callable only for body-derived headings.  The structural
    # rule above is an EntrySplitterRule and has no such provenance input.
    if proposal in {"inline_fallback_append", "profile_union", "composite"} and derived:
        existing_keys = {tuple(sorted(candidate.terms)) for candidate, _source in proposed}
        for candidate in _extract_inline_quoted_definitions(text, scope=scope):
            key = tuple(sorted(candidate.terms))
            if key not in existing_keys:
                proposed.append((candidate, "proposed_fed_inline_union"))
                existing_keys.add(key)
    return current, proposed


def _stamped(profile, body: str, row: dict, scope: str, stream):
    output = []
    for candidate, source in stream:
        for assignment in profile.determine_scope_assignments(
            body,
            scope=scope,
            article_number=str(row.get("section_number") or ""),
            chapter=row.get("chapter") or "",
        ):
            stamped = replace(candidate, scope=assignment.kind)
            if assignment.kind == "chapter":
                stamped.source_chapter = assignment.value
            elif assignment.kind == "local":
                stamped.source_article_number = assignment.value
            else:
                stamped.scope_value = assignment.value
            output.append((stamped, source))
    return output


def _winner_map(stream):
    winners = {}
    for candidate, source in stream:
        winners.setdefault(tuple(sorted(candidate.terms)), (candidate, source))
    return winners


def _canonical_changed_ledger_sha256(result: dict) -> str:
    """Hash only persisted core tuples, never annotations, timing, or paths."""
    projection = {
        "changed_persisted_keys": sorted(
            [
                {
                    field: item.get(field)
                    for field in (
                        "file",
                        "jurisdiction",
                        "act_id",
                        "derived_heading",
                        "terms",
                        "before",
                        "after",
                    )
                }
                for item in result["changed_persisted_keys"]
            ],
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
        ),
    }
    encoded = json.dumps(projection, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _row_streams(row: dict, code: str, proposal: str):
    profile = get_profile(code)
    body, _ = strip_wikilinks(profile.normalize_for_parsing(row["text"].replace("\\n", "\n")))
    heading = row.get("section_title") or ""
    is_definitions = profile.is_definitions_heading(heading, body)
    derived = False
    if not is_definitions:
        derived_heading = profile.derive_heading_from_body(heading, body)
        if derived_heading is not None and profile.is_definitions_heading(derived_heading, body):
            is_definitions = True
            derived = True
    if not is_definitions:
        local = profile.extract_local_scope_definitions(
            body, article_number=str(row.get("section_number") or ""), chapter=row.get("chapter") or ""
        )
        return [(candidate, "local_scope") for candidate in local], [(candidate, "local_scope") for candidate in local], False
    scope = profile.determine_scope(body)
    current, proposed = _with_proposal(profile, code, body, scope, derived, proposal)
    # G8's real pipeline order matters at persisted altitude: for a body-
    # derived Definitions heading, local-scope candidates enter first and own
    # their sorted-term keys.  A later section candidate with that key is not
    # merely de-prioritized; it is never appended for persistence.  Model the
    # exact local dedupe/suppression for both current and proposed streams.
    local = []
    local_keys = set()
    if derived:
        for candidate in profile.extract_local_scope_definitions(
            body, article_number=str(row.get("section_number") or ""), chapter=row.get("chapter") or ""
        ):
            key = tuple(sorted(candidate.terms))
            if key not in local_keys:
                local.append((candidate, "local_scope"))
                local_keys.add(key)
    current_stamped = _stamped(profile, body, row, scope, current)
    proposed_stamped = _stamped(profile, body, row, scope, proposed)
    return (
        local + [item for item in current_stamped if tuple(sorted(item[0].terms)) not in local_keys],
        local + [item for item in proposed_stamped if tuple(sorted(item[0].terms)) not in local_keys],
        derived,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--proposal",
        choices=(
            "inline_fallback_append",
            "profile_union",  # Historical rejected-ledger reproducibility alias.
            "structural_rule",
            "structural_rule_exact",
            "composite",
        ),
        required=True,
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()
    files = sorted(args.corpus.glob("us_*_statutes.parquet"))
    assert len(files) == 53, f"expected 53 statute files, found {len(files)}"
    started = time.monotonic()
    counts = Counter()
    by_jurisdiction = defaultdict(Counter)
    changes = []
    for path in files:
        code = _jurisdiction(path)
        parquet = pq.ParquetFile(path)
        # The proposal itself has an exact US-FED jurisdiction guard. Count
        # every non-target corpus row from immutable parquet metadata rather
        # than spending replay time materializing rows that cannot enter it.
        if code != "US-FED":
            counts["rows"] += parquet.metadata.num_rows
            counts["jurisdiction_guarded_rows"] += parquet.metadata.num_rows
            continue
        for batch in parquet.iter_batches(
            batch_size=5000, columns=["act_id", "section_number", "section_title", "chapter", "text"]
        ):
            for row in batch.to_pylist():
                counts["rows"] += 1
                # For the accepted exact proposal, a non-prefix body cannot
                # receive a candidate at the real EntrySplitter seam. Avoid
                # expensive current/proposed replay for that provably identical
                # row while still examining and counting every US-FED row.
                if args.proposal == "structural_rule_exact":
                    callable_body, _ = strip_wikilinks(
                        get_profile(code).normalize_for_parsing(row["text"].replace("\\n", "\n"))
                    )
                    if not callable_body.startswith(_FED_GOOD_SAMARITAN_PREFIX):
                        continue
                current, proposed, derived = _row_streams(row, code, args.proposal)
                current_winners = _winner_map(current)
                proposed_winners = _winner_map(proposed)
                all_keys = sorted(set(current_winners) | set(proposed_winners))
                for key in all_keys:
                    before = current_winners.get(key)
                    after = proposed_winners.get(key)
                    if before is not None and after is not None and (
                        before[0].definition_text,
                        before[0].scope,
                    ) == (after[0].definition_text, after[0].scope):
                        continue
                    counts["changed_persisted_keys"] += 1
                    by_jurisdiction[code]["changed_persisted_keys"] += 1
                    changes.append(
                        {
                            "file": path.name,
                            "jurisdiction": code,
                            "act_id": row["act_id"],
                            "derived_heading": derived,
                            "terms": list(key),
                            "before": None
                            if before is None
                            else {"source": before[1], "text": before[0].definition_text, "scope": before[0].scope},
                            "after": None
                            if after is None
                            else {"source": after[1], "text": after[0].definition_text, "scope": after[0].scope},
                        }
                    )
    result = {
        "corpus": str(args.corpus),
        "files": len(files),
        "proposal": args.proposal,
        "altitude": "pipeline-equivalent persisted first winner: (act_id, sorted terms, definition_text, scope)",
        "denominator": dict(counts),
        "by_jurisdiction": {code: dict(counts) for code, counts in sorted(by_jurisdiction.items())},
        "changed_persisted_keys": changes,
        "wall_seconds": round(time.monotonic() - started, 3),
    }
    result["canonical_changed_ledger_sha256"] = _canonical_changed_ledger_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"proposal": args.proposal, "denominator": result["denominator"], "by_jurisdiction": result["by_jurisdiction"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
