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

Idempotency: re-ingesting the same `(repository_id, matter_id, title)` reuses
the existing `Document` row (rather than creating a second one for what is
semantically the same file), and re-ingesting a row whose section identity
already has an `Article` under that `Document` reuses the existing
`Article`/`SourceSpan` rather than inserting a duplicate. This dataset's rows
are keyed by `act_id`, but `act_id` is not itself part of the `Article`
schema (an additive-only surface, per ruling M1) -- and bare `section_number`
alone is NOT unique either: real statute files legitimately repeat a bare
section number across different titles/chapters within one file (e.g. two
unrelated "§ 796"s from Title 5 and Title 29). Keying idempotency on
`(document_id, section_number)` alone therefore treats a genuinely different
section as "already ingested" and silently drops it -- real data loss with no
trace in `skipped_rows`.

**Wave-4 fix (sprint 2026-08-02-us-state-law, item 5, QA cycle 2, ruling
R7(b)):** wave-3's key was `(document_id, section_number, chapter,
section_title)`, and any row with a missing/empty `chapter` was
unconditionally SKIPPED because bare `section_number` alone can collide
across titles/chapters. That traded a silent merge for an explicit skip, but
it still lost real law: on the real `us_de_statutes.parquet`, 647 of 21,649
rows (3.0%) have an empty `chapter` -- and every one of them was dropped,
even though `citation` (e.g. `"5 Del. C. § 796"`), the dataset's own
canonical unique legal identifier, is present and non-empty in 100% of real
rows (0% null/empty, verified against the live file).

The obvious fix ("re-key on `citation`") was checked against the real file
before committing to it, per the brief's own instruction to verify
uniqueness rather than assume it: **`citation` is NOT 100% unique** --
`us_de_statutes.parquet` has exactly ONE real duplicate pair
(`"29 Del. C. § 7905A"`, shared by `STATE_DE_T29_C79_SI_S7905A` and
`STATE_DE_T29_C79A_S7905A` -- two genuinely different sections, chapters
`"79"` vs `"79A"`). Keying blindly on `citation` alone would have silently
merged that real pair. Worse, real-data validation of wave-3's own
"primary" `(section_number, chapter, section_title)` key surfaced a second,
larger, PRE-EXISTING collision class inherited from wave-3, not introduced
by empty chapters at all: `chapter` codes are **not unique across titles**
-- e.g. Title 24 Chapter 44 and Title 18 Chapter 44 both exist in the same
file, so `STATE_DE_T24_C44_SI_S4401` ("§ 4401. Short title.") and
`STATE_DE_T18_C44_S4401` ("§ 4401. Short title.") share an IDENTICAL
`(section_number="4401", chapter="44", section_title="§ 4401. Short
title.")` key despite being two unrelated sections of two unrelated titles
with different citations and different body text. Measured on the real
file: **179 such cross-title collisions, silently merging 293 genuinely
different rows down to 179 Articles** -- exactly the "two genuinely
different sections must produce two Articles, even with equal
section_number" requirement this fix is required to hold, broken by the
inherited wave-3 key on real data.

Both findings point to the same conclusion: neither `chapter` nor bare
`citation` is a safe sole disambiguator on this real dataset. What IS
verified 100% collision-free across all 21,649 real DE rows (including the
one row where `citation` itself repeats, since its two rows also differ in
heading/text) is `(section_number, section_title, text)` together -- the
section's own number, heading, AND actual legal body text. Two distinct real
sections essentially never share byte-identical body text; re-ingesting the
exact same row always reproduces the exact same text, so idempotency holds.
The lookup key is therefore
**`(document_id, section_number, section_title, quote_text)`** (`quote_text`
lives on the row's `SourceSpan`, so the lookup joins to it) -- applied
uniformly to every row with `text`, independent of whether `chapter` is
present. `Article.number`/`Article.chapter` still store the row's real,
unmodified `section_number`/`chapter` values (including an honestly empty
`chapter` when the source row has none) -- this key does not require
inventing a synthetic stand-in for either field, so `Article.number` keeps
matching "Section N" cross-references via `matcher.py` and
`Article.chapter` keeps its real value for chapter-scoped definition
matching, both completely unchanged from before this fix. No schema change
is needed (no `citation` column exists on `Article`, and this module does
not own the model file) since `quote_text` already exists on the
already-persisted `SourceSpan`.

`citation`'s role in this design is now purely evidentiary, not structural:
its 100%-non-empty real-data rate is what proves nearly every real row
carries a genuine, addressable legal identity worth keeping (motivating
"stop skipping empty-chapter rows" in the first place), while its
NOT-quite-100%-unique real-data rate is exactly why it was rejected as the
literal lookup key in favor of the independently-verified-unique
`(section_number, section_title, text)` triple.

Error paths (all have RED tests):
  - a row missing (or with `None`/empty) required `"text"` is SKIPPED, not
    fatal -- collected into `result["skipped_rows"]` with a reason, every
    other row in the same batch still ingests. This is the ONLY skip
    condition left: unlike wave-3, an empty/missing `"chapter"` no longer
    causes a skip on its own (0 of the 21,649 real DE rows hit any other
    skip condition).
  - an unknown jurisdiction code raises `ValidationError` (same controlled
    vocabulary the API enforces, `app.services.jurisdiction
    .validate_jurisdiction`).
  - an empty `rows` list raises `ValueError` -- never a silent no-op that
    could be mistaken for "ingested, zero sections".
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.document import Document
from app.models.source_span import SourceSpan
from app.services.jurisdiction import validate_jurisdiction


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
    "source_span_ids": list[str], "skipped_rows": list[dict]}` --
    `article_ids`/`source_span_ids` are in the same order as the
    successfully-ingested rows appear in `rows`; `skipped_rows` holds
    `{"act_id": ..., "reason": ...}` for every row that failed to ingest
    (never fatal to the rest of the batch).
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
    source_span_ids: list[str] = []
    skipped_rows: list[dict] = []

    for row in rows:
        act_id = row.get("act_id")
        text = row.get("text")
        if not text:
            skipped_rows.append(
                {"act_id": act_id, "reason": "missing required 'text' column"}
            )
            continue

        chapter = row.get("chapter") or ""
        number = str(row.get("section_number"))
        heading = row.get("section_title") or ""

        # Idempotency key (wave-4 fix, ruling R7(b)): (section_number,
        # section_title, text) -- verified 100% collision-free across all
        # 21,649 real US-DE rows (see module docstring for why neither
        # `chapter` alone nor `citation` alone is safe on real data).
        # `Article.chapter` still stores the row's real chapter value
        # (including honestly empty) -- it is just not part of the lookup.
        lookup = (
            select(Article)
            .join(SourceSpan, Article.source_span_id == SourceSpan.id)
            .where(
                Article.document_id == document.id,
                Article.number == number,
                Article.heading == heading,
                SourceSpan.quote_text == text,
            )
        )

        existing_article = session.execute(lookup).scalar_one_or_none()

        if existing_article is not None:
            article_ids.append(existing_article.id)
            source_span_ids.append(existing_article.source_span_id)
            continue

        source_span = SourceSpan(
            id=str(uuid.uuid4()),
            document_id=document.id,
            matter_id=matter_id,
            quote_text=text,
        )
        session.add(source_span)
        session.flush()

        article = Article(
            id=str(uuid.uuid4()),
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
        source_span_ids.append(source_span.id)

    session.commit()

    return {
        "document_id": document.id,
        "article_ids": article_ids,
        "source_span_ids": source_span_ids,
        "skipped_rows": skipped_rows,
    }
