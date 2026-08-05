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

| 4 | Scout (read-only) | G7 baseline reproducibility | Sonnet/high — tracing measurement recipes across divergent branches; a misclassified number produces a false G7 pass; Haiku considered: no | read-only, no branch | `a682047c7fe5507af` | **COMPLETE** — protocol committed @ 503fb64; opened Q-G3-A + Q-G3-B |
| 5 | Planner | G8 (collision preference) | Sonnet/high — P-R6; Haiku considered: no, the deliverable is a design judgment over shared persistence code with real wrong-direction risk both ways | `claude/defs-core-follow-on-2-plan4` / `...-wt/defs-core-follow-on-2-plan4` | `a880e3c4f0fed4e79` | running |

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

---

## Phase 0c — scout #4 returned; two G3 questions opened (2026-08-05)

Scout #4 (`a682047c7fe5507af`) completed. Its protocol is committed as
`2026-08-05-defs-core-follow-on-2-g7-merge-protocol.md` (manager-committed;
scout remained read-only). Classifications: markers' zero-yield table
**reproducible on-branch** (exact 7/7 state match); preamble's
23,617/27,209 and GA's 2,794 **merged-tree only** (verified three ways);
nothing untraceable. One disclosed gap: the preamble QA's harness scripts
were never committed and no longer exist — the prose methodology survives
and its BEFORE side was independently re-verified (GA before = 2/28,154,
exact).

Two findings exceeded the scout's brief and were **re-verified by the
manager against source** before being recorded:

- **Q-G3-A — sibling-function scope gap.** us_profile.py:588 in
  `_extract_inline_quoted_definitions` reads
  `end = entries[index + 1][1] if index + 1 < len(entries) else len(text)`
  — the identical unbounded-last-entry defect, in a function G3's gate text
  does not name. The 27,209 rows' `definition_text` caveat lives HERE, not
  in `_split_into_numbered_blocks`. Inside the sprint's write-set, so no
  fence issue; the question is gate coverage. **Open — needs a ruling.**
- **Q-G3-B — DC attribution unproven.** G3's held RED
  (`test_us_markers_unbounded_last_entry.py`, `claude/defs-us-markers`)
  pins CONTAMINATION on an already-capturing FED row (`USC_T5_C34_S3401`,
  ~487 real chars captured as 4,627), not a zero-to-nonzero conversion.
  The same file records that DC's relayed 91.7% **did not reproduce** —
  DC bodies ended cleanly in 8/8 sampled rows, trailing-marker measure
  0.1%. So no evidence supports "G3 moves DC's 27.3%". Hypothesis (NOT
  measured, flagged as such): DC's zero-yield is driven by its
  unquoted-term shape, which `_leading_quote_candidate` cannot match and
  G3 cannot touch. **Open — plan2 tasked to measure DC's real causation.**

Also confirmed incidentally: **G1's premise is exact.** us_profile.py:581
(`_extract_inline_quoted_definitions`) does `term_match.group(1).strip()`;
us_profile.py:608 (`_leading_quote_candidate`) does `term_match.group(1)`
with no strip. The asymmetry is real as specified.

---

## Phase 0d — G8 RULED IN (program manager, 2026-08-05)

**New shared-module defect, ruled into this sprint while Planners are still
designing.** Found by the markers panel's QA while attributing WA's 3
oversized definitions; it sits one layer past the split defect, in
PERSISTENCE rather than extraction.

**Mechanism (manager-verified against `pipeline.py`, not accepted on
report):** Stage 2 builds `all_candidates` baseline-first, then persists in
list order (lines 289-310). The write is guarded by
`if definition_row is None:` on key `(article_id, tuple(sorted(terms)))`.
When baseline emits a BAD candidate and a registered rule emits a CLEAN
candidate for the SAME term, baseline's row is created first and the rule's
`definition_text` is **never written** — first-candidate-wins.

Kill-control evidence (markers QA, real
`ingest_us_statute_rows → run_definition_linking` path): on all 3 WA rows,
baseline alone emits 10,838 / 6,515 / 8,769-char swallows while the markers
engine alone emits the same terms at 303 / 188 / 105 chars — and the swallow
is what persists.

**Two properties the manager found beyond the relayed report, both
load-bearing for the fix design:**
1. **There is no UPDATE path for `definition_text` at all** — the only write
   is inside the `is None` branch. A colliding candidate can never correct
   an existing row.
2. **`definitions_by_key` is pre-seeded from existing DB rows** (lines
   282-284), so a bad `definition_text` persisted once **wins over every
   future re-run**. The defect is sticky across runs, not merely
   within one. (Corpus measurements call extraction functions directly and
   are unaffected; the live product path is not.)
3. Nuance for the RED's assertion target: the losing candidate IS still
   appended to `resolved` (line 310), paired with the WINNER's `Definition`
   row. What is discarded is specifically its `definition_text`/scope at
   persistence — not the candidate's downstream participation.

### MANAGER DESIGN CALL: opened as a named **G8**, not folded into G3

Ruled by the program manager as the panel manager's call. Decided **G8**,
for four reasons:
1. **Different module and different mechanism** — `pipeline.py` persistence
   dedupe vs `us_profile.py` entry-boundary logic.
2. **It honors the program manager's own guard.** "G3 happened to make it
   unobservable on these 3 rows" must not close it. An independent gate with
   its own RED — one that does NOT depend on baseline emitting a swallow —
   makes that structurally impossible, whereas folding it into G3's
   acceptance makes silent closure the default outcome.
3. **The design judgment is independent.** Preference between baseline and
   rule candidates is seam-relevant; baseline-first was presumably
   deliberate, and flipping order could let a BAD rule candidate beat a GOOD
   baseline one. A length-sanity or specificity criterion may be sounder.
   That reasoning does not belong inside a boundary-fix gate.
4. **Coupling acceptance of two independent fixes** would let either one's
   difficulty hold the other hostage at QA.

**G8 — collision preference.** A baseline bad candidate must not silently
beat a cleaner same-term candidate from a registered rule at persistence.
Owner: **new Planner (plan4)**, `pipeline.py` surface. The G3↔G8 interaction
is owned explicitly: plan2 reports (factually) whether its G3 design would
moot the 3 WA rows; plan4 designs G8 so it stands independently of that
answer; the manager arbitrates when both return.

</content>
</invoke>

---

## Phase 1 — manager verification of all four Planners (2026-08-05)

**All four verified; all four ACCEPTED.** Merged into the sprint branch
@ `79c0e73` (plan1, plan2, plan4 clean; plan3 add/add conflict on this log
resolved by keeping the manager record and folding plan3's planner notes in
verbatim as Appendix A).

### What the manager verified FIRST-HAND (not accepted on report)

1. **Every RED actually fails, and for the right reason** — run in each
   Planner's own worktree/venv, failure messages inspected individually:
   - plan1: **8 failed / 4 passed** (4 passing are regression guards, which
     must pass now and keep passing). Oregon RED yields
     `got (UnitStep(kind='digit', value='1'),)` — the non-empty WRONG path
     mode, exactly as specified.
   - plan2: **3 failed / 13 passed**. G1 RED shows the mechanism directly:
     padded `' Registrant '` finds **0** matches where the stripped term
     finds 1.
   - plan3: **8 failed / 2 passed**, incl.
     `TypeError: ScopeKindRule.__init__() got an unexpected keyword argument
     'detect_value'` (seam genuinely absent) and G5 failing on **both** US
     and IL — confirming the two-site fix.
   - plan4: **1 failed / 4 passed**; RED asserts on REAL PERSISTED OUTPUT
     and shows a 155-char candidate carrying a separate sub-item's
     `(B) "Occurrence"` marker beating both baseline's own later clean
     candidate AND the registered rule's, purely by enumeration order.
2. **Fixture provenance byte-verified against the real corpus by the
   manager** — all **10 fixture rows across three branches** re-read from
   the parquet snapshot and compared: **10/10 BYTES MATCH**, lengths
   identical (AR 4,866 / MS 1,015 / FED `USC_T5_C34_S3401` 5,229 / AZ 9,307
   / SC 23,574 / SC 1,476 / TX 8,545 / TX 956 / ME 14,416 / OR 6,402).
   Probe note (P-R10): the manager's first pass failed on a wrong key
   (`section_id`); the corpus keys on **`act_id`** — the probe was wrong,
   not the fixtures.
3. **Tests-only, no production code** on all four branches (diff --stat).
4. **Seam v2.8 is genuinely append-only**: `254 insertions, 0 deletions`
   on the seam doc; §0 re-verifies the manager's M9 finding (HOLDS), §8 does
   the row-by-row on all 8 U2 rows.

### Carried into implementation as named hazards (binding on Developers)

- **G2 requires plan1's discovered THIRD sub-step** — defer ladder selection
  past tokens matching NO outermost rung, or ME's `(NEW)` annotation still
  hijacks the ladder. Prototype: 8.4% → 0.64% corpus-wide, ME 81.0 → 0.2%,
  AZ 69.7 → 0.2%.
- **G4's 42% / 34% corpus-scale figures are EXPLICITLY PROVISIONAL**
  (prototype, 6 rows spot-checked). **They must NOT enter any certified
  record without the sampled audit plan1 recommends.**
- **G4 implementation hazard:** SC's `(A)(1) or (A)(2)` connector chain
  still lands the wrong top-level value in the prototype — real engineering
  required, documented in the G4 test docstring.
- **G3 termination is CONTENT-marker based, not structural** (plan2's
  both-sides sampling justified it); extended 10-marker set recommended;
  24.62% of 27,051 last entries contaminated.
- **G1 mechanism confirmed:** `re.escape` does not escape spaces, so padded
  terms miss punctuation-abutting mentions. Padding = 2.24% of extracted
  terms (NC 55%, WY 61.6%, NM 79.8%) — a **lower bound**; MS stays invisible
  until preamble merges.

### Program-manager rulings on the two open questions — RECORDED

- **Q-G3-A: YES — the sibling `_extract_inline_quoted_definitions` is IN
  G3's scope** (its IL 71.4% contamination is the very population G3's
  purpose clause invokes; one shared termination helper).
  **CONDITION (binding):** before the Developer touches the sibling, the
  same both-sides sample plan2 ran for the main function must be run on the
  **SIBLING's** population — its over-correction risk is plan2's own named
  unverified gap. **If that sample shows a materially worse trade, the
  sibling becomes its own follow-up WITH the data — not silently built
  anyway.** plan2 re-engaged to run this; dev1 is fenced off the sibling
  until it returns.
- **Q-G3-B: DC is DE-LINKED from G3.** plan2's mechanical proof stands:
  **202/332 quoteless, 130/332 blocked by the `"The term "` lead-in** —
  neither reachable by any boundary fix. Merge-protocol pass condition
  amended to: (a) FED RED green, (b) corpus-wide last-entry contamination
  near-zero against plan2's **27,051-row** denominator, (c) **DC explicitly
  EXCLUDED from G3's promise.** DC's real shapes route elsewhere: the
  lead-in shape to the markers panel (a registry `TermClauseRule` handles
  `(1) The term "X" means` with no shared edit — their QA independently
  named the same NC/DC shape), quoteless to their unquoted family.

### G8 corroboration recorded (independent instruments agreeing)

plan4's AR **self-collision** discovery — baseline colliding with ITSELF,
**2,282 rows / 34 jurisdictions, no rules needed** — plus its
containment-update design (ordering-flip and length-threshold both rejected
WITH data; 745 unambiguous / 2,307 benign / 1,308 ambiguous left untouched).
Corroborated by a DIFFERENT instrument: the markers manager independently
sized severe collisions at **213** (TN 146, FED 51; worst discarded
improvement **163,875 chars**, `USC_T5_C83_S8331`). Its TX finding (3,910
rows, 19,352 keys, **ZERO** severe — likely a genuinely-distinct-definitions
population) independently supports leaving the ambiguous group untouched.

---

## Phase 1b — TWO NEW GATES: manager decision (2026-08-05)

Decision authority was the panel manager's; the program manager asked for
reasons either way. **Both ACCEPTED.**

### G9 — breadcrumbs data source: **ACCEPT**

`pipeline.py:212` hardcodes `heading_breadcrumbs=()`; `sections.py:138`'s
`len==2` gate discards 3+-equals heading text. Reasons:

1. **The seam doc already claimed this as core's own work and did not
   finish it.** v2.6 §1 (M-D1), input-availability note, verbatim:
   accumulating all depths into `heading_breadcrumbs` is *"core's own
   ONE-PLACE additive change (default `()`, so every existing construction
   site is unaffected)."* Accepting is completing declared scope, not
   expanding it.
2. **It is a starved-seam defect of the P-R8 class this sprint's lineage
   exists to close.** `StructuralUnitRule.derive` consumes
   `StructuralContext.heading_breadcrumbs`; hardcoding it `()` means every
   panel's `StructuralUnitRule` is fed nothing — registered, dispatched,
   and useless. "Live dispatch" over an empty input is not live capability.
3. **Only this sprint can do it.** `pipeline.py` is in the exclusive
   write-set and `sections.py` is core-owned; P-R1 fences every panel out.
   Deferring leaves IL's סימן/חלק containment residual blocked with no
   other route.
4. **Cheapest gate on the board:** small, additive, safe default, and two
   committed REDs already exist on `claude/defs-il` to vendor equivalents
   from.

Carried caveat: `sections.py` is a **Hebrew regression surface** — existing
IL tests must pass UNCHANGED; editing one to fit is a planning bug and
escalates.

### G10 — `TermClauseRule` scope threading: **ACCEPT** (highest-value of the two)

`registry.py:139-145` — `parse` receives the block string ONLY;
`us_profile.py:1351` drops the scope the dispatcher already holds. Reasons:

1. **It is an active correctness bug producing WRONG assertions today**, not
   a missing capability. Every panel's `TermClauseRule` stamps `law-wide`;
   a law-wide stamp on a section-scoped definition manufactures false
   `USES_DEFINITION` assertions across the whole law. That is precisely the
   failure mode seam v2.1 (M9) names — *a silent broadening fallback is a
   false-positive generator, never an acceptable default* — and it violates
   the director's founding scoped-definitions constraint and D-E1
   (narrowest governs).
2. **Proven from source on a real IN row** (silent wrong-scope winner), not
   inferred.
3. **Unblocks correctness for FOUR panels** — the widest leverage available
   this sprint.
4. **The fix shape already has a precedent in flight:** additive signature
   threading (optional param or context object, existing rule modules keep
   working) is exactly G5's pattern, so it composes with work already
   designed rather than fighting it. Seam version bump → **v2.9**, appended
   after v2.8.

**Scope-collision check before accepting both** (manager): G9 touches
`pipeline.py:212` + `sections.py`; G8 touches `pipeline.py:262-310` —
distinct regions. G10 touches `registry.py` + `us_profile.py:1351`; the
resolver pair holds 1075-1256 and the extraction pair 346-620 — all
distinct. No two accepted gates contend for the same lines.

### Deferred, NOT lost — core-follow-on-3 accumulator

plan2's out-of-scope list routes to the opened core-follow-on-3 accumulator
(program log), explicitly not absorbed here: **AZ bare-digit-dot
sibling-swallow, WA mid-paragraph markers, MI spaced `( l )`, CT
conventions.**

---

## Phase 2 — implementation wave 1 (2026-08-05)

Spawned after Planner verification. Model/effort for every Developer:
**Sonnet/medium** — design and tests already exist, so this is bounded
implementation against a written spec; Haiku considered: no, each lands in
shared code six panels depend on.

| Agent | Gates | Branch | agentId | Outcome |
|---|---|---|---|---|
| dev1 | G3 + G1 | `...-dev1` | `a1d5577f4545118ae` | running |
| dev2 | G8 | `...-dev2` | `ad5caf511b321ca57` | **MERGED @ 715211a** |
| dev3 | G2 + G4 | `...-dev3` | `ac0dfea20acd8ed41` | running |
| plan5 | G10 | `...-plan5` | `a78f13f6bc7939fbf` | running |
| plan6 | G9 | `...-plan6` | `a38aa7f6e1cf03cd3` | running |
| plan7 | G11 | `...-plan7` | `af70147302e1a0212` | running |

G5+G6 implementation is deliberately NOT yet spawned: G5 depends on the
resolver pair (dev3) landing. G6 will be paired with it to keep one head on
plan3's design.

### G8 — manager verification (dev2), ACCEPTED and merged

Verified first-hand, not accepted on report:
- Diff is **`pipeline.py` only, 46 insertions / 0 deletions, 0 test files
  touched**; full diff read (shared persistence code — full reads are the
  rule in this sprint).
- G8's suite: **5 passed** (the RED now green + 4 that already passed).
- Full suite **794 passed / 19 failed**, and the 19 are exactly the other
  gates' unimplemented REDs (G2 4 + G4 4 + G1 2 + G3 1 + G5 2 + G6 6 = 19).
  Independently recomputed against the manager's own earlier per-branch RED
  counts — they reconcile exactly.
- 33 IL/Hebrew tests pass unchanged (regression surface intact).

**The implemented criterion** (`_is_tighter_containment`) is
`candidate != persisted and len(candidate) < len(persisted) and candidate in
persisted` — a strict byte-exact substring test, applied in a new `elif`
branch that updates `definition_text`/`scope`/`qualifier` together.

**Manager's own analysis of why this matches the Planner's partition** (the
mapping is exact, which is good evidence the design was implemented rather
than approximated):
- identical text → excluded by `!=` → the **2,307 benign**;
- no containment relationship → excluded by `in` → the **1,308 ambiguous**,
  left untouched as designed;
- strict containment → fires → the **745 unambiguous**.

**Outcome is order-independent** (manager-checked by reasoning through both
orders): long-then-short overwrites; short-then-long does not fire, since
`len(candidate) < len(persisted)` fails. Shorter-contained wins either way,
and nested chains converge to the innermost.

**Origin-agnostic**, so it covers the majority case — baseline colliding
with ITSELF (2,282 rows / 34 jurisdictions) — and not merely baseline-vs-rule.

**It also closes the stickiness property** the manager found: because
`definitions_by_key` is pre-seeded from existing DB rows, this `elif` is the
only path by which a bad `definition_text` persisted by a PRIOR run can ever
be corrected.

### TWO RISKS THE MANAGER IDENTIFIED — handed to QA as required attack points

Neither blocks the merge; both are assumptions the fix rests on, and neither
is proven by the tests as they stand.

1. **"Longer = contaminated" is the load-bearing assumption of all of G8.**
   The criterion prefers the shorter text whenever it is strictly contained.
   That is correct when the extra bytes are a leaked neighbor's marker+quote
   — but WRONG if the longer text is a legitimately fuller definition
   (e.g. `"means X."` contained in `"means X. It also includes Y."`), where
   preferring the shorter DROPS real content. Under an absolute zero-miss
   bar that is a recall loss, not a cleanup. **QA must verify the 745
   "unambiguous" cases are genuinely contamination, not fuller definitions
   — on a hand-judged sample, not by assertion.**
2. **Scope may silently BROADEN on update.** The branch assigns
   `definition_row.scope = candidate.scope` alongside the text. If the
   superseding candidate carries a broader scope than the row it replaces,
   the update broadens it — which seam v2.1 (M9) names as a
   false-positive generator ("a silent broadening fallback is... never an
   acceptable default"). The field-replacement is deliberate and reasoned
   (avoiding a row that mixes fields from two candidates), but its
   scope-direction effect is untested. **QA must add a direction check: an
   update must never widen scope.**

### G3 + G1 — manager verification (dev1), ACCEPTED and merged @ cfe10ce

Verified first-hand:
- Diff is **`us_profile.py` only, 103 insertions / 2 deletions, 0 test files
  touched**; full diff read.
- **G3's RED green and all 12 guard pins green** (15 passed / 1 failed in the
  targeted run, the 1 being the G1 re-point below).
- Full suite **795 passed / 18 failed**; 17 reconcile exactly to the other
  unimplemented gates.
- **Hebrew/IL surface intact** — manager's own filtered run: 52 passed, and
  its only 2 failures are the unimplemented G5-IL / G6-IL REDs, not
  regressions.

**Implementation (as instructed, the shared-helper shape is real, not
cosmetic):** `_trailing_notes_boundary(text, start, end) -> int` plus the
extended 10-marker `_TRAILING_NOTES_MARKERS`, applied only to `blocks[-1]`
(every other block is already bounded by the next entry marker's start).
The helper is deliberately **offset-in / offset-out**, and its docstring
states the exact sibling wiring: `_trailing_notes_boundary(text,
definition_start, end)` replaces the sibling's literal `len(text)` fallback
**with no other change** — which is what makes the Q-G3-A sibling adoption a
one-line change once its condition is discharged.

**Line-granularity is a verified design decision, not a shortcut:** markers
can sit MID-line inside citation parentheticals — real FED row
`USC_T5_C34_S3401` carries `(Added Pub. L. 95-437, ...)` before "Editorial
Notes", so truncating at the marker substring's own offset would leave
`"(Added "` dangling in the kept text. Dropping the whole line does not.

**G1** is the one-line `.strip()` on `_leading_quote_candidate`'s captured
group, matching the sibling's long-standing convention for the same capture.

#### Honest caveats recorded (not papered over)

- **The 12/12 guard-pin result is weaker than it sounds.** dev1 disclosed
  that LA/ID/MI's last raw blocks DO contain marker text but contribute no
  candidate — so truncation is **inert** on those three. The guard proves
  non-regression there, but does not exercise the new boundary. QA should
  not read 12/12 as 12 live exercises of the rule.
- **MANAGER-IDENTIFIED QA ATTACK POINT — marker matching is broad.** The
  check is `any(marker in line for marker in _TRAILING_NOTES_MARKERS)`: a
  bare, case-sensitive SUBSTRING test anywhere in the line. Tokens like
  `"Amendments"`, `"Source:"`, `"History:"` and `"Cited."` are generic
  enough that a GENUINE final-entry line mentioning one (e.g. "...subject
  to Amendments made by...") would truncate the entry at that line. Blast
  radius is bounded (last block only), but the last block is a real
  definition. **QA must measure how often a genuine last-entry line
  contains one of these tokens** — this is the precision side of G3 and it
  is not proven by the current pins.

#### The 18th failure — Planner-side re-point, correctly handled by dev1

`test_padded_term_silently_misses_a_mention_that_the_stripped_term_finds`
fails **by construction**: it sources its padded term from live extraction
(`next(t for t in by_term if t.strip() == "Registrant")`) and asserts it
equals `' Registrant '` — which G1 now correctly prevents. The test's OWN
assertion message prescribed the remedy ("needs to be re-pointed, not
silently adjusted"). dev1 respected the role boundary and did not touch it.

**Manager judgment (made, then handed to plan2 to execute):** the mechanism
the test proves — `re.escape` does not escape a plain space, so a padded
term misses a punctuation-abutting mention — is a property of
`find_term_uses`, NOT of the extractor, and remains true and worth pinning.
Re-point to a **synthetically-constructed** padded term, keep the
stripped-finds-1 / padded-finds-0 contrast intact, and record in the
docstring that the extractor-side guarantee is covered by the sibling test
`test_ms_defined_terms_are_stripped_of_quote_interior_padding` (now
passing). Routed to **plan2** rather than a Haiku micro-fix: it authored the
tripwire and the M-R32 reasoning, test authorship is Planner-owned, and the
risk of a re-point that pins the wrong thing outweighs the saving on a task
this small.

### PROCESS CORRECTION — manager error, recorded

Phase 0d/Phase 1 of this log stated "plan2 re-engaged to run this" for the
Q-G3-A sibling both-sides sample. **That message was never actually sent.**
The gap surfaced when plan2 resumed with "no active task," proving it had
been idle rather than measuring. The real brief has now been dispatched and
the sibling sample is plan2's PRIMARY task, ahead of the re-point.

Consequence to note: the sibling sample is on the sprint's critical path
(dev1's sibling fence lifts only after it, and **G11's flip must pair with
the sibling boundary fix** or ship the measured 202-row debt), so this error
cost wall-clock time on the longest chain. No work was lost or duplicated.
Recorded rather than quietly fixed, per this log's append-only convention.

### G2 + G4 — manager verification (dev3), ACCEPTED and merged

Merged; **integrated sprint suite: 803 passed / 10 failed** — dev1 and dev3
compose cleanly. The 10 are fully accounted for: G5 (2) and G6 (6)
unimplemented, plus the two known test-side items below.

Verified first-hand: `us_profile.py` only, **205 insertions / 30 deletions,
0 test files touched**; every changed hunk lies in **1078-1450** (the
resolver region), clear of dev1's extraction region — which is why the two
merged without conflict.

**One token-acceptance story, as required:** every candidate token (paren OR
period-style) passes one funnel — G4's citation/cross-reference reject
first, then (only while the ladder is unset) G2's shape-must-match-a-rung
defer. G2 widens what is *recognized*; G4 narrows what is *trusted*; they
compose because G4's reject is applied uniformly to both token vocabularies.

**SC connector-chain hazard SOLVED** (handed over as unsolved): resolves to
exact `(C,2,c,i)` — top-level lands on `'C'`, not `'A'`, hand-traced against
the real 23,574-char row.

**All 4 G4 cases are the non-empty WRONG-path class** (per the binding
split-reporting ruling) — none are visibly-empty failures: SC `(C,)` vs
correct 4-level; TX top-level relabeled `'a'` vs correct `'f'`; ME
`(digit:'13',)` where the correct answer is EMPTY `()`; OR `(digit:'1',)`
vs correct `(digit:'2', lower_alpha:'a')`. The whole named sample is the
more dangerous silent-mis-scope class.

**Provisional figures correctly NOT laundered:** dev3 explicitly declined to
certify or re-quote the 42%/34% G4 corpus numbers, citing them as the
Planner's provisional 6-row-spot-checked figures. G2's census is cited as
Planner-measured, not re-derived.

#### MANAGER PROBE — a suspected G2 regression, DISPROVEN

`test_i9_me_s751_body_with_only_annotations_produces_the_articles_own_base_path`
(a PRIOR sprint's test, cd_i9) flipped from `()` to `(digit:'1',)`. Its
docstring claims the row uses period-style markers **"A.", "B.", "C."** — so
a DIGIT-seeded path would have meant G2 mis-selected the ladder on ME, its
own flagship state. That would be a silent wrong-direction fix, so the
manager probed the real fixture rather than accepting "intended change":

- `STATE_ME_T30-A_P1_C3_S751` (2,072 chars) contains **exactly ONE**
  period-style marker — `'1'` at offset 219, context
  `[PL 1991, c. 257 (NEW).]\n\n1. Membership. The budget com...`
- Line-start scan: `^\s*A\.\s` → **0**, `^\s*B\.\s` → **0**,
  `^\s*1\.\s` → **1**, `^\s*2\.\s` → **0**.
- Resolver returns `(digit:'1',)` consistently at every offset past 219.

**Verdict: `(digit:'1',)` is CORRECT** — a genuine top-level marker the
parenthesized-only regex could never see. The suspicion was wrong, and the
check was still worth running. Confirmed still-correct on the same row: the
`(NEW)` annotation and the `PL 1991, c. 257` citation are both ABSENT from
the path, so I9's annotation-is-a-no-op invariant and G4's citation
discriminator both hold.

**The real defect is in the OLD TEST'S DOCSTRING, which misdescribes its own
fixture** ("A.", "B.", "C." — the row has none). That error was
load-bearing: the entire `== ()` rationale rested on it. Routed to plan1
(author of the predicting RED) to update the assertion AND correct the
docstring AND preserve the annotation-no-op guard — not a bare assertion
flip.

#### New residual gap disclosed by dev3 (assessment requested, build nothing)

G4's discriminator uses a CLOSED structural-word vocabulary that does **not**
include `"item"`/`"subitem"`. Real SC text "under subitem (3)" and "provided
in item (8)" are therefore not recognized as cross-reference context and can
transiently mis-set the stack until the next real marker overwrites it
(observed at positions ~631 and ~1702 in `STATE_SC_T58_C9_A5_S58-9-576`).
Bounded and non-cascading on that row, but **untested and un-measured**.
plan1 asked to recommend test-and-measure-now vs route to
core-follow-on-3; manager rules after.

---

## Phase 3 — G11 measurement returned; manager ruling (2026-08-05)

plan7 delivered a measurement-only report (no commits, correctly withholding
items/REDs because the data does not support shipping).

### Verified quality of the measurement

- **P-R10 anchor reproduced:** 82,155→82,156 live-recognized;
  53,918→53,919 zero-live; 39,955→**39,956** rescued (74.1%). Off by exactly
  1 in each aggregate, **EXACT on all 5 cited per-state numbers**
  (NV/NJ/AZ/MI/WA) — a population-definition edge case, not a methodology
  mismatch.
- **Denominator is genuinely signal-agnostic (P-R7/M18):**
  `re.search(r"defin", title, re.I)` over raw `section_title` — independent
  of baseline's positional logic, of every HeadingRule predicate, and of the
  extraction grammar (which reads `text`, not the title). Drawn from the
  entry LINE. 53 files, 2,038,247 rows.
- **Denominator hygiene honored:** it did not touch or attempt to reconcile
  the markers panel's 86.5%/11,010 population.
- **FP sample is reproducible:** seed 20260805, reservoir k=30 per path
  (60 rows), uniform over the full rescued populations, rubric stated,
  judged at row level.

### Findings that change the gate

- **The rationale was MISREAD by everyone, including me.** The "zero-risk for
  the 7 already-working states" guarantee is a **regression-safety**
  guarantee ("don't break what already produces candidates"), NOT a precision
  guarantee about the fallback's output. Those states are themselves
  majority zero-yield on baseline recognition today (NY 1479/1479,
  OH 949/950, WA 1778/1800, PA 534/543) — the fallback was never exercised
  for them, so it was never *proven safe* for them.
- **The split is empirically TWO-way, not three:** baseline 61,075 +
  registry 21,081 = 82,156; **ZERO** body-derived rows in the defin-titled
  population (placeholder-heading derivation and defin-titled headings are
  near-disjoint). The conflation mechanism itself was confirmed exactly as
  predicted.
- **Counter-intuitive direction, and its cause:** baseline path **40.0%**
  (12/30) contaminated vs registry **13.3%** (4/30). Cause is **section
  complexity/length, NOT which recognition mechanism fired** — registry rows
  skew short single-term "X defined" sections (NV alone is 42% of all
  registry-recognized rows), baseline rows include large multi-topic
  sections. **This kills the narrow-open-by-recognition-path design I
  hypothesized in Phase 1b** — it would open the *cleaner* population while
  leaving the *dirtier* one closed, backwards from the intent.
- **G3-main overlap is provably ZERO** (structural, from the `if not
  candidates` guard — the fallback only runs when the splitter produced
  nothing). No double-counting risk between G3-main and G11.
- **NV reconciled, non-contradictory:** baseline path 924/1,262 = 73.2%
  (exact match to the amendment) and registry path 8,881→8,217 rescued are
  different NV slices.

### MANAGER RULING ON G11: DO-NOT-SHIP-ALONE, accepted

G11 does **not** flip this sprint unless the extraction-grammar fixes land
with it. Accepted on the evidence: at 40%/13.3% row-level contamination
neither path is clean enough to open, and no per-path narrowing rescues it.

### ESCALATED — a second defect with no home, colliding with a director ruling

plan7 found a **previously-unflagged defect**: `_MEANS_IDIOM_GAP_RE` matches
only `means|shall mean|has the meaning`. When an intermediate entry uses
`includes` or "has the SAME meaning", it never starts its own candidate and
is **silently swallowed into the PRECEDING entry's `definition_text`**
(observed repeatedly — e.g. a 14-candidate US-NY row where 5 candidates each
absorbed 1-4 unrelated subsequent definitions). Because this corrupts
content well below the 5,000-char proxy, **the length-only proxy
systematically undercounts true contamination.**

It is in no gate's scope, and widening the idiom set collides with
**D-INCLUDES-MEASURE**, where the director explicitly reserved the
`includes`-as-defining-verb question pending a measured FP side. Escalated
rather than absorbed — with a proposed decoupling: treat `includes` as an
entry **BOUNDARY** (terminating the preceding definition) **without emitting
a candidate** for it. That fixes the contamination this sprint owns while
leaving the director's recall question untouched.

Also recorded from plan7: a severe federal outlier (8 U.S.C. §1101 — a
"term" of `"SEC. 602. PROTECTION FOR AFGHAN ALLIES."` with a 104,229-char
swallowed definition, from amendment-history notes quoting old statutory
text in quotes), and a named likely-overlap with G8 (the US-AR
duplicate-candidate row), flagged for the merge protocol rather than
asserted.

---

## Phase 3b — D-INCLUDES resolves the escalation; G12 opened (2026-08-05)

The escalated `_MEANS_IDIOM_GAP_RE` question was **already answered**.
**D-INCLUDES** (program doc, main @ `6a56a84`) — manager-verified by reading
the primary source, not the summary:

> the `includes` defining-verb class is CAPTURED with the naive quoted-term
> anchor, **program-wide**. 50,528 anchor occurrences / 32,199 rows
> corpus-wide; **100/100 hand-read occurrences definitional across two
> independent seeds** (one-sided 95% upper bound 3.6% FP); tightened guards
> measured to cost **32–56% of TRUE definitions for no measured precision
> gain — rejected**.

The measurement's anchor shape (quoted term immediately before "includes")
**is** the fallback's own quote-first + idiom shape, so EMISSION is covered
by the ruling's evidence, not merely its text. My decouple-to-protect-the-
director's-question rationale is therefore moot and is withdrawn.

### MANAGER RULING: implement BOTH boundary AND emission, together

Sequencing was mine to choose; I rejected boundary-now/emission-later.

**Reason (decisive):** boundary-without-emission would convert a
contamination bug into a **silent-drop** bug. Today the swallowed entry's
content is at least PRESENT in the data, wrongly attached to the preceding
definition. Terminating the preceding entry without emitting the new one
would make that content vanish entirely. Under the program's absolute
zero-miss bar that is a regression in kind — contamination is visible in the
data; a dropped entry is invisible. Recorded as a scope decision on the
merits, not as deference to an already-ruled question.

### G12 — opened, assigned to plan8

Widen `_MEANS_IDIOM_GAP_RE` to the includes-family, boundary AND emission.

**Mandatory conditions carried from the primary source** (the relayed
summary omitted the first two — caught by reading the ruling itself):
1. **The PA construction-clause guard is REQUIRED and must be TARGETED:**
   suppress `References to "X" shall include Y` **only when the quote is
   preceded by "References to"** (22 construction-clause rows protected vs
   4,729 genuine recall rows). **Never by idiom-absence**, and never by a
   broader guard — the ruling explicitly rejected tightened guards as pure
   recall loss.
2. **Any existing pin that passes BECAUSE `includes` was absent from the
   vocabulary must be RE-AUTHORED to assert the guard** — those tests will
   flip, and flipping them silently is forbidden. Every touched test
   reported with before/after intent.
3. **Enumerate the naive anchor's known recall limits, do not hide them:**
   non-adjacent "includes" (colon + numbered-list between term and verb),
   unquoted defined terms (2 characterized control misses), and
   **Massachusetts having ZERO anchor occurrences corpus-wide** (open:
   drafting convention vs corpus artifact).

### Blocking chain for G11, now fully named

G11 (~39,955-row recall win) ships only if BOTH land:
- **G12** (this gate) — idiom widening; and
- **G3-sibling** (line-588 boundary) — still pending plan2's GO/NO-GO
  both-sides sample.

If either fails, **G11 does not ship this cycle**.

## Phase 3c — G5+G6 implementation unblocked

The resolver pair (G2+G4) has landed, so G5's dependency is discharged.
dev4 spawned for G5+G6 against seam v2.8 (§9 is its implementation spec).
Baseline handed to it: **803 passed / 10 failed**; target **811 passed / 2
failed**, the 2 being the known Planner-side items (the G1 re-point and the
i9 update) which it is explicitly forbidden to touch.

| Agent | Gates | Model/effort | Branch | agentId | Outcome |
|---|---|---|---|---|---|
| plan8 | G12 | Sonnet/high — P-R6; widens a defining-verb vocabulary in shared extraction under a director ruling with mandatory conditions; Haiku considered: no | `...-plan8` | `a17f139e498c1076c` | running |
| dev4 | G5 + G6 | Sonnet/medium — bounded implementation against seam v2.8 §9 + 8 existing REDs; Haiku considered: no, shared registry/profile seam | `...-dev4` | `abb08ac1b9814cf00` | running |

All briefs from this point carry the direct-report SendMessage instruction
per the director-ordered harness adjustment.

---

## Phase 4 — G9 Planner returned; ONE ITEM HELD for a program-level call

plan6 (`a38aa7f6e1cf03cd3`) delivered on `claude/defs-core-follow-on-2-plan6`
@ `bd53d10`. **Items G9-1 / G9-3 / G9-4 ACCEPTED. Item G9-2 HELD.**

### Manager verification (first-hand)

- REDs **re-authored, not cherry-picked** — independently chosen real laws
  (`חוק תכנון משק החלב`, `תקנות מחלות בעלי חיים`), every excerpt
  byte-verified as a literal substring of its real source.
- The live-path P-R8 proof registers a `StructuralUnitRule` whose `.derive`
  reads `ctx.heading_breadcrumbs` **dynamically** and fails today with
  `uses_props=[], created_assertions=[]`, while definition-capture
  assertions pass FIRST — so it isolates containment and genuinely proves
  **consumption**, not mere population. (A wrongly-populated field fails the
  same assertion.) This is the distinction P-R8 exists to enforce.
- Depth-2 non-regression evidenced, not asserted: 35 existing IL tests pass
  UNEDITED with an empty `git diff --stat` on those files, plus a positive-
  control `.chapter` byte-identity pin.
- Zero production code touched; lint PASS.
- Line numbers had drifted from the brief (pipeline.py 212→243,
  sections.py 138 gate) because of other gates' edits; plan6 re-verified
  both defects still present at its fork point rather than trusting the
  brief's numbers.

### plan6's self-reported "gap" was actually a P-R10 SUCCESS (manager correction)

plan6 honestly flagged that it could not reproduce M8(a)'s "124 of 6,133
bare-@ documents," getting **42**. It was comparing against a **superseded**
number. Program ruling **P-E3** corrects that framing verbatim: *"real
bare-@ occurrences are 331 across **42 files**."*

**plan6 hit the corrected figure exactly.** Its probe PASSED its sanity
check; the reference was stale, not the method — which materially
strengthens confidence in its own corpus numbers (14,393 discarded depth≥3
heading lines; **50,472/128,234 = 39.36%** of articles gaining breadcrumb
depth), since the same scan reproduced an independently-corrected figure.
Relayed to plan6 for correction in its appendix.

### G9-2 — new persisted column: HELD, with a recommendation to proceed

plan6 specified a new additive nullable column on `models.article.Article`.
**The manager verified its "no other route" reasoning independently and it
HOLDS:**
- `pipeline.py:172` loads articles via `select(Article)` — it never
  re-parses raw text.
- `Article` carries no breadcrumb field (id, document_id, matter_id,
  source_span_id, number, heading, chapter).
- `add_raw_text_columns.py` applies to **assertion tables only**; no
  document-level raw text is persisted anywhere to re-derive heading
  structure from. (Checked precisely because, if raw text WERE persisted,
  pipeline could re-derive transiently and seam v2.5's philosophy would
  favor no column.)

This meets the exact bar seam **v2.5** set when ruling `scope_value`
transient-by-design: a column becomes right when a concrete consumer needs
the value without re-deriving it from source text. v2.5 also named the
shape — `add_assertion_subject_unit_path_column.py` (additive, nullable,
real `downgrade()`, no backfill) — and that file exists.

**Why it is nonetheless HELD rather than approved by the panel manager:**
this sprint merges **FIRST** among pending program merges and **all six
family panels rebase onto it**, so a schema migration here ripples into
every panel's rebase. That is merge-sequencing, which **P-R5 assigns to the
program manager**. Additionally, the manager's own Phase-1b acceptance of G9
was reasoned as *"small, additive, safe default"* and *"cheapest gate on the
board"* — **a premise a schema migration materially changes**, so the
acceptance was made on an incomplete picture and is re-surfaced honestly
rather than quietly extended.

**Recommendation: PROCEED.** The technical bar is met on verified evidence,
the precedent shape exists, G9 is non-functional without it (the whole gate
is making `StructuralUnitRule` consumption possible), and deferring pays the
same migration cost later with MORE panel rebases outstanding, not fewer.

**No G9 Developer spawned pending that call** — zero cost, since six agents
are already in flight and nothing is idle waiting on G9.

---

## Phase 5 — i9 update landed; G10 verified and in implementation

### i9 test update (plan1) — ACCEPTED and merged

plan1 **re-ran the manager's probe independently rather than taking it on
trust**, and went further: it checked each of the 8 real `(NEW)`/`(AMD)`
annotations individually (`()` before offset 220, `(digit:'1',)` after),
confirming zero leakage at every point. Fix: docstring corrected **in place
and marked "CORRECTED 2026-08-05"** rather than silently rewritten;
assertion re-pointed; and the I9 invariant **strengthened** — it now loops
all 8 annotations asserting the exact path at each one's own offset, so a
future leakage regression is caught where it happens, not only at
end-of-body. Production code untouched. Contract lint **PASS 110**.

**Manager ruling — 300-line style gate, deliberate exception recorded.**
The file is now 309 lines (9 over). plan1 flagged it rather than silently
cutting or silently accepting, and had already trimmed its own additions
once; the residual length is a PRIOR Planner's fixture-provenance and
UT-row evidentiary record. **Accepted as an exception for this sprint**, and
the split routed to the core-follow-on-3 accumulator. Reasons: the overage
is 9 lines; cutting another author's evidentiary record to hit a line count
would destroy more value than the gate protects; and restructuring a test
file that four gates currently depend on, mid-convergence, is a real risk
for no functional gain. Note the contract lint does not enforce file length
— this is a convention call, made explicitly rather than by omission.

### item/subitem residual gap — manager ruling: ROUTE to core-follow-on-3

plan1's recommendation ACCEPTED. It independently reproduced both named
positions on `STATE_SC_T58_C9_A5_S58-9-576`: offset 617 ("under subitem
(3)") is a no-op, `(A,3)` before and after; offset 1685 ("provided in item
(8)") does corrupt — `(B,2)` → `(B,8)` — but the row's own next genuine
marker at offset 1981 overwrites it back to `(B,3)`. **Transient and
self-correcting**, unlike the persistent fabrications G4 already fixes.

The decisive reason is its second one, and it is correct: adding
"item"/"subitem" to the structural-word vocabulary **without corpus
measurement would repeat this module's own reverted mistake** — the earlier
annotation word-list, removed under precedent P-E3 as unproven once
mutation-testing showed the general shape-based mechanism already covered
it. "Item (N)" could plausibly be some jurisdiction's genuine marker
convention; suppressing it unmeasured is precisely the recall-vs-FP conflict
**D-Q1** requires be escalated with data rather than settled by judgment
call. Routed, not built.

### G10 (plan5) — manager verification, ACCEPTED and merged @ af84a25

Verified first-hand:
- **Zero production code touched**; diff is the test file + seam doc only.
- **Seam v2.9 is genuinely append-only**: 317 insertions, **0 deletions**.
- REDs fail for the stated reason: **2 failed / 3 passed**, both failures
  `TypeError: TermClauseRule.__init__() got an unexpected keyword argument
  'parse_scoped'`; the 3 passing are the green "before" bug-pin and the two
  backward-compat anchors.

Notable practice worth recording: plan5 **proved the design buildable** by
applying it as a scratch edit (5/5 green, 801/17 with zero new failures),
then **reverted it before committing** — so the design is verified end-to-end
while the Planner's no-production-code boundary stays intact. That is the
right way to de-risk a seam design without crossing roles.

Also correctly handled: **P-R10 dormancy explained** — zero registered
`TermClauseRule` modules exist on this branch, so the buggy loop body never
executes in production here and the defect is LATENT until the first family
panel's rule merges. That is exactly the "why isn't everything downstream
already visibly broken" check the rule demands.

Measured (signal-agnostic, production detection path): 2,038,247 rows →
64,480 Definitions-section rows → **20,520 chapter-scoped** = the full
at-risk population; 43,960 law-wide (where hardcoding is coincidentally
correct). The 494-row figure is explicitly labelled a HEURISTIC lower bound,
not a census — correct discipline, and the fix's coverage is the full
20,520, not the 494.

**dev5 spawned** for G10 implementation against seam v2.9 §7.

### The G9-2 hold already paid for itself (2026-08-05)

plan6 accepted the hold without contest and, in re-checking, found its own
**G9-2 migration precedent citation was WRONG**: it had cited the
`Document.jurisdiction` / `create_all()` shape, which only applies to
fresh-test-only tables and **would not have worked on an already-provisioned
production DB**. Corrected (plan6 @ `01b6f2e`) to
`add_assertion_subject_unit_path_column.py`'s actual raw-DDL
`upgrade()`/`downgrade()` pattern — the shape seam v2.5 named.

So the hold did not merely defer a decision; it surfaced a latent defect in
the item specification before any Developer built against it. The G9-2 item
is now correctly specified **if** the program manager approves the column.
plan6 also reclassified its P-R10 note from "unreproduced gap" to "passed
sanity check," citing P-E3.

| Agent | Gate | Model/effort | Branch | agentId | Outcome |
|---|---|---|---|---|---|
| dev5 | G10 | Sonnet/medium — bounded implementation against seam v2.9 §7 + 5 existing tests, design already proven buildable; Haiku considered: no, shared registry seam | `...-dev5` | `ab129bb0201744fb0` | running |

---

## Phase 6 — G9-2 APPROVED; G9 in implementation (2026-08-05)

Program manager approved the persisted breadcrumb column. Grounds: the
manager's independently-verified no-other-route claim clears seam v2.5's
bar; the program already has the accepted shape (D-ANCHOR's
`subject_unit_path` column — additive NULLABLE, reversible raw-DDL
`upgrade()`/`downgrade()`, no backfill); and an additive nullable column
does not break any panel's rebase, since code that never reads it is
unaffected.

### Four binding conditions, and where each is discharged

1. **Nullable, no default-write requirement outside the new code path** —
   in dev6's brief as a binding condition.
2. **`downgrade()` proven reversible** — dev6 must *demonstrate* it
   (upgrade → verify present → downgrade → verify gone, on a real engine),
   explicitly not assert it.
3. **Merge protocol gains the migration line** — DONE, new
   "SCHEMA MIGRATION" section in
   `2026-08-05-defs-core-follow-on-2-g7-merge-protocol.md`: each panel runs
   `upgrade()` in its OWN worktree venv before its suite, or it will read
   migration-absence as regression.
4. **IL's two held containment REDs are the acceptance evidence at merge** —
   coordinated with the IL phase-3 manager (`a18597f9be6c49ed6`) NOW rather
   than discovered at merge. Asked specifically for: which laws/rows and
   what containment outcomes they assert; the breadcrumb SHAPE assumed
   (ordered `(depth, heading_text)`, `.chapter` unchanged at depth-2 with
   deeper entries appended); any surprising depth convention
   (non-monotonic sequences, depth-3 with no depth-2 parent); and whether
   they consume via a `StructuralUnitRule` reading
   `StructuralContext.heading_breadcrumbs` or some other route. This matters
   because our Planner deliberately re-authored against DIFFERENT real laws
   to keep authorship clean — good for provenance, but it means the
   implementation is validated against fixtures that are not the acceptance
   evidence.

dev6 also carries the corrected migration pattern explicitly, with the
rejected one named: **do NOT use the `Document.jurisdiction`/`create_all()`
shape** (works only for fresh-test-only tables; would fail on an
already-provisioned production DB).

| Agent | Gate | Model/effort | Branch | agentId | Outcome |
|---|---|---|---|---|---|
| dev6 | G9 | Sonnet/medium — items/REDs/migration pattern all specified; Haiku considered: no, it ships a schema migration in the first-merging sprint and touches Hebrew-side parsing | `...-dev6` | `ac0a7de0800432e51` | running |

Boundary restated to the IL manager: this sprint builds the seam and data
path only; the IL סימן/חלק rule modules remain the IL panel's own work.

---

## Phase 6b — condition-4 amendment CONFIRMED (program manager, 2026-08-05)

The corrected G9 acceptance split is ratified. The original condition
**conflated "G9 works" with "the combined cross-panel chain works"**; the
positive-control probe (throwaway `StructuralUnitRule` + throwaway
`scope_value` stamp) is the correct isolation of what THIS sprint's merge
can actually promise, and IL's two REDs are rightly the end-to-end evidence
for the combined result **on the IL panel's own schedule**.

**Binding: do NOT hold this sprint's merge for the IL panel's queue.**

Both hardenings ratified: the **kind-not-depth** correctness constraint and
the **two-negative-shapes** (different-VALUED unit vs ABSENT unit)
requirement. Recorded rationale worth keeping for future panels: the
reversed-nesting fixture — חלק below סימן with perfectly monotonic depths —
is a textbook case of **why the convention table is not the data**. The same
principle already bit this program once (the dispatch sprint's erratum:
panels declare `scope_unit_kind` from their OWN measured convention, never
the illustrative table).

### Cross-panel coordination with `2026-08-04-defs-il` — CLOSED

Confirmed by the IL panel manager (`a18597f9be6c49ed6`), no open items:

1. **Sequencing:** the IL-side work (`StructuralUnitRule` deriving units from
   breadcrumbs + the `scope_value` amendment to
   `il_siman_chelek_scope_triggers.py`) lands **after their cycle-4 QA**, not
   before. They have a D-1b Developer and a separator Planner in flight and
   declined to commit a window before QA reports — correct call, and the same
   guess-versus-measure discipline this harness exists to enforce. They will
   ping with a concrete window; **this sprint's merge does not wait on it.**
2. **Boundary recorded identically on both sides:** seam and data path ours;
   IL סימן/חלק rule modules and the `scope_value` amendment theirs; we are
   neither building them nor fencing them out.
3. **Shape confirmed compatible** with both their fixtures: ordered
   `(depth, heading_text)`, depth-2 `.chapter` byte-identical under a
   positive-control pin, deeper entries appended. Their
   `source_chapter=ctx.chapter` chapter-containment tests are green today and
   are the regression surface they would most regret losing — which is why
   the `.chapter` pin is the one this sprint protects hardest.

**Fallback recorded (offered, not requested):** if this sprint's own fixtures
turn out to cover only ONE of the two negative discriminator shapes, IL's two
REDs cover the pair between them — **סימן = different-VALUED unit, חלק =
ABSENT unit**. So once G9 lands, running theirs supplies that coverage without
authoring a third fixture here. dev6 still reports which shapes our fixtures
exercise; this only removes the cost of a gap if one exists.

---

## Phase 7 — G5+G6 delivered with 2 escalations; both verified, resolving differently

dev4 delivered **6 of 8 REDs green** and escalated 2, correctly refusing to
edit tests or touch out-of-gate production code. Merged @ `4c2d526`:
production code only (`registry.py`, `profiles.py`, `us_profile.py`,
`pipeline.py`), **195 insertions / 7 deletions, 0 test files touched**.

**G5 green at BOTH sites.** `RuleContext` gains a defaulted
`resolve_unit_path` bound-resolver; both construction sites bind it as a
closure over the profile's OWN resolver and compute the static `unit_path`
via the same call instead of a bare `()` — so zero logic is duplicated and
`ctx.unit_path` tracks the resolver's None-contract instead of going stale.

**G6 consumed on the live path.** New `ScopeAssignment`; `ScopeKindRule`
gains optional `detect_value`; `determine_scope_assignments` on both profiles
**replays `determine_scope`'s dispatch exactly** so the winning rule can never
drift from what `determine_scope` itself picked; `pipeline.py` fans out one
candidate per assignment. **Anti-broadening is structurally enforced** — the
only two producers of a returned `ScopeAssignment` are the narrow-by-
construction default helper and a rule's own explicit `detect_value`; there is
no third implicit path. That RED is green.

### Escalation #2 (KY dotted numbers) — FIXTURE artifact, NOT a production defect

Manager-verified and **closed without any production change**.
`_ARTICLE_MARKER_RE` (`^@\s+(?P<number>\d+[א-ת]*)\.\s*...`) truncates
`156.106` → `156`. But `ingest_us_statutes.py`'s own docstring states US rows
are *"already-parsed row dicts rather than raw wiki-marker text, **so there is
no `parse_articles` call**"*, and grep confirms `parse_articles` is called
ONLY from `ingest.py` (the IL/wiki path).

**US statutes never touch that regex in production.** The fixture simulated a
US row through the IL ingestion path. dev4 was right to refuse to widen a
jurisdiction-agnostic core regex — and right that it was out of mandate — but
**no follow-on gate is needed either**, which is the part worth recording:
the instinct to open one would have manufactured a wide-blast-radius change
for a phantom production defect. Routed to plan3 to re-author via the
`ingest_us_statutes` row-dict path, preserving real-KY fidelity.

### Escalation #1 (TN dual-scope) — a REAL seam limitation; §8's claim is unproven

Manager-verified in code:
- `_US_CHAPTER_SCOPE_TRIGGERS` (us_profile.py:1112-1117) contains the plain
  substring **`"in this part"`**.
- `determine_scope` (us_profile.py:1120-1125) returns `"chapter"` the instant
  ANY trigger is a substring of the first non-blank line.
- `USProfile.determine_scope`'s own docstring: baseline *"wins whenever it
  already detects `chapter` — never overridden."*

TN's real text *"As used in **this part** and Section 6-51-301..."* trips it,
so the rule loop never runs and the test's own precondition fails before the
seam is exercised.

**The consequence is larger than one fixture: a registered `ScopeKindRule`
can never refine ANY body whose first line trips a baseline chapter trigger.**
Seam v2.8 §8 row 7 asserts "Yes — live-path dispatch proven," which cannot
have been run against the real unmodified baseline.

**Ordered to plan3: MEASURE FIRST** — how many of the 8 U2 rows trip a
baseline trigger? That number decides whether this is one bad fixture or a
structural hole in G6's deliverable. Then recommend among: (a) re-author the
TN fixture to a non-tripping real row (cheapest; papers over the hole if the
blast radius is wide); (b) narrow the baseline trigger (out of gate,
core-owned, risks the 7-states guarantee — manager default is NO);
(c) **decouple KIND from VALUE** — let `determine_scope_assignments` consult
`detect_value` even when baseline won the KIND, since the 7-states guarantee
governs the KIND and baseline has no opinion on the VALUE. Honest limit of
(c), stated in the brief: it yields TN a value but leaves its kind
`"chapter"`, so it may only partially express a genuine dual-KIND scope.
**plan3 may not implement (b) or (c) unilaterally** — both change shipped
dispatch semantics and (c) needs a seam version bump. Escalated to the
program manager because it bears on what v2.8 promised.

---

## Phase 7b — both G6 escalations resolved; G5+G6 GREEN (2026-08-05)

plan3 delivered both fixes. Merged; **suite 815 passed / 3 failed**, and
**G5 and G6 are fully green (8/8 REDs)** — the 3 remaining are G10's
in-flight REDs and the G1 re-point. Verified: seam **v2.10 append-only
(125 insertions, 0 deletions)**; **zero production code touched** by the
Planner.

**KY fixed the better way.** Re-authored onto `ingest_us_statute_rows` (the
production US row-dict path) rather than renumbering to non-dotted values, so
the real dotted KY numbers (`156.106`/`161.605`/`139.486`) persist exactly —
the test is now MORE production-faithful than originally, not less.
`_ARTICLE_MARKER_RE` untouched. plan3 independently re-derived the
"US never uses that regex" conclusion rather than taking the manager's
diagnosis on trust.

**A second defect plan3 found independently — manager-confirmed.**
`pipeline.py`'s `created_assertions.append({...})` carries only `id`,
`assertion_type`, `proposition`, `status`, `origin` — **no
`subject_entity_id`**, though the test read that key. It was fully MASKED
behind the earlier `ImportError`, i.e. the kind of defect that survives a
green suite. Fixed test-side by querying persisted `Assertion` rows. Whether
the RETURN SHAPE should carry the key is latent (nothing else reads it) →
routed to core-follow-on-3, not opened here.

### TN blast radius MEASURED: 1 of 8 — and the MANAGER RULING

plan3 ran `determine_scope` against the real corpus `text` for all 8 U2 rows:
**exactly 1 (TN) trips a baseline trigger.** The other 7 (AK, CT, KY×4, VA)
fall through to `law-wide`, leaving the registered-rule path open as designed.
Per-row table in seam v2.10. **Single-row limitation, not a structural hole.**

**RULING: (c) is NOT implemented this sprint, and the (b) measurement is NOT
commissioned.** Reasons, in order:
1. Measured severity is 1/8; the other 7 work as designed.
2. **(c)-narrow is inert today** (zero `detect_value` consumers), so it would
   change shipped dispatch precedence — in the sprint that merges FIRST and
   that all six panels rebase onto — for zero measurable behavior now.
3. **Decisive: (c)-narrow does not fix TN, its own motivating row.** plan3's
   sharper framing established this: TN's true two-kind (`"part"`+`"local"`)
   split needs the rule's `detect()` to fire independently of baseline's
   `"chapter"` verdict — the BIGGER variant. Changing precedence semantics for
   a change that does not fix the case that motivated it is the wrong trade.
4. **The bigger variant is not a panel-level call.** Letting `detect()` fire
   independently of baseline contradicts the baseline-first-never-overridden
   mechanism seam v2.6/M-D2 established to protect the 7 already-working
   states. That needs a program/director ruling AND a corpus-wide cost
   measurement first — which is why (b) is deferred WITH (c) rather than run
   ahead of it.

**Disposition:** TN ships as a NAMED, documented gap. plan3's partial-(a) —
TN-shaped-but-non-triggering wording in the dispatch proof, **disclosed in
the docstring** so the mechanism is proven live while the real-row gap stays
visible — is the correct handling and the disclosure must survive. Both (b)
and (c) route to core-follow-on-3 **carrying the 1-of-8 measurement**, so the
next owner starts from the number instead of re-deriving it.

### DELIVERABLE CORRECTION (owed to the program manager)

Seam **v2.8 §8 row 7 claimed TN was "Yes — live-path dispatch proven." That
claim was wrong** — it cannot have been run against the real unmodified
baseline. v2.10 corrects it. **G6 therefore ships with 7 of 8 U2 rows
expressible, TN named as a limitation** — not the 8/8 the original gate text
promised.

---

## Phase 8 — G12 Planner verified; implementation spawned (2026-08-05)

plan8 delivered on `claude/defs-core-follow-on-2-plan8` @ `c7b32ec`; merged
@ `a963cb4`. Manager verification: **zero production code touched**; 3 REDs
fail / 3 sanity checks pass; **all 3 fixtures byte-verified by the manager
against the real corpus** (`STATE_IL_C220_A5_S16-102` 9,304 chars,
`STATE_IL_C735_A110_S10` 1,058, `STATE_PA_T15_C57_S5749` 946 — all exact).

**The boundary+emission ruling is now proven with real data, not just
argued.** RED #2 (`STATE_IL_C735_A110_S10`) shows "Government"/"Person"/
"Motion" precede the row's first `means`-entry and are therefore **silently
DROPPED entirely today** — not swallowed into a neighbour. That is exactly
the silent-drop failure mode the manager's Phase-3b ruling predicted when
rejecting boundary-only, and it was speculative when ruled. It is now a
measured, real-row fact.

**Mandate #2 discharged as a genuine negative result:** plan8 searched every
test using `heading_was_derived=True` and every fixture containing
"includes"/"shall include", then EMPIRICALLY simulated the widened regex
against each candidate — **zero core-owned pins rely on idiom-absence.**
Verified, not assumed, and correctly distinguished from the scoped-inline
panel's own re-authored pins (different panel, different file, unmerged
here — not double-counted).

**Measured (M18-compliant, idiom-agnostic denominator):** the population is
defined structurally (`heading_was_derived` True AND primary splitter yields
nothing), never by which idiom words appear — so the denominator does not
come from the grammar being changed. 2,117 fallback-eligible rows corpus-wide
(CA 442, GA 3, IL 1,672); 11,960 quoted-term occurrences; 9,677 recognized
today → 10,170 widened = **+493 newly-recognized entries across 329 rows**.
Of those 493, **0** are preceded by "References to" within 25 chars — the
guard's real trigger rate in this population is currently zero, yet it stays
mandatory per the ruling's program-wide framing.

**P-R10 honestly reported as approximate:** re-derived the ruling's anchor at
49,594 occurrences / 31,588 rows vs the ruling's 50,528 / 32,199 — **~1.9%
low, reported as a close but NOT exact reproduction** because the original
script no longer exists to diff against. Corpus row count 2,038,247 matched
exactly, confirming glob and scope.

**Additional recall limits found and carried forward** (beyond the three
D-INCLUDES named): bare `include` without `-s` stays unrecognized (matching
the ruling's precise wording, not a broader family); and the OR-chain shape
(`"Judicial claim" or "claim" include ...` — two quotes sharing one verb) is
structurally unreachable regardless of vocabulary, since `_QUOTE_TERM_RE`'s
gap-matching stops at the intervening quote. Pre-existing and separate, not
introduced or fixed here.

### MANAGER-FLAGGED FRAGILITY carried into the Developer brief

RED #3 **monkeypatches `_MEANS_IDIOM_GAP_RE` to a hardcoded widened pattern**
(no real row combines the PA construction-clause shape with the fallback path
— plan8 swept all 2,117 and found 0). Consequence: **if the shipped regex
differs in any way from the pattern the test hardcodes, the test validates a
stale pattern rather than the real one.** dev7 is required to quote BOTH its
shipped regex and the test's simulated one and state explicitly whether they
are equivalent, stopping rather than adjusting either if they differ.

Noted for QA: RED #3 guards **G12-2 only** — because it patches the regex
itself, it would still pass if G12-1 were reverted. G12-1 is guarded by REDs
#1 and #2. The division is intentional, but it means #3 must not be read as
evidence for G12-1.

| Agent | Gate | Model/effort | Branch | agentId | Outcome |
|---|---|---|---|---|---|
| dev7 | G12 | Sonnet/medium — both items specified exactly, 3 REDs committed; Haiku considered: no, widens a defining-verb vocabulary under a director ruling with a mandatory guard | `...-dev7` | `a20fef95ffe28f502` | running |

**plan3 acknowledged the (b)/(c) deferral** with no disagreement; G5/G6 are
closed from the Planner side, working tree clean @ `18f0a4b`.

---

## Phase 8b — G12 implemented, verified, merged (2026-08-05)

dev7 @ `2fc6644`, merged. **Suite 821 passed / 3 failed** (G10×2 in flight,
plus the G1 re-point). Manager verification, first-hand:

- **`us_profile.py` only, 61 insertions / 1 deletion, 0 test files touched**;
  full diff read.
- **The flagged monkeypatch fragility is CLOSED — verified by the manager
  independently, which is the whole reason it was flagged.** Shipped regex
  (`us_profile.py:659-662`) and the test's hardcoded simulated pattern
  (test file `:314-317`) are **byte-identical strings with identical
  `re.IGNORECASE` flags**. Extracted both and compared rather than accepting
  the equivalence claim.
- **Exactly two forms added** (`shall include`, `includes`) — bare `include`
  stays unrecognized, matching D-INCLUDES's precise wording rather than a
  broader family.
- **Guard is a literal textual lookback**, as mandated:
  `_REFERENCES_TO_RE = re.compile(r"References?\s+to\s*$", re.IGNORECASE)`
  over a bounded 25-char window, wired as a `continue` at the TOP of
  `_extract_inline_quoted_definitions`'s per-quote loop — before the idiom
  check runs. It tests nothing about idiom presence/absence or sentence
  structure, so it cannot become the broad heuristic D-INCLUDES rejected.
- **G3-sibling's reserved scope untouched**: the `end = ... else len(text)`
  last-entry fallback is not in the diff. Fence held.
- IL/Hebrew: 46 passed, 0 failed.

Note on guard semantics (correct, worth recording): a `References to "X"`
quote is skipped ENTIRELY — it neither starts its own entry nor terminates
the preceding one. That is right: a construction clause is not a definition,
so it should not create a boundary either.

### Gate status after Phase 8b

| Gate | State |
|---|---|
| G1 | landed (one Planner-side re-point outstanding, plan2) |
| G2 | landed |
| G3 (main) | landed |
| G3 (sibling) | **conditional** — pending plan2's both-sides GO/NO-GO |
| G4 | landed |
| G5 | landed, green |
| G6 | landed, green — **7 of 8 U2 rows**, TN a named gap (v2.10) |
| G8 | landed |
| G9 | in implementation (dev6) |
| G10 | in implementation (dev5) |
| G11 | **ruled DO-NOT-SHIP-ALONE** — needs G12 (now landed) **and** G3-sibling |
| G12 | landed, green |

**G11's remaining blocker is now singular:** G12 has landed, so the only
outstanding dependency is the G3-sibling boundary fix — which is itself
gated on plan2's both-sides sample. That single measurement now decides
whether G11's ~39,955-row recall win ships this cycle or defers with its
202-row debt unspent.

---

## Phase 9 — two G8 items from the markers panel: manager rulings (2026-08-05)

### Item 2 — G8's coverage: CONFIRMED same-key only; class-D RE-ROUTED

**Manager-verified in code**, not inferred. `pipeline.py`'s persistence loop
keys on `(owning_art.id, tuple(sorted(candidate.terms)))`. The
containment-update `elif` fires only when `definitions_by_key.get(key)`
returns an existing row — i.e. **same article AND same term set**.

**Cross-term containment produces a DIFFERENT key**, so it hits the
`definition_row is None` branch and simply creates a new row. **G8's
mechanism structurally never fires on it.**

**Ruling: G8 covers same-term key collisions ONLY.** Nothing in this
sprint's records ever claimed cross-term coverage (the G8 items, the
Phase-2 verification entry, and the merge protocol all describe same-key
collisions), so nothing here needs correcting — but the routing assumption
did exist upstream and is now explicitly withdrawn. **Class-D (one term's
text swallowed inside ANOTHER term's `definition_text`) is re-routed to
core-follow-on-3's boundary work.** It is an extraction-boundary problem,
not a persistence-preference problem, and it must not wait on a gate that
cannot close it.

### Item 1 — the named falsifier has a real row class: SPLIT ruling

Markers found exactly the row class plan4 named as its own falsifier: a
degenerate 6-char baseline candidate (`"means:"`) persists first and a
correct 941-char candidate can never displace it, because
`_is_tighter_containment` only replaces when the NEW text is a strict
SUBSTRING of the old — so a longer-better candidate never wins.

**This vindicates the manager's Phase-2 QA attack point #1**, recorded when
G8 merged: *"the criterion prefers the shorter text whenever it is strictly
contained... WRONG if the longer text is a legitimately fuller definition...
Under an absolute zero-miss bar that is a recall loss, not a cleanup."* The
assumption was flagged as unproven; markers supplied the disproving row.

The ruling SPLITS, because the report describes one failure mode and the
manager found a second that is materially different:

**(1a) Improvement-suppression (OBSERVED) → NAMED LIMITATION, routed to
core-follow-on-3.** Option (b), not (a). Reasons:
- **Zero-regression holds for this ordering.** First-wins is today's shipped
  behavior; the degenerate candidate would win without G8 too. G8 neither
  created nor worsened it — this is a capture-quality gap, not new damage.
- **Amending needs a measured FP side** (program law: every fix carries a
  measured before/after; D-Q1 requires conflicts escalate with data). That
  measurement does not exist and is a Planner cycle.
- **A "degenerate-short" guard reintroduces exactly what plan4 rejected with
  data** — it measured and rejected length thresholds as unprincipled and
  tuned to too few rows. Re-adding one unmeasured, late, in shared
  persistence, in the sprint that merges FIRST, is the wrong risk.
- **Design steer recorded for core-3 so it does not start cold:** prefer a
  *semantic emptiness* test over a char-count threshold — a
  `definition_text` consisting of nothing but the defining idiom itself
  (`"means:"`) carries no definitional content, which is principled in a way
  a length cutoff is not. To be measured, not assumed.

**(1b) Reverse-order displacement (MANAGER-IDENTIFIED, UNVERIFIED) →
MANDATORY QA CHECK BEFORE MERGE.** Not in the markers report. If the good
941-char candidate is persisted FIRST and the degenerate `"means:"` arrives
SECOND, then `_is_tighter_containment("means:", <941 chars>)` evaluates:
`!=` ✓, `len <` ✓, and **`"means:" in <941 chars>`** — which is plausible
whenever the long text contains that literal substring. If so, **G8 would
REPLACE a good definition with a 6-char degenerate one.**

That is **new damage introduced by G8**, not pre-existing behavior, and it is
therefore a **merge blocker if it fires** — categorically different from
(1a). **QA must test this ordering explicitly on the real corpus. If it
occurs, G8's criterion must be amended BEFORE merge, not routed to core-3.**

---

# Appendix A — Planner record: plan3 (G5, G6)

Authored by Planner plan3 on `claude/defs-core-follow-on-2-plan3`, which
branched at 8c49498 before this log existed; folded in verbatim at merge
(its own H1 demoted to H2 below, no other edit).

## Sprint log: core follow-on 2 — Planner (G5, G6)

Worktree `/Users/nerya/LexGraph-wt/defs-core-follow-on-2-plan3`, branch
`claude/defs-core-follow-on-2-plan3`, forked from the sprint branch @
`8c49498`. This log covers gates **G5** (`RuleContext.unit_path`) and
**G6** (scope-VALUE seam) only — G1-G4/G7 are other Planners' write-set.

Role boundary held: this Planner wrote tests, the seam-doc v2.8 append,
and this item-definition log. No production `.py` file under
`backend/app/` was edited — a Developer implements against the items
below and the seam doc.

---

## G5 — RuleContext.unit_path

### Verification (byte-read, not assumed)

Both hardcode sites confirmed exactly as briefed:
`backend/app/definition_links/profiles.py:256`
(`HebrewProfile.extract_local_scope_definitions`) and
`backend/app/definition_links/us_profile.py:1421`
(`USProfile.extract_local_scope_definitions`) both build
`RuleContext(article_number=..., chapter=..., unit_path=())` with a
literal `()`.

**One correction to the gate's own one-line framing, reported honestly
because it changes the fix's shape (not its necessity).** `resolve_
unit_path(article, char_offset=None)` is DOCUMENTED and CONFIRMED (direct
read, `us_profile.py:1145-1211`: `if char_offset is None: return ()`) to
always return `()`. Both hardcode sites build their `RuleContext` ONCE,
BEFORE any rule has matched anything, scanning the WHOLE article body — no
match offset exists yet at that point. So a literal `unit_path=()` and a
"real" `resolve_unit_path(article, None)` are **behaviorally identical**
in this exact call shape; the hardcoded value was never factually wrong
for the field it occupies. The genuine gap: **no rule can ever obtain a
NON-empty unit path through `ctx` at all**, because a static, pre-match
field cannot represent "the path at the position where THIS rule's OWN
match lands" — only the rule itself, after it matches, knows that
position. Fixing this needs a bound RESOLVER a rule can call with its own
offset, not a differently-computed static value.

### Items

**G5-1.** `RuleContext` (`rules/registry.py`) gains one new, defaulted
field: `resolve_unit_path: Callable[[int], UnitPath] | None = None`.
Defaulted (not required) so the existing
`test_definition_links_rules_registry.py::
test_rule_context_carries_article_number_chapter_and_unit_path` (which
constructs `RuleContext(article_number=..., chapter=..., unit_path=(step,))`
with no 4th kwarg) keeps passing unchanged.
*Acceptance:* `RuleContext(article_number="1", chapter=None,
unit_path=())` still constructs with no error (regression guard); a
4-kwarg construction supplying `resolve_unit_path=` also succeeds.

**G5-2.** At both real construction sites
(`profiles.py:256`, `us_profile.py:1421`), `resolve_unit_path` is bound to
a closure over the SAME `article_body` string already passed to the rule,
calling the OWNING profile's own `resolve_unit_path` method (`self.
resolve_unit_path(<article-body-carrying stub>, char_offset)`) — zero
duplicated ladder/marker logic, plan1's G2/G4 changes to that method are
automatically picked up. `unit_path` itself is also computed via the same
bound resolver at `char_offset=None` (still legitimately `()`) instead of
a hand-typed literal, so a future change to `resolve_unit_path`'s
`None`-handling can never silently diverge from `ctx.unit_path`.
*Acceptance (RED, live path):*
`test_definition_links_g5_rule_context_unit_path.py::
test_g5_rule_context_delivers_a_real_nonempty_unit_path_to_a_scope_trigger_rule_us`
and `..._il` — a probe `ScopeTriggerRule` calls `ctx.resolve_unit_path
(offset)` at the offset of its OWN regex match and gets back a real,
non-empty `UnitPath`, equal to an independent direct call to `profile.
resolve_unit_path(article, offset)` for the same inputs.

**G5-3 (regression pin, already GREEN — included so it stays proven).**
`ctx.unit_path` for the whole-body call (no rule has matched anything
yet) stays legitimately `()` — `test_g5_rule_context_unit_path_field_
still_correctly_empty_for_the_whole_body_call` (passes today AND after
the fix; not a RED, a documented invariant).

### What must NOT change (G5)

- `resolve_unit_path`'s own internals/ladder logic — plan1's G2/G4
  territory; my tests assert EQUIVALENCE to a fresh direct call, never a
  pinned literal path value, specifically so plan1's legitimate changes
  cannot manufacture a false conflict here.
- No existing rule module's direct `resolve_unit_path` import is removed
  or deprecated — additive plumbing only (gate's own text).
- `extract_local_scope_definitions`'s own Protocol signature — unchanged.

---

## G6 — scope-VALUE seam

### Verification (byte-read, not assumed)

**Manager's "M9 already live" finding: RE-VERIFIED, HOLDS — see seam doc
v2.8 §0 for the full byte-verification** (`DefinitionCandidate`'s tuple
typing, `_value_matches`'s three call sites, `_subsection_contains_
offset`'s tuple normalization — all confirmed by direct read). This does
NOT need re-scoping.

**One correction to the brief's framing, also in v2.8 §0:** the value gap
is not confined to `"chapter"` — `determine_scope` has no `"local"` option
at all today, which blocks 4 of the 8 target rows (all KY) regardless of
the value question. The fix (below) closes both together.

**Panel evidence read directly** (not re-derived): `claude/defs-us-
headings-plan5@8cd3829` — `test_definition_links_us_heading_variants_
cycle5_scope_parse.py` (the genuinely-new heading-text parsing RED, held
by that panel, NOT rebuilt here — write-set fence respected) and
`test_definition_links_matcher_u2_scope_cycle5.py` (matcher-level
containment proof, already green, reused as evidence that containment
itself needs no new work). Full 10-row table read from `defs-us-headings-
log.md`'s 2026-08-04 "U2 gap" entry; NJ/UT re-fetched from the real
corpus this session and confirmed NOT scope-VALUE cases (see seam v2.8
§8) — this is how "10" in the manager's log becomes "8" in this gate's own
text; not a discrepancy, a documented narrowing.

### Items

**G6-1.** New `ScopeAssignment` frozen dataclass (`kind: str, value: str |
tuple[str, ...] | None`) in `rules/registry.py`.
*Acceptance:* importable as `registry.ScopeAssignment`; equality by value
(frozen dataclass default).

**G6-2.** `ScopeKindRule` gains one new, defaulted field: `detect_value:
Callable[[str], ScopeAssignment | tuple[ScopeAssignment, ...] | None] |
None = None`. Verified zero real consumers exist to break (`git grep
register_scope_kind_rule` across every remote branch's `rules/*.py`
matches only `registry.py` itself).
*Acceptance:* every existing `ScopeKindRule(jurisdiction_codes=...,
detect=...)` 2-kwarg construction across the existing suite
(`test_definition_links_rule_dispatch_scope_kind.py`,
`test_definition_links_rule_dispatch.py`) keeps passing unchanged.

**G6-3.** New `JurisdictionProfile.determine_scope_assignments(self,
body_text, *, scope, article_number, chapter) -> tuple[ScopeAssignment,
...]` on `USProfile`, `HebrewProfile`, and the `Protocol`. Dispatch
replays `determine_scope`'s own baseline-first/first-non-None-wins order
exactly (see seam v2.8 §3 for the precise algorithm) so the "winning
rule" can never drift from what `determine_scope` itself picked. Default
value for a rule that wins the kind but declines the value (or when
nothing registered fires): the article's own narrow, self-referential
identity (`chapter` for `"chapter"`, `article_number` for `"local"`,
`None` otherwise) — never a broadening default.
*Acceptance (RED, dispatch-proof, P-R8-shaped):*
`test_definition_links_g6_scope_value_seam.py`, 5 tests:
  - `test_g6_determine_scope_assignments_default_matches_todays_chapter_stamping_us`
    — baseline-only default.
  - `test_g6_scope_kind_rule_detect_value_overrides_the_chapter_value_with_an_enumerated_tuple_us`
    — AK-shaped 9-member chapter tuple override.
  - `test_g6_scope_kind_rule_detect_value_overrides_the_local_value_with_an_enumerated_tuple_il`
    — KY-shaped 2-member article tuple override, IL side (mechanism
    parity).
  - `test_g6_scope_kind_rule_declining_a_value_falls_back_to_the_narrow_default_never_broadens`
    — a rule wins the kind, declines the value, default is narrow not
    broad.
  - `test_g6_scope_kind_rule_can_supply_two_coequal_assignments_tn_dual_scope_shaped`
    — TN-shaped multi-assignment fan-out data shape.

**G6-4.** `pipeline.py`'s Definitions-SECTION stamping loop calls
`profile.determine_scope_assignments(...)` and fans out one
`DefinitionCandidate` copy per returned `ScopeAssignment`, routing
`.value` to `source_chapter`/`source_article_number`/`scope_value` by
`.kind` (existing `_in_scope` dispatch, unchanged). See seam v2.8 §4.
*Acceptance (RED, ONE live-path proof, real corpus words):*
`backend/tests/integration/test_definition_links_g6_scope_value_seam_live.py`:
  - `test_g6_ky_156_106_shaped_section_before_the_fix_wrongly_links_an_uninvolved_ky_article`
    — POSITIVE CONTROL (P-R10), **passes today** on unmodified `main`,
    documents the live bug (today's `"law-wide"` default over-links).
  - `test_g6_ky_156_106_shaped_section_after_the_fix_links_only_the_two_named_sections`
    — RED today (`ImportError: ScopeAssignment`); once G6-1..G6-4 land,
    must produce a `USES_DEFINITION` assertion linking KY article
    `161.605` and must NOT link the uninvolved `139.486`-shaped article,
    through the real `run_definition_linking` entry point.

### Row-by-row: the 8 U2 rows

Full table with per-row reasoning is in the seam doc, **v2.8 §8** (not
duplicated here to avoid the two copies drifting) — summary: all 8
expressible under this design; rows 2 (CT) and 8 (VA) additionally need
ordinary future rule-module work this sprint does not build (value
parsing for CT's prose scope; a `StructuralUnitRule` for VA's new
`"title"` kind) — flagged, not silently assumed away.

### What must NOT change (G6)

- `determine_scope`'s own signature, return type, or dispatch order —
  `determine_scope_assignments` is a sibling, not a replacement.
- `_in_scope` / `_value_matches` / `_subsection_contains_offset` — the M9
  tuple mechanism they already run is reused as-is, zero edits.
- Any existing `ScopeKindRule` registration/lookup test's assertions.
- `Definition`'s schema — no new column; `scope_value` stays transient
  (v2.5's ruling re-applied, not re-litigated — see seam v2.8 §6).
- The headings panel's own value-PARSING rule modules
  (`chapter_range_scope_bounds`, `enumerated_local_scope_targets`, etc.)
  — explicitly their later work, not built here.

---

## Full-suite state at handoff

`backend/.venv/bin/pytest tests/ -q` (this worktree, this branch):
**772 passed, 8 failed** — the 8 failures are exactly the RED tests listed
above (2 × G5 dispatch, 5 × G6 dispatch, 1 × G6 live-path); zero
collateral damage to the pre-existing suite. The 2 intentionally-GREEN
tests (G5's static-field invariant, G6's positive control) are included
in the 772 passed and are load-bearing regression guards, not filler.

---

## Planner response to dev4's 2 escalated fixtures (post-merge of
`claude/defs-core-follow-on-2` @ `4c2d526`, relayed by the manager)

dev4 turned 6 of 8 REDs green and escalated 2, both confirmed by the
manager to be fixture defects rather than implementation gaps (one of
which also exposed a real, narrow dispatch-precedence limitation). Both
addressed below; full reasoning also recorded in seam doc **v2.10**.

### Item 1 — KY live-path test: fixed, no production change needed

Confirmed the manager's diagnosis: my original fixture ingested through
`ingest_wiki_law` (the IL/wiki-marker path), whose `_ARTICLE_MARKER_RE`
requires a pure digit run and truncated the real dotted KY number
`"156.106"` to `"156"`. Confirmed independently, by direct read of
`ingest_us_statutes.py`'s own module docstring and a `grep` for
`parse_articles`'s call sites, that **real US statute ingestion never
touches `_ARTICLE_MARKER_RE` at all** — `ingest_us_statute_rows` maps each
already-parsed row dict directly to one `Article`, storing `section_number`
verbatim. `_ARTICLE_MARKER_RE` correctly stays untouched.

**Fix:** `test_definition_links_g6_scope_value_seam_live.py` rewritten to
ingest through `ingest_us_statute_rows` (the production US path) with the
real KY row-dict shape (`act_id`/`section_number`/`section_title`/`chapter`/
`text`), so the real dotted article numbers `"156.106"`/`"161.605"`/
`"139.486"` persist exactly — more production-faithful than the original
version, not a workaround. Both tests (`before_the_fix` positive control,
`after_the_fix`) pass.

**One additional, previously-latent defect found and fixed while doing
this:** the original test's `after_the_fix` assertion read `a["subject_
entity_id"]` from `result["created_assertions"]`'s own dicts, but
`pipeline.py`'s `_create_assertion` never puts `subject_entity_id` into
that dict (confirmed by direct read, `pipeline.py:448-456`) — this was
masked before the merge because the test failed earlier, at the
`ImportError`, before ever reaching that line. Fixed by querying the
persisted `Assertion` rows by id instead. Not part of dev4's report; found
independently while re-running the corrected test, disclosed here rather
than silently folded in.

### Item 2 — TN dual-scope: real, narrow limitation; measured, not guessed

**Blast radius, measured (not estimated):** `determine_scope(text)` run
directly against the real corpus `text` column for all 8 U2 rows this
gate's §8 table covers. **Exactly 1 of 8 (TN) trips a baseline chapter
trigger** (`"in this part"` is a literal substring of TN's real first line,
"As used **in this part** and Section 6-51-301..."); the other 7 (AK, CT,
KY ×4, VA) correctly fall through to `"law-wide"` and leave the
registered-rule path open. Full per-row table in seam v2.10. **This is a
single-row limitation, not a structural hole across the deliverable** —
but it is real: TN's own real wording is genuinely blocked from reaching a
registered `ScopeKindRule` by the same baseline-first precedence that
protects the 7 already-working states, applied here to a row it wasn't
designed with in mind.

**Options assessed (full reasoning in seam v2.10); none implemented,
per the explicit instruction not to decide (b)/(c) unilaterally:**

1. **(a) Re-author away from TN.** Rejected as the FULL answer — no other
   real row among the 8 demonstrates genuine dual-KIND scope; doing this
   alone would hide the gap rather than disclose it. Adopted in PART: the
   dispatch-proof unit test now uses a body shaped like TN's real
   declaration but phrased to avoid the literal trigger substring, so the
   MECHANISM is proven live while the real-row gap stays visible rather
   than silently papered over.
2. **(b) Narrow `_US_CHAPTER_SCOPE_TRIGGERS`.** Not recommended — core-
   owned, jurisdiction-agnostic, high blast radius, no corpus-wide
   measurement of what currently-correct rows would break; not this
   Planner's to run unilaterally.
3. **(c) Decouple KIND-dispatch from VALUE-dispatch**, gated on the SAME
   rule's own `detect()` also firing (never an unconditional override).
   Verified architecturally clean (assignments fully override whatever
   `scope=` was seeded with, so a mismatch is not internally
   inconsistent) but is a genuine, if narrow, precedence change --
   inert today (zero registered `detect_value` consumers exist), live
   risk only once family panels opt in. Honest limit: even under (c),
   TN's TRUE two-kind (`"part"` + `"local"`) split needs the rule's
   `detect()` to fire independently of baseline's own `"chapter"`
   verdict in the value-consultation loop — getting a richer VALUE for
   baseline's OWN kind is the smaller, safer version of (c); getting a
   genuinely DIFFERENT kind is the bigger version and was not
   distinguished clearly enough in the original ask. **This Planner's
   lean: (c), narrow/gated variant, is the most principled option, but
   needs a program-level ruling and a seam version bump (v2.11) if
   adopted — escalated, not decided here.**

Test corrected (mechanism-proof, non-baseline-tripping body, full
disclosure in its own docstring) and green: `test_g6_scope_kind_rule_can_
supply_two_coequal_assignments_tn_dual_scope_shaped`. Seam v2.8 §8 row 7
verdict corrected from "Yes" to "Partial" in seam v2.10 (append-only —
v2.8's original text is untouched).

### Full-suite state after both fixes

`backend/.venv/bin/pytest tests/ -q` (post-merge of `claude/defs-core-
follow-on-2` @ `4c2d526`): **815 passed, 3 failed** — the 3 failures
(`test_definition_links_g10_term_clause_scope_threading.py` ×2,
`test_us_core_g1_ms_padding_strip_red.py` ×1) belong to gates G10/G1,
outside this Planner's write-set (G5/G6), untouched and unexamined beyond
confirming they are not caused by anything in this response. All of this
Planner's own G5/G6 tests pass, including both items dev4 escalated.

---

# Appendix B — Planner record: plan6 (G9)

Worktree `/Users/nerya/LexGraph-wt/defs-core-follow-on-2-plan6`, branch
`claude/defs-core-follow-on-2-plan6`, forked from the sprint branch @
4a47666 (after G8 and G3+G1 had already merged — verified both defects
still present at this tip before writing anything: `pipeline.py:243`
still hardcodes `heading_breadcrumbs=()`; `sections.py:138` still gates
`.chapter` on a literal `len(break_match.group(1)) == 2`, line numbers
shifted from the brief's 212/138 by G8/G1/G3's own edits elsewhere in
these files, same defects). This log covers gate **G9** only — Planner
owns tests and item definitions, no production `.py` file under
`backend/app/` was edited (`git diff --stat HEAD -- backend/app` is
empty).

## Read before writing anything

Seam spec v2.6 §1 (M-D1, `docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md:1226-1276`)
per the brief — its "input-availability, resolved" paragraph is the
authorizing text: accumulating all depths into `heading_breadcrumbs` is
*"core's own ONE-PLACE additive change (default `()`, so every existing
construction site is unaffected)"*, and US/parquet availability was
separately verified against a real file in a prior sprint (no ingest-
contract escalation needed for US — not built this gate, see "What was
NOT built" below). Also read this log's own "Phase 1b" section (G9's
acceptance reasons) and `claude/defs-il`'s D-1b Planner commit `bc54e1a`
(`git show bc54e1a`) in full — the two existing committed REDs this gate
vendors equivalents from, per the brief's "do not cherry-pick" instruction.

## Design decision: what "the fix" requires beyond the two named lines

The two named defects (`pipeline.py:243` hardcoded `()`, `sections.py:138`'s
`len==2` gate) are the OBSERVABLE locus, but tracing the data path required
by a genuine fix surfaces one more fact worth recording so the Developer
doesn't have to re-derive it: `run_definition_linking` (`pipeline.py`)
operates over ALREADY-INGESTED `Article` ORM rows (`models/article.py`) —
it never re-parses raw wiki text, and `models.document.Document` does not
store the original text either (confirmed by reading both models). Depth
3+ heading text is discarded at PARSE time (`ingest_wiki_law` calls
`sections.parse_articles`, then persists only `.number`/`.heading`/
`.chapter` onto the ORM row — confirmed by reading `ingest.py`). So a
genuine fix has THREE parts, not two, mirroring exactly how `.chapter`
itself already flows end to end:
1. `sections.py` — capture full-depth breadcrumbs additively (item G9-1).
2. `models.article.Article` — one new additive, nullable column to carry
   it from ingest-time to pipeline-time (item G9-2) — see that item's own
   entry below for the corrected migration precedent (a real
   `backend/app/migrations/*.py` module, not `Document.jurisdiction`'s
   fresh-test-only `create_all()` shape) and the merge-sequencing HOLD on
   it.
3. `ingest.py` (persist) + `pipeline.py` (read instead of hardcode) —
   items G9-3/G9-4.

This is NOT scope creep — it is the necessary shape of "core's own
ONE-PLACE additive change" once traced to where the data actually has to
live to reach `pipeline.py:243` at all. No test in this Planner's set
asserts anything about the INTERNAL persistence shape (column name,
serialization format) — every RED goes through the public entry points
(`sections.parse_articles`, `ingest_wiki_law`, `run_definition_linking`)
only, so the Developer is free to choose the concrete column/serialization
as long as the item's observable contract holds.

## Item definitions (G9)

**G9-1 — `sections.py`: capture full-depth heading breadcrumbs, additively.**
New field `Article.heading_breadcrumbs: tuple[tuple[int, str], ...] = ()`
on `sections.Article` (mirrors `.structural_units`'s own existing
additive-default convention in the same dataclass). `parse_articles`
maintains a breadcrumb STACK alongside (not instead of) its existing
`current_chapter` tracking: on any `_HEADING_BREAK_RE` match at depth `d`
with text `t`, pop every stack entry with depth `>= d`, then push `(d,
t)`; every `Article` flushed after that point carries `tuple(stack)` as
its own `.heading_breadcrumbs`. `.chapter`'s own existing `len==2`-gated
assignment is UNTOUCHED — this is a parallel accumulation, not a rewrite.
*Acceptance (RED, unit, byte-verified real fixtures):*
`backend/tests/unit/test_definition_links_g9_heading_breadcrumbs.py`,
4 REDs + 1 regression-pin (see "REDs" below).

**G9-2 — `models.article.Article`: one new additive nullable column.**
Carries G9-1's captured breadcrumbs from ingest-time to pipeline-time (no
other route exists — `run_definition_linking` never re-parses raw text,
see "Design decision" above). Additive, nullable. **Correction to this
Planner's own first pass:** the fresh-test-only `Base.metadata.create_
all()` precedent (`Document.jurisdiction`'s own docstring) is NOT the
right analogy for a column that must survive on an already-provisioned
production database — `backend/app/migrations/add_assertion_subject_
unit_path_column.py` (verified present, read in full) is the real,
already-established convention for exactly this shape: a raw-DDL
`upgrade(engine)`/`downgrade(engine)` pair against a plain `Engine`, no
backfill (`NULL` == "no breadcrumbs known" is the correct, honest value
for every pre-existing row). Follow that file's shape exactly, not
`Document.jurisdiction`'s. Column name/serialization choice is otherwise
the Developer's own; no RED in this Planner's set pins it directly. See
the HOLD note immediately below — this item does not proceed until the
program manager confirms the merge-sequencing question.

**HOLD (2026-08-05, manager verification, not this Planner's call to
lift):** the manager independently re-verified the "no other route"
reasoning above (`pipeline.py`'s `select(Article)` load site does not
re-parse; `Article`'s current columns carry no breadcrumb field;
`add_raw_text_columns.py` covers assertion tables only, no document-level
raw text exists anywhere to re-derive structure from) and confirmed it
holds. G9-2 is held pending a PROGRAM-level merge-sequencing call
(P-R5, program manager's own authority, not a panel-level decision) — this
sprint merges first among pending program merges and all six family
panels rebase onto it, so a schema migration here ripples into every
panel's rebase; that materially changes the "small, additive, safe
default" premise the manager's own G9 acceptance was reasoned on. Per
seam v2.5's own precedent test ("a column becomes right when a concrete
consumer needs to answer it without re-deriving it from source text"),
follow `add_assertion_subject_unit_path_column.py`'s shape exactly if/when
this proceeds (additive, nullable, real `downgrade()`, no backfill). No
Developer is spawned for G9 until the manager confirms; G9-1/G9-3/G9-4 are
unaffected and stand as specified.

**G9-3 — `ingest.py`: persist `heading_breadcrumbs` onto the new column.**
`ingest_wiki_law`'s per-article `Article(...)` construction gains one more
field, sourced from G9-1's `parsed_article.heading_breadcrumbs`, exactly
parallel to how `.chapter` is already threaded there today.

**G9-4 — `pipeline.py`: read real breadcrumbs instead of hardcoding `()`.**
The one `StructuralContext(article_number=art.number,
heading_breadcrumbs=())` construction site (`pipeline.py:243`) reads the
per-article value G9-2/G9-3 persisted (deserialized back into
`tuple[tuple[int, str], ...]`), defaulting to `()` only when the column is
genuinely absent/empty (e.g. a pre-G9 row, or a jurisdiction this gate
does not populate it for — see "What was NOT built"). Safe default
preserved exactly as the seam spec already promises.
*Acceptance (RED, live-path, P-R8-shaped, byte-verified real fixture):*
`backend/tests/integration/test_definition_links_g9_heading_breadcrumbs_live.py`,
1 RED (both containment directions combined — see "REDs" below for why).

## REDs (re-authored, not cherry-picked — new law, new articles, new fixtures)

The two `claude/defs-il` REDs this gate's brief points at
(`test_definition_links_il_siman_chelek_containment_live.py`, commit
bc54e1a) use `חוק לקידום תשתיות לאומיות`/`תקנות המשקלות והמידות` and a
REAL, shipped `il_siman_chelek_scope_triggers.py` rule module that does
not exist on this branch (IL panel work, not yet merged here). Vendoring
their EXACT fixtures/rule would be cherry-picking; instead this Planner
independently read the same read-only corpus and picked a DIFFERENT real
law (`חוק תכנון משק החלב, התשע"א-2011` — Milk Economy Planning Law) with
the same structural shape (chapter > two siblings simanim, byte-verified
this session), plus a SECOND real law
(`תקנות מחלות בעלי חיים (שחיטת בהמות)`) for a non-monotonic-depth edge
case D-1b's own log flagged as a real corpus complication but did not
build a fixture for. Both source files verified present in the read-only
corpus at `/Users/nerya/AI for others/israeli-laws-wiki/data/laws/`; every
excerpted span verified (this session, via direct Python `in`-substring
checks, shown in this Planner's own transcript) a literal, byte-identical
substring of its real source file before being copied into a new fixture
under `backend/tests/fixtures/wiki_laws/`. The corpus itself was never
read by, or made reachable from, any test — only by this Planner's
one-off, non-committed measurement/verification scripts.

### Unit-level (G9-1's capture contract) — 4 REDs, 1 regression pin

File: `backend/tests/unit/test_definition_links_g9_heading_breadcrumbs.py`.
Run: `backend/.venv/bin/pytest tests/unit/test_definition_links_g9_heading_breadcrumbs.py -v`.

1. `test_parse_articles_captures_chapter_and_siman_breadcrumbs_for_a_nested_article`
   — article 3 (`פרק ג': תכנון משק החלב` > `סימן א': הסדרת הייצור
   והשיווק`). RED: `AttributeError: 'Article' object has no attribute
   'heading_breadcrumbs'`.
2. `test_parse_articles_captures_chapter_only_breadcrumbs_when_no_siman_is_open`
   — article 1 (chapter only, no siman nested under it) — same
   `AttributeError`.
3. `test_parse_articles_resets_the_siman_breadcrumb_and_does_not_leak_the_prior_simans_text`
   — articles 12 (last of סימן א') and 15 (סימן ב', same chapter) — same
   `AttributeError`; also pins that a superseding depth-3 heading REPLACES
   rather than appends (a naive stack that only pushes would leave the
   stale סימן א' entry present alongside סימן ב').
4. `test_parse_articles_handles_a_real_non_monotonic_depth_sequence` —
   the `תקנות מחלות בעלי חיים` fixture, where a REAL depth-4 heading
   appears BEFORE the depth-3 heading it nests under (D-1b's own flagged
   complication, reproduced against an independently-found file, not
   theirs) — same `AttributeError`.
5. `test_the_existing_len_two_chapter_gate_stays_byte_identical_alongside_the_new_field`
   — the depth-2 NON-REGRESSION pin: pins `.chapter` to the EXACT values
   today's unmodified `parse_articles` already produces for every article
   these fixtures touch (confirmed by running against today's code before
   writing the other 4 tests). **This one PASSES today** (positive
   control — `.chapter` is untouched by this gate's design) and must keep
   passing unchanged after G9-1 lands; if it ever goes red, the Developer
   changed `.chapter` behavior, which this gate forbids.

Actual run today (`4 failed, 1 passed`), full text captured this session;
all 4 failures are the identical one-line `AttributeError` above (correct
reason — the field genuinely does not exist yet, not a fixture/import
error).

### Live-path (G9-4's consumption contract, P-R8) — 1 RED

File: `backend/tests/integration/test_definition_links_g9_heading_breadcrumbs_live.py`.
Run: `backend/.venv/bin/pytest tests/integration/test_definition_links_g9_heading_breadcrumbs_live.py -v`.

`test_a_structural_unit_rule_receives_real_siman_breadcrumbs_and_containment_holds_in_both_directions_live`
registers (jurisdiction code `US-HI`, verified unused by any other
rule-registration test on this branch — `git grep -c "US-HI"` → 0 hits in
both `backend/tests` and `backend/app`, so this cannot pollute the real
`"IL"` dispatch path or collide with any sibling gate's own probe codes)
a `ScopeTriggerRule` that stamps a real `"siman"`-scoped `Definition` for
the real word `"מוצרי חלב"` from article 3's genuine body, and a
`StructuralUnitRule` whose `.derive` DYNAMICALLY reads
`ctx.heading_breadcrumbs` for a depth-3 entry (not hardcoded per article,
unlike QA gate A2's own `ctx.article_number`-keyed probe — A2 predates
this gate and deliberately avoided `heading_breadcrumbs` because it was
already known dead; this test's whole point is that field). Runs the REAL
`ingest_wiki_law` + `run_definition_linking` and inspects the REAL created
`USES_DEFINITION` assertions, both directions combined in one test
(same-סימן article 12 must link, different-סימן article 15 must not —
combined per the established M16/D-1b precedent so the test is not
vacuously green on the non-leakage half alone, since nothing links
anywhere yet today).

Actual failure today, quoted verbatim:
```
AssertionError: expected article 12 (SAME סימן א' as the defining article 3) to get a USES_DEFINITION edge for its genuine mention of "מוצרי חלב" in its own body -- this requires a live StructuralUnitRule to have received article 12's real depth-3 breadcrumb ("סימן א': הסדרת הייצור והשיווק") through ctx.heading_breadcrumbs and stamped a matching ScopeUnit; got uses_props=[], created_assertions=[]. If this is empty, pipeline.py's StructuralContext(heading_breadcrumbs=()) hardcode (or sections.py's discarded 3+-equals heading text) is still starving StructuralUnitRule.derive of real data.
assert False
 +  where False = any(<generator object ...>)
```
The Definition-capture assertions (`len(term_defs) == 1`, `scope ==
"siman"`) pass BEFORE this failure — proving the `ScopeTriggerRule` half
fires correctly and the failure is isolated to CONTAINMENT (the
`StructuralUnitRule`/breadcrumbs half), the exact defect this gate targets
and not some other cause.

**Why this proves CONSUMPTION, not mere population:** the assertion under
test is an END-TO-END observable answer (`USES_DEFINITION` assertions
created by the real pipeline, read back through
`result["created_assertions"]`), not an inspection of
`StructuralContext.heading_breadcrumbs`'s own value or `Article.
structural_units`'s own contents. `_derive` reads `ctx.heading_breadcrumbs`
DYNAMICALLY per article (no article-number branching) — if the Developer's
fix populated the field but with WRONG data (e.g. the wrong depth, stale
text, or a value that doesn't match `defining_siman`'s exact string), this
test would still fail, exactly as a population-only test would NOT catch.

## Depth-2 non-regression proof (not an assertion — measured two ways)

1. **Execution-level:** the EXISTING, UNEDITED
   `backend/tests/unit/test_definition_links_sections.py` (10 tests,
   including its own `test_article_records_its_nearest_preceding_chapter_
   heading`) plus `test_definition_links_profiles.py` (25 tests) and
   `test_definition_links_models.py` (4 tests) — 35 tests total, ALL still
   PASS, unedited, run this session:
   `backend/.venv/bin/pytest tests/unit/test_definition_links_sections.py tests/unit/test_definition_links_profiles.py tests/unit/test_definition_links_models.py -v`
   → `35 passed`. `git diff --stat HEAD -- backend/tests/unit/test_definition_links_sections.py`
   is empty — this Planner touched zero bytes of that file.
2. **Assertion-level, this Planner's own fixtures:** item G9's own
   `test_the_existing_len_two_chapter_gate_stays_byte_identical_alongside_
   the_new_field` (above) pins the EXACT `.chapter` values for every
   article these NEW fixtures touch, confirmed against today's unmodified
   code before the other REDs were written, and passes today as a
   positive control.

## Measured before/after (read-only corpus scan, never touched by a test)

One-off script (`/private/tmp/.../scratchpad/g9_measure.py` — not
committed, not importable, not part of the test suite), mirroring
`sections.parse_articles`'s exact control flow plus the additive
breadcrumb-stack G9-1 specifies, run read-only against the corpus at
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws` (6,133 `.wiki`
files — this file count independently matches the corpus-size denominator
already cited elsewhere in this codebase's own comments, e.g.
`sections.py`'s M8(a) note, cross-validating this measurement targets the
same corpus snapshot):

| Denominator | Value |
|---|---|
| total `.wiki` law files scanned | 6,133 |
| files containing >= 1 depth>=3 (`===`+) heading | 3,064 (49.96% of files) |
| total depth>=3 heading-break LINES (currently-discarded heading text — M18 entry-line count) | 14,393 |
| total articles parsed corpus-wide | 128,234 |
| articles gaining a non-empty breadcrumb tail beyond `.chapter` once fixed | 50,472 (39.36% of all articles) |

**Why these generalize:** the script does not approximate or sample — it
runs the SAME regexes (`_ARTICLE_MARKER_RE`, `_BARE_ARTICLE_MARKER_RE`,
`_HEADING_BREAK_RE`) and the SAME control flow as the real
`sections.parse_articles`, over every real file, so "articles gaining a
breadcrumb tail" is not an estimate — it is what the exact algorithm this
gate's REDs pin produces, corpus-wide. The algorithm itself is validated
against ground truth by this Planner's own 4 unit REDs (hand-verified
expected breadcrumbs for 2 real files, 3 fixture excerpts, covering the
2-level, chapter-only, reset/non-leak, and non-monotonic-depth cases) —
not merely asserted to be correct.

**P-R10 probe-sanity, CORRECTED (2026-08-05, manager verification of this
Planner's delivery):** this Planner's first pass at this note flagged its
own bare-marker sub-check (same `_BARE_ARTICLE_MARKER_RE` regex, same
corpus) reproducing **42** files instead of `sections.py`'s M8(a) code
comment's "124 of 6,133" as an unreproduced discrepancy. The manager
identified the actual reference: the program doc's own **P-E3** (append,
"cross-panel factual correction," program-manager-probed on the real
corpus) already supersedes M8(a)'s "124" — verbatim: *"the IL panel's E5
'124 bare-@ laws / 12 with definitions' framing is corrected — real
bare-@ occurrences are 331 across 42 files, ALL followed by table/list
markup, never by a heading."* **42 is the corrected figure, and this
script's own read-only measurement hit it exactly.** This is therefore a
PASSED P-R10 sanity check, not a gap — the same scanning approach used
for this gate's own two new numbers independently reproduced an
already-corrected, program-level corpus figure, which strengthens
confidence in 14,393/50,472 rather than merely leaving them unchecked.

## What the Developer must implement

**No Developer is spawned for G9 yet** — G9-2 (the new persisted column)
is held pending the program manager's own merge-sequencing call (see the
HOLD note under G9-2 above); G9-1/G9-3/G9-4 depend on it existing, so the
whole gate waits together rather than a partial build. The below is the
implementation spec for once the hold lifts.

- G9-1/G9-2/G9-3/G9-4 above, in order (G9-1 has no dependency; G9-2/3/4
  depend on G9-1's field existing).
- Column/serialization choice for G9-2 is open — JSON is one reasonable
  option (Hebrew heading text may contain arbitrary characters including
  `:`/`>`, ruling out a naive delimiter scheme like `_serialize_unit_path`'s
  own `kind:value>kind:value` convention elsewhere in `pipeline.py`).
- `heading_breadcrumbs=()` must remain the default read path whenever the
  new column is null/absent (pre-G9 rows, or a jurisdiction this gate does
  not populate — see below) — the safe-default promise the seam spec
  already makes.

## What must NOT change

- `sections.py`'s existing `.chapter` computation/gate (`len(break_match.
  group(1)) == 2`) — G9-1 is additive alongside it, never a rewrite.
- `StructuralContext`'s existing shape (`article_number`,
  `heading_breadcrumbs: tuple[tuple[int, str], ...]`) — already fully
  specified by seam spec v2.6 §1; no seam-doc version bump needed for this
  gate (the DATA source changes, the CONTRACT shape does not).
- Any existing test in `test_definition_links_sections.py`,
  `test_definition_links_profiles.py`, `test_definition_links_models.py`,
  or any other already-passing IL test — all verified passing UNCHANGED
  this session (see "Depth-2 non-regression proof" above). Per the brief:
  editing one of these to fit would be a planning bug, escalated rather
  than done; none needed editing.
- `matcher._in_scope` / `_value_matches` / `_subsection_contains_offset` —
  already proven live and correct by QA gate A2
  (`test_dispatch_qa_gate_a2_structural_unit_rule_live.py`); G9 only fixes
  what feeds INTO the `StructuralContext` that dispatch already consumes
  correctly. Zero edits needed or made.

## What was NOT built (explicitly out of scope, flagged not silently assumed)

- **The IL siman/chelek `StructuralUnitRule`/`ScopeTriggerRule` rule
  modules themselves.** This gate unblocks them (real data now reaches
  `StructuralUnitRule.derive`); building them is the IL panel's own future
  work per the brief ("their M20 escalation") and this sprint's P-R1
  panel/shared-module fence. This Planner's live-path RED registers its
  OWN throwaway probe rules (jurisdiction `US-HI`) purely to PROVE the
  seam is live — not a shipped rule module.
- **`ingest_us_statutes.py` (US/parquet ingestion) reading the real
  `breadcrumb`/`display_path`/`chapter_name`/`title_number` parquet
  columns.** The seam spec's own "input availability, resolved" note
  confirms these columns EXIST in real parquet files (verified in a prior
  sprint) — but confirming a column's EXISTENCE is not the same as this
  gate WIRING it, and neither of the two named defects in this gate's
  brief mentions `ingest_us_statutes.py`. G9-4's fix in `pipeline.py`
  reads generically (whatever the ORM row's new column holds, defaulting
  to `()`), so it is NOT US-hostile — a future gate can wire
  `ingest_us_statutes.py` to populate the same column with zero further
  `pipeline.py` change. Flagged as a natural, low-cost follow-on, not
  built here (no US parquet fixture was byte-verified this session, and
  the brief's own "main risk" framing is entirely IL/Hebrew).

## Full suite state, this worktree, this branch

`backend/.venv/bin/pytest tests -q` → **22 failed, 797 passed** (up from
the pre-existing **17 failed, 796 passed** baseline confirmed at this
branch's tip before writing anything — the 17 pre-existing failures are
OTHER gates' own still-open REDs, G2/G4/G5/G6, untouched by this Planner).
The 5 new failures are exactly this gate's own REDs (4 unit + 1
live-path); the 1 new pass is this gate's own regression pin. Zero
collateral damage anywhere else in the suite.
