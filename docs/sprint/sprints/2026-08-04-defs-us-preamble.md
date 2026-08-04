---
id: "2026-08-04-defs-us-preamble"
status: planning
current_role: planner
branch: claude/defs-us-preamble
worktree: /Users/nerya/LexGraph-wt/defs-us-preamble
locked_by: "claude-code:planner"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US family 2 — body preambles without the word "Definitions"

## Mandate

Capture definitions sections whose only signal is a body preamble that never
uses the word "Definitions": GA's `"As used in this chapter, the term:"`
(173/400 sampled instances missed; GA capture is 0), MD and NE (0% capture,
no heading signal at all — strictly worse than GA), MS (0%), SD (dominant
miss type: `"For the purposes of this chapter, the term, X, means…"` under
term-name headings), plus low-volume instances in OR/PA/RI/SC/TN/TX/UT/VT.
This is the family the prior sprint deliberately skipped to protect zero
false positives — P-R2 escalation is EXPECTED here: bring the director real
conflict examples rather than silently choosing recall or precision.

## Acceptance gates (program manager-defined)

- **U1 — Every preamble variant is captured**, with RED tests from real GA/
  MD/NE/MS/SD rows before implementation.
- **U2 — Scope is stamped correctly and enforced** for scoped preambles
  ("As used in this chapter…" → chapter scope), live-path both directions,
  built on the core seam.
- **U3 — Rules ship as registry modules** per the core seam spec; zero edits
  to shared modules.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for preamble signals; every hit captured or proven not-a-definition.
- **U5 — Nothing regresses**: baseline states hold; all existing tests
  green; false-positive risk is the KNOWN hazard of this family — any
  precision/recall trade escalates per P-R2 with examples.
- **U6 — Measured before/after** full-corpus capture-rate report (GA must
  move from 5/28,154; report the new number honestly).

## Coordination

Core sprint owns scope plumbing + registry; read its published `## Seam
spec` from branch `claude/defs-core-scope`; merge after core. Registry
registrations are append-only. Out-of-family misses are reported to the
program manager for routing. Overlap warning: preamble detection feeds the
scoped-inline family (a preamble is often also a scope trigger) — the
boundary is: THIS sprint owns recognizing a definitions-bearing BLOCK with
no heading signal; the scoped-inline sprint owns scope-trigger parsing
inside otherwise-ordinary sections. Ambiguous cases escalate to the program
manager rather than being claimed by both panels.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager findings (full detail in `-log.md`, M-R1/M-R2)

Manager ran a full-corpus (not sampled) live probe of the real Stage-2 path.
The family-2 miss is **two gates**, not one regex:

| State | rows | preamble-signal | GATE A `_is_placeholder_heading` | GATE B `_BODY_DEFINITIONS_PREAMBLE_RE` |
|---|---|---|---|---|
| GA | 28,154 | 1,224 | **1,222 pass** | **1 pass** |
| MD | 39,552 | 1 | 0 | 0 |
| NE | 25,997 | 2 | 0 | 0 |
| MS | 158,688 | 637 | 0 | 0 |
| SD | 39,589 | 218 | 0 | 0 |

- **GA — single-gate fix**: Gate A already passes (bare citation breadcrumb
  heading); only the Gate-B regex's literal-"Definitions" requirement blocks
  `"As used in this article, the term:"`. Bodies then carry ordinary
  `(1) "Term" means` markers the existing extractor handles.
- **MD/NE/MS — fail Gate A**: their headings are *unrecognized placeholder
  shapes* (`"§5–114."`, `"View Statute 44-4051"`, `"Miss. Code Ann. §
  27-65-201"`). Widening the placeholder recognizer is shared-module work →
  coordinate with core, do not edit `pipeline.py` here.
- **MD/NE convention is NOT confirmed to be the GA shape** (1 and 2 rows
  respectively; both NE hits are false positives). Inventory them from real
  rows before writing tests — assuming GA's shape would be a planning bug.
- **SD — fails Gate A because its headings are real** (`"Loan processor or
  underwriter defined"`), and its term is **unquoted/comma-delimited**
  (`the term, X, means`), which no current extractor parses.

Three cross-sprint boundary conflicts are open (log M-R2): MS reads as
scoped-inline; SD overlaps the headings sprint's verb-form family; SD's
unquoted term is markers-sprint territory. The Planner quantifies each with
real rows; the manager then escalates per P-R2.

## Next Steps

D0-D2 done (Planner attempt #2, full detail in `-log.md`). **D0 is an open
ESCALATION**: core's branch (`origin/claude/defs-core-scope`) has ZERO
backend code as of this writing — verified via `git diff --stat` — so
whether `BodyPreambleRule` registry dispatch is tried for a heading that
already failed the placeholder gate (M-R7(a)) cannot be settled from code.
Items 2-9 below are written to be correct under EITHER answer, with their
core-dependency shape spelled out per item; item 1 is the escalation itself.

1. **Settle M-R7(a)** (blocking design question, not a code change). CHECK:
   a direct answer from core's Planner/the director, or core's Stage B
   landing and being re-read. Until answered, items 3/4/6/8 below cannot be
   marked done even once `us_body_preamble.py` exists and is correct,
   because whether the rule ever RUNS for MD/NE/MS/SD depends on this.
   **Blocked on core** (or the director, per the escalation's lean (b)).

2. **GA capture** — register a `BodyPreambleRule` recognizing "As used in
   this &lt;chapter/article&gt;, the term:" (1,222/1,224 real rows already
   pass Gate A regardless of M-R7(a)'s answer — GA is NOT gated by the open
   question). Serves **U1, U6**. CHECK: `test_us_body_preamble_capture_
   red.py::test_ga_as_used_in_this_chapter_the_term_is_captured` and both
   GA tests in `test_definition_links_us_preamble_family.py` go green;
   full-corpus GA rate re-measured (was 5/28,154 per the program dossier,
   target ~1,222+/28,154). **Blocked on core's registry mechanism
   (Seam 2) landing at all, NOT on M-R7(a)'s specific answer.**

3. **MD capture** — register recognizing "In this &lt;section/subtitle/
   title&gt;... the following words have the meanings indicated." Serves
   **U1, U6**. CHECK: `test_md_in_this_section_the_following_words_have_
   the_meanings_indicated` green; full-corpus MD rate measured (was
   0/39,552, target up to 3,327/39,552). **Blocked on M-R7(a) resolving
   favorably (branch: registry tried regardless of heading) OR core
   separately widening `_is_placeholder_heading`/Gate A to recognize MD's
   `"§N–NNN."` shape (branch: gate still wraps dispatch) — a hard core
   dependency either way, exact shape depends on the answer.**

4. **NE capture, quoted subset (46/559)** — register recognizing NE's "For
   purposes of.../In the &lt;Named Code&gt;:" preambles. Serves **U1, U6**.
   CHECK: `test_ne_in_the_named_code_quoted_term_means_is_captured` green.
   **Same dependency shape as item 3** (NE's heading, "View Statute
   N-NNNN", fails Gate A the same way MD's does).

5. **NE unquoted subset (511/559) + SD unquoted subset (124/218)** — no
   further work possible in THIS sprint's file; both are confirmed live
   (D1/D2) unparseable by any current extractor even with a perfect
   heading. Serves **U1** (documents the miss rather than silently
   dropping it). CHECK: `test_ne_unquoted_term_means_needs_markers_sprint_
   too` / `test_sd_unquoted_comma_term_needs_markers_sprint_too` go green.
   **Blocked on `2026-08-04-defs-us-markers`, not core.**

6. **MS capture, BLOCK-shaped rows** — register recognizing "As used in
   this article/chapter/section, the term:" for MS's bare "Miss. Code Ann.
   § N-N-N" headings. Serves **U1, U2, U6**. CHECK: `test_ms_as_used_in_
   this_article_the_term_is_captured` green; full-corpus MS rate measured
   against the D2 discriminator's BLOCK-subset estimate (~400-450/637).
   **Same dependency shape as item 3** (MS's heading also fails Gate A
   outright).

7. **MS CLAUSE-shaped rows (~190-240/637) — routing, not building.** Per
   the D2 split proposal, these route to `defs-us-scoped-inline`, pending
   the program manager's P-R2 ruling on the item-level split table. Not
   this sprint's file. CHECK: program manager's routing decision recorded
   in the program log; the receiving sprint's own gate covers it. Tracked
   here only so it is not silently dropped by either panel.

8. **SD capture, quoted subset (15/218)** — register recognizing SD's "For
   the purposes of this chapter, the term "X" means". Serves **U1, U2,
   U6**. CHECK: `test_sd_the_term_quoted_means_is_captured` green. **Sharper
   dependency than items 3/4/6**: SD's headings (e.g. "Loan processor or
   underwriter defined") are genuinely NOT placeholders — `_is_placeholder_
   heading` correctly returns `False` for them, so no amount of widening
   the placeholder-recognizer's pattern list can rescue SD the way it can
   MD/NE/MS. Under M-R7(a)'s branch 1 (registry tried whenever baseline
   returns None, for any reason) SD unlocks with NO further core change.
   Under branch 2 (gate wraps everything), SD is not just blocked but
   **structurally unreachable by a `BodyPreambleRule` under the current
   architecture** — informative-but-non-Definitions headings never reach
   body derivation at all, and rescuing SD would need a different
   mechanism than this sprint's file can provide. This is the sharpest
   consequence of M-R7(a) found in this sprint and strengthens the case
   for resolving it directly rather than waiting for a full core
   implementation (see the escalation's lean).

9. **Scope stamping for chapter-scoped rows (GA/MS)** — "As used in this
   chapter/article" needs core's `determine_scope` (Seam 1/C2, core's own
   "Done here" list) to recognize it as an English chapter-scope trigger.
   Not this sprint's file to build. Serves **U2**. CHECK:
   `test_us_body_preamble_scope_red.py::test_chapter_scoped_ga_definition_
   links_a_same_chapter_use_but_not_a_different_chapter_use` goes green in
   BOTH halves (capture AND the in-scope/out-of-scope split). **Blocked on
   core's C2 scope-trigger coverage of this specific phrasing** — a
   separate, named dependency from M-R7(a).

10. **Regression guard** — baseline states (IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/
    NY/OK) and existing IL/Hebrew tests stay green, unedited. Serves **U5**.
    CHECK: `backend/.venv/bin/pytest backend/tests -q` — pre-sprint 641
    passing tests all still pass. **Already true today** (641 baseline + 6
    of this sprint's own green tests = 647 passed, 12 intentional RED,
    verified at commit `38ee931`) and true by construction (zero edits to
    `pipeline.py`/`matcher.py`/`profiles.py`/`extract.py`). Not blocked on
    anything.

11. **Full-corpus before/after measurement** — once items 2/3/4/6/8 land,
    re-run a D1-style live scan across all 5 states (GA/MD/NE/MS/SD) plus
    ideally the contract's named low-volume states (OR/PA/RI/SC/TN/TX/UT/
    VT) to report the honest new capture number (GA was 5/28,154 per the
    program dossier). Serves **U4, U6**. CHECK: a probe script's output
    committed to the log, old vs. new counts side by side, every hit
    manually judged captured-or-proven-not-a-definition (U4's zero-miss
    sweep bar). This is QA's deliverable per the harness role split, not
    the Planner's — flagged here so it is not lost.

## Manager status (2026-08-04, after both Planners)

Both Planner instances ran to completion **concurrently in one worktree** and
are reconciled as ONE deliverable: `bd18411..f77eec3`. (My earlier
"Planner died" diagnosis was wrong — retracted in log M-R8.)

**Verified by the manager directly** (log M-R10): diff is additions-only with
**zero edits to `pipeline.py`/`matcher.py`/`profiles.py`/`extract.py`/
`us_profile.py`** (U3 holds by construction); suite is **12 failed, 647
passed** against a 641-passing baseline, so **U5 is intact**; the RED tests
drive the real ingest + real `run_definition_linking` and fail for the right
reason; **all 12 fixture rows are byte-exact real corpus rows**; no test
reads the snapshot.

**Routings approved by the program manager**: item 7 (MS clause rows) →
`defs-us-scoped-inline`; item 5 (NE/SD unquoted shapes) → `defs-us-markers`.
The `find_term_uses` case-sensitivity finding → core.

**Items 3/4/6/8 are HELD** pending core's seam-v2 ruling on M-R7(a).

**Items 2 and 9 are blocked on core's registry existing at all** — verified:
core's branch is docs-only and has no `rules/` package. Manager ruling: do
NOT force GA through the frozen shared modules (`_BODY_DEFINITIONS_PREAMBLE_RE`
is slated for deletion by core). No Developer work is available in this
sprint until `rules/` lands.

**Open defects for Planner/QA** (manager does not edit tests): (a) three test
names say "misses" while asserting the fixed behavior — rename; (b) the
fixture README wrongly says `pyarrow` is not installed in `backend/.venv`
(it is, and it is declared at `backend/pyproject.toml:15`).

**Active work**: all-state inventory per director ruling D-PREAMBLE-ALL.

## Director ruling D-PREAMBLE-ALL (main @ 321ddab) — sprint scope is now all states

*"I explicitly asked researching and writing code for all of the states."*
Supersedes QA's options A/B/C. **Dispatch stays UNGATED** (core's M6,
director-confirmed) — so **M-R7(a) is ANSWERED (branch 1) and items 3/4/6/8
are UN-HELD**. Precision now comes from **inventoried per-state rules +
negative guards**, not from gating.

**Worklist** = QA's measured candidate population: **7,383 rows / 2,038,247
scanned**, 1,468 gated + **5,915 ungated-only**, touching **50 of 53
jurisdictions**. Diffuse, not concentrated: top 6 states hold 69%; the
remaining 1,813 rows spread over 44 jurisdictions at 1–142 each. Only 5
states have ever been inventoried — ~3,079 ungated-only rows sit in 41
states with no inventory, no test, no routing.

Per state, classify: **BLOCK-shaped** (ours → capture rules), **CLAUSE-shaped**
(scoped-inline's → hand off with data), **hazard** (→ negative guards).

**Scale-out design (M-R15)**: 4 parallel **read-only** inventory scouts
(disjoint jurisdiction slices, findings to disjoint scratchpad files, no repo
writes, no git) → then **ONE** consolidating Planner as sole writer. This
avoids the two-writers-in-one-worktree hazard from M-R8 by construction.
Slices: S1 FL/NC/AL/MO · S2 FED/DC/NY · S3 the 39 low-volume states ·
S4 re-classify GA/MD/NE/MS/SD + gated CA/IL.

Also folded in: the MS chapter-scope U2 RED test (QA-flagged gap), and
per-state CLAUSE row lists packaged for scoped-inline routing.

**Still blocked**: implementation. Core is docs-only with no `rules/`
package. Inventory + RED authoring proceed now; code follows core's merge.

Suite at `eb1f0d8`: **648 passed, 12 RED** (641 baseline intact).

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Manager setup complete: worktree + venv + identity verified. U5 baseline
measured: **641 passed, 0 failed** at `bd18411`.

**Core seam spec IS published** (log M-R7). This sprint's entire deliverable
is one new file `backend/app/definition_links/rules/us_body_preamble.py`
(rule kind `BodyPreambleRule`, `derive_heading: body -> synthesized heading |
None`, registered via `register_body_preamble_rule`) plus our own tests.
Detection kinds are baseline-first, registry-second, first-match-wins in
filename-sort order. Zero edits to `pipeline.py`/`matcher.py`/`profiles.py`/
`extract.py` — that satisfies U3.

**Open question M-R7(a)**: `BodyPreambleRule.derive_heading` receives only the
body, never the heading. If registry rules are tried whenever the baseline
returns `None` (regardless of heading shape), MD/NE/MS/SD are unblocked with
no core dependency — but gate A's false-positive guard is gone and all
precision risk lands on our rule. Planner must settle this against core's
real code before tests are finalized.

Planner attempt #1 died mid-exploration with no work product and no partial
state (log M-R5); attempt #2 runs the same brief with an incremental
commit-per-deliverable requirement.
