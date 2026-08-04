---
id: "2026-08-04-definition-completeness"
status: planning
created: "2026-08-04"
director_mandate: "2026-08-04 (this file, §Mandate)"
sprints: []   # filled after recon: core-scope + il + us families
---

# Program: Definition completeness — country-specific rules

## Mandate (director, 2026-08-04, verbatim intent)

> "Do the specific rules for each country. Launch swarms of agents to make a
> separate sprint for each country, all at once. Spawn a manager for each
> sprint, and every sprint will serve as a workflow and a panel where the
> manager, planner, developer, and QA speak with one another to refine the
> results. You bring me the questions they ask. We need to make sure every
> definition is captured, and if a definition appears in another article (not
> in the usual place for definitions), it should be captured as well, even if
> it is relevant only to specific articles or subsections. Do that also for
> Israeli laws, and make sure that specific-article/subsection-related-
> definitions make assertions only to mentions within the section they are
> specified for."

Plus (mid-session addition): **all agents must use the CodeGraph graphs in
order to save tokens** — the `.codegraph/` index exists (built 2026-08-04,
196 files / 2,386 nodes / 5,435 edges); every brief carries the mandate.

## Director decisions (2026-08-04, AskUserQuestion — binding)

1. **Sprint split: Israel + US style families.** One Israeli sprint plus one
   US sprint per drafting-style family (grouping fixed by recon), all
   concurrent, each with its own manager/planner/developer/QA panel.
2. **Prior sprint 2026-08-02-us-state-law closed as done** (merged, PR #18).
3. **Recall bar: ABSOLUTE ZERO-MISS.** Chosen over the manager's
   recommendation (measured completeness) — recorded honestly: any missed
   definition QA finds fails the gate. Combined with the harness's 5-cycle QA
   safety valve, a non-converging panel ends `blocked` for a director
   decision instead of shipping with known limitations.
4. **IL corpus: the full israeli-laws-wiki corpus** (from the POC folder),
   ingested and measured like the US 2,045,897-row run — same "prove it
   works" standard.

## Program-level manager rulings

- **P-R1 — Phase 0 before family fan-out (write-set isolation).** All family
  sprints extend the same six shared modules today; unsequenced parallel
  edits would collide. A single **core sprint** first (a) moves the US
  inline-fallback/body-heading extraction out of `pipeline.py` behind the
  profile seam (closing the 2026-08-02 sprint's recorded architecture
  deviation), (b) adds a per-jurisdiction/per-state **rule registry** so
  family sprints ship rules as NEW modules, (c) implements **scope-restricted
  assertion linking** (the director's scoped-definitions requirement) as core
  behavior for every profile. All panels LAUNCH at once (planning is
  parallel); only developer merges sequence behind the core seam.
- **P-R2 — Zero-miss vs zero-false-positive conflict is a director question.**
  The prior sprint deliberately left Georgia undetected to protect zero false
  positives. Absolute zero-miss reverses that pressure. Panels must NOT
  silently pick a side: each conflict class escalates with real examples, and
  the manager relays it to the director (standing question Q-1 below).
- **P-R3 — Panel structure.** Per director order, each sprint gets a spawned
  sub-manager running its panel as a workflow (planner ⇄ developer ⇄ QA
  cross-talk). Deviation from the harness's single-manager rule is
  director-ordered and recorded. Escalations flow sub-manager → program
  manager → director; the program manager relays panel questions verbatim.
- **P-R4 — Pointer semantics.** `current-sprint.json` cannot point at N
  concurrent sprints; while the program runs it points at the core sprint,
  and this file is the authoritative roster. Deviation recorded.
- **P-R5 — Branch/merge flow.** Repo convention (prior sprint R1): work on
  `claude/*`-style branches → PR → main. Each sprint gets its own branch;
  the program manager owns merges and sequencing.
- **P-R6 — Models per role** (cheapest-fit, auditable in every spawn):
  sub-manager Opus/high (arbitration + verification duties); Planner Sonnet
  high (always); Developer Sonnet medium (Haiku only for bounded mechanical
  changes per harness policy); QA Sonnet high; recon/scout Haiku–Sonnet per
  task. `model=inherit` forbidden.

## Standing constraints (every panel)

- **Scoped definitions:** a definition declared for a specific article/
  subsection/chapter must create USES_DEFINITION assertions ONLY for mentions
  within that scope — proven live-path in BOTH directions (in-scope mention
  links; out-of-scope mention does NOT). Applies to IL and US alike.
- **Non-standard placement:** definitions appearing outside the canonical
  definitions section (body preambles, inline parentheticals, ad-hoc/להלן,
  substantive articles) must be captured, with correct scope.
- **Hebrew is a regression surface** (prior R2): existing IL tests pass
  unchanged; editing one to fit is a planning bug — escalate.
- **Full-corpus measured runs** (prior R3 standard): US 105 parquet files and
  the full israeli-laws-wiki corpus; report rows, misses, wall time, memory —
  never extrapolate from samples.
- **No test downloads the corpus** (prior R6): suites run offline on small
  vendored real-row fixtures.
- **CodeGraph first** for all code understanding/location (director mandate).
- **Red before green; live-path tests; Planner owns tests; QA independent** —
  full harness rules apply inside each panel.

## Sprint roster

Recon dossier: `2026-08-04-definition-completeness-recon.md` (in this dir),
§6 addendum covers OR→FED. All 53 US jurisdictions now assessed; none is
miss-free. Three NEW families found in the addendum: verb-form headings
(`"X" defined` — VA/WA/WV/WI/WY/DC/FED, 0% captured), unquoted-term
definitions (DC), and **Puerto Rico is Spanish-language** (~529 Definiciones
sections, 100% invisible to the English-only USProfile) — PR gets its own
sprint. Highest-impact single fix: the no-marker inline-quote shape — FED
84% / VA 97% / WA 98% of detected Definitions sections extract ZERO today
(markers sprint).

| Sprint | Branch | Scope | Merge order |
|---|---|---|---|
| `2026-08-04-defs-core-scope` | `claude/defs-core-scope` | Scope-restricted linking at article/subsection/chapter granularity; profile-dispatched scope triggers; extraction moved behind the seam; per-jurisdiction rule registry | **1 — critical path; everyone builds behind its published seam spec** |
| `2026-08-04-defs-il` | `claude/defs-il` | Full israeli-laws-wiki corpus (6,133 laws); 4 confirmed missed IL classes; scoped-assertion proof on real corpus | 2+ (after core) |
| `2026-08-04-defs-us-scoped-inline` | `claude/defs-us-scoped-inline` | Family 1: "As used in / For purposes of this section…" scoped-inline defs, 0% captured everywhere — the English `extract_local_definitions` analog + scope stamping. Lead states: UT(34.6%), OH(47%), MO, ME, TN, VT, OR, RI, SC + all 36 first-round states | 2+ (after core) |
| `2026-08-04-defs-us-preamble` | `claude/defs-us-preamble` | Family 2: body preamble without the literal word "Definitions" (GA/MD/NE/MS zero-signal states + SD-dominant + low-volume everywhere) | 2+ (after core) |
| `2026-08-04-defs-us-markers` | `claude/defs-us-markers` | Family 3 (highest corpus impact): entry-marker mismatch — bare digit-dot, unquoted caps, mojibake (AL/AZ/AK/IL/AR/RI), bare-(N) (SC), nested lettered sub-clauses (UT), colon-then-list (TN), AND the no-marker inline-quote sub-case dominating VA(97%)/WA(98%)/FED(84%)/WV/DC + DC's unquoted-term shape. The existing-but-unwired inline fallback rescues most (dossier §6 finding #1) | 2+ (after core) |
| `2026-08-04-defs-us-headings` | `claude/defs-us-headings` | Family 4: compound/mid-token Definitions headings (MO/NV/NH/NY/MI/TN/SC/SD/PA/UT/TX) + NEW verb-form family `"X" defined` (VA/WA/WV/WI/WY/DC/FED, ~800 headings, 0% captured) | 2+ (after core) |
| `2026-08-04-defs-us-multiterm` | `claude/defs-us-multiterm` | Families 5+6: multi-term shared-clause (MT/MI/ND/NY/OK/NH/VT/SD) + inline parentheticals ("Term") appositions (MI/MT/NH/ND/NY/OK/OR) | 2+ (after core) |
| `2026-08-04-defs-us-pr` | `claude/defs-us-pr` | NEW: Puerto Rico Spanish-language rules — Definiciones headings, significa / A los fines de / se entenderá por idioms, Spanish scope phrases; ~529 sections 100% missed today | 2+ (after core) |
| _program close_ | — | Program-level integration QA: full-corpus US + IL runs on the merged tree; aggregate zero-miss verdict | last |

Working-baseline regression-guard states for every US sprint:
IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK.

## Director rulings during execution (AskUserQuestion — binding)

- **D-E1 (2026-08-04): narrowest scope governs.** A mention inside multiple
  definitions' scopes links ONLY to the narrowest (subsection > article/local
  > chapter/part > law-wide); the general definition still fires wherever no
  narrower one was detected. Authorizes the core panel's attribution-bug fix
  (edges must carry their authorizing definition).
- **D-Q1 (2026-08-04): recall-vs-false-positive conflicts escalate per class
  with data.** No standing winner; each conflict class comes to the director
  with real examples and measured counts. (Q-1 closed.)
- **D-PR-A (2026-08-04): PR prose definitions get a narrow heading-anchored
  rule** (headings naming the term, e.g. "Bienes; definición"); anchor-less
  residue is enumerated by act_id as a documented gap. PR sprint is NOT
  blocked.

## Program routing decisions (program manager)

- Seam spec v2 requested from core, consolidating: generic (unit_kind,
  unit_value) scopes; ScopeTriggerRule owning-article context; explicit
  M-R7(a) dispatch-gating ruling; PR profile-vs-rules ruling.
- Two NEW core items (measured zero-miss breaches in core-owned modules):
  bare-`@` article markers (124 IL laws parse to zero articles) and
  case-sensitive `find_term_uses` (GA lowercase re-mentions).
- Headings U2 = option C (ship recall win; 10 act_ids recorded; scope model
  to core v2). Boundary routings: MS clause rows → scoped-inline; NE/SD
  unquoted → markers; VT S3700 fan-out → multiterm; verb-form bodies →
  markers; CO truncated titles + repealed stubs → program data-quality list.
- Process rules (after two incidents): ONE writer per worktree, always;
  verify agent liveness before respawning (staleness watchdogs unreliable).

## Log

- 2026-08-04: program created; recon swarm launched (6 agents); prior sprint
  closed as done (`300f464`).
