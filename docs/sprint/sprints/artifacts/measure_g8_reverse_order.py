#!/usr/bin/env python3
"""Measure G8's real-corpus reverse-order containment updates.

This deliberately replays the production ingest and Stage 0/2 candidate
construction before simulating pipeline.py's same-key persistence loop.  It
does not read or write a database: every corpus row maps to one freshly
ingested Article, so an in-memory key map is equivalent for the in-run
collision population being measured.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pyarrow.parquet as pq

from app.definition_links.normalize import strip_wikilinks
from app.definition_links.matcher import scope_rank
from app.definition_links.profiles import get_profile
from app.definition_links.extract import _parse_terms_and_qualifier


DEFAULT_CORPUS = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
EXPECTED_NY_FIXTURE_TERMS = {
    "Unlimited dividend rights",
    "Equity shares",
    "Voting rights",
    "Voting shares",
    "Preemptive right",
    "New shares or securities",
}
_NEXT_ENTRY_HEADER_RE = re.compile(
    r"^\s*(?:[;,.]|and\b)*\s*\([A-Za-z0-9]+\)\s*"
    r"(?P<header>.*?)\b(?:means|includes|shall\s+mean|shall\s+include|has\s+(?:the\s+)?same\s+meaning|has\s+the\s+meaning|refers\s+to)\b",
    re.IGNORECASE | re.DOTALL,
)
_TERM_PUNCTUATION_RE = re.compile(r"[\"“”'`.,;:]+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _historic_g8_tighter_containment(candidate_text: str, persisted_text: str) -> bool:
    """Simulate the exact retired G8 predicate for historical evidence.

    Production intentionally restored first-wins and removed this helper at
    056b5d0.  The measurement still asks how often that former behavior
    *would* have fired, so it carries the three-clause predicate locally
    instead of importing a production symbol which no longer exists.
    """
    return (
        candidate_text != persisted_text
        and len(candidate_text) < len(persisted_text)
        and candidate_text in persisted_text
    )


def _jurisdiction(path: Path) -> str:
    stem = path.stem.removeprefix("us_").removesuffix("_statutes")
    return "US-FED" if stem == "federal" else f"US-{stem.upper()}"


def _candidates_for_row(row: dict, profile):
    """Replay pipeline.py Stage 0 and Stage 2 for one freshly ingested row."""
    # This is the exact ingest_us_statute_rows transformation.  Applying it
    # before Stage 0 is essential: NY stores real line breaks as literal
    # backslash-n bytes in the source parquet.
    ingested = row["text"].replace("\\n", "\n")
    normalized = profile.normalize_for_parsing(ingested)
    body, _ = strip_wikilinks(normalized)
    heading = row.get("section_title") or ""
    article_number = str(row.get("section_number"))
    chapter = row.get("chapter") or ""

    is_definitions_section = profile.is_definitions_heading(heading, body)
    derived = False
    if not is_definitions_section:
        derived_heading = profile.derive_heading_from_body(heading, body)
        if derived_heading is not None and profile.is_definitions_heading(derived_heading, body):
            is_definitions_section = True
            derived = True

    if is_definitions_section:
        scope = profile.determine_scope(body)
        section_candidates = profile.extract_definitions_from_section(
            body, scope=scope, heading_was_derived=derived
        )
        # The persistence identity ignores scope, but pipeline.py fans out
        # scope assignments before persistence; preserve that list order.
        candidates = []
        for candidate in section_candidates:
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
                candidates.append(stamped)
        return candidates
    return profile.extract_local_scope_definitions(
        body, article_number=article_number, chapter=chapter
    )


def _run_controls(corpus: Path) -> dict:
    ny_path = corpus / "us_ny_statutes.parquet"
    ca_path = corpus / "us_ca_statutes.parquet"
    ny_rows = 0
    ny_real_newline = 0
    ny_literal_newline = 0
    ny_fixture = None
    for batch in pq.ParquetFile(ny_path).iter_batches(columns=["act_id", "text"]):
        for row in batch.to_pylist():
            text = row["text"]
            ny_rows += 1
            ny_real_newline += "\n" in text
            ny_literal_newline += "\\n" in text
            if row["act_id"] == "STATE_NY_ABNK_A15_T6_S6021":
                ny_fixture = text
    assert (ny_rows, ny_real_newline, ny_literal_newline) == (40102, 0, 40102)
    assert ny_fixture is not None and "\\n" in ny_fixture and "\n" not in ny_fixture
    ny_profile = get_profile("US-NY")
    raw_fixture_candidates = ny_profile.extract_definitions_from_section(
        ny_profile.normalize_for_parsing(ny_fixture), scope="section"
    )
    assert raw_fixture_candidates == []
    fixture_candidates = ny_profile.extract_definitions_from_section(
        ny_profile.normalize_for_parsing(ny_fixture.replace("\\n", "\n")), scope="section"
    )
    assert {term for c in fixture_candidates for term in c.terms} == EXPECTED_NY_FIXTURE_TERMS

    ca_fixture = None
    for batch in pq.ParquetFile(ca_path).iter_batches(columns=["act_id", "text"]):
        for row in batch.to_pylist():
            if row["act_id"] == "STATE_CA_Chsc_D31_P1_C3_S50150":
                ca_fixture = row["text"]
                break
        if ca_fixture is not None:
            break
    assert ca_fixture is not None
    assert ca_fixture.count("\\n") == 1
    assert ca_fixture.replace("\\n", "\n") != ca_fixture
    return {
        "positive_ny_raw_rows_literal_newline": ny_literal_newline,
        "positive_ny_raw_rows_real_newline": ny_real_newline,
        "negative_ny_raw_fixture_candidate_count": len(raw_fixture_candidates),
        "positive_ny_fixture_terms_after_ingest": sorted(EXPECTED_NY_FIXTURE_TERMS),
        "negative_ca_fixture_exact_one_literal_newline": ca_fixture.count("\\n"),
    }


def _canonical_terms(terms: tuple[str, ...]) -> tuple[str, ...]:
    """Compare quoted term-sets after harmless quote/punctuation cleanup."""
    return tuple(
        sorted(_TERM_PUNCTUATION_RE.sub("", " ".join(term.casefold().split())).strip() for term in terms)
    )


def _levenshtein(left: str, right: str) -> int:
    """Small, dependency-free edit distance for conservative alias screening."""
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def _near_alias(left: str, right: str) -> bool:
    """Reject plausible aliases; G8 prefers conservative false negatives."""
    left_words = left.split()
    right_words = right.split()
    if left_words[: len(right_words)] == right_words or right_words[: len(left_words)] == left_words:
        return True
    left_compact = _NON_ALNUM_RE.sub("", left)
    right_compact = _NON_ALNUM_RE.sub("", right)
    if left_compact.rstrip("s") == right_compact.rstrip("s"):
        return True
    return _levenshtein(left_compact, right_compact) <= 2


def _structural_discriminator(
    earlier_text: str,
    later_text: str,
    current_terms: tuple[str, ...],
    earlier_scope: str,
    later_scope: str,
):
    """Apply the proposed safe replacement discriminator to one G8 firing.

    A shorter candidate can only be eligible when it is the exact beginning
    of the persisted text and the discarded suffix starts a new quoted entry
    for a DIFFERENT persistence key.  This intentionally preserves a
    same-term ``(B) \"Term\" includes/does not include`` continuation.
    """
    if scope_rank(later_scope) > scope_rank(earlier_scope):
        return {"eligible": False, "reason": "broader_scope_candidate"}
    if not earlier_text.startswith(later_text):
        return {"eligible": False, "reason": "not_same_start_prefix"}
    suffix = earlier_text[len(later_text) :]
    match = _NEXT_ENTRY_HEADER_RE.match(suffix)
    if match is None:
        return {"eligible": False, "reason": "suffix_has_no_parseable_entry_boundary"}
    # Reuse extract.py's production header parser rather than capturing only
    # the first quote.  A boundary such as `"Sale" or "sell" includes` is
    # therefore compared as the complete leading quoted term-set.  The
    # pipeline persistence identity is ``tuple(sorted(candidate.terms))``;
    # the two sets use the same term semantics, although a profile may emit a
    # subset of a header's aliases today.  Comparing the complete header is
    # deliberately more conservative in that case.
    parsed_terms, _ = _parse_terms_and_qualifier(match.group("header"))
    next_terms = tuple(parsed_terms)
    if not next_terms:
        return {"eligible": False, "reason": "boundary_has_no_quoted_term_set"}
    canonical_next_terms = _canonical_terms(next_terms)
    canonical_current_key = _canonical_terms(current_terms)
    if canonical_next_terms == canonical_current_key:
        return {
            "eligible": False,
            "reason": "same_canonical_term_continuation",
            "next_terms": list(next_terms),
            "canonical_next_terms": list(canonical_next_terms),
        }
    if any(_near_alias(current, next_term) for current in canonical_current_key for next_term in canonical_next_terms):
        return {
            "eligible": False,
            "reason": "near_alias_boundary",
            "next_terms": list(next_terms),
            "canonical_next_terms": list(canonical_next_terms),
        }
    return {
        "eligible": True,
        "reason": "different_canonical_term_boundary",
        "next_terms": list(next_terms),
        "canonical_next_terms": list(canonical_next_terms),
    }


def _scope_direction(earlier_scope: str, later_scope: str) -> str:
    earlier_rank = scope_rank(earlier_scope)
    later_rank = scope_rank(later_scope)
    if later_rank > earlier_rank:
        return "broader"
    if later_rank < earlier_rank:
        return "narrower"
    return "equal_rank"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    files = sorted(args.corpus.glob("us_*_statutes.parquet"))
    assert len(files) == 53, f"expected 53 statute files, got {len(files)}"
    controls = _run_controls(args.corpus)
    counts = Counter()
    firings = []

    for path in files:
        profile = get_profile(_jurisdiction(path))
        parquet = pq.ParquetFile(path)
        columns = ["act_id", "section_number", "section_title", "chapter", "text"]
        for batch in parquet.iter_batches(batch_size=5_000, columns=columns):
            for row in batch.to_pylist():
                counts["rows"] += 1
                candidates = _candidates_for_row(row, profile)
                counts["candidates"] += len(candidates)
                persisted_by_key = {}
                collided_keys = set()
                for index, candidate in enumerate(candidates):
                    key = tuple(sorted(candidate.terms))
                    persisted = persisted_by_key.get(key)
                    if persisted is None:
                        persisted_by_key[key] = (candidate, index)
                        continue
                    earlier, earlier_index = persisted
                    counts["same_key_later_candidates"] += 1
                    if key not in collided_keys:
                        collided_keys.add(key)
                        counts["same_key_collision_groups"] += 1
                    if _historic_g8_tighter_containment(
                        candidate.definition_text, earlier.definition_text
                    ):
                        counts["firings"] += 1
                        structural = _structural_discriminator(
                            earlier.definition_text,
                            candidate.definition_text,
                            key,
                            earlier.scope,
                            candidate.scope,
                        )
                        scope_direction = _scope_direction(earlier.scope, candidate.scope)
                        counts[f"structural_{structural['reason']}"] += 1
                        counts[f"scope_{scope_direction}"] += 1
                        if structural["eligible"]:
                            counts["structural_eligible"] += 1
                        firings.append(
                            {
                                "file": path.name,
                                "act_id": row["act_id"],
                                "terms": list(candidate.terms),
                                "candidate_index": index,
                                "earlier_candidate_index": earlier_index,
                                "earlier_text": earlier.definition_text,
                                "later_text": candidate.definition_text,
                                "earlier_length": len(earlier.definition_text),
                                "later_length": len(candidate.definition_text),
                                "earlier_scope": earlier.scope,
                                "later_scope": candidate.scope,
                                "scope_direction": scope_direction,
                                "structural": structural,
                            }
                        )
                        persisted_by_key[key] = (candidate, index)

    result = {
        "corpus": str(args.corpus),
        "glob": "us_*_statutes.parquet",
        "files": len(files),
        "controls": controls,
        "denominator": dict(counts),
        "firings": firings,
        "wall_seconds": round(time.monotonic() - started, 3),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"denominator": result["denominator"], "wall_seconds": result["wall_seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
