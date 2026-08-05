"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, C1's
bounded scout item (contract amendment 1), Job 2.

~92,600 is the QUOTED-span population -- itself a signal choice (a
well-motivated one, but a choice). This script probes the COMPLEMENT:
does Hebrew statutory drafting ever define a term WITHOUT a quote
delimiter at all? Per the US track's hardest lesson (NE 92.1% unquoted),
that is an ASSUMPTION today, not a measurement.

## Role of the trigger vocabulary here -- stated explicitly per the
## contract's own instruction ("say which role the vocabulary is playing
## wherever it appears")

This script imports the SAME known trigger/marker vocabulary the capture
rules use (`il_law_wide_vocabulary.law_wide_preamble_phrases`, plus the
scope-trigger words the various `rules/il_*_scope_triggers.py` modules
match on). Here it plays the role of a PROBE INSTRUMENT testing whether
the denominator's own quoted-span boundary is in the right place -- NOT
the role of a denominator (M18 governs the denominator, which C1 keeps
signal-agnostic; it does not forbid using known vocabulary to test the
denominator's own scope). If this scout found a large, genuine unquoted
population, that population would need ITS OWN signal-agnostic
denominator before certification -- this script's job is only to decide
whether that is necessary.

## Method

For every line inside every article's NORMALIZED body (article-body
scope, matching `c1_denominator.py`'s own scope decision):

1. Skip any line containing a quote character (`"`, on normalized text --
   already quoted, not a complement candidate).
2. Flag the line if it matches ONE of two disjoint marker shapes:
   - `entry_marker`: starts with `:-` or `::-` (the list-shape entry-start
     grammar, `extract._ENTRY_START_RE`'s own shape) -- a real entry line
     with NO quote at all would mean an UNQUOTED term in the one grammar
     shape that structurally expects a quoted header.
   - `trigger_word`: contains one of the known scope-trigger phrases
     (law-wide preamble phrases, plus every local/chapter/siman/chelek/
     paragraph/item/three-word trigger word every registered
     `ScopeTriggerRule` module matches on) AND the line contains a
     dash (`-`) or colon (`:`) somewhere at or after the trigger --
     the shape every quote-first/list-shape grammar expects to precede
     a definition, just missing the quotes.
3. Deterministic seeded sample (seed committed below) of the combined
   hit population, hand-judged by the Planner (not automated -- the
   contract's own instruction: "sample and hand-judge").

## Usage

    backend/.venv/bin/python backend/tests/certification/c1_complement_scout.py \\
        [--corpus-dir PATH] [--out-dir PATH] [--sample-size N]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sys

_BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.definition_links import normalize as norm_mod  # noqa: E402
from app.definition_links import sections  # noqa: E402
from app.definition_links.rules.il_law_wide_vocabulary import (  # noqa: E402
    law_wide_preamble_phrases,
)

_DEFAULT_CORPUS_DIR = pathlib.Path("/Users/nerya/AI for others/israeli-laws-wiki/data/laws")
_DEFAULT_OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "certification"

# Committed seed (C1/C5: re-runnable, deterministic -- QA draws the same
# sample from a clean checkout).
_SAMPLE_SEED = 20260805

_ENTRY_MARKER_RE = re.compile(r"^\s*:{1,2}-")

# Scope-trigger vocabulary, gathered from every registered `ScopeTriggerRule`
# module's own `_TRIGGER_RE` (read directly off each file, not guessed) --
# playing a PROBE role here, per this module's own docstring.
_SCOPE_TRIGGER_WORDS: tuple[str, ...] = (
    "בפרק זה",
    "לענין פרק זה",
    "לעניין פרק זה",
    "בסימן זה",
    "בחלק זה",
    "לענין זה",
    "לעניין זה",
    "בסעיף זה",
    "לענין סעיף זה",
    "לעניין סעיף זה",
    "בפסקה זו",
    "לענין פסקה זו",
    "לעניין פסקה זו",
    "בפרט זה",
    "להלן",
)


def _build_marker_re() -> re.Pattern[str]:
    words = tuple(dict.fromkeys(_SCOPE_TRIGGER_WORDS + law_wide_preamble_phrases()))
    words_sorted = sorted(words, key=len, reverse=True)
    return re.compile("|".join(re.escape(w) for w in words_sorted))


_TRIGGER_WORD_RE = _build_marker_re()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=pathlib.Path, default=_DEFAULT_CORPUS_DIR)
    parser.add_argument("--out-dir", type=pathlib.Path, default=_DEFAULT_OUT_DIR)
    parser.add_argument("--sample-size", type=int, default=120)
    return parser


def scout(corpus_dir: pathlib.Path) -> list[dict]:
    files = sorted(corpus_dir.glob("*.wiki"))
    hits: list[dict] = []

    for fp in files:
        raw = fp.read_text(encoding="utf-8")
        for art in sections.parse_articles(raw):
            body_norm = norm_mod.normalize_for_parsing(art.body)
            for line_idx, line in enumerate(body_norm.split("\n")):
                if '"' in line:
                    continue
                stripped = line.strip()
                if not stripped:
                    continue

                if _ENTRY_MARKER_RE.match(line):
                    hits.append(
                        {
                            "file": fp.name,
                            "article_number": art.number,
                            "line_index": line_idx,
                            "line": stripped,
                            "marker_kind": "entry_marker",
                        }
                    )
                    continue

                trigger_match = _TRIGGER_WORD_RE.search(stripped)
                if trigger_match and ("-" in stripped or ":" in stripped):
                    hits.append(
                        {
                            "file": fp.name,
                            "article_number": art.number,
                            "line_index": line_idx,
                            "line": stripped,
                            "marker_kind": "trigger_word",
                            "matched_trigger": trigger_match.group(0),
                        }
                    )

    return hits


def main() -> None:
    args = _build_parser().parse_args()
    hits = scout(args.corpus_dir)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # `c1_complement_scout_hits.jsonl` (the FULL hit list, ~15MB) is
    # written for local inspection but deliberately NOT committed to git
    # -- nothing reads it at test time (only the SAMPLE below is a
    # committed, vendored artifact), and it is trivially reproducible by
    # re-running this deterministic script against the read-only corpus
    # (C5). Committing the summary counts + the seeded sample is enough
    # for QA to re-run and diff without carrying a large, test-unread
    # file in the repo.
    hits_path = args.out_dir / "c1_complement_scout_hits.jsonl"
    with hits_path.open("w", encoding="utf-8") as fh:
        for hit in hits:
            fh.write(json.dumps(hit, ensure_ascii=False) + "\n")

    by_kind: dict[str, int] = {}
    for hit in hits:
        by_kind[hit["marker_kind"]] = by_kind.get(hit["marker_kind"], 0) + 1

    rng = random.Random(_SAMPLE_SEED)
    sample_size = min(args.sample_size, len(hits))
    sample = rng.sample(hits, sample_size) if hits else []
    sample_path = args.out_dir / "c1_complement_scout_sample.jsonl"
    with sample_path.open("w", encoding="utf-8") as fh:
        for hit in sample:
            fh.write(json.dumps(hit, ensure_ascii=False) + "\n")

    summary = {
        "total_hits": len(hits),
        "by_marker_kind": by_kind,
        "sample_seed": _SAMPLE_SEED,
        "sample_size": sample_size,
    }
    summary_path = args.out_dir / "c1_complement_scout_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nwrote {hits_path} ({len(hits)} rows) -- NOT committed, regenerate locally if needed")
    print(f"wrote {sample_path} ({sample_size} rows) -- seed {_SAMPLE_SEED}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
