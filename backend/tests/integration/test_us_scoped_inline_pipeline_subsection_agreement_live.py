"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 7, Task C, rulings
S-R14/S-R15). South Carolina half -- see this module's sibling,
`test_us_scoped_inline_pipeline_subsection_agreement_texas_live.py`, for
the federal-ladder half and the shared design rationale (split across two
files for the 300-line style gate).

Pins AGREEMENT between our rule's stamped `(scope_value, scope_unit_kind)`
and an INDEPENDENT call to core's own `profile.resolve_unit_path` -- never
a hard-coded kind string. That discipline is S-R10's own: a test that
hard-coded `"lower_alpha"` would have PASSED while the real answer on a
different real row was `"lower_roman"` (the sprint log's S-R14 section,
the real Oregon `STATE_OR_T22_C238_S238.300` measurement) -- exactly the
defect class this file exists to keep un-reintroducible.

`STATE_SC_T14_C7_A7_S14-7-845`: upper_alpha-outermost (Ohio-style) ladder
-- real `(A)(B)(C)` subsections, no deeper nesting for either term used
here. Byte-verified free of the citation pin-cite stack corruption Task A
found elsewhere (Maine's CFR/USC pin-cites, this same state's OWN
`"(C)(2)(c)"` cross-reference in a DIFFERENT row) -- every parenthesized
token in this row IS a genuine structural marker (confirmed by listing
every `_US_UNIT_MARKER_RE` match before selecting it), and deliberately
SINGLE-LEVEL (innermost == outermost) so the S-R15 open question -- WHICH
step of a multi-level path to stamp -- cannot confound this file's
verdict either way. Planner pass 7's Task A report has the multi-level
counterexample from this SAME state (`STATE_SC_T12_C6_A9_S12-6-1170`)
that makes S-R15 an escalation, not a fixture for this file.

FIXED (Planner pass 8, Task 2): `test_subsection_scope_does_not_link_a_
different_subsection_south_carolina` (originally about the "school
employee" term) had a factually wrong premise -- it called the term's
one out-of-quote mention "in subsection (A)" and asserted it must NOT
link. Checking the row's own text: `(A)` begins at offset 0, `(B)` at
307, `(C)` at 1197; the definition's trigger is at 709, INSIDE `(B)`
(`For purposes of this subsection, a "school employee" is a person
employed...`); the mention the old test called "in subsection (A)" is at
offset 334 -- 27 characters AFTER `(B)` begins, in `(B)`'s own opening
clause (`(B) If a public or private school employee, a person...`). The
mention is in the SAME subsection as the definition and SHOULD link.

Director ruling D-S15 does NOT fix this test, because it cannot: this
row is single-level (no nesting under `(A)`/`(B)`/(C)`), so innermost and
outermost resolve to the identical step -- verified directly against the
real matcher, both policies agree here. "Fixing" the old assertion to
pass as written would have meant teaching the rule to under-link a
mention sitting inside its own definition's subsection, the exact
silent-miss failure mode this whole family exists to eliminate. Renamed
and re-authored below to assert what the row actually says; the genuine
"different top-level subsection" (direction 2) proof for THIS state now
lives in `test_us_scoped_inline_pipeline_subsection_outermost_live.py`
(multi-level `STATE_SC_T12_C6_A9_S12-6-1170`), since a single-level row
can never distinguish the two policies.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_scoped_inline_subsection_agreement_rows.json"
)

_ACT_ID = "STATE_SC_T14_C7_A7_S14-7-845"


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


def _ground_truth_innermost(body: str, term: str) -> tuple[str, str]:
    """Independently ask core's OWN `resolve_unit_path` what unit is open
    at `"<term>"`'s quoted offset (this row has no marker between the
    trigger and the quote, so this offset and the trigger's are
    equivalent) -- never the rule under test."""
    from app.definition_links.us_profile import resolve_unit_path

    offset = body.index(f'"{term}"')
    path = resolve_unit_path(_Article(body=body), char_offset=offset)
    assert path, f"ground truth itself resolved empty for {term!r} -- fixture row unsuitable"
    return path[-1].kind, path[-1].value


def _uses_edges(result, db_session, definition_id):
    from app.models.assertion import Assertion

    return [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == definition_id
    ]


def test_subsection_candidate_agrees_with_core_resolver_south_carolina():
    """Unit-level agreement pin (no DB): `extract_us_scoped_inline_
    definitions`'s OWN candidate for "school term" must carry
    `(scope_value, scope_unit_kind)` equal to whatever
    `profile.resolve_unit_path` independently resolves at the SAME
    offset -- computed dynamically here, never copied from a table."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _row()
    body = _normalized_body(row["text"])
    candidates = extract_us_scoped_inline_definitions(body)
    hits = [c for c in candidates if "school term" in c.terms]
    assert hits, "the real South Carolina 'school term' definition was never captured"
    candidate = hits[0]
    assert candidate.scope == "subsection"

    kind, value = _ground_truth_innermost(body, "school term")
    assert candidate.scope_unit_kind == kind
    assert candidate.scope_value == value


def test_subsection_scope_links_both_directions_live_south_carolina(
    db_session, matter_with_users
):
    """BEHAVIOR half: the real row's OWN subsection `(A)` mentions of
    "school term" (before subsection `(B)`, where the term is actually
    defined, even begins) must NOT link; subsection `(B)`'s own later
    reuse must. Both are real, unmodified text -- ground-truthed via
    `str.count`, never hard-coded offsets."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    assert text.count("school term") >= 3, (
        "fixture must carry the definition plus at least one in- and one out-of-subsection "
        "reuse -- ground truth missing, test cannot prove anything"
    )
    assert '"school term" means' in text, "the defining quoted entry must be present verbatim"

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="South Carolina Code (subsection-scope agreement proof)",
        rows=[_clean(row)],
        jurisdiction="US-SC",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if "school term" in d["terms"]]
    assert defs, "the real South Carolina 'school term' definition was never captured live"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "the real row's own later reuse of 'school term' inside its OWN defining subsection "
        "(B) got no USES_DEFINITION edge -- our stamped scope_value/scope_unit_kind disagree "
        "with core's resolve_unit_path even though this row is byte-verified single-level"
    )


def test_subsection_scope_links_a_same_subsection_mention_south_carolina_school_employee(
    db_session, matter_with_users
):
    """FIXED (Planner pass 8, Task 2 -- see module docstring for the full
    story): same row, a DIFFERENT term, "school employee". Its one
    out-of-quote mention (offset 334) sits 27 characters AFTER subsection
    `(B)` begins (offset 307) -- the SAME subsection as the definition's
    own trigger (offset 709), not "subsection (A)" as the test this
    replaces incorrectly claimed. It must link.

    Ground-truthed against the real, unmodified text below (never trusted
    from a docstring): the mention's offset must fall AFTER `(B)`'s own
    marker and BEFORE `(C)`'s."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    assert text.count("school employee") == 2, (
        "fixture must carry exactly the definition plus one same-subsection mention -- "
        "ground truth missing, test cannot prove anything"
    )
    assert '"school employee" is a person' in text, "the defining quoted entry must be present"

    b_start = text.index("(B)")
    c_start = text.index("(C)")
    mention_offset = text.index("school employee")
    assert b_start < mention_offset < c_start, (
        "the mention of 'school employee' must sit inside subsection (B), the SAME subsection "
        "as its own definition -- ground truth missing, test cannot prove anything"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="South Carolina Code (subsection-scope agreement proof, same-subsection direction)",
        rows=[_clean(row)],
        jurisdiction="US-SC",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if "school employee" in d["terms"]]
    assert defs, "the real South Carolina 'school employee' definition was never captured live"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "a mention of 'school employee' inside its OWN defining subsection (B) got no "
        "USES_DEFINITION edge -- our stamped scope_value/scope_unit_kind disagree with core's "
        "resolve_unit_path even though this row is byte-verified single-level"
    )
