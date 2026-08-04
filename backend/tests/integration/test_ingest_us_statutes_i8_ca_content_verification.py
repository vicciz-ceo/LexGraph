"""QA regression test — sprint 2026-08-04-defs-core-scope, item I8/M14,
residual concern #2 (QA manager brief): "I8's fix is a BLANKET transform
(`text.replace("\\n", "\n")`) applied to every US row, verified 'no-op
outside NY/CA' only by a row-count probe. Verify by CONTENT, not count:
... on CA's 21 affected rows, confirm the literal sequence really is a
mis-escaped line break rather than intentional prose."

**Independent corpus measurement performed by QA (not a test — this file
does not read the corpus, per ruling R6):** swept the FULL real corpus,
all 105 `us_*_{statutes,constitutions}.parquet` files (53 statutes + 52
constitutions, ~2.05M rows total) for the literal two-character `\\n`
sequence in the `text` column. Result: exactly two files are affected --
`us_ny_statutes.parquet` (40,102/40,102 rows) and `us_ca_statutes.parquet`
(21/161,429 rows) -- every other file, including all 52 constitution
files, is a genuine no-op (zero rows contain the literal sequence). This
independently reproduces the sprint's own "CA 21 rows" figure via a fresh
sweep, not by trusting the prior probe's count.

Manually inspected the CONTENT around all 21 CA rows' literal-`\\n`
occurrences (23 total occurrences: 2 rows carry two each): every single
one sits between two clauses of a legislative "Effective/Inoperative/
Repealed ... by its own provisions" editorial annotation, always
immediately followed by whitespace and the start of a new capitalized
clause (e.g. "...by its own provisions.\\n   Repealed as of January 1,
2027, by its own provisions." or "...Ch. 56, Sec. 41.\\n   Repealed
conditionally as prescribed..."). This is unambiguously a mis-escaped
LINE BREAK role, not textually-significant prose -- there is no CA row
where the literal sequence appears mid-word, inside a quoted excerpt, or
anywhere its removal could plausibly change a reader's understanding of
the statute (the transform only ever swaps a 2-char escape for a 1-char
real newline; it never touches a letter or digit).

This test vendors ONE real, byte-for-byte CA row
(`STATE_CA_Chsc_D31_P1_C3_S50150`, Health & Safety Code, real 2026-vintage
"Repealed as of January 1, 2027,\\nby its own provisions." annotation --
copied from the live `us_ca_statutes.parquet` snapshot, never downloaded
or read by this test itself) and pins, on the LIVE `ingest_us_statute_rows`
path, that the fix (a) actually fires on real CA content (not just the
NY-shaped synthetic case the M14 test already covers), (b) changes NOTHING
except that one 2-character-to-1-character substitution -- every other
byte of this ~1.4KB real row survives untouched.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "ca_i8_newline_content_verification_row.json"
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_real_ca_row_content_is_unchanged_except_the_one_mis_escaped_line_break(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.article import Article
    from app.models.source_span import SourceSpan

    m = matter_with_users
    row = _load_row()
    assert row["act_id"] == "STATE_CA_Chsc_D31_P1_C3_S50150"
    raw_text = row["text"]

    # Sanity on the vendored fixture itself (fails loudly if the fixture
    # were ever hand-edited into a shape that no longer exercises the
    # defect): exactly one literal backslash-n sequence, at the real,
    # human-inspected editorial-annotation line-break position.
    assert raw_text.count("\\n") == 1
    assert '2027,\\nby its own provisions.' in raw_text

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="California Health and Safety Code (I8 CA content-verification fixture)",
        rows=[row],
        jurisdiction="US-CA",
    )
    assert result["skipped_rows"] == []
    assert len(result["article_ids"]) == 1

    article = db_session.get(Article, result["article_ids"][0])
    span = db_session.get(SourceSpan, article.source_span_id)
    ingested_text = span.quote_text

    # 1. The mis-escaped sequence is gone -- no literal backslash-n survives
    # anywhere in the ingested text.
    assert "\\n" not in ingested_text, (
        "the literal two-character backslash-n sequence still appears in "
        f"the ingested SourceSpan.quote_text for a real CA row -- got "
        f"{ingested_text!r}"
    )

    # 2. It became a REAL newline at exactly that position -- the two
    # clauses of the editorial annotation are now genuinely line-broken,
    # not merely space-separated.
    assert "2027,\nby its own provisions." in ingested_text, (
        "expected the literal escape to become a real newline at the "
        "editorial-annotation clause boundary -- got "
        f"{ingested_text!r}"
    )

    # 3. NOTHING else changed: exactly one character shorter than the raw
    # row (one 2-char sequence -> one 1-char real newline, and nothing
    # else touched), and every other real newline already present in the
    # raw text (this row has several, separating its own paragraphs)
    # survives byte-for-byte.
    assert len(ingested_text) == len(raw_text) - 1, (
        f"expected the ingested text to be exactly 1 character shorter "
        f"than the raw row (one 2-char escape collapsed to one 1-char "
        f"real newline) -- raw len={len(raw_text)}, ingested "
        f"len={len(ingested_text)}"
    )
    assert ingested_text == raw_text.replace("\\n", "\n"), (
        "the ingested text diverges from a plain literal-backslash-n-to-"
        "real-newline substitution of the raw row -- something other "
        "than the intended escape was altered"
    )

    # 4. Distinctive prose well away from the defect survives untouched --
    # guards against a broader, unintended rewrite silently passing the
    # narrower checks above.
    assert (
        "Business, Consumer Services and Housing Agency" in ingested_text
    )
    assert "shall become inoperative on July 1, 2026" in ingested_text
