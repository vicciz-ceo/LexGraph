# Expansion-wave precision sample — sprint 2026-08-20-defs-boundary-idioms

Read-only precision sampler pass. Quantifies Item 2 design (b)'s "expansion
wave" (log doc: "Planner pass 2, Item 2 design" — the 61/200-row seeded
sample, 122-new-term footprint on rows where the primary engine already
finds >= 1 entry). No `backend/`/`frontend/` files touched; all
pre-fix/post-fix/design-(b) comparisons run in-process via direct
(unmodified) function calls plus a pure post-hoc merge/filter function —
never `git checkout`/`reset`/`switch`/`stash` in this worktree.

Verified before starting: `git log --oneline -1` == `326f898` on
`claude/defs-boundary-idioms`.

_(placeholder — being filled in as the analysis completes)_
