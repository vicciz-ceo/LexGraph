"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 8, Task 3, director
ruling D-S15). Washington half -- see this module's sibling,
`test_us_scoped_inline_pipeline_subsection_outermost_live.py`, for the
upper_alpha-outermost (South Carolina) half and the shared design
rationale (split across two files for the 300-line style gate). Proves
D-S15's fix holds across a DIFFERENT `resolve_unit_path` ladder, not just
one -- `resolve_unit_path` picks its ladder per-call from the shape of the
row's own first genuine marker, and Washington's is digit-shaped.

`STATE_WA_T18_C104_S065`: real, unmodified, `(1)(2)(a)(b)(3)` structure --
digit-outermost (Oregon-style, per `us_profile.py`'s own ladder comment)
ladder, lower_alpha one level below. Item `(2)(b)` defines `"construction
has been substantially completed"` `For purposes of this subsection`
(D-S15: `"this subsection"` names the OUTERMOST unit open at the trigger,
here digit `'2'`, not the innermost lower_alpha `'b'`). Item `(2)(a)`
genuinely reuses the term twice.

Byte-verified free of pin-cite corruption: `_US_UNIT_MARKER_RE`'s full hit
sequence up to the last offset this file touches is `(1)@0, (2)@281,
(a)@349, (b)@516` -- every one a genuine structural marker, nothing
citation-shaped before them. (The one real citation-shaped token in this
row, `"Subsection (2) of this section"` inside item `(3)`, sits at offset
866 -- well past every offset used below.)
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

_ACT_ID = "STATE_WA_T18_C104_S065"
_TERM = "construction has been substantially completed"


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


def test_subsection_candidate_agrees_with_core_resolver_outermost_washington():
    """Same agreement pin as the South Carolina sibling file, on a row
    whose `resolve_unit_path` ladder is digit-outermost instead of
    upper_alpha-outermost. FAILS against the shipped interim (`path[-1]`
    = `lower_alpha 'b'`); ground truth below is `digit '2'`."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _row()
    body = _normalized_body(row["text"])
    candidates = extract_us_scoped_inline_definitions(body)
    hits = [c for c in candidates if _TERM in c.terms]
    assert hits, "the real Washington 'construction has been substantially completed' definition was never captured"
    candidate = hits[0]
    assert candidate.scope == "subsection"

    kind, value = _ground_truth_outermost(body, _TERM)
    assert candidate.scope_unit_kind == kind, (
        f"stamped kind {candidate.scope_unit_kind!r} != outermost {kind!r} -- the rule is still "
        "stamping the innermost step (S-R14/S-R15 interim), not the D-S15 outermost one"
    )
    assert candidate.scope_value == value


def test_subsection_scope_links_same_subsection_different_item_live_washington(
    db_session, matter_with_users
):
    """BEHAVIOR half: item `(2)(a)`'s own two real reuses of the term --
    a SIBLING of the defining item `(2)(b)`, both under the SAME top-level
    subsection `(2)` -- must get a `USES_DEFINITION` edge.

    The real row ALSO carries two same-item ('b') reuses immediately
    before the definer, which already link under the shipped innermost
    interim (same lower_alpha value) and would mask this direction. This
    truncation drops ONLY that one real sentence (asserted present
    verbatim below, nothing invented) so the surviving reuses are
    unambiguously the cross-item `(2)(a)` ones -- the same isolation
    technique the Texas sibling file (Task C) uses.

    FAILS today: under the shipped innermost interim, `(a)`'s lower_alpha
    value ('a') never matches the definer's own ('b'), so these two
    genuine reuses do not link.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]

    before_sentence = (
        "(b) For wells for which construction has been substantially completed on or after "
        "July 1, 1993, more than three years after construction has been substantially "
        "completed. "
    )
    assert before_sentence in text, (
        "fixture text changed shape -- the real sentence this truncation drops is no longer "
        "present verbatim"
    )
    truncated_text = text.replace(before_sentence, "(b) ")

    # +1: `.index` lands on the opening quote character, not the term text
    # itself, which is what `re.finditer` below actually matches.
    quoted_offset = truncated_text.index(f'"{_TERM}"') + 1
    reuse_offsets = [
        match.start()
        for match in re.finditer(re.escape(_TERM), truncated_text)
        if match.start() != quoted_offset
    ]
    assert len(reuse_offsets) == 2, (
        "truncation must keep exactly the definition's own quoted entry plus item (a)'s 2 real "
        "reuses -- ground truth missing, test cannot prove anything"
    )
    assert f'"{_TERM}" has the same meaning' in truncated_text, (
        "the defining quoted entry must be present verbatim"
    )

    truncated_row = dict(row)
    truncated_row["act_id"] = f"{_ACT_ID}_SUBSECTION_ISOLATION_TRUNCATED"
    truncated_row["text"] = truncated_text

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Washington RCW (D-S15 outermost-scope proof, digit-outermost ladder)",
        rows=[_clean(truncated_row)],
        jurisdiction="US-WA",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert defs, (
        "the real Washington 'construction has been substantially completed' definition was "
        "never captured live from the truncated body"
    )
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "item (2)(a)'s own reuses of the term, in a DIFFERENT item of the SAME top-level "
        "subsection (2), got no USES_DEFINITION edge -- under D-S15's outermost policy they "
        "must link; a silent under-link here is the exact failure mode D-S15 exists to close"
    )
