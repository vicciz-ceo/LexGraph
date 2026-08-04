"""US statute dataset ingestion (sprint 2026-08-02-us-state-law, item 5,
gate G6).

Ingests already-parsed row dicts from the `vaquill/open-us-law` HuggingFace
dataset schema (`act_id, citation, state, jurisdiction, section_number,
section_title, text, ...`) -- mirrors `app.definition_links.ingest
.ingest_wiki_law`'s shape (one `Document` per ingested file, one `Article` +
backing `SourceSpan` per section), but the input here is already-parsed row
dicts rather than raw wiki-marker text, so there is no `parse_articles` call:
each row maps directly to one Article.

`jurisdiction` is REQUIRED (keyword-only, no default) -- unlike
`ingest_wiki_law`'s `jurisdiction="IL"` default (which exists only for
Hebrew-test backward compatibility), this is a brand-new function with zero
existing call sites, so there is no backward-compatibility reason to accept
an unvalidated/missing jurisdiction, and gate G5 requires every ingested
document to carry a real, validated jurisdiction from the start.

**Wave 5b fix (QA cycle 3 bounce, defects 5/6): the idempotency key is now
`act_id`, not a composite of body fields.** Every prior key tried
(`section_number` alone; `+ chapter + section_title`; `+ section_title +
text`) was verified collision-free on ONE real file and then broken by the
NEXT real file:

  - wave-3's `(section_number, chapter, section_title)` dropped 647/21,649
    (3.0%) real DE rows with an empty `chapter`.
  - wave-4's `(section_number, section_title, text)` was verified
    collision-free on all 21,649 real DE rows, but QA cycle 3 found it
    silently MERGES genuinely different real sections that happen to share
    byte-identical cross-title boilerplate `text` under an equally generic
    `section_title` -- **9 collision groups / 11 rows lost in the real
    14,547-row `us_pa_statutes.parquet`** (e.g. `74 Pa.C.S. § 7` merged into
    `51 Pa.C.S. § 7`) and, far worse, **83 collision groups / 176 rows lost
    in the real 161,429-row `us_ca_statutes.parquet`** (California's
    `section_title` is *always* a bare `"Section N"` placeholder -- see
    `app.definition_links.us_profile`'s ruling R10 -- which makes the
    collision far more likely, not a rare fluke).

Rather than keep chasing a bigger tuple of body-derived fields (every one of
which is repeated dataset boilerplate somewhere in a 2M-row corpus), this
fix uses the dataset's OWN per-row identifier, `act_id` (e.g.
`"STATE_PA_T74_C7_S7"`, `"STATE_PA_T51_C7_S7"` -- note these two encode
their different source titles even though every other field collides).
**Verified directly against all 10 real state files already available
locally (570,397 rows total, including the two files -- PA and CA -- QA
cycle 3 proved the wave-4 key broken on): `act_id` is 100% non-null and
100% unique in EVERY file**, including `us_ca_statutes.parquet` (161,429
rows, the single largest file in the whole corpus) and `us_pa_statutes
.parquet` (14,547 rows). See the collision table in this sprint's developer
report for the full per-file measurement.

Because `act_id` is not itself a column on the `Article`/`SourceSpan`
schema (an additive-only surface, per ruling M1 -- this module does not own
either model file, so no column can be added), it cannot be looked up via a
`WHERE act_id = ...` clause the way `section_number`/`section_title`/`text`
were. Instead, `Article.id` (the existing primary key) is derived
DETERMINISTICALLY from `(document.id, act_id)` via `uuid.uuid5` -- the same
document + the same `act_id` always produces the same `Article.id`, so:

  - **Two genuinely different sections -> two Articles.** Different
    `act_id` (which is 100% unique per real file) means different derived
    `Article.id`; PA's `74 Pa.C.S. § 7` and `51 Pa.C.S. § 7` no longer
    collide despite sharing identical `(section_number, section_title,
    text)`, and neither do CA's `Cal. WIC § 7` / `Cal. INS § 7`.
  - **Re-ingest is still a no-op.** Re-running the exact same file (same
    `Document`, found by the existing `(repository_id, matter_id, title)`
    lookup, so it has the same `document.id` even across separate process
    runs) with the same `act_id` per row reproduces the identical
    `Article.id`, found via `session.get` and reused -- no duplicate.
  - **No mutation of fields other code depends on.** `Article.number`,
    `Article.heading`, and `Article.chapter` still store the row's real,
    unmodified `section_number`/`section_title`/`chapter` -- unlike the
    rejected alternative of encoding disambiguating data INTO one of those
    fields, which would have corrupted `matcher.py`'s `article.number ==
    definition.source_article_number` / `article.chapter ==
    definition.source_chapter` cross-reference matching, or
    `is_definitions_heading`'s heading-text matching (both operate on the
    row's real values elsewhere in the pipeline and are not owned by this
    module). `SourceSpan.quote_text` stays byte-identical to the row's real
    `text` in every other respect -- nothing synthetic is appended to it,
    since it is downstream input to definitions extraction (`pipeline.py`)
    and to evidence display; corrupting it to smuggle in a disambiguator
    would have traded one silent-merge bug for a silent-corruption one. The
    ONE exception (sprint 2026-08-04-defs-core-scope, item I8/M14) is the
    literal-`\n` line-break unescape applied below: some source files
    (verified against the real `us_ny_statutes.parquet` snapshot, 40,102/
    40,102 rows) store line breaks as the literal two-character sequence
    backslash + "n" rather than a real newline byte, which makes
    `us_profile.py`'s `_split_into_numbered_blocks` (`text.split("\n")`,
    a REAL newline) see the whole body as one unsplittable line and yields
    zero definition candidates corpus-wide. That normalization is applied
    here, at ingest, rather than in the shared `normalize_for_parsing` --
    this module has no IL/Hebrew call site, so the fix is off Hebrew's call
    path by construction, not merely untouched by today's test suite. It is
    a no-op for source files that already store real newlines (verified
    against `de_sample_rows.parquet`: 0/3 rows contain the literal
    sequence).

A row missing (or with `None`/empty) `act_id` cannot be identified at all --
`citation` came close to 100% but had 1 real duplicate pair in the one file
it was checked against (see wave-4 history above), so nothing else in the
row schema is trusted as a substitute. Such a row is SKIPPED and reported,
the same as a row missing `text` -- consistent with this module's existing
"never silently drop, always count" discipline. (Not observed in any of the
570,397 real rows checked across the 10 available state files -- `act_id`
looks to be a mandatory dataset column -- but the requirement here is "count
and report any skip", not "assume it can never happen".)

Error paths (all have RED tests):
  - a row missing (or with `None`/empty) required `"text"` is SKIPPED, not
    fatal -- collected into `result["skipped_rows"]` with a reason, every
    other row in the same batch still ingests.
  - a row missing (or with `None`/empty) required `"act_id"` is likewise
    SKIPPED and reported (new in wave 5b -- no prior key depended on
    `act_id` being present, so this skip condition did not exist before).
  - an unknown jurisdiction code raises `ValidationError` (same controlled
    vocabulary the API enforces, `app.services.jurisdiction
    .validate_jurisdiction`).
  - an empty `rows` list raises `ValueError` -- never a silent no-op that
    could be mistaken for "ingested, zero sections".

Return shape: `{"document_id", "article_ids", "created_article_ids",
"source_span_ids", "skipped_rows"}`. `article_ids`/`source_span_ids` cover
EVERY successfully-processed row (both newly-created articles and rows that
matched an already-ingested `act_id`), same as before this fix, so existing
callers/tests that only care about "how many rows came out the other end"
are unaffected. `created_article_ids` is NEW: the subset of `article_ids`
that were newly inserted by THIS call -- added so the bulk CLI's summary can
report "rows newly ingested" separately from "rows that matched an
already-ingested `act_id`" (QA cycle 3's Q3: the wave-4 CLI folded both into
one "rows ingested" count, which is exactly how an 11-row PA text collision
went unnoticed -- 14,547 reported vs 14,536 real `Article` rows in the DB).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.document import Document
from app.models.source_span import SourceSpan
from app.services.jurisdiction import validate_jurisdiction

# Namespace for deriving a stable, deterministic `Article.id` /
# `SourceSpan.id` from `(document_id, act_id)` via `uuid.uuid5` -- any fixed
# namespace works (uuid5 only requires it be stable across calls so the
# same input always reproduces the same output); `uuid.NAMESPACE_URL` is the
# standard library's own pre-defined constant, reused here rather than
# inventing a bespoke one.
_ARTICLE_ID_NAMESPACE = uuid.NAMESPACE_URL


def _derive_article_id(document_id: str, act_id: str) -> str:
    return str(uuid.uuid5(_ARTICLE_ID_NAMESPACE, f"lexgraph:us-statute-article:{document_id}:{act_id}"))


def _derive_source_span_id(document_id: str, act_id: str) -> str:
    return str(uuid.uuid5(_ARTICLE_ID_NAMESPACE, f"lexgraph:us-statute-span:{document_id}:{act_id}"))


def ingest_us_statute_rows(
    session: Session,
    *,
    repository_id: str,
    matter_id: str,
    title: str,
    rows: list[dict],
    jurisdiction: str,
) -> dict:
    """Ingest already-parsed US statute `rows` into one `Document`, one
    `Article` + backing `SourceSpan` per row.

    Returns `{"document_id": str, "article_ids": list[str],
    "created_article_ids": list[str], "source_span_ids": list[str],
    "skipped_rows": list[dict]}` -- `article_ids`/`source_span_ids` are in
    the same order as the successfully-ingested rows appear in `rows` and
    include BOTH newly-created and already-existing (matched) rows;
    `created_article_ids` is the subset that were newly inserted by this
    call; `skipped_rows` holds `{"act_id": ..., "reason": ...}` for every
    row that failed to ingest (never fatal to the rest of the batch).
    """
    validate_jurisdiction(jurisdiction)

    if not rows:
        raise ValueError(
            "ingest_us_statute_rows requires at least one row (got an empty list); "
            "an empty batch must fail loudly, not silently no-op"
        )

    document = session.execute(
        select(Document).where(
            Document.repository_id == repository_id,
            Document.matter_id == matter_id,
            Document.title == title,
        )
    ).scalar_one_or_none()

    if document is None:
        document = Document(
            id=str(uuid.uuid4()),
            repository_id=repository_id,
            matter_id=matter_id,
            title=title,
            jurisdiction=jurisdiction,
        )
        session.add(document)
        session.flush()

    article_ids: list[str] = []
    created_article_ids: list[str] = []
    source_span_ids: list[str] = []
    skipped_rows: list[dict] = []

    for row in rows:
        act_id = row.get("act_id")
        text = row.get("text")

        if not act_id:
            skipped_rows.append(
                {"act_id": act_id, "reason": "missing required 'act_id' column"}
            )
            continue

        if not text:
            skipped_rows.append(
                {"act_id": act_id, "reason": "missing required 'text' column"}
            )
            continue

        # M14/I8: unescape the literal `\n` two-character sequence to a
        # real newline byte before it becomes `SourceSpan.quote_text` --
        # see the module docstring's "ONE exception" paragraph. A no-op
        # when the row already stores real newlines.
        text = text.replace("\\n", "\n")

        chapter = row.get("chapter") or ""
        number = str(row.get("section_number"))
        heading = row.get("section_title") or ""

        # Idempotency key (wave 5b fix, QA cycle 3 bounce): the dataset's
        # own per-row `act_id`, verified 100% unique across all 570,397
        # real rows in the 10 real state files available locally (incl. PA
        # and CA, the two files that broke the wave-4 body-field key -- see
        # module docstring). `Article.id` is derived deterministically from
        # `(document.id, act_id)` so the same row, re-ingested into the
        # same document, always reproduces the same id -- found via a
        # primary-key lookup and reused rather than re-inserted.
        article_id = _derive_article_id(document.id, act_id)
        existing_article = session.get(Article, article_id)

        if existing_article is not None:
            article_ids.append(existing_article.id)
            source_span_ids.append(existing_article.source_span_id)
            continue

        source_span = SourceSpan(
            id=_derive_source_span_id(document.id, act_id),
            document_id=document.id,
            matter_id=matter_id,
            quote_text=text,
        )
        session.add(source_span)
        session.flush()

        article = Article(
            id=article_id,
            document_id=document.id,
            matter_id=matter_id,
            source_span_id=source_span.id,
            number=number,
            heading=heading,
            chapter=chapter,
        )
        session.add(article)
        session.flush()

        article_ids.append(article.id)
        created_article_ids.append(article.id)
        source_span_ids.append(source_span.id)

    session.commit()

    return {
        "document_id": document.id,
        "article_ids": article_ids,
        "created_article_ids": created_article_ids,
        "source_span_ids": source_span_ids,
        "skipped_rows": skipped_rows,
    }
