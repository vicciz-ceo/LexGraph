# Sprint log — 2026-08-04-defs-il (Israel: definition completeness, full corpus)

Append-only. Panel dialogue (Manager ⇄ Planner ⇄ Developer ⇄ QA), manager
rulings, escalations, and verification evidence. The contract
(`2026-08-04-defs-il.md`) holds state; this file holds the reasoning.

---

## 2026-08-04 — Manager setup (Opus/high; arbitration + verification duties)

**Workspace.** Worktree `/Users/nerya/LexGraph-wt/defs-il` on branch
`claude/defs-il`, created from `origin/main` (`ba1b398`). Own backend venv
built with python3.13; verified it imports worktree code, not the main
checkout (`app from: /Users/nerya/LexGraph-wt/defs-il/backend/app/__init__.py`).
`git config user.email` = `256402398+vicciz-ceo@users.noreply.github.com`
(GH007 guard). The main checkout `/Users/nerya/LexGraph` is the program
manager's and is off-limits to this panel.

**Corpus.** `/Users/nerya/AI for others/israeli-laws-wiki/data/laws` —
12,266 files = 6,133 `.wiki` + 6,133 `.meta.json`, consistent with the
recon dossier's 6,133-law count. READ-ONLY: director POC data; no writes,
moves, or reformatting. Fixtures are COPIES into
`backend/tests/fixtures/wiki_laws/`.

**CodeGraph availability (director mandate).** The `.codegraph/` index lives
at `/Users/nerya/LexGraph/.codegraph` (main checkout); the worktree has none.
Verified working: `codegraph explore "extract_local_definitions
_LOCAL_TRIGGER_RE"` from `/Users/nerya/LexGraph` returned the blast radius
plus verbatim `extract.py:16-60`. Ruling M1 below governs how agents use it.

---

## Manager rulings

### M1 — CodeGraph access from the worktree (director mandate, mechanics)

The index is at the main checkout and the worktree has no `.codegraph/`.
Querying an index is a READ; it does not violate workspace isolation. All
agents therefore use ONE of:

- shell: `cd /Users/nerya/LexGraph && codegraph explore "<symbols or question>"`
- MCP: `codegraph_explore` with `projectPath: /Users/nerya/LexGraph`

**Caveat carried in every brief:** the index reflects the main checkout's
tree. `claude/defs-il` branched from the same commit (`ba1b398`), so the
index is accurate for BASELINE understanding. Once an agent has edited a
worktree file, CodeGraph output for that file is stale — re-Read the
worktree copy. Never write anything under `/Users/nerya/LexGraph`.

### M2 — Two-phase execution, forced by the core-sprint dependency

Checked at setup: branch `claude/defs-core-scope` has **no commits beyond the
shared base `ba1b398`** and its contract has **no `## Seam spec (published)`
section yet**. There is also no `origin/claude/defs-core-scope` (core has not
pushed). So the seam this sprint must build behind does not exist yet.

Per the sprint contract's §Coordination, work splits:

- **Phase A (now, unblocked).** Planner plans ALL items and authors ALL RED
  tests in NEW test files (no conflict with core's refactor of existing
  files). Developers implement ONLY items that touch no shared module.
  Shared modules frozen for this sprint until core merges:
  `pipeline.py`, `matcher.py`, `extract.py`, `sections.py`, `profiles.py`.
- **Phase B (after core merges to main).** Rebase `claude/defs-il` on main,
  read core's published seam spec, and implement the Hebrew trigger CONTENT
  as registered rule module(s) behind that seam.

**Consequence, recorded honestly:** of the five gates, only **I1** (full-corpus
ingest + measurement) is fully deliverable in Phase A, because it lands as a
NEW module (see M3). **I2/I3** are Phase-B implementation with Phase-A RED
tests. **I4/I5** are QA gates that can only run against implemented code, so
they are Phase B. If core does not merge, this sprint ends `blocked` on core
with RED tests + I1 delivered — that is the honest outcome, not a failure to
hide.

### M3 — I1 lands as a new module, so it is Phase-A work

Scouted via CodeGraph (`"How are Israeli wiki law files ingested…"`) plus a
worktree listing of `backend/app/definition_links/`:

- `ingest.py::ingest_wiki_law` (extract.py-adjacent, `ingest.py:27`) is the
  existing single-law IL ingester — 22 callers, well covered by
  `backend/tests/integration/test_definition_links_ingest.py`.
- `ingest_us_statutes_cli.py` is the US **bulk** CLI precedent (per-file
  `_FileResult` with `ok/error/created/matched/skipped/skipped_reasons`,
  `DEFAULT_BATCH_SIZE = 5000`) — this is the shape the US 2,045,897-row
  measured run was reported from, and the honesty standard I1 must match.
- There is **no IL bulk CLI**. So I1's deliverable is a NEW module
  (e.g. `ingest_wiki_corpus_cli.py`) that reuses `ingest_wiki_law` without
  editing it. New file + new test file = zero shared-module edits =
  implementable in Phase A.

The bulk run is an **explicitly-invoked deliverable, never part of
`pytest`** (program constraint: no test downloads or reads the corpus).

### M4 — Recon examples are leads, not proof

Dossier §3 lists four missed classes with act examples. The Planner
RE-CONFIRMS each against the live corpus by calling the real extract
functions through the worktree venv, and records the actual observed output
(`[]` vs. candidates) in this log before authoring the matching RED test.
A class that does not reproduce is escalated to me, not quietly dropped.

---

### M5 — Measured baseline for gate I5 (contract's "167" corrected)

Manager-run, worktree venv, before any panel work:

```
backend/.venv/bin/pytest backend/tests -q
641 passed, 18 warnings in 21.95s
```

Collection breakdown: **166** collected tests have `definition_links` in
their nodeid (contract I5 says "167" — off by one; the measured number is
166, of which 18 are `test_definition_links_us_profile.py`, i.e. ~148
IL-side). I5's real bar is therefore stated as: **the full backend suite
stays 641-green plus whatever NEW tests this sprint adds, with no existing
test edited** (prior R2: editing an existing IL test to fit is a planning
bug → escalate to me).

---

## Panel dialogue

_(appended as roles report)_

---

## 2026-08-04 — Planner report (Sonnet/high)

Read the program doc, recon dossier, sprint contract, and this log first
(per brief). Used `codegraph explore` from `/Users/nerya/LexGraph` for
baseline understanding of `extract.py`/`sections.py`/`matcher.py`/
`pipeline.py`/`profiles.py` (ruling M1) before Reading the worktree copies
for exact line numbers. All live re-confirmation below was run directly
against `/Users/nerya/AI for others/israeli-laws-wiki/data/laws` through
`backend/.venv/bin/python`, calling the REAL, unmodified `extract.py`/
`sections.py`/`normalize.py` functions -- never a mock, never a guess.

### 1. Live re-confirmation of the four dossier classes (ruling M4)

**Class (a) -- `בפרק זה` scoped quoted definitions.** Reproduces exactly.
`חוק זכות מטפחים של זני צמחים` article 15, real body (after
`normalize_for_parsing` + `strip_wikilinks`):
```
(א) בפרק זה, "בקשה" - כל בקשה או התנגדות לפי פרקים ד' או י'.
```
`extract_local_definitions(body)` -> `[]`. `_LOCAL_TRIGGER_RE`
(extract.py:28-30) only matches `לענין זה`/`בסעיף זה`. Broadened corpus
grep (trigger word wrapped in `[[...]]` in the RAW file, since the wiki
markup wikilinks these scope phrases -- `strip_wikilinks` removes that
before extraction runs, so this is a non-issue for the real pipeline, only
for a naive raw-file grep) for the exact `TRIGGER, "term" - definition`
shape across בפרק זה/בסימן זה/בחלק זה/לפרק זה found **154 distinct real
occurrences** corpus-wide (deduplicated identical lines; actual per-file
instance count is higher) -- not an isolated example. Sample (see also the
fixture file for more):
```
[[בסימן זה]], "בית הדין" - לרבות בית המשפט לימאות בשבתו כבית משפט לערעורים לפי [[פרק זה]]
[[בחלק זה]], "התפרצות של מחלה" - הופעה של תחלואה זיהומית בהיקף העולה בבירור על שיעור ההיארעות הצפוי באותו אזור או קהילה
```

**Correction to the dossier's OWN second example for class (a):** dossier
§3 also cites `חוק החברות הממשלתיות art.50א` for class (a). Live text
there is actually `... שהוא בן העדה הדרוזית ([[בפרק זה]] - ייצוג הולם).`
-- a PARENTHETICAL `(TRIGGER - term)` shape, i.e. class (c)'s grammar, not
class (a)'s quote-first `TRIGGER, "term" -` grammar. Both are correctly
"not captured today," but by two different functions
(`extract_adhoc_definitions` for 50א, not `extract_local_definitions`) --
reported per M4 ("class reproduces DIFFERENTLY than dossier says -- report
the difference").

**Class (b) -- `לענין/לעניין סעיף זה` 3-word variant.** Reproduces
exactly. `חוק איסור הלבנת הון` article 3's real body contains, twice:
```
לענין סעיף זה, ”מסירת מידע כוזב” - לרבות אי מסירת עדכון של פרט החייב בדיווח.
```
(Note: source uses U+201D right-double-quote as BOTH open and close --
`normalize_for_parsing` only collapses U+201C/U+201D/gershayim to ASCII
`"`, so this is not itself the gap.) `extract_local_definitions` on the
FULL article-3 body -> `[]`. Corpus grep for the exact 3-word-trigger
quote-dash shape found **255 distinct real occurrences** corpus-wide, all
inspected samples unambiguous single-clause definitions (no false-positive
shape observed in the sample).

**Class (c) -- ad-hoc parenthetical `(TRIGGER - X)` markers.**
Reproduces, but NOT at the dossier's cited location. `חוק רכבת תחתית
(מטרו)` article 13's real body contains **zero** occurrences of
`(בפרק זה`/`(בסימן זה` in any form (grepped the raw file directly,
including the wikilinked form -- no match at or near article 13). Per M4:
"a class that does NOT reproduce is escalated, not quietly dropped" --
escalating the WRONG EXAMPLE (not the class itself, which does reproduce
broadly): corpus-wide grep of `([[?בפרק זה/בסימן זה/בחלק זה]?] - X)`
found **709 distinct real markers**, e.g. `חוק החברות הממשלתיות` article
50א (used as this sprint's corrected fixture) and, powerfully,
`חוק רכבת תחתית (מטרו)` article 19 ITSELF (just not article 13): that
article's body contains FOUR ad-hoc markers -- three `(להלן - X)` (all
correctly captured by `extract_adhoc_definitions` today) and one
`([[בפרק זה]] - שומת ההשבחה)` (silently dropped) -- in the SAME article,
same paragraph structure, differing only by trigger word. Token-length
distribution of the 1041 raw parenthetical matches: only 46 exceed the
existing 4-token safety cap (`extract.py:213`); zero verb-shaped
(non-term, e.g. cross-reference) false-positive candidates found in a
targeted keyword sweep (`יהיה|יהיו|ייחשב|יחול|רואים|ראו |כאילו|לרבות `,
0 hits).

**Class (d) -- structural, prose-body הגדרות/הגדרה sections.**
Reproduces EXACTLY as dossier states for the cited example
(`חוק החברות הממשלתיות art.16`, heading `הגדרה`,
`is_definitions_heading("הגדרה") == True`, body
`[[בפרק זה]], "דירקטור" - דירקטור מטעם המדינה בחברה ממשלתית.`,
`extract_definitions_from_section(body, scope="global")` -> `[]`) --
**but the dossier drastically understates the scale.** Planner wrote a
full-corpus scan (`is_definitions_heading(article.heading) and
article.body.strip() and extract_definitions_from_section(article.body,
scope="global") == []`, all 6,133 files, 3.3s wall time, 0 errors) and
found **592 real, non-trivial hits** (~9.7% of the ENTIRE corpus). Every
hit sampled (dumped to a local scratch file, ~40 inspected by hand) has
genuine substantive definition text; none are repealed/placeholder
markers (0/592 bodies under 20 characters). This is the single largest
finding of this sprint's recon and should be treated as the sprint's
primary deliverable risk, not a corner case.

Three distinct structural sub-shapes found within class (d), each needing
different (or a unified, more careful) handling:
  - **(d-i) single inline sentence**, no list at all -- the dossier's own
    example, and the majority shape by instance count, e.g.
    `: בתקנות אלה, "היום הקובע" - 31 במרס של כל שנה.`
  - **(d-ii) `::-` (double-colon-dash) entries** under a `TRIGGER -`
    preamble line, e.g. `תקנות קרן גרמניה-ישראל למחקר ולפיתוח מדעי (פטור
    ממסים)` article 1: `: (א) בתקנות אלה -` then four `::- "term" -
    definition;` lines. `_ENTRY_START_RE` (`^\s*:-`) never matches a line
    starting `::-` (second character is `:`, not `-`), so
    `_split_into_blocks` produces zero blocks.
  - **(d-iii) numbered `: (N) "term" -` entries** under a `TRIGGER -`
    preamble, e.g. `הוראות מס הכנסה (ניהול פנקסי חשבונות)` article 27:
    `: בפרק זה -` then `: (1) "פעולה כספית" - ...`, `: (2) "יומן העסק" -
    ...`. **Genuine false-positive trap for any naive fix**: the same file
    also has entries like `: (8)(א) בעל מסעדה - יומן שירות ...` where
    `בסיס המשכורת`-style bodies (seen repeatedly in the "צו שירות המדינה
    (גמלאות)" family, ~30 near-duplicate files in the corpus) read: one
    quoted term followed by a definition whose OWN text continues into a
    numbered sub-list `(1)`/`(2)`/`(3)` (e.g. a deduction formula's line
    items) -- these numbered items are CONTINUATION of the single
    definition, not N separate defined terms. A fix that treats every
    `: (N)` line as a new entry (mimicking `:-` or the US `(N)`-splitter)
    would silently fabricate 3-4 spurious extra "definitions" for every
    one of these ~30+ files. Flagged as the sprint's highest
    false-positive risk (see §3 below).

### 2. Fifth class found (per M4 instruction to actively look)

**`בפסקה זו, "term" - definition`** -- a definition scoped to a single
numbered PARAGRAPH (subsection) inside an ordinary article, narrower than
today's `"local"` (whole-article) scope. Corpus frequency: 522 files
contain the phrase `בפסקה זו` at all. Real example, live-confirmed:
`הוראות מס הכנסה (ניהול פנקסי חשבונות)`, appendix `תוספת י"א` article 3,
item (8):
```
: (8)(א) בעל מסעדה - יומן שירות ... ;
:: (ב) האמור בפסקת משנה (א) לא יחול אם הודיע בעל המסעדה ... ;
:: בפסקה זו, "בעל מסעדה" - לרבות כל בעל עסק המעסיק מלצרים.
```
Both `extract_local_definitions` and `extract_adhoc_definitions` return
`[]` on the real article body (heading `ספרים מיוחדים` is not a הגדרות
heading, so this routes through the ordinary-article path in
`pipeline.py`'s `else` branch). This is the class most directly on-point
for the director's own mandate wording ("relevant only to specific
articles or subsections"), and feeds directly into whatever core-scope
ships for subsection-level enforcement. This finding feeds QA's I4
zero-miss sweep as a named check, per the brief.

### 3. Design-question answers

**Q: Scope granularity vs. the data model (does Article/Definition carry
סימן/חלק?).** **No, and this is a genuine core-seam dependency -- do not
paper over it (ESCALATION E1).** `Article` (ORM, `app/models/article.py`)
has exactly one scope-adjacent field: `chapter: str | None`. It is
populated (`sections.parse_articles`, sections.py:59-109) ONLY from
headings marked with EXACTLY two `=` characters (`len(break_match.
group(1)) == 2`) -- any heading marked with 3+ equals (`===`, `====`, ...)
ALSO ends the current article's body scope (so it is not simply ignored --
it silently terminates article boundaries) but its own heading TEXT is
discarded entirely, stored nowhere. Verified against the real corpus:
`==` and `===` both occur >2,400 times corpus-wide; `====` occurs 1,785
times; heading lines whose TEXT contains the word "חלק" occur at ALL
THREE depths (2/3/4 equals: 354/1266/82 files respectively) -- i.e. the
Hebrew word used (חלק vs. פרק vs. סימן) is NOT consistently tied to a
fixed `=`-depth across the corpus; it depends on each individual law's own
structure. Consequence: `matcher._in_scope` (matcher.py:104-110) can only
ever enforce "chapter" (via the one `Article.chapter` field, itself
already a conflation of whatever the LAW calls its top `==`-level
grouping -- חלק or פרק, indistinguishably) and "local" (article number).
There is NO field, at any layer (`Article` schema, `Definition` schema,
`DefinitionCandidate` dataclass, `sections.parse_articles`'s output
shape), capable of representing סימן or a genuinely nested חלק today. All
four of those things live in FROZEN files (`sections.py`, the ORM models
are not frozen, but populating a new field requires editing the frozen
`sections.py` parser) or require new columns core's registry/seam should
own so US and IL don't diverge on how sub-chapter granularity is named. **I
did not write a RED test for סימן/חלק scope enforcement** because there is
nowhere yet to put the expected data -- a test asserting `Article.siman`
existed would test a schema gap, not a behavior, and per my role I do not
design schema changes unilaterally. Recommend the program manager confirm
with core-scope whether סימן/חלק granularity is IN or OUT of core's
"subsection-level enforcement" scope; if OUT, that leaves a real, director-
relevant gap (class (a)'s בסימן זה/בחלק זה sub-cases, and the fifth class's
paragraph-level need) permanently unaddressed unless a later sprint picks
it up explicitly.

**Q: Zero-miss vs. zero-false-positive (P-R2/Q-1) -- real conflict
examples.** Surveyed each of the four (five) classes for concrete
corpus-level false-positive risk, real examples only, no side picked:
  - Classes (a)/(b) (quote-dash grammar, new trigger words only): **LOW
    risk observed.** The grammar is tight (`"term" -` immediately after
    the trigger); of 154 (class a) and 255 (class b) sampled real
    occurrences, none was an obviously wrong capture (a citation, a
    cross-reference, or an ordinary sentence coincidentally shaped like a
    definition). No conflict example found to escalate for these two.
  - Class (c) (ad-hoc parenthetical, new trigger words within the EXISTING
    4-token cap): **LOW risk observed**, same reasoning -- reusing the
    already-trusted cap that protects `להלן` today. 46/1041 sampled real
    parentheticals would exceed the cap (correctly excluded, same as
    `להלن` already is); 0/1041 verb-shaped false positives in a targeted
    sweep.
  - **Class (d) -- HIGH risk, real conflict, escalating per P-R2 (E3):**
    the (d-iii) numbered-continuation sub-shape (§1 above, "בסיס
    המשכורת" family) is a genuine, demonstrated false-positive trap: a
    naive "any `: (N) "term" -` line inside a recognized הגדרות section
    is a new entry" rule would fabricate spurious definitions from a
    SINGLE term's own multi-line definition body. This is not
    hypothetical -- it recurs verbatim across at least ~30 real corpus
    files (the "צו שירות המדינה (גמלאות) (עדכון המשכורת הקובעת) (דירוג
    ...)" family alone). **Proposed rule (Planner recommendation, not a
    unilateral decision -- surfacing for the manager to arbitrate):** a
    numbered `(N)` line only starts a NEW entry if it is preceded (after
    the `TRIGGER -` preamble, or as the very first content line) by
    nothing but other same-depth numbered entries -- i.e. detect the
    shape via a two-pass check: does EVERY top-level numbered item after
    the preamble open with its own quoted term (`"..."`) followed by a
    dash? If even one does not (a bare `(N)` continuing prose with no
    leading quote), treat the WHOLE numbered run as prose belonging to
    the single preceding quoted-term entry, not as N separate entries.
    This mirrors the existing `_find_split_dash`/`_parse_terms_and_
    qualifier` discipline (a dash only splits when the header prefix
    actually contains a quoted term) rather than inventing new heuristics.
    **Failure mode named:** a genuinely multi-term numbered list where
    the FIRST entry happens to be a long prose lead-in before its own
    quote (rare in the sample, not observed) could still misfire; flagged
    for QA's I4 sweep to watch for.

**Q: Class (d) design -- prose-definition vs. ordinary substantive prose
boundary.** Because the section's HEADING has already been confirmed a
הגדרות/הגדרה heading (`is_definitions_heading` already gates this whole
code path in `pipeline.py`), the false-positive surface here is much
narrower than for classes (a)/(b)/(c) (which fire on ARBITRARY,
not-heading-gated article bodies). **Proposed rule:** once inside a
confirmed-definitions-section body that yields zero `:-` blocks, fall back
to the SAME quote-dash grammar `extract_local_definitions`/class (a)
already trusts (`(TRIGGER,)? "term" - definition`, TRIGGER optional here
since the heading itself already establishes the definitional context) --
reusing `_find_split_dash` and `_parse_terms_and_qualifier` verbatim
rather than a new regex family, scoped per sub-shape: (d-i)/(d-ii) are
safe to apply this to directly (94%+ of the 592 sampled hits); (d-iii)
needs the two-pass numbered-continuation guard above. **Failure mode
named:** a הגדרות-headed section whose body is genuinely NOT a definition
at all (e.g. a repealed/placeholder section, or a section that only
CITES another law's definitions without restating them, `: ראו הגדרות
בחוק ...`) must still yield `[]`, not a fabricated definition from
whatever quoted phrase happens to appear -- none of the 592 sampled hits
were this shape, but QA's I4 sweep should watch for it explicitly since
this Planner's sample was not exhaustive.

**Q: What is genuinely Phase-A implementable (confirm/correct M3)?**
**M3 confirmed, no correction.** `ingest_wiki_law` (ingest.py) is
UNCHANGED-reusable and ingest.py is not in the frozen list; the new
`ingest_wiki_corpus_cli.py` module + its tests touch zero frozen files.
One thing to flag, not a correction to M3 but a note for whoever
implements it: **`ingest_wiki_law` itself has NO idempotency/dedup logic**
(unlike `ingest_us_statute_rows`, which explicitly supports resumable
reruns) -- every call unconditionally creates a new `Document` + fresh
`Article`/`SourceSpan` rows. A partial 6,133-file run that needs resuming
would duplicate already-ingested laws if simply re-invoked over the same
directory. This wasn't in M3's scope to decide and I did not write a test
pinning a specific resumability contract (I don't know whether the
program wants dedup-by-title added to the NEW CLI module, or considers a
single uninterrupted full run acceptable for I1's "prove it works" bar) --
**escalating as an open question (E4)**, not deciding it myself.

### 4. Escalations (numbered, for the manager to relay)

- **E1 (design fork, needs a decision):** סימן/חלק scope granularity
  cannot be represented in today's `Article`/`Definition` schema at all --
  is this in-scope for core-scope's "subsection-level enforcement" seam,
  or does it need its own follow-up? Recon-confirmed corpus scale: `==`/
  `===` each 2,400+ files, `====` 1,785 files, and the Hebrew word used at
  each depth is INCONSISTENT across laws (verified: "חלק" appears as
  heading text at all three depths).
- **E2 (design fork, same shape as E1):** the fifth class (`בפסקה זו`,
  paragraph/subsection scope) needs an even finer granularity than
  סימן/חלק -- narrower than today's `"local"`, not broader. Same
  schema-representability gap. 522 files affected.
- **E3 (false-positive risk, needs arbitration per P-R2):** class (d)'s
  numbered-continuation sub-shape (d-iii) is a real, demonstrated
  false-positive trap (~30+ real files). Proposed rule given above; not
  unilaterally adopted.
- **E4 (open question, not urgent but should be answered before I1's real
  run):** should the new bulk CLI add its own dedup-by-title check before
  calling `ingest_wiki_law` (to make a resumed partial run safe), or is a
  single uninterrupted 6,133-file run the accepted bar for I1?
- **Wrong dossier example (informational, already corrected in the tests
  themselves, not blocking):** dossier §3's class (a) second example
  (`חוק החברות הממשלתיות art.50א`) is actually class (c)'s shape; dossier
  §3's class (c) example (`חוק רכבת תחתית (מטרו) art.13`) does not
  reproduce at all (the law itself has the pattern, elsewhere, at
  article 19). Both are corrected in this sprint's fixtures/tests; no
  action needed unless the dossier itself is later revised.

### 5. Deliverables

**Fixtures added** (`backend/tests/fixtures/wiki_laws/`, all real
verbatim excerpts from the read-only POC corpus unless noted):
`חוק זכות מטפחים של זני צמחים_ch3_ch4_excerpt.wiki` (פרק ג'+ד', real,
73 lines -- doubles as the I3 scope fixture), `חוק איסור הלבנת הון_
art3_excerpt.wiki`, `חוק החברות הממשלתיות_art50א_excerpt.wiki`,
`חוק החברות הממשלתיות_art16_excerpt.wiki`, `תקנות קרן גרמניה-ישראל_
art1_excerpt.wiki`, `צו פיקוח על מחירי מצרכים ושירותים (חמאה)_
art1_excerpt.wiki`, `הוראות מס הכנסה (ניהול פנקסי חשבונות)_
besel_mesada_excerpt.wiki`. Plus `backend/tests/fixtures/
wiki_corpus_sample/` (new subdirectory) for the I1 CLI tests: two REAL
complete small laws with their real `.meta.json` files, plus one
DELIBERATELY SYNTHETIC (not real corpus data, clearly labeled in its own
`<שם>` line) no-metadata `.wiki` file to exercise the CLI's per-file
failure-reporting path.

**Test files added (all NEW, no existing test touched):**
- `backend/tests/integration/test_definition_links_il_missed_classes_
  live.py` -- 7 tests (classes a/b/c/d-i/d-ii/d-iii/fifth), all live-
  path via `ingest_wiki_law` + `run_definition_linking`, all RED today
  (`AssertionError`, empty `created_definitions`).
- `backend/tests/integration/test_definition_links_il_chapter_scope_
  live.py` -- 1 test (gate I3, both directions), RED today.
- `backend/tests/integration/test_ingest_wiki_corpus_cli.py` -- 4 tests
  (gate I1), 1 green (fixture sanity check), 3 RED today
  (`ImportError: cannot import name 'ingest_wiki_corpus_cli'`).

**Suite numbers (worktree venv, `backend/.venv/bin/pytest backend/tests -q`):**
- Before this session: `641 passed` (M5 baseline, unchanged).
- After: `642 passed, 11 failed` (642 = 641 baseline + 1 new green fixture
  sanity check; 11 = all new RED tests; **zero existing tests modified**,
  confirmed via `git status --short` showing only new, untracked files).

Proof-of-RED transcripts (captured before writing this log entry):
```
backend/.venv/bin/pytest backend/tests/integration/test_definition_links_il_missed_classes_live.py \
    backend/tests/integration/test_definition_links_il_chapter_scope_live.py -v
=> 8 failed (all AssertionError: "... got []")

backend/.venv/bin/pytest backend/tests/integration/test_ingest_wiki_corpus_cli.py -v
=> 1 passed (fixture sanity check), 3 failed (all ImportError: cannot
   import name 'ingest_wiki_corpus_cli' from 'app.definition_links')

backend/.venv/bin/pytest backend/tests -q
=> 642 passed, 11 failed, 18 warnings
```

`## Next Steps` in the sprint contract has been filled with 8 numbered
items, each tagged Phase A/B, each naming its gate and RED test(s).

---

## 2026-08-04 — Manager verification of the Planner handoff + rulings M6-M8

### Verification I performed MYSELF (not "the agent said so")

- Three-dot diff materialized: `git diff --stat origin/main...HEAD` — 17
  files, **zero** `backend/app/` production files. No frozen module touched.
- `git diff --name-status origin/main...HEAD -- backend/tests` — every entry
  is `A` (addition). **No existing test modified or deleted** (prior R2 bar
  holds).
- Manager-run suite: **`11 failed, 642 passed, 18 warnings in 13.39s`**.
  Baseline was 641 passed; 642 = 641 untouched + 1 new green fixture sanity
  check; the 11 failures are exactly the new RED tests. RED is proven by my
  own run, not the Planner's.
- Corpus integrity: `find data -newermt "-2 hours" -type f` → empty;
  `ls data/laws | wc -l` → 12,266 unchanged; corpus `git status --porcelain`
  → clean. **The read-only POC corpus was not written to.**
- Read `test_definition_links_il_chapter_scope_live.py` in full: it is
  genuinely live-path (`ingest_wiki_law` → `run_definition_linking` → assert
  on `Definition` rows and `USES_DEFINITION` edges), seam-agnostic (touches
  no frozen-module internal), and asserts BOTH directions (articles 13/16/17
  same-chapter link; article 20 different-chapter must NOT). This survives
  core's refactor — accepted as the I3 proof-test.

**Handoff ACCEPTED.**

### M6 — ruling on E4 (bulk-CLI resumability). Manager decision, not escalated.

This sits inside my own gate definition, so I decide it rather than spending
a director escalation. **I1's bar is ONE uninterrupted full run over all
6,133 laws**, and its headline numbers must be pure `created` counts — that
is what "the same standard as the US 2,045,897-row run" means. To keep a
resumed run possible without silently duplicating (`ingest_wiki_law` has no
idempotency, correctly flagged by the Planner), the new CLI gets an
**opt-in `--skip-existing-titles` flag, DEFAULT OFF**, reporting any skips
under their own named counter so they can never be confused with `created`.
Default-off preserves measurement honesty; opt-in preserves operability.
New-module-only, so still Phase A.

### M7 — ruling on E3 (class (d) false-positive trap). Arbitrated, NOT a P-R2 escalation.

P-R2 requires escalation when zero-miss and zero-false-positive genuinely
CONFLICT — i.e. when you must sacrifice one. That is not this case: the
Planner proposed a two-pass rule that captures the real (d-i)/(d-ii)
definitions AND rejects the (d-iii) numbered-continuation trap (~30+ real
files), by reusing the existing `_find_split_dash` /
`_parse_terms_and_qualifier` discipline rather than inventing heuristics.
A solved conflict is a design decision, not a director question.

**Adopted** as specified, with two binding conditions:
1. The residual failure mode the Planner named (a genuinely multi-term
   numbered list whose FIRST entry opens with prose before its own quote —
   not observed in sampling) becomes a **named, mandatory check in QA's I4
   sweep**, not a footnote.
2. The other named failure mode — a הגדרות-headed section that is a
   placeholder/repeal or merely CITES another law's definitions
   (`: ראו הגדרות בחוק ...`) — must still yield `[]`. Also a named I4 check.
If QA demonstrates either failure mode is real AND unavoidable, THAT
becomes the P-R2 escalation, with its corpus examples.

### M8 — E1 + E2 are genuine escalations; sequencing decision

E1 (סימן/חלק unrepresentable in the schema) and E2 (`בפסקה זו` paragraph
scope, finer still) are real architecture forks that cross into
core-scope's remit and bear directly on the director's own mandate wording
("relevant only to specific articles or subsections"). They also determine
whether gate **I3 as written** ("including סימן/פרק/חלק units") is
achievable at all. These escalate.

**Sequencing:** I am NOT stopping on them yet. Phase B is already blocked on
core (which has published no seam), so an immediate stop buys the director
nothing, while item 1 (I1, the measured full-corpus run) is unblocked Phase-A
work whose OUTPUT will quantify the E1/E2 gap corpus-wide. I therefore run
the Developer on I1, execute the real 6,133-law measured run myself, and then
escalate E1/E2 carrying hard corpus numbers instead of estimates.

---

## 2026-08-04 — Manager verification of the Developer handoff + I1 measured run

### Developer handoff verification (mine, not reported)

- `git diff --name-status b3cd641..HEAD` → exactly two entries, both `A`:
  `ingest_wiki_corpus.py`, `ingest_wiki_corpus_cli.py`. **No test, no
  fixture, no frozen module touched** — checked explicitly against all five
  frozen files plus `ingest.py`: all unchanged.
- Style gate: 213 + 145 = 358 lines across two files, both **under 300**.
- Manager-run suite: **`8 failed, 645 passed, 18 warnings in 14.27s`** — the
  641 pre-existing tests still green, the 4 CLI tests now green, and the 8
  Phase-B RED tests still RED (correct: fixing them requires frozen files).
- **Correctness check I ran because the code worried me:** `_ingest_one_file`
  calls `session.rollback()` in its failure path. If the CLI committed only
  at the end, one bad file would discard every previously-ingested law. I
  checked: `ingest.py:84` calls `session.commit()` per law, so the rollback
  can only discard the current file's partial work. **Safe** — but this is a
  load-bearing coupling to `ingest.py`'s commit behavior and should be
  re-checked if `ingest.py` ever changes.

**Handoff ACCEPTED.**

### I1 — the real full-corpus measured run (executed by me)

Command (explicitly invoked, NOT part of `pytest`):
```
LEXGRAPH_DATABASE_URL="sqlite:///<scratch>/corpus_run.db" \
  backend/.venv/bin/python -m app.definition_links.ingest_wiki_corpus_cli \
  --input-dir "/Users/nerya/AI for others/israeli-laws-wiki/data/laws" \
  --repository-id <repo> --matter-id <matter>
```
Measured result — real numbers, no extrapolation:
```
files found:             6133
files processed:         6133
files failed:            0
total articles ingested: 127903
existing titles skipped: 0
wall time:               37.426s
peak memory:             79986688 bytes  (76.3 MiB)
```
Cross-checked against `/usr/bin/time -l`: `37.77 real`, `maximum resident
set size 79986688` — agrees with the CLI's own instrumentation.
Corpus re-verified untouched after the run.

### **I1 verdict: PASS on its literal terms — with a material caveat that I am escalating (new class (f))**

The gate asked whether the corpus loads, and it does: 6,133/6,133, zero
failures. But "ingested" is NOT the same as "reachable", and under the
director's absolute zero-miss bar the difference is the whole point. The
Developer flagged, as a passing observation, that 2 of its 4 smoke files
ingested with 0 articles. I chased it corpus-wide rather than letting it go.

**Measured (probe over all 6,133 files, calling the real `parse_articles`):**
```
documents:                     6133
articles:                      127903
documents with 0 articles:     124   (2.02%)
articles/doc (nonzero):        min=1  median=8  max=1203
```
Of those 124 zero-article laws, **57 contain at least one definition
signal** (`להלן` 47, quote-dash grammar 14, scope triggers 6, a
הגדרות heading 5). Breaking down the CAUSE:
```
zero-article files:                                124
  ...with a bare/unnumbered "@" marker:            101   (12 of these contain quote-dash definitions)
  ...with no "@" at all:                            21
  ...other:                                          2
```
**Root cause, confirmed live.** `sections.parse_articles` requires the
`@ N.` numbered-article shape. A law whose body uses a BARE `@` (no number)
parses to zero articles, so `run_definition_linking` never sees any of its
text. Verified end-to-end on `רשימת הזכויות לפי חוק לקידום התחרות
ולצמצום הריכוזיות.wiki`: the file is 10,502 bytes, DOES contain `@`,
`parse_articles` → **0 articles**, and its real definitions are therefore
entirely unreachable:
```
::- "סיווג" - סיווג המנוי בסעיף 271א(ד) לתקנות התעבורה;
::- "צד קשור" - אדם או תאגיד השולטים במבקש הבקשה, ...
::- "קטגוריה" - קטגוריה המנויה בסעיף 271א(א) לתקנות התעבורה, ...
::- "שליטה" - כהגדרתה בחוק ניירות ערך, התשכ"ח-1968 (להלן - חוק ניירות ערך), ...
```
Its `<מבוא>` preamble also carries `(להלן - החוק)` — lost as well.

**This is a SIXTH miss class, not in the recon dossier, and architecturally
distinct from classes (a)-(e).** Those are extraction failures INSIDE a
parsed article. This is a structural loss one layer EARLIER, at article
parsing, so no amount of trigger-content work in this sprint can reach it.
It lives in `sections.py` — **frozen**, and owned by core's refactor.

Conservative floor on the damage: **12 laws** with unambiguous quote-dash
definitions are wholly invisible today; up to 57 have some definition
signal. That is a direct, measured breach of the zero-miss bar.

### M9 — ruling on class (f)

Class (f) is **out of this sprint's implementable scope** (frozen
`sections.py`) and **was not in any gate**, so I am not silently absorbing
it into I2/I3. It escalates as **E5**, with the numbers above. I did NOT
have the Planner write a RED test for it: the fix belongs to whoever owns
`sections.py` (core, or a follow-up sprint), and a test authored here would
either duplicate core's or pin a parser contract this panel does not own.
**Gate I4's zero-miss sweep must treat class (f) as a named, mandatory
check** — QA is not allowed to report zero-miss while 124 laws parse to
nothing.

---

## 2026-08-04 — Manager: core's seam spec landed; escalation set re-scored

Core pushed `origin/claude/defs-core-scope` (`9272f6e`) with
`## Seam spec (published)` (`5610fb1`) AFTER my ruling M2 was written. I
read it before escalating, and it changes the picture — for the better on
one point, not at all on the other.

### What the seam gives us

- `Definition.scope` becomes 4-way: `"chapter" | "local" | "subsection" |
  "law-wide"`, plus a new persisted `Definition.source_subsection` column
  and `profile.split_into_subsections()`.
- Rules ship as NEW FILES in `backend/app/definition_links/rules/`, auto
  -discovered by `pkgutil.iter_modules` — a family panel's only repo change
  is adding its own file. **Genuinely conflict-free**, as promised.
- Our four/five trigger classes map cleanly onto `ScopeTriggerRule`
  (classes a/b/c/e) and `EntrySplitterRule`/`TermClauseRule` (class d).

### **E2 is RESOLVED by the seam — withdrawing it.**

The fifth class (`בפסקה זו`, paragraph scope, 522 files) needed a
granularity narrower than `"local"`. The seam's new `"subsection"` value is
exactly that, and core explicitly names "IL: קטן/lettered markers" as its
own Stage-B work. So class 5 ships as a registered `ScopeTriggerRule`
stamping `"subsection"`. No director decision needed. **E2 withdrawn.**

### **E1 is NOT resolved — it stays open.**

The seam's four levels are chapter / local / subsection / law-wide. סימן
(siman) sits BETWEEN chapter and article, and nested חלק between law and
chapter; neither exists in the seam, and `Article.chapter` remains a single
flat field populated only from exactly-`==` headings. So `בסימן זה` (200
files) and `בחלק זה` (68 files) still have nowhere to store their scope.
**Gate I3 as written ("including סימן/פרק/חלק units") cannot be met.**

### Phase B remains hard-blocked

The `rules/` package does not exist on `main` (`origin/main` is at
`3925f41`; core is unmerged and is itself held on its own escalation E-1 —
multi-scope precedence, a different question from mine but one that also
touches our classes). So ruling M2's Phase-B gate still holds: no IL rule
module can be written until core merges.

### Escalation set, final

| # | Status | Owner of the answer |
|---|---|---|
| E1 — סימן/חלק unrepresentable; I3 unachievable as written | **OPEN — escalating** | director / core boundary |
| E2 — `בפסקה זו` paragraph scope | **WITHDRAWN** — seam's `"subsection"` covers it | resolved |
| E3 — class (d) false-positive trap | settled by me, ruling **M7** | manager |
| E4 — bulk-CLI resumability | settled by me, ruling **M6** | manager |
| E5 — class (f): 124 laws parse to zero articles, 12 with real definitions wholly lost | **OPEN — escalating** | director / core boundary |

---

## 2026-08-04 — UNBLOCKED: core merged; E1/E5 answered; my E5 framing CORRECTED

Core is on `main` (`06d67d8`; my rebase target `0d57228`). Program manager
answered both escalations and issued binding ruling **P-E3**.

### E1 — ANSWERED by the shipped seam

Generic `(unit_kind, unit_value)` scope units with narrowest-governs-as-
longest-prefix are live (independent QA, 2 cycles, 700/0). סימן/חלק/פרק are
expressible as unit kinds. **Gate I3 is achievable after all** — my earlier
"unachievable as written" verdict is superseded. The AUTHORITATIVE seam is
**v2.5** in `docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md` on
main; my panel had planned against v2, so the Planner re-reads v2.5 first.

### **E5 — MY FRAMING WAS WRONG. Corrected facts are binding (P-E3).**

I recorded this honestly and prominently because I got it wrong, and the
correction changes who owns the fix:

| | My claim (2026-08-04, ruling M9) | Corrected fact (P-E3, program-manager-probed) |
|---|---|---|
| bare-`@` scale | 101 zero-article FILES | **331 occurrences across 42 files** |
| what follows a bare `@` | implied: lost article content | **ALWAYS table/list markup; NEVER a definitions heading** |
| the lost definitions | "12 laws, definitions wholly lost to the parser" | definitions ARE real, but live as **`::-` double-colon nested-list entries** with **ITEM-level scope**, introduced by **`בפרט זה -`** ("for this item"); population **~8-12 files** |
| owner | "structural, frozen `sections.py`, core's" | **REACHABILITY was core's — delivered.** **CAPTURE is MINE.** |

**Where I went wrong, precisely:** my probe measured at the wrong layer. I
counted zero-article files and then regex-matched definition signals across
each WHOLE FILE, which let me attribute the loss to the bare-`@` parser gap
without ever characterizing what actually followed those `@` markers. The
zero-article count (124) and the observation that real definitions were
unreachable were both correct; the *mechanism* and therefore the *owner*
were not. A signal-anywhere-in-file regex is not evidence about a specific
structural position — that is the same class of error P-R7 warns about.

**Consequence for this sprint: `בפרט זה` is a SIXTH trigger-content class
and it is OURS**, not core's. It was in nobody's inventory before now. It
becomes a new item with a RED test on the exact vendored fixture already on
main: `backend/tests/fixtures/wiki_laws/רשימת הזכויות לפי חוק לקידום
התחרות ולצמצום הריכוזיות_excerpt.wiki`.

### **M10 — binding instruction for I4's adversarial sweep (supersedes M9's class-(f) check)**

1. Use the **corrected** facts above, never my original class-(f) framing.
2. **P-R7 denominators: ground truth must be independent of our own
   triggers' signals.** A sweep that finds definitions by grepping for the
   very phrases we implemented will always report ~100% and prove nothing.
   The PR panel's QA caught exactly this trap. QA must build its denominator
   from a signal source that does not reuse our trigger list — and state in
   the log how it did so.
3. My own E5 error is the worked example of why (1) and (2) are mandatory.

### Post-rebase state (verified by me)

- Rebase onto `0d57228`: 6 commits replayed, no conflicts.
- venv refreshed (`pip install -e '.[dev]'`); `import app` still resolves to
  the worktree.
- `rules/` package present on main: `registry.py`, `il_scope_triggers.py`
  (the IL rule-module example to copy), `us_scope_trigger_proof.py`.
- Suite: **8 failed, 704 passed** (was 645 passed pre-rebase; core added
  tests). The 8 failures are the SAME 8 Phase-B REDs, and I verified they
  fail for **behavioral** reasons, not collection/import drift — every one
  is `AssertionError: ... got []`. Phase B is now genuinely unblocked.


---

## 2026-08-04 — Planner RESUMED (Sonnet/high): v2 -> v2.5 re-spec, sixth class, three new architecture escalations

Per the manager's brief: core is merged (`0d57228`), the prior Planner
instance's Phase-A recon (classes a-d, fifth class, escalations E1-E5, ruling
M9(a)-of-this-sprint... actually M4/M6/M7/M9 above) is NOT redone here --
read from this log as instructed. This entry covers what changed re-speccing
against the AUTHORITATIVE seam v2.5 (`docs/sprint/sprints/
2026-08-04-defs-core-scope-seam.md`), a live re-confirmation of `בפרט זה`
(the sixth class, program manager ruling P-E3), and three architecture
findings verified by direct source-reading of the SHIPPED code on `main`,
not by trusting the seam document's prose alone -- the same discipline that
caught the earlier E5 framing error.

### What changed, v2 -> v2.5, and why it matters for our plan

Read every delta (v2 -> v2.1 -> v2.2 -> v2.3 -> v2.4 -> v2.5) in
`defs-core-scope-seam.md`, not just the final section, per the manager's
instruction ("read v2.5 and every delta that leads to it"). The load-bearing
changes since the prior Planner's v2-based plan:

- **v2.2/v2.4: `UnitPath` replaces `ScopeUnit`+`Subsection`, and is
  BELOW-article only** (v2.4 §1 corrects v2.2). Container levels ABOVE the
  article (chapter/siman/chelek/part/subchapter) stay on the LEGACY
  `"chapter"` field or the GENERIC `scope_value`+`structural_units` path
  (v2 M4), never merged into `UnitPath`. This directly shapes item 9's
  design (`בפרט זה` is a below-article/item-level concept, so it belongs to
  the `UnitPath` conceptual family, not `structural_units` -- even though,
  per the E7 finding below, no rule-registration seam actually lets us
  extend `UnitPath` resolution for IL).
- **v2.2 §3: "narrowest governs" = longest matching prefix, WITHDRAWING
  v2's `register_scope_unit_kind`/`rank_for`.** Confirmed shipped exactly
  this way: `matcher.scope_rank` uses a fixed `_LEGACY_KIND_RANK` dict
  (`{"subsection": 0, "local": 1, "chapter": 2, "law-wide": 1000}`) and
  defaults every OTHER kind (e.g. our new `"siman"`/`"chelek"`/`"item"`) to
  rank 1 (same as `"local"`) -- there is no live per-kind rank registration
  to call. Noted in the re-spec: a `"siman"`-scoped and a `"local"`-scoped
  definition sharing the same mention would TIE (both survive, M10) rather
  than the siman one "winning" as more specific -- moot in practice today
  since `"siman"` never actually contains anything live (see E1 update).
- **v2.5: `Definition.scope_value` is TRANSIENT-BY-DESIGN, no column, no
  migration.** Verified: `app/models/definition.py` has no `scope_value`
  column, confirming v2.5's own correction is accurate as shipped. Our new
  rule modules (item 2b, item 9) must NOT expect `scope_value` to survive
  a DB round-trip -- fine, since none of our new tests read it back from a
  persisted row.
- **The seam's SIX registered rule kinds (`HeadingRule`, `BodyPreambleRule`,
  `EntrySplitterRule`, `TermClauseRule`, `ScopeTriggerRule`,
  `StructuralUnitRule`) plus `CitationRule` (v2.3) are all real, unit-tested
  dataclasses in `rules/registry.py`.** This is where the plan diverges
  sharply from what the seam DOCUMENT claims vs. what is actually WIRED --
  see "Three new architecture findings" below. This is the single biggest
  difference from the prior (pre-merge) plan, which reasonably assumed the
  seam document's own worked examples (`us_entry_marker_variants.py` etc.)
  meant the corresponding dispatch was live everywhere it was described.

### Three new architecture findings (verified by direct source-reading, not assumed)

**(1) E1 status update -- schema question ANSWERED, but a SEPARATE wiring
gap blocks סימן/חלק containment.** The manager's post-merge log entry says
"E1 is ANSWERED... Gate I3 is achievable." The schema/mechanism HALF of
that is true: `matcher._in_scope`'s generic branch (any kind other than
chapter/local/subsection/law-wide) checks `article.structural_units`
against `definition.scope_value`, and this is exercised correctly by a
UNIT test (`test_definition_links_matcher.py::
test_link_articles_to_definitions_respects_generic_scope_unit_containment`)
using a hand-built `SimpleNamespace` stub that already carries
`.structural_units`. But nothing in the LIVE pipeline ever builds such a
stub for a real ingested article:

```
grep -rn "structural_unit_rules_for(\|heading_breadcrumbs=\|\.structural_units\s*=" backend/app --include="*.py"
-> ONLY registry.py's own definition (structural_unit_rules_for's def line).
   Zero call sites in profiles.py, us_profile.py, pipeline.py, sections.py.
```

`sections.py`'s `parse_articles` (still frozen, still core-owned) discards
every 3+-equals heading's text exactly as it did before this whole sprint
started (`if len(break_match.group(1)) == 2: current_chapter = ...` --
`sections.py:128`, unchanged since v1). `pipeline.py`'s `MatcherArticle(...)`
construction (`pipeline.py:190`) passes only `number/heading/body/chapter`
-- no `structural_units` kwarg, and `sections.Article`'s dataclass has no
such field to accept one anyway. **Consequence: a `"siman"`/`"chelek"`-
scoped `Definition` can be CAPTURED (the row gets created -- capture never
depends on containment, `pipeline.py`'s Stage-2/candidate-persistence loop
runs before any containment check) but can NEVER produce a `USES_DEFINITION`
edge on the live path**, because `getattr(article, "structural_units", ())`
is always `()`. `StructuralUnitRule` (registered, unit-tested) has no
production consumer. Fixing this needs `sections.py` to capture
`heading_breadcrumbs` (exactly the "single, ONE-PLACE... made ONCE by
core" change seam v2.1 §3 already specified) plus `pipeline.py` to call
`structural_unit_rules_for` and populate `MatcherArticle.structural_units`
-- both frozen/shared, off-limits to this sprint's family panel. I did NOT
write a containment RED test for סימן/חלק for exactly the reason the
original Planner gave for the original E1: there is nowhere for a
live-path test to observe the expected behavior. Recommend the manager
route this back to core (or the program manager) as a scoped, ONE-TIME
wiring request -- the mechanism it would activate already exists and is
already tested in isolation.

**(2) NEW escalation E6 (severity: HIGH -- blocks the sprint's single
largest item) -- `EntrySplitterRule`/`TermClauseRule`/`HeadingRule`/
`BodyPreambleRule` have ZERO production consumers anywhere.**

```
grep -rn "entry_splitter_rules_for\|term_clause_rules_for\|heading_rules_for\|body_preamble_rules_for" backend/app --include="*.py"
-> ONLY registry.py's own def lines for all four functions. No caller.
```

`HebrewProfile.extract_definitions_from_section` (`profiles.py:180-188`)
calls `extract.extract_definitions_from_section(text, scope=scope)`
DIRECTLY -- it never touches the registry (contrast with
`HebrewProfile.find_citations`, which DOES consult
`registry.citation_rules_for` in a baseline-first-then-union pattern, and
`HebrewProfile.extract_local_scope_definitions`, which DOES consult
`registry.scope_trigger_rules_for`). `pipeline.py`'s own dispatch
(`pipeline.py:220-232`) is a strict `if is_definitions_section: ... else:
...` -- a definitions-heading article NEVER falls through to
`extract_local_scope_definitions`/`ScopeTriggerRule` either. Item 5 (I2(d),
class (d), 592 files -- "the single largest and most severe finding of
this sprint," per the prior Planner's own words) is EXACTLY the shape the
seam's own worked-example file list (`us_entry_marker_variants.py`,
`us_multiterm_shared_clause.py`) says `EntrySplitterRule`/`TermClauseRule`
exist to solve. **No new file in `rules/`, however written, can ever be
reached for this class under the current wiring.** I did not spec item 5
as "ready" -- it is marked BLOCKED in the rewritten contract, with the
exact fix location named (`HebrewProfile.extract_definitions_from_section`
needs the same baseline-first-then-union treatment `find_citations`
already got) so whoever picks this up next does not have to re-derive it.
This is, in my assessment, the most consequential finding of this
resumption -- it is not a corner case, it is the sprint's headline gap.

**(3) NEW escalation E7 (smaller, same family as the original E1/E2) --
no registered-rule seam extends `resolve_unit_path`'s marker vocabulary.**
`HebrewProfile.resolve_unit_path` (`profiles.py:229-245`) is a concrete
method with a HARDCODED regex, `_IL_SUBSECTION_MARKER_RE = re.compile(r"
סעיף\s+קטן\s+\(([א-ת]+)\)")` -- literally the phrase "סעיף קטן (X)". It
consults no registry. The fifth class (`בפסקה זו`, 522 files) and the new
sixth class (`בפרט זה`, item 9 below) both use a COMPLETELY DIFFERENT
below-article marker convention in the real corpus -- colon-indented
numbered/lettered list items (e.g. `: (8)(א)`, `: (3)` then `::-`
sub-entries), never the literal phrase "סעיף קטן". So `resolve_unit_path`
can never recognize either class's real marker shape, meaning
`_subsection_contains_offset` will always return `False` for a mention
inside either class's own scope, even a mention in the SAME paragraph/item
as its own definition. **This means the earlier log entry's "E2 withdrawn
... class 5 ships as scope='subsection', resolved, no director decision
needed" overstated the resolution**: CAPTURE is genuinely fine (verified,
unchanged), CONTAINMENT is not -- I am correcting that framing here,
append-only, per this file's own convention, not editing the earlier
entry. Both the fifth-class test (already existing, unrevised) and item
9's new test are deliberately CAPTURE-only for this reason, matching the
discipline the original Planner already used before E2's premature
"withdrawal."

### Live re-confirmation: `בפרט זה` (the sixth class, P-E3)

Ran three live corpus scans through the REAL, unmodified `sections.py`/
`normalize.py`/`extract.py` (never a mock), against
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws` (read-only,
verified untouched afterward):

1. Raw substring `בפרט זה` anywhere: **68 files, 199 occurrences**
   corpus-wide (broader than the exact shape below -- includes other
   grammars, e.g. the ad-hoc `(להלן בפרט זה - X)` apposition variant found
   in `תקנות התעבורה` article 8א, a THIRD grammar not covered by this
   sprint's item 9 and flagged here for a future item, not silently
   dropped).
2. EXACT target shape (`בפרט זה -` line immediately followed, after
   skipping blank lines, by a line starting `::-`): **7 real corpus
   files** -- `חוק מימון מפלגות`, `רשימת הזכויות לפי חוק לקידום התחרות
   ולצמצום הריכוזיות` (the already-vendored fixture), `תקנות התכנון
   והבניה (בקשה להיתר, תנאיו ואגרות)`, `תקנות התכנון והבנייה (הקמת מכון
   בקרה ודרכי עבודתו)`, `תקנות התעבורה`, `תקנות ניירות ערך (זירת סוחר
   לחשבונו העצמי)`, `תקנות שוויון זכויות לאנשים עם מוגבלות (התאמות נגישות
   לאתר)`. Reported as a freshly-measured, more precise number against the
   brief's own "~8-12 files" ESTIMATE -- not a contradiction of it, a
   refinement.
3. Confirmed via the real `sections.parse_articles` (not raw-text grep)
   that the vendored fixture's law parses to exactly ONE article, number
   `@1` (core's bare-`@` fix, M8(a)), heading `""` (empty ->
   `is_definitions_heading("") is False`, confirming this routes through
   the WIRED ordinary-article path, `extract_local_scope_definitions`, not
   item 5's BLOCKED definitions-section path) -- matching the brief's own
   framing exactly ("REACHABILITY was core's -- delivered. CAPTURE is
   MINE.").

Also live-reconfirmed, per M4's discipline ("class does not reproduce as
stated -- report the difference"): the original contract's class-(a)
`לפרק זה` trigger word does **NOT reproduce** anywhere in the real corpus
as a definitional grammar. Raw scan: 103 occurrences of the phrase, 100%
cross-references (`סימן ג' לפרק זה`, `התוספת לפרק זה`, "the appendix TO
this chapter" / "siman X OF this chapter" -- structurally the OPPOSITE of
a scope trigger, a reference FROM inside the chapter to a sub-part of
itself). Zero matched the `TRIGGER, "term" - definition` grammar even with
a generous scan (checked all 103 for a nearby quote+dash, zero hits).
**`לפרק זה` is dropped from item 2a's trigger-phrase spec** -- implementing
it as originally worded would add a regex with zero true positives and a
non-zero risk of a hasty pattern snagging cross-reference text instead.

New real, verbatim fixtures added (COPIES from the read-only POC corpus,
corpus itself re-verified untouched after this session):
`backend/tests/fixtures/wiki_laws/חוק איסור מימון טרור_art31_excerpt.wiki`
(`בסימן זה` quote-first, term "בית המשפט"),
`backend/tests/fixtures/wiki_laws/חוק השיפוט הצבאי_art159א_excerpt.wiki`
(ONE real article exhibiting BOTH `בחלק זה` quote-first, term "הוראת
פרקליט", AND the ad-hoc-parenthetical `([[בחלק זה]] - חוות דעת)` shape --
efficient corpus reuse, both classes' סימן/חלק sub-cases now have a real
fixture).

### New test file (additive only -- no existing test touched)

`backend/tests/integration/test_definition_links_il_missed_classes_extended_live.py`
-- 4 NEW tests, all RED today for behavioral reasons (verified by my own
run, transcript below):

- `test_class_a_besiman_zeh_scoped_quoted_definition_is_captured`
- `test_class_a_bechelek_zeh_scoped_quoted_definition_is_captured`
- `test_class_c_adhoc_parenthetical_bechelek_zeh_marker_is_captured`
- `test_sixth_class_beprat_zeh_item_scoped_double_colon_entries_are_captured`

### Deliverable 3 -- verification of the 8 existing RED tests under v2.5

Read all 8 in full (`test_definition_links_il_missed_classes_live.py`'s 7
tests + `test_definition_links_il_chapter_scope_live.py`'s 1 test).
**None required revision. Zero existing tests edited.** Reasoning, per
test:

- The 7 capture-only tests (classes a/b/c/d-i/d-ii/d-iii/fifth) assert
  ONLY on `result["created_definitions"]` term membership -- none pins a
  `scope` value, a `scope_value`, or any containment/`USES_DEFINITION`
  behavior. Nothing about v2->v2.5's scope-model changes (4-way enum ->
  generic `(kind, value)` -> `UnitPath` prefix-matching -> transient-only
  `scope_value`) touches what these tests actually assert. They remain
  exactly as valid under v2.5 as under the v2 model they were originally
  planned against.
- The 1 containment test (`test_beperek_zeh_definition_links_within_
  chapter_and_not_outside_it`, gate I3) exercises the `"chapter"` scope
  kind specifically -- the ONE kind that was ALREADY fully wired before
  this whole seam sprint even started (`Article.chapter` /
  `definition.source_chapter` / `matcher._in_scope`'s dedicated chapter
  branch are all pre-existing, unchanged by any seam version). v2.5
  changes nothing about this kind's mechanism. Still valid, unrevised.

### Suite proof (my own run, worktree venv)

```
backend/.venv/bin/pytest backend/tests -q
-> 12 failed, 704 passed, 18 warnings in ~19s
```

704 = the exact pre-resumption baseline (confirmed identical to the
manager's own post-rebase count -- zero regressions, zero existing tests
touched, verified via `git status --short` / `git diff --stat` showing
only new, untracked files before staging). 12 failed = the 8 pre-existing
Phase-B REDs (unchanged, still failing for the same behavioral reasons as
before this session) + the 4 new REDs above, all `AssertionError`
("expected N, got [...]" / "got {'חוק ניירות ערך'}" for the sixth-class
test, confirming the pipeline runs end-to-end and merely fails to capture
the intended terms -- not an import/collection error).

### Escalation table, updated (append-only -- prior rows kept verbatim)

| # | Status | Owner of the answer |
|---|---|---|
| E1 (original, schema) | ANSWERED by the shipped seam (unchanged from the prior entry) | resolved |
| **E1 (wiring, this session)** | **OPEN -- NEW finding: `StructuralUnitRule`/`heading_breadcrumbs` mechanism exists but has zero production wiring** | core / program manager |
| E2 | superseded -- see E7 below (capture resolved, containment reopened) | resolved (capture) / see E7 |
| E3 | settled, ruling M7 (unchanged, do not re-litigate) | manager |
| E4 | settled, ruling M6 (unchanged) | manager |
| E5 | corrected, ruling P-E3 (program manager) -- superseded by item 9 above | resolved (reframed) |
| **E6 (NEW)** | **OPEN -- `EntrySplitterRule`/`TermClauseRule`/`HeadingRule`/`BodyPreambleRule` have zero production consumers; blocks item 5/I2(d), the sprint's largest finding (592 files)** | core / program manager |
| **E7 (NEW)** | **OPEN -- no registered-rule seam extends `resolve_unit_path`'s marker vocabulary; blocks containment for the fifth class and item 9 (below-article granularity)** | core / program manager |

### Open questions for the manager (escalating, not guessing)

1. E1(wiring)/E6/E7 all point at the same root shape: the seam SPEC
   describes dispatch that the seam IMPLEMENTATION does not yet wire for
   four of seven registered rule kinds, plus the below-article marker
   vocabulary. Is the right move to route these back to core as scoped,
   named wiring requests (I named the exact one-line-of-reasoning fix for
   each), or does the program manager want this sprint to escalate further
   up before any Phase-B implementation resumes on items 2b/5/7/9's
   containment halves?
2. Item 5 (class (d), 592 files) is now the sprint's single most
   consequential BLOCKED item. Given I4/I5 cannot close without it (it is
   ~9.7% of the whole corpus), should the sprint's own gate status
   (currently `blocked`) reflect this explicitly, or is this already
   understood from the E6 entry above?
3. Confirming scope, not asking permission: items 2a/3/4(chapter
   sub-case)/7/9 are all genuinely Phase-B READY (capture, and for 2a also
   containment) with no further architecture blocker found. If the
   Developer is dispatched now, these five are safe to implement
   immediately without waiting on E1(wiring)/E6/E7.

---

## 2026-08-04 — Program ruling P-R8 received; ruling M11 (live/dead split)

Rebased onto `origin/main` `0f4e8fc` (8 commits replayed, no conflicts);
venv refreshed; suite re-verified by me: **12 failed, 704 passed** (8 prior
REDs + the Planner's 4 new ones; 704 baseline intact).

**P-R8: 5 of 7 registry rule kinds are DEAD on the live path.** This is
*convergent* with my Planner's own independent finding (E6/E7/E1-wiring),
which it reached by exhaustive grep for callers of
`entry_splitter_rules_for` / `term_clause_rules_for` /
`structural_unit_rules_for` — zero, in all cases. Two panels finding the
same defect by different routes is strong evidence; I am treating P-R8 as
authoritative and my Planner's escalations as answered by it.

### M11 — what this sprint builds NOW vs. what holds

**`ScopeTriggerRule` is LIVE** (core's own `rules/il_scope_triggers.py`
dispatches for real). Every one of our Hebrew trigger-content classes is a
`ScopeTriggerRule`, so the *capture* half of this sprint is buildable now:

| Item | Class | Stamps | Status under M11 |
|---|---|---|---|
| 2a | `בפרק זה` | `scope="chapter"` (+ `source_chapter`) | **BUILD NOW** — capture AND containment (chapter kind was wired before the seam sprint) |
| 2b | `בסימן זה`/`בחלק זה` | `scope="siman"`/`"chelek"` | **BUILD NOW, capture only** — containment HELD (StructuralUnitRule dead) |
| 3 | 3-word `לעניין סעיף זה` | `scope="local"` | **BUILD NOW** |
| 4 | ad-hoc `(בפרק זה - X)` | chapter / siman / chelek by trigger | **BUILD NOW** — chapter containment live; siman/chelek capture-only |
| 7 | `בפסקה זו` | sub-article | **BUILD NOW, capture only** — containment open (E7: `resolve_unit_path`'s marker regex is hardcoded) |
| 9 | `בפרט זה` (sixth class, P-E3) | item-level | **BUILD NOW, capture only** |
| 5 | class (d) prose-body sections | — | **HELD** — needs `EntrySplitterRule`/`TermClauseRule` (both dead) or a frozen-module edit. Holds either way. |
| 6 | I3's סימן/חלק containment half | — | **HELD** — blocked-on-core-dispatch |

**Consequence for gates, stated honestly:** I2 becomes largely achievable
now (capture for classes a/b/c/e/f); **I3 splits** — its `בפרק זה` chapter
half is achievable now, its סימן/חלק half is blocked-on-core-dispatch.
Item 5 is the single largest held item (592 files, ~9.7% of the corpus)
and I am recording it as the sprint's most consequential blocker, per the
Planner's escalation #2.

`לפרק זה` was DROPPED from class (a) on live evidence (103 occurrences,
100% cross-references, zero definitional). Recorded because it *reduces*
claimed coverage — the honest direction.

I4's adversarial sweep still waits for full implementation, and remains
bound by M10 (corrected E5 facts + P-R7 independent denominators).

---

## 2026-08-04 — Manager verification of the Developer handoff (items 2a/2b/3/4/7/9)

### Verified MYSELF

- `git diff --name-status d97324c..HEAD` → six entries, all `A`, all under
  `backend/app/definition_links/rules/`. **Nothing else.**
- Frozen check against all five modules → **none touched**.
- Test/fixture check on the dev commit → **none touched**.
- Style gate: 42-84 lines each (390 total incl. core's own 36-line example)
  — all well under 300.
- Manager-run suite: **`3 failed, 713 passed, 18 warnings in 14.16s`**
  (was `12 failed, 704 passed`). 713 = 704 baseline + 9 newly green. The 3
  remaining failures are exactly the class-(d)/item-5 tests, which are
  correctly held on core's dispatch-completion sprint per P-R8 — the
  Developer did NOT attempt them, which is the correct behavior.

**Handoff ACCEPTED.**

Notable: item 2a's rule correctly sets `source_chapter=ctx.chapter` itself
(the gotcha the Planner surfaced), and the containment test passes in BOTH
directions — same-chapter articles 13/16/17 link, different-chapter article
20 does not, despite carrying the same surface form. **Gate I3's chapter
half is now PROVEN on real corpus text**, not just specced.

Items 2b/7/9 are capture-only *by construction*: their scope kinds
(`siman`/`chelek`/`paragraph`/`item`) fall to `matcher._in_scope`'s generic
branch, which is always False in production because nothing populates
`article.structural_units`. No guard code was needed to achieve that, and
no false containment can leak. Clean.

Naming call the Developer flagged as unpinned by any test: item 7 uses
`scope="paragraph"`. Reasonable and consistent with item 9's `"item"`;
**recorded here so core's dispatch sprint can align kind names** if it
standardizes a vocabulary. Not worth an escalation.

### New zero-miss gap found by the Developer during its P-R2 sweep

`חוק הבנקאות (שירות ללקוח)_excerpt.wiki:16` contains
`(בפסקה זו - חוק הדואר)` — item 4's ad-hoc `(TRIGGER - term)` shape, but
with a trigger word outside item 4's list. The Developer left it alone
rather than scope-creeping, and reported it. **That is exactly the right
behavior**, and it is a confirmed miss under the absolute zero-miss bar.
`ScopeTriggerRule` is LIVE, so this is buildable now — I have sent the
Planner back to size the gap across ALL ad-hoc trigger words (not just this
one instance) and author the RED test.

---

## 2026-08-04 — Manager: corpus-wide capture measurement (I2 evidence)

Explicitly-invoked probe (NOT part of `pytest`), running the REGISTERED
rules through the real `HebrewProfile.extract_local_scope_definitions` seam
over all 6,133 laws / 128,234 parsed articles:

```
files with >=1 ordinary-article scoped definition: 3294

captured candidates by scope kind:
  local        11095
  chapter        878
  siman          404
  paragraph      364
  chelek          38
  item            26
  TOTAL        12805
```
`chapter`/`siman`/`chelek`/`paragraph`/`item` did **not exist as scope kinds
before this sprint** — so **1,710 scoped definitions across the real corpus
are newly captured** by items 2a/2b/4/7/9. `local` (11,095) mixes core's
baseline triggers with item 3's 3-word widening and is not separable
without a before/after run; I am NOT claiming it.

One real example per kind was captured and logged (e.g. `[siman]`
חוק אוויר נקי art.18 `"בקשה"`; `[item]` חוק מימון מפלגות art.3 `"ישיבה"`).

### **I made the wrong-layer measurement error a SECOND time — recording it**

My first pass of this probe returned **chapter=0, siman=0, chelek=0** and I
nearly reported the new rules as non-functional on real data. They were
fine; **my probe was wrong.** I called `extract_local_scope_definitions` on
raw `parse_articles` output, but the live path (`pipeline.py:188`) applies
`normalize_for_parsing` **and `strip_wikilinks`** first. The real corpus
writes the trigger as `[[בפרק זה]],` — a wikilink — so the rule's
`בפרק זה,` regex could never match un-stripped text. With the correct
chain the number is 878, not 0.

This is the **same failure shape as my E5 error**: measuring at a layer the
production path does not use. Twice in one sprint. Naming it because it is
the single most useful thing this log can teach the next panel — and because
it is exactly the trap **P-R7** exists to prevent, which makes it doubly
binding on QA's I4 sweep (ruling M10): **any sweep denominator or capture
count MUST be produced through the real pipeline preprocessing chain
(`normalize_for_parsing` → `strip_wikilinks` → profile seam), never by
regexing raw corpus text.** I have now demonstrated both directions of this
error — false alarm (this) and false attribution (E5).

### Quality check on a suspicious shape — resolved, not a defect

Several captures have `definition_text == term` (e.g. חוק אומנה לילדים
art.23: `(בפרק זה - המבקש)` → `terms=('המבקש',) def='המבקש'`). I checked
core's baseline `extract.extract_adhoc_definitions` before flagging it: it
sets `definition_text=term` for the ad-hoc apposition form by design. Our
item-4 rule follows the established convention. **Not a defect.**

### Jurisdiction isolation verified

`registry.scope_trigger_rules_for("IL")` → **8** rules (core's 2 + our 6);
`scope_trigger_rules_for("US-CA")` → **1** (core's proof rule only). Our
Hebrew rules do not leak into any US profile.


---

## 2026-08-04 — Planner: manager-requested miss, "ad-hoc trigger widening round 2"

Resumed at `c50fd32` (already in sync with `origin/claude/defs-il`, no
pull/rebase needed -- verified via `git rev-parse HEAD` == `git rev-parse
origin/claude/defs-il`). Confirmed the Developer's six shipped
`ScopeTriggerRule` modules independently: `backend/.venv/bin/pytest
backend/tests -q` -> `3 failed, 713 passed` (matches the manager's report
exactly) -- the 3 REDs are precisely items 5's class-(d) tests, all others
green.

### Live re-confirmation of the manager-flagged miss (ruling M4 -- leads aren't proof)

Ran the REAL live pipeline (`ingest_wiki_law` + `run_definition_linking`,
not a mock) against the manager's own cited fixture
(`חוק הבנקאות (שירות ללקוח)_excerpt.wiki`, already vendored by the
Developer). Confirmed: `גוף פיננסי` (an ordinary `:-`-entry term in the
SAME section) IS captured today (19 total definitions from this fixture),
`חוק הדואר` (the ad-hoc `(בפסקה זו - חוק הדואر)` marker embedded inside
`גוף פיננסי`'s own body text) is NOT -- genuine, confirmed miss.

**But the mechanism is different from the manager's framing, and I am
correcting it rather than silently building around it (M4: report the
difference).** Article 1's heading is `הגדרות (תיקון: ...)` --
`is_definitions_heading(...) is True`. `pipeline.py`'s dispatch (lines
220-232, re-verified this session, unchanged) means a definitions-heading
article's body NEVER reaches `extract_local_scope_definitions`/
`ScopeTriggerRule` at all -- only `profile.extract_definitions_from_
section` runs, and that function (per this session's earlier E6 finding)
has zero registry consumption and never re-scans an already-extracted
entry's OWN body text for an embedded ad-hoc marker. So widening item
4/10's `il_adhoc_scope_triggers.py` trigger list would do NOTHING for
this SPECIFIC occurrence -- it is a new, real instance of item 5's E6
blocker, not a trigger-list gap. Written up as its own contract item
(11, BLOCKED) rather than folded into item 10's "ready" framing.

### Corpus frequency table (the manager's explicit ask -- "size the gap honestly")

Live-scanned every candidate trigger word for the `(TRIGGER - term)`
ad-hoc apposition grammar, through the real `sections.parse_articles` +
`is_definitions_heading` (not raw-text grep), split by ordinary-article
(immediately fixable) vs definitions-heading (E6-blocked, same as item 5):

| Trigger | Total | Files | In ordinary article | In definitions-heading section |
|---|---|---|---|---|
| `בסעיף זה` | **2,335** | **572** | 2,328 | 7 |
| `בפסקה זו` | 221 | 117 | 213 | 8 |
| `בפרט זה` | 13 | 5 | 13 | 0 |
| `לענין זה` | 2 | 2 | 2 | 0 |
| `לענין סעיף זה` | 2 | 2 | 2 | 0 |
| `לעניין זה` / `לעניין סעיף זה` | 0 | 0 | 0 | 0 |

**`בסעיף זה` is the standout finding: 2,335 occurrences / 572 files is
larger than class (d)'s own 592-file finding, previously this sprint's
largest.** 25 random samples manually inspected for quality (seed 42, not
cherry-picked) -- all genuine short defined-term appositions (`המועד
החוזי`, `התקרה`, `יום התחילה`, `ועדת הבדיקה`, ...), zero verb-shaped or
citation-shaped false positives observed, same low-risk profile the
original Planner found for classes (a)/(b)/(c)'s other trigger words.

**No P-R2 conflict found** -- every sampled occurrence across every
trigger word reads as a genuine definitional apposition, same grammar and
same 4-token-cap discipline already trusted for `להלן`/`בפרק זה` etc. Not
escalating a zero-miss-vs-zero-false-positive trade because none was
observed; reporting the real numbers as asked rather than picking a side
that isn't actually in tension here.

### New fixtures + tests (additive to my own file, per the manager's "it's yours")

Two new real, verbatim fixtures: `חוק ההתנתקות והפיצויים לנפגעיה_
art45_excerpt.wiki` (`בסעיף זה` ad-hoc, term "מענק נוסף", ordinary
article), `תקנות הרופאים (פרסומת אסורה)_art3_excerpt.wiki` (`בפסקה זו`
ad-hoc, term "תמורה", ordinary article). Reused the Developer's already-
vendored `חוק הבנקאות (שירות ללקוח)_excerpt.wiki` for the E6-blocked
sub-case (no new fixture needed).

Three new tests appended to `test_definition_links_il_missed_classes_
extended_live.py` (my own file):
- `test_class_c_adhoc_parenthetical_beseif_zeh_marker_is_captured`
- `test_class_c_adhoc_parenthetical_beparagraph_zo_marker_in_ordinary_article_is_captured`
- `test_class_c_adhoc_parenthetical_beparagraph_zo_inside_definitions_section_is_captured`
  (BLOCKED by E6, correctly RED, kept anyway -- same precedent as item 5's
  three tests, which this sprint already established as legitimate: a
  RED test proving a real, confirmed miss is authored even when the fix
  needs a shared-file wiring change outside this sprint's reach).

### Suite proof (my own run)

```
backend/.venv/bin/pytest backend/tests/integration/test_definition_links_il_missed_classes_extended_live.py -v
-> 3 failed (the three new tests, all AssertionError -- e.g. "expected
   a Definition row for ... 'מענק נוסף' ...; got [...]" with real
   created_definitions lists, not import errors), 4 passed (the
   already-green tests from this file's earlier round)

backend/.venv/bin/pytest backend/tests -q
-> 6 failed, 713 passed, 18 warnings in ~15s
```
713 = unchanged (matches the Developer/manager's post-implementation
baseline exactly). 6 = item 5's 3 pre-existing REDs (unchanged) + this
round's 3 new REDs. Zero existing tests touched (verified `git diff
--name-status` shows only additions to files this Planner already owns,
plus the contract/log).

### Contract updated

Added items 10 (ready, `ScopeTriggerRule`, LIVE per M11/P-R8 -- `בסעיף
זה`/`בפסקה זו` ordinary-article ad-hoc widening) and 11 (BLOCKED, same
E6 as item 5 -- the manager's originally-cited definitions-heading
instance). Contract now exactly 400 lines (`scripts/contract_lint.sh`
budget, still PASS). Pre-existing lint FAIL (`last_updated` not full
ISO-8601) predates this session's edits -- frontmatter is left untouched
per this Planner's own scoping (Next Steps section only), flagging rather
than silently fixing governance fields outside the brief.

### Nothing to escalate as a P-R2 conflict this round

Explicitly checked per the manager's closing instruction: no real corpus
example was found where widening the ad-hoc trigger set risks a
false-positive against a genuine zero-miss need. Reporting real numbers,
not picking a side, because no side needed picking this time.

---

## 2026-08-04 — Manager verification: Planner round 2 + Developer item 10

### Planner round 2 (`e544a8c`) — ACCEPTED, and it corrected ME

It re-confirmed the miss I flagged, then **corrected my framing with live
evidence**, which is exactly the standard I hold the panel to: the
`(בפסקה זו - חוק הדואר)` occurrence I cited sits inside an article whose
heading IS a הגדרות heading, so `pipeline.py`'s dispatch never routes that
body to `extract_local_scope_definitions` at all. Widening a trigger list
could not have reached it. It is a new instance of the **E6** blocker, not a
trigger-list gap — filed as item 11, BLOCKED, instead of being folded into a
"ready" item. **Correction accepted.** That is now three times this sprint a
framing was corrected by evidence (my E5, my wrong-layer probe, and this).

Its corpus sizing found the **largest population of the whole sprint**:
ad-hoc `(TRIGGER - term)` with `בסעיף זה` = 2,335 occurrences / 572 files
(2,328 in ordinary articles), bigger than class (d)'s 592 files. 25 random
samples (seed 42, not cherry-picked) hand-verified genuine, zero verb-shaped
false positives.

### Developer item 10 (`a3505b6`) — ACCEPTED

Verified by me: **one** production file modified
(`rules/il_adhoc_scope_triggers.py`, 110 lines — under 300); **zero** test or
fixture edits; **zero** frozen-module edits. Suite reproduced by my own run:
**`4 failed, 715 passed`** (net +2). The 4 = 3 held class-(d) + 1 E6-blocked
definitions-section variant — all expected. The Developer verified the E6
blockage itself rather than trusting my framing. The ≤4-token cap that keeps
this class's false-positive rate at zero is preserved.

### Corpus-wide capture, re-measured through the real seam after item 10

```
files with >=1 ordinary-article scoped definition: 3375   (was 3294)

  local        13355   (was 11095  -> +2260 from בסעיף זה)
  chapter        878
  paragraph      578   (was   364  ->  +214 from בפסקה זו)
  siman          404
  chelek          38
  item            26
  TOTAL        15279   (was 12805  -> +2474 from item 10)
```
**Sprint total newly-captured scoped definitions: ~4,184** — 1,924 in scope
kinds that did not exist before this sprint (chapter/siman/chelek/paragraph/
item) plus ~2,260 `בסעיף זה` ad-hoc appositions now landing as `local`.

### Contract hygiene

`scripts/contract_lint.sh 2026-08-04-defs-il` → **PASS 400** (all 7 checks).
I fixed two lint FAILs that were mine: `last_updated` was a bare date (now
ISO-8601 UTC) and the item counters were stale (now `total_items: 12`,
`completed_items: 8`, `dev_complete_items: 8`). The contract is at exactly
**400/400 lines — at the cap**, so all further detail goes here, per the
size-budget rule.

---

## QA cycle 1 (Sonnet/high, independent)

Read the contract in full (gates I1-I5, items 1-11, rulings M1-M11) and the
whole log (all entries, not just the last four -- including the "wrong-layer
measurement error a SECOND time" and the Planner-corrects-the-manager entry
named in the brief as the sprint's own worked examples of what to distrust).
Worktree `/Users/nerya/LexGraph-wt/defs-il`, branch `claude/defs-il`, HEAD
`39c3b7a` (verified clean, in sync with `origin/claude/defs-il`). All
verification below is MY OWN run, in the worktree venv, never trusting a
prior role's report. **I never touched `backend/app/**` -- verified after
every probe via `git status --short` (clean except this log + the contract
frontmatter timestamp/`qa_cycles` bump below).**

### Gate I5 (regressions) -- PASS

- `backend/.venv/bin/pytest backend/tests -q` -> **`4 failed, 715 passed,
  18 warnings in ~14s`**, reproduced twice, byte-identical both times. The 4
  failures are exactly `test_class_c_adhoc_parenthetical_beparagraph_zo_
  inside_definitions_section_is_captured` (E6-blocked, item 11) +
  `test_class_d_prose_body_definitions_section_yields_zero_today` /
  `test_class_d_variant_double_colon_entry_list_under_a_trigger_preamble_
  is_captured` / `test_class_d_minimal_single_sentence_variant_is_captured`
  (held class d) -- matches the contract's claimed baseline exactly.
- `npm --prefix frontend run test -- --run` -> **`165 passed (165)`,
  `25 passed (25)` files**.
- `npm --prefix frontend run typecheck` -> clean (`tsc --noEmit`, no output).
- `bash scripts/contract_lint.sh 2026-08-04-defs-il` -> **PASS 400** (all 7
  checks), reproduced.
- `git diff --name-status origin/main...HEAD -- backend/tests` -> every
  entry `A` (addition). **No existing test edited.**
- `git diff --stat origin/main...HEAD -- backend/app` -> exactly 8 files,
  all under `rules/` or the two new `ingest_wiki_corpus*.py` modules. No
  frozen module (`pipeline.py`/`matcher.py`/`extract.py`/`sections.py`/
  `profiles.py`) touched.

### Gate I1 (full corpus loads) -- PASS on its literal terms, with a stale-number finding

Independently re-ran the bulk ingest myself: own scratch sqlite DB, own
script calling the real `app.definition_links.ingest_wiki_corpus.
run_bulk_ingest` (not a re-implementation) against the real, read-only
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws`. Result: **files
found 6133, files processed 6133, files failed 0** -- confirms the literal
gate. Corpus re-verified untouched afterward (`ls | wc -l` -> 12266,
unchanged).

**Finding: the contract's recorded `127,903 articles` is stale.** My run
measured **128,234 articles** (+331). Root cause, verified: the manager's
original I1 run (which produced 127,903) executed BEFORE `claude/defs-il`
was rebased onto core's merged `main` -- i.e. before core's bare-`@` parser
fix (M8(a)) landed. My run is on HEAD `39c3b7a`, post-merge. **+331 matches
EXACTLY the corrected P-E3 bare-`@` figure ("331 occurrences across 42
files")** -- strong independent confirmation that core's reachability fix
is live and doing exactly what it claims, but the contract's own I1 numbers
should be corrected to 128,234 (not a gate failure -- 6,133/6,133, 0
failures both times -- a documentation-accuracy note). Wall
time/memory (48.5s / 87.7 MiB RSS on my run vs. the recorded 37.4s / 76.3
MiB) differ by machine/disk conditions (my scratch DB sits under
`/private/tmp`), same order of magnitude, not itself a finding.

### Gate I3 (scope containment) -- PASS, attacked on TWO independent real corpus laws not used by any existing test

**Attack 1 -- chapter scope, both directions, on a law the sprint's own
fixture never touches.** Ingested the FULL, unedited
`חוק הבוררות המסחרית הבין-לאומית.wiki` (48 real articles, not an excerpt)
through the live pipeline (`ingest_wiki_law` + `run_definition_linking`).
Article 18 (chapter `פרק ה': סעד זמני`) defines `"סעד זמני"` via `בפרק
זה`, scope=chapter. Ground truth (`find_term_uses` over every article's raw
body): the term appears in articles 10, 18, 19, 20, 22, 23, 24, 25, 26.
Live result: **linked to 18/19/20/22/23/24/25/26 (all same chapter, `פרק
ה'`) and correctly NOT linked to article 10** (different chapter, `פרק ב':
הסכם בוררות`), despite article 10's body genuinely containing the surface
form. Both directions match ground truth exactly.

**Attack 2 -- siman/chelek/paragraph/item containment is genuinely inert
(the safe-failure direction), not merely untested.** Ingested the FULL,
unedited `חוק אוויר נקי.wiki` (136 articles) live. 6 real
siman/paragraph-scoped `Definition` rows were captured (scope=siman:
`בקשה`/`מפר`/`הודעה על כוונת חיוב`; scope=paragraph: `מזהם`/`מסמך`;
+1 siman `דרישת תשלום`). **All 6 produced ZERO `USES_DEFINITION` edges** --
including `בקשה` (siman-scoped, article 18), which genuinely appears
(`find_term_uses`) in **23 other articles** of the same law, several in the
SAME siman -- proving this is a real missed-linking opportunity that stayed
correctly unlinked, not an untested code path that happens not to fire.
CHECK: my own probe scripts (not any existing test), transcripts above.

### Gate I4 (zero-miss sweep) -- **FAIL. Confirmed, real, live-verified misses. This is the headline finding.**

#### Methodology and the independence argument (ruling M10 / P-R7)

Built **two structural, trigger-independent ground truths**, both scanned
through the REAL live preprocessing chain (`sections.parse_articles` on raw
`.wiki` text -> `HebrewProfile.normalize_for_parsing` ->
`strip_wikilinks`, the exact order `pipeline.py:187-188` uses) -- never raw
grep, per the manager's own "wrong-layer" lesson (M10) which this cycle
treats as binding, not merely advisory:

1. **Generic quote-first grammar**: any `"term" -` (quote, close-quote,
   dash) anywhere in a normalized article body, regardless of what -- if
   anything -- precedes it. This is NOT built from our trigger list; it is
   the bare grammar every one of this sprint's OWN rules eventually keys
   on, generalized to any preceding context. **60,114 raw hits / 4,500
   files** corpus-wide.
2. **Generic `::-`-nested-entry-list-under-a-bare-preamble grammar**: any
   line ending in `-` immediately followed (blank lines skipped) by a
   `::-`-marked line -- the exact structural shape item 9's own rule
   already trusts for the ONE trigger word `בפרט זה`, generalized here to
   ANY preceding text, not that one hardcoded phrase. **2,300 occurrences**
   corpus-wide.

Neither denominator was built by grepping our own implemented trigger
phrases -- that is precisely what let them surface trigger words nobody on
this sprint had ever catalogued. Every finding below was then independently
confirmed LIVE (not assumed from the denominator alone) by calling the
real, unmodified `extract.extract_local_definitions` /
`HebrewProfile.extract_local_scope_definitions` functions directly on real
corpus excerpts and observing `[]`.

#### CONFIRMED MISS GROUP A -- new/unimplemented single-line quote-first triggers

| Family | Occ. | Files | Ordinary | In הגדרות-heading (E6-blocked) |
|---|---|---|---|---|
| `לעניין זה` (tzere spelling; baseline only covers `לענין זה`) | 1,702 | 714 | 1,563 | 139 |
| `בסעיף קטן זה` (subsection scope -- entirely new) | 313 | 213 | 313 | 0 |
| `בתקנה זו` (regulation-local -- entirely new) | 427 | 289 | 427 | 0 |
| `לעניין/לענין תקנה זו` (regulation-local, 3-word) | 104 | 90 | 104 | 0 |
| `בתקנת משנה זו` (sub-regulation) | 83 | 68 | 83 | 0 |
| `תקנת משנה זו` (bare) | 42 | 39 | 42 | 0 |
| `לעניין/לענין פסקה זו` (paragraph, alt phrasing) | 132 | 98 | 121 | 11 |
| `בפסקת משנה זו` (sub-paragraph) | 59 | 46 | 59 | 0 |

Live-verified `[]` on real excerpts (function called directly, no mock):
- `הוראות הפיקוח על שירותים פיננסיים (ביטוח)...` art.3: `לעניין זה,
  "ביטוח מועדף" - כהגדרתו בסעיף 32(14) לפקודת מס הכנסה.` ->
  `extract_local_definitions` = `[]`.
- `צו הבטיחות בעבודה (אגרות בדיקה)` art.6: `בתקנה זו, "מדד" - מדד המחירים
  לצרכן שמפרסמת הלשכה המרכזית לסטטיסטיקה.` -> `[]`.
- `החלטת הרשויות המקומיות (גמלאות לראש רשות וסגניו)` art.29ב:
  `בסעיף קטן זה, "המדד" - מדד המחירים לצרכן...` -> `[]`.
- Confirmed absent from the implementation: `grep -rn "תקנה\|תקנת משנה\|סעיף
  קטן\|פסקת משנה" backend/app/definition_links/rules/*.py
  backend/app/definition_links/extract.py` -> zero regex hits (only two
  docstring mentions of `סעיף קטן` describing an unrelated escalation).

#### CONFIRMED MISS GROUP B -- the `::-`-nested-list-under-preamble grammar is wired for exactly ONE trigger word

Aggregate, full corpus, by core trigger phrase (through the live chain):

```
GRAND TOTAL: 2,300 occurrences (2,147 in ordinary articles, 153 in
             הגדרות-heading sections)
  'בסעיף זה'            1,067 occ / 448 files  -- NOT implemented (this shape)
  OTHER/UNRECOGNIZED       825 occ / 579 files  -- NOT implemented
  'לעניין זה'              120 occ / 107 files  -- NOT implemented
  'לענין זה'                72 occ /  62 files  -- NOT implemented
  'לענין סעיף זה'           61 occ /  41 files  -- NOT implemented
  'בפרק זה'                 49 occ /  42 files  -- NOT implemented
  'בסימן זה'                39 occ /  27 files  -- NOT implemented
  'בפסקה זו'                31 occ /  24 files  -- NOT implemented
  'לעניין סעיף זה'          22 occ /  15 files  -- NOT implemented
  'בפרט זה'                 12 occ /   7 files  -- item 9 ALREADY implements this
  'בחלק זה'                  2 occ /   2 files  -- NOT implemented
```
Only 12/2,300 (0.5%) are captured. **The other 2,288 (99.5%) are a
confirmed, real, live-verified miss.** Even trigger words this sprint
ALREADY implemented for the single-line form (`בסעיף זה`, `בפרק זה`,
`בסימן זה`, `בפסקה זו`, `לענין/לעניין סעיף זה`) are missed here because
they never occur inline with their own quote in this shape -- the quote
sits on a SEPARATE `::-` line, which none of the quote-first regexes can
reach.

Live-verified on a real, whole, unedited law
(`החלטת מימון מפלגות (יחידות מימון ומועדי תשלום).wiki`, art.2):
```
: (א) בסעיף זה -
::- "מדד" - מדד המחירים לצרכן המתפרסם מדי פעם מטעם הלשכה המרכזית לסטטיסטיקה;
::- "מדד יסודי" - המדד לחודש מאי 1991.
```
`profile.extract_local_scope_definitions(...)` on this real, normalized,
wikilink-stripped body -> **`[]`** -- two genuine, unambiguous, real
definitions ("מדד"/"מדד יסודי") silently dropped despite using an
ALREADY-implemented trigger word, purely because of the `::-` list shape.
A 25-sample of the "OTHER/UNRECOGNIZED" tail (seed 42) found zero
verb-shaped/wrong matches -- every one was a genuine additional
definitional preamble (`בתקנה זו -`, `בסעיף זה ובסעיף X -` compound scope,
`בחוק זה -`/`בתקנות אלה -` law-wide, `לענין תקנת משנה (X) -`, `באמת מידה
זו -`), reinforcing that this is a real coverage gap, not noise.

#### CONFIRMED FALSE POSITIVE -- citation-shaped captures in the widened ad-hoc rule (adversarial check 3)

Ran the LIVE, registered `il_adhoc_scope_triggers` rule (not a
re-implementation) over the whole corpus: **3,605 real candidates**,
token-length histogram `{1: 942, 2: 1745, 3: 624, 4: 294}` confirms the
<=4-token cap holds structurally (zero over cap). A targeted sweep for
verb-/citation-shaped terms found **3 confirmed false positives** (0.08%):
`סעיף 149א` / `סעיף 51טו` / `סעיף 9`, all captured as
`terms=("סעיף N",), definition_text="סעיף N"`. Verified live in the raw
corpus text, e.g. `חוק המדיניות הכלכלית לשנים 2011 ו-2012 (תיקוני חקיקה)`
art.39: `... כנוסחו בסעיף 37(32) לחוק זה (בסעיף זה - סעיף 51טו), יחולו`.
This is a citation-shorthand-naming convention ("hereinafter in this
section: 'section 51טו'"), not a substantive term definition -- the same
apposition GRAMMAR our rule trusts, aimed at a cross-reference instead of a
concept.

#### Adversarial checks 1 & 2 (M7's two named class-(d) failure modes) -- both investigated with real evidence

**Check 1 (residual multi-term-list trap) is REAL, and slightly worse than
M7's own proposed two-pass guard anticipated.** `חוק הגנת הדייר` art.41,
heading `הגדרות`:
```
: לענין פרק זה -
: (1) חדרי כניסה ששטחם פחות משמונה מטרים מרובעים... אינה בכלל "חדר";
: (2) חדר ששטחו אינו פחות מששה ואינו יותר משמונה מטרים מרובעים... הוא "חצי חדר".
```
Two genuine, distinct terms (`חדר`/`חצי חדר`) defined via a numbered list
with **quote-LAST grammar** (the quote closes the sentence, not opens it)
and **no preceding quoted anchor entry at all** -- the preamble line itself
(`לענין פרק זה -`) carries no quote either. M7's proposed fix ("fold an
all-unquoted numbered run into the single PRECEDING quoted-term entry")
has nothing to fold into here. HELD (class d is not this sprint's to
implement), but this is the concrete corpus evidence M7 asked QA to find
if the failure mode is real -- it is, feeding back per M7's own
instruction rather than opening a new escalation.

**Check 2 (citation-only/incorporation-by-reference sections) resolves
safely today.** Found 4 real definitions-heading sections whose body
contains NO quote character at all, e.g. `חוק מפעלי ים המלח (ריבית על
מניות)` art.1: `בחוק זה תהיה משמעותו של כל מונח כמשמעותו בפקודת מס הכנסה
(להלן - הפקודה).` -- `extract_definitions_from_section` correctly yields
`[]`, not a fabricated definition. Side note, not a new escalation: the
`(להלן - הפקודה)` ad-hoc marker embedded in this body IS a genuine,
capturable ad-hoc definition by grammar, but sits inside a
definitions-heading section, so it hits the SAME already-escalated E6/item-
11 blocker (ad-hoc markers inside a definitions-section body are never
scanned) -- one more real instance of a known gap, not a new one.

#### Adversarial check 4 (IL/US leakage) -- PASS, extended beyond the manager's original spot check

`registry.scope_trigger_rules_for("IL")` = **8**. Checked SIX US codes
(not just `US-CA`): `US-CA`/`US-NY`/`US-TX`/`US-FED`/`US-DC`/`US-PR`, each
= **1** (core's baseline proof rule only, module
`us_scope_trigger_proof`). Every one of the 8 IL rules' `extract`
functions resolves to an `il_*` module. Zero leakage across every code
checked.

#### What I tried that found nothing (evidence, not just a clean bill)

- Full-corpus false-positive hunt on the LIVE `il_adhoc_scope_triggers`
  rule (3,605 real candidates) for verb-shaped matches
  (`יהיה|יחול|רואים|כאילו|לרבות ` etc.) -- zero found (only the 3
  citation-shaped ones above, a different signature).
- 25-sample (seed 42) of unrecognized `::-`-preamble tails -- zero
  verb-shaped or clearly-wrong matches; every one was a genuine additional
  definitional preamble.
- Hunted specifically for a literal "ראו הגדרות בחוק ..." citation-only
  clause (the manager's own example phrasing) -- zero files contain that
  exact phrase anywhere in the corpus; the real-world shape turned out to
  be free-form incorporation-by-reference prose instead (Check 2 above),
  which I found and verified by a broader no-quote-in-body scan.
- IL/US rule leakage -- none, across six US codes (not just one).

### Escalations (P-R2 -- reporting, not deciding)

1. **I4 FAIL, absolute-zero-miss bar.** Miss Group A (8 new/unimplemented
   trigger phrase families, ~2,862 occurrences / ~1,300+ files aggregate)
   and Miss Group B (the `::-`-nested-list shape wired for 1 of >=11
   trigger phrasings, 2,288 uncaptured occurrences) are both confirmed
   real and live-verified. Both use the SAME already-proven
   `ScopeTriggerRule` mechanism (no new architecture/wiring gap, unlike
   E6/E7/item-5/item-6) -- Group A is additional sibling quote-first rules;
   Group B is generalizing item 9's own preamble detector to loop over the
   known trigger set (or become trigger-word-agnostic) instead of
   hardcoding `בפרט זה`. Recommending a Phase-C item, not deciding scope
   myself.
2. **P-R2, small but real conflict.** 3/3,605 (0.08%) of the widened
   ad-hoc rule's own live captures are citation-shorthand labels (`סעיף
   N`/`תקנה N`), not genuine terms. Suggest excluding candidates matching
   `^(סעיף|תקנה)\s+\d` from `il_adhoc_scope_triggers.py`; reporting per
   policy rather than choosing between zero-miss and zero-false-positive
   myself.
3. Feeding back real corpus evidence for M7's named residual class-(d)
   risk (real, worse than anticipated -- no anchor entry, quote-last
   grammar) per M7's own binding instruction. Not a new escalation.
4. I1's contract-recorded article count (127,903) is stale post-rebase;
   confirmed current figure is 128,234 (+331, exactly matching P-E3's
   corrected bare-`@` count). Documentation fix, not a gate failure.

### Suite numbers recap (all reproduced by me)

Backend: `4 failed, 715 passed, 18 warnings in ~14s`. Frontend: `165
passed (165)`, `25 passed (25)` files. `tsc --noEmit`: clean.
`contract_lint.sh 2026-08-04-defs-il`: `PASS 400`. `git diff --name-status
origin/main...HEAD -- backend/tests`: all `A`. I1 independent re-run:
`6133/6133 files, 0 failed, 128234 articles`.

### Gate verdicts

**I1: PASS** (with a stale-number documentation finding, not a gate
failure). **I2: not re-litigated this cycle** (Phase-B implementation
status unchanged; the 8 shipped rules pass their own RED-turned-GREEN
tests, confirmed by the I5 suite run above). **I3: PASS**, both directions
attacked on two independent real corpus laws. **I4: FAIL** -- confirmed,
live-verified misses (Groups A and B) and one confirmed false-positive
class, all with real corpus examples above; this is the director's
absolute zero-miss bar, so this fails the gate as specified. **I5: PASS**,
fully reproduced.

qa_cycles: 1.

---

## 2026-08-04 — Manager verdict on QA cycle 1: ACCEPTED, sprint goes qa-fail

### QA's boundaries, verified mechanically by me

`git diff --name-status 39c3b7a..05f42e7` → exactly two files, both docs.
`git diff --name-only 39c3b7a..05f42e7 -- backend/app` → **empty**. QA
touched zero implementation. Role boundary respected. Suite unchanged by its
commit (`4 failed, 715 passed`), contract lint still `PASS 400`.

### I verified QA's headline misses MYSELF — all confirmed

Through the real chain (`normalize_for_parsing` → `strip_wikilinks` →
`HebrewProfile.extract_local_scope_definitions`), my own probe:

```
yod   לענין זה  : 1 candidates -> [(('ביטוח מועדף',), 'local')]
tzere לעניין זה : 0 candidates -> []
בתקנה זו       : 0 candidates -> []
בסעיף קטן זה   : 0 candidates -> []
::- list shape : 0 candidates -> []
```

**The `לעניין זה` finding is the one that stings.** It is not an exotic
convention — it is the *tzere* spelling of a trigger the baseline has
supported in its *yod* spelling since before this sprint. 1,702 occurrences
across 714 files, silently dropped, and nobody on this panel — Planner,
Developer, or me — caught it, because every one of us checked coverage using
the spelling the code already had. That is the P-R7 trap in its purest form,
and only a trigger-INDEPENDENT denominator could have surfaced it. QA's
methodology is vindicated.

### Classification of the confirmed misses (per program instruction)

**(1) BUILDABLE NOW — live `ScopeTriggerRule` kind, ordinary articles.**
Group A single-line families, ordinary-article occurrences only:
`לעניין זה` 1,563 · `בתקנה זו` 427 · `בסעיף קטן זה` 313 · `לעניין/לענין
תקנה זו` 104 · `בתקנת משנה זו` 83 · `לעניין/לענין פסקה זו` 121 ·
`בפסקת משנה זו` 59 · `תקנת משנה זו` 42 = **2,712 occurrences**.
Group B `::-`-nested-list shape, ordinary articles = **2,147 occurrences**
(item 9 already proves this shape is reachable via `ScopeTriggerRule`, so
the mechanism exists; it is wired for exactly one trigger word today).
Plus the 3 confirmed false positives (citation-shaped `סעיף N`, 0.08% of
3,605 candidates) — a tightening of the live ad-hoc rule.
**Total buildable now: ~4,859 occurrences.**

**(2) BLOCKED-ON-CORE-DISPATCH.** Group A in-הגדרות 150 · Group B
in-הגדרות 153 · existing held items 5 and 11 (class (d), 592 files).
Same E6 root cause: `EntrySplitterRule`/`TermClauseRule` have no production
consumer, so a definitions-heading body is unreachable by any rule module.

**(3) NEW CONVENTION CLASSES — for the program manager under D-Q1.**
`בתקנה זו` / `בתקנת משנה זו` / `לעניין תקנה זו` (~656 occurrences) are
**regulation-level** scope — a structural axis this program has not modelled
at all (the corpus is laws AND regulations; `תקנה` is a regulation's
article-equivalent). `בסעיף קטן זה` / `בפסקת משנה זו` (~372) are
subsection/sub-paragraph, which the seam's `UnitPath` does model.

### M12 — sprint status and the RED-provenance gate

**Status → `qa-fail`, `qa_cycles: 1`** (safety valve is 5; we are at 1).
I4 FAILS on the director's absolute zero-miss bar and I am not softening
that: ~4,859 buildable-now occurrences are confirmed missed.

**RED-provenance gate: QA committed NO test files, so no bounced item has a
committed RED test yet.** Per the program's rule, a Developer may NOT be
respawned on these findings until each bounced item has a committed RED test
reproducing the miss (or an explicit impossibility line). Role separation
holds: **the Planner authors those tests, not QA and not me.** Next cycle is
therefore Planner → Developer → QA cycle 2, and I am NOT dispatching a
Developer before the REDs exist.

### Corrections QA made to MY records

- I1's article count `127,903` is **stale** → correct is **128,234**. My
  original run predated the rebase onto core's merged bare-`@` fix; the
  delta is **+331, exactly P-E3's bare-`@` figure**. Independent
  confirmation that core's reachability fix is live. Gate verdict unchanged
  (6,133/6,133, 0 failures, both runs); the number is corrected here.
- Wall time/memory differ by machine (48.5s / 87.7 MiB on QA's scratch DB vs
  my 37.4s / 76.3 MiB) — same order, not a finding.

---

## 2026-08-04 — D-Q1 regulation-scope verification (program-manager-conditioned) + full go on the fix cycle

### The evidence test the program manager set — **CONDITION MET**

"IF regulation documents' תקנה units parse as Article rows today, THEN
`בתקנה זו` = LOCAL scope." I ran the real `sections.parse_articles` over
three real regulation instruments from the read-only corpus:

```
תקנות אגרות בריאות.wiki               -> 65 articles   (art.'1' heading='אגרות')       בתקנה זו present: True
תקנות אגרות חקלאיות (הצמדה למדד).wiki -> 60 articles   (art.'1' heading='הצמדה למדד')  בתקנה זו present: True
תקנות אוויר נקי (אגרות).wiki          ->  8 articles   (art.'1' heading='הגדרה')       בתקנה זו present: True
```

**תקנה units DO parse as `Article` rows.** So, per the ruling and without a
director cycle:
- `בתקנה זו` / `לעניין תקנה זו` (~531 occ) → **`scope="local"`**, enforceable
  by existing machinery. Ship as ordinary trigger rules NOW.
- `בתקנת משנה זו` / `תקנת משנה זו` / `בפסקת משנה זו` / `בסעיף קטן זה`
  (~497 occ) → **subsection-level**, which `UnitPath` already models. Ship
  NOW.
- **No subset is held for modelling.** The D-Q1 escalation is CLOSED by
  evidence.

Incidental observation (not acted on, not a gate): `תקנות אגרות חקלאיות`
parses TWO articles numbered `'1'` — a duplicate article number within one
document, probably a תוספת/schedule restarting numbering. Flagged for a
future panel; it does not affect this sprint's classes.

### M13 — the fix cycle, dispatched

Program manager gave **full go**. Per the RED-provenance gate I held, the
Planner authors the complete RED set FIRST; no Developer runs before those
REDs are committed and proven red. Scope:
1. The 8 single-line trigger families incl. **both spellings** (tzere AND
   yod) everywhere — the canonical P-R7 lesson of this program.
2. The `::-` nested-list generalization. **Program efficiency directive,
   binding: ONE mechanism item serving ~2,288 occurrences, NOT per-trigger
   items.** The shape is already proven reachable by item 9's rule; what is
   wrong is that it is wired to a single hardcoded trigger word.
3. The 3 citation-shaped false positives as **precision REDs** (a test that
   fails while `סעיף 149א` is captured as a term).
4. Regulation + subsection families per the verification above.
The E6-blocked subset (~303 occ + items 5/11) stays parked on core's
dispatch merge, now at final-items stage.


---

## 2026-08-04 — Planner: QA cycle 1 RED-provenance set (12 tests, program-directed fix cycle)

Resumed at `8118ef6` (already in sync with `origin/claude/defs-il`, no pull
needed). Read the contract in full (items 1-11) and the WHOLE log per the
manager's instruction, especially `## QA cycle 1` and the two manager
entries following it (ACCEPTED verdict + D-Q1 regulation-scope closure) --
did not re-derive QA's sweep; built every RED test from QA's own findings,
independently re-verified live (never trusted blind, per M4/M10).

### Yod/tzere audit of the six shipped IL rule modules (manager-requested)

Read all six shipped rule files (`il_chapter_scope_triggers.py`,
`il_siman_chelek_scope_triggers.py`, `il_seif_zeh_three_word_scope_
triggers.py`, `il_adhoc_scope_triggers.py`, `il_paragraph_scope_
triggers.py`, `il_prat_zeh_item_scope_triggers.py`) plus the original
`il_scope_triggers.py`. **Finding: the yod/tzere hole exists in exactly
ONE place** -- `extract._LOCAL_TRIGGER_RE` (frozen, wrapped unchanged by
`il_scope_triggers.py`), which matches only `לענין זה` (yod), never
`לעניין זה` (tzere). Every other shipped rule's trigger words (`בפרק`/
`בסימן`/`בחלק`/`בפסקה`/`בפרט`/`בסעיף`) do not use the `לענין`/`לעניין`
word at all, so the spelling-pair ambiguity does not apply to them --
confirmed by direct source read of each file's own `_TRIGGER_RE`, not
assumed. **Reassuring finding, worth stating plainly: item 3's
`il_seif_zeh_three_word_scope_triggers.py` ALREADY covers both spellings
correctly** (`(?:לענין|לעניין) סעיף זה`) -- the ONE prior rule this Planner
personally authored that had the opportunity to make this exact mistake,
didn't. The bug is real but contained to the one place QA found it.

### Live re-confirmation of every Group A/B/precision-RED fixture

Built 12 real, verbatim fixtures (11 new + reused none from before) into
`backend/tests/fixtures/wiki_laws/`. Every single one independently
re-confirmed by THIS Planner through the real chain
(`profile.normalize_for_parsing` -> `strip_wikilinks` -> `sections.
parse_articles` -> `profile.extract_local_scope_definitions`) before
writing the matching test -- not copied blind from QA's log:

- `לעניין זה` (tzere): QA's own cited fixture, `הוראות הפיקוח על שירותים
  פיננסיים (ביטוח) (ביטוח אובדן כושר עבודה קבוצתי)` art.3, term "ביטוח
  מועדף" -- confirmed `[]`.
- `בתקנה זו`: `צו הבטיחות בעבודה (אגרות בדיקה)` art.6, term "מדד" --
  confirmed `[]`.
- `בסעיף קטן זה`: `החלטת הרשויות המקומיות (גמלאות לראש רשות וסגניו)`
  art.29ב, term "המדד" -- confirmed `[]` (this SAME article already
  captures a DIFFERENT term, "יום העדכון", via the already-shipped item
  10 `בפסקה זו` ad-hoc rule -- verified the two do not collide).
- `לעניין תקנה זו` (tzere, 3-word): `תקנות בריאות העם (דיגום וביצוע בדיקות
  קורונה)` art.14, term "ציוד רפואי" -- confirmed `[]`. (Also live-checked
  the yod spelling, `לענין תקנה זו`, on a separate real file -- `תקנות
  ביטוח בריאות ממלכתי`, art.4, term "חציון" -- to confirm the family
  reproduces under BOTH spellings; used only the tzere fixture for the
  committed test, matching QA's own combined-count convention for this
  family.)
- `בתקנת משנה זו`: `תקנות שירות הביטחון הכללי (סייגים בקרבת משפחה)` art.4,
  term "קרוב משפחה" -- confirmed `[]`.
- `תקנת משנה זו` (bare): `תקנות צער בעלי חיים...` art.26, term "משקל
  כולל" -- confirmed `[]`.
- `לעניין פסקה זו`: `הוראות הבחירות לכנסת (סדרי הצבעה...)` art.5, term
  "מזוודת החומר הרגיש" -- confirmed `[]`. **Scope-kind inference, flagged
  explicitly (D-Q1 did not name this family):** mapped to
  `scope="paragraph"`, the same kind item 7's `בפסקה זו` already
  registers, since this is plainly an alternate phrasing of the same
  concept ("regarding this paragraph" vs "in this paragraph"). If the
  manager disagrees with this inference, it is cheap to correct before
  implementation -- flagging rather than silently deciding is the point.
- `בפסקת משנה זו`: `פקודת מס הכנסה` art.87ה, term "קרוב" -- confirmed `[]`.
- Group B mechanism: `החלטת מימון מפלגות (יחידות מימון ומועדי תשלום)`
  art.2 -- QA's own exact cited law/article, verbatim. Confirmed
  `profile.extract_local_scope_definitions` -> `[]` for BOTH `"מדד"` and
  `"מדד יסודי"`, despite `בסעיף זה` being a trigger this sprint ALREADY
  implements for two other grammars.
- 3 precision REDs: confirmed via the LIVE registered `il_adhoc_scope_
  triggers` rule (not a re-implementation) that `סעיף 9`/`סעיף 149א`/
  `סעיף 51טו` are each captured as `terms=("סעיף N",)` today, exactly as
  QA reported -- `חוק התוכנית הכלכלית...` art.33, `חוק ההתייעלות
  הכלכלית...` art.34, `חוק המדיניות הכלכלית לשנים 2011 ו-2012...` art.39.

**Verbatim-fixture discipline note (self-correction, caught before
committing):** my first draft of several fixtures (the three precision-RED
laws + the `לעניין פסקה זו` fixture) stripped the source `[[...]]`
wikilink markup by hand instead of copying it verbatim -- functionally
harmless (`strip_wikilinks` removes it before extraction either way, so no
test behavior changed) but a real deviation from this sprint's own
"REAL, verbatim excerpts" discipline. Caught and rewritten to match the
exact raw corpus text (including the more unusual `[[+|...]]`/`[[-|...]]`
link-annotation forms in the two longer economic-policy-law fixtures)
before running any test. Recorded here rather than silently fixed, per
the standing instruction to report process deviations, not just outcomes.

### New test file (additive only -- no existing test touched)

`backend/tests/integration/test_definition_links_il_qa_cycle1_fixups_
live.py` -- 12 NEW tests (8 Group A + 1 Group B + 3 precision), all RED
today for behavioral reasons (real `AssertionError`s with actual
`created_definitions`/captured-term contents shown, never an import or
collection error). All go through the full live pipeline
(`ingest_wiki_law` + `run_definition_linking`), consistent with every
prior test in this sprint (the manager's message offered the lighter
`profile` seam as an alternative given the volume; kept the heavier,
established DB-backed path for consistency and because it is what the
sprint's own gates actually measure).

### Suite proof (my own run, worktree venv)

```
backend/.venv/bin/pytest backend/tests/integration/test_definition_links_il_qa_cycle1_fixups_live.py -v
-> 12 failed (all AssertionError, real captured-term output shown, e.g.
   "got {'id': ..., 'terms': ['סעיף 51טו'], 'scope': 'local'}" for the
   precision REDs, "got []"/partial-term-set for the capture REDs)

backend/.venv/bin/pytest backend/tests -q
-> 16 failed, 715 passed, 18 warnings in ~14s
```
715 = the exact QA cycle 1 baseline, unchanged (zero regressions). 16 =
4 pre-existing (item 11's E6-blocked test + items 5's 3 class-(d) tests,
all unchanged) + 12 new REDs from this round.

### Contract updated

Added item 12 (READY, `ScopeTriggerRule` -- LIVE per M11/P-R8 -- covering
all 12 new tests) to `## Next Steps`. To stay under the 400-line
`contract_lint.sh` budget, compressed item 5's prose (removed restated
detail already recorded in the log/ruling M7, kept the load-bearing facts:
BLOCKED, the exact grep evidence, the exact fix location, gate/test
references) -- no substantive claim was cut, only redundant phrasing.
Final: **399/400 lines, `contract_lint.sh` PASS on all 7 checks**
(including timestamps and status/total_items -- both already corrected by
the manager's own prior edit, not touched by this Planner).

### Nothing else to escalate this round

The scope-kind inference for `לעניין פסקה זו` (above) is flagged, not an
escalation requiring a stop -- it is cheap to correct if wrong, and
capture (this cycle's actual deliverable) does not depend on it being
right. No new architecture gap found beyond what QA already surfaced;
every family in this round used the SAME already-live `ScopeTriggerRule`
mechanism (no new E6/E7-shaped surprise).

---

## 2026-08-04 — Manager verification of the Planner's RED-provenance set (91c70de)

### Boundaries (mechanical)

`git diff --name-only 8118ef6..91c70de -- backend/app` → **empty**; zero
production files. `git diff --name-status ... -- backend/tests` → all `A`.
Suite by my own run: **16 failed, 715 passed** — the 715 baseline is
untouched and all 12 new tests are behaviorally RED. `contract_lint` →
**PASS 399**.

### The three flags the program manager asked me to close

**1. Fixture fidelity after the Planner's self-caught deviation — CONFIRMED.**
It reported hand-stripping wikilinks, then rewriting to verbatim. I
byte-checked one regulation fixture against the read-only source:
```
fixture bytes:                                    1022
verbatim substring of the corpus source:          True
byte-identical to source segment (offset 3943):   True
fixture contains raw [[wikilinks]]:               False
corpus source contains [[wikilinks]] anywhere:    True
```
The last two lines together matter: the fixture has no wikilinks because
that article genuinely has none, NOT because they were stripped — the source
file does contain them elsewhere. **The rewrite took.** Self-caught and
self-corrected before commit is exactly the behavior I want recorded.

**2. `לעניין פסקה זו` → `scope="paragraph"` — CONFIRMED CORRECT, recorded.**
Checked the test's own reasoning against the shipped rules: it is an
alternate PHRASING of `בפסקה זו`, which item 7 already registers at
`scope="paragraph"`. Same structural granularity, same kind, and paragraph
is a `UnitPath`-modeled level. The Planner's independent judgment agrees
with the program manager's read and with the shipped code. **Ratified.**

**3. The takana evidence-check — LANDED, and run by ME, not the Planner.**
This was the program manager's flagged gap. Answer: the check exists at this
log's "D-Q1 regulation-scope verification" entry (committed `8118ef6`),
executed by me as manager BEFORE the Planner authored any regulation-family
RED: `sections.parse_articles` over three real regulation instruments →
**65 / 60 / 8 Article rows**, all containing `בתקנה זו`. So the
regulation-family REDs rest on verified evidence, not assumption. **Gap
closed.**

**Handoff ACCEPTED.** RED-provenance gate satisfied; Developer dispatched on
the 12 with an explicit instruction NOT to touch the frozen
`extract._LOCAL_TRIGGER_RE` — the tzere fix ships as an additive rule module,
since the seam guarantees rule candidates are UNIONed and never suppress each
other.

---

## 2026-08-04 — **PROCESS INCIDENT (manager-caused): authorship contamination in commit `806c86a`**

### What happened

I ran `git add -A && git commit` in `/Users/nerya/LexGraph-wt/defs-il` to
record my verification of the Planner's RED set. **The Developer was working
in that SAME worktree at that moment.** My `-A` swept its six uncommitted
production files into MY commit, under MY authorship, with a commit message
that describes only my doc work and does not mention the code at all. The
Developer then found its work already committed before it could commit.

`git show --stat 806c86a` — the truthful contents:
```
 rules/il_adhoc_scope_triggers.py                 |  24 ++
 rules/il_colon_dash_nested_list_scope_triggers.py| 149 +++
 rules/il_lenyan_zeh_tzere_scope_triggers.py      |  57 ++
 rules/il_paragraph_scope_triggers.py             |  11 +-
 rules/il_subsection_scope_triggers.py            |  64 ++
 rules/il_takana_scope_triggers.py                |  57 ++
 docs/sprint/sprints/2026-08-04-defs-il-log.md    |  51 ++
 7 files changed, 412 insertions(+), 1 deletion(-)
```

### **AUTHORSHIP CORRECTION (the record, since history is not being rewritten)**

**Every one of the six `backend/app/definition_links/rules/*.py` files in
commit `806c86a` is DEVELOPER work, not manager work.** Only the
`...-il-log.md` hunk in that commit is mine. The Developer independently
verified the committed content is byte-identical to what it wrote. No
history rewrite — the commit stands, and this paragraph is the correction.

### Why it matters even though the content is fine

This is the one-writer-per-worktree rule violated in **exactly the shape
that caused the M-R7 evidence-contamination incident in another panel**. The
danger is not corrupted bytes; it is that authorship provenance is the thing
my whole verification method rests on. I verify handoffs by reading the diff
attributable to a role. If a manager commit can silently contain developer
code, then "I verified the Developer's diff" stops being a meaningful
sentence. I had also been telling every agent "your entire change is X" and
then verifying that claim with `git diff --name-status <role-commit>` — a
check this incident would have quietly defeated.

Contributing cause, named plainly: I used `git add -A` instead of explicit
paths, in a directory I did not exclusively own. Both halves were mine.

### **M14 — binding, effective immediately**

1. **Every role agent gets its OWN worktree.** No exceptions, no
   cohabitation, for the remainder of this sprint and any resumption of it.
   Role branches off `claude/defs-il`; I merge their commits in.
2. **I verify via diffs, never via cohabitation.** My own commits use
   EXPLICIT PATHS — `git add <path> ...` — never `git add -A`, never `.`.
3. This entry is the standing warning for whoever resumes this sprint.

### Handoff verification of the Developer's work (done despite the incident)

- Suite, my own run: **`4 failed, 727 passed`** — exactly the target end
  state. All 12 fix-cycle REDs green; the 4 remaining are the 3 held
  class-(d) + 1 E6-blocked item 11.
- Frozen check: no `pipeline.py`/`matcher.py`/`extract.py`/`sections.py`/
  `profiles.py` edit. The tzere fix shipped as an ADDITIVE module
  (`il_lenyan_zeh_tzere_scope_triggers.py`) rather than touching the frozen
  `extract._LOCAL_TRIGGER_RE`, as instructed; double-capture is structurally
  impossible since `לענין` is never a substring of `לעניין`.
- The `::-` generalization is **ONE** mechanism file
  (`il_colon_dash_nested_list_scope_triggers.py`, 149 lines) with a shared
  trigger→scope table — the single-mechanism shape the program directed,
  not eight cloned rules.
- **Citation guard spot-checked live by me** against the 3 confirmed FPs and
  3 genuine multi-word terms:
```
FP סעיף 149א   -> []            GENUINE ועדת הבדיקה -> [('ועדת הבדיקה',)]
FP סעיף 51טו   -> []            GENUINE יום התחילה  -> [('יום התחילה',)]
FP סעיף 9      -> []            GENUINE המועד החוזי -> [('המועד החוזי',)]
```
  `_CITATION_SHAPED_TERM_RE = ^סעיף\s+\d+[א-ת]*$` is fully anchored, so it
  cannot over-reject a multi-word term. Precise, not blunt.

**Developer work ACCEPTED** on content; the authorship defect is mine and is
recorded above rather than hidden.
