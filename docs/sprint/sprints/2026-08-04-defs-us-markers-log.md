# Panel log — sprint 2026-08-04-defs-us-markers

Append-only. Per program ruling P-R3 the Planner, Developer and QA speak with
one another THROUGH the sub-manager; every exchange is recorded here.
Escalations the panel cannot settle go to the program manager (and from there
to the director).

---

## M0 — sprint manager setup (2026-08-04)

**Manager (Opus/high).** Read in mandated order: program doc, recon dossier
(§2 family 3 + §6 addendum findings #1/#2 + per-jurisdiction detail), this
sprint's contract, `docs/sprint/repo-profile.md`. Also read the prior sprint's
`## Known limitations at sprint close` (2026-08-02-us-state-law.md:234-269) to
pin the boundary-precision residual this sprint inherits.

Workspace established per brief:
- Worktree `/Users/nerya/LexGraph-wt/defs-us-markers`, branch
  `claude/defs-us-markers`, based on `origin/main` @ `83532fe`.
- Own backend venv built (`python3.13`, `pip install -e '.[dev]'`, rc=0,
  Python 3.13.12) — the known worktree-venv trap avoided.
- `git config user.email` verified =
  `256402398+vicciz-ceo@users.noreply.github.com` before any commit.
- CodeGraph verified working (`codegraph` CLI on PATH; index at
  `/Users/nerya/LexGraph/.codegraph` was built against `main` @ `83532fe`,
  which is exactly this worktree's base commit — so the index is current for
  our base tree).

**Coordination state at spawn time.** `origin/claude/defs-core-scope` exists
with one commit (`5b93ef8`, planner lock + C5 baseline). Its contract declares
the `## Seam spec (published)` section as the core Planner's FIRST deliverable
but that section is **not yet published**. Per this sprint's brief the Planner
plans and authors RED tests meanwhile, and polls for the seam spec.

**Baseline measured by the manager in THIS worktree** (not inherited from a
doc): `backend/.venv/bin/pytest backend/tests -q` →
`641 passed, 18 warnings in 17.24s`. This matches the prior sprint's recorded
close-out number (641), so the tree is clean at `83532fe`. Any RED the Planner
introduces must be visible against exactly this number.

---

## M1 — manager rulings (standing, this sprint)

- **U-R1 — "Captured" means captured CLEANLY.** Inherited from the prior
  sprint's residual (2026-08-02 known limitations): a definition counts as
  captured only with the right term AND the right boundary. Explicitly NOT
  captured: 21,174-char swallow-the-neighbour bodies, sentence-fragment
  "terms", degenerate near-empty definitions (prior measured rates: corpus
  424/258,472 = 0.16% over 5,000 chars; TX letter-led recovered subset 17.33%
  degenerate). The Planner must express this as measurable RED assertions, not
  prose.
- **U-R2 — The fallback rewiring is a JOINT decision with the core panel.**
  `_extract_inline_quoted_definitions` (pipeline.py:246-289) is gated on
  `used_body_derived_heading` (pipeline.py:405/429) and is the single
  highest-impact fix in the program (VA 93% / WA 90% / FED 77% of misses
  rescuable). It lives in the exact code core's C3 gate is migrating. No
  Developer of this sprint touches it until both Planners have recorded the
  boundary IN WRITING in both contracts. Disagreement escalates to the program
  manager.
- **U-R3 — Correctly-empty classifier is a first-class deliverable.** Pure
  cross-reference sections ("The definitions in ss. 851.01 to 851.31 apply…"),
  `Repealed.`/`Expired.` bodies are correctly empty and must NOT be counted as
  misses — but the classifier must be defined by the Planner and independently
  verified by QA, not asserted by the Developer to explain away a residue.
- **U-R4 — P-R2 applies per conflict class.** Any sub-case where zero-miss
  can only be bought with a false-positive risk stops and escalates with real
  statute rows; the panel never silently picks a side.
