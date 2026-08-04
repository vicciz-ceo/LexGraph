"""Cycle-4 Planner tests, item 25 -- P3 xfail -> real RED conversion
(sprint 2026-08-04-defs-us-pr, gate P3).

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
