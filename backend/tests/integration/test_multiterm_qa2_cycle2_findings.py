"""QA cycle 2 (sprint 2026-08-04-defs-us-multiterm, phase-2) -- independent
adversarial re-verification findings.

Per this panel's QA role rule, this file NEVER touches implementation --
these are RED (except where noted GREEN), on purpose, pinning the exact
real-world shape each defect needs to stop reproducing, for whichever
panel/sprint picks each one up. All rows are vendored, byte-verified
against the real parquet snapshot (`301000fc3465374ee0f23c3c6953a8a861e95cad`)
-- see `qa2_finding_rows.json`; verification script (not committed, per
scratchpad discipline P-R9) confirmed byte-identical `text`/`section_title`
for all 5 rows, `ok=5 bad=0`.

Four independent findings from a fresh, from-scratch, full-corpus
(2,038,247 rows, no sampling) U4 sweep against the CURRENT code (commit
`6d9fe51` + this cycle's own verification commits):

1. **NEW gap, F5's own remit -- split into finding A (idiom recognition,
   FIXED, GREEN) and finding A2 (untriggered trailing member, a SEPARATE,
   STILL-OPEN miss found in the SAME target row, RED).** Finding A:
   `_IDIOM_RE` (`rules/us_multiterm_shared_clause.py`) recognized only
   `means?|shall\\s+mean`, not "have/has the meaning(s)" -- a common real
   federal (and some state) drafting idiom for multi-term shared clauses.
   Full-corpus sizing: 70 genuinely missed terms across federal (57)/HI(2)/
   IL(7)/MI(1)/MT(2)/ND(1). Same class of defect as QA cycle 1's finding 3
   ("as defined in" missing from the SIBLING module F6's idiom list, since
   fixed). FIXED by the Developer this cycle (widened `_IDIOM_RE` to the
   plural "have/has the meanings" idiom; +739 terms corpus-wide, 0 lost) --
   pinned GREEN below.

   Finding A2 (Planner amendment, this commit): the ORIGINAL version of
   this test carried a second assertion on real row `USC_T2_C20_S900`,
   framed as a "differential control" -- the claim that the SAME
   sentence's 5th co-defined term, `"discretionary spending limit"`,
   "uses plain 'shall mean' and IS correctly captured by baseline."
   **That premise is false, independently re-verified this cycle** (see
   the new test below): the term has never been captured, by baseline,
   by F5 before this idiom fix, or by F5 after it. It is not a control on
   finding A at all -- it is a genuine, previously-unidentified miss, now
   pinned as its own RED test with its own honest root cause and
   ownership, no longer conflated with finding A's (fixed, GREEN)
   4-term claim.
2. **Correction to the manager's residual-R5 count** -- "duplicates are
   down to 1 row corpus-wide (HI `association`)" underclaims by one: a
   FULL-corpus (not the manager's 79,500-row stride sample) re-run of the
   identical cross-primitive-overlap check found a SECOND real row, DE
   `STATE_DE_T12_C9_S902`, term `"the Code"`. Checked one level deeper
   before filing (this panel's own standing lesson): at the PERSIST layer
   both known instances (HI + DE) collapse to exactly ONE `Definition` row
   each, because both duplicate candidates carry the IDENTICAL term tuple
   -- so the corrected count is 2 known candidate-level dup rows, not 1,
   but severity is unchanged (harmless, same class as the already-accepted
   AR within-primitive guard below). GREEN, not RED -- this test PASSES
   today; it corrects a number, not a defect.
3. **Correction to ruling M-R24's "absent elsewhere" claim** -- "[the
   hyphen-suffixed-marker recall regression] is a Texas drafting
   convention... pervasive within TX and absent elsewhere" (checked
   DE/NY/CA/IL/FL/OH/PA/GA/AR, found zero). A full-corpus scan for the
   underlying residual-R6 SHAPE (hyphen-suffixed marker directly before a
   quoted term using PLAIN "means", which baseline's
   `_MARKER_TOKEN_RE = \\(\\w+\\)` cannot open a block at) found it very
   much NOT absent elsewhere: DC (1 row) and NH (4 rows) both have it,
   genuinely missed today, confirmed live -- these two states were not
   among the ones M-R24 checked. (NY also matched the R6 shape 19 times,
   but NY's case is dwarfed by finding 4 below and not double-counted
   here.) R6 remains correctly routed to markers (core-owned
   `_MARKER_TOKEN_RE`, a shared module this sprint cannot edit under U3) --
   this is a sizing correction to the "TX-only" framing, not an ownership
   dispute.
4. **NEW, large, previously-unrouted finding, found while investigating
   #3** -- every one of NY's 40,102 real corpus rows (100% of the file,
   confirmed) stores `text` with ZERO real newline characters and literal
   two-character `"\\n"` sequences instead (a raw-text/scrape-encoding
   defect upstream of extraction entirely, confirmed at the byte level,
   not a printing artifact). `_split_into_numbered_blocks` anchors entry
   markers on real newlines, so ANY NY Definitions section -- not just
   ones with F5/F6 shapes -- yields ZERO blocks and ZERO candidates.
   Full-corpus measured: 1,470 real NY Definitions sections (of 64,480
   corpus-wide) are TOTAL misses as a direct result -- every definition in
   every one of those sections, not just multi-term ones. Confirmed this
   is NOT a regression this sprint caused: the bare pre-sprint
   `extract_definitions_from_section` function fails identically (verified
   live, `test_qa2_finding_d_...` below uses the SAME dispatched call this
   sprint's own U5 baseline-state check already exercises). Not F5/F6's
   mechanism, not markers' drafting-convention territory either -- a raw
   data-ingestion/normalization defect, reported here because it was found
   during this cycle's own adversarial work and was not on any ledger or
   escalation this panel could find. Routed to the program manager, not
   claimed by this sprint.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "qa2_finding_rows.json"
)


def _row(act_id: str) -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}[act_id]


def _ingest_and_link(db_session, matter_with_users, *, title, row, jurisdiction):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        rows=[row],
        jurisdiction=jurisdiction,
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


def test_qa2_finding_a_f5_have_the_meaning_idiom_not_recognized(db_session, matter_with_users):
    """FINDING A -- new gap, F5's own remit, not blocked on any other
    sprint. NOW GREEN. Real row `USC_T2_C20_S900` (federal 2 U.S.C. §
    900(c)): `'The terms "budget authority", "new budget authority",
    "outlays", and "deficit" have the meanings given to such terms in
    section 3 of the Congressional Budget and Impoundment Control Act of
    1974 [2 U.S.C. 622] and "discretionary spending limit" shall mean the
    am...'` -- a clean, textbook 4-term nested shared clause
    (`_NESTED_TRIGGER_RE` matches "The terms" and `_extract_leading_terms`
    correctly walks all 4 quotes), but `_IDIOM_RE` did not recognize "have
    the meaning(s)" as a defining idiom (only `means?`/`shall\\s+mean`), so
    `_nested_clause_candidates` silently dropped the whole clause. Fixed
    by the Developer this cycle (widened `_IDIOM_RE` to also recognize the
    plural "have/has the meanings" idiom).

    Planner amendment (this commit): this test previously carried a SECOND
    assertion on the same row's 5th co-defined term,
    `"discretionary spending limit"`, framed as a "differential control."
    That framing was FALSE -- the term has never been captured by any
    mechanism, independently re-verified (see the new, separate
    `test_qa2_finding_a2_...` test below, which now owns that claim
    honestly as its own genuine miss). Removed from here per this sprint's
    own one-defect-per-test convention (this file's sibling tests, and
    ruling M-R19 item 3) -- this test now pins ONLY finding A's actual,
    fixed claim."""
    row = _row("USC_T2_C20_S900")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="US Code (QA-2 finding A -- F5 'have the meaning(s)' idiom not recognized)",
        row=row,
        jurisdiction="US-FED",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    missing = {"budget authority", "new budget authority", "outlays", "deficit"} - all_terms
    assert not missing, (
        f"expected all 4 terms captured via the 'have the meanings given' idiom -- "
        f"F5's _IDIOM_RE (rules/us_multiterm_shared_clause.py) recognizes only "
        f'"means"/"shall mean", not "have/has the meaning(s)". Missing: {sorted(missing)!r}. '
        f"All captured terms: {sorted(all_terms)!r}. Corpus-wide sizing (QA-2, full 53-file "
        f"scan, no sampling): 70 genuinely missed terms, federal=57 hi=2 il=7 mi=1 mt=2 nd=1."
    )


def test_qa2_finding_a2_discretionary_spending_limit_untriggered_trailing_member_miss(
    db_session, matter_with_users
):
    """FINDING A2 (Planner amendment, this commit, split out of finding A
    above) -- a GENUINE, previously-unidentified miss on the SAME real row
    `USC_T2_C20_S900`, NOT a differential control, NOT caused by the
    idiom fix, NOT a regression. Independently re-verified live (Planner,
    this cycle) by driving the real dispatching
    `USProfile.extract_definitions_from_section` path and swapping only
    `_IDIOM_RE` between its pre-finding-A-fix and post-fix forms:

        BEFORE fix: 4 target terms captured? False   ([])
        AFTER  fix: 4 target terms captured? True
        'discretionary spending limit' BEFORE: False    AFTER: False
        terms LOST by the fix: []
        terms GAINED by the fix: [budget authority, deficit,
                                   new budget authority, outlays]

    Also independently confirmed against PURE baseline (the bare
    `us_profile.extract_definitions_from_section` function, zero rules
    consulted at all): it captures ZERO terms from this row's entry (1)
    block, because the block's own leading token is `The terms`, not a
    quote (`_LEADING_QUOTE_RE` requires the block to START with `"`/`“`)
    -- so baseline was never a route to this term either, before or after
    anything this sprint has done.

    **Root cause (Developer's, independently verified live).** Entry (1)
    is ONE block: `'The terms "budget authority", "new budget authority",
    "outlays", and "deficit" have the meanings given to such terms in
    section 3 ... and "discretionary spending limit" shall mean the
    amounts specified in section 901 of this title.'` It contains exactly
    ONE `_NESTED_TRIGGER_RE` match (`"The terms"`, at the start) --
    `"to such terms in section 3"` does not match (`_NESTED_TRIGGER_RE`
    requires "the" immediately before "term(s)"; "such terms" does not
    qualify). `_nested_clause_candidates`'s Case 2 bounds a clause from
    its own trigger to the START of the NEXT trigger (or end-of-block) --
    with no second trigger, the clause runs to end-of-block, so the
    trailing `and "discretionary spending limit" shall mean ...` text is
    swallowed whole into the 4-term candidate's own `definition_text` as
    dead prose, never re-scanned for its own quoted term. Confirmed live:
    the produced 4-term candidate's `definition_text` ends with exactly
    that trailing text, verbatim, and no candidate anywhere carries
    `("discretionary spending limit",)`.

    **This assertion is satisfiable, not vacuous (checked both the defect
    state AND a plausible fixed state before trusting it, per this
    sprint's own M-R28 discipline).** Measured: `"discretionary spending
    limit" in all_terms` is False today (both before and after the idiom
    fix) and flips to True under a hypothetical structural fix that splits
    an un-triggered trailing `and "X" <idiom> ...` member out of a Case-2
    clause into its own candidate (verified live against the real
    dispatch + persist pipeline via a scratch monkeypatch, not committed,
    per scratchpad discipline P-R9) -- the 4-term claim continued to hold
    simultaneously, confirming a real fix would not need to trade one
    claim for the other.

    **Ownership: OURS -- F5's own family, not markers', not scoped-
    inline's.** Unlike residual ledger R1/R6 (owned by markers, living in
    the SHARED `us_profile.py` gate U3 forbids this sprint from editing),
    this defect lives entirely inside `_nested_clause_candidates`'s own
    clause-boundary logic in `rules/us_multiterm_shared_clause.py` -- a
    module this sprint owns and can edit freely. It is a multi-term
    shared clause (F5's own remit by definition) whose trailing member is
    introduced without its own `the term(s)` trigger -- structurally the
    same FAMILY of shape F5 already exists to handle, just one boundary
    case deeper.

    **Deliberately NOT fixed this cycle.** Closing it needs a structural
    change to Case 2's clause-boundary detection (recognizing an
    un-triggered trailing `and "X" <idiom>` member as its own clause),
    not an idiom widening like finding A's fix. That kind of broadening
    is exactly the shape of risk this program has already been burned on
    twice under ESCALATION E3 (`docs/sprint/sprints/2026-08-04-defs-us-
    multiterm-log.md`): F6's cross-reference rescue previously
    over-broadened into "family 1" territory (`defs-us-scoped-inline`'s
    own remit -- an ordinary body's ANY quoted-term-plus-plain-idiom
    match, e.g. bare "means"/"shall mean" on a term with no special
    trigger), and had to be narrowed back under a program ruling.
    Recognizing an un-triggered trailing "and \"X\" shall mean ..."
    member is the SAME general shape (a plain idiom match with no `the
    term(s)` trigger) E3 drew the family-1 boundary around -- a careless
    fix here risks re-opening that exact boundary rather than staying
    inside F5's own multi-term-shared-clause remit. `_IDIOM_RE`'s own
    module comment (this file's sibling, `rules/us_multiterm_shared_
    clause.py`) documents the same class of guard rail already paid for
    once (the DC "parent" / TX "Governmental body" duplicate-candidate
    guard tests) -- any structural fix here must keep those green too.

    **Closing condition.** This assertion should flip from `in` staying
    RED to GREEN only when Case 2's clause-boundary detection is
    structurally widened to recognize an un-triggered trailing member as
    its own candidate, WITHOUT (a) reopening the F5/F6 single-term
    duplicate-candidate boundary (the DC/TX guard tests in
    `tests/unit/test_definition_links_leading_quote_guard.py` must stay
    green), and (b) colonizing family-1/E3 territory (any newly-broadened
    match must stay scoped to an un-triggered member INSIDE an otherwise
    trigger-anchored multi-term clause, not fire on an ordinary standalone
    body sentence). Until then this test is EXPECTED to stay RED; that
    RED is the pin, not a bug in this test."""
    row = _row("USC_T2_C20_S900")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="US Code (QA-2 finding A2 -- untriggered trailing member, genuine miss)",
        row=row,
        jurisdiction="US-FED",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "discretionary spending limit" in all_terms, (
        '"discretionary spending limit" was not captured -- it is the SAME row\'s 5th '
        "co-defined term, introduced by `and \"discretionary spending limit\" shall mean ...` "
        "with no `the term(s)` trigger of its own, so F5's `_nested_clause_candidates` (Case "
        "2, `rules/us_multiterm_shared_clause.py`) swallows it whole into the preceding "
        "4-term candidate's own definition_text instead of emitting it as its own candidate. "
        "Never captured by baseline, by F5 before finding A's idiom fix, or by F5 after it -- "
        "a genuine, previously-unidentified miss, OWNED BY THIS SPRINT (F5's own family, "
        "`rules/us_multiterm_shared_clause.py`, not the shared `us_profile.py`), deliberately "
        "not fixed this cycle: closing it needs a structural change to Case 2's clause-"
        "boundary detection, not an idiom widening, and that change risks reopening the "
        "family-1/E3 boundary this program has already been burned on twice -- see this "
        f"test's own docstring for the full root-cause and closing-condition detail. "
        f"All captured terms: {sorted(all_terms)!r}"
    )


def test_qa2_finding_b_r5_second_cross_path_duplicate_is_harmless_at_persist_layer(
    db_session, matter_with_users
):
    """FINDING B -- GREEN, not RED. Corrects a COUNT, not a defect.

    Manager's claim (ruling M-R24 / residual ledger R5): "duplicates are
    down to 1 row corpus-wide (the HI `association` cross-path case)". A
    full-corpus (2,038,247 rows, no sampling -- the manager's own number
    came from a 79,500-row deterministic stride sample) re-run of the
    IDENTICAL cross-primitive-overlap check (`_apposition_candidates`
    term-set ∩ `_cross_reference_candidates` term-set, per ordinary-body
    row) found a SECOND real instance: `STATE_DE_T12_C9_S902`, term
    `"the Code"` -- captured once via the apposition primitive
    (`(“the Code”)`) and once via the cross-reference primitive (`... any
    reference in this chapter to “the Code” as defined in paragraph
    (a)(1)...`), confirmed live, both primitives firing independently on
    the SAME article body (mirrors the HI mechanism exactly: each
    primitive is individually clean, per M-R21(b); the union happens in
    `_extract_ordinary_body`).

    Checked one level deeper (this panel's own "re-derive, don't re-read"
    discipline, and per the sprint's OWN documented lesson from checking
    the AR within-primitive case) before filing this as a severity
    escalation: BOTH `terms` tuples for DE's two candidates are the
    IDENTICAL `("the Code",)`. The persist-layer dedup key
    `(article_id, sorted(candidate.terms))` therefore collapses them to
    ONE `Definition` row -- verified live, this test. (A parallel check,
    not included as its own test to avoid re-deriving what this file
    already establishes, confirmed the SAME collapse for the original HI
    `association` row.) So the corrected, full-corpus count for this
    residual is 2 known candidate-level duplicate rows, not 1 -- but
    severity is UNCHANGED: both are harmless at the live/persisted level,
    the same class already accepted as a GREEN guard for the AR
    within-primitive duplicate in `test_multiterm_qa_u4_findings.py`."""
    row = _row("STATE_DE_T12_C9_S902")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="DE Code (QA-2 finding B -- R5 count correction, harmless at persist layer)",
        row=row,
        jurisdiction="US-DE",
    )
    the_code_defs = [d for d in result["created_definitions"] if "the Code" in d["terms"]]
    assert len(the_code_defs) == 1, (
        f'expected the cross-primitive duplicate for "the Code" to collapse to exactly ONE '
        f"persisted Definition row (same-term-tuple dedup at the persist layer) -- got "
        f"{len(the_code_defs)}: {the_code_defs!r}. If this now fails, the persist-layer dedup "
        f"key itself has changed behavior -- re-diagnose before assuming R5 is unchanged."
    )


def test_qa2_finding_c1_r6_hyphen_marker_shape_is_not_tx_only_dc(db_session, matter_with_users):
    """FINDING C1 -- sizing correction to ruling M-R24's "Texas drafting
    convention... absent elsewhere" claim (checked DE/NY/CA/IL/FL/OH/PA/GA/
    AR, found zero). Real row `STATE_DC_T5_C12_S5-1201`:
    `'(1-a) "State agent" means any person compensated directly or
    indirectly by a state or...'` -- a hyphen-suffixed marker `(1-a)`
    directly before a quoted term using PLAIN "means" (not a
    cross-reference idiom, so F6's cross-reference rescue -- the mechanism
    that made the ORIGINAL M-R23 TX regression visible at all -- does not
    apply here either). Baseline's `_MARKER_TOKEN_RE = \\(\\w+\\)`
    (`us_profile.py`) cannot open a block at a hyphenated marker, so this
    term is dropped entirely -- confirmed pre-existing in the SHARED,
    core-owned module (not this sprint's to fix under gate U3), the same
    mechanism as residual R6, genuinely present in DC (not TX). RED,
    correctly not ours to fix -- pinned so the state name is on record."""
    row = _row("STATE_DC_T5_C12_S5-1201")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="DC Code (QA-2 finding C1 -- residual R6 shape, DC not TX)",
        row=row,
        jurisdiction="US-DC",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "State agent" in all_terms, (
        f'"State agent" (marker "(1-a)") was not captured -- baseline\'s _MARKER_TOKEN_RE '
        f"cannot open a block at a hyphen-suffixed marker (residual R6's mechanism), a SHARED "
        f"core-owned module this sprint cannot edit under gate U3. Correctly routed to markers, "
        f"same as R6 -- this pin corrects ruling M-R24's claim that the shape is TX-only. "
        f"All captured terms: {sorted(all_terms)!r}"
    )


def test_qa2_finding_c2_r6_hyphen_marker_shape_is_not_tx_only_nh(db_session, matter_with_users):
    """FINDING C2 -- second state for the same correction as C1 above.
    Real row `STATE_NH_TXXXVIII_C421-B_S1-102`: `'(35-a) "Open blockchain
    token" means a digital unit which is: ...'` -- same mechanism, same
    residual R6, genuinely present in NH."""
    row = _row("STATE_NH_TXXXVIII_C421-B_S1-102")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="NH Code (QA-2 finding C2 -- residual R6 shape, NH not TX)",
        row=row,
        jurisdiction="US-NH",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "Open blockchain token" in all_terms, (
        f'"Open blockchain token" (marker "(35-a)") was not captured -- same residual-R6 '
        f"mechanism as finding C1, genuinely present in NH, not TX-specific. "
        f"All captured terms: {sorted(all_terms)!r}"
    )


def test_qa2_finding_d_ny_corpuswide_literal_backslash_n_defect(db_session, matter_with_users):
    """FINDING D -- NEW, large, previously-unrouted finding, found while
    investigating finding C's routing. Real row `STATE_NY_AHAY_A6_S110`
    (heading "§ 110. Definitions.", confirmed a recognized Definitions
    section): `'1. The term "state moneys" shall include moneys paid by
    the state to\\n  the county...  2. The term "county superintendent of
    highways" shall include county\\n...'` -- as VENDORED (this row's
    `text` field, byte-verified against the real parquet snapshot), the
    two `\\n` sequences shown above are the LITERAL two-character string
    backslash+n, NOT real newline characters -- confirmed at the byte
    level (`text.count(chr(10)) == 0`, `text.count("\\\\n") == 4` for this
    row). `_split_into_numbered_blocks` (`us_profile.py`) anchors entry
    markers on real newlines, so this genuine, well-formed, 2-term
    Definitions section yields ZERO candidates -- both terms silently lost.

    Verified this is corpus-wide, not this one row: EVERY ONE of NY's
    40,102 real rows (100%, confirmed) has zero real newline characters.
    Full-corpus measured (QA-2, no sampling): 1,470 real NY Definitions
    sections yield zero candidates as a direct, measured consequence --
    not limited to multi-term/parenthetical shapes, EVERY definition in
    each of those 1,470 sections is lost. This is NOT a regression this
    sprint introduced (the bare pre-sprint `extract_definitions_from_
    section` fails identically -- this sprint's rules never get a chance
    to run at all, since baseline's own block splitter already returns
    zero blocks). Not F5/F6's mechanism, not a drafting-convention gap
    markers would fix either -- looks like a raw corpus/scrape
    normalization defect specific to the NY file, reported here because
    it was found during this cycle's adversarial work and is not on any
    ledger or escalation list this panel could find. Routed to the program
    manager; NOT claimed by this sprint."""
    row = _row("STATE_NY_AHAY_A6_S110")

    real_newlines = row["text"].count("\n")
    literal_backslash_n = row["text"].count("\\n")
    assert real_newlines == 0 and literal_backslash_n > 0, (
        "precondition failed -- this row's `text` no longer has the literal-backslash-n shape "
        f"this finding depends on (real_newlines={real_newlines}, "
        f"literal_backslash_n={literal_backslash_n}); re-diagnose before trusting the "
        "assertion below."
    )

    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="NY Code (QA-2 finding D -- corpus-wide literal-backslash-n defect)",
        row=row,
        jurisdiction="US-NY",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    missing = {"state moneys", "county superintendent of highways"} - all_terms
    assert not missing, (
        f"expected both real terms captured from a genuine, well-formed NY Definitions "
        f"section -- got zero candidates because `_split_into_numbered_blocks` cannot find "
        f'any REAL newline character in this row\'s `text` (it has {literal_backslash_n} '
        f'literal two-character "\\\\n" sequences instead, a raw corpus-encoding defect '
        f"affecting 100% of NY's 40,102 rows). Missing: {sorted(missing)!r}. Full-corpus "
        f"measured impact: 1,470 real NY Definitions sections (of 64,480 corpus-wide) are "
        f"TOTAL misses as a direct result -- reported to the program manager, not claimed "
        f"by this sprint."
    )
