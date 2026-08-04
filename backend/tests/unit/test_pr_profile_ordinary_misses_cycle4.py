"""Cycle-4 Planner tests, item 21 -- the 17 real ordinary misses among
the 33 canonical zero-yield rows (sprint 2026-08-04-defs-us-pr, gate P4).

QA's cycle-3 verification classified all 33 canonical zero-yield rows
individually (panel log, "Classification of the 33 canonical zero-yield
rows"): 9 confirmed accepted gaps, 5 marker-precondition-gate tension
(item 22), 2 other (item 23's residue 8th row + a data-truncation
artifact already documented), and **17 genuine ordinary misses across 14
distinct, individually-verified root causes**. This file pins those 17 --
14 new fixture rows (2 of the 17 were already QA-vendored: `quiere decir`
in `STATE_PR_LEY_82_1964_ART3`, the ASCII-hyphen dash gap in
`STATE_PR_LEY_209_2016_ART2`, both already RED in `test_pr_profile_
qa_cycle4_findings.py` and not re-pinned here; 1 more,
`STATE_PR_LEY_15_1931_SEC22`, is reused unmodified from the cycle-2
fixture). Root-cause letters below match QA's own lettering in the panel
log verbatim, for cross-reference.

Every candidate count below is re-verified LIVE against the current
(unmodified) `pr_profile.py` immediately before writing each assertion --
all 14 rows below yield ZERO candidates today.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle4.json"
)
CYCLE2_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle2.json"
)


def _load(path: Path) -> dict[str, dict]:
    return {row["act_id"]: row for row in json.loads(path.read_text(encoding="utf-8"))}


@pytest.fixture()
def pr_rows():
    return _load(FIXTURE_PATH)


@pytest.fixture()
def cycle2_rows():
    return _load(CYCLE2_FIXTURE_PATH)


# --- (A) unquoted term + bare/comma idiom PER-BLOCK inside a marker loop ----


def test_a_terapista_ocupacional_comma_idiom_inside_marker_loop(pr_rows):
    """`STATE_PR_LEY_137_1968_SEC1`: `(2) Terapista Ocupacional, significa
    la persona autorizada...` -- unquoted term + comma + `significa`,
    ONE of 7 marked entries in this shape (7 real terms lost)."""
    row = pr_rows["STATE_PR_LEY_137_1968_SEC1"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Terapista Ocupacional" in c.terms for c in candidates)


def test_a_universidad_bare_idiom_no_comma_inside_marker_loop(pr_rows):
    """`STATE_PR_LEY_1_1966_ART14`: `(1) Universidad Significará la
    Universidad de Puerto Rico.` -- unquoted term + SPACE + idiom, no
    comma at all (10 real terms lost in this one row)."""
    row = pr_rows["STATE_PR_LEY_1_1966_ART14"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Universidad" in c.terms for c in candidates)


def test_a_junta_comma_idiom_second_confirming_row(pr_rows):
    """`STATE_PR_LEY_97_1971_SEC1`: `(3) Junta, significa la Junta
    Examinadora de Tecnólogos Dentales...` -- same A shape, different
    law (6 real terms lost)."""
    row = pr_rows["STATE_PR_LEY_97_1971_SEC1"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Junta" in c.terms for c in candidates)


# --- (B) same shape, single no-marker whole-body block, no quote anywhere --


def test_b_campeon_no_marker_no_quote_whole_body(pr_rows):
    """`STATE_PR_LEY_154_2004_ART2`: `Campeón o Ex Campeón significa todo
    boxeador profesional...` -- the ENTIRE body is one unmarked,
    unquoted term-then-idiom sentence."""
    row = pr_rows["STATE_PR_LEY_154_2004_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Campeón o Ex Campeón" in c.terms for c in candidates)


def test_b_materia_prima_se_entendera_por_no_marker(pr_rows):
    """`STATE_PR_MUNICIPAL_ART7_100`: `...se entenderá por materia prima
    no solo los productos...` -- unquoted `se entenderá por X` shape,
    single unmarked block."""
    row = pr_rows["STATE_PR_MUNICIPAL_ART7_100"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("materia prima" in c.terms for c in candidates)


# --- (C) "se entiende por"/"se entenderá por" not a recognized pre-quote cue


def test_c_reused_cycle2_row_still_zero_yield(cycle2_rows):
    """`STATE_PR_LEY_15_1931_SEC22`, reused unmodified from the cycle-2
    fixture (no new vendoring) -- still zero-yield, confirming QA's
    classification did not silently regress."""
    row = cycle2_rows["STATE_PR_LEY_15_1931_SEC22"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert candidates == []


def test_c_aditamento_especial_se_entendera_por_quoted_term(pr_rows):
    """`STATE_PR_LEY_45_1935_ART36`: `Se entenderá por "aditamento
    especial", fajas ortopédicas, muletas...` -- idiom BEFORE the quoted
    term (inverted order from the ordinary term-then-idiom shape); `se
    entenderá por`/`se entiende por` are not recognized pre-quote cues in
    `_PRE_QUOTE_IDIOM_CUE_RE` today."""
    row = pr_rows["STATE_PR_LEY_45_1935_ART36"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("aditamento especial" in c.terms for c in candidates)


# --- (D)/(E) alt-term joiner "y" (not "o"); plural "los términos" ----------


def test_d_e_persona_y_personas_plural_lead_in_y_joiner(pr_rows):
    """`STATE_PR_LEY_77_1964_ART1`: `Los términos "persona" y "personas"
    se usan en esta ley...` -- stacks TWO gaps: (D) the alt-term joiner
    `" y "` is not recognized (only `" o "` is, per the comma-idiom/dash
    patterns' existing optional-second-quoted-phrase allowance) and (E)
    the plural lead-in `"Los términos"` is not a recognized pre-quote cue
    (only singular `"el término"` is)."""
    row = pr_rows["STATE_PR_LEY_77_1964_ART1"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("persona" in c.terms for c in candidates)


# --- (H) quoted term + PERIOD + idiom, no comma/dash -----------------------


def test_h_asegurador_quoted_term_period_then_idiom(pr_rows):
    """`STATE_PR_LEY_77_1957_ART26_030`: `(a) "Asegurador". Significa
    cualquier asegurador...` -- quoted term, then a bare PERIOD, then the
    idiom -- no comma, no dash. None of `_QUOTED_TERM_*_RE` expects a
    block to start `"Term". Idiom...` (only `"Term", idiom` or `"Term"
    idiom` directly, no intervening period)."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART26_030"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Asegurador" in c.terms for c in candidates)


# --- (I) quoted term + comma + bare apposition, NO idiom word at all ------


def test_i_administracion_comma_bare_apposition_no_idiom_word(pr_rows):
    """`STATE_PR_LEY_55_1996_ART2`: `(a) "Administración", la
    Administración de Vivienda Pública de Puerto Rico.` -- quoted term +
    comma + a bare noun-phrase apposition, with NO idiom verb
    (`significa`/`es`/etc.) anywhere in the block at all -- outside
    `_QUOTED_TERM_COMMA_IDIOM_RE`'s idiom-lookahead requirement entirely
    (9 real terms lost in this one row, all sharing this exact shape)."""
    row = pr_rows["STATE_PR_LEY_55_1996_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Administración" in c.terms for c in candidates)


# --- (J) 60-char lead-in bound too short when a citation bracket precedes --


def test_j_ex_campeon_citation_bracket_pushes_lead_in_past_the_bound(pr_rows):
    """`STATE_PR_LEY_271_2004_ART2`: `[15 L.P.R.A § 567a Inciso (a)] Para
    propósitos de esta Ley, el término "ex-campeón" significará...` --
    the citation-bracket prefix pushes the real lead-in past
    `_MAX_LEAD_IN_LEN` (60 chars; measured real length here is longer)."""
    row = pr_rows["STATE_PR_LEY_271_2004_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("ex-campeón" in c.terms for c in candidates)


# --- (K) multi-term list, no markers, lead-in too short for the full intro -


def test_k_ataque_multi_term_no_marker_long_intro_sentence(pr_rows):
    """`STATE_PR_LEY_55_1963_SEC3`: `Los siguientes términos y frases
    tendrán los significados que a continuación se expresan, excepto
    donde el contexto de esta ley claramente indique otra cosa. "Ataque"
    significará...` -- 3 real quoted-term entries chained with NO
    markers at all between them (only sentence boundaries), and the
    intro sentence before the FIRST quoted term is far longer than any
    lead-in bound."""
    row = pr_rows["STATE_PR_LEY_55_1963_SEC3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Ataque" in c.terms for c in candidates)


# --- (L) dash-shaped single-entry lead-in, dispatch only recognizes bare ---


def test_l_productor_dash_lead_in_not_recognized_by_dispatch(pr_rows):
    """`STATE_PR_LEY_77_1957_ART9_020`: `Productor. — Es la persona
    que...`, with an incidental `(1)(2)(3)` duties sub-list (same shape
    the cycle-2 dispatch fix already protects for `STATE_PR_LEY_
    77_1957_ART9_040`) -- but THIS row's lead-in is DASH-shaped
    (`"Término. — Es..."`), and `_UNQUOTED_BARE_IDIOM_TERM_RE` (the
    dispatch's own lead-in check) only recognizes a BARE copulative
    shape (`"Término es..."`, no dash), so the whole body wrongly takes
    the markers path instead of being treated as one single entry."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART9_020"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Productor" in c.terms for c in candidates)


# --- (M) inverted idiom order "Por X se entenderá Y" -----------------------


def test_m_maestro_inverted_por_x_se_entendera_y_order(pr_rows):
    """`STATE_PR_LEY_34_1966_ART10`: `(a) Por Maestro de instrucción
    pública se entenderá todo el personal docente...` -- the term
    follows "Por" and PRECEDES the idiom verb "se entenderá", with the
    actual definition only starting AFTER the idiom -- an inverted
    "Por TERM se entenderá DEFINITION" order no existing pattern
    expects."""
    row = pr_rows["STATE_PR_LEY_34_1966_ART10"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert any("Maestro de instrucción pública" in c.terms for c in candidates)


# --- (N) deeply-nested subsection quoted-term shapes, lower confidence -----


def test_n_periodo_de_transicion_deeply_nested_subsection(pr_rows):
    """`STATE_PR_RENTAS_SEC1115_09`: `el término "período de transición
    después de la terminación" significa -` deep inside subsection
    (b)(1) of a multi-level `(a)/(b)/(c)` structure. QA's own framing:
    "lower confidence" than the other 13 -- pinned at FLOOR granularity
    only (>=1 real term from this row), not an exact full-candidate-list
    assertion, since the right mechanism (deep-nesting-aware splitting
    vs. a simpler lead-in widening) is a genuine Developer design
    choice."""
    row = pr_rows["STATE_PR_RENTAS_SEC1115_09"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {t for c in candidates for t in c.terms}
    assert any(
        term in all_terms
        for term in (
            "período de transición después de la terminación",
            "miembro de una familia",
        )
    )
