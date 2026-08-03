"""RED (and explicitly DEFERRED-pending-core-seam) tests for gate P3 "Scope
stamped/enforced for Spanish scope phrases" -- sprint 2026-08-04-defs-us-pr.

As of this sprint's planning pass, `2026-08-04-defs-core-scope` (the
program's critical-path sprint) had NOT YET published its `## Seam spec`
section (polled via `git fetch origin && git show origin/claude/defs-core-
scope:...` -- see the sprint contract's `## Core seam coordination` section
and this file's own module-level marks below). Core's gates C2/C3 own HOW
scope-trigger phrases dispatch through a profile (`_CHAPTER_SCOPE_TRIGGERS`
today is a Hebrew-only literal tuple living in `pipeline.py`, not
profile-dispatched at all -- recon dossier §1). This sprint's Coordination
clause: "if P3 cannot be fully wired before core lands, still author the
test and mark it clearly ... and tell me, so I can sequence it" -- these
tests do exactly that: every test below is marked `xfail(strict=False)` with
an explicit reason, NOT a hard failure, so a full test-suite run does not
block on an interface that does not exist yet program-wide (not just for
this sprint).

What IS measured and ready for whoever implements C2 (real corpus counts,
`## Spanish idiom survey (measured)` in the sprint contract):

  - Within canonical Definiciones sections, the scope-setting phrase is
    overwhelmingly LAW-WIDE: "Para propósitos de (general)" 98 rows, "A los
    efectos de (general)" 48, "Para propósitos de esta Ley" 65, "A los
    fines de esta Ley" 51 (measured against the 635 real canonical rows).
  - CHAPTER-scope is rare but real: "A los efectos de este Capítulo" (5),
    "A los fines de este Capítulo" (2) -- `STATE_PR_LEY_77_1957_ART30_020`
    (already vendored, see `test_pr_profile_extraction.py`) is a real
    example, opening "A los fines de este Capítulo, ...".
  - ARTICLE-scope (`"local"`) NEVER appears as a canonical section's own
    scope-setter (0/635 for "A los fines/efectos/propósitos de este
    Artículo" inside a canonical section) -- it is instead the domain of
    the AD-HOC definitions extracted by `extract_local_definitions`
    (`test_pr_profile_ad_hoc_definitions.py`), a clean, corpus-confirmed,
    mutually-exclusive split between "which extraction path produces which
    granularity" -- exactly mirroring the Hebrew section-heading vs.
    local-trigger split.

Interface tested below (`determine_chapter_scope`) is the Planner's
PROPOSAL for what a Spanish analog of `pipeline._determine_scope`/
`_CHAPTER_SCOPE_TRIGGERS` would look like -- NOT a confirmed core seam
interface (none is published as of this sprint's planning pass). Whoever
implements C2 may choose a different shape (e.g. a `chapter_scope_triggers`
tuple attribute core's own `_determine_scope` consults, rather than a
profile-owned `determine_scope` method) -- these tests exist to hand the
core Planner/Developer a concrete, corpus-grounded Spanish trigger list to
build against, not to freeze the exact method signature.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.xfail(
    reason=(
        "P3 depends on core sprint 2026-08-04-defs-core-scope's C2 seam "
        "(profile-dispatched scope triggers), not yet published as of this "
        "sprint's planning pass (git show origin/claude/defs-core-scope:"
        "docs/sprint/sprints/2026-08-04-defs-core-scope.md had no "
        "'## Seam spec (published)' section body at poll time). Re-run "
        "once core publishes and this sprint aligns to the real interface."
    ),
    strict=False,
    raises=(ImportError, ModuleNotFoundError, AttributeError),
)


def test_chapter_scope_trigger_is_recognized_on_the_real_fixture_row():
    from app.definition_links.pr_profile import determine_chapter_scope

    body = (
        "A los fines de este Capítulo, los siguientes términos y frases "
        "tendrán el significado que se indica a continuación: (a) "
        "“Asegurador”: Significa entidad dedicada..."
    )
    assert determine_chapter_scope(body) == "chapter"


def test_law_wide_is_the_default_when_no_chapter_trigger_is_present():
    from app.definition_links.pr_profile import determine_chapter_scope

    body = (
        "Para propósitos de esta Ley, los términos que a continuación se "
        "indican tendrán el siguiente significado: a. “Agencia "
        "Gubernamental”: cualquier departamento..."
    )
    assert determine_chapter_scope(body) == "law-wide"


@pytest.mark.parametrize(
    "trigger_phrase",
    [
        "A los fines de este Capítulo",
        "A los efectos de este Capítulo",
        "En este Capítulo",
    ],
)
def test_each_measured_chapter_scope_trigger_variant_is_recognized(trigger_phrase):
    from app.definition_links.pr_profile import determine_chapter_scope

    body = f'{trigger_phrase}, "Término" significa una definición de prueba.'
    assert determine_chapter_scope(body) == "chapter"


def test_article_scope_phrases_never_set_whole_section_scope_to_local():
    """"A los fines de este Artículo" measured 0/635 times as a canonical
    Definiciones section's own opening scope-setter (article-scope is the
    ad-hoc extractor's domain, not the section extractor's) -- a
    well-designed `determine_chapter_scope` must not treat it as
    chapter-or-narrower and must not itself ever return "local" (that
    granularity is only ever produced by `extract_local_definitions`)."""
    from app.definition_links.pr_profile import determine_chapter_scope

    body = 'A los fines de este Artículo, "vehículo" incluye motocicletas.'
    assert determine_chapter_scope(body) != "local"
