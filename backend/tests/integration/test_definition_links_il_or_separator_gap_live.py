"""Sprint 2026-08-04-defs-il, Phase D, Planner (Sonnet/high, worktree
`defs-il-plan3`, branch `claude/defs-il-plan-sep`) -- RED tests for the
`או` ("or") / hyphenated-`ו-` multi-term list-entry separator gap the
panel manager found by direct probe after merging D-1a (log entry `##
2026-08-05 -- M25`). Per ruling M14, additive only: a NEW file, no
existing test edited, zero `backend/app` changes from this Planner.

**Root cause, live-confirmed (not inferred).** D-1a's `il_list_shape_
scope.parse_entry` ported the FROZEN `extract._find_split_dash`'s
dash-finding and `extract._parse_terms_and_qualifier`'s qualifier
tolerance, but did NOT port that same frozen function's separator
behaviour: `_parse_terms_and_qualifier` grabs EVERY quoted span in the
header regardless of what sits between them, so the definitions-SECTION
path (`extract_definitions_from_section`, used for `הגדרות`-headed
articles) already handles `או`/`ו-` correctly today. `parse_entry`'s own
`_TERM_SEP_RE = re.compile(r'(?:\\s*,\\s*ו?|\\s+ו)"([^"]+)"')` requires a
comma and/or a `ו` character DIRECTLY prefixed to the next quote -- `או`
(aleph-vav, "or") and the hyphenated `ו-` conjunction do not match this
pattern, so `parse_entry` silently stops after the FIRST term and treats
`או "term2"` / `ו-"term2"` as part of the "qualifier" it already
tolerates and discards. This is a SILENT PARTIAL miss (worse than the
pre-D-1a silent TOTAL miss): the entry no longer vanishes, so nothing
signals the second term was ever there.

**M18 compliance (binding, program law) -- independent denominator,
built from the ENTRY LINE, classified AFTER matching.** This Planner's
own corpus sweep (`il_or_sep_sweep_planner3.py`, scratchpad) does NOT
import `parse_entry` or `_TERM_SEP_RE` (the code under test); its only
reused production helper is `app.definition_links.sections.
parse_articles`/`is_definitions_heading` -- NOT part of the separator
bug, and it is literally the function `pipeline.py` itself calls to
decide whether an article's `:-`/`::-` entries reach the FROZEN
definitions-section path or the buggy list-shape `ScopeTriggerRule`
path. Every dash-finder, quote-scanner, separator-classifier, and
preamble/reach-scanner in this sweep is a fresh, independent
implementation (P-R7), including a deliberate re-implementation of both
list-shape rule modules' own `PREAMBLE_RE` + entry-scan loop, so
"reached by the list-shape scan" is measured structurally, not assumed.

Corpus-wide (6,133 files), `או` as a term separator between two quoted
spans in an entry's header:

```
total entry lines with an 'או' header-separator (any header shape):     243
  header has NO real standalone dash at all (excluded -- a DIFFERENT,
    already-named phenomenon: a `X` או `Y` כולל/כוללים.. grammar with
    no dash, same class as this sprint's own Class-B "no split marker"
    residual, not this bug):                                             20
  WITH a dash, inside a `הגדרות`/`הגדרת מונחים`/`הגדרה`/`הגדרות ופירוש`
    -headed article (routes to the FROZEN definitions-section path,
    already correct today -- extract._parse_terms_and_qualifier grabs
    every quoted span regardless of separator):                         181
  WITH a dash, in an ORDINARY (non-definitions-heading) article:          42
    of those, NOT reached by the list-shape scan loop at all (no
      preceding preamble line ending in a bare `-` found -- a SEPARATE,
      pre-existing miss unrelated to `או`; affects that article's
      SINGLE-term entries too, e.g. all of `חוק הפרשנות` art.3 and
      `פקודת הפרשנות` art.1, both real "Interpretation" articles whose
      own preamble line ends in `:` not `-`; out of this bug's scope,
      named here as an honest gap, not silently folded in):              26
    of those, REACHED by the list-shape scan (THE REAL GAP -- this is
      the number that matters, not the 230/160 upper bound the manager
      cited as a lead, and not the 243 raw total either):                16
      unique files contributing:                                          9
```

The hyphenated `ו-` conjunction (`"t1" ו-"t2"`, distinct from D-1a's
already-handled bare `ו"t2"` direct-prefix form):

```
total entry lines with a 'ו-' header-separator:                          37
  WITH a dash, inside a definitions-heading article (frozen, correct):   29
  WITH a dash, in an ordinary article, NOT reached:                       3
  WITH a dash, in an ordinary article, REACHED (THE GAP):                 4
    unique files:                                                         4
  header has no real dash at all (excluded):                              1
```

Both gaps (16 `או` + 4 `ו-` = 20 lines / 13 unique files) were then
LIVE-reconfirmed against `profile.extract_local_scope_definitions`
directly (own script, scratchpad) -- every single one of the 20 shows
the FIRST term captured and every subsequent term missing, exactly the
"silent partial" shape the manager's own probe demonstrated. Full
per-line output is in the scratchpad
(`il_or_sep_sweep_planner3.py`/`il_or_sep_gap_or.json`/
`il_or_sep_gap_vavhyphen.json`), not reproduced in full here for length.

**Cross-check against the D-1a Planner's own 392-line confirmed-missing
set (per the brief's explicit ask).** Reading D-1a's own sweep script,
still present in the shared scratchpad
(`il_d1a_classA_sweep.py`): its gap-validation regex for the separator
between two quoted spans is
`re.fullmatch(r'[,\\s]*(?:או|ו)?[\\s]*', gap)` -- this DOES match a gap of
`" או "` (empty `[,\\s]*`, then the literal alternative `או`, then
trailing `[\\s]*`), so D-1a's own denominator sweep counted `או`-joined
entries as "confirmed missing" ALONGSIDE the comma/vav ones -- but its
separator-BREAKDOWN accounting only tests `has_vav = bool(re.search(r'ו"',
header))` (vav DIRECTLY prefixed to a quote) and `has_comma = "," in
header`, neither of which an `או`-only pair satisfies (`או` contains no
`ו"` substring). **Reconciling the arithmetic confirms this exactly**:
D-1a's own reported breakdown is comma-only 83 + vav-only 203 + mixed 72
= 358, against its own reported total of 392 confirmed-missing lines --
a gap of 34 lines the breakdown itself does not name. This Planner did
not re-run D-1a's exact script end-to-end to identify those specific 34
line-for-line (out of this Planner's own time-box; named as an honest
gap below), but the arithmetic plus this Planner's OWN independent
corpus sweep (which found `או` as a real, non-trivial, structurally
distinct separator, 16 of which reach the list-shape path today) both
point the same way: **`או`-separated entries were very likely already
counted inside D-1a's reported 392, uncounted in its separator
breakdown, and -- confirmed by direct live re-probe on the merged tree
(the manager's own M25 finding, reproduced independently by this
Planner above) -- are NOT actually fixed by `parse_entry` today.**
**Plainly stated finding for the manager:** D-1a's own bundle does not
fully close "class A" as D-1a's own Planner measured and reported it;
an unquantified subset of its own 392/963/207 headline numbers remains
unfixed post-merge. This does not fault D-1a's shipped work (which was
honestly scoped to comma/vav-direct and said so), but the headline
392/963/207 was never actually 100% closed by the fix that shipped
against it.

**P-R2/D-Q1 false-positive/precision analysis.** Hand-read all 20
live-confirmed gap lines above (not a sample) -- every one is a genuine
Hebrew legal-drafting convention: two (or three) near-synonymous
headwords, or a canonical name plus its symbol/abbreviation alias,
sharing exactly one definition (`"מקום" או "מקום ובניין" כוללים ...`,
`"בנק" או "בנקאי" כולל ...`, `"הליך תחרותי לקביעת תעריף" או "ההליך" -
...`, `"כמות המים האזורית" או "<math>W</math>" - ...`). Zero cases where
`או` between two header quotes meant anything other than "these names
share one definition" -- structurally the SAME argument D-1a's own
Class-A FP analysis already made for comma/vav (a strict superset of an
already-precision-proven single-term grammar, requiring N>=2 quoted
spans immediately separated from their neighbour, immediately before the
one trusted split dash).

**The manager's specific concern, verified rather than assumed** (per
the brief: "note `parse_entry` reads terms only from the header BEFORE
the dash ... verify rather than assume"). The worried-about shape --
`"term" - definition text containing "quoted thing" או "other thing"` --
is REAL and common in this corpus (13 files found by direct search, not
hypothetical), e.g. `תקנות ביטוח בריאות ממלכתי (הסדרי בחירה בין נותני
שירותים)`: `:- "כירורגיה גדולה" - כירורגיה שאינה "כירורגיה זעירה",
"כירורגיה קטנה" או "כירורגיה בינונית";` -- three quoted spans joined by
comma/`או` sit entirely in the DEFINITION TEXT (after the dash), not the
header. `parse_entry`'s own `_find_dash_marker` cuts the header at the
FIRST standalone dash BEFORE any term-scanning happens (`header =
entry_text[:dash_idx]`), so these post-dash quoted spans are structurally
unreachable by the term-extraction loop today, and remain so for any
`או`-widening implemented the same way D-1a's comma/vav widening already
is (extending `_TERM_SEP_RE`'s alternation, not restructuring the
dash-then-header boundary). **Confirmed safe, not merely assumed** --
this Planner traced `"כירורגיה גדולה"`'s header (`"כירורגיה גדולה"`
alone, one term, dash immediately after) and confirmed the three
or/comma-joined quotes never enter `header` at all. No escalation
warranted on this specific concern: it is a genuine shape, and the
existing dash-boundary design (already relied on for every prior
widening this sprint shipped) already protects against it, by
construction. Flagged here as an explicit implementation constraint for
whoever builds the fix, not as an open risk.

**Live path:** every test below goes through the REAL chain --
`ingest_wiki_law` -> `run_definition_linking` (`sections.parse_articles`
-> `profile.normalize_for_parsing` -> `strip_wikilinks` -> `profile.
extract_local_scope_definitions` internally, via the live-registered
`il_single_colon_list_scope_triggers`/`il_colon_dash_nested_list_scope_
triggers` `ScopeTriggerRule`s) -- never a rule's private `_extract`
directly.

**Fixtures:** all 3 vendored below are real, unedited, programmatically
line-sliced corpus excerpts (Python, exact `@ N. heading` line through
the line before the next `@`/`==` marker), proven byte-identical
substrings of their source `.wiki` file (`excerpt in source_text`,
verified by this Planner immediately before writing this file, and
re-verified from the written fixture files themselves right before
writing this test module). Offline: no test reads the corpus.
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _ingest_and_link(db_session, matter_with_users, *, title: str, fixture: str) -> dict:
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        wiki_text=_read(fixture),
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


def test_or_separator_single_colon_pure_multiterm_entry_is_currently_missed(
    db_session, matter_with_users
):
    """`:- "t1" או "t2" - definition` (single-colon marker, PURE `או`
    separator, no comma/vav at all).

    Fixture: `קובץ החלטות מועצת מקרקעי ישראל` article `5.1.` (source
    marker `@ 3.5.1.`, a plain numbered-heading "הגדרות" article whose
    heading TEXT starts with the digit `5` -- `sections.
    _DEFINITIONS_HEADING_RE` requires the heading to START with the word
    `הגדרות` itself, so this numbered-prefix heading does NOT match and
    correctly routes as an ORDINARY article to the list-shape
    `ScopeTriggerRule` path, real and live-confirmed, not a hypothetical
    edge case). Preamble `: [[פרק זה|בפרק משנה זה]] -` (wikilink display
    text "בפרק משנה זה", scope="subsection", unrelated to this bug, not
    asserted here). 7 single-term sibling entries in the SAME list
    capture correctly today; the `או`-joined pair does not.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="קובץ החלטות מועצת מקרקעי ישראל",
        fixture="קובץ החלטות מועצת מקרקעי ישראל_art3_5.1_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert {"הקרקע", "הוועדה לתכנון ופיתוח", "מוסדות חינוך"} <= captured_terms, (
        f"sanity: single-term sibling entries in the SAME list should "
        f"still capture today; got {captured_terms!r}"
    )
    assert "הסכם" in captured_terms, (
        f'sanity: the FIRST term of the או-joined pair captures today '
        f"(parse_entry's single-term fallback) -- the miss is specifically "
        f"the second term; got {captured_terms!r}"
    )
    assert "הסכם גג" in captured_terms, (
        f'expected the SECOND term of the או-joined entry ("הסכם" או '
        f'"הסכם גג" - הסכם בין רשות מקרקעי ישראל...) to be captured -- '
        f"`il_list_shape_scope._TERM_SEP_RE` does not recognize `או` as a "
        f"term separator (only comma and vav-direct), so it is silently "
        f'discarded as part of the "qualifier" today; got {captured_terms!r}'
    )


def test_or_separator_double_colon_mixed_comma_and_or_multiterm_entry_is_currently_missed(
    db_session, matter_with_users
):
    """`::- "t1", "t2" או "t3" - definition` (double-colon marker, MIXED
    comma+`או` sub-shape -- proves comma still works up to the point
    `או` is reached, then the SAME entry's parsing stops).

    Fixture: `חוק הפסיכולוגים` article `5א` (real, verbatim): a `בסעיף
    זה -` preamble followed by 2 `::-`-marked entries; the first is
    single-term (`"השתמש"`), the second names THREE terms
    (`"תואר", "כינוי" או "הגדר"`). Live-confirmed by this Planner: the
    comma-separated pair (`"תואר"`, `"כינוי"`) captures today (D-1a's own
    comma fix), the `או`-joined third term does not.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק הפסיכולוגים, התשל"ז-1977',
        fixture="חוק הפסיכולוגים_art5א_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert "השתמש" in captured_terms, (
        f"sanity: the single-term sibling entry in the SAME list should "
        f"still capture today; got {captured_terms!r}"
    )
    assert {"תואר", "כינוי"} <= captured_terms, (
        f"sanity: the comma-separated first two terms of the mixed entry "
        f"capture today (D-1a's own comma fix); got {captured_terms!r}"
    )
    assert "הגדר" in captured_terms, (
        f'expected the THIRD term ("הגדר", reached via `או` after the '
        f'comma-separated "תואר", "כינוי") to be captured -- silently '
        f"dropped today because `_TERM_SEP_RE` stops matching once it "
        f"hits `או` instead of a comma/vav; got {captured_terms!r}"
    )


def test_vav_hyphen_separator_double_colon_multiterm_entry_is_currently_missed(
    db_session, matter_with_users
):
    """`::- "t1" ו-"t2" - definition` (double-colon marker, hyphenated
    `ו-` conjunction -- DISTINCT from D-1a's already-handled bare
    `ו"t2"` direct-prefix form: the hyphen between `ו` and the opening
    quote is real corpus text `_TERM_SEP_RE`'s `(?:\\s*,\\s*ו?|\\s+ו)"`
    alternation does not match, since neither branch tolerates a `-`
    immediately before the quote).

    Fixture: `פקודת מס הכנסה` article `68א` (real, verbatim): a `בסעיף
    זה -` preamble followed by 2 `::-`-marked entries; the first names
    two terms via the hyphenated conjunction (`"אמצעי שליטה" ו-"יחד עם
    אחר"`), the second is single-term (`"בעלי שליטה"`). Live-confirmed by
    this Planner: the single-term sibling captures; the FIRST term of the
    hyphenated pair captures (parse_entry's single-term fallback); the
    SECOND does not.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="פקודת מס הכנסה",
        fixture="פקודת מס הכנסה_art68א_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert "בעלי שליטה" in captured_terms, (
        f"sanity: the single-term sibling entry in the SAME list should "
        f"still capture today; got {captured_terms!r}"
    )
    assert "אמצעי שליטה" in captured_terms, (
        f"sanity: the FIRST term of the ו--joined pair captures today "
        f"(parse_entry's single-term fallback); got {captured_terms!r}"
    )
    assert "יחד עם אחר" in captured_terms, (
        f'expected the SECOND term ("יחד עם אחר", joined via the '
        f'hyphenated `ו-` conjunction) to be captured -- silently dropped '
        f"today because `_TERM_SEP_RE` does not tolerate a hyphen between "
        f"`ו` and its quote; got {captured_terms!r}"
    )
