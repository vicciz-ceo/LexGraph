---
id: "2026-08-05-defs-il-certification"
status: planning
current_role: planner
branch: claude/defs-il-certification
locked_by: null
locked_at: null
last_agent: "claude-code:panel-manager-defs-il"
last_updated: "2026-08-05T09:49:42Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-04-defs-il"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/sprints/2026-08-04-defs-il.md
---

# Sprint: Israel — inverted certification of definition capture

**DRAFT — awaiting program-manager sanity-check. No Planner spawns until
signed off.**

## Mandate

This is the IL track of **D-CERT**, the program close. Every prior IL
cycle worked *forwards*: pick a signal, sweep for it, fix what it finds.
Three cycles did that and each one surfaced a class the previous cycle
missed — most recently, three independent variant hunts each missed a
spelling variant the next one found (M17 spellings, M21 `הכרזה`/`אכרזה`,
M22 `זו`/`זאת`). Forward sweeping cannot terminate, because its
denominator is whatever the sweeper thought to look for.

This sprint **inverts** it. We fix a signal-agnostic denominator of every
plausible definition candidate in the corpus, assign **every single one**
to a cluster with a committed, executable predicate, and prove
mechanically that the assignment is exhaustive and disjoint. Then every
cluster is disposed to one of four buckets with a measured error rate.
The claim at the end is not "we swept and found nothing more" — it is
"here are N candidates, here is the disposition of each, here is the
measured error rate of each disposition, and here is the script that
re-derives all of it."

## The denominator (measured, not estimated)

Independently measured **twice** — by the phase-2 manager (M19-EXT) and
re-derived from scratch by the phase-3 manager (M22 follow-up), using the
production `sections.parse_articles`, over the full read-only corpus:

```
files                                6,133      (both runs agree exactly)
articles (production parse)        128,234      (both runs agree exactly)
raw quote characters               276,815      (phase-2: 276,628; delta 0.07%)
word-internal (abbreviations)       91,605      33.1%  (phase-2: 91,431; 33.1%)
delimiter-eligible                 185,210      (phase-2: 185,197)
==> paired candidate spans         ~92,605      (phase-2: ~92,598)
```

**~92,600 candidate spans.** Two independent derivations agreeing to
within 0.07% is the standard this denominator is held to; the residual
delta is itself an item (see C1).

**Included on purpose: `הגדרות`-headed articles.** Every prior IL sweep
excluded them because their dispatch path differs. That exclusion is
exactly the signal-dependence D-CERT outlaws, and it is not repeated here.

### The quote character is NOT one character — phase-3 finding

The phase-2 spec said "raw `"` characters". Measured per codepoint, the
population is a **mixture of four**, with radically different behaviour:

| codepoint | raw | word-internal | eligible | ~spans |
|---|---:|---:|---:|---:|
| `U+0022` straight quote | 256,680 | 32.7% | 172,826 | 86,413 |
| `U+05F4` Hebrew gershayim | 7,649 | **98.7%** | 103 | 51 |
| `U+201D` right double quote | 12,468 | **1.6%** | 12,263 | 6,131 |
| `U+201C` left double quote | 18 | 0.0% | 18 | 9 |

Two consequences the Planner must design for, not discover:

1. A certification that scans only `U+0022` **silently drops ~12,500
   `U+201D` characters (~6,100 spans, 6.6% of the population)** — a
   6.6% blind spot in a sprint whose entire purpose is having no blind
   spot.
2. The word-internal predicate is **not uniform across codepoints**:
   `U+05F4` is 98.7% word-internal (it is essentially only an
   abbreviation marker), `U+201D` is 1.6% (essentially only a
   delimiter). A single blended predicate hides both facts. Cluster 1
   must be evaluated per codepoint, and pairing must handle
   **mixed-codepoint pairs** (`“term”` opens `U+201C` and closes
   `U+201D`; `"term"` uses `U+0022` twice).

## Cluster 1, stated up front as the falsifiable-mechanical template

The IL-specific hazard: Hebrew gershayim is *also* a word-internal
abbreviation marker (`תשע"א`, `עו"ד`, `הג"א`). A naive `"([^"]+)"`
pairing scan pairs one abbreviation's quote with the next one's and
manufactures tens of thousands of phantom spans. **33.1% of all quote
characters are word-internal.**

So cluster 1's predicate is mechanical and falsifiable:

> *A quote character immediately preceded AND followed by a Hebrew letter
> (U+05D0–U+05EA), with no intervening whitespace, is word-internal and
> cannot be a term delimiter.*

That is a committed function, not a sentence. It disposes of ~91,605
characters before any human judgment is applied. **Every other cluster
must take this same form**: an executable predicate that a reviewer can
run and try to break. A cluster whose membership rule is a paragraph of
prose is not a cluster; it is a narrative, and it fails C2.

## Acceptance gates

- **C1 — The denominator is signal-agnostic and reproducible.** A
  committed script derives the candidate population from the corpus with
  **no reference to any trigger phrase, heading, or capture rule**, and
  reproduces the counts above. It covers **all four quote codepoints**.
  The 0.07% delta between the two independent derivations is either
  explained or eliminated — an unexplained delta in the denominator is a
  C1 FAIL, because every downstream percentage rests on it.
- **C2 — Exhaustive and disjoint assignment, asserted mechanically.**
  Every candidate row carries **exactly one** `cluster_id`. A committed
  test runs every cluster predicate over the **full ~92,600-row
  population** and asserts **zero unassigned and zero double-assigned**.
  This is the backbone of the sprint. Without it, "every candidate is
  classified" is a claim about a spreadsheet rather than about the
  corpus. Sampling does not substitute for it: C2 is over the whole
  population, always.
- **C3 — Every disposition carries a MEASURED error rate.** Each cluster
  is assigned exactly one bucket — `captured` / `fixed` /
  `proven-not-a-definition` / `director-named residual` — and each
  assignment is backed by a **seeded random hand-verified sample** with a
  reported error rate and sample size. A clean bill with no measured
  error rate is a C3 FAIL. The seed is committed so QA draws the same
  sample. Report the error rate even when it is zero — *especially* when
  it is zero, with the sample size that makes that meaningful.
- **C4 — The fix loop is closed inside this sprint.** Classification WILL
  surface new buildable classes; it has in all three prior cycles, and
  the phase-3 manager found two more (the `זאת` demonstrative, and IL's
  `לרבות`/`למעט` includes-family gap) while merely *verifying* the
  handover. Each such class runs REDs → build → **re-certify the affected
  clusters**, re-running C2's exhaustiveness assertion over the full
  population each time. A sprint that ends with "we found these and filed
  them for later" has produced a survey, not a certification.
- **C5 — The artifact re-runs clean for an independent QA.** The
  deliverable is a committed script + manifest (predicates, counts,
  bucket assignments, sample verdicts, seeds) that **QA re-runs from a
  clean checkout and diffs**. A non-empty diff QA cannot explain is a C5
  FAIL. A certification nobody can re-execute certifies nothing.

## What this sprint is NOT

- Not another variant hunt. If it finds itself grepping for a new trigger
  phrase as its primary method, it has reverted to the forward mode this
  sprint exists to replace.
- Not a rewrite of capture. Fixes are in scope **only** via C4's loop,
  scoped to what classification surfaces.
- Not a place to relitigate `2026-08-04-defs-il`'s enumerated residual.
  The סימן/חלק containment REDs are **core-blocked** (M20 — no live
  breadcrumb data source; `pipeline.py:212` hardcodes
  `heading_breadcrumbs=()` and `sections.py:138` gates on 2-equals, both
  frozen). They enter the certification as a **named residual cluster**
  with that citation, not as work.

## Coordination

- Opens **after** `2026-08-04-defs-il` closes (its cycle-4 QA must land
  first — this sprint's denominator must be measured against the capture
  behaviour the panel actually shipped, not a moving target).
- The US certification is D-CERT's other track. **Two precedents set here
  bind it too:** (1) the denominator includes definitions-headed articles
  — no signal-dependence; (2) classification predicates are committed
  executable functions, not prose. The four-codepoint finding above is
  the IL-specific instance of a general lesson: **measure the character
  class, don't assume it** — the US track should check its own quote and
  dash inventory rather than assuming ASCII.
- Frozen files stay frozen. Any fix in C4's loop that appears to need a
  frozen-file edit **escalates** to the program manager rather than
  proceeding.

## Standing constraints

All program standing constraints apply: CodeGraph first; red-before-green
live-path tests; **Planner owns tests, QA independent** (test/contract-only
commits); **M18 — denominators from the entry LINE, never the entry
grammar**; no test reads the corpus (byte-verified vendored fixtures
only); the corpus at `/Users/nerya/AI for others/israeli-laws-wiki` is
**READ-ONLY**; absolute zero-miss bar; P-R2 escalation on precision
conflicts; M14 (own worktree + own venv per role agent, explicit `git add`
paths, never `git stash`); files under 300 lines.

## Sizing and the valve

Honest sizing from the phase-2 manager, which the phase-3 manager
concurs with: comparable in effort to Phase A–C of the parent sprint
combined — an estimated 20–40 clusters and ~600–1,200 hand
verifications, plus C4's inner loop. This sprint gets its **own 5-cycle
valve**; that is precisely why it was split out rather than run on the
parent's last cycle. Program manager has confirmed it sits inside
D-CERT's authorized "roughly one additional sprint per track" envelope.

## Next Steps

_Planner defines items — after program-manager sign-off of this contract._

## Dev Complete

_None._

## Completed

_None._

## Context Dump

New sprint, drafted by the phase-3 panel manager of
`2026-08-04-defs-il`. Planner starts by reading the program doc, this
contract, and the parent sprint's log entries M18–M22. The denominator
and the four-codepoint table above are measured facts to build on, but
re-derive them yourself before authoring anything — that is the habit
this whole sprint is about.
