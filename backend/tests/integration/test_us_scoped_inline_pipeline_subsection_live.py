"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 3, ruling S-R10).

`test_us_scoped_inline_pipeline_live.py`'s U2 both-directions proofs cover
`scope="local"` and `scope="chapter"` only. `scope="subsection"` was never
proven on the live path -- only STAMPED (that file's own
`test_a_scope_unit_not_yet_enforced_by_matcher_is_still_stamped_faithfully`).
This file closes that coverage gap.

The risk (S-R10): `us_scoped_inline._subsection_label` derives the defining
subsection's label with its OWN regex (a paragraph-initial-marker
heuristic). `matcher._subsection_contains_offset` (`matcher.py:166`)
compares that label against a SECOND, INDEPENDENT derivation --
`profile.resolve_unit_path(article, char_offset)[0].value`, a flat,
sequential marker-kind-ladder scan living entirely in core's
`us_profile.py`. Nothing before this proved the two derivations ever
agree. If they disagree, `_subsection_contains_offset` returns False for
EVERY mention, including one sitting inside the definition's own
subsection -- a silent, total under-link, exactly what the absolute
zero-miss bar forbids and exactly what unit-green-but-live-dead testing
hides.

Deliberately does NOT assert the label's literal string (e.g. `"(c)"`)
anywhere -- core has a pending fix to `resolve_unit_path`'s handling of
Maine's inline `(NEW)`/`(AMD)`/`(AFF)` legislative-history annotations,
which will change nearest-marker derivation edge cases. This test pins
AGREEMENT/behavior only, so it survives that fix unchanged.

Uses the real, unmodified `STATE_OR_T22_C238_S238.300` (Oregon --
deliberately NON-Maine, so this proof is not confounded by that specific,
already-known annotation defect). The row's own real text defines
`"number of years of membership"` via `"(c) As used in this subsection,
... means ..."` nested inside subsection `(2)`, and NATURALLY (no
invented prose) reuses the same phrase twice more later in that SAME `(c)`
clause, and ALSO uses it twice earlier inside sibling clauses
`(2)(a)(A)`/`(2)(a)(B)` -- a different subsection of the very same
article, before the definition even appears. Both directions' raw
material already exist in one unmodified row; ground-truthed below via
`re.finditer` on the real text, never hard-coded offsets.

The "different subsection, same article" direction needs the SAME
article's body to carry ONLY the out-of-subsection mentions, with no
in-subsection reuse alongside them -- otherwise a single surviving
`USES_DEFINITION` assertion (Stage 3's dedup key is `(subject, object,
proposition)`, not per-mention) cannot be attributed to either direction.
`test_...different_subsection_does_not_link` therefore ingests the SAME
real row's text MECHANICALLY TRUNCATED right after the defining sentence
ends -- every remaining character is a real, verbatim substring of the
vendored row, nothing invented -- which drops the two later in-subsection
reuses while keeping the two earlier out-of-subsection ones and the
definition itself intact.
"""

from __future__ import annotations

import json
import pathlib
import re

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)

_TERM = "number of years of membership"
_DEFINING_SENTENCE_END = (
    "creditable service plus any remaining fraction of a year of creditable service."
)


def _row() -> dict:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == "STATE_OR_T22_C238_S238.300")


def _clean(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def _uses_edges(result, db_session, definition_id):
    from app.models.assertion import Assertion

    return [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == definition_id
    ]


def test_subsection_scoped_definition_links_a_mention_inside_its_own_subsection(
    db_session, matter_with_users
):
    """Direction 1 of gate U2 for `scope="subsection"`: the real row's OWN
    later reuse of "number of years of membership", inside the SAME `(c)`
    clause that defines it, must get a `USES_DEFINITION` edge.

    Ground-truthed against the real, unmodified text (not assumed): the
    defining sentence ends at `_DEFINING_SENTENCE_END`; any occurrence of
    the term AFTER that point is a genuine in-subsection reuse, not the
    definition's own quoted entry.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    def_end = text.index(_DEFINING_SENTENCE_END) + len(_DEFINING_SENTENCE_END)
    in_subsection_offsets = [
        match.start() for match in re.finditer(re.escape(_TERM), text) if match.start() >= def_end
    ]
    assert in_subsection_offsets, (
        "fixture must reuse the term again inside its own defining subsection, "
        "after the defining sentence -- ground truth missing, test cannot prove anything"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Oregon Revised Statutes (subsection-scope live agreement proof, in-subsection direction)",
        rows=[_clean(row)],
        jurisdiction="US-OR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    nym_defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert nym_defs, "the real Oregon subsection-scoped definition was never captured at all"
    definition_id = nym_defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "a mention of 'number of years of membership' inside its OWN defining subsection "
        "got no USES_DEFINITION edge at all. This means "
        "us_scoped_inline._subsection_label's derivation and "
        "matcher._subsection_contains_offset's profile.resolve_unit_path derivation "
        "DISAGREE even for a mention truly inside the defining subsection -- exactly the "
        "silent under-link ruling S-R10 exists to catch. Report this to the manager; do "
        "not patch us_scoped_inline.py to route around a core (us_profile.py) defect."
    )


def test_subsection_scoped_definition_does_not_link_a_mention_in_a_different_subsection(
    db_session, matter_with_users
):
    """Direction 2 of gate U2 for `scope="subsection"`: a mention of the
    SAME term inside a DIFFERENT subsection of the SAME article (the real
    row's own `(2)(a)(A)`/`(2)(a)(B)` clauses, both BEFORE the `(2)(c)`
    definition) must NOT get a `USES_DEFINITION` edge.

    Ingests the real row's text mechanically truncated right after
    `_DEFINING_SENTENCE_END` -- every character kept is a real, verbatim
    substring of the vendored row (no invented prose) -- which drops the
    two LATER in-subsection reuses this file's other test exercises,
    isolating this direction: the only candidate "reuse" mentions left in
    this body are the two out-of-subsection ones, so any created
    `USES_DEFINITION` edge would be directly attributable to one of them.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    def_end = text.index(_DEFINING_SENTENCE_END) + len(_DEFINING_SENTENCE_END)
    truncated_text = text[:def_end]

    out_of_subsection_offsets = [
        match.start() for match in re.finditer(re.escape(_TERM), truncated_text) if match.start() < def_end
    ]
    # 2 out-of-subsection reuses plus the definition's own quoted entry.
    assert len(out_of_subsection_offsets) >= 3, (
        "truncation must keep the real row's own 2 out-of-subsection mentions plus the "
        "definition's own entry -- ground truth missing, test cannot prove anything"
    )

    truncated_row = dict(row)
    truncated_row["act_id"] = "STATE_OR_T22_C238_S238.300_SUBSECTION_ISOLATION_TRUNCATED"
    truncated_row["text"] = truncated_text

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Oregon Revised Statutes (subsection-scope live agreement proof, out-of-subsection direction)",
        rows=[_clean(truncated_row)],
        jurisdiction="US-OR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    nym_defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert nym_defs, "the real Oregon subsection-scoped definition was never captured from the truncated body"
    definition_id = nym_defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert not uses_edges, (
        "a mention of 'number of years of membership' in a DIFFERENT subsection of the "
        f"SAME article got a USES_DEFINITION edge anyway: {uses_edges!r} -- a subsection-"
        "scoped definition must never link a mention outside its own subsection"
    )
