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

---

## QA cycle 2 (Sonnet/high, independent)

Own worktree `/Users/nerya/LexGraph-wt/defs-il-qa2`, branch
`claude/defs-il-qa2`, HEAD `8a91a55` (== `origin/claude/defs-il` at
resume, verified clean). Read the contract in full and the WHOLE log,
especially `## QA cycle 1`, the manager's ACCEPTED verdict, D-Q1's
regulation-scope closure, the Planner's RED-provenance set, and the
process-incident entry (M14 -- read as my own standing warning; every
`git add` below uses explicit paths, never `-A`). Zero
`backend/app/**` touched — verified `git status --short` clean at every
checkpoint below; the only artifact used for I3 was a throwaway pytest
file (`zzz_qa_cycle2_probe.py`) written, run, then deleted before this
commit — never pushed.

### Methodology / independence argument (M10, P-R7 — binding, unchanged)

Every measurement below runs through the REAL live chain:
`sections.parse_articles` (raw `.wiki`) → `profile.normalize_for_parsing`
→ `normalize.strip_wikilinks` → `profile.extract_local_scope_definitions`
(ordinary articles) or the live registered `il_adhoc_scope_triggers` rule
(precision re-sample), exactly the order `pipeline.py:187-188` uses.
Denominators are built from GRAMMAR, not our own trigger list: a generic
quote-first `"term" -` scan classified AFTER matching (never used to
build the miss population itself), plus dedicated re-derivations of QA
cycle 1's own two structural denominators. Every finding below is a real,
named corpus file+article, independently re-confirmed by direct function
calls, not assumed from a denominator count alone.

### Gate I5 (regressions) — PASS

- `backend/.venv/bin/pytest backend/tests -q` → **`4 failed, 727 passed,
  18 warnings`**, reproduced twice. The 4 are exactly the 3 held class-(d)
  tests + 1 E6-blocked item-11 test — matches the claimed target state.
- `npm --prefix frontend run test -- --run` → **`165 passed (165)`, `25
  passed (25)` files** (frontend `node_modules` was absent in this fresh
  worktree; ran `npm install` first — dev-dependency install only, no
  source change).
- `npm --prefix frontend run typecheck` → clean.
- `bash scripts/contract_lint.sh 2026-08-04-defs-il` → **PASS 399**.
- `git status --short` clean at every checkpoint; no existing test edited.

### Gate I1 (full corpus loads) — PASS, confirms (does not correct) cycle 1's figure

Independent re-run: own scratch sqlite DB, real
`app.definition_links.ingest_wiki_corpus.run_bulk_ingest` against the
real read-only corpus. Result: **files found 6133, processed 6133, failed
0, total_articles 128234** — exact match to QA cycle 1's corrected
figure. Corpus re-verified untouched after (`ls | wc -l` → 12266).

### Gate I3 (new/changed scope kinds' containment) — PASS, attacked on 3 fresh real corpus laws + static proof

Confirmed BOTH by reading `matcher._in_scope`/`_subsection_contains_offset`
(subsection-scope: `mention_path[0].value` is NEVER `None` when
non-empty per `HebrewProfile.resolve_unit_path`'s own contract, while
`allowed=(None,)` for a `scope_value=None` definition — structurally
inert by construction, not merely untested; paragraph/siman/chelek hit
`_in_scope`'s generic-kind branch, which reads `article.structural_units`
— always `()` on a real `MatcherArticle` — same inertness) AND live, on
laws no fixture/test touches:

- **Subsection (`בסעיף קטן זה`)** — `חוק איסור פרסומת והגבלת השיווק של
  מוצרי טבק ועישון` (full, unedited, 32 articles). Term `"סיגר"` captured
  subsection-scoped at article 9ב. Ground truth (raw substring): the term
  recurs in 9 articles (`1,4א,7,7א,7ג,9,9ב,9ה,11`). Live result: **0
  `USES_DEFINITION` edges anywhere**, including inside article 9ב itself.
  Genuinely inert.
- **Takana/regulation-local (`בתקנה זו`, D-Q1)** — `תקנות בתי המשפט
  (גישור)`. Term `"סכסוך"` captured local-scoped at article 10; raw
  substring recurs in 9 articles. Live result: linked to **exactly
  article 10, nowhere else** — both directions correct, same machinery
  as any other local-scoped definition.
- **Paragraph (`בפסקה זו`/`לענין זה`)** — `תקנות הנכים (כללים לקביעת
  דרגת נכות מיוחדת)`. Two paragraph-scoped definitions captured
  (`פגיעת נפש`, `פגיעת ראש`). Live result: **0 edges**. Inert.

CHECK: throwaway `backend/tests/integration/zzz_qa_cycle2_probe.py`
(3 tests, all green), run then deleted — not committed, per the "no test
downloads/keeps scratch fixtures" discipline; the log entry above is the
durable record.

### Gate I4 (zero-miss sweep) — **FAIL. Real, live-verified misses found — smaller than cycle 1's, but real, plus one significant NEW class.**

#### Part A — re-measuring cycle 1's own miss population against the fixed tree

Re-derived cycle 1's Group A (8 families) and Group B (`::-` shape)
denominators independently and ran them corpus-wide through the real
chain.

**Group A (8 single-line families) — 5,400 ordinary occurrences, 5,340
captured, 60 confirmed still-missed (98.9%).** Two distinct root causes,
both real:

1. **Punctuation-variant gap — 38 confirmed misses across 7 families.**
   Every shipped rule (frozen `_LOCAL_TRIGGER_RE` included) hardcodes a
   LITERAL COMMA between the trigger phrase and the opening quote
   (`TRIGGER,\s*"..."`). The real corpus routinely omits it (bare space,
   occasionally a colon). Confirmed live (`extract_local_scope_
   definitions` → term absent):
   `לעניין זה` tzere 9, `לענין זה` yod 6, `בסעיף זה` 10 (+1 colon-variant:
   `צו בדבר שטחים סגורים (אזור הגדה המערבית)` art.1ג, `"ישראלי"`),
   `בתקנה זו` 6, `בסעיף קטן זה` 1 (`פקודת מס הבולים` art.74, `"ההשכרה"`),
   `בפסקה זו` 2, `לענין סעיף זה` 3. Examples: `חוק ההתייעלות הכלכלית
   (...2017 ו-2018)` art.70 `"... לעניין זה \"מחזור ההתחשבנות\" -
   ..."` (no comma) → `[]`; `תקנות הביטוח הלאומי (קביעת דרגת נכות
   לנפגעי עבודה)` art.22א `"...לעניין זה \"איברים סולידיים\" - ..."` →
   `[]`; `חוק העונשין`-adjacent examples in `בסעיף זה`/`בתקנה זו` families
   (`חוק השיפוט הצבאי` art.415א `"החלטה"`, `תקנות התעבורה` art.287
   `"רכב ציבורי"`, art.377 `"מרכז הגלגל החמישי"`).
2. **Greedy same-line-swallow — 3 confirmed misses, pre-existing in the
   FROZEN `_LOCAL_TRIGGER_RE`.** Root cause isolated with a minimal
   synthetic repro: `_LOCAL_TRIGGER_RE.finditer('foo; לענין זה, "א" -
   defA; לענין זה, "ב" - defB.')` → only `"א"` matches; `(.*)$` is
   greedy/unbounded except by end-of-LINE, so when the identical trigger
   phrase (same regex object — the frozen rule alternates `לענין
   זה|בסעיף זה` in ONE pattern) fires twice on one physical source line,
   the first match's definition-text capture swallows the rest of the
   line, including the second trigger+quote, before `finditer` can reach
   it. Cross-rule pairs (e.g. `בסעיף זה` then the SEPARATE tzere rule's
   `לעניין זה`) are unaffected — each rule scans the untouched body
   independently. Real corpus instances (all yod `לענין זה` twice on one
   line): `היתר לעשיית עסקה בניירות ערך (עובדי הרשות)` art.1 (`"תאגיד
   מפוקח"` captured, `"חברה מוחזקת"` swallowed); `חוק הסדרת מקומות רחצה`
   art.5א (`"מקום מרפא"` captured, `"בית מלון"` swallowed); `חוק מס ערך
   מוסף` art.106ב (`"בעל תפקיד"` captured, `"בעל שליטה"` swallowed).
3. **`בפרט זה` single-line inline form — never implemented, 19/19 missed,
   6 files.** Item 9's rule only ever detects the `::-`-LIST shape for
   this trigger; the plain single-line `בפרט זה, "term" - def.` grammar
   (every OTHER trigger word in this sprint has this form) has no rule at
   all. Confirmed live: `חוק בתי משפט לענינים מינהליים` art.40, `"גוף
   אחר"` → `[]`; also `חוק המידע הפלילי ותקנת השבים`,
   `חוק זכויות נפגעי עבירה`, `תקנות הביטוח הלאומי (...)`,
   `תקנות התכנון והבניה (בקשה להיתר...)` (9 occurrences alone),
   `תקנות שוויון זכויות לאנשים עם מוגבלות (...)`.

(One apparent "bare `תקנת משנה זו`" concern I chased and ruled OUT: QA
cycle 1's "bare" label means "no leading `ב`", i.e. the `לענין/לעניין
תקנת משנה זו` 3-word form, NOT a literally-unprefixed occurrence — the
corpus contains ZERO literally-bare `תקנת משנה זו` quote-first hits
anywhere; the 42-occurrence family is fully captured (31 tzere + 11 yod,
both 100%). Verified by exhaustive corpus scan before reporting, not
assumed — recording the negative result per the brief's "what you tried
that found nothing.")

**Group B (`::-` nested-list shape) — PASS, 100% capture.** Re-derived
denominator (any line ending bare `-`, immediately followed by `::-`
entries): **4,972/4,972 ordinary occurrences captured, 0 missed**
(723 more sit in E6-blocked הגדרות-heading sections, untouched, as
designed). The single-mechanism generalization
(`il_colon_dash_nested_list_scope_triggers.py`) works comprehensively —
this is a clean, resounding fix.

#### Part B — NEW class found by the independent grammar sweep (task 4)

**HEADLINE FINDING: single-`:-`-colon definitions-list entries embedded
under a bare `TRIGGER -`/plain-sentence-ending-`-` preamble, inside
articles NOT dispatched as a definitions section — 800 real terms, 130
files, 199 qualifying articles, 799 confirmed uncaptured today.** This is
the SAME preamble+list grammar Group B's rule already generalizes for
`::-` (double-colon) — but Group B's `_ENTRY_LINE_RE` requires `::-`
specifically; it does not match the SINGLE-colon `:-` marker (the
definitions-SECTION entry marker, `extract._ENTRY_START_RE`), so no rule
reaches these at all. Two sub-shapes, both real, both confirmed live
(`extract_local_scope_definitions` → `[]` for every listed term):

1. **Unrecognized definitions-heading synonym — 116 terms / 23 files.**
   `sections._DEFINITIONS_HEADING_RE` only matches `הגדרות(...)/הגדרת
   מונחים/הגדרה/הגדרות ופירוש`. `פרשנות` ("Interpretation" / "Construction")
   is a standard, real Israeli-legislative synonym for the SAME concept
   and is not in that list — every one of 23 real corpus articles headed
   exactly `פרשנות` (optionally with a `(תיקון: ...)` suffix) whose body
   is a genuine `:-`-marked definitions list is therefore dispatched as
   an ORDINARY article and yields `[]` for ALL its terms, not just some.
   Examples: `תקנות הכשרות המשפטית והאפוטרופסות (סדרי הדין וביצוע)`
   art.1 (11 terms, 0 captured — `"בית המשפט"`, `"הנחיות מקדימות
   לאפוטרופוס"`, `"החוק"`, `"חשבון"`, ...); `חוק רשות השידור` art.1 (14
   terms); `חוק התגמולים לנפגעי פעולות איבה` art.1 (10 terms); `כללי
   אתיקה לדיינים`/`כללי אתיקה לשופטים` art.1 (6/7 terms each). Fixing
   `is_definitions_heading` itself needs a FROZEN-module edit
   (`sections.py`), same family as E6 — **but** unlike class (d), this
   is ALSO reachable without touching any frozen file, via the exact
   precedent Group B already sets this cycle (sub-finding 2, below).
2. **Genuine embedded local/law-wide/chapter/siman/takana-scoped
   definitions lists sitting inside substantive, topically-unrelated
   articles** (heading recognized fine, article legitimately about
   something else) — the remaining ~107 files. These are real,
   deliberate definitions ("for purposes of THIS article/paragraph...")
   the corpus places inline rather than in a dedicated section, using
   preambles that in most cases DO carry a recognizable trigger word
   (`בסימן זה -`, `בסעיף זה -`, `בחלק זה -`, `בתקנה זו -`, `בתקנות אלה
   -`, `לענין הסעיפים X-Y -`) but sometimes none at all (a plain sentence
   ending `-`, e.g. `חוק גיל פרישה` art.13א). 21/21 hand-verified genuine
   across two independent random samples (seed 42 and seed 7) — zero
   false positives found. Examples: `חוק בית העצמאות` art.16 (heading
   `ניגוד עניינים`) defines `"עניין אישי"`/`"קרוב"` via `בסעיף זה -`;
   `חוק הביטוח הלאומי` art.340א (heading `דמי ביטוח לעובד במשק בית`)
   defines `"עובד במשק בית"`/`"שכר"`; `חוק העונשין` art.401 (heading
   `גניבת כלי שיט או כלי טיס`) defines `"כלי שיט"`/`"כלי טיס"` via
   `בסעיף זה -`; `חוק הדיור המוגן` art.55 defines `"בית משותף"`/`"חוק
   המקרקעין"` via `לעניין זה -`.

Because this reuses the SAME dispatch path (`extract_local_scope_
definitions`) Group B already proves reachable, a NEW `ScopeTriggerRule`
generalizing the SAME algorithm to the single-`:-` marker (mirroring
`il_colon_dash_nested_list_scope_triggers.py` almost exactly, swapping
`::-` for `:-`) would reach BOTH sub-shapes above without any frozen-file
edit — recommending this as the next Phase-C item, not deciding scope
myself (P-R2). Not the same category as E6/class(d); flagging the
distinction explicitly so it is not silently merged into "still blocked."

#### Precision re-sample (P-R7) — PASS, no over-rejection found

Ran the LIVE, registered `il_adhoc_scope_triggers` rule over the whole
corpus (not a re-implementation). Raw trigger-regex matches: 3,684;
rejected by the ≤4-token cap: 125; **rejected by the citation guard:
exactly 3** (`סעיף 149א`/`סעיף 51טו`/`סעיף 9`, the SAME three QA cycle 1
found — no more, no less); **live candidate output (ordinary articles):
3,556**. Explicit over-rejection hunt: scanned every raw match whose
captured term starts with the literal word `סעיף` — **zero** survive
that aren't the 3 pure citations, and the guard's anchored regex
(`^סעיף\s+\d+[א-ת]*$`) structurally cannot match a multi-word term
either way. The small gap between this cycle's 3,556 and cycle 1's
reported 3,605 is explained by measurement layer, not regression: my
count deliberately excludes הגדרות-heading articles (the real production
dispatch never invokes this rule there — M10's own binding lesson),
which cycle 1's cruder count did not exclude.

#### What I tried that found nothing

- Full re-hunt for the "bare `תקנת משנה זו`" family QA cycle 1 named —
  confirmed it means the `לענין/לעניין`-prefixed 3-word form, not a
  literal bare occurrence; the corpus has zero literal-bare hits; the
  named family is 100% captured (see above).
- 21-item hand-verification (two independent random samples) of the new
  single-`:-` class — zero false positives; every hit is a genuine
  definitions list.
- Boundary hunt on the citation guard across the whole corpus (3,684 raw
  matches) — zero terms starting with `סעיף` survive besides the 3 known
  citations; zero over-rejection.
- Verb-shaped/citation-shaped false-positive hunt repeated on this
  cycle's fresh `il_adhoc_scope_triggers` output — none beyond the
  already-known 3.
- Checked whether the same-line-swallow bug reaches any of the NEWLY
  shipped rules (takana/subsection/paragraph/tzere) — it does not; each
  new family is its own independent regex object, so only the FROZEN
  `לענין זה|בסעיף זה` alternation (pre-existing, not introduced this
  cycle) is vulnerable. Recorded as a pre-existing-bug finding, not a
  regression from this cycle's fix.

### Gate verdicts

**I1: PASS** (confirms 128,234, no correction needed). **I3: PASS**,
both new/changed kinds attacked live on 3 fresh corpus laws plus static
proof from the containment code itself. **I4: FAIL** — 60 confirmed
residual misses in cycle 1's own 8 families (punctuation-variant gap +
pre-existing same-line-swallow bug + never-implemented `בפרט זה`
single-line form), PLUS a newly-discovered, well-evidenced class (800
terms / 130 files / 799 missed) the independent grammar sweep surfaced
this cycle. Group B (`::-` shape) and the precision guard both PASS
cleanly with zero residual issues found. **I5: PASS**, fully reproduced
(727/4, 165/165, tsc clean, contract lint PASS 399).

### Suite numbers recap (all reproduced by me)

Backend: `4 failed, 727 passed, 18 warnings in ~14-17s`. Frontend: `165
passed (165)`, `25 passed (25)` files (after `npm install` in this fresh
worktree). `tsc --noEmit`: clean. `contract_lint.sh 2026-08-04-defs-il`:
`PASS 399`. I1 independent re-run: `6133/6133 files, 0 failed, 128234
articles`.

### Escalations (P-R2 — reporting, not deciding)

1. **I4 FAIL, absolute zero-miss bar.** 60 residual misses in cycle 1's
   own families (all buildable-now, no new architecture gap — the
   punctuation-variant gap is a one-character regex widening per rule;
   the same-line-swallow bug needs a non-greedy/lookahead-bounded rewrite
   of the shared `.*$` idiom; `בפרט זה` single-line needs one more
   sibling rule) + the new single-`:-` class (800 terms/130 files,
   reachable via one more `ScopeTriggerRule` mirroring Group B's own
   precedent, NOT E6-blocked). Recommending a Phase-C item bundling all
   four, not deciding scope myself.
2. The same-line-swallow bug lives in the FROZEN `extract.
   _LOCAL_TRIGGER_RE` — pre-existing, not introduced by this sprint's
   fix cycle, but only 3 real corpus instances found, all small. Noting
   it is technically a frozen-module defect but achievable as an
   ADDITIVE sibling rule (an extra pass that specifically re-scans each
   already-matched line's own swallowed tail) without editing the frozen
   file itself, same discipline this sprint has used throughout.
3. No genuine zero-miss vs zero-false-positive conflict found this
   cycle — the precision guard is clean (exactly 3 rejected, 0
   over-rejection), so nothing to arbitrate.

qa_cycles: 2.

---

## 2026-08-04 — Manager verdict on QA cycle 2: ACCEPTED; sprint stays qa-fail (cycle 2 of 5)

### Boundaries (mechanical, from its isolated worktree — M14 working as intended)

`git diff --name-only 8a91a55..29e7e42 -- backend/app` → **empty**.
`... -- backend/tests` → **empty** (its throwaway I3 probe was run and
deleted before committing, as reported). Only log + contract. Merged into
`claude/defs-il` via `--no-ff`. Post-merge, my own run: **`4 failed, 727
passed`**, `contract_lint` **PASS 399**. **M14 worked** — this handoff had
zero authorship ambiguity, in direct contrast to the incident above.

### I verified its three headline claims MYSELF

```
--- punctuation variant (comma hardcoded) ---
comma  בתקנה זו,   -> [('מדד',)]        space בתקנה זו -> []      dash בתקנה זו - -> []
--- single-colon list under a bare preamble ---
double ::- (fixed) -> [('מדד',)]        single :-      -> []
--- single-line בפרט זה ---
inline בפרט זה,    -> []
```
All three real. The comma IS hardcoded across the rule family; single-`:-`
is genuinely uncovered while `::-` now works; item 9 built only the
list-shape and never the plain inline form.

### Scoreboard — the fix cycle worked, and the bar moved

| Population | Cycle 1 | Cycle 2 measured | Verdict |
|---|---|---|---|
| Group A (8 families) | 5,400 missed | **5,340 captured (98.9%)**, 60 residual | large win |
| Group B (`::-` shape) | 2,288 missed | **4,972/4,972 (100%)** | **clean fix** |
| 3 citation FPs | present | rejected, **0 over-rejection**, 3,556 live candidates | **fixed** |
| NEW single-`:-` class | not known | **799/800 missed** (130 files) | **new finding** |

**I4 still FAILS**, but for a far smaller and much more precisely
characterized reason than cycle 1 — which is what a working fix cycle looks
like. The residual 60 decompose into three named bugs (38 punctuation
variants, 3 same-line-swallow from a greedy regex in the FROZEN rule, 19
inline `בפרט זה`), not a vague shortfall.

### The new class is NOT E6-blocked — that is the important part

Single-`:-` definitions lists under a bare preamble inside articles whose
heading is not a definitions heading: **800 terms / 130 files**, 21/21
hand-verified genuine across two independent random samples. Includes an
unrecognized heading synonym **`פרשנות`** ("interpretation", 116 terms /
23 files) and genuine embedded definitions inside substantive articles
(e.g. `חוק בית העצמאות` art.16 defining `"עניין אישי"`/`"קרוב"`).
Reachable by one more `ScopeTriggerRule` mirroring Group B's own precedent
— so it is **buildable now**, not parked on core.

### M15 — Phase C scope (for the next cycle), and the frozen-file caveat

Recommended bundle, all additive rule modules: (a) punctuation-variant
widening across the family; (b) an additive fix for the same-line-swallow
bug — **note it lives in the FROZEN `extract` trigger regex, so it must be
worked around additively, never edited**; (c) an inline `בפרט זה` sibling
rule; (d) a `ScopeTriggerRule` generalizing the single-`:-` shape, including
the `פרשנות` heading synonym. Per the RED-provenance gate, the **Planner
authors REDs for all four before any Developer runs.**

Status stays **`qa-fail`, `qa_cycles: 2`** (valve at 5). E6-held subset
(3 class-(d) + 1 item-11 test, ~303 in-הגדרות occurrences) still parked on
core's dispatch sprint.

---

## Phase C — Planner RED set (Sonnet/high, M15 bundle)

Own worktree `/Users/nerya/LexGraph-wt/defs-il-plan3`, branch
`claude/defs-il-plan3`, HEAD at resume `71cbeb4` (== `origin/claude/defs-il`,
verified clean via `git status`/`git log`). `import app` resolves to this
worktree (`backend/.venv/bin/python -c "import app; print(app.__file__)"`
→ `.../defs-il-plan3/backend/app/__init__.py`). Read the program doc, the
full sprint contract, the WHOLE log (QA cycle 1 + 2, the M14 process
incident, M15), and the seam v2.5 doc before touching anything. Read
`extract.py`, every `rules/il_*.py` module, `registry.py`, the relevant
slices of `profiles.py`/`sections.py`/`pipeline.py` directly (worktree is
divergent from `main`, so CodeGraph's index is stale for these files —
used direct `Read` per M1/the program's CodeGraph caveat).

**Methodology (P-R7, binding on every population claim below):** every
denominator is built from GRAMMAR (trigger-word text scans, or — for
C4 — a bare-preamble-line-then-`:-`-entries STRUCTURAL shape scan),
never from our own shipped rule's own regex, then cross-checked against
the LIVE chain `sections.parse_articles` (raw `.wiki`) →
`profile.normalize_for_parsing` → `strip_wikilinks` →
`profile.extract_local_scope_definitions` — the exact order
`pipeline.py:187-236` uses for an ORDINARY (non-הגדרות-heading) article.
Every fixture was extracted PROGRAMMATICALLY, never hand-retyped: a
reusable script (`il_phaseC_plan_fixture_builder.py`, scratchpad) finds
the article's own verbatim `@ N. heading` marker line via regex on the
RAW corpus file, concatenates it with `Article.body` (itself a
`"\n".join(original_lines)` reconstruction — never retyped), and before
writing proves (1) the fixture bytes are a literal substring of the
corpus source file (`fixture_text in raw`, logging the offset), (2)
re-parsing the fixture alone reproduces the identical single `Article`,
and (3) the LIVE captured-terms set is IDENTICAL between the original,
untrimmed corpus article body and the trimmed fixture body (proves
trimming context didn't change behavior). All three checks passed for
every fixture below — full per-fixture transcripts are in this session's
scratchpad scripts (`il_phaseC_plan_c1_*.py`, `il_phaseC_plan_c4_*.py`);
representative output reproduced below.

### C1 — punctuation-variant widening: PLANNED, RED committed

Corpus-wide sweep (`il_phaseC_plan_c1_punct_sweep.py`): for each of the 7
confirmed-miss families, scanned all 6,133 files (post
`normalize_for_parsing`) for `TRIGGER<0-3 chars>"term"`, classified the
punctuation. Real counts (comma vs. everything else):

| family | comma | non-comma (bare-space/colon/dash) |
|---|---|---|
| `לעניין זה` (tzere) | 2010 | 26 |
| `לענין זה` (yod) | 883 | 21 |
| `בסעיף זה` | 1288 | 50 (incl. 4 colon) |
| `בתקנה זו` | 475 | 16 |
| `בסעיף קטן זה` | 370 | 6 |
| `בפסקה זו` | 408 | 10 |
| `לענין/לעניין סעיף זה` | 232+145 | 8+1 |

(Non-comma raw counts here include some junk/duplicate/long-tail matches
the ANCHORED per-owning-article resolution below discards — the
FP-measurement table further down is the trustworthy per-article count.)

Picked the SHORTEST clean, live-reconfirmed, currently-uncaptured real
instance per family (via `il_phaseC_plan_c1_shortest_candidates.py`,
which resolves each hit's owning `Article` and sorts by body length) —
except for `בסעיף קטן זה`, where the shortest candidate (`חוק הגנת
הצרכן` art.22ט, term `"מדד"`) turned out to be a FALSE LEAD: its live
capture set was `{'מדד'}`, not empty — the term is ALREADY captured via
an unrelated definition of the same common term elsewhere in the same
article, which would have made a misleading RED test (green for the
wrong reason once "fixed"). Caught this before writing the test (ruling
M4) and substituted the next-shortest clean candidate. Also rejected
`צו בדבר ההתגוננות האזרחית` (colon variant of the same family) because
its captured term itself contains an embedded gershayim-quote
(`"תקציב הג"א מקומי"`), an unrelated edge case that would confound the
test's own intent.

Live re-confirmation (actual output, this session):
```
תקנות הביטוח הלאומי (קביעת דרגת נכות...)  art22א  לעניין זה "איברים סולידיים"  -> set()
חוק שירות הציבור (הגבלות לאחר פרישה)      art7    לענין זה "חבר הנהלה"        -> set()
חוק השיפוט הצבאי                          art415א בסעיף זה "החלטה"           -> set()
צו בדבר שטחים סגורים (...)                art1ג   בסעיף זה: "ישראלי"         -> set()
תקנות הביטוח הלאומי (ביטוח מפני פגיעה...) art38   בתקנה זו - "רופא מוסמך"     -> set()
צו בדבר העסקת עובדים (...)                art6    בסעיף קטן זה - "שוהה לא חוקי" -> set()
תקנות תכנון משק החלב (...)                art6    בפסקה זו - "מועצה אזורית"   -> set()
צו בדבר שיקים ללא כיסוי (...)             art17   לענין סעיף זה - "בנק הדואר" -> set()
```
Fixtures (8, all byte-verified substring + re-parse + live-equivalence,
per methodology above): `תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי
עבודה)_art22א_excerpt.wiki`, `חוק שירות הציבור (הגבלות לאחר
פרישה)_art7_excerpt.wiki`, `חוק השיפוט הצבאי_art415א_excerpt.wiki`, `צו
בדבר שטחים סגורים (אזור הגדה המערבית)_art1ג_excerpt.wiki`, `תקנות
הביטוח הלאומי (ביטוח מפני פגיעה בעבודה)_art38_excerpt.wiki`, `צו בדבר
העסקת עובדים במקומות מסוימים (יהודה והשומרון)_art6_excerpt.wiki`,
`תקנות תכנון משק החלב (העברת מכסות של יצרנים שיתופיים בענף
הבקר)_art6_excerpt.wiki`, `צו בדבר שיקים ללא כיסוי (יהודה
והשומרון)_art17_excerpt.wiki`.

**FP measurement (P-R2/D-Q1, `il_phaseC_plan_c1_fp_measure.py`).**
Proposed widening (design guidance for the Developer, not implemented by
this Planner): replace the hardcoded `,\s*"` with
`(?:[,:\-]\s*|\s+)"` — comma/colon/dash (each with optional surrounding
whitespace) OR one-or-more bare whitespace, but NEVER a zero-length gap
(this excludes the one pathological "immediate adjacency" hazard found
during recon: a trigger phrase sitting immediately before an unrelated
quote character elsewhere, e.g. a gershayim-marked year abbreviation
like `תשע"א` — both branches require ≥1 separator character, so a
zero-gap coincidence can never match). Measured on the FULL corpus,
ordinary (non-הגדרות-heading) articles only, using the EXACT downstream
grammar (`"term" - definition-to-EOL`), not just trigger+quote adjacency:

| family | current (comma) | widened | NEW |
|---|---|---|---|
| tzere 2-word | 1563 | 1573 | 10 |
| yod 2-word | 731 | 738 | 7 |
| בסעיף זה | 1106 | 1117 | 11 |
| בתקנה זו | 427 | 433 | 6 |
| בסעיף קטן זה | 313 | 314 | 1 |
| בפסקה זו | 353 | 355 | 2 |
| לענין/לעניין סעיף זה | 204 | 207 | 3 |
| **TOTAL new** | | | **40** |

40 new corpus-wide matches (in the same ballpark as QA cycle 2's own "38
confirmed misses" estimate — the small gap is expected: QA's number was
a hand count of confirmed leads, this is an exhaustive regex sweep).
Hand-verified EVERY family's full "new" sample (42 rows dumped, not just
a subset): 100% genuine real definitions — real trigger, real quoted
term, real definition clause. Two borderline cases specifically chased
down: (1) `נוהל לתמיכות מתקציב המדינה` term `"להעביר"` ("to transfer") —
a VERB being defined looked suspicious, but the raw text confirms a
genuine inclusive definition (`לעניין זה, "להעביר" - לרבות למכור,
לשעבד, ...`), a normal Israeli-legislative-drafting pattern for verbs;
(2) `חוק הגבלת הפרסומת...` term `"מערכת הביטחון"` and `צו הפיקוח על
מצרכים...` term `"שאינם ראויים למאכל אדם"` both have a
DEFINITION-TEXT-TRUNCATED-AT-A-COLON artifact (`"... - כל אחד מאלה:"`)
because the real definition continues on subsequent `::`-indented
sub-items the single-line grammar doesn't reach — the TERM capture is
still correct and genuine, this is a pre-existing definition_text-
completeness characteristic already shared by every comma-triggered
instance of this same grammar (not a new defect introduced by the
punctuation widening). **Zero false positives found.**

Tests (NEW, `test_definition_links_il_phase_c_widening_live.py`, all
proven RED — see suite tail below):
`test_c1_tzere_lenyan_zeh_bare_space_variant_is_currently_missed`,
`test_c1_yod_lenyan_zeh_bare_space_variant_is_currently_missed`,
`test_c1_beseif_zeh_bare_space_variant_is_currently_missed`,
`test_c1_beseif_zeh_colon_variant_is_currently_missed`,
`test_c1_betakana_zo_dash_variant_is_currently_missed`,
`test_c1_beseif_katan_zeh_dash_variant_is_currently_missed`,
`test_c1_beparagraph_zo_dash_variant_is_currently_missed`,
`test_c1_lenyan_seif_zeh_dash_variant_is_currently_missed`.

### C2 — same-line-swallow: PLANNED, RED committed

Synthetic repro re-verified (this session, direct call, NOT a pytest
test — the pytest test below is the live-path RED):
```python
>>> _LOCAL_TRIGGER_RE.finditer('foo; לענין זה, "א" - defA; לענין זה, "ב" - defB.')
# 1 match only: group(1)='א', group(2)='defA; לענין זה, "ב" - defB.'
```
matches the log's own citation exactly. All three real corpus instances
QA cycle 2 named were independently re-confirmed live by this Planner:
```
היתר לעשיית עסקה בניירות ערך (עובדי הרשות) art1  -> captured {'החזקה כדין של ניירות ערך','תקנון הבורסה','תאגיד מפוקח'}, "חברה מוחזקת" ABSENT
חוק הסדרת מקומות רחצה                      art5א -> captured {'מקום מרפא'}, "בית מלון" ABSENT
חוק מס ערך מוסף                            art106ב -> captured {'בעל תפקיד'}, "בעל שליטה" ABSENT
```
Vendored only the smallest as the fixture (`חוק הסדרת מקומות
רחצה_art5א_excerpt.wiki`, byte-verified per methodology) — the other two
are recorded here as corroborating live evidence, not built as separate
fixtures (proportionate effort; one clean RED test suffices for
RED-provenance, all three share the identical root cause).

**Design guidance for the Developer (non-overlap / dedup-hazard
reasoning, per the manager's explicit ask):** the fix must be an
ADDITIVE sibling rule (never edit `_LOCAL_TRIGGER_RE`). Whatever shape
that sibling takes, it should stamp `scope="local"` for this trigger
vocabulary — IDENTICAL to what the frozen rule already stamps. This
matters because `pipeline.py`'s dedup key is `(article_id,
sorted(terms))` with first-candidate-wins: if the additive sibling's own
scan also happens to re-capture the FIRST (already-captured) term on a
swallow-affected line, that's a harmless duplicate PROVIDED the two
candidates agree on scope (which they do, by design) — order cannot
silently swap in a wrong scope. Confirmed this reasoning is not merely
asserted: checked that no OTHER newly-shipped rule (takana/subsection/
paragraph/tzere) is vulnerable to the same swallow bug, since each is
its own independent regex object scanning the untouched body
independently — only the FROZEN `לענין זה|בסעיף זה` alternation shares
one capture group across two trigger words, which is the actual root
cause (re-confirms QA cycle 2's own finding, not merely repeated).

Test (NEW): `test_c2_second_same_line_trigger_match_is_currently_swallowed`.

### C3 — inline בפרט זה single-line form: PLANNED, RED committed

Live re-confirmation (this session, the log's own named example):
```
חוק בתי משפט לענינים מינהליים art40, "בפרט זה, \"גוף אחר\" - כהגדרתו..." -> extract_local_scope_definitions == set()
```
Fixture: `חוק בתי משפט לענינים מינהליים_art40_excerpt.wiki` (846 bytes,
byte-verified).

**FP measurement (`il_phaseC_plan_c3_fp_measure.py`).** Proposed rule:
same single-line quote-dash grammar as every other trigger this sprint
ships, punctuation-widened per C1's own finding (`בפרט זה(?:[,:\-]\s*|
\s+)"term"\s*-\s*def`). Measured on the full corpus, ordinary articles
only: **19 occurrences / 6 files** — an EXACT match to QA cycle 2's own
"19/19 missed, 6 files" claim (`חוק בתי משפט לענינים מינהליים` (1),
`חוק המידע הפלילי ותקנת השבים` (1), `חוק זכויות נפגעי עבירה` (1),
`תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה)` (2), `תקנות
התכנון והבניה (בקשה להיתר, תנאיו ואגרות)` (9), `תקנות שוויון זכויות
לאנשים עם מוגבלות (...)` (2)). Hand-verified all 19: every one is a
real trigger + real quoted term + real definition (one has the same
colon-continuation-truncation characteristic noted under C1, term
capture itself still correct). **Overlap check with the already-shipped
`::-` list-shape rule: 0** — structurally disjoint grammars (the list
rule's own matched line ends in a bare `-` with nothing after it; this
shape's matched line has the term+definition on the SAME line as the
trigger) — verified by scanning every line in the corpus for BOTH
regexes matching simultaneously: zero hits. **Zero false positives, zero
double-capture risk.**

Test (NEW): `test_c3_inline_beprat_zeh_single_line_form_is_currently_missed`.

### C4 — single-`:-` list generalization incl. `פרשנות` synonym: PLANNED, RED committed

**Non-overlap static proof (manager-verified fact #1, explicit assertion
per the brief):**
```python
>>> _ENTRY_START_RE.pattern
'^\\s*:-\\s?'
>>> _ENTRY_START_RE.match(':- "term" - definition')      # -> matches
>>> _ENTRY_START_RE.match('::- "term" - definition')     # -> None
>>> _ENTRY_START_RE.match('::-"term" - definition')      # -> None
```
Confirmed structurally: leading `\s*` cannot consume the first `:` of
`::-`, so the pattern always needs the character right after any leading
whitespace to be `:` immediately followed by `-`; a `::-` line's SECOND
character is `:`, not `-`. A new single-`:-` rule anchored the same way
cannot double-fire alongside `il_colon_dash_nested_list_scope_
triggers.py` on the same line — mutually exclusive by construction.
Test (NEW, plain assertion, not live-path — the load-bearing invariant
this whole item depends on): `test_c4_entry_start_re_cannot_match_double_colon_marker`.

**`פרשנות` heading synonym (sub-shape i).** `is_definitions_heading`
confirmed `False` for `"פרשנות"` and `"פרשנות (תיקון: ...)"` this
session. Full corpus enumeration (`il_phaseC_plan_c4_population.py`,
structural denominator: bare `-`-ending preamble line immediately
followed by `:-`-marked `"term" - definition` entries, NOT gated by any
trigger word — signal-agnostic per P-R7): **23 (file, article) pairs, 93
terms**, every heading exactly `פרשנות` optionally with a `(תיקון: ...)`
suffix (full per-file table logged in this session's scratchpad output,
reproduced below):
```
חוק העיטורים במשטרת ישראל ובשירות בתי הסוהר  art1    5 terms
חוק הצהרות מוות                              art1    3 terms
חוק התגמולים לנפגעי פעולות איבה              art1    1 term
חוק מס מקביל                                 art1    7 terms
חוק מס עזבון                                 art13א  4 terms
חוק רשות השידור                              art1    6 terms
חוק תכנית החירום הכלכלית (...)               art26   2 terms
כללי אתיקה לדיינים                           art1    6 terms
כללי אתיקה לשופטים                           art1    7 terms
פקודת המשטרה                                 art49א  2 terms
פקודת מס הכנסה                               art235א 4 terms
צו התגמולים לנפגעי פעולות איבה (...)         art1    2 terms
תקנות הבטיחות במקומות ציבוריים (סדרנים...)   art1    5 terms
תקנות הביטוח הלאומי (ביטוח נכות)(...)        art1    4 terms
תקנות הכשרות המשפטית והאפוטרופסות (...)      art1    11 terms
תקנות המשקלות והמידות                        art44   3 terms
תקנות העיצובים (יישום הסכם האג)              art1    5 terms
תקנות התגמולים לנפגעי פעולות איבה (...)      art1    1 term
תקנות מוסדות חינוך תרבותיים ייחודיים (...)   art1    4 terms
תקנות מס הכנסה (קביעת שיעור ריבית...)        art1    3 terms
תקנות סדרי הדין בעניני בוררות                art1    2 terms
תקנות סימני מסחר (יישום פרוטוקול מדריד)      art1    4 terms
תקנות שירות עבודה בשעת-חירום (מתנדבים)       art1    2 terms
```
**Honest reconciliation note:** this Planner's own count (93/23) differs
from QA cycle 2's cited "116 terms/23 files" for the SAME sub-case. Same
23 files/articles in both — the file/article population agrees exactly.
The term-count gap is explained, not hand-waved: this Planner's
structural scanner (deliberately modeled AFTER the exact algorithm the
real fix will use, mirroring `il_colon_dash_nested_list_scope_
triggers.py::_extract`'s own single-pass "consume `:-` lines until a
non-matching line, then STOP" loop) stops collecting entries at the
first `::`-indented CONTINUATION line inside a multi-line entry (e.g.
`חוק התגמולים לנפגעי פעולות איבה` art.1's `"פגיעת איבה"` entry
continues via three `:: (1)/(2)/(3)` sub-items) — any FURTHER `:-`
entries appearing after such a continuation break in the SAME list are
therefore undercounted by this Planner's (and, predictably, the real
rule's) simple algorithm, exactly the SAME known limitation the
already-shipped `::-` rule has for its own captures (not a new defect).
QA cycle 2's "116" was very likely counted with a more lenient
whole-body `"term" -` scan (their own methodology note: "a generic
quote-first scan classified AFTER matching"), which does not stop at
continuation breaks. **Net: the real fix will capture at least 93/93
terms across these 23 files with certainty (this Planner's own
conservative, algorithm-faithful count); the residual ~23-term gap
implied by QA's broader count is a genuine, separate completeness nuance
(multi-line entries after a continuation break) shared with the ALREADY
-shipped `::-` rule — flagging for QA cycle 3 to re-measure once the
Developer's actual implementation lands, not deciding it myself.**

Live re-confirmation of the fixture example:
```
כללי אתיקה לדיינים art1 (heading='פרשנות'): is_definitions_heading -> False
extract_local_scope_definitions -> set()  (all 6 terms: בן משפחה, דיין,
דיין בדימוס, נושא משרה, נשיא בית הדין הרבני הגדול, עד מרכזי)
```
Fixture: `כללי אתיקה לדיינים_art1_excerpt.wiki` (byte-verified).

**Genuine embedded lists (sub-shape ii).** Same structural denominator,
EXCLUDING `פרשנות`/standard-heading articles: **1,014 terms / 170
files** (superset of QA's "~107 files" estimate for the same sub-case —
this Planner's sweep additionally catches several near-miss headings QA
did not separately break out, e.g. numbered-prefixed `"N. הגדרות"`
headings recurring throughout `קובץ החלטות מועצת מקרקעי ישראל`, which
fall through `is_definitions_heading` for the identical "not exactly at
the START of the heading text" reason `פרשנות` does, and are reached by
the SAME fix for free — a bonus recall win, not a methodology error;
flagged here rather than silently folded in). Trigger-word breakdown of
the combined (i)+(ii) population (1,107 terms total): `(none)` 405,
`בסימן זה` 141, `בחלק זה` 134, `בפרק זה` 95, `בתקנות אלה` 104, `בסעיף
זה` 109, `לעניין זה` 42, `לענין זה` 24, `בתקנה זו` 25, `בפרט זה` 9,
`בסעיף קטן זה` 3, `לענין/לעניין תקנה זו` 12, `לענין הסעיפים` 4 — the
"trigger-less" 405 bucket is dominated by very common generic preambles
(`בחוק זה -`, `בתקנות אלה -`, `בהסכם זה -`, `[[בפרק זה]] -` via
wikilink) not in the sprint's existing trigger-word table at all;
`_infer_scope`'s existing default-to-`"local"` fallback (same as the
`::-` rule) handles these safely without overclaiming a wider scope.

Two fixtures vendored for sub-shape (ii), both live-reconfirmed:
```
חוק העונשין art401 (heading='גניבת כלי שיט...'): preamble 'בסעיף זה -' -> set()  ("כלי שיט"/"כלי טיס")
חוק הדיור המוגן art55 (heading='תחולה על בתים משותפים'): preamble 'לעניין זה -' -> set()  ("בית משותף"/"חוק המקרקעין")
```
(`חוק גיל פרישה` art.13א, the log's OWN cited "no trigger at all"
example, was independently re-checked and found to actually contain the
recognized phrase `לעניין זה -` directly before the dash — a correction
to the prior framing, recorded per this file's append-only convention,
not silently substituted. A genuinely trigger-less real instance DOES
exist in the corpus — e.g. `פקודת האגודות השיתופיות` art.2's `"...
הפירושים דלקמן, מלבד אם ענין הכתוב יחייב פירוש אחר -"` — but this
Planner did not build a dedicated fixture/test for the trigger-less
default-to-`"local"` fallback specifically; the two vendored fixtures
above already prove sub-shape (ii) is reachable, and `_infer_scope`'s
default behavior is unit-testable by the Developer/QA without a new
corpus fixture if desired.)

**Adversarial FP hunt (P-R2/D-Q1).** Automated proxy scan across all
1,107 candidates for `len(term) <= 1` or empty `definition_text`: 13
flagged. Hand-checked every one: ALL are genuine terms whose definition
content is a MULTI-LINE `::`-continuation (same completeness nuance
noted above, term identity still correct — e.g. `חוק התגמולים לנפגעי
פעולות איבה` art.1's `"פגיעת איבה"`, definition continues via `:: (1)/
(2)/(3)` sub-items) — zero of the 13 are a spuriously-captured non-term.
No candidate anywhere violates the strict `"term" - definition`
entry-line grammar (the SAME precision guard the shipped `::-` rule
already relies on: a preamble ending in `-` for an unrelated reason,
e.g. a table row, can never fabricate a candidate — it can only
"activate" entries that already look exactly like a definition).
**Zero structural false positives found across the full corpus.**

Tests (NEW):
`test_c4_entry_start_re_cannot_match_double_colon_marker` (static proof,
passes today, correctly — not a RED),
`test_c4_parshanut_heading_synonym_single_colon_list_is_currently_missed`,
`test_c4_embedded_single_colon_list_with_trigger_is_currently_missed`,
`test_c4_embedded_single_colon_list_second_trigger_word_is_currently_missed`.

### Fixture byte-verification (all 13, summarized — full per-fixture
transcript in this session's `il_phaseC_plan_fixture_builder.py` output)

Every fixture: (1) `fixture_text in raw_corpus_source` → `True` (with
logged byte offset), (2) re-parsing the fixture alone reproduces the
identical single `Article` (number/body byte-equal), (3) LIVE captured-
terms set identical between the original untrimmed article body and the
fixture body. All 13/13 PASS on all three checks; zero fixtures written
that failed any check (the builder script refuses to write on failure).

### RED proof — full new-file run

```
backend/.venv/bin/pytest backend/tests/integration/test_definition_links_il_phase_c_widening_live.py -v
...
13 failed, 1 passed in 0.33s
```
The 1 pass is `test_c4_entry_start_re_cannot_match_double_colon_marker`
(a structural invariant that correctly holds TODAY, not a miss). All 13
capture-behavior tests fail with `AssertionError` showing the expected
term(s) absent from `created_definitions` — RED for the right reason,
not an error/fixture-loading failure.

### Full suite

```
backend/.venv/bin/pytest backend/tests -q
...
17 failed, 728 passed, 18 warnings in 16.67s
```
Exactly `4` (the E6-held set: 3 class-(d) tests +1 item-11 test,
unchanged, untouched) `+ 13` (this Planner's new REDs) `= 17` failed;
`727` (untouched baseline) `+ 1` (the new green non-overlap proof) `=
728` passed. Reproduced twice, stable.

### Boundaries / git discipline (M14)

`git status --short`: 14 untracked files (13 fixtures under
`backend/tests/fixtures/wiki_laws/` + 1 new test file
`backend/tests/integration/test_definition_links_il_phase_c_widening_
live.py`) — zero modifications to any existing file, zero
`backend/app/**` touched. Staged/committed with EXPLICIT paths only
(never `git add -A`/`git add .`, per M14). No `git stash` used.

### Honest gaps / assumptions (nothing hidden)

1. C2's fix design (additive sibling rule) is this Planner's
   recommendation for the Developer, not implemented or independently
   proven beyond the reasoning above — the RED test proves the MISS, not
   any particular fix shape.
2. C4's term-count reconciliation (93 vs QA's 116 for the `פרשנות`
   sub-case) is flagged, not resolved — see the honest note above;
   recommend QA cycle 3 re-measure against the Developer's actual
   implementation rather than trusting either sweep's number as final.
3. This Planner did NOT build a dedicated fixture/test for C4's
   genuinely-trigger-less default-to-`"local"` fallback path (found one
   real instance, `פקודת האגודות השיתופיות` art.2, but judged the two
   triggered-embedded fixtures already sufficient for RED-provenance;
   proportionate-effort call, not an oversight).
4. Did not attempt to measure or fix the definition_text-truncation-at-
   multi-line-continuation characteristic noted under both C1 and C4 —
   it is pre-existing (shared by every comma-triggered/`::-`-triggered
   instance already shipped), out of this bundle's scope, and does not
   affect term-identity correctness (only definition_text completeness)
   — noted for awareness, not escalated as a conflict (no recall-vs-
   precision tension here, just an existing completeness limit).
5. Did not vendor fixtures for the 2 additional real C2 instances
   (`היתר לעשיית עסקה בניירות ערך`, `חוק מס ערך מוסף`) beyond the one
   used for the RED test — live-reconfirmed but not built as separate
   fixtures (proportionate effort per the sprint's own established
   discipline for Group-B-style single-mechanism items).

qa_cycles: 2 (unchanged — Phase C is Planner work; QA cycle 3 is next).

---

## Phase C round 2 — M16 law-wide scope under-claim (Sonnet/high, Planner)

Relayed via inter-agent message from the sprint manager (a separate
Claude session, `general-purpose` agent role). Treated as a lead per M4,
not proof — every claim below was independently re-derived before any
test was written, same discipline as round 1.

### Independent verification of the core claim

Read `matcher._in_scope` directly (backend/app/definition_links/
matcher.py:136-163): `"local"` requires `article.number ==
definition.source_article_number`; `"law-wide"` returns unconditional
`True`. Confirmed `HebrewProfile.determine_scope` (profiles.py:192-199)
already defaults a RECOGNIZED הגדרות section to `"law-wide"` unless its
first line carries a chapter trigger — the exact parity precedent M16
cites. Confirmed my own round-1 C4 fixture (`כללי אתיקה לדיינים` art.1,
preamble `לעניין כללים אלה -`) is NOT in `il_colon_dash_nested_list_
scope_triggers.py::_SCOPE_TRIGGER_WORDS`, so it would default to
`"local"` under my own round-1 design — the defect is real and directly
affects my own shipped fixture, not a hypothetical.

### Population re-derivation (independent, not trusted)

Own script (`il_phaseC_plan_m16_vocab.py`), corpus-wide, both `:-` and
`::-`, ordinary (non-הגדרות) articles only, denominator = bare-`-`-
ending preamble + `"term" - definition` entries (same structural,
trigger-independent shape as round 1's C4 denominator — P-R7):
**reproduced the manager's headline number exactly: 1,107 single-`:-`
terms** (297 lists). Cross-check of the `::-` population: 5,573 terms
(2,018 lists) — also matches.

### Curated vocabulary — measured, hand-verified per phrase

**Method:** extracted every distinct preamble "reference phrase" across
both populations (297+2,018 = 2,315 lists), bucketed by frequency, then
fetched >=2 real corpus instances per non-trivial candidate phrase
(`il_phaseC_plan_m16_phrase_verify.py`) to visually confirm the
referenced noun genuinely denotes the WHOLE instrument.

**INCLUDED (law-wide), each verified against >=2 real instances:**
`בחוק זה` (e.g. `חוק איסור הונאה בכשרות` art.2ד; `חוק ביטוח בריאות
ממלכתי` art.7), `בחוק יסוד זה`, `בתקנות אלה` (`תקנות אוויר נקי (זיהום
אוויר מכלי רכב בדרך)` art.1, heading `פרשנות`), `בתקנות אלו` (`תקנות בדבר סמכויות
הקונסולים בישראל` art.2, heading `פירוש`), `בהסכם זה` (`הסכם בדבר מתן
הטבה סוציאלית לאוכלוסיה נזקקת` art.4), `בכללים אלה` (`כללי הבזק (שירותי
החברה)` art.1, heading `פרשנות`), `בפקודה זו` (`פקודת בזיון בית המשפט`
art.2), `בצו זה` (`צו בדבר חוק תכנון ערים...` art.1, heading
`פרשנות`), `באכרזה זו` (`אכרזת הפיקוח על מצרכים ושירותים...` art.1),
`בנוהל זה` (`נוהל עבודת הוועדה הציבורית...` art.2) — each also with the
`לענין`/`לעניין` preposition variant (verified for `חוק`/`פקודה` live;
the rest follow the same word-substitution pattern, included by the
same reasoning, not separately re-verified one-by-one — proportionate
effort, noted honestly).

**EXCLUDED, each with the reason live-verified — the manager's own
"watch the boundary cases" instruction, taken seriously:**
- `בתוספת זו` ("in this schedule", 72 single-`:-` terms) — the
  manager's own named case, confirmed: a schedule is a sub-part.
- **`בפוליסה זו`** ("in this policy", 21 terms) — **this Planner's OWN
  additional catch, not named by the manager.** Fetched the real
  instances (`הוראות הפיקוח על שירותים פיננסיים (ביטוח) (תנאי חוזה
  לביטוח חובה של רכב מנועי)`): every one sits inside an article headed
  `<עוגן * פרט N לטופס זה>` — the "policy" is an embedded FORM (a
  schedule-equivalent sub-document within the regulation), not the
  regulation itself. Would have been a genuine over-claim if included —
  exactly the boundary-case risk the manager flagged generically.
- `בפרק משנה זה` (sub-chapter, 110 terms) — narrower than the
  instrument; same open-containment category as סימן/חלק (item 2b,
  already capture-only this sprint).
- `בנספח זה`/`בטבלה זו`/`בנוסחה זו` (appendix/table/formula) — same
  sub-part reasoning as בתוספת זו.
- `בתקנה זאת` (alt. spelling of בתקנה זו — LOCAL, not law-wide) — a
  real, additional missing-spelling finding, flagged below, NOT folded
  into this fix (a different, smaller gap).
- `בתקנת שעת חירום זו` (emergency regulation) — article-level, same
  granularity as בתקנה זו per D-Q1, not the whole instrument.
- `לעניין כלל זה` (ONE specific rule, singular) — narrower than
  `בכללים אלה` (plural, the whole rules instrument); different phrase.
- `לעניין פרט חימוש זה` (a specific ammunition item), `באמת מידה זו`
  (a specific standard within a larger standards document) — far
  narrower than even one article.
- `לענין הסעיפים X-Y` / `לעניין סעיפים N ו-M` (enumerated multi-article
  ranges) — narrower than the whole law; a SEPARATE, smaller potential
  under-scope this bundle does NOT address (the schema already supports
  an enumerated `source_article_number` tuple per M9, but no rule
  populates it this way — flagged, not silently folded in).
- `לענין/לעניין סעיף (קטן) זה` — already correctly narrow via the
  existing 3-word local/subsection triggers.

### Zero collision with existing tests — verified, not assumed

Grepped every fixture in `backend/tests/fixtures/wiki_laws/` for each
INCLUDED law-wide phrase: 8 files hit (`חוק להגנת רכוש מופקד`, `חוק
המחשבים_stub`, `חוק הבנקאות (רישוי)_stub`, `תקנות קרן
גרמניה-ישראל_art1`, `צו איסור הלבנת הון (מפעיל מערכת
לתיווך)_excerpt`, plus 3 more that turned out to be the UNRELATED
ad-hoc-parenthetical grammar — `חוק איסור הלבנת הון_art3`, `חוק איסור
מימון טרור_art31`, `חוק זכות מטפחים...`). **Every genuine preamble+list
hit sits inside an article headed exactly `הגדרות`** (recognized —
`is_definitions_heading` → `True`), meaning `pipeline.py` dispatches
these via `extract_definitions_from_section` (which ALREADY defaults to
`"law-wide"` via `determine_scope`), never via the `ScopeTriggerRule`
path this change touches — this is actually POSITIVE supporting
evidence for the vocabulary choice: these 5 real, recognized-heading
`הגדרות` sections with `בחוק זה -`/`בתקנות אלה -`/`בצו זה -` preambles
are ALREADY treated as law-wide today, confirming the corpus's own
drafting convention matches the M16 fix's intent. Grepped every test
file for `["scope"]`/`.scope` assertions: the only 3 hits are in
`test_definition_links_pipeline_scope_seam.py` (core-owned, synthetic
`"Term"`/`"Widget"` fixtures, unrelated to real IL content). **Nothing
to escalate — no existing test asserts a scope value this change would
alter.**

### Containment machinery re-verified (static, live, this session)

```python
_in_scope(local_def(article="401"), article_401)  -> True   (own article)
_in_scope(local_def(article="401"), article_158)  -> False  (different article — correct non-leakage)
_in_scope(lawwide_def(), article_1)               -> True   (own article)
_in_scope(lawwide_def(), article_2)               -> True   (DIFFERENT article, same instrument — correct)
_in_scope(naive_local_def(article="1"), article_2) -> False  (M16's exact under-claim, reproduced)
```
Confirms: (1) the fix's target behavior is exactly what `"law-wide"`
already does (no new containment code needed, only classification), (2)
the negative/non-leakage direction is ALREADY proven by this unchanged
branch — every other local-scoped rule this sprint ships already relies
on it, extensively tested elsewhere (QA cycle 2's I3 gate). **A
repo-committed pytest RED test for the negative direction would be
vacuously green today** (nothing captured yet for the not-yet-shipped
C4 rule, so "no assertion anywhere" trivially holds — writing it would
violate the RED-provenance gate's own "fails today for the right
reason" requirement, not satisfy it). Not written, for that reason —
recommended as a QA cycle 3 live-verification item instead of a
committed test.

### RED tests (2, both live-confirmed failing for the right reason)

**1. New C4 rule's law-wide classification** —
`test_m16_lawwide_preamble_definition_links_a_mention_in_a_different_article`.
Fixture: `כללי אתיקה לדיינים_art1_art2_excerpt.wiki` (NEW, 2-article,
built by concatenating two INDEPENDENTLY byte-verified spans — see
below). Article 1 (`פרשנות`, preamble `לעניין כללים אלה -`) defines
`"דיין"`; article 2 (`מקור הכללים ותכליתם`) genuinely mentions `דיין`
in prose. Actual failure tail:
```
AssertionError: expected article 2 to get a USES_DEFINITION assertion
for the law-wide-scoped term "דיין" defined in article 1 ...; got
USES_DEFINITION assertions: [] (created_definitions=[])
```

**2. ALREADY-SHIPPED `::-` rule's under-scoping** —
`test_m16_already_shipped_double_colon_rule_under_scopes_a_lawwide_list`.
Fixture: `חוק הרשות לחקירה בטיחותית בתעופה_art1_art2_excerpt.wiki` (NEW,
2-article). Article 2 (`פרשנות`, preamble `בחוק זה -`) `::-`-defines
`"חוק הטיס"`; article 1 (`מטרה`) genuinely mentions `[[חוק הטיס]]`. This
is the CLEANER of the two REDs: capture already happens TODAY
(`created_definitions` shows `{'terms': ['חוק הטיס'], 'scope':
'local'}`) — only the scope (and therefore the cross-article assertion)
is wrong. Actual failure tail:
```
AssertionError: expected article 1 to get a USES_DEFINITION assertion
for the law-wide-scoped term "חוק הטיס" defined in article 2 (בחוק זה
-); got USES_DEFINITION assertions: [{...'Article 2 uses the definition
of "חוק שירות המדינה (מינויים)".'...}, {...'Article 2 uses the
definition of "משרד התחבורה".'...}, {...'Article 2 uses the definition
of "חוק הטיס".'...}] (created_definitions=[{'terms': ['חוק הטיס'],
'scope': 'local'}, ...])
```
(Note: article 2 gets a self-referential `USES_DEFINITION` assertion
for its own term — `"חוק הטיס"` is genuinely re-mentioned inside article
2's own body too, per the SAME `::-` list's own cross-references — a
real, correct edge, not a bug; the MISSING edge is specifically
article 1's.)

### Fixture byte-verification (2 new multi-article fixtures)

Non-adjacent-article fixtures cannot be a single contiguous corpus
slice by construction, so a small extension of round 1's builder
(`il_phaseC_plan_m16_multi_fixture_builder.py`) extracts EACH article's
own span independently (same marker-line-regex + `Article.body`
reconstruction as round 1), proves EACH is a byte-identical substring
of ITS OWN source file, then concatenates the verified spans (joined by
a blank line — the same separator `sections.parse_articles` already
tolerates between articles) and does a FINAL re-parse check confirming
the whole fixture yields exactly N Articles with byte-identical bodies
to the originals. Every byte in the fixture traces to a verified real
corpus slice; only the concatenation itself (assembling two real
articles into one synthetic document) is fixture-author-assembled — the
same characteristic any multi-article, non-adjacent fixture must have.
Both fixtures actually built this way happened to be numerically
ADJACENT in their source (art.1+art.2 in both cases, no chapter break
between), so each is independently also verifiable as part of one
larger contiguous region, a stronger property than required:
```
[כללי אתיקה לדיינים_art1_art2_excerpt.wiki]
  span [art 1]: 1024 bytes, verbatim substring of source: CONFIRMED
  span [art 2]: 1028 bytes, verbatim substring of source: CONFIRMED
  re-parses to 2 articles (expected 2): True

[חוק הרשות לחקירה בטיחותית בתעופה_art1_art2_excerpt.wiki]
  span [art 1]: 456 bytes, verbatim substring of source: CONFIRMED
  span [art 2]: 1373 bytes, verbatim substring of source: CONFIRMED
  re-parses to 2 articles (expected 2): True
```

### UNRECOGNIZED buckets — enumerated, denominator for QA cycle 3 reuse

Own script (`il_phaseC_plan_m16_unrecognized.py`), same denominator as
above, classified into KNOWN / LAW_WIDE / UNRECOGNIZED:

| population | total terms | KNOWN | LAW_WIDE | UNRECOGNIZED |
|---|---|---|---|---|
| single `:-` | 1,107 | 615 | 260 | 232 |
| double `::-` | 5,573 | 5,090 | 171 | 312 |

Top UNRECOGNIZED phrases (single `:-`): `בפרק משנה זה` 110, `בתוספת זו`
72, `בפוליסה זו` 21, `לעניין פרט חימוש זה` 6, enumerated section ranges
(`לעניין סעיפים...`/`לענין הסעיפים...`) 6+4+4, `לעניין כלל זה` 3,
`לעניין נוסחה זו` 2, `באמת מידה זו` 1. Top UNRECOGNIZED (double `::-`):
`באמת מידה זו`-family 131+7+4+4=146, enumerated subsection/paragraph
ranges ~30, `בתוספת זו`-family 12+1, `בתקנה זאת` 13, `בנספח זה`/`בטבלה
זו` 15, `בתקנת שעת חירום זו` 8, `בפיסקה זו` 6 (alt spelling of בפסקה
זו, another missing-spelling finding).

**Verdict per group (all already excluded above, restated for QA reuse
as a single denominator):** sub-part references (sub-chapter/schedule/
appendix/table/policy-form/standard) default-`"local"` is SAFE-BUT-
INCOMPLETE — same capture-only precedent as this sprint's existing
סימן/חלק items (item 2b), not a NEW gap, not part of this bundle.
Enumerated multi-article ranges default-`"local"` UNDER-claims for the
additional named articles — a real, separate, smaller gap, explicitly
NOT folded into this fix. Alternate spellings found but not yet
covered by ANY existing trigger (`בתקנה זאת`, `בפיסקה זו`) are real
additional findings, out of THIS bundle's scope, flagged for a future
cycle. Everything else (ammunition items, single rules, formulas,
standards) is genuinely narrow — default-`"local"` is CORRECT there.

### Suite (reproduced)

```
backend/.venv/bin/pytest backend/tests/integration/test_definition_links_il_phase_c_widening_live.py -v
...
15 failed, 1 passed in 0.29s
```
(13 round-1 REDs + 2 new M16 REDs = 15; the 1 pass is the non-overlap
static proof.)
```
backend/.venv/bin/pytest backend/tests -q
...
19 failed, 728 passed, 18 warnings in 12.41s
```
Exactly `4` (E6-held, unchanged) `+ 15` (this file's REDs) `= 19`
failed; `727` (untouched baseline) `+ 1` (green proof) `= 728` passed.
Reproduced twice, stable.

### Honest gaps / assumptions (round 2, nothing hidden)

1. The `לענין`/`לעניין` preposition-variant law-wide phrases were only
   individually live-verified for `חוק`/`פקודה`; the rest (תקנות/הסכם/
   כללים/צו/נוהל/אכרזה) are included by the same word-substitution
   pattern, not separately fetched one-by-one — proportionate effort,
   flagged rather than silently assumed.
2. Two real additional missing-spelling findings surfaced during this
   pass (`בתקנה זאת`, `בפיסקה זו` — alternate spellings of already-
   KNOWN triggers, not law-wide, not currently captured by ANY rule) —
   noted, not fixed, out of M16's own scope.
3. The enumerated-multi-article-range under-scope (a smaller, separate
   gap from M16's law-wide one) is flagged with counts but not
   addressed — a real residual for a future cycle, not silently folded
   into "law-wide" (would have been an over-claim to do so).
4. Per this Planner's own reasoning above, no repo-committed pytest RED
   exists for the negative/non-leakage direction — deliberate, per the
   RED-provenance gate, not an oversight; the static `_in_scope` proof
   above is the evidence offered instead.

### Boundaries / git discipline (M14, round 2)

Own worktree only (`/Users/nerya/LexGraph-wt/defs-il-plan3`); explicit
`git add` paths (2 new fixtures under `backend/tests/fixtures/wiki_laws/`
+ the extended existing test file + this log + the contract); no
`git add -A`, no `git stash`. Scratchpad files prefixed
`il_phaseC_plan_` throughout.

---

## Phase C round 3 — M17 spelling-variant audit (Sonnet/high, Planner, LAST increment)

Synced first: `git fetch origin` + `git merge origin/claude/defs-il
--ff-only` → fast-forwarded `715afd8..ae9d29f` cleanly (manager's merge
of rounds 1-2). Re-ran the full suite post-merge: `19 failed, 728
passed` — unchanged, confirms a clean base before starting.

### Enumeration method — corpus-derived, not invented

Wrote a shape-based, noun-agnostic sweep
(`il_phaseC_plan_m17_full_scan.py`): every occurrence of `<word(s)>
<demonstrative>` immediately before a quote (quote-first grammar) or at
a preamble-line tail before a bare `-` (list grammar), for
`<demonstrative> ∈ {זה, זו, זאת, אלה, אלו}` — the closed set of Hebrew
"this/these" forms every trigger in this sprint already uses. Ordinary
(non-הגדרות-heading) articles only, live chain. Result: **54 distinct
quote-first phrases (4,421 occurrences), 52 distinct list-shape phrases
(901 occurrences)** — the full observed universe, not a guessed list.
Every phrase was individually read and classified against the complete
existing/planned trigger inventory (every `rules/il_*.py` module's own
trigger regex, read directly; the frozen `_LOCAL_TRIGGER_RE`/
`_ADHOC_RE`; the M16 law-wide table).

### A methodology bug caught and fixed before it produced a false test

Initial list-shape measurement flagged `בתקנה זאת` as a 15-occurrence
`:-`-marker miss. Investigating the SMALLEST candidate
(`תקнות שעת חירום (מסירת מידע...)` art.2) before building a fixture
showed the "hit" was a **coincidental substring match**: the article's
own text contains an AD-HOC parenthetical `(בתקנה זאת - זיהוי)` earlier
in a long sentence, and the REAL preamble governing the following
`:-`-list, at the actual end of that same physical line, is `בתקנה
זו` — already a KNOWN, correctly-scoped trigger. My first-pass scan
matched "trigger anywhere in the line," not "trigger is the line's own
GOVERNING phrase." Fixed the scanner to require the match within 6
characters of the trailing dash (i.e. actually adjacent to it,
matching what "the phrase that introduces this list" has to mean) and
re-ran: **`בתקנה זאת` list-shape is 15 `::-` occurrences (all ALREADY
captured today, all ALREADY correctly scoped `"local"` — a `תקנה`-
family word is article-level per D-Q1, so the existing unrecognized-
trigger default happens to be right here, unlike M16's law-wide words)
and 0 genuine `:-` misses.** Recorded as a corrected finding, not
silently dropped — the module-level comment in the test file documents
this explicitly so a later reader does not rediscover the same false
lead. (Quote-first measurements are NOT vulnerable to this bug: the
downstream regex requires the trigger to be immediately followed by a
quote via a tight connector, which cannot be satisfied by a
coincidental earlier mention.)

### Full variant-by-variant table (corpus counts, both grammars)

| Phrase | Quote-first | List-shape (`::-`/already captured) | List-shape (`:-`/genuine miss) | Verdict |
|---|---|---|---|---|
| בתקנה זאת | 6 | 15 (correct, local) | 0 | BUILD (qf only) |
| לענין/לעניין תקנה זאת | 0 | 0 | 0 | measured zero |
| בפסקה זאת | 1 | — | 0 | BUILD (qf) |
| לענין/לעניין פסקה זאת | 1 | — | 0 | BUILD (qf) |
| בתקנת משנה זאת | 4 | — | 0 | BUILD (qf) |
| בפסקה משנה זו (ה-spelling) | 4 | 0 | 0 | BUILD (qf) |
| בפסקה משנה זאת | 0 | 0 | 0 | measured zero |
| לענין/לעניין פרט זה (3-word) | 15 | 0 | 0 | BUILD (qf) |
| בחוק זה | 45 | 135 (M16-covered) | — | BUILD (qf) |
| לענין/לעניין חוק זה | 8 | 7 (M16-covered) | — | BUILD (qf) |
| בחוק יסוד זה | 0 | 3 (M16-covered) | — | measured zero (qf) |
| בתקנות אלה | 23 | 149 (M16-covered) | — | BUILD (qf) |
| בתקנות אלו | 1 | 0 | 1 | BUILD (both) |
| לענין/לעניין תקנות אלה | 2 | 4 (M16-covered) | — | BUILD (qf) |
| בהסכם זה | 0 | 36 (M16-covered) | — | measured zero (qf) |
| לענין/לעניין הסכם זה | 0 | 0 | 0 | measured zero |
| בכללים אלה | 1 | 23 (M16-covered) | — | BUILD (qf) |
| בכללים אלו | 0 | 0 | 0 | measured zero |
| לענין/לעניין כללים אלה | 0 | 13 (M16-covered) | — | measured zero (qf) |
| בפקודה זו | 1 | 72 (M16-covered) | — | BUILD (qf) |
| לענין/לעניין פקודה זו | 0 | 0 | 0 | measured zero |
| בצו זה | 2 | 25 (M16-covered) | — | BUILD (qf) |
| לענין/לעניין צו זה | 1 | 0 | 0 | BUILD (qf) |
| באכרזה זו | 0 | 2 (M16-covered) | — | measured zero (qf) |
| לענין/לעניין אכרזה זו | 0 | 0 | 0 | measured zero |
| בנוהל זה | 0 | 20 (M16-covered) | — | measured zero (qf) |
| לענין/לעניין נוהל זה | 0 | 0 | 0 | measured zero |

"M16-covered" = already captured today with `scope="local"`, already
identified as a defect and given a dedicated RED in round 2 (M16's
vocabulary fix, once shipped, fixes the SCOPE for every phrase in that
table at once — no per-phrase M17 test needed for the list-shape side
of an M16-table word; M17's own contribution is specifically the
QUOTE-FIRST grammar, which M16 never touched).

### Residuals — genuinely NOT spelling variants, logged not built

- **לענין/לעניין הגדרה זו** (11 qf + 13 ls = 24) — "regarding this
  DEFINITION": a nested-definition cross-reference matching the FROZEN
  `extract._NESTED_MARKER_RE` (`לעניין הגדרה זו,`) concept, structurally
  different from a scope-container trigger; not reachable by the
  ordinary-article path today. Not a spelling variant of anything.
- **לענין קו זה** (6) — "regarding this bus/train LINE," an unrelated
  transportation concept.
- **פרט משנה זה** (4) — "sub-item": follows the SAME "X משנה" sub-unit
  morphological PATTERN as `תקנת משנה`/`פסקת משנה`, but is a different
  base noun combination, not an orthographic respelling of `בפרט זה` —
  a new (if pattern-consistent) granularity concept, out of scope.
- **לצורך X זה** (~5: `לצורך סעיף זה` 3, `לצורך תקנה זו` 1, `לצורך הגדרה
  זו` 1) — a THIRD preposition family (`לצורך`, "for the purpose of"),
  not an orthographic variant of `ל`/`לענין`.
- **בכלל זה** (2) — Hebrew idiom "including this," a FALSE FRIEND, not
  a respelling of `בכללים אלה` (different word entirely) — explicitly
  excluded, same caution as round 2's own false-friend catch (`בפוליסה
  זו`).
- **במנשר זה** (2) — "in this manifesto," a rare Mandate-era instrument
  word, thematically parallel to the M16 law-wide family but not a
  respelling of any word already in it.
- **ביום זה** (6) — temporal ("on this day"), unrelated.
- Already-excluded sub-part family, re-confirmed present (not new):
  `באמת מידה זו`-family (~146), `בתוספת זו`, `בנספח זה`, `בטבלה זו`,
  `בפוליסה זו`, `בנוסחה(ות) זו/אלה`, `בפרק משנה זה`.

### Completeness argument (verbatim, also in the test file's module
docstring — this is the sentence the manager asked to be read hardest)

The enumeration is complete FOR THE DEMONSTRATIVE-ADJACENT SHAPE this
sprint's own trigger grammar universally uses: every trigger phrase
across every shipped/planned rule module has the form `<noun phrase>
<demonstrative>`, and the sweep scanned for exactly that shape,
corpus-wide, unfiltered by any assumption about which nouns or
demonstratives to expect — a variant sharing the shape cannot escape it
(there is no sixth Hebrew "this/these" form). What it honestly does
NOT prove: (1) a trigger that drops the demonstrative entirely (no
evidence any shipped trigger works this way — not a live risk, but not
provably absent); (2) a variant using a preposition other than `ב`/`ל`
— the sweep's own regex only anchors those two (plus no-prefix); it DID
surface a third, `לצורך`, logged as a residual rather than silently
folded in or silently missed; (3) a spelling variant of a concept-noun
never yet added to the ~30-trigger base set at all — mitigated (the
scan is noun-agnostic, so an unknown noun's OWN spelling would still
surface in the frequency table for review) but not eliminated: a noun
variant that occurs literally ZERO times under any demonstrative
anywhere in the corpus is undetectable by any corpus-derived method,
and no claim is made to have found it.

### Fixtures (16 new, all byte-verified per the established methodology)

All confirmed via the same `il_phaseC_plan_fixture_builder.py` triple
check (verbatim substring / re-parse identity / live-equivalence)
before writing; one filename-length caveat: the corpus's own file for
`תקנות הנזיקים האזרחיים (אחריות המדינה) (הוועדה...)` is itself
truncated at the filesystem level (ends `...סדרי עבודה ו.wiki` — a
read-only corpus characteristic, not something this Planner touched or
could touch). One article-number pitfall caught before building: a
`בתקנות אלה` candidate in `תקנות שעת חירום (הסדרים לשעת חירום במשק
המדינה)` resolved to an AMBIGUOUS article number (2 distinct articles
numbered `'3'` in that file — a real, if unusual, corpus characteristic
some files exhibit); the fixture builder's own single-match assertion
caught it before a wrong fixture could be built, and a different,
unambiguous candidate was used instead.

### RED proof (this file, M17 tests only)

```
backend/.venv/bin/pytest backend/tests/integration/test_definition_links_il_phase_c_widening_live.py -k m17 -v
...
16 failed, 16 deselected in 0.48s
```
All 16 fail with `AssertionError: expected "<term>" captured (art.N);
got []` — RED for the right reason (term genuinely absent), not a
fixture-loading error.

### Full suite

```
backend/.venv/bin/pytest backend/tests -q
...
35 failed, 728 passed, 18 warnings in 13.46s
```
Exactly `4` (E6-held, unchanged) `+ 13` (round 1) `+ 2` (round 2/M16)
`+ 16` (round 3/M17) `= 35` failed; `727` (untouched baseline) `+ 1`
(round 1's green non-overlap proof) `= 728` passed. Reproduced, stable.

### Boundaries / git discipline (M14, round 3)

Own worktree only; explicit `git add backend/tests/fixtures/wiki_laws
backend/tests/integration/test_definition_links_il_phase_c_widening_live.py`
(the fixtures directory add picks up only the 16 new untracked files —
verified via `git status --short` before and after, nothing pre-existing
touched); no `git add -A`, no `git stash`. Scratchpad prefixed
`il_phaseC_plan_` throughout.

### Honest gaps (round 3, nothing hidden)

1. This is a Planner-level audit against the CURRENT trigger inventory;
   it does not (and per M17's own scope, should not) re-audit C1's
   punctuation-variant findings for THEIR OWN spelling-variant exposure
   (e.g. does `בפסקה זאת` also need the comma/space/colon/dash widening
   C1 already found for `בפסקה זו`?) — flagging this as a plausible
   compounding dimension neither round has fully crossed, for QA cycle
   3 or a future cycle to weigh.
2. The `לצורך` residual (~5 occurrences) was found opportunistically by
   this audit's own regex (which permits an optional `ל`/`ב` prefix,
   and `לצורך` happened to still satisfy the trailing noun+demonstrative
   shape) — not from a deliberate third-preposition sweep. A dedicated
   sweep for `לצורך`/other prepositions was NOT run; this residual's
   own count (~5) should be treated as a lower bound, not a ceiling.
3. Per M17's explicit instruction, no attempt was made to fix or build
   for any residual — all are named with counts and left for director/
   program-manager review.

qa_cycles: 2 (unchanged — Phase C is Planner work through all three
rounds; QA cycle 3 is next).

---

## Phase C — Developer (Sonnet, medium effort), worktree defs-il-dev3

Own worktree `/Users/nerya/LexGraph-wt/defs-il-dev3`, branch
`claude/defs-il-dev3`, reset to `origin/claude/defs-il` @ `237716c`
(includes `main` @ `fbb6c9e`). `import app` verified to resolve to this
worktree. Verified baseline before touching anything: `35 failed, 798
passed` — exactly the Planner's own reported figure (31 new REDs + the
4 manager-designated out-of-scope class-(d)/E6 tests). Read the
contract, all three Phase C log entries above, the RED test file's full
docstrings/comments, the seam v2.5 doc, and every existing `rules/il_*.py`
module directly (CodeGraph's index predates this branch's rule files).

### Design decisions, per item

**C1 (punctuation widening).** New shared module
`il_trigger_grammar.py`: `CONNECTOR = (?:[ \t]*[,:\-][ \t]*|[ \t]+)` —
intra-line whitespace only (never `\n`, a precision safeguard beyond the
contract's literal snippet — real fixtures need a LEADING optional space
before the punctuation mark too, e.g. `בתקנה זו - "..."`, which the
contract's bare `(?:[,:\-]\s*|\s+)"` cannot match; verified against every
C1 fixture before committing to this shape). `quote_first_re()` builds a
SHORT trigger+connector-only regex (never a greedy to-EOL capture — see
C2). `extract_quote_first_candidates()` is the shared parsing algorithm:
finds the split marker via `_find_split_marker` (a standalone `-`, OR the
corpus's own `((-))` double-paren-escaped-dash idiom — evidence-required
by the real `צו בדבר העסקת עובדים...` art.6 fixture, `"שוהה לא חוקי"
((-)) כהגדרתו ...`, not invented), then parses 1+ quoted terms + an
optional qualifier via a local copy of `extract._parse_terms_and_qualifier`'s
algorithm (a copy, not an import — this sprint's change set is
rule-modules-only, `extract.py` stays untouched even as an import
source) — needed because a single `"([^"]+)"\s*-\s*` capture group
cannot parse the real `"term1" ו"term2" qualifier - definition` shape
(`חוק שירות הציבור...` art.7, `תקנות תכנון משק החלב...` art.6). Applied
by editing 5 existing modules (lenyan_zeh_tzere, takana, subsection,
paragraph, seif_zeh_three_word) to call the shared helper instead of
their own inline `"([^"]+)"\s*-\s*(.*)$` pattern. Did NOT widen
chapter/siman/chelek's connector — not in the contract's named 7
families, no FP measurement exists for it, would be an unverified
over-claim.

**C2 (same-line-swallow).** New additive sibling
`il_local_trigger_widened_scope_triggers.py` for the yod-family `לענין
זה`/`בסעיף זה` (never edits frozen `_LOCAL_TRIGGER_RE`). Design decision
left open by the Planner: rather than a "re-scan for what the frozen
rule swallowed," this sibling's own trigger regex only matches
trigger+connector (not a greedy-to-EOL capture), so `finditer`'s scan
position is never affected by how far the wrapper reads ahead for its
own definition text — a second same-line trigger is found independently
by construction, without needing to know what the frozen rule did. This
ALSO fixes C1's yod-family punctuation gap for free, so ONE module
serves both items. **Regression found and fixed**: this sibling's own
candidates for a COMMA-connector, single-occurrence body duplicate what
`extract_local_definitions` already produces — harmless under
`pipeline.py`'s dedup (same scope, first-candidate-wins), but broke a
committed unit test asserting the IL profile's raw candidate COUNT
matches calling the two frozen functions directly
(`test_il_profile_extract_local_scope_definitions_matches_todays_extract_local_and_adhoc`).
Fixed by explicit term-level de-dup against `extract_local_definitions`'s
own baseline output for the same body — caught via the mandatory
full-suite run after implementing C1+C2, not assumed safe from the
"harmless duplicate" reasoning alone.

**C3 (inline בפרט זה).** Extended `il_prat_zeh_item_scope_triggers.py`
with a SECOND registered `ScopeTriggerRule` (`_extract_inline`, using
the shared quote-first helper) rather than a new file — same trigger
word, same `scope="item"`, just a different grammar, kept together with
its sibling. Structurally disjoint from the existing `::-` list rule
(preamble-ends-in-bare-dash vs. quote-on-the-trigger's-own-line); even
if it weren't, same scope, harmless.

**C4 (single-`:-` list generalization).** New
`il_single_colon_list_scope_triggers.py`. Extracted the existing `::-`
rule's own preamble->scope vocabulary table, `_infer_scope`, and
candidate-building logic into a new shared module `il_list_shape_scope.py`
(byte-for-byte verified via a diff script against the original table
before editing anything downstream), then had BOTH the new single-`:-`
rule and the edited existing `::-` rule import from it — the "shared
trigger→scope vocabulary table, reused across rules" directive, applied
literally. Non-overlap with the existing `::-` rule is structural (this
rule's own `_ENTRY_LINE_RE = ^\s*:-\s*` cannot match a `::-` line, same
argument `test_c4_entry_start_re_cannot_match_double_colon_marker` pins
for the frozen `_ENTRY_START_RE`) — kept as two sibling files rather
than merging into one marker-agnostic regex, matching the contract's own
"two rules... structural non-overlap" framing rather than a
reinterpretation.

**M16 (law-wide scope).** Added `LAW_WIDE_WORDS`/`law_wide_preamble_phrases()`
to `il_trigger_grammar.py` (extracted programmatically from the log's
own INCLUDE list, cross-checked byte-for-byte via script rather than
hand-typed, given the Hebrew-transcription risk) — 10 instrument words ×
{bare, `לענין`, `לעניין`} = 30 phrases, all mapped to `scope="law-wide"`
in the shared `il_list_shape_scope.SCOPE_TRIGGER_WORDS` table. Both the
new single-`:-` rule and the edited existing `::-` rule consume this
table, so BOTH classify an instrument-naming preamble correctly from day
one. Verified no substring collision between the new law-wide phrases
and the existing local/subsection/paragraph/item vocabulary (distinct
base nouns throughout — e.g. `תקנה` singular vs. `תקנות` plural never
collide).

**M17 (spelling variants).** New
`il_m17_spelling_variant_scope_triggers.py`. Group 1: 5 trigger
alternations covering the local/paragraph/subsection/item spelling
variants (`בתקנה זאת`, `בפסקה זאת`/`לענין/לעניין פסקה זאת`,
`בתקנת משנה זאת`, `בפסקה משנה זו`, `לענין/לעניין פרט זה`) — each
verified disjoint in TEXT from every other trigger this sprint
registers (no substring containment either direction), so no
double-capture-with-differing-scope risk. Group 2: reuses
`law_wide_preamble_phrases()` verbatim as ONE alternation for the
quote-first law-wide grammar M16 never touched — same vocabulary, same
scope, a different grammar shape only.

### Verification methodology (avoiding Hebrew-transcription risk)

Every trigger phrase used across all new/edited modules was extracted
PROGRAMMATICALLY from either the already-vendored fixture files (via a
boundary-scan script locating the exact text immediately preceding each
test's expected quoted term) or the log's own INCLUDE list (via regex
extraction + `repr()` dump), never hand-retyped from a visual reading of
Hebrew text — the existing `il_colon_dash_nested_list_scope_triggers.py`
vocabulary table was additionally diffed programmatically
(tuple-for-tuple equality check) against its extracted copy in
`il_list_shape_scope.py` before any downstream file was written against
it.

### Full suite (reproduced 3x, stable)

```
backend/.venv/bin/pytest backend/tests -q
...
4 failed, 829 passed, 18 warnings in ~217-620s (wall time varied with
concurrent sibling-worktree load; failure/pass counts identical every
run)
```
The 4 failures are exactly the manager-designated out-of-scope set
(`test_class_c_adhoc_parenthetical_beparagraph_zo_inside_definitions_
section_is_captured`, `test_class_d_prose_body_definitions_section_
yields_zero_today`, `test_class_d_variant_double_colon_entry_list_
under_a_trigger_preamble_is_captured`, `test_class_d_minimal_single_
sentence_variant_is_captured`), untouched. All 31 Phase C REDs
(`test_definition_links_il_phase_c_widening_live.py`) pass; the 1
already-green static proof (`test_c4_entry_start_re_cannot_match_
double_colon_marker`) still passes.

Only ONE test changed state, and it changed AND WAS FIXED within this
same session (not a residual gap): `test_il_profile_extract_local_
scope_definitions_matches_todays_extract_local_and_adhoc` (unit,
`test_definition_links_profiles.py`) — see C2's write-up above. Verified
green again in every subsequent full-suite run.

### Git discipline (M14)

`git add` with explicit paths only (12 files: 5 new, 7 edited, all under
`backend/app/definition_links/rules/`), never `git add -A`/`git add .`;
no `git stash`. `git diff --name-status origin/claude/defs-il..HEAD`
confirms the entire change set is exactly this boundary — zero test or
fixture files touched. `contract_lint.sh 2026-08-04-defs-il`: PASS (400
lines, at the cap — this entry kept to a summary, full design reasoning
lives here in the log per the contract's own instruction).

### Honest gaps / assumptions (nothing hidden)

1. The CONNECTOR shape deviates from the contract's literal regex
   snippet (`(?:[,:\-]\s*|\s+)"`) by adding a LEADING `\s*` before the
   punctuation branch — required by every C1 dash-variant fixture
   (`TRIGGER - "term"`, a space THEN a dash), which the literal snippet
   cannot match. Documented as a deliberate, evidence-driven correction
   in `il_trigger_grammar.py`'s own docstring, not a silent deviation.
2. The `((-))` escaped-dash marker and the multi-term-before-dash
   parsing were both NECESSARY additions beyond the contract's explicit
   C1 description (which only names the trigger-to-quote connector) —
   both are directly required by real, already-vendored Planner
   fixtures, not speculative widening; documented in
   `il_trigger_grammar.py`.
3. Did not attempt to fix the definition_text-truncation-at-multi-line-
   continuation characteristic the Planner already flagged as
   pre-existing and out of this bundle's scope (C1/C4 log entries) —
   unaffected by this Developer's changes, term-identity correctness
   only, not touched.
4. `il_m17_spelling_variant_scope_triggers.py`'s Group 1 patterns are
   individually widened via the SAME shared connector as every other
   quote-first rule (so a bare-space/colon/dash variant of e.g. `בתקנה
   זאת` would also be caught) — this was not separately FP-measured by
   the Planner for these specific spelling-variant phrases (only for the
   original 7 C1 families), but the invariant (never a zero-length gap)
   is the same evidence-based one throughout; flagging as a minor
   implementation-reuse choice, not a claimed, separately-measured
   population.

Branch `claude/defs-il-dev3`, final SHA `572343c`. Pushed for the
manager to merge.

---

## QA cycle 3 (Sonnet/high, independent)

Own worktree `/Users/nerya/LexGraph-wt/defs-il-qa3`, branch
`claude/defs-il-qa3`, reset to `origin/claude/defs-il` @ `4f95c4a`
(verified: `git log --oneline -3` matches, `git status --short` clean at
start). `import app` resolves to this worktree. Read the contract in
full (gates, items 1-12, rulings M1-M17) and the WHOLE log, especially
QA cycles 1+2, all three Phase C Planner rounds, and the Phase C
Developer entry. **Never touched `backend/app/**`** — verified
`git status --short` clean throughout except this log/contract and one
throwaway pytest file (`backend/tests/integration/zzz_qa_cycle3_probe.py`,
3 tests, all green, deleted before this commit — never pushed; same
discipline as QA cycle 2's own throwaway probe).

### Gate I5 (regressions) — PASS

- `backend/.venv/bin/pytest backend/tests -q` → **`4 failed, 829 passed,
  18 warnings in ~14-31s`**, reproduced 3x (including once AFTER deleting
  the throwaway probe file, to confirm cleanup left the suite unchanged).
  The 4 failures are exactly the E6-held set (3 class-(d) + 1 item-11),
  matching the contract's claimed target state.
- `bash scripts/contract_lint.sh 2026-08-04-defs-il` → **PASS 400**.
- `git diff --name-status origin/main...HEAD -- backend/tests` → all 65
  entries `A` (addition); **zero existing test edited.**
- `git diff --name-status origin/main...HEAD -- backend/app/definition_
  links/{pipeline,matcher,extract,sections,profiles}.py` → **empty**
  (all 5 frozen modules untouched).
- `git diff --name-status 237716c..4f95c4a -- backend/app` (Phase C
  Developer's own commits, isolated from Phase A/B) → **exactly 5 `A` +
  7 `M`, all under `backend/app/definition_links/rules/`**, matching the
  Developer's own claimed boundary exactly; zero tests/fixtures touched
  in this range either.

### Gate I1 (full corpus loads) — PASS, confirms cycle 1/2's corrected figure, post core-dispatch merge

Independent re-run (own script, own scratch sqlite DB, real
`app.definition_links.ingest_wiki_corpus.run_bulk_ingest`, not a
re-implementation): **files found 6133, files processed 6133, files
failed 0, total_articles 128234** — exact match to QA cycles 1 and 2's
figure, confirming the tree now including `main` @ `fbb6c9e` (core's
dispatch sprint) introduced no change to IL parsing/reachability. Wall
time 24.8s, peak RSS 65.6 MiB (same order of magnitude as prior runs).
Corpus re-verified untouched after (`ls | wc -l` → 12266).

### Gate I3 (scope enforcement, BOTH directions) — PASS, live end-to-end, on two fresh real corpus laws neither prior cycle used

This cycle's mandatory, previously-un-run check (the Phase C Planner
deliberately did not commit a RED for the non-leakage direction — see
round 2's log entry — and asked QA to verify it live). Both directions
proven through the REAL chain (`ingest_wiki_law` + `run_definition_
linking` end-to-end, throwaway pytest probe, deleted before commit):

**Direction (a) — law-wide DOES link across articles**, specifically
exercising the NEW C4+M16 combination (a single-`:-` list under a
`בחוק זה -` preamble in an ORDINARY, non-הגדרות-heading article — not
the older, already-proven הגדרות-section law-wide default):
`חוק להשבחת ייצור חקלאי (בעלי חיים), תשי"ב-1952` (6 real articles,
unedited). Article 1 (heading `פירושים`, preamble `בחוק זה -`, single-
`:-` list) defines `"בעל חיים"`. Live result: `created_definitions` =
`[{'terms': ['בעל חיים'], 'scope': 'law-wide'}]`; article 4 (a
DIFFERENT article, genuinely mentions `"בעל חיים"` twice in its own
prose, e.g. `"לתפוס כל בעל חיים... למחזיק בעל החיים"`) gets
`USES_DEFINITION` → `'Article 4 uses the definition of "בעל חיים".'`.

**Direction (b) — local (`בסעיף זה`) does NOT link outside its own
article**: `חוק אימות מסמכים (תביעות פיצויים מיוחדות), תש"י-1949` (6
real articles, unedited). Article 2 (heading `תנאי לשימוש בסמכות`,
preamble `בסעיף זה -`, `::-` list) defines `"מסמך"`, scope confirmed
`local`. Ground truth: article 3's own raw body genuinely contains the
standalone term `מסמך` (`"...לתרגם ולאשר את תרגומו של מסמך לשפה
נכרית"`). Live result: article 2 gets its own (correct, same-article)
`USES_DEFINITION` edge; **article 3 gets ZERO edges for `מסמך`** despite
the genuine textual recurrence — proving this is a real missed-linking
opportunity staying correctly unlinked, not an untested path.

CHECK: throwaway `backend/tests/integration/zzz_qa_cycle3_probe.py`
(2 I3 tests + 1 I4 test, all green — see below), deleted before this
commit, never pushed; the transcripts above are the durable record.

### Gate I4 (zero-miss sweep) — **FAIL. Confirmed, real, live-verified misses — three of them structurally NEW (not named by cycles 1 or 2 or Phase C), plus large residuals in the two headline populations the manager asked me to attack.**

#### Methodology (P-R7, binding)

Every measurement below runs through the REAL live chain
(`sections.parse_articles` → `profile.normalize_for_parsing` →
`profile.extract_local_scope_definitions`, the exact order
`pipeline.py` uses for an ordinary article), on ordinary
(non-הגדרות-heading) articles — the only articles the rules under test
reach. Every denominator below is built from STRUCTURE or GRAMMAR
(preamble-line shape, entry-marker shape, demonstrative-anchored
trigger shape), **never from the shipped rule's own regex** — this is
what makes each one signal-agnostic per P-R7. Every reported miss was
independently confirmed live (direct `extract_local_scope_definitions`
call showing the term absent, or — for the three new bugs — a direct
call into the actual shared helper function showing exactly where/why
the candidate is discarded).

#### NEW BUG A — multi-term list-shape entries are silently dropped whole (structural sweep, found by looking at the ENTRY grammar itself, not any trigger word)

**Root cause (proven, not inferred):** the shared `il_list_shape_scope.
ENTRY_TERM_DASH_RE = re.compile(r'^"([^"]+)"\s*-\s*(.*)$')` (used by
BOTH `il_colon_dash_nested_list_scope_triggers.py` and the new C4
`il_single_colon_list_scope_triggers.py`) only matches a SINGLE quoted
term at the start of an entry line. A real, common corpus shape —
`::- "term1", "term2" ו"term3" - definition` (one entry line naming
MULTIPLE terms, exactly the shape Developer's OWN C1 work added
`_parse_terms_and_qualifier` to the quote-first grammar to handle) — is
NOT handled by the list-shape grammar at all: `entry_match` still
succeeds (the line starts with `:-`/`::-`), but `term_match` fails
silently, and the loop just moves on to the next line without adding
ANY candidate for that entry — dropping every term on that line, not
just the extras.

**Denominator (signal-agnostic):** every `:-`/`::-` entry line in an
ordinary article whose header starts with a quoted term but is NOT
single-term-dash-shaped, with ≥2 genuinely distinct quoted terms in the
HEADER portion only (before the real split marker — fixed a v1 script
bug that scanned quotes in the definition text too, which falsely
flagged gershayim abbreviations like `ת"י`/`גפ"מ` as "extra terms";
v2's fix mirrors `il_trigger_grammar._find_split_marker`'s own
algorithm).

**Result: 482 multi-term entry lines / 1,188 quoted terms found
corpus-wide; 479 lines / 1,173 terms confirmed MISSING from live
`extract_local_scope_definitions` output (98.7%); 239 unique files.**
Zero false positives found in a full read of the qualifying sample
(citations, wiki-links, and reference clauses inside the DEFINITION
text are correctly excluded by the fixed split-marker logic). Named
examples (file, article, terms, all confirmed live `[]`):
- `חוק אזורים חופשיים לייצור בישראל` art.23א: `"החזקה"`, `"שליטה"`,
  `"אמצעי שליטה"` (`::- "החזקה", "שליטה", ו"אמצעי שליטה" - כמשמעותם
  [[בחוק ניירות ערך]];`). Confirmed via full live `ingest_wiki_law` +
  `run_definition_linking` on the whole unedited law: `"החזקה"` is
  absent from the WHOLE document's `created_definitions` (a clean,
  unambiguous, standalone miss — no other article in this law defines
  it). `"שליטה"`/`"אמצעי שליטה"` ALSO happen to be independently
  (correctly) defined via unrelated single-term entries in three OTHER
  articles of the same law (lines 217/304/337) — a genuine
  self-caught P-R10 subtlety: their term-strings are NOT absent from
  the whole-document term set, but article 23א's OWN local-scoped
  definition of them is still genuinely dropped (any mention relying
  on THAT specific local scope would fail to link).
- `חוק ביטוח בריאות ממלכתי` art.21ד: `"בית מרקחת"`, `"תכשיר מרשם"`.
- `חוק הביטוח הלאומי` art.295א: `"חבלת שירות"`, `"חייל בשירות קבע"`,
  `"מחלה"`, `"מחלת שירות"`.
- `חוק הבנקאות (שירות ללקוח)` art.7א: `"סולק"`, `"ספק"`, `"עסקה"`.
- `הוראות הפיקוח על שירותים פיננסיים (ביטוח) (תנאי חוזה לביטוח חובה של
  רכב מנועי)` art.1: `"נזק גוף"`, `"נפגע"`, `"שימוש ברכב מנועי"`,
  `"תאונת דרכים"`.
- `חוק איסור הלבנת הון` art.30: three separate multi-term entries —
  `"ארגון טרור"`/`"ארגון טרור מוכרז"`/`"מעשה טרור"`/`"רכוש טרור"`;
  `"גורם זר מסייע"`/`"פעילות כלכלית"`; `"גורם מוכרז"`/`"גורם קשור"`.
- Full enumerated list (all 479 lines / 1,173 terms) in this session's
  scratchpad `il_phaseC_qa3_i4_multiterm_listentry_sweep2.py` output —
  available on request, not reproduced in full here for length.
- Live end-to-end proof (not just the isolated-article function call):
  `test_i4_multiterm_list_entry_is_dropped_live_end_to_end` in the now-
  deleted throwaway probe, green, asserting `"החזקה"` absent from the
  WHOLE document's `created_definitions` after a full `ingest_wiki_law`
  + `run_definition_linking` run on the real, unedited law.

#### NEW BUG B — quote-first candidates with NO split-marker after the quote are silently discarded whole (a second, independent structural sweep)

**Root cause (proven, not inferred):** `il_trigger_grammar.
extract_quote_first_candidates` requires `_find_split_marker` to find a
standalone `-` (or `((-))`) SOMEWHERE after the quoted term(s); if it
returns `-1`, the WHOLE candidate is discarded (`continue`), even
though the trigger+quote matched correctly. Real corpus definitions
routinely use `TRIGGER, "term" כהגדרתו/כמשמעותה [[citation]].` (a
by-reference definition with NO second dash — the sentence just ends)
or `TRIGGER, "term" <definition text ending in a period/semicolon, no
dash at all>` — BOTH shapes are silently dropped, corpus-wide, for
EVERY rule built on this shared helper (every C1-widened family, C2's
yod sibling, C3, M17 groups 1+2 — i.e. most of Phase C's own output).
Confirmed live for the ROOT case:
```python
>>> extract_quote_first_candidates('לענין זה - "מסירה" כמשמעותה בסעיף 8 לחוק המכר...', trig, scope="local")
[]   # _find_split_marker returned -1
```
matching the real corpus text `חוק מס ערך מוסף` art.22: `לענין זה -
"מסירה" כמשמעותה [[בסעיף 8 לחוק המכר, תשכ"ח-1968]].` →
`extract_local_scope_definitions` → `[]` (confirmed live, term `"מסירה"`
absent).

**Denominator (signal-agnostic — reuses M17's own noun-agnostic
demonstrative-shape scan, not this sprint's curated trigger list):**
every `<1-3 Hebrew words><דמonstrative><connector>"term"` occurrence in
an ordinary article (`(?:זה|זו|זאת|אלה|אלו)` + the shared C1
connector), then checked for a split marker in the remainder of the
clause. **Result: 6,364 generic quote-first candidates corpus-wide;
132 (2.1%) have no split-marker and are silently dropped.** Hand-
classified a sample of 60: ~20% (`~26/132` extrapolated) are the clean
`כהגדרתו/כמשמעותו`-reference shape; ~80% (`~106/132`) are a plain
"quoted term, definition continues without any dash at all" shape (a
few of the 60-sample are a genuinely DIFFERENT, unrelated grammar —
`"X נקרא/נקראת בחוק זה 'term'"`, term-naming without a preceding
trigger-quote-dash structure at all — outside this bug's scope, noted
not folded in). Named, live-confirmed examples: `חוק מס ערך מוסף`
art.22 `"מסירה"`; `פקודת מס הכנסה` art.135 `"פקיד שומה"` (via `ולענין
זה, "פקיד שומה" למעט עוזר פקיד שומה...` — the `ו`-conjunction-prefixed
form); `חוק התקנים` art.13 `"מצרך"`; `חוק החמרים המסוכנים` art.16ג
`"קצין משטרה"`; `חוק זכויות נפגעי עבירה` art.1 `"אחראי על קטין או חסר
ישע"`. Full list in scratchpad `il_phaseC_qa3_i4_nodash_afterquote_
sweep.py` output.

#### NEW BUG C — the preamble sometimes lives in the ARTICLE'S OWN HEADING, not the body; no list-shape rule ever scans the heading

**Root cause (proven):** both list-shape rules (`il_colon_dash_nested_
list_scope_triggers.py`, `il_single_colon_list_scope_triggers.py`) call
`PREAMBLE_RE.search(lines[i])` only over `article_body`'s own lines —
`RuleContext`/the rule signature never receives `.heading` at all. A
real, recurring corpus shape (mostly `== תוספת ==`/schedule
sub-articles, and a few free-standing `הכרזה` documents) puts the
scope-trigger preamble directly IN the heading line, e.g. heading
`(תיקון: תש"ף) : [[בתוספת זו]] -` or `: לעניין הכרזה זו -`, with the
`:-`/`::-` entries starting on the VERY FIRST line of the body — no
preamble line anywhere in the body at all. **Result: 27 entry-runs / 24
unique files / 117 terms, ALL confirmed missing (100% of this narrow,
cleanly-isolated class).** Named examples: `אכרזת גנים לאומיים, שמורות
טבע, ...` art.8 (heading ends `[[בתוספת זו]] -`): `"תמצית"`,
`"כלי נגינה מוגמרים"`, `"אבזרים מוגמרים לכלי נגינה"`,
`"חלקים מוגמרים לכלי נגינה"`, `"מוצרים מוגמרים וארוזים לצורך מכירה
קמעונאית"`, `"אבקה"`, `"משלוח"`, `"עץ מעובד"` (8 terms, ZERO captured);
`הכרזה מס' 3/4 ומס' 1+2 על שינויים בתחולת חוק כליאתם של לוחמים בלתי
חוקיים` (3 files, same 5 terms each — `"הודעת ועדת השרים"`,
`"החוק"`, `"החלטת ועדת השרים"`, `"ועדת השרים"`, `"תקנות מועדים
לטיפול"`); `תקנות התקשורת (בזק ושידורים) (היתר כללי למתן שירותי בזק)`
art.1 (heading `[[בתוספת זו]] -`): 31 technical-standards-body acronym
terms (`3GPP`, `ATIS`, `IEEE`, `ITU-T`, ... — ALL 31 missing). Full
list in scratchpad `il_phaseC_qa3_i4_heading_preamble_sweep.py` output.

#### Population 1 re-derivation — the 8 single-line trigger families, post-C1/C2 fix

Own fresh regex (widened connector, independently written, not
imported from `il_trigger_grammar.py`), corpus-wide, ordinary articles
only, every hit resolved to its owning article and checked against
LIVE `extract_local_scope_definitions`: **5,497 occurrences, 5,414
captured, 83 missed (98.5%)** — a real improvement over cycle 2's
pre-fix 5,340/5,400 (98.9% of a SMALLER denominator; C1/C2 add real net
new capture even though my own wider/independent scan surfaces a
comparable-sized residual). Per-family breakdown and every miss (file +
article + term) is in this session's transcript above (script
`il_phaseC_qa3_i4_pop1_families.py`). Root-caused a representative
sample: some are Bug B instances (already counted above, e.g. `מסירה`/
`פקיד שומה`); some are measurement-only truncation from an embedded
gershayim WITHIN the term itself (e.g. `"רכיב המע"` for the real term
`"רכיב המע"מ"` — this is a pre-existing, ALREADY-DOCUMENTED limitation,
explicitly named by the Phase C Planner round 1 as a reason it rejected
one candidate fixture — not a new finding, corroborating it); one
(`חוק המכר (דירות)...` art.3ג/3ג1) looks like it may be touching a
FROZEN `sections.py` article-boundary parsing edge case (`3ג1`'s own
`@` heading marker appearing to remain inside `3ג`'s parsed body) —
flagged, NOT deep-dived (out of scope, frozen file, low materiality),
recorded as something I could NOT fully verify (see closing section).

#### Populations 2+3 — `::-`/`:-` list shapes, re-derived independently and ATTACKED per the manager's explicit request

**`::-` (double-colon): 5,928 terms / 5,285 captured / 643 missed
(89.2%).** **`:-` (single-colon): 1,671 terms / 1,021 captured / 650
missed (61.1%).** Both diverge sharply from QA cycle 2's `4,972/4,972`
and the manager's `1,107/1,107` — **I attacked the manager's number as
asked, and it does not reproduce.** Root-caused, not just re-measured:
- 23/73 single-`:-` miss-files and 66/161 `::-` miss-files overlap
  exactly with NEW Bug A (multi-term entries) above.
- A further chunk overlaps with NEW Bug C (heading-embedded preamble)
  above.
- The residual scope-split of what I DID capture is proportionally
  consistent with the manager's own claimed split (mine: single-`:-`
  captured scope = local 432/law-wide 234/siman 133/chelek 130/
  chapter 80/item 9/subsection 3, vs. the manager's local 465/law-wide
  260/siman 141/chelek 134/chapter 95/item 9/subsection 3 — same rank
  order, `item`/`subsection` match EXACTLY, everything else within
  ~15%) — strong evidence my sweep is measuring the SAME underlying
  mechanism correctly, just over a LARGER, more inclusive denominator
  (multi-term entries, heading-embedded preambles, and other structural
  variants the manager's simpler sweep did not reach), not a scanning
  bug inflating false "misses."
- I could NOT fully reconcile 100% of the gap within available time —
  honestly flagged, not hidden (see closing section). What I CAN state
  with confidence: the claimed **100% capture for both shapes does not
  hold** once the denominator is widened to structurally-identical
  entries the manager's own sweep under-counted; every miss I am
  reporting by name above (Bugs A/C) is independently, live,
  hand-verified — the parts of the gap I have NOT individually
  hand-verified are named as such, not asserted as confirmed misses.

#### Population 4 — M17 spelling-variant "measured zeros," spot-checked

Two independently spot-checked (own regex, not the shipped module's):
**`בהסכם זה` quote-first: 0** and **`בנוהל זה` quote-first: 0**, both
reproduce the round-3 table's claimed zeros exactly, corpus-wide.

#### An independent, genuinely new sweep that found NOTHING (reported per the brief)

Hunted for curly/typographic quote characters (U+201C/U+201D, `“”`)
used as the term-delimiting quote instead of straight `"` — a REAL
corpus characteristic (**636 raw occurrences** of a trigger+connector
immediately followed by `”`, e.g. `חוק איסור אלימות בספורט` art.9:
`בסעיף זה, ”תכנית היערכות” – מסמך...`). Traced this to `normalize.
_QUOTE_VARIANTS_RE = re.compile("[""״]")`, which ALREADY collapses
curly quotes (and gershayim) to `"` during `normalize_for_parsing` —
confirmed live: `extract_local_scope_definitions` on the normalized
body of the exact example above correctly captures `"תכנית היערכות"`.
**Zero real misses from this angle** — a clean negative result,
explaining why P-R10's "why isn't everything downstream already
broken" check matters: I nearly reported this as a headline finding
before checking normalization.

### Precision / P-R2 / D-Q1 — no NEW conflict found; one self-declared gap resolved clean

- **M16 exclusion list still holds, live.** Spot-checked `בתוספת זו`,
  `בפוליסה זו`, `בכלל זה` (3 of the 11 excluded phrases, incl. the
  false-friend) against real corpus preamble lines via
  `il_list_shape_scope.infer_scope` — all three still classify
  `"local"` (never wrongly promoted to `"law-wide"`).
- **M17 Group-1 connector-widening FP risk (the self-declared gap) —
  measured, ZERO risk.** For all 8 Group-1 phrases (`בתקנה זאת`,
  `בפסקה זאת`, `לענין/לעניין פסקה זאת`, `בתקנת משנה זאת`, `בפסקה משנה
  זו`, `לענין/לעניין פרט זה`), corpus-wide: the widened (space/colon/
  dash) connector produces **0 NEW matches beyond the comma-only form**
  for every single phrase — the widening is a complete no-op for this
  specific vocabulary corpus-wide, so there is no FP exposure to
  measure. Resolves the Developer's own honestly-flagged gap.
- **Citation guard still holds.** Corpus-wide, ALL IL rules combined,
  ordinary articles: 23,825 total captured terms, **0** citation-shaped
  (`^סעיף\s+\d+[א-ת]*$`) survivors — reconfirms cycles 1/2's finding.
- **C1 widening FP hunt** — relied on the Planner's own thorough
  42-sample hand-check (0 FPs) rather than re-doing it from scratch
  (proportionate effort given time spent on I4); corroborated
  indirectly via the citation-guard and M16/M17 spot-checks above
  finding nothing new.
- **No zero-miss-vs-zero-false-positive conflict to arbitrate this
  cycle** — every precision check above came back clean; the three new
  I4 bugs are pure recall gaps (silently dropped candidates), not
  precision trades, so nothing new for P-R2/D-Q1 to weigh.

### What I could NOT verify (honest gaps)

1. Did not hand-verify all 650/643 raw misses in Populations 2/3, nor
   all 83 in Population 1 — verified representative samples and the
   THREE new bugs' full populations (A/B/C, fully enumerated in
   scratchpad scripts), but the residual, not-yet-individually-
   root-caused portion of Populations 1-3's misses (roughly 83 - [Bug B
   overlap], and the Pop 2/3 misses not explained by Bugs A/C) is
   reported as a NUMBER with a methodology, not as an exhaustively
   named list — flagging this explicitly rather than implying full
   verification.
2. The `חוק המכר (דירות)...` art. `3ג`/`3ג1` anomaly (heading marker for
   `3ג1` appearing to remain inside `3ג`'s own parsed `.body`) was
   noticed but not investigated — touches the FROZEN `sections.py`,
   low materiality (one file), out of my mandate to fix, flagged for
   whoever owns that module next.
3. Did not re-verify Group A/B (cycle 1) or the punctuation-variant/
   swallow-bug fixes (C1/C2) beyond what Population 1's re-derivation
   already covers implicitly (they are the same 8 families).
4. Did not attempt to measure the ~80/132 Bug-B "other" grammar
   (`"X נקרא/נקראת בחוק זה 'term'"`, term-naming without a trigger-
   quote-dash structure) — noted as a residual, not sized.

### Suite numbers recap (all reproduced by me)

Backend: `4 failed, 829 passed, 18 warnings` (reproduced 3x). No
frontend/typecheck changes this cycle (Phase C touched
`backend/app/definition_links/rules/**` only) — not re-run, since
nothing in this cycle's diff touches frontend or non-IL backend code;
`I5`'s own backend-diff check above is the load-bearing evidence.
`contract_lint.sh 2026-08-04-defs-il`: `PASS 400`. I1 independent
re-run: `6133/6133 files, 0 failed, 128234 articles`, wall 24.8s, peak
65.6 MiB.

### Escalations (P-R2/D-Q1 — reporting, not deciding)

1. **I4 FAIL, absolute zero-miss bar, again.** Three structurally NEW
   bugs (A: multi-term list entries, 479/1,173 confirmed; B: no-dash-
   after-quote quote-first candidates, 132/6,364 generic population; C:
   heading-embedded preambles, 27/117 confirmed) plus large,
   independently-attacked residuals in the two headline list-shape
   populations (643/5,928 for `::-`, 650/1,671 for single-`:-` — both
   refuting the previously-claimed 100%). All three new bugs share the
   SAME already-proven `ScopeTriggerRule` mechanism (Bugs A/B are
   one-line fixes to already-shared helper functions — widen
   `ENTRY_TERM_DASH_RE` to the same multi-term parser C1 already built,
   and stop discarding a quote-first candidate when no split marker
   exists, treating "rest of clause" as the definition text instead);
   Bug C needs `RuleContext`/the rule signature to also receive the
   owning article's `.heading` (a small, additive seam extension, not a
   frozen-file edit). Recommending a Phase-D item bundling all three,
   not deciding scope myself.
2. **Pattern worth naming explicitly, not just the individual
   numbers:** this is the THIRD consecutive QA cycle in which an
   independent, trigger-word-agnostic structural sweep surfaces a
   headline-sized new miss class the prior round's fix cycle did not
   anticipate (cycle 1: Groups A/B; cycle 2: punctuation-variant +
   swallow-bug + the whole single-`:-` class; cycle 3: multi-term
   entries + no-dash-after-quote + heading-embedded preambles). Each
   round's fix has been real and net-positive (I1/I3/I5 stay solid,
   Population 1's capture rate improved), but the corpus's own grammar
   diversity appears to keep out-pacing each round's fix scope. Not
   deciding whether to keep iterating vs. accept a diminishing-returns
   stopping point myself — surfacing the pattern with data per P-R2/
   D-Q1 for the director/program manager to weigh.
3. No precision/recall conflict to arbitrate this cycle (see Precision
   section) — the self-declared M17 Group-1 gap resolved clean (0 FP
   risk found).

### Gate verdicts

**I1: PASS** (confirms 128,234, no regression post core-dispatch
merge). **I3: PASS**, both directions proven live end-to-end on two
fresh corpus laws, one specifically exercising the NEW C4+M16 path.
**I4: FAIL** — three new, structurally-independent, live-verified miss
classes (Bugs A/B/C) plus large, independently-reproduced residuals in
both list-shape populations that refute the previously-claimed 100%
capture. **I5: PASS**, fully reproduced, mechanical diff checks confirm
zero frozen-file/test edits. **Precision: PASS**, no new conflict, one
self-declared gap (M17 Group-1 FP exposure) measured and resolved
clean.

qa_cycles: 3.

---

---

## 2026-08-04 — Manager verdict on QA cycle 3: ACCEPTED; sprint stays qa-fail (cycle 3 of 5)

### Boundaries (mechanical, from its own worktree — M14 holding)

`git diff --name-only 4f95c4a..55ca5b5 -- backend/app` → **empty**;
`... -- backend/tests` → **empty**. Docs only. Merged `--no-ff`.
Post-merge, my own run: **`4 failed, 829 passed`**, `contract_lint` PASS.
Every Phase C handoff was verified the same way: the Planner's three
rounds (zero `backend/app`, zero pre-existing tests modified) and the
Developer's (zero frozen files, zero test/fixture files — its entire
change set is 12 files under `rules/**` plus the log).

### M18 — I was wrong, and the error is exactly the one P-R7 names

I measured the single-`:-` population post-fix at **1,107/1,107 captured
(100%)** and handed QA that number with an explicit instruction to attack
it rather than echo it. **QA refuted it: 61.1% on its own, larger
denominator.** QA is right and I am recording the root cause against
myself, because it is instructive.

My denominator enumerated entries with the regex `^"([^"]+)"\s*-\s*(.*)$`
— **the same single-term entry grammar the rule itself uses.** So a
multi-term entry line (`:- "t1", "t2" - def`) was invisible to my sweep
in precisely the way it is invisible to the rule: my probe and the code
under test shared a blind spot, so the probe could only ever return 100%.
That is P-R7's rule violated by the person quoting P-R7 in the brief.
Confirmed live with my own minimal probe after reading QA's finding:

```
:- "מונח א", "מונח ב" - הגדרה משותפת;   -> []      (multi-term, dropped whole)
:- "מונח ג" ו"מונח ד" - הגדרה משותפת;   -> []      (ו-joined, dropped whole)
:- "מונח ה" - הגדרה;                     -> [('מונח ה', 'law-wide')]  (control)
בסעיף זה, "מונח ו" כהגדרתו בחוק אחר.     -> []      (no dash after quote)
בסעיף זה, "מונח ז" - הגדרה.              -> [('מונח ז', 'local')]     (control)
```

**Binding for every future cycle of this sprint: a capture denominator
must be built from the ENTRY LINE (any `:-`/`::-` line, any
quote-bearing line), classified AFTER matching — never from the entry
GRAMMAR.** QA cycle 3's denominator is the reusable one; use it.

### What Phase C did deliver (measured, not claimed)

31 REDs green across C1 (punctuation widening, 7 families), C2 (additive
same-line-swallow workaround, frozen regex untouched), C3 (inline
`בפרט זה`), C4 (single-`:-` generalization incl. `פרשנות`-headed articles
without editing `sections.py`), M16 (law-wide scope vocabulary, applied
to the new rule AND the already-shipped `::-` rule), M17 (16 spelling
variants from a corpus-derived demonstrative audit). I3 now passes in
BOTH directions live — the under-reach direction is new this cycle and
is the director's scoped-assertion mandate actually proven, not assumed.

My own both-directions spot-check on the merged tree:

```
בחוק זה -    :- entries  -> law-wide      בתוספת זו - (excluded) -> local
בתקנות אלה - ::- entries -> law-wide      בכלל זה -   (false friend) -> local
בסעיף זה -   :- entries  -> local         בפרק זה -   -> chapter
two `לענין זה` triggers on ONE line       -> BOTH terms captured, both local
```

### M19 — Phase D scope (next cycle)

1. **Bugs A/B/C** from QA cycle 3, REDs first per the RED-provenance gate
   (none exists yet): (A) multi-term entry lines dropped whole — the
   largest, and it also invalidates part of the `::-` rule's own prior
   100% claim; (B) quote-first candidates with no dash after the quote;
   (C) preambles in the article's own heading.
2. **The E6 batch, now unblocked** by core's dispatch merge (all 7 rule
   kinds live): the 3 class-(d) prose-body tests + item 11. REDs for
   these already exist and are red. Note M-D3: declare any
   `scope_unit_kind` from measured Hebrew convention.
3. Named residuals carried, NOT silently folded: sub-part scope
   references defaulting to `"local"` (`בפרק משנה זה` ~110, `בתוספת זו`
   ~72, appendix/table/policy/formula families); enumerated multi-article
   ranges (`לענין הסעיפים X-Y`); multi-line `::`-continuation
   `definition_text` truncation (term identity unaffected).

### Escalation to the program manager — the pattern QA named, with my read

Three consecutive QA cycles, each finding a headline-sized NEW class, and
in every case the class was found by **widening the denominator**, not by
finding a defect in what was already measured. Cycle 1 found trigger
families; cycle 2 found the single-`:-` shape; cycle 3 found multi-term
entries, no-dash candidates, and heading preambles. Each new class is
smaller than the last, but "smaller" is not "none", and the director's
bar is absolute.

My read, offered as a concrete proposal rather than a complaint:
**iterating sweeps cannot terminate at zero, because each sweep's own
shape defines its blind spot** — that is the same failure my own M18
error demonstrates in miniature. The only construction that can support
the word "zero" is to invert the method: take the MAXIMAL
signal-agnostic denominator — every quoted-term occurrence in the corpus,
irrespective of trigger, marker, or entry shape — and classify every one
of them as captured or proven-not-a-definition. That is a far larger
population (order 10^5) and would be its own sprint, but it is the only
method whose completeness argument does not depend on having guessed the
right grammar. The director should decide between that and an
enumerated-residual acceptance; the panel should not pick for them.

Status stays **`qa-fail`, `qa_cycles: 3`** (valve at 5).

---

## 2026-08-05 — M19-EXT: Phase D spec under D-CERT (for program-manager sign-off BEFORE any Planner spawns)

D-CERT read verbatim at `main` `58162b2`. IL's certification folds into
Phase D after the known residual builds; M18 is program law for the
certification denominators. This entry is the spec the program manager
asked for. **No Planner spawned pending sign-off.**

### D-1 — known-buildable residual FIRST (certify against nothing you already know how to fix)

Two bundles, sequenced, RED-provenance gate binding on both.

**D-1a — QA cycle 3's three classes.** No REDs exist yet, so the Planner
authors them first: **(A)** multi-term entry lines dropped whole
(`:- "t1", "t2" - def` and the `ו`-joined form) — 479/1,173, the largest
and the one that also invalidates part of the `::-` rule's earlier "100%"
claim; **(B)** quote-first candidates with no dash after the quote
(`TRIGGER, "term" כהגדרתו [[ref]]`) — 132; **(C)** preambles living in the
article's own HEADING, never scanned by either list-shape rule — 117
terms / 27 runs. All three are rule-module work on the live path; no
frozen-file edit should be needed, and a claim that one IS needed
escalates rather than proceeding.

**D-1b — the E6 batch, now unblocked** (core dispatch merged; all 7 rule
kinds live). The 3 class-(d) prose-body sub-shapes + item 11's embedded
ad-hoc marker. **REDs already exist and are already red** — this bundle
goes straight to a Developer. Uses the definitions-SECTION path and
`EntrySplitterRule`/`TermClauseRule`/`HeadingRule`, a different dispatch
path from everything Phase C touched, which is exactly why it is a
separate bundle and not a Phase C addendum. Honor M-D3: declare any
`scope_unit_kind` from measured Hebrew convention, not by analogy to US.
Also now buildable and previously parked: סימן/חלק containment via
`StructuralUnitRule` (old E1) — needs NEW REDs, since the original was
never written on the stated grounds that the behavior was unobservable.
It is observable now.

Then **QA cycle 4** over D-1a+D-1b.

### D-2 — the certification proper, and why it must be its OWN sprint

**Denominator, measured by me today, not estimated.** Every gershayim-
delimited span in every article of all 6,133 files — **including
הגדרות-headed articles**, which every prior IL sweep excluded because the
dispatch path differs. That exclusion is precisely the kind of
signal-dependence D-CERT outlaws.

```
files 6,133 / articles 128,234
raw " characters            276,628
word-internal (abbreviation) 91,431   (33.1%)
delimiter-eligible           185,197  -> ~92,598 paired candidate spans
```

**~92,600 candidates** — confirms the director's 10^5 order with a real
figure.

**The IL-specific hazard, named up front:** Hebrew gershayim is also a
word-internal abbreviation marker (`תשע"א`, `עו"ד`, `הג"א`). A naive
`"([^"]+)"` pairing scan pairs one abbreviation's quote with the next
one's and manufactures tens of thousands of phantom spans. 33.1% of all
quote characters are word-internal. So cluster 1 of the certification is
mechanical and testable: *a gershayim immediately preceded AND followed
by a Hebrew letter with no intervening whitespace is word-internal and
cannot be a term delimiter.* That predicate is stated, falsifiable, and
disposes of ~91,431 quote characters before any judgment is applied.

**Claim structure (the part that makes this a certification rather than a
report).** Per the program manager: cluster + per-cluster proof, never
row-by-row prose — but the CLAIM is per-candidate. Concretely:
1. Every candidate row carries exactly one `cluster_id`.
2. Every cluster carries a **stated, testable predicate** (a committed
   function, not a sentence) and a bucket: captured / fixed /
   proven-not-a-definition / director-named residual.
3. **Mechanically asserted exhaustiveness and disjointness**: a committed
   test proves every one of the ~92,600 rows matches exactly one cluster
   predicate — zero unassigned, zero double-assigned. This is the
   backbone; without it "every candidate is classified" is narrative.
4. Each cluster's bucket assignment is backed by a hand-verified random
   sample with a **measured error rate**, not a clean bill.
5. The artifact is a committed script + manifest (predicates, counts,
   sample verdicts, seeds) that QA re-runs and diffs — reproducible, not
   prose. A certification nobody can re-execute certifies nothing.
6. **Fix loop INSIDE the certification**, per the program manager: when
   classification surfaces a new buildable class (expect this — it has
   happened in all three cycles so far), it goes REDs → build → re-certify
   the AFFECTED clusters, re-running the exhaustiveness assertion over the
   full population each time.

### The structural problem I have to raise: the 5-cycle valve

This sprint is at **`qa_cycles: 3` of 5**. D-1 consumes cycle 4. That
leaves ONE cycle for a certification the director's own ruling calls a
sprint in its own right — and my honest sizing is that D-2 is comparable
in effort to Phase A-C combined (~600-1,200 hand verifications across an
estimated 20-40 clusters, plus an inner fix loop). Running it on the last
valve cycle would force exactly the choice the valve exists to prevent:
ship thin or end `blocked` on a technicality.

**Proposal: split the sprints.** D-1 completes `2026-08-04-defs-il` (cycle
4, cycle 5 held in reserve for a bounce) and the sprint closes on its
original I1-I5 gates with an enumerated residual. The certification opens
as a NEW sprint — `2026-08-05-defs-il-certification` — with its own
5-cycle valve, its own gates (C1 denominator is signal-agnostic and
reproducible; C2 exhaustive+disjoint assignment; C3 per-cluster sampled
error rates; C4 fix loop closed; C5 artifact re-runs clean for QA), and a
fresh Planner/Developer/QA in the existing role worktrees. This is a
budget/scoping question above my level — flagging it rather than
quietly consuming the valve.

### Sequencing note

D-1a and D-1b are independent (different dispatch paths, different rule
kinds, disjoint file sets), so their Planners can run concurrently in
separate worktrees per M14. Their Developers must NOT — one writer per
worktree, and both bundles land rule modules in the same package.

---

## 2026-08-05 — M19-EXT APPROVED; D-1 Planners dispatched

Program manager signed off on the Phase D spec in full, incl. the sprint
split, and closed the budget question: D-CERT was presented to the
director with "roughly one additional sprint per track" as its stated
cost, so `2026-08-05-defs-il-certification` sits INSIDE the authorized
envelope rather than expanding it. Recorded at `main` `8c49498`.

**Confirmed:** D-1 (classes A/B/C + the E6 batch + the now-observable
old-E1 `StructuralUnitRule` containment) completes THIS sprint — cycle 4
runs it, **cycle 5 is held as the bounce reserve** — closing on the
original I1-I5 gates with an enumerated residual. Concurrent Planners,
serialized Developers, per the disjoint-paths analysis. The certification
sprint opens with its own valve and the five gates I named.

**Two program precedents set from this panel's work:** (1) the ~92,600
denominator INCLUDING הגדרות-headed articles is now the no-signal-
dependence standard the US certification will also be held to; (2) the
word-internal-gershayim predicate (Hebrew letter both sides, no
whitespace) is the falsifiable-mechanical form the whole classification
should take.

Dispatched concurrently in their own worktrees (M14): **D-1a** (plan3 /
`claude/defs-il-plan-d1a`) — REDs for classes A/B/C, incl. characterizing
the ~80% of class B that QA cycle 3 left uncharacterized. **D-1b** (plan4
/ `claude/defs-il-plan-d1b`) — job 1: REVALIDATE the 4 existing E6 REDs,
which were authored against a DEAD dispatch and may encode stale seam
assumptions (escalate, never edit); job 2: NEW both-directions
containment REDs for סימן/חלק, whose original "unobservable, so no test"
justification has now expired.

Certification contract to be drafted once D-1's Developers are running,
not before — one thing at a time through the remaining cycles.
## 2026-08-05 — Planner D-1b (Sonnet/high), worktree `defs-il-plan4`

Read the full contract (all items, especially 2b/5/11), this log's E6/E1
history, `## QA cycle 3`, M18, and `## 2026-08-05 — M19-EXT`, plus
`2026-08-04-defs-core-dispatch.md` and the seam spec through v2.7. Verified
baseline myself first: `backend/.venv/bin/pytest backend/tests -q` ->
`4 failed, 829 passed, 18 warnings` — exact match to the brief.

### Job 1 — revalidation of the 4 existing E6 REDs (per-test verdict)

All four re-run individually and read; for each I also ran a POSITIVE
CONTROL (a throwaway monkeypatched probe rule registered for `"IL"`,
never committed) proving the dispatch machinery genuinely fires on that
exact fixture, so the failure is "no rule registered" and not "the seam
itself can't reach this." **Verdict for all four: still correctly RED,
same failure mode as before core's dispatch merge (an empty result), now
CONFIRMED buildable rather than architecture-blocked. No stale
expectations found — nothing edited.**

1. `test_definition_links_il_missed_classes_live.py::
   test_class_d_prose_body_definitions_section_yields_zero_today` —
   `extract_definitions_from_section` on art.16's body (`חוק החברות
   הממשלתיות`) returns `[]` (confirmed live). Root cause: `baseline_
   blocks = extract._split_into_blocks(text)` requires a `:-` line to
   start ANY block; a marker-less prose body produces zero blocks, so the
   `TermClauseRule` union loop (`for block in all_blocks: ...`) never
   even executes — not a TermClauseRule gap, an EntrySplitterRule gap.
   Positive control: registered a probe `EntrySplitterRule` that returns
   `[text]` (whole body as one block) with NO other change — baseline's
   OWN `_parse_block` then correctly extracts `('דירקטור',
   'דירקטור מטעם המדינה בחברה ממשלתית.')` unaided. Failure: `assert 0 ==
   1` / `got []`.
2. `...::test_class_d_variant_double_colon_entry_list_under_a_trigger_
   preamble_is_captured` — same law family (`תקנות קרן גרמניה-ישראל`
   art.1, heading `הגדרות`), `::-`-marked entries. `[]` confirmed live
   (`_ENTRY_START_RE` only matches `:-`, not `::-`). Positive control:
   probe `EntrySplitterRule` recognizing `::-` as a block-start — baseline
   `_parse_block` then correctly extracts all 4 real terms, INCLUDING the
   multi-quote entry `"מס שבח מקרקעין" ו"זכות במקרקעין"` via the existing
   `_parse_terms_and_qualifier` multi-quote logic (no TermClauseRule
   needed either). Failure: `got []`.
3. `...::test_class_d_minimal_single_sentence_variant_is_captured` — same
   shape/root-cause as #1 (`צו פיקוח... (חמאה)` art.1, single sentence, no
   `:-`). Positive control: identical whole-body-as-block probe correctly
   extracts `('חמאה', 'חמאה רגילה בחבילה.')`. Failure: `got []`.
4. `test_definition_links_il_missed_classes_extended_live.py::
   test_class_c_adhoc_parenthetical_beparagraph_zo_inside_definitions_
   section_is_captured` — `חוק הבנקאות (שירות ללקוח)` art.1, `(בפסקה זו -
   חוק הדואר)` embedded inside the "גוף פיננסי" entry's OWN body.
   Confirmed live: 18 candidates extracted total, "גוף פיננסי" among them
   (baseline `:-` grammar unaffected), "חוק הדואר" absent. THIS one IS a
   genuine `TermClauseRule` gap (the embedded marker lives inside an
   already-existing block's body text, not a missing block) — positive
   control: a probe `TermClauseRule` scanning block text for `(בפסקה זו -
   X)` correctly produced `DefinitionCandidate(terms=('חוק הדואר',),
   ...)` when registered. Failure: `any(...) == False`.

No test's assertions, fixtures, or docstrings needed correction — every one
already documents (in its own prose, written before this session) exactly
the mechanism this session's positive controls just proved live. `git diff
--name-status` confirms zero edits to either file this session.

### Job 2 — old-E1 סימן/חלק structural-unit containment: new REDs

**Load-bearing claim, proven with a positive control (not inferred from
the dispatch-sprint merge):** `matcher._in_scope`'s generic branch +
`pipeline.py`'s `structural_units` population site
(`pipeline.py:212-228`) ARE genuinely live and CORRECT when given data.
Throwaway probe `backend/tests/integration/zzz_d1b_probe.py` (deleted
before this commit, never pushed) registered a fake IL `StructuralUnitRule`
hardcoding article->siman membership PLUS a fake `ScopeTriggerRule`
stamping a real `scope_value` (needed because the REAL, shipped
`il_siman_chelek_scope_triggers.py` always stamps `scope_value=None` — see
below), ran the real `ingest_wiki_law` + `run_definition_linking` against a
3-article synthetic law. Result: same-siman article got
`'Article 2 uses the definition of "מונח_בדיקה".'`; different-siman
article got nothing. Reproduced, stable.

**But — re-reading the contract's own item 2b (which this Planner was
directed to read) shows this is NOT a new finding, it is a CONFIRMATION,
with a more precise root cause, of what item 2b already said.** Item 2b:
"Containment is NOT achievable this sprint... it needs a core-owned edit
to `sections.py` (capture `heading_breadcrumbs`...) and `pipeline.py`
(consume `StructuralUnitRule`...), both frozen/off-limits to a family
panel." The dispatch sprint fixed the SECOND half (pipeline.py now DOES
consume `StructuralUnitRule` and populate `structural_units` — proven
above). **It did NOT fix the first half**, verified this session, live,
against the actual frozen files (read only, not edited):
- `StructuralUnitRule.derive` receives only `StructuralContext
  (article_number, heading_breadcrumbs)`. `heading_breadcrumbs` is
  hardcoded `()` at pipeline.py's one production call site
  (`structural_ctx = StructuralContext(article_number=art.number,
  heading_breadcrumbs=())`, pipeline.py:212) — the comment there says so
  explicitly and invites exactly this escalation: "a family panel's own
  rule is free to derive purely from `article_number`, or escalate for a
  breadcrumb column when it actually needs one." Deriving סימן/חלק
  membership from `article_number` alone is not possible (article numbers
  don't encode their enclosing סימן/חלק).
- The chapter-scope precedent this Planner was told to look at
  (`il_chapter_scope_triggers.py` stamps `source_chapter=ctx.chapter`)
  works ONLY because `RuleContext.chapter` IS populated, from `sections.
  py`'s OWN `==`-depth chapter tracking. `RuleContext` has no equivalent
  field for סימן/חלק, and `sections.py` (frozen, read only) still
  discards every 3+-equals heading's own text
  (`_HEADING_BREAK_RE` matches any `={2,}` break and ends the article's
  body scope for all of them, but `current_chapter` is updated ONLY when
  `len(break_match.group(1)) == 2` — unchanged since v1, confirmed by
  direct read this session).
- `ingest_wiki_law` persists only `.number`/`.heading`/`.chapter` onto the
  ORM `Article` (confirmed by direct read) — no trace of any enclosing
  סימן/חלק reaches the database at all, so there is nothing for
  `pipeline.py` to thread into `StructuralContext` even if it wanted to.

**Conclusion: neither side of a fix (stamping a real `scope_value` on the
`ScopeTriggerRule` side, or stamping a matching `ScopeUnit` on the
`StructuralUnitRule` side) has a live data source today.** This is
rule-module-UNREACHABLE, unlike D-1a's three bugs — it needs frozen-file
work (`sections.py` to capture full-depth heading breadcrumbs instead of
discarding anything past 2 equals-signs; `pipeline.py` to thread real
breadcrumbs into `StructuralContext`; very likely a new persisted column
on `models.article.Article`). M19-EXT's phrasing ("It is observable
now... needs NEW REDs") is right about the consumption machinery (proven
above) but does not on its own convey that the DATA gap item 2b named is
still standing — a Developer reading only M19-EXT could reasonably attempt
an unauthorized frozen-file edit or a fragile article_number-based hack.
Flagging this explicitly rather than letting it surface downstream.

**Real corpus complication found while building the fixtures below,
recorded per M-D3 ("measured convention, not analogy"):** חלק nesting
depth is NOT uniform corpus-wide. Most laws nest חלק ABOVE סימן; `תקנות
המשקלות והמידות` nests `==== חלק N ====` (4 equals) INSIDE `=== סימן
... ===` (3 equals) inside `== פרק ... ==` (2 equals) — the reverse. Any
future breadcrumb-capture fix must record full depth-ordered breadcrumbs,
not assume a fixed סימן/חלק ordering.

**New REDs (2, both directions each, combined into one assertion block per
axis — see the file's own docstring for why: following the Phase C
Planner's own established, manager-accepted precedent (round 2's M16
entry), a standalone non-leakage assertion would be VACUOUSLY true today
since nothing links anywhere yet; combining keeps each test genuinely RED
for the real reason while still pinning non-leakage as part of "green"):**

- `backend/tests/integration/test_definition_links_il_siman_chelek_
  containment_live.py::
  test_besiman_zeh_scoped_definition_containment_holds_in_both_
  directions_live` — fixture `חוק לקידום תשתיות לאומיות_siman_
  containment_excerpt.wiki` (real law, articles 8/9/22, non-adjacent
  assembly, every span independently byte-verified a literal substring of
  the source file, method identical to Phase C round 2's
  `il_phaseC_plan_m16_multi_fixture_builder.py`). Article 8 (סימן א')
  defines `"קו תשתית שאינו ממופה"`; article 9 (SAME סימן א') genuinely
  uses it; article 22 (סימן ב', a DIFFERENT unit) genuinely uses it too
  while explicitly stating its own סימן's rules don't apply to it — real
  corpus prose, not authored. Live failure tail (reproduced):
  `AssertionError: expected article 9 (same סימן א' as the defining
  article 8) to get a USES_DEFINITION edge for the genuine mention of "קו
  תשתית שאינו ממופה" in its own body; got []`. (The capture-only asserts —
  one Definition row, `scope == "siman"` — pass today; only containment is
  RED, confirming item 2b's capture/containment split is still accurate.)
- `...::test_bechelek_zeh_scoped_definition_containment_holds_in_both_
  directions_live` — fixture `תקנות המשקלות והמידות_chelek_containment_
  excerpt.wiki` (articles 47/72/73, same byte-verification method).
  Article 72 (פרק ה'>סימן ג'>חלק 1) defines `"בקרה מטרולוגית"` via a
  wikilink-aliased trigger `[[סימן משנה זה|בחלק זה]]` (display text
  resolves to `בחלק זה` after `strip_wikilinks`, confirmed live); article
  73 (SAME חלק 1) genuinely uses the construct-state surface variant
  "הבקרה המטרולוגית" (confirmed live via `matcher.find_term_uses` — one
  hit); article 47 (a different פרק AND סימן AND חלק entirely) genuinely
  uses the bare term. Live failure tail (reproduced): `AssertionError:
  expected article 73 (same חלק 1 as the defining article 72) to get a
  USES_DEFINITION edge for its genuine (construct-state) mention of "בקרה
  מטרולוגית"; got []`.

Full suite after adding both: `6 failed, 829 passed, 18 warnings` (the
same 4 Job-1 tests + these 2 new ones; 829 unchanged, confirming zero
regressions and zero existing tests touched).
`bash scripts/contract_lint.sh 2026-08-04-defs-il` -> `PASS 398`.
`git diff --name-status HEAD -- backend/app` -> empty (zero frozen-file
edits, zero production code — Planner-only, as required).

### Honest gaps

1. Did not attempt to build (or even sketch) the frozen-file fix itself —
   out of scope for a Planner, and per this sprint's own discipline a
   Developer must not attempt it either without the manager authorizing a
   scoped frozen-file change (same posture as D-1a's "a claim that one IS
   needed escalates rather than proceeding").
2. Did not survey the WHOLE corpus for every חלק-nesting-depth variant
   beyond the one real complication found while building the fixture
   above (`תקנות המשקלות והמידות`'s reversed nesting) — flagged as a
   measured data point for whoever eventually designs the breadcrumb
   capture, not claimed as an exhaustive census.
3. Did not re-verify Group A/B/precision REDs from earlier phases — out of
   this session's Job 1/Job 2 scope, untouched.

### Git discipline (M14)

Worktree `defs-il-plan4` only. New files only (`git status --short` shows
2 new fixtures + 1 new test file, plus this log edit); `git diff --name-
status HEAD -- backend/app` empty throughout. Throwaway probe file created
and deleted within this session, never staged, never pushed — same
discipline as prior QA cycles' own throwaway probes.

---

## 2026-08-05 — M20: D-1b ACCEPTED, and it corrects M19-EXT (mine). ESCALATION to core.

### Boundaries (mechanical)

`git diff --name-only 2e6cfdb..bc54e1a -- backend/app` → **empty**; no
existing test edited. 3 additions + append-only log. Both fixtures
independently byte-verified BY ME: these are non-contiguous multi-article
excerpts, so the contiguous-substring check is the wrong shape — checked
line-wise instead, **12/12 and 48/48 non-blank lines verbatim in source,
zero not found.** Merged (log conflict was two concurrent appends; both
kept in order). Post-merge, my own run: **`6 failed, 829 passed`**, lint
PASS 398.

### Job 1 — the four E6 REDs are still correctly RED, and now have exact root causes

D-1b did what I asked and did not assume: it re-ran each and registered
throwaway positive-control probe rules (never committed) to prove the
specific dispatch path fires. Result — all four still fail for the right
reason, **and the root causes are now precise enough to hand a Developer**:
three of them (`class_d` prose-body, `::-` variant, minimal single
sentence) are a missing **`EntrySplitterRule`**, NOT `TermClauseRule` —
baseline `_split_into_blocks` needs a `:-` line to produce ANY block, so a
marker-less prose body yields zero blocks and the registered-rule loop
never runs; once a probe splitter hands over the body, the EXISTING
baseline `_parse_block` extracts the terms unaided. The fourth (item 11's
embedded `(בפסקה זו - X)`) is a genuine **`TermClauseRule`** gap. That is a
materially better spec than "implement class (d)".

### M20 — I was wrong in M19-EXT about סימן/חלק containment

I wrote that old-E1 containment is "now observable" and scoped it into
D-1 as panel-buildable. **Half right, and the wrong half matters.** The
CONSUMPTION machinery is genuinely live (D-1b proved it end-to-end with a
probe `StructuralUnitRule`, not by inferring it from core's merge — the
standard I asked for). But there is still **no live DATA SOURCE**, and I
verified both halves myself rather than taking the report's word:

```
pipeline.py:212  StructuralContext(article_number=art.number, heading_breadcrumbs=())
sections.py:138  if len(break_match.group(1)) == 2:      # only 2-equals (chapter) kept
```

So breadcrumbs are hardcoded empty at the single call site, and 3+-equals
(סימן/חלק) heading text is still discarded at parse time. Both files are
FROZEN. No family-panel rule module can close this — a rule can only
derive from `article_number`, which cannot express סימן membership.

**This is exactly the escalation core itself anticipated.** `pipeline.py`'s
own comment at the call site: a family panel "is free to derive purely
from `article_number`, or **escalate for a breadcrumb column when it
actually needs one**." We actually need one now.

**ESCALATION to the program manager → core:** סימן/חלק containment needs a
persisted above-article breadcrumb source (core's own suggested shape: a
breadcrumb column on the ORM `Article`, plus lifting `sections.py`'s
2-equals gate to capture deeper heading levels). Two committed REDs now
exist and are correctly red, so whoever builds it has its acceptance test
already written — that is the one thing this panel could usefully do here.

### Consequence for D-1's scope (correcting my own plan)

- **D-1b Developer bundle = the 4 E6 tests only** (buildable now, with the
  splitter/clause split above). The 2 containment REDs are **blocked on
  core**, stay red, and become a named enumerated residual for the
  sprint's close — not a Developer target.
- D-1a (classes A/B/C) is unaffected and still buildable.

### A real finding worth carrying to whoever builds breadcrumbs

חלק nesting depth is **not uniform corpus-wide**: `תקנות המשקלות והמידות`
nests חלק INSIDE סימן, reversed from the usual convention. A breadcrumb
design that assumes a fixed level→kind mapping will be wrong on real data.
This is an M-D3-style "measure the convention, don't assume it" finding.
## 2026-08-05 — D-1a Planner (Sonnet/high): RED tests for QA cycle 3 classes A/B/C

Worktree `/Users/nerya/LexGraph-wt/defs-il-plan3`, branch
`claude/defs-il-plan-d1a`, off `origin/claude/defs-il` @ `2e6cfdb`
(verified at session start: `git log --oneline -3` matched, `git status
--short` clean, `import app` resolved to this worktree). Baseline
reproduced: `4 failed, 829 passed` (the E6-held set, untouched —
sibling D-1b's territory). Read the contract, QA cycle 3, M18, and
M19-EXT before starting. Note for the manager: `origin/claude/defs-il`
has since advanced to `462e93f` ("M20 — D-1b accepted..."), one commit
past this branch's fork point — not rebased onto it this session (out of
my mandate; flagging so the merge accounts for it).

### Class A — multi-term list entries dropped whole — RED committed

Root cause confirmed live (M4): `il_list_shape_scope.ENTRY_TERM_DASH_RE`
matches only a single quoted term; both list-shape rules share it.
Independent denominator re-derivation (M18-compliant — entry-line-based,
classified AFTER matching; P-R7-compliant — reuses
`il_trigger_grammar._find_split_marker`/`_QUOTE_RE`, a DIFFERENT helper
than the buggy one), ordinary (non-הגדרות-heading) articles only, own
script (`il_d1a_classA_sweep.py`, scratchpad): first pass 549/1336
lines/terms found unfiltered; after excluding (a) entries with no real
split marker at all (a different phenomenon, not this class) and (b) a
gershayim-in-term false-split guard (zero-width adjacency between two
"quoted spans" — the SAME already-documented, pre-existing limitation
this sprint's own QA cycle 3 named for `"רכיב המע"` truncation, not a new
finding), settled at **395 multi-term entry lines / 975 terms found; 392
lines / 963 terms confirmed missing from live `extract_local_scope_
definitions`; 207 unique files**. Lower than QA cycle 3's own 479/1,173/
239 (my gap-validation is stricter — requires an explicit `,`/`ו`/`או`
separator with no zero-width adjacency), same order of magnitude, same
class, cross-validated: my own real named examples (חוק אזורים חופשיים
לייצור בישראל art.23א, חוק ביטוח בריאות ממלכתי art.21ד, חוק הביטוח
הלאומי art.295א, חוק הבנקאות (שירות ללקוח) art.7א) match QA's own list
exactly. Separator breakdown: comma-only 83, vav-only 203, mixed 72 (both
"two real sub-shapes" the brief named are real and independently
confirmed, plus the naturally-occurring mixed comma+vav construction).

**FP exposure (P-R2/D-Q1):** hand-read the FULL 392-line confirmed-
missing dump (not a sample) — every entry has genuine defining prose
after its split marker; zero false positives. Structural argument: the
multi-term grammar is a superset of the already-shipped, already-
precision-proven single-term grammar (N>=2 quoted spans separated by a
real separator immediately before the SAME trusted split marker) — more
constrained, not less, so it cannot admit anything the single-term
grammar's own precision argument doesn't already cover.

**RED tests (3, node-ids):**
`backend/tests/integration/test_definition_links_il_phase_d1a_abc_live.py::test_class_a_single_colon_comma_separated_multiterm_entry_is_currently_missed`
(fixture `חוק הנהיגה הספורטיבית_art4_excerpt.wiki`, single-colon, pure
comma, TWO multi-term entries in one block + 3 single-term sibling
controls asserted captured);
`::test_class_a_double_colon_vav_joined_multiterm_entry_is_currently_missed`
(fixture `חוק ביטוח בריאות ממלכתי_art21ד_excerpt.wiki`, double-colon,
pure ו-joined);
`::test_class_a_double_colon_mixed_comma_and_vav_multiterm_entry_is_currently_missed`
(fixture `חוק אזורים חופשיים לייצור בישראל_art23א_excerpt.wiki`,
double-colon, mixed comma+ו, the exact real example QA cycle 3's log
names, sibling single-term entries "המעביר"/"הנעבר" asserted captured as
controls). All 7 vendored fixtures programmatically extracted (Python
line-slice) and byte-verified (`excerpt in source_text`) immediately
before writing the test file. Live re-confirmation output (representative):

```
:- "מונח א", "מונח ב" - הגדרה משותפת;   (after a בחוק זה - preamble) -> []
:- "מונח ג" ו"מונח ד" - הגדרה משותפת;   (after a בחוק זה - preamble) -> []
:- "מונח ה" - הגדרה;                     (after a בחוק זה - preamble) -> [('מונח ה','law-wide')]
```
reproduces the manager's own M18 minimal probe exactly (own venv, own run).

### Class B — quote-first candidates with no split marker — RED committed

Root cause confirmed live: `il_trigger_grammar.extract_quote_first_
candidates` discards the whole candidate (`continue`) when
`_find_split_marker` returns `-1`. Confirmed the ROOT case verbatim:
`extract_quote_first_candidates('לענין זה - "מסירה" כמשמעותה בסעיף 8
לחוק המכר...', trig, scope="local")` -> `[]`, matching `חוק מס ערך מוסף`
art.22 live via the full profile chain.

**Denominator (P-R7):** two independent sweeps, own scripts
(`il_d1a_classB_sweep.py`, `il_d1a_classB_sweep_prodtriggers.py`,
scratchpad). (1) A generic demonstrative-anchored scan (1-3 Hebrew words
+ זה/זו/זאת/אלה/אלו + connector + quote, independent of any curated
trigger list, mirroring M17's own method): 6,534 candidates, 147 no
split-marker, 139 confirmed missing — order-of-magnitude match to QA's
own 6,364/132. Hand-reading this raw list surfaced two important P-R10
findings: (a) `החוק הפלילי הירדני` art.164 "מהומה" and a "נוסח זה"
disclaimer-text instance are BOTH false candidates of my own generic
probe, not real production risks — neither "התקהלות זו" nor "בנוסח זה"
is an actually-registered trigger phrase, so no real rule would ever
match them; (b) `חוק החמרים המסוכנים` art.16ג "קצין משטרה"/"קצין צה"ל"
(one of QA's own cited Bug-B examples) does NOT actually demonstrate
Bug B on inspection — it HAS a real dash; the miss is the SAME
already-documented, pre-existing embedded-gershayim-in-term limitation
(`קצין צה"ל`'s own internal gershayim breaks `_find_split_marker`'s
quote-parity tracking), not an absent marker. Flagging this as a
correction to QA cycle 3's own example attribution, not a new finding.
(2) A production-trigger-scoped re-derivation (collected every actual
`_TRIGGER_RE`-shaped pattern from all 8 `il_*_scope_triggers.py` modules
that build on `extract_quote_first_candidates`, 20 distinct regexes):
**103 real production-trigger quote-first matches have no split marker;
100 confirmed missing from live capture** — the decision-relevant,
stricter number.

**Characterization of QA's unexplained ~80% (this Planner's own work,
per the brief):** two real sub-shapes, both live-confirmed:
(i) the clean reference shape, `TRIGGER, "term" כהגדרתו/כמשמעותה
[[citation]].` (QA's ~20%, e.g. "מסירة", `חוק זכויות נפגעי עבירה`
art.1 "אחראי על קטין או חסר ישע");
(ii) a plain LOCAL-defining continuation with no dash and no reference
word at all — `TRIGGER, "term" <לרבות/למעט ... defining text>;` — the
defining clause uses a Hebrew inclusion/exclusion verb (`לרבות`=
"includes", `למעט`="excludes") directly after the quote. Live-confirmed
twice independently: `חוק התקנים` art.13 "מצרך" (`... "מצרך" לרבות
האריזה...`) and `פקודת מס הכנסה` art.135 "פקיד שומה" (`...ולענין זה,
"פקיד שומה" למעט עוזר פקיד שומה...`), both -> `[]` live, both confirmed
`_find_split_marker` -> `(-1, 0)` genuinely (not a gershayim confound —
checked directly).

**FP exposure (P-R2/D-Q1):** hand-read all 60 printed examples of the
103 production-trigger no-marker set (capped for output length, not for
verification — the summary counts above are exhaustive). Two named,
benign risk shapes, both term-identity-safe: (1) ~8% (5/60, extrapolates
to ~8/100) have a near-empty "rest of clause" (bare `.`/`);`/`).`) under
a naive "grab rest of clause as definition_text" fix — e.g. `חוק לימוד
חובה` art.2's "X נקרא בחוק זה 'term'" naming construct, where the TERM is
genuinely real (the law does name that concept) but its defining prose
sits BEFORE the quote, not after, so `definition_text` would degenerate
to punctuation only — a `definition_text` QUALITY gap, term identity
unaffected, the same accepted-limitation class as this sprint's own
documented multi-line `::`-continuation truncation residual, not a false
capture. (2) A handful of `(TRIGGER, "term")`-parenthetical-alias
instances (e.g. `חוק לעידוד השקעות הון` arts.3/4, "הפקודה") leave a
stray leading `)` in `definition_text` — same formatting-artifact class,
not a false capture (a `(hereinafter: "X")` alias IS a legitimate
definition, the same shape this sprint's own `(TRIGGER - term)` ad-hoc
mechanism already treats as definitional). No genuinely non-definitional
term found in the sample.

**RED tests (2, node-ids):**
`::test_class_b_reference_shape_no_dash_after_quote_is_currently_missed`
(fixture `חוק מס ערך מוסף_art22_excerpt.wiki`, the manager's own root
example, "מסירה");
`::test_class_b_plain_continuation_shape_no_dash_after_quote_is_currently_missed`
(fixture `חוק התקנים_art13_excerpt.wiki`, "מצרך"; the "פקיד שומה"
instance cited in the docstring as a second live-reconfirmed occurrence,
not separately vendored, per this sprint's established "smallest of
several instances" fixture convention).

### Class C — preambles living in the article's own heading — RED committed

Root cause confirmed by direct reads of all three touch points: neither
`registry.RuleContext` (article_number/chapter/unit_path only), nor
`HebrewProfile.extract_local_scope_definitions`'s signature (`profiles.
py`, FROZEN, `article_body, *, article_number, chapter=None` — no
heading param), nor its sole caller in `pipeline.py` (FROZEN, `profile.
extract_local_scope_definitions(matcher_article.body, article_number=
art.number, chapter=art.chapter)` — heading never passed) ever threads
the owning article's `.heading` text to a `ScopeTriggerRule`.

**Feasibility independently verified live (M4/P-R10 — the D-1a spec
asserts "no frozen-file edit should be needed" and a contrary claim
escalates, so this was checked, not trusted):** a throwaway, uncommitted
probe registered a NEW `registry.HeadingRule` (`registry.py` is NOT
frozen) whose `matches` callable recognizes a heading ending in a bare
`-` and whose `body_confirms` callable checks the body's first line is
`:-`/`::-`-marked. Registering it and re-running the REAL `אכرزת גנים
לאומיים` article 8 fixture: `profile.is_definitions_heading` flips
`False` -> `True`; `profile.extract_definitions_from_section` (the
ALREADY-correct, multi-term-safe definitions-section path) then captures
all 10 real terms. Confirms the class is reachable via a NEW rule-module-
only file, zero frozen-file edits — matching the D-1a spec's claim,
independently proven rather than assumed. **Open gap, not resolved
here:** `determine_scope` reads BODY text only, so a heading-only trigger
like `בתוספת זו` is invisible to it; the probe's `determine_scope`
returned `"law-wide"` by unconditional default — likely an over-claim for
a schedule/appendix sub-part (mirrors M16's own reasoning for excluding
`בתוספת זו` from the law-wide vocabulary). Flagged for the Developer/QA;
my tests assert CAPTURE only, never a specific `scope` value, for this
class.

**Denominator:** reused QA cycle 3's own count (27 runs / 24 files / 117
terms) — did not re-derive independently this session (time-boxed;
flagged as a gap below). Two real, independent fixtures instead, to
demonstrate the class recurs across different documents/trigger phrases
rather than re-deriving the corpus-wide count.

**RED tests (2, node-ids):**
`::test_class_c_schedule_heading_embedded_preamble_is_currently_missed`
(fixture `אכרזת גנים לאומיים_art8_excerpt.wiki`, heading `(תיקון: תש"ף) :
[[בתוספת זו]] -`, 10 terms, all asserted captured);
`::test_class_c_ordinary_heading_embedded_preamble_is_currently_missed`
(fixture `הכרזה מס' 3 לוחמים בלתי חוקיים_art1_excerpt.wiki`, heading
`(תיקון: תשפ"ד) : לעניין הכרזה זו -`, a non-schedule document/trigger, 5
terms).

### Suite numbers, contract lint, honest gaps

`backend/.venv/bin/pytest backend/tests -q` -> **`11 failed, 829 passed,
18 warnings in 38.94s`** (the pre-existing 4 E6-held failures, untouched,
+ this session's 7 new REDs; 829 passed unchanged, zero existing test
edited — `git status --short` at commit time showed only 8 new/untracked
files). `bash scripts/contract_lint.sh 2026-08-04-defs-il` -> **PASS
398** (contract file itself untouched this session). `git diff
--name-status` against this branch's own fork point (`2e6cfdb`) is 8 `A`
entries, nothing else; a diff against the CURRENT `origin/claude/defs-il`
tip (`462e93f`, one commit ahead of this branch's fork point — D-1b's
work landed there since) additionally shows 2 `D` fixture entries + 1 `D`
test file belonging to D-1b's own prior work, not touched by this
session — noted for the manager's merge, not a finding of mine.

**Honest gaps:**
1. Class A's denominator is my own conservative re-derivation (392/963/
   207), not QA's exact 479/1,173/239 — both measure the same real class
   via different (both P-R7-compliant) gap-validation strictness; did not
   reconcile the exact numeric gap between the two methodologies.
2. Class B's characterization sample is thorough (60/100 production-
   trigger matches hand-read in full, all named examples individually
   verified) but not literally 100/100.
3. Class C's denominator was NOT independently re-derived this session
   (reused QA's 27/24/117 as-is) — two real, independent fixtures stand
   in for a fresh corpus-wide sweep; if the manager wants an independent
   re-derivation before Developer handoff, that is still open.
4. Did not rebase onto the current `origin/claude/defs-il` tip
   (`462e93f`, D-1b's acceptance/correction of M19-EXT re: סימן/חלק) —
   out of this Planner's mandate this session; flagged for the merge.
5. Class C's `determine_scope` gap (heading-only triggers invisible to
   body-only scope inference, likely defaulting to an over-claiming
   `"law-wide"`) is named but not resolved — a genuine open design
   question for whoever implements, not decided here.

Status: RED committed for all three classes (A/B/C), none impossible,
none escalated. Ready for Phase D Developer handoff pending manager
review.

---

## 2026-08-05 — M21: D-1a ACCEPTED; D-1 planning complete; Developers are the next step

### Boundaries (mechanical)

`git diff --name-only 2e6cfdb..333c467 -- backend/app` → **empty**; zero
existing tests edited. 7 fixtures + 1 test file + append-only log.
**All 7 fixtures byte-verified BY ME**; the one that failed my first pass
(`הכרזה מס' 3 ...`) was my own filename shorthand, not a defect — an
exhaustive corpus scan found every one of its 6 lines verbatim in
`הכרזה מס' 3 על שינויים בתחולת חוק כליאתם של לוחמים בלתי חוקיים.wiki`.

**D-1a's flagged merge worry is resolved: unfounded.** It saw D-1b's
files as `D` when diffing against a tip that had moved, and correctly
flagged rather than acting. A real `--no-ff` merge (not a reset) preserved
both; verified after merging — both test files and both containment
fixtures are present, and both Planners' REDs run. Log conflicts on both
merges were two concurrent appends; both kept in order.

Suite now: **`13 failed, 829 passed`** = 4 E6-held + 2 סימן/חלק
containment (core-blocked per M20) + 7 D-1a REDs. Lint PASS 398.

### What D-1a delivered beyond the ask

- **Class B's unexplained ~80% is now characterized** (the thing I
  specifically asked for): a quoted term followed by a Hebrew
  inclusion/exclusion verb (`לרבות`/`למעט`) with NO dash anywhere —
  live-confirmed on two real laws.
- **A P-R10 catch against QA cycle 3:** one of QA's own cited Bug-B
  examples (`קצין משטרה`/`קצין צה"ל`) does NOT demonstrate Bug B — it has
  a real dash; its miss is the separate, already-documented embedded-
  gershayim limitation. Corrected in the log. Good discipline: it checked
  a cited example instead of inheriting it.
- **Class C feasibility proven, not assumed** — a throwaway `HeadingRule`
  probe showed the class is reachable from a rule-module-only file with
  zero frozen-file edits.

### M21 — a finding of my own for the D-1a Developer, from D-1a's own fixture

D-1a's class-C fixture opens `@ 1. (תיקון: תשפ"ד) : לעניין הכרזה זו -`.
That is an INSTRUMENT word — and the M16 law-wide vocabulary in
`il_trigger_grammar.py` contains `אכרזה זו` (aleph) but **not** `הכרזה זו`
(heh). Two different Hebrew spellings of "proclamation"; only one is
covered. Measured corpus-wide by me just now:

```
באכרזה זו        46 occurrences / 46 files   IN the law-wide table
לעניין הכרזה זו   3 occurrences /  3 files   NOT in the table
בהכרזה זו / לענין הכרזה זו / לעניין אכרזה זו   0 (measured zeros)
```

Small, but under an absolute bar a measured 3 is not zero, and the fix is
one vocabulary entry. **Fold `לעניין/לענין הכרזה זו` into the law-wide
table as part of D-1a's build** — and note this is exactly the M17
spelling-variant class recurring, which is itself evidence for why the
certification (D-2) is the right closing method rather than another
variant hunt.

**Related open question D-1a raised and did NOT resolve** (correctly —
it is a design call): a naive class-C fix defaults heading-only-triggered
definitions to `"law-wide"`, because `determine_scope` reads the BODY
only. That is a plausible over-claim in the M16 direction. The Developer
must decide deliberately and QA must attack it; do not let it default
silently.

### Next step: D-1 Developers (serialized, per the disjoint-paths analysis)

- **D-1a bundle** — classes A/B/C, 7 REDs, plus the `הכרזה` vocabulary
  entry above. Buildable, rule-module-only.
- **D-1b bundle** — the 4 E6 tests ONLY, with D-1b's precise split: three
  need an **`EntrySplitterRule`** (baseline `_split_into_blocks` yields
  zero blocks for a marker-less prose body, so the registered-rule loop
  never runs), one needs a **`TermClauseRule`**. The 2 סימן/חלק
  containment REDs are **core-blocked (M20)** and stay red as an
  enumerated residual — NOT a Developer target.
- Both bundles land rule modules in the same package, so their Developers
  must NOT run concurrently (one writer per worktree, M14). Worktrees
  `defs-il-dev3` (exists, venv built) and one more to create.
- Then **QA cycle 4**; cycle 5 stays the bounce reserve.

---

## 2026-08-05 — M22: phase-3 manager re-verification of inherited state; THREE corrections to the record

Phase-2 predecessor clean-exited after M21. Per program law I re-verified
every inherited claim I intend to build on with my own positive controls,
in the `defs-il` worktree's OWN venv (`import app` ->
`/Users/nerya/LexGraph-wt/defs-il/backend/app`, confirmed), rather than
taking the log's word.

### Inherited state — CONFIRMED as stated

- `claude/defs-il` @ `64932d7`, clean, matches `origin`. Worktree git
  email is the noreply address.
- **Suite: `13 failed, 829 passed` — reproduced exactly**, and the 13
  failing node-ids are exactly the enumerated set: 7 D-1a REDs (3 class A
  + 2 class B + 2 class C), 4 E6 REDs, 2 סימן/חלק containment REDs.
  Nothing extra, nothing missing.
- `bash scripts/contract_lint.sh 2026-08-04-defs-il` -> PASS 398.
- **M20's core-block, re-verified by direct read of the frozen files**
  (not inferred): `pipeline.py:212` hardcodes
  `StructuralContext(article_number=art.number, heading_breadcrumbs=())`;
  `sections.py:138` still gates on `len(break_match.group(1)) == 2`. Both
  halves of M20 stand. The 2 containment REDs remain core-blocked and are
  NOT in either Developer bundle.
- All 8 rule kinds are present in `registry.py` (285 lines, under the
  300-line style gate), including `HeadingRule`/`EntrySplitterRule`/
  `TermClauseRule`.

### My own positive controls (throwaway, scratchpad only, never committed)

1. **D-1b's `EntrySplitterRule` root cause — CONFIRMED.** On the real
   `חוק החברות הממשלתיות` art.16 fixture body: baseline
   `extract._split_into_blocks` -> `[]`, profile section path -> `[]`.
   Registering ONE probe `EntrySplitterRule(jurisdiction_codes=("IL",),
   split=lambda t: [t])` and changing nothing else -> baseline's own
   `_parse_block` extracts `('דירקטור', 'דירקטור מטעם המדינה בחברה
   ממשלתית....')` unaided. The gap is the splitter, not the clause parser,
   exactly as D-1b said.
2. **D-1a's class-C `HeadingRule` feasibility — CONFIRMED.** On
   `אכרזת גנים לאומיים` art.8 (heading `@ 8. (תיקון: תש"ף) :
   [[בתוספת זו]] -`): baseline `is_definitions_heading` -> `False`;
   after registering one probe `HeadingRule`, -> `True`, and the section
   path captures **10 terms, 10 unique** (matching D-1a's claimed 10 —
   my first run printed 11 with `תמצית` doubled, which was MY probe
   splitter from control 1 leaking into the same process, not a product
   defect; isolated re-run gives a clean 10). Zero frozen-file edits.
3. **The class-C scope over-claim — CONFIRMED LIVE, first-hand.**
   `determine_scope(body)` on that same article returns **`'law-wide'`**.
   The article's trigger is `בתוספת זו` (a SCHEDULE), so a naive class-C
   fix would publish a schedule-local definition as law-wide. This is the
   deliberate design decision I am handing the D-1a Developer.
4. **D-1a's class-A root cause — CONFIRMED.**
   `il_list_shape_scope.ENTRY_TERM_DASH_RE` is `^"([^"]+)"\s*-\s*(.*)$`.
   Applied to entry text after the `:-` prefix: single-term
   `"מונח ה" - הגדרה;` matches; both `"מונח א", "מונח ב" - ...` and
   `"מונח ג" ו"מונח ד" - ...` return **no match at all**. Single-term
   only, as claimed.

### CORRECTION 1 — M21's `בהכרזה זו` "measured zero" is wrong (conclusion survives)

M21 recorded `בהכרזה זו` as a measured **0**. Re-measured on `*.wiki`
only: **2 files / 4 occurrences.** I read every one: both files are
COVID `הכרזת סמכויות מיוחדות...` instruments and every occurrence is
REFERENTIAL prose inside `<מבוא>` ("באזורים המצוינים בהכרזה זו",
"ההגבלות המפורטות בהכרזה זו") — never a defining preamble. So M21's
*decision* (no vocabulary entry for `בהכרזה זו`) is right, but its
*measurement* was not. Recording this because D-2 will re-derive these
counts mechanically and a stale "measured zero" in this log would read as
a contradiction. Same class of error as M18: a phrase that OCCURS but is
never in the defining role is not a zero.

Also re-measured, for the record: `באכרזה זו` = **47 files / 53
occurrences** (M21 said 46/46); `לעניין הכרזה זו` = **3 files / 3
occurrences**, all three genuinely definitional heading preambles
(`@ 1. ... : לעניין הכרזה זו -`) — M21's actual fix target is CONFIRMED
correct and stays in the D-1a bundle. `לענין הכרזה זו` = 0 (confirmed).

### CORRECTION 2 — a NEW measured, definitional vocabulary gap nobody has named: the `זאת` demonstrative

`LAW_WIDE_WORDS` carries `אכרזה זו` / `פקודה זו` etc. — every entry uses
the `זו`/`אלה` demonstrative. The `זאת` demonstrative is absent
entirely. Measured corpus-wide:

```
באכרזה זאת    1 file    DEFINITIONAL (heading preamble, class-C shape)
בפקודה זאת    4 files   2 of them DEFINITIONAL law-wide preambles
בחוק זאת / בהסכם זאת / בצו זאת / בנוהל זאת / בהכרזה זאת   0 (measured)
```

The definitional ones, read individually:
- `אכרזה על ארגון יציג של זכאים...` — `@ (תיקון: תשפ"ג) : באכרזה זאת,
  "זכאים לפי [[החוק האמור]]" - ...` (a heading-embedded preamble — this
  is simultaneously a class-C instance AND a vocabulary gap)
- `פקודת הצופים` — `: בפקודה זאת -` (bare law-wide preamble)
- `פקודת האריסים (הגנה)` — `: בפקודה זאת יהיו למונחים הבאים הפירושים
  דלקמן מלבד אם ענין הכתוב יחייב פירוש אחר -`
The other `בפקודה זאת` hits are referential ("שום דבר האמור בפקודה
זאת"), plus one parenthetical naming alias (`הקרוי בפקודה זאת "פטנט
לתוספת אמצאה"`) which belongs to the same naming-construct class D-1a
already characterized under class B.

**This is the M17 spelling-variant class recurring for the THIRD time**
(M17 spellings, M21 `הכרזה`/`אכרזה`, now `זו`/`זאת`). Small and bounded —
it is two vocabulary entries — but under an absolute-zero bar a measured
3 definitional instances is not zero. **Folded into the D-1a Developer's
vocabulary work.** It is also the strongest argument yet that D-2's
mechanical certification, not another hand variant-hunt, is the correct
closing method: three independent hunts each missed a variant the next
one found.

### CORRECTION 3 — D-INCLUDES: IL DOES have the includes-family gap (my brief's expectation refuted)

The program's D-INCLUDES ruling asks each panel whether its vocabulary
has an includes-family enumeration-verb gap. My brief carried the
expectation that `לרבות` is already core IL vocabulary, so likely no
action. **Measured, that is false:**

```
grep -rn "לרבות\|למעט" backend/app/definition_links/   ->  NO MATCHES (whole package)
il_trigger_grammar._find_split_marker('לענין זה, "מצרך" לרבות האריזה...')  -> (-1, 0)
il_trigger_grammar._find_split_marker('ולענין זה, "פקיד שומה" למעט עוזר...') -> (-1, 0)
il_trigger_grammar._find_split_marker('לענין זה, "מצרך" - האריזה...')       -> (17, 1)
```

`לרבות` and `למעט` appear NOWHERE in the definition-links package. They
are recognized as neither split markers nor defining verbs — only the
dash is. `לרבות` is common *inside* definition bodies (which is likely
where the "already core vocabulary" impression came from), but it has no
grammatical role in capture.

So IL has a genuine analogue of the US includes-family gap. **It is
already covered by the existing D-1a bundle** — this is precisely
D-1a's class-B sub-shape (ii), the `TRIGGER, "term" לרבות/למעט <defining
text>` no-dash form the D-1a Planner characterized as ~80% of class B,
pinned by the committed RED
`test_class_b_plain_continuation_shape_no_dash_after_quote_is_currently_missed`
(fixture `חוק התקנים` art.13, "מצרך"). No new work item — but the D-1a
Developer is told explicitly that this RED is the IL discharge of
D-INCLUDES, so the includes-family verbs get treated as a first-class
defining-verb vocabulary and not as a one-off regex patch. Reporting the
measurement rather than assuming, per the brief.

### Plan from here (unchanged in shape, corrected in content)

D-1a Developer (dev3) -> merge -> D-1b Developer (dev4) -> QA cycle 4.
Certification contract drafted once the Developers are RUNNING, sent to
the program manager for sanity-check before its Planner spawns. Cycle 5
stays the bounce reserve.

---

## 2026-08-05 — D-1a Developer spawned (agentId `a4f70d362996ee90a`)

Model/effort: **Sonnet/medium** — implementation against 7 already-written
REDs whose root causes are established and positive-controlled; Haiku
considered: **no**, because the class-C scope semantics is a genuine
design decision with over-claim risk, and the Hebrew grammar work is
nuanced. Worktree `defs-il-dev3`, branch `claude/defs-il-dev-d1a` off
`8599a81` (M22 tip), own venv verified. Briefed with: the 7 RED node-ids,
per-class root causes, the class-C scope decision as an explicit
deliberate choice (with my live `determine_scope -> 'law-wide'`
measurement), M21 + M22 vocabulary entries to re-measure themselves, and
D-INCLUDES as discharged by class-B sub-shape (ii). Told explicitly: no
test edits (escalate instead), no frozen-file edits (escalate instead),
files under 300 lines, corpus read-only, D-1b's 4 E6 REDs and the 2
core-blocked containment REDs are off-limits. Expected end state
`6 failed, 836 passed`.

---

## 2026-08-05 — M23: certification contract DRAFTED (awaiting program-manager sign-off); D-2 denominator independently re-derived

Drafted `docs/sprint/sprints/2026-08-05-defs-il-certification.md` while
the D-1a Developer runs, per the phase-3 brief's sequencing ("once the
Developers are RUNNING, not before"). `contract_lint.sh` -> **PASS 227**.
**No Planner spawns until the program manager signs it off.** The
certification sprint opens only after this sprint closes anyway — its
denominator must be measured against the capture behaviour the panel
actually ships in cycle 4, not a moving target.

### The D-2 denominator, re-derived from scratch by me — CONFIRMED

I did not inherit the ~92,600 figure. Own script, own venv, production
`sections.parse_articles`, full read-only corpus:

```
                        phase-3 (mine)   phase-2 (M19-EXT)   delta
files                            6,133             6,133    exact
articles                       128,234           128,234    exact
raw quote chars                276,815           276,628    +187 (0.07%)
word-internal                   91,605 (33.1%)    91,431 (33.1%)  pct exact
delimiter-eligible             185,210           185,197    +13
paired candidate spans         ~92,605           ~92,598    +7
```

Two independent derivations agreeing to 0.07% — the denominator stands.
The residual delta is written into the contract as a **C1 gate item**
(explain or eliminate), not waved through: every downstream percentage
rests on it.

### NEW phase-3 finding folded into the contract: the quote character is FOUR characters

M19-EXT's spec says "raw `"` characters", singular. Measured per
codepoint, the population is a mixture with *opposite* behaviours:

```
codepoint                    raw     word-internal   eligible    ~spans
U+0022 straight quote    256,680           32.7%     172,826    86,413
U+05F4 Hebrew gershayim    7,649           98.7%         103        51
U+201D right double       12,468            1.6%      12,263     6,131
U+201C left double            18            0.0%          18         9
```

Two consequences, both now written into the contract as design
constraints rather than left for the Planner to trip over:

1. A certification scanning only `U+0022` **silently drops ~12,500
   `U+201D` characters — ~6,100 spans, 6.6% of the population.** A 6.6%
   blind spot in the one sprint whose entire purpose is having no blind
   spot.
2. **The word-internal predicate is not uniform across codepoints.**
   `U+05F4` is 98.7% word-internal (essentially only an abbreviation
   marker); `U+201D` is 1.6% (essentially only a delimiter). One blended
   predicate hides both facts. Cluster 1 must be evaluated per codepoint,
   and pairing must handle mixed-codepoint pairs (`“term”` opens U+201C
   and closes U+201D).

This is the same lesson as M-D3 and M22's `זאת` finding, one level down:
**measure the character class, don't assume it.** Carried into the
contract as a precedent binding D-CERT's US track too — it should check
its own quote/dash inventory rather than assuming ASCII.

### Gates proposed (C1-C5)

C1 signal-agnostic reproducible denominator covering all four codepoints;
C2 mechanically-asserted exhaustive+disjoint cluster assignment over the
FULL population (the backbone); C3 every disposition carries a measured,
seeded, hand-verified error rate; C4 fix loop closed INSIDE the sprint
with re-certification of affected clusters; C5 artifact re-runs clean and
diffs for an independent QA. Full text in the contract.

---

## 2026-08-05 — M24: harness adjustment — role agents report DIRECTLY to the panel manager

Director-ordered, relayed by the program manager. Effective from this
panel's next spawn or resume:

- Role agents (Planner / Developer / QA) deliver their reports **directly
  to the panel manager** (agentId `a18597f9be6c49ed6`) via SendMessage.
  A plain-text final return is **not** a reliable delivery channel — the
  SendMessage IS the report. Every brief from now on carries that
  sentence verbatim, including the "if the send fails, say so in your
  final text" clause.
- **Escalations** (first line `ESCALATION:`) arrive on the same channel.
  The panel manager resolves them, or escalates onward to the program
  manager — the program manager no longer relays them.
- Peer-manager coordination by agentId is unchanged.

**Applied retroactively to the in-flight D-1a Developer**
(`a4f70d362996ee90a`), which was briefed before the change. Rather than
leave it on the degraded fallback path, I sent it the new delivery
instruction as a scope-neutral amendment — explicitly "your task, scope
and constraints are completely unchanged; do not restart or redo
anything" — plus a restatement of the required report contents and the
two escalation triggers (a test that looks wrong; a frozen-file edit
appearing necessary). Recording it here because a mid-flight amendment to
a running role agent is exactly the kind of thing that must be auditable
rather than tacit.

Remaining briefs in this sprint (D-1b Developer, QA cycle 4) carry the
clause from the start.
## 2026-08-05 — D-1a Developer (Sonnet/medium), worktree `defs-il-dev3`

Worktree `/Users/nerya/LexGraph-wt/defs-il-dev3`, branch
`claude/defs-il-dev-d1a`, at `8599a81` (M22), clean at start. Venv
verified: `import app` -> this worktree's `backend/app`. Git email
confirmed noreply. Baseline reproduced myself before touching anything:
`backend/.venv/bin/pytest backend/tests -q` -> `13 failed, 829 passed` --
exact match to the brief and to M22's own re-verification.

### Per-class live re-confirmation (before fixing, per M4)

- **Class A.** `il_list_shape_scope.ENTRY_TERM_DASH_RE` re-confirmed:
  `"מונח א", "מונח ב" - ...` and `"מונח ג" ו"מונח ד" - ...` both return no
  match; single-term `"מונח ה" - ...` matches. Matches M22 control 4
  exactly.
- **Class B.** `extract_quote_first_candidates('לענין זה - "מסירה"
  כמשמעותה [[בסעיף 8 לחוק המכר, תשכ"ח-1968]].', ...)` -> `[]` reproduced;
  `_find_split_marker` on the post-quote clause -> `(-1, 0)`, and the
  visible dash inside `תשכ"ח-1968` is correctly NOT picked up (no space
  on either side) -- confirmed this is a genuine no-marker case, not a
  measurement artifact.
- **Class C.** `HeadingRule` feasibility re-confirmed with my own
  throwaway probe (registered, ran, deleted, never committed): on
  `אכרזת גנים לאומיים` art.8, baseline `is_definitions_heading` -> `False`;
  with the probe registered -> `True`, section path captures all 10
  terms. Also independently re-confirmed the scope hazard myself:
  `HebrewProfile.determine_scope(body)` on that same article body ->
  `'law-wide'` (no chapter trigger in the first body line, no
  `ScopeKindRule` registered that could see the heading-only trigger
  `בתוספת זו` either way). This is the load-bearing fact the whole
  Class-C design decision below rests on.

### Class A fix -- multi-term list entries

`il_list_shape_scope.py`: added `parse_entry(entry_text)`, replacing the
single-term `ENTRY_TERM_DASH_RE` match at both call sites. Finds the
entry's split marker (first standalone `-` outside any quote, whole-string
scan) first, then reads every leading quoted term from the header before
it, each non-first one introduced by a comma and/or the vav conjunction
prefixed directly to its own opening quote (the two real corpus
sub-shapes, plus their natural combination). `make_candidate` widened to
accept `terms: str | tuple[str, ...]` (a bare string still wraps to a
1-tuple, so every pre-existing call site needed zero changes beyond the
two list-shape `_extract` functions themselves).

Also fixed, found while reading the code (not asked for, but real): the
`::-` rule (`il_colon_dash_nested_list_scope_triggers.py`) had its OWN
private single-term-only `_TERM_DASH_RE` copy, despite its own docstring
already claiming to share `il_list_shape_scope.py`'s logic -- a doc/code
mismatch, not just a duplicate of the multi-term bug. Both sibling rules
now call the one shared `parse_entry`.

While making Class C's fixture pass (see below), I found `parse_entry`
also needed to tolerate a QUALIFIER between the last term and the dash
(`"גידול מלאכותי" (Artificially propagated) - כהגדרתו ...`, a real entry
in the Class-C schedule fixture) -- the FROZEN, already-shipped
definitions-SECTION path (`extract._find_split_dash` +
`_parse_terms_and_qualifier`) already tolerates exactly this shape (a
whole-line, quote-aware dash search, not an immediately-after-the-quote
match), so widening `parse_entry` to the same algorithm is parity with
an already-precision-proven mechanism, not new risk.

### Class B fix -- no split marker after the quote (also IL's D-INCLUDES discharge)

`il_trigger_grammar.py`: added `_find_fallback_word_marker`, tried only
when `_find_split_marker` finds no punctuation marker at all (a real dash
still always wins when present). Two named word sets: `REFERENCE_WORDS =
("כהגדרתו", "כהגדרתה", "כמשמעותו", "כמשמעותה")` (sub-shape (i), the
by-reference shape) and `INCLUDES_FAMILY_WORDS = ("לרבות", "למעט")`
(sub-shape (ii)). Matched as a whole word (start/whitespace before,
whitespace/light-punctuation/end after) outside any quote; the marker is
zero-width and stays IN `definition_text` (unlike the dash, these are
meaningful content words, not punctuation).

**D-INCLUDES discharge, stated explicitly per the brief:** `INCLUDES_
FAMILY_WORDS` is a named, reusable defining-verb vocabulary living
alongside the dash in the SAME shared helper every quote-first IL rule
already builds on (`extract_quote_first_candidates`), not a one-off
regex patch scoped to one fixture. Every rule already built on this
helper (8 modules) picks up both sub-shapes for free, for its own
already-registered trigger vocabulary -- confirmed live: the "פקיד שומה"
/ `למעט` instance the Planner named (not vendored as a fixture) also now
captures (spot-checked in the venv, not asserted by any test).

### Class C fix -- preambles living in the article's own heading

New file `il_heading_embedded_preamble_scope_triggers.py`. Detection:
the article body's FIRST non-blank line is already a `:-`/`::-`-marked
entry -- i.e. neither list-shape sibling rule ever found a preamble line
to start a list from (both already scan the WHOLE body for one). Reused
`parse_entry`/`make_candidate` from the shared module (so this path is
multi-term-safe too, for free). Registered as an ordinary `ScopeTriggerRule`
(the already-wired `extract_local_scope_definitions` path), NOT a new
`HeadingRule`.

**Corpus-wide precision sanity check (my own, scratchpad, read-only,
not a test):** swept all 6,133 files for this exact detection shape
(ordinary article, `is_definitions_heading` False, body's first content
line already `:-`/`::-`-marked) -- **57 real hits**. Hand-read the full
list: ~50 are genuine definitional lists (schedules/appendices, `פירוש`/
`פירושים`-headed articles baseline's regex doesn't recognize, a
numbering-prefixed `הגדרות` heading, a heading-embedded `לעניין הכרזה זו`
instance and its 2 siblings). The remaining ones are all SAFE non-captures
by construction, not false positives: `והואיل:`/`لكבود` recital/form-letter
bodies whose first "entry" doesn't start with a quote (`parse_entry`
returns `None`); a `בפקודה זאת -`-adjacent article whose OWN first `:-`
line is a stray `((,))` artifact with no quote at all; a `TERM פירושו
definition` no-dash grammar `parse_entry` correctly declines to guess at.
Zero false TERM captures found in the full sweep.

### THE DESIGN DECISION -- Class-C scope semantics

**Chosen: `scope="local"` for every Class-C candidate, unconditionally,
built directly by this rule (never delegated to `determine_scope`).**

**Why not the `HeadingRule` + definitions-section route (the Planner's own
probe used it for feasibility, but feasibility != correctness):** once
`is_definitions_heading` is flipped `True`, `pipeline.py` calls `scope =
profile.determine_scope(matcher_article.body)` and stamps that ONE scope
string onto EVERY candidate from `extract_definitions_from_section`
uniformly (`extract._parse_block(block, scope=scope, ...)`) -- there is no
per-candidate override available from a rule module on that path.
`determine_scope`'s signature is `(self, body_text: str)` -- FROZEN, and
verified live (control 3 above) that it never receives heading text, so
for a Class-C article (no chapter trigger in the body's own first line,
and no `ScopeKindRule` I could register would have any body-text signal
for a heading-only trigger either) it falls through to its own
unconditional `return "law-wide"`. Ruling M16 already, deliberately,
EXCLUDES `בתוספת זו` from the law-wide vocabulary specifically because it
does NOT mean "the whole law" -- shipping `scope="law-wide"` here via the
section-dispatch route would directly contradict that established policy
and manufacture real false `USES_DEFINITION` edges reaching articles
outside the defining schedule/instrument-subpart. That is a genuine
precision regression, not a hypothetical one, so I did not take that
route even though it is the more "obvious" one Class C's feasibility
probe used.

**Rejected alternatives (stated per the brief's explicit ask):**
1. HeadingRule + section dispatch, accepting `determine_scope`'s law-wide
   default -- rejected for the reason above.
2. A new `scope_unit_kind` (e.g. `"schedule"`) -- rejected per M-D3 (no
   measured Hebrew structural convention for what a schedule/appendix
   UNIT even is, gathered this session) and moot regardless: it is the
   SAME "no live DATA SOURCE" gap M20 already found for סימן/חלק --
   `pipeline.py`'s `StructuralContext(..., heading_breadcrumbs=())` is
   hardcoded empty at its one call site, so no `StructuralUnitRule` could
   populate a matching `ScopeUnit` even if I declared the kind.
3. A module-level mutable side channel (`HeadingRule.matches` stashing the
   heading string, a `ScopeKindRule.detect` call reading it back) --
   technically achievable (pipeline.py's per-article loop IS sequential,
   confirmed by reading it), but rejected as a fragile hidden coupling on
   a frozen file's own call ordering that I do not own and that could
   change; it also does not even answer the real question (WHICH scope a
   given, still-invisible heading trigger means) -- it would only
   relocate the guess, not remove it.
4. Escalating and leaving Class C red -- rejected: the brief frames this
   choice as mine to make deliberately, and a legitimate, non-over-claiming
   rule-module-only path exists (this file), so there is no genuine
   blocker.

**The honest trade, stated plainly:** `scope="local"` (`HebrewProfile.
main_unit_kind`, the same conservative default `infer_scope` already
falls back to for any unrecognized preamble) UNDER-claims -- a mention of
the same term in a SIBLING article of the same schedule/instrument will
not link, and it under-claims even in the (measured, real) cases where the
heading's own invisible trigger IS an already-recognized law-wide phrase
(`: בצו זה -`, `: [[בתוספת זו]] -`, both present among the 57 corpus hits)
or a numbering-prefixed plain "הגדרות" heading that would ordinarily
default to law-wide. It NEVER over-claims -- no false link to an unrelated
article elsewhere in the law. Given there is genuinely no live way for any
rule-module-only file to learn what a Class-C heading's own trigger phrase
says, I chose the direction that cannot fabricate a wrong link, consistent
with the brief's own framing ("refusing to over-claim when the trigger is
unknown"). This is a recall gap on top of an already-uncapturable class,
not a new false-positive risk -- P-R2-compliant, no precision conflict to
escalate. Both concrete under-claim examples above are documented in the
new rule module's own docstring for whoever eventually threads heading
text through the frozen seam.

### Law-wide vocabulary -- own re-measurement (not trusted from the log)

Re-measured directly against `/Users/nerya/AI for others/israeli-laws-wiki/data/laws/*.wiki`
(read-only, grep + manual reads, not a script re-running M21/M22's own
tooling):

- `לעניין הכרזה זו` = **3 files / 3 occurrences**, all three
  `@ N. ... : לעניין הכרזה זו -` heading preambles (Class-C shape) --
  matches M22 exactly. `לענין הכרזה זו` = 0, confirmed.
- `בהכרזה זו` = **2 files / 4 occurrences**, both COVID
  `הכרזת סמכויות מיוחדות...` instruments, every occurrence referential
  prose inside `<מבוא>`, NEVER ending in a dash -- matches M22's
  correction of M21's stale "measured zero" exactly.
- Added `הכרזה זו` to a NEW `LAW_WIDE_PREPOSITION_ONLY_WORDS` table (in
  the new `il_law_wide_vocabulary.py`, see below) rather than
  `LAW_WIDE_WORDS` -- `law_wide_preamble_phrases()` now generates ONLY
  `לענין הכרזה זו`/`לעניין הכרזה זו` for it, never the bare `בהכרזה זו`
  form every other entry gets. This is a real, deliberate mechanism
  change (not just a data addition): blindly adding `"הכרזה זו"` to
  `LAW_WIDE_WORDS` would have auto-generated the unsafe `ב`-form too.
- `באכרזה זאת` = **1 file**, confirmed definitional, but its ONE
  occurrence is `@ (תיקון: תשפ"ג) : באכרזה זאת, "..." - ...` -- a HEADING
  line (inline quote-first grammar, not a `:-` list) -- a Class-C-adjacent
  shape my Class-C mechanism does NOT reach (it only handles `:-`/`::-`
  list bodies). **Deliberately NOT added to the vocabulary** -- neither
  vocabulary consumer (list-shape body scan, M17 quote-first body scan)
  ever reads heading text, so it would be a permanently-dead entry today.
  Recorded here as an honest, measured, currently-unreachable gap rather
  than added as vocabulary theater.
- `בפקודה זאת` = **4 files / 6 lines**, 2 genuinely definitional
  (`פקודת הצופים`: `: בפקודה זאת -`; `פקודת האריסים (הגנה)`: `: בפקודה
  זאת יהיו למונחים... -`, both immediately followed by real `:-` entries,
  read directly). The other 2 dash-ending lines carrying this SAME phrase
  (also in `פקודת האריסים (הגנה)`, arts. 7/15) are referential prose that
  ALSO happens to end in "-" -- checked directly whether this is a real
  FP risk: both are immediately followed by `(א)`/`(ב)`-labelled clause
  continuations, never `:-`-marked entries, so `infer_scope` firing on
  them is harmless (the entry-collecting loop finds nothing and produces
  zero candidates) -- the SAME "a preamble ending in `-` for an unrelated
  reason cannot fabricate a definition on its own" argument this whole
  sprint already relies on. Added `"פקודה זאת"` as a full `LAW_WIDE_WORDS`
  entry (all 3 prefix forms) since this specific FP path is verified
  neutralized.

Split `il_trigger_grammar.py`'s law-wide vocabulary section into a NEW
`il_law_wide_vocabulary.py` (both files were pushed over the 300-line
style gate by this session's additions) -- `il_trigger_grammar.py`
re-exports `LAW_WIDE_WORDS`/`LAW_WIDE_PREPOSITION_ONLY_WORDS`/`law_wide_
preamble_phrases` for every existing importer, byte-identical behavior,
verified live (`import` + a direct call) before running the suite.

### Suite, lint, diff boundaries

`backend/.venv/bin/pytest backend/tests -q` -> **`6 failed, 836 passed,
18 warnings`** (reproduced twice, stable) -- exactly the expected end
state: the 4 E6 REDs (D-1b's bundle) + 2 סימן/חלק containment REDs
(core-blocked, M20) stay red, unaffected; 829 -> 836 (+7, all D-1a's own),
zero existing test edited or broken.

`bash scripts/contract_lint.sh 2026-08-04-defs-il` -> `PASS 398`.

`git diff --name-status HEAD -- backend/tests backend/app/definition_
links/profiles.py backend/app/definition_links/pipeline.py backend/app/
definition_links/sections.py` -> **empty** (verified, reproduced above).
Full diff: 4 modified rule files (`il_colon_dash_nested_list_scope_
triggers.py`, `il_list_shape_scope.py`, `il_single_colon_list_scope_
triggers.py`, `il_trigger_grammar.py`) + 2 new rule files (`il_heading_
embedded_preamble_scope_triggers.py`, `il_law_wide_vocabulary.py`) + this
log entry. Every touched/added file under the 300-line style gate
(largest: `il_trigger_grammar.py` at 242 lines).

### Honest gaps

1. Class C's `scope="local"` default is a genuine, measured recall gap
   for two real sub-populations found in my own 57-hit sweep (headings
   whose own trigger is an already-recognized law-wide phrase; a
   numbering-prefixed plain "הגדרות" heading) -- named above and in the
   new rule module's own docstring, not silently absorbed. Not fixable
   rule-module-only given the frozen `determine_scope(body_text)`
   signature.
2. Did not hand-verify all 57 corpus-wide Class-C-shape hits term-by-term
   (spot-checked the majority, verified every NON-definitional one
   produces zero candidates by construction) -- a full per-term audit is
   D-2/certification-scale work, out of this bundle's mandate.
3. Class B's fallback-word fix was verified against the two vendored
   fixtures plus the "פקיד שומה" instance named in the test's own
   docstring (spot-checked live, not asserted by any test) -- did not
   re-run the Planner's own 103-item production-trigger sweep to confirm
   every one of those now captures; the mechanism is a direct,
   conservative widening of an already-scoped, already-measured class, so
   I judged this sufficient for this bundle rather than re-deriving the
   whole population.
4. `parse_entry`'s new qualifier-tolerance (needed for Class C's own
   fixture) widens what EVERY list-shape rule accepts, not just Class C
   -- a deliberate, justified widening (parity with the already-shipped,
   already-precision-proven `extract._find_split_dash`/`_parse_terms_
   and_qualifier`), but I did not separately corpus-sweep for its own
   marginal recall/precision effect on Class A's already-shipped
   single-term shape; the full-suite zero-regression result is the
   evidence I am relying on for its safety, not a dedicated sweep.
5. Did not attempt to characterize or fix `אכרזה זאת`'s heading-embedded
   quote-first shape or the two Class-C under-claim sub-populations named
   above -- out of scope for this bundle (no RED test requires them),
   flagged for whoever next touches heading-text plumbing.

### Git discipline (M14)

Worktree `defs-il-dev3` only, explicit-path `git add`, no `-A`, no
`git stash`. Commit message below covers the rule-module changes; this
log entry is appended, not editing any prior entry.

---

## 2026-08-05 — M25: D-1a ACCEPTED and merged; but I found a measured incompleteness in the Class-A fix (`או`)

### Boundaries (mechanical, verified BY ME, not from the report)

`git diff --name-status origin/claude/defs-il...bdc8e61 -- backend/tests
backend/app/definition_links/profiles.py pipeline.py sections.py` →
**empty**. Zero test edits, zero frozen-file edits. Three-dot diff (696
lines) materialized to scratchpad and **read in full**. Own venv, own
run: **`6 failed, 836 passed`** — the 4 E6 + 2 containment REDs remain,
all 7 D-1a REDs green, 829→836 = +7, zero regressions. Lint PASS 398.
Style gate: largest touched rule file 242 lines (`il_trigger_grammar.py`),
all under 300. Merged `--no-ff`; log conflict was two concurrent appends,
both kept in order. Post-merge re-run by me: `6 failed, 836 passed`.

### What D-1a delivered well

- `parse_entry` **fails closed** — returns `None` rather than guessing
  whenever the trusted quote/dash shape is absent. That is the right
  default for a recall fix and is what makes its precision argument hold.
- **A real bonus catch:** `il_colon_dash_nested_list_scope_triggers.py`
  kept its OWN private single-term `_TERM_DASH_RE` while its docstring
  claimed it shared `il_list_shape_scope`'s logic. A doc/code mismatch
  nobody had noticed; now genuinely shared.
- The **class-C scope decision is sound and well-argued**: `scope="local"`
  built directly by the rule, never delegated to the heading-blind frozen
  `determine_scope`, with four alternatives explicitly rejected in the
  module docstring. It UNDER-claims (named, quantified) and never
  over-claims. That is the honest direction, and it respects M16's own
  exclusion of `בתוספת זו` from the law-wide vocabulary.
- **D-INCLUDES discharged properly**: `INCLUDES_FAMILY_WORDS =
  ("לרבות", "למעט")` as named reusable vocabulary in the shared helper
  every quote-first IL rule builds on, so all 8 consumers get it — not a
  one-off patch.
- `LAW_WIDE_PREPOSITION_ONLY_WORDS` is a genuinely good piece of design:
  it lets `הכרזה זו` generate only its verified-safe `לענין/לעניין`
  forms and never the verified-UNSAFE bare `ב`-form.

### M25 — the incompleteness: `parse_entry` does not handle `או`

Green tests do not prove a class is closed. None of the 7 REDs uses the
`או` ("or") separator, so I attacked the new parser directly:

```
D-1a parse_entry              FROZEN extract._parse_terms_and_qualifier
  comma -> 2 terms              comma -> 2 terms
  vav   -> 2 terms              vav   -> 2 terms
  OR    -> 1 term  <-- GAP      OR    -> 2 terms  <-- handles it
```

`extract._parse_block` on `:- "טופס השתתפות" או "כרטיס" - ...` returns
**both** terms. `parse_entry` on the same line returns **one**.

This matters for three reasons:

1. **The claimed parity is incomplete.** The module docstring justifies
   the new dash scan as "porting an already-precision-proven algorithm,
   not inventing one" — but it ported the dash-finding and
   qualifier-tolerance and NOT the `או` separator the frozen algorithm
   also has. So the SAME entry line now yields 2 terms through the
   definitions-section path and 1 term through the list-shape path. An
   internal inconsistency between two live paths in one product.
2. **The miss became silent.** Before D-1a, `"א" או "ב" - def` matched
   nothing and the whole entry was dropped — a visible total miss. Now
   the first term is captured and `או "ב"` is discarded as a "qualifier".
   Strictly better recall, but the second term is now dropped with no
   trace. Silent partial > visible total, for an absolute-zero-miss bar.
3. **It is not small.** Measured by me, corpus-wide, on the entry LINE
   (M18):

```
^:{1,2}- "term" או "term2"            230 lines / 160 files   (upper bound)
   same, requiring a following dash   197 lines / 142 files
^:{1,2}- "term" ו- "term2"             23 lines   (hyphenated vav conjunction)
^:{1,2}- "term" ו "term2"               1 line    (spaced vav — negligible)
```

**230 is an UPPER BOUND, not the decision-relevant number** — it counts
every entry line corpus-wide including those inside `הגדרות` sections,
which route through the frozen path and are parsed correctly today. The
subset that actually reaches the list-shape rules (ordinary,
non-`הגדרות`-heading articles) needs its own M18-compliant derivation;
that is the Planner's job, not a number I will invent here. But even the
upper bound's shape is telling: `או` alone is larger than the comma-only
sub-shape (83) the fix DID handle, and `ו-` adds ~23 more.

**Not a regression, and not grounds to reject D-1a** — it delivered its
seven REDs with zero regressions and reported honestly. But class A is
**not closed**, and I am not going to let "7/7 green" stand in for that.

### Routing (red-before-green preserved)

The `או`/`ו-` separator gap needs a **RED test first** — the Developer
who wrote `parse_entry` may not author its own acceptance test. Spawning
a Planner for it, concurrently with the D-1b Developer: the Planner
writes only `backend/tests/**`, the Developer writes only
`backend/app/definition_links/rules/**`, so the file sets are disjoint
and M14's one-writer rule holds (same concurrency pattern this panel used
for the D-1a/D-1b Planners).

### Carried forward as enumerated residual (not silently dropped)

- `אכרזה זאת` — 1 file, measured definitional, heading-embedded
  quote-first; unreachable by any rule registered today (no rule reads
  heading text). D-1a correctly declined to add dead vocabulary. Named
  here so it survives to the certification's cluster set.
- Class C's two under-claim sub-populations (headings whose own trigger
  IS a recognized law-wide phrase; numbering-prefixed plain `הגדרות`
  headings) — recall gaps, never false links, blocked on the same frozen
  heading-text seam.
- The 2 סימן/חלק containment REDs — core-blocked per M20, unchanged.

---

## 2026-08-05 — Planner (Sonnet/high, worktree `defs-il-plan3`, branch `claude/defs-il-plan-sep`): RED tests for the `או`/`ו-` separator gap M25 found

### Scope discipline (M14)

Worktree `/Users/nerya/LexGraph-wt/defs-il-plan3` only, own venv verified
(`import app` -> this worktree's `backend/app`). `git diff --name-status
HEAD -- backend/app` -> **empty**, verified before and after this
session's writes. Zero existing tests edited — one NEW test file
(`backend/tests/integration/test_definition_links_il_or_separator_gap_
live.py`) + 3 NEW vendored fixtures. Did not touch `test_definition_
links_il_siman_chelek_containment_live.py` (M20's 2 core-blocked REDs,
untouched, still red). A D-1b Developer was running concurrently in a
different worktree against `backend/app/definition_links/rules/**` only
— disjoint file sets, M14 held.

### Job 1 — independently re-derived denominator (M18/P-R7-compliant)

Own script (`il_or_sep_sweep_planner3.py`, scratchpad), imports NOTHING
from `il_list_shape_scope.py`/`extract.py` (the code under test) except
`app.definition_links.sections.parse_articles`/`is_definitions_heading`
— production article-routing code, not part of the separator bug, and
literally the function `pipeline.py` itself uses to decide which of the
two live paths an article's entries reach. Every dash-finder,
quote-scanner, separator-classifier, and the preamble+entry-scan "is this
line actually reached by the list-shape rule" simulation is a fresh,
independent re-implementation of both `il_*_list_scope_triggers.py`
modules' own scan loop (not copied from them).

**`או` ("or") separator, corpus-wide (6,133 files):**

```
total entry lines with an 'או' header-separator:                    243
  no real standalone split dash at all (excluded -- a different,
    already-named phenomenon, e.g. "X" או "Y" כוללים... with no dash):  20
  WITH a dash, inside a הגדרות/הגדרת מונחים/הגדרה/הגדרות ופירוש
    -headed article (FROZEN definitions-section path, already correct
    -- extract._parse_terms_and_qualifier grabs every quoted span
    regardless of separator):                                        181
  WITH a dash, ordinary article, NOT reached by the list-shape scan
    (no preceding preamble line ending in bare "-" found -- a SEPARATE
    pre-existing gap, e.g. all of `חוק הפרשנות` art.3 and `פקודת
    הפרשנות` art.1, whose own preamble ends in ":" not "-"; affects
    those articles' SINGLE-term entries too, unrelated to `או`):        26
  WITH a dash, ordinary article, REACHED (THE REAL GAP):                16
    unique files:                                                        9
```

**`ו-` hyphenated vav conjunction** (distinct from D-1a's already-fixed
bare `ו"t2"` direct-prefix form):

```
total entry lines:            37
  no real dash:                 1
  frozen (correct):            29
  not reached:                  3
  REACHED (THE GAP):            4  (unique files: 4)
```

**`ו ` spaced-vav form:** 1 line corpus-wide, confirmed — and that ONE
instance (`תקנות ביטוח בריאות ממלכתי (העברת דמי ביטוח...)`, `"נכה" ו
"נצרך"`) sits inside a `הגדרות`-headed article, already routed to the
FROZEN path today. **Zero live gap from this form** — excluded from the
RED tests not merely as "negligible" but as a confirmed zero.

**The 230/160 lead in my own brief was an upper bound, exactly as
flagged — the decision-relevant number is 16 (`או`) + 4 (`ו-`) = 20
lines / 13 unique files that actually reach the buggy list-shape path.**
The other 181+29=210 with-dash `או`/`ו-` lines are already correctly
captured today via the frozen path; a further 26+3=29 are in ordinary
articles but never reached by ANY rule today for a reason unrelated to
this separator bug (no preceding preamble line in the shape the scan
loop requires) — a pre-existing, orthogonal gap, named here, not folded
into this bug's count.

All 20 gap lines were then LIVE re-confirmed against `profile.
extract_local_scope_definitions` directly (own script) — every one shows
the FIRST term captured (parse_entry's single-term fallback) and every
subsequent term absent, the exact "silent partial" signature M25 named.

### Cross-check against the D-1a Planner's own 392 (explicitly asked for)

Read D-1a's own sweep script, still present in the shared scratchpad
(`il_d1a_classA_sweep.py`). Its own gap-validation regex,
`re.fullmatch(r'[,\s]*(?:או|ו)?[\s]*', gap)`, **does** match a bare `"
או "` gap between two quoted spans — so D-1a's reported 392
confirmed-missing lines already counted `או`-joined entries as missing,
alongside comma/vav ones. But its separator-BREAKDOWN accounting only
tests `has_vav = bool(re.search(r'ו"', header))` and `has_comma = ","
in header` — neither of which an `או`-only pair satisfies. The
arithmetic confirms it: comma-only 83 + vav-only 203 + mixed 72 = **358**
against D-1a's own reported total of **392** — a gap of **34** lines its
own breakdown does not name.

**Plain finding for the manager:** `או`-separated entries were very
likely already inside D-1a's own reported 392/963/207, silently
uncounted in its separator breakdown, and — per M25's own live re-probe
on the merged tree, reproduced independently here — are **not** actually
fixed by the `parse_entry` that shipped against that number. D-1a's own
work was honestly scoped (it said "requires an explicit `,`/`ו`/`או`
separator" for its gap-VALIDATION step, i.e. `או` was swept INTO the
denominator, just never separately reported) and delivered real, correct
comma/vav fixes with zero regressions — this is not a fault in what it
built. But **class A, as D-1a's own Planner measured and reported its
392/963/207 headline, was not fully closed by the fix that shipped
against those numbers.** Did not re-run D-1a's exact script end-to-end
to identify the specific 34 lines 1:1 (time-boxed; honest gap below) —
the arithmetic plus this session's own independent 16-line live-reproduced
`או` gap both point the same way, which is what I am reporting.

### Job 2 — RED tests (3, node-ids), all fail for the right reason

`backend/tests/integration/test_definition_links_il_or_separator_gap_live.py`:

- `::test_or_separator_single_colon_pure_multiterm_entry_is_currently_missed`
  (fixture `קובץ החלטות מועצת מקרקעי ישראל_art3_5.1_excerpt.wiki`,
  single-colon, pure `או`, "הסכם" או "הסכם גג" — a numbered `5.1.
  הגדרות` sub-heading that does NOT match `_DEFINITIONS_HEADING_RE`
  (must START with the bare word), a real, live-confirmed instance of a
  numbered-heading definitions article routing to the ordinary-article
  path);
- `::test_or_separator_double_colon_mixed_comma_and_or_multiterm_entry_is_currently_missed`
  (fixture `חוק הפסיכולוגים_art5א_excerpt.wiki`, double-colon, mixed
  comma+`או`, "תואר", "כינוי" או "הגדר" — proves comma still resolves up
  to the point `או` is hit, same entry);
- `::test_vav_hyphen_separator_double_colon_multiterm_entry_is_currently_missed`
  (fixture `פקודת מס הכנסה_art68א_excerpt.wiki`, double-colon, `ו-`
  hyphenated, "אמצעי שליטה" ו-"יחד עם אחר").

Each asserts (a) sibling single-term entries in the SAME list still
capture (sanity control), (b) the FIRST term of the multi-term entry
still captures (parse_entry's single-term fallback — proves "silent
partial", not "silent total"), (c) the missing subsequent term(s) —
which is what actually fails today. Reproduced failure tails (own run):

```
test_or_separator_single_colon_pure_multiterm_entry_is_currently_missed
  AssertionError: expected the SECOND term of the או-joined entry
  ("הסכם" או "הסכם גג" ...) to be captured ...
  got {'תשתיות צמודות', 'תשתיות על', 'הסכם', 'מוסדות חינוך', 'הקרקע',
       'מוסדות ציבור רשות', 'תשתיות תחבורתיות', 'הוועדה לתכנון ופיתוח'}

test_or_separator_double_colon_mixed_comma_and_or_multiterm_entry_is_currently_missed
  AssertionError: expected the THIRD term ("הגדר" ...) to be captured ...
  got {'תואר', 'השתמש', 'כינוי'}

test_vav_hyphen_separator_double_colon_multiterm_entry_is_currently_missed
  AssertionError: expected the SECOND term ("יחד עם אחר" ...) to be
  captured ... got {'אמצעי שליטה', 'בעלי שליטה'}
```

All 7 preceding sanity/control assertions in these 3 tests passed (never
the line that raised) — confirmed each test fails for the SPECIFIC
missing-term reason, not a broad breakage.

Fixtures: all 3 real, unedited, programmatically line-sliced (`@ N.
heading` line through the line before the next `@`/`==` marker),
byte-verified (`excerpt in source_text`) both immediately after
extraction and again from the written fixture files immediately before
writing the test module.

### Job 3 — precision/FP analysis (P-R2/D-Q1)

Hand-read all 20 live-confirmed gap lines (not a sample) — every one is
a genuine Hebrew legal-drafting convention: near-synonym headwords or a
canonical-name-plus-symbol-alias sharing one definition. Zero cases
where `או` between two header quotes meant anything other than "these
names share one definition" — the same structural argument (superset of
an already-precision-proven single-term grammar, N>=2 quoted spans
immediately adjacent to a real separator, immediately before the one
trusted split dash) D-1a's own Class-A FP analysis already made for
comma/vav.

**The manager's specific concern, checked rather than assumed:** does
`parse_entry` reading terms only from the pre-dash header actually
protect against a real corpus shape like `"term" - def containing
"quoted thing" או "other thing"`? **Verified with real corpus text, not
hypothesized** — 13 real files found (e.g. `תקנות ביטוח בריאות ממלכתי
(הסדרי בחירה בין נותני שירותים)`: `"כירורגיה גדולה" - כירורגיה שאינה
"כירורגיה זעירה", "כירורגיה קטנה" או "כירורגיה בינונית";` — three
comma/`או`-joined quoted spans, all in the DEFINITION TEXT after the
dash). Traced `_find_dash_marker`: the header for this entry is
`"כירורגיה גדולה"` alone (dash immediately after); the three post-dash
quotes never enter the header string the term-loop scans. **Confirmed
safe by construction, for any `או`-widening implemented the way D-1a's
comma/vav widening already is** (extending `_TERM_SEP_RE`'s
alternation, not restructuring the dash-then-header boundary). No
escalation — this is a real shape with a real, already-relied-upon
protection, not an open conflict.

### Honest gaps

1. Did not re-run D-1a's exact classA sweep end-to-end to name the
   specific 34 unreconciled lines 1:1 against my own 16/4 (`או`/`ו-`)
   gap — the arithmetic reconciliation plus this session's own
   independently-derived, live-confirmed 20-line gap both point at the
   same conclusion, but the two sets were not proven line-for-line
   identical.
2. Did not investigate whether `או`/`ו-` also appears as a separator
   inside the quote-first (`extract_quote_first_candidates`) or Class-C
   heading-embedded shapes — out of this session's scope (M25 named the
   list-shape `parse_entry` specifically), flagged for whoever
   certifies class A/B/C completeness next.
3. The 26 (`או`) + 3 (`ו-`) = 29 "ordinary article, not reached at all"
   lines are a real, separate, pre-existing gap (missing/malformed
   preamble line) — named, not fixed, not tested here; two concrete
   examples (`חוק הפרשנות` art.3, `פקודת הפרשנות` art.1) are
   important, frequently-referenced interpretation-clause laws whose
   ENTIRE definitions list (not just multi-term entries) is unreached
   by any list-shape rule today.
4. Test file is 326 lines, over the sprint's stated 300-line style
   gate. Checked precedent before proceeding: every prior `_live.py`
   integration test file in this sprint that touches this area is
   already over 300 lines (`test_definition_links_il_phase_d1a_abc_
   live.py` 440, `..._missed_classes_extended_live.py` 439,
   `..._qa_cycle1_fixups_live.py` 419, `..._phase_c_widening_live.py`
   1154), and every log entry citing "under 300 lines" names "rule
   file"/"touched rule file" specifically (production code under
   `backend/app/definition_links/rules/`) — this Planner reads the gate
   as scoped to production files, consistent with actual sprint
   practice, not test files. Flagging the reasoning rather than
   silently assuming.

### Suite, lint

`backend/.venv/bin/pytest backend/tests -q` -> **`9 failed, 836
passed, 18 warnings`** (6 pre-existing: 4 E6-held + 2 סימן/חלק
containment (M20, untouched) + 3 new REDs this session). `836` passed
unchanged from the post-D-1a baseline. `bash scripts/contract_lint.sh
2026-08-04-defs-il` -> **PASS 398**. `git diff --name-status HEAD --
backend/app` -> empty, verified.
