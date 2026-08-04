"""Cycle-4 Planner tests, item 20 -- bare-term-heading definitions, the
"TRANSITO class" (sprint 2026-08-04-defs-us-pr, gates P2/P4).

## The convention (QA's biggest single cycle-3 finding, independently
## re-measured and precision-checked this cycle)

QA found PR's Vehicle & Traffic Code (`STATE_PR_TRANSITO_ART1_*`, 128
rows) is overwhelmingly `"Artículo 1.NN. <bare term>"` headings -- the
TERM ITSELF is the heading, with no "definición" word anywhere -- whose
body is a clean `[citation bracket] "Term" <idiom>...` definition. This
cycle's own re-derivation (narrow, conservative signature: heading tail
has no stem, no `;`/`,`, <=60 chars; body opens, after an optional
`[bracket]`, with a quoted term <=60 chars directly followed by a
recognized idiom) found **117 corpus-wide matches: 116 from TRANSITO
(spanning articles 1 AND 16, not just Article 1 as QA's own headline
number suggested) and 1 from the Insurance Code**
(`STATE_PR_LEY_77_1957_ART16_330`), proving the convention is not
literally TRANSITO-only even though it is overwhelmingly concentrated
there.

A BROADER generalization (any bare-term heading whose term appears
anywhere in the body's first sentence, no quote/idiom requirement) was
also measured and explicitly REJECTED as unsafe: 1,702 corpus-wide hits,
sampled overwhelmingly false (`"Artículo 1150. Orden"` -> body about
payment order, not a definition of "orden"; `"Artículo 12.
Reglamentación"` -> body about who may issue regulations, not a
definition). See the contract's cycle-4 item plan -- this is exactly the
kind of general-prose-matcher risk the director's original bucket-D
ruling rejected, and this item deliberately does NOT build it. Only the
QUOTED-lead, idiom-adjacent shape (117 rows) is in scope.

## Precision, live-verified

`extract_definitions_from_section`, called directly on the body with
only its LEADING citation bracket stripped, ALREADY returns the correct
single candidate for every real row checked (`STATE_PR_TRANSITO_ART1_25`
-> `Carril exclusivo`, `STATE_PR_TRANSITO_ART1_76` -> `Peatón`,
`STATE_PR_LEY_77_1957_ART16_330` -> `Seguro de gastos de familia por
incapacidad`) -- so, like item 19, this is substantially a
RECOGNITION/DISPATCH gap, not a fresh extraction-mechanism gap. Unlike
item 19, this needs a genuinely NEW function
(`extract_bare_term_heading_definition`) rather than
`derive_heading_from_body` alone, because the gating condition here is
about the HEADING's own shape (short, no stem, no clause delimiters) AND
requires the corroborating quoted term to match the heading's own tail --
mirroring `extract_heading_anchored_definition`'s (item 13) discipline of
"the heading anchors the term", just without requiring
`is_definitions_heading` to be true first.

`extract_bare_term_heading_definition` does not exist in `pr_profile.py`
today -- every test below is RED via `ImportError`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle4.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


def test_transito_article_1_shape_carril_exclusivo(pr_rows):
    """`STATE_PR_TRANSITO_ART1_25`: heading `"Artículo 1.25. Carril
    exclusivo"` (bare term, no stem); body `"[9 L.P.R.A § 5001 Inciso
    (23)] \\"Carril exclusivo\\" Significará..."` (citation bracket, then
    the quoted term, then the idiom)."""
    from app.definition_links.pr_profile import extract_bare_term_heading_definition

    row = pr_rows["STATE_PR_TRANSITO_ART1_25"]
    candidates = extract_bare_term_heading_definition(
        row["section_title"], row["text"], scope="local"
    )
    matching = [c for c in candidates if "Carril exclusivo" in c.terms]
    assert len(matching) == 1
    assert matching[0].scope == "local"


def test_transito_article_1_shape_peaton_short_body(pr_rows):
    """`STATE_PR_TRANSITO_ART1_76`: the shortest real shape -- heading
    `"Artículo 1.76. Peatón"`, single-sentence body, no trailing prose at
    all after the definition."""
    from app.definition_links.pr_profile import extract_bare_term_heading_definition

    row = pr_rows["STATE_PR_TRANSITO_ART1_76"]
    candidates = extract_bare_term_heading_definition(
        row["section_title"], row["text"], scope="local"
    )
    matching = [c for c in candidates if "Peatón" in c.terms]
    assert len(matching) == 1


def test_non_transito_law_shares_the_same_shape(pr_rows):
    """`STATE_PR_LEY_77_1957_ART16_330` (PR's Insurance Code, NOT
    TRANSITO): heading `"Artículo 16.330. Seguro de gastos de familia por
    incapacidad"` (bare term, no citation bracket this time), body opens
    directly `"\\"Seguro de gastos de familia por incapacidad\\" es el
    que se provee..."`. Proves the convention is a genuine SHAPE, not a
    TRANSITO-only special case."""
    from app.definition_links.pr_profile import extract_bare_term_heading_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART16_330"]
    candidates = extract_bare_term_heading_definition(
        row["section_title"], row["text"], scope="local"
    )
    matching = [c for c in candidates if "Seguro de gastos de familia por incapacidad" in c.terms]
    assert len(matching) == 1


def test_does_not_fire_when_heading_has_a_clause_delimiter():
    """Precision guard: a compound heading (`;`/`,`) is a DIFFERENT
    shape (the Civil-Code `"X; definición"` family item 13 already
    handles, or ordinary substantive prose) -- this function must not
    widen into that population. Real corpus shape mirrored, not vendored
    verbatim (the point is the gate, not a specific row)."""
    from app.definition_links.pr_profile import extract_bare_term_heading_definition

    heading = "Artículo 236. Bienes; clasificación"
    body = '"Bienes" son las cosas o derechos que pueden ser apropiables.'
    candidates = extract_bare_term_heading_definition(heading, body, scope="local")
    assert candidates == []


def test_does_not_fire_when_the_body_does_not_open_with_a_quoted_term():
    """Precision guard, grounded in the REJECTED broader generalization's
    real false-positive data (panel log): a bare-term heading whose body
    is ordinary prose about that noun, not a defining apposition, must
    stay at zero. Mirrors the real rejected hit `"Artículo 1150. Orden"`
    -> `"Si son varias las deudas que pueden compensarse, se sigue el
    orden previsto..."` (not vendored verbatim -- a structurally
    equivalent synthetic body, since the point is the gate)."""
    from app.definition_links.pr_profile import extract_bare_term_heading_definition

    heading = "Artículo 1150. Orden"
    body = "Si son varias las deudas que pueden compensarse, se sigue el orden previsto para la imputación de pagos."
    candidates = extract_bare_term_heading_definition(heading, body, scope="local")
    assert candidates == []


def test_does_not_fire_on_a_genuine_definiciones_heading():
    """Gate boundary: a heading that already IS a genuine Definiciones
    heading is item 13's domain (`extract_heading_anchored_definition`),
    not this function's -- the two must stay disjoint by construction (a
    heading with the stem is never "bare")."""
    from app.definition_links.pr_profile import extract_bare_term_heading_definition

    heading = "Artículo 3. Definiciones"
    body = '"Agencia" significa todo departamento del Gobierno.'
    candidates = extract_bare_term_heading_definition(heading, body, scope="local")
    assert candidates == []
