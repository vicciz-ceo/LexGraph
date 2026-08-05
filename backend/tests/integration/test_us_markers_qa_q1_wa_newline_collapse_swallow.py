"""QA1 (phase-2 QA cycle 1) -- Q1: WA's 3 remaining >5,000-char definitions
(sprint 2026-08-04-defs-us-markers, gate U1, ruling U-R1: "captured" means
captured CLEANLY).

**Classification: all 3 are boundary SWALLOWS, not genuinely long statutory
definitions.** Each row's real defining sentence for its swallowed term is
short (105-303 chars, verified below); what gets PERSISTED is 6,515-10,838
chars because it silently absorbs every sibling entry in the same
Definitions section as if it were part of the first term's own definition.

**Root cause, diagnosed (not guessed) -- lives in TWO places, NEITHER of
which is this sprint's own rule-module territory:**

1. `us_profile.py`'s baseline `_split_into_numbered_blocks` (shared code,
   not ours) is LINE-anchored: `_entry_start_remainder` only recognizes a
   new entry at the START of a `\\n`-delimited line. All 3 real rows below
   pack their ENTIRE run of `(1) "Term" means ... (2) "Term2" means ...`
   entries onto ONE line with zero internal newlines (confirmed:
   `text.split("\\n")` yields exactly one non-blank line spanning the whole
   operative body for each row). Baseline therefore recognizes only the
   FIRST `(1)` marker as a block boundary and returns exactly ONE
   degenerate block spanning the entire remaining body -- the leading-quote
   parser then treats the true LAST term's own text as if it belonged to
   the FIRST term's definition.
2. `pipeline.py`'s Stage-2/persistence loop (`ingest_us_statutes.py` call
   path, lines ~234-310 of `pipeline.py`) is idempotent-by-key: `key =
   (owning_art.id, tuple(sorted(candidate.terms)))`; the FIRST candidate
   seen for a given key is persisted, every later candidate sharing the
   same key is silently DISCARDED (`if definition_row is None:` guards
   creation). `USProfile.extract_definitions_from_section` builds
   `all_blocks = baseline_blocks + extra_blocks` -- baseline's blocks come
   FIRST, our own `EntrySplitterRule`'s blocks come second. **This
   sprint's own family-3 rule (`us_markers_inline_quote.py`, via
   `us_markers_boundary.extract_quote_anchored_entries`) ALREADY produces a
   CLEAN, boundary-correct candidate for every one of these 3 swallowed
   terms** (proven live, second test below) -- but because it is
   enumerated SECOND, the collision-by-key logic in `pipeline.py` silently
   keeps baseline's swallow and drops our clean candidate. Confirmed with a
   kill control: blinding `registry.entry_splitter_rules_for` still
   reproduces the exact same swallowed length for all 3 rows (baseline
   alone already produces it), proving the swallow itself is NOT a defect
   in the rule module we own.

Neither `us_profile.py` nor `pipeline.py` is this panel's to touch (per
this sprint's brief and ruling U-R2). This is the same "un-fixable behind
the registry seam" shape as the already-accepted FED unbounded-last-entry
RED test (`test_us_markers_unbounded_last_entry.py`, held red by agreement
pending `2026-08-05-defs-core-follow-on-2` gate G3) -- pinned here, per
QA's mandate to pin every swallow it finds regardless of fix ownership, and
reported to the manager as a NEW defect class (candidate collision
ordering), distinct from G3's own single-splitter unbounded-tail shape.

All 3 rows vendored verbatim, byte-verified against
`us_wa_statutes.parquet` this pass (`section_title`/`text`, full row).
"""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.rules import registry
from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_wa_newline_collapse_rows.json"
)

# (act_id, swallowed term, real clean definition_text, real clean length)
_CASES = [
    (
        "STATE_WA_T82_C04_S065",
        "800 service",
        'a telecommunications service that allows a caller to dial a toll-free number '
        'without incurring a charge for the call. The service is typically marketed '
        'under the name "800," "855," "866," "877," and "888" toll-free calling, and '
        "any subsequent numbers designated by the federal communications commission.",
    ),
    (
        "STATE_WA_T43_C88_S020",
        "Administrative expenses",
        "expenditures for: (a) Salaries, wages, and related costs of personnel and (b) "
        "operations and maintenance including but not limited to costs of supplies, "
        "materials, services, and equipment.",
    ),
    (
        "STATE_WA_T82_C04_S192",
        "Digital audio works",
        "works that result from the fixation of a series of musical, spoken, or other "
        "sounds, including ringtones.",
    ),
]

# The next sibling term each swallow illegally absorbs (proves it ran past
# its own true boundary, not merely "the text is long").
_NEXT_SIBLING_TERM = {
    "800 service": "900 service",
    "Administrative expenses": "Agency",
    "Digital audio works": "Digital audiovisual works",
}


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def test_fixture_rows_are_directly_definitions_headed_not_body_derived():
    """Sanity: all 3 titles already say "Definitions" -- these are NOT
    placeholder/body-derived headings, so `heading_was_derived=False` for
    all 3 in the real pipeline (matches this file's root-cause diagnosis,
    which is specific to the direct-heading baseline splitter path)."""
    rows = _load_rows()
    for act_id, _term, _clean in _CASES:
        assert is_definitions_heading(rows[act_id]["section_title"]) is True, act_id


def test_our_own_family_3_engine_already_produces_the_clean_candidate():
    """Proves the swallow is NOT a defect in the rule module this sprint
    owns: calling `extract_quote_anchored_entries` directly (bypassing
    baseline entirely) on each real row's raw body yields the term with its
    TRUE short definition, none of them anywhere near 5,000 chars."""
    rows = _load_rows()
    for act_id, term, clean_text in _CASES:
        entries = dict(extract_quote_anchored_entries(rows[act_id]["text"]))
        assert term in entries, f"{act_id}: our engine should still find {term!r} directly"
        assert entries[term] == clean_text, (
            f"{act_id}: our engine's own candidate for {term!r} changed -- got "
            f"{entries[term]!r}"
        )
        assert len(entries[term]) < 500, (
            f"{act_id}: our engine's candidate for {term!r} is "
            f"{len(entries[term])} chars -- should be the short, clean, real definition"
        )


def test_kill_control_baseline_alone_already_produces_the_swallow():
    """Kill control (P-R10 probe discipline): with the family-3 registry
    blinded (`entry_splitter_rules_for` -> `[]`), baseline's own
    `_split_into_numbered_blocks` STILL produces the identical swallowed
    length for all 3 rows -- proving the defect is 100% baseline's, not
    introduced or worsened by our own rule module's presence."""
    rows = _load_rows()
    from app.definition_links.us_profile import USProfile

    orig = registry.entry_splitter_rules_for
    registry.entry_splitter_rules_for = lambda code: []
    try:
        profile = USProfile(code="US-WA")
        for act_id, term, _clean in _CASES:
            text = rows[act_id]["text"]
            scope = profile.determine_scope(text)
            cands = profile.extract_definitions_from_section(text, scope=scope, heading_was_derived=False)
            by_term = {t: c for c in cands for t in c.terms}
            assert term in by_term, f"{act_id}: baseline alone should still (badly) capture {term!r}"
            assert len(by_term[term].definition_text) >= 5000, (
                f"{act_id}: expected baseline-alone to reproduce the swallow "
                f"(>=5000 chars); got {len(by_term[term].definition_text)}"
            )
    finally:
        registry.entry_splitter_rules_for = orig


def test_real_pipeline_does_not_let_the_baseline_swallow_beat_our_clean_candidate(
    db_session, matter_with_users
):
    """The load-bearing RED: through the REAL production call path
    (`ingest_us_statute_rows` -> `run_definition_linking`), each swallowed
    term's PERSISTED `Definition.definition_text` must be the true, short,
    clean definition -- not the 5,000+ char swallow that wins today because
    `pipeline.py`'s idempotent-by-key persistence loop keeps whichever
    candidate is enumerated FIRST (`all_blocks = baseline_blocks +
    extra_blocks` puts the defective baseline block ahead of our own
    correct one)."""
    rows = _load_rows()
    for act_id, _term, _clean in _CASES:
        ingest_us_statute_rows(
            db_session,
            repository_id=matter_with_users["repository_id"],
            matter_id=matter_with_users["matter_id"],
            title="WA newline-collapse swallow (QA1 Q1)",
            rows=[rows[act_id]],
            jurisdiction="US-WA",
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

    for act_id, term, clean_text in _CASES:
        matches = by_term.get(term, [])
        assert matches, f"{act_id}: {term!r} was not captured at all -- got terms {sorted(by_term)!r}"
        assert len(matches) == 1, (
            f"{act_id}: expected exactly one persisted Definition for {term!r}, got "
            f"{len(matches)} -- collision-by-key behavior changed, re-derive this test"
        )
        persisted = matches[0]
        assert persisted.definition_text == clean_text, (
            f"{act_id}: {term!r} swallowed the section -- persisted "
            f"{len(persisted.definition_text)} chars, real definition is "
            f"{len(clean_text)} chars. persisted[:200]={persisted.definition_text[:200]!r}"
        )
        sibling = _NEXT_SIBLING_TERM[term]
        assert sibling not in persisted.definition_text, (
            f"{act_id}: {term!r}'s persisted definition_text illegally contains its "
            f"sibling term {sibling!r} -- it swallowed the next entry"
        )
