---
id: "2026-08-04-defs-core-scope"
status: review
current_role: planner
branch: claude/defs-core-scope
worktree: /Users/nerya/LexGraph-wt/defs-core-scope
locked_by: null
locked_at: null
last_agent: "claude-code:qa-manager"
last_updated: "2026-08-04T12:03:25Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 11
lint: "PASS 199 2026-08-04T12:03:39Z"
completed_items: 11
dev_complete_items: 0
qa_cycles: 2
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

_None — all 11 items Completed; re-QA cycle 2 PASS on every gate._

## Completed

All 11 verified by an INDEPENDENT QA agent, gates re-run, live paths traced,
pinning tests mutation-proven. Full evidence: `-log.md` Rounds 17-19.

- **I1 — subsection-scope containment, LIVE** (C1). Cycle-1 bounce, fixed
  `c76c2f6`. Reuses the D-ANCHOR `resolve_unit_path` seam; pinned in BOTH
  directions plus 3-level nesting.
- **I2 — profile-dispatched scope determination + extraction seam** (C2, C3).
- **I3 — `pipeline.py` retains no jurisdiction-specific literals** (C3). Guard
  extended by QA to English literals, not only Hebrew.
- **I4 — rule registry**, 6 kinds + auto-discovery (C4). QA proved it by
  shipping a throwaway rule with zero shared-file edits.
- **I5 — M8(a) bare-`@` articles.** Reachability, not capture (E-3 / P-E3).
- **I6 — M8(b) case-folded term matching.** Corpus FP exposure measured;
  outcome fed director ruling D-CF.
- **I7 — M12 `find_citations` + pointer emission.** D-MT-E1 two-capture shape
  confirmed; NO typed pointer field anywhere.
- **I8 — M14 NY literal-`\n` ingest fix.** CA's 21 rows verified by content.
- **I9 — M15 profile-dispatched `normalize_for_parsing`.** Verified against
  AK's real byte family.
- **I10 — D-CF structural-context guard** (`7e7100b`). Gated on the TERM via a
  closed 10-word set, so an arbitrary term can never be suppressed.
- **I11 — `Definition.scope_value` is transient-by-design.** Seam doc amended
  as v2.5, append-only; spec and code now agree.

## Context Dump

**COMPLETE, awaiting merge.** Evaluator at HEAD: backend 700/0, frontend 165/165, `tsc` clean; lint genuinely PASS (an earlier `lint: PASS` was FALSE — Round 19).
**Authoritative seam = v2.5** (`-seam.md`) — family panels read that, not this contract. The `register_scope_unit_kind`/`rank_for` rank registry is WITHDRAWN.
**Deliberately unpinned (not oversights):** D-ANCHOR storage shape; `scope_value` persistence (transient by design, flip condition named in v2.5).
**Open D-Q1 watch items for program close:** structural nouns outside D-CF's closed 10-word set; intervening-punctuation / multi-token chains ("division, (i)").
**Traps that cost time:** CodeGraph indexes `main`, not branches — Read/Grep branch-divergent files. `(b)(1)(A)`-style prose pollutes the marker stream in fixtures. Never `git stash` (stack is shared across worktrees). Each worktree needs its OWN backend venv.
**History:** `-log.md`, 19 rounds — do not auto-load.

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
