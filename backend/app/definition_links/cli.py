"""`link-definitions` CLI (sprint 2026-07-29-definition-links, item DL9,
ruling M6: parity with `app/enrich/cli.py`).

`python -m app.definition_links.cli --matter-id <id> --triggered-by-user-id
<id>` runs one definition-linking pass over Articles already ingested (via
`app.definition_links.ingest.ingest_wiki_law`) for `--matter-id`, and
writes `proposed`, `system_generated` `USES_DEFINITION`/`DERIVES_FROM_LAW`
assertions via `app.definition_links.pipeline.run_definition_linking`.

Created assertions are visible via the EXISTING `GET /api/v1/assertions`
route -- no new router this sprint (M6: API route is optional stretch).

Reads `LEXGRAPH_DATABASE_URL` the same way `app.config.get_settings()`
does, so this CLI operates on whatever sqlite file the caller's
environment points at -- in tests, the exact same file the
`client`/`db_session` fixtures already use.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.definition_links.pipeline import UnknownMatterError, run_definition_linking

# Registers every ORM model class against `app.db.Base` (mirrors
# `app/enrich/cli.py`'s own convention) so this standalone entrypoint's
# session can query all mapped tables, not just the ones
# `app/definition_links/pipeline.py` itself happens to import.
from app import models  # noqa: F401,E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.definition_links.cli",
        description=(
            "Run the deterministic definition-linking pass over Articles "
            "already ingested in the local DB for one matter."
        ),
    )
    parser.add_argument("--matter-id", required=True, help="matter to link definitions for")
    parser.add_argument(
        "--triggered-by-user-id",
        required=True,
        help="user id recorded as the author of the system-generated assertions",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    session = session_factory()
    try:
        result = run_definition_linking(
            session,
            matter_id=args.matter_id,
            triggered_by_user_id=args.triggered_by_user_id,
        )
    except UnknownMatterError as exc:
        print(f"link-definitions failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
        engine.dispose()

    print(
        f"link-definitions complete: {len(result['created_assertions'])} proposed "
        f"assertion(s), {len(result['created_definitions'])} definition(s) created, "
        f"{len(result['skipped_degraded_article_ids'])} degraded article(s) skipped "
        f"for matter {args.matter_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
