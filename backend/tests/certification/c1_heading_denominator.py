"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, Round 2,
ruling M33-3 (panel manager).

**Why this script exists.** Round 1's `c1_denominator.py` measures
article BODY text only, because that is the only configuration that
reproduces the M31-corrected figures digit-for-digit, and because
`ingest.py:66` persists only `parsed_article.body`, never `.heading`, as
the text `pipeline.py` normalizes and extracts from. Round 1 named the
consequence (the `אכרזה זאת` residual lives entirely in heading text,
outside that denominator) but did not measure the heading population
itself. **Ruling M33-3 is explicit: excluding headings because "the
dispatch path differs" is precisely the signal-dependence the contract
outlaws for `הגדרות`-headed articles** -- so headings get their OWN
separately-measured population and their own clusters here, rather than
staying a named-but-unmeasured gap.

## Why this is a SEPARATE script/population, not folded into
## `c1_denominator.py`

Body-only stays PRIMARY (it is what production actually parses); this is
an ADDITIVE population, not a revision of the first. Folding the two
together would silently change the already-reproduced ~92,600 headline
mid-sprint, which is exactly the kind of unannounced denominator drift
C1 exists to prevent. Keeping them separate lets each be independently
verified, reproduced, and diffed (C5).

## Method -- deliberately DIFFERENT from the body scan in one respect,
## same in every other

Exhaustively grepped first, not assumed (`grep -rn "\\.heading\\b"
backend/app/definition_links`): `art.heading` is used ONLY as an argument
to `is_definitions_heading`/`derive_heading_from_body` -- a boolean
STRING-MATCH classification, never scanned character-by-character, never
fed to any extraction function, anywhere in the package. So:

1. Same article boundaries (`sections.parse_articles`), same files.
2. **Heading text is scanned RAW, NOT normalized** -- this is the
   opposite choice from the body scan, and deliberate: `normalize_for_
   parsing` is called on `raw_body` at exactly one production site
   (`pipeline.py:188`); there is no equivalent call anywhere for heading
   text, because heading text never reaches that stage at all. Scanning
   normalized heading text would measure a population that does not
   correspond to anything production ever touches -- the same mistake
   Round 1's whole methodology exists to avoid, just on the other side.
3. Because heading text is raw, this script re-applies the M23 lesson
   fresh: it checks for **all four** known quote codepoints (U+0022,
   U+05F4 gershayim, U+201C, U+201D) individually, never assuming
   headings only ever use one, exactly as the body population was WRONG
   to assume until M23/M31 measured otherwise.
4. `clusters.is_word_internal_quote` (the SAME refined, M33-2-corrected
   predicate `c1_denominator.py` uses) is reused unchanged -- it only
   inspects a quote's NEIGHBORING characters, not the quote's own
   codepoint, so it is already codepoint-agnostic and needed no
   heading-specific variant.
5. Same per-article sequential pairing, same odd-count handling.

## A correction to ruling M33-3's own framing, found while building this
## script -- `אכרזה זאת` is NOT reachable here either

M33-3 named this script as "the honest home for residual (5) `אכרזה
זאת`". Verified directly against the real file (`אכרזה על ארגון יציג של
זכאים לפי חוק משפחות חיילים שנספו במערכה (תגמולים ושיקום).wiki`) before
trusting that framing: its own `@`-marker line is `@ (תיקון: תשפ"ג) :
באכרזה זאת, "זכאים לפי [[החוק האמור]]" - ...` -- which matches NEITHER
`sections._ARTICLE_MARKER_RE` (no digits-plus-optional-Hebrew-letters
followed by a literal period, immediately after `@`)
NOR `_BARE_ARTICLE_MARKER_RE` (there is trailing content, not just
whitespace). `sections.parse_articles` on this real file returns **ZERO
Article objects** -- confirmed live, not inferred. This is not a
heading-vs-body scope question at all: there is no `Article.heading` to
scan in the first place, because the whole document never produces a
single `Article`.

**Measured corpus-wide, because a residual this specific deserved
verification rather than a second unverified assumption:** `@`-prefixed
lines matching NEITHER frozen marker regex: **21,498 lines / 1,646
files**. Of those, files where this leaves the ENTIRE document with
**zero** articles (not just one skipped line): **121 files (2.0% of the
corpus)** -- a distinct, third `@`-marker gap from the already-known
bare-`@`-with-nothing-after-it case (P-E3, 331 occurrences/42 files,
already fixed by `_BARE_ARTICLE_MARKER_RE`/M8(a)). This is a
`sections.py` (frozen) gap, not a rule-module-only fix, closer in shape
to M20's סימן/חלק breadcrumb blocker than to anything this Planner's own
scope can build. Named here, precisely, rather than silently absorbed
into "the heading population covers it" -- it does not, and claiming it
did would repeat exactly the kind of unverified inherited claim this
whole program exists to catch.

## `production_captured` is trivially, verifiably False for every row

Confirmed by the exhaustive grep above, not asserted: no rule in this
codebase reads heading TEXT content today (only its own boolean match
against `is_definitions_heading`'s known patterns). Every row in this
population is therefore given a SINGLE cluster,
`heading_quoted_span_unreached` -- not because this script declines to
look harder, but because there is genuinely nothing to differentiate
yet: every heading-embedded quoted span is equally unreached by every
registered rule.

## Usage

    backend/.venv/bin/python backend/tests/certification/c1_heading_denominator.py \\
        [--corpus-dir PATH] [--out-dir PATH]
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

from app.definition_links import sections  # noqa: E402

from clusters import is_word_internal_quote  # noqa: E402

_DEFAULT_CORPUS_DIR = pathlib.Path("/Users/nerya/AI for others/israeli-laws-wiki/data/laws")
_DEFAULT_OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "certification"

# The four known quote codepoints (M23's own finding, re-applied fresh
# here since heading text is scanned RAW -- see this module's docstring).
_QUOTE_CODEPOINTS = {
    '"': "U+0022",
    "״": "U+05F4",
    "“": "U+201C",
    "”": "U+201D",
}

# Copied verbatim (read-only re-derivation, not an import of a private
# name) from `sections.py`'s own two marker regexes, ONLY to diagnose how
# many `@`-prefixed lines match NEITHER -- see this module's own
# docstring, "A correction to ruling M33-3's own framing". Frozen file,
# never edited; this is analysis of its behavior, not a dependency on
# its internals.
_ARTICLE_MARKER_RE = re.compile(r"^@\s+(?P<number>\d+[א-ת]*)\.\s*(?P<heading>.*)$")
_BARE_ARTICLE_MARKER_RE = re.compile(r"^@\s*$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=pathlib.Path, default=_DEFAULT_CORPUS_DIR)
    parser.add_argument("--out-dir", type=pathlib.Path, default=_DEFAULT_OUT_DIR)
    return parser


def _numberless_at_marker_diagnostic(files: list[pathlib.Path]) -> dict:
    """How many `@`-prefixed lines match NEITHER of `sections.py`'s own
    two marker regexes, and how many whole files end up with ZERO
    articles as a result -- see this module's own docstring. A
    diagnostic about the POPULATION this script can even see, not part
    of the heading-quote scan itself."""
    numberless_lines = 0
    numberless_files: set[str] = set()
    zero_article_files: list[str] = []

    for fp in files:
        raw = fp.read_text(encoding="utf-8")
        file_has_numberless = False
        for line in raw.split("\n"):
            if (
                line.startswith("@")
                and not _ARTICLE_MARKER_RE.match(line)
                and not _BARE_ARTICLE_MARKER_RE.match(line)
            ):
                numberless_lines += 1
                file_has_numberless = True
        if file_has_numberless:
            numberless_files.add(fp.name)
        if len(sections.parse_articles(raw)) == 0:
            zero_article_files.append(fp.name)

    return {
        "note": "A `sections.py` (frozen) marker gap, distinct from the "
        "already-known bare-@-with-nothing-after-it case (P-E3, fixed by "
        "_BARE_ARTICLE_MARKER_RE) -- '@ (תיקון...) : ...'-shaped lines "
        "match neither marker regex. Explains why the אכרזה זאת residual "
        "is NOT reachable by this script's own heading population "
        "either: its file produces zero Article objects, so there is no "
        ".heading to scan at all.",
        "numberless_at_lines": numberless_lines,
        "files_with_a_numberless_at_line": len(numberless_files),
        "files_with_zero_articles_total": len(zero_article_files),
        "zero_article_files_sample": sorted(zero_article_files)[:10],
    }


def derive(corpus_dir: pathlib.Path) -> tuple[dict, list[dict], dict]:
    files = sorted(corpus_dir.glob("*.wiki"))

    total_quotes = 0
    total_word_internal = 0
    total_eligible = 0
    total_articles_with_heading = 0
    unpaired_trailing_quotes = 0
    by_codepoint: dict[str, int] = {name: 0 for name in _QUOTE_CODEPOINTS.values()}
    span_rows: list[dict] = []
    row_id = 0

    numberless_at_diagnostic = _numberless_at_marker_diagnostic(files)

    for fp in files:
        raw = fp.read_text(encoding="utf-8")
        for art in sections.parse_articles(raw):
            heading = art.heading
            if not heading:
                continue
            n = len(heading)
            has_quote = any(ch in _QUOTE_CODEPOINTS for ch in heading)
            if has_quote:
                total_articles_with_heading += 1

            eligible_positions: list[int] = []
            for i, ch in enumerate(heading):
                if ch not in _QUOTE_CODEPOINTS:
                    continue
                total_quotes += 1
                by_codepoint[_QUOTE_CODEPOINTS[ch]] += 1
                prev_ch = heading[i - 1] if i > 0 else ""
                next_ch = heading[i + 1] if i < n - 1 else ""
                before_prev_ch = heading[i - 2] if i - 2 >= 0 else ""
                if is_word_internal_quote(prev_ch, next_ch, before_prev_ch):
                    total_word_internal += 1
                else:
                    total_eligible += 1
                    eligible_positions.append(i)

            if len(eligible_positions) % 2 == 1:
                unpaired_trailing_quotes += 1
                eligible_positions = eligible_positions[:-1]

            for span_idx in range(0, len(eligible_positions), 2):
                start = eligible_positions[span_idx]
                end = eligible_positions[span_idx + 1]
                term_text = heading[start + 1 : end]
                span_rows.append(
                    {
                        "id": row_id,
                        "file": fp.name,
                        "article_number": art.number,
                        "heading_text": heading,
                        "start": start,
                        "end": end,
                        "term_text": term_text,
                        # Verified by exhaustive grep (this module's own
                        # docstring), not assumed: no rule reads heading
                        # text content anywhere in this codebase today.
                        "production_captured": False,
                    }
                )
                row_id += 1

    summary = {
        "files": len(files),
        "articles_with_nonempty_heading_and_a_quote_char": total_articles_with_heading,
        "raw_quote_chars_in_headings": total_quotes,
        "by_codepoint": by_codepoint,
        "word_internal": total_word_internal,
        "word_internal_pct": round(total_word_internal / total_quotes * 100, 1)
        if total_quotes
        else 0.0,
        "eligible": total_eligible,
        "unpaired_trailing_quotes": unpaired_trailing_quotes,
        "paired_candidate_spans": len(span_rows),
        "numberless_at_marker_diagnostic": numberless_at_diagnostic,
    }
    return summary, span_rows, numberless_at_diagnostic


def main() -> None:
    args = _build_parser().parse_args()
    t0 = time.time()
    summary, span_rows, _diagnostic = derive(args.corpus_dir)
    summary["wall_time_seconds"] = round(time.time() - t0, 1)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = args.out_dir / "c1_heading_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    manifest_path = args.out_dir / "c1_heading_span_population.jsonl"
    with manifest_path.open("w", encoding="utf-8") as fh:
        for row in span_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nwrote {summary_path}")
    print(f"wrote {manifest_path} ({len(span_rows)} rows)")


if __name__ == "__main__":
    main()
