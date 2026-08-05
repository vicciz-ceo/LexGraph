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
