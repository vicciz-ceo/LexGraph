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
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.enrich.pipeline import UnknownMatterError, run_enrichment

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
        help="user id recorded as the author of the model-suggested assertions",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    session = session_factory()
    try:
        created = run_enrichment(
            session,
            matter_id=args.matter_id,
            triggered_by_user_id=args.triggered_by_user_id,
        )
    except UnknownMatterError as exc:
        print(f"enrichment failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
        engine.dispose()

    print(
        f"enrichment complete: {len(created)} draft assertion(s) created "
        f"for matter {args.matter_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
