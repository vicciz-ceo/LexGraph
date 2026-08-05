# HANDOFF — definition-completeness program

Written 2026-08-05 at session conclusion, by the outgoing program manager,
for any successor model/session. Everything below is recoverable from git
and these docs alone — no conversation context is required or available.

## 0. Read these first, in this order

1. `docs/sprint/programs/2026-08-04-definition-completeness.md` — mandate,
   ALL director rulings (D-* sections), program rulings (P-*), sprint
   roster, core follow-on candidate lists.
2. `docs/sprint/programs/2026-08-04-definition-completeness-log.md` —
   append-only event log. The most recent ~40 entries are the last day's
   rulings, corrections, and measured findings. Newest entries are at the
   TOP of `## Events`.
3. Each sprint's contract + `-log.md` under `docs/sprint/sprints/` (listed
   below) — per-panel state, residual ledgers, delivery contracts.
4. `docs/sprint/sprints/2026-08-05-defs-core-follow-on-2-g7-merge-protocol.md`
   — the per-number merge verification protocol for the core merge.

## 1. CRITICAL session-boundary facts

- **Every agent id in these logs is DEAD.** Agent ids (`a...`-style) are
  session-scoped. Do not SendMessage them; do not wait for their reports.
  Spawn fresh managers per panel; each contract + log is a complete brief.
- **All durable state is on pushed branches and committed docs.** Every
  panel operated under commit-before-spawn and push-always discipline;
  last-known SHAs below, but `git fetch --all` and trust origin.
- Two measurements were IN FLIGHT (uncommitted) at conclusion and are
  presumed lost; both have their full method recorded and are cheap to
  respawn (see §4, items A and B).
- The `israeli-laws-wiki` corpus (`/Users/nerya/AI for others/...`) is
  READ-ONLY. The US parquet corpus is in the HF cache
  (`~/.cache/huggingface/hub/datasets--vaquill--open-us-law`). No test
  reads corpora — byte-verified vendored fixtures only.
- Worktrees under `/Users/nerya/LexGraph-wt/` each need their OWN backend
  venv (main venv imports main checkout). Never `git stash` (shared
  stack). Never `git add -A`. Noreply git identity required (GH007).
- **NY parquet trap (bit 7 sessions/agents):** NY text in parquet is
  literal `\n` (escaped); the fix is at INGEST
  (`ingest_us_statutes.py` ~line 237). Any measurement on raw parquet
  text manufactures phantom NY misses. See memory file
  `lexgraph-raw-vs-ingest-trap.md` and log entries.

## 2. Per-stream state (last known; trust origin over this table)

| Stream | Branch @ last-known SHA | Status |
|---|---|---|
| Headings | `claude/defs-us-headings` @ dbbce7d | **QA-CERTIFIED.** 860/0, recall 21,080/22,228 = 94.84%, ledger L1–L12 dispositioned. Awaits merge slot. Post-merge item 16 = `includes` widening. |
| IL (parent) | `claude/defs-il` @ ca62964 | **REVIEW.** Byte-identical to reviewed tip 24c88a6 (+2 doc commits M32/M36 only). Six-item residual director-visible. Awaits merge slot. |
| IL certification | `claude/defs-il-certification` @ f72af1f | **ACTIVE, mid-C4.** Denominator pinned (93,509 spans); 'ltr' over-capture FIXED; next: sibling `_split_marker_less_prose` audit, remaining clusters, C5 re-run. Manager must be respawned to continue. 32MB manifest merge decision documented in its contract's merge notes. |
| Multiterm | `claude/defs-us-multiterm` @ 1c0c8cd | **REVIEW-READY.** 14/815, all failures owned (13 cross-panel, 1 deferred). U2 partial pending core G10 merge; U4 → certification. |
| Scoped-inline | `claude/defs-us-scoped-inline` @ 21e0c45 | Fully green (857/0/1 xfail tripwire). **QA cycle 4 (final pass) was launching** — respawn it per the manager's committed brief in the sprint log; close statement pre-agreed (log). WATCH: R3 must be recorded in their sprint docs before merge (see §5). |
| Markers | `claude/defs-us-markers` @ 422d469 | Build done, 24/885 all owned. VA 4.4/WA 6.4% zero-yield; MI 2,711/NY 1,319 captured. Remaining: unpinned merged-code defects (FED trailing-annotation architecture, MN idiom gate), U-R13 re-check at persisted altitude (procedure in log M40), final QA. Merge slot = 2nd. |
| Preamble | `claude/defs-us-preamble` @ 8ad3052 (+ successor doc commits) | Mid P-FP corrective cycle: Planner was adjudicating 6 cycle-8 negatives (2 must be re-authored to ASSERT capture — they currently force violating D-MT-E1); then Developer (option-c root causes + M-R53 comment fix BLOCKING + 386→300 split); then QA definition-granularity FP re-measure = certification gate. Merge slot = 3rd. |
| PR | `claude/defs-us-pr` @ ed8a295 | P1 LIVE (633 Definiciones rows, 5,720 candidates). M-R20 rulings issued; **a Planner pass was in flight**: corpus-enumerated footer families + leading-`\b` fix + abbreviation-period class characterization; then bounded Developer; then close. Gate table P1/P5 PASS, P2/P3 PARTIAL, P4 HELD (18c now unblocked by gate-2 proof). |
| Core-2 (shared) | `claude/defs-core-follow-on-2` @ b52aed5 | **837/0, 11 gates landed** (G1,G2,G3-main,G4,G5,G6@7-of-8,G8,G9,G10,G12,G13). G3-sibling NO-GO (measured); G11 DEFERRED with data (202-row debt unspent). **Merge blocked on exactly one item: the G8 reverse-order displacement check** (§4-A). |
| Core-3 accumulator | recorded in program doc + log | ~14 evidence-backed items. Anchor: citation-vs-marker discriminator (context-API + corpus-wide-shape-aggregation constraints binding). Priority: IL `sections.py` whole-file gap (100 files, religious-courts law); splitter newline-assumption (12-jurisdiction census, PRELIMINARY — re-run post-ingest). |

## 3. The merge queue (nothing has merged yet)

Order (program-ruled): **core-2 → markers → preamble → then** headings,
scoped-inline, multiterm, IL-parent, PR (order among these at successor's
discretion; IL-certification merges LAST, after deciding its 32MB manifest
question).

Per-merge checklist (non-delegable program-manager work):
1. `git fetch`; name-only diff; materialize full three-dot diff to a
   scratchpad file and READ it (full reads for shared persistence/parsing
   code); risk-grep (`fetch|axios|/api/|Authorization|Bearer|localStorage|
   process.env|...`).
2. Run the **G7 merge protocol** file (per-number recipes, expected
   directions — e.g. markers' held FED RED goes green at core-2 merge;
   GA 2,794 must not drop).
3. **Schema migration**: core-2 adds `heading_breadcrumbs`
   (additive-nullable, raw-DDL reversible). Every panel rebase must run
   `upgrade()` in its own worktree venv before its suite, or
   migration-absence reads as phantom regression.
4. Cross-panel watch items at specific gates (§5).
5. Own live evaluator run on the merged tree
   (`backend/.venv/bin/pytest backend/tests -v` + frontend tests +
   `tsc`); main venv refresh if deps changed.
6. Reviewed branches must merge EXACTLY what was reviewed (byte-equality
   principle, program law — the IL split is precedent).

## 4. Two lost-in-flight measurements to respawn FIRST

- **A. Core-2 G8 reverse-order displacement check** (the ONLY merge
  blocker for the whole queue). Question: does any same-key pair exist
  where a good long candidate persisted first and a degenerate short one
  arrives second, so `_is_tighter_containment` REPLACES good with
  degenerate? Pass condition: zero degrading firings (exhaustive
  hand-judgment if population is small). If any fire: amend G8's
  criterion BEFORE merge. Method + rationale: core-2 log (the manager's
  Phase-9 blocker entry).
- **B. PR footer/`\b`/abbreviation-class Planner pass** — spec is fully
  written in PR log M-R20; respawn bounded.

## 5. Cross-panel watch items (enforce at the named gate)

- **R3 "Taken"** (`STATE_OR_T41_C496_S496.716`, plain-`means`, from
  multiterm's E3): scoped-inline acknowledged custody in reports but it
  appears NOWHERE in their sprint docs. R3's own text says silence isn't
  closure. Enforce disposition at scoped-inline's merge-readiness check.
- **G3-HEAL two-layer** (markers): at core-2 merge, on the merged tree,
  assert BOTH the WA swallows are gone AND markers' clean candidates are
  the ones PERSISTED. Instrument: markers' held RED
  `test_us_markers_qa_q1_wa_newline_collapse_swallow`.
- **Multiterm findings 1/1b** close only after core G10 is in the merged
  tree (they're currently held REDs).
- **IL containment REDs (2)** close on core-2 G9 (breadcrumbs) reaching
  the merged tree + IL-side `scope_value` fix (IL's own, sequenced after
  their QA — see IL log M20/M27).
- **PR Título/Subtítulo/Subcapítulo** (19 rows): family-buildable after
  core-2 merge via G6's ScopeKindRule kind-strings; cite G6's VA "title"
  precedent.
- **Preamble's 3 markers-dependency REDs** go green at the markers merge.
- **NE extraction** (markers) is blocked until preamble merges
  (recognition rule lives there).
- **Headings L1** (WA reference edge) was re-scoped: closes on G11 —
  which is DEFERRED — so it stays a named residual for the certification.

## 6. The program close (director-ruled: D-CERT)

- **IL track**: running (see §2). Continue its C4 loop → C5 re-run →
  merge decision.
- **US track**: NOT yet commissioned. It is the program-close integration
  QA, to be commissioned by the program manager ON THE MERGED TREE after
  the queue completes: signal-agnostic denominator (seed: preamble's
  P-R7 91,878-hit denominator + the shape tables in the preamble log),
  every candidate classified captured / fixed / proven-not-a-definition /
  director-named residual, committed re-runnable artifact. IL's contract
  sets binding precedents (executable predicates, per-(row,term)
  judgment, measured error rates, exhaustive+disjoint backbone test).
- Final deliverable to the director: aggregate verdict against the
  absolute zero-miss bar + the enumerated residual list.

## 7. Program laws (all recorded in program doc/log; the short index)

D-CERT (inverted certification close) · D-INCLUDES (includes-family
captured, naive anchor; PA guard targeted-literal only) · D-S15
("this subsection" = outermost) · P-FP (FP granularity follows rule
output; forwarding defs are genuine) · P-ALT (persisted layer is the
contract; candidate pins only for own-module emission) · two-altitude pin
law · M18 (denominators from the entry line) · P-R10 (probe sanity;
probe ARGUMENTS are part of the claim) · differential-vs-absolute rule ·
dispatch-precondition rule (a count claims a mechanism only if gated on
its real dispatch precondition) · fork-point-diff law (diff a Developer
against ITS OWN fork point) · emission≠correctness (the three-polarity
root cause) · "an assertion isn't specified until it has failed against
the defect state" · positional/structural tests survive the corpus,
magnitude thresholds don't · review-branch byte-equality · liveness
probes on long-quiet critical-path agents are part of the job.

## 8. Resumption recipe

1. Read §0 documents. `git fetch --all`.
2. Respawn §4-A (core-2 G8 check) immediately — it gates everything.
3. Respawn one manager per ACTIVE stream (IL-cert, scoped-inline QA4,
   preamble cycle, PR Planner pass, markers final QA), each briefed from
   its contract + log tail; managers spawn their own role agents.
   Delivery protocol: manager commits its own (new) agent id to the
   sprint log's delivery section; briefs point to that committed section
   ("if committed id and briefed id disagree — don't send, report").
4. When core-2's blocker clears: run the §3 merge queue with the
   checklist, enforcing §5 at each gate.
5. Commission the US certification (§6) on the merged tree.
6. Report to the director only at milestones, escalations, or genuine
   decisions (director's standing instruction: managers run
   autonomously; program manager intervenes on escalation, cross-panel
   arbitration, rulings, and merges).
