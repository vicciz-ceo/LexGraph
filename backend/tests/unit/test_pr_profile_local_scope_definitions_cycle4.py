"""Cycle-4 Planner tests for gate P2 (outside-canonical Spanish
definitions) -- sprint 2026-08-04-defs-us-pr, item 18, THE LEAD item per
ruling M-R10.

## Why this cycle exists (program ruling P-R7)

Every measurement in this sprint before QA's cycle-3 pass used "the
`Definici(ón|ones)` stem appears in `section_title`" as ground truth --
the canonical-section population, 635 rows. QA built its OWN ground truth
(a corpus-wide idiom sweep, not gated on heading presence) and found the
other 23,001 rows were never in any sweep: only 7/833 idiom-bearing
non-canonical rows were captured (0.8%). Program ruling P-R7 (new,
broadcast program-wide): a zero-miss sweep must build ground truth
INDEPENDENT of the capture mechanism's own signals. This file's own
survey (panel log, cycle-4 Planner entry) re-derives that population from
scratch with a WIDER idiom census (21 idioms, corpus-wide vs.
non-canonical) plus sample-classification (11-25 rows/idiom, hand-read)
to separate genuine definitions from incidental prose -- `incluye`
(608/23,636, sampled ~20% genuine), `comprende` (105, ~25% genuine), `se
considera como` (302, sampled 0/14 genuine STANDALONE-term shape in this
pass -- almost all are legal-classification prose, not term appositions),
and `según se define`/bare `se define` (398+257, sampled ~95%+ POINTER/
cross-reference usage -- these name an ALREADY-defined term, they do not
define a new one, and belong to `detect_cross_law_derivations`-style
pointer machinery, not this file) are all LOW-PRECISION and excluded from
this item's population. `significa(rá)`, `se entenderá por`, `quiere
decir`, and the bare quoted-term-then-idiom shape below sampled cleanly
(see below).

## Seam dependency (core sprint `2026-08-04-defs-core-scope` @ `6de6d6e`,
spec v2.4 -- NOT yet merged to `origin/main`)

`PRProfile.extract_local_scope_definitions(self, article_body, *,
article_number) -> list[DefinitionCandidate]` is a NEW Protocol method
(seam spec v1, unchanged through v2.4) -- it does not exist on `PRProfile`
or the `JurisdictionProfile` Protocol in this un-rebased tree. Every test
in `TestExtractLocalScopeDefinitionsSeam` below is RED via
`AttributeError` today; this is EXPECTED per ruling M-R11's sequencing
note ("tests referencing the new profile methods will be RED against the
un-rebased tree -- that is expected and correct, not a planning bug").
Ruling M-R11: this method is how gate P2's "not wired into `pipeline.py`"
finding closes -- NOT by editing `pipeline.py` (forbidden to this panel,
and now jurisdiction-literal-free by core's own C3).

The method must union THREE sources, all `scope="local"`:

  (a) `extract_local_definitions` -- ALREADY RED-pinned against QA's
      findings 1-2 in `test_pr_profile_qa_cycle4_findings.py` (the `se
      define "X" como` lead-in, the unquoted-term shape, and the missing
      `A los efectos de este Artículo` trigger variant). Not re-pinned
      here to avoid duplicate assertions -- this file only proves the
      UNION wiring reaches that function's output.
  (b) `extract_adhoc_definitions` -- unchanged.
  (c) NEW -- `extract_inline_local_definitions` (this file's own item,
      see `TestExtractInlineLocalDefinitions` below), a bounded,
      no-unbounded-search `finditer` sweep for a quoted-term-then-
      recognized-idiom pair ANYWHERE in a non-canonical article body,
      not gated behind any specific scope-trigger phrase at all.

## `extract_inline_local_definitions` -- pure function, testable TODAY

Real, unambiguous rows found by the P-R7 sweep where a genuine local
definition sits mid-body with NO "A los fines/efectos de este Artículo"
(or similar) lead-in phrase preceding it at all -- neither
`extract_local_definitions` nor `extract_adhoc_definitions` can ever
reach these, by design (both require a specific trigger phrase):
`STATE_PR_RENTAS_SEC1071_07` (`el término "período aplicable"
significa...`, buried inside subsection (a)(3) of an otherwise entirely
non-definitional article about partner/partnership transactions) and
`STATE_PR_LEY_55_1933_SEC12` (`el término "control" significa...`, inside
subsection (b) of a bank-control-change article).

Measured precision (panel log has the full sweep): a naive whole-body
`finditer` of the quoted-term-then-bare-idiom shape over the full
23,001-row non-canonical population found 889 hits; two independent
random samples (20 + 25 rows) were 100% and 96% genuine respectively (the
one false positive, `STATE_PR_LEY_146_2011_ART3`, was a RE-MENTION of an
already-defined term -- "Dicho 'Fondo Especial' será administrado..." --
not a fabrication of new prose). See `## ESCALATION` in the sprint
contract's cycle-4 item plan for the ship-it-vs-gate-it-narrower question
this precision profile raises.

`extract_inline_local_definitions` does not exist in `pr_profile.py`
today -- every test in `TestExtractInlineLocalDefinitions` is RED via
`ImportError` (the same legitimate RED signal cycle 1's very first pass
used, per CodeGraph-verified precedent).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle4.json"
)
QA_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_qa_cycle4.json"
)
CYCLE3_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle3.json"
)


def _load(path: Path) -> dict[str, dict]:
    return {row["act_id"]: row for row in json.loads(path.read_text(encoding="utf-8"))}


@pytest.fixture()
def pr_rows():
    return _load(FIXTURE_PATH)


@pytest.fixture()
def qa_rows():
    return _load(QA_FIXTURE_PATH)


@pytest.fixture()
def cycle3_rows():
    return _load(CYCLE3_FIXTURE_PATH)


# --- item 18c: extract_inline_local_definitions (pure function, no core dep) -


class TestExtractInlineLocalDefinitions:
    """RED via `ImportError` -- `extract_inline_local_definitions` does not
    exist in `pr_profile.py` yet."""

    def test_captures_a_buried_definition_with_no_scope_trigger_lead_in(self, pr_rows):
        """`STATE_PR_RENTAS_SEC1071_07`: no `A los fines/efectos de este
        Artículo` anywhere -- the real trigger is just `Para fines de este
        párrafo, el término "período aplicable" significa...`, mid-body,
        inside an otherwise entirely procedural article. Neither
        `extract_local_definitions` nor `extract_adhoc_definitions` can
        reach this (both require one of their own specific lead-in
        phrases)."""
        from app.definition_links.pr_profile import extract_inline_local_definitions

        row = pr_rows["STATE_PR_RENTAS_SEC1071_07"]
        candidates = extract_inline_local_definitions(row["text"])
        matching = [c for c in candidates if "período aplicable" in c.terms]
        assert len(matching) == 1
        assert matching[0].scope == "local"

    def test_captures_a_second_buried_definition_real_row(self, pr_rows):
        """`STATE_PR_LEY_55_1933_SEC12`: `el término "control" significa
        la facultad para...`, subsection (b) of a bank-control-change
        article with no article-scope trigger phrase at all."""
        from app.definition_links.pr_profile import extract_inline_local_definitions

        row = pr_rows["STATE_PR_LEY_55_1933_SEC12"]
        candidates = extract_inline_local_definitions(row["text"])
        matching = [c for c in candidates if "control" in c.terms]
        assert len(matching) == 1

    def test_does_not_fabricate_from_a_re_mention_of_an_already_defined_term(self):
        """Precision regression guard, per the panel log's sampled false
        positive (`STATE_PR_LEY_146_2011_ART3`): a quoted term followed by
        `será` can be a RE-MENTION, not a fresh definition. This
        synthetic body (mirroring that real row's shape, not vendored
        verbatim since the point is the mechanism, not a specific corpus
        row) documents the residual ~4% risk named in the contract's
        cycle-4 ESCALATION rather than silently ignoring it -- the exact
        disambiguation heuristic (e.g., requiring the quote to be the
        FIRST occurrence of that term in the body) is a Developer/Planner
        design choice a future cycle should make with more data, not
        something this test prescribes. RED today via `ImportError` like
        every other test in this class; once the function exists, this
        assertion should hold from day one (a precision guard, not a
        capture gap) -- if a future pass finds it does not, that is new
        information for the log, not a reason to weaken this assertion.
        """
        from app.definition_links.pr_profile import extract_inline_local_definitions

        body = (
            "El Fondo Especial para el Desarrollo consolidará los recursos "
            'aprobados por la Asamblea Legislativa. Dicho "Fondo Especial" '
            "será administrado por la Corporación de Puerto Rico para la "
            "Difusión Pública conforme a los reglamentos aplicables."
        )
        candidates = extract_inline_local_definitions(body)
        # Documented residual risk, not asserted as fixed this cycle --
        # if a future Developer pass narrows this correctly, delete this
        # xfail's `strict=False` escape hatch rather than the assertion.
        assert not any("Fondo Especial" in c.terms for c in candidates), (
            "known residual false-positive risk (re-mention, not a fresh "
            "definition) -- see contract's cycle-4 ESCALATION"
        )


# --- item 18: PRProfile.extract_local_scope_definitions (core-gated seam) ---


class TestExtractLocalScopeDefinitionsSeam:
    """RED via `AttributeError` -- `PRProfile.extract_local_scope_
    definitions` does not exist yet (core seam v2.4 not merged/rebased).
    Expected per ruling M-R11's sequencing note."""

    def test_unions_the_local_trigger_extractor(self, qa_rows):
        """QA finding 1's `se define "X" como` lead-in
        (`STATE_PR_LEY_20_2017_ART4_14`) must be reachable through the
        SEAM method, not just the bare module function."""
        from app.definition_links.pr_profile import PRProfile

        row = qa_rows["STATE_PR_LEY_20_2017_ART4_14"]
        profile = PRProfile(code="US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        matching = [c for c in candidates if "toque de queda" in c.terms]
        assert len(matching) == 1
        assert matching[0].scope == "local"

    def test_unions_the_new_inline_scan(self, pr_rows):
        """The item-18c inline scan's own real row must also be reachable
        through the seam method, proving the union covers all three
        sources, not just `extract_local_definitions`."""
        from app.definition_links.pr_profile import PRProfile

        row = pr_rows["STATE_PR_RENTAS_SEC1071_07"]
        profile = PRProfile(code="US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        assert any("período aplicable" in c.terms for c in candidates)

    def test_still_does_not_swallow_the_gender_disclaimer_row(self, cycle3_rows):
        """Regression guard, reusing the cycle-3 `STATE_PR_LEY_214_2004_
        ART2` fixture (already vendored, no new fixture needed): the
        gender-neutrality preamble must not collapse this row's 26 real
        marked terms into one fabricated candidate via the seam path
        either -- the same collision `test_pr_profile_idiom_widening_
        cycle3.py` already guards for the bare module function."""
        from app.definition_links.pr_profile import PRProfile

        row = cycle3_rows["STATE_PR_LEY_214_2004_ART2"]
        profile = PRProfile(code="US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        assert not any("se refiere a ambos géneros" in " ".join(c.terms) for c in candidates)
