"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, C1/C5.

Committed, re-runnable, DETERMINISTIC denominator script. Derives the
signal-agnostic candidate-definition population for the whole
israeli-laws-wiki corpus and writes two artifacts:

1. A small aggregate summary JSON (the headline counts -- files, articles,
   quote characters, word-internal, eligible, paired candidate spans).
2. A row-level SPAN manifest (JSONL, one row per candidate span) --
   vendored into `backend/tests/fixtures/certification/`, the artifact
   `C2`'s backbone test reads instead of the live corpus (program
   standing constraint: no TEST reads the corpus; this is a SCRIPT, run
   explicitly and out-of-band from `pytest`, exactly like
   `ingest_wiki_corpus_cli.py`'s own "never part of pytest" discipline).

## Method (signal-agnostic, no reference to any trigger phrase/heading/
## capture rule for the DENOMINATOR itself -- C1)

For every `*.wiki` file in the corpus:

1. Read raw text, UTF-8 (byte-identical to `ingest_wiki_corpus.py`'s own
   `wiki_path.read_text(encoding="utf-8")` -- zero decode errors measured
   across all 6,133 files, confirmed before relying on this).
2. Split into articles via `sections.parse_articles(raw_text)` -- the
   EXACT function `ingest.ingest_wiki_law` calls at ingest time. This is
   not a denominator-shaping choice; it is the one place article
   boundaries are defined in this codebase at all, and using anything
   else would silently disagree with what an "article" even is.
3. For each article, normalize its BODY (not heading -- see "Heading vs
   body" below) via `normalize.normalize_for_parsing`, the exact function
   `pipeline.py:188` calls on `raw_body` before any extraction runs. This
   is the single most important methodological fact this whole sprint is
   built on (manager rulings M28/M23/M31): compute every statistic on the
   text the production path actually consumes, not on raw corpus text.
4. Scan every `"` character (there is exactly ONE quote codepoint left
   after normalization -- `normalize.normalize_for_parsing` collapses
   U+201C/U+201D/U+05F4 into U+0022). A quote character immediately
   preceded AND followed by a Hebrew letter (U+05D0-U+05EA), with no
   intervening whitespace, is WORD-INTERNAL (cluster 1's predicate,
   `clusters.is_word_internal_quote`) -- an abbreviation marker, never a
   term delimiter. Every other quote character is ELIGIBLE.
5. Eligible characters are paired SEQUENTIALLY within each article (1st
   eligible quote opens candidate span 1, 2nd closes it, 3rd opens span
   2, ...) -- the simplest signal-agnostic pairing rule, and the one that
   reproduces the historical ~92,600 headline exactly (see "Reproduction"
   below). An article with an ODD eligible count leaves its last eligible
   quote unpaired; these are counted and reported separately (`unpaired_
   trailing_quotes` in the summary), never silently dropped or forced
   into a bogus pairing with the next article's first quote.

## Heading vs body -- a decision this script had to make, not inherited

`ingest.py` persists ONLY `parsed_article.body` as the `SourceSpan.
quote_text` that `pipeline.py` later normalizes and extracts from
(`ingest.py:66`); the heading text (`parsed_article.heading`, everything
after `@ N.` on the marker's own line) is stored on `Article.heading` and
is normalized/scanned for quotes NOWHERE in the production extraction
path. Measured directly (three configurations run against the real
corpus by this script's author before committing to one):

    whole raw file (incl. pre-article-1 metadata)  528,564 total quotes
    article HEADING + BODY, normalized                389,351 total quotes
    article BODY ONLY, normalized                     276,815 total quotes

Only "article body only" reproduces the manager's own M31-corrected
figures EXACTLY (276,815 total / 91,611 word-internal (33.1%) / ~92,602
paired spans) -- not merely "within tolerance", an exact match to every
digit. This script therefore scans BODY TEXT ONLY, matching what
production actually normalizes and extracts from. The consequence is
named explicitly, not buried: a quote-delimited span living entirely
inside an article's HEADING line (e.g. the `אכרזה זאת` residual --
`il_law_wide_vocabulary.py`'s own docstring names this exact case) is
OUTSIDE this denominator by construction, because it is outside what
`pipeline.py` ever normalizes or scans. See the sprint log's C1 section
for why this is reported as a scope boundary of the denominator rather
than silently absorbed.

## Reproduction -- ROUND 2 (post-M33-2, the vav-conjunction fix APPLIED)

    files                                6,133
    articles (sections.parse_articles)  128,234
    raw quote chars (article bodies)    276,815
    word-internal (cluster 1, REFINED)   89,515   (32.3%)
    eligible                            187,300
    unpaired_trailing_quotes                282   (was 1,676 pre-fix)
    ACTUAL paired candidate spans        93,509   (was 91,764 pre-fix)

The first three rows (files/articles/raw quote chars) are UNCHANGED from
Round 1 and still an EXACT match to the panel manager's M31 post-QA-
cycle-4 correction -- the vav-conjunction fix changes how quote
CHARACTERS are CLASSIFIED (word-internal vs eligible), never how many
of them exist. **The delta from Round 1's own reported figures (91,611
word-internal / 91,764 spans) is fully explained, not absorbed:** see
"The vav-conjunction correction, APPLIED" below for the exact mechanism
and the independent confirmation that it is a correction, not merely a
different number.

## The vav-conjunction correction, APPLIED (ruling M33-2, panel manager)

Round 1 of this sprint measured `unpaired_trailing_quotes` -- articles
whose ELIGIBLE quote count is odd, so the last eligible quote cannot be
paired (dropped, counted, never silently mis-paired with the next
article's first quote) -- at 1,676 of 128,234 articles (1.3%), and
traced that symptom to a genuine FALSE POSITIVE in cluster 1's ORIGINAL
predicate: a quote immediately preceded by a bare, standalone vav
conjunction ("ו", itself preceded by whitespace/start -- e.g. `"רכב"
ו"דרך"`, "car AND road", two real terms joined without a space before
the second quote) satisfied "Hebrew letter both sides" and was
classified word-internal, even though it is a genuine term-OPENING
delimiter, not an abbreviation marker. Round 1 measured this at 2,096 of
91,611 word-internal-classified quotes (2.3%), 1,004 files, and reported
it as a CANDIDATE correction without applying it (cluster 1 was the
contract's own stated template; changing it unilaterally was not a
Planner's call to make).

**Round 2: the panel manager independently re-verified this finding
(not accepted on report -- their own direct probe of `"רכב" ו"דרך"`
reproduced the exact same `prev='ו' next='ד' word_internal=True` result)
and ruled it APPLIED** (`docs/sprint/sprints/2026-08-05-defs-il-
certification-log.md`, M33, ruling 2). `clusters.is_word_internal_quote`
now takes a third character of context (`char_before_prev`) and excludes
the standalone-vav-conjunction case directly -- see that function's own
docstring for the full predicate. This script's `vav_conjunction_
correction` summary block is now an AUDIT count (2,096 corrections
applied, 1,004 files), not a candidate report -- the `word_internal`/
`eligible`/`paired_candidate_spans` figures above already reflect it.

**Independent confirmation this is a correction, not merely a
different number** (both measured before AND after applying, not
assumed): `unpaired_trailing_quotes` drops from 1,676 to 282 (-83%) --
the dominant, though not sole, root cause of the pairing anomaly. The
residual 282 odd-parity articles are NOT further root-caused this round
(honest gap, carried forward).

The refined predicate carries its OWN committed unit test, per the
ruling's explicit instruction: `backend/tests/unit/
test_certification_clusters_word_internal_quote.py` pins the `"רכב"
ו"דרך"` case (and its own negative controls -- a vav that is NOT
standalone, e.g. mid-word, must still be classified word-internal).

## Production-captured cross-check (for the span manifest's own
## `production_captured` column, used by clusters 2+, NOT by C1 itself)

For every article, this script also replicates `pipeline.py`'s own
dispatch (lines 236-273: `profile.is_definitions_heading` with the
body-derived-heading fallback, then EITHER `profile.
extract_definitions_from_section` OR `profile.
extract_local_scope_definitions`) via the real, UNMODIFIED `HebrewProfile`
-- imported, never copied or reimplemented. A candidate span's `term_text`
is marked `production_captured=True` when it appears (string membership,
not offset identity -- a known, named limitation, see the sprint log's
honest-gaps section) among the real `DefinitionCandidate.terms` produced
for that article. Wikilink stripping (`normalize.strip_wikilinks`, which
`pipeline.py` applies AFTER normalization and BEFORE extraction) is
applied only for this cross-check, never for the denominator's own
quote-counting -- confirmed empirically not to change quote counts
(this script's own totals match the officially-reported figures exactly
without it).

## Usage

    backend/.venv/bin/python backend/tests/certification/c1_denominator.py \\
        [--corpus-dir PATH] [--out-dir PATH]

Deterministic: no randomness anywhere in this script. Re-running against
an unchanged corpus reproduces byte-identical output (QA's C5 re-run+diff
requirement).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

_BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.definition_links import normalize as norm_mod  # noqa: E402
from app.definition_links import sections  # noqa: E402
from app.definition_links.normalize import strip_wikilinks  # noqa: E402
from app.definition_links.profiles import get_profile  # noqa: E402

from clusters import is_hebrew_letter, is_word_internal_quote  # noqa: E402

_DEFAULT_CORPUS_DIR = pathlib.Path("/Users/nerya/AI for others/israeli-laws-wiki/data/laws")
_DEFAULT_OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "certification"

# Found Round 1 (not inherited), by hand-reading a sample of the 16% of
# spans whose term_text has no Hebrew letter at all: MediaWiki table
# markup (`{| ... ! width="200px" | ... !! width="100px" | ...`) uses `"`
# as an HTML-attribute delimiter, which this script's signal-agnostic
# character scan correctly (per M18 -- no capture-rule reference) counts
# as a raw quote character, but which is never Hebrew legal-drafting text.
# See `clusters.cluster_wiki_table_markup_attribute` -- this regex feeds
# ONLY that span-manifest feature column, never cluster 1's own
# word-internal bucketing (a markup attribute quote is never word-internal
# in the first place -- its neighbors are `=`/digits/letters like "px").
# Round 2 widening (small, precisely measured, not guessed): MediaWiki's
# own `{{=}}` template-escape for a literal `=` inside a template
# parameter (`<div style{{=}}"padding: 5px 30px; ...">`, used when a raw
# `=` would otherwise be misparsed as a template named-parameter
# separator) is the SAME phenomenon, just a different literal token
# immediately before the quote. Measured before widening: 5 quote
# characters / 1 file (`תקנות התעבורה`) -- tiny, but the SAME mechanical
# category, not a new one; folded into this one regex rather than a
# second near-duplicate cluster.
_HTML_ATTR_RE = re.compile(r"[A-Za-z][A-Za-z-]*(?:=|\{\{=\}\})$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=pathlib.Path, default=_DEFAULT_CORPUS_DIR)
    parser.add_argument("--out-dir", type=pathlib.Path, default=_DEFAULT_OUT_DIR)
    return parser


def _production_captured_terms(profile, art) -> set[str]:
    """Mirror `pipeline.py`'s own dispatch (lines 236-273) exactly, via the
    real, unmodified `HebrewProfile` -- never a reimplementation."""
    normalized_body = norm_mod.normalize_for_parsing(art.body)
    stripped_body, _hints = strip_wikilinks(normalized_body)

    is_definitions_section = profile.is_definitions_heading(art.heading, stripped_body)
    if not is_definitions_section:
        derived_heading = profile.derive_heading_from_body(art.heading, stripped_body)
        if derived_heading is not None and profile.is_definitions_heading(
            derived_heading, stripped_body
        ):
            is_definitions_section = True

    if is_definitions_section:
        scope = profile.determine_scope(stripped_body)
        candidates = profile.extract_definitions_from_section(stripped_body, scope=scope)
    else:
        candidates = profile.extract_local_scope_definitions(
            stripped_body, article_number=art.number, chapter=art.chapter
        )

    terms: set[str] = set()
    for candidate in candidates:
        terms.update(candidate.terms)
    return terms, is_definitions_section


def derive(corpus_dir: pathlib.Path) -> tuple[dict, list[dict]]:
    profile = get_profile("IL")
    files = sorted(corpus_dir.glob("*.wiki"))

    total_quotes = 0
    total_word_internal = 0
    total_eligible = 0
    total_articles = 0
    unpaired_trailing_quotes = 0
    # Audit count, per M33-2: how many characters cluster 1's ORIGINAL
    # (pre-M33) predicate would have wrongly disposed as word-internal,
    # now correctly classified eligible -- kept for auditability/history,
    # not because anything downstream still branches on the old behavior.
    vav_conjunction_corrections_applied = 0
    vav_conjunction_correction_files: set[str] = set()
    html_attribute_spans = 0
    html_attribute_files: set[str] = set()
    span_rows: list[dict] = []
    row_id = 0

    for fp in files:
        raw = fp.read_text(encoding="utf-8")
        articles = sections.parse_articles(raw)
        total_articles += len(articles)

        for art in articles:
            body_norm = norm_mod.normalize_for_parsing(art.body)
            n = len(body_norm)

            eligible_positions: list[int] = []
            for i, ch in enumerate(body_norm):
                if ch != '"':
                    continue
                total_quotes += 1
                prev_ch = body_norm[i - 1] if i > 0 else ""
                next_ch = body_norm[i + 1] if i < n - 1 else ""
                before_prev_ch = body_norm[i - 2] if i - 2 >= 0 else ""
                if is_word_internal_quote(prev_ch, next_ch, before_prev_ch):
                    total_word_internal += 1
                else:
                    total_eligible += 1
                    eligible_positions.append(i)
                    # Audit only -- both neighbors are Hebrew letters (the
                    # ORIGINAL predicate's own trigger condition) but the
                    # REFINED predicate above correctly let it through.
                    if is_hebrew_letter(prev_ch) and is_hebrew_letter(next_ch):
                        vav_conjunction_corrections_applied += 1
                        vav_conjunction_correction_files.add(fp.name)

            if len(eligible_positions) % 2 == 1:
                unpaired_trailing_quotes += 1
                eligible_positions = eligible_positions[:-1]

            if not eligible_positions:
                continue

            captured_terms, is_defs_heading = _production_captured_terms(profile, art)

            for span_idx in range(0, len(eligible_positions), 2):
                start = eligible_positions[span_idx]
                end = eligible_positions[span_idx + 1]
                term_text = body_norm[start + 1 : end]
                preceded_by_html_attribute = bool(
                    _HTML_ATTR_RE.search(body_norm[max(0, start - 20) : start])
                )
                if preceded_by_html_attribute:
                    html_attribute_spans += 1
                    html_attribute_files.add(fp.name)
                span_rows.append(
                    {
                        "id": row_id,
                        "file": fp.name,
                        "article_number": art.number,
                        "is_definitions_heading_article": is_defs_heading,
                        "span_index_in_article": span_idx // 2,
                        "start": start,
                        "end": end,
                        "term_text": term_text,
                        "production_captured": term_text in captured_terms,
                        "preceded_by_html_attribute": preceded_by_html_attribute,
                    }
                )
                row_id += 1

    summary = {
        "files": len(files),
        "articles": total_articles,
        "raw_quote_chars": total_quotes,
        "word_internal": total_word_internal,
        "word_internal_pct": round(total_word_internal / total_quotes * 100, 1)
        if total_quotes
        else 0.0,
        "eligible": total_eligible,
        "unpaired_trailing_quotes": unpaired_trailing_quotes,
        "paired_candidate_spans": len(span_rows),
        "vav_conjunction_correction": {
            "note": "M33-2 (panel manager): APPLIED, not a diagnostic "
            "candidate -- word_internal/eligible/paired_candidate_spans "
            "above already reflect this correction. This block is an "
            "AUDIT count only: how many characters the ORIGINAL (pre-M33) "
            "predicate would have wrongly disposed as word-internal, now "
            "correctly classified eligible by the refined "
            "clusters.is_word_internal_quote.",
            "corrections_applied": vav_conjunction_corrections_applied,
            "files": len(vav_conjunction_correction_files),
            "pct_of_original_word_internal_estimate": round(
                vav_conjunction_corrections_applied
                / (total_word_internal + vav_conjunction_corrections_applied)
                * 100,
                1,
            )
            if (total_word_internal + vav_conjunction_corrections_applied)
            else 0.0,
        },
        "wiki_table_markup_attribute_spans": {
            "note": "MediaWiki table markup ('! width=\"200px\" | ...') "
            "uses `\"` as an HTML-attribute delimiter -- counted as raw "
            "quote characters by this signal-agnostic scan (correctly, "
            "per M18) but never Hebrew legal-drafting text. Cluster "
            "'wiki_table_markup_attribute' (clusters.py) disposes these "
            "spans as proven-not-a-definition using this same feature.",
            "spans": html_attribute_spans,
            "files": len(html_attribute_files),
            "pct_of_paired_spans": round(html_attribute_spans / len(span_rows) * 100, 1)
            if span_rows
            else 0.0,
        },
    }
    return summary, span_rows


def main() -> None:
    args = _build_parser().parse_args()
    t0 = time.time()
    summary, span_rows = derive(args.corpus_dir)
    summary["wall_time_seconds"] = round(time.time() - t0, 1)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = args.out_dir / "c1_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest_path = args.out_dir / "c1_span_population.jsonl"
    with manifest_path.open("w", encoding="utf-8") as fh:
        for row in span_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nwrote {summary_path}")
    print(f"wrote {manifest_path} ({len(span_rows)} rows)")


if __name__ == "__main__":
    main()
