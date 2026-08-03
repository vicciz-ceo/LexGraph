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

## Panel dialogue

_(appended as roles report)_
