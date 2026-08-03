"""Sprint 2026-08-04-defs-us-scoped-inline (Planner, D5, target 1: pure rule
module). RED today with `ModuleNotFoundError` -- see
`test_us_scoped_inline_rules_trigger_axis.py`'s module docstring for the
full public-API contract this sprint pins.

This file: the BODY axis -- the shape that follows a recognized trigger.
Real corpus evidence (Planner's 2026-08-04 D1 inventory): `(N) "X" means`,
`(letter) "X" means`, bare `"X" means`, `the term "X" includes/means`,
`"X" shall mean`, `"X" has the meaning` (including the real cross-reference
shape `"X" has the SAME meaning as in section N`), `"X" includes`,
colon-then-numbered-list, colon-then-lettered-list (including Oregon's real
capital-letter `(A)(B)` convention). Also pins the two "must NOT
over-split" cases that make this the hardest part of the extraction: nested
roman-numeral sub-clauses inside one lettered entry, and a single term's
OWN numbered/lettered elaboration list (no new quoted term at each item) --
both must stay part of ONE definition's `definition_text`, never spawn
spurious extra (unnamed) entries. And the one body shape proven NOT to
belong here at all: a bare, unquoted cross-reference ("...is the same as
defined in Section N") carries no quoted term and no recognized defining
idiom, so it must yield nothing (covered in
`test_us_scoped_inline_rules_negative_controls.py`, not here).
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def _terms(candidates) -> set[str]:
    out = set()
    for c in candidates:
        out.update(c.terms)
    return out


def _by_term(candidates, term):
    hits = [c for c in candidates if term in c.terms]
    assert hits, f"{term!r} not found among extracted terms {sorted(_terms(candidates))!r}"
    return hits[0]


# --- bare "X" means (single entry, no numbering) ----------------------------


def test_bare_quote_means_single_entry():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T20A_S20A_2_204"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    vrf = _by_term(candidates, "voter registration form")
    assert vrf.scope == "local"
    assert "qualifying form" in vrf.definition_text


def test_bare_quote_means_subsection_scope_maine():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ME_T38_C3_S464"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    du = _by_term(candidates, "designated use")
    assert du.scope == "subsection"


def test_bare_quote_means_subsection_scope_oregon():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_OR_T22_C238_S238.300"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    nym = _by_term(candidates, "number of years of membership")
    assert nym.scope == "subsection"


# --- "X" shall mean ----------------------------------------------------------


def test_quote_shall_mean_idiom():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T59_C111_A5_S59-111-310"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    tuition = _by_term(candidates, "tuition")
    assert "credit hour" in tuition.definition_text


# --- "X" has the meaning / has the SAME meaning as (real OH cross-ref) -----


def test_quote_has_the_meaning_idiom_including_same_meaning_variant():
    """`STATE_OH_T33_C3313_S3313.906`: `"“digital learning” has the
    same meaning as in section 3301.079..."` -- the term IS locally
    scoped to this section even though its substantive meaning is imported
    by reference (same precedent as the existing captured-heading pathway:
    `extract_definitions_from_section` already captures `"X" has the
    meaning specified in..."`-shaped entries verbatim, letting Stage 4's
    `detect_cross_law_derivations` handle the reference separately -- this
    rule module follows the identical division of labor, not a special
    case of its own)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_OH_T33_C3313_S3313.906"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    dl = _by_term(candidates, "digital learning")
    assert dl.scope == "local"
    assert "3301.079" in dl.definition_text


# --- "X" includes (TX) -------------------------------------------------------


def test_quote_includes_idiom():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TX_Cwa_C55_S55.047"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    city = _by_term(candidates, "city")
    assert "town" in city.definition_text


def test_the_term_quote_includes_idiom():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TN_T34_C6_S34-6-302"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    parent = _by_term(candidates, "parent")
    assert "legal guardian" in parent.definition_text


# --- colon-then-numbered-list / colon-then-lettered-list (multi-entry) -----


def test_colon_then_numbered_list_four_entries():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T37_C6_S37-6-402"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert {"Contested case", "License", "Licensing", "Party"} <= _terms(candidates)


def test_colon_then_lettered_list_oregon_capital_letters():
    """`STATE_OR_T59_C825_S825.224`: `"(b) As used in this subsection:
    (A) “Overcharges” means..."` -- Oregon's real capital-letter
    `(A)(B)` marker convention (not lowercase `(a)(b)`)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_OR_T59_C825_S825.224"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    overcharges = _by_term(candidates, "Overcharges")
    assert overcharges.scope == "subsection"


# --- MUST NOT over-split: nested roman-numeral sub-clauses -----------------


def test_nested_roman_numeral_subclauses_stay_inside_their_own_entry():
    """`STATE_UT_T53G_S53G_10_402`: `"(1) As used in this section: (a)
    “LEA governing board” means... (b) “Refusal skills” means
    instruction: (i)...(ii)...(iii)...(iv)... (c) “Situational
    awareness” means..."` -- three genuine top-level entries
    ((a)/(b)/(c), each with its own new quoted term), where entry (b)'s
    OWN definition contains four roman-numeral sub-clauses. Those
    roman-numeral markers are nested INSIDE (b)'s entry, one level deeper
    than the (a)/(b)/(c) split -- they must never be split out as their
    own (unnamed) candidates, and (b)'s definition_text must carry the
    full nested content through to (c), not truncate at the first "(i)"."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T53G_S53G_10_402"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = _terms(candidates)
    assert {"LEA governing board", "Refusal skills", "Situational awareness"} <= terms

    refusal = _by_term(candidates, "Refusal skills")
    assert refusal.scope == "local"
    # the nested (iv) content must survive inside THIS entry's text
    assert "criminally prohibited" in refusal.definition_text
    # none of the roman-numeral markers leaked out as their own bogus terms
    for bogus in ("i", "ii", "iii", "iv"):
        assert bogus not in terms


# --- MUST NOT over-split: a single term's own elaboration list -------------


def test_definitions_own_numbered_elaboration_list_is_not_split_into_new_entries():
    """`STATE_MT_T23_C5_P8_S23-5-801`: `"As used in this part, a
    “fantasy sports league” means a gambling activity conducted in
    the following manner: (1)... (2)... (3)..."` -- ONE term
    ("fantasy sports league"), whose own definition elaborates via a
    numbered list with NO new quoted term introduced at (1)/(2)/(3). This
    must extract as exactly one candidate, not spuriously split into
    unnamed per-item entries the way a genuine multi-entry list
    (`(1) "X" means...(2) "Y" means...`) correctly would."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_MT_T23_C5_P8_S23-5-801"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    matches = [c for c in candidates if "fantasy sports league" in c.terms]
    assert len(matches) == 1
    assert matches[0].scope == "part"
    assert "entrance fee" in matches[0].definition_text


def test_shared_clause_own_numbered_list_not_split_tennessee():
    """`STATE_TN_T36_C5_S36-5-910`: `"“financial institution” shall
    mean: (1) A depository institution... (2)... (3)... (4)..."`
    -- same shape as the Montana case above, different state/idiom
    (`shall mean` instead of `means`). This row's raw text is also
    duplicated verbatim within the same `text` field (a real, observed
    corpus data-quality artifact, not injected) -- assertions use
    membership, never an exact candidate count, for exactly this reason."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TN_T36_C5_S36-5-910"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert "financial institution" in _terms(candidates)
    fi = _by_term(candidates, "financial institution")
    assert fi.scope == "part"


def test_shared_clause_own_list_not_split_vermont():
    """`STATE_VT_T11C_C7_S701`: `"“marketing contract” means a
    contract...: (1) requiring... or (2) authorizing..."` --
    same "own elaboration list, no new quoted term per item" shape again,
    via the bare `In this article` trigger."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T11C_C7_S701"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    matches = [c for c in candidates if "marketing contract" in c.terms]
    assert len(matches) == 1


# --- multi-scope-in-one-body (the hardest correctness property) ------------


def test_multiple_terms_in_one_body_each_keep_their_own_scope():
    """`STATE_VT_T3_C45_S2291` defines THREE terms in one section body
    under THREE trigger occurrences naming TWO DIFFERENT scope units
    (title, then chapter, then chapter again) -- scope must be resolved
    per-entry from ITS OWN nearest trigger, never defaulted from the
    first trigger found in the body."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T3_C45_S2291"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    by_scope = {c.terms[0]: c.scope for c in candidates if c.terms}
    assert by_scope.get("life-cycle costs") == "title"
    assert by_scope.get("State facilities") == "chapter"
    assert by_scope.get("State fleet") == "chapter"
