"""Sprint 2026-08-04-defs-il, Planner-authored RED tests for gate I1 --
"the whole Israeli corpus loads": all 6,133 laws ingest through ONE
documented command with a measured report (rows, per-file failures WITH
REASONS, wall time, peak memory) -- the same honesty standard as the US
2,045,897-row `ingest_us_statutes_cli.py` run (manager ruling M3).

`app.definition_links.ingest_wiki_corpus_cli` does not exist yet --
ModuleNotFoundError is the expected RED signal for every test in this file.
Manager ruling M3: this is Phase-A work because it is a brand-new module
reusing `ingest.py::ingest_wiki_law` UNCHANGED (no frozen-module edits) --
modeled on `ingest_us_statutes_cli.py`'s per-file `_FileResult`
(ok/error/created/matched/skipped/skipped_reasons) shape and its
"continue past a single bad file, never abort the whole batch" honesty
discipline.

Design this test file pins:
  - `python -m app.definition_links.ingest_wiki_corpus_cli --input-dir <dir>
    --repository-id <id> --matter-id <id>` -- ingests every `<title>.wiki`
    file directly inside `<dir>` in one process, one command. Mirrors
    `ingest_us_statutes_cli.py`'s `--input-dir` bulk mode (same
    `argparse`/`get_settings()`/`make_engine()` shape).
  - Per real corpus layout (dossier §3): each `<title>.wiki` has a sibling
    `<title>.meta.json` carrying a `"law_title"` field -- THAT field, not
    the filename, is the `Document.title` passed to `ingest_wiki_law`
    (filenames can be truncated/escaped; `law_title` is the clean value).
  - **No fabricated title, ever** (matches this codebase's existing "no
    fabricated guess" discipline -- e.g. `profiles.get_profile` raises
    rather than silently falling back): a `.wiki` file with NO matching
    `.meta.json`, or a `.meta.json` that fails to parse or has no
    `"law_title"`, is recorded as a per-file FAILURE with a clear reason
    -- the run continues to the next file, it does not abort the batch and
    does not invent a title from the filename.
  - `jurisdiction="IL"` for every file (single jurisdiction, no per-file
    derivation needed -- unlike the US CLI's filename-derived
    `US-<postal>` codes).
  - Bulk-run summary: files found / files processed / files failed (each
    with its reason) / total articles ingested -- the per-file honesty
    shape gate I1 asks for. Wall time and peak memory are properties of
    the ACTUAL 6,133-file run the Developer explicitly invokes and reports
    (never part of `pytest` -- program standing constraint: no test reads
    or downloads the real corpus); this fixture-scale test only pins the
    command's per-file reporting CONTRACT, not the real corpus numbers.

Fixtures: `backend/tests/fixtures/wiki_corpus_sample/` holds two REAL,
complete, small law files copied verbatim from the read-only POC corpus
(`צו פיקוח על מחירי מצרכים ושירותים (רמת הפיקוח על חמאה)`, 5 articles;
`תקנות קרן גרמניה-ישראל למחקר ולפיתוח מדעי (פטור ממסים)`, 7 articles) each
with its real `.meta.json`, PLUS one deliberately SYNTHETIC (not real
corpus data -- clearly a test-only fixture, see its own `<שם>` line) `.wiki`
file with no `.meta.json` sibling at all, to exercise the missing-metadata
failure path without needing to hunt the real corpus for a naturally
occurring malformed pair.
"""

from __future__ import annotations

import pathlib

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_corpus_sample"


def test_fixture_dir_has_the_expected_real_and_synthetic_files():
    """Sanity guard on the fixtures themselves (not the RED signal for this
    file) -- if this fails, the fixture directory is missing/corrupt, not
    "feature not implemented yet"."""
    wiki_files = sorted(p.name for p in FIXTURE_DIR.glob("*.wiki"))
    assert len(wiki_files) == 3
    meta_files = sorted(p.name for p in FIXTURE_DIR.glob("*.meta.json"))
    assert len(meta_files) == 2  # the synthetic "no metadata" file has none


def test_cli_bulk_ingests_every_wiki_file_in_a_directory(db_session, matter_with_users):
    from sqlalchemy import select

    from app.definition_links import ingest_wiki_corpus_cli
    from app.models.article import Article
    from app.models.document import Document

    m = matter_with_users
    ingest_wiki_corpus_cli.main(
        [
            "--input-dir",
            str(FIXTURE_DIR),
            "--repository-id",
            m["repository_id"],
            "--matter-id",
            m["matter_id"],
        ]
    )

    documents = (
        db_session.execute(select(Document).where(Document.matter_id == m["matter_id"]))
        .scalars()
        .all()
    )
    titles = {d.title for d in documents}
    # Titles come from each file's real `.meta.json` "law_title" field, not
    # the raw filename -- both real fixture laws must be present.
    assert "צו פיקוח על מחירי מצרכים ושירותים (רמת הפיקוח על חמאה)" in titles
    assert "תקנות קרן גרמניה-ישראל למחקר ולפיתוח מדעי (פטור ממסים)" in titles
    assert all(d.jurisdiction == "IL" for d in documents)

    articles = (
        db_session.execute(select(Article).where(Article.matter_id == m["matter_id"]))
        .scalars()
        .all()
    )
    # 5 articles (חמאה) + 7 articles (קרן גרמניה) = 12 -- the synthetic
    # no-metadata file must NOT contribute any articles (it fails, per the
    # next test).
    assert len(articles) == 12


def test_cli_records_a_per_file_failure_for_a_wiki_file_with_no_matching_metadata_and_continues(
    db_session, matter_with_users
):
    """Honesty discipline (mirrors `ingest_us_statutes_cli.py`'s bulk
    mode): one bad file in the directory must be reported as a named
    per-file failure, WITHOUT aborting the rest of the batch and WITHOUT
    fabricating a title from the filename."""
    from sqlalchemy import select

    from app.definition_links import ingest_wiki_corpus_cli
    from app.models.document import Document

    m = matter_with_users
    exit_code = ingest_wiki_corpus_cli.main(
        [
            "--input-dir",
            str(FIXTURE_DIR),
            "--repository-id",
            m["repository_id"],
            "--matter-id",
            m["matter_id"],
        ]
    )

    # At least one file failed (the synthetic no-metadata file) -> the
    # process must signal that in its exit code, same discipline as
    # `ingest_us_statutes_cli.py`'s `_run_bulk`.
    assert exit_code != 0

    # The two REAL, well-formed files must still have been ingested --
    # the bad file must not have aborted the whole run.
    documents = (
        db_session.execute(select(Document).where(Document.matter_id == m["matter_id"]))
        .scalars()
        .all()
    )
    assert len(documents) == 2

    # No document was created from the fabricated/guessed filename of the
    # synthetic bad file -- it must be ABSENT, not present-with-a-wrong-title.
    titles = {d.title for d in documents}
    assert "חוק ללא מטא-דאטה תואמת (תקול)" not in titles


def test_cli_reports_files_found_processed_failed_and_total_articles(
    db_session, matter_with_users, capsys
):
    """The measured per-file honesty report gate I1 asks for -- files
    found/processed/failed and a total-articles count must appear
    somewhere in the command's own stdout summary, the same "real measured
    report" shape `ingest_us_statutes_cli.py` prints at the end of its
    bulk run."""
    from app.definition_links import ingest_wiki_corpus_cli

    m = matter_with_users
    ingest_wiki_corpus_cli.main(
        [
            "--input-dir",
            str(FIXTURE_DIR),
            "--repository-id",
            m["repository_id"],
            "--matter-id",
            m["matter_id"],
        ]
    )

    out = capsys.readouterr().out
    assert "files found:" in out
    assert "files processed:" in out
    assert "files failed:" in out
