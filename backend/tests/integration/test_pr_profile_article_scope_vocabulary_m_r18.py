r"""Planner (M-R18, sprint 2026-08-04-defs-us-pr) -- audits the
ARTICLE-scope trigger set (`_LOCAL_TRIGGER_PHRASE_ALTERNATION`, feeding
`extract_local_definitions` via the registered `ScopeTriggerRule`) the same
way job 1 closed the chapter-scope set, per the manager's own instruction
("the same question should be asked of the article-scope trigger set").

## Method and headline result (full derivation in the panel log)

Swept all 23,003 NON-canonical bodies (the `extract_local_scope_definitions`
population) for `este Artículo` / `esta Sección`, unanchored (mirrors
`_LOCAL_TRIGGER_RE`'s own `.finditer` discipline -- no first-sentence
anchor on this path), independent of the shipped alternation (P-R7).
5,098 raw hits. Restricted to the SAME broad grammatical family already
confirmed genuine for Capítulo (`(?:A|Para)\s+(?:los\s+)?(?:fines|efectos|
prop[oó]sitos)\s+de\s+(?:este|esta)\s+(?:Artículo|Sección)`): **247
non-canonical bodies** contain at least one such phrase.

Calling the REAL `pr_profile.extract_local_definitions` directly (not a
re-derived regex -- avoids exactly the footer-stripping discrepancy this
sprint's own traps warn about) on each: **229 of the 247 produce ZERO
candidates today**, despite a grammatically genuine trigger phrase being
present. This is materially larger than the chapter-scope gap (6 rows).

Simulating a fix that widens ONLY the phrase alternation (both
prepositions, "los" optional, both unit words) against the SAME unmodified
capture-group tails (copied verbatim, not reimplemented): **+11 rows / +12
candidates**. Additionally allowing `"el término "` (and its accented
variant) as a THIRD quoted lead-in -- alongside the 2 already shipped
(`"se define "` / `"la frase "`) -- a real, common shape found by hand-
reading (e.g. `"...el término "año permitido" significa..."`): **+56 more
rows**. Combined, purely vocabulary-and-lead-in fix: **67 of the 229 rows
(≈29%)** -- closed here.

**The Sección unit word is the single biggest component: currently
ZERO Sección coverage at all** (`_LOCAL_TRIGGER_PHRASE_ALTERNATION` names
only "Artículo"). Confirmed genuine, not incidental: PR's SEC-numbered
laws (`Código de Rentas Internas`, `Código de Incentivos`, and several
`Ley`s that number sections rather than articles) use "esta Sección"
exactly the way ART-numbered laws use "este Artículo" (e.g.
`STATE_PR_LEY_83_1963_SEC3`: '"Para efectos de esta Sección, "unidad"
será..."'). Sección "deserves the same treatment" as Artículo, per the
brief's own question -- confirmed by measurement, not assumed.

## What stays OPEN (escalated, not guessed at here)

**162 of the 229 rows remain uncaptured** even after the vocabulary+
lead-in fix. Hand-read a diverse ~26-row sample across every shape bucket:
this residue is a MIX of two different things, not one:

  1. A genuinely DIFFERENT structural shape -- a trigger phrase introducing
     a whole colon-delimited, numbered MULTI-TERM list (e.g.
     `STATE_PR_RENTAS_SEC1052_04`: "(a) Definiciones.- Para fines de esta
     sección los siguientes términos... (1)...(2)..."), i.e. a
     mini-canonical-section embedded inside an ordinary article. The
     single-inline-clause shape `_LOCAL_TRIGGER_RE`/`_LOCAL_TRIGGER_
     UNQUOTED_RE` are built for cannot represent this; it would need
     something closer to the canonical extractor's own marker-based
     splitting. A real fix, but a DESIGN decision (how to split, whether
     to reuse `_split_into_numbered_blocks`), not a vocabulary tweak --
     escalated.
  2. Genuinely NOT a definition at all -- the trigger phrase introduces a
     PROCEDURAL or substantive rule, not a term (e.g.
     `STATE_PR_LEY_171_2018_SEC31`: "A los fines de este Artículo, el
     Departamento establecerá mediante reglamento, el procedimiento...").
     Correctly uncaptured; not a gap.

No further split of the 162 between these two classes was measured (bounded
pass; would need per-row structural classification, itself the kind of
"guess" the brief says to escalate rather than force). Named on the
residual ledger with full evidence for the manager/program to route.

## Fixtures

`pr_sample_rows_cycle12.json` (shared with the chapter-scope files) -- 4
REAL rows, byte-verified sha256-identical against a fresh, independent read
of the pinned snapshot (`301000fc3465374ee0f23c3c6953a8a861e95cad`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(name: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows_cycle12():
    return _load("pr_sample_rows_cycle12.json")


def _extract(profile, row):
    return profile.extract_local_scope_definitions(
        row["text"], article_number=row["section_number"], chapter=row["chapter"]
    )


def test_get_profile_us_pr_captures_a_definition_gated_by_esta_seccion_live(pr_rows_cycle12):
    """`STATE_PR_LEY_83_1963_SEC3` (heading "Sección 3. Penalidades" -- NOT
    a Definiciones section, so this is the `extract_local_scope_
    definitions` path): '...Para efectos de esta Sección, "unidad" será
    aquel artificio...' -- a clean single quoted definition, gated on
    "esta Sección" alone. `_LOCAL_TRIGGER_PHRASE_ALTERNATION` names only
    "Artículo" today; Sección support is entirely missing. RED live."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle12["STATE_PR_LEY_83_1963_SEC3"]
    profile = get_profile("US-PR")

    candidates = _extract(profile, row)
    terms = {t for c in candidates for t in c.terms}
    assert "unidad" in terms, f"expected 'unidad' among captured terms, got {terms!r}"


def test_get_profile_us_pr_captures_a_definition_gated_by_esta_seccion_with_el_termino_lead_in_live(
    pr_rows_cycle12,
):
    """`STATE_PR_RENTAS_SEC1081_02`: '(a) A los efectos de esta sección, el
    término "Cuenta de Retiro Individual" significará...' -- a compound
    gap: Sección is unsupported AND "el término " before an opening quote
    is not one of the 2 shipped lead-ins (only "se define "/"la frase ").
    RED live for both reasons at once, on a real row."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle12["STATE_PR_RENTAS_SEC1081_02"]
    profile = get_profile("US-PR")

    candidates = _extract(profile, row)
    terms = {t for c in candidates for t in c.terms}
    assert "Cuenta de Retiro Individual" in terms, (
        f"expected 'Cuenta de Retiro Individual' among captured terms, got {terms!r}"
    )


def test_get_profile_us_pr_captures_a_definition_gated_by_para_efectos_no_los_este_articulo_live(
    pr_rows_cycle12,
):
    """`STATE_PR_LEY_77_1957_ART40_050`: '(c) Para efectos de este
    Artículo, "causa" incluye, pero no se limita a...' -- "Para efectos"
    (no "los") is not one of the 3 shipped phrases (`A los fines`/`A los
    efectos`/`Para propósitos de este Artículo`), the SAME character of
    gap already fixed for Capítulo's 5th shape. RED live on a real row
    that isolates this gap alone (already-shipped unit word, already-
    shipped lead-in discipline -- only the preposition/"los" combination
    is missing)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle12["STATE_PR_LEY_77_1957_ART40_050"]
    profile = get_profile("US-PR")

    candidates = _extract(profile, row)
    terms = {t for c in candidates for t in c.terms}
    assert "causa" in terms, f"expected 'causa' among captured terms, got {terms!r}"


def test_get_profile_us_pr_captures_a_definition_gated_by_para_los_fines_este_articulo_with_el_termino_live(
    pr_rows_cycle12,
):
    """`STATE_PR_LEY_77_1957_ART6_140`: '(4) Para los fines de este
    Artículo, el término "opción" significa un acuerdo...' -- "Para los
    fines" (Para + fines) is not one of the 3 shipped phrases either
    (shipped: A los fines / A los efectos / Para propósitos only), AND
    "el término " precedes the quote. A second real row compounding both
    gaps."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle12["STATE_PR_LEY_77_1957_ART6_140"]
    profile = get_profile("US-PR")

    candidates = _extract(profile, row)
    terms = {t for c in candidates for t in c.terms}
    assert "opción" in terms, f"expected 'opción' among captured terms, got {terms!r}"


@pytest.mark.parametrize("unit_word", ["Artículo", "Sección"])
@pytest.mark.parametrize(
    "preposition_phrase",
    [
        "Para los fines de",
        "Para fines de",
        "Para efectos de",
        "Para los efectos de",
        "A fines de",
        "A efectos de",
        "A propósitos de",
        "A los propósitos de",
    ],
)
def test_each_missing_preposition_los_combination_is_recognized_for_both_units_live(
    preposition_phrase, unit_word
):
    """Full combinatorial closure: every preposition/"los"/scope-noun
    combination NOT already in `_LOCAL_TRIGGER_PHRASE_ALTERNATION`
    ("A los fines" / "A los efectos" / "Para propósitos" are the only 3
    shipped), crossed with BOTH unit words. Synthetic body, isolating the
    mechanism the same way `test_each_no_los_chapter_scope_trigger_
    variant_is_recognized_live` does for Capítulo -- no real corpus row
    needed to prove a well-defined positive for an isolated trigger
    phrase (this codebase's own established convention, e.g.
    `test_pr_profile_article_scope_live_cycle5.py`'s module docstring)."""
    from app.definition_links.profiles import get_profile

    demonstrative = "este" if unit_word == "Artículo" else "esta"
    body = f'{preposition_phrase} {demonstrative} {unit_word}, "Término" significa una definición de prueba.'
    profile = get_profile("US-PR")

    candidates = profile.extract_local_scope_definitions(body, article_number="1", chapter=None)
    terms = {t for c in candidates for t in c.terms}
    assert "Término" in terms, (
        f"phrase {preposition_phrase!r} + {demonstrative} {unit_word} should gate a local "
        f"definition -- got candidates {candidates!r}"
    )
