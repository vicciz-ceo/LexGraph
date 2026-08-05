"""RED test for sprint 2026-08-04-defs-us-multiterm, ruling M-R14: F6's
apposition path (`_apposition_candidates` in `rules/us_inline_
parenthetical.py`) can extract the SAME term as MULTIPLE separate
`DefinitionCandidate`s from one article -- "one term, one candidate" is
violated.

Post-narrow corpus measurement (sprint manager, program ruling E3's
narrowing applied): F6 fires on 280/79,847 US rows (0.35%, exactly the
projected rate), but 17 of those 280 (6.1%) have a duplicate term across
their own extracted candidates. Every measured example is an acronym/
short-title apposition (`("BOP")`, `("OSSE")`, `("ASAM")`) that the real
statutory text happens to name/parenthesize MORE THAN ONCE within one
article body -- the narrowing (which only touched the CROSS-REFERENCE path,
`_cross_reference_candidates`/`_IDIOM_GAP_RE`) reduced this from 10.8% to
6.1% without curing it, because the duplication lives entirely in the
APPOSITION path, `_apposition_candidates`/`_APPOSITION_RE`, which scans the
WHOLE article body unconditionally and unions in a fresh candidate for
EVERY match -- including a second, third, ... occurrence of the identical
`("Term")` shorthand appearing later in the same body for an unrelated
sentence.

**Why this matters (same hazard class as Residual ledger R1, except this
one is F6's own, not markers'):** `pipeline.py`'s persist-layer dedup key
is `(article_id, sorted(candidate.terms))` -- for two single-term
candidates sharing the identical term, this key happens to collapse them
to ONE `Definition` row WITHIN a single ingest run (verified live,
2026-08-05: this exact fixture row, run through the real production
`ingest_us_statute_rows -> run_definition_linking` path, persists only
ONE "ASAM" `Definition` row). That in-run collapse is real, but it means
the duplication is INVISIBLE at the persisted/integration-test level for
this exact shape -- it is observable only at the CANDIDATE level, before
persistence, which is what this test pins. (The dedup collapse also
silently DISCARDS whichever duplicate candidate's `definition_text` lost
the race, with no signal that a second, differently-worded occurrence
existed at all -- a separate, un-pinned data-loss concern, not this
test's claim.)

Fixture: REAL row vendored verbatim (full original parquet columns,
values unmodified, no trimming) from the local HF snapshot at
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law`
(`us_de_statutes.parquet`), `backend/tests/fixtures/us_statutes/
f6_apposition_duplicate_rows.json` -- see that directory's `README.md`
for full provenance and the byte-exactness re-verification (an
independent second parquet read, diffed field-by-field against the
committed fixture, zero mismatches).

Live-path discipline: calls the REAL, current `USProfile.
extract_local_scope_definitions` -- the dispatching profile method,
reached via `get_profile(...)`, that unions in every registered
`ScopeTriggerRule` for the profile's code (`us_inline_parenthetical.py`'s
`_extract_ordinary_body` among them) -- the same method `pipeline.py`
calls for an ordinary (non-Definitions-heading) article body
(`pipeline.py:270`). Verified live this row's own `section_title`
("Insurance coverage for serious mental illness...") is NOT recognized as
a Definitions heading (`is_definitions_heading(...) == False`), so this
IS the real path this row's real production run takes -- not a
hypothetical or a different code path than production uses.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.definition_links.profiles import get_profile

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "f6_apposition_duplicate_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_de_s3578_asam_apposition_is_extracted_exactly_once():
    """Real row `STATE_DE_T18_C35_SIV_S3578`. The parenthetical shorthand
    `("ASAM")` for "American Society of Addiction Medicine" appears TWICE
    in the real body -- once inside entry (1)'s own `"ASAM criteria"
    means ...` definition, and again, unrelatedly, deep in subsection
    (d)(1)c's prose describing a "clinical review tool ... designated by
    the American Society of Addiction Medicine ("ASAM")". Each occurrence
    independently satisfies `_APPOSITION_RE`, so `_apposition_candidates`
    emits TWO separate `DefinitionCandidate(terms=("ASAM",), ...)` objects
    for this one article -- "one term, one candidate" is violated."""
    row = _load_rows()["STATE_DE_T18_C35_SIV_S3578"]
    profile = get_profile("US-DE")
    candidates = profile.extract_local_scope_definitions(
        row["text"], article_number=row["section_number"], chapter=row["chapter"]
    )
    term_counts = Counter(t for c in candidates for t in c.terms)
    assert term_counts["ASAM"] == 1, (
        f'"ASAM" was extracted as its own term in {term_counts["ASAM"]} separate '
        f"candidates from this one article (expected exactly 1 -- one term, one "
        f"candidate). `_apposition_candidates` (rules/us_inline_parenthetical.py) "
        f'scans the WHOLE article body unconditionally, and `("ASAM")` genuinely '
        f"appears twice in this real row's text for two UNRELATED sentences -- a "
        f"duplicate-term-across-candidates hazard measured on 17/280 (6.1%) of "
        f"all F6-firing US rows post-narrow (M-R14). All terms extracted: "
        f"{sorted(t for c in candidates for t in c.terms)!r}"
    )
