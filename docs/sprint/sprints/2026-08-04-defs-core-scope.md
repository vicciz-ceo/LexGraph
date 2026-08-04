---
id: "2026-08-04-defs-core-scope"
status: qa-fail
current_role: developer
branch: claude/defs-core-scope
worktree: /Users/nerya/LexGraph-wt/defs-core-scope
locked_by: "claude-code:qa-manager"
locked_at: "2026-08-04T09:52:12Z"
last_agent: "claude-code:qa-manager"
last_updated: "2026-08-04T11:05:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 11
lint: PASS
completed_items: 8
dev_complete_items: 1
qa_cycles: 1
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: Core scope seam — scoped definitions + rule registry

**Program role: CRITICAL PATH.** Every other program sprint builds behind this
sprint's seam and merges after it. The Planner must publish the seam spec (a
`## Seam spec (published)` section in this contract, committed and pushed on
the sprint branch) as its FIRST deliverable so family panels can plan against
it before this sprint's code lands.

## Mandate

From the program (read `design_sections` first — do not re-derive recon):
make scope a first-class, profile-dispatched concept so that a definition
declared for a specific article/subsection/chapter creates USES_DEFINITION
assertions ONLY for mentions within that scope, in every jurisdiction; and
give per-jurisdiction convention rules a registry seam so family sprints ship
rules as NEW modules without editing shared files.

Recon facts to build on (dossier §1): enforcement already exists and works
(`matcher._in_scope`, matcher.py:104-110; `Definition.scope`,
definition.py:35); production of scoped rows is Hebrew-only
(`_CHAPTER_SCOPE_TRIGGERS` pipeline.py:62-68; `_LOCAL_TRIGGER_RE`/`_ADHOC_RE`
extract.py:28-33); US fallback extraction lives inline in pipeline.py
(:106-289), not in USProfile.

## Acceptance gates (program manager-defined)

- **C1 — Scope is enforced everywhere, at every granularity.** A definition
  scoped to an article, subsection, chapter/part/siman creates assertions
  only for mentions within that scope — proven live-path in BOTH directions
  (in-scope mention links; out-of-scope mention does not), for IL AND US test
  cases. Subsection granularity is new design work: mentions must be
  scope-checked below article level.
- **C2 — Scope triggers dispatch through the profile.** No Hebrew-only (or
  English-only) scope literals in shared pipeline/matcher/extract code;
  English triggers ("As used in this section/subsection/chapter", "For
  purposes of this section/part") produce correctly-scoped definitions.
- **C3 — Extraction lives behind the seam.** The inline-quote fallback,
  body-heading derivation, and preamble detection move from pipeline.py into
  profile-owned code; pipeline.py retains no jurisdiction-specific literals.
- **C4 — Rule registry.** A new convention rule ships as a new module plus a
  registration, with zero edits to shared modules; the seam interface is
  documented in this contract for the family sprints.
- **C5 — Nothing regresses.** All existing IL tests green unchanged (prior
  R2: editing one is a planning bug — escalate); US baseline states
  (IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK) capture rates do not drop.

## Standing constraints

All program standing constraints apply (program doc §Standing constraints):
CodeGraph first for all code work; red-before-green with live-path RED tests;
Planner owns tests; QA independent; absolute zero-miss bar (director
decision 3); zero-miss vs false-positive conflicts escalate (P-R2), never
silently resolved.

## Next Steps

- [x] **I1 (DEV COMPLETE, cycle 2 — manager-verified, pending re-QA) —
  subsection-granularity scope containment, now LIVE (C1).**
  **FIXED** by `c76c2f6`, merged `86e0bbe`. `_subsection_contains_offset`
  keeps the `article.subsections` stub branch first, and when that
  attribute is absent (every real `MatcherArticle`) falls back to the
  already-live `profile.resolve_unit_path(article, char_offset=...)`
  retrieval seam, comparing `mention_path[0].value` against
  `scope_value` — `.value` only, never `.kind`, per v2.2's
  kind-is-display-only rule. `profile` threaded through
  `definition_covers_mention` with a `None` default so every existing
  call site is unaffected; `pipeline.py` Stage 3 passes the
  per-document profile. **Reuses the D-ANCHOR seam rather than building
  a parallel span mechanism** — one implementation of "which subsection
  is this offset in", so the two cannot drift.
  Manager-verified: 2 production files, ZERO test edits, full-hunk read
  of both; merged-tree suite **693 passed / 0 failed** (was 692/1).
  **Still owed before re-QA passes this (routed to Planner, cycle 2):**
  (a) the EXCLUSION direction is proven only by a hand-run outside
  pytest — the committed test still asserts the weaker "at least one
  edge exists"; (b) **multi-level nesting is untested** — the fix reads
  the OUTERMOST path step and `resolve_unit_path`'s replace-ancestor
  semantics were traced by hand for ONE level only, so a definition
  scoped to `(a)` containing a mention at `(a)(1)(A)` is unproven. Per
  v2.4 §3 there is no depth cap; the federal 8-level ladder is real.
  **Original bounce record (kept — this is the historical finding):**
  **[QA-FAIL: what failed]** A `scope="subsection"` definition links NOTHING
  live — not even the mention inside its own defining subsection.
  `matcher._subsection_contains_offset` reads
  `getattr(article, "subsections", ())`, but the real object
  `run_definition_linking` passes (`sections.Article`, aliased
  `MatcherArticle`) is a frozen dataclass with exactly four fields —
  `number`, `heading`, `body`, `chapter` — so the check is
  `any(...)` over an empty sequence → `False` unconditionally. There is no
  live PRODUCER either: no rule in this sprint stamps `scope="subsection"`.
  The unit tests that appeared to cover this pass only via a
  `SimpleNamespace` stub carrying `.subsections`, which the real dataclass
  does not declare.
  **[what was expected]** C1: "mentions must be scope-checked below article
  level", proven live-path in BOTH directions — the in-scope subsection
  mention links, the out-of-scope one does not.
  **RED provenance (committed, currently failing):**
  `backend/tests/integration/test_definition_links_pipeline_scope_seam.py::test_a_subsection_scoped_definition_links_a_mention_inside_its_own_subsection_live`
  (`2f88060`).
  **Scope of the fix:** (a) produce transient `Subsection(label, start, end)`
  spans on the live matcher article — the Stage-B design specified these and
  they were never built; (b) stamp `scope="subsection"` from the English
  subsection triggers through the EXISTING profile/rule seam (no shared-file
  edits beyond the matcher/pipeline wiring the seam already owns); (c) make
  the RED test green.
  **Also required in this cycle (QA gap 3, Planner-owned test):** a live US
  **chapter-scope OUT-of-scope EXCLUSION** test — none exists today, so the
  Developer must prove BOTH directions, not just the positive one.
  D-ANCHOR anchoring tests do NOT satisfy this: anchoring records WHERE a
  mention is, containment restricts WHICH mentions a definition covers.

- [ ] **I10 (NEW, director ruling D-CF) — case-fold structural-context guard.**
  Case-folding stays (I6 is not reverted); it gains a guard that SUPPRESSES a
  case-fold match when the hit sits inside a structural-reference pattern —
  a unit word followed by a numbering token ("division (ii)", "part (a)",
  "title 5"). Residual false-positive classes escalate with data per D-Q1.
  **Sequencing:** Planner authors the RED test FIRST (fixture material comes
  from QA's own corpus examples, the "Division"/"division (ii)" case), then
  Developer implements. No test may read the corpus (prior R6) — vendor the
  real rows as fixtures.

- [ ] **I11 (NEW, QA gap 5) — `Definition.scope_value` spec/code
  reconciliation.** Seam v2 §M4 specifies `scope_value` as a PERSISTED column
  with a migration. **Neither the column nor the migration exists.** Harmless
  today (nothing reads a persisted `scope_value`; the field lives only on the
  in-memory `DefinitionCandidate`), but spec and code disagree, and six
  family panels are about to build against that spec. Planner-role decision:
  either implement the column + migration, or amend the seam doc to match the
  code. **Do not leave the disagreement standing.** Note I1's fix may make a
  persisted `scope_value` genuinely load-bearing — settle I11 with I1's
  design in hand, not before it.

## Completed

QA cycle 1 (`claude/defs-core-scope-qa` @ `010e9c1`, merged `34a413f`) verified
these eight independently: each item's named `file::test` map re-run, the live
path traced to a production call site, and the pinning test **mutation-proven**
(production behavior temporarily broken, test confirmed RED, restored via
`git checkout --`). Full per-item evidence in `-log.md` Round 17.

- **I2 — Profile-dispatched scope determination + extraction seam** (C2, C3).
  Live at `pipeline.py` `determine_scope` / `extract_definitions_from_section` /
  `extract_local_scope_definitions` / `derive_heading_from_body`.
- **I3 — `pipeline.py` retains no jurisdiction-specific literals** (C3).
  QA EXTENDED the guard to English literals, not only Hebrew (`010e9c1`).
- **I4 — Rule registry**: 6 kinds, auto-discovery, registration (C4). QA
  proved C4 by shipping a throwaway rule module + registration with zero
  shared-file edits and confirming the live pipeline reached it.
- **I5 — M8(a) bare-`@` articles.** Reachability (not capture) per E-3/P-E3;
  corrected corpus fact re-verified by QA against the real 6,133-law corpus.
- **I6 — M8(b) case-folded term matching.** Corpus-wide FP exposure finally
  MEASURED (P-R7 independent denominator). Outcome fed director ruling D-CF;
  the fix stays, the guard lands as I10.
- **I7 — M12 `find_citations` + pointer emission.** D-MT-E1 two-capture shape
  confirmed: definition row + `DERIVES_FROM_LAW` edge, incl. internal same-law
  `Article` targets. **No typed pointer field anywhere** — manager grep for
  `pointer_kind|is_pointer|pointer_type|definition_kind|POINTER|Pointer` over
  `backend/app` returns one prose comment and nothing else.
- **I8 — M14 NY literal-`\n` ingest fix.** Residual closed: CA's 21 rows
  verified by CONTENT, not row count (`3d896f0`).
- **I9 — M15 profile-dispatched `normalize_for_parsing`.** Residual closed:
  verified against AK's REAL byte family (`bdb20de`).

## Context Dump

**State:** cycle 2 in progress. Backend at merge `86e0bbe`: **693 passed /
0 failed** — I1's C1 RED is now GREEN. Planner still in flight (gap-3
exclusion test, D-CF REDs, I11). Merge-to-main gate is re-QA cycle 2. Frontend 165 passed, `tsc` clean.

**The bounce in one line:** subsection-scope CONTAINMENT never runs in
production — no producer stamps `scope="subsection"`, and the live
`MatcherArticle` (4 fields) carries no `.subsections` for the consumer to
read. Unit greens came from `SimpleNamespace` stubs.

**Do not confuse anchoring with containment.** D-ANCHOR (`get_mention_unit_paths`)
records WHERE a mention sits and is live and correct. C1 containment restricts
WHICH mentions a definition covers and is dead. Fixing one does not fix the other.

**D-ANCHOR storage shape stays deliberately unpinned** (column name, type,
`subject_entity_type`) — a recorded intentional gap, not an oversight. Do not
"fix" it and do not pin it.

**CodeGraph's index reflects `main`, not worktree branches.** Use CodeGraph for
`main`-state structure and call paths; use Read/Grep for branch-divergent
source. Every brief in this program must carry this.

**Corpora ARE available** (the earlier "no corpus access" note was stale):
IL `/Users/nerya/AI for others/israeli-laws-wiki` (6,133 `.wiki`);
US `~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad`
— **105 parquet = 52 constitutions + 53 statutes**, 2,038,247 statute rows.
Measurement only: **no test may read the corpus** (prior R6); vendor real rows
as fixtures.

**Byte families are distinct — program-level correction:** AK mojibake is raw
cp1252 **U+0093/U+0094/U+0097** (~32K occurrences in 17,935 rows), NOT
`â€`-style sequences (which appear in 2 rows corpus-wide, both KY). CA is real
Unicode curly quotes (54,988 rows). A markers-panel rule written against `â€`
would miss all of AK.

**Process:** never `git stash` (stack SHARED across worktrees, concurrent
writers — use `git checkout --`); ONE writer per worktree; QA commits touch
ONLY `backend/tests/**`; merges manager-owned; never push `main`; no PR.
Worktrees under `/Users/nerya/LexGraph-wt/`, each needs its OWN backend venv
(the main checkout's venv imports the wrong code).

**Full panel history:** `-log.md`, 17 rounds, rulings M1-M15, D-CF, E-1..E-3.
Do not auto-load.

## Seam spec (published)

**Moved to `docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md`** (contract
line budget). That file holds all six published versions verbatim; **v2.4 is
AUTHORITATIVE and final** — where an earlier version disagrees, v2.4 wins.

Family panels: read the seam doc, not this contract, for the interface.
Key supersessions to be aware of: the `register_scope_unit_kind`/`rank_for`
rank registry was WITHDRAWN (v2.2; a pinned test asserts its absence), scope
containment is prefix-matching over a `UnitPath` with narrowest-governs =
longest-matching-prefix, and `find_citations` IS rule-extensible (v2.3).

## Stale-pin sweep

> **Historical (Stage B/C, pre-QA).** Its suite counts (644/38) are STALE —
> current numbers are in §Context Dump. Kept for its C5 evidence, which stands.

Swept `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/e2e/`
for every symbol this sprint deletes/renames/changes the signature of:
`_determine_scope`, `_CHAPTER_SCOPE_TRIGGERS`, `_is_placeholder_heading`,
`_derive_heading_from_body`, `_extract_inline_quoted_definitions`,
`link_articles_to_definitions`, `find_term_uses`, `find_citations`,
`extract_local_definitions`/`extract_adhoc_definitions`.

Result: **none need editing.**

- `_determine_scope` / `_CHAPTER_SCOPE_TRIGGERS` / `_is_placeholder_heading`
  / `_derive_heading_from_body` / `_extract_inline_quoted_definitions` —
  0 references anywhere under `backend/tests/`; all 5 live ONLY in
  `pipeline.py` today (confirmed via `grep -rln` across `backend/tests`
  and `backend/app`). Deleting them from `pipeline.py` breaks no test.
- `link_articles_to_definitions` — every caller (`test_definition_links_
  matcher.py`, `test_us_profile_definitions_section_end_to_end.py`,
  `pipeline.py`) calls it with its EXISTING signature
  (`(definitions, articles[, profile=...])`); this sprint's new behavior
  is reached by reading additional attributes off the SAME positional
  arguments (`.unit_path` etc.), not by adding/renaming parameters — no
  call site needs updating.
- `find_term_uses` (`us_profile.py`'s, the one M8(b) modifies) — every
  existing caller asserts either membership (`any(... in ...)`) or an
  exact-case match that a case-INSENSITIVE superset still satisfies
  (case-folding only ADDS matches, never removes one that matched
  before). Empirically confirmed, not just reasoned: the full suite run
  below shows 644 passed = 641 baseline + exactly 3 new PASSING guard
  tests this sprint added, 0 previously-passing tests newly failing.
- `find_citations` — existing assertions use substring membership
  (`expected_substring in c`) against patterns the decimal-truncation/
  state-code fixes don't touch (no existing test's expected substring
  contains a decimal section number or a state-code citation). Same
  empirical confirmation as above.
- `extract_local_definitions` / `extract_adhoc_definitions` — NOT
  deleted or changed (seam spec: they become IL's own registered
  `ScopeTriggerRule` bodies, called the same way internally); their own
  direct unit tests (`test_definition_links_extract.py`) are untouched,
  confirmed via the full run below (that file's tests are among the 644
  passing, unmodified).

Full backend suite (`backend/.venv/bin/pytest backend/tests -q
--continue-on-collection-errors`, this worktree, this commit):
**644 passed, 20 failed (this sprint's genuine RED, +3 from the v2.4
dossier-alignment/D-ANCHOR pass: deep-nesting, the no-bare-sub-unit
invariant, and sub-article anchoring), 1 collection error (this sprint's
registry module, genuine RED), 18 warnings, ~15.9s.**
0 previously-passing tests now fail — C5 confirmed empirically, not
merely argued. Frontend/typecheck not re-run this pass (no frontend file
touched this sprint; `git diff --name-only` confirms zero `frontend/`
paths in this sprint's changes).

**Stage C update.** The collection error above is FIXED (deliverable 1: the
module-level import in `test_definition_links_rules_registry.py` moved
inside each test body) — the contract's own plain evaluator command
(`pytest backend/tests -q`, no extra flags) now runs to completion with no
`--continue-on-collection-errors` needed. After Stage C's 7 new RED tests
(M9 live proof, M10 tie, pointer emission, 3 `_TRIGGER_PHRASES` idioms, I3
guard ×3 — the collection-error fix and D-ANCHOR/deep-nesting/invariant
tests were already in place at Stage C's start): `backend/.venv/bin/pytest
backend/tests -q` → **644 passed, 38 failed, 0 errors, 18 warnings, ~13-17s**.
644 unchanged throughout every Stage C commit (verified after each one).


---
