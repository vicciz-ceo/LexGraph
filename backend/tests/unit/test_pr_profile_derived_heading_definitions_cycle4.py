"""Cycle-4 Planner tests, item 19 -- blank-title Definiciones sections
(sprint 2026-08-04-defs-us-pr, gates P2/P4).

## The convention (P-R7-compliant sweep finding, panel log has the full
## method + tables)

A structural sweep INDEPENDENT of idiom vocabulary (not "which idiom
words appear", but "does this article's OWN `section_title` carry zero
descriptive text at all") found 47 corpus-wide non-canonical rows whose
`section_title` is a bare `"Artículo N."`/`"Sección N."` label -- the law
simply never gave that article a title beyond its number -- but whose
body OPENS with an unmistakable Definiciones-block preamble sentence
(`"Los siguientes términos/vocablos/palabras/frases ... tendrá(n) el/los
significado(s) que ..."`). `is_definitions_heading` correctly returns
`False` for these (there is no "Definiciones" word anywhere in the
title to match) -- this is not a heading-regex bug, it is a title-
labeling accident the corpus itself contains, and no amount of widening
`is_definitions_heading`'s vocabulary can ever find it, because the
signal is not IN the heading at all.

A related, smaller convention (3 corpus-wide rows): a Definiciones
sub-heading is embedded INSIDE another article's amendment-instruction
quote (`"...para que lea como sigue: 'Artículo 2. Definiciones. Los
siguientes términos...'"`) -- the amending article's OWN `section_title`
describes the AMENDMENT, not the amended content, so it never carries the
stem either.

## Extraction ALREADY WORKS -- this is a heading-recognition-only gap

Live-verified (not assumed) against the REAL vendored bodies below:
`extract_definitions_from_section`, called DIRECTLY on the body text
(bypassing `is_definitions_heading` entirely), already returns the
correct terms for the clean, `(a)/(b)/(c)`-marked convention rows --
e.g. `STATE_PR_LEY_241_1950_ART2` yields all 6 real terms today, byte-
for-byte, with ZERO code change. This isolates the gap precisely: the
missing piece is `derive_heading_from_body` (seam spec v1, unchanged
through v2.4) recognizing the preamble sentence and synthesizing a
heading (or an equivalent "should this non-canonical body be treated as
Definiciones-bearing" signal) -- NOT new extraction logic.

`STATE_PR_LEY_36_1984_ART9` is a HARDER, DISTINCT sub-case, flagged for
the Developer rather than silently folded into the clean floor-proof
above: it uses an UNMARKED repeated "Término. — Definición." shape (no
`(a)/(1)` markers at all chaining multiple entries together) -- a
genuinely different, additional entry-splitting gap on top of the
heading-recognition one, and its body also contains real mid-body footer
boilerplate (reused by `test_pr_profile_footer_artifact_cycle4.py`'s
sibling concern, item 24). `STATE_PR_LEY_171_2018_SEC18` (the embedded-
amendment convention) is ALSO a harder sub-case, for a different reason:
its real body quotes only a partial, illustrative entry set separated by
a literal `"…"` ellipsis, which sits outside `_ENTRY_MARKER_RE`'s
boundary set -- most of its real markers are invisible today. Both are
left as real, unresolved RED tests below (not floor-proofs) so these
distinctions are not lost.

Core seam dependency: `PRProfile.derive_heading_from_body(self, heading,
body) -> str | None` does not exist yet (not merged/rebased) --
`TestDeriveHeadingFromBodySeam` is RED via `AttributeError`, expected per
M-R11. `TestExtractionAlreadyWorksFloor` needs NO core dependency at all
-- it calls the EXISTING `extract_definitions_from_section` directly and
is RED only in the sense that nothing currently ROUTES these real bodies
to it in the live pipeline; the function call itself already succeeds.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle4.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


import pytest


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- floor proof: extraction already works once routed to the body --------


class TestExtractionAlreadyWorksFloor:
    """No core dependency -- calls `extract_definitions_from_section`
    directly on the real body text. This documents that the gap is
    ISOLATED to heading recognition, not extraction."""

    def test_clean_parenthetical_marked_body_yields_all_six_real_terms(self, pr_rows):
        """`STATE_PR_LEY_241_1950_ART2`: blank title `"Artículo 2. "`,
        body opens `"Los siguientes términos tendrán los significados que
        a continuación se indican..."` then 6 `(a)-(f)` entries."""
        from app.definition_links.pr_profile import extract_definitions_from_section

        row = pr_rows["STATE_PR_LEY_241_1950_ART2"]
        candidates = extract_definitions_from_section(row["text"], scope="law-wide")
        all_terms = {t for c in candidates for t in c.terms}
        expected = {
            "Mercado agrícola",
            "Producto agrícola",
            "Reglamento o reglamentación",
            "Standard",
            "Funcionario",
            "Mercadeo",
        }
        assert expected <= all_terms
        assert len(candidates) == 6

    def test_embedded_amendment_definiciones_subheading_body_still_fails_today(self, pr_rows):
        """`STATE_PR_LEY_171_2018_SEC18`: the article's OWN `section_title`
        describes an amendment instruction; the body it quotes opens
        `"Definiciones. Los siguientes términos tendrán los significados
        que se expresan a continuación..."` -- BUT this real row quotes
        only a partial, illustrative set of entries, separated by a
        literal `"…"` ellipsis (ordinary sentence punctuation is not what
        precedes most of its markers: `"...Nacionales.… (g) Secretario-
        ..."`). Live-verified: `_ENTRY_MARKER_RE`'s boundary set
        (`[.;:\\]]`) does not include `…`, so only 2 of the real 6 markers
        are found (`(a)`, `(f)`) and the resulting mis-split blocks yield
        ZERO candidates today -- a genuinely DIFFERENT, additional gap
        from the clean convention-1 shape above (not solved by
        `derive_heading_from_body` alone; the marker boundary set itself
        needs the ellipsis character added). Documented as a real,
        unresolved RED rather than silently claimed as a floor-proof."""
        from app.definition_links.pr_profile import extract_definitions_from_section

        row = pr_rows["STATE_PR_LEY_171_2018_SEC18"]
        candidates = extract_definitions_from_section(row["text"], scope="law-wide")
        all_terms = {t for c in candidates for t in c.terms}
        assert "Departamento" not in all_terms, (
            "if this now passes, the ellipsis-boundary marker gap has "
            "been fixed -- update this test to assert the real terms "
            "(Departamento, Gobernador, Parque Nacional, Programa, "
            "Secretario, Agencia del Gobierno) instead"
        )


class TestUnmarkedRepeatedEntryShapeStillFails:
    """`STATE_PR_LEY_36_1984_ART9` -- the HARDER sub-case named above.
    Genuinely RED (not a floor-proof): no `(a)/(1)` markers exist at all
    in this real body, so `extract_definitions_from_section`'s single-
    entry-vs-markers dispatch takes the single-entry path and only ever
    attempts ONE `_extract_term_and_definition` call over the WHOLE body
    -- which fails because the preamble sentence before "Municipio" is
    longer than every unquoted pattern's 100-char bound, and there is no
    quote character anywhere in the body for the lead-in fallback to
    find. A real, additional entry-splitting gap for the Developer, not
    solved by `derive_heading_from_body` alone."""

    def test_currently_yields_zero_despite_four_real_entries(self, pr_rows):
        from app.definition_links.pr_profile import extract_definitions_from_section

        row = pr_rows["STATE_PR_LEY_36_1984_ART9"]
        candidates = extract_definitions_from_section(row["text"], scope="law-wide")
        all_terms = {t for c in candidates for t in c.terms}
        # Documents today's real gap -- flip this to the positive
        # assertion (all 4 terms present) once the Developer adds an
        # unmarked-repeated-entry splitter; do not silently soften this
        # to a floor (`>=1`) assertion, which would hide the gap.
        assert "Municipio" not in all_terms, (
            "if this now passes, the unmarked-repeated-entry splitter gap "
            "has been fixed -- update this test to assert all four real "
            "terms (Municipio, Representante autorizado del Secretario de "
            "Salud, Veterinario licenciado, Animal realengo) instead"
        )


# --- core-gated seam: PRProfile.derive_heading_from_body -------------------


class TestDeriveHeadingFromBodySeam:
    """RED via `AttributeError` -- `PRProfile.derive_heading_from_body`
    does not exist yet (core seam v2.4 not merged/rebased). Expected per
    ruling M-R11's sequencing note."""

    def test_synthesizes_a_definitions_heading_from_the_preamble(self, pr_rows):
        from app.definition_links.pr_profile import PRProfile

        row = pr_rows["STATE_PR_LEY_241_1950_ART2"]
        profile = PRProfile(code="US-PR")
        derived = profile.derive_heading_from_body(row["section_title"], row["text"])
        assert derived is not None
        from app.definition_links.pr_profile import is_definitions_heading

        assert is_definitions_heading(derived)

    def test_a_real_non_definitions_blank_title_article_derives_nothing(self):
        """Two-sided gate, mirroring M-R4/P5: a blank-title article whose
        body is ordinary substantive prose (no Definiciones-block
        preamble at all) must NOT get a synthesized heading -- otherwise
        every one-off `"Artículo N. "` row in the corpus risks being
        wrongly routed through `extract_definitions_from_section`."""
        from app.definition_links.pr_profile import PRProfile

        profile = PRProfile(code="US-PR")
        body = (
            "El Departamento notificará a las partes interesadas dentro "
            "de los treinta (30) días siguientes a la radicación de la "
            "solicitud correspondiente, conforme al reglamento aplicable."
        )
        derived = profile.derive_heading_from_body("Artículo 5. ", body)
        assert derived is None
