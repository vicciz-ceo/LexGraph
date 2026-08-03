"""RED unit tests for the family-4 heading-variants registry module (sprint
2026-08-04-defs-us-headings, gate U1 "every named heading variant is
captured", gate U5 "zero false positives").

**Contract this file locks the Developer to** (per the seam published by
`claude/defs-core-scope` @ `9272f6e`, `## Seam spec (published)` -> "Seam 2
-- per-jurisdiction rule registry"):

  - New file: `backend/app/definition_links/rules/us_heading_variants.py`.
  - It exposes a PUBLIC module-level function
    `matches_heading_variant(heading: str) -> bool` (this is the Planner's
    own naming choice for the callable the seam requires -- the seam only
    fixes the TYPE, `Callable[[str], bool]`, not the name -- documented
    here so it is one contract, not a guess the Developer has to make).
  - At import time, it registers exactly once via:
    `register_heading_rule(HeadingRule(jurisdiction_codes=("US-*",),
    matches=matches_heading_variant))` (see the companion registry-
    integration test).
  - It implements its OWN heading normalization -- it must NOT import or
    reuse `us_profile.py`'s private `_SECTION_LABEL_RE`,
    `_SECTION_NUMBER_TOKEN_RE`, or `_PRECEDING_EXCLUSION_WORDS` (ruling
    H-R4); those stay untouched, this module is self-contained.

**RULE SET this module must implement** (Planner's recommendation --
evidence and per-rule recall/precision numbers are in the Planner's report
to the manager and in `backend/tests/fixtures/us_statutes/README.md`, not
repeated here):

  - R-SEC: strip a `Sec.`/`Secs.`/`Art.`/`Article` (case-insensitive,
    optional trailing `.`) section-label prefix (baseline only accepts the
    spelled-out word `Section`), THEN apply the same first-word/last-word
    (with preposition-exclusion) decision baseline uses.
  - R-MID: any TAIL TOKEN (tokenized the same way -- whitespace or
    `-`/en-dash/em-dash/`:`/`;`/`,` -- as baseline's own tail tokenizer) is
    EXACTLY `Definition`/`Definitions` (case-insensitive, whole token),
    at any position EXCEPT the very first or very last (those are
    baseline's job already) -- and the token immediately preceding it is
    not a preposition/function word (same exclusion-word semantics as
    baseline, own copy). NOTE: a prototyped R-COLON rule ("strip a `:`-
    separated number prefix") was measured against the full 22,228-row
    miss pool and dropped -- ALL 31 of its target rows are ALSO captured
    by R-MID alone (0 unique value) -- do not build R-COLON.
  - R-VERB-bare: the LAST tail token is exactly `defined` (case-
    insensitive).
  - R-VERB-extended: the token `defined` (word-boundary) is immediately
    followed by `;` or `:` (optional whitespace) and then more text.
  - R-TRUNC: the LAST tail token, lower-cased, is exactly one of
    `{"defin", "defini", "definit", "definiti", "definitio"}` (a strict
    prefix of "definitions", length >= 5, verified against
    `/usr/share/dict/words` on the Planner's machine to NOT be real
    English words) and sits at the very end of the (period-stripped)
    title.
  - R-MISSPELL: the LAST tail token matches
    `^(defintions?|definitons?|defintion)$` (case-insensitive).

Fixture: REAL rows, all 24 original columns, values unmodified, vendored
2026-08-04 -- `backend/tests/fixtures/us_statutes/us_heading_variants_rows.json`.
See that file's sibling `README.md` ("`us_heading_variants_rows.json` --
sprint 2026-08-04-defs-us-headings (family 4)") for full provenance, the
live re-verification of every counterfactual, and why each row was picked.

RED signal (proven by the Planner before the Developer starts -- see the
Planner's report): `ModuleNotFoundError: No module named
'app.definition_links.rules'` -- the seam's registry package does not
exist in this worktree yet (core sprint `claude/defs-core-scope` has not
merged). This is EXPECTED per the sprint contract's Coordination note
("merge after core") -- these tests go green once (a) core merges/rebases
in, AND (b) the Developer creates this module. Both are needed; neither
alone is sufficient.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_heading_variants_rows.json"
)
QA_CYCLE3_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "qa_cycle3_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _title(act_id: str) -> str:
    return _load_rows()[act_id]["section_title"]


# --- Positive: each candidate rule, on its real vendored row ---------------


def test_r_sec_recognizes_abbreviated_sec_label_before_definitions():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_CT_T42a_C9_S42a-9-102")
    assert heading == "Sec. 42a-9-102. Definitions and index of definitions."
    assert matches_heading_variant(heading) is True, (
        "R-SEC: baseline's _SECTION_LABEL_RE only accepts the spelled-out word "
        "'Section', not the abbreviation 'Sec.' -- this real CT UCC heading is "
        "a baseline miss that R-SEC's own label-strip must recover"
    )


def test_r_mid_recognizes_definitions_as_a_non_first_non_last_tail_token():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_MO_C334_S334.043")
    assert heading == "334.043 Reciprocity — definitions — procedure — fees."
    assert matches_heading_variant(heading) is True, (
        "R-MID: 'definitions' is neither the first nor last tail token here "
        "(sandwiched between 'Reciprocity' and 'procedure'/'fees') -- baseline's "
        "first-word and last-word rules both miss it; a real dossier-cited "
        "family-4 example"
    )


def test_r_mid_recovers_colon_numbered_heading_without_a_dedicated_colon_rule():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_DC_T28_C_S28:2A-103")
    assert heading == "§ 28:2A-103. Definitions and index of definitions."
    assert matches_heading_variant(heading) is True, (
        "R-MID: DC's UCC title-colon-chapter numbering ('28:2A-103') defeats "
        "baseline's first-word rule (the residual ':2A-103.' prefix blocks it), "
        "but 'Definitions' still lands as a genuine mid-token once the number "
        "fragments are tokenized out -- proves R-MID subsumes what a dedicated "
        "R-COLON rule would have done (measured and dropped, see module docstring)"
    )


def test_r_mid_recognizes_scope_unit_naming_heading():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_AK_T13_C13.06_S13.06.050")
    assert heading == "General definitions for AS 13.06 \x97 AS 13.36."
    assert matches_heading_variant(heading) is True, (
        "R-MID: 'General' precedes 'definitions' so baseline's first-word rule "
        "never fires; this is also the sprint's chosen U2 scope-seam worked "
        "example (see Planner's report) -- heading recognition is asserted "
        "here, scope correctness is a SEPARATE, escalated question"
    )


def test_r_trunc_recognizes_colorado_source_data_truncated_title():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_CO_T2_A3_P1_S2-3-110.5")
    assert heading.endswith("definitio")
    assert matches_heading_variant(heading) is True, (
        "R-TRUNC: Colorado's source-data character cap truncates the title "
        "mid-word ('...definitio'); 'definitio' is a verified non-English-word "
        "strict prefix of 'definitions' and sits at the very end of the title"
    )


def test_r_trunc_does_not_require_body_to_also_parse():
    """Zero-yield companion to the row above -- proves R-TRUNC is a pure
    HEADING rule (ruling H-R1): it must fire on the truncated title even
    when the body itself yields nothing extractable today."""
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_CO_T22_A33_P1_S22-33-106.3")
    assert heading.endswith("definitio")
    assert matches_heading_variant(heading) is True


def test_r_verb_bare_recognizes_words_and_phrases_defined():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_WI_C939_S939.22")
    assert heading == "Words and phrases defined."
    assert matches_heading_variant(heading) is True, (
        "R-VERB-bare: last tail token is exactly 'defined' -- the sprint "
        "mandate's own cited verb-form example, and (per the Planner's live "
        "re-check) one of the rare verb-form headings whose body ALSO parses "
        "today (27 real candidates) -- see the end-to-end test"
    )


def test_r_verb_bare_recognizes_nevada_dominant_cluster_shape():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_NV_T58_C706_S706.074")
    assert heading == "“Hazardous material” defined"
    assert matches_heading_variant(heading) is True, (
        "R-VERB-bare: representative of NV's 8,829-row bare-verb-form cluster "
        "(52% of the entire family-4 miss pool) -- heading recognition is "
        "correct here even though the body yields 0 candidates today "
        "(markers-family hand-off, ruling H-R1, do not expect extraction)"
    )


def test_r_verb_extended_recognizes_defined_before_semicolon_clause():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_AL_T25_C9_S25-9-276")
    assert "Defined;" in heading
    assert matches_heading_variant(heading) is True, (
        "R-VERB-extended: 'Defined' is immediately followed by ';' and more "
        "clause text -- the census's 'verb-form extended' shape"
    )


def test_r_misspell_recognizes_defintions():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title("STATE_CT_T36a_C668_S36a-636")
    assert heading == "Sec. 36a-636. Defintions."
    assert matches_heading_variant(heading) is True, (
        "R-MISSPELL: 'Defintions' (missing the second 'i') -- also proves this "
        "row is captured despite ALSO having an abbreviated 'Sec.' label, "
        "because the misspelling defeats R-SEC's own first/last-word check too "
        "(isolates R-MISSPELL from R-SEC, no rule-overlap ambiguity)"
    )


# --- Negative: must stay False under every family-4 rule -------------------


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_TX_Cfa_C101_S101.001",
            "verified TRUE NEGATIVE: real body defines zero terms, it is a "
            "precedence clause ('APPLICABILITY OF DEFINITIONS')",
        ),
        (
            "STATE_AZ_T33_C6.1_A1_S821",
            "preposition-exclusion guard: 'from' immediately precedes "
            "'definition' ('Exemption from definition')",
        ),
        (
            "STATE_AR_T23_C64_S1_S23-64-103",
            "preposition-exclusion guard: 'to' immediately precedes "
            "'definitions' ('Exceptions to definitions')",
        ),
        (
            "STATE_NY_ANPC_A4_S406",
            "'... as defined in ...' verb-form guard: 'defined' is followed by "
            "' in ', not ';'/':' directly, and is nowhere near the last token",
        ),
        (
            "STATE_AK_T32_C32.06_S32.06.406",
            "morphology guard: 'definite' is not 'definition(s)'/'defined' as "
            "an exact token",
        ),
        (
            "STATE_TX_Cgv_C2001_S2001.175",
            "morphology guard: 'UNDEFINED' (ALL-CAPS), not an exact "
            "'definition(s)'/'defined' token",
        ),
    ],
)
def test_negative_guards_stay_false(act_id, reason):
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    heading = _title(act_id)
    assert matches_heading_variant(heading) is False, f"{heading!r}: {reason}"


def test_negative_guard_bare_section_placeholder_stays_false():
    """Reuses the existing real IL 'Section 15' placeholder row (ruling
    R9/R12) already committed in qa_cycle3_rows.json -- no re-vendoring
    needed. A bare 'Section N' with no descriptive text carries no
    definitions signal under any family-4 rule either."""
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    rows = json.loads(QA_CYCLE3_FIXTURE_PATH.read_text(encoding="utf-8"))
    row = {r["act_id"]: r for r in rows}["STATE_IL_C325_A7_S15"]
    assert row["section_title"] == "Section 15"
    assert matches_heading_variant(row["section_title"]) is False


def test_negative_guard_dossier_synthetic_repeal_of_definitions():
    """The dossier's own cited false-positive-hazard example. No real row
    with this EXACT shape was found in the live corpus census (Planner
    searched all 52 files) -- real corpus rows with the same grammatical
    shape (preposition immediately before Definitions) are covered by the
    real AZ/AR rows above; this one synthetic string, drawn directly from
    the sprint contract's own Mandate text, is kept in addition because it
    is the literal phrase the contract asks to be guarded."""
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    assert matches_heading_variant("Repeal of definitions") is False


def test_negative_guard_dossier_synthetic_as_defined_in():
    from app.definition_links.rules.us_heading_variants import matches_heading_variant

    assert matches_heading_variant("Terms as defined in section 5") is False
