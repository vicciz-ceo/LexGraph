"""Runtime-only B1 clause-group prototype for M-R111.

This deliberately patches the proposed additive seam, never production:
registry returns a ``BodyPreambleMatch``-shaped value for B1, B1 discovers
bounded clause groups, ``USProfile`` carries the match into extraction, and
the pipeline's profile resolver sees that patched profile.  Legacy rules still
return headings and non-B1 paths are byte-for-byte delegated to production.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import multiprocessing
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from qa_g7_common import SNAPSHOT_ID, capture_row, jurisdiction_for, tuple_key, validate_corpus, write_json, write_jsonl


@dataclass(frozen=True)
class ClauseGroup:
    """One bounded relationship plus every quoted alias it governs.

    The production equivalent belongs in ``registry.py`` as additive evidence
    on a B1-only ``BodyPreambleMatch``.  Spans are body offsets; no group is a
    body boundary and all independently valid groups are unioned.
    """

    term_spans: tuple[tuple[str, int, int], ...]
    relationship_span: tuple[int, int]
    colon_list: bool = False


@dataclass(frozen=True)
class BodyPreambleMatch:
    heading: str
    clause_groups: tuple[ClauseGroup, ...] = ()


_QUOTE = re.compile(r'["“]([^"”]{1,200})["”]')
_RELATION = re.compile(
    r"\b(?:"
    r"shall\s+have\s+the\s+(?:same\s+)?(?:meaning|definition)(?:\s+(?:set\s+forth|provided|given|found|prescribed))?(?:\s+(?:in|under|by|at))?|"
    r"(?:has|have)\s+the\s+(?:same\s+)?(?:meaning|definition)(?:\s+(?:set\s+forth|provided|given|found|prescribed))?(?:\s+(?:in|under|by|at))?|"
    r"(?:means?|shall\s+mean|includes?|shall\s+include|does\s+not\s+include|shall\s+not\s+include|"
    r"expressly\s+excludes?|excludes?|refers?\s+to|shall\s+refer\s+to|is|are|shall\s+be|"
    r"(?:meaning|definition)\s+(?:given|assigned|ascribed|provided|prescribed|found)(?:\s+(?:in|under|to))?)"
    r")\b",
    re.IGNORECASE,
)
_CLAUSE_BOUNDARY = re.compile(r"[;\n]")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.?!])(?:\s|$)")
_MAX_GROUP = 600
_COLON_INTRO_WINDOW = 160


def _group_end(body: str, start: int) -> int:
    """End at the first clause/sentence boundary, never a whole body."""
    limit = min(len(body), start + _MAX_GROUP)
    tail = body[start:limit]
    ends = [m.start() + start + 1 for m in _CLAUSE_BOUNDARY.finditer(tail)]
    sentence = _SENTENCE_BOUNDARY.search(tail)
    if sentence is not None:
        ends.append(start + sentence.start() + 1)
    return min(ends) if ends else limit


def discover_clause_groups(body: str) -> tuple[ClauseGroup, ...]:
    """Find syntactically self-contained quoted B1 definition groups.

    A relation owns every quote since the closest prior clause boundary.  That
    makes aliases and ellipses one group, while a quote in an earlier operative
    sentence cannot be inherited by a later relation.  The parser accepts the
    existing forwarding/exclusion vocabulary plus descriptive copulas; it does
    not use jurisdiction, title, term, or corpus identity.
    """
    groups: list[ClauseGroup] = []
    for relation in _RELATION.finditer(body):
        before = body[max(0, relation.start() - _MAX_GROUP): relation.start()]
        boundary = max(before.rfind(";"), before.rfind("\n"), before.rfind(":"))
        clause_start = relation.start() - len(before) + boundary + 1
        quote_matches = list(_QUOTE.finditer(body, clause_start, relation.start()))
        if not quote_matches:
            continue
        # Reject narrative quotations intermixed with an otherwise unrelated
        # relation: aliases may be comma/and/or separated, not prose clauses.
        cursor = quote_matches[0].start()
        valid = True
        for quote in quote_matches:
            bridge = body[cursor:quote.start()]
            if bridge and not re.fullmatch(r"[\s,]*(?:(?:and|or)\s*)?", bridge, re.I):
                valid = False
                break
            cursor = quote.end()
        if not valid:
            continue
        bridge = body[cursor:relation.start()]
        if not re.fullmatch(r"[\s,]*(?:(?:and|or)\s*)?", bridge, re.I):
            continue
        terms = tuple((m.group(1).strip(), m.start(), m.end()) for m in quote_matches if m.group(1).strip())
        if not terms:
            continue
        end = _group_end(body, relation.start())
        intro = body[max(0, quote_matches[0].start() - _COLON_INTRO_WINDOW): quote_matches[0].start()]
        colon_list = bool(
            re.search(r"(?:As\s+used|For\s+(?:the\s+)?purposes?\s+of|In\s+this)[^;\n]{0,160}:\s*(?:\([^)]{1,12}\)\s*)?$", intro, re.I)
        )
        groups.append(ClauseGroup(term_spans=terms, relationship_span=(relation.start(), end), colon_list=colon_list))
    # A duplicate can arise from a nested regex alternative; preserve source
    # order but make union deterministic.
    seen: set[tuple[tuple[tuple[str, int, int], ...], tuple[int, int], bool]] = set()
    return tuple(g for g in groups if not ((key := (g.term_spans, g.relationship_span, g.colon_list)) in seen or seen.add(key)))


def _b1_clause_group_match(body: str) -> BodyPreambleMatch | None:
    """B1 recognition requires both its existing intro and one valid group."""
    from app.definition_links.rules.us_body_preamble_b1 import _B1_TRIGGER_RE

    if not _B1_TRIGGER_RE.search(body):
        return None
    groups = discover_clause_groups(body)
    return BodyPreambleMatch("Definitions", groups) if groups else None


def _group_candidates(text: str, groups: tuple[ClauseGroup, ...], scope: str):
    from app.definition_links.extract import DefinitionCandidate

    candidates = []
    for group in groups:
        start, end = group.relationship_span
        definition_text = text[start:end].strip()
        if group.colon_list:
            idiom = re.match(r"(?:means?|shall\s+mean|includes?|shall\s+include)\b:?\s*", definition_text, re.I)
            if idiom is not None:
                definition_text = definition_text[idiom.end():]
        if not definition_text:
            continue
        for term, _, _ in group.term_spans:
            candidates.append(DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope))
    return candidates


@contextlib.contextmanager
def clause_group_runtime_patch():
    """Patch and restore the four proposed layers deterministically."""
    from app.definition_links import pipeline
    from app.definition_links.rules import registry
    from app.definition_links.rules.registry import BodyPreambleRule
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import USProfile, derive_heading_from_body

    original_rules_for = registry.body_preamble_rules_for
    original_derive = USProfile.derive_heading_from_body
    original_extract = USProfile.extract_definitions_from_section
    original_extract_local = USProfile.extract_local_scope_definitions
    original_pipeline_get_profile = pipeline.get_profile
    # The production resolver may materialize equivalent profile instances;
    # body text is the immutable carrier key that survives all four layers.
    matches: dict[str, BodyPreambleMatch] = {}

    def rules_for(code: str):
        rules = original_rules_for(code)
        return [
            BodyPreambleRule(rule.jurisdiction_codes, _b1_clause_group_match)
            if rule.derive_heading is _b1_trigger_colon_or_quote_means
            else rule
            for rule in rules
        ]

    def derive(self, heading: str, body: str):
        baseline = derive_heading_from_body(heading, body)
        if baseline is not None:
            return baseline
        for rule in registry.body_preamble_rules_for(self.code):
            value = rule.derive_heading(body)
            if value is None:
                continue
            if isinstance(value, BodyPreambleMatch):
                matches[body] = value
                return value.heading
            return value
        return None

    def extract(self, text: str, *, scope: str, heading_was_derived=False):
        match = matches.get(text)
        if match is None or not heading_was_derived:
            return original_extract(self, text, scope=scope, heading_was_derived=heading_was_derived)
        # Drop every quoted whole-body candidate (the false operative/citation
        # population) and replace it with bounded group evidence.  Unquoted
        # candidates remain delegated unchanged.
        baseline = original_extract(self, text, scope=scope, heading_was_derived=False)
        quoted_terms = {quote.group(1).strip() for quote in _QUOTE.finditer(text)}
        baseline = [
            candidate
            for candidate in baseline
            if all(term not in quoted_terms for term in candidate.terms)
        ]
        return baseline + _group_candidates(text, match.clause_groups, scope)

    def extract_local(self, article_body: str, *, article_number: str, chapter=None):
        # Pipeline normally asks for local candidates first.  Preserve its
        # exact candidate text/order for valid groups (including the current
        # source-faithful ``means`` text), while suppressing only quoted terms
        # that are not group evidence.  Missing aliases are added later by the
        # section side and deduped by the real pipeline identity.
        match = matches.get(article_body)
        original = original_extract_local(self, article_body, article_number=article_number, chapter=chapter)
        if match is None:
            return original
        accepted_terms = {term for group in match.clause_groups for term, _, _ in group.term_spans}
        quoted_terms = {quote.group(1).strip() for quote in _QUOTE.finditer(article_body)}
        return [
            candidate
            for candidate in original
            if all(term not in quoted_terms or term in accepted_terms for term in candidate.terms)
        ]

    registry.body_preamble_rules_for = rules_for
    USProfile.derive_heading_from_body = derive
    USProfile.extract_definitions_from_section = extract
    USProfile.extract_local_scope_definitions = extract_local
    # ``_profile_for_document`` is a closure inside the real pipeline.  Its
    # imported resolver is therefore the pipeline layer's patch point.
    pipeline.get_profile = lambda code: original_pipeline_get_profile(code)
    try:
        yield
    finally:
        pipeline.get_profile = original_pipeline_get_profile
        USProfile.extract_definitions_from_section = original_extract
        USProfile.extract_local_scope_definitions = original_extract_local
        USProfile.derive_heading_from_body = original_derive
        registry.body_preamble_rules_for = original_rules_for


def _current_b1_winner(code: str, heading: str, body: str) -> bool:
    """Exact current first-winner prefilter; prototype never expands it."""
    # Registration is import-time by design; make the production family
    # module explicit so a forked worker starts from the same registry state
    # as the real profile/pipeline imports.
    import app.definition_links.rules.us_body_preamble  # noqa: F401
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import derive_heading_from_body

    if derive_heading_from_body(heading, body) is not None:
        return False
    # The runtime patch replaces the public lookup for AFTER capture.  The
    # audited winner prefilter must instead read the unchanged registered
    # sequence directly, retaining current first-winner membership exactly.
    for rule in (rule for rule in registry._body_preamble_rules if registry._matches(rule.jurisdiction_codes, code)):
        if rule.derive_heading(body) is not None:
            return rule.derive_heading is _b1_trigger_colon_or_quote_means
    return False


def _file(path_text: str):
    path = Path(path_text)
    code = jurisdiction_for(path)
    before, after, members, selected = [], [], [], []
    # Current production is the baseline.  ``capture_row(after=True)`` is
    # intentional here: it exercises today's registered B1 pipeline, before
    # the runtime patch exists, rather than the pre-B1 legacy baseline.
    for batch_index, batch in enumerate(
        pq.ParquetFile(path).iter_batches(
            columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=4096
        )
    ):
        for row_index, row in enumerate(batch.to_pylist()):
            source_row = batch_index * 4096 + row_index
            body, heading = row["text"] or "", row["section_title"] or ""
            if not _current_b1_winner(code, heading, body):
                continue
            selected.append((source_row, row))
            members.append({"source_file": path.name, "source_row": source_row, "source_row_id": str(row["act_id"] or f"{path.name}:{source_row}")})
            before.extend(x.record() for x in capture_row(jurisdiction=code, source_file=path.name, source_row=source_row, row=row, after=True))
    with clause_group_runtime_patch():
        for source_row, row in selected:
            after.extend(x.record() for x in capture_row(jurisdiction=code, source_file=path.name, source_row=source_row, row=row, after=True))
    baseline = {tuple_key(x): x for x in before}
    proposed = {tuple_key(x): x for x in after}
    changes = []
    for change, left, right in (("removed", baseline, proposed), ("added", proposed, baseline)):
        for key in left.keys() - right.keys():
            row = left[key]
            classification = "source_held_hi" if row["jurisdiction"] == "US-HI" else "source_held_fed" if row["jurisdiction"] == "US-FED" else "needs_source_adjudication"
            changes.append({"change": change, "classification": classification, **row})
    return changes, members


def _run_self_check() -> int:
    """Run direct and real persistence controls under the runtime prototype."""
    import pytest

    tests = [
        "backend/tests/unit/test_us_body_preamble_b1_occurrence_local_profile_red.py",
        "backend/tests/integration/test_us_body_preamble_b1_occurrence_local_persistence_red.py",
        "backend/tests/unit/test_us_body_preamble_b1_structural_future_law_red.py",
        "backend/tests/integration/test_us_body_preamble_b1_structural_future_law_persistence_red.py",
    ]
    with clause_group_runtime_patch():
        return pytest.main(["-q", *tests])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        return _run_self_check()
    if args.snapshot is None or args.out is None:
        parser.error("--snapshot and --out are required unless --self-check")
    files, rows, _ = validate_corpus(args.snapshot)
    chosen = files[args.shard :: args.shards]
    with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("fork")) as pool:
        parts = list(pool.map(_file, map(str, chosen)))
    changed = [row for part, _ in parts for row in part]
    members = [row for _, part in parts for row in part]
    changed.sort(key=lambda row: (tuple_key(row), row["change"]))
    members.sort(key=lambda row: (row["source_file"], row["source_row"]))
    args.out.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "lexgraph.mr111.clause-group.v1",
        "snapshot_id": SNAPSHOT_ID,
        "files": len(files),
        "rows": rows,
        "shard": [args.shard, args.shards],
        "b1_winner_row_count": len(members),
        "b1_winner_membership_sha256": write_jsonl(args.out / "b1_winner_rows.jsonl", members),
        "changed_key_count": len(changed),
        "classification_totals": dict(sorted(Counter(row["classification"] for row in changed).items())),
        "ledger_sha256": write_jsonl(args.out / "changed.jsonl", changed),
    }
    write_json(args.out / "summary.json", result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
