"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 8, Task 3, director
ruling D-S15). South Carolina half -- see this module's sibling,
`test_us_scoped_inline_pipeline_subsection_outermost_digit_live.py`, for the
digit-outermost (Washington) half and the shared design rationale (split
across two files for the 300-line style gate).

D-S15: `"this subsection"` scopes to the TOP-LEVEL subdivision (OUTERMOST
open step at the trigger offset), not the innermost enclosing unit. The
rule currently ships the S-R14/S-R15 INTERIM (`_subsection_scope_level`
returns `path[-1]`, the innermost step) -- Developer cycle 4 is the
one-line flip to `path[0]` (outermost) that makes the tests below pass.
Both tests here are RED against the pre-flip tree BY DESIGN: they assert
the OUTERMOST-correct behavior, not the shipped interim.

`STATE_SC_T12_C6_A9_S12-6-1170`: real, unmodified, `(A)(1)..(4)` structure
-- upper_alpha-outermost (Ohio-style) ladder, digit one level below. Item
`(2)` defines `"retirement income"` `as used in this subsection`; items
`(1)` and `(3)` each genuinely reuse the term (`(4)` has no reuse of this
term but itself says `"this subsection"`, self-proving the subsection is
`(A)` and spans all 4 items, not just `(2)`). Byte-verified free of the
Oregon-row pin-cite corruption Task 1 found: every parenthesized token
from offset 0 through the last reuse used below (1141) is a genuine
structural marker (`_US_UNIT_MARKER_RE`'s only other hit before that point
is none -- the first citation-shaped token, a `"(A)"` cross-reference
inside subsection `(B)`, sits at offset 1664, well past every offset this
file touches). This is the SAME row the manager's own S-R15-verdict
harness reproduced end-to-end (sprint log): shipped INNERMOST links 0 of
4 genuine reuses, OUTERMOST links 4 of 4.

This is also the row that makes Task 1's Oregon direction-2 re-authoring
an "onto a clean row" (option (a)) rather than a same-row assertion flip:
Oregon's own resolver path is corrupted at the exact offsets that proof
would need, so the genuine cross-paragraph-same-subsection proof lives
here instead.
"""

from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_scoped_inline_subsection_outermost_rows.json"
)

_ACT_ID = "STATE_SC_T12_C6_A9_S12-6-1170"
_TERM = "retirement income"


@dataclass
class _Article:
    body: str


def _row() -> dict:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == _ACT_ID)


def _clean(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def _normalized_body(raw_text: str) -> str:
    from app.definition_links.normalize import strip_wikilinks
    from app.definition_links.us_profile import normalize_for_parsing

    normalized = normalize_for_parsing(raw_text)
    stripped, _hints = strip_wikilinks(normalized)
    return stripped


def _ground_truth_outermost(body: str, term: str) -> tuple[str, str]:
    """Independently ask core's OWN `resolve_unit_path` for the OUTERMOST
    step (`path[0]`) open at `"<term>"`'s quoted offset -- D-S15's own
    level choice, never the rule under test's `path[-1]` interim."""
    from app.definition_links.us_profile import resolve_unit_path

    offset = body.index(f'"{term}"')
    path = resolve_unit_path(_Article(body=body), char_offset=offset)
    assert path, f"ground truth itself resolved empty for {term!r} -- fixture row unsuitable"
    return path[0].kind, path[0].value


def _uses_edges(result, db_session, definition_id):
    from app.models.assertion import Assertion

    return [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == definition_id
    ]


def test_subsection_candidate_agrees_with_core_resolver_outermost_south_carolina():
    """Unit-level agreement pin (no DB): under D-S15 the candidate's
    `(scope_value, scope_unit_kind)` must equal core's OUTERMOST step at
    the trigger offset, not the innermost one -- computed dynamically
    here, never copied from a table. FAILS against the shipped S-R14/
    S-R15 interim (which stamps `path[-1]` = `digit '2'`); the ground
    truth below is `upper_alpha 'A'`."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _row()
    body = _normalized_body(row["text"])
    candidates = extract_us_scoped_inline_definitions(body)
    hits = [c for c in candidates if _TERM in c.terms]
    assert hits, "the real South Carolina 'retirement income' definition was never captured"
    candidate = hits[0]
    assert candidate.scope == "subsection"

    kind, value = _ground_truth_outermost(body, _TERM)
    assert candidate.scope_unit_kind == kind, (
        f"stamped kind {candidate.scope_unit_kind!r} != outermost {kind!r} -- the rule is still "
        "stamping the innermost step (S-R14/S-R15 interim), not the D-S15 outermost one"
    )
    assert candidate.scope_value == value


def test_subsection_scope_links_same_subsection_different_item_live_south_carolina(
    db_session, matter_with_users
):
    """BEHAVIOR half, D-S15's whole point: the real row's OWN reuses of
    "retirement income" in items `(1)` and `(3)` -- siblings of the
    defining item `(2)`, all under the SAME top-level subsection `(A)` --
    must get a `USES_DEFINITION` edge. No truncation needed: the real,
    unmodified row already isolates this direction (no OTHER subsection
    of this article mentions the term at all, so any edge is
    unambiguously attributable to the `(A)`-internal reuses).

    Ground-truthed via `re.finditer` against the real text, never
    hard-coded offsets. FAILS today: under the shipped innermost interim,
    `(1)`'s and `(3)'s digit values ('1', '3') never match the definer's
    own digit value ('2'), so zero of these genuine reuses link -- exactly
    the S-R15-verdict harness's "0 of 4" finding, reproduced live here.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]

    # +1: `.index` lands on the opening quote character, not the term text
    # itself, which is what `re.finditer` below actually matches.
    quoted_offset = text.index(f'"{_TERM}"') + 1
    reuse_offsets = [
        match.start() for match in re.finditer(re.escape(_TERM), text) if match.start() != quoted_offset
    ]
    assert len(reuse_offsets) == 4, (
        "fixture must carry exactly the definition's own quoted entry plus 4 real reuses in "
        "sibling items (1)/(3) -- ground truth missing, test cannot prove anything"
    )
    assert '"retirement income", as used in this subsection, means' in text, (
        "the defining quoted entry must be present verbatim"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="South Carolina Code (D-S15 outermost-scope proof)",
        rows=[_clean(row)],
        jurisdiction="US-SC",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert defs, "the real South Carolina 'retirement income' definition was never captured live"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "the real row's own reuses of 'retirement income' in sibling items (1)/(3) of the SAME "
        "top-level subsection (A) got no USES_DEFINITION edge at all -- under D-S15's outermost "
        "policy they must link; a silent under-link here is the exact failure mode D-S15 exists "
        "to close (sprint log, S-R15 verdict: shipped innermost links 0 of 4 on this exact row)"
    )
