"""RED tests for the ONE documented ingest command (sprint
2026-08-02-us-state-law, gate G6): "All 109 dataset files ingest through
one documented command."

Reads the REAL, small, committed local Parquet fixture
`backend/tests/fixtures/us_statutes/de_sample_rows.parquet` (round-trip
verified byte-identical to `de_sample_rows.json` -- see that directory's
README) -- never downloads anything (ruling R6).

`pyarrow` is NOT installed in `backend/.venv` as of this sprint (Planner
preflight: `ModuleNotFoundError` verified directly) -- these tests are
expected RED via that ModuleNotFoundError until the Developer adds
`pyarrow` as a real dependency for this item (per the sprint contract, the
Planner does not add production/CLI dependencies itself).

Design calls this test pins:
  - `python -m app.definition_links.ingest_us_statutes_cli --input
    <parquet-file> --repository-id <id> --matter-id <id> --title <str>
    --jurisdiction <code>` -- one process, one file in, one Document out.
    Mirrors `app/definition_links/cli.py`'s existing
    `argparse`/`get_settings()`/`make_engine()` shape (same "reads
    `LEXGRAPH_DATABASE_URL`" convention, so tests can point it at the same
    sqlite file the `client`/`db_session` fixtures already use).
  - Reads the parquet file via `pyarrow.parquet.read_table(path).to_pylist()`
    and calls the already-tested `app.definition_links.ingest_us_statutes.
    ingest_us_statute_rows` with the result -- this CLI is a thin
    parquet-to-rows adapter over that function, not a second
    implementation of the ingest logic.
  - "One documented command" for ALL 109 files means this same command is
    invoked once per file (an outer shell loop / Makefile target over the
    109 filenames is the documented wrapper -- not a new bespoke
    orchestration module) -- the per-file measured report (G6/R3: rows
    ingested, wall time, peak memory, per-file failures) is a separate,
    explicitly-invoked deliverable the Developer produces by actually
    running it, not something this fixture-scale test can measure.
  - Resumability: re-running the SAME command against the SAME file a
    second time must not create duplicate Articles (delegates straight to
    `ingest_us_statute_rows`'s already-tested idempotency).
"""

from __future__ import annotations

import pathlib

FIXTURE_PARQUET = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.parquet"
)


def test_fixture_parquet_file_exists_and_is_nonzero_bytes():
    """Sanity guard on the fixture itself (not the RED signal for this
    file) -- if this fails, the fixture is missing/corrupt, not "feature
    not implemented yet"."""
    assert FIXTURE_PARQUET.exists()
    assert FIXTURE_PARQUET.stat().st_size > 0


def test_cli_ingests_a_local_parquet_file_end_to_end(db_session, matter_with_users, monkeypatch):
    from app.definition_links import ingest_us_statutes_cli
    from app.models.article import Article
    from sqlalchemy import select

    m = matter_with_users
    exit_code = ingest_us_statutes_cli.main(
        [
            "--input",
            str(FIXTURE_PARQUET),
            "--repository-id",
            m["repository_id"],
            "--matter-id",
            m["matter_id"],
            "--title",
            "Delaware Code -- Statutes (CLI test fixture)",
            "--jurisdiction",
            "US-DE",
        ]
    )
    assert exit_code == 0

    articles = db_session.execute(
        select(Article).where(Article.matter_id == m["matter_id"])
    ).scalars().all()
    assert len(articles) == 3


def test_cli_rerun_against_the_same_file_is_resumable_and_creates_no_duplicates(
    db_session, matter_with_users
):
    from app.definition_links import ingest_us_statutes_cli
    from app.models.article import Article
    from sqlalchemy import select

    m = matter_with_users
    args = [
        "--input",
        str(FIXTURE_PARQUET),
        "--repository-id",
        m["repository_id"],
        "--matter-id",
        m["matter_id"],
        "--title",
        "Delaware Code -- Statutes (CLI test fixture)",
        "--jurisdiction",
        "US-DE",
    ]
    assert ingest_us_statutes_cli.main(args) == 0
    assert ingest_us_statutes_cli.main(args) == 0  # rerun -- must not error or duplicate

    articles = db_session.execute(
        select(Article).where(Article.matter_id == m["matter_id"])
    ).scalars().all()
    assert len(articles) == 3


def test_cli_exits_non_zero_for_a_missing_input_file(matter_with_users):
    """Error path: an oversized/missing/corrupt file must fail loudly
    (non-zero exit, clear stderr), never silently succeed with 0 rows."""
    from app.definition_links import ingest_us_statutes_cli

    m = matter_with_users
    exit_code = ingest_us_statutes_cli.main(
        [
            "--input",
            "/nonexistent/path/does_not_exist.parquet",
            "--repository-id",
            m["repository_id"],
            "--matter-id",
            m["matter_id"],
            "--title",
            "Nowhere",
            "--jurisdiction",
            "US-DE",
        ]
    )
    assert exit_code != 0
