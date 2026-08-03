---
id: "2026-08-04-defs-us-scoped-inline"
status: in_progress
current_role: planner
branch: claude/defs-us-scoped-inline
locked_by: "claude-code:sprint-manager"
locked_at: "2026-08-04"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US family 1 — scoped-inline definitions (no Definitions heading)

## Mandate

Capture the dominant US miss-class: definitions declared inside ordinary
substantive sections via `"As used in this section…"` / `"For purposes of
this section/subsection/chapter/part…"` — the English analog of the Hebrew
local-definitions path. 0% captured today in every state tested (dossier §2
family 1, §6 addendum). Lead states by measured frequency: OH 47%, UT 34.6%,
ME 39%, MO 33%, MT 27%, plus F1 presence in all 36 first-round states and
OR/TN/VT/RI/SC/PA/TX. These definitions are the canonical SCOPED case: the
scope unit named by the trigger (section/subsection/chapter/part) must be
stamped and enforced (assertions only within scope) via the core seam.

## Acceptance gates (program manager-defined)

- **U1 — Every convention variant in this family is captured**, with RED
  tests from real corpus rows of the lead states before implementation.
- **U2 — Scope is stamped correctly and enforced**: each captured definition
  carries the scope its trigger names; live-path proof both directions
  (in-scope mention links, out-of-scope does not) — built on the core seam.
- **U3 — Rules ship as registry modules** per the core seam spec; zero edits
  to shared modules.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for this family's signal patterns; every hit is captured or proven
  not-a-definition; any confirmed miss fails.
- **U5 — Nothing regresses**: baseline states (IN/CO/KY/LA/DE/ID/NJ/MI/MT/
  ND/NY/OK) capture rates hold; all existing tests green; zero-miss vs
  false-positive conflicts escalate per P-R2.
- **U6 — Measured before/after**: full-corpus capture-rate report for this
  family's signals (before vs after), same honesty standard as prior runs.

## Coordination

Core sprint `2026-08-04-defs-core-scope` owns scope plumbing + registry; read
its published `## Seam spec` from branch `claude/defs-core-scope` before
implementation; merge after core. Registry registrations are a
Planner-pre-declared append-only zone (program P-R5 merges). Misses found
outside this family's classes are REPORTED to the program manager for
routing, never fixed here. File-boundary conflicts escalate immediately.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings

Full reasoning in `2026-08-04-defs-us-scoped-inline-log.md` (append-only).

- **S-R1** — Core's `## Seam spec` is NOT yet published (`origin/claude/defs-core-scope`
  @ `5b93ef8`). RED tests are authored against two core-proof targets: the new
  pure rule module this sprint owns, and the pipeline live path
  (`run_definition_linking`, `pipeline.py:311`) asserting persisted
  `Definition.scope` + `USES_DEFINITION` edges. No test may be written against
  core's registry-registration API before the spec publishes.
- **S-R2** — Developers are fenced to the new rule module until core merges to
  `main`. Zero edits to `pipeline.py` / `extract.py` / `matcher.py` /
  `profiles.py` / `us_profile.py` / `sections.py` (gate U3).

## Next Steps

Full design rationale, the D1 convention inventory, D2 boundary verdict, and
D3 scope-unit gap table are in the panel log (`## 2026-08-04 — Planner`).
This section is the executable item list only.

### Phase A — buildable now (no core dependency; ruling S-R2 fences all of
Phase A to ONE new file; zero edits to `pipeline.py`/`extract.py`/
`matcher.py`/`profiles.py`/`us_profile.py`/`sections.py`)

1. **Create `backend/app/definition_links/rules/__init__.py`** (empty,
   new package) and **`backend/app/definition_links/rules/us_scoped_inline
   .py`** exposing:

   ```python
   def extract_us_scoped_inline_definitions(body: str) -> list[DefinitionCandidate]
   ```

   A pure function (`DefinitionCandidate` imported read-only from
   `app.definition_links.extract` — same dataclass `extract_local_
   definitions` already uses, so Phase B can hand its output straight into
   `pipeline.py`'s existing candidate list). Serves gates **U1**, **U2**
   (the scope-STAMPING half), **U3**. Full behavioral spec — trigger
   vocabulary, scope-unit mapping table, recognized defining idioms, the
   entry-boundary/no-over-split algorithm, and every excluded shape — is in
   the panel log's D1/D2 sections; the RED tests below are the executable
   version of that spec and are the actual source of truth for edge cases.

   Proven by (all currently RED with `ModuleNotFoundError`, pasted tails in
   the log):
   - `backend/tests/unit/test_us_scoped_inline_rules_trigger_axis.py` (13
     tests — trigger phrase recognition, scope-unit mapping, marker-prefix
     tolerance, trigger-after-term).
   - `backend/tests/unit/test_us_scoped_inline_rules_body_axis.py` (14
     tests — every idiom shape, multi-entry splitting, the two
     must-not-over-split cases, multi-scope-in-one-body).
   - `backend/tests/unit/test_us_scoped_inline_rules_negative_controls.py`
     (6 tests — false-positive bait, baseline-state no-trigger rows, the
     escalated PA boundary case).

   `.source_article_number`/`.source_chapter` stay `None` on every returned
   candidate (matches `extract_local_definitions`'s existing convention —
   the caller fills these in from the owning `Article`, Phase B's job, not
   this function's).

### Phase B — blocked on `2026-08-04-defs-core-scope` merging to `main` and
publishing its `## Seam spec`

2. **Register** `extract_us_scoped_inline_definitions` through core's
   per-jurisdiction rule registry for every `US-*`/`US-FED` code (never
   `IL`). Exact registration API is core's seam spec's call — not
   pre-decided here (ruling S-R1: no test was written against it before it
   publishes).
3. **Wire the registered rule into `pipeline.py` Stage 2's `else:` branch**
   (pipeline.py:436-442) so a US-profile article whose heading is NOT a
   recognized Definitions heading routes through the new rule instead of
   (or alongside, per core's seam) the Hebrew-only `extract_local_
   definitions`/`extract_adhoc_definitions`. **Critical provenance
   requirement**: use the SAME conditional pattern the `if is_definitions_
   section:` branch already uses at pipeline.py:434 — `if candidate.scope
   == "chapter": candidate.source_chapter = art.chapter` /
   `elif candidate.scope == "local": candidate.source_article_number =
   art.number` — NOT the current `else:` branch's unconditional
   `source_article_number = art.number` (every existing Hebrew else-branch
   candidate is `scope="local"`; this family's are not — a `"chapter"` or
   other-unit-scoped candidate wired through the old unconditional line
   would be silently mis-stamped). Serves gates **U1**, **U2** (both
   directions), **U3**.
   Proven by: `backend/tests/integration/test_us_scoped_inline_pipeline_live.py`
   (4 tests, currently RED with real assertion failures against the
   unmodified pipeline — go GREEN once this step lands).
4. **Confirm** `backend/tests/integration/test_us_scoped_inline_pipeline_baseline_regression.py`
   stays GREEN, unchanged, after step 3 (gate **U5**).
5. **Full-corpus before/after capture-rate measurement** for this family's
   trigger signal across all 53 jurisdictions (gate **U6**) — QA's sweep,
   unblocked once steps 2-4 land; flagged here as the next acceptance gate,
   not a Developer task.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Sprint opened. Worktree `/Users/nerya/LexGraph-wt/defs-us-scoped-inline` off
`origin/main` `83532fe`; own backend venv built and importing. Panel log
opened with the manager's verified architecture read (F1 root cause is the
`else:` branch at `pipeline.py:436-442` calling Hebrew-only
`extract_local_definitions`/`extract_adhoc_definitions` for US articles).
Core seam spec still unpublished — Planner proceeds per S-R1/S-R2.
