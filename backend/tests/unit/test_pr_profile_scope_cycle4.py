"""Cycle-4 Planner tests, item 25 -- P3 xfail -> real RED conversion
(sprint 2026-08-04-defs-us-pr, gate P3).

## RETIRED (ruling M-R17, 2026-08-05) -- superseded-not-edited, skipped not deleted

**What these 6 tests were written to prove**: that a `PRProfile` class,
called directly (`PRProfile(code="US-PR").determine_scope(body)`), resolves
Spanish chapter-scope trigger phrases correctly (4 distinct behaviors: the
real-fixture-row positive, the law-wide default, 3 named trigger-phrase
variants, and the article-scope-never-local guard).

**Why they could never have gone green.** Confirmed this cycle (and
independently reconfirmed by the cycle-9 Planner, whose docstring this
one's reasoning matches): the seam question was SETTLED, before this
method was ever written, AGAINST the distinct-`PRProfile`-class proposal
(sprint contract `## Coordination`: "PR ships as `USProfile`-hosted rule
modules"). `PRProfile` (`pr_profile.py`) has no `determine_scope` method at
all and is never instantiated anywhere in `backend/app/` outside its own
module; `get_profile("US-PR")` returns a `USProfile` instance that never
consults a `PRProfile`. No `ScopeKindRule` registration -- no registration
of any kind -- can make a method exist on a class the registry never
returns. These 6 tests target an interface that never existed and, per the
seam decision, never will; every failure below is `AttributeError`, forever,
regardless of what else ships.

**Where the substance lives now, live.** The SAME 4 behaviors these tests
assert, retargeted at the real seam
(`get_profile("US-PR").determine_scope`, dispatched through the registered
`ScopeKindRule`), are proven in
`backend/tests/integration/test_pr_profile_scope_kind_rule_live_cycle9.py`
-- see that file's own "## Supersedes `test_pr_profile_scope_cycle4.py` IN
SUBSTANCE, not in file" section for the exact mapping:
`test_chapter_scope_trigger_is_recognized_on_the_real_fixture_row` ->
`test_get_profile_us_pr_determines_chapter_scope_on_the_real_fixture_row_live`
(same real row, `STATE_PR_LEY_77_1957_ART30_020`);
`test_law_wide_is_the_default_when_no_chapter_trigger_is_present` ->
`test_get_profile_us_pr_defaults_to_law_wide_on_the_mandate_example_row_live`
(same real row, `STATE_PR_LEY_249_2003_ART3`);
`test_each_measured_chapter_scope_trigger_variant_is_recognized` ->
`test_each_named_chapter_scope_trigger_variant_is_recognized_live` (same 3
phrases); `test_article_scope_phrases_never_set_whole_section_scope_to_local`
-> `test_article_scope_phrase_never_yields_local_or_chapter_live` (same
guard, strengthened to also check `!= "chapter"`). Nothing this file once
covered is uncovered now.

**Mechanism chosen: `pytest.mark.skip`, not deletion.** The sprint's own
precedent for a superseded assertion is INVERSION-not-deletion
(`test_documented_residual_..._live` in
`test_pr_profile_scope_triggers_live_pipeline_cycle5.py`, ruling M-R13) --
"deleting would erase the record of why this specific row matters." That
precedent does not apply here unmodified: there is no opposite assertion to
invert to (an `AttributeError` has no meaningful negation), and unlike that
row, THESE 6 will never become live again under any future ruling this
seam decision allows. `pytest.mark.skip` (not `xfail`) is the honest
middle ground: `xfail` implies "might start passing," which is false by
construction here; leaving them RED forever is exactly the misleading-
permanently-red-artifact class ruling P-R8 taught this panel to distrust
(a future reader greeping for `PRProfile` coverage would see 30 failures
and have to re-derive all of the above to learn it is not one of them).
A skip, with this reasoning attached, is discoverable in-place without
git archaeology and cannot be confused with an open defect. Full ruling
text and this retirement's own record: panel log, M-R17 section
(2026-08-05) and this cycle's Planner entry.

**Original module docstring, preserved verbatim below the divider for
provenance** (cycle-4 planning context, current as of when written --
"core has since published..." refers to the seam poll available AT cycle-4
time, itself since superseded by the settled seam decision above).

---

`test_pr_profile_scope.py` (cycle 1) authored 6 tests against a Planner-
PROPOSED interface, `determine_chapter_scope`, explicitly marked
`xfail(strict=False)` because core sprint `2026-08-04-defs-core-scope`
had not yet published ANY seam spec at cycle-1 planning time. That file
is left UNTOUCHED (superseded, not edited -- role separation: "do not
edit existing tests to fit").

Core has since published seam spec v2.4 (`origin/claude/defs-core-scope`
@ `6de6d6e`): the REAL Protocol method is `determine_scope(self,
body_text: str) -> str` (spec v1, unchanged through v2.4), not the
Planner's cycle-1 placeholder name. Per ruling M-R11's sequencing
instruction, this file converts the SAME 4 scope-trigger assertions to
target the real seam method name, as genuine (non-xfail) RED tests. Core
is not yet merged to `origin/main` and this branch has not rebased, so
`PRProfile` has no `determine_scope` method yet -- every test below is
RED via `AttributeError`, which is EXPECTED and CORRECT per M-R11's own
words ("tests referencing the new profile methods will be RED against
the un-rebased tree -- that is expected and correct, not a planning
bug"), not a mistake to fix.

The measured trigger data these tests are built from (real corpus
counts) is unchanged from cycle 1's own survey, in the sprint contract's
`## Spanish idiom survey (measured)` / panel log: within canonical
Definiciones sections, CHAPTER-scope is real but rare ("A los efectos de
este Capítulo" 5, "A los fines de este Capítulo" 2 -- `STATE_PR_LEY_
77_1957_ART30_020`, already vendored cycle-1, is a real example);
ARTICLE-scope (`"local"`) never appears as a canonical section's OWN
scope-setter (0/635) -- that granularity belongs exclusively to
`extract_local_scope_definitions` (item 18), never to `determine_scope`.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason=(
        "RETIRED, ruling M-R17 (2026-08-05): targets PRProfile.determine_scope, "
        "an interface that never existed and never will (seam settled against "
        "the distinct-PRProfile-class proposal before this method was written; "
        "PRProfile is never instantiated in backend/app/ and get_profile('US-PR') "
        "returns USProfile). Substance covered live in "
        "test_pr_profile_scope_kind_rule_live_cycle9.py via get_profile('US-PR')"
        ".determine_scope -- see this file's module docstring for the exact "
        "per-test mapping. skip (not xfail) because there is no scenario under "
        "the settled seam in which these could start passing."
    )
)


def test_chapter_scope_trigger_is_recognized_on_the_real_fixture_row():
    from app.definition_links.pr_profile import PRProfile

    body = (
        "A los fines de este Capítulo, los siguientes términos y frases "
        "tendrán el significado que se indica a continuación: (a) "
        "“Asegurador”: Significa entidad dedicada..."
    )
    profile = PRProfile(code="US-PR")
    assert profile.determine_scope(body) == "chapter"


def test_law_wide_is_the_default_when_no_chapter_trigger_is_present():
    from app.definition_links.pr_profile import PRProfile

    body = (
        "Para propósitos de esta Ley, los términos que a continuación se "
        "indican tendrán el siguiente significado: a. “Agencia "
        "Gubernamental”: cualquier departamento..."
    )
    profile = PRProfile(code="US-PR")
    assert profile.determine_scope(body) == "law-wide"


@pytest.mark.parametrize(
    "trigger_phrase",
    [
        "A los fines de este Capítulo",
        "A los efectos de este Capítulo",
        "En este Capítulo",
    ],
)
def test_each_measured_chapter_scope_trigger_variant_is_recognized(trigger_phrase):
    from app.definition_links.pr_profile import PRProfile

    body = f'{trigger_phrase}, "Término" significa una definición de prueba.'
    profile = PRProfile(code="US-PR")
    assert profile.determine_scope(body) == "chapter"


def test_article_scope_phrases_never_set_whole_section_scope_to_local():
    """"A los fines de este Artículo" measured 0/635 times as a canonical
    Definiciones section's own opening scope-setter (article-scope is
    `extract_local_scope_definitions`'s domain, item 18) -- a
    well-designed `determine_scope` must not treat it as chapter-or-
    narrower and must not itself ever return "local"."""
    from app.definition_links.pr_profile import PRProfile

    body = 'A los fines de este Artículo, "vehículo" incluye motocicletas.'
    profile = PRProfile(code="US-PR")
    assert profile.determine_scope(body) != "local"
