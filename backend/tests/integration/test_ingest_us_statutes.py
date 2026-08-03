"""RED tests for the US dataset ingester (sprint 2026-08-02-us-state-law,
director decision #2, gate G6): "All 109 dataset files ingest through one
documented command ... a real measured report."

Ruling R6: NO test here downloads the corpus. Real rows, committed as a
small fixture (`backend/tests/fixtures/us_statutes/de_sample_rows.json` /
`.parquet` -- see that directory's `README.md` for full provenance), stand
in for the 1.1 GB real dataset. The full 109-file bulk run (G6/R3's
"measured deliverable": rows ingested, wall time, peak memory, per-file
failures) is a separate, explicitly-invoked, NOT-part-of-`pytest`
deliverable the Developer runs and reports on directly -- not something a
routine test can assert on without downloading 1.1 GB.

Design calls this test pins:

  - New function `app.definition_links.ingest_us_statutes.
    ingest_us_statute_rows(session, *, repository_id, matter_id, title,
    rows, jurisdiction) -> dict` -- parallel in shape to `ingest.
    ingest_wiki_law`, but the input is already-parsed row dicts (this
    dataset's schema: `act_id, citation, section_number, section_title,
    text, ...`) rather than raw wiki text. Returns
    `{"document_id", "article_ids", "source_span_ids", "skipped_rows"}`
    (the last one new -- see the malformed-row test below; `ingest_wiki_law`
    has no analogous "a row failed to parse" case since wiki-marker parsing
    either finds an `@ N.` line or it doesn't produce an article at all).
  - ONE Document per ingested file/title (`title` is caller-supplied, e.g.
    "Delaware Code -- Statutes"), one Article + backing SourceSpan per row
    -- `Article.number = row["section_number"]`, `Article.heading =
    row["section_title"]`, `SourceSpan.quote_text = row["text"]`.
  - `jurisdiction` is REQUIRED (keyword-only, no default) -- unlike
    `ingest_wiki_law`'s `jurisdiction="IL"` default (which exists ONLY for
    Hebrew-test backward compatibility, ruling R2), this is a brand new
    function with zero existing call sites, so there is no
    backward-compatibility reason to default it, and G5 requires every
    ingested document to carry a real jurisdiction from the start.
  - Idempotent re-ingest of the same `act_id` twice creates no duplicate
    Article/SourceSpan rows (mirrors `run_definition_linking`'s existing
    idempotency discipline).
  - A row missing the required `"text"` key (or with `None` there) is
    SKIPPED, not fatal -- its `act_id` is collected into
    `result["skipped_rows"]` with a reason, and every OTHER row in the same
    batch still ingests (a bad row must not sink an entire 20K-row state
    file's ingest).
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_JSON = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _load_rows() -> list[dict]:
    return json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))


def test_ingest_us_statute_rows_creates_one_document_and_one_article_per_row(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.article import Article
    from app.models.document import Document

    m = matter_with_users
    rows = _load_rows()

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (test fixture)",
        rows=rows,
        jurisdiction="US-DE",
    )

    assert len(result["article_ids"]) == len(rows) == 3
    assert result["skipped_rows"] == []

    document = db_session.get(Document, result["document_id"])
    assert document.jurisdiction == "US-DE"

    articles = [db_session.get(Article, aid) for aid in result["article_ids"]]
    numbers = {a.number for a in articles}
    assert numbers == {"796", "6060", "5227"}


def test_ingest_us_statute_rows_populates_source_spans_with_the_real_text(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.article import Article
    from app.models.source_span import SourceSpan

    m = matter_with_users
    rows = _load_rows()
    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (test fixture)",
        rows=rows,
        jurisdiction="US-DE",
    )
    articles = [db_session.get(Article, aid) for aid in result["article_ids"]]
    definitions_article = next(a for a in articles if a.number == "796")
    span = db_session.get(SourceSpan, definitions_article.source_span_id)
    assert "Affiliate" in span.quote_text


def test_ingest_us_statute_rows_is_idempotent_on_repeated_ingest(db_session, matter_with_users):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.article import Article
    from sqlalchemy import select

    m = matter_with_users
    rows = _load_rows()
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (test fixture)",
        rows=rows,
        jurisdiction="US-DE",
    )
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (test fixture)",
        rows=rows,
        jurisdiction="US-DE",
    )
    total_articles = db_session.execute(
        select(Article).where(Article.matter_id == m["matter_id"])
    ).scalars().all()
    assert len(total_articles) == 3  # not 6 -- the second ingest was a no-op


def test_ingest_us_statute_rows_skips_a_row_missing_the_text_column(db_session, matter_with_users):
    """Error path: a malformed row (missing/None `"text"`) must not sink
    the whole batch -- it is skipped and reported, the other rows still
    ingest."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows

    m = matter_with_users
    rows = _load_rows()
    broken_row = dict(rows[0])
    broken_row["text"] = None
    broken_row["act_id"] = "STATE_DE_BROKEN_ROW"

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (test fixture, with a broken row)",
        rows=[broken_row] + rows,
        jurisdiction="US-DE",
    )

    assert len(result["article_ids"]) == 3  # the 3 good rows, not 4
    assert len(result["skipped_rows"]) == 1
    assert result["skipped_rows"][0]["act_id"] == "STATE_DE_BROKEN_ROW"


def test_ingest_us_statute_rows_rejects_an_unknown_jurisdiction_code(db_session, matter_with_users):
    """Error path: G5's controlled vocabulary applies here too -- an
    ingest command is a write path, same as the API."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.services.validation import ValidationError

    m = matter_with_users
    rows = _load_rows()
    try:
        ingest_us_statute_rows(
            db_session,
            repository_id=m["repository_id"],
            matter_id=m["matter_id"],
            title="Nowhere Statutes",
            rows=rows,
            jurisdiction="XX-NOPE",
        )
        raised = False
    except ValidationError:
        raised = True
    assert raised


def test_ingest_us_statute_rows_rejects_an_empty_row_list(db_session, matter_with_users):
    """Error path: an empty batch (e.g. a state file that failed to
    download/parse upstream) must be a clear, explicit failure -- never a
    silent no-op that could be mistaken for "ingested, zero sections"."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows

    m = matter_with_users
    try:
        ingest_us_statute_rows(
            db_session,
            repository_id=m["repository_id"],
            matter_id=m["matter_id"],
            title="Empty Statutes",
            rows=[],
            jurisdiction="US-DE",
        )
        raised = False
    except ValueError:
        raised = True
    assert raised
