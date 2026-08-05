"""QA cycle 2 (sprint 2026-08-04-defs-us-scoped-inline). Item 12,
specifically requested: Planner pass 8's own named gap on D-S15's two NEW
outermost-policy fixture rows (South Carolina, Washington) is that
NEITHER carries a real out-of-(top-level)-subsection mention -- both
sibling files only pin the POSITIVE "same top-level subsection, different
item, links" direction (their own module docstrings say so explicitly).
This file finds a DIFFERENT real row where a genuine out-of-subsection
mention DOES exist, and pins whether the negative direction holds live
under the shipped outermost policy.

`STATE_AL_T25_C4_S25-4-75`: real, unmodified, long Alabama unemployment-
benefits statute with clean, non-corrupted top-level lettered subsections
`(a)` through `(m)` -- independently confirmed below: every top-level
marker occurs at a genuine paragraph break, `\\n\\n(<letter>) `, in strict
alphabetical sequence. (QA's FIRST candidate for this proof,
`STATE_AL_T13A_C6_S13A-6-130`, was rejected after a cheap "does the marker
occur somewhere" guard turned out to be insufficient: that row's own
top-level path is CORRUPTED by a mid-sentence citation, `"under subsection
(b)"`, sitting inside subsection `(c)` -- exactly the pin-cite corruption
class the manager warned QA not to certify a row through. The stricter
guard here -- genuine markers occur only at `\\n\\n(<letter>) ` paragraph
starts, in strict alphabetical order -- is what caught it and is re-run as
its own test below.)

Subsection `(i)`, item `(3)`, defines `"suitable work"`
(`"For the purposes of this subsection (i), the term "suitable work"
means..."`); subsections `(j)` and `(k)` each naturally reuse the term
(`(j)`'s own text even says so itself: `"...to which the definition in
subdivision (i)(4) does not apply."`). Subsection `(i)` ALSO reuses the
term twice more, in its own items `(1)` and `(4)` -- genuine same-
subsection reuses that WOULD (correctly) link too, which would mask the
negative-direction proof this file needs (the pipeline's `USES_DEFINITION`
assertion is one-per-article-per-definition, aggregating every matching
mention, not one per offset -- QA discovered this the hard way: an
untruncated first draft of this test failed because the in-subsection
reuses alone were enough to produce the assertion). The isolation
technique below (same rationale as the WA/TX sibling files) drops ONLY
subsection `(i)`'s own items `(1)`/`(2)`/`(4)`/`(5)` -- verbatim text,
asserted present before truncation -- keeping item `(3)`'s defining
sentence and the `(j)`/`(k)` reuses untouched, so any resulting edge is
unambiguously attributable to the out-of-subsection mentions.
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
    / "qa_cycle2_subsection_outermost_negative_rows.json"
)

_ACT_ID = "STATE_AL_T25_C4_S25-4-75"
_TERM = "suitable work"

_TOP_LEVEL_MARKER_RE = re.compile(r"(?:\A|\n\n)\(([a-z])\)\s")

_ITEMS_1_2 = (
    "(1) Notwithstanding the other provisions of this section, payment of any extended "
    "benefits under this section shall not be made to any individual for any week of "
    "unemployment in his eligibility period:\n\n"
    "a. during which he fails to accept any offer of suitable work as defined in "
    "subdivision (i)(3) or fails to apply for any such suitable work to which he was "
    "referred by the secretary; or\n\n"
    "b. during which he fails to actively seek work, except as provided in subdivision "
    "(a)(5) of Section 25-4-77, but only with regard to the exception for the appearance "
    "for jury duty as provided therein.\n\n"
    "(2) If any individual is ineligible for extended benefits for any week by reason of "
    "a failure described in subdivision (i)(1), the individual shall be ineligible to "
    "receive extended benefits for any week during a period which:\n\n"
    "a. begins with the week following the week in which such failure occurs and\n\n"
    "b. does not end until such individual has been employed in at least four weeks "
    "which begin after such failure and the total of the remuneration earned by the "
    "individual for being so employed is not less than four times his extended weekly "
    "benefit amount for his benefit year.\n\n"
)

_DEFINITION_TAIL_AND_ITEMS_4_5 = (
    "; except that, if the individual furnishes evidence satisfactory to the secretary "
    "that such individual’s prospects for obtaining work in his customary occupation "
    "within a reasonably short period are good, the determination of whether any work is "
    "suitable work shall be made in accordance with other provisions of this chapter."
    "\n\n(4) Extended benefits shall not be denied under paragraph a. of subdivision "
    "(i)(1) to any individual for any week by reason of a failure to accept an offer of, "
    "or apply for, suitable work:\n\n"
    "a. If the gross average weekly remuneration payable to such individual for the "
    "position does not exceed the sum of:\n\n"
    "1. the individual’s extended weekly benefit amount for the benefit year plus;\n\n"
    "2. the amount if any of supplemental unemployment benefits (as defined in 26 U.S.C. "
    "501(c)(17)(D)) payable to such individual for such week;\n\n"
    "b. if the position was not offered to such individual in writing or was not listed "
    "with the state employment service;\n\n"
    "c. if such failure would not result in a denial of benefits under the other "
    "provisions of this chapter to the extent that such provisions are not inconsistent "
    "with subdivisions (4) and (5) of this subsection (i); or\n\n"
    "d. if the position pays wages less than the higher of the minimum wages provided "
    "under Section 6 (a)(1) of the Fair Labor Standards Act of 1938, as amended, without "
    "regard to any exemption or the applicable state or local minimum wage, if any.\n\n"
    "(5) For purposes of this subsection (i), an individual shall be treated as actively "
    "engaged in seeking work during any week if the individual has engaged in a "
    "systematic and sustained effort to obtain work during such week, and provides "
    "tangible evidence to the secretary that he has engaged in such effort during such "
    "week."
)


@dataclass
class _Article:
    body: str


def _row() -> dict:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == _ACT_ID)


def _top_level_label(text: str, offset: int) -> str | None:
    matches = list(_TOP_LEVEL_MARKER_RE.finditer(text[:offset]))
    return matches[-1].group(1) if matches else None


def _uses_edges(result, db_session, definition_id):
    from app.models.assertion import Assertion

    return [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == definition_id
    ]


def test_top_level_markers_are_clean_not_pin_cite_corrupted():
    """Ground truth precondition (P-R10 probe sanity), checked before
    anything else: every top-level lettered marker in the real,
    UNTRUNCATED row occurs at a genuine paragraph break, in strict
    alphabetical order, with no out-of-sequence repeat -- unlike a
    pin-cite-corrupted row (e.g. a mid-sentence "under subsection (x)"
    citation), where the SAME letter can recur out of order and silently
    reset the resolver's top-level position. This is exactly the guard
    that rejected QA's first candidate row for this proof; if it ever
    fails here too, this row is no longer trustworthy either."""
    row = _row()
    labels = [m.group(1) for m in _TOP_LEVEL_MARKER_RE.finditer(row["text"])]
    assert labels == sorted(set(labels)), (
        f"expected strictly increasing, non-repeating top-level letters -- got {labels!r}"
    )
    assert {"i", "j", "k"} <= set(labels)


def test_subsection_candidate_agrees_with_core_resolver_outermost_alabama():
    """Unit-level agreement pin (no DB, mirrors the SC/WA sibling files):
    the candidate's stamped `(scope_value, scope_unit_kind)` must equal
    core's OUTERMOST step at the trigger offset -- computed dynamically,
    never copied from a table."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions
    from app.definition_links.us_profile import resolve_unit_path

    row = _row()
    text = row["text"]
    candidates = extract_us_scoped_inline_definitions(text)
    hits = [c for c in candidates if _TERM in c.terms]
    assert hits, "the real Alabama 'suitable work' definition was never captured"
    candidate = hits[0]
    assert candidate.scope == "subsection"

    def_start = text.index(f"the term “{_TERM}” means")
    trigger_start = text.rindex("For the purposes of this subsection", 0, def_start)
    path = resolve_unit_path(_Article(body=text), char_offset=trigger_start)
    assert path, "ground truth itself resolved empty -- fixture row unsuitable"
    assert candidate.scope_unit_kind == path[0].kind
    assert candidate.scope_value == path[0].value == "i"


def test_out_of_subsection_reuses_do_not_link_live_alabama(db_session, matter_with_users):
    """BEHAVIOR half, the actual coverage gap: this row's own natural
    reuses of "suitable work" in subsections (j) and (k) -- genuinely
    DIFFERENT top-level subsections than (i), where the term is defined --
    must NOT get a `USES_DEFINITION` edge, once subsection (i)'s OWN
    same-subsection reuses (which would correctly link and mask this
    proof) are isolated out."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]

    assert _ITEMS_1_2 in text, "fixture text changed shape -- items (1)/(2) no longer verbatim"
    assert _DEFINITION_TAIL_AND_ITEMS_4_5 in text, (
        "fixture text changed shape -- the definition's qualifier tail + items (4)/(5) are no "
        "longer verbatim"
    )
    truncated_text = text.replace(_ITEMS_1_2, "").replace(_DEFINITION_TAIL_AND_ITEMS_4_5, ".")

    def_start = truncated_text.index(f"the term “{_TERM}” means")
    def_label = _top_level_label(truncated_text, def_start)
    assert def_label == "i"
    # +1: `.index` on the quoted form lands on the opening curly quote
    # character, not the term text itself, which is what `re.finditer`
    # below actually matches.
    quoted_offset = truncated_text.index(f"“{_TERM}”") + 1

    reuse_offsets = [
        match.start()
        for match in re.finditer(re.escape(_TERM), truncated_text)
        if match.start() != quoted_offset
    ]
    out_of_subsection = [off for off in reuse_offsets if _top_level_label(truncated_text, off) != def_label]
    assert len(reuse_offsets) == len(out_of_subsection) == 2, (
        "truncation must leave exactly the definition's own entry plus 2 genuine "
        f"out-of-subsection reuses -- got {len(reuse_offsets)} reuse(s), "
        f"{len(out_of_subsection)} out-of-subsection -- ground truth missing"
    )

    truncated_row = dict(row)
    truncated_row["act_id"] = f"{_ACT_ID}_SUBSECTION_ISOLATION_TRUNCATED"
    truncated_row["text"] = truncated_text
    clean_row = {k: v for k, v in truncated_row.items() if not k.startswith("_")}

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Code of Alabama (D-S15 outermost, negative-direction proof)",
        rows=[clean_row],
        jurisdiction="US-AL",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert defs, "the real Alabama 'suitable work' definition was never captured from the truncated body"
    definition_id = defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert not uses_edges, (
        f"a mention of 'suitable work' in a subsection OTHER than the one defining it (i) got "
        f"a USES_DEFINITION edge anyway: {uses_edges!r} -- this is the exact negative-direction "
        "proof Planner pass 8 left unpinned on the SC/WA outermost rows"
    )
