"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 7, Task C, rulings
S-R14/S-R15). Texas half -- see this module's sibling,
`test_us_scoped_inline_pipeline_subsection_agreement_live.py`, for the
Ohio-style (upper_alpha-outermost) half and the shared design rationale
(split across two files for the 300-line style gate).

`STATE_TX_Coc_C2301_S2301.551`: federal lower_alpha-outermost ladder --
real `(a)(b)(c)` subsections, same shallow, single-level shape as the
South Carolina row (a `(1)(2)` list lives under `(b)`/`(c)`, never reached
by the offsets used here). Byte-verified free of the citation pin-cite
stack corruption Task A found elsewhere -- every parenthesized token in
this row is a genuine structural marker, confirmed by listing every
`_US_UNIT_MARKER_RE` match before selecting it. Proves the agreement
pin holds across DIFFERENT `resolve_unit_path` ladders, not just one.
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

_ACT_ID = "STATE_TX_Coc_C2301_S2301.551"


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
    at `"<term>"`'s quoted offset -- never the rule under test."""
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


def test_subsection_candidate_agrees_with_core_resolver_texas():
    """Same agreement pin as the South Carolina sibling file, on a row
    whose `resolve_unit_path` ladder is the FEDERAL lower_alpha-outermost
    convention instead of Ohio's upper_alpha-outermost one."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _row()
    body = _normalized_body(row["text"])
    candidates = extract_us_scoped_inline_definitions(body)
    hits = [c for c in candidates if "fee" in c.terms]
    assert hits, "the real Texas 'fee' definition was never captured"
    candidate = hits[0]
    assert candidate.scope == "subsection"

    kind, value = _ground_truth_innermost(body, "fee")
    assert candidate.scope_unit_kind == kind
    assert candidate.scope_value == value


def test_subsection_scope_links_both_directions_live_texas(db_session, matter_with_users):
    """BEHAVIOR half: the real row's subsection `(a)` reuse of "fee" must
    link; subsection `(b)`'s "may not pay a fee to any person" must not.
    `find_term_uses`'s `\\b` word boundaries mean the row's OWN plural
    "fees" (subsection `(c)`) is never a confound either way."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    assert text.count(" fee ") + text.count(" fee.") + text.count(" fee\n") >= 2, (
        "fixture must carry at least one in- and one out-of-subsection reuse of 'fee' -- "
        "ground truth missing, test cannot prove anything"
    )
    assert '"fee" does not include' in text, "the defining quoted entry must be present verbatim"

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Texas Occupations Code (subsection-scope agreement proof)",
        rows=[_clean(row)],
        jurisdiction="US-TX",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if "fee" in d["terms"]]
    assert defs, "the real Texas 'fee' definition was never captured live"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "the real row's own later reuse of 'fee' inside its OWN defining subsection (a) "
        "got no USES_DEFINITION edge -- our stamped scope_value/scope_unit_kind disagree "
        "with core's resolve_unit_path even though this row is byte-verified single-level"
    )


def test_subsection_scope_does_not_link_a_different_subsection_texas(
    db_session, matter_with_users
):
    """Negative direction: subsection `(a)`'s own two same-subsection
    reuses of "fee" sit either side of the definition in this row, so
    isolating the `(b)` mention needs dropping those two REAL sentences
    (both located and asserted present below, never invented) rather than
    a single-point truncation -- the marker chain and the definition's own
    sentence are otherwise untouched, verbatim."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    before_sentence = "(a) A vehicle lessor may not directly or indirectly accept a fee from a dealer. "
    after_sentence = (
        "This subsection does not authorize a fee for referring vehicle leases "
        "or prospective lessees.\n\n"
    )
    assert before_sentence in text and after_sentence in text, (
        "fixture text changed shape -- the two real sentences this truncation drops "
        "are no longer present verbatim"
    )
    truncated_text = text.replace(before_sentence, "(a) ").replace(after_sentence, "")
    assert '"fee" does not include' in truncated_text
    assert "may not pay a fee to any person" in truncated_text

    truncated_row = dict(row)
    truncated_row["act_id"] = "STATE_TX_Coc_C2301_S2301.551_SUBSECTION_ISOLATION_TRUNCATED"
    truncated_row["text"] = truncated_text

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Texas Occupations Code (subsection-scope agreement proof, negative direction)",
        rows=[_clean(truncated_row)],
        jurisdiction="US-TX",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if "fee" in d["terms"]]
    assert defs, "the real Texas 'fee' definition was never captured from the truncated body"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert not uses_edges, (
        f"a mention of 'fee' in subsection (b), a DIFFERENT subsection than the one "
        f"defining it, got a USES_DEFINITION edge anyway: {uses_edges!r}"
    )
