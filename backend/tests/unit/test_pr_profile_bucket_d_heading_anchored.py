"""RED tests for the DIRECTOR-ORDERED heading-anchored bucket-D rule --
sprint 2026-08-04-defs-us-pr, cycle 3, gate P1/P4.

## Director ruling (this cycle's scope)

Bucket D (copulative/prose Definiciones-section bodies with no entry
marker and no canonical defining idiom -- e.g. `"Son bienes las cosas o
derechos que pueden ser apropiables..."` for heading `"Bienes; definición"`)
was ESCALATED in cycle 2 (M-R6) as a zero-miss-vs-zero-false-positive
conflict (P-R2/Q-1). The director's ruling: build a NARROW
heading-anchored rule -- capture the subset whose HEADING NAMES THE
DEFINED TERM, using the heading as the anchor. No general Spanish prose
matcher. The anchor-less residue is enumerated as a documented,
director-reviewable gap (see `test_bucket_d_residue_stays_at_zero_*`
below and the sprint contract's `## Bucket D final split (cycle 3)`).

## Why this is SAFE (not a general prose matcher)

The rule never inspects body prose for copulative shape on its own. It
only fires when TWO independent conditions both hold:
  1. The heading (already known, via `is_definitions_heading`, to be a
     genuine Definiciones heading) NAMES a specific term as its own
     subject -- the non-"definición(es)" clause of a heading already
     shaped like `"<Term>; definición"`, `"<Term>, definición"`,
     `"Definición de <Term>"`, or `"<Term>—Definiciones"`.
  2. That EXACT named term (word-boundary, accent-folded, leading Spanish
     article stripped) is independently corroborated by appearing,
     verbatim, somewhere in the section's own body text.
Neither condition alone is a general prose matcher -- condition 1 is
already-existing heading-parsing machinery (`is_definitions_heading`'s own
clause-splitting shape), and condition 2 is a literal, disciplined
verbatim-presence check, not a grammar/POS matcher. A body that does NOT
literally repeat its own heading's named term (e.g. because the term is
only implied via a different grammatical form, or because the heading's
named term does not match what the body actually defines) correctly
yields NOTHING -- see the residue tests below, which are exactly as
important as the positive tests: they prove the rule does NOT silently
widen into general prose capture.

## Refined split, cycle 3 (differs from the manager's crude 65/19 split)

The manager's own crude split-script (regex-substring based, `scratchpad/
mgr_bucketD_split.py`) reported 65 anchored / 19 residue out of the 84
bucket-D rows. Re-deriving this LIVE against the current `pr_profile.py`
(not trusting the crude script) with THREE corrections found while
re-triaging surfaced a DIFFERENT, more accurate split:

  1. **Idiom-gap correction** (see `test_pr_profile_idiom_widening_
     cycle3.py`): 1 row (`STATE_PR_LEY_66_2011_ART3`) is not bucket D at
     all -- it is fully solved by widening the recognized idiom set to
     include `se refiere a`/`se referirá a` (a QUOTED-term, marked-list
     row; the manager's own idiom regex just didn't include this idiom).
  2. **Quote-mechanical-gap correction**: 4 more rows the manager's crude
     split miscategorized as bucket-D residue actually contain an
     explicit QUOTED term and are ordinary mechanical extraction gaps
     (missing lead-in-strip / new idiom recognition), not copulative
     prose at all -- see `test_pr_profile_extraction_cycle3.py`
     (`STATE_PR_LEY_141_2002_ART6`, `STATE_PR_LEY_420_2004_ART2`,
     `STATE_PR_LEY_15_1931_SEC22`, `STATE_PR_LEY_155_1937_SEC1`).
  3. **A genuine new correct-zero guard**: 1 more row
     (`STATE_PR_LEY_48_2018_ART3`) is a WHOLESALE CROSS-LAW/TITLE
     deferral (`"...conocida como, 'Ley de Procedimiento Administrativo
     Uniforme...'"` -- the quote is a LAW TITLE via the `conocido como`
     idiom the cycle-1 survey already flagged as "overwhelmingly a
     law-title-naming idiom, not term-defining"), the SAME shape as the
     already-pinned `STATE_PR_LEY_52_2019_ART3` correct-zero guard.
  4. **A refinement the crude split's own footer boilerplate broke**: a
     REAL, previously-uncatalogued corpus artifact -- a page-break scrape
     footer (`"Rev. <date> www.ogp.pr.gov Página N de M "<Law Title>" de
     <year> [Ley N-YYYY, según enmendada]"`, 370 corpus-wide rows) can be
     injected ANYWHERE in a Civil Code row's body, carrying its OWN
     quoted law title. This is NOT the term-defining shape a mechanical-
     gap classifier should trigger on -- ignoring it (matching the sprint's
     "byte-compare, don't paraphrase" discipline on the DATA, but this is
     an ANALYSIS discipline on top of that data) is what correctly keeps
     5 genuinely copulative rows (e.g. `STATE_PR_CIVIL_ART1223`, `"La
     retención es la facultad..."`) IN the heading-anchored bucket instead
     of being wrongly routed to a "needs a quoted-term fix" bucket they
     don't belong in.
  5. **A genuine new anchor-extraction capability** ("Definición de X"
     single-clause shape): the manager's crude split only extracted a
     candidate term from a heading clause that DOESN'T itself match the
     "definición" stem (works for `;`/`,`/em-dash-delimited compound
     headings). It missed headings that are a SINGLE clause of the shape
     `"Definición de <Term>"` (no delimiter at all) -- the term is the
     prepositional object of "de" WITHIN the same clause that also
     satisfies the stem match. Recovers 4 real rows:
     `STATE_PR_RENTAS_SEC2030_03`, `STATE_PR_LEY_12_1966_ART7`,
     `STATE_PR_PENAL_ART35`, `STATE_PR_LEY_284_2004_ART3` (not all 4
     vendored here -- see the sprint contract's full enumeration; 2 are
     pinned below as real fixture rows, the other 2 are parametrized bare
     strings mirroring cycle 2's own precedent).

**Result**: 70 heading-anchored (up from the crude 65), 7 anchor-less
residue (down from 19) -- the FINAL documented gap, enumerated below and
in the sprint contract for director review.

## Interface under test (NEW -- does not exist yet, RED via ImportError)

`extract_heading_anchored_definition(heading, body, *, scope) ->
list[DefinitionCandidate]` -- returns exactly one candidate when both
conditions above hold, else `[]`. The Developer's exact implementation
(how the anchor term is parsed out of the heading, how corroboration is
checked) is not pinned here -- only the OUTCOME, per this sprint's
standing "tests pin outcome, not internals" discipline.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows_cycle3.json` -- see that file's sibling `README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_cycle3.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- Positive: heading-anchored rows, diverse anchor shapes ------------------


def test_semicolon_clause_anchor_real_row(pr_rows):
    """`STATE_PR_CIVIL_ART236`: `"Bienes; definición"` -> body `"Son bienes
    las cosas o derechos..."`. The director's own confirmed example."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART236"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Bienes",)
    assert "cosas o derechos" in candidates[0].definition_text
    assert candidates[0].scope == "law-wide"


def test_comma_clause_anchor_real_row(pr_rows):
    """`STATE_PR_LEY_77_1957_ART5_020`: `"Pasivos, definición"` -> body
    `"Para propósitos de este Capítulo, los pasivos se definirán
    como..."`. The director's own confirmed example."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART5_020"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="chapter"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Pasivos",)
    assert candidates[0].scope == "chapter"


def test_hay_x_cuando_copulative_shape_real_row(pr_rows):
    """`STATE_PR_CIVIL_ART1264`: `"Evicción; definición"` -> body `"Hay
    evicción cuando se vence al adquirente..."` -- the "Hay X cuando"
    copulative shape. Director's own confirmed example."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART1264"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Evicción",)
    assert "se vence al adquirente" in candidates[0].definition_text


def test_leading_article_stripped_multiword_term_real_row(pr_rows):
    """`STATE_PR_CIVIL_ART1508`: `"El contrato de seguro; definición"` --
    the heading's own leading Spanish article "El" must be stripped so the
    anchor term is "contrato de seguro", matching the body's own
    lowercase "El contrato de seguro es aquel...". Director's own
    confirmed example."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART1508"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("contrato de seguro",)


def test_x_es_la_facultad_shape_real_row(pr_rows):
    """`STATE_PR_CIVIL_ART326`: `"Poder; definición"` -> body `"Poder es
    la facultad por la que..."`. This is the SAME real row already
    referenced in `pr_profile.py`'s own module comments (the unbounded-
    forward-search bug fix) as a row with NO safe separator-based
    extraction -- proving the heading anchor is what makes THIS row safe
    to capture at all, not a separator-pattern fix."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART326"]
    assert row["text"].startswith("Poder es la facultad")  # sanity
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Poder",)


def test_definicion_de_x_single_clause_anchor_real_row(pr_rows):
    """`STATE_PR_RENTAS_SEC2030_03`: `"Definición de Caudal Relicto
    Bruto"` -- a SINGLE clause (no `;`/`,`/em-dash), where the whole
    clause satisfies `is_definitions_heading`'s first-word stem match AND
    the anchor term is the prepositional object of "de" within that SAME
    clause. A genuinely NEW anchor-extraction shape this cycle's
    diagnosis found (cycle-2's crude split heuristic never handled this
    case -- it only split on `;`/`,`/em-dash delimiters between two
    SEPARATE clauses)."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_RENTAS_SEC2030_03"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Caudal Relicto Bruto",)


def test_em_dash_compound_heading_anchor_term_at_end_of_body_real_row(pr_rows):
    """`STATE_PR_LEY_77_1957_ART36_020`: `"Sistema de logias—Definiciones"`
    -- em-dash-delimited compound heading (same family cycle 2's heading
    fix already recognizes as a genuine Definiciones heading). The anchor
    term "Sistema de logias" appears at the very END of a 472-char single-
    sentence body (`"...se considerará que está operando dentro del
    sistema de logias."`) -- proving the corroboration check must NOT be
    artificially window-truncated to only the body's own opening chars."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART36_020"]
    assert row["text"].rstrip().endswith("sistema de logias.")  # sanity
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Sistema de logias",)


def test_semicolon_compound_with_trailing_qualifier_real_row(pr_rows):
    """`STATE_PR_CIVIL_ART1139`: `"Subrogación; definición y alcance"` --
    already a recognized Definiciones HEADING per cycle 2's own test
    (`test_civil_code_semicolon_compound_heading_real_row` in
    `test_pr_profile_headings_cycle2.py`); this cycle proves the SAME
    row's body extraction is also now recoverable via the heading anchor
    (cycle 2 only proved the heading recognized as Definiciones, never
    that its body yields a candidate)."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART1139"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Subrogación",)


@pytest.mark.parametrize(
    "heading,body,expected_term",
    [
        # bare-string parametrize cases mirroring cycle 2's own precedent
        # (real headings, verified live against the corpus) -- the
        # remaining 2 real "Definición de X" single-clause rows this
        # cycle diagnosed, not vendored as full fixture rows since only
        # the heading/body pair matters for this test.
        (
            "Artículo 35. Definición de la tentativa",
            "Existe tentativa cuando la persona realiza acciones o incurre "
            "en omisiones inequívoca e inmediatamente dirigidas a iniciar "
            "la ejecución de un delito, el cual no se consuma por "
            "circunstancias ajenas a su voluntad.",
            "tentativa",
        ),
        (
            "Artículo 3. Definición de la Región",
            "La región quedará compuesta por los siguientes municipios; "
            "Dorado, Toa Baja, Toa Alta, Vega Baja, Vega Alta, Manatí, "
            "Ciales, Barceloneta, Morovis, Camuy, Hatillo y Arecibo.",
            "Región",
        ),
    ],
)
def test_definicion_de_x_family_bare_string_cases(heading, body, expected_term):
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    candidates = extract_heading_anchored_definition(heading, body, scope="law-wide")
    assert len(candidates) == 1
    assert candidates[0].terms[0].lower() == expected_term.lower()


# --- Residue: the FINAL documented gap (director-reviewable) ----------------
#
# Every row below is a genuine bucket-D row where the heading-anchor rule
# correctly yields NOTHING -- proving the rule is narrow, not a general
# prose matcher. Each has an independently-diagnosed reason (see module
# docstring / sprint contract); these are NOT interchangeable "same
# reason" rows.


def test_residue_nominalization_mismatch_stays_zero(pr_rows):
    """`STATE_PR_CIVIL_ART1526`: `"Enriquecimiento sin causa; definición"`
    -- the heading names a NOMINALIZED noun phrase, but the body only uses
    the VERB form (`"...se enriquece a expensas de otra..."`), never the
    noun phrase itself. No literal verbatim corroboration exists -- correct
    residue, not a bug to widen around with grammatical stemming (that
    would reopen the general-prose-matcher risk the director's ruling
    explicitly rejected)."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART1526"]
    assert "enriquecimiento sin causa" not in row["text"].lower()  # sanity
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


def test_residue_bare_heading_names_no_term_stays_zero(pr_rows):
    """`STATE_PR_LEY_77_1957_ART35_020`: heading is the bare word
    `"Definición"` -- no term is named at all, so there is nothing to
    anchor from (a human reading only the heading could not know what is
    being defined either)."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART35_020"]
    assert row["section_title"] == "Artículo 35.020. Definición"  # sanity
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


def test_residue_second_bare_heading_stays_zero():
    """`STATE_PR_PENAL_ART15`: same bare-heading shape as the row above,
    a SECOND real corpus row, different law (bare heading string only --
    the body's own definitional content, `"Delito es un acto..."`, is
    irrelevant to a heading-anchor rule that has no term to anchor
    from)."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    body = (
        "Delito es un acto cometido u omitido en violación de alguna ley "
        "que lo prohíbe u ordena, que apareja, al ser probado, alguna "
        "pena o medida de seguridad."
    )
    candidates = extract_heading_anchored_definition("Artículo 15. Definición", body, scope="law-wide")
    assert candidates == []


def test_residue_heading_body_term_mismatch_stays_zero(pr_rows):
    """`STATE_PR_CIVIL_ART1293`: `"Las normas de la compraventa;
    definición y aplicabilidad"` -- the heading names "las normas de la
    compraventa" (the rules of sale), but the body's OWN definitional
    content is actually about a DIFFERENT term, "permuta" (barter), merely
    stating that permuta follows sale's rules. The heading's named term
    and the body's actual defined term are NOT the same thing -- correct
    residue (a genuine heading/body mismatch, not a corroboration-window
    bug)."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART1293"]
    assert row["text"].startswith("La permuta es un contrato")  # sanity
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


def test_residue_meta_heading_about_definitions_in_general_stays_zero(pr_rows):
    """`STATE_PR_LEY_77_1957_ART4_010`: `"Definiciones que no se
    excluyen"` -- a META-heading about how definitions in this chapter
    relate to each other (they don't mutually exclude), not itself naming
    any specific defined term."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART4_010"]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


def test_residue_non_contiguous_term_stays_zero(pr_rows):
    """`STATE_PR_LEY_77_1957_ART5_030`: `"Activo no Admitido,
    definición"` -- the body's own words ("un activo es uno no admitido")
    convey the SAME concept but never repeat the heading's exact phrase
    CONTIGUOUSLY ("Activo no Admitido" is split apart by "es uno" in the
    body). A literal, disciplined verbatim-presence check correctly finds
    no match -- this is deliberate: a fuzzy/reordering match would be the
    first step toward the general-prose-matcher risk the ruling rejected."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART5_030"]
    assert "activo no admitido" not in row["text"].lower()  # sanity: not contiguous
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


def test_residue_uncorroborated_term_not_repeated_in_body_stays_zero(pr_rows):
    """`STATE_PR_LEY_77_1957_ART42_010`: `"Organizaciones caritativas,
    definición"` -- the body is a long qualifying description of what
    counts as such an organization (897 chars) but never once repeats the
    phrase "organizaciones caritativas" itself (only the unrelated
    adjective "caritativos" describing "fines"). No corroboration ->
    correct residue. (This row's body also carries a LATE bracketed
    citation with its own quoted law title, `"[Nota: ... 'Código de
    Rentas Internas de Puerto Rico de 2011']"` -- a regression guard that
    the presence of AN quote elsewhere in the body must not be confused
    with the anchor term itself being corroborated.)"""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_LEY_77_1957_ART42_010"]
    assert "organizaciones caritativas" not in row["text"].lower()  # sanity
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


# --- Precision regression guard: page-break footer boilerplate --------------


def test_page_break_footer_boilerplate_does_not_block_or_corrupt_the_real_anchor(pr_rows):
    """Real, previously-uncatalogued corpus artifact: a scrape page-break
    footer (`"Rev. <date> www.ogp.pr.gov Página N de M "<Law Title>" de
    <year> [Ley N-YYYY, según enmendada]"`) can be injected ANYWHERE in a
    Civil Code row's body -- confirmed on 370 corpus-wide rows -- carrying
    its OWN quoted law title that has NOTHING to do with this section's
    own heading. `STATE_PR_CIVIL_ART263` (`"Hechos jurídicos; definición"`)
    is a real row where this footer sits BEFORE the actual definitional
    sentence (`"...[Ley 55-2020, según enmendada] Son hechos jurídicos
    aquellos que producen..."`). Two things must both hold: (1) the real
    anchor ("Hechos jurídicos") is still found DESPITE the unrelated
    footer quote appearing first in the body, and (2) the captured
    `definition_text` is the REAL definitional sentence, not the footer's
    own citation noise."""
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = pr_rows["STATE_PR_CIVIL_ART263"]
    assert row["text"].startswith("Rev. 17 de julio de 2026")  # sanity: footer comes first
    assert "Código Civil de Puerto Rico" in row["text"]  # sanity: unrelated footer quote present
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1
    assert candidates[0].terms == ("Hechos jurídicos",)
    assert "producen la adquisición" in candidates[0].definition_text
    assert "www.ogp.pr.gov" not in candidates[0].definition_text
    assert "según enmendada" not in candidates[0].definition_text
