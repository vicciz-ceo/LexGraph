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
