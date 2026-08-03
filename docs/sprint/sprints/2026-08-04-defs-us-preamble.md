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

1. **Convention inventory (real rows, live code)** for GA/MD/NE/MS/SD —
   confirm or correct the manager's table; establish MD/NE's actual
   definition-introducing convention.
2. **Boundary dossier** for the three M-R2 conflicts with counts + real
   `act_id` examples, sufficient for a director decision.
3. **RED tests** (live-path, proven red) for the unblocked GA fix and for
   whatever MD/NE inventory establishes; vendored small real-row fixtures
   only — no test may read the parquet snapshot.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Manager setup complete: worktree + venv + identity verified. Core seam spec
not yet published — plan and author RED tests meanwhile; developers do
non-shared-module work only until core merges. Planner spawned with the
findings above.
