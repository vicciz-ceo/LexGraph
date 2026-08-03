# Sprint log — 2026-08-04-defs-us-multiterm (append-only)

Panel dialogue, manager rulings, and overflow from the contract. Newest
entries at the bottom. Nothing here is ever rewritten; corrections are new
entries.

---

## 2026-08-04 — Manager setup (Opus/high)

**Workspace.** Worktree `/Users/nerya/LexGraph-wt/defs-us-multiterm` created
from `origin/main` (`83532fe`), branch `claude/defs-us-multiterm`. Own backend
venv built (python3.13, `pip install -e '.[dev]'`) per the known worktree trap.
`git config user.email` verified =
`256402398+vicciz-ceo@users.noreply.github.com`. The main checkout
`/Users/nerya/LexGraph` is the program manager's and is NEVER written to by
this panel; it is read-only for CodeGraph queries only (the `.codegraph/`
index lives there and matches `origin/main`, which is our branch point).

**Core seam spec status at setup:** NOT yet published. `git show
origin/claude/defs-core-scope:docs/sprint/sprints/2026-08-04-defs-core-scope.md`
contains only the forward-reference to a `## Seam spec (published)` section,
not the section itself. Per the manager brief the panel plans and authors RED
tests meanwhile; Developers implement only non-shared-module work until core
merges to main, then rebase.

**Model policy for this panel** (P-R6, recorded per spawn): manager Opus/high;
Planner Sonnet/high always; Developer Sonnet/medium; QA Sonnet/high.
`model=inherit` forbidden. Haiku considered and rejected for every role so far
(none of the work is bounded-mechanical).

---

## Manager rulings (this sprint)

### M-R1 — CodeGraph invocation path in a worktree

The `.codegraph/` index exists only in the program manager's main checkout.
Every brief therefore instructs: run `codegraph explore "<question>"` with
`/Users/nerya/LexGraph` as the working directory (a read-only query — it
writes nothing), or use the `codegraph_explore` MCP tool with
`projectPath=/Users/nerya/LexGraph`. All *edits, test runs, and commits*
happen in `/Users/nerya/LexGraph-wt/defs-us-multiterm` only. Rationale: the
director's CodeGraph-first mandate must not be defeated by the worktree
isolation rule.

---

### M-R2 — Independent pre-sprint test baseline

Manager ran the evaluator on the untouched worktree BEFORE any panel work, so
U5 regressions are attributable:

```
cd /Users/nerya/LexGraph-wt/defs-us-multiterm && backend/.venv/bin/pytest backend/tests -q
641 passed, 18 warnings in 19.05s
```

`docs/sprint/repo-profile.md` claims 504 backend tests — **stale**, exactly as
its own 2026-08-02 note warns. **641 passed / 0 failed** is this sprint's
baseline. Any non-Planner-authored failure at QA time is a regression.

### M-R3 — Markers-boundary prep (manager, before Planner reported)

Manager read `origin/claude/defs-us-markers` contract read-only to be able to
arbitrate. Their U1 owns making zero-yield bodies yield candidates AT ALL
(no-marker inline-quote, mojibake, bare-(N), nested sub-clauses…) and their
U-R1 defines "captured" as captured CLEANLY (right term, right boundary).
That is the mechanics half of the VT `§ 3700` overlap. Our half is per-term
fan-out. The Planner's written proposal must therefore be expressed as a
contract ON THEIR OUTPUT (what a candidate for a multi-term clause looks like
when it reaches us), not as a claim on their internals.

---

## Panel dialogue

### 2026-08-04 — Planner spawn (attempt 1) — FAILED SILENTLY

Manager spawned a background Planner (Sonnet/high, agent id
`a4b9b7d3e93045935`); the tool returned "launched successfully" but the agent
never ran to completion and produced no work — the program manager observed
zero live children and no log entry. Recorded honestly rather than papered
over. **Lesson (manager):** a spawn acknowledgement is not evidence of a run,
and a background child is the only thing that resumes this manager; ending a
turn with no live child stalls the sprint. Attempt 2 runs SYNCHRONOUSLY.

### 2026-08-04 — Planner spawn (attempt 2), synchronous

**Model/effort — Sonnet/high; justification:** test authorship, live corpus
re-confirmation, and cross-sprint boundary negotiation need design judgment
and produce the artifacts every later gate rests on. **Haiku considered and
rejected** — none of this is bounded-mechanical; F6 is an FP-prone judgment
surface. `model=inherit` forbidden (P-R6). Brief carries: contract gates
U1–U6, recon dossier §2 families 5-6 + §6 addendum, the CodeGraph-first
mandate via M-R1, RED-before-green live-path test rules, worktree-only paths,
the no-corpus-in-tests rule, and the markers-boundary deliverable.
