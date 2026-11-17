"""Enrichment CLI (Track B, item B1).

`python -m app.enrich.cli --matter-id <id> --triggered-by-user-id <id>`
runs one enrichment pass over source spans already stored in the local DB
for `--matter-id` (document acquisition/scraping is out of scope this
sprint -- ruling R7: "no file-ingest CLI, no txt/md/html parsing
pipeline") and writes draft `model_suggested` assertions via
`app.enrich.pipeline.run_enrichment`.

Reads `LEXGRAPH_DATABASE_URL` the same way `app.config.get_settings()`
does (rather than hardcoding a connection), so this CLI operates on
whatever sqlite file the caller's environment points at -- in tests, the
exact same file the `client`/`db_session` fixtures already use.

Failures are reported on stderr as `enrichment failed: ...` with exit
status 1, never as a traceback (audit finding pipeline:6): an unknown
matter, an unknown triggering user or one without a contributor, reviewer or
admin role in the matter, and every database the agent CLI's check
(`app.agent_database.open_database`) refuses: an unset or in-memory database
URL (another process can never see what it would write), a database file that
does not exist (nothing is created, review authoring:6), one without the
LexGraph tables, and one an older LexGraph created (it names the
`python -m app.migrate` command).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from app.agent_database import ConfigurationError, open_database
from app.config import get_settings
from app.db import make_session_factory
from app.enrich.pipeline import EnrichmentRefused, run_enrichment

# Registers every ORM model class against `app.db.Base` (mirrors
# `app.main.create_app()`'s own `from app import models` import) so this
# standalone entrypoint's session can query all mapped tables, not just
# the ones `app/enrich/pipeline.py` itself happens to import.
from app import models  # noqa: F401,E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.enrich.cli",
        description=(
            "Run the offline enrichment pass over spans already stored in "
            "the local DB for one matter."
        ),
    )
    parser.add_argument("--matter-id", required=True, help="matter to enrich")
    parser.add_argument(
        "--triggered-by-user-id",
        required=True,
        help=(
            "user id recorded as the author of the model-suggested assertions "
            "(needs a contributor, reviewer or admin role in the matter)"
        ),
    )
    return parser


def _fail(message: str) -> int:
    print(f"enrichment failed: {message}", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:  # checks before connecting: SQLite would create a missing file
        engine = open_database(get_settings().database_url)
    except ConfigurationError as exc:
        return _fail(str(exc))
    try:
        session = make_session_factory(engine)()
        try:
            created = run_enrichment(
                session,
                matter_id=args.matter_id,
                triggered_by_user_id=args.triggered_by_user_id,
            )
        finally:
            session.close()
    except EnrichmentRefused as exc:
        return _fail(str(exc))
    except SQLAlchemyError as exc:
        return _fail(f"database error: {exc}")
    finally:
        engine.dispose()

    print(
        f"enrichment complete: {len(created)} draft assertion(s) created "
        f"for matter {args.matter_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
