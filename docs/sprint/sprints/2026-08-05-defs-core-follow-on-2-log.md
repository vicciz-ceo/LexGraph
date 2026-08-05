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
</content>
</invoke>
