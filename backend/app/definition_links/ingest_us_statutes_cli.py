"""`ingest-us-statutes` CLI (sprint 2026-08-02-us-state-law, item 5, gate
G6): "All 109 dataset files ingest through one documented command."

`python -m app.definition_links.ingest_us_statutes_cli --input <parquet>
--repository-id <id> --matter-id <id> --title <str> --jurisdiction <code>`
reads ONE local Parquet file and ingests it via
`app.definition_links.ingest_us_statutes.ingest_us_statute_rows` -- this CLI
is a thin parquet-to-rows adapter over that function, not a second
implementation of the ingest logic. Mirrors `app/definition_links/cli.py`'s
existing `argparse`/`get_settings()`/`make_engine()` shape (same "reads
`LEXGRAPH_DATABASE_URL`" convention).

**Streaming, not whole-file-in-memory** (ruling R6: the CLI must be capable
of the full 109-file run, some of which are hundreds of thousands of rows):
the file is read in row-group batches via
`pyarrow.parquet.ParquetFile.iter_batches`, each batch converted to a list
of row dicts and handed to `ingest_us_statute_rows` in turn, rather than
materializing the whole file with `read_table()` up front. Every batch's
row/skip counts are printed as they complete, so progress is observable on
a long-running multi-hundred-thousand-row file, and the process's own exit
code makes a whole-file failure (missing/corrupt input) visible to a caller
scripting the 109-file bulk run.

**Resumability**: delegates entirely to `ingest_us_statute_rows`'s own
idempotency (same `(repository_id, matter_id, title)` reuses the same
`Document`; same `(document_id, section_number)` reuses the same `Article`)
-- re-running this exact command against the exact same file a second time
creates no duplicate rows.

**Running all 109 files** ("one documented command" per G6): invoke this
same command once per file, e.g.:

    for f in /path/to/open-us-law/*.parquet; do
        python -m app.definition_links.ingest_us_statutes_cli \\
            --input "$f" \\
            --repository-id "$REPOSITORY_ID" \\
            --matter-id "$MATTER_ID" \\
            --title "$(basename "$f" .parquet)" \\
            --jurisdiction "$JURISDICTION_FOR_FILE" \\
        || echo "FAILED: $f" >> failures.log
    done

See `docs/RUNBOOK.md` for the full recipe (jurisdiction-per-filename
mapping, resuming after a partial run).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pyarrow.parquet as pq

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.services.validation import ValidationError

# Registers every ORM model class against `app.db.Base` (mirrors
# `app/definition_links/cli.py`'s own convention) so this standalone
# entrypoint's session can query all mapped tables.
from app import models  # noqa: F401,E402

DEFAULT_BATCH_SIZE = 5000


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.definition_links.ingest_us_statutes_cli",
        description=(
            "Ingest one US statute Parquet file (vaquill/open-us-law dataset "
            "schema) into one Document, one Article + SourceSpan per row."
        ),
    )
    parser.add_argument("--input", required=True, help="path to a local .parquet file")
    parser.add_argument("--repository-id", required=True, help="repository to ingest into")
    parser.add_argument("--matter-id", required=True, help="matter to ingest into")
    parser.add_argument(
        "--title", required=True, help="title recorded on the created/reused Document"
    )
    parser.add_argument(
        "--jurisdiction",
        required=True,
        help="controlled-vocabulary jurisdiction code (e.g. US-DE, US-FED)",
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


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"ingest-us-statutes failed: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        parquet_file = pq.ParquetFile(input_path)
    except Exception as exc:  # pragma: no cover - defensive: corrupt/non-parquet input
        print(f"ingest-us-statutes failed: could not open '{input_path}': {exc}", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    session = session_factory()

    total_ingested = 0
    total_skipped = 0
    batch_count = 0
    document_id: str | None = None

    try:
        for batch in parquet_file.iter_batches(batch_size=args.batch_size):
            rows = batch.to_pylist()
            if not rows:
                continue
            batch_count += 1
            result = ingest_us_statute_rows(
                session,
                repository_id=args.repository_id,
                matter_id=args.matter_id,
                title=args.title,
                rows=rows,
                jurisdiction=args.jurisdiction,
            )
            document_id = result["document_id"]
            total_ingested += len(result["article_ids"])
            total_skipped += len(result["skipped_rows"])
            print(
                f"ingest-us-statutes: batch {batch_count} -- "
                f"{len(result['article_ids'])} row(s) ingested, "
                f"{len(result['skipped_rows'])} skipped "
                f"(running total: {total_ingested} ingested, {total_skipped} skipped)"
            )
    except (ValidationError, ValueError) as exc:
        print(f"ingest-us-statutes failed for '{input_path}': {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
        engine.dispose()

    if batch_count == 0:
        print(f"ingest-us-statutes failed: '{input_path}' contains no rows", file=sys.stderr)
        return 1

    print(
        f"ingest-us-statutes complete: {total_ingested} row(s) ingested, "
        f"{total_skipped} skipped, document {document_id}, from '{input_path}'"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
