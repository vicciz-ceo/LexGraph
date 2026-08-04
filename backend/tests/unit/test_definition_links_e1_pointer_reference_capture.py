"""RED tests -- sprint 2026-08-04-defs-us-multiterm, DIRECTOR RULING E1
(two-capture pointer definitions).

E1: a pointer-only cross-reference entry (a term with NO substantive
defining text of its own, only a redirect -- `"X" has the meaning
assigned by Section N`) IS a definition. Capturing it correctly is now
TWO captures, not one:

  1. the definition row, with the redirect sentence as `definition_text`
     -- already pinned elsewhere (`test_multiterm_f6_blocked_on_core_seam
     .py::test_or_cross_reference_style_definitions_resolve`,
     `test_multiterm_f5_shared_clause.py::
     test_tx_parent_clause_redirect_list_2009_003`/`_2002_001`); and
  2. a captured reference/link to the target law/section -- PINNED HERE.

Scope discipline (director/program-manager order, sprint log "ESCALATIONS
RESOLVED"): WHERE the reference lives (a family rule returns a pointer
target -> the pipeline emits a reference/assertion for it) is core's seam
v2 -- it spans 32 jurisdictions and 4+ panels, not this family sprint's to
build. This file builds NO plumbing: every test here calls the two REAL,
already-existing, already profile-dispatched primitives the eventual
wiring will need (`app.definition_links.us_profile.find_citations` /
`.detect_cross_law_derivations`) directly, the same altitude the sprint
manager's own E1 groundwork probes used, and asserts the CORRECT final
citation text -- never a new field, model, or pipeline branch.

Three distinct, separately-verified defects (manager's groundwork,
independently reproduced live by this Planner -- see the sprint log's
Planner entry for the exact command output):

  (i)   State-code citations are invisible. `_CITATION_PATTERNS`
        (us_profile.py:409-419) knows only `N U.S.C. Section N`, spelled-
        out `Section N`, and bare `Section N` (symbol) -- no state-code
        grammar (ORS/RCW/SDCL/...) at all. `ORS 153.005` yields nothing.
  (ii)  Decimal section numbers are TRUNCATED, not merely missed.
        `_SECTION_WORD_RE = \\bSection\\s+\\d+\\b` (us_profile.py:412)
        stops at the decimal point: `Section 552.003` becomes
        `Section 552` -- a citation to a DIFFERENT, real, EXISTING
        section. Pinned below as an explicit wrong-target assertion
        (`citations == [...]`, not `in`), so the failure message shows
        the wrong value pytest caught, not just an absence.
  (iii) The three REAL pointer idioms in these rows (`has the meaning
        given that term in`, `has the meaning assigned by`, `have the
        meanings assigned by`) are not in `_TRIGGER_PHRASES`
        (us_profile.py:443 -- only `has the meaning specified in` / `as
        defined in`), so `detect_cross_law_derivations` returns 0 edges
        for all three real rows. The manager's own two control probes
        (built from the registered phrases) ALSO returned 0 and were
        flagged as possibly mis-constructed -- reproduced and RESOLVED
        below (`test_detect_cross_law_derivations_recognizes_a_
        registered_trigger_phrase_control`, a GREEN control, not part of
        the RED set): the SAME call shape, given an ALREADY-REGISTERED
        trigger phrase, returns a real edge. The invocation is correct;
        the gap is specifically `_TRIGGER_PHRASES`'s content.

Live-path / no-fabricated-text discipline: every sentence below is sliced
out of the ALREADY-VENDORED `multiterm_f5_rows.json`/`multiterm_f6_rows
.json` fixtures (same rows `test_multiterm_f5_shared_clause.py`/
`test_multiterm_f6_blocked_on_core_seam.py`/the two unit-level files
already use -- no new fixture file, no test reads the corpus) via
anchor-based regex, never hand-retyped -- the exact discipline this
sprint adopted after its own peer-reviewed defect (a hand-typed OK
excerpt silently dropping a real `TM` token).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.definition_links.us_profile import detect_cross_law_derivations, find_citations

_F5_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)
_F6_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f6_rows.json"
)


def _load(fixture_path: Path) -> dict[str, dict]:
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _sentence(text: str, pattern: str) -> str:
    """Anchor-based slice of ONE real sentence out of a vendored row's raw
    `text` -- never a hand-retyped excerpt."""
    match = re.search(pattern, text, re.DOTALL)
    assert match is not None, f"anchor pattern {pattern!r} did not match the real row text"
    return match.group(0)


# --- Control: establish the correct invocation BEFORE pinning defect (iii) -


def test_detect_cross_law_derivations_recognizes_a_registered_trigger_phrase_control():
    """GREEN control, not part of the RED set. Resolves the sprint log's
    open item: the manager's own two control probes (built from the
    real, already-registered `_TRIGGER_PHRASES` values) returned 0 edges
    and were flagged as possibly mis-constructed. Reproduced here with the
    exact same `detect_cross_law_derivations(text, source_term=...)` call
    shape used by every RED test below: given an ALREADY-REGISTERED
    trigger phrase ('has the meaning specified in') immediately followed
    by a recognized citation, a real, non-empty edge comes back. This
    proves the invocation itself is correct -- the trigger-phrase gap
    pinned below is real, not an artifact of how the function is called.
    """
    edges = detect_cross_law_derivations(
        '"Foo" has the meaning specified in Section 552.003.', source_term="Foo"
    )
    assert len(edges) == 1, f"expected exactly one edge from a registered trigger phrase, got {edges!r}"
    assert edges[0].trigger_phrase == "has the meaning specified in"
    # NOT this test's concern: `matched_text` is truncated to "Section 552"
    # here too -- that is defect (ii), pinned on its own real rows below.


# --- OR STATE_OR_T41_C496_S496.716, entry (a) "Enforcement officer" -------
# '“Enforcement officer” has the meaning given that term in ORS 153.005
# (Definitions) .' -- capture 1 (the definition row) is already pinned by
# `test_multiterm_f6_blocked_on_core_seam.py::
# test_or_cross_reference_style_definitions_resolve`. Capture 2 (this
# file): the ORS citation itself must be a captured reference.


def test_or_enforcement_officer_state_code_citation_is_invisible_today():
    """Defect (i). `ORS 153.005` is a real, resolvable Oregon Revised
    Statutes citation; `find_citations` has no state-code grammar at all
    and returns nothing for it."""
    row = _load(_F6_FIXTURE)["STATE_OR_T41_C496_S496.716"]
    sentence = _sentence(row["text"], r"“Enforcement officer”.*?\(Definitions\)\s*\.")
    citations = find_citations(sentence)
    assert citations == ["ORS 153.005"], (
        f"E1 capture 2 (director ruling): the pointer's target citation "
        f"'ORS 153.005' must be captured. Got {citations!r} -- "
        f"`_CITATION_PATTERNS` (us_profile.py:409-419) has no state-code "
        f"citation form (ORS/RCW/SDCL/...) at all, so a state-code pointer "
        f"target is silently invisible, not merely truncated."
    )


def test_or_enforcement_officer_reference_edge_needs_both_i_and_iii_fixed():
    """Defect (iii), combined with (i): the real idiom 'has the meaning
    given that term in' is not a registered trigger phrase, AND even if it
    were, the ORS citation right after it would still not be recognized.
    Both gaps must close before this pointer's reference is capturable."""
    row = _load(_F6_FIXTURE)["STATE_OR_T41_C496_S496.716"]
    sentence = _sentence(row["text"], r"“Enforcement officer”.*?\(Definitions\)\s*\.")
    edges = detect_cross_law_derivations(sentence, source_term="Enforcement officer")
    assert len(edges) == 1 and edges[0].matched_text == "ORS 153.005", (
        f"E1 capture 2: expected one derivation edge pointing at 'ORS "
        f"153.005'. Got {edges!r} -- 'has the meaning given that term in' "
        f"is not in `_TRIGGER_PHRASES` (us_profile.py:443: only 'has the "
        f"meaning specified in' / 'as defined in' are registered)."
    )


# --- TX STATE_TX_Cgv_C2009_S2009.003, entry (2) "Governmental body" ------
# '"Governmental body" has the meaning assigned by Section 552.003.' --
# capture 1 already works TODAY (verified live: `extract_definitions_
# from_section` already yields `definition_text="has the meaning assigned
# by Section 552.003."` for this single-quote entry -- it is NOT a
# multi-term shared clause, so family 5's parent-clause defect does not
# apply to it). Capture 2 (this file) is the gap.


def test_tx_governmental_body_section_citation_is_truncated_to_a_wrong_target():
    """Defect (ii), pinned as an explicit WRONG-target assertion (equality,
    not membership): today's `find_citations` does not just miss `Section
    552.003` -- it returns `['Section 552']`, a citation to a DIFFERENT,
    real, EXISTING TX Government Code section. A reviewer following it
    lands on the wrong statute silently -- worse than a miss."""
    row = _load(_F5_FIXTURE)["STATE_TX_Cgv_C2009_S2009.003"]
    sentence = _sentence(row["text"], r'"Governmental body".*?Section 552\.003\.')
    citations = find_citations(sentence)
    assert citations == ["Section 552.003"], (
        f"E1 capture 2 (director ruling): the pointer's target citation "
        f"must be captured WHOLE. Got {citations!r} -- `_SECTION_WORD_RE` "
        f"(\\bSection\\s+\\d+\\b, us_profile.py:412) stops at the decimal "
        f"point, silently truncating to 'Section 552': a WRONG-TARGET "
        f"reference to a different real section, not merely a missing one."
    )


def test_tx_governmental_body_reference_edge_needs_both_ii_and_iii_fixed():
    """Defect (iii): the real idiom 'has the meaning assigned by' is not a
    registered trigger phrase; even a hypothetical fix would still need
    (ii)'s decimal-truncation fix to produce the correct `matched_text`."""
    row = _load(_F5_FIXTURE)["STATE_TX_Cgv_C2009_S2009.003"]
    sentence = _sentence(row["text"], r'"Governmental body".*?Section 552\.003\.')
    edges = detect_cross_law_derivations(sentence, source_term="Governmental body")
    assert len(edges) == 1 and edges[0].matched_text == "Section 552.003", (
        f"E1 capture 2: expected one derivation edge pointing at 'Section "
        f"552.003' (untruncated). Got {edges!r} -- 'has the meaning "
        f"assigned by' is not in `_TRIGGER_PHRASES`."
    )


# --- TX STATE_TX_Cgv_C2002_S2002.001, entry (4) parent-redirect clause ---
# 'The following terms have the meanings assigned by Section 2001.003:'
# shared by SIX terms (contested case/license/licensing/party/person/
# rule.) -- BOTH an F5 fan-out (item 3, `test_multiterm_f5_shared_clause
# .py::test_tx_parent_clause_redirect_list_2002_001`, still RED on its own
# capture-1 fix) AND, per E1, a pointer needing capture 2. Pinned here at
# the parent clause's OWN text, independent of whether item 3's fan-out
# fix has landed yet -- `find_citations`/`detect_cross_law_derivations`
# take a bare string, not a `DefinitionCandidate`, so this pin does not
# presuppose item 3's outcome. Per M-R4 (per-term resolution is
# behavioural), the eventual seam wiring calling this once per one of the
# six shared terms is a pipeline-shape question for core, not pinned here
# -- one representative call (`source_term="contested case"`) is the
# correct altitude for a primitive-level test.


def test_tx_parent_clause_2001_003_citation_is_truncated_to_a_wrong_target():
    """Defect (ii), same wrong-target shape as the single-term TX case
    above, on the SIX-term shared parent clause. The identical sentence
    also occurs byte-for-byte in `STATE_TX_Cgv_C2009_S2009.003`'s entry
    (4) -- one fix covers both real rows."""
    row = _load(_F5_FIXTURE)["STATE_TX_Cgv_C2002_S2002.001"]
    sentence = _sentence(row["text"], r"The following terms have the meanings assigned by Section 2001\.003:")
    citations = find_citations(sentence)
    assert citations == ["Section 2001.003"], (
        f"E1 capture 2 (director ruling), six-term parent-clause pointer: "
        f"the target citation must be captured WHOLE. Got {citations!r} -- "
        f"truncated to 'Section 2001', a WRONG-TARGET reference to a "
        f"different real section, not merely a missing one."
    )


def test_tx_parent_clause_2001_003_reference_edge_needs_both_ii_and_iii_fixed():
    """Defect (iii): the plural-verb idiom 'have the meanings assigned by'
    (the multi-term subject's grammatically-correct plural verb -- the
    SAME plural-verb shape this sprint's own F5 work already root-caused
    for VT/SD, see `test_definition_links_multiterm_shared_clause.py`) is
    not a registered trigger phrase."""
    row = _load(_F5_FIXTURE)["STATE_TX_Cgv_C2002_S2002.001"]
    sentence = _sentence(row["text"], r"The following terms have the meanings assigned by Section 2001\.003:")
    edges = detect_cross_law_derivations(sentence, source_term="contested case")
    assert len(edges) == 1 and edges[0].matched_text == "Section 2001.003", (
        f"E1 capture 2: expected one derivation edge pointing at 'Section "
        f"2001.003' (untruncated), shared by all six of this clause's "
        f"terms once the seam fans it out per-term (M-R4). Got {edges!r} "
        f"-- 'have the meanings assigned by' is not in `_TRIGGER_PHRASES`."
    )
