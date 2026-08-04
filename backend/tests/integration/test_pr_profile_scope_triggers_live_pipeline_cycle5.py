r"""Cycle-5 Planner, item 26 (gates P2, P-R8 cycle-5 orders): live-path
`run_definition_linking` proof for the PR `ScopeTriggerRule` seam, PLUS
ruling M-R12's required guard + invariance proof for item 18c's
whole-body quoted-idiom sweep.

Unlike `test_pr_profile_local_scope_definitions_cycle4.py` (profile-
method level, `get_profile("US-PR")` direct), every test here drives the
REAL production entry point, `run_definition_linking`, over a REAL
DB-backed matter -- the strongest live-path proof available, mirroring
core's own `test_definition_links_pipeline_scope_seam.py` discipline.

Reaches a NEW rule module the Developer creates, `backend/app/
definition_links/rules/us_pr_scope_triggers.py`, registering THREE
`ScopeTriggerRule`s for `jurisdiction_codes=("US-PR",)`:
  - one wrapping `extract_local_definitions` (widened per items 18a/QA
    findings -- already RED-pinned at the pure-function level in
    `test_pr_profile_qa_cycle4_findings.py`, not re-pinned here);
  - one wrapping `extract_adhoc_definitions` (unchanged);
  - one wrapping the NEW `extract_inline_local_definitions` (item 18c),
    which must itself open with the M-R12 body-based guard specified
    below BEFORE running its whole-body `finditer` sweep.

## Ruling M-R12's guard (measured against the real `us_pr_statutes.parquet`,
full method + numbers in the panel log's cycle-5 Planner entry)

`RuleContext` carries no heading, and `pipeline.py`'s `else` branch is
what calls `extract_local_scope_definitions` -- today EVERY PR row,
including the ~633 canonical `Definiciones` sections, reaches it (no
`HeadingRule` dispatch yet). Measured: of item 18c's naive unguarded
sweep, 913 hits land in 117/633 (18.5%) of the REAL canonical rows -- a
population D-PR-18c's 889-hit/96-100%-precision sample never covered
(that sample explicitly excluded every canonical-headed row). Required
guard (`_opens_with_broader_than_article_scope_preamble`, checked against
`article_body.strip()[:300]` BEFORE the whole-body sweep runs -- bails
with `[]` for the WHOLE body when true):

    _BROAD_SCOPE_NOUN = r"(?:esta\s+Ley|este\s+C[oó]digo|este\s+Cap[ií]tulo"
                        r"|este\s+Subt[ií]tulo|este\s+T[ií]tulo|esa\s+Ley)"
    match ANY of, case-insensitive, anchored to the first 300 chars:
      1. (términos|vocablos|palabras|frases|conceptos) ... (tendrá(n)|
         tiene(n)) (el|los|un) (significado(s)|contenido)
      2. Según (se emplea(n)|se usa(n)|se utiliza(n)|utilizados|
         empleados) ... en <BROAD_SCOPE_NOUN>
      3. (Para|A) (los)? (fines|efectos|propósitos) (de)? de
         <BROAD_SCOPE_NOUN>

Deliberately keyed on a BROAD-scope noun (Ley/Código/Capítulo/Subtítulo/
Título), NEVER "este Artículo/párrafo/inciso/sección" -- that vocabulary
is item 18a's OWN local-scope trigger territory (`extract_local_
definitions`), not overlapping. Measured effect: suppresses 79/117
canonical leaks (all 3 patterns combined) AND correctly excludes rows
that are non-canonical by HEADING but self-announce a broader-than-
article scope in their own body (these were never safe "local" captures
to begin with, regardless of heading) -- net genuine recall cost on the
real, sampled 889/872-hit population: ~0 rows lose a legitimately-local
capture; the 27 non-canonical rows the guard also suppresses were
mis-scoped-if-kept, not a loss.

**Documented residual, NOT eliminated (real, measured, accepted -- same
discipline as the Bucket-D residue table):** 38/633 canonical rows still
leak after this guard -- bodies with NO preamble sentence at all (a bare
single-entry definition occupying near enough the whole body, or a
marker-list that opens immediately with `(a) "Term" significa...`, no
lead-in). Genuinely undecidable from body content alone without the
heading (item 1's own HELD territory). Planner's judgment call, flagged
for veto: these residual captures are MECHANICALLY INERT, not merely
narrower-than-ideal -- `matcher.py`'s `_is_own_defining_entry` exclusion
means the defining sentence itself is never counted as a "use", and a
single-sentence-body article has no OTHER position for the term to be
"used" at, so no USES_DEFINITION assertion is ever wrongly created from
one; once item 1 (HELD) eventually adds the correct law-wide row for the
SAME term, D-E1 narrowest-governs lets both coexist safely (the local row
just narrows THIS article's own self-mentions, never suppresses the
broader one elsewhere).

**AMENDED, cycle-5 Planner re-partition pass (ruling M-R13 / program
Option D overrules the paragraph above):** the acceptance described above
was Option A ("ship the 38-row residual as an accepted inert capture").
The program manager overruled Option A once the inertness premise was
found FALSE for 29/38 of these rows (467 wrongly-scoped `USES_DEFINITION`
assertions, see the panel log's cycle-5 verification entry) and ruled
Option D instead: item 18c (`extract_inline_local_definitions`, the
function that would have produced this capture) is **not built this
cycle at all**, and ships only once core's dispatch sprint lands and
canonical rows route to `pipeline.py`'s `if` branch, never reaching this
seam again -- at which point the residual problem (for ALL 38 rows, not
just the 9 that stayed genuinely inert) disappears by construction. The
paragraph above is kept as the historical record of what the guard was
originally built to bound, not as the current shipped behavior.
`test_documented_residual_...` below was INVERTED (not deleted) by that
same re-partition pass: it now asserts the row is NOT captured, which is
vacuously true today (nothing registered can capture it) and becomes a
real regression guard once 18c is eventually built and registered --
proving the by-construction claim holds even then. A permanently-red test
asserting the overruled Option-A behavior is exactly the misleading-
artifact class ruling P-R8 taught this panel to distrust.

## Invariance requirement (M-R12 point 3)

The guard is a property of `extract_inline_local_definitions` itself,
checked unconditionally from the body text -- NOT conditioned on which
branch of `pipeline.py` called it. This makes its output identical
whether it runs from today's `else` branch (canonical headings
unrecognized) or, after core's dispatch lands and canonical rows reroute
to the `if` branch, never reaches this function again at all (its own
`if is_definitions_heading(...)` gate short-circuits first). Both worlds
agree: a canonical-preamble-shaped body is NEVER captured as
`scope="local"` by this function. `test_the_inline_sweep_bails_on_a_real_
canonical_definiciones_body_...` pins this as an unconditional property of
the function/rule, independent of dispatch plumbing -- the same assertion
holds true regardless of which branch reaches it.
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
def pr_rows_cycle2():
    return _load("pr_sample_rows_cycle2.json")


@pytest.fixture()
def pr_rows_cycle3():
    return _load("pr_sample_rows_cycle3.json")


def test_run_definition_linking_captures_a_real_local_scope_definition_via_the_registered_pr_rules_live(
    db_session, matter_with_users, pr_rows_cycle1
):
    """`STATE_PR_LEY_85_2018_ART9_04` (real, already vendored cycle 1):
    'A los fines de este Artículo "cualquier tipo de arma" incluye...' --
    a genuine article-scoped Spanish local definition. Proves the REAL
    `run_definition_linking` path reaches `extract_local_definitions`
    through the NEW registered `ScopeTriggerRule`, not just a direct
    profile-method call."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = pr_rows_cycle1["STATE_PR_LEY_85_2018_ART9_04"]
    wiki_text = f"@ 9.04. {row['section_title']}\n{row['text']}\n"
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test PR Statute (item 26 live proof)",
        wiki_text=wiki_text,
        jurisdiction="US-PR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    matching = [d for d in result["created_definitions"] if "cualquier tipo de arma" in d["terms"]]
    assert len(matching) == 1, (
        "the real 'A los fines de este Artículo' local definition must be "
        "captured through the REAL run_definition_linking path once the "
        "PR ScopeTriggerRule is registered -- got "
        f"created_definitions={result['created_definitions']!r}"
    )
    assert matching[0]["scope"] == "local"


def test_the_inline_sweep_bails_on_a_real_canonical_definiciones_body_even_though_it_currently_reaches_the_else_branch_live(
    db_session, matter_with_users, pr_rows_cycle2
):
    """Ruling M-R12's guard, proven live: `STATE_PR_LEY_214_1995_ART2`
    (real, already vendored cycle 2) is a genuine CANONICAL Definiciones
    section (15 real terms, law-wide scope) whose body opens 'Para
    propósitos de esta ley, los siguientes términos tendrán el
    significado...'. Because `USProfile.is_definitions_heading` returns
    False for every Spanish heading today (no `HeadingRule` dispatch),
    this article reaches the SAME `else` branch item 18c's rule lives in
    -- without the guard, its naive whole-body sweep would fire on this
    body's own `"Activos líquidos" Aquellos activos...`-shaped entries
    and wrongly stamp `scope="local"` on law-wide definitions (the exact
    Option-C-shaped defect the program manager rejected). With the guard,
    NONE of this body's real terms may be captured as `scope="local"` by
    this article's own extraction -- proving the guard fires on the REAL
    live path, not merely in isolation."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = pr_rows_cycle2["STATE_PR_LEY_214_1995_ART2"]
    # Deliberately a GENERIC, non-"Definiciones" heading -- proving the
    # guard is BODY-based (the only signal `RuleContext` can ever carry),
    # not secretly relying on the heading text this test intentionally
    # withholds.
    wiki_text = f"@ 2. Artículo 2.\n{row['text']}\n"
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test PR Statute (M-R12 guard proof)",
        wiki_text=wiki_text,
        jurisdiction="US-PR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    local_scoped_terms = {
        term
        for d in result["created_definitions"]
        if d["scope"] == "local"
        for term in d["terms"]
    }
    real_canonical_terms = {
        "Activos líquidos",
        "Agente",
        "Comisionado",
        "Financiamientos",
        "Prestamista",
        "Préstamos",
    }
    leaked = local_scoped_terms & real_canonical_terms
    assert not leaked, (
        "the M-R12 guard must bail on a real canonical Definiciones-block "
        "body BEFORE the whole-body sweep runs -- these law-wide terms "
        f"were wrongly captured as scope=local: {leaked!r} (full "
        f"created_definitions={result['created_definitions']!r})"
    )


def test_documented_residual_a_single_bare_canonical_definition_is_not_captured_as_local_scope_live(
    db_session, matter_with_users, pr_rows_cycle3
):
    """INVERTED by the Planner's cycle-5 re-partition pass (ruling M-R13 /
    program Option D). This test used to assert the OPPOSITE -- that
    `STATE_PR_LEY_133_1979_ART1`'s bare 'El término "equipo solar"
    significa...' body (real, already vendored cycle 3; canonical heading
    'Artículo 1. Definiciones', no preamble sentence at all) IS captured
    as `scope="local"` (Option A: ship the 38-row residual as an accepted
    inert capture). The program manager overruled Option A once the
    inertness premise was measured FALSE for 29/38 of the residual rows
    (467 wrongly-scoped `USES_DEFINITION` assertions -- see the panel
    log's cycle-5 verification entry) and ruled Option D: item 18c
    (`extract_inline_local_definitions`, the sweep that produced this
    capture) is NOT built this cycle at all. A permanently-red test
    asserting the overruled Option-A behavior is exactly the misleading-
    artifact class ruling P-R8 taught this panel to distrust, so it is
    inverted here to the honest assertion rather than left red or quietly
    deleted (deleting would erase the record of why this specific row
    matters and what it must keep proving later).

    ## Status: VACUOUS TODAY -- states the condition that makes it real

    Nothing currently registered for `"US-PR"` can capture 'equipo solar'
    as local scope at all (no rule reaches this shape), so `not matching`
    holds trivially -- this assertion is not yet proving anything live.
    It becomes a REAL regression guard once BOTH land: (1) core's
    dispatch sprint merges, and (2) a future cycle builds and registers
    `extract_inline_local_definitions` (18c). Per Option D's own
    reasoning, by then canonical `Definiciones` rows route through
    `pipeline.py`'s `if` branch (via the Spanish `HeadingRule`, currently
    HELD) and never reach `extract_local_scope_definitions` at all -- so
    this row must STILL not be captured as local scope, even once the
    machinery that used to produce that capture exists again. If this
    assertion ever starts failing after 18c is rebuilt, that is a live
    signal the by-construction claim did NOT hold.

    ## Standing duty (ruling M-R13, not discharged by this test)

    This test alone does not satisfy M-R13's re-verification requirement
    -- it only proves ONE row stays uncaptured. Once core's dispatch
    lands and 18c is rebuilt and registered, QA must empirically RE-RUN
    the full canonical-leak measurement (all 117/633 canonical rows the
    naive sweep hit, per the M-R12 measurement archived in the panel log)
    against the DISPATCHED pipeline to confirm the by-construction claim
    holds for the whole population -- never assume it from this test
    alone.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = pr_rows_cycle3["STATE_PR_LEY_133_1979_ART1"]
    wiki_text = f"@ 1. Artículo 1.\n{row['text']}\n"
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test PR Statute (M-R13 inverted residual guard)",
        wiki_text=wiki_text,
        jurisdiction="US-PR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    matching = [d for d in result["created_definitions"] if "equipo solar" in d["terms"]]
    assert not matching, (
        "Option A (shipping this residual as an accepted local-scope "
        "capture) was overruled by ruling M-R13 / program Option D -- "
        "'equipo solar' must NOT be captured as scope=local by the "
        "currently-registered PR rules. This assertion is vacuous today "
        "(nothing registered can capture it at all) and becomes a real "
        "guard once item 18c is rebuilt post-dispatch -- see this test's "
        f"own docstring. Got created_definitions={result['created_definitions']!r}"
    )
