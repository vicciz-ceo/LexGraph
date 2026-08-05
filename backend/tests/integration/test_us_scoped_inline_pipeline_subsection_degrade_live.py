"""QA cycle 2 (sprint 2026-08-04-defs-us-scoped-inline). Pins the coverage
gap dev4 found and the manager routed to this cycle (`-log.md`, "NEW
coverage gap found by dev4, routed to QA cycle 2"): **no pytest test
exercises the empty-path `"local"` degrade branch on a real state row.**

The two existing tests that cite Maine/Florida as their motivation
(`test_bare_quote_means_subsection_scope_maine` in `..._rules_body_axis.py`,
and the period-style-marker fix pin in
`test_us_scoped_inline_planner_pass6_missed_conventions.py`) both resolve
NON-EMPTY paths at their trigger offsets -- the Maine test's own docstring
says so explicitly ("its `resolve_unit_path` is non-empty but built from
unrelated CITATION pin-cites"). Neither exercises
`_resolve_subsection_scope`'s degrade branch (S-R14/S-R16: `resolve_unit_
path` recognizes only PARENTHESIZED markers, so Maine's real period-style
subsection numbering -- `25.`, `26.`, `27.` here -- is invisible to it,
and the branch returns `"local", None, None` on an empty path).

`STATE_ME_T12_P13_C937_S13106-A`: a real, unmodified, LONG Maine statute
whose subsections are numbered `25.` `26.` `27.` (period-style, genuinely
invisible to core's paren-only marker regex -- independently confirmed
below via a direct, dynamic call to `resolve_unit_path` at the trigger
offset, never assumed from a docstring). Subsection `26.` defines
`"snowmobile trail"` (`"For purposes of this subsection, "snowmobile
trail" means..."`); subsection `27.` (a DIFFERENT top-level, period-
numbered subsection, genuinely later in the same article) reuses the term
naturally. Under a genuine (non-degraded) `"subsection"` scope this
cross-subsection mention would NOT link (exactly the containment the SC/
WA/TX sibling files prove); under the `"local"` degrade it SHOULD -- the
whole point of degrading to the narrowest REPRESENTABLE unit rather than
shipping a scope guaranteed to link nothing (S-R9/S-R11/S-R14 zero-miss
precedent). This file is the first live-path proof that the degrade
branch is not just theoretically reachable but is ACTUALLY exercised, on
real text, on the real pipeline.
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
    / "qa_cycle2_subsection_degrade_rows.json"
)

_ACT_ID = "STATE_ME_T12_P13_C937_S13106-A"
_TERM = "snowmobile trail"


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


def _uses_edges(result, db_session, definition_id):
    from app.models.assertion import Assertion

    return [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == definition_id
    ]


def test_trigger_offset_genuinely_resolves_an_empty_path_maine():
    """Ground truth, computed dynamically (never assumed): core's OWN
    `resolve_unit_path`, called at the exact trigger offset, returns an
    empty path for this row -- the precondition for the degrade branch to
    fire at all. If this ever stops being true (core extends its marker
    regex to recognize period-style numbering), this test -- not the
    behavior test below -- is the one that should start failing, which is
    exactly why it is pinned separately."""
    from app.definition_links.us_profile import resolve_unit_path

    row = _row()
    body = _normalized_body(row["text"])
    offset = body.index('"snowmobile trail" means')
    path = resolve_unit_path(_Article(body=body), char_offset=offset)
    assert path == (), (
        f"expected an EMPTY path at the trigger offset (Maine's real period-style '25.'/'26.'/"
        f"'27.' numbering is invisible to core's paren-only marker regex) -- got {path!r}. If "
        "core's resolver now sees period-style markers, the degrade branch this file exists to "
        "pin no longer fires on this row; find a fresh degraded row instead of relaxing this."
    )


def test_candidate_degrades_to_local_scope_maine():
    """Unit-level pin (no DB): the rule's OWN candidate for 'snowmobile
    trail' must carry `scope == "local"`, not `"subsection"` -- confirms
    `_resolve_subsection_scope`'s degrade branch is what actually produces
    this candidate, not a genuinely-resolved subsection step."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _row()
    body = _normalized_body(row["text"])
    candidates = extract_us_scoped_inline_definitions(body)
    hits = [c for c in candidates if _TERM in c.terms]
    assert hits, "the real Maine 'snowmobile trail' definition was never captured"
    assert hits[0].scope == "local"
    assert hits[0].scope_value is None
    assert hits[0].scope_unit_kind is None


def test_degraded_definition_links_a_mention_in_a_different_period_numbered_subsection_live(
    db_session, matter_with_users
):
    """BEHAVIOR half, the actual coverage gap: subsection `27.`'s own
    natural reuse of "snowmobile trail" -- a DIFFERENT top-level,
    period-numbered subsection than `26.`, where the term is defined --
    must get a `USES_DEFINITION` edge. Ground-truthed via `re.finditer`
    against the real, unmodified text (never hard-coded offsets): the
    fixture's own defining sentence anchors the split between "the
    definition's own entry" and "later reuses," and the reuse used here is
    independently confirmed (by its raw offset, printed during authoring,
    not repeated here since the code below re-derives it dynamically) to
    sit inside a later, differently-numbered period-style subsection than
    the one containing the trigger.

    A genuinely-resolved `"subsection"` scope (as SC/WA/TX prove
    elsewhere) would NOT link this mention -- it is a different top-level
    subsection. The degrade's `"local"` scope SHOULD, because it is
    article-wide by design (the zero-miss-safe fallback when core cannot
    resolve a real subsection step at all)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]

    def_start = text.index(f'"{_TERM}" means')
    def_end = text.index(".", def_start) + 1
    reuse_offsets = [
        match.start() for match in re.finditer(re.escape(_TERM), text) if match.start() > def_end
    ]
    assert reuse_offsets, (
        "fixture must reuse the term again AFTER its own defining sentence -- ground truth "
        "missing, test cannot prove anything"
    )
    # independently confirm at least one of those reuses sits in a
    # DIFFERENT period-numbered subsection than the definer -- never
    # trusted from the module docstring, re-derived here from the raw text
    def_subsection = _period_subsection_label(text, def_start)
    cross_subsection_reuses = [
        off for off in reuse_offsets if _period_subsection_label(text, off) != def_subsection
    ]
    assert cross_subsection_reuses, (
        f"expected at least one reuse of {_TERM!r} outside subsection {def_subsection!r} -- "
        "fixture text changed shape, this proof needs a genuine cross-subsection reuse"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Maine Revised Statutes (subsection-scope EMPTY-PATH degrade live proof)",
        rows=[_clean(row)],
        jurisdiction="US-ME",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert defs, "the real Maine 'snowmobile trail' definition was never captured live"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "local", (
        f"expected the degrade to persist scope='local', got {definition_row.scope!r} -- if "
        "this now resolves to a real 'subsection' scope, the degrade branch is no longer being "
        "exercised by this row (see test_trigger_offset_genuinely_resolves_an_empty_path_maine)"
    )

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "a mention of 'snowmobile trail' in a DIFFERENT, later, period-numbered subsection than "
        "the one defining it got no USES_DEFINITION edge -- under the 'local' degrade this "
        "article-wide mention must link; this is the empty-path degrade branch's own live-path "
        "coverage gap dev4 found and this file exists to close"
    )


def _period_subsection_label(text: str, offset: int) -> str | None:
    """The nearest preceding period-style subsection marker (`\\n25.`,
    `\\n26.`, ...) before `offset` -- Maine's real, unmodified numbering
    convention on this row, independently re-derived from the raw text
    every time this is called, never cached from a prior run."""
    matches = list(re.finditer(r"\n(\d+(?:-[A-Z])?)\.\s", text[:offset]))
    return matches[-1].group(1) if matches else None
