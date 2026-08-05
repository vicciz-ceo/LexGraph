# Sprint log — 2026-08-05-defs-core-follow-on-2 (shared-module owner)

Append-only. Manager: claude-code panel manager (Opus/high). Branch
`claude/defs-core-follow-on-2`, worktree
`/Users/nerya/LexGraph-wt/defs-core-follow-on-2`, forked from main @ 8c49498.

---

## Phase 0 — manager intake (2026-08-05)

Read: sprint contract (G1–G7), program doc (P-R1..P-R10, D-* rulings, M18,
D-CERT), seam doc structure + the three load-bearing prior-art sections for
G6 (v2.1 §1/M9 enumerated scopes, v2.5 `scope_value` transient-by-design,
v2.6 §2/M-D2 `ScopeKindRule`). Seam doc's latest published version is
**v2.7** — G6's seam change therefore publishes as **v2.8**, append-only.

### Manager verification of the six candidates (CodeGraph + direct read)

All six defect sites confirmed to exist in main's code as described. This is
manager-level sanity only; the Planner still owns full verification per the
contract ("verify, then build").

| Gate | Site (main @ 8c49498) | Confirmed defect |
|---|---|---|
| G1 | `us_profile._leading_quote_candidate` (us_profile.py:598) vs `_extract_inline_quoted_definitions` (:551) | two quote-extraction paths, padding treatment differs — Planner byte-verifies the exact `.strip()` asymmetry |
| G2 | `_US_UNIT_MARKER_RE = re.compile(r"\(([A-Za-z]+\|\d+)\)")` (us_profile.py:1075) | matches **parenthesized tokens only** — period-style top-level markers (ME `2-A.`/`F.`, AZ `J.`, VA `A.`) are invisible, so `resolve_unit_path` returns `()`. Direct mechanical cause of the S-R16 empty-path degrade |
| G3 | `_split_into_numbered_blocks` (us_profile.py:346) | final `if current is not None: blocks.append(current)` appends **all remaining lines to end-of-text**; no terminator detection. Unbounded last entry confirmed |
| G4 | `resolve_unit_path` (us_profile.py:1145) — the `replaced` loop, lines ~1230-1236 | any shape-matching token **truncates the stack** (`stack = stack[: i + 1]`) and overwrites that step's value. A citation pin-cite `(C)` is indistinguishable from a genuine marker, so it resets the stack. Ladder selection additionally reads only the FIRST parenthesized token (already a named limitation in the docstring) |
| G5 | `RuleContext(..., unit_path=())` at **us_profile.py:1421 AND profiles.py:256** | hardcoded in **both** profiles (US and Hebrew) — G5 is a two-site fix, not one |
| G6 | `ScopeKindRule.detect: Callable[[str], str \| None]` (registry.py, v2.6 §2) | returns a KIND only; no seam carries a scope VALUE from a rule |

### Manager finding that materially re-scopes G6 (recorded before planning)

**M9's tuple-valued scope machinery is ALREADY LIVE — G6 is smaller than it
looks.** Verified on main, not assumed:

- `DefinitionCandidate` (extract.py:72-78) already types `source_article_number`,
  `source_chapter`, and `scope_value` as `str | tuple[str, ...] | None`.
- `matcher` already compares set-valued scopes: `_value_matches` is used by
  the chapter/local branches (matcher.py:170/172/176), and the
  subsection-level comparison normalizes to a tuple
  (`allowed = expected if isinstance(expected, tuple) else (expected,)`).

So G6 must NOT re-build tuple scope support. The genuine gap is only the
**rule → value delivery path**: no registered rule can hand a scope VALUE
(enumerated tuple or range) to the candidate. Planner 3 is briefed to
byte-verify this before designing, and to build only the missing seam.

This check was run precisely because the seam doc has a track record of
spec/code divergence — v2.5/I11 found the specified `scope_value` COLUMN was
never built. Same class of risk, checked rather than assumed.

### Sequencing decision (manager)

Three Planners in parallel, clustered so each owns a disjoint code surface
and no two designs collide textually:

- **plan1 — G2 + G4** (both are `resolve_unit_path`; contract requires one
  designer so the fixes compose rather than collide). Front-loaded: highest
  leverage, most blocked-upon.
- **plan2 — G3 + G1** (both `us_profile` extraction-side; G3 front-loaded —
  it holds the markers panel's RED and blocks preamble's 27,209-row
  re-measure).
- **plan3 — G5 + G6** (both seam/registry-side; G6 is design-heavy and its
  seam-doc v2.8 needs manager review time, so it starts now).

Coupling risk identified and briefed out: G5 plumbs `resolve_unit_path`'s
result into `RuleContext`, whose BEHAVIOR plan1 is changing. Plan3 is
instructed that G5's tests must exercise the plumbing (that a real path
arrives) and must NOT pin resolver internals that G2/G4 legitimately change.

### Operational facts pinned for all agents

- Corpus: `/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`
  — 105 parquet files = **53 `us_*_statutes.parquet` + 52 constitutions**.
  Prior census figures (2,038,247 / 2,045,897 rows) come from the 53
  statutes files; measurements must state which glob they used.
  israeli-laws-wiki corpus is READ-ONLY and off-limits to tests.
- No test reads the corpus (program rule): byte-verified vendored fixtures.
- Each role agent: OWN worktree + OWN backend venv (main venv imports the
  main checkout's code). Never `git stash`; never `git add -A`.

---

## Spawn ledger (append-only)

| # | Role | Gates | Model/effort | Branch / worktree | agentId | Outcome |
|---|---|---|---|---|---|---|
| 1 | Planner | G2 + G4 (resolver) | Sonnet/high — P-R6 Planner is always Sonnet/high; Haiku considered: no, open-ended design over a shared parsing surface six panels depend on | `claude/defs-core-follow-on-2-plan1` / `...-wt/defs-core-follow-on-2-plan1` | `a3dda557ae5eb694e` | running |
| 2 | Planner | G3 + G1 (extraction) | Sonnet/high — P-R6; Haiku considered: no, G3's boundary design is open-ended and three panels are blocked on it | `claude/defs-core-follow-on-2-plan2` / `...-wt/defs-core-follow-on-2-plan2` | `aae653f9956064e9f` | running |
| 3 | Planner | G5 + G6 (seam) | Sonnet/high — P-R6; Haiku considered: no, G6 authors a seam version the rest of the program builds against | `claude/defs-core-follow-on-2-plan3` / `...-wt/defs-core-follow-on-2-plan3` | `a2987562ee6ff3a61` | running |

| 4 | Scout (read-only) | G7 baseline reproducibility | Sonnet/high — tracing measurement recipes across divergent branches; a misclassified number produces a false G7 pass; Haiku considered: no | read-only, no branch | `a682047c7fe5507af` | running |

### Manager-identified G7 ambiguity (scout #4 commissioned to resolve it)

G7 requires the panels' certified numbers to "re-reproduce **on this
branch**." But this branch contains **no panel code** — panels are fenced
out of shared modules (P-R1) and their rule modules are unmerged. A number
certified WITH panel rules registered therefore cannot reproduce here even
in principle; only numbers that are pure corpus/shared-code measurements
can. Classifying a panel-code-dependent number as reproducible here would
manufacture a false G7 pass.

Rather than guess or spend a program-manager round-trip on an unanswered
question, scout #4 resolves it with data: per certified number (markers'
zero-yield table, preamble's 23,617 + the 27,209 fallback-affected rows,
GA 2,794) it traces the exact recipe and denominator, classifies it as
reproducible-here / needs-unmerged-panel-code / untraceable, and proposes
the concrete G7 verification protocol. Escalation to the program manager
follows only if G7 as written turns out to be unachievable for some number.

### Briefing notes carried into all three Planner spawns
- Own worktree + own venv (main venv imports main checkout code); verify
  noreply `user.email` before first commit; never `git stash`, never
  `git add -A`.
- CodeGraph-first; index reflects `main`, so panel-branch evidence is read
  directly (`git show` / `git grep` on the panel branch).
- Vendor equivalent REDs rather than cherry-picking panel commits
  (authorship stays clean); no test reads the corpus; fixtures name the real
  row they were copied from.
- P-R7 signal-agnostic denominator, P-R10 probe sanity (reproduce a known
  number first), M18 entry-LINE denominators, measured before/after.
- Contract duty carried explicitly: flag any candidate that should NOT be
  built, with evidence, rather than silently dropping or over-building it.
- Per-gate cautions briefed: G2/G4 pull in opposite directions (widen
  recognition vs. trust fewer tokens) and must share one token-acceptance
  story; G3's terminator rule can truncate genuine final entries (measure
  BOTH sides) and affects every US jurisdiction because the splitter runs
  before registered rules; G1 changes a term string that is also a matching
  key; G5 is a two-site fix including the Hebrew regression surface; G6 is
  seam + ONE proof only (the headings panel's rules stay theirs).
- Cross-planner coupling briefed out: plan3's G5 tests prove the PLUMBING
  and must not pin resolver internals plan1 is legitimately changing.

---

## Phase 0b — program-manager clarification (2026-08-05)

Phase 0 intake ACCEPTED by the program manager. Seam **v2.8 append-only**
confirmed as G6's publication target. Two binding updates recorded below;
they supersede the Phase-0 ambiguity note above (append-only convention —
the earlier text stays, read this as its resolution).

### G7 CLARIFIED — binding form (program manager)

G7 as originally written conflated two obligations. Binding reading:

- **(a) ON THIS BRANCH.** The existing suite stays green (baseline-path
  behavior doesn't regress), and each gate carries its OWN measured
  before/after on the real corpus. Panel-certified numbers whose recipe
  involves unmerged panel rules are **not reproducible here even in
  principle** — this sprint is NOT required to reproduce them, only to
  avoid touching their baseline-path inputs in unintended ways.
- **(b) ON THE MERGED TREE, AT MERGE TIME.** No panel-certified number moves
  except in its INTENDED direction: markers' held RED goes green, DC moves
  UP, preamble's fallback rows become re-measurable, GA's 2,794 does not
  drop. **This verification belongs to the program manager's merge
  checklist, not to this sprint's close.**

**Consequence for scout #4 (agentId `a682047c7fe5507af`):** its deliverable
becomes a per-number VERIFICATION PROTOCOL the program manager can execute
at merge — per number: recipe (script + branch + command + denominator,
traced not inferred), P-R7 signal-agnostic assessment, classification
(reproducible-on-branch / merged-tree-only / untraceable), **expected
direction under this sprint's fixes and which gate drives it**, and the
concrete merge-time step with its pass condition. Anything untraceable
**escalates to the program manager with the full trace attempt attached**;
an honest "untraceable, here is how far I got" is a valid outcome, a
plausible reconstruction presented as traced is not.

The scout stays READ-ONLY (it is not a writer in any worktree, and three
planner worktrees have live writers). It returns the protocol as finished,
directly-committable prose; **the manager commits it** into the sprint docs
as the artifact the program manager executes. This preserves one-writer-per-
worktree while still producing the committed artifact requested.

### G4 — fourth verified latch case (relayed to plan1)

Oregon **`STATE_OR_T22_C238_S238.300`**: `resolve_unit_path` latches onto
"under subsection (1) of this section" and returns top-level digit `'1'`
instead of the structural `(2)`.

Manager note carried into the plan1 brief: this is a **structurally
different shape** from the SC/TX/ME cases. Those are citation pin-cites (a
section number followed by a parenthesized token); the Oregon case is an
ordinary in-prose CROSS-REFERENCE containing no citation-looking section
number at all. **A discriminator built only around citation shapes will not
catch it** — plan1 must cover both shapes or state plainly which it does not
cover and why. Also flagged: this case yields a **non-empty WRONG path**,
not an empty one (the class the program doc calls worse than the empty-path
S-R16 class), so G4's before/after must distinguish "empty path" from
"non-empty wrong path" — collapsing them into one number would hide the
fix's actual effect.

Scratchpad access to the scoped-inline pass-7 Planner's corpus-scale
corruption-class scripts (prefix `si_cycle2_scout1_` and later
scoped-inline-era prefixes) **explicitly authorized by the program manager**,
as a named exception to P-R9; read-only, scoped to that set.

### Sequencing confirmed (program manager)

Resolver work (G2+G4) lands **before** dependent plumbing (G5). **G3 is
independent** — if plan2 returns first, its Developer starts immediately
without waiting on the resolver pair.

### Phase 0b addendum — program-manager approvals (binding)

1. **Scout-protocol authorship settled.** Scout #4 stays read-only; the
   manager commits its protocol. Confirmed as manager-scope hands-on work
   under the harness (doc/contract commits), not a role deviation — the
   requirement is the committed artifact plus a clean authorship trail, and
   single-writer-per-tree is the better discipline for reaching it.

2. **G4 RESULT-REPORTING EXPECTATION (binding on Planner, Developer, and
   QA).** G4's before/after must report the two failure modes **separately**:
   - **empty path** (the S-R16 class — visibly fails to scope), and
   - **non-empty WRONG path** (e.g. Oregon's top-level `'1'` where `(2)`
     governs — silently MIS-scopes assertions).

   Collapsing them into a single number is not an acceptable report: it
   hides G4's actual effect, and the two carry different downstream costs.

3. **G4 discriminator bar (binding).** A discriminator built only around
   citation shapes (preceding `Section` / `§` / CFR / U.S.C. context) passes
   SC/TX/ME and **still misses Oregon**, which is an in-prose cross-reference
   with no citation-looking section number. The design must cover both
   shapes or state plainly which shape it does not cover, and why.

No further program-manager input required until the Planner verifications.

</content>
</invoke>
