# HANDOFF — Claude Code / US body-preamble M-R122

Written 2026-08-09 by the outgoing Planner. This is a **provisional WIP
handoff**, not a Developer-ready certification. Production was not edited.

## Open this checkout

- Worktree: `/Users/nerya/LexGraph-wt/defs-us-preamble`
- Branch: `claude/defs-us-preamble`
- Pre-handoff local SHA: `c2a871725221cd79fca89743d48feecf387bffee`
- Pre-handoff remote SHA: `c2a871725221cd79fca89743d48feecf387bffee`
- The pushed provisional WIP commit is the branch tip; verify with
  `git rev-parse HEAD origin/claude/defs-us-preamble` after `git fetch`.

Do not work from `/Users/nerya/LexGraph`. That main checkout is read-only and
contains the user's untracked `.claude/settings.json`; do not add, delete, or
modify it.

## Harness state

- Sprint: `2026-08-04-defs-us-preamble`
- Current role: Planner; status: `qa-fail`; QA cycles: **4/5**.
- Items 1–6 remain Dev Complete. Item 7 is provisional M-R122 evidence.
- Successor must independently accept or reject the source correction before
  spawning/acting as Developer. The next fresh QA is cycle 5; another failure
  reaches the safety valve and must be blocked/escalated, not silently cycled.
- Read, in order:
  1. `docs/sprint/sprints/2026-08-04-defs-us-preamble.md`
  2. `docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/DEVELOPER_READY.md`
  3. `docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/mr122/FULL_PROTOTYPE_AUDIT.md`
  4. `docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md` v2.7/v2.6.

## Production checkpoint and failure

Production is frozen at `c2a8717`. The only production file in scope is
`backend/app/definition_links/rules/us_body_preamble_b1.py` (279 lines, SHA
`c154e942e84a04e041bbc2e85defa01c1efd2569db6da95d945a6315e3c4a1da`).

Its retained all-53 acceptance run passed population/baseline guards but failed
the old certificate:

- 193,830 normalized B1 winners / `851e85dc…6af5a`
- 359 changes = 355 removals + 4 additions
- 202 M-R121 certified changes missing; 5 production changes extra
- artifacts: `/tmp/mr121-acceptance.XoddA3`

## Why M-R121's 556 certificate is invalid

The full 207-key raw-source audit has zero unclassified keys:

| Family | Keys | Binding source decision |
|---|---:|---|
| Explicit post-quote relation | 185 | preserve; old removal invalid |
| Explicit pre-quote alias relation | 3 | preserve; old removal invalid |
| Closing quote hid nondefinition | 14 | remove after quote-direction fix |
| Closing quote hid genuine definition | 5 | preserve after quote-direction fix |

The 188 explicit-relation removals contradict M-R121's own required semantics.
This is new raw-source evidence under the stated certificate-change exception;
forcing 556 would knowingly delete definitions. The provisional corrected
certificate is **368 = 364 removals + 4 additions**, canonical SHA-256
`49a9d3f71d124e19f085ded69d5fbaae269d8ecfc518cd8a9457a9d34e00933d`.

Durable source ledger:
`.../mr118/qa/mr122/mismatch_inventory.jsonl` — 207 rows, SHA
`707e6299a445a878e02302a0620735c87224804f5b7671321c87520106caad2c`.
Every row carries the full key, raw-row/excerpt hashes and text, old/corrected
predicate evidence, and both production/certificate directions.

## Completed full-prototype proof

The corrected runtime prototype completed over all 53 files / 2,038,247 rows;
there is no active corpus process.

- Prototype: 193,830 members / `851e85dc…6af5a`
- Prototype records: 592,334 / `9e6e0196…2ca8`
- Archived `5753e11` baseline: 592,694 / `f065d8ee…b3f8`
- Delta: 368 = 364 removals + 4 additions / `49a9d3f7…0933d`
- Certificate comparison: missing 0, extra 0, byte `cmp=0`
- Complete artifacts: `/tmp/mr121-prototype-corrected.20260809`
- Source-audit scratch: `/tmp/mr121-set-classification.rbq0Vj`

Durable proof is under `.../mr118/qa/mr122/`:
`full_prototype_summary.json`, `full_prototype_changed.jsonl`,
`certificate_correction_summary.json`, `mismatch_inventory.jsonl`, and
`FULL_PROTOTYPE_AUDIT.md`. The full-prototype ledger and corrected certificate
are byte-identical.

A redundant pre-fix prototype process was terminated after c2's retained run
and the semantic comparison made it unnecessary. Its directory
`/tmp/mr121-prototype.gvbybi` has no atomic result and is not evidence.

## Exact proposed one-file correction

After successor acceptance, edit only
`backend/app/definition_links/rules/us_body_preamble_b1.py`:

1. In `_quote_occurrences.continuation`, keep the 6,000-character nearest-prior
   quote lookback. Treat that quote as an opening delimiter only when its
   physical-line prefix since the last CR/LF is whitespace-only **and** the gap
   after it starts the numbered marker. Visible content before the quote proves
   it is a closer; it must not hide the next independent occurrence.
2. At `_groups()` return, source-order deduplicate exact group tuples. Do not
   alter matching, spans, relation text, or repair emission.

The verbatim helper code and port boundaries are in `DEVELOPER_READY.md`.
No other semantic mismatch exists. Group dedup changes zero pinned-corpus keys
but prevents duplicate direct candidates in an unseen dual-trigger law.

Never add source/row/term/hash/jurisdiction allowlists, identity exceptions, or
exact-sentence matches. Future-law behavior is mandatory; R8–R11 use novel
identifiers, terms, and wording.

## Focused gates

At c2, direct+persistence M-R121/M-R122 tests are intentionally **5 failed / 49
passed**. The runtime prototype is **86/86**; legacy raw provenance is **13/13**.
After the proposed one-file port require:

1. focused direct+persistence **54/54**;
2. legacy raw provenance **13/13**;
3. runtime prototype self-check **86/86**;
4. module `<=300` lines;
5. one production all-53 run **without** `--prototype`, exactly 368/364/4,
   `49a9d3f7…0933d`, missing 0, extra 0;
6. then the appropriate full backend/evaluator gate and fresh QA cycle 5.

Exact commands are in `mr118/DEVELOPER_READY.md`.

## Reproducible archived baseline

The runner is
`mr118/qa/measure_actual_production.py`. The durable recipe:

1. `git archive 5753e11 | tar -x -C "$BASELINE_SOURCE"` into a fresh temp root.
2. Run current production (or Planner proof with `--prototype`) with
   `--current`; this emits and validates `members.jsonl`.
3. Run the archived source with that exact `--members` file; never reselect.
4. Require baseline count 592,694 and SHA `f065d8ee…b3f8`.
5. Run `--compare` against `mr121/expected_changed.jsonl`.

Use the single fail-closed shell block in `DEVELOPER_READY.md`; it retains its
temp root on failure and deletes only that explicit root on success.

## Ordered resumption

1. Fetch, open the worktree above, and confirm local/remote tips and clean tree.
2. Verify `git diff c2a8717 -- backend/app` is empty.
3. Independently review the 207-key ledger, especially all 188 certificate
   invalidations, and accept/reject M-R122 explicitly at Planner altitude.
4. If accepted, run the c2 focused gates, make only the exact one-file
   Developer correction, and rerun gates in the order above.
5. Commit Developer work separately. Spawn fresh QA cycle 5; QA independently
   reruns production (not prototype), baseline guards, certificate comparison,
   and the relevant full suite.

## External repositories

`Vaquill-AI/open-us-law` is external. Upstream PR #4 is closed/retracted. Only
the authorized `vicciz-ceo/open-us-law` fork may ever be used, and no new fork
write, upstream PR, or Hugging Face publication is authorized here. This
handoff owns no open-us-law worktree and no upstream PR; do not create or touch
one while resuming this LexGraph task.
