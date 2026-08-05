"""G8 (sprint 2026-08-05-defs-core-follow-on-2) -- a baseline BAD candidate
must not silently beat a cleaner SAME-TERM candidate at persistence.

**The defect** (`backend/app/definition_links/pipeline.py`, Stage 2,
~lines 262-310): `all_candidates` is built, then persisted in LIST ORDER.
The write is guarded by `if definition_row is None:` on key
`(article_id, tuple(sorted(candidate.terms)))` -- the FIRST candidate seen
for a key is persisted; every later candidate sharing that key is silently
discarded (`definitions_by_key[key] = definition_row` never gets a second
write). There is no UPDATE path for `definition_text` at all, and
`definitions_by_key` is pre-seeded from EXISTING DB rows (lines ~277-284),
so a bad `definition_text` persisted once wins over every future re-run
too (sticky across runs, not just within one).

**Why this file does NOT reuse the WA newline-collapse fixture**
(`test_us_markers_qa_q1_wa_newline_collapse_swallow.py`, branch
`claude/defs-us-markers`, uncommitted in that branch's own QA worktree --
read for evidence, never cherry-picked here, per program convention on
authorship). That fixture's swallow is caused by
`_split_into_numbered_blocks` finding the section's entire body as ONE
line (no internal newlines) -- i.e. exactly the shape gate G3
(`us_profile.py:346`, "unbounded last entry") targets. A parallel Planner
is fixing G3 in this same sprint; if G3's fix generalizes to mid-line
marker detection, the WA rows' swallow could stop reproducing, making a
G8 RED built on them UNOBSERVABLE post-merge without proving the
collision-preference behavior is safe IN GENERAL (explicit program
ruling: "G3 happened to make it unobservable" does NOT close G8).

This file's fixture instead uses a REAL Arkansas row where the collision
is PROVABLY independent of G3: the losing candidate's own block is never
the row's last block (`test_occurrence_is_not_the_last_block...` below
makes this a machine-checked fact, not an assertion in prose), and the
corpus-wide scan below (see Planner's report) confirms this shape --
same-key collisions inside a MULTI-block, properly newline-separated
section -- occurs in 4,360 real rows across 35 jurisdictions, and by
construction NEVER involves the winning (first) candidate's own block
being the row's last block (0/4,360) -- i.e. this entire population is
outside G3's declared scope regardless of what shape G3's fix takes.

**The real row and its real defect.** `STATE_AR_T27_C14_S23_S27-14-2301`
(Ark. Code Ann. Section 27-14-2301, "Definitions", `us_ar_statutes.parquet`)
has its own body TEXT DUPLICATED verbatim by the source dataset (a real,
pre-existing corpus artifact -- see
`backend/tests/fixtures/us_statutes/README.md`'s D-CF fixture #4 for an
independently-found instance of the same AR duplication pattern) -- once
as a compact run-on paragraph, once reformatted with real paragraph
breaks around each numbered/lettered marker. For the term "Occurrence",
this produces THREE baseline candidates (byte-verified below):

  0. 155 chars (FIRST -- wins today): 'means the event that caused the
     motor vehicle to become damaged. (B) "Occurrence" includes without
     limitation collision, theft, vandalism, storm, or flood;'
  1.  64 chars (clean): 'means the event that caused the motor vehicle to
     become damaged.'
  2.  73 chars: 'includes without limitation collision, theft, vandalism,
     storm, or flood;'

Candidate 0 is objectively worse than candidate 1 by a SPECIFICITY/
CONTAINMENT criterion (not merely "shorter is better", which the corpus
scan shows is unreliable -- see Planner's report): candidate 1's text is
a literal, byte-exact SUBSTRING of candidate 0's text -- candidate 0 is
candidate 1 PLUS a structurally separate sub-item's own marker+quote
(`(B) "Occurrence"`) leaked into its own `definition_text`. This is the
"tighter span wins" criterion this gate's design settles on; see the
Planner's report for the corpus-measured comparison against a pure
ordering flip and a pure length-sanity threshold, both rejected.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.rules import registry
from app.definition_links.us_profile import (
    _leading_quote_candidate,
    _split_into_numbered_blocks,
    determine_scope,
    extract_definitions_from_section,
    is_definitions_heading,
)
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_g8_ar_occurrence_embedded_continuation_row.json"
)

_ACT_ID = "STATE_AR_T27_C14_S23_S27-14-2301"
_TERM = "Occurrence"
_CLEAN_TEXT = "means the event that caused the motor vehicle to become damaged."
_BAD_TEXT = (
    'means the event that caused the motor vehicle to become damaged. (B) "Occurrence" '
    "includes without limitation collision, theft, vandalism, storm, or flood;"
)
# The next block AFTER all of "Occurrence"'s own blocks in the real row --
# proves "Occurrence" is not the section's last defined term either
# (independent of the block-index check below).
_NEXT_TERM_AFTER_OCCURRENCE = "Office of Motor Vehicle"


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["act_id"] == _ACT_ID
    return rows[0]


# --- G8 proof-of-mechanism EntrySplitterRule (test-local only -- NOT
# production code; registered here the same way `test_definition_links_
# rule_dispatch.py` registers its own probe rules, per this codebase's own
# documented convention that "the registry has no reset/teardown between
# tests -- registrations accumulate for the whole pytest session"). Scoped
# to jurisdiction "US-AR" only (verified unused by any other test in this
# suite) so it cannot contaminate any other jurisdiction's tests. -------

_TERM_MEANS_EMBEDDED_CONTINUATION_RE = re.compile(
    r'[“"](?P<term>[^”"]+)[”"]\s*means\s+(?P<def>.{1,220}?)\s*\([A-Za-z0-9]+\)\s*[“"](?P=term)[”"]',
    re.DOTALL,
)


def _split_embedded_same_term_continuation(text: str) -> list[str]:
    """Recognizes the real English drafting convention where a term's OWN
    definition continues via a lettered sub-clause that RE-QUOTES the same
    term (e.g. "(A) "Foo" means X. (B) "Foo" includes Y.") -- a shape
    baseline's `_leading_quote_candidate` cannot see, since it captures
    everything from the first closing quote to the end of ITS OWN block
    verbatim, including an embedded `(marker) "sameterm"` continuation.
    Contributes one clean, correctly-bounded extra block per match (the
    gap is bounded to 220 chars, mirroring `_MEANS_IDIOM_GAP_RE`'s own
    bounded-gap discipline elsewhere in `us_profile.py`, so this can never
    leap across unrelated later occurrences of the same term name -- see
    the Planner's report for the unbounded version's failure mode)."""
    return [
        f'"{m.group("term")}" means {m.group("def").strip()}'
        for m in _TERM_MEANS_EMBEDDED_CONTINUATION_RE.finditer(text)
    ]


registry.register_entry_splitter_rule(
    registry.EntrySplitterRule(
        jurisdiction_codes=("US-AR",),
        split=_split_embedded_same_term_continuation,
    )
)


# --- Diagnostics (mirror the evidence-reading test's own structure:
# sanity -> baseline-alone proof -> G3-independence proof -> rule-live
# proof -- THEN the load-bearing RED). ---------------------------------


def test_fixture_row_is_directly_definitions_headed_not_body_derived():
    """Sanity: the real row's own heading already says "Definitions" --
    not a placeholder/body-derived heading, so `heading_was_derived=False`
    in the real pipeline, matching this file's own direct calls below."""
    row = _load_row()
    assert is_definitions_heading(row["section_title"]) is True


def test_baseline_alone_already_produces_two_different_quality_candidates_for_the_same_term():
    """The core finding, needing ZERO registered rules: baseline's OWN
    `extract_definitions_from_section` (bare module function, no
    `USProfile`, no registry) already produces MULTIPLE candidates for
    "Occurrence" from its own block splitting -- because the real row's
    text is duplicated by the source dataset (see module docstring). This
    is a stronger control than a "kill control" (blinding the registry):
    it proves the collision exists with the registry entirely out of the
    picture, so no registered rule can be blamed for causing it."""
    row = _load_row()
    text = row["text"]
    scope = determine_scope(text)
    candidates = extract_definitions_from_section(text, scope=scope, heading_was_derived=False)
    occurrence_candidates = [c.definition_text for c in candidates if c.terms == (_TERM,)]

    assert len(occurrence_candidates) >= 2, (
        f"expected baseline alone to produce >=2 'Occurrence' candidates from this row's "
        f"duplicated text; got {len(occurrence_candidates)}: {occurrence_candidates!r}"
    )
    first, clean = occurrence_candidates[0], occurrence_candidates[1]
    assert first == _BAD_TEXT, f"fixture/baseline drifted -- got first={first!r}"
    assert clean == _CLEAN_TEXT, f"fixture/baseline drifted -- got second={clean!r}"

    # The specificity/containment criterion this gate's design settles on:
    # the clean candidate's text is a literal substring of the bad one's.
    assert clean in first, "expected the clean candidate's text to be contained in the bad one's"
    assert len(clean) < len(first)


def test_occurrence_is_not_the_last_entry_g3_cannot_be_the_mechanism_here():
    """G3-independence, machine-checked (not just argued in prose): G3
    (`_split_into_numbered_blocks`' unbounded LAST entry, `us_profile.py:
    346`) only touches the final block `_split_into_numbered_blocks`
    returns. Every block this row's baseline splitter finds for
    "Occurrence" (the winning one included) has at least one MORE block
    after it -- concretely, the very next defined term is "Office of
    Motor Vehicle" -- so no fix scoped to the LAST entry's boundary can
    reach the candidate this test cares about, regardless of what shape
    that fix takes."""
    row = _load_row()
    text = row["text"]
    blocks = _split_into_numbered_blocks(text)
    assert len(blocks) > 1, "fixture must be genuinely multi-block (not a G3-shaped single block)"

    occurrence_block_indices = [
        i
        for i, block in enumerate(blocks)
        if (candidate := _leading_quote_candidate(block, scope="law-wide")) is not None
        and candidate.terms == (_TERM,)
    ]
    assert occurrence_block_indices, "fixture drifted -- no 'Occurrence' blocks found"
    last_block_index = len(blocks) - 1
    assert max(occurrence_block_indices) < last_block_index, (
        f"expected every 'Occurrence' block (indices {occurrence_block_indices}) to precede "
        f"the row's last block (index {last_block_index}) -- if this fails, this fixture is no "
        f"longer safely G3-independent and must be re-picked"
    )

    winning_block = blocks[occurrence_block_indices[0]]
    assert winning_block  # sanity: not empty

    # The block right after the LAST "Occurrence" block (not just the
    # winning one) must be a DIFFERENT term -- confirms the whole
    # "Occurrence" run is closed out by a genuine subsequent entry, not
    # merely absorbed into an unbounded tail.
    next_block = blocks[max(occurrence_block_indices) + 1]
    next_candidate = _leading_quote_candidate(next_block, scope="law-wide")
    assert next_candidate is not None and next_candidate.terms == (_NEXT_TERM_AFTER_OCCURRENCE,), (
        f"expected the block right after the last 'Occurrence' block to be "
        f"{_NEXT_TERM_AFTER_OCCURRENCE!r}; got {next_candidate.terms if next_candidate else None!r} "
        "-- confirms the 'Occurrence' run is a genuine, closed, non-last sequence of entries"
    )


def test_registered_rule_reaches_real_persistence_when_uncontested(db_session, matter_with_users):
    """P-R8 control (a probe whose ANSWER changes): before trusting the
    load-bearing RED below, prove the registered `EntrySplitterRule` is
    genuinely LIVE all the way to persistence -- not merely registered
    and looked up (P-R8's exact warning: "a wiring test asserting
    registration+lookup is NOT a dispatch test"). Uses a SYNTHETIC probe
    text (clearly not vendored corpus evidence -- the real defect evidence
    is the AR row above) shaped so baseline's own line-anchored splitter
    finds NOTHING at all (the probe sentence never starts a LINE with a
    marker), so the only way a "Widget" `Definition` can be persisted is
    through this test's own registered rule."""
    m = matter_with_users
    control_text = (
        "Introductory prose that never starts a line with a parenthetical marker, so "
        'baseline\'s own line-anchored splitter finds nothing here at all. "Widget" means '
        'a small mechanical device. (b) "Widget" also includes any component thereof.'
    )
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="G8 uncontested-control probe (synthetic, not corpus evidence)",
        rows=[
            {
                "act_id": "G8_SYNTHETIC_CONTROL_WIDGET_PROBE",
                "section_title": "Definitions",
                "text": control_text,
            }
        ],
        jurisdiction="US-AR",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    widget_defs = [d for d in result["created_definitions"] if d["terms"] == ["Widget"]]
    assert widget_defs, (
        "the registered EntrySplitterRule's candidate never reached persistence at all -- "
        f"created_definitions={result['created_definitions']!r} -- the rule may be inert "
        "(registered+looked-up but never actually dispatched), which would make the "
        "load-bearing RED below untrustworthy"
    )
    persisted = db_session.get(Definition, widget_defs[0]["id"])
    assert persisted.definition_text == "means a small mechanical device.", (
        f"registered rule's candidate reached persistence but with the wrong text: "
        f"{persisted.definition_text!r}"
    )


def test_real_pipeline_does_not_let_baselines_first_bad_candidate_beat_the_clean_one(
    db_session, matter_with_users
):
    """THE LOAD-BEARING RED: through the REAL production call path
    (`ingest_us_statute_rows` -> `run_definition_linking`), the PERSISTED
    `Definition.definition_text` for "Occurrence" must be the clean,
    tightly-bounded text -- not the 155-char text that illegally contains
    a structurally separate sub-item's own marker+quote. Today it is not:
    `pipeline.py`'s Stage 2 persists whichever candidate for a given
    `(article_id, sorted(terms))` key is encountered FIRST in list order
    and never revisits that row, regardless of what arrives later --
    baseline's own bad candidate (block index 3) precedes both baseline's
    own clean candidate (block index 4) AND this test's registered rule's
    independently-sourced clean candidate (sourced via the SAME
    `EntrySplitterRule` -> `_leading_quote_candidate` path the real
    markers engine uses) in that list, so it wins regardless of either."""
    row = _load_row()
    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="AR Code Title 27 (G8 real-row fixture)",
        rows=[row],
        jurisdiction="US-AR",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    matches = [d for d in definitions if d.terms == [_TERM]]

    assert matches, f"{_TERM!r} was not captured at all -- got terms {[d.terms for d in definitions]!r}"
    assert len(matches) == 1, (
        f"expected exactly one persisted Definition for {_TERM!r}, got {len(matches)} -- "
        "collision-by-key behavior changed, re-derive this test"
    )
    persisted = matches[0]
    assert persisted.definition_text == _CLEAN_TEXT, (
        f"{_TERM!r}'s persisted definition_text is the WORSE candidate -- got "
        f"{len(persisted.definition_text)} chars {persisted.definition_text!r}, expected the "
        f"clean {len(_CLEAN_TEXT)}-char text {_CLEAN_TEXT!r}. A baseline candidate that "
        "illegally contains a structurally separate sub-item's own marker+quote "
        "(literal '(B) \"Occurrence\"') silently beat both baseline's own later clean "
        "candidate and this test's registered rule's clean candidate, purely by being "
        "enumerated first."
    )
