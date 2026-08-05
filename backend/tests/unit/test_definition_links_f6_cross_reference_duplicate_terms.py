"""RED test for sprint 2026-08-04-defs-us-multiterm, ruling M-R17: F6's
CROSS-REFERENCE path (`_cross_reference_candidates` in `rules/us_inline_
parenthetical.py`) can extract the SAME term as MULTIPLE separate
`DefinitionCandidate`s from one article -- "one term, one candidate" is
violated, mirroring M-R14's already-fixed apposition-path defect
(`test_definition_links_f6_apposition_duplicate_terms.py`) but on the
SIBLING extraction primitive M-R14's `seen_terms` dedup was never applied
to.

Post-cycle-2 corpus re-measure (sprint manager): duplicates, driven to 0
by M-R14, are back -- 18 duplicate-term rows, ALL on the cross-reference
path (0 on the apposition path, confirming M-R14's own fix there still
holds). Cause: M-R14 added `seen_terms` deduplication to `_apposition_
candidates` ONLY; `_cross_reference_candidates` has no equivalent guard.
This was previously checked and correctly found to be a NON-issue at the
PERSISTED level (`test_multiterm_qa_u4_findings.py::
test_cross_reference_path_duplicate_candidates_are_still_deduped_at_
persist_layer`, QA cycle 1, kept GREEN as a regression guard for that
specific claim) -- the persist-layer dedup key `(article_id,
sorted(candidate.terms))` happens to collapse two identical-single-term
candidates into ONE `Definition` row WITHIN a single ingest run. Cycle 2's
own wiring change (QA finding 3 adding `"as defined in"` to `_IDIOM_GAP_RE`,
QA finding 4 wiring `_cross_reference_candidates` into the `TermClauseRule`
path) is what re-surfaced this as an OBSERVABLE, double-emitting defect at
the candidate level -- this file pins THAT candidate-level fact directly,
the same altitude M-R14's sibling test already established for the
apposition path, not a persisted-row claim (which the QA test above
already covers and which this file does not duplicate or contradict).

Fixture: REAL row vendored verbatim (full original parquet columns, values
unmodified, no trimming) from the local HF snapshot at
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law`
(`us_ar_statutes.parquet`), `backend/tests/fixtures/us_statutes/
f6_cross_reference_duplicate_rows.json` -- see that directory's `README.md`
for full provenance and the byte-exactness re-verification (an independent
second parquet read, diffed field-by-field against the committed fixture,
zero mismatches). `STATE_AR_T4_C28_S2_S4-28-208` (`"private foundation"`,
2 occurrences -> 1 distinct term) was picked over the sprint manager's other
suggested example (`STATE_GA_T38_C3_S38-3-42`, `"rule"`) as the smaller of
the two real rows (5,425 vs 7,654 chars).

Live-path discipline: calls the REAL, current `USProfile.
extract_local_scope_definitions` -- the dispatching profile method,
reached via `get_profile(...)`, that unions in every registered
`ScopeTriggerRule` for the profile's code (`us_inline_parenthetical.py`'s
`_extract_ordinary_body`, which calls `_cross_reference_candidates`,
among them) -- the same method `pipeline.py` calls for an ordinary
(non-Definitions-heading) article body (`pipeline.py:270`). Verified live
this row's own `section_title` ("Private foundations - Amendment of
articles of incorporation by operation of law") is NOT recognized as a
Definitions heading (`is_definitions_heading(...) == False`), so this IS
the real path this row's real production run takes.
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
    / "f6_cross_reference_duplicate_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_ar_s4_28_208_private_foundation_cross_reference_is_extracted_exactly_once():
    """Real row `STATE_AR_T4_C28_S2_S4-28-208`. The real corpus text
    itself repeats an entire paragraph verbatim (a genuine scrape
    artifact, not injected), so the cross-reference idiom `"private
    foundation" as defined in section 509 of the Internal Revenue Code of
    1954...` appears TWICE in the real body. Each occurrence independently
    satisfies `_IDIOM_GAP_RE`, so `_cross_reference_candidates` emits TWO
    separate `DefinitionCandidate(terms=("private foundation",), ...)`
    objects for this one article -- "one term, one candidate" is
    violated, the same hazard class M-R14 already fixed on the sibling
    apposition path."""
    row = _load_rows()["STATE_AR_T4_C28_S2_S4-28-208"]
    profile = get_profile("US-AR")
    candidates = profile.extract_local_scope_definitions(
        row["text"], article_number=row["section_number"], chapter=row["chapter"]
    )
    term_counts = Counter(t for c in candidates for t in c.terms)
    assert term_counts["private foundation"] == 1, (
        f'"private foundation" was extracted as its own term in '
        f'{term_counts["private foundation"]} separate candidates from this one article '
        f"(expected exactly 1 -- one term, one candidate). `_cross_reference_candidates` "
        f"(rules/us_inline_parenthetical.py) has no `seen_terms`-style dedup (M-R14 added "
        f"that guard to `_apposition_candidates` only), and the real row's own text "
        f'genuinely repeats the `"private foundation" as defined in ...` idiom twice -- a '
        f"duplicate-term-across-candidates hazard measured on 18 real rows post-cycle-2 "
        f"(M-R17), all on this path (0 on the apposition path, confirming M-R14's own fix "
        f"there still holds). All terms extracted: "
        f"{sorted(t for c in candidates for t in c.terms)!r}"
    )
