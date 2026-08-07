"""Shared, non-counting support for the permanent G7 certification tools.

This module intentionally contains input identity, canonicalisation and live
production adapters only.  Q-D1 owns capture accounting; Q-D2 owns an
independent raw denominator and does not import Q-D1; Q-D3 reads artifacts.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[3]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SNAPSHOT_ID = "301000fc3465374ee0f23c3c6953a8a861e95cad"
INTEGRATION_SHA = "4fa9e7b368801757039091646e06a832620a3a2c"
EXPECTED_FILE_COUNT = 53
EXPECTED_ROW_COUNT = 2_038_247
REQUIRED_COLUMNS = ("act_id", "section_title", "text", "chapter", "section_number")


class CertificationError(RuntimeError):
    """A non-negotiable input or accounting contract violation."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def jsonl_hash(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_bytes(record))
        digest.update(b"\n")
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")
    return sha256_value(value)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("wb") as stream:
        for record in records:
            line = canonical_bytes(record) + b"\n"
            stream.write(line)
            digest.update(line)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CertificationError(f"cannot read canonical JSON {path}: {exc}") from exc


def snapshot_files(snapshot: Path) -> list[Path]:
    """Validate exactly the ratified statutes census before any measuring."""
    snapshot = snapshot.resolve()
    if snapshot.name != SNAPSHOT_ID:
        raise CertificationError(f"snapshot id must be {SNAPSHOT_ID}, got {snapshot.name}")
    if not snapshot.is_dir():
        raise CertificationError(f"snapshot is not a directory: {snapshot}")
    files = sorted(snapshot.glob("us_*_statutes.parquet"))
    if len(files) != EXPECTED_FILE_COUNT:
        raise CertificationError(f"expected {EXPECTED_FILE_COUNT} statute files, found {len(files)}")
    names = [path.name for path in files]
    if len(set(names)) != EXPECTED_FILE_COUNT:
        raise CertificationError("duplicate statute filename in snapshot")
    return files


def validate_corpus(snapshot: Path) -> tuple[list[Path], int, dict[str, int]]:
    """Read parquet metadata ourselves; malformed files or census drift fail closed."""
    import pyarrow.parquet as pq

    files = snapshot_files(snapshot)
    by_file: dict[str, int] = {}
    for path in files:
        try:
            parquet = pq.ParquetFile(path)
            names = set(parquet.schema_arrow.names)
            missing = set(REQUIRED_COLUMNS) - names
            if missing:
                raise CertificationError(f"{path.name} missing columns {sorted(missing)}")
            by_file[path.name] = parquet.metadata.num_rows
        except CertificationError:
            raise
        except Exception as exc:  # pyarrow's corruption errors vary by version.
            raise CertificationError(f"cannot read parquet metadata {path}: {exc}") from exc
    total = sum(by_file.values())
    if total != EXPECTED_ROW_COUNT:
        raise CertificationError(f"expected {EXPECTED_ROW_COUNT} rows, found {total}")
    return files, total, by_file


def validate_integration() -> None:
    """Certify the fixed production integration and reject later app changes."""
    try:
        subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{INTEGRATION_SHA}^{{commit}}"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", INTEGRATION_SHA, "HEAD"], check=True, capture_output=True)
        changed = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", f"{INTEGRATION_SHA}..HEAD", "--", "backend/app"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise CertificationError(f"integration SHA {INTEGRATION_SHA} is unavailable or not ancestral") from exc
    if changed:
        raise CertificationError(f"production changed after pinned integration SHA: {changed}")


def jurisdiction_for(path: Path) -> str:
    state = path.name.removeprefix("us_").removesuffix("_statutes.parquet")
    return "US-FED" if state == "federal" else f"US-{state.upper()}"


@dataclass(frozen=True)
class CapturedTuple:
    jurisdiction: str
    source_file: str
    source_row: int
    source_row_id: str
    term: str
    definition_text: str
    scope: str
    scope_value: str | list[str] | None
    route: str
    rule_family: str
    source_row_sha256: str
    section_number: str
    chapter: str | None

    def record(self) -> dict[str, Any]:
        return asdict(self)


def _scope_value(value: Any) -> str | list[str] | None:
    return list(value) if isinstance(value, tuple) else value


def _winner_family(profile, heading: str, body: str) -> str:
    """Identify the actual registered body rule after calling the profile seam."""
    from app.definition_links.rules import registry
    from app.definition_links.us_profile import derive_heading_from_body

    if derive_heading_from_body(heading, body) is not None:
        return "legacy"
    for rule in registry.body_preamble_rules_for(profile.code):
        if rule.derive_heading(body) is not None:
            fn = rule.derive_heading
            return f"{fn.__module__.rsplit('.', 1)[-1]}:{fn.__name__}"
    return "none"


def capture_row(*, jurisdiction: str, source_file: str, source_row: int, row: dict[str, Any], after: bool) -> list[CapturedTuple]:
    """Invoke the production profile/extractor and apply pipeline's actual dedup key.

    No regex or extractor is recreated here.  The explicit first-wins map is
    the persistence key from ``pipeline.run_definition_linking``:
    ``(article_id, sorted(terms))``.  A stable source-file/row identity stands
    in for the corpus article id so evidence remains retrievable outside a DB.
    """
    from app.definition_links.normalize import strip_wikilinks
    from app.definition_links.profiles import get_profile
    from app.definition_links.us_profile import (
        derive_heading_from_body as legacy_derive_heading,
        extract_definitions_from_section as legacy_extract,
        is_definitions_heading as legacy_is_heading,
    )

    profile = get_profile(jurisdiction)
    heading = row["section_title"] or ""
    raw_body = row["text"] or ""
    body, _ = strip_wikilinks(profile.normalize_for_parsing(raw_body))
    if after:
        recognized = profile.is_definitions_heading(heading, body)
        derived = False
        if not recognized:
            derived_heading = profile.derive_heading_from_body(heading, body)
            recognized = derived_heading is not None and profile.is_definitions_heading(derived_heading, body)
            derived = recognized
        if not recognized:
            return []
        scope = profile.determine_scope(body)
        assignments = profile.determine_scope_assignments(
            body, scope=scope, article_number=row["section_number"] or "", chapter=row["chapter"]
        )
        primary = profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=False)
        candidates = profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=derived)
        route = "fallback" if derived and not primary and candidates else "primary"
        family = _winner_family(profile, heading, body) if derived else "heading"
    else:
        recognized = legacy_is_heading(heading)
        derived = False
        if not recognized:
            derived_heading = legacy_derive_heading(heading, body)
            recognized = derived_heading is not None and legacy_is_heading(derived_heading)
            derived = recognized
        if not recognized:
            return []
        from app.definition_links.us_profile import determine_scope
        scope = determine_scope(body)
        candidates = legacy_extract(body, scope=scope, heading_was_derived=derived)
        from app.definition_links.rules import registry
        assignments = (registry.default_scope_assignment(scope, article_number=row["section_number"] or "", chapter=row["chapter"]),)
        route = "fallback" if derived and candidates else "primary"
        family = "baseline"

    source_row_id = str(row["act_id"] or f"{source_file}:{source_row}")
    row_hash = sha256_value({"act_id": source_row_id, "heading": heading, "body": raw_body})
    # Preserve Stage 2's order, including G8's body-derived local candidates,
    # then apply Stage 3's actual first-wins persistence identity once.  Scope
    # assignments are deliberately inside this ordered stream: a multi-value
    # assignment does not create duplicate Definition rows for one terms key.
    emissions: list[Any] = []
    local_keys: set[tuple[str, ...]] = set()
    if after and derived:
        for candidate in profile.extract_local_scope_definitions(
            body, article_number=row["section_number"] or "", chapter=row["chapter"]
        ):
            key = tuple(sorted(candidate.terms))
            if key not in local_keys:
                local_keys.add(key)
                emissions.append(candidate)
    for candidate in candidates:
        key = tuple(sorted(candidate.terms))
        if after and derived and key in local_keys:
            continue
        if after and derived:
            local_keys.add(key)
        for assignment in assignments:
            stamped = replace(candidate, scope=assignment.kind)
            if assignment.kind == "chapter":
                stamped.source_chapter = assignment.value
            elif assignment.kind == "local":
                stamped.source_article_number = assignment.value
            else:
                stamped.scope_value = assignment.value
            emissions.append(stamped)
    dedup: dict[tuple[str, ...], Any] = {}
    for candidate in emissions:
        dedup.setdefault(tuple(sorted(candidate.terms)), candidate)
    tuples: list[CapturedTuple] = []
    for terms, candidate in dedup.items():
        for term in terms:
            tuples.append(CapturedTuple(
                jurisdiction=jurisdiction, source_file=source_file, source_row=source_row,
                source_row_id=source_row_id, term=term, definition_text=candidate.definition_text,
                scope=candidate.scope, scope_value=_scope_value(candidate.scope_value), route=route,
                rule_family=family, source_row_sha256=row_hash,
                section_number=row["section_number"] or "", chapter=row["chapter"],
            ))
    return tuples


def tuple_key(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (record["jurisdiction"], record["source_file"], str(record["source_row"]), record["term"], record["definition_text"] + "\0" + record["scope"])


def sort_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=tuple_key)
