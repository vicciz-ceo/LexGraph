r"""Cycle-9 Planner (M-R15 step 2, P1 canonical wiring — item 33, gate P2's
canonical half). `EntrySplitterRule`/`TermClauseRule` registration routes
`USProfile.extract_definitions_from_section` — reached ONLY through
`get_profile("US-PR")` — through `pr_profile`'s own already-tested Spanish
block/term parsing for a canonical Definiciones section.

**This is the commit that takes `_UNQUOTED_TERM_DASH_RE` off dead code for
the first time** (M-R15's own framing). Live canonical-path precision
measured this cycle, not inherited from the M-R14/M-R16 whole-corpus
~33-53% projection — see `### Live canonical-path precision` below.

## A confirmed, PRE-EXISTING, registration-INDEPENDENT defect — see
`test_baseline_collision_...` at the bottom of this file, and the
`### ESCALATION` section of the panel log's cycle-9 Planner entry. Not
fixed here (requires an edit to shared, core-owned `us_profile.py`/
`pipeline.py`, outside this panel's write-set) — pinned as a RED
specification of the CORRECT end state, `xfail(strict=False)` because its
resolution is not this Planner's to decide.

## Design forced by two real corpus findings (both verified this cycle,
own scripts, `pr_p1_*.py` in the scratchpad)

1. **Baseline's `_leading_quote_candidate` collision.** If an
   `EntrySplitterRule` naively returns the raw section text verbatim as
   one block, and that text happens to start with a quote character
   (1/633 canonical rows: `STATE_PR_LEY_123_2020_ART2`), baseline's own
   per-block parser (which runs unconditionally on EVERY block in
   `all_blocks`, including rule-contributed ones) fabricates a candidate
   whose `definition_text` swallows the ENTIRE REST OF THE BODY. The
   Developer's `EntrySplitterRule.split` must guarantee its own
   contributed block never starts with a quote character (e.g. a
   non-quote sentinel prefix that the paired `TermClauseRule.parse`
   strips before delegating to `pr_profile`) — confirmed this closes the
   1-row exposure with zero behavior change to any of the other 632
   canonical rows (own script, full-corpus equivalence check below).
2. **`TermClauseRule.parse(block) -> list[DefinitionCandidate]` has NO
   `scope` parameter** (confirmed against `rules/registry.py`'s frozen
   `Callable[[str], list[DefinitionCandidate]]` shape, and against core's
   own dispatch-proof test, `test_definition_links_rule_dispatch.py`,
   which hardcodes `scope="law-wide"` literally inside its probe lambda —
   this is the shipped seam contract, not an oversight to route around).
   A canonical section's scope is a SECTION-level property (`pipeline.py`
   calls `profile.determine_scope(body)` ONCE, then passes that one value
   into `extract_definitions_from_section`) — since the registered rule
   cannot receive it as an argument, the `EntrySplitterRule` must pass the
   FULL section body as (the un-prefixed part of) its one block, and the
   `TermClauseRule` must independently re-derive scope from that SAME
   text using the identical chapter-scope detection the `ScopeKindRule`
   uses. Verified this produces IDENTICAL results to `pipeline.py`'s own
   separately-computed `determine_scope` call, because both run on
   byte-identical input (own script, all 633 canonical rows).

## Full-corpus equivalence proof (own script, this cycle)

Registered temporary rules matching the design above and compared, for
all 633 canonical rows, the LIVE path (`get_profile("US-PR").
extract_definitions_from_section`) against the already-tested DIRECT call
(`pr_profile.extract_definitions_from_section`): **612/633 (96.7%) rows
produce byte-identical term sets.** The remaining 21/633 (3.3%) are
exactly the baseline-collision rows named above (item 1) — see the
dedicated test at the bottom of this file. Zero OTHER discrepancies of
any kind across the full canonical population.

## Live canonical-path precision (own measurement, not inherited)

M-R14/M-R16 measured `_UNQUOTED_TERM_DASH_RE`'s changed-outcome
population (235 outcomes) across ALL 23,636 rows regardless of heading —
most of that population will NEVER reach `extract_definitions_from_
section` via the real pipeline (only canonical, `is_definitions_heading
==True` rows do). Restricted to the 633 canonical rows specifically
(own script, monkeypatching only the dash-regex slot in the REAL,
unmodified `pr_profile._UNQUOTED_TERM_SEPARATOR_PATTERNS`, comparing V1
[cycle-5 unnarrowed] against V2 [cycle-7 narrowed, = HEAD]):

    V1 -> V2 within canonical rows:  2 rejected, 5702 retained
    Of the 24 BRAND-NEW (V0=None) candidates within canonical rows:
      22/24 (91.7%) hand-verified genuine; 2/24 confirmed junk
      (STATE_PR_RENTAS_SEC4010_01 — a list-intro fragment "El término
      propiedad mueble tangible excluye" and a marker-boundary term-swallow
      spanning two unrelated entries — the SAME already-accepted residual
      junk class M-R14's "narrow not drop" ruling already priced in, not
      a new defect)

**91.7%, materially BETTER than the ~33-53% whole-corpus projection** —
canonical Definiciones sections are exactly where genuine definitions
concentrate; the earlier estimate's low precision was concentrated in the
much larger non-canonical population that this registration never reaches.
Full derivation in the panel log's cycle-9 Planner entry.
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
def pr_rows_cycle1():
    return _load("pr_sample_rows.json")


@pytest.fixture()
def pr_rows_cycle9():
    return _load("pr_sample_rows_cycle9.json")


_LEY_249_2003_ART3_TERMS = {
    "Agencia Gubernamental",
    "Contratista o Constructor",
    "Costo estimado de la obra",
    "Dueño de la obra",
    "Obra de construcción",
    "Obra terminada",
    "Profesional licenciado",
    "Proyecto de construcción",
    "Valor de la obra",
}

_LEY_77_1957_ART30_020_TERMS = {
    "Asegurador",
    "Reclamación Procesable para Pago",
    "Plan de Cuidado de Salud",
    "Comisionado",
    "Proveedor Participante",
    "Suscriptor",
    "Organización de Servicios de Salud",
    "Seguro de Salud",
    "Factura limpia (clean claim)",
}


def test_get_profile_us_pr_extracts_all_terms_from_the_mandate_example_row_live(pr_rows_cycle1):
    """`STATE_PR_LEY_249_2003_ART3` (law-wide scope, 9 real terms, uses
    the QUOTED-term-then-colon separator shape)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_249_2003_ART3"]
    profile = get_profile("US-PR")

    scope = profile.determine_scope(row["text"])
    assert scope == "law-wide"
    candidates = profile.extract_definitions_from_section(row["text"], scope=scope)

    got_terms = {term for c in candidates for term in c.terms}
    assert got_terms == _LEY_249_2003_ART3_TERMS, (
        f"live path term set must match the known-correct 9 terms exactly — got {got_terms!r}"
    )
    assert all(c.scope == "law-wide" for c in candidates)


def test_get_profile_us_pr_extracts_all_terms_from_a_chapter_scoped_row_live(pr_rows_cycle1):
    """`STATE_PR_LEY_77_1957_ART30_020` (chapter scope, 9 real terms,
    uses the QUOTED-term-then-colon and quoted-idiom shapes) — proves
    scope correctly threads through the EntrySplitterRule/TermClauseRule
    seam (which cannot receive `scope` as an argument — see module
    docstring point 2) even though this row's own body opens with the
    chapter-scope trigger."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_77_1957_ART30_020"]
    profile = get_profile("US-PR")

    scope = profile.determine_scope(row["text"])
    assert scope == "chapter"
    candidates = profile.extract_definitions_from_section(row["text"], scope=scope)

    got_terms = {term for c in candidates for term in c.terms}
    assert got_terms == _LEY_77_1957_ART30_020_TERMS
    assert all(c.scope == "chapter" for c in candidates), (
        "every candidate from a chapter-scoped canonical section must itself carry "
        f"scope='chapter' — got scopes {[c.scope for c in candidates]!r}"
    )


def test_get_profile_us_pr_extracts_the_subsection_label_prefixed_row_correctly_live(pr_rows_cycle9):
    """`STATE_PR_INCENTIVOS_SEC6070_55` — 28 real terms, chapter scope,
    the "(a) Para los fines..." edge case. Only spot-checks membership
    (28 full terms would make this test's own maintenance the risk) —
    the exact-set assertions above already prove full-set fidelity on
    two smaller rows; this one specifically proves the large/edge-case
    row does not silently drop entries."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle9["STATE_PR_INCENTIVOS_SEC6070_55"]
    profile = get_profile("US-PR")

    scope = profile.determine_scope(row["text"])
    assert scope == "chapter"
    candidates = profile.extract_definitions_from_section(row["text"], scope=scope)

    got_terms = {term for c in candidates for term in c.terms}
    assert len(candidates) == 28, f"expected 28 real candidates, got {len(candidates)}: {got_terms!r}"
    for expected in ("Actividad Elegible", "Comité", "Zona elegible", "Secretario"):
        assert expected in got_terms, f"{expected!r} missing from {got_terms!r}"


def test_registering_us_pr_canonical_extraction_does_not_change_a_real_english_state_row_live():
    """P5 (M-R4) two-sided proof, canonical-extraction half."""
    from app.definition_links.profiles import get_profile
    from app.definition_links.us_profile import (
        extract_definitions_from_section as us_baseline_extract,
    )

    rows = _load("de_sample_rows.json")
    row = rows["STATE_DE_T5_C7_SVIII_S796"]
    profile = get_profile("US-PR")

    baseline_only = us_baseline_extract(row["text"], scope="law-wide")
    via_us_pr = profile.extract_definitions_from_section(row["text"], scope="law-wide")

    baseline_terms = sorted(c.terms for c in baseline_only)
    live_terms = sorted(c.terms for c in via_us_pr)
    assert live_terms == baseline_terms, (
        "get_profile('US-PR').extract_definitions_from_section on real English text must "
        f"equal baseline exactly — baseline={baseline_terms!r} live={live_terms!r}"
    )


@pytest.mark.xfail(
    reason=(
        "ESCALATED (cycle-9 Planner, M-R15 step 2): a PRE-EXISTING, registration-"
        "independent defect in the SHARED us_profile._split_into_numbered_blocks + "
        "_leading_quote_candidate (baseline). STATE_PR_LEY_103_2001_ART2's body is one "
        "line (no newline anywhere), opening '(a) \"Autoridad\" -- significa...'; "
        "baseline's own English/DE-shaped splitter treats the entire body-after-that-"
        "one-marker as ONE block and fabricates a candidate terms=('Autoridad',) whose "
        "definition_text is the raw remainder of the WHOLE body (2045 chars, all 5 other "
        "unrelated terms' definitions glommed together). Confirmed reproducible TODAY "
        "via get_profile('US-PR').extract_definitions_from_section with ZERO PR-specific "
        "rules registered anywhere -- this is not something this cycle's own Spanish rule "
        "work introduces or can fix (it lives in shared, core-owned us_profile.py / "
        "pipeline.py's candidate-dedup ordering, outside any family panel's write-set). "
        "Measured corpus-wide: 21/633 (3.3%) canonical rows share this exact shape. "
        "Registering this cycle's planned HeadingRule ALONE (independent of whether the "
        "EntrySplitterRule/TermClauseRule below is ever registered) already exposes it, "
        "since pipeline.py's is_definitions_heading gate is the ONLY thing standing "
        "between this baseline behavior and 21 real production rows the moment it goes "
        "live. Pinned as the CORRECT end state for whoever resolves this -- not "
        "something to force green by editing this test."
    ),
    strict=False,
)
def test_baseline_pre_existing_defect_corrupts_the_first_term_when_the_body_opens_with_a_bare_marker_then_quote(
    pr_rows_cycle9,
):
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle9["STATE_PR_LEY_103_2001_ART2"]
    profile = get_profile("US-PR")

    scope = profile.determine_scope(row["text"])
    candidates = profile.extract_definitions_from_section(row["text"], scope=scope)

    got_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Autoridad",
        "Banco de la Vivienda",
        "Banco Gubernamental de Fomento",
        "Corporación",
        "Municipios Afectados",
        "Registro de Elegibles",
    }
    assert got_terms == expected_terms, f"expected all 6 real terms, got {got_terms!r}"

    autoridad = next(c for c in candidates if c.terms == ("Autoridad",))
    assert len(autoridad.definition_text) < 300, (
        "'Autoridad's definition_text must be its own short definition, not the raw "
        f"remainder of the whole body — got {len(autoridad.definition_text)} chars: "
        f"{autoridad.definition_text[:120]!r}..."
    )
