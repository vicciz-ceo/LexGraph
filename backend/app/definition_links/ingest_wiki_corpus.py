"""Bulk-ingest core logic for the Israeli wiki-format law corpus (sprint
2026-08-04-defs-il, gate I1: "the whole Israeli corpus loads").

Split out of `ingest_wiki_corpus_cli.py` (style gate: files under 300
lines) -- this module holds the per-file/per-directory ingestion logic with
NO `argparse`/process concerns; the CLI module is a thin wrapper that adds
arg parsing, DB engine setup, and the measured (wall time / peak memory)
summary print.

Reuses `app.definition_links.ingest.ingest_wiki_law` UNCHANGED (manager
ruling M3) -- this module never edits that function, only calls it once per
`.wiki` file. Modeled on `ingest_us_statutes_cli.py`'s `_FileResult` /
"continue past one bad file, never abort the batch" honesty discipline, per
the same manager ruling.

Corpus layout (recon dossier §3, `/Users/nerya/AI for others/israeli-laws-
wiki/data/laws`): each `<title>.wiki` has a sibling `<title>.meta.json`
carrying a `"law_title"` field. The `Document.title` passed to
`ingest_wiki_law` comes from `law_title`, NEVER from the filename (filenames
can be truncated/escaped for filesystem-safety; `law_title` is the clean
source value) -- matches this codebase's existing "no fabricated guess"
discipline (e.g. `profiles.get_profile` raises rather than silently falling
back). A `.wiki` file with no matching `.meta.json`, or a `.meta.json` that
fails to parse or has no `"law_title"`, is a per-file FAILURE with a named
reason -- the run continues to the next file, never aborts the batch.

**Ruling M6 (`--skip-existing-titles`, default OFF):** the bulk run's
headline numbers must stay pure `created` counts, matching the honesty
standard of the US 2,045,897-row run. `ingest_wiki_law` itself has no
idempotency (unlike `ingest_us_statute_rows`), so an opt-in flag lets a
caller skip files whose `law_title` already has a `Document` row for the
same `(repository_id, matter_id)` -- reported under its own counter
(`skipped_existing_count`/`skipped_existing_titles`), never folded into
`files_processed`/`total_articles`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.definition_links.ingest import ingest_wiki_law
from app.models.document import Document

DEFAULT_JURISDICTION = "IL"


@dataclass
class _FileResult:
    """Outcome of ingesting (or skipping) ONE `.wiki` file."""

    ok: bool
    error: str | None = None
    skipped_existing: bool = False
    title: str | None = None
    document_id: str | None = None
    article_count: int = 0


@dataclass
class BulkSummary:
    """Outcome of one full `--input-dir` bulk run -- the per-file honesty
    report gate I1 asks for (files found/processed/failed with reasons,
    total articles), plus the M6 skip-existing counter kept separate from
    `files_processed`/`total_articles` so it can never be conflated with
    genuinely new `created` rows."""

    files_found: int = 0
    files_processed: int = 0
    files_failed: list[tuple[str, str]] = field(default_factory=list)
    total_articles: int = 0
    skipped_existing_count: int = 0
    skipped_existing_titles: list[str] = field(default_factory=list)


def _resolve_law_title(wiki_path: Path) -> tuple[str | None, str | None]:
    """Return `(title, error)` -- exactly one is non-`None`.

    Title comes from the sibling `<stem>.meta.json`'s `"law_title"` field,
    never the filename. `wiki_path.stem` strips only the trailing `.wiki`
    suffix (real corpus filenames may contain other dots, e.g. "...עד שעה
    23.00.wiki"), so `stem + ".meta.json"` is the correct sibling name.
    """
    meta_path = wiki_path.with_name(f"{wiki_path.stem}.meta.json")

    if not meta_path.is_file():
        return None, f"no matching metadata file: '{meta_path.name}'"

    try:
        raw = meta_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"could not parse metadata file '{meta_path.name}': {exc}"

    if not isinstance(data, dict):
        return None, f"metadata file '{meta_path.name}' is not a JSON object"

    title = data.get("law_title")
    if not isinstance(title, str) or not title.strip():
        return None, f"metadata file '{meta_path.name}' has no 'law_title' field"

    return title, None


def _title_already_ingested(session: Session, *, repository_id: str, matter_id: str, title: str) -> bool:
    existing = session.execute(
        select(Document.id).where(
            Document.repository_id == repository_id,
            Document.matter_id == matter_id,
            Document.title == title,
        )
    ).first()
    return existing is not None


def _ingest_one_file(
    session: Session,
    wiki_path: Path,
    *,
    repository_id: str,
    matter_id: str,
    jurisdiction: str = DEFAULT_JURISDICTION,
    skip_existing_titles: bool = False,
    print_progress: bool = True,
) -> _FileResult:
    """Ingest ONE `.wiki` file via `ingest_wiki_law`. Never raises for a
    per-file problem (missing/bad metadata, a parse error) -- always
    returns a `_FileResult` so the bulk loop can report and continue."""
    title, error = _resolve_law_title(wiki_path)
    if error is not None:
        return _FileResult(ok=False, error=error)

    if skip_existing_titles and _title_already_ingested(
        session, repository_id=repository_id, matter_id=matter_id, title=title
    ):
        if print_progress:
            print(f"ingest-wiki-corpus: SKIPPING '{wiki_path.name}' -- title already ingested: {title}")
        return _FileResult(ok=True, skipped_existing=True, title=title)

    try:
        wiki_text = wiki_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _FileResult(ok=False, error=f"could not read '{wiki_path}': {exc}", title=title)

    try:
        result = ingest_wiki_law(
            session,
            repository_id=repository_id,
            matter_id=matter_id,
            title=title,
            wiki_text=wiki_text,
            jurisdiction=jurisdiction,
        )
    except Exception as exc:  # noqa: BLE001 - any ingest failure is a per-file, non-fatal outcome
        session.rollback()
        return _FileResult(ok=False, error=f"ingest_wiki_law failed: {exc}", title=title)

    article_count = len(result["article_ids"])
    if print_progress:
        print(
            f"ingest-wiki-corpus: '{wiki_path.name}' complete -- {article_count} "
            f"article(s), document {result['document_id']}, title '{title}'"
        )
    return _FileResult(ok=True, title=title, document_id=result["document_id"], article_count=article_count)


def run_bulk_ingest(
    session: Session,
    input_dir: Path,
    *,
    repository_id: str,
    matter_id: str,
    jurisdiction: str = DEFAULT_JURISDICTION,
    skip_existing_titles: bool = False,
    print_progress: bool = True,
) -> BulkSummary:
    """Ingest every `<title>.wiki` file directly inside `input_dir` in one
    pass. A single bad file (missing/unparseable metadata, an ingest
    failure) is recorded in `BulkSummary.files_failed` and the run
    CONTINUES to the next file -- it never aborts the batch."""
    files = sorted(input_dir.glob("*.wiki"))
    summary = BulkSummary(files_found=len(files))

    for path in files:
        result = _ingest_one_file(
            session,
            path,
            repository_id=repository_id,
            matter_id=matter_id,
            jurisdiction=jurisdiction,
            skip_existing_titles=skip_existing_titles,
            print_progress=print_progress,
        )

        if not result.ok:
            if print_progress:
                print(f"ingest-wiki-corpus: FAILED '{path.name}' -- {result.error}")
            summary.files_failed.append((path.name, result.error or "unknown error"))
            continue

        if result.skipped_existing:
            summary.skipped_existing_count += 1
            summary.skipped_existing_titles.append(result.title or path.name)
            continue

        summary.files_processed += 1
        summary.total_articles += result.article_count

    return summary
