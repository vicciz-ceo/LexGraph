"""`ingest-us-statutes` CLI (sprint 2026-08-02-us-state-law, item 5, gate
G6): "All 109 dataset files ingest through one documented command."

Two modes, both funneling through the SAME per-file ingestion helper
(`_ingest_one_file`) -- neither mode is a second implementation of the ingest
logic, both are thin adapters over
`app.definition_links.ingest_us_statutes.ingest_us_statute_rows`:

  - **Single-file mode**: `--input <parquet> --repository-id <id>
    --matter-id <id> --title <str> --jurisdiction <code>` reads ONE local
    Parquet file. Mirrors `app/definition_links/cli.py`'s existing
    `argparse`/`get_settings()`/`make_engine()` shape (same "reads
    `LEXGRAPH_DATABASE_URL`" convention).
  - **Bulk directory mode** (wave-4 fix, QA cycle 2 gap): `--input-dir
    <dir> --repository-id <id> --matter-id <id>` ingests every `*.parquet`
    file directly inside `<dir>` in one process, one command -- the actual
    "ALL 109 dataset files ... through one documented command" gate G6 asks
    for, not a shell loop wrapped around a single-file invocation (the CLI
    had no filename -> jurisdiction mapping before this fix, so a shell loop
    needed one manually per invocation; QA also flagged that a shell loop
    aborts the WHOLE run on the first failing file unless the caller
    remembers `|| echo ... >> failures.log` on every single line). Title and
    jurisdiction are DERIVED from each filename
    (`us_<postal>_statutes.parquet` / `us_<postal>_constitutions.parquet`,
    e.g. `us_de_statutes.parquet` -> jurisdiction `US-DE`, title
    `us_de_statutes`; `us_federal_statutes.parquet` -> `US-FED`), validated
    against `app.services.jurisdiction.JURISDICTION_CODES` before that file
    is touched. **A single file failing (corrupt input, unrecognized
    filename, a raised `ValidationError`/`ValueError`) is recorded and the
    run CONTINUES to the next file** -- it does not abort the batch, which
    is exactly the mid-file-corruption reporting gap QA flagged. A final
    summary prints files processed, total rows ingested, total rows skipped
    (broken down by reason), and files failed (with reasons) -- the
    "real measured report" ruling R3 asks for at bulk-run scale. Process
    exit code is non-zero if at least one file failed, so the run is still
    scriptable, without ever giving up on the remaining files.

**Streaming, not whole-file-in-memory** (ruling R6: the CLI must be capable
of the full 109-file run, some of which are hundreds of thousands of rows):
each file is read in row-group batches via
`pyarrow.parquet.ParquetFile.iter_batches`, each batch converted to a list
of row dicts and handed to `ingest_us_statute_rows` in turn, rather than
materializing the whole file with `read_table()` up front. Every batch's
row/skip counts are printed as they complete, so progress is observable on
a long-running multi-hundred-thousand-row file.

**Resumability**: delegates entirely to `ingest_us_statute_rows`'s own
idempotency -- re-running this exact command (either mode) against the exact
same file(s) a second time creates no duplicate rows. In bulk mode, a file
that failed partway through a previous run can simply be re-run (as part of
a full `--input-dir` re-run, or narrowed to just that file with single-file
`--input`) -- already-ingested rows from its earlier partial pass are
reused, not duplicated.

See `docs/RUNBOOK.md` for the full recipe (the one documented bulk command,
filename -> jurisdiction mapping table, resuming after a partial run).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow.parquet as pq

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.services.jurisdiction import validate_jurisdiction
from app.services.validation import ValidationError

# Registers every ORM model class against `app.db.Base` (mirrors
# `app/definition_links/cli.py`'s own convention) so this standalone
# entrypoint's session can query all mapped tables.
from app import models  # noqa: F401,E402

DEFAULT_BATCH_SIZE = 5000

# `us_<code>_statutes.parquet` / `us_<code>_constitutions.parquet` -> the
# dataset's own real filename shape (verified against the vaquill/open-us-law
# listing). `<code>` is either a 2-letter postal code (`de`, `ca`, `dc`,
# `pr`, ...) or the literal `federal`.
_DOCUMENT_TYPES = ("statutes", "constitutions")


@dataclass
class _FileResult:
    """Outcome of ingesting one Parquet file, used by both CLI modes."""

    ok: bool
    error: str | None = None
    ingested: int = 0
    skipped: int = 0
    skipped_reasons: Counter = field(default_factory=Counter)
    document_id: str | None = None
    batch_count: int = 0


def derive_jurisdiction_and_title_from_filename(path: Path) -> tuple[str, str] | None:
    """Derive `(jurisdiction_code, title)` from a dataset filename shaped
    `us_<postal-or-federal>_<statutes|constitutions>.parquet`.

    Returns `None` if the filename does not match the dataset's naming
    convention (an unrecognized file in the directory) -- the caller is
    responsible for treating that as a per-file failure, not raising.
    """
    stem = path.stem  # e.g. "us_de_statutes"
    parts = stem.lower().split("_")
    if len(parts) != 3 or parts[0] != "us" or parts[2] not in _DOCUMENT_TYPES:
        return None

    code = parts[1]
    jurisdiction = "US-FED" if code == "federal" else f"US-{code.upper()}"
    return jurisdiction, stem


def _ingest_one_file(
    session,
    input_path: Path,
    *,
    repository_id: str,
    matter_id: str,
    title: str,
    jurisdiction: str,
    batch_size: int,
    print_progress: bool = True,
) -> _FileResult:
    """Ingest ONE local Parquet file via `ingest_us_statute_rows`, streamed
    in row-group batches. Never raises for a per-file problem (bad
    jurisdiction, corrupt file, empty file) -- always returns a `_FileResult`
    describing what happened, so callers (single-file or bulk mode) can
    report and, in bulk mode, continue to the next file."""
    if not input_path.is_file():
        return _FileResult(ok=False, error=f"input file not found: {input_path}")

    try:
        parquet_file = pq.ParquetFile(input_path)
    except Exception as exc:  # pragma: no cover - defensive: corrupt/non-parquet input
        return _FileResult(ok=False, error=f"could not open '{input_path}': {exc}")

    result = _FileResult(ok=True)

    try:
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            rows = batch.to_pylist()
            if not rows:
                continue
            result.batch_count += 1
            batch_result = ingest_us_statute_rows(
                session,
                repository_id=repository_id,
                matter_id=matter_id,
                title=title,
                rows=rows,
                jurisdiction=jurisdiction,
            )
            result.document_id = batch_result["document_id"]
            result.ingested += len(batch_result["article_ids"])
            result.skipped += len(batch_result["skipped_rows"])
            for skipped in batch_result["skipped_rows"]:
                result.skipped_reasons[skipped["reason"]] += 1
            if print_progress:
                print(
                    f"ingest-us-statutes: '{input_path.name}' batch {result.batch_count} -- "
                    f"{len(batch_result['article_ids'])} row(s) ingested, "
                    f"{len(batch_result['skipped_rows'])} skipped "
                    f"(running total: {result.ingested} ingested, {result.skipped} skipped)"
                )
    except (ValidationError, ValueError) as exc:
        session.rollback()
        return _FileResult(ok=False, error=str(exc))

    if result.batch_count == 0:
        return _FileResult(ok=False, error=f"'{input_path}' contains no rows")

    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.definition_links.ingest_us_statutes_cli",
        description=(
            "Ingest US statute Parquet file(s) (vaquill/open-us-law dataset "
            "schema) into one Document, one Article + SourceSpan per row -- "
            "either a single file (--input) or every file in a directory "
            "(--input-dir, jurisdiction/title derived per-file from its name)."
        ),
    )
    parser.add_argument("--input", help="path to a single local .parquet file")
    parser.add_argument(
        "--input-dir",
        help=(
            "directory of .parquet files to bulk-ingest in one run "
            "(mutually exclusive with --input); jurisdiction and title are "
            "derived from each file's name "
            "(us_<postal|federal>_<statutes|constitutions>.parquet)"
        ),
    )
    parser.add_argument("--repository-id", required=True, help="repository to ingest into")
    parser.add_argument("--matter-id", required=True, help="matter to ingest into")
    parser.add_argument(
        "--title",
        help=(
            "title recorded on the created/reused Document -- single-file "
            "mode only; bulk mode derives this per-file from its filename"
        ),
    )
    parser.add_argument(
        "--jurisdiction",
        help=(
            "controlled-vocabulary jurisdiction code (e.g. US-DE, US-FED) -- "
            "single-file mode only; bulk mode derives this per-file from its "
            "filename"
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "rows read per Parquet row-group batch (default "
            f"{DEFAULT_BATCH_SIZE}) -- keeps memory bounded on large state "
            "files instead of loading the whole file at once"
        ),
    )
    return parser


def _run_single_file(args: argparse.Namespace) -> int:
    if not args.title or not args.jurisdiction:
        print(
            "ingest-us-statutes failed: --title and --jurisdiction are "
            "required in single-file mode (--input)",
            file=sys.stderr,
        )
        return 1

    input_path = Path(args.input)
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    session = session_factory()

    try:
        result = _ingest_one_file(
            session,
            input_path,
            repository_id=args.repository_id,
            matter_id=args.matter_id,
            title=args.title,
            jurisdiction=args.jurisdiction,
            batch_size=args.batch_size,
        )
    finally:
        session.close()
        engine.dispose()

    if not result.ok:
        print(f"ingest-us-statutes failed for '{input_path}': {result.error}", file=sys.stderr)
        return 1

    print(
        f"ingest-us-statutes complete: {result.ingested} row(s) ingested, "
        f"{result.skipped} skipped, document {result.document_id}, from '{input_path}'"
    )
    return 0


def _run_bulk(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"ingest-us-statutes failed: input directory not found: {input_dir}", file=sys.stderr)
        return 1

    files = sorted(input_dir.glob("*.parquet"))
    if not files:
        print(f"ingest-us-statutes failed: no .parquet files found in {input_dir}", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    session = session_factory()

    files_processed = 0
    files_failed: list[tuple[str, str]] = []
    total_ingested = 0
    total_skipped = 0
    skipped_reasons: Counter = Counter()

    try:
        for path in files:
            derived = derive_jurisdiction_and_title_from_filename(path)
            if derived is None:
                reason = (
                    f"filename does not match 'us_<postal|federal>_"
                    f"<{'|'.join(_DOCUMENT_TYPES)}>.parquet'"
                )
                print(f"ingest-us-statutes: SKIPPING '{path.name}' -- {reason}", file=sys.stderr)
                files_failed.append((path.name, reason))
                continue

            jurisdiction, title = derived
            try:
                validate_jurisdiction(jurisdiction)
            except ValidationError as exc:
                print(f"ingest-us-statutes: SKIPPING '{path.name}' -- {exc}", file=sys.stderr)
                files_failed.append((path.name, str(exc)))
                continue

            result = _ingest_one_file(
                session,
                path,
                repository_id=args.repository_id,
                matter_id=args.matter_id,
                title=title,
                jurisdiction=jurisdiction,
                batch_size=args.batch_size,
            )

            if not result.ok:
                print(f"ingest-us-statutes: FAILED '{path.name}' -- {result.error}", file=sys.stderr)
                files_failed.append((path.name, result.error or "unknown error"))
                continue

            files_processed += 1
            total_ingested += result.ingested
            total_skipped += result.skipped
            skipped_reasons.update(result.skipped_reasons)
            print(
                f"ingest-us-statutes: '{path.name}' complete -- {result.ingested} "
                f"ingested, {result.skipped} skipped, jurisdiction {jurisdiction}, "
                f"document {result.document_id}"
            )
    finally:
        session.close()
        engine.dispose()

    print("ingest-us-statutes bulk run summary:")
    print(f"  files found:      {len(files)}")
    print(f"  files processed:  {files_processed}")
    print(f"  files failed:     {len(files_failed)}")
    for name, reason in files_failed:
        print(f"    - {name}: {reason}")
    print(f"  rows ingested:    {total_ingested}")
    print(f"  rows skipped:     {total_skipped}")
    for reason, count in skipped_reasons.most_common():
        print(f"    - {count}x: {reason}")

    return 1 if files_failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if bool(args.input) == bool(args.input_dir):
        print(
            "ingest-us-statutes failed: specify exactly one of --input "
            "(single file) or --input-dir (bulk directory mode)",
            file=sys.stderr,
        )
        return 1

    if args.input_dir:
        return _run_bulk(args)
    return _run_single_file(args)


if __name__ == "__main__":
    raise SystemExit(main())
