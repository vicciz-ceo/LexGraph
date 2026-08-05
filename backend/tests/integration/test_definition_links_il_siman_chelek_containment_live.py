"""Sprint 2026-08-04-defs-il (program 2026-08-04-definition-completeness),
Phase D, Planner D-1b. New RED tests for the old E1 escalation: סימן/חלק
structural-unit CONTAINMENT (not mere capture -- `il_siman_chelek_scope_
triggers.py` already captures `scope="siman"`/`"chelek"` `Definition` rows;
this file is about whether a `USES_DEFINITION` edge links a genuine mention,
which it does not today).

## Why this file exists now, and not in an earlier phase

`il_siman_chelek_scope_triggers.py`'s own docstring (unedited by this
Planner -- read, not touched) records the original reason no containment
RED was ever written: `matcher._in_scope`'s generic branch reads
`article.structural_units`, which "no rule in this sprint populates and
which a real production `MatcherArticle` never carries." Per this Phase's
brief, core's dispatch sprint (`2026-08-04-defs-core-dispatch`, merged to
this branch) was expected to have retired that reason by making
`StructuralUnitRule` live. **Re-confirmed live before writing this file
(ruling M4 -- leads are not proof), with a mixed result, recorded
precisely because it changes what a Developer can actually build:**

1. **The CONSUMPTION machinery genuinely is live now** -- this is NOT
   inferred from the dispatch sprint's own summary, it is proven with a
   positive control on THIS branch, THIS session, end-to-end through
   `ingest_wiki_law` + `run_definition_linking`. A throwaway probe
   (`backend/tests/integration/zzz_d1b_probe.py`, deleted before this
   commit, never pushed -- same discipline as prior QA cycles' own
   throwaway probes) registered a fake IL `StructuralUnitRule` that
   hardcodes article->siman membership PLUS a fake `ScopeTriggerRule` that
   stamps a real `scope_value` (see point 2 for why the real, shipped rule
   cannot), then ran the real pipeline against a tiny synthetic law with
   one siman-scoped definition and two mentions -- one inside the same
   siman, one in a different siman of the same law. Result (this
   session's transcript): the SAME-siman mention got a `USES_DEFINITION`
   edge (`'Article 2 uses the definition of "מונח_בדיקה".'`); the
   DIFFERENT-siman mention got none. `matcher._in_scope`'s generic branch
   and `pipeline.py`'s `structural_units` population site
   (`ScopeUnit("chapter", ...)` plus every registered `StructuralUnitRule`'s
   contribution, per M-D1) are therefore proven reachable and CORRECT when
   given data, not merely "wired but untested."

2. **But no rule -- ScopeTriggerRule OR StructuralUnitRule -- has any live
   DATA SOURCE for סימן/חלק identity today, on either side of the
   comparison.** This is the actual, load-bearing finding, more precise
   than "nothing consumes structural_units" (that part is fixed):
   - `StructuralUnitRule.derive` receives only a `StructuralContext
     (article_number, heading_breadcrumbs)` (`rules/registry.py`).
     `heading_breadcrumbs` is hardcoded `()` at pipeline.py's ONE
     production call site (`pipeline.py:212`, comment: "No above-article
     breadcrumb source is threaded through to this per-run pass yet...
     `heading_breadcrumbs` stays `()`; a family panel's own rule is free
     to derive purely from `article_number`, or escalate for a breadcrumb
     column when it actually needs one" -- this file IS that escalation,
     see the sprint log). Deriving siman/חלק membership from
     `article_number` alone is not possible in general (article numbers do
     not encode their enclosing סימן/חלק).
   - The analogous "stamp it yourself" path that WORKS for `scope="chapter"`
     (`il_chapter_scope_triggers.py` stamps `source_chapter=ctx.chapter`,
     because `RuleContext.chapter` IS populated, from `sections.py`'s own
     `==`-depth chapter tracking) has no equivalent for סימן/חלק:
     `RuleContext` carries `article_number`, `chapter`, `unit_path` (the
     LAST always `()` at extraction time, and BELOW-article-only by
     design, v2.4 §1) -- nothing carries סימן/חלק identity either.
   - Root cause, traced to `sections.py` (frozen, unedited, read only):
     `_HEADING_BREAK_RE` matches any `={2,}` break and ends the current
     article's body scope for ALL of them, but only a literal 2-equals
     break updates `current_chapter`
     (`if len(break_match.group(1)) == 2: current_chapter = ...`) -- a
     3-or-more-equals break's own heading TEXT (`break_match.group(2)`) is
     read, then thrown away. `ingest_wiki_law` -> `models.article.Article`
     persists only `.number`/`.heading`/`.chapter`; no trace of any
     enclosing סימן/חלק ever reaches the ORM row, so there is nothing for
     `pipeline.py` to thread into `StructuralContext` even if it wanted to.
   - **A real corpus complication found while building this file's own
     fixture, recorded per M-D3's "measured convention, not analogy":**
     nesting depth for חלק is NOT uniform. In most laws (e.g. this file's
     own חלק fixture's outer heading chain) חלק sits ABOVE סימן, but
     `תקנות המשקלות והמידות` nests `==== חלק N ====` (4 equals) INSIDE
     `=== סימן ... ===` (3 equals) inside `== פרק ... ==` (2 equals) --
     the reverse of the usual convention. Any future breadcrumb-capture
     fix must record FULL depth-ordered breadcrumbs, not assume a fixed
     סימן/חלק ordering.

**Conclusion carried to the manager (not decided here):** making these two
tests pass is NOT rule-module-only work, unlike D-1a's three bugs or the
already-shipped chapter-scope containment. It needs FROZEN-file changes
(`sections.py` to capture full-depth heading breadcrumbs instead of
discarding anything past 2 equals-signs; `pipeline.py` to thread real
breadcrumbs into `StructuralContext` instead of the hardcoded `()`; very
likely a new persisted column on `models.article.Article`, exactly the
"escalate for a breadcrumb column when it actually needs one" case
`pipeline.py`'s own comment anticipates) -- outside a rule-module Developer's
authorized scope per this sprint's established discipline (M14 and D-1a's
own "a claim that one IS needed escalates rather than proceeding"). See the
sprint log for the full escalation.

## Why each test asserts BOTH directions together, not as two separate tests

Following the Phase C Planner's own established, manager-approved
precedent (round 2's M16 log entry): when a scope kind's containment is
COMPLETELY unbuilt, a standalone "does NOT leak into a different unit"
assertion is trivially true today for the WRONG reason (nothing links
ANYWHERE yet) -- a vacuous pass, not a meaningful RED. Combining both
directions into one test keeps the test genuinely RED now (the
same-unit-linking half fails for a real, load-bearing reason) while still
pinning the non-leakage half as part of what "green" must mean once this is
built, so a future fix cannot satisfy this test by over-linking either.

## Fixtures

Both are real, unedited, byte-verified corpus excerpts (verified this
session, non-adjacent-article assembly per the established
`il_phaseC_plan_m16_multi_fixture_builder.py` method -- each span
independently confirmed a literal substring of its own source file, then
concatenated; see the sprint log for the verification transcript):

- `חוק לקידום תשתיות לאומיות_siman_containment_excerpt.wiki` --
  `חוק לקידום תשתיות לאומיות, התשפ"ד-2024`, articles 8 (defining, סימן א':
  העתקת קו תשתית שאינו ממופה), 9 (same סימן א', genuine mention), and 22
  (סימן ב': העתקת תשתית תקשורת פסיבית -- a genuinely DIFFERENT סימן,
  genuine mention: "הוראות סימן זה לא יחולו לגבי תשתית פסיבית שהיא קו
  תשתית שאינו ממופה כהגדרתו בסעיף 8" -- article 22 explicitly
  cross-references article 8's own definition while stating its OWN
  סימן's rules do not apply to it, real corpus text, not fixture-author
  prose).
- `תקנות המשקלות והמידות_chelek_containment_excerpt.wiki` --
  `תקנות המשקלות והמידות`, articles 72 (defining, פרק ה' > סימן ג' > חלק 1
  - מכונת שקילה לשימוש אישי וביתי), 73 (same חלק 1, genuine mention: "...
  תדירות הבקרה המטרולוגית למכונת שקילה..." -- matches the term's
  construct-state surface variant, confirmed live via
  `matcher.find_term_uses`), and 47 (פרק ד' > סימן ב': כללי -- a
  genuinely different פרק AND סימן AND חלק, genuine mention: "תדירות
  בקרה מטרולוגית למשקולת מטרית תהיה כמפורט להלן").
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_besiman_zeh_scoped_definition_containment_holds_in_both_directions_live(
    db_session, matter_with_users
):
    """`בסימן זה, "term" - definition` (article 8) should link article 9
    (same סימן א') and must NOT link article 22 (סימן ב', a genuinely
    different structural unit of the same law) even though article 22
    genuinely uses the same term string.

    Live re-confirmation (this Planner, before writing this test):
    `il_siman_chelek_scope_triggers.py`'s real, unmodified `_extract`
    correctly captures a `Definition(terms=("קו תשתית שאינו ממופה",),
    scope="siman", scope_value=None)` from article 8's real body -- CAPTURE
    already worked before this test (item 2b, shipped). Today's live
    `run_definition_linking` on this exact fixture produces ZERO
    `USES_DEFINITION` edges for this term at all (neither article 9 nor
    article 22) -- `_in_scope`'s generic branch never finds a matching
    `"siman"` unit in `article.structural_units` (only `"chapter"` is ever
    stamped there today, see `pipeline.py`), and even if it did,
    `scope_value=None` could never match any real unit's `.value` (see
    this file's module docstring). This test asserts the CORRECT target
    behavior, not today's behavior -- it is expected RED.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק לקידום תשתיות לאומיות, התשפ"ד-2024',
        wiki_text=_read("חוק לקידום תשתיות לאומיות_siman_containment_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    term_defs = [
        d for d in result["created_definitions"] if "קו תשתית שאינו ממופה" in d["terms"]
    ]
    assert len(term_defs) == 1, (
        f'expected exactly one siman-scoped Definition row for "קו תשתית '
        f'שאינו ממופה" (article 8); got {result["created_definitions"]!r}'
    )
    assert term_defs[0]["scope"] == "siman", term_defs[0]

    uses_props = [
        a["proposition"]
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert any("Article 9" in p for p in uses_props), (
        f"expected article 9 (same סימן א' as the defining article 8) to "
        f"get a USES_DEFINITION edge for the genuine mention of "
        f'"קו תשתית שאינו ממופה" in its own body; got {uses_props!r}'
    )
    assert not any("Article 22" in p for p in uses_props), (
        f"expected article 22 (סימן ב', a DIFFERENT structural unit of "
        f"the same law) to get NO USES_DEFINITION edge for its own genuine "
        f'mention of "קו תשתית שאינו ממופה" -- a סימן-scoped definition '
        f"must not leak across סימן boundaries; got {uses_props!r}"
    )


def test_bechelek_zeh_scoped_definition_containment_holds_in_both_directions_live(
    db_session, matter_with_users
):
    """`[[סימן משנה זה|בחלק זה]], "term" - definition` (article 72, a
    wikilink-aliased trigger -- the display text resolves to `בחלק זה`
    after `strip_wikilinks`, confirmed live) should link article 73 (same
    חלק 1) and must NOT link article 47 (a genuinely different פרק/סימן/
    חלק of the same document) even though article 47 genuinely uses a
    surface variant of the same term.

    Live re-confirmation (this Planner, before writing this test): article
    73's real body contains "תדירות הבקרה המטרולוגית" -- the construct-
    state-plus-prefix surface variant of "בקרה מטרולוגית"
    (`matcher._surface_variants` covers this: the ה-inserted construct
    form "בקרה המטרולוגית" plus a stacked ה-prefix on the first word --
    confirmed live via `matcher.find_term_uses("בקרה מטרולוגית", ...)`
    returning one hit, span "הבקרה המטרולוגית"). Article 47's real body
    contains the bare term "בקרה מטרולוגית" directly. Today's live
    `run_definition_linking` on this exact fixture produces ZERO
    `USES_DEFINITION` edges for this term (same root cause as the סימן
    test above -- see this file's module docstring). Expected RED.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="תקנות המשקלות והמידות",
        wiki_text=_read("תקנות המשקלות והמידות_chelek_containment_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    term_defs = [d for d in result["created_definitions"] if "בקרה מטרולוגית" in d["terms"]]
    assert len(term_defs) == 1, (
        f'expected exactly one chelek-scoped Definition row for "בקרה '
        f'מטרולוגית" (article 72); got {result["created_definitions"]!r}'
    )
    assert term_defs[0]["scope"] == "chelek", term_defs[0]

    uses_props = [
        a["proposition"]
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert any("Article 73" in p for p in uses_props), (
        f"expected article 73 (same חלק 1 as the defining article 72) to "
        f"get a USES_DEFINITION edge for its genuine (construct-state) "
        f'mention of "בקרה מטרולוגית"; got {uses_props!r}'
    )
    assert not any("Article 47" in p for p in uses_props), (
        f"expected article 47 (a DIFFERENT פרק/סימן/חלק of the same "
        f"document) to get NO USES_DEFINITION edge for its own genuine "
        f'mention of "בקרה מטרולוגית" -- a חלק-scoped definition must not '
        f"leak across חלק boundaries; got {uses_props!r}"
    )
