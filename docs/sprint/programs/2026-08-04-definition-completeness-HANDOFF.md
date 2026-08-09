# HANDOFF — definition-completeness program

Rewritten 2026-08-09 by the program manager, replacing the M-R122 Planner
handoff. That document is superseded: its central instruction — "independently
accept or reject the source correction" by re-reviewing all 207 keys before any
code may be written — was itself a re-entry into the loop the director
escalated. The decision has now been taken and the certificate is closed.

## Read this first: why the preamble sprint circled

The acceptance gate was self-referential. Item 7 required production to
reproduce a **hand-authored** expected-changed-key ledger exactly, zero missing
and zero extra. Four such ledgers were written in about 24 hours —
636 → 586 → 556 → 368 — each superseded by the next, because a ledger authored
in advance cannot predict the tail of a 592,334-record output. The tail is only
discoverable by running. M-R121 froze its 556-key ledger with the log line
"No all-53 run was made"; the first full execution disagreed on 207 keys, and
**188 of those were the ledger's own error** — enforcing it would have deleted
185 genuine statutory definitions.

Two aggravators. The certificate anchored at `5753e11`, which is not `main` but
a docs commit 167 commits ahead of it, so intra-sprint churn scored as
regression. And the 5-cycle safety valve never fired: 22 manager rulings
(M-R101…M-R122) rejected and replanned at Planner altitude, which does not
increment `qa_cycles` — it sat at 4 the whole time.

Binding consequences are program rulings **P-R11** (executed certificates
only), **P-R12** (rejection-count hard stop), and **P-R13** (a certification
item blocks only itself) in the program doc.

## Preamble sprint: state now

- Worktree `/Users/nerya/LexGraph-wt/defs-us-preamble`, branch
  `claude/defs-us-preamble`. Production tip `00b5b5c`.
- Items 1-6 plus the B1 corrections are Dev Complete. **Item 7 (D-PFP-400) is
  BLOCKED and is not this panel's to close — see below.**
- Two production corrections landed, each proven by an executed full-corpus
  run: `941661b` (physical-line-start continuation opener + source-order group
  dedup) and `00b5b5c` (digit-enumerator recognition). Module 298 lines.
- Gates reproduced by the program manager: focused direct+persistence
  **54 passed** (was 5F/49P), legacy raw provenance **13 passed**, runtime
  prototype **86 passed**, backend **24F / 1201P** (exactly the accepted
  23-marker + held-T35 ledger, zero new failures), frontend **165 passed** +
  `tsc --noEmit` clean.
- Executed all-53 acceptance: members 193,830 / `851e85dc…6af5a`, records
  592,357, archived `5753e11` baseline 592,694 / `f065d8ee…96b3f8`, and
  **345 changed = 341 removed + 4 added**, actual == certified ==
  `db52f060…bb1778`, missing 0, extra 0. Certificate:
  `mr118/qa/mr124/expected_changed.jsonl`.

### Item 7 is blocked on a component this panel cannot edit

A pre-QA dry run adjudicated all 400 regenerated D-PFP-400 tuples against
pinned source (8 independent auditors, 0 id mismatches): **314 genuine /
83 overrun / 2 false captures / 1 ambiguous — FAIL**. All three blockers were
re-verified directly in the shipped record set, and every one is a **shared
extraction** defect (`us_profile.py` term construction and boundary logic),
marked `fixable_in_b1: false`:

| Family | Example | Corpus size |
|---|---|---|
| wrong definiendum (heading + Pub. L. credit line as term) | `USC_T33_C36_S2319` | 818 (0.170%) |
| wrong definiens start (fired on the noun "means") | `STATE_IL_C735_A5_S2-1704` | — |
| truncated-definiens undercapture (49-char stub) | `STATE_NJ_T30_C1AA_S1AA-2` | floor 2,367 (0.49%) |
| right term, wrong body (pre-quote alias) | `STATE_CO_T25_A3.5_P1_S25-3.5-108` | 490 (0.083%) |

This is the deepest root cause of the whole loop: **D-PFP-400 gates the
preamble panel on a component the panel is forbidden to touch**, so no number
of preamble cycles could ever close it (program ruling P-R14). The families
become named shared-extraction items; under P-R13 the panel's feature work
merges on its own gates.

Two director questions are open and are the only things needing your input:
1. Truncated-definiens **undercapture** has no bucket in the D-PFP-400
   taxonomy. It is the mirror of the overrun carve-out. Informational like
   overrun, or a false capture? It governs ~2,367 records.
2. `new_fallback_byte_quality_ledger.jsonl` stamps `informational_only=true`
   on 50 rows that are all `qa_boundary_status: unreviewed`, and both
   confirmed false captures are members. The producer is claiming your overrun
   carve-out for rows QA never adjudicated. Confirm that only QA adjudication
   may convert a row to informational.

### What QA cycle 5 must and must not do

MUST: rerun the focused trio, the full evaluator, and the single all-53
acceptance against **production** (no `--prototype`) using
`mr124/expected_changed.jsonl`, plus the deletion-side relation screen.

MUST NOT: re-open the 207-key inventory or author a replacement ledger.
Disagreement with an executed certificate escalates to the program manager
with source evidence.

### Traps already cleared (do not rediscover them)

- `qa_g7_common.INTEGRATION_SHA` was pinned at `4fa9e7b…`, predating two
  production changes, so `validate_integration()` fail-closed on every
  D-PFP-400 run without measuring anything. It now tracks HEAD, and the
  evaluator asserts the invariant (ancestral, production frozen after it,
  committed evidence generated under the same pin). **Re-pin and regenerate
  whenever `backend/app` moves.**
- The worktree had no `frontend/node_modules`, which is why earlier cycles
  recorded the frontend gate as unrunnable. `npm ci` has been run there.
- The main venv at `/Users/nerya/LexGraph/backend/.venv` resolves worktree code
  correctly with `PYTHONPATH=.:backend` from the worktree root — verified.
  Measurements were not poisoned by this.

### Named residuals, quantified

- `STATE_IN_T5_A28_C28_S5-28-28-3` "loan": (1) **refers to** … is still
  removed; that verb is absent from the defining-verb vocabulary. One token
  closes it; deliberately deferred so it cannot invalidate the executed run.
- Deletion-side screen stands at 3 of 341 removals, 2 of which are the Indiana
  plural-repair tuples that the 4 additions replace.
- The physical-line-start rule is **formatting-bound, not structure-bound**: it
  depends on the scraper preserving paragraph breaks. Nine jurisdictions
  (NH/SC/PR/NY/UT/OH/IL/WA/NJ) have effectively no newlines, so suppression is
  inert there. Zero realized impact on the pinned corpus — the executed run
  lands exactly on 345 — but "works for future enacted laws" holds only for
  laws ingested with newlines intact.
- Boundary overrun runs at 83/400 = 20.8% of sampled tuples. Non-blocking
  under the director's carve-out, but it is the dominant byte-quality cost.

## Program state: read each contract from its OWN branch

The copies of other panels' contracts on this branch are stale from 2026-08-04
and will tell you every panel is `planning` with 0 items. That is an artifact.
Use `git show <branch>:docs/sprint/sprints/<id>.md`. Real state:

| Sprint | Status | Items | QA cycles | Unmerged prod |
|---|---|---|---|---|
| `defs-us-headings` | **qa-certified** | 15/15 | 4 | 727 lines |
| `defs-il` | review | 8/12 | 4 | 2,355 lines |
| `defs-us-pr` | in_progress (planner) | 14 dev-complete / 33 | 4 | 1,857 lines |
| `defs-us-scoped-inline` | in_progress (developer) | 0/1 | 2 | 796 lines |
| `defs-us-multiterm` | planning | 0/11 | 2 | 636 lines |

All five branches were last touched 2026-08-05. **6,371 lines of production
code sit unmerged.** `defs-us-headings` is QA-certified and has been waiting
five days. Three panels sit one cycle from the safety valve, so the
non-convergence dynamic is program-wide, not a preamble quirk — P-R12 applies
to all of them.

Merged and done: `defs-core-scope` (@ `06d67d8`), `defs-core-dispatch`
(@ `8524067`), `defs-core-follow-on-2` (@ `d783052`), `defs-us-markers`
(@ `7208dcf`).

## Ordered next actions

1. Run QA cycle 5 on the preamble sprint under the scope above.
2. Merge `defs-us-headings` — it is QA-certified and only waiting on a merge
   slot, which P-R13 no longer justifies withholding.
3. Resume `defs-il` (review, 8/12) and `defs-us-pr` (14/33), both at 4/5
   cycles: before spawning, apply P-R12 and state what would close each item.
4. Resume `defs-us-scoped-inline` and `defs-us-multiterm`.
5. The program-close D-CERT integration QA builds its certificate under P-R11:
   run first, adjudicate 100% of the actual delta, anchor at `main`.

## External repositories

`Vaquill-AI/open-us-law` is external; upstream PR #4 is closed/retracted. Only
the authorized `vicciz-ceo/open-us-law` fork may be used. No new fork write,
upstream PR, or Hugging Face publication is authorized. This handoff owns no
open-us-law worktree and no upstream PR; do not create or touch one.
