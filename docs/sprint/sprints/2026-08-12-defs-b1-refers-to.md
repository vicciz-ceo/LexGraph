---
id: "2026-08-12-defs-b1-refers-to"
status: planned
current_role: developer
branch: claude/defs-b1-refers-to
locked_by: "claude-code:developer"
locked_at: "2026-08-12T10:52:00Z"
last_agent: "claude-code:planner"
last_updated: "2026-08-12T10:46:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 1
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
lint: "PASS 108 2026-08-12T10:30:17Z"
previous_sprint: "2026-08-12-shared-extraction-t35"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: B1 defining-verb vocabulary — recover the "refers to" loss (issue #19)

## Mandate

GitHub issue #19. The B1 body-preamble recognizer's post-quote relation
vocabulary (`_POST_RELATION` in
`backend/app/definition_links/rules/us_body_preamble_b1.py`, lines 73-77)
omits "refers to"/"refer to". The Indiana row
`STATE_IN_T5_A28_C28_S5-28-28-3` defines "loan" as "(1) refers to a loan made
by the corporation..." — with no relation match the candidate falls through
`_candidate_is_substantive` to `_bounded_payload` and is dropped. It is the
SINGLE genuine loss found by the P-R15 deletion-side screen (evidence:
`docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/mr124/removal_relation_screen.jsonl`).

Director decision already taken: widen ONLY `_POST_RELATION` initially. The
sibling vocabularies `_ENUM_RELATION` (lines 78-81) and `_B1_QUOTE_MEANS_RE`
(lines 47-51) stay untouched unless separately justified AND separately
measured — widening `_B1_QUOTE_MEANS_RE` changes which bodies dispatch to B1
at all (bigger blast radius).

Follow-up sprint (not this one): issue #27 (`_TIGHT_IDIOM_RE` idiom widening
in `us_markers_boundary.py`), separately certified. Issue #26 deferred to its
own future sprint per standing manager ruling.

## Acceptance gates (manager-defined, director-approved 2026-08-12)

1. **The loss is recovered.** `STATE_IN_T5_A28_C28_S5-28-28-3` "loan" is
   captured and persisted again.
2. **Certified by execution (P-R11).** One full all-53 run; the actual delta
   vs the current certified output is adjudicated 100% — no hand-authored
   expected-change ledger. Expected shape: the Indiana recovery plus nothing
   genuinely lost; every other changed key individually adjudicated at ANCHOR
   granularity before reacting (decompose remove+add pairs on the same
   (row, term) first).
3. **Deletion-side screen (P-R15) re-runs clean.** The loan row clears; no
   new relation-adjacent removals appear.
4. **No regression.** Backend suite, frontend tests, and contract lint all
   stay green (current backend baseline on main: 12/12 in the narrowing-red
   file; full-suite count to be established by the Planner's baseline run).
   **Planner's baseline (2026-08-12, HEAD `7af67d8` + this pass's 2 new RED
   files): 1342 passed / 5 failed / 1347 collected — the 5 failures are
   exactly this pass's own new RED tests (see `## Next Steps`). Gate-4
   target post-fix: 1347 passed / 0 failed** (same collection count).
5. **Bounded.** Only `us_body_preamble_b1.py` may change in `backend/app/`,
   and within it only the `_POST_RELATION` widening. Module stays ≤300 lines
   (currently 298 — 2 lines of headroom). No edits to `us_markers_boundary.py`,
   `_citation_or_xref_context`, or the compound-idiom guard.
6. **Red before green.** A failing live-path test reproducing the loss is
   committed and proven RED before any fix exists. M-R107 applies: controls
   must be structural — novel constructed direct + live-persistence cases with
   unseen identifiers, no keying on row-ID/hash/section/term of the known row.

## Rulings in force

P-R11 (executed certificates only), P-R12 (rejection-count hard stop),
P-R15 (deletion-side screen is the primary gate), M-R107 (structural signals,
no jurisdiction/term/section keying), D-RECALL-FP (misses are the expensive
defect class), D-MAP (the (row, term) anchor is the product). Program doc:
`docs/sprint/programs/2026-08-04-definition-completeness.md`. Handoff:
`docs/sprint/programs/2026-08-04-definition-completeness-HANDOFF.md`.

## Known traps (from the program handoff — do not rediscover)

- `qa_g7_common.INTEGRATION_SHA` must be re-pinned and evidence regenerated
  whenever `backend/app` moves, or the G7 evaluator fail-closes without
  measuring anything.
- Worktree venv: use the main checkout's venv with `PYTHONPATH=.:backend`
  from the worktree root (verified safe); worktrees share ONE stash stack —
  `git stash` is forbidden.
- Raw-vs-ingest: fixtures are post-ingest by construction; never measure on
  raw text.

## Next Steps

### Item 1 — widen `_POST_RELATION` to recognize "refers to"/"refer to" (issue #19)

Add a `refers?\s+to`-shaped verb alternative to `_POST_RELATION`'s
alternation only (`us_body_preamble_b1.py:73-77`). Sibling `_ENUM_RELATION`/
`_B1_QUOTE_MEANS_RE` untouched; module stays ≤300 lines (298 today, 2 lines
of headroom); `git diff -- backend/app/` must touch only this file.

**Acceptance = gates 1-6 above.** RED tests (this pass, both proven RED for
the right reason — see the run tail in the Planner's report):
`backend/tests/unit/test_us_body_preamble_b1_refers_to_relation_red.py`,
`backend/tests/integration/test_us_body_preamble_b1_refers_to_relation_persistence_red.py`.
Gate-2 all-53 run commands, gate-3 deletion-side re-screen methodology, the
`qa_g7_common.INTEGRATION_SHA` re-pin/regen step, and the full loss-
reproduction + fix-simulation transcript: all in
`docs/sprint/sprints/2026-08-12-defs-b1-refers-to-log.md` (Planner pass).

## Stale-pin sweep

`grep -rniE "refers?\s+to|_POST_RELATION"` run across `backend/tests/unit/`,
`backend/tests/integration/`, `backend/tests/e2e/` (no hits), and
`frontend/src/components/__tests__/` (no hits). Seven pre-existing hits
outside this pass's own two new files, each individually traced (full
disposition and, for the one non-obvious case, an empirical before/after
simulation transcript — in the log doc). **Result: none re-pointed** — no
pre-existing GREEN test pins the current loss behavior in a way this
sprint's widening would break. Six hits never reach `_POST_RELATION` at all
(different module, or `heading_was_derived=False` so `preserve_substantive_
b1_candidates` is never invoked, or the bare recognizer function that never
references it); one (`test_mr121_b1_source_truth_red.py`'s
`R3_dotted_term_ignores_normalized_ordinary_reference` case) DOES exercise
the real B1 filter path and was verified empirically, in-process, against
both the unwidened and a simulated widened `_POST_RELATION` — stays
`absent` either way, because its "refers to" occurs a full sentence away
from the quoted term with no comma bridging the gap `_POST_RELATION`
requires.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Sprint opened 2026-08-12 by the manager off main tip `ffcbd83` (all of
PR #20 and the week's fixes merged; six related issues #21-#25/#28 closed
today with evidence). Planner to author RED tests per gate 6 and define the
single item per the mandate above.

2026-08-12 (Planner pass, off `7af67d8`). Loss reproduced live against the
real snapshot row and traced to its exact mechanism (see the log doc).
Single item defined; 2 RED test files committed (5 parametrized cases
proven RED for the right reason, 2 bounded negative controls proven GREEN
today and must stay green). Baseline established: 1342 passed / 5 failed /
1347 collected. Stale-pin sweep: none re-pointed. Gate-2/3 tooling located
and exact commands recorded in the log doc — the Developer must run the
all-53 acceptance and deletion-side re-screen themselves (P-R11: not run by
this Planner). Handing off to Developer.
