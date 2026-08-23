"""RED (sprint 2026-08-20-defs-boundary-idioms, issue #27) -- representative
ceiling-tripped loss, recovered by widening `_TIGHT_IDIOM_RE`
(`backend/app/definition_links/rules/us_markers_boundary.py`) to recognize
"shall include" as a defining idiom.

`STATE_NJ_T27_C1A_S1A-3.1`, term `"Department"`, is the FLAGSHIP example
named in issue #27's own director comment and the FX7 investigation
(`docs/sprint/sprints/2026-08-10-green-the-suite-log.md`, commit
`9f06dfc`'s test file `test_us_markers_fx7_ceiling_known_closed_scope.py`):
the real definition is one four-word sentence, `"the Department of
Transportation."`, but today's `_TIGHT_IDIOM_RE` does not recognize the
NEXT term's own idiom ("shall include", introducing `"New Jersey tolling
entity"`), so `close_entries` never sees a next `starts` entry to bound
"Department" against, `has_next_term` is False, zero hard-stops are found,
capture runs 10,319 chars to end-of-text, and `MAX_CLEAN_DEFINITION_LENGTH`
(3,000 chars) correctly drops the whole candidate -- "Department" is
entirely ABSENT from production today, not merely truncated.

Re-derived live this sprint (not trusting the stale 2026-08-11 "41 anchors"
count -- see this sprint's log doc): a direct-function scan of the 14
`us_markers_inline_quote._OTHER_JURISDICTIONS` states' Definitions-headed
sections, verified at REAL pipeline persistence altitude, finds the current
loss set is materially larger (118 real losses, not 41) and only ONE
clean, unambiguous "shall include"-recoverable case was found within that
scan: this row. (Other losses in the live-verified set are either
unrelated to idiom vocabulary at all -- e.g. `USC_T5_C75_S7511`
"furlough", whose true boundary is an un-quote-adjacent "(b)" LETTER
marker, a different defect family entirely and out of this item's scope
-- or too noisy to attribute a clean idiom to at planning altitude.)

Byte-verified against the real corpus this pass
(`us_nj_statutes.parquet`, vaquill/open-us-law): fixture vendored
verbatim, act_id/section_title/chapter/section_number unchanged."""
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
    / "us_markers_boundary_idioms_nj_department_row.json"
)

ACT_ID = "STATE_NJ_T27_C1A_S1A-3.1"
TERM = "Department"
EXPECTED_TEXT = "the Department of Transportation."


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["act_id"] == ACT_ID
    return rows[0]


def test_fixture_is_a_provenanced_verbatim_real_row_with_the_shall_include_shape():
    """Sanity: guards against this RED silently going vacuous if the
    fixture is ever edited. The row must still have its real Definitions
    heading, the victim term's own tight "means" idiom, and the
    NEXT term's own untight-today "shall include" idiom immediately after
    ITS closing quote (the exact precondition for the ceiling-trip)."""
    row = _load_row()
    assert is_definitions_heading(row["section_title"]) is True
    text = row["text"]
    assert f'"{TERM}" means' in text
    assert '"New Jersey tolling entity" shall include' in text, (
        "fixture no longer carries the next-entry 'shall include' idiom this "
        "RED depends on -- test would be vacuous"
    )
    assert text.index(f'"{TERM}"') < text.index('"New Jersey tolling entity"')
    assert len(text) > 3000


def test_red_our_engine_drops_department_entirely_today():
    """RED at the engine level: `extract_quote_anchored_entries` should
    surface "Department" bounded at the true next term -- today it is
    silently ABSENT (ceiling-dropped at 10,319 uncapped chars), not merely
    truncated."""
    from app.definition_links.rules.us_markers_boundary import (
        extract_quote_anchored_entries,
    )

    row = _load_row()
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert TERM in entries, (
        f"{TERM!r} is missing from extract_quote_anchored_entries's output entirely -- "
        f"expected once _TIGHT_IDIOM_RE recognizes 'shall include': {EXPECTED_TEXT!r}. "
        f"Got terms: {sorted(entries)!r}"
    )
    assert entries[TERM] == EXPECTED_TEXT, (
        f"{TERM!r} recovered but with the wrong text: {entries[TERM]!r}, "
        f"expected {EXPECTED_TEXT!r}"
    )


def test_red_real_pipeline_never_captures_department_at_all(db_session, matter_with_users):
    """The load-bearing RED, end-to-end: through the real
    `ingest_us_statute_rows` -> `run_definition_linking` pipeline (the
    exact live path, not a stubbed call), "Department" should be captured
    with its real, complete, four-word definition -- today it is captured
    by NO path at all (dropped by the ceiling), so the term is entirely
    invisible to `run_definition_linking`."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="NJ Department boundary-idiom recovery (issue #27)",
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
        "because its true closing boundary (the next term's 'shall include' "
        "idiom) is not yet recognized."
    )
    texts = [d.definition_text for d in by_term[TERM]]
    assert EXPECTED_TEXT in texts, (
        f"{TERM!r} captured but not with its correct, complete text -- got {texts!r}, "
        f"expected {EXPECTED_TEXT!r}"
    )
