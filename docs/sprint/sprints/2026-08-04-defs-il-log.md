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
