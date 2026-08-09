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
  `claude/defs-us-preamble`. Production tip `941661b`.
- All 7 items Dev Complete. `status: review`, `current_role: qa`,
  `qa_cycles: 4`. QA cycle 5 owns the verdict.
- The one-file M-R122 port is landed: `us_body_preamble_b1.py` only,
  physical-line-start continuation opener + source-order group dedup,
  295 lines.
- Gates reproduced by the program manager: focused direct+persistence
  **54 passed** (was 5F/49P), legacy raw provenance **13 passed**, runtime
  prototype **86 passed**, backend **1199 passed / 24 failed** (exactly the
  accepted 23-marker + held-T35 ledger; zero new failures), frontend
  **165 passed** + `tsc --noEmit` clean.
- Single all-53 acceptance over 53 files / 2,038,247 rows: members 193,830 /
  `851e85dc…6af5a`, records 592,334 / `9e6e0196…22ca8`, archived `5753e11`
  baseline 592,694 / `f065d8ee…96b3f8`, and **368 changed = 364 removed + 4
  added**, actual hash == certified hash == `49a9d3f7…00933d`, missing 0,
  extra 0. The ported production output is byte-identical to the prototype.

### What QA cycle 5 must and must not do

MUST: rerun the focused trio, the full evaluator, and the single all-53
acceptance against **production** (no `--prototype`); then adjudicate the
regenerated D-PFP-400 400-tuple sample against source.

MUST NOT: re-open the 207-key inventory or the 368-key certificate. It is
executed evidence, independently re-adjudicated by four auditors (207/207
excerpt-integrity checks, 205 agreements). Disagreement with a closed
certificate is an escalation to the program manager with source evidence —
never a replacement ledger.

### Traps already cleared (do not rediscover them)

- `qa_g7_common.INTEGRATION_SHA` was pinned at `4fa9e7b…`, predating
  `c2a8717`, so `validate_integration()` fail-closed on every D-PFP-400 run.
  Re-pinned to `941661b`. The pin seeds the sample rank, so the old
  population/sample hashes (`08ca7a33…`, `880cdec8…`) are void.
- The worktree had no `frontend/node_modules`, which is why earlier cycles
  recorded the frontend gate as unrunnable. `npm ci` has been run there.
- The main venv at `/Users/nerya/LexGraph/backend/.venv` resolves worktree
  code correctly when invoked with `PYTHONPATH=.:backend` from the worktree
  root — verified, `app` imports from the worktree. Measurements were not
  poisoned by this.

### Named residual — pre-quote alias mis-bodied tuples

A third failure class M-R122's two-bucket taxonomy could not express: right
term, wrong body. Where the only preserving evidence is a PRE-quote alias, the
definiens sits before the quote while shared extraction harvests after it.
Verified in the acceptance record set for all three inventory members: CO
`25-3.5-108` "state report", NM `73-7-1` "assessment of benefits." and
"assessments for construction.".

These are **not** in the 368-key certificate — they are unchanged pre-existing
baseline behavior. Preserving them is correct at B1 altitude: rejecting a
genuinely coined term because the extractor mis-bodies it is exactly M-R121's
rule, which deletes 185 real definitions. Owner is shared extraction +
D-MT-E1, alongside the CO wrong-tuple control and T35.

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
