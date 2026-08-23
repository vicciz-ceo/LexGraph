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

### Item 7: D-PFP-400 restated at anchor granularity — no longer blocked

A pre-QA dry run adjudicated all 400 regenerated tuples against pinned source
(8 independent auditors, 0 id mismatches). Under the original body-text rule it
read 314 genuine / 83 overrun / 2 false / 1 ambiguous = FAIL, and all three
blockers were shared-extraction defects this panel cannot edit (P-R14).

The director then ruled **D-MAP** (the product is a map of WHERE definitions
are; an AI consumer can read the section once pointed at it) and
**D-RECALL-FP** (prefer a small false-positive rate over a large miss on terms
and references). Re-read at ANCHOR granularity — is `(row, term)` a real
definition location? — the same 400 give **399 correct anchors / 1 phantom**.

| Family | Under D-MAP | Size |
|---|---|---|
| phantom / wrong TERM (heading + Pub. L. credit as definiendum) | **blocking** | 944 = 0.159%, + 179 citation family |
| undercapture (49-char stub) | informational | floor 2,367 (0.49%) |
| wrong body (pre-quote alias) | informational | 490 (0.083%) |
| boundary overrun | informational | 83/400 = 20.8% |

Under D-RECALL-FP the 0.159% phantom rate is **named tracked debt, not a merge
blocker**: relative to `main` neither B1 module exists, so this branch strictly
increases anchor recall. Item 7 is Dev Complete again. The **deletion-side
screen (P-R15) is now the primary gate**, because a miss is the expensive
defect.

Both director questions from the previous handoff are now answered and closed:
undercapture is informational (D-MAP), and only QA adjudication may convert a
row to informational — the producer no longer self-stamps `informational_only`,
and a contract test enforces it.

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

- ~~`STATE_IN_T5_A28_C28_S5-28-28-3` "loan"~~ CLOSED 2026-08-20 by sprint
  `2026-08-12-defs-b1-refers-to` (issue #19): `_POST_RELATION` widened
  (`86fccfb`), certified delta exactly 1 record, QA cycle 1 PASS. Trap found
  en route: `measure_actual_production.py` baseline runs MUST pass
  `--current` too — the flag asymmetry manufactured a phantom 4,255-record
  delta (see that sprint's investigation.md; P-R16 family).
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
- 2026-08-23, sprint `2026-08-20-defs-boundary-idioms` (issue #27, PR #30):
  `_TIGHT_IDIOM_RE` widened + fallback guard merged per-term + dedup fix.
  Certified +27,568 anchors / 0 genuine losses (cc51c49 executed run,
  byte-identity chain). Tracked debt: next-entry bleed, 19 enumerated
  single-letter wave phantoms, mis-paired-quote FP class, FX7 remainder
  (~60 marker-family + ~40 citation-noise). LESSON (single-letter rule,
  reverted): a zero-collateral claim measured on ONE population does not
  transfer to other populations the same rule reaches — the `^[A-Za-z]$`
  filter was clean on the wave but deleted a genuine pre-existing anchor
  (NV 484B.307 "X"). Measure every population a filter change can touch.

## Program state: read each contract from its OWN branch

The copies of other panels' contracts on this branch are stale from 2026-08-04
and will tell you every panel is `planning` with 0 items. That is an artifact.
Use `git show <branch>:docs/sprint/sprints/<id>.md`. Real state:

| Sprint | Status | Items | QA cycles | Unmerged prod |
|---|---|---|---|---|
| `defs-us-headings` | **merged into this branch @ `cdfa699`, in PR #20** | 15/15 | 4 | — |
| `defs-il` | review | 8/12 | 4 | 2,355 lines |
| `defs-us-pr` | in_progress (planner) | 14 dev-complete / 33 | 4 | 1,857 lines |
| `defs-us-scoped-inline` | in_progress (developer) | 0/1 | 2 | 796 lines |
| `defs-us-multiterm` | planning | 0/11 | 2 | 636 lines |

The four remaining branches were last touched 2026-08-05 and hold **5,644
lines** of unmerged production. Three panels sit one cycle from the safety
valve, so P-R12 applies to all of them.

### Read this before merging any two panels (P-R17)

Merging headings into preamble registered 3 `US-*` HeadingRules that had NEVER
registered before — nothing imported the package until `rules/__init__.py`'s
`pkgutil` auto-discovery reached it. Recognition then preempted the
body-preamble derived path and silently switched off two separately-gated
extractors: the inline-quoted fallback (SD `11-9-10`, 1 -> 0 definitions) and
local-scope extraction (KS `46-225`, 5 -> 1 tuples). **Neither panel could see
it — each half is inert without the other**, and the interaction lands on
`main` when the SECOND branch merges, so sequenced single-panel PRs only defer
it. Measure co-firing panels on the MERGED tree before either merges.

Two more traps this exposed, both now ruled:

- **P-R16** — `measure_actual_production.capture()` REIMPLEMENTS pipeline
  Stage 2 rather than calling it. After a pipeline fix it kept modelling the
  old program and reported a 3,311-record net loss that did not exist. If you
  change the pipeline, mirror it into the harness or the numbers are fiction.
- Decompose removals at ANCHOR granularity before reacting. The first
  corrected run showed 1,170 removals; 826 were remove+add pairs on the same
  `(row, term)` — text changed, definition kept. Genuine anchor losses: 8.

Merged and done: `defs-core-scope` (@ `06d67d8`), `defs-core-dispatch`
(@ `8524067`), `defs-core-follow-on-2` (@ `d783052`), `defs-us-markers`
(@ `7208dcf`), `defs-us-headings` (in PR #20).

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
