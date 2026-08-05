"""Planner cycle-8/phase-2 (sprint 2026-08-04-defs-us-preamble, D1, manager
rulings M-R59 -> M-R64 -> program ruling P-FP -> M-R70..M-R74): live-path
tests for the commissioned colon-list defining-verb narrowing.

**RE-ADJUDICATED under P-FP (2026-08-05, this Planner pass).** Cycle-8
authored 6 `Test*NotCaptured` rows as "false positives" using QA's cycle-7
ROW-level FP list. Program ruling P-FP (`-programs/2026-08-04-definition-
completeness.md`) settled that FP granularity for a capture/extraction rule
follows the RULE'S OUTPUT: an FP exists only if a captured `(row, term,
definition_text)` tuple is not a genuine definition of that term in that
row. Trigger-clause mislabeling that still yields a genuine definition is a
RECOGNITION-path note, not an FP. Forwarding / "has the meaning given in"
definitions are GENUINE per D-MT-E1.

This Planner re-read all 6 rows' REAL captured `(term, definition_text)`
tuples against the real corpus body (not the test's own prior docstring --
"the label on the jar is what rots"). Verdict: **5 of 6 are GENUINE**,
including 3 the manager had not yet ruled on (`USC_T10_C303_S4093`,
`USC_T42_C7_S679c`, `USC_T10_C953_S9448` -- all three docstrings'
characterizations turned out to be WRONG once the actual captured text was
read). Only `USC_T35_C4_S41` is confirmed definition-level garbage.

| act_id | captured term(s) | real definition_text (abridged) | verdict |
|---|---|---|---|
| `USC_T22_C102_S9528` | `financial, material, or technological support`, `foreign person`, `Syria` | `"...has the meaning given such term in section NNN.NNN of title 31, CFR..."` (x3, real (d) Definitions clause) | GENUINE forwarding (M-R72 RULED) |
| `STATE_DE_T13_C5_SII_S513` | `Employer` | `"has the meaning given such term in Sec. 4301(d)... AND includes any governmental entity... AND includes an individual, partnership..."` | GENUINE forwarding + substantive `includes` content (M-R72 RULED) |
| `USC_T10_C303_S4093` | `institution of higher education` | real body: `"(h) Institution of Higher Education Defined.--In this section, the term 'institution of higher education' has the meaning given such term in section 101 of the Higher Education Act of 1965 (20 U.S.C. 1001)."` -- the captured text is this exact clause | GENUINE forwarding (this Planner's own read, confirming M-R72's SUSPECT flag) |
| `USC_T42_C7_S679c` | `early approved tribe, organization, or consortium` | real body: `"(III) Definition of early approved tribe, organization, or consortium -- For purposes of subclause (II) of this clause, the term \\"early approved tribe, organization, or consortium\\" means an Indian tribe, tribal organization, or tribal consortium that had a plan approved under section 671..."` -- the captured `definition_text` is a byte-for-byte match of this real `means` clause, NOT the superficially-similar-sounding `"...is an early approved tribe..."` USE elsewhere in the body the old docstring described | GENUINE local `means` definition (this Planner's own read; the old docstring's "circular self-reference" characterization described the WRONG sentence) |
| `USC_T10_C953_S9448` | `commissioned service obligation` | real body, subsection (d): `"In this section, the term 'commissioned service obligation', with respect to a cadet, means the period beginning on the date of the cadet's appointment as a commissioned officer and ending on the sixth anniversary of such appointment..."` -- the captured `definition_text` is a byte-for-byte match | GENUINE local `means` definition (this Planner's own read; the old docstring's "amendment-history note" characterization described a DIFFERENT, unrelated substring match, not what was actually captured) |
| `USC_T35_C4_S41` | `SEC. 804. DEFINITION.` | real body: a quoted historical-note block whose OWN internal heading is `"SEC. 804. DEFINITION."`, itself containing a genuine `"the term 'Director' means..."` clause -- but the extractor captured the SECTION-LABEL HEADING as the term (not `Director`), and the definition_text then bleeds across several UNRELATED subsequent editorial notes to the end of the body | GARBAGE at definition granularity: wrong term captured, definition_text is not a definition of that term (confirmed M-R63 + this Planner) |

**Consequence**: 5 of the 6 original `Test*NotCaptured` functions asserted
exactly what P-FP forbids ("this genuine definition must not be captured")
and are re-authored below as `test_*_still_captured` regression guards,
physically joining Section 2's existing 5-test family (M-R64's directive:
"the 5 positive guards must be extended to cover forwarding-definition
rows like `USC_T22_C102_S9528`" -- satisfied here for `USC_T22_C102_S9528`
AND the other 4 newly-adjudicated genuine rows in one pass). Only
`USC_T35_C4_S41` remains a true negative (Section 1).

**Zero production code touched by this re-adjudication.** No narrowing has
shipped; `us_body_preamble.py` is unchanged. Every row below is captured
(or not) by TODAY's unmodified code -- this file only corrects which
outcome the test SHOULD assert, per P-FP.

**Named, unresolved dependency (M-R73/D-MT-E1, not this file's job):**
every GENUINE forwarding definition below (`has the meaning given...in
section X`) captures the LOCAL row + term today, but not yet the
REFERENCE EDGE to the target law/section D-MT-E1 also requires ("capture
now, AND capture the reference"). That edge is core-v2 seam plumbing, out
of this sprint's file -- named here, not silently dropped.

---

Section 2 (unchanged from cycle-8) also carries the POSITIVE / REGRESSION-
GUARD tests for real rows that are GENUINELY, CORRECTLY captured TODAY
(verified against the real `definition_text` output) and that a NAIVE
local-window narrowing -- one that only inspects a bounded text window
immediately following the SPECIFIC trigger occurrence that won recognition
-- WOULD SILENTLY DROP (M-R64's adopted option (c): fix the root causes so
the RIGHT occurrence wins, instead of narrowing around a wrong one).

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _negative_row(act_id: str) -> dict:
    # Historical fixture-file name (cycle-8): 5 of its 6 rows are now used
    # as POSITIVE/regression-guard fixtures below, per the P-FP
    # re-adjudication in this file's module docstring. Kept unrenamed to
    # avoid churning a byte-exact vendored fixture file for a naming-only
    # reason; only `USC_T35_C4_S41` is still used as a true negative.
    data = json.loads((FIXTURES / "cycle8_defining_verb_negative_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


def _positive_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "cycle8_defining_verb_positive_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


def _ingest_and_link(db_session, matter_with_users, *, row: dict, jurisdiction: str, title: str):
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


def _persisted_definition_text_by_term(db_session, result: dict) -> dict[str, str]:
    """Read the persisted P-FP output, not merely the response's term list."""
    from app.models.definition import Definition

    persisted = []
    for created in result["created_definitions"]:
        definition = db_session.get(Definition, created["id"])
        assert definition is not None, f"pipeline returned missing Definition id {created['id']}"
        persisted.append(definition)
    return {term: definition.definition_text for definition in persisted for term in definition.terms}


# --- 1. NEGATIVE: the ONE row confirmed genuine definition-level garbage ---
# --- under P-FP (re-adjudicated; was 6, now 1 -- see module docstring) ----


def test_usc_t35_c4_s41_section_label_is_not_a_defined_term_not_captured(db_session, matter_with_users):
    """`USC_T35_C4_S41`: today's colon-list branch wrongly claims this row
    off a spurious 'in this section to recover the estimate...' occurrence.
    The real body DOES contain a genuine embedded definition (a quoted
    historical note whose own internal heading is 'SEC. 804. DEFINITION.',
    reading 'In this title, the term "Director" means the Under Secretary
    of Commerce for Intellectual Property...') -- but the extractor
    captures the SECTION-LABEL HEADING TEXT ITSELF ('SEC. 804.
    DEFINITION.') as the TERM, not 'Director', and the definition_text
    then bleeds across several unrelated subsequent editorial notes all the
    way to the end of the body. Confirmed live (this Planner, phase-2):
    the captured term is not genuinely defined by the captured
    definition_text in this row -- genuine definition-level garbage under
    P-FP, independent of the (also real) recognition-path mislabeling."""
    row = _negative_row("USC_T35_C4_S41")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T35 C4 S41 (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']} once the colon-list "
        f"branch requires a real term:means structure in its own window; got "
        f"{result['created_definitions']!r} -- this row has no genuine local "
        "definition anywhere near its winning trigger occurrence (QA cycle-7 FP, "
        "P-FP-confirmed definition-granularity garbage)"
    )


# --- 2. POSITIVE / REGRESSION-GUARD: genuine captures a naive narrowing --
# --- would silently drop. GREEN today; must STAY green. -------------------
#
# Two sub-families, both under the SAME contract ("must remain captured"):
#   (a) the original 5 (M-R59/M-R64): genuine LOCAL `means`/`shall mean`
#       definitions reached today only via a spurious rescuing occurrence
#       elsewhere in the body.
#   (b) the 5 re-adjudicated under P-FP (this Planner pass, phase-2):
#       genuine FORWARDING definitions (`has the meaning given...`) or
#       genuine local `means` definitions the cycle-8 docstrings had
#       mischaracterized as garbage -- see module docstring's table.


def test_state_oh_child_still_captured_despite_a_spurious_winning_occurrence_elsewhere_in_the_body(
    db_session, matter_with_users
):
    """`STATE_OH_T45_C4510_S4510.17`: today's WINNING recognition
    occurrence ('in this state.', deep in a driver's-license-suspension
    procedural clause) is JUST AS SPURIOUS as this cycle's confirmed FPs
    -- but the SAME body's division (H) genuinely reads '(H) As used in
    divisions (C) and (D) of this section: (1) "Child" means a person who
    is under the age of eighteen years...'. `_B1_TRIGGER_RE` never
    matches THIS clause at all ('As used in divisions (C) and (D) of'
    intervenes between 'As used in' and 'this section'), so recognition
    depends entirely on the spurious occurrence. A narrowing that inspects
    only the spurious occurrence's own local window would orphan this
    genuine 'Child' definition. Must remain captured."""
    row = _positive_row("STATE_OH_T45_C4510_S4510.17")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-OH",
        title="OH T45 C4510 S4510.17 (cycle-8 defining-verb regression guard)",
    )
    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "Child" in created_terms, (
        f"expected 'Child' among {sorted(created_terms)} -- this row's real "
        "definition ('\"Child\" means a person who is under the age of "
        "eighteen years...') must survive the colon-list narrowing even "
        "though today's winning trigger occurrence is itself spurious"
    )


def test_usc_public_utility_and_wholesale_sale_still_captured_despite_a_spurious_winning_occurrence(
    db_session, matter_with_users
):
    """`USC_T16_C12_S824`: today's winning occurrence ('in this section
    shall—', introducing '(A) preempt applicable State law...(B) in any
    way limit rights...') is a limitations clause structurally identical
    to QA's confirmed em-dash FPs -- yet this real Federal Power Act
    section ALSO genuinely defines '"Sale of electric energy at
    wholesale" ... means a sale of electric energy to any person for
    resale' and '"Public utility" ... means any person who owns or
    operates facilities subject to the jurisdiction of the Commission...'
    elsewhere in the same body. Must remain captured."""
    row = _positive_row("USC_T16_C12_S824")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T16 C12 S824 (cycle-8 defining-verb regression guard)",
    )
    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert {"Sale of electric energy at wholesale", "Public utility"} <= created_terms, (
        f"expected both real Federal Power Act terms among {sorted(created_terms)} "
        "-- must survive the colon-list narrowing even though today's winning "
        "trigger occurrence is itself a spurious limitations clause"
    )


def test_state_pa_association_still_captured_despite_the_trigger_regexs_own_greedy_tail_swallowing_means(
    db_session, matter_with_users
):
    """`STATE_PA_T15_C75_S7502`: the real defining clause is '...as used
    in this chapter means a corporation with or without capital stock
    incorporated under any of the following: (1)...'. `_B1_TRIGGER_RE`'s
    own greedy unit-name tail (`[A-Za-z0-9 .\\-]{0,30}`) consumes 'means a
    corporation wit' INTO the trigger match itself (confirmed live: the
    winning match text is literally 'in this chapter means a corporation
    wit'), so a verb-presence check applied only to text strictly AFTER
    the trigger match's end never sees the word 'means' at all -- a
    PRE-EXISTING regex-greediness hazard this sprint's own D3 note
    flagged last cycle ('found zero false positives caused by it' then).
    Must remain captured. (See also `test_us_body_preamble_option_c_root_
    cause_red.py`, which pins this SAME root cause directly against the
    `_B1_TRIGGER_RE` regex as a live-path RED test for the Developer's
    option-(c) fix, rather than only guarding the pipeline-level
    OUTCOME here.)"""
    row = _positive_row("STATE_PA_T15_C75_S7502")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-PA",
        title="PA T15 C75 S7502 (cycle-8 defining-verb regression guard)",
    )
    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "association" in created_terms, (
        f"expected 'association' among {sorted(created_terms)} -- this row's "
        "own defining verb ('means') is swallowed by the trigger regex's own "
        "greedy tail; a narrowing that searches only strictly-after-trigger "
        "text must still be able to reach it (or the trigger regex itself "
        "needs a matching fix) for this real row to survive"
    )


def test_usc_united_states_includes_still_captured_the_d_includes_cascading_gap(
    db_session, matter_with_users
):
    """`USC_T15_C1_S26a`: '(c) "United States" defined\\n\\nAs used in this
    section, "United States" includes the several States, the District of
    Columbia...'. This occurrence is a comma-gap quote-means shape, not
    colon-list, but `_b1_quote_means_branch`'s own verb group
    (`_B1_QUOTE_MEANS_RE`) is `means|shall mean` ONLY -- it does not
    recognize `includes` (the D-INCLUDES gap, but in the SIBLING branch
    M-R59 does not commission touching). Recognition succeeds today only
    via a genuinely spurious 'in this section shall—' occurrence earlier
    in the body (a prohibition-list clause). If the colon-list narrowing
    ships WITHOUT also widening quote-means' own verb vocabulary to
    include `includes`/`shall include`, this genuine capture is lost.
    Must remain captured. (See also `test_us_body_preamble_option_c_root_
    cause_red.py`, which pins the D-INCLUDES gap directly against
    `_B1_QUOTE_MEANS_RE`, plus the mandatory targeted-guard companion
    against a real PA construction-clause row, as live RED tests for the
    Developer's fix.)"""
    row = _positive_row("USC_T15_C1_S26a")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T15 C1 S26a (cycle-8 defining-verb regression guard)",
    )
    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "United States" in created_terms, (
        f"expected 'United States' among {sorted(created_terms)} -- this row's "
        "only genuine definition uses 'includes', not 'means'/'shall mean'; "
        "it must survive the colon-list narrowing, which requires EITHER "
        "quote-means also gaining 'includes' support or the narrowing "
        "otherwise reaching this occurrence"
    )


def test_state_ar_interstate_compact_still_captured_the_singular_purpose_trigger_gap(
    db_session, matter_with_users
):
    """`STATE_AR_T8_C8_S1_S8-8-102`: the Interstate Environmental
    Compact's real intro clause is 'For the purpose of this compact and
    of any supplemental or concurring legislation...: (a) "State" shall
    mean...'. `_B1_TRIGGER_RE` requires PLURAL 'purposes' (`For (?:the
    )?purposes of`) and never matches this row's singular 'purpose' at
    all. Recognition succeeds today only via a genuinely spurious
    '...shall be construed to [limit the right of Congress...]'
    occurrence elsewhere in the body; the compact's own 5 real 'shall
    mean' definitions (State, Interstate environment pollution,
    Government, Federal government, Signator) are reached only via
    body-wide extraction once ANY occurrence grants recognition. Must
    remain captured. (See also `test_us_body_preamble_option_c_root_
    cause_red.py`, which pins this SAME root cause directly against the
    `_B1_TRIGGER_RE` regex as a live-path RED test.)"""
    row = _positive_row("STATE_AR_T8_C8_S1_S8-8-102")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-AR",
        title="AR T8 C8 S1 S8-8-102 (cycle-8 defining-verb regression guard)",
    )
    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    expected = {"State", "Interstate environment pollution", "Government", "Federal government", "Signator"}
    assert expected <= created_terms, (
        f"expected all 5 real Interstate Environmental Compact terms among "
        f"{sorted(created_terms)} -- this row's genuine 'For the purpose of "
        "this compact' (singular) intro clause is never matched by "
        "`_B1_TRIGGER_RE` at all; recognition depends entirely on a "
        "genuinely spurious occurrence elsewhere in the body, and must "
        "still succeed after the colon-list narrowing lands"
    )


# --- 2b. NEW under P-FP re-adjudication (this Planner pass, phase-2): -----
# --- forwarding + local-means rows the cycle-8 negatives wrongly asserted -
# --- as "must not be captured". Re-authored per M-R72's ruling + this -----
# --- Planner's own read of the other 3. All GREEN today already -- no ----
# --- production code changed to make them pass. ---------------------------


def test_usc_foreign_person_and_syria_forwarding_definitions_still_captured(db_session, matter_with_users):
    """`USC_T22_C102_S9528` (RULED REJECTED BY CONSTRUCTION under P-FP,
    M-R72): every entry in the real '(d) Definitions / In this section:'
    clause reads '"X" has the meaning given such term in section NNN.NNN
    of title 31, Code of Federal Regulations...'. `has the meaning given`
    is a forwarding idiom -- GENUINE per D-MT-E1, not garbage -- so all
    three terms this row genuinely defines by reference must be captured,
    not dropped. `financial, material, or technological support` was not
    named by the manager's own two-term summary but is the SAME forwarding
    shape as the other two and is included here since it is equally
    genuine (measured, not assumed -- read directly against the real
    corpus body by this Planner). Satisfies BOTH the M-R72 re-adjudication
    (Task 1) AND M-R64's directive to extend this guard family to
    forwarding-definition rows (Task 2) in one test."""
    row = _negative_row("USC_T22_C102_S9528")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T22 C102 S9528 (cycle-8/phase-2 forwarding-definition regression guard)",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    expected = {"foreign person", "Syria", "financial, material, or technological support"}
    assert expected <= persisted.keys(), (
        f"expected all 3 real forwarding-defined terms among {sorted(persisted)} "
        "-- every entry in this real body is a genuine 'has the meaning given...in "
        "section...' forwarding pointer, GENUINE per D-MT-E1/P-FP, not a false "
        "positive; must remain captured"
    )
    assert "section 542.304 of title 31" in persisted["financial, material, or technological support"]
    assert "section 594.304 of title 31" in persisted["foreign person"]
    assert "section 542.316 of title 31" in persisted["Syria"], (
        "P-FP output is the persisted (term, definition_text) tuple: forwarding "
        "targets, not term presence alone, must be retained"
    )


def test_state_de_employer_forwarding_pointer_still_captured(db_session, matter_with_users):
    """`STATE_DE_T13_C5_SII_S513` (RULED REJECTED BY CONSTRUCTION under
    P-FP, M-R72): 'Employer' has the meaning given such term in Sec.
    4301(d) of the Internal Revenue Code of 1986 [repealed], AND includes
    any governmental entity and any labor organization..., AND includes an
    individual, partnership, association, corporation, trust, federal
    agency, state agency or political subdivision paying or obligated to
    pay income. This is not 'pure' forwarding with zero local content (as
    the old docstring claimed) -- it is a forwarding pointer PLUS
    substantive local `includes` content, doubly genuine under D-MT-E1/
    D-INCLUDES. Must remain captured."""
    row = _negative_row("STATE_DE_T13_C5_SII_S513")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-DE",
        title="DE T13 C5 SII S513 (cycle-8/phase-2 forwarding-definition regression guard)",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "Employer" in persisted, (
        f"expected 'Employer' among {sorted(persisted)} -- a genuine "
        "forwarding-plus-substantive definition (GENUINE per D-MT-E1/P-FP), "
        "not a false positive; must remain captured"
    )
    assert "4301(d) of the Internal Revenue Code of 1986" in persisted["Employer"], (
        "P-FP requires the persisted forwarding target citation, not only the term"
    )


def test_usc_institution_of_higher_education_forwarding_definition_still_captured(
    db_session, matter_with_users
):
    """`USC_T10_C303_S4093` (SUSPECT under M-R72, ADJUDICATED GENUINE by
    this Planner): the old docstring characterized the winning 'in this
    paragraph is an individual who—' occurrence's eligibility-CRITERIA
    list as the row's content and conceded 'the row's one real definition
    elsewhere is 100% forwarding' -- correctly predicting the outcome but
    treating it as disqualifying. It is not: the real body's subsection
    (h) reads '(h) Institution of Higher Education Defined.--In this
    section, the term "institution of higher education" has the meaning
    given such term in section 101 of the Higher Education Act of 1965
    (20 U.S.C. 1001).' -- confirmed live, the captured `definition_text`
    is exactly this forwarding clause, not the eligibility-criteria list.
    GENUINE under D-MT-E1/P-FP. Must remain captured; the eligibility-
    criteria occurrence that (spuriously) grants recognition is a
    RECOGNITION-path note only, not an FP (P-FP's own distinction)."""
    row = _negative_row("USC_T10_C303_S4093")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T10 C303 S4093 (cycle-8/phase-2 forwarding-definition regression guard)",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "institution of higher education" in persisted, (
        f"expected 'institution of higher education' among {sorted(persisted)} "
        "-- a genuine forwarding definition ('has the meaning given such term in "
        "section 101 of the Higher Education Act of 1965'), GENUINE per D-MT-E1/"
        "P-FP; must remain captured"
    )
    assert "section 101 of the Higher Education Act of 1965 (20 U.S.C. 1001)" in persisted[
        "institution of higher education"
    ]


def test_usc_early_approved_tribe_organization_or_consortium_still_captured(db_session, matter_with_users):
    """`USC_T42_C7_S679c` (SUSPECT under M-R72, ADJUDICATED GENUINE by
    this Planner). The old docstring described a circular USE of the term
    ('...if the tribe, organization, or consortium is an early approved
    tribe, organization, or consortium (as defined in subclause (III) of
    this clause)...') and called it 'never a means/includes idiom' -- but
    that is a DIFFERENT sentence from what was actually captured. The real
    body's subclause (III) reads: '(III) Definition of early approved
    tribe, organization, or consortium--For purposes of subclause (II) of
    this clause, the term "early approved tribe, organization, or
    consortium" means an Indian tribe, tribal organization, or tribal
    consortium that had a plan approved under section 671 of this title in
    accordance with this section for any quarter of fiscal year 2010 or
    2011.' -- confirmed live, the captured `definition_text` is a
    byte-for-byte match of this real `means` clause. GENUINE local
    definition, not circular garbage. Must remain captured."""
    row = _negative_row("USC_T42_C7_S679c")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T42 C7 S679c (cycle-8/phase-2 forwarding-definition regression guard)",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "early approved tribe, organization, or consortium" in persisted, (
        f"expected 'early approved tribe, organization, or consortium' among "
        f"{sorted(persisted)} -- the real subclause (III) 'Definition of "
        "early approved tribe, organization, or consortium' clause is a genuine "
        "local `means` definition, not the circular USE elsewhere in the body "
        "the old docstring described; must remain captured"
    )
    assert "an Indian tribe, tribal organization, or tribal consortium" in persisted[
        "early approved tribe, organization, or consortium"
    ]


def test_usc_commissioned_service_obligation_still_captured(db_session, matter_with_users):
    """`USC_T10_C953_S9448` (not flagged SUSPECT by the manager, but
    ADJUDICATED GENUINE by this Planner on direct read -- 'not measured'
    would have been a valid answer; a genuine local definition is what was
    actually found). The old docstring claimed the winning 'In this
    section' occurrence sits inside an amendment-history note describing a
    1989 amendment, and that 'commissioned service obligation... is never
    actually defined (X means Y) anywhere in this body'. That second claim
    is false: the real body's subsection (d) reads, verbatim, 'In this
    section, the term "commissioned service obligation", with respect to a
    cadet, means the period beginning on the date of the cadet's
    appointment as a commissioned officer and ending on the sixth
    anniversary of such appointment or, at the discretion of the Secretary
    of Defense, any later date up to the eighth anniversary of such
    appointment.' -- confirmed live, the captured `definition_text` is a
    byte-for-byte match of this real `means` clause. GENUINE. Must remain
    captured."""
    row = _negative_row("USC_T10_C953_S9448")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T10 C953 S9448 (cycle-8/phase-2 forwarding-definition regression guard)",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "commissioned service obligation" in persisted, (
        f"expected 'commissioned service obligation' among {sorted(persisted)} "
        "-- subsection (d)'s real 'In this section, the term \"commissioned "
        "service obligation\"... means...' clause is a genuine local definition, "
        "not amendment-history noise; must remain captured"
    )
    assert "period beginning on the date of the cadet's appointment" in persisted[
        "commissioned service obligation"
    ]
