"""Planner phase-2 (sprint 2026-08-04-defs-us-preamble, Task 3, manager
charter M-R64/M-R72..M-R74): live RED tests for the four named root causes
option (c) must fix -- "make the RIGHT occurrence win", per M-R64's ruling
that this is the only remedy that improves precision AND recall together
(the rejected options (a)/(b), a purely local per-occurrence window check,
cannot: see `-log.md`, cycle-8 D1's corpus-wide measurement).

**Why these are UNIT-level tests on the real `us_body_preamble.py`/
`us_profile.py` regex objects, not full live-path pipeline-outcome tests
(disclosed, matching this sprint's own D2 precedent, not a shortcut).**
None of these four defects currently causes a live-path MISS: every row
below is already fully, correctly captured TODAY via a spurious rescuing
occurrence elsewhere in its body (see `test_us_body_preamble_defining_
verb_narrowing_red.py`'s Section 2 regression guards for the pipeline-
outcome-level pin on each of these same rows). The defects are LATENT --
they only bite once a verb-presence/trigger-precision check is added at
the WINNING occurrence's own boundary (exactly what option (c) commissions
building). A live-path pipeline assertion against today's code cannot
distinguish "fixed" from "unfixed" for these four causes, because today's
code does not yet couple recognition to the winning occurrence's own
window at all. So each test below pins the causal MECHANISM directly
(the real regex object, applied to real, byte-exact corpus row text --
never a synthetic string) rather than the pipeline's aggregate outcome.
Each is genuinely RED today and defines exactly what GREEN means once the
Developer's fix lands.

No test in this file reads the parquet snapshot; `optionc_root_cause_
rows.json`'s one new row (`STATE_PA_T15_C57_S5749`) was fetched directly
via `pyarrow.parquet.read_table` from this Planner's own local snapshot of
`vaquill/open-us-law`
(`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/
301000fc3465374ee0f23c3c6953a8a861e95cad/us_pa_statutes.parquet`), all
values unmodified, and verified byte-identical by round-tripping through
JSON before being committed here (see this cycle's `-log.md` for the
verification transcript). The other 3 real rows this file needs
(`STATE_PA_T15_C75_S7502`, `STATE_AR_T8_C8_S1_S8-8-102`,
`STATE_OH_T45_C4510_S4510.17`, `USC_T15_C1_S26a`) reuse the ALREADY-
vendored, byte-verified `cycle8_defining_verb_positive_rows.json` fixture
-- no new fixture needed for those.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _positive_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "cycle8_defining_verb_positive_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


def _optionc_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "optionc_root_cause_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


# --- Root cause 1: `_B1_TRIGGER_RE`'s greedy unit-name tail can swallow ---
# --- a following defining verb into the trigger match itself --------------


def test_pa_association_trigger_regex_greedy_tail_swallows_the_defining_verb_red():
    """`STATE_PA_T15_C75_S7502`'s real defining clause is '...as used in
    this chapter means a corporation with or without capital stock
    incorporated under any of the following...'. `_B1_TRIGGER_RE`'s own
    unit-name character class (`[A-Za-z0-9 .\\-]{0,30}`) has no anchor
    against consuming a following defining verb -- confirmed live: the
    FIRST real trigger match in this body is literally 'in this chapter
    means a corporation wit', i.e. the verb 'means' and 12 more characters
    of the definition itself are swallowed INTO the trigger's own match
    span. Option (c)'s fix must cap this tail so a verb-presence check
    applied to text strictly after the trigger match's end can still see
    'means' here -- today it cannot. RED today; GREEN once the Developer
    anchors the trigger's unit-name class against consuming known defining
    verbs."""
    from app.definition_links.rules.us_body_preamble import _B1_TRIGGER_RE

    row = _positive_row("STATE_PA_T15_C75_S7502")
    body = row["text"]

    match = next(_B1_TRIGGER_RE.finditer(body))
    assert match.group() == "in this chapter means a corporation wit", (
        "fixture/regex drift: this test's own oracle string no longer matches "
        f"the real body's first trigger occurrence (got {match.group()!r}) -- "
        "re-verify against the real row before trusting the assertion below"
    )

    assert "means" not in match.group(), (
        f"expected the trigger match span to stop BEFORE any defining verb, but "
        f"got {match.group()!r} -- `_B1_TRIGGER_RE`'s greedy unit-name tail "
        "swallows 'means' into its own match on this real PA row (STATE_PA_"
        "T15_C75_S7502); a verb-presence check anchored strictly after the "
        "trigger's own match end can never see it until this regex is capped"
    )


# --- Root cause 2a: `_B1_QUOTE_MEANS_RE`'s verb group lacks `includes`/ ---
# --- `shall include` (D-INCLUDES gap in the recognition regex) ------------


def test_usc_united_states_quote_means_re_misses_the_includes_verb_red():
    """`USC_T15_C1_S26a`'s only genuine local definition is 'As used in
    this section, "United States" includes the several States, the
    District of Columbia...' -- a quote-means shape whose verb is
    `includes`, not `means`/`shall mean`. `_B1_QUOTE_MEANS_RE`'s own verb
    alternation is `means|shall mean` ONLY. Confirmed live against the
    real trigger occurrence's own `after` text: today's regex does not
    match at all. Under D-INCLUDES (`includes`/`shall include` captured
    program-wide with the naive quoted-term anchor, no tightened guard),
    this is a genuine gap in the recognition regex specifically -- distinct
    from (and orthogonal to) the SIBLING extraction-side gap pinned by
    `test_pa_references_to_construction_clause_needs_a_targeted_guard_
    red` below. RED today; GREEN once `_B1_QUOTE_MEANS_RE`'s verb group is
    widened to include `includes`/`shall include`."""
    from app.definition_links.rules.us_body_preamble import _B1_LOOKAHEAD, _B1_QUOTE_MEANS_RE, _B1_TRIGGER_RE

    row = _positive_row("USC_T15_C1_S26a")
    body = row["text"]

    genuine_after = None
    for m in _B1_TRIGGER_RE.finditer(body):
        if m.group() == "As used in this section":
            genuine_after = body[m.end() : m.end() + _B1_LOOKAHEAD]
            break
    assert genuine_after is not None, (
        "fixture/regex drift: could not locate the real 'As used in this "
        "section' trigger occurrence in USC_T15_C1_S26a's body -- re-verify "
        "against the real row before trusting the assertion below"
    )
    assert genuine_after.startswith(', "United States" includes'), (
        f"fixture/regex drift: expected the genuine occurrence's own `after` "
        f"text to start with the real 'includes' clause, got "
        f"{genuine_after[:60]!r} -- re-verify against the real row"
    )

    assert _B1_QUOTE_MEANS_RE.match(genuine_after) is not None, (
        f"expected `_B1_QUOTE_MEANS_RE` to match the real 'includes' clause "
        f"{genuine_after[:60]!r}, but it did not -- the D-INCLUDES verb "
        "`includes` is missing from `_B1_QUOTE_MEANS_RE`'s verb group "
        "(`means|shall mean` only); this is the D-INCLUDES gap in the "
        "recognition regex specifically"
    )


# --- Root cause 2b: D-INCLUDES's MANDATORY condition -- the PA -----------
# --- construction-clause hazard must be suppressed by a TARGETED guard ---
# --- ("preceded by References to"), never by idiom-absence ---------------


def test_pa_references_to_construction_clause_needs_a_targeted_guard_red():
    """D-INCLUDES's mandatory condition (this Planner's own charter,
    measured against the real corpus, not assumed): once `includes`/`shall
    include` join the defining-verb vocabulary anywhere in the extraction
    path, a NEW real hazard opens up that `has the meaning`-only vocabulary
    never touched -- Pennsylvania's construction-clause idiom, 'References
    to "X" shall include Y', e.g. `STATE_PA_T15_C57_S5749`: 'For the
    purposes of this subchapter: (1) References to "other enterprises"
    shall include employee benefit plans and references to "serving at the
    request of the corporation" shall include any service...'. This is NOT
    a definition of 'other enterprises' -- it is a drafting convention
    ("read this term, elsewhere in the subchapter, as covering that") --
    and must stay suppressed. This Planner MEASURED (not assumed) that a
    NAIVE verb-group widening of `_MEANS_IDIOM_GAP_RE` (the extraction-
    fallback regex in `us_profile.py` that governs the SAME 'quoted term +
    defining verb, naive anchor' idiom D-INCLUDES targets) -- adding
    `includes`/`shall include` with NO other change -- WOULD wrongly
    capture both 'other enterprises' and 'serving at the request of the
    corporation' as spurious definitions from this real row. A TARGETED
    guard (suppress only when the quoted term is immediately preceded by
    'References to') correctly blocks both PA hazard terms while still
    allowing the genuine `USC_T15_C1_S26a` 'includes' row through --
    confirmed against BOTH real rows in the same run below. Per this
    Planner's charter: 'never by idiom-absence' -- i.e. the guard must be
    this targeted structural check, not a reliance on `includes` staying
    absent from the verb vocabulary (which D-INCLUDES itself removes).

    Mutation-verified (this Planner, live in this worktree, reverted
    before commit -- see `-log.md`): with the naive widening applied and
    NO targeted guard, this test's own 'naive widening captures the hazard'
    assertion flips as expected, proving the danger is real, not
    hypothetical; with the targeted guard applied on top, the hazard
    assertion flips back while the genuine-row control still passes.

    RED today in the sense that the FIX (D-INCLUDES verb widening) does not
    exist yet in production, so this test pins the REQUIRED SHAPE of that
    fix using locally-defined, test-only regex objects that mirror exactly
    what the Developer must build (never committed to `app/`) -- disclosed
    explicitly, matching this sprint's own D2 precedent for a defect the
    live path cannot yet manifest."""
    from app.definition_links.us_profile import _QUOTE_TERM_RE

    pa_row = _optionc_row("STATE_PA_T15_C57_S5749")
    pa_text = pa_row["text"]
    us_row = _positive_row("USC_T15_C1_S26a")
    us_text = us_row["text"]

    # The exact widening D-INCLUDES commissions: add `includes`/`shall
    # include` to the SAME naive-anchor verb group `_MEANS_IDIOM_GAP_RE`
    # already uses for `means`/`shall mean`/`has the meaning`. Defined
    # LOCALLY here (test-only spec, never written to `app/`) so this test
    # can prove both halves of the mandatory condition on real rows.
    naive_widened_gap_re = re.compile(
        r'^[^"“”]{0,200}?\b(?:means|shall mean|has the meaning|includes|shall include)\b:?\s*',
        re.IGNORECASE,
    )

    def naive_capture(text: str) -> list[str]:
        terms = []
        for term_match in _QUOTE_TERM_RE.finditer(text):
            gap = text[term_match.end() : term_match.end() + 200]
            if naive_widened_gap_re.match(gap) is not None:
                terms.append(term_match.group(1))
        return terms

    # 1) Prove the hazard is REAL (mutation-style control): the naive
    #    widening, with NO guard, wrongly captures both PA construction-
    #    clause terms.
    naive_pa = naive_capture(pa_text)
    assert set(naive_pa) == {"other enterprises", "serving at the request of the corporation"}, (
        f"expected the naive D-INCLUDES widening (no guard) to wrongly capture "
        f"both PA construction-clause terms on the real row, got {naive_pa!r} -- "
        "if this fails, either the fixture no longer exercises the hazard or "
        "the naive-widening spec above no longer matches D-INCLUDES's own "
        "verb vocabulary; re-verify before trusting the guard proof below"
    )

    # 2) Prove the TARGETED guard ("preceded by References to") correctly
    #    suppresses both hazard terms while the genuine USC row still
    #    passes -- this is the exact shape the Developer's real guard must
    #    have; never by idiom-absence.
    def references_to_guard_blocks(text: str, quote_start: int) -> bool:
        prefix = text[max(0, quote_start - 20) : quote_start]
        return bool(re.search(r"References to\s*$", prefix, re.IGNORECASE))

    def guarded_capture(text: str) -> list[str]:
        terms = []
        for term_match in _QUOTE_TERM_RE.finditer(text):
            gap = text[term_match.end() : term_match.end() + 200]
            if naive_widened_gap_re.match(gap) is None:
                continue
            if references_to_guard_blocks(text, term_match.start()):
                continue
            terms.append(term_match.group(1))
        return terms

    guarded_pa = guarded_capture(pa_text)
    assert guarded_pa == [], (
        f"expected the TARGETED 'preceded by References to' guard to suppress "
        f"BOTH PA construction-clause terms, got {guarded_pa!r} still captured "
        "-- the targeted guard must block on the structural 'References to' "
        "prefix, not on the mere presence of a qualifier clause"
    )

    guarded_us = guarded_capture(us_text)
    assert "United States" in guarded_us, (
        f"expected the SAME targeted guard to still allow the genuine "
        f"USC_T15_C1_S26a 'includes' row through, got {guarded_us!r} -- a "
        "guard that also blocks genuine rows is over-broad, not just "
        "under-tested; the guard must key on the structural 'References to' "
        "prefix specifically, never on the includes verb's mere presence"
    )


# --- Root cause 3: trigger vocabulary misses singular "purpose" -----------


def test_ar_interstate_compact_trigger_regex_misses_singular_purpose_red():
    """`STATE_AR_T8_C8_S1_S8-8-102`'s real intro clause is 'For the
    purpose of this compact and of any supplemental or concurring
    legislation...: (a) "State" shall mean...' -- SINGULAR 'purpose'.
    `_B1_TRIGGER_RE` requires PLURAL 'purposes' only (`For (?:the
    )?purposes of`). Confirmed live: zero `_B1_TRIGGER_RE` matches occur
    anywhere near the real clause's own start index (measured at index
    2088 in the real body); every match in this body is a different,
    genuinely spurious 'in this compact'/'in this agreement' occurrence
    elsewhere. RED today; GREEN once the Developer widens the trigger to
    also accept singular 'purpose'."""
    from app.definition_links.rules.us_body_preamble import _B1_TRIGGER_RE

    row = _positive_row("STATE_AR_T8_C8_S1_S8-8-102")
    body = row["text"]

    real_clause_index = body.find("For the purpose of this compact")
    assert real_clause_index != -1, (
        "fixture drift: the real 'For the purpose of this compact' clause is "
        "no longer present in this row's body -- re-verify against the real "
        "row before trusting the assertion below"
    )

    matches_at_real_clause = [
        m for m in _B1_TRIGGER_RE.finditer(body) if real_clause_index <= m.start() <= real_clause_index + 5
    ]
    assert matches_at_real_clause != [], (
        f"expected `_B1_TRIGGER_RE` to match the real singular-'purpose' intro "
        f"clause at index {real_clause_index} ('For the purpose of this "
        "compact...'), but it does not match there at all today -- the "
        "trigger's `purposes` alternative is plural-only; must accept "
        "singular 'purpose' for this real AR row's own genuine intro clause "
        "to be reached directly, instead of only via a spurious rescuing "
        "occurrence elsewhere in the body"
    )


# --- Root cause 4: intervening clauses between trigger and unit name -----


def test_oh_child_trigger_regex_misses_the_intervening_divisions_clause_red():
    """`STATE_OH_T45_C4510_S4510.17`'s real definitions clause is '(H) As
    used in divisions (C) and (D) of this section: (1) "Child" means a
    person who is under the age of eighteen years...'. `_B1_TRIGGER_RE`
    requires the literal word 'this' immediately after 'in'/'of' (mediated
    only by a short unit-name run); the intervening clause 'divisions (C)
    and (D) of' breaks that adjacency entirely. Confirmed live: zero
    `_B1_TRIGGER_RE` matches occur anywhere near the real clause's own
    start index (measured at index 18671 in the real body); every match in
    this body is a different, genuinely spurious 'in this state.'/'in this
    division' occurrence elsewhere. RED today; GREEN once the Developer
    widens the trigger to tolerate a bounded intervening clause between
    'As used in' and the unit name."""
    from app.definition_links.rules.us_body_preamble import _B1_TRIGGER_RE

    row = _positive_row("STATE_OH_T45_C4510_S4510.17")
    body = row["text"]

    real_clause_index = body.find("As used in divisions (C) and (D) of this section")
    assert real_clause_index != -1, (
        "fixture drift: the real 'As used in divisions (C) and (D) of this "
        "section' clause is no longer present in this row's body -- "
        "re-verify against the real row before trusting the assertion below"
    )

    matches_at_real_clause = [
        m for m in _B1_TRIGGER_RE.finditer(body) if real_clause_index <= m.start() <= real_clause_index + 5
    ]
    assert matches_at_real_clause != [], (
        f"expected `_B1_TRIGGER_RE` to match the real intervening-clause intro "
        f"'As used in divisions (C) and (D) of this section' at index "
        f"{real_clause_index}, but it does not match there at all today -- "
        "the intervening 'divisions (C) and (D) of' breaks the 'As used in "
        "... this <unit>' adjacency the trigger currently requires; must "
        "tolerate a bounded intervening clause for this real OH row's own "
        "genuine clause to be reached directly, instead of only via a "
        "spurious rescuing occurrence elsewhere in the body"
    )
