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

## CYCLE-5 STATUS -- 18c DEFERRED (ruling M-R13 / program Option D,
## Planner re-partition pass)

Everything above describes item 18c's DESIGN -- it is still the standing
spec the function must satisfy whenever it is eventually built. But the
program manager ruled Option D on the cycle-5 inertness-premise escalation
(panel log): `extract_inline_local_definitions` is **not built this
cycle at all**. It waits for core's dispatch sprint to land, at which
point canonical `Definiciones` rows route through `pipeline.py`'s `if`
branch and never reach this seam -- the 38-row canonical-leak residual
this function's guard was designed to bound disappears by construction,
at zero recall cost, instead of being approximated now by a body-based
heuristic that measured out at 6-31% recall lost or hundreds of wrongly-
scoped assertions (full options table in the panel log's cycle-5
escalation entry).

`TestExtractInlineLocalDefinitions` (all 3 tests, this file) and
`TestExtractLocalScopeDefinitionsSeam::test_unions_the_new_inline_scan`
(below) are marked `xfail(strict=True, raises=...)`, pinned to the EXACT
exception each currently raises (`ImportError` for the former,
`AssertionError` for the latter) -- not a bare catch-all -- so that if
either ever fails for a DIFFERENT reason (a real, unrelated regression),
pytest reports a hard FAILURE, not a silently-absorbed XFAIL. `strict=
True` additionally means an unexpected XPASS (e.g. someone builds the
function ahead of the ruling) is reported as a failure too, forcing this
marker to be revisited rather than silently going green.

**STANDING DUTY, not discharged by these markers:** once core's dispatch
lands and a future cycle builds and registers `extract_inline_local_
definitions`, QA must empirically RE-RUN the canonical-leak measurement
(the 117/633 canonical-row leak this module's guard design measured)
against the DISPATCHED pipeline to confirm the by-construction claim
holds -- never assume it. See ruling M-R13 in the sprint contract and the
panel log's Option-D ruling entry for the full reasoning.
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


@pytest.mark.xfail(
    reason=(
        "Item 18c (extract_inline_local_definitions, the untriggered "
        "whole-body Spanish idiom sweep) is DEFERRED by ruling M-R13 / "
        "program Option D: it waits for core's dispatch sprint to land, "
        "at which point canonical Definiciones rows route through "
        "pipeline.py's `if` branch and never reach this seam, so the "
        "38-row canonical-leak residual this function was designed to "
        "guard against disappears by construction, at zero recall cost "
        "-- not a bug, extract_inline_local_definitions is deliberately "
        "not built this cycle. STANDING DUTY once core's dispatch lands "
        "and this function is built and registered: QA must empirically "
        "RE-RUN the canonical-leak measurement against the dispatched "
        "pipeline to confirm the by-construction claim -- never assume "
        "it holds."
    ),
    strict=True,
    raises=ImportError,
)
class TestExtractInlineLocalDefinitions:
    """DEFERRED (18c, ruling M-R13 / program Option D) -- RED via
    `ImportError` because `extract_inline_local_definitions` does not
    exist in `pr_profile.py` and is deliberately not being built this
    cycle. Marked `xfail(strict=True, raises=ImportError)`; see the
    module docstring's `## CYCLE-5 STATUS` section for the full reasoning
    and the post-dispatch re-verification duty."""

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


# --- item 18/26: USProfile.extract_local_scope_definitions, the REAL seam
# --- (cycle-5 realignment) ---------------------------------------------
#
# CYCLE-5 REALIGNMENT (Planner, ruling P-R8/cycle-5 orders: "the Planner
# realigns ONLY the tests for [18c, citation grammar, P3 article-scope]").
# This class originally targeted `PRProfile.extract_local_scope_
# definitions` -- the M-R5 seam PROPOSAL ("PRProfile as a distinct class,
# the Spanish sibling of HebrewProfile"). That proposal was never adopted:
# the phase-2 blocker probe confirmed, live, that `get_profile("US-PR")`
# resolves to `USProfile(code="US-PR")` (`profiles.py:256`), and the real,
# merged seam is core's per-jurisdiction RULE REGISTRY -- `USProfile.
# extract_local_scope_definitions` (`us_profile.py:1162`) unions every
# registered `ScopeTriggerRule` for `"US-PR"` via `registry.scope_trigger_
# rules_for(self.code)`. `PRProfile` is NOT registered anywhere and is
# UNREACHABLE from `get_profile` -- exactly the M-R5-flagged residual risk
# materializing. Retargeting these 3 tests (not superseding-by-new-file,
# unlike `test_pr_profile_scope.py` -> `test_pr_profile_scope_cycle4.py`)
# is deliberate: the old interface is unreachable BY CONSTRUCTION, not a
# case of weakening an assertion to fit current behavior -- leaving them
# RED via `AttributeError` against a class that will never be wired would
# be a permanently un-closeable trap, the same "wiring test, not a
# dispatch test" anti-pattern P-R8 itself exists to name. Same behavioral
# assertions, corrected entry point.
#
# Reachable via a NEW rule module the Developer creates, `backend/app/
# definition_links/rules/us_pr_scope_triggers.py` (item 26), registering
# THREE `ScopeTriggerRule`s for `jurisdiction_codes=("US-PR",)` -- one
# wrapping `extract_local_definitions` (widened per items 18a/QA
# findings), one wrapping `extract_adhoc_definitions` (unchanged), one
# wrapping the NEW `extract_inline_local_definitions` (item 18c) --
# mirroring `rules/il_scope_triggers.py`'s exact registration shape
# (`ScopeTriggerRule` is a union kind: every matching rule's candidates
# survive). Today NONE of the three are registered, so `USProfile.
# extract_local_scope_definitions` (which DOES already exist, merged)
# returns `[]` for everything -- RED via a real behavioral assertion
# failure (`len(matching) == 1` on an empty list), not an AttributeError/
# ImportError, per this cycle's own "meaningful failure" standard.


class TestExtractLocalScopeDefinitionsSeam:
    """RED via a behavioral assertion failure (empty result) -- `USProfile.
    extract_local_scope_definitions` exists (merged core seam) but no
    `ScopeTriggerRule` is registered for `"US-PR"` yet. See the module
    comment above for the cycle-5 realignment from the dead `PRProfile`
    interface onto the real, live `get_profile("US-PR")` path."""

    def test_unions_the_local_trigger_extractor(self, qa_rows):
        """QA finding 1's `se define "X" como` lead-in
        (`STATE_PR_LEY_20_2017_ART4_14`) must be reachable through the
        SEAM method, not just the bare module function."""
        from app.definition_links.profiles import get_profile

        row = qa_rows["STATE_PR_LEY_20_2017_ART4_14"]
        profile = get_profile("US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        matching = [c for c in candidates if "toque de queda" in c.terms]
        assert len(matching) == 1
        assert matching[0].scope == "local"

    @pytest.mark.xfail(
        reason=(
            "Item 18c (extract_inline_local_definitions) is DEFERRED by "
            "ruling M-R13 / program Option D -- see the module docstring's "
            "`## CYCLE-5 STATUS` section. `USProfile.extract_local_scope_"
            "definitions` already unions every registered ScopeTriggerRule "
            "for 'US-PR' (that seam is live), but no rule wraps "
            "extract_inline_local_definitions yet because the function "
            "itself is deliberately not built this cycle, so the union "
            "returns no candidate for this row. STANDING DUTY once core's "
            "dispatch lands and this function is built and registered: QA "
            "must empirically RE-RUN the canonical-leak measurement "
            "against the dispatched pipeline to confirm the by-"
            "construction claim -- never assume it holds."
        ),
        strict=True,
        raises=AssertionError,
    )
    def test_unions_the_new_inline_scan(self, pr_rows):
        """DEFERRED (18c, ruling M-R13 / program Option D) -- the item-18c
        inline scan's own real row must eventually be reachable through the
        seam method too, proving the union covers all three sources, not
        just `extract_local_definitions`. Marked `xfail(strict=True,
        raises=AssertionError)`; not built this cycle by design."""
        from app.definition_links.profiles import get_profile

        row = pr_rows["STATE_PR_RENTAS_SEC1071_07"]
        profile = get_profile("US-PR")
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
        from app.definition_links.profiles import get_profile

        row = cycle3_rows["STATE_PR_LEY_214_2004_ART2"]
        profile = get_profile("US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        assert not any("se refiere a ambos géneros" in " ".join(c.terms) for c in candidates)
