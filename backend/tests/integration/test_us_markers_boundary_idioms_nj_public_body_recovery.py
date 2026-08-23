"""RED (sprint 2026-08-20-defs-boundary-idioms, issue #27) -- a SECOND
representative ceiling-tripped loss, recovered by widening `_TIGHT_IDIOM_RE`
(`backend/app/definition_links/rules/us_markers_boundary.py`) to recognize
"has the same meaning" (a variant of the already-recognized "has the
meaning" idiom, with an inserted "same").

`STATE_NJ_T34_C1A_S1A-1.16`, term `"Public body"`: the real, complete
definition is a single clean sentence ending "... or of any of its
political subdivisions.", correctly bounded by the NEXT real term's own
idiom -- but that next term, `"State wage, benefit and tax laws"`, uses
"has the same meaning as" (not the tight "has the meaning" `_TIGHT_
IDIOM_RE` already recognizes), so it never becomes a `starts` entry,
"Public body" has no next term to bound against, zero hard-stops are
found in range, capture runs to end-of-text well past 3,000 chars, and
`MAX_CLEAN_DEFINITION_LENGTH` correctly drops the whole candidate --
"Public body" is entirely ABSENT from production today.

Found via this sprint's live re-derivation of the loss set (see the NJ
Department companion test and this sprint's log doc for the full
methodology and evidence). Chosen as a second representative because it
independently confirms the "has the following meaning"/"has the same
meaning" idiom-family widening with a DIFFERENT specific idiom string than
the "shall include" case and the "has the following meaning" case, with
the identical zero-additional-collateral-risk profile measured this
sprint (see the log doc's collateral sweep) -- unlike a same-shaped FED
row considered and rejected during planning (`USC_T12_C13_S1715r`
"approved percentage"), whose recovered text carries an unrelated,
already-tracked digit-paren-run-membership artifact (the same defect
family as issues #21/#28) that has nothing to do with idiom vocabulary;
this NJ row's recovered text is clean.

Byte-verified against the real corpus this pass (`us_nj_statutes.
parquet`, vaquill/open-us-law): fixture vendored verbatim."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_boundary_idioms_nj_public_body_row.json"
)

ACT_ID = "STATE_NJ_T34_C1A_S1A-1.16"
TERM = "Public body"
EXPECTED_TEXT = (
    "the State of New Jersey, any of its political subdivisions, any authority "
    "created by the Legislature of the State of New Jersey, and any "
    "instrumentality or agency for the State of New Jersey or of any of its "
    "political subdivisions."
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["act_id"] == ACT_ID
    return rows[0]


def test_fixture_is_a_provenanced_verbatim_real_row_with_the_has_same_meaning_shape():
    """Sanity: guards against this RED silently going vacuous if the
    fixture is ever edited. The row must still have its real Definitions
    heading, the victim term's own tight "means" idiom, and the NEXT
    term's own untight-today "has the same meaning" idiom immediately
    after ITS closing quote (the exact precondition for the ceiling-trip)."""
    row = _load_row()
    assert is_definitions_heading(row["section_title"]) is True
    text = row["text"]
    assert f'"{TERM}" means' in text
    assert '"State wage, benefit and tax laws" has the same meaning' in text, (
        "fixture no longer carries the next-entry 'has the same meaning' "
        "idiom this RED depends on -- test would be vacuous"
    )
    assert text.index(f'"{TERM}"') < text.index('"State wage, benefit and tax laws"')
    assert len(text) > 3000


def test_red_our_engine_drops_public_body_entirely_today():
    """RED at the engine level: `extract_quote_anchored_entries` should
    surface "Public body" bounded at the true next term -- today it is
    silently ABSENT (ceiling-dropped), not merely truncated."""
    from app.definition_links.rules.us_markers_boundary import (
        extract_quote_anchored_entries,
    )

    row = _load_row()
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert TERM in entries, (
        f"{TERM!r} is missing from extract_quote_anchored_entries's output entirely -- "
        f"expected once 'has the same meaning' is recognized: {EXPECTED_TEXT!r}. "
        f"Got terms: {sorted(entries)!r}"
    )
    assert entries[TERM] == EXPECTED_TEXT, (
        f"{TERM!r} recovered but with the wrong text: {entries[TERM]!r}, "
        f"expected {EXPECTED_TEXT!r}"
    )


def test_red_real_pipeline_never_captures_public_body_at_all(db_session, matter_with_users):
    """The load-bearing RED, end-to-end: through the real
    `ingest_us_statute_rows` -> `run_definition_linking` pipeline,
    "Public body" should be captured with its real, complete definition --
    today it is captured by NO path at all (dropped by the ceiling), so
    the term is entirely invisible to `run_definition_linking`."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="NJ Public body boundary-idiom recovery (issue #27)",
        rows=[row],
        jurisdiction="US-NJ",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list[Definition]] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d)

    assert TERM in by_term, (
        f"{TERM!r} was never captured by the real pipeline at all -- got terms "
        f"{sorted(by_term)!r}. This is a genuine, real, correct statutory "
        f"definition ({EXPECTED_TEXT!r}) silently invisible to every path today "
        "because its true closing boundary (the next term's 'has the same "
        "meaning' idiom) is not yet recognized."
    )
    texts = [d.definition_text for d in by_term[TERM]]
    assert EXPECTED_TEXT in texts, (
        f"{TERM!r} captured but not with its correct, complete text -- got {texts!r}, "
        f"expected {EXPECTED_TEXT!r}"
    )
