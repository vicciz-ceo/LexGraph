"""`ingest-wiki-corpus` CLI (sprint 2026-08-04-defs-il, item 1, gate I1:
"the whole Israeli corpus loads through one documented command with a
measured report -- the same standard as the US 2,045,897-row run").

`python -m app.definition_links.ingest_wiki_corpus_cli --input-dir <dir>
--repository-id <id> --matter-id <id> [--skip-existing-titles]` bulk-ingests
every `<title>.wiki` file directly inside `<dir>` in one process, one
command -- mirroring `ingest_us_statutes_cli.py`'s `--input-dir` bulk mode
(same `argparse`/`get_settings()`/`make_engine()` shape) and the "continue
past one bad file, report it, never abort the batch" honesty discipline.

Per-file ingestion logic (title resolution from each file's sibling
`<title>.meta.json`, calling `ingest.py::ingest_wiki_law` UNCHANGED) lives in
`ingest_wiki_corpus.py`, split out to keep this module -- and that one --
under the 300-line style gate. This module is the thin process-level wrapper:
arg parsing, DB engine/session setup, and the measured summary print (files
found/processed/failed with reasons, total articles, wall time, peak
memory -- I1's full reporting bar).

**Never part of `pytest`** (program standing constraint: no test reads or
downloads the real corpus) -- the actual 6,133-file run against
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws` is a separate,
explicitly-invoked deliverable.

**Peak memory unit (I1's honesty bar):** `resource.getrusage(...).ru_maxrss`
is BYTES on macOS/BSD and KIBIBYTES on Linux -- this module labels the unit
it actually observed (via `sys.platform`) rather than printing an ambiguous
raw number, and degrades gracefully (prints "unavailable") on a platform
where the `resource` module does not exist (e.g. Windows) instead of
crashing the whole run over a reporting nicety.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.definition_links.ingest_wiki_corpus import DEFAULT_JURISDICTION, BulkSummary, run_bulk_ingest

# Registers every ORM model class against `app.db.Base` (mirrors
# `app/definition_links/cli.py`'s own convention) so this standalone
# entrypoint's session can query all mapped tables.
from app import models  # noqa: F401,E402

try:
    import resource

    _PEAK_MEMORY_UNIT = "bytes" if sys.platform == "darwin" else "KiB (assumed Linux ru_maxrss unit)"
except ImportError:  # pragma: no cover - defensive: non-POSIX platform (e.g. Windows)
    resource = None  # type: ignore[assignment]
    _PEAK_MEMORY_UNIT = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.definition_links.ingest_wiki_corpus_cli",
        description=(
            "Bulk-ingest every <title>.wiki file in a directory (Israeli "
            "wiki-format law corpus) into one Document (jurisdiction=IL) + "
            "one Article/SourceSpan per parsed article, title taken from "
            "each file's sibling <title>.meta.json 'law_title' field."
        ),
    )
    parser.add_argument("--input-dir", required=True, help="directory of <title>.wiki + <title>.meta.json pairs")
    parser.add_argument("--repository-id", required=True, help="repository to ingest into")
    parser.add_argument("--matter-id", required=True, help="matter to ingest into")
    parser.add_argument(
        "--skip-existing-titles",
        action="store_true",
        default=False,
        help=(
            "opt-in, default OFF (manager ruling M6): skip a file whose "
            "law_title already has a Document row for this repository/"
            "matter, reported under its own counter -- never conflated "
            "with the 'created' totals. Off by default keeps a plain run's "
            "headline numbers pure created counts."
        ),
    )
    return parser


def _print_summary(summary: BulkSummary, *, wall_time_seconds: float) -> None:
    print("ingest-wiki-corpus bulk run summary:")
    print(f"  files found:          {summary.files_found}")
    print(f"  files processed:      {summary.files_processed}")
    print(f"  files failed:         {len(summary.files_failed)}")
    for name, reason in summary.files_failed:
        print(f"    - {name}: {reason}")
    print(f"  total articles ingested: {summary.total_articles}")
    print(f"  existing titles skipped: {summary.skipped_existing_count}")
    for title in summary.skipped_existing_titles:
        print(f"    - {title}")
    print(f"  wall time:            {wall_time_seconds:.3f}s")

    if resource is None:
        print("  peak memory:          unavailable (no 'resource' module on this platform)")
        return
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"  peak memory:          {peak} {_PEAK_MEMORY_UNIT}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"ingest-wiki-corpus failed: input directory not found: {input_dir}", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    session = session_factory()

    start = time.perf_counter()
    try:
        summary = run_bulk_ingest(
            session,
            input_dir,
            repository_id=args.repository_id,
            matter_id=args.matter_id,
            jurisdiction=DEFAULT_JURISDICTION,
            skip_existing_titles=args.skip_existing_titles,
        )
    finally:
        session.close()
        engine.dispose()
    wall_time_seconds = time.perf_counter() - start

    if summary.files_found == 0:
        print(f"ingest-wiki-corpus failed: no .wiki files found in {input_dir}", file=sys.stderr)
        return 1

    _print_summary(summary, wall_time_seconds=wall_time_seconds)

    return 1 if summary.files_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
