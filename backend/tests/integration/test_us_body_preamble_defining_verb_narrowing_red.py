"""Planner cycle-8 (sprint 2026-08-04-defs-us-preamble, D1, manager ruling
M-R59): live-path tests for the commissioned colon-list defining-verb
narrowing. M-R59's diagnosis (QA cycle-7, `-log.md`): `_b1_colon_list_
branch` only checks that the FILLER before the colon/em-dash contains no
`_B1_FORWARDING_PHRASES` -- it never checks that a genuine term:means
structure actually follows. QA measured 18% FP on shape 3 ("In this X")
and 14% on the em-dash branch (n=50 each, real corpus rows) from exactly
this gap. The commissioned remedy: require the colon-list branch's
post-colon/post-dash window to contain a recognizable defining-verb
pattern (D-INCLUDES: naive quoted-term anchor, `means`/`shall mean`/
`includes`/`shall include` all count, no tightened guard).

**Two halves, both load-bearing (this is the hard part of M-R59, not an
afterthought)**:

1. NEGATIVE (`Test*NotCaptured`) -- the real FP `act_id`s named in QA's
   cycle-7 log (`-log.md`, "2026-08-05 -- QA: cycle-7 D1..."). Each is
   RED today (something non-empty IS created, because the colon-list
   branch has no term:means check) and must go GREEN (zero created
   definitions) once the narrowing lands.

2. POSITIVE / REGRESSION-GUARD (`test_*_still_captured`) -- real rows
   that are GENUINELY, CORRECTLY captured TODAY (verified against the
   real `definition_text` output, not inferred) and that a NAIVE
   implementation of the narrowing -- one that only inspects a bounded
   text window immediately following the SPECIFIC trigger occurrence
   that won recognition -- WOULD SILENTLY DROP. These are GREEN today
   and MUST STAY GREEN; this Planner verified live (measurement script
   `measure_defining_verb_narrowing.py`, sprint scratchpad) that a
   reasonably-tuned local-window candidate (600-char search from the
   trigger match, quoted-term + means/shall mean/includes/shall include,
   80-char bounded gap) fails at least 2 of these 5 rows outright and
   that the underlying population-level risk is large (see -log.md D1
   for the full corpus-wide measurement and the escalation this cycle
   raises). Root causes, confirmed against the real body text for each
   row below:

   - `STATE_OH_T45_C4510_S4510.17` / `USC_T16_C12_S824`: the WINNING
     recognition occurrence is a genuinely spurious mid-sentence match
     (a procedural/prohibition clause, structurally identical to QA's
     confirmed FPs) that happens to occur EARLIER in a long, multi-topic
     body than the section's own real "As used in ...: (N) "Term"
     means ..." clause. Recognition succeeds today only because ANY
     successful trigger occurrence unlocks body-wide extraction
     (`extract_definitions_from_section` re-scans the WHOLE body,
     independent of which occurrence won) -- narrowing the SPECIFIC
     winning occurrence's own local window, without ALSO reaching the
     real clause, silently orphans the genuine content.
   - `STATE_PA_T15_C75_S7502`: the real defining verb ("means a
     corporation with or without capital stock...") is swallowed INTO
     the trigger match's own greedy tail (`_B1_TRIGGER_RE`'s
     `[A-Za-z0-9 .\\-]{0,30}` unit-name class has no anchor against
     consuming a following verb -- the SAME hazard this sprint's own
     D3 note flagged last cycle, "found zero false positives caused by
     it" THEN; this row shows it is a real recall hazard NOW, once a
     verb-presence check runs against text strictly AFTER the trigger
     match's end).
   - `USC_T15_C1_S26a`: the row's ONLY genuine definition uses
     `"United States" includes the several States...` -- but this
     occurrence's own shape is a comma-gap quote-means structure, not
     colon-list, and `_b1_quote_means_branch`'s own verb group
     (`_B1_QUOTE_MEANS_RE`) is `means|shall mean` ONLY -- it does not
     recognize `includes` (the SAME D-INCLUDES gap the brief warns
     about, but manifesting in the SIBLING branch M-R59 does not
     commission touching). Recognition succeeds today only via a
     SEPARATE, genuinely spurious colon-list occurrence earlier in the
     body; narrowing that occurrence without ALSO widening quote-means'
     own verb vocabulary to include `includes` orphans this genuine
     capture.
   - `STATE_AR_T8_C8_S1_S8-8-102`: the row's real intro clause is "For
     the purpose of this compact..." -- SINGULAR "purpose", never
     matched by `_B1_TRIGGER_RE` (`For (?:the )?purposes of`, PLURAL
     only). Recognition succeeds today only via a genuinely spurious
     "...shall be construed to [limit the right of Congress...]"
     occurrence elsewhere in the body; the row's own 5 real "shall
     mean" definitions (State, Interstate environment pollution,
     Government, Federal government, Signator) are reached only via
     body-wide extraction once ANY occurrence grants recognition.

These 5 rows are this Planner's OWN measurement-driven discovery (not
named in QA's cycle-7 log), found via a corpus-wide prospective run of a
concrete candidate narrowing pattern -- see `-log.md` for the full
methodology and the resulting corpus-wide trade numbers this cycle
reports to the manager.

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _negative_row(act_id: str) -> dict:
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


# --- 1. NEGATIVE: real FP rows from QA's cycle-7 log, must become uncaptured ---


def test_usc_t35_c4_s41_section_label_is_not_a_defined_term_not_captured(db_session, matter_with_users):
    """`USC_T35_C4_S41`: today's colon-list branch wrongly claims this row
    off a spurious 'in this section to recover the estimate...' occurrence
    and extraction produces a malformed candidate whose TERM is the
    literal section-label clause "SEC. 804. DEFINITION." -- not a real
    term at all. QA cycle-7 log, shape-3 FP sample."""
    row = _negative_row("USC_T35_C4_S41")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T35 C4 S41 (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']} once the colon-list "
        f"branch requires a real term:means structure in its own window; got "
        f"{result['created_definitions']!r} -- this row has no genuine local "
        "definition anywhere near its winning trigger occurrence (QA cycle-7 FP)"
    )


def test_usc_t10_c953_s9448_amendment_history_note_is_not_a_definition_not_captured(
    db_session, matter_with_users
):
    """`USC_T10_C953_S9448`: the winning 'In this section' occurrence sits
    inside an amendment-history note quoting OLD repealed text ('...
    inserted \"the term\" after \"In this section,\"' describing a 1989
    amendment). The phrase 'commissioned service obligation' appears in
    ordinary prose but is never actually defined ('X means Y') anywhere in
    this body. QA cycle-7 log, shape-3 FP sample."""
    row = _negative_row("USC_T10_C953_S9448")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T10 C953 S9448 (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']}; got "
        f"{result['created_definitions']!r} -- 'commissioned service obligation' "
        "is used in prose but never defined by a means/includes idiom anywhere "
        "in this real body (QA cycle-7 FP)"
    )


def test_usc_t22_c102_s9528_pure_forwarding_pointers_not_captured(db_session, matter_with_users):
    """`USC_T22_C102_S9528`: every entry reads '"X" has the meaning given
    such term in section NNN.NNN of title 31, Code of Federal
    Regulations...' -- a pure forwarding pointer, zero local content.
    `has the meaning given` is deliberately NOT in this narrowing's
    verb vocabulary (measured to collide with exactly this forwarding
    shape -- see -log.md) so this row must be excluded even though a
    naive `has the meaning` verb choice would wrongly keep it. QA
    cycle-7 log, shape-3 FP sample."""
    row = _negative_row("USC_T22_C102_S9528")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T22 C102 S9528 (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']}; got "
        f"{result['created_definitions']!r} -- every entry in this real body is "
        "a pure 'has the meaning given...in section...' forwarding pointer "
        "(QA cycle-7 FP)"
    )


def test_usc_t10_c303_s4093_eligibility_criteria_list_not_captured(db_session, matter_with_users):
    """`USC_T10_C303_S4093`: the winning 'in this paragraph is an
    individual who—' occurrence introduces eligibility CRITERIA
    ('(A) has not previously been awarded...', '(B) is not a citizen...'),
    not defined terms; the row's one real definition elsewhere is 100%
    forwarding. QA cycle-7 log, em-dash FP sample."""
    row = _negative_row("USC_T10_C303_S4093")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T10 C303 S4093 (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']}; got "
        f"{result['created_definitions']!r} -- an eligibility-criteria list, "
        "not a definitions block (QA cycle-7 FP)"
    )


def test_state_de_employer_forwarding_pointer_not_captured(db_session, matter_with_users):
    """`STATE_DE_T13_C5_SII_S513`: 'Employer' has the meaning given such
    term in [the Internal Revenue Code, repealed]... -- a pure forwarding
    pointer to federal law with no local content. QA cycle-7 log,
    shape-3 FP sample."""
    row = _negative_row("STATE_DE_T13_C5_SII_S513")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-DE",
        title="DE T13 C5 SII S513 (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']}; got "
        f"{result['created_definitions']!r} -- a pure forwarding pointer "
        "(QA cycle-7 FP)"
    )


def test_usc_t42_c7_s679c_circular_is_an_individual_not_captured(db_session, matter_with_users):
    """`USC_T42_C7_S679c`: 'the tribe...is an early approved tribe,
    organization, or consortium' -- a circular self-reference ('is a[n] X'),
    never a means/includes idiom, structurally the same non-definitional
    shape as the confirmed 'is an individual who—' eligibility-criteria
    FPs. QA cycle-7 log, shape-3 FP sample."""
    row = _negative_row("USC_T42_C7_S679c")
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-FED",
        title="USC T42 C7 S679c (cycle-8 defining-verb negative)",
    )
    assert result["created_definitions"] == [], (
        f"expected zero created definitions for {row['act_id']}; got "
        f"{result['created_definitions']!r} -- a circular 'is a[n] X' clause, "
        "not a definition (QA cycle-7 FP)"
    )


# --- 2. POSITIVE / REGRESSION-GUARD: genuine captures a naive narrowing --
# --- would silently drop. GREEN today; must STAY green. -------------------


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
    Must remain captured."""
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
    Must remain captured."""
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
    remain captured."""
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
