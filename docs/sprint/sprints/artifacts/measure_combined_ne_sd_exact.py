#!/usr/bin/env python3
"""G8-aware persisted-output replay for the accepted exact NE/SD proposal.

The model has three deliberately jurisdiction-scoped recognition shapes:
NE's ``sections ... following definitions apply`` and named-Act numbered list,
plus SD's ``For the purposes of this chapter, the term, X, means``.  It then
models their unquoted extraction and SD-only chapter scope assignment.  The
replay retains pipeline G8 local-first/same-key suppression and first-key
persistence, and scans every 53 US parquet files.  Every changed key must
match the reviewed ledger below or the instrument fails.
"""

from __future__ import annotations

import json
import hashlib
import re
import time
from dataclasses import replace
from pathlib import Path

import pyarrow.parquet as pq

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.normalize import strip_wikilinks
from app.definition_links.profiles import get_profile

DEFAULT_CORPUS = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
_NE_C43_RE = re.compile(
    r"^For purposes of sections 43-3328 to 43-3339\s*,\s*the following definitions apply:",
    re.IGNORECASE,
)
_NE_C44_RE = re.compile(r"^For purposes of the Children of Nebraska Hearing Aid Act:\s*\n\s*\(1\)")
_SD_TERM_RE = re.compile(
    r"^For the purposes of this chapter, the term,\s+(?P<term>loan processor or underwriter),\s+(?P<verb>means)\s+",
    re.IGNORECASE,
)
_EXPECTED = {
    "STATE_NE_C43_S43-3329": {
        "Account", "Authorized attorney", "Child support", "Department", "Financial institution", "Match",
        "Medical support", "Obligor", "Payor", "Spousal support", "Support", "Support order",
    },
    "STATE_NE_C44_S44-5003": {"Health insurance plan", "Hearing aid", "Hearing impairment", "Insured child"},
    "STATE_SD_T54_C14_S54-14-12.1": {"loan processor or underwriter"},
}
_NE_C43_ORDER = (
    "Account", "Authorized attorney", "Child support", "Department", "Financial institution", "Match",
    "Medical support", "Obligor", "Payor", "Spousal support", "Support", "Support order",
)
_NE_C44_ORDER = ("Health insurance plan", "Hearing aid", "Hearing impairment", "Insured child")


def _jurisdiction(path: Path) -> str:
    state = path.stem.removeprefix("us_").removesuffix("_statutes")
    return "US-FED" if state == "federal" else f"US-{state.upper()}"


def _mode(code: str, body: str) -> str | None:
    if code == "US-NE" and _NE_C43_RE.match(body):
        return "ne_c43"
    if code == "US-NE" and _NE_C44_RE.match(body):
        return "ne_c44"
    if code == "US-SD" and _SD_TERM_RE.match(body):
        return "sd"
    return None


def _literal_ne_entries(body: str, ordered_terms: tuple[str, ...]) -> list[DefinitionCandidate]:
    """Explicit source-boundary parser for the two reviewed NE statutes.

    It accepts no generic named-Act population.  C43's ``Support in the
    definitions of ... means`` is intentionally a distinct term-selection
    branch: ``Support`` is the defined key and the qualifying phrase is not
    definition text.
    """
    candidates = []
    for index, term in enumerate(ordered_terms, start=1):
        if term == "Support":
            start_token = "(11) Support in the definitions of child support, medical support, and spousal support "
            verb_offset = body.find("means", body.find(start_token))
            assert verb_offset >= 0, "reviewed C43 Support clause drifted"
            definition_start = verb_offset
        else:
            start_token = f"({index}) {term} "
            definition_start = body.find(start_token) + len(start_token)
        start = body.find(start_token)
        assert start >= 0 and definition_start > start, f"reviewed NE entry drifted: {term}"
        end_token = f"\n\n({index + 1}) {ordered_terms[index]} " if index < len(ordered_terms) else "\n\nLaws"
        end = body.find(end_token, definition_start)
        assert end > definition_start, f"reviewed NE boundary drifted: {term}"
        candidates.append(DefinitionCandidate(terms=(term,), definition_text=body[definition_start:end].strip(), scope="law-wide"))
    return candidates


def _proposed_candidates(body: str, mode: str, scope: str) -> list[DefinitionCandidate]:
    if mode == "sd":
        match = _SD_TERM_RE.match(body)
        assert match is not None
        end_match = re.search(r"\n\nNo individual engaging solely", body[match.end() :])
        assert end_match is not None, "unreviewed SD boundary shape"
        return [
            DefinitionCandidate(
                terms=(match.group("term").strip(),),
                definition_text=body[match.start("verb") : match.end() + end_match.start()].strip(),
                scope=scope,
            )
        ]
    return _literal_ne_entries(body, _NE_C43_ORDER if mode == "ne_c43" else _NE_C44_ORDER)


def _stamp(profile, body: str, row: dict, scope: str, candidates: list[DefinitionCandidate]):
    output = []
    for candidate in candidates:
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
            output.append(stamped)
    return output


def _winner_map(candidates):
    winners = {}
    for candidate in candidates:
        winners.setdefault(tuple(sorted(candidate.terms)), candidate)
    return winners


def _canonical_changed_ledger_sha256(result: dict) -> str:
    """Hash only stable persisted core tuples, excluding judgments/timing."""
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
        )
    }
    return hashlib.sha256(
        json.dumps(projection, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _row_delta(row: dict, code: str):
    profile = get_profile(code)
    body, _ = strip_wikilinks(profile.normalize_for_parsing(row["text"].replace("\\n", "\n")))
    heading = row.get("section_title") or ""
    current_is_definitions = profile.is_definitions_heading(heading, body)
    # EntrySplitterRules receive only jurisdiction and body. Their exact
    # shapes can therefore run in explicit Definitions sections as well as
    # ones newly routed by a BodyPreambleRule.
    mode = _mode(code, body)
    current_local = (
        []
        if current_is_definitions
        else profile.extract_local_scope_definitions(
            body, article_number=str(row.get("section_number") or ""), chapter=row.get("chapter") or ""
        )
    )
    current = list(current_local)
    if current_is_definitions:
        scope = profile.determine_scope(body)
        current.extend(
            _stamp(profile, body, row, scope, profile.extract_definitions_from_section(body, scope=scope))
        )
    if mode is None:
        return _winner_map(current), _winner_map(current), None
    scope = "chapter" if mode == "sd" else profile.determine_scope(body)
    local_keys = {tuple(sorted(candidate.terms)) for candidate in current_local}
    proposed = list(current)
    proposed[0:0] = [
        candidate
        for candidate in _stamp(profile, body, row, scope, _proposed_candidates(body, mode, scope))
        if tuple(sorted(candidate.terms)) not in local_keys
    ]
    return _winner_map(current), _winner_map(proposed), mode


def main() -> int:
    output = Path("docs/sprint/sprints/artifacts/2026-08-07-defs-us-combined-ne-sd-exact.json")
    files = sorted(DEFAULT_CORPUS.glob("us_*_statutes.parquet"))
    assert len(files) == 53, f"expected 53 files, got {len(files)}"
    started = time.monotonic()
    rows = guarded = 0
    changed = []
    for path in files:
        code = _jurisdiction(path)
        parquet = pq.ParquetFile(path)
        # All non-NE/SD rows are excluded by the proposal's literal
        # jurisdiction registry guard; count all 53 files from parquet
        # metadata and replay only the two callable jurisdictions.
        if code not in {"US-NE", "US-SD"}:
            rows += parquet.metadata.num_rows
            guarded += parquet.metadata.num_rows
            continue
        for batch in parquet.iter_batches(
            batch_size=5000, columns=["act_id", "section_number", "section_title", "chapter", "text"]
        ):
            for row in batch.to_pylist():
                rows += 1
                # A non-matching literal preamble cannot reach either of the
                # new exact splitters, even when its heading is explicitly
                # Definitions. It is therefore provably unchanged; count it
                # but avoid replaying the unrelated registered stream.
                quick_body, _ = strip_wikilinks(
                    get_profile(code).normalize_for_parsing(row["text"].replace("\\n", "\n"))
                )
                if _mode(code, quick_body) is None:
                    continue
                before, after, mode = _row_delta(row, code)
                for key in sorted(set(before) | set(after)):
                    old, new = before.get(key), after.get(key)
                    if old is not None and new is not None and (old.definition_text, old.scope) == (
                        new.definition_text,
                        new.scope,
                    ):
                        continue
                    changed.append(
                        {
                            "act_id": row["act_id"], "jurisdiction": code, "mode": mode,
                            "terms": list(key),
                            "before": None if old is None else {"text": old.definition_text, "scope": old.scope},
                            "after": None if new is None else {"text": new.definition_text, "scope": new.scope},
                        }
                    )
    observed = {}
    for item in changed:
        assert item["before"] is None and item["after"] is not None, item
        observed.setdefault(item["act_id"], set()).add(item["terms"][0])
        item["machine_judgment"] = "new persisted key from exact jurisdiction+shape rule"
        item["human_judgment"] = "genuine source entry; text bounded at next reviewed source entry/tail"
    assert observed == _EXPECTED, f"unreviewed/stale changed keys: {observed!r}"
    result = {
        "files": len(files), "rows": rows, "jurisdiction_guarded_rows": guarded,
        "altitude": "G8 local-first/same-key suppression plus persisted (act_id, sorted terms, text, scope)",
        "proposal": "US-NE literal C43/C44 BodyPreamble shapes + exact source-bound EntrySplitter; US-SD literal preamble + chapter scope + exact source-bound EntrySplitter; no TermClauseRule",
        "changed_persisted_keys": changed, "wall_seconds": round(time.monotonic() - started, 3),
    }
    result["canonical_changed_ledger_sha256"] = _canonical_changed_ledger_sha256(result)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows": rows, "guarded": guarded, "changed": len(changed), "wall_seconds": result["wall_seconds"]}))


if __name__ == "__main__":
    main()
