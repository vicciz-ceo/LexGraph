"""RED tests for sprint 2026-08-04-defs-us-multiterm, ruling M-R18 --
pinning the FULL, unmodified `STATE_TX_Cgv_C2009_S2009.003` row's real
candidate-level duplication, driven through the real dispatching
`USProfile.extract_definitions_from_section` method (`get_profile(...)`),
never the bare free function.

Live-verified (2026-08-05) today's real output for the full row:

    total candidates: 9
    term counts: {'Alternative dispute resolution procedure': 1,
                   'Governmental body': 2, 'State agency': 1,
                   'contested case': 2, 'party': 2, 'person': 2,
                   'rule.': 2}

**Every one of the 5 terms this sprint's own F5/F6 work is meant to make
resolvable is double-counted -- but by TWO DIFFERENT, INDEPENDENT root
causes, not one.** Per the sprint manager's own instruction ("if they
share a test, fixing one masks the other"), that same discipline is
applied here to ALL five terms, not only the trailing-period case (see
below) -- each is its OWN test function, and the two mechanisms are never
conflated:

1. **`"Governmental body"` -- ruling M-R18, genuinely new.** Root cause
   confirmed live: ruling U-R10's TX-scoped parent-redirect
   `EntrySplitterRule` (`rules/us_multiterm_shared_clause.py`'s
   `_split_parent_redirect_whole_text`) re-contributes the WHOLE section
   text as an extra block. Baseline's own per-block pass already captures
   `"Governmental body"` correctly from its OWN small block. The
   Developer's finding-4 leading-quote guard
   (`rules/us_inline_parenthetical.py`'s `_parse_block`, pinned by
   `test_definition_links_leading_quote_guard.py`, M-R16) is SUPPOSED to
   stop a `TermClauseRule` pass from re-emitting a term baseline already
   captured for THAT block -- but the guard compares against the
   CONTAINING block's OWN leading quote, and the whole-text block's own
   leading token is `"In this chapter:"`, not a quote at all
   (`_leading_quote_term(...)` is `None`). So when `_parse_block` runs on
   the whole-text block, its unguarded `_cross_reference_candidates` scan
   re-discovers `"Governmental body"` a second time. This is a genuinely
   NEW candidate-level defect, first found while pinning M-R16 -- no
   existing test currently checks this term's COUNT (only its presence,
   e.g. `test_multiterm_f5_shared_clause.py`'s `working_term` regression
   guard).

2. **`"contested case"` / `"party"` / `"person"` / `"rule."`
   -- Residual ledger R1, PRE-EXISTING, unrelated to the guard.** This
   is NOT M-R18's mechanism. Root cause, matching the ledger's own R1
   entry verbatim ("The section now yields 8 candidates: our correct
   combined N-term row, the 4 ORIGINAL degenerate 1-term rows (`;`,
   `""`), and 3 already-working entries"): F5's own
   `_parent_redirect_candidates` (`rules/us_multiterm_shared_clause.py`)
   produces ONE combined 4-term candidate `("contested case", "party",
   "person", "rule.")` from the SAME whole-text block, while baseline's
   OWN per-block pass ALSO independently produces 4 separate degenerate
   1-term candidates (`";"`, `"; and"`, `""` as their `definition_text`)
   from the 4 ORIGINAL lettered blocks -- a completely different pair of
   rule modules and dispatch kinds (F5's `TermClauseRule` vs baseline's
   own per-block splitter) than what produces Governmental body's
   duplicate. R1 is EXPLICITLY on the sprint's own ledger, with its OWN
   owner ("markers", entry-boundary damage per M-R5) and its OWN closing
   condition ("markers' entry-boundary work lands and the degenerate
   rows stop being produced") -- NOT this sprint's to fix, and NOT the
   same defect M-R16/M-R18 investigated. Confirms the count: R1's own
   documented "8 candidates" does NOT include Governmental body's extra
   duplicate -- this file's own live measurement above found 9 total,
   exactly R1's 8 plus M-R18's 1 additional. Pinned here as separate,
   individually-named tests (not folded into the Governmental body pin)
   specifically so a fix to M-R18 (the guard/EntrySplitterRule
   interaction) is never mistaken for also fixing R1 (markers' own,
   differently-owned mechanism), and vice versa.

Live-path discipline: every test below drives the REAL, current
`USProfile.extract_definitions_from_section` method via `get_profile(...)`
on the real, full, unmodified fixture row -- never an excerpt, never the
bare free function.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.definition_links.profiles import get_profile

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _candidates() -> list:
    """The raw candidate list (not flattened to a term Counter) -- added by
    the Planner's cycle-P3 amendment (see `test_tx_rule_entry_term_
    boundary_excludes_trailing_period` and its new sibling
    `test_tx_rule_degenerate_trailing_period_row_residual_r1_blocked_on_
    markers` below) so a test can identify a SPECIFIC candidate by its
    `.terms` shape, not merely ask whether a spelling appears anywhere in
    the flattened population."""
    row = _load_rows()["STATE_TX_Cgv_C2009_S2009.003"]
    profile = get_profile("US-TX")
    scope = profile.determine_scope(row["text"])
    return profile.extract_definitions_from_section(row["text"], scope=scope)


def _term_counts() -> Counter:
    return Counter(t for c in _candidates() for t in c.terms)


# --- M-R18: guard defeated by the TX EntrySplitterRule's whole-text block -


def test_tx_governmental_body_captured_exactly_once_through_full_dispatch():
    """M-R18 (new). See module docstring, item 1, for the full root-cause
    trace (leading-quote guard's per-block comparison never sees a term
    reappearing inside the EntrySplitterRule's own whole-text
    contribution)."""
    counts = _term_counts()
    assert counts["Governmental body"] == 1, (
        f'"Governmental body" was captured {counts["Governmental body"]} times through the '
        f"full, real dispatching path -- expected exactly 1. Ruling M-R18: the finding-4 "
        f"leading-quote guard (rules/us_inline_parenthetical.py's _parse_block) cannot "
        f"suppress this, because the duplicate comes from the TX-scoped parent-redirect "
        f"EntrySplitterRule's whole-text block, whose OWN leading token is 'In this "
        f"chapter:' (not a quote), so the guard's per-block comparison never fires. All "
        f"term counts: {dict(counts)!r}"
    )


# --- Residual ledger R1: pre-existing, NOT M-R18, owned by markers --------


def test_tx_contested_case_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2). Kept as its OWN test, separate from Governmental body's M-R18
    pin above, because the two have different root causes, different
    owners, and different closing conditions on the ledger -- a fix to
    one must never be mistaken for a fix to the other."""
    counts = _term_counts()
    assert counts["contested case"] == 1, (
        f'"contested case" was captured {counts["contested case"]} times through the full, '
        f"real dispatching path -- expected exactly 1. This is Residual ledger R1 (owned by "
        f"markers, NOT M-R18/this sprint's own F6 guard defect): baseline's own degenerate "
        f'per-block candidate (definition_text=";") coexists with F5\'s correct combined '
        f"4-term candidate. All term counts: {dict(counts)!r}"
    )


def test_tx_party_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2 and the sibling `contested_case` test above for the shared
    root cause)."""
    counts = _term_counts()
    assert counts["party"] == 1, (
        f'"party" was captured {counts["party"]} times through the full, real dispatching '
        f"path -- expected exactly 1. Residual ledger R1 (owned by markers): baseline's own "
        f'degenerate per-block candidate (definition_text=";") coexists with F5\'s correct '
        f"combined 4-term candidate. All term counts: {dict(counts)!r}"
    )


def test_tx_person_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2 and the sibling `contested_case` test above for the shared
    root cause)."""
    counts = _term_counts()
    assert counts["person"] == 1, (
        f'"person" was captured {counts["person"]} times through the full, real dispatching '
        f"path -- expected exactly 1. Residual ledger R1 (owned by markers): baseline's own "
        f'degenerate per-block candidate (definition_text="; and") coexists with F5\'s correct '
        f"combined 4-term candidate. All term counts: {dict(counts)!r}"
    )


def test_tx_rule_entry_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2). DEDUP COUNT ONLY -- checks the DUPLICATION count for this
    term, deliberately independent of the term-BOUNDARY question (whether
    the trailing period belongs in the term string at all), which is
    pinned separately in `test_tx_rule_entry_term_boundary_excludes_
    trailing_period` below -- kept apart per the same "don't fold two
    defects into one test" instruction this ruling gave for that other
    test, applied here for consistency to every term in this file.

    Amended per ruling M-R19 item 3 (coordinated Planner change, this
    commit): before this amendment the assertion tracked `counts["rule."]`
    (the term-boundary defect's own captured spelling, matching what
    production emitted at the time). Left as `"rule."`, this pin would
    have become permanently unsatisfiable the moment the Developer's
    unrelated term-boundary fix landed -- production would stop emitting
    `"rule."` (with the period) entirely, so `counts["rule."]` would sit
    at 0 forever regardless of whether markers ever fixes R1's own
    duplication, converting this from "a defect pin" into "a test that
    can never pass." Tracking `counts["rule"]` (bare) instead keeps this
    a valid R1 duplication pin both before and after that unrelated fix:
    right now it is RED because bare "rule" is not the captured spelling
    yet (0 != 1); once the Developer's fix lands it will be RED for R1's
    actual reason (the term is captured twice, 2 != 1); once markers'
    entry-boundary work closes R1 it will pass (1 == 1)."""
    counts = _term_counts()
    assert counts["rule"] == 1, (
        f'"rule" was captured {counts["rule"]} times through the full, real dispatching '
        f"path -- expected exactly 1. Residual ledger R1 (owned by markers): baseline's own "
        f'degenerate per-block candidate (definition_text="") coexists with F5\'s correct '
        f"combined 4-term candidate. All term counts: {dict(counts)!r}"
    )


# --- Separate defect: term-boundary (trailing period), NOT dedup ----------


def test_tx_rule_entry_term_boundary_excludes_trailing_period():
    """A SEPARATE defect from every dedup test above -- deliberately its
    own test, per the sprint manager's explicit instruction not to fold
    this into a dedup assertion (fixing one would mask the other).

    The real row's own text is `(D) "rule."` -- the sentence's own
    closing full stop sits inside the closing quote mark (a common legal-
    drafting/typesetting convention: the WHOLE list-sentence's final
    period, not part of the defined word itself). `_LETTERED_TERM_RE`
    (`rules/us_multiterm_shared_clause.py`) captures group 1 verbatim
    (`[^”"]+`, no `.rstrip()` at all -- contrast `_extract_leading_terms`
    in the SAME module, which already `.rstrip(" ,;")`s ITS OWN captured
    terms, just not `.`), so the captured term is `"rule."`, with the
    period, not the bare word `"rule"` a real downstream mention of "rule"
    would actually contain.

    **DEFENDED, not guessed, per the explicit instruction to say so if my
    own judgment differs:** I agree bare `"rule"` is the semantically
    correct term (the period here is the SENTENCE's own terminator
    adjacent to the closing quote, not part of the word, unlike a genuine
    abbreviation such as "Corp." where the period IS part of the term) --
    matching how `_extract_leading_terms` already strips comma/semicolon
    for the SAME reason on MT's `"owns,"`.

    **CONFLICT this test's own fix would have created, RESOLVED via
    ruling M-R19 item 3 (coordinated Planner amendment, commit
    `64e1634`):** THREE tests elsewhere in this sprint's OWN
    already-committed suite PREVIOUSLY REQUIRED `"rule."` (WITH the
    trailing period) to be the correctly-captured term, and were GREEN
    only because of it:
      - `test_definition_links_multiterm_shared_clause.py::
        test_tx_s2009_003_parent_clause_terms_get_the_real_shared_
        definition_text` (`for term in (..., "rule."): assert term in
        by_term`)
      - `test_multiterm_f5_shared_clause.py::
        test_tx_parent_clause_redirect_list_2009_003`
      - `test_multiterm_f5_shared_clause.py::
        test_tx_parent_clause_redirect_list_2002_001`
    All three were amended in that same commit (plus this file's own
    dedup pin and `test_definition_links_entry_splitter_scope_and_
    length_bound.py`'s `_TX_REDIRECT_TERMS` tuple) to expect bare
    `"rule"`, so the suite was never left internally inconsistent.

    **Planner cycle-P3 amendment (this commit) -- second half split out.**
    This test previously ALSO asserted `"rule." not in counts` (the full
    population never contains the period-bearing spelling at all). That
    half is UNSATISFIABLE within this panel's authority: baseline's own
    per-block splitter (`_leading_quote_candidate` / `_LEADING_QUOTE_RE`
    in `app/definition_links/us_profile.py`) independently emits a
    degenerate 1-term candidate `("rule.",)` from the SAME `(D) "rule."`
    block -- `us_profile.py` is a SHARED module (its own header: "serves
    every US-*/US-FED jurisdiction code, not a per-state fork") and gate
    U3 ("rules ship as registry modules; ZERO shared-module edits")
    forbids this sprint from touching it. That degenerate row is
    Residual ledger R1, owned by markers (ruling M-R5), and does not
    close until markers' entry-boundary work removes it -- see the new
    `test_tx_rule_degenerate_trailing_period_row_residual_r1_blocked_on_
    markers` below, which now carries that half as its own live,
    still-RED pin (not merely a docstring note) so the requirement stays
    ACTIVELY monitored rather than silently dropped.

    What THIS test keeps and tightens is the half that is actually this
    panel's own zero-miss guarantee: not just "bare `rule` appears
    somewhere in the flattened term population" (which the now-inert
    degenerate row could never satisfy anyway, so that alone would be a
    weak check), but that it is F5's own combined parent-redirect
    candidate specifically -- the one whose `.terms` is the 4-tuple --
    that carries it. That is the candidate a real downstream mention of
    "rule" actually resolves through."""
    candidates = _candidates()
    combined = [c for c in candidates if len(c.terms) == 4]
    assert len(combined) == 1, (
        f"expected exactly ONE combined 4-term parent-redirect candidate (F5's own "
        f"`_parent_redirect_candidates`) among the full row's candidates; found "
        f"{len(combined)}. All candidate term-tuples: {[c.terms for c in candidates]!r}"
    )
    assert combined[0].terms == ("contested case", "party", "person", "rule"), (
        f'expected F5\'s combined parent-redirect candidate to carry the bare term "rule" '
        f"(no trailing period) as its 4th term -- the period in the real row's own "
        f'`(D) "rule."` is the enclosing sentence\'s own terminal punctuation, not part of '
        f"the defined word. Got: {combined[0].terms!r}"
    )


# --- Residual ledger R1 (rule.-shaped row): split out, still blocked ------


def test_tx_rule_degenerate_trailing_period_row_residual_r1_blocked_on_markers():
    """Residual ledger R1 (pre-existing, owned by markers per ruling M-R5
    -- see module docstring item 2 and the sibling `contested_case`/
    `party`/`person` dedup tests above for the shared root cause). SPLIT
    OUT (Planner cycle-P3) from `test_tx_rule_entry_term_boundary_
    excludes_trailing_period` above, which used to assert this same
    condition as its second half (`"rule." not in counts`) until the
    Developer's term-boundary fix made that shared test internally
    self-contradictory: after the fix, bare `"rule"` and period-bearing
    `"rule."` are two DIFFERENT strings that no longer collide in a flat
    `Counter`, so the two concerns needed two tests to stay honest about
    which one is satisfiable and which is not.

    (a) **The row still exists.** `USProfile.extract_definitions_from_
    section`'s baseline per-block pass (`_leading_quote_candidate`,
    driven by `_LEADING_QUOTE_RE = re.compile(r'^[“"]([^”"]+)[”"]')`
    in `app/definition_links/us_profile.py`) captures the real row's
    `(D) "rule."` block verbatim, period included, producing a degenerate
    1-term candidate `("rule.",)` with an empty `definition_text` --
    confirmed live (Planner, this cycle) alongside F5's own correct
    4-term combined candidate from the SAME block.

    (b) **It is markers-owned, not this sprint's.** `us_profile.py` is a
    SHARED module used by every `US-*`/`US-FED` jurisdiction, and gate U3
    ("rules ship as registry modules; ZERO shared-module edits") forbids
    this sprint from editing it. Residual ledger R1 already names this
    exact row (`STATE_TX_Cgv_C2009_S2009.003`) and mechanism, owned by
    markers under ruling M-R5, alongside its three siblings
    (`contested case`/`party`/`person`) pinned above in this same file.

    (c) **It is INERT, not harmful, today.** Before the Developer's
    term-boundary fix, NO candidate anywhere carried bare `"rule"` --
    F5's own combined candidate also said `"rule."` -- so a real
    downstream mention of the word "rule" matched NOTHING (a genuine
    zero-miss defect). After that fix (pinned by the sibling test above),
    F5's combined candidate carries bare `"rule"` and the mention
    resolves correctly; this degenerate `"rule."`-spelled row can never
    match real prose (nothing in running text is spelled with a literal
    trailing period fused to the word) -- it is pure noise, not a miss.

    (d) **Closing condition.** This assertion becomes satisfiable again
    -- and should be flipped from `not in` back to a positive check, or
    simply deleted once confirmed structurally impossible -- only when
    markers' entry-boundary work lands and the degenerate per-block rows
    stop being produced for this row (ledger R1's own documented closing
    condition, unchanged by this amendment). Until then this test is
    EXPECTED to stay RED; that RED is the pin, not a bug in this test."""
    counts = _term_counts()
    assert "rule." not in counts, (
        f'"rule." (with the trailing period baked into the term string) is still produced '
        f"by baseline's own per-block splitter in the SHARED `us_profile.py` module "
        f"(gate U3 forbids this sprint from editing it) -- Residual ledger R1, owned by "
        f"markers (ruling M-R5), closing only when their entry-boundary work removes the "
        f"degenerate per-block rows. It is inert (cannot match real prose) now that F5's "
        f'own combined candidate correctly carries bare "rule" (see the sibling '
        f"boundary test above), so this is a precision/noise residual, not a zero-miss "
        f"defect. Got term counts: {dict(counts)!r}"
    )
