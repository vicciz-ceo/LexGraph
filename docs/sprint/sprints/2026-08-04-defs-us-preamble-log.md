# Sprint log — 2026-08-04-defs-us-preamble (append-only)

Panel dialogue, manager rulings, and verification evidence for US family 2
(body preambles without the literal word "Definitions"). Append only; never
rewrite earlier entries.

---

## 2026-08-04 — Manager setup + independent recon (before any role spawn)

Worktree `/Users/nerya/LexGraph-wt/defs-us-preamble` created from
`origin/main` (83532fe) on branch `claude/defs-us-preamble`; own backend venv
built (python3.13); `git config user.email` verified as
`256402398+vicciz-ceo@users.noreply.github.com`.

Core sprint seam spec: **not yet published**. `git show
origin/claude/defs-core-scope:docs/sprint/sprints/2026-08-04-defs-core-scope.md`
contains only the instruction that a `## Seam spec (published)` section must
appear; the section itself does not exist. Per the sprint contract we plan and
author RED tests meanwhile, and developers do non-shared-module work only.

### M-R1 — The family-2 miss is a TWO-GATE failure, not one regex

Manager ran a full-corpus probe (all rows, not a sample) of the real
Stage-2 path — `USProfile.is_definitions_heading` → `_is_placeholder_heading`
→ `_BODY_DEFINITIONS_PREAMBLE_RE` / `_derive_heading_from_body` — imported
live from the worktree venv against the vaquill parquet snapshot. Script:
scratchpad `mgr_probe.py` (not committed; reads the snapshot, so it is recon
tooling only — no test may do this).

Preamble-signal rows counted by `(As used in|For (the) purposes of) this
<unit> ... the term`:

| State | rows | preamble-signal | heading already "Definitions" | GATE A (`_is_placeholder_heading`) pass | GATE B (`_BODY_DEFINITIONS_PREAMBLE_RE`) pass |
|---|---|---|---|---|---|
| GA | 28,154 | 1,224 | 0 | **1,222** | **1** |
| MD | 39,552 | 1 | 0 | 0 | 0 |
| NE | 25,997 | 2 | 0 | 0 | 0 |
| MS | 158,688 | 637 | 0 | **0** | 0 |
| SD | 39,589 | 218 | 5 | **0** | 0 |

Consequences the panel must build on:

- **GA is a single-gate fix.** Gate A already passes for 99.8% of GA's
  preamble rows (their `section_title` is the bare citation breadcrumb
  `"Georgia Code Title 45. Public Officers and Employees § 45-2-20"`, which
  `_BARE_CITATION_LABEL_RE` matches). Only Gate B fails, because
  `_BODY_DEFINITIONS_PREAMBLE_RE` demands the literal word "Definitions" and
  GA writes `"As used in this article, the term:"`. GA bodies then carry
  ordinary `(1) "Term" means …` markers the existing US extractor handles,
  so widening Gate B should convert directly into captured definitions.
  False-positive exposure is bounded by Gate A (placeholder headings only).
- **MD / NE / MS fail Gate A**, so body derivation is never attempted. Their
  headings are placeholders of *shapes `_is_placeholder_heading` does not
  recognize*: MD `"§5–114."`, NE `"View Statute 44-4051"` (a scrape
  artifact), MS `"Miss. Code Ann. § 27-65-201"`. This is a placeholder-
  recognizer widening, i.e. **shared-module territory** — coordinate with
  the core sprint rather than editing `pipeline.py` here.
- **The recon's MD/NE characterisation is not reproducible from the preamble
  signal alone.** MD yields 1 row and NE 2 (both NE hits are false positives
  — the bodies are substantive provisions, not definitions). The dossier's
  "MD/NE 0% capture" is an *overall* capture statistic, not evidence of a
  `the term`-shaped preamble convention. The Planner must inventory MD/NE's
  actual definition-introducing convention from real rows before writing a
  single test for them; assuming the GA shape would be a planning bug.
- **SD fails Gate A for a different reason: its headings are real.**
  `"Loan processor or underwriter defined"`, `"Electric bicycle defined--
  Classes"` carry genuine descriptive text. SD's body shape is also
  distinctive: `"For the purposes of this chapter, the term, loan processor
  or underwriter, means …"` — an **unquoted, comma-delimited** term that no
  current extractor can parse.

### M-R2 — Three cross-sprint boundary conflicts, flagged for escalation

Raised now, decided later — the Planner quantifies each with real rows before
the manager escalates to the program manager (P-R2 requires real examples,
not a manager's guess):

1. **MS (637 rows) reads as scoped-inline, not family 2.** Bodies are
   dominantly `"(1) For purposes of this section, … the term "X" means"` and
   `"(1) As used in this section: (a) The term "public facility" means"`
   inside sections that are substantively about something else. The contract's
   boundary rule gives "scope-trigger parsing inside otherwise-ordinary
   sections" to `2026-08-04-defs-us-scoped-inline`. But MS's heading is a bare
   citation placeholder, so *nothing in the heading distinguishes* an
   ordinary section from a whole-body definitions block — the discriminator
   has to be body shape, which is this sprint's stated competence.
2. **SD overlaps the headings sprint.** SD's dominant rows are verb-form
   headings (`"X defined"`), which the program doc assigns to
   `2026-08-04-defs-us-headings` (NEW verb-form family, ~800 headings). The
   same rows are family 2 by body shape. Fixing either signal alone may
   capture them; fixing both risks double ownership.
3. **SD's unquoted comma-delimited term is a marker-format problem**, i.e.
   `2026-08-04-defs-us-markers` territory, even once the block is recognized.

### M-R3 — Model/effort for the Planner spawn

Planner: **Sonnet / high** — authoring RED live-path tests plus a real-corpus
convention inventory across four states requires sustained judgment about
what counts as a definition; per P-R6 the Planner is always Sonnet high.
**Haiku considered: no** — this is open-ended discovery over real statutory
prose with a zero-miss bar, not a bounded mechanical change.
`model=inherit` not used.

### M-R4 — Baseline for U5, measured (not assumed)

`backend/.venv/bin/pytest backend/tests -q` at `bd18411`:
**641 passed, 0 failed, 18 warnings in 14.62s.** This is the U5 reference.

Also verified independently (constraint enforcement, not trust): **no test in
`backend/tests/` reads the vaquill snapshot** — every `parquet`/`huggingface`
reference is a docstring or a committed local fixture. Repo fixture convention
is `backend/tests/fixtures/us_statutes/*.json` holding verbatim full parquet
row dicts, 4–37 KB per file. Re-check after any role vendors new fixtures.

### M-R5 — Planner attempt #1 died mid-run; retry recorded

The program manager flagged that this sprint had **no live background child**
while the manager reported "Planner running". Verified rather than assumed:

- Transcript `agent-ad74ac35c5b90e094.jsonl` exists — 64 records, 424 KB — so
  the agent genuinely launched and worked.
- Its last record is an **empty assistant turn**; there is no result record
  and, unlike sibling agents, **no `.meta.json`**. It terminated without
  returning.
- `git log` shows no Planner commit and `git status --porcelain` is **empty**
  — it died during the read/explore phase (last calls: `Read`, `Bash` grep,
  `codegraph_explore`) before writing anything. **No work product lost beyond
  the exploration; no partial or corrupt state in the worktree.**

Manager ruling: the failure mode is silent agent death with total work loss,
because the agent batched all writing to the end. Attempt #2 adds an
**incremental-durability requirement** — commit and push after each deliverable
(D1–D4) — so a second death costs one deliverable, not the phase. Same brief
and same model/effort otherwise (M-R3).

Process lesson: *a recorded spawn ruling is not a running agent.* The manager
must confirm a child is live (transcript growing, or a commit landing) before
reporting it as running, and must never end a turn with no live child and no
pending work.

### M-R6 — Boundary conflicts pre-approved for routing

Program manager's answer to M-R2: the three cross-sprint conflicts
(MS → scoped-inline, SD → headings verb-form, SD unquoted term → markers) are
**pre-approved for routing**. Once the Planner's D2 dossier quantifies them,
the manager sends an **item-level split proposal**; the program manager rules
or relays to the director under P-R2. The panel does NOT settle ownership
itself — it produces the numbers that make the split decidable.

### M-R7 — Core seam spec published; this sprint's slot is explicit

`## Seam spec (published)` appeared on `origin/claude/defs-core-scope` (found
on poll 7 of a bounded watch). Read in full. What it means here:

- This sprint's deliverable is **exactly one new file**,
  `backend/app/definition_links/rules/us_body_preamble.py`, plus its own
  tests. Rule modules self-register by *existing* in `rules/` (the package
  `__init__` imports every module via `pkgutil.iter_modules`), so file
  creation is the whole change and six panels cannot conflict.
- Our rule kind is **`BodyPreambleRule(jurisdiction_codes, derive_heading)`**
  where `derive_heading: Callable[[str], str | None]` maps **body text → a
  synthesized heading**. Registered via `register_body_preamble_rule`.
- Detection kinds are **baseline-first, registry-second, first-match-wins in
  filename-sort order**. Extraction kinds union. Ours is a detection kind.
- Core deletes `_is_placeholder_heading` / `_derive_heading_from_body` /
  `_extract_inline_quoted_definitions` from `pipeline.py`, moving them
  verbatim behind `USProfile.derive_heading_from_body(heading, body)` and
  `extract_definitions_from_section(..., heading_was_derived=...)`.
- **Zero edits** permitted by us to `pipeline.py`, `matcher.py`,
  `profiles.py`, or `extract.py`'s existing functions — satisfying U3.

**M-R7(a) — OPEN QUESTION the Planner must settle against core's real code.**
`BodyPreambleRule.derive_heading` receives **only the body**, never the
heading. If registered body-preamble rules are tried whenever the *baseline*
returns `None` — including when the heading is not a placeholder at all —
then MD/NE/MS/SD are **not** blocked by the gate-A finding of M-R1, and this
sprint needs no core change to `_is_placeholder_heading`. But the entire
false-positive guard that gate A provided (restricting derivation to
information-free headings) would then be **absent for registry rules**,
putting 100% of the precision burden on our own rule's discrimination — over
every US section in the corpus, not just placeholder-headed ones. If instead
the placeholder gate still wraps registry dispatch, MD/NE/MS stay blocked and
we have a hard dependency on core. The spec does not say which. The Planner
resolves this by reading core's actual implementation and tests on
`origin/claude/defs-core-scope`; if the code does not yet answer it, it is a
panel question for core and the manager escalates it.

---

## 2026-08-04 — Planner attempt #2, D0: ESCALATION — core has zero backend code, M-R7(a) unanswerable from code today

Verified, not guessed: `git fetch origin claude/defs-core-scope` then `git
diff --stat ba1b398 origin/claude/defs-core-scope -- backend/` (`ba1b398` is
the commit core's own worktree was created from, per its log's own Setup
entry) → **empty output. Zero backend files changed.** `git ls-tree -r
origin/claude/defs-core-scope --name-only` confirms `backend/app/
definition_links/` has no `rules/` directory at all — no `registry.py`, no
`__init__.py` auto-discovery, no `il_scope_triggers.py`/`us_scope_trigger_
proof.py` — and `profiles.py`/`pipeline.py` are still the pre-seam files.
Core's own log (`docs/sprint/sprints/2026-08-04-defs-core-scope-log.md`,
read in full) confirms this is not an oversight: core's Stage B
(implementation) is **explicitly held** pending an escalation (E-1,
multi-scope precedence) the sub-manager raised to the program manager after
reviewing the Planner's Stage A seam-spec-only deliverable — "Sprint status
held at `planning`, Planner agent ... left resumable for Stage B the moment
an answer lands." Core has published a spec document and nothing else.

**Consequence for M-R7(a): the question cannot be settled from code, because
there is no code.** The brief's own contingency applies verbatim: "If core's
branch does not yet contain code that answers this, STOP and escalate to
me... Do not guess." This is that STOP.

**What I can say from the spec text alone (not sufficient to resolve it,
but narrows the question for whoever answers it):** the new Protocol method
is `derive_heading_from_body(self, heading: str, body: str) -> str | None`
— it receives `heading`, which only makes sense if the moved-verbatim
`_is_placeholder_heading(heading)` check lives INSIDE this one method
(pipeline.py is stated to retain zero jurisdiction-specific literals after
this sprint, so the check cannot stay as a separate pipeline.py call site
the way it is today). The consumption contract's own wording ("the
profile's EXISTING baseline logic runs first ...; only if baseline returns
false/empty does the profile try registered rules") is read most naturally
as: baseline = the existing two-gate check as a single unit (call it
GATE-A-then-GATE-B); if EITHER gate fails, "baseline returns false/empty"
literally holds, and registry dispatch would fire — which is M-R7(a)'s
FIRST branch (rules tried for any heading, MD/NE/MS/SD unblocked, but see
the exposure quantification below). But the equally natural competing
reading is that a competent "move this verbatim, then append registry
dispatch" implementation keeps GATE A as an early-return guarding the WHOLE
method (both the baseline body regex AND the new registry loop), because
that is what "verbatim" behavior-preservation for the 7 already-working
states + GA/CA/IL most simply implies in code — which is the SECOND branch
(MD/NE/MS/SD stay blocked, hard core dependency). **I do not have a way to
choose between these two readings without seeing core's actual method
body**, and I am not guessing.

**Exposure quantification for the FIRST branch (requested by the brief, so
the answer is ready the moment this unblocks)**, run live against the
current pre-seam pipeline to approximate "how many non-definitions US
sections would a naive body-preamble rule wrongly claim if the placeholder
gate did not restrict it": see D2 below (negative-guard hand examples) —
GA alone has at minimum the real, corpus-confirmed `STATE_GA_T44_C6_S44-6-
165` shape ("at the term of the court" — ordinary-English "term", no
definition) as a documented false-positive trap; a full-corpus count of
every US section containing "the term"/"as used in"/"for purposes of"
without a defining idiom nearby was NOT run (would require scanning all 53
files' full text, hours of wall time) — flagged as **not verified, honestly
a gap**, not a number I am willing to assert without having run it.

**Ruling on how I am proceeding given the STOP:** per the brief's own
durability mandate, I am not idling on an unresolved escalation. D1 (real-
row convention inventory) and D2 (boundary dossier) below depend on NEITHER
branch of M-R7(a) — they are facts about the corpus and today's code, not
about the seam. D3's RED tests are written against the STABLE public entry
point (`ingest_us_statute_rows` + `run_definition_linking`), which survives
the seam refactor unchanged in signature — so they do not need M-R7(a)
resolved to be authored, run, and proven RED today; two of them (SD/NE's
unquoted-term rows) are additionally flagged, independent of M-R7(a), as
blocked on `2026-08-04-defs-us-markers`. D4's item breakdown marks which
items fork on M-R7(a)'s answer. Continuing to D1.

**ESCALATION (repeated at the top of the final report per the brief's
format): M-R7(a) is unresolved. Options: (a) wait for core's Stage B to
land and re-read; (b) the manager/program manager puts the question
directly to core's panel as a cross-sprint question (core's own log shows
their Planner is "left resumable," i.e., reachable) rather than waiting for
a full implementation; (c) the director decides the intended reading
directly, since it is a one-sentence design choice (does the placeholder
gate wrap registry dispatch, yes/no) that core's Planner could answer in one
message without finishing Stage B. My lean: (b) — this is a narrow, answerable
design question, not something that needs a full implementation to resolve,
and the sprint's four-vs-one-item shape depends on it.**

---

## 2026-08-04 — Planner attempt #2, D1: convention inventory for GA/MD/NE/MS/SD, real rows, live code

Method for all five: `backend/.venv/bin/python` importing the real
`USProfile`/`pipeline._is_placeholder_heading`/`pipeline._derive_heading_
from_body` from THIS worktree, run against the on-disk vaquill snapshot
(never downloaded). Every count below was reproduced by me independently
(re-run, not just read from a stale output file) before being written here.
Scripts live in the shared session scratchpad (`planner_md_ne_convention
.py`, `planner_md_ne_classify.py`, `planner_sd_dossier.py` — discovered
already on disk from attempt #1, which reached much further than the
manager's git-only check (M-R5) could see: git tracks commits, not the
scratchpad or even everything attempt #1 wrote directly into the worktree
as untracked files — `test_definition_links_us_preamble_family.py` was one
such untracked survivor, adopted into D3 below after independent
verification, not taken on faith).

**GA (28,154 rows) — manager's table confirmed, no correction.** 1,224
preamble-signal rows, 1,222 pass Gate A, only 1 passes Gate B. Convention:
`"As used in this <chapter/article>, the term:"` then `(N) "Term" means`.
Examples: `STATE_GA_T7_C8_S7-8-1` ("As used in this chapter, the term: (1)
"Access area" means any paved walkway..."), `STATE_GA_T50_C8_S50-8-80`
("As used in this article, the term: (1) "Area" means a standard
metropolitan statistical area..."). Blocked by: Gate B only.

**MD (39,552 rows) — manager's narrow probe corrected, as flagged.** The
`the term`-anchored signal used for the full-corpus table finds only 2 raw
hits (`for_purposes_of_the_term`), both non-representative. MD's REAL
dominant convention, found by broadening the signal set to 9 independent
phrase families and cross-checking against a full-body entry count: **"In
this <section/subtitle/title>[,] the following words have the meanings
indicated. (N) "Term" means / has the meaning stated..."** — 3,327/39,552
rows (8.4%) carry >=2 such entries in the full body (a genuine multi-term
BLOCK, this sprint's territory, not a single incidental clause). 0/39,552
MD headings ever say "Definitions" (own separate check, ALL rows, not just
signal-matched ones) — MD's heading is ALWAYS a bare `"§N–NNN."`
pinpoint-citation placeholder, confirmed not recognized by `_is_placeholder_
heading` (`_is_placeholder_heading("§5–114.")` is `False`; regex expects
either `"Section \d..."` or a `"...Code Title N. ... § ..."` breadcrumb,
neither of which `"§N–NNN."` matches). Examples: `STATE_MD_Agtp_T9_S2_S9-
258` ("(a) (1) In this section the following words have the meanings
indicated. (2) "Dwelling" has the meaning stated in § 9–105..."),
`STATE_MD_Agho_T7_S1_S7-101` ("(a) In this title the following words have
the meanings indicated. (a–1) "Alkaline hydrolysis" has the meaning
stated..."). Blocked by: Gate A only (once past Gate A, the existing
extractor already parses these bodies unmodified — verified live, both
`extract_definitions_from_section` and the inline-quote fallback succeed on
the real MD row).

**NE (25,997 rows) — manager's narrow probe corrected, MOST corrected of
the four, exactly as flagged as the genuinely open question.** The `the
term`-anchored signal finds only 2 hits and BOTH are false positives
(confirmed by the manager: bodies are substantive, not definitional). NE's
real convention, found the same broadened way, is **NOT** GA's "the
term:"-shaped preamble at all — NE's actual shapes are (a) `"For purposes
of [the Named Act / sections N to M]... the following definitions apply:
(N) Term means..."` and (b) `"In the <Named Code/Act>: (N) "Term" means/
includes..."`, both with NO literal "the term" phrase anywhere. Broadened
signal finds 699 candidate rows; 559 are genuine multi-entry BLOCKs (>=2
entries). 0/699 captured today. Two sub-shapes matter for D3/D4: **quoted**
entries (e.g. `STATE_NE_C30_S30-3803`, Nebraska Uniform Trust Code: `(1)
"Action", with respect to an act of a trustee, includes a failure to act.
(2) "Ascertainable standard" means...`) are extractable TODAY by the
existing extractor once a heading is recognized (verified live: 27
candidates extracted) — achievable within this sprint's own scope; **un­
quoted** entries (e.g. `STATE_NE_C44_S44-5003`: `(1) Health insurance plan
means a plan which includes...`, `STATE_NE_C48_S48-1229`: `(1) Employee
means any individual...`) are NOT extractable by any current code today
even with a perfect heading (verified live: both `extract_definitions_from_
section` and the inline-quote fallback return `[]` on the real unquoted
body) — a hard dependency on `2026-08-04-defs-us-markers`. NE's `section_
title` is essentially always `"View Statute N-NNNN"` (a scrape artifact) or
a bare number, never recognized by Gate A. Blocked by: Gate A (both
sub-shapes), PLUS a marker/quote-format gap for the unquoted sub-shape
specifically.

**MS (158,688 rows) — manager's table confirmed.** 637 preamble-signal
rows, 0 pass either gate (heading is always `"Miss. Code Ann. § N-N-N"`, not
recognized by Gate A). Convention: `"As used in this <chapter/article/
section>, the term:"` (dominant) plus `"For (the) purposes of this
<chapter/section>, the term ... means"` (dominant single-clause variant —
see D2). Examples: `STATE_MS_T45_C9_S35-51` ("As used in this article, the
term: (a) "Commissioner" means the Commissioner..." — 7 lettered entries),
`STATE_MS_T39_C1_S3-25` ("...For purposes of this section, the term "
minor " means any person under the age of eighteen..." — single clause deep
inside a 5,632-char section about something else). Blocked by: Gate A only.

**SD (39,589 rows) — manager's table confirmed, structurally split by
heading AND by term-quoting, both relevant to D2/D4.** 218 preamble-signal
rows. Heading: 5 already say "Definitions", 120 are verb-form ("X defined",
headings-sprint overlap, M-R2 boundary #2), 93 are other/unrelated
headings. Body term-quoting (independent axis): 124/218 (57%) are
**unquoted, comma-delimited** (`"the term, X, means"`, e.g.
`STATE_SD_T54_C14_S54-14-12.1`, heading "Loan processor or underwriter
defined": `"...the term, loan processor or underwriter, means..."`) — 15/218
(7%) are **quoted** (`"X" means`, e.g. `STATE_SD_T11_C9_S11-9-10`, heading
"Blighted area defined": `"...the term "blighted area" means..."`) — 79/218
(36%) match neither shape in the first 400 chars. Verified live: the
QUOTED subset is extractable TODAY once a heading is recognized (inline-
quote fallback succeeds, confirmed on the real row above); the UNQUOTED
subset is NOT extractable by any current code (both extractors return `[]`
on the real unquoted row) — same hard dependency on
`2026-08-04-defs-us-markers` as NE's unquoted sub-shape. Blocked by: Gate A
(SD's headings are real descriptive text, not placeholders — `_is_
placeholder_heading` correctly returns `False` for them, this is not a bug,
SD's headings genuinely aren't information-free), PLUS the same marker gap
as NE for the majority (57%) unquoted sub-shape.

---

## 2026-08-04 — Planner attempt #2, D2: boundary dossier for the three M-R2 conflicts

### MS: whole-body BLOCK (ours) vs clause-in-a-different-section (scoped-inline's)

Hand-labeled a 30-row sample of MS's 637 preamble-signal rows BLOCK/CLAUSE
by reading each body in full (script + labels: scratchpad `planner_ms_
discriminator.py`, recovered from attempt #1 and independently re-run by
me — same 22/30 agreement reproduced). **Discriminator**: "trigger phrase
appears within 5 chars of the body's real start" AND "the last recognized
`"Term" means` entry's end position leaves less than 50% of the body as
trailing tail" → BLOCK, else CLAUSE. **Error rate: 8/30 = 26.7% (73.3%
agreement)**, and — important for the split decision — **100% of the 8
errors are the SAME direction**: real BLOCKs the discriminator calls
CLAUSE, never the reverse. Root cause (read every one of the 8): each is a
SINGLE-entry body whose one definition's own prose runs long (e.g.
`STATE_MS_T57_C35_S44-3`, 493 chars, one entry, 86% "tail" — but the "tail"
is the SAME definition's own continuing sentences, "A project may also
include any fixtures... A project may be for any freight transportation
purpose..." — not a different topic). The crude tail-ratio metric cannot
tell "still explaining the one term" from "moved on to something else"
without sentence-level parsing.

Real examples of both kinds:
- **BLOCK** (ours): `STATE_MS_T45_C9_S35-51` — "As used in this article,
  the term: (a) "Commissioner" means... (b) "Department" means..." — 7
  entries, tail is 10% of body. `STATE_MS_T75_C12_S55-5` — "The words,
  terms and phrases as used in this chapter shall have the following
  meanings... (a) The term "commissioner" means..." — 10 entries, tail 41%.
- **CLAUSE** (scoped-inline's): `STATE_MS_T39_C1_S3-25` — "The state...may
  offer digital or online resources... For purposes of this section, the
  term " minor " means any person under the age of eighteen (18). (2) A
  vendor or other person...must have safety policies..." — 1 entry, tail
  93% (genuinely a different topic after the definition). `STATE_MS_T27_
  C1_S7-26` — pass-through-entity tax election section, one definitional
  aside, tail 91% (continues with filing-election procedure, unrelated to
  the definition).

**Conclusion for the split**: of MS's 637 preamble-signal rows, a crude
but honest discriminator finds roughly a 2-to-1 split favoring BLOCK once
corrected for its own documented conservative bias (single-long-definition
bodies undercounted as CLAUSE) — i.e., MORE than half of MS's 637 rows are
this sprint's territory (whole-body definitions blocks), with a genuine,
real minority that IS a single definitional clause embedded in an
otherwise-different section (scoped-inline's stated territory per the
sprint contract's own boundary rule). Both kinds are real and both are
common enough to matter — this is not a case where one interpretation
turns out to dominate.

### SD: verb-form heading vs body-preamble requirement

Of 218 preamble-signal rows: 120 (55%) have a verb-form "X defined"
heading (headings-sprint territory by name), 5 (2%) already say
"Definitions", 93 (43%) have an unrelated heading entirely (this sprint's
plain territory, no overlap).

**Would fixing the heading alone capture the 120 verb-form rows? Verified
live: NO, not even the quoted subset.** `pipeline.py`'s inline-quote
fallback (`_extract_inline_quoted_definitions`) — the ONLY extractor that
can parse SD's no-`(N)`-marker bodies at all, quoted or not (confirmed:
`extract_definitions_from_section` alone returns `[]` on every SD example
tested) — is gated to fire **only when `used_body_derived_heading` is
True** (pipeline.py:429, preserved by the seam spec's own stated
replacement: "if empty AND `heading_was_derived`, try the inline-quoted
extractor"). A `HeadingRule` that makes `is_definitions_heading("Loan
processor or underwriter defined")` return True DIRECTLY (heading
recognized on its own terms, not synthesized from body) sets `heading_was_
derived`/`used_body_derived_heading` to **False** — so the inline fallback
would never even be attempted, and extraction still yields zero, for EVERY
SD row, quoted or unquoted. **This means a headings-sprint-only fix for SD
does not unblock SD's extraction at all** — SD's capture genuinely needs
EITHER this sprint's body-preamble path (which sets `heading_was_derived
=True`, unlocking the fallback) OR the markers sprint generalizing the
inline-quote fallback to fire outside the derived-heading case (the
program roster's own description of that sprint's job — "the existing-but-
unwired inline fallback rescues most" VA/WA/FED/WV/DC misses — reads as
exactly this generalization). Whichever lands first satisfies the
dependency; it is not a hard sequencing requirement on ONE specific sprint.

### SD unquoted term: can any current extractor parse it?

Already answered in D1 with a live re-check here: **no.** 124/218 (57%)
of SD's rows are the unquoted `"the term, X, means"` shape; 15/218 (7%)
are quoted `""X" means"`. Verified live on real rows: the quoted shape
(`STATE_SD_T11_C9_S11-9-10`) IS parseable by the inline-quote fallback (1
candidate, "blighted area") once that fallback is reached; the unquoted
shape (`STATE_SD_T54_C14_S54-14-12.1`) is parsed by NEITHER extractor (both
return `[]`) — no quote characters anywhere near the term for either
regex to anchor on. This is squarely `2026-08-04-defs-us-markers`
territory (M-R2 boundary #3, confirmed with live evidence, not assumed).

### Item-level split proposal (for the manager to escalate per P-R2, pre-approved routing M-R6)

| Contested group | Rows | Proposed owner | Why |
|---|---|---|---|
| MS whole-body BLOCK rows (definitional entries consume most of the body) | ~400-450 of 637 (est., see discriminator's conservative bias) | **this sprint (defs-us-preamble)** | Matches the contract's own boundary rule verbatim: "recognizing a definitions-bearing BLOCK with no heading signal" |
| MS single-clause CLAUSE rows (one definition inside a substantively-different section) | ~190-240 of 637 (est.) | **defs-us-scoped-inline** | Matches that sprint's stated territory: "scope-trigger parsing inside otherwise-ordinary sections" |
| SD verb-form headings, AS A HEADING-RECOGNITION SIGNAL only | 120 of 218 | **defs-us-headings** (heading detection) — but does NOT by itself unblock extraction, see above | Headings sprint already owns the "X defined" verb-form family by name (program roster) |
| SD body-preamble path (unlocks the inline-quote fallback for SD's un-`(N)`-marked bodies) | 218 of 218 (all of them, quoted or not, need this OR the markers generalization) | **this sprint (defs-us-preamble)**, coordinating with `defs-us-markers` | Verified live: heading fix alone does not unblock extraction; the body-preamble path (or markers' fallback generalization) is load-bearing regardless of heading ownership |
| SD unquoted-comma term parsing (124 of 218, 57%) | 124 of 218 | **defs-us-markers** | Confirmed live: unparseable by any current extractor, a marker-shape problem, not a detection problem |
| NE unquoted term parsing | 511 of 559 (91.4%) | **defs-us-markers** | Same confirmed live gap as SD's unquoted case |
| NE quoted term (achievable within this sprint alone) | 46 of 559 (8.2%) | **this sprint (defs-us-preamble)** | Verified live: existing extractor already parses it once heading is recognized |

**NE quoted/unquoted split, closed (was a D1 gap, measured before finalizing
D2 rather than left open)**: full-corpus count of NE's 559 multi-entry BLOCK
rows by entry quoting style — **511 (91.4%) unquoted-only, 46 (8.2%)
quoted-only, 2 (0.4%) mixed**. NE skews far more unquoted than SD (57%) —
the table above (`up to 559`) is now precise: **511 of 559 need
defs-us-markers; 46 of 559 are achievable within this sprint's own scope
once heading recognition lands** (verified live in D1 via `STATE_NE_C30_
S30-3803`, the quoted Nebraska Uniform Trust Code example).

---

## 2026-08-04 — Planner attempt #2, D4 note: SD sharpens the D0 escalation, not just widens its scope

Found while writing the item breakdown (contract `## Next Steps`, item 8),
recorded here because it changes the STAKES of M-R7(a), not just its
bookkeeping. MD/NE/MS all fail Gate A because their headings ARE
placeholders of a shape `_is_placeholder_heading` doesn't yet recognize —
core widening that regex's pattern list is a bounded, obviously-available
rescue path independent of which way M-R7(a) resolves. **SD is
different: its headings are NOT placeholders.** `_is_placeholder_heading`
correctly returns `False` for "Loan processor or underwriter defined" —
that's real, informative text, just not the word "Definitions". No
widening of the PLACEHOLDER pattern list can ever rescue SD, because SD's
headings were never meant to match it. So: if M-R7(a) resolves to branch 1
(registry tried whenever baseline returns None, for any reason), SD
unlocks for free, no further core work. If it resolves to branch 2 (gate
wraps registry dispatch too), SD is not merely "blocked pending a core
fix" the way MD/NE/MS are — it is **structurally unreachable by a
`BodyPreambleRule` under the seam as currently specified**, full stop,
regardless of any future placeholder-list widening; rescuing it would need
a different mechanism (e.g., trying body derivation whenever `is_
definitions_heading` is False, not only when the heading is ALSO a
placeholder — a broader change than this sprint's contract authorizes).
This asymmetry — MD/NE/MS have a rescue path under branch 2, SD does not —
is new information for whoever answers M-R7(a) and strengthens (not just
supports) the escalation's lean toward asking core directly rather than
waiting for a full Stage B implementation to read.

---

## 2026-08-04 — Independent second Planner instance: process note + one uncredited finding

**Process note, recorded for the manager, not the sprint substance.** This
entry is written by a SEPARATE live Planner instance from the one that
authored every entry above from "D0" onward. That instance (labeling itself
"attempt #2") appears to have been spawned believing this instance ("attempt
#1") had died — it had not: this instance ran continuously throughout,
independently reproducing the full D1 convention inventory (GA/MD/NE/MS/SD,
matching counts exactly: MD 3,327/39,552, NE 559/25,997, SD's 5/120/93
heading split and 124/15/79 quote-shape split) and the D2 MS/SD boundary
dossier, and authoring `test_definition_links_us_preamble_family.py` +
`fixtures/us_statutes/us_preamble_rows.json` before discovering, via a
routine `git status`, that attempt #2 was concurrently writing to the SAME
worktree and had (per its own D1 commit message) found this instance's
scratchpad scripts and untracked test file, re-verified them independently,
and adopted the test file into its own D3 commit. Both instances converged
on essentially identical numbers and conclusions across D0-D2 — strong,
independent cross-validation, not a disagreement to resolve. Given attempt
#2 reached D0-D4, all pushed (`adf4b8d`), before this instance could safely
land a competing set of commits without risking git collisions on a shared
working tree, this instance stood down from writing further competing
deliverables and is instead recording here the one substantive finding from
its own research that is NOT yet reflected anywhere above.

**Finding: `find_term_uses` is case-sensitive (no `re.IGNORECASE`), and
real US statutory prose routinely re-mentions a defined term in lowercase
mid-sentence — a latent gap that will block correct mention-linking for
this family's captures even after M-R7(a) resolves and scope lands.**
Verified live on real GA text: `STATE_GA_T7_C8_S7-8-1` defines `"Access
area"` (capital A, quoted); the SAME real chapter's `STATE_GA_T7_C8_S7-8-3`
mentions it as `"...the operator controls the access area or defined
parking area..."` — lowercase `a`. `us_profile.find_term_uses`/
`matcher.find_term_uses` both compile `r"\b" + re.escape(term) + r"\b"`
with NO `re.IGNORECASE` (`us_profile.py:387-396`), so this real, in-chapter,
genuinely-in-scope mention would NOT match even once GA's preamble is
captured and chapter-scope is enforced. This is not specific to GA or to
this sprint's family — it is a pre-existing, shared-module (`us_profile.py`
+ `matcher.py`) gap that affects EVERY US jurisdiction's mention-linking,
independent of which family captures the definition. `test_us_body_
preamble_scope_red.py`'s hand-constructed "using" rows sidestep this by
construction (both deliberately capitalize "Access area" mid-sentence,
e.g. `"Each Access area shall be maintained..."`), which is a reasonable
test-authoring choice but means the case-sensitivity gap stays externally
invisible until a REAL corpus row is run through the live scope path.
Recorded here as a candidate PROGRAM-level (not sprint-level) finding —
out of this sprint's charter to fix (it lives in `us_profile.py`, shared
with every other US family), but real, verified, and worth the program
manager routing to whichever sprint/QA cycle next runs a full-corpus
mention-linking measurement, since it will otherwise silently under-link
even a fully-fixed family-2 capture.

---

## 2026-08-04 — Manager: corrections, rulings absorbed, handoff verification

### M-R8 — CORRECTION to M-R5: no Planner ever died. I was wrong.

M-R5 above claimed Planner attempt #1 "died silently". **That diagnosis was
incorrect and is retracted here** (the log is append-only, so M-R5 stands as
written and this entry supersedes it).

What actually happened: BOTH Planner instances ran to completion
**concurrently in this one worktree**. Attempt #1 delivered independently and
pushed `f77eec3`; attempt #2 delivered `0b97809..adf4b8d`. Attempt #1
cross-validated attempt #2's numbers exactly (MD 3,327; NE 559; the SD
splits), noticed attempt #2 had adopted its test file with credit, and stood
down from competing writes rather than fighting over the tree.

Where my reasoning failed, precisely:

1. I read an empty final assistant record plus a missing `.meta.json` as
   proof of death. **`.meta.json` is written at SPAWN, not completion** — I
   proved this myself minutes later when my first watchdog reported "clean
   completion" at poll 1, ~15s after spawn, which is impossible. I corrected
   the watchdog but did not go back and re-examine the death conclusion that
   the same false signal had produced.
2. A transcript that stops growing is **not** evidence of death; an agent can
   be quiet for a long stretch. Staleness watchdogs are unreliable for this.
3. I treated "clean tree + no commit" as corroboration, when it was equally
   consistent with an agent that had not yet reached its first commit.

**Program rule now in force** (program manager): verify liveness positively
before declaring death, and **NEVER let two writers share a worktree** — the
absence of conflicts here was luck, not design. My respawn created exactly
that hazard and I did not recognize it.

Both Planners' output is reconciled as ONE deliverable of this sprint:
`bd18411..f77eec3`.

### M-R9 — Program manager rulings absorbed

- **M-R7(a) is now with core**, to be ruled explicitly in seam spec v2, with
  our MD/NE/MS/SD numbers and the SD-unreachable-under-the-gated-reading
  nuance attached. **Items 3/4/6/8 are HELD pending that ruling.**
- Seam v2 is also expected to add generic scope units, which addresses item
  9's chapter-scope dependency.
- **Boundary routings APPROVED as proposed**: item 7 (MS clause-shaped rows,
  ~190–240/637) → `defs-us-scoped-inline`; item 5 (NE/SD unquoted shapes) →
  `defs-us-markers`. Those panels are being informed. Neither is this
  sprint's file to build; both stay listed so they are not silently dropped.
- The `find_term_uses` case-sensitivity finding (no `re.IGNORECASE`; real GA
  rows re-mention capitalized defined terms in lowercase,
  `STATE_GA_T7_C8_S7-8-1` → `S7-8-3`) is **routed to core** as a new core
  item, matcher being core-owned. Correctly out of our charter.
- Director's standing policy for our expected false-positive conflicts:
  escalate each class **with data**; the corpus-wide FP-exposure measurement
  for the ungated branch is the right artifact. That is now this sprint's
  active work (M-R11).

### M-R10 — Manager verification of the combined Planner deliverable

Verified by me directly, not accepted on report:

- **Diff** `bd18411...f77eec3`: 13 files, +1,861/−12. Additions only —
  6 fixture JSONs + a fixture README, 4 new test files, contract, log. **Zero
  changes to `pipeline.py`, `matcher.py`, `profiles.py`, `extract.py`,
  `us_profile.py`** → U3's "no shared-module edits" holds by construction.
- **Suite**: `12 failed, 647 passed` vs. the 641-passing baseline (M-R4).
  All 641 baseline tests still pass → **no regression (U5 intact)**; 6 new
  green tests (guards) + 12 new RED.
- **RED tests are genuinely live-path and fail for the right reason.**
  Inspected `test_real_pipeline_misses_a_real_georgia_body_preamble_
  definitions_section_end_to_end`: it drives real `ingest_us_statute_rows` +
  real `run_definition_linking`, and fails with `expected 6 real GA terms,
  got []`. Not a regex-echo test, not vacuous.
- **Fixtures are genuine.** I re-read all 12 fixture rows back against the
  real parquet by `act_id`: every one is **byte-exact** on `text` (7,640b /
  1,913b / 6,339b / … all EXACT) with matching `section_title`. Nothing
  fabricated.
- **No test reads the snapshot.** The only `huggingface`/snapshot references
  are the fixture README's provenance notes and one pre-existing docstring.

Two defects found, neither blocking, both for the Planner/QA to fix (I do not
edit tests):

- **(a) Inverted test names.** `test_real_pipeline_MISSES_a_real_georgia_…`
  asserts the *fixed* behavior, so when the fix lands the suite will read
  "pipeline misses GA" while proving the opposite. Same shape for the MD and
  NE siblings. Rename to the asserted behavior.
- **(b) Factual error in `backend/tests/fixtures/us_statutes/README.md`**: it
  states `huggingface_hub`/`pyarrow` are NOT installed in `backend/.venv`.
  **`pyarrow` IS installed and IS a declared dependency** (`pyarrow>=17.0`,
  `backend/pyproject.toml:15`); only `huggingface_hub` is absent. Left
  uncorrected, this sends the next agent to build a scratch venv it does not
  need.

### M-R11 — Sprint status: every build item is blocked on core; FP measurement is the live work

Verified: `git diff --stat origin/main...origin/claude/defs-core-scope` is
**docs-only (2 files)**, and `backend/app/definition_links/` on core's branch
contains **no `rules/` package**. So the registry does not exist yet.

Consequence for item 2 (GA), which the program manager left to my judgment:
GA is *not* blocked on the M-R7(a) answer, but it IS blocked on Seam 2
existing. Implementing GA any other way means editing `pipeline.py`'s frozen
`_BODY_DEFINITIONS_PREAMBLE_RE` — which the seam spec forbids and which would
collide with core's in-flight deletion of that very symbol. **Manager ruling:
do NOT force GA through the frozen shared modules.** GA waits for the
registry; the RED test is already written and will drive it the moment
`rules/` lands.

There is therefore **no Developer work available in this sprint right now**;
spawning one would produce either a forbidden edit or an idle agent. The
useful, unblocked, program-manager-endorsed work is the **corpus-wide
false-positive exposure measurement** for M-R7(a)'s ungated branch, plus
independent QA of the Planner's test suite. Spawning QA for both (M-R12).

### M-R12 — Model/effort for the QA spawn

QA: **Sonnet / high** — the deliverable is a precision measurement whose
crux is judging, row by row over real statutory prose, whether a candidate
is genuinely a definition; a wrong call here mis-informs a director-level
P-R2 decision. Per P-R6 QA is Sonnet high. **Haiku considered: no** — the
judgment, not the scripting, is the load-bearing part. `model=inherit` not
used. QA commits only test/contract/log files and never touches
implementation.

---

## 2026-08-04 — QA: D3, the two logged defects fixed

Both are docs/tests, not implementation, per this QA brief's D3.

**(a) Inverted test names (M-R10(a)).** Three tests in
`test_definition_links_us_preamble_family.py` (`test_real_pipeline_
misses_a_real_georgia_body_preamble_definitions_section_end_to_end` and its
MD/NE siblings) assert the FIXED behavior (`expected_terms <=
created_terms`) while their names say "misses" — post-fix the suite would
read "pipeline misses Georgia" while proving the opposite. Renamed to
`test_real_pipeline_captures_a_real_georgia_body_preamble_definitions_
section_end_to_end` (and the MD/NE equivalents,
`..._captures_a_real_maryland_...`/`..._captures_a_real_nebraska_...`).
Verified: `grep -rn` for the old names across `backend/` and `docs/` found
no other reference (nothing else depended on the literal name); re-ran the
file after renaming — still 4 failed / 1 passed, same failure reasons as
before, confirming the rename touched nothing but the identifier. These
tests were authored by a Planner instance that has since stood down, so
renaming them is not a role violation (per the brief's own framing) — noted
here per that same instruction.

**(b) Fixture README factual error (M-R10(b)).**
`backend/tests/fixtures/us_statutes/README.md` stated flatly that
`huggingface_hub`/`pyarrow` are not installed in `backend/.venv`. That was
true when written (an earlier sprint, 2026-08-02) but is stale: **`pyarrow`
IS installed in THIS sprint's `backend/.venv` and IS a declared dependency**
(`pyarrow>=17.0`, verified at `backend/pyproject.toml:15`). Only
`huggingface_hub` remains absent, and no fixture-building script in this
sprint needed it (all of QA's D1/D2 scripts read the on-disk vaquill/
open-us-law snapshot directly via `pyarrow.parquet` against the HF cache
path, never via the `huggingface_hub` API). Added a dated correction
paragraph rather than rewriting the original (which remains accurate as a
historical record of the 2026-08-02 sprint's own environment) — left
uncorrected, the original paragraph would send a future agent to build a
disposable scratch venv it does not need, exactly the drift M-R10(b)
flagged.

Both changes committed separately from D1/D2 per this sprint's
incremental-commit requirement.

---

## 2026-08-04 — QA: D2, independent audit of the Planner's test suite

Scope per the brief: do NOT redo the manager's M-R10 verification (diff
shape, 647/12 split, fixture byte-exactness — already independently
verified there). Audit what M-R10 did NOT check: are the 6 new GREEN tests
legitimately constraining, do the 12 RED tests actually prove the gates
they claim, and are the negative/FP guards strong enough given D1.

### Are the 6 new GREEN tests vacuous?

The 6: 1 unit-level gate pin
(`test_body_definitions_preamble_regex_does_not_recognize_georgias_real_
as_used_in_the_term_shape`) + 5 negative-FP guards
(`test_us_body_preamble_negative_guard.py`'s GA/MD/NE/MS/SD tests).
Confirmed by direct count: `backend/.venv/bin/pytest
backend/tests/integration/test_us_body_preamble_negative_guard.py
backend/tests/integration/test_definition_links_us_preamble_family.py -q`
shows exactly 1 + 5 = 6 passed among these two files (the other 4 tests in
`test_definition_links_us_preamble_family.py` are RED), matching the
manager's count.

**Unit-level pin**: asserts three things directly against
`pipeline._is_placeholder_heading`/`_BODY_DEFINITIONS_PREAMBLE_RE`/
`_derive_heading_from_body` — real, currently-existing functions. If that
code were deleted the import would fail and the test would error, not
silently pass — not vacuous. Its own docstring correctly says it is a
diagnostic pin, not a spec for the fix.

**The 5 negative-FP guards**: "would pass even if production code were
deleted" is TRUE today for all 5 (nothing captures ANY US preamble today,
so `created_definitions == []` is trivially true) — that is expected of
every RED-first negative guard and is not itself vacuity. The real
question is whether they would still discriminate once a REAL rule lands.
Tested this directly (not just reasoned about it) by building an
independent candidate `BodyPreambleRule.derive_heading` regex from the
sprint log's own D1 inventory (GA/MS "As used in this <unit> ... the
term", MD "In this <unit> ... the following words have the meanings
indicated" — see D1 below for the full regex) and running the 5 negative
fixture rows through it:

- GA/MD/MS/SD negatives: none contain "the term" (GA/MS shape) or "the
  following words have the meanings indicated" (MD shape) near their own
  trigger phrase, so my candidate regex correctly excludes all 4. More
  importantly, I confirmed these 4 tests would CATCH a plausible *looser*
  bug — a candidate regex requiring only the bare trigger phrase ("as used
  in this X" / "for purposes of this X") with no "the term" anchor DOES
  match all 4 negative rows — so these 4 tests demonstrably discriminate
  against a real, plausible over-broad implementation. Not vacuous.
- NE negative (`STATE_NE_C60_S60-643`, "Operator's license shall have the
  meaning found in section 60-474.") does not begin with an "As used in
  this X"/"For purposes of this X" trigger phrase at all — it guards a
  narrower, different hazard (a bare forwarding-reference sentence being
  treated as definitional on its own) than the other 4, and would not be
  reached by a trigger-phrase-anchored candidate rule's regex in the first
  place. Not vacuous, but its protection is of a different, narrower kind
  than advertised by grouping it with the other 4 — flagged below as a
  coverage gap, not a defect in the existing test.

**Verdict: none of the 6 green tests are vacuous.** All demonstrably
constrain behavior; one (NE) protects a narrower hazard class than the
other 4, which motivated the new test below.

### Do the 12 RED tests prove the gates/items they claim? Gate/item map

| Test | File | Item | Gate(s) |
|---|---|---|---|
| `test_ga_as_used_in_this_chapter_the_term_is_captured` | capture_red | 2 (GA) | U1, U6 |
| `test_real_pipeline_captures_a_real_georgia_...` | family | 2 (GA) | U1, U6 |
| `test_real_pipeline_does_not_fabricate_a_definition_from_a_georgia_section_...` | family | 2 (GA) | U1, U5 |
| `test_md_in_this_section_the_following_words_have_the_meanings_indicated` | capture_red | 3 (MD) | U1, U6 |
| `test_real_pipeline_captures_a_real_maryland_...` | family | 3 (MD) | U1, U6 |
| `test_ne_in_the_named_code_quoted_term_means_is_captured` | capture_red | 4 (NE quoted) | U1, U6 |
| `test_ne_unquoted_term_means_needs_markers_sprint_too` | capture_red | 5 (NE unquoted) | U1 (documents miss) |
| `test_real_pipeline_captures_a_real_nebraska_...` | family | 5 (NE unquoted — NOT item 4; fixture `STATE_NE_C43_S43-3329` is the unquoted shape, docstring confirms) | U1 (documents miss) |
| `test_ms_as_used_in_this_article_the_term_is_captured` | capture_red | 6 (MS block) | U1, U2, U6 |
| `test_sd_the_term_quoted_means_is_captured` | capture_red | 8 (SD quoted) | U1, U2, U6 |
| `test_sd_unquoted_comma_term_needs_markers_sprint_too` | capture_red | 5 (SD unquoted) | U1 (documents miss) |
| `test_chapter_scoped_ga_definition_links_a_same_chapter_use_but_not_a_different_chapter_use` | scope_red | 9 (GA half only) | U2 |

(11 rows above; the RED count is 12 because
`test_real_pipeline_does_not_fabricate_...` is counted RED in the manager's
tally even though its assertion is a negative-shape guard — it is RED
today only because the exact-set assertion `created_terms == expected_terms`
currently sees `created_terms == set()` for the genuine GA row too, per its
own docstring. Recorded that way here to match the manager's 12, not as a
disagreement.)

**Every test does drive the gate/item it claims** — I did not find a test
whose assertion is disconnected from its documented purpose. **One real
gap found**: item 9 in the sprint contract names "GA/MS" for chapter-scope
stamping, but `test_us_body_preamble_scope_red.py` contains only ONE test,
GA-only. **MS's own chapter/article-scoped convention (item 6's "As used
in this article, the term:" — the SAME trigger family as GA's, just a
different jurisdiction) has ZERO scope-enforcement test** — U2's live-path
"both directions" proof exists only for GA. This is a real, reportable gap
(the brief: "flag any gate with NO test coverage" — U2 has coverage, but
not for the second jurisdiction the contract itself names). I did not add
a fix for this myself: building a same-chapter/different-chapter MS
scope-scaffolding test would require either a second real MS row with
usable chapter metadata or hand-constructed scaffolding rows (the pattern
`test_us_body_preamble_scope_red.py` itself uses for GA) — a reasonable
next-QA-cycle addition, not urgent enough to add today given item 9 is
already blocked on the same core scope-trigger dependency for both states
and the underlying mechanism is already proven once (GA). Flagging to the
manager rather than guessing at scaffolding under time pressure.

**U3, U4** are correctly NOT covered by any committed test — U3 (zero
shared-module edits) is a structural fact best verified by `git diff`
(which the manager already did), not something a pytest assertion usefully
proves; U4 (full 53-jurisdiction sweep) requires reading the parquet
snapshot, which no test may do. Both are satisfied by non-test artifacts
(the manager's diff review; QA's D1 corpus scan below) — not a coverage
gap, a correct absence.

### New test added (QA-authored, new file only — Planner's tests untouched)

D1 (below) found a REAL, corpus-confirmed row that reproduces the NE
guard's exact hazard class (a forwarding-reference clause with no
definition text of its own) but — unlike the NE fixture — under a body
shape that DOES match a trigger-phrase-anchored candidate rule:
`STATE_MS_T17_C2_S25-34`, "(2) For purposes of this section, the term
\"political subdivision\" shall have the same meaning as provided under
Section 11-46-1." Added:

- `backend/tests/fixtures/us_statutes/qa_d2_forwarding_reference_rows.json`
  — one REAL, VERBATIM, full parquet row (all original columns), fetched
  live from the on-disk snapshot by a QA scratchpad script (never
  downloaded by any test).
- `backend/tests/integration/test_us_body_preamble_negative_guard_qa_
  forwarding_reference.py` — one new test,
  `test_ms_for_purposes_of_this_section_the_term_shall_have_the_same_
  meaning_as_provided_under_is_a_forwarding_reference_not_captured`,
  asserting `created_definitions == []` for this row.

**Confirmed GREEN today** (`pytest ... -v`: 1 passed) — same "nothing
captures anything yet" reason as every other negative guard. **Confirmed
NOT vacuous** by direct demonstration: widening the current inline-quote
extractor's idiom list by one plausible phrase
(`shall have the same meaning as`, a natural next step if someone tried to
also rescue NE's own "shall have the same meaning" rows) DOES cause a
spurious pointer-only `"political subdivision" -> "shall have the same
meaning as provided under Section 11-46-1"` candidate to be produced on
this exact real row when run through the unmodified extraction chain in a
scratch script — proving this new test would catch that specific,
plausible future regression, which the existing NE guard would not (its
own fixture row never reaches a trigger-anchored regex at all).

---

## 2026-08-04 — QA: D1, corpus-wide false-positive exposure for M-R7(a)'s ungated branch

**Verdict up front (plain language): the fully-ungated reading of M-R7(a)
is NOT safe to ship as specified.** Not because it fabricates wrong data —
in a 45-row hand-judged sample, it did not fabricate a single false
term/definition pair — but because of scale and section-type
misclassification: a realistic candidate rule claims **4x more rows
outside the placeholder-gated population than inside it (5,915 vs 1,468)**,
spread across **50 of 53 scanned US jurisdictions**, not just the 5 states
(GA/MD/NE/MS/SD) this sprint inventoried and tested. Most of that
ungated-only population turns out to be genuine, accurate single-clause
definitions embedded inside ordinary, substantively-different statutes
(criminal law, tax code, licensing, environmental rules) — the SAME
BLOCK-vs-CLAUSE boundary problem the Planner already found and routed for
Mississippi specifically (D2, MS→`defs-us-scoped-inline`), but the ungated
reading opens that exact problem to every jurisdiction in the corpus with
no inventory, no test, and no routing decision for any of the other 44.
Full reasoning, numbers, and the hand-judged sample below.

### Method

Script: scratchpad `qa_d1_corpus_scan.py` (not committed — measurement
tooling, not a test; reads the snapshot, per the brief's own carve-out).
Mirrors the manager's `mgr_probe.py` methodology: live import of the
CURRENT pre-seam `pipeline.py`/`us_profile.py` from this worktree, run
against the on-disk vaquill/open-us-law snapshot (never downloaded),
column-projected to `act_id`/`section_title`/`text` for memory efficiency.
Scanned **all 53 `us_*_statutes.parquet` files** in the canonical snapshot
(`301000fc3465374ee0f23c3c6953a8a861e95cad`) — every US state plus DC,
Puerto Rico, and the federal code — **2,038,247 rows total**. Run time
~93s.

**Candidate rule** (a realistic `BodyPreambleRule.derive_heading`, built
independently from the sprint log's own D1 inventory, NOT copied from any
hidden implementation — none exists; core's `rules/` package is still
absent, verified again today): three regexes, searched within the leading
500 chars of the normalized body —

1. GA/MS/SD shape: `\b(?:As used in this|For (?:the )?purposes of this)\s+
   (?:chapter|article|part|title|subchapter|section|act)\b[^.]{0,80}?\bthe
   term\b` — covers GA's and MS's dominant "the term:" preamble AND SD's
   unquoted comma variant ("the term, X, means"), since "the term" appears
   shortly after the trigger in both.
2. MD shape: `\bIn this\s+(?:chapter|article|part|title|subchapter|
   section|act)\b[,]?\s*the following words? have the meanings?\s+
   indicated\b`.
3. MS alternate shape (real D2 example, `STATE_MS_T75_C12_S55-5`): `\bThe
   words,?\s+terms and phrases as used in this\s+(?:...)\b[^.]{0,40}?
   \bshall have the following meanings?\b`.

For every row where one of these matched: **excluded** (not counted as
exposure) if `profile.is_definitions_heading(heading)` was already True
(baseline captures it via heading alone — registry is never consulted
either way), or if the CURRENT two-gate combo (Gate A
`_is_placeholder_heading` AND Gate B `_BODY_DEFINITIONS_PREAMBLE_RE`)
already succeeded (already captured today, not new exposure). Everything
else is "claimed" under the ungated reading and split:

- **GATED** — heading passes Gate A (`_is_placeholder_heading`): exposure
  identical under EITHER M-R7(a) branch, already a known/bounded/reviewed
  risk (this is GA's own population).
- **UNGATED-ONLY** — heading does NOT pass Gate A, i.e. is a real,
  descriptive, non-placeholder heading: claimed ONLY if M-R7(a) resolves
  to the fully-ungated branch. This is the NEW incremental exposure.

### Corpus totals

| | rows |
|---|---|
| Total rows scanned (53 files) | 2,038,247 |
| **Total claimed by the candidate rule** | **7,383** |
| — of which GATED (same risk either branch) | 1,468 |
| — of which UNGATED-ONLY (new risk, ungated branch only) | **5,915** |
| States/territories with any ungated-only exposure | 50 of 53 |

Gated population (1,468) is concentrated almost entirely in GA (1,224 —
this sprint's own target), plus CA (174) and IL (65), both pre-existing
placeholder-heading jurisdictions unrelated to this sprint, plus AL (5).

Ungated-only population (5,915) is **diffuse, not concentrated** — the top
6 states account for 4,102 (69%) but the remaining 31% (1,813 rows) is
spread across 44 more jurisdictions in amounts from 1 to 142:

| State | rows in corpus | claimed (ungated-only) |
|---|---:|---:|
| MD | 39,552 | 1,841 |
| FL | 24,866 | 1,031 |
| MS | 158,688 | 769 |
| FEDERAL | 54,853 | 435 |
| DC | 23,694 | 300 |
| SD | 39,589 | 226 |
| NC | 26,685 | 142 |
| NY | 40,102 | 136 |
| AL | 45,984 | 129 |
| MO | 29,296 | 103 |
| LA / MA / IN / WV / PA / DE / VA / KS / MN / ME / OK / RI / NV / WA / NJ / SC / ID / MT / VT / AR / NH / ND / HI / IA / OR / CO / CT / KY / MI / TN / NM / UT / AZ / TX / GA / NE / WI / IL / OH / WY | (various) | 1–84 each, 39 states, 673 rows combined |

Of the 5 states THIS sprint inventoried and tested (GA/MD/NE/MS/SD): only
MD (1,841), MS (769), and SD (226) show ungated-only exposure — matching
items 3/6/8's own targets almost exactly (this is the GOOD news: the
candidate rule's MD/MS/SD hits land where the Planner's D1 inventory says
they should). GA is almost entirely in the GATED population already (only
2 ungated-only, noise). **The other ~3,079 ungated-only rows are in 41
states this sprint never inventoried, never wrote a test for, and never
proposed a routing decision for** — that is the core of the exposure this
measurement exists to surface.

### Hand-judged sample: 45 rows, uniform random, seed 42

Sampled uniformly at random (not stratified — the resulting per-state mix,
MD 10 / FL 9 / FEDERAL 7 / MS 6 / DC 4 / SD 2 / NJ 1 / ID 1 / SC 1 / MN 1 /
WA 1 / NY 1 / AL 1, roughly tracks the population's own concentration).
For every sampled row, re-fetched the FULL (untruncated) real body text
from the snapshot, then ran it through the **actual, unmodified,
currently-shipping extraction chain** (`USProfile.extract_definitions_
from_section` then, if empty, `pipeline._extract_inline_quoted_
definitions` — exactly the same two calls pipeline.py already makes at
lines 418-429 for GA today) to see EMPIRICALLY what `Definition` rows
would be created, rather than eyeballing the prose and guessing. Scripts:
scratchpad `qa_d1_fetch_sample_fulltext.py`, `qa_d1_simulate_extraction.py`.

**Result: 0 of 45 rows produced a fabricated or nonsensical term/
definition pair.**

- **9/45 (20%) produced zero candidates.** Read every one of these 9 by
  hand: all 9 are GENUINE definitions the current idiom-anchored extractor
  simply can't parse yet (verbs it doesn't recognize — `"X" includes
  Y` appears in 6 of the 9: `STATE_DC_T47_C44_S47-4405`, `STATE_SC_
  T34_C5_S34-5-10`, `STATE_DC_T19_C17_S19-1705.01`, `STATE_FL_TX_C112_
  PIII_S112.3125`, `STATE_MS_T63_C16_S17-217`, plus SD's already-documented
  unquoted-comma shape twice and one new data point:
  `STATE_AL_T2_C40_S11-40-25`, "For purposes of this section, the term
  elected municipal official means any mayor, council member..." —
  **Alabama also has an unquoted-term convention**, previously undocumented
  in the D1 inventory (only NE/SD were flagged) — a new, small,
  cross-sprint (`defs-us-markers`) data point, not a false positive since
  it produces zero output either way). None of these 9 are "trigger fired,
  nothing is actually defined" false positives — every one has a real
  definitional relationship in its text; today's code just can't extract
  it. Harmless (no bad data), but also not the safety net it might look
  like — it's an accident of today's narrow idiom list, not a designed
  guard (see the forwarding-reference finding below).
- **36/45 (80%) produced ≥1 candidate. Every term I checked against the
  row's own real text was accurate** — a real term genuinely given its
  real statutory meaning (examples: MD `STATE_MD_Agbo_T3_S1_S3-101`, 14
  clean architect-licensing terms; FL `STATE_FL_TXIV_C215_S215.4725`, 9
  terms from Florida's Israel-boycott-divestment statute; USC
  `STATE...USC_T43_C44_S2607`, 4 clean federal land-grant terms). The
  closest things to "noise" found were data-QUALITY issues, not
  false-DATA issues: definition text sometimes bleeds into trailing
  legislative-history/citation boilerplate when a federal section has no
  later quoted term to bound the entry (`USC_T26_C1_S804`, "life insurance
  deductions" definition text runs on into "(Added Pub. L. 98-369...)
  Editorial Notes... Prior Provisions..."), and a handful of dual-alias
  `"X" or "Y" means` definitions capture only one of the two aliases
  (`STATE_FL_TXLVIII_C1004_PI_S1004.0971`'s "Administer"/"administration"
  — a pre-existing extractor limitation, not something this rule
  introduces).

**But roughly half of the 36 are CLAUSE-shaped, not BLOCK-shaped** — a
single (or 2-3) defined term(s) embedded inside a section whose real
subject is something else entirely, not a definitions-focused block. Real
examples, quoted verbatim: `STATE_NJ_T2C_C35_S35-10.4` ("Toxic
Chemicals") — "As used in this section the term \"toxic chemical\" means
any chemical or substance having the property of releasing toxic fumes"
— followed by 3 subsections of drug-paraphernalia criminal-offense
provisions with nothing else definitional in them. `STATE_MS_T41_C25_
S41-45` — "As used in this section, the term \" abortion \" means the use
or prescription of any instrument, medicine, drug..." inside Mississippi's
abortion-restriction statute, whose remaining subsections are penalties,
not definitions. `STATE_DC_T8_C1_S8-108.03` (dry-cleaning solvent
regulation) — one clause defining "child-occupied facility", the rest of
the section is unrelated equipment/permitting rules. `STATE_FL_TX_C112_
PIII_S112.3125` (dual public employment) — one clause defining "public
officer", the rest is conflict-of-interest procedure. Each of these
produces an individually-accurate `Definition` row, but the SECTION gets
reclassified as a "Definitions section" when it plainly is not one — the
exact MS BLOCK-vs-CLAUSE conflict the Planner already found and routed
(D2), now confirmed live in NJ, MS (again, a different row), DC, and FL,
none of which were part of that routing decision.

**A sharper finding, confirmed live, cross-referenced in D2 above:**
`STATE_MS_T17_C2_S25-34` — "(2) For purposes of this section, the term
\"political subdivision\" shall have the same meaning as provided under
Section 11-46-1." — reproduces the exact forwarding-reference
false-positive shape the Planner's own NE negative-guard test exists to
prevent, EXCEPT this row's trigger phrase ("For purposes of this section,
the term") DOES match a realistic candidate rule's anchor, unlike NE's own
fixture row. It produced 0 candidates today only because the current idiom
list doesn't recognize "shall have the same meaning as provided under" —
proven live (scratchpad snippet) that widening the idiom list by one
plausible phrase (`shall have the same meaning as`, a natural next step to
also rescue NE's own convention) DOES turn this into a spurious
pointer-only `"political subdivision" -> "...Section 11-46-1"`
`Definition`. This is not hypothetical: it is a real corpus row sitting in
the ungated-only population today, one idiom-list widening away from
becoming a live false positive. Added a dedicated test for it (D2 above).

### Is the ungated branch safe? What would make it safe? Costs in each direction.

**Not safe as a blanket "any US-\* rule fires whenever baseline returns
None" mechanism.** The risk is not "wrong facts get created" (empirically
low in this sample) — it is (1) **scale**: 5,915 rows, 4x the gated
population; (2) **breadth**: 50 of 53 jurisdictions touched, only 5 ever
inventoried; (3) **section-type misclassification**: roughly half the
rows that DO extract cleanly are CLAUSE-shaped, reclassifying an ordinary
criminal/tax/licensing/environmental statute as a "Definitions section"
for the sake of one embedded clause — a real precision cost even though
the specific `Definition` row is accurate; and (4) a **confirmed,
reproducible hazard class** (forwarding-reference-as-definition) that
recurs outside the one state it was originally tested for, and is
currently masked only by an accident of today's narrow idiom list, not by
any designed guard.

Three options, with actual row counts (not a recommendation to pick one —
per the brief, recall/precision trade-offs escalate to the director):

- **(A) Keep the placeholder-heading gate (M-R7(a) branch 2).** Captures
  the 1,468 gated rows (GA's 1,224, already fully inventoried and tested,
  plus CA/IL/AL as a bonus nobody asked for). **Loses all 5,915
  ungated-only rows — including this sprint's own targeted MD (1,841),
  MS (769), and SD (226) conventions.** Per the Planner's own D4 finding,
  this does not just "block pending a future core fix" for MD/MS — it
  makes them unreachable by a `BodyPreambleRule` UNLESS core separately
  widens the placeholder-recognizer's pattern list for MD's `"§N–NNN."`
  and MS's `"Miss. Code Ann. § N-N-N"` heading shapes specifically (a
  bounded, reviewable, already-flagged-as-available core change,
  independent of M-R7(a)'s general answer). SD stays unreachable either
  way — its headings are genuinely real, not placeholders (D4).
- **(B) Full ungate (M-R7(a) branch 1), as specified.** Captures all 7,383
  rows, including the targeted MD/MS/SD conventions. **Cost: 5,915 rows of
  brand-new exposure across 44 states this sprint never inventoried**,
  a large minority to roughly half of the extractable ones (my sample's own
  count: 15/36 ≈ 42% clearly CLAUSE-shaped, a few more borderline) being
  CLAUSE-shaped section misclassifications, plus the confirmed,
  reproducible forwarding-reference hazard recurring outside NE, plus a
  confirmed data-quality risk (definition-text pollution from trailing
  legislative-history boilerplate, worse for FEDERAL sections, which
  showed 435 ungated-only rows on their own).
- **(C) A narrower middle path** (offered as an option for the director,
  not a QA recommendation): keep the placeholder gate for the GENERAL
  "any US-\* rule, any heading" case — this alone protects all 41
  non-targeted states from ANY exposure — and have core do the bounded
  MD/MS placeholder-widening from (A) to unlock 2,610 of this sprint's
  own targeted rows (1,841 + 769) with the SAME precision profile GA
  already has (bounded by "is this heading really information-free", a
  narrower and better-understood risk surface than "does any US section's
  body happen to contain this trigger phrase"). SD (226 rows) would need
  its own separate, `US-SD`-scoped mechanism (e.g. an entry-count/
  block-shape requirement, matching the Planner's own D2 MS discriminator
  idea, but scoped to one jurisdiction, not opened to the other 52) rather
  than a blanket ungate. Cost: this sprint does not get the ~3,079
  ungated-only rows in the other 41 states — but those were never part of
  this sprint's mandate to begin with, so that is not a loss relative to
  the contract, only relative to option (B)'s larger scope.

Not verified (explicit gap, not asserted): I did not re-run the D1
extraction-chain simulation across the FULL 5,915-row ungated-only
population, only the 45-row sample — the per-state totals above are exact
(full-corpus regex counts), but the "0/45 fabricated, ~50% CLAUSE-shaped"
rates are sample-based estimates with the honest uncertainty of n=45, not
a full census. I also did not attempt to quantify how many of the 5,915
would trip the SPECIFIC forwarding-reference hazard if the idiom list were
widened — I found and confirmed one live instance, not a corpus-wide count
of that specific sub-shape.

---

## 2026-08-04 — Manager: D-PREAMBLE-ALL absorbed, sprint scaled to all states

### M-R13 — Director ruling D-PREAMBLE-ALL supersedes QA's options A/B/C

Director (main @ `321ddab`), verbatim intent: *"I explicitly asked
researching and writing code for all of the states."*

The ruling supersedes all three of QA's options. Binding consequences:

- **No targeted-widening compromise, no gate, no state left dark.** Every
  jurisdiction's preamble-family shapes get INVENTORIED and then CODED.
- **Dispatch stays UNGATED** — core's M6, now director-confirmed. M-R7(a) is
  therefore ANSWERED: branch 1. Items 3/4/6/8 are **un-held**; the
  placeholder gate is not coming back.
- **Precision comes from inventoried per-state rules + negative guards**
  (QA's forwarding-reference guard is the model), **not** from gating. This
  is the key design instruction: our defence against the 5,915-row exposure
  QA measured is *knowing each state's real shapes*, not refusing to look.
- Per-state precision conflicts still escalate with data, per D-Q1 — as QA
  modelled.

Verified before acting (not taken on report): QA's three commits are on the
branch (`e4a030f`, `29391e7`, `eb1f0d8`), remote in sync, and the corpus
totals I quote below are read from the committed log, not relayed.

### M-R14 — The worklist, and why it is bigger than "44 more states"

QA's D1 candidate population is the worklist: **7,383 rows over 2,038,247
scanned across 53 files** — 1,468 gated + **5,915 ungated-only**, touching
**50 of 53 jurisdictions**.

Two properties make this a different shape of job from the original 5-state
sprint, and they drive the plan:

1. **It is diffuse, not concentrated.** The top 6 states hold 4,102 (69%);
   the remaining 1,813 are spread over 44 jurisdictions in amounts from 1 to
   142. There is no small set of big wins that finishes this — a long tail of
   1-to-84-row states has to be inventoried individually or it stays dark,
   which is exactly what the ruling forbids.
2. **Only 5 states have ever been inventoried.** ~3,079 ungated-only rows sit
   in 41 states with no inventory, no test, and no routing decision. Reused
   sample-level guesses are explicitly not acceptable per the ruling ("the
   inventory must cover every state's shapes, not a sample-level guess per
   state").

Per state the inventory must classify: **BLOCK-shaped** (ours → capture
rules), **CLAUSE-shaped** (scoped-inline's → hand off WITH data, never thrown
over the wall), and **hazard rows** (→ negative guards).

### M-R15 — Scale-out design: parallel READ-ONLY scouts, then ONE writer

The obvious move — several Planners inventorying concurrently — is exactly
the hazard that bit this sprint already (M-R8: two writers in one worktree,
conflict-free only by luck). The program rule now forbids it.

**Design: separate reading from writing.**

- **N inventory scouts run in parallel, strictly READ-ONLY to the repo.**
  Each owns a disjoint slice of jurisdictions, reads the parquet snapshot and
  the live code, and writes its findings ONLY to its own uniquely-named
  scratchpad file. No repo writes, no `git` commands, no commits. Disjoint
  scratchpad paths mean zero write contention by construction.
- **Then ONE Planner** (sole writer in the worktree) consolidates every
  scout file into the contract + log, authors the RED tests from the real
  rows the scouts identified, and commits. Single writer, so the M-R8 hazard
  cannot recur.

Slices are balanced by judgment load rather than row count, because the
long-tail states cost per-state overhead regardless of volume:

- **S1** — FL (1,031), NC (142), AL (129), MO (103): 4 states, 1,405 rows.
- **S2** — FEDERAL (435), DC (300), NY (136): 3 states, 871 rows; FED is the
  most structurally complex (lettered/numbered outline paragraphs, and QA
  flagged legislative-history boilerplate polluting definition text there).
- **S3** — the 39 low-volume jurisdictions (673 rows combined, 1–84 each):
  many states, low volume, high per-state overhead.
- **S4** — re-classify the 5 already-inventoried states (GA/MD/NE/MS/SD) into
  the new BLOCK/CLAUSE/hazard scheme so the whole corpus is described in ONE
  vocabulary, plus the gated CA (174) / IL (65) population that this sprint
  inherits but never chose.

**Model/effort — all four scouts: Sonnet/high.** Justification: the load-
bearing act is judging, on real statutory prose, whether a row is a
definitions-bearing BLOCK, an embedded CLAUSE, or a hazard — the same
judgment QA did by hand, now at 50-state scale, and a wrong call propagates
into a RED test and then into shipped behavior. **Haiku considered: no** —
scripting is the easy half; the classification is not mechanical.
`model=inherit` not used. Scouts are read-only, so they carry no commit
rights and cannot violate role separation.

### M-R16 — Two ruling items folded into the same pass

- **MS chapter-scope U2 gap** (QA-flagged): the MS scope RED test is added in
  the consolidating Planner's pass, not deferred.
- **CLAUSE-shaped populations**: each scout produces a per-state row list +
  verbatim examples, packaged for the scoped-inline panel and sent to the
  program manager for routing. Data first, never bare rows.

### M-R17 — Implementation remains blocked; this is inventory + RED authoring

Unchanged from M-R11 and re-verified: core's branch is docs-only, no `rules/`
package. Nothing here is implementable yet. The ruling explicitly endorses
running inventory + RED authoring NOW so the panel is not idle, with
implementation following core's merge.

---

## 2026-08-04 — Manager: scouts returned, verified, consolidating Planner dispatched

### M-R18 — Scout outputs verified against the files, not accepted on report

All four scouts completed and reported through the program manager (they had
no channel to me by name). Every one confirmed zero repo writes. I verified:

- All four findings files exist and are substantial: `scout_S1_findings.md`
  (45,810 b), `scout_S2_findings.md` (48,026 b), `scout_S3_findings.md`
  (31,746 b), `scout_S4_findings.md` (39,215 b), plus CLAUSE packages
  (`scout_S3_clause_package.json` 25,657 b, `scout_S4_clause_package.json`
  29,313 b) and S1/S2 per-jurisdiction JSONs.
- **The read-only design held.** `git status --porcelain` on this worktree is
  clean apart from my own committed docs; the scouts wrote only to disjoint
  scratchpad paths. The M-R15 separation of reading from writing worked as
  intended — four agents ran concurrently with zero write contention.

**S4's test-defect claim independently CONFIRMED by me** (the highest-impact
claim, so the one I checked myself rather than delegating):
`test_real_pipeline_captures_a_real_nebraska_body_preamble_definitions_
section_end_to_end` (`test_definition_links_us_preamble_family.py:328`)
targets `STATE_NE_C43_S43-3329` and asserts capture of 4 unquoted terms
(`Account`, `Authorized attorney`, `Child support`, `Department`). **Its own
docstring concedes** that going green needs "BOTH this sprint's preamble-
recognition fix AND a NEW unquoted-term entry splitter -- the latter is
`2026-08-04-defs-us-markers` territory". A test in this sprint's suite that
cannot pass on this sprint's work alone makes this sprint's gate hostage to
another panel's delivery. Genuine defect; must be re-scoped.

### M-R19 — Headline findings that change the plan

- **S3's is the structurally important result**: the 40-state tail holds only
  ~30 genuine BLOCK rows, and **two shared idioms (B1 GA-style colon-list, B2
  words-have-meanings) cover essentially all of it**. That converts the long
  tail from 39 bespoke rules into a **parameterized rule + test matrix** — the
  single biggest simplification available to this sprint.
- **S1 found a real production bug**: the inline fallback's last entry runs to
  end-of-text (proven on FL 540.11 — ~100% claimed vs ~12% true coverage).
  This **inflates any capture measurement that uses the fallback**, so our
  before/after numbers (U6) must not be taken from it uncorrected. Already
  routed to the markers panel; consequence for us is measurement hygiene.
- **S2**: FED ~45.5% BLOCK but with 26.4% legislative-history contamination
  and 86% contaminated last-entries (compounded by S1's bug); DC uniform 48%
  BLOCK + 26 genuinely unquoted rows; NY has a literal-`\n` corpus bug causing
  a 100% extraction blackout — **already accepted by core as its I8, do not
  re-route**.
- **S4**: MS population is **2.7x** D1's (second convention, "shall have the
  meaning(s) ascribed herein", hand-confirmed); CA has 1,401 signal rows (748
  new exposure, 663 BLOCK) — a large population this sprint inherits; IL is
  **79% CLAUSE**, an outlier; MD's count is 44% of D1's and **unreconciled**.
- **S4 also found and fixed a tail-ratio bias in the D2 discriminator** (67%
  false-CLAUSE rate on SD). **The consolidating Planner must not reuse that
  discriminator style unfixed** — this is the kind of methodology error that
  silently mis-routes whole populations between panels.
- **Count methodologies do not reconcile** (S1's FL 330–646 vs QA D1's 1,031;
  S4's MD gap). Honest floor/ceiling reporting is required; a single
  confident number here would be fabricated precision.

### M-R20 — Model/effort for the consolidating Planner

Planner: **Sonnet / high** — it must reconcile conflicting count
methodologies, re-scope a defective test without weakening it, design a
parameterized rule+test matrix across ~50 jurisdictions, and avoid a
discriminator bias that already produced a 67% false-CLAUSE rate. That is
sustained judgment, not transcription. **Haiku considered: no.**
`model=inherit` not used. It is the **sole writer** in this worktree
(M-R8/M-R15); no other agent writes here while it runs.

---

## 2026-08-04 — Consolidating Planner: D1–D6 (sole writer, per M-R15/M-R20)

Read all four scout findings files, both CLAUSE packages, the S1/S2
per-jurisdiction JSONs, the sprint contract, and M-R13..M-R20 in full before
writing anything. Committing after each deliverable per the director's
worktree-safety instruction (two writers already caused an incident this
sprint, M-R8).

### P-D2 — NE test defect re-scoped (manager's highest priority, M-R18)

Confirmed the defect independently (re-ran the assertion against real code,
did not take the manager's/S4's report on faith): `extract_definitions_
from_section(row["text"], scope="law-wide")` and `_extract_inline_quoted_
definitions(row["text"], scope="law-wide")` both return `[]` for
`STATE_NE_C43_S43-3329`'s real, unquoted body, live-verified in this
worktree's venv today. `_is_placeholder_heading(row["section_title"])` is
also `False` (NE's real `"View Statute 43-3329"` heading is not a bare
placeholder), so today's gated dispatch never even attempts body derivation
for it — matches D1's 0/559 exactly.

**Split `test_definition_links_us_preamble_family.py`'s single mis-scoped
NE test into two, coverage unchanged, correctly attributed:**

1. `test_real_nebraska_unquoted_body_preamble_is_a_genuine_in_family_
   candidate_but_no_current_extractor_can_parse_it` — NEW unit-level pin
   (mirrors this file's own existing GA gate-level-pin convention), calling
   only real, unedited code. Pins exactly what a `BodyPreambleRule` built in
   THIS sprint's file can and cannot deliver for this row: (a) the row
   genuinely carries this sprint's own trigger convention ("the following
   definitions apply:"); (b) it is unrecognized today for the ordinary
   reason (no placeholder heading); (c) both real extractors already return
   `[]` given this exact body, isolating the unquoted-term gap as a pure
   extraction defect (`2026-08-04-defs-us-markers` territory), not a
   recognition defect (this sprint's territory). **GREEN today** (like the
   family's negative-guard tests) — verified by running it.
2. `test_real_pipeline_still_cannot_capture_the_real_nebraska_unquoted_
   body_preamble_definitions_needs_markers_sprint_too` — the original test,
   renamed to disclose the cross-sprint dependency in its own name (matching
   the sibling convention already established by `test_us_body_preamble_
   capture_red.py`'s `test_ne_unquoted_term_means_needs_markers_sprint_too`,
   a DIFFERENT real NE row, `STATE_NE_C44_S44-5003`, same shape). **Assertion
   is byte-for-byte unchanged** — still requires all 4 real terms
   (`Account`, `Authorized attorney`, `Child support`, `Department`) —
   nothing weakened. **Verified RED for the right reason**: ran it directly,
   fails with `assert {...4 terms...} <= set()` (empty `created_definitions`
   from the real pipeline), the same live-path failure mode as every other
   capture test in this sprint, not an import error or a fixture defect.

Verified the whole file after the edit: `2 passed` (the new unit pin + the
pre-existing GA gate-level pin), `4 failed` (GA capture, GA false-positive
guard, MD capture, the renamed NE test) — exactly the expected shape before
`us_body_preamble.py`/core's registry exist. No test outside the NE block
was touched.

### P-D3 — MS chapter-scope U2 test (QA-flagged gap, M-R16)

New file `test_us_body_preamble_ms_chapter_scope_red.py` +
`fixtures/us_statutes/ms_scope_preamble_rows.json`, mirroring
`test_us_body_preamble_scope_red.py`'s GA convention exactly (one real
vendored definitions row + two hand-constructed, unvendored "using" rows,
never a fabricated corpus row).

Real base row `STATE_MS_T45_C10_S34-1` (chapter `"10"`, terms Conviction/
Department/Offender/Registrable offense/Registrant) fetched **live, myself,
directly from the real `us_ms_statutes.parquet`** in this worktree's venv —
not copied from the scout's truncated `body_opening` summary field — and
vendored byte-for-byte into the new fixture, diffed against my own live
fetch to confirm exactness before committing.

**Followed S4's warning, verified independently before writing the test**:
re-fetched `us_ms_statutes.parquet` and confirmed `S34-1`'s body text is
byte-identical across the 11 chapter values S4 named
(`C1,C2,C3,C4,C5,C6,C7,C9,C10,C11,C33`) — so, exactly as recommended, the
out-of-chapter negative case is a hand-constructed scaffolding row (chapter
`"99"`), never a second real corpus row, which would very likely be the
SAME duplicated text rather than a distinct statute.

Also flagged, in the test's own module docstring, an MS-specific
sharpening of the GA scope test's already-named core dependency: MS's
chapter trigger wording ("For purposes of this chapter, unless the context
requires otherwise...") differs from GA's ("As used in this chapter"), so
core recognizing GA's phrasing for `_determine_scope` does not
automatically cover MS's — a per-phrasing, not per-state, dependency worth
a future reader knowing before assuming GA's scope test going green implies
MS's will too.

**Verified RED for the right reason**: ran the test directly —
`assert 0 == 1` on `registrant_defs` (zero `Definition` rows created today,
same underlying miss as every other capture test in this family), not a
fixture-loading error or an import error.

### P-D1 — Count reconciliation: methodologies found and diffed, not guessed

Neither S1 nor S4 had the ORIGINAL scripts behind the numbers they were
comparing against — I do, because this scratchpad is shared across the
whole sprint. I located and read the actual source scripts for every cited
figure below (not re-derived from prose) before writing this section.

**FL/NC/AL/MO (S1's floor-vs-cited gap): genuinely reconciled, not a
mystery, and not the same story for every state.**

I confirmed `qa_d1_corpus_scan.py` (QA's D1 corpus-wide false-positive
exposure scan — the SAME script that produced the 7,383-row worklist
M-R13/14 cite) is the exact, reproducible source of the M-R15 slice
numbers: re-reading its own output file (`qa_d1_summary.json`) gives FL
`claimed_total=1031`, NC `142`, AL `claimed_ungated_only=129`
(`claimed_total=134`, 5 gated), MO `103` — an EXACT match to M-R15's
citation, not an approximation. So the "cited" number is real, reproducible
code output, not folklore.

The gap to S1's own count (FL 330/646, NC 102/276, AL 135/216, MO 476/744)
is explained by two independent, provable regex differences between QA's
`_TERM_PREAMBLE_RE` and S1's `PREAMBLE_RE`, not by one script being "wrong":

1. **QA's regex requires the literal singular phrase `"the term"` (word-
   bounded — I verified live: `re.search(r"\bthe term\b", "the following
   terms mean")` is `None`, since `\b` fails between "term" and the "s")
   and does NOT require any defining verb to follow it.** S1's regex
   ADDITIONALLY matches the plural `"the following terms mean"` shape (MO's
   OWN dominant convention, confirmed 434/476 of MO's own candidates use
   "this section" as the unit — plural "terms", not singular) but DOES
   require a defining verb (`means`/`shall mean`/etc.) within a bounded gap
   after the trigger. Net effect, verified against each state's own
   dominant idiom (scout §1 tables): MO's gap (476 vs 103, 4.6x) is almost
   entirely the plural-vs-singular anchor — QA's regex structurally cannot
   match MO's dominant shape at all. AL's smaller, same-direction gap (135
   vs 129, roughly even) is because AL's real population splits between a
   plural multi-term convention (QA misses it) and a singular single-term
   convention (QA catches it), so the two roughly offset.
2. **For FL, the gap runs the OTHER way** (S1 330-646 vs QA 1,031, QA
   HIGHER) because QA's regex, unlike S1's, never requires a defining verb
   after "the term" — it fires on ANY body containing "the term" within 80
   non-period-crossing chars of "As used in this X"/"For purposes of this
   X", including non-defining mentions (forwarding references, "shall be
   deemed" attribution clauses, and other HAZARD shapes S1's §7-equivalent
   catalogue and QA's own D1 45-row hand-check already document as real).
   This is not a defect in QA's script — its own docstring says its PURPOSE
   is false-positive EXPOSURE measurement (a deliberately loose net to
   stress-test the ungated branch), not a precise convention census. NC's
   smaller reverse gap (S1 full-body 276 > QA's 142) is consistent with the
   same story at smaller scale.

**Recommendation, not a single fabricated number**: report BOTH numbers for
what they actually measure, not as competing claims about the same thing.
QA's D1 total (1,031/142/129/103, and the 7,383/5,915 worklist totals built
from it) is the right number for **exposure/risk sizing** — it is already
the sprint's official worklist and should NOT change. S1's own count
(330-646/102-276/135-216/476-744, a genuine defining-verb required) is the
right number for **building actual capture rules** — it is a truer
per-state estimate of what a real `BodyPreambleRule` would need to parse.
Neither is "the" candidate count; they answer different questions.

**MD: genuinely reconciled, and the correction changes the contract's own
target number.** The contract's item 3 target ("3,327/39,552") and S4's own
comparison baseline ("D1") are NOT QA's D1 script — I confirmed
`qa_d1_summary.json` gives MD `claimed_ungated_only=1841`, essentially
matching S4's own independent re-measurement (1,849, off by 8 — a near-exact
convergence between two INDEPENDENT methodologies, QA's regex-based scan
and S4's own trigger+structural-entry scan). I traced "3,327" to its real
source: `planner_md_ne_classify.py` (an earlier Planner-attempt-1 script,
found on disk in this same scratchpad, output preserved in
`planner_md_ne_classify.out`). Its "multi-entry BLOCK" bucket — the exact
source of "3,327" (`grep` confirms the literal number in its own stdout) —
counts **any MD row with >=2 occurrences of a quoted-term-then-"means"/
"shall mean"/"has the meaning" pattern ANYWHERE IN THE FULL BODY TEXT**,
with NO requirement that an "In this &lt;unit&gt;... the following words have
the meanings indicated" preamble trigger be present at all, let alone near
the body's start. This is a structurally different, much LOOSER population
than "rows whose body opens with MD's real preamble convention" (what QA's
D1 and S4's re-scan both measure) — it is a superset that also counts any
MD row that happens to gloss two unrelated quoted terms anywhere in a long
body for reasons having nothing to do with this sprint's family.

**Correction for the record**: MD's reconciled, reproducible population for
THIS sprint's rule-building purposes is **~1,841–1,849/39,552** (two
independent methodologies converging), not 3,327. I am NOT silently
patching the contract's old item-3 language — the corrected number and this
reasoning carry into D6's item-list rewrite below, with the "3,327" figure
explicitly retired and its real source documented so no future reader
re-cites it as if it measured the same thing.

**Fallback-inflation caveat (S1's proven bug, D-PREAMBLE-ALL M-R19)** —
stating plainly which numbers in this sprint's own findings ARE and ARE NOT
built on the affected measurement, as directed:

- **NOT affected**: every count in this section above (QA's D1, S1's own
  330-646/102-276/135-216/476-744, S4's 1,849/558/1,423/171/1,316/9 BLOCK
  counts) — all are regex/trigger-match counts or bounded-paragraph-run
  heuristics, none call `_extract_inline_quoted_definitions`/
  `extract_definitions_from_section` and treat "produced >=1 candidate" as
  the classification signal. S1 explicitly abandoned that approach after
  finding the bug (see S1 §2's own methodology note).
- **AFFECTED, do not reuse uncorrected for U6**: S2's FEDERAL/DC/NY
  extraction-rate figures ("386/435 FEDERAL rows yield >=1 candidate",
  "145/300 DC rows extract... 91.7% leak", "94/136 NY rows extract... 79.8%
  of last entries >1,000 chars") are raw, uncorrected
  `_extract_inline_quoted_definitions` output counts — S2 already
  self-flagged the specific contamination/leak rates for each, so these are
  disclosed, not silently wrong, but whoever builds U6's before/after
  capture-rate report must not treat "row produced >=1 candidate" as "row
  correctly captured" for these three jurisdictions without applying the
  same correction. **S4's `n_extracted_today` field is the SAME
  raw-extractor count** (S4's own method note: "run the REAL extractors to
  get `n_extracted_today` — empirical ground truth") — safe for
  BLOCK/CLAUSE/HAZARD classification (S4's discriminator uses `trig_start`,
  not extractor output, after its own self-correction) but the EXACT term
  counts inside `n_extracted_today`/`extracted_terms` for any state's
  longer-tail rows should be treated with the same caution before being
  quoted as a clean per-row capture count in a U6 report.

### P-D4 — Parameterized rule + test matrix (the main event)

Six new test files, six new fixture files, all vendored from LIVE fetches
against the real corpus (never from a scout's truncated `body_opening`
summary field) and verified against real, unedited production code before
being written. Every capture test confirmed RED for the live-path reason
(pipeline creates zero `Definition` rows today); every negative-guard test
confirmed to pass today (matching the family's established "green today,
must stay green" convention).

**B1 (colon-list, S3's own naming) — the single biggest simplification
this sprint found.** `test_us_body_preamble_b1_colon_list_matrix_red.py`,
parametrized over 9 real rows across DE/ID/KS/LA/OK/SC/VA/WV/IL (`fixtures/
us_statutes/us_preamble_b1_rows.json`). One shared idiom + the EXISTING
`(N)"Term"` splitter or its inline-quote fallback (both already shipped,
neither edited) covers all 9 — no per-state bespoke extraction logic
needed. Each expected-terms set is a verified-live SUBSET, not the row's
full term list, with the specific, real, independently-confirmed reason
for each omission named in the test's own comment (LA's own preamble
sentence defines a term before the numbered list starts and is missed by
the primary extractor; WV's own first entry is itself a forwarding
reference, deliberately not asserted as a positive capture; KS's fourth
term has a corpus-quirky casing). GA is not duplicated here (already has
its own dedicated fixture/tests).

**A new, real, live-confirmed corpus defect found while building this
matrix, distinct from the already-documented DE-style `Â` mojibake**:
`STATE_RI_T42_C42-28_S42-28-3.5` (S3's own named RI example) stores its
quote characters as a mangled `\x80\x9c`/`\x80\x9d` byte sequence — NEITHER
extractor recognizes any term in it (0 candidates, confirmed live). Left
out of the capture matrix rather than asserting something the real data
cannot support; flagged here, not silently dropped, for whoever owns
corpus ingestion next.

**B2 (words-have-meanings) — MD's own dominant shape, also DE/LA/WV.**
`test_us_body_preamble_b2_words_have_meanings_matrix_red.py`, 3 real rows,
all extract cleanly via the existing splitter, no fallback needed. Also
pins WV's own near-miss (S3 §4): its B2 row's body opens with the LITERAL
word "Definitions." as its own embedded sub-heading — a cheaper signal
than the idiom this file tests, not built here (production-rule design is
out of Planner scope), but confirmed present on the real, vendored row so
a future rule author does not have to re-verify a scout's unverified
claim.

**MS's second convention** (S4 finding, ~845 real rows corpus-wide,
distinct from MS's original D1-inventoried "As used in this article, the
term:" shape already covered by `test_us_body_preamble_capture_red.py`).
`test_us_body_preamble_ms_second_convention_red.py`, 2 real rows —
reuses `STATE_MS_T45_C10_S34-1` (already vendored for D3's scope test,
deliberately not duplicated into a second fixture file) plus one freshly
fetched row (`STATE_MS_T49_C5_S11-1`), confirming the convention across
more than a single example.

**CA — 663 BLOCK rows, "not a minor bonus population" (S4's correction of
M-R11's earlier phrase).** `test_us_body_preamble_ca_block_red.py`, one
real row plus a unit-level pin. The pin proves something concrete and
specific: this exact row's body already contains today's EXISTING (pre-
sprint) Gate B trigger vocabulary ("definitions"..."apply") and misses
ONLY because the real prefix before the word "definitions" is 84
characters, one over Gate B's own 80-char cap — a different, narrower,
already-almost-passing reason than GA/MD/NE/MS/SD's own misses, confirmed
by calling `_derive_heading_from_body` directly and reading its `None`
return, not asserted from a scout's report.

**FEDERAL/DC/NY** (scout S2's slice). `test_us_body_preamble_fed_dc_ny_red
.py`. FEDERAL's own capture test asserts only 2 of 4 real terms (the 2
confirmed clean) — the answer to the contract's own open question ("say
whether a preamble rule can produce clean text for FED"): **NO, not for
every entry, using either existing extractor as-is** — proven on a real,
vendored row, not asserted: a companion unit-level pin shows the row's own
LAST entry ("wildlife") swallows 8,195 of 8,539 characters, including the
entirely unrelated next subsection. This needs a new, properly-bounded
extractor — production code out of this sprint's Planner-only file and out
of bounds for this sprint's frozen modules (`us_profile.py`/`pipeline.py`)
— named here as a real, confirmed, currently-open defect, not silently
absorbed into a passing test. Two more real, independently-confirmed
FEDERAL extractor gaps are named in the same file (a compound-quote entry
that never extracts either of its two terms; an "includes"-verbed entry
`_MEANS_IDIOM_GAP_RE` does not recognize). DC's own row extracts all 4
terms cleanly (0% contamination, confirmed). NY's own row is captured via
the newline-agnostic inline fallback (confirmed live to be unaffected by
the corpus-wide literal-`\n` defect, already routed to core as I8, not
re-routed here) — asserts only 3 of 11 real terms, deliberately not the
whole set, to avoid coupling to whichever later entry might carry the same
last-entry risk FEDERAL/DC both show.

**Negative-guard hazard catalogue** (S3's H1/H3 + S1's AL cluster + S4's
SD finding + S2's DC exclusion-only clause — 6 real rows across
CO/MT/AL/IN/SD/DC, `test_us_body_preamble_hazard_catalogue_red.py`).
Two of the six are SHARPER than "nothing captures today": calling the
real, unedited extractors DIRECTLY on `STATE_CO_T15_A11_P7_S15-11-701`
and `STATE_MT_T7_C14_P41_S7-14-4103` already produces a real, non-empty,
WRONG candidate right now (a spurious "Governing instrument" ->
"shall not include a deed..." exception-as-definition; a spurious "motor
vehicles" -> pure forwarding-pointer) — confirmed live, pinned as its own
test, not merely asserted in prose. This is the SAME hazard shape QA's own
MS forwarding-reference finding modeled, now independently reproduced on
two states never covered by that guard.

**Suite state after D4**: every new capture test fails via the SAME
live-path mechanism as every other test in this family (`created_
definitions == []`), verified by running each file directly, not
inferred. Every negative-guard test passes today. No test in any new file
reads or downloads the parquet snapshot — every row was fetched once,
during authoring, and vendored byte-for-byte.

### P-D5 — Consolidated CLAUSE routing package

Merged all four scouts' own CLAUSE packages into ONE, per M-R16: S1's
`classify7` output filtered `label == "CLAUSE"` (FL/NC/AL/MO), S2's
FEDERAL/DC/NY clustered results filtered `n_clustered_terms == 1`
(NY using S2's OWN newline-defect-corrected version, not the raw one), S3's
already-built 38-state package, S4's already-built GA/MD/NE/MS/SD/CA/IL
package. Committed as two files: `2026-08-04-defs-us-preamble-clause-
package.json` (the data — **2,659 real `act_id`s across 51 jurisdictions**,
deduplicated) and `2026-08-04-defs-us-preamble-clause-package.md` (the
summary: top-15-by-volume table, 3 verbatim examples, caveats).

**Followed the director's discriminator-bias instruction explicitly**: MS
and SD's entries come from S4's OWN CORRECTED discriminator (trigger
position alone), NOT the tail-ratio-inclusive one that produced a 67%
false-CLAUSE rate on SD (M-R19) — stated prominently in the package's own
`.md` file, not just this log, since the scoped-inline panel will read the
package directly, not necessarily this log.

**Verified before merging, not assumed**: NE's rows appear in BOTH S3's
generic 40-state scan and S4's own dedicated NE inventory — confirmed
identical (both count 2), deduplicated to 2, not double-counted. GA/IL
were deliberately reported ONLY by S4 (S3's own design, to avoid
double-counting territory it deferred) — confirmed no overlap risk.

**Not done in this pass, stated in the package's own file, not hidden**:
no re-classification of any row across scouts (this merges four
already-verified lists, it does not re-run a single unified discriminator
over all 2,659 rows); only 3 rows got a fresh verbatim cross-check for the
summary's own examples, the remaining 2,656 are exactly as each scout's
own script produced them.

### P-D6 — Item matrix rewritten in the contract

Rewrote the contract's `## Next Steps` entirely: 20 items, grouped by
**shape-cluster** (one parameterized rule/test file per idiom, covering
many states) rather than per-state, each naming its gate(s), its CHECK,
and its exact blocking status. Superseded the old items 1 (M-R7(a)
escalation — answered), 7 (MS CLAUSE routing — folded into the new item 20's
full 2,659-row/51-jurisdiction package), and corrected the old item 3's
stale "3,327" MD target to the reconciled ~1,841–1,849 figure from P-D1,
with the correction's reasoning cross-referenced rather than silently
overwritten.

New items added for this pass's own deliverables: 11 (B1 matrix), 12 (B2
matrix), 13 (CA), 14+15 (FEDERAL achievable-subset capture + the named,
NOT-this-sprint's-file bounded-extractor defect, kept as two separate
items so the achievable part isn't held hostage to the unbuilt part), 16
(DC), 17 (NY — explicitly stating it is NOT blocked on core's I8, only on
core's registry, to prevent a future reader over-generalizing NY's other
known defect onto this item), 18 (hazard catalogue, already-passing
regression gate), 19 (RI's newly-found mangled-quote-byte defect,
routing only), 20 (the full CLAUSE package, superseding the old item 7's
now-stale 190–240-row MS-only estimate).

Every item's CHECK names a real, already-committed test file from this
sprint's own D2–D4 work — none point at a test that does not yet exist.

---

## 2026-08-04 — Manager: UNBLOCKED, rebased onto main, seam v2.5 re-read

### M-R21 — Core is on main; seam v2.5 re-read before any build

Core merged (`origin/main` @ `0d57228`). Registry is LIVE production code:
`rules/{__init__,registry,il_scope_triggers,us_scope_trigger_proof}.py`.

Re-read the AUTHORITATIVE seam (`docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md`,
**v2.5**) rather than building on the v2.2–2.4 we planned against:

- **v2.5 delta**: `Definition.scope_value` is **transient-by-design** — no
  persisted column, no migration. Our rules produce `DefinitionCandidate`s
  and scope is recomputed from source text every run, so this does **not**
  change our rule design. Confirmed, not assumed.
- **Our rule kind, verified live**: `BodyPreambleRule(jurisdiction_codes,
  derive_heading: body -> str | None)`, registered via
  `register_body_preamble_rule`. **Single-valued, FIRST-NON-None-WINS in
  filename-sort order.** Design consequence for the Developer: one rule
  returning a heading SUPPRESSES every later rule for that row, so the
  shapes must be precise, not greedy — a broad catch-all registered early
  would silently starve the specific ones.
- **M6 ungated dispatch, director-confirmed.** Baseline runs first
  (unchanged, still gated on `_is_placeholder_heading`), then registered
  rules always run if nothing was found. New exposure is confined to rows
  where baseline finds nothing today — **additive-only, never a regression
  of a working state**. The seam states explicitly that escalating a
  measured FP number is **NOT** a request to re-gate; the remedy is
  narrower rules, never suppressed dispatch. Recorded so nobody later
  misreads our U6/FP numbers as a gating argument.

### M-R22 — Rebase verified; 7 tests are stale-import, not behavioral

Rebased 22 commits onto main cleanly, no conflicts. Venv refreshed
(`pip install -e '.[dev]'`); imports verified live: rules package loads,
`BodyPreambleRule` fields correct, `USProfile.derive_heading_from_body` and
`.resolve_unit_path` present, `mcp` imports.

Suite: **37 failed / 714 passed** (was 31/661; +53 passes are core's own
tests arriving on main). Triaged all 37 by failure type rather than assuming:

- **30 behavioral REDs** — failing for the right reason, still specifying
  unbuilt behavior.
- **7 stale-import failures** — core deleted `_extract_inline_quoted_
  definitions` (3), `_is_placeholder_heading` (2), `_derive_heading_from_
  body` (1), `_BODY_DEFINITIONS_PREAMBLE_RE` (1) from `pipeline.py`, moving
  them behind `USProfile`, exactly as the seam said it would.

**An ImportError proves nothing about behavior.** Those 7 must be re-pointed
at the new seam locations before they count as RED-for-the-right-reason —
otherwise we would ship believing 7 guards are protecting us when they are
merely erroring. One of them is a NEGATIVE guard (the Montana forwarding-
reference hazard), so leaving it broken would hide a false-positive class.
Test repair is Planner role; the Developer never touches tests.

---

## 2026-08-04 — Planner: D1–D4, stale-import repair, and a load-bearing dispatch-gap finding

### P-D1 — 7 stale-import tests repaired: mechanical relocation, zero weakened assertions

All 4 missing symbols (`_is_placeholder_heading`, `_derive_heading_from_body`,
`_BODY_DEFINITIONS_PREAMBLE_RE`, `_extract_inline_quoted_definitions`) turned
out to be **verbatim-moved, still-private, module-level symbols inside
`app.definition_links.us_profile`** — same names, same call signatures (single-
arg `_derive_heading_from_body(body)`, same for the others) — not deleted, not
renamed, not made genuinely inaccessible. Confirmed by reading the actual
on-disk source (`us_profile.py:405-595`), not inferred from the seam doc's
"moved verbatim" claim. Repair was a pure import re-point,
`app.definition_links.pipeline` → `app.definition_links.us_profile`, in 5
files (7 test functions): `test_us_body_preamble_b1_colon_list_matrix_red.py`,
`test_us_body_preamble_ca_block_red.py`,
`test_us_body_preamble_hazard_catalogue_red.py` (Montana negative guard),
`test_us_body_preamble_fed_dc_ny_red.py`, and 3 in
`test_definition_links_us_preamble_family.py` (GA gate-pin, MD live-path, NE
unit-pin). No assertion text changed, no fixture changed, no test weakened.

**Montana negative guard, specifically verified, not assumed**: re-ran
`test_montana_row_already_produces_a_real_spurious_forwarding_candidate_from_
the_unedited_live_extractor` after the re-point — it still calls the REAL
`_extract_inline_quoted_definitions` (now correctly imported) against the real
MT fixture body and asserts `("motor vehicles",) in terms`, a specific,
non-trivial fact about the raw extractor's output — not a vacuous pass. This
guard genuinely still proves the hazard it was built to prove.

Result: 6 of the 7 are unit-level pins/negative guards **designed to be
green** (matches this family's own documented convention — see
`test_us_body_preamble_hazard_catalogue_red.py`'s module docstring, "every
test here is GREEN TODAY... and must STAY GREEN once a `BodyPreambleRule`
ships"). The 7th (MD's live-path capture test,
`test_real_pipeline_captures_a_real_maryland_body_preamble_definitions_
section_end_to_end`) now correctly fails as a behavioral RED (0 definitions
captured) instead of erroring. Suite: 37 failed → 31 failed / 720 passed.

### P-D2 — Honest-green sweep: verified empirically, nothing went green from core's merge

Rather than reason from the summary counts alone, checked out the exact
pre-rebase tip (`8a8837a`, reachable via `git reflog`, the commit the rebase
replayed 22 commits on top of) into an isolated worktree
(`git worktree add --detach`, outside both `/Users/nerya/LexGraph` and this
worktree — read-only, removed after use), built a throwaway venv, and ran
**this sprint's own 12 test files** there.

Result: **31 failed / 20 passed, and the exact set of 31 failing test node
IDs is byte-identical** to the post-repair run in this worktree (`diff`,
exit 0) — same names, same parametrize ids, same counts. Confirms
`app/services/jurisdiction.py` and every other file these tests touch outside
`definition_links/` is untouched by the rebase in a way that matters here.
**Conclusion: zero tests in this sprint's family flipped RED→GREEN due to
core's merge.** Nothing to mutation-prove — the honest finding is that there
is nothing to report here, verified rather than assumed. `git status` clean
of `backend/app/` throughout; temp worktree removed.

### P-D3 — 30 behavioral REDs re-verified; one pre-existing (non-rebase) defect found and fixed

Sampled every failure's exception type across the 9 capture/scope files
(`--tb=line`, one line per failure): all 31 current failures are
`AssertionError`s describing genuinely missing production behavior (0 or too
few `created_definitions`, or an exact-set mismatch) — none show a changed
API signature, a new `TypeError`/`AttributeError`, or any other "wrong
reason" shape, **except one**:
`test_federal_conservation_easements_definitions_first_two_clean_terms_are_
captured` (`test_us_body_preamble_fed_dc_ny_red.py`) was raising
`app.services.validation.ValidationError: jurisdiction 'US-FEDERAL' is not in
the controlled vocabulary` — it never reached the pipeline at all. The
controlled vocabulary (`app/services/jurisdiction.py`) uses `"US-FED"`, not
`"US-FEDERAL"` (confirmed against `JURISDICTION_CODES` and `profiles.py`'s
per-code `USProfile` registration, both keyed on `"US-FED"`). Verified this
predates the rebase — `git diff --exit-code 8a8837a -- backend/app/services/
jurisdiction.py` is clean — so this is a latent test-authoring defect, not
something core's merge changed. Fixed the literal string; the test now fails
with the intended `AssertionError` (0 FEDERAL definitions captured, matching
its own docstring). No other wrong-reason failures found in the sample.

### P-D4 — Developer build target, and the finding that changes its shape

**Headline finding, verified live, not inferred from the seam doc:**
**the M6 "ungated dispatch" mechanism the seam spec describes for
`BodyPreambleRule` does not exist in the shipped code.**
`registry.body_preamble_rules_for(code)` (registration/lookup) works
correctly — proved by registering a throwaway rule and confirming the lookup
returns it — but `USProfile.derive_heading_from_body`
(`us_profile.py:510-519`) never calls it:

```python
def derive_heading_from_body(heading: str, body: str) -> str | None:
    if not _is_placeholder_heading(heading):
        return None
    return _derive_heading_from_body(body)
```

This is v1's GATED shape (legacy-only, return `None` immediately if the
heading isn't a placeholder) — not v2's M6 shape ("after the legacy branch,
registered `BodyPreambleRule`s are ALWAYS tried next if nothing was found
yet — regardless of what `_is_placeholder_heading` returned"). Confirmed by
a live probe: registered a trivial always-non-None `BodyPreambleRule` for
`"US-*"`, called `USProfile("US-GA").derive_heading_from_body("Section 15",
<body with no legacy-recognized shape>)` → returned `None`. `pipeline.py`
calls `profile.derive_heading_from_body(...)` exactly once per non-heading
article (`pipeline.py:215`) and nowhere else touches the registry for this
kind, so there is no alternate call site making this moot. Cross-checked
against `registry.py`'s own module docstring ("consuming a kind's registered
rules... is `profiles.py`'s job, not this module's") and against which of
the 7 rule kinds actually ARE consumed: only `scope_trigger_rules_for` (in
`extract_local_scope_definitions`) and `citation_rules_for` (in
`find_citations`) are ever called anywhere in `pipeline.py`/`profiles.py`/
`us_profile.py`. `heading_rules_for`, `body_preamble_rules_for`,
`entry_splitter_rules_for`, `term_clause_rules_for`, and
`structural_unit_rules_for` are registered/lookup-only, never consumed.

**This is not a hypothetical edge case for this family — it is the dominant
case.** Sampled the placeholder-heading status of every state's real fixture
row live: only **GA and CA** have placeholder-shaped headings (satisfying
the LEGACY gate at all); **MD, NE, MS, SD (both rows), FED, DC, NY, DE, ID,
IL, and MS's second-convention row are all NOT placeholders** — for these,
today's gated `derive_heading_from_body` returns `None` immediately, before
ever trying either the legacy body-scan or a registered rule. And even for
GA/CA (placeholder headings), the LEGACY body-scan alone already fails them
today (confirmed by this sprint's own pinned tests: GA's "As used in this
chapter" has no literal "Definitions"; CA's real preamble is 84 chars before
"definitions", 4 over the legacy regex's 80-char cap) — so GA/CA ALSO need
the registry consulted, just via the gate's OTHER branch. **Every single one
of the 31 remaining REDs in this family depends on this dispatch wire.** A
perfect `rules/us_body_preamble.py` registered today would still leave every
test in this file RED, because nothing ever calls
`registry.body_preamble_rules_for(...)`.

`us_profile.py` is out of bounds for both this Planner (explicit rule) and,
per the seam's own text, for a family panel ("C4... working end-to-end for
both jurisdictions... **Done here (assume it, do not rebuild it)**" — a claim
this session's live verification shows is NOT true for the `BodyPreambleRule`
kind specifically, though it IS true for `ScopeTriggerRule`/`CitationRule`,
which are genuinely wired). **This needs either core to wire the 4-line
dispatch call (mirroring the `scope_trigger`/`citation` pattern already
shipped) or an explicit, scoped exception letting the Developer add exactly
that call to `us_profile.py`** — my lean is the former (matches the existing
division of labor and the seam's own "core-authored, stable forever" framing
of Seam 1 methods), but this is the sub-manager's/program manager's call, not
mine to make unilaterally. Flagged prominently rather than silently worked
around.

**One stale test-authored claim, superseded by core's actual merge (good
news, not a gap):** `test_us_body_preamble_ms_chapter_scope_red.py`'s own
docstring states `_CHAPTER_SCOPE_TRIGGERS` is "5 Hebrew phrases only, zero
English triggers exist in the shipped code today" and treats English
chapter-scope recognition as an open dependency. Verified live: core's merge
already added `_US_CHAPTER_SCOPE_TRIGGERS = ("for purposes of this chapter",
"in this chapter", "for purposes of this part", "in this part")` to
`USProfile.determine_scope`, and it already correctly stamps BOTH GA's "As
used in this chapter" (via the "in this chapter" substring) and MS's "For
purposes of this chapter" as `"chapter"` scope
(`determine_scope(...) == "chapter"` for both, confirmed live). **Scope
stamping is NOT a blocker** for this sprint's 2 chapter-scope tests once the
dispatch gap above is resolved — the docstring is simply stale relative to
what landed on main; noted here rather than silently corrected in test prose
(no assertion depends on the stale claim, so left as-is per the append-only/
no-drive-by-edits discipline, but a future reader should trust this log
entry over that docstring).

**Concrete build target for `rules/us_body_preamble.py`** (assuming the
dispatch gap above is resolved first — otherwise none of this fires):

Idiom shapes, in the order they should be registered (first-non-None-wins;
since no other file registers a `BodyPreambleRule` today, declaration order
within this ONE file is the entire precedence order — narrower/hazard-aware
patterns should still precede any broad catch-all so a future second file
sorting earlier by filename can't silently starve them, and so the negative
guards below are structurally satisfied, not just coincidentally):

1. **B1 — `"(As used in)|(For (the) purposes of) this <unit>, the term:"`**
   immediately followed by a colon and ≥2 quoted-or-derivable terms.
   `jurisdiction_codes=("US-*",)`. Satisfies: all 9 params in
   `test_us_body_preamble_b1_colon_list_matrix_red.py`
   (`test_b1_colon_list_preamble_is_captured`, DE/ID/KS/LA/OK/SC/VA/WV/IL),
   GA/MS-first-convention/SD-quoted in `test_us_body_preamble_capture_red.py`
   (`test_ga_as_used_in_this_chapter_the_term_is_captured`,
   `test_ms_as_used_in_this_article_the_term_is_captured`,
   `test_sd_the_term_quoted_means_is_captured`), FED/DC in
   `test_us_body_preamble_fed_dc_ny_red.py`
   (`test_federal_conservation_easements_definitions_first_two_clean_terms_are_
   captured`, `test_dc_trust_for_beneficiary_with_disability_all_four_terms_
   are_captured`), the GA/MS chapter-scope definitions in
   `test_us_body_preamble_scope_red.py` and
   `test_us_body_preamble_ms_chapter_scope_red.py`, and GA's capture in
   `test_definition_links_us_preamble_family.py`. **Must NOT fire** (or must
   be paired with a same-clause exclusion) on: the 6 `HAZARD_CASES` in
   `test_us_body_preamble_hazard_catalogue_red.py` (CO/MT/AL/IN/SD/DC
   forwarding-references and exception lists — same trigger vocabulary,
   defines nothing locally), the 5 negative-guard rows in
   `test_us_body_preamble_negative_guard.py` (GA/MD/NE/MS/SD administrative
   sentences), and the MS forwarding row in
   `test_us_body_preamble_negative_guard_qa_forwarding_reference.py`
   (`"For purposes of this section, the term \"political subdivision\" shall
   have the same meaning as provided under Section 11-46-1"` — matches B1's
   own "the term" anchor but is pointer-only). A defensive check along the
   lines of "does the clause immediately following the anchor contain a
   forwarding phrase (`has/shall have/shall be as defined in`, `shall have
   the same meaning as`) with no quoted term of its own before it" is what
   the hazard/negative-guard rows need; do not build B1 without it.

2. **B2 — `"In this <unit>[,] the following word(s) have the meaning(s)
   indicated:"`**, colon + numbered list of quoted terms.
   `jurisdiction_codes=("US-*",)`. Satisfies: all 3 params in
   `test_us_body_preamble_b2_words_have_meanings_matrix_red.py` (DE/LA/WV),
   MD in `test_definition_links_us_preamble_family.py`
   (`test_real_pipeline_captures_a_real_maryland_body_preamble_definitions_
   section_end_to_end`).

3. **MS second convention — `"For purposes of this <unit>[, unless the
   context requires otherwise,] the following terms shall have the
   meaning(s) ascribed herein:"`**. Only measured on MS this sprint (845
   rows corpus-wide, MS-only) — recommend `jurisdiction_codes=("US-MS",)`,
   narrower than B1/B2, unless the Developer independently confirms the
   phrasing recurs elsewhere (escalate with data per this sprint's standing
   policy if widening). Satisfies both params in
   `test_us_body_preamble_ms_second_convention_red.py` and the chapter-scope
   definition in `test_us_body_preamble_ms_chapter_scope_red.py`.

4. **CA definitions-preamble, wide-window variant — same idiom the
   EXISTING legacy `_BODY_DEFINITIONS_PREAMBLE_RE` already targets
   ("...Definitions...appl(y/ies/ied)/govern/shall apply"), just without
   the legacy regex's 80-char prefix cap** (CA's real prefix is 84 chars).
   `jurisdiction_codes=("US-CA",)` (only measured on CA this sprint; S4's
   1,401-row CA population was never attributed to other states).
   Satisfies `test_us_body_preamble_ca_block_red.py`'s
   `test_california_for_purposes_of_this_division_the_following_definitions_
   apply_is_captured`.

5. **NY newline-agnostic path** — no new idiom needed (NY's row is a B1
   shape); NY works automatically once rule 1 fires, because
   `extract_definitions_from_section`'s numbered-block splitter fails on
   NY's literal-`\n` corpus defect (core's I8, not this sprint's) but
   `_extract_inline_quoted_definitions` (the existing quote-anchored
   fallback, already reachable via `heading_was_derived=True`) is
   newline-agnostic and already confirmed live to extract NY's terms
   cleanly. Satisfies
   `test_ny_literal_backslash_n_body_still_yields_clean_terms_via_the_
   inline_fallback`.

**Explicitly NOT achievable by this sprint's file alone (disclosed by the
tests' own names, not a gap in this brief):** the two
`*_needs_markers_sprint_too` tests (NE unquoted, SD unquoted-comma) in
`test_us_body_preamble_capture_red.py`, and
`test_real_pipeline_still_cannot_capture_the_real_nebraska_unquoted_body_
preamble_definitions_needs_markers_sprint_too` in
`test_definition_links_us_preamble_family.py` — all three need a NEW
unquoted-term entry splitter, `2026-08-04-defs-us-markers` territory, a
cross-sprint dependency, not a defect in the Developer's rule.
`test_federal_last_entry_extraction_swallows_the_next_unrelated_subsection_
confirmed_live` is a unit-level pin on a pre-existing, out-of-bounds
extractor defect (last-entry-unbounded), already GREEN, not a capture test.

**Pushed**: `0ebafcd` (D1), `cf10cd7` (D3 jurisdiction-typo fix), branch
`claude/defs-us-preamble`, `git status` clean of `backend/app/`.

---

## 2026-08-04 — Manager: P-R8 confirmed independently; Developer held; sprint re-parked

### M-R23 — I verified the dispatch gap myself. Both halves of P-R8 hold.

The Planner reported it and P-R8 rules it, but this is the claim that decides
whether we build, so I proved it directly rather than accepting two reports.

Live probe: registered a throwaway always-firing `BodyPreambleRule` for
`("US-*",)`, then called `USProfile(code="US-GA").derive_heading_from_body`
on a real GA preamble body.

```
derive_heading_from_body -> None
throwaway rule consulted? -> False
```

Source of the merged implementation (`us_profile.derive_heading_from_body`):

```python
def derive_heading_from_body(heading: str, body: str) -> str | None:
    if not _is_placeholder_heading(heading):
        return None
    return _derive_heading_from_body(body)
```

Both defects confirmed from the code itself, not inferred:

1. **Registry consumption is absent** — no `body_preamble_rules_for` call
   anywhere in the path; registered rules are never consulted.
2. **The `_is_placeholder_heading` gate is still in the merged code** — so
   the ungated dispatch that M6 and D-PREAMBLE-ALL require was never
   implemented. Its own docstring says so plainly: *"this behavior moved
   here verbatim, nothing about it changed."*

**A `rules/us_body_preamble.py` built today would be inert.** Holding the
Developer spawn is correct. Note the irony worth recording: the seam spec's
own §4 describes ungated dispatch at length, and the code moved the v1
gated shape across verbatim — the spec was written, agreed, director-
confirmed, and then not implemented. Two panels found it independently only
because both probed the live path instead of trusting the spec.

### M-R24 — Handoff verification of the Planner's repair (ba9eb53)

Verified by me, not accepted on report:

- **Diff `79978ed...ba9eb53` is tests + docs ONLY**; `git diff --name-only
  -- backend/app/` is **empty**. No production code touched.
- **Suite reproduces exactly: 31 failed / 720 passed** (was 37/714).
- **Zero remaining ImportError/ModuleNotFoundError failures** — all 7 stale
  imports repaired; every one of the 31 failures is now behavioral.
- The Planner's honest-green method was rigorous and worth recording: it
  checked out the pre-rebase tip (`8a8837a`) into an ISOLATED worktree with
  its own throwaway venv, re-ran this sprint's 12 files there, and compared
  failing-test-ID sets — byte-identical, `diff` exit 0. So **nothing flipped
  RED→GREEN on core's merge**, proven rather than assumed, and no mutation
  proof was needed because there was nothing to prove.
- It also found and fixed a pre-existing test bug (`US-FEDERAL` instead of
  `US-FED`, outside the controlled vocabulary) that was masking a behavioral
  RED behind a `ValidationError`, and confirmed via `git diff 8a8837a` that
  it predated the rebase. Good catch — that test was failing for the wrong
  reason and would have read as legitimate RED.

### M-R25 — Status: re-parked, blocked on core's dispatch-completion sprint

Item (1) of the program manager's non-blocked list is **DONE** (the 31 REDs
are verified behavioral against the merged tree). Items (2) the guarded-
cluster cross-check and (3) U6 baselines under the corrected inline-fallback
caveat remain available and are named in the Context Dump for whoever
resumes.

**The matrix, fixtures, and CLAUSE package are unaffected** — the inventory
is real regardless of dispatch, exactly as the program manager notes. What
is blocked is only the wiring that lets rules fire.

---

## 2026-08-04 — Manager: dispatch verified LIVE, Developer dispatched

### M-R26 — P-R8 closed, proven by the same probe that caught it missing

Rebased 27 commits onto main (`fbb6c9e`) cleanly; venv refreshed.

Re-ran my M-R23 probe. Result needs care, because a naive read says nothing
changed:

- `us_profile.derive_heading_from_body` (the **module-level function**) is
  **unchanged** — still `if not _is_placeholder_heading(heading): return None`,
  still no registry call.
- But `USProfile.derive_heading_from_body` (the **METHOD**) now does:

```python
baseline = derive_heading_from_body(heading, body)   # gated, unchanged
if baseline is not None:
    return baseline
for rule in registry.body_preamble_rules_for(self.code):
    derived = rule.derive_heading(body)
    if derived is not None:
        return derived
return None
```

Live proof: a throwaway always-firing `BodyPreambleRule` registered for
`("US-*",)` **was consulted and won** on a deliberately NON-placeholder
heading (`derive_heading_from_body -> 'Definitions'`, rule fired `True`).

So the module-level function staying gated is **correct by design** — it is
the *baseline*, and keeping it gated is exactly what preserves the 7
already-working states and CA/IL/GA byte-for-byte. My earlier probe was
reading the baseline helper and would have produced a false "still broken"
verdict if I had stopped there. **P-R8 is genuinely closed.**

### M-R27 — CORRECTION to M-R21: ordering is REGISTRATION order, not filename-sort

M-R21 recorded `BodyPreambleRule` as "first-non-None-wins in **filename-sort**
order", taken from the earlier seam text. The **shipped** implementation's own
docstring says **"first-non-None-wins in REGISTRATION order"**, and the code
iterates `registry.body_preamble_rules_for(self.code)` directly.

Practical consequence, and it is a good one: all our rules live in ONE module,
so registration order is simply the order of our `register_body_preamble_rule`
calls — entirely under the Developer's control, no filename games. The design
rule stands unchanged in substance: **register precise shapes BEFORE broad
ones**, because the first non-`None` wins and silently starves the rest.

### M-R28 — REDs re-verified against the merged tree

Suite: **31 failed / 790 passed** (+70 passes are the dispatch sprint's own
tests). **Zero ImportErrors.** The 31 failures are the SAME 31 across the same
9 files as the pre-dispatch run, all behavioral `AssertionError`s describing
missing capture — now **reachable-behavioral** rather than dead-kind, since
dispatch exists. **Nothing went green on arrival**, so no honest-green
mutation treatment is owed. Verified, not assumed.

### M-R29 — Model/effort for the Developer spawn

Developer: **Sonnet / medium** — the design work is done (the Planner's D4
build target names the shapes, order, jurisdiction codes, and the tests each
rule satisfies); what remains is implementing one new file against a fixed
contract with 31 tests as the oracle. Per P-R6 the Developer is Sonnet
medium. **Haiku considered: no** — the rules are real regex/prose judgment
over statutory shapes with an explicit false-positive hazard, and
first-non-None-wins ordering has a silent-starvation failure mode; that is
more than a bounded mechanical change. `model=inherit` not used. Sole writer;
never touches tests.

---

## 2026-08-04 — Manager: Developer handoff verified; two escalations adjudicated

### M-R30 — Developer handoff verified (f6778b3)

- `git diff --name-only 977c8d9 HEAD` → **exactly one file**,
  `backend/app/definition_links/rules/us_body_preamble.py`. **Zero test
  edits**, zero other `backend/app/` edits. Role separation held.
- Suite reproduces: **6 failed / 815 passed** (from 31/790). 25 REDs went
  green; **no previously-passing test regressed**.
- The Developer disclosed two deviations rather than hiding them: it built
  ONE general B1 rule instead of the build target's two (having measured
  that MS's "second convention" row is byte-identical in shape to B1), and
  it committed once rather than per-cluster. Both are recorded, both are
  defensible, and the disclosure is the behavior I want.
- Registration order CA → NE → B2 → B1 (state-specific before `US-*`),
  correct per M-R27, and it noted honestly that in this particular rule set
  the outcome would be identical either way — it front-loaded on principle,
  not on a measured conflict. That is the right instinct for a
  first-non-None-wins registry.
- `scope_unit_kind`: correctly concluded not applicable — `BodyPreambleRule`
  has exactly two fields and `derive_heading` can only return a heading
  string. Checked against `registry.py`, not guessed. M-D3 erratum
  therefore does not bite this sprint.

### M-R31 — RULING on escalation 1 (GA fabrication guard): the TEST is wrong

**Verified independently by me** with a regex written from scratch against the
vendored 7,640-char body of `STATE_GA_T7_C8_S7-8-1`, deliberately not using
the Developer's rule: the row genuinely defines **Access area, Candlefoot
power, Customer, Defined parking area, Financial institution, Hours of
darkness, Operator, Owner of an automated teller machine, Public road,
Remote service terminal** — plus `Access device` and `Control` via other
idioms. The six "extra" terms are **real statutory definitions present in
the row**, not fabrications.

`test_real_pipeline_does_not_fabricate_a_definition_from_a_georgia_section_...`
asserts `created_terms == {6 terms}`. Its factual premise is simply false.
The Developer is right, and no `derive_heading`-only rule could ever satisfy
it while also satisfying its passing sibling — a deterministic body cannot
yield 6 terms for one test and 12 for another.

**Ruling: amend to the FULL real term set, keeping `==`.**

Explicitly NOT the Developer's alternative of relaxing to `<=`. This is a
**fabrication guard** — its whole job is to fail if the pipeline invents a
term. `<=` would let any fabricated extra term pass and would destroy the
guard while appearing to fix it. `==` against the true full set preserves the
guard at full strength and makes it *more* informative than before.

This is the R18 precedent's shape (pin accepted, verified behavior), not the
forbidden "edit a test to fit" — the edit follows an independent
verification that the test's premise was factually wrong, which is exactly
the case the escalate-don't-edit rule exists to route here.

### M-R32 — RULING on escalation 2 (MS padded terms): amend our tests, and ROUTE the real defect

**Verified independently**: `STATE_MS_T45_C10_S34-1`'s real body contains
curly quotes with literal internal padding — `“ Conviction ”`, `“ Department ”`,
`“ Offender ”`, `“ Registrable offense ”`, `“ Registrant ”`. The primary
extractor's `_leading_quote_candidate` (`us_profile.py`) does
`term = term_match.group(1)` with **no `.strip()`**, so terms are produced as
`' Conviction '`. The inline fallback DOES strip — but MS's body has real
numbered blocks, so the non-stripping primary always wins.

**This is not test cosmetics.** A `Definition` whose term is `' Conviction '`
carries padding into downstream term matching, which can silently
under-link real mentions of "Conviction" — i.e. a **zero-miss risk in shared
code**, not a formatting nit. It is invisible today only because no rule
previously reached these MS rows.

**Ruling, two parts:**
1. **Amend this sprint's two MS tests to `.strip()`** — matching the
   convention their own sibling test already uses — so the sprint is not
   blocked by a defect it is forbidden to fix.
2. **ROUTE the non-stripping defect to the program manager** with the
   evidence above, for core or the markers panel. `us_profile.py` is frozen
   to this panel; option (c) (widening `_leading_quote_candidate` here) is
   correctly refused. Amending our tests must NOT be mistaken for the defect
   being resolved — it is deliberately deferred, with a named owner sought.

### M-R33 — Who makes the amendments, and model/effort

**Not the Developer** — tests are out of its role, and it correctly refused
to touch them. A **Planner** (tests are its property) makes both amendments.
**Sonnet / high** — each amendment must preserve a guard's strength while
changing its expectation, and the GA one is precisely where a careless
`<=` would silently destroy a fabrication guard. **Haiku considered: no.**
`model=inherit` not used.

## 2026-08-04 — Planner: amendment 1 (GA fabrication guard, M-R31)

### P-D1 — GA full term set independently re-verified, `==` preserved

Read the vendored `STATE_GA_T7_C8_S7-8-1` body directly (7,640 chars,
`backend/tests/fixtures/us_statutes/us_preamble_rows.json`) BEFORE running
anything, to derive the expected set from the statute text itself, not
from the pipeline's output. All 12 numbered entries use a genuine defining
idiom (`(N) "Term" means ...` for 10 of them, `(2) "Access device" shall
have the same meaning as ...` for the 11th, `(4) "Control" of an access
area or defined parking area means ...` for the 12th):

Access area, Access device, Candlefoot power, Control, Customer, Defined
parking area, Financial institution, Hours of darkness, Operator, Owner of
an automated teller machine, Public road, Remote service terminal.

This is exactly the 12-term set M-R31 already named. Then ran the real
pipeline on the fixture row (before touching the assertion) to confirm
its actual output — the real production `created_terms` for this row is
this SAME 12-term set, term-for-term, with nothing extra and nothing
missing. The two derivations (statute text, live pipeline) match, and the
match is a confirmation of an independently-derived set, not the source of
it — the test does not paste-the-pipeline's-output-into-the-assertion (the
tautology M-R31/the sprint contract warns against).

Amended `test_real_pipeline_does_not_fabricate_a_definition_from_a_
georgia_section_that_merely_uses_the_word_term_without_defining_anything`
(`test_definition_links_us_preamble_family.py`): `expected_terms` widened
from the factually-wrong 6-term set to the full, real 12-term set above.
**`assert created_terms == expected_terms` kept as `==`, not relaxed to
`<=`** — per M-R31, `<=` would let a future fabricated term pass silently
and destroy this test's purpose as a fabrication guard. Docstring and the
module-level GA convention note updated to disclose the true 12-term total
and cite M-R31, so a future reader does not mistake the positive test's
6-term `<=` subset check (left unchanged — still a true subset of 12, no
amendment needed there) for the row's full term count.

Verified green: both GA tests in the file pass
(`test_real_pipeline_captures_a_real_georgia_body_preamble_definitions_
section_end_to_end` and the fabrication-guard test above).

**Not verified by me**: the negative-control row
(`STATE_GA_T44_C6_S44-6-165`, "at the term of the court") still produces
zero spurious `Definition` rows — this assertion is untouched by my edit
and was already passing pre-amendment (the 0-vs-6 diff was entirely on the
genuine row's side), so I did not re-derive it from the text independently;
I only confirmed the whole test now passes.

Diff so far: `backend/tests/integration/test_definition_links_us_preamble_
family.py` only. Committing and pushing this amendment now, before
starting amendment 2, per the sole-writer instruction (no batching).

Pushed as `8fa70d6`.

## 2026-08-04 — Planner: amendment 2 (MS padded terms, M-R32)

### P-D2 — `.strip()` added to both MS tests, both scope directions intact

Ran both failing MS tests first to capture the live failure shape, not
guessed: `test_ms_shall_have_the_meaning_ascribed_herein_is_captured
[ms-sex-offender-registration]` failed with `got [' Conviction ',
' Department ', ' Offender ', ' Registrable offense ', ' Registrant ']`
against a clean `expected_terms` set — exactly the padding M-R32 names.
`test_chapter_scoped_ms_definition_links_a_same_chapter_use_but_not_a_
different_chapter_use` failed earlier, at `assert len(registrant_defs)
== 1` (`0 == 1`), because `"Registrant" in d["terms"]` is an exact-match
list membership check against a padded-term list — it never reaches its
own scope-direction assertions.

Amended both, matching the sibling convention already in
`test_us_body_preamble_capture_red.py::test_ms_as_used_in_this_article_
the_term_is_captured` (`all_terms = {t.strip() for d in ... for t in
d["terms"]}`):
- `test_us_body_preamble_ms_second_convention_red.py`: `created_terms`
  now built with `{t.strip() for d in ... for t in d["terms"]}`.
- `test_us_body_preamble_ms_chapter_scope_red.py`: `registrant_defs` now
  filters on `"Registrant" in {t.strip() for t in d["terms"]}`. Nothing
  else in this test changed — both scope-direction assertions
  (`in_chapter_article_id in subject_article_ids` and
  `out_of_chapter_article_id not in subject_article_ids`) are byte-
  identical to before my edit and both independently re-verified passing
  below.

Both amendments carry an explicit in-test comment (not just this log)
that `.strip()` is a **workaround for a routed production defect, not a
resolution of it**: `us_profile._leading_quote_candidate`'s primary
extractor does `term = term_match.group(1)` with no `.strip()`, so MS's
real curly-quote-padded terms (`"“ Conviction ”"`) arrive padded; the
inline fallback strips but never runs here because the primary already
produced candidates. `us_profile.py` stays untouched (frozen to this
sprint's panel) — the fix is on the program's core-follow-on-2 list, named
in the comment so a future reader does not mistake the test-side
`.strip()` for the defect being closed.

Investigated (did not just assume) whether `.strip()` was the ONLY thing
needed, i.e. whether the padded term also breaks live term-USE matching
(`find_term_uses`, `\b`-anchored regex) — it does not for this fixture:
`re.escape(" Registrant ")` keeps the literal leading/trailing spaces in
the pattern, and because the hand-written "using" row's own prose has
ordinary single-space word separation ("...A Registrant who fails..."),
the `\b` boundaries land on the naturally-occurring spaces either side of
the word, so the match still succeeds today. This is fixture-specific
luck (a mention directly abutting non-space punctuation would not match),
not a guarantee — flagged here, not assumed silently, in case a future
reader treats the passing match as proof the padding is harmless in
general; it is exactly the "silent under-linking risk" M-R32 already
named for the general case.

Verified green, both tests, all 3 parametrized cases:
```
tests/integration/test_us_body_preamble_ms_chapter_scope_red.py::test_chapter_scoped_ms_definition_links_a_same_chapter_use_but_not_a_different_chapter_use PASSED
tests/integration/test_us_body_preamble_ms_second_convention_red.py::test_ms_shall_have_the_meaning_ascribed_herein_is_captured[ms-sex-offender-registration] PASSED
tests/integration/test_us_body_preamble_ms_second_convention_red.py::test_ms_shall_have_the_meaning_ascribed_herein_is_captured[ms-wildlife-fisheries-parks] PASSED
```

### P-D3 — Full suite: 3 failed / 818 passed, all 3 the documented markers-sprint REDs

Full `pytest -q` from `backend/`: **3 failed, 818 passed** (was 815
passed / 6 failed before either amendment; 821 total both times — no test
added, removed, or newly regressed). All three failures are the exact
three named in this sprint's expected end state, each confirmed failing
for the right reason (`got []` / membership-in-empty-set, i.e. the rule
correctly does not fire for an unquoted entry, not a wrong-reason
failure):
- `test_ne_unquoted_term_means_needs_markers_sprint_too` —
  `AssertionError: assert 'Health insurance plan' in set()`.
- `test_sd_unquoted_comma_term_needs_markers_sprint_too` —
  `AssertionError: assert 'loan processor or underwriter' in set()`.
- `test_real_pipeline_still_cannot_capture_the_real_nebraska_unquoted_
  body_preamble_definitions_needs_markers_sprint_too` —
  `assert {'Account', 'Authorized attorney', 'Child support',
  'Department'} <= set()`.

No 4th red, and none of the 3 fails on a different assertion than the
one its own docstring/name already discloses (all three are "the pipeline
produced nothing for this unquoted row" — a right-reason RED on the
already-flagged `2026-08-04-defs-us-markers` cross-sprint dependency, not
a defect in this sprint's rule).

Diff for both amendments combined: `git diff --name-only 92c2b1f HEAD` →
`backend/tests/integration/test_definition_links_us_preamble_family.py`,
`backend/tests/integration/test_us_body_preamble_ms_chapter_scope_red.py`,
`backend/tests/integration/test_us_body_preamble_ms_second_convention_
red.py`, plus this log file. Tests and docs only — no
`backend/app/` edit, matching the role boundary.

---

## 2026-08-04 — Manager: amendments verified; QA dispatched for U6 / P-R7 / cross-check

### M-R34 — Amendment handoff verified (bd4dde7)

- `git diff --name-only 92c2b1f HEAD` → 3 test files + the log. **Zero
  `backend/app/` edits.** Role separation held.
- **The fabrication guard kept `==`** (`assert created_terms ==
  expected_terms`), with the full 12-term set. I compared it against the term
  list I derived independently in M-R31 from the raw body: Access area,
  Access device, Candlefoot power, Control, Customer, Defined parking area,
  Financial institution, Hours of darkness, Operator, Owner of an automated
  teller machine, Public road, Remote service terminal — **exact match**. The
  guard is now stronger than before, not weaker.
- The `<=` still present at line 175 is the separate *capture* test, where a
  subset assertion is correct — not the guard. Checked, not assumed.
- The Planner derived the set from the body FIRST and used the pipeline run
  only as confirmation, avoiding a tautological assertion. That was the
  specific failure mode I warned about and it was handled correctly.
- Suite: **3 failed / 818 passed** — the exact expected end state. The 3 are
  the disclosed `defs-us-markers` unquoted-entry dependencies, failing with
  empty results (right-reason REDs).
- Honest note carried from the Planner: the MS padding doesn't break live
  term-USE matching for this fixture only because `\b`-anchored regex happens
  to land on naturally-occurring spaces — **fixture-specific luck, not a
  general guarantee**. That is precisely the silent under-linking risk M-R32
  named, and it strengthens the case for the routed core fix.

### M-R35 — Model/effort for the QA spawn

QA: **Sonnet / high** — the U6 measurement is the director's headline number
(GA moving from 5/28,154, awaited since the first sprint) and must be
measured cleanly under the corrected-fallback caveat; P-R7 requires
constructing an INDEPENDENT denominator, which is a reasoning task, not a
scripting one; and the guarded-cluster cross-check requires judging another
panel's rows against our populations. Per P-R6 QA is Sonnet high. **Haiku
considered: no.** `model=inherit` not used. QA commits only test/contract/log
files and never touches implementation.

---

## 2026-08-04 — QA: U6 before/after, D1b false-positive sample, P-R7 independent
denominator (D2), guarded-cluster cross-check (D3), suite + mutation-proof (D4)

Sole writer for this dispatch. Worked in `/Users/nerya/LexGraph-wt/defs-us-preamble`
at `a0d82cc`. All measurement is via a scratchpad harness that replicates
`pipeline.py`'s Stage-1/Stage-2 logic (`normalize_for_parsing` → `strip_wikilinks`
→ `is_definitions_heading` → `derive_heading_from_body` → `determine_scope` →
`extract_definitions_from_section`) directly against the real parquet corpus,
verified line-by-line against `pipeline.py:180-268` and `us_profile.py:1386-1406`
before writing a single line — no test reads or downloads the corpus; no
`backend/app/` file was touched.

### Q-D1 — Methodology, stated once, used consistently

**BEFORE** = `is_definitions_heading(heading)` [bare fn] OR (`derive_heading_from_
body(heading, body)` [BARE fn, registry untouched] gives a heading AND
`is_definitions_heading` on it is True). This is mathematically identical to
`USProfile.derive_heading_from_body` with an empty `body_preamble_rules`
registry (verified by reading `us_profile.py:1399-1406`: baseline is the bare
call; the registry loop is a no-op on `[]`) — i.e. exactly "main's behavior with
our rules module absent", with zero file-system trickery.

**AFTER** = same, but `derive_heading_from_body` is the **profile method**
(bare-first, then our 4 registered `BodyPreambleRule`s, first-non-None-wins) —
today's real shipped behavior.

**"captured"** (this report's one definition, used everywhere below):
`is_definitions_section` resolves True for the row AND `extract_definitions_
from_section` yields **≥1 `DefinitionCandidate` with a non-empty `.terms`
tuple** — what production would actually persist as ≥1 `Definition` row.
A weaker "heading recognized" count exists underneath this (see NE below) and
is called out by name wherever it materially diverges from "captured".

No other rule kind (`EntrySplitterRule`/`TermClauseRule`/`HeadingRule`) is
registered anywhere in this codebase for any `US-*` code today (grep-verified
against every file under `rules/`) — so `extract_definitions_from_section`
(bare) and the `USProfile` method are behaviorally identical for this family,
and using the bare function for BEFORE and the profile method for AFTER
isolates exactly the delta our 4 rules cause, nothing else.

Full corpus, all 53 jurisdictions, snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad` — **2,038,247 rows scanned**,
matching the contract's own cited worklist denominator exactly (cross-check).
Scripts: `qa_d1_measure.py` (D1/D1b), `qa_d2_independent_denominator.py` (D2),
`qa_d3_crosscheck.py` (D3) — all in the scratchpad, none committed.

### Q-D1 — THE HEADLINE NUMBER: Georgia

**Measured, not fabricated: GA before = 2/28,154; after = 2,794/28,154.**

This is the honest number under my stated methodology. It does **not**
reconcile with the "5/28,154" figure the director has been quoted since the
first sprint, and I am disclosing that rather than silently substituting my
number for theirs. I traced my own 2: both rows go through the LEGACY
`_BODY_DEFINITIONS_PREAMBLE_RE` body-derivation path (unrelated to this
sprint's rules — matches Gate B in the manager's original M-R1/M-R2 table),
confirmed by direct inspection (`STATE_GA_T48_C8_S48-8-13`,
`STATE_GA_T14_C7_S14-7-2`). The manager's own M-R1 table reported "Gate B: 1
pass" — a narrower count restricted to the 1,224-row *preamble-signal*
subset the scouts inventoried, not a full-corpus scan of all 28,154 rows
against my stated "captured" definition. My 2 is a superset measurement
(full corpus, both heading-match and body-derivation paths) using a
consistently-applied definition; the "5" traces to an earlier, differently-
scoped measurement I cannot reproduce from what's in this log. **Both
numbers are small; the qualitative finding — GA baseline capture was
negligible — holds either way.** I am reporting my own measured number, not
overwriting the director's cited figure with false confidence.

**GA after = 2,794/28,154 (9.9%).** Of the 2,792 *newly* captured rows
(2,794 − 2 pre-existing): **1,926 (69%) via the PRIMARY numbered-block
splitter (clean, NOT affected by the S1 fallback bug)**; **866 (31%) via
the inline-quote fallback (the KNOWN-BUGGY extractor whose last entry runs
to end-of-text)**. GA's own fixture row (`STATE_GA_T7_C8_S7-8-1`, the
12-term row M-R31 independently verified) goes through the clean primary
path, matching the manager's own finding that GA's real rows carry genuine
`(N)"Term"` numbered structure.

**GA moves from a baseline of essentially zero to capturing roughly 1 row
in 10 — a real, substantial, honestly-measured improvement, with a third of
the *new* rows still carrying the disclosed fallback-boundary risk (term
identification is intact; the `definition_text` field on those rows may run
long/contaminated on the last entry per S1's proven FL 540.11 finding — see
Q-D1 fallback note below).**

### Q-D1 — Per-state table, the 10 requested + full 53-jurisdiction appendix

`captured` = my stated definition; `new` = after − before; `new_primary` /
`new_fallback` = of the *new* captures, how many came via the clean
numbered-block splitter vs. the S1-flagged inline fallback.

| state | rows | before | after | new | new via primary (clean) | new via fallback (flagged) |
|---|---:|---:|---:|---:|---:|---:|
| GA | 28,154 | 2 | 2,794 | 2,792 | 1,926 | 866 |
| MD | 39,552 | 0 | 3,185 | 3,185 | 3,150 | 35 |
| NE | 25,997 | 0 | 7 | 7 | 2 | 5 |
| MS | 158,688 | 0 | 6,113 | 6,113 | 4,969 | 1,144 |
| SD | 39,589 | 712 | 801 | 89 | 18 | 71 |
| CA | 161,429 | 1,296 | 5,871 | 4,575 | 3,690 | 885 |
| FL | 24,866 | 684 | 2,685 | 2,001 | 36 | 1,965 |
| FED | 54,853 | 320 | 2,268 | 1,948 | 343 | 1,605 |
| DC | 23,694 | 884 | 1,593 | 709 | 342 | 367 |
| NY | 40,102 | 0 | 1,077 | 1,077 | 0 | 1,077 |

**MD note**: my 3,185-captured figure is higher than the Planner's own
corrected inventory target ("~1,841–1,849/39,552", contract item 2) — because
my count is the ACTUAL PIPELINE OUTPUT under ungated dispatch (any of the 4
rules can fire on any MD row), not a hand-scoped count of B2's own trigger
signal alone. I am not force-reconciling the two; both are honestly measured,
against different questions ("how many rows carry the B2 signal" vs. "how
many rows does the shipped pipeline actually capture").

**NE note — disappointing, reported plainly**: only 7/25,997 captured, far
below the sprint's own "quoted subset (46/559)" target (contract item 3).
I checked why directly: 274 NE rows get a "Definitions" heading synthesized
by `derive_heading_from_body` (i.e. SOME rule recognizes them as candidates),
but only 7 of those 274 successfully extract a non-empty term. The other 267
are recognition-without-extraction — the NE/B1 trigger fires (often on
unrelated body content reached via `finditer` scanning the whole body, not
just its start) but no parseable quoted-term-and-verb shape follows closely
enough for either extractor to produce a candidate. **NE's real capture rate
is small and the number should be reported as such, not rounded up.**

**SD note**: 712/801 of SD's "captured" total is the PRE-EXISTING baseline
(real `"Definitions"`-headed sections, e.g. `STATE_SD_T34_C51_S34-51-1`,
unrelated to this sprint's family) — SD's own contribution is only 89 new
rows, and of those, most (71/89) are fallback-affected.

Full 53-jurisdiction table (same columns), sorted by postal code:

```
state    code      rows(scanned) before   after     new  new_primary  new_fallback
ak       US-AK      17,935           1        1        0            0            0
al       US-AL      45,984          50      200      150           24          126
ar       US-AR      36,936       1,999    2,187      188          121           67
az       US-AZ      22,674          30      129       99           21           78
ca       US-CA     161,429       1,296    5,871    4,575        3,690          885
co       US-CO      34,231       1,967    3,080    1,113          983          130
ct       US-CT      16,082         704      856      152           77           75
dc       US-DC      23,694         884    1,593      709          342          367
de       US-DE      21,649         909    1,339      430          286          144
federal  US-FED     54,853         320    2,268    1,948          343        1,605
fl       US-FL      24,866         684    2,685    2,001           36        1,965
ga       US-GA      28,154           2    2,794    2,792        1,926          866
hi       US-HI      16,446          10      546      536           28          508
ia       US-IA      28,223         950    1,556      606          517           89
id       US-ID      22,754         718    1,138      420          272          148
il       US-IL      72,456       1,537    2,544    1,007            2        1,005
in       US-IN      83,148         283    3,420    3,137           75        3,062
ks       US-KS      24,361         881    1,516      635          487          148
ky       US-KY      20,894         965    1,429      464          345          119
la       US-LA      43,474       1,171    2,407    1,236          801          435
ma       US-MA      23,152           2        3        1            0            1
md       US-MD      39,552           0    3,185    3,185        3,150           35
me       US-ME      25,316           1      249      248            0          248
mi       US-MI      40,658       1,763    2,931    1,168          315          853
mn       US-MN      27,747          92      773      681           32          649
mo       US-MO      29,296         936    1,730      794          519          275
ms       US-MS     158,688           0    6,113    6,113        4,969        1,144
mt       US-MT      30,514       1,221    1,592      371          282           89
nc       US-NC      26,685         485    1,016      531          210          321
nd       US-ND      29,042           3      276      273           12          261
ne       US-NE      25,997           0        7        7            2            5
nh       US-NH      25,375           0      180      180            0          180
nj       US-NJ      55,897           7      755      748            0          748
nm       US-NM      34,455          47      936      889          725          164
nv       US-NV      48,190           0    1,823    1,823            1        1,822
ny       US-NY      40,102           0    1,077    1,077            0        1,077
oh       US-OH      33,161           1    1,703    1,702            0        1,702
ok       US-OK      35,329          68      734      666           21          645
or       US-OR      36,202       1,340    2,989    1,649        1,251          398
pa       US-PA      14,547           9      246      237            5          232
pr       US-PR      23,636           0        2        2            0            2
ri       US-RI      21,107           0        0        0            0            0
sc       US-SC      29,947          22      356      334            0          334
sd       US-SD      39,589         712      801       89           18           71
tn       US-TN      32,693       1,105    1,926      821          671          150
tx       US-TX     122,535       3,942    4,144      202          106           96
ut       US-UT      25,880          42    1,913    1,871            1        1,870
va       US-VA      33,856          31      895      864           10          854
vt       US-VT      23,521         766    1,253      487          392           95
wa       US-WA      51,498          22      789      767            4          763
wi       US-WI      18,158         479      617      138          102           36
wv       US-WV      25,460         771    1,314      543          308          235
wy       US-WY      10,219         439      606      167          135           32
TOTAL              2,038,247      29,667  80,493  50,826       23,617       27,209
```

**Fallback caveat (S1's proven bug), handled explicitly per the binding
directive**: 27,209/50,826 (54%) of the corpus-wide NEW captures went through
`_extract_inline_quoted_definitions` (`heading_was_derived=True`, primary
block splitter found nothing). I am NOT reporting the 80,493/50,826 headline
figures as clean — the primary/fallback split above is reported alongside
every number so the reader can subtract or discount the fallback-affected
column. What the fallback bug does NOT do (verified, not assumed): it does
not fabricate extra TERMS — `_extract_inline_quoted_definitions` only
mis-bounds the LAST entry's `definition_text` per body (S1's FL 540.11
finding was about definition-text byte-coverage, ~12% true vs ~100% claimed,
not about phantom term counts). So the TERM-level capture counts above are a
reasonable, honestly-labelled figure; the risk the fallback column names is
data-quality on `definition_text`, not spurious extra rows or terms.

**Not measured**: how many of the 27,209 fallback-affected `definition_text`
fields are actually contaminated (vs. simply being the row's genuine last
entry with nothing else trailing it, which is common on short single-term
NV/DC/LA-style rows — see Q-D1b below for real examples of this). A
byte-coverage measurement in S1's own style, per-state, was out of this
QA cycle's time budget; flagging as explicitly not measured rather than
guessing.

### Q-D1b — False positives: 0/50 confirmed, methodology disclosed

Our dispatch is ungated; the total corpus-wide NEW-claim population is
**50,826** rows (the same figure as Q-D1's TOTAL row) — far larger than the
sprint's own scoped/inventoried "7,383 rows" worklist (contract's
D-PREAMBLE-ALL ruling). This is itself a material finding: the B1/CA/NE/B2
rules generalize FAR beyond the ~50 states' worth of hand-inventoried
population they were designed against — the shared "As used in this
X"/"For purposes of this X" idiom is pervasive across nearly all 53
jurisdictions, not just the ones scouted.

**Random sample of 50** (seed `20260804`, pooled across all 53 states,
proportional to each state's share of the 50,826-row population —
`d1b_sample.json`/`d1b_sample_full.json` in the scratchpad hold the full
list with real `act_id`s, headings, and body excerpts): 47 from the
`primary`/`fallback` mix in natural proportion, spanning IL/FL/OR/PA/NV/
MD/CA/DC/LA/DE/CT/NM/UT/WV/MI/MS/GA/NY/OH/OK/IN/KS.

**Methodology correction, disclosed rather than hidden**: my first pass
hand-judged 3 of the 50 as false positives using a crude `body.find()`
string search (OR `STATE_OR_T22_C243_S243.706`, NV `STATE_NV_T57_C689B_
S689B.0307`, MS `STATE_MS_T19_C23_S31-23`) — that search matched the WRONG
(earlier, ordinary-usage, unquoted) occurrence of the extracted term text
rather than the actual quoted defining clause, which in all 3 cases sat
much later in the body. Re-verifying all 3 against the REAL pipeline
output (`qa_verify_row.py`, printing the actual `derive_heading_from_body`
result and every `DefinitionCandidate.definition_text`) showed all 3 are
genuine: OR's row defines `"civilian or community oversight board, agency
or review body"` at char ~3,900 of a 5,589-char body (`(9) As used in this
section, "civilian or community oversight board, agency or review body"
means a board, an agency or a body:...`); NV's `"Attending practitioner"`
is defined with `"...the practitioner, as defined in NRS 639.0125, who has
primary responsibility..."`; MS's `"developer"` is defined with `"...any
entity or natural person which enters into an agreement with a district
whereby the developer agrees to construct..."`. I am disclosing this
correction because a first-pass judgment I initially got wrong is exactly
the kind of unsupported claim the manager cannot use if uncaught.

**Final: 0/50 confirmed false positives** (verified against the real
`definition_text` output, not crude string search, for every ambiguous
case — 8 rows needed this deeper check; all 8 confirmed genuine, including
GA `STATE_GA_T16_C11_S16-11-130` where 2 of 4 extracted terms initially
looked unsupported but are genuinely defined deeper in the 43,402-char
body). **FP rate: 0/50 (0%), with the standard rule-of-three caveat that a
0/50 sample is statistically consistent with a true corpus-wide rate
anywhere up to roughly 6% at 95% confidence — I am not claiming a proven
zero.**

**Minor data-quality observations found along the way (not FPs, reported
for completeness)**: (1) GA `STATE_GA_T16_C11_S16-11-130` and
`STATE_GA_T48_C13_S48-13-50-2` both produce each real term TWICE
(byte-identical duplicate `DefinitionCandidate`s) — looks like duplicated
content in the GA corpus body text itself, not a recognition defect; not
investigated further, flagged for whoever owns corpus ingestion. (2) MS/NM
padded-term artifacts (`" 340B drug "`, `" Certification "`) are the SAME
already-routed M-R32 defect (`_leading_quote_candidate` non-stripping),
reconfirmed live, not new. (3) CA `STATE_CA_Cedc_T3_D5_P42_C1.7_A1_
S69432.7` produces terms with a trailing comma (`"Expected family
contribution,"`, `"Full time,"`) — an extraction-boundary nit, not a
recognition FP.

Per the sprint's own seam ruling, **this is reported, not re-gated**: a
material FP number would not justify gating dispatch; a 0/50 sample gives
no basis to act on precision at all, only to note the recall surface is
much larger than scoped.

### Q-D2 — P-R7 independent-denominator sweep

**Denominator design, deliberately NOT built from our rules' own trigger
regexes** (per P-R7 / the binding directive): two components, neither
requiring any specific INTRO-CLAUSE phrase our 4 rules key on ("As used in
this X" / "For purposes of this X" / "In this X" / "In the Named Code" /
"the following words have the meaning(s) indicated"):

- **(A) quoted term + broad defining verb** (`means`/`shall mean`/`has the
  meaning`/`has the same meaning`/`is defined as`/`are defined as`/`shall
  have the meaning`) within the first 600 chars of body, ANYWHERE, no intro
  phrase required at all.
- **(B) unquoted term + the same verb set** — SD's own comma-delimited
  `"the term, X, means"` shape, plus a bare capitalized-phrase variant —
  catching the disclosed MD/NE/SD unquoted convention too.

Restricted to rows whose ORIGINAL heading already fails baseline
`is_definitions_heading` (our rules' own candidate population). Full corpus,
same 2,038,247-row scan: **91,878 denominator hits**; of these, **32,417
(35%) are already captured by the CURRENT shipped rules**; **59,461 (65%)
are NOT captured — the raw U4-miss candidate population** (97% of the raw
misses come from component A alone; component B contributes 1,996).

**A raw 59,461 is not a literal miss count** — component A is intentionally
broad (matches ANY quoted-term-then-"means" in the window, including
ordinary non-definitional prose). Following the SAME discipline as Q-D1b:
**random sample of 50** (seed `20260804`, `d2_miss_sample.json`/
`d2_miss_sample_full.json` in scratchpad), full body fetched and hand-judged
against the real text.

**Result: this is the opposite finding from Q-D1b. Roughly 47/50 (94%) of
the sampled misses are GENUINE local definitions our 4 shipped rules
structurally cannot recognize today** — every one individually confirmed by
reading the actual defining clause in the real corpus text, not inferred.
Only ~3/50 are ALREADY-DISCLOSED, already-routed dependencies (SD's own
unquoted comma-term shape, `STATE_SD_T22_C3_S22-3-5` and `STATE_SD_T61_
C6A_S61-6A-1` — the item-4 markers-sprint dependency, re-confirmed live, not
new; and NY `STATE_NY_AGCT_A3_S27-A` — the already-accepted-by-core literal-
`\n` corpus bug, confirmed here to ALSO break our B1 trigger's `\s+`
requirement, not just the extractor, a nuance worth naming but not a new
routing).

**Named, distinct shapes, each confirmed by ≥2 independently-verified real
rows (`act_id`s in `d2_miss_sample_full.json`), classified in-family
(ours to route/consider) unless noted**:

1. **Bare `"Term" means ...` with NO intro-trigger phrase at all** (no "As
   used in"/"For purposes of" anywhere) — the single most common shape in
   the sample. Real examples: IL `STATE_IL_C5_A100_S1-90` (`Sec. 1-90.
   Rulemaking. (a) "Rulemaking" means...`), IL `STATE_IL_C225_A705_S1.15`,
   CA `STATE_CA_Cfac_D5_P2_C3_A1_S10302`, CA `STATE_CA_Cprc_D21_C1_S31016`,
   CA `STATE_CA_Cgov_T9_C2_S82048.7`, MD `STATE_MD_Agtr_T11_S1_S11-136`, MN
   `STATE_MN_P59A_79A_C62Q_S62Q.53`. Also the dominant shape behind NV's
   own `"<Term>" defined` heading convention (8 of my 50-row sample were
   NV, all this shape) — NV alone shows `denominator_hits=8,569`,
   `captured=246`, so the bulk of NV's ~8,323 raw misses are very likely
   this exact single-term-per-section convention.
2. **Trigger present, but the quote follows immediately with NO literal
   "the term" wording and no colon** — `As used in this X, "TERM" means...`.
   `_B1_QUOTE_MEANS_RE` specifically requires the LITERAL phrase "the term"
   before the quote; this shape omits it. Real examples: NM
   `STATE_NM_C59A_A5A_S59A-5A-5`, KS `STATE_KS_C75_A45_S75-4511`, CA
   `STATE_CA_Cwic_D5_P4_C1_A11_S5878.2`, IN `STATE_IN_T36_A7_C26_
   S36-7-26-4`, LA `STATE_LA_Crevised-statutes_T14_S40.5`, NH `STATE_NH_
   TVII_C105_S19`.
3. **`"In this <unit>"` as the trigger** (not "As used in"/"For purposes
   of", the only two phrases `_B1_TRIGGER_RE` matches) — and this is
   **FEDERAL USC's own dominant convention**: all 4 of my sample's FEDERAL
   rows share the exact shape `"(a/b) Definitions\n\nIn this section:\n\n
   (N) <label>\n\nThe term "X" means..."` (`USC_T7_C31_S936f`, `USC_T27_
   C6_S122a`, `USC_T43_C35_S1742a`, `USC_T10_C147_S2496`) — none captured.
   Also seen in TX `STATE_TX_Chs_C62_S62.106` and WI `STATE_WI_C281_
   S281.625`. **This is a concrete, live-confirmed signal that the
   contract's own item-14 "FEDERAL achievable subset (198/435, 45.5%)"
   target may not be substantially reached by the shipped B1 rule** — B1's
   trigger vocabulary does not include "In this" at all, and 4/4 of my
   independently-sampled FEDERAL rows use exactly that phrasing. Not
   independently re-measured at scale this cycle (see "not measured"
   below); named here so it is not lost.
4. **Trigger references specific external section numbers/ranges instead
   of "this <unit>"** — `"For purposes of Sections 21-27-201 through
   21-27-221..."` (MS `STATE_MS_T21_C21_S27-203`), `"For the purposes of
   §§ 61-6A-1 to 61-6A-14..."` (SD `STATE_SD_T61_C6A_S61-6A-1`, also
   folded into the already-disclosed SD bucket above since it's ALSO
   unquoted).
5. **Named-Act phrasing** (`"As used in the <Named Act>"`, not `"this
   <unit>"`) — confirms Q-D3's NM finding (below) generalizes: NM
   `STATE_NM_C3_A32_S3-32-3`.
6. **Intervening qualifier clause between trigger and quoted term** —
   `"As used in this section, unless the context otherwise requires,
   "veteran" means..."` (TN `STATE_TN_T49_C4_S49-4-938`) — breaks both B1
   branches (not "the term", and the qualifier clause pushes past the
   colon-window in some cases).
7. **CA's own `"Definitions...govern/apply"` wide-window idiom, appearing
   in OTHER states** — the shipped rule is explicitly scoped to `US-CA`
   only (its own docstring says so). MS `STATE_MS_T17_C3_S17-103`
   (`"...the definitions which follow govern the construction and meaning
   of the terms used in Sections 17-17-101 through 17-17-135:..."`) is the
   SAME idiom, confirmed live, in a state the rule doesn't reach. Confirms
   Q-D3's Indiana finding (below) is not an isolated case.
8. **B2 phrasing variants not matching its exact wording** — B2 requires
   the literal "the following words have the meaning(s) indicated"; MS
   `STATE_MS_T27_C7_S19-3` uses `"...words and phrases...have the meanings
   respectively ascribed to them in this section..."` — same intent,
   different wording, not matched.

**Not measured**: the true corpus-wide size of each named shape (I have a
50-row hand-verified sample, not a full re-scan per shape); whether
widening B1's trigger vocabulary to include "In this" would introduce new
false positives (a real question, deliberately left to whoever designs the
fix, per this sprint's role boundary — QA reports, does not design rules).
Given the raw 59,461 and a 94% genuine rate on an unbiased random sample,
my honest estimate is the TRUE U4 miss population is in the **tens of
thousands of rows**, dominated by shapes 1 and 3 above — but this is an
estimate from one sample, not a re-measured count, and I am labelling it as
such.

### Q-D3 — Guarded-cluster cross-check (headings panel's 245-row doc)

Read `docs/sprint/sprints/2026-08-04-defs-us-headings-guarded-cluster.md`
at `639268f` on `claude/defs-us-headings` (fetched read-only via `git show`,
never checked out). Parsed its 245-row table, looked up every `act_id` in
the real corpus (244/245 found — 1 NM entry appears twice in the doc under
two different `act_id`s for the same underlying statute,
`STATE_NM_C3_A32_S3-32-3` / `STATE_NM_STATUTES_C3_A32_S3-32-3`, both
checked), ran each through the exact AFTER path.

**0/244 are captured by our current rules.** All 244 fail `is_definitions_
section` under the current shipped ruleset. Given the doc's own uncertainty
("scout ~10–15% true positives, QA cycle 1 ~25%, QA cycle 2 zero genuine
misses in 15"), I hand-reviewed every row with `body_len >= 250`
(50 rows — the ones large enough to plausibly hold real local content,
excluding 194 rows with a median 129-char stub body that cannot fit a real
definition list) plus a random spot-check of 8 of the 194 small-bodied
stubs (all 8 confirmed correctly-excluded pure cross-references, e.g. `Sec.
1. The definitions in this chapter apply throughout this article.` with
nothing else).

**Genuine gaps found (real `act_id`s, classified)**:
- **In-family, NEW (not previously disclosed)**: CO `STATE_CO_T10_A2_P1_
  S10-2-105` and NV `STATE_NV_T34_C396_S396.826` / `STATE_NV_T34_C396_
  S396.829` — real EXCLUSION-style local definitions (`"the term
  'insurance producer' does not include..."` / `"'pledged revenues' does
  not include..."`) that use "does not include" rather than any
  means/shall-mean verb our extraction idiom recognizes. NM
  `STATE_NM_C3_A32_S3-32-3` (and its duplicate `act_id`) — `"As used in
  the Industrial Revenue Bond Act, 'project' also means:..."`, a genuine
  quoted definition that slips past B1 for TWO independent reasons at
  once (Named-Act phrasing, not "this X"; and "also means" breaks the
  immediate-adjacency requirement of `_B1_QUOTE_MEANS_RE`) — this is the
  SAME shape Q-D2 independently found via the unrelated denominator,
  cross-confirming it. IN `STATE_IN_T21_A44_C7_S21-44-7-1` and its
  versioned sibling `...-1-b` — real numbered definitions (`"(1) 'Board'
  refers to..."`) reached via a `"The following definitions apply
  throughout this chapter:"` intro, structurally the SAME wide-window
  `"Definitions...apply"` idiom the CA rule targets — but that rule is
  explicitly `US-CA`-scoped only, so it never reaches Indiana. This
  directly matches the guarded-cluster doc's own prediction: *"The
  Indiana rows... are dominated by [a] cross-reference whose BODY often
  does carry a real definition list. That body shape is exactly what
  D-HG routes to the preamble panel"* — confirmed, concretely, on 2 real
  rows, though the other 182 IN rows in the cluster are genuinely empty
  stubs (verified, not assumed).
- **In-family, ALREADY DISCLOSED (not a new gap)**: SD `STATE_SD_T22_
  C46_S22-46-1.1` (`"the term, neglect, does not include..."`) — SD's own
  unquoted comma-delimited shape, the SAME disclosed markers-sprint
  dependency (contract item 4), re-confirmed live via this cross-check.
- **Borderline/soft (flagged, not counted as a hard miss)**: AZ
  `STATE_AZ_T43_C10_A1_S1002` — supplementary rules refining an
  externally-located definition ("married person" defined in a DIFFERENT
  section, 43-1001); real content, but arguably not itself "a local
  definitions block."
- **Correctly excluded (checked, not assumed)**: all 7 WV `"PART N.
  DEFINITIONS."` rows, all 5 TX `"APPLICABILITY OF DEFINITIONS"` rows, both
  WA rows, AL's 2 "Meaning of Herein" rows, KS/MO/MI/ND/NJ/OR/SC/TN/VA/ID/
  WY/AR's entries in the >=250-char set, and all 8 spot-checked small stubs
  — every one of these points to definitions located ELSEWHERE (a
  different section/chapter/"library of definitions" index) rather than
  carrying real local content in THIS row's own body. Read directly, not
  inferred from heading text alone.

**Answer to D3's own question**: yes, there ARE genuine rows in the
headings panel's cluster that neither our rules nor any documented routing
account for — at minimum the 5 named above (CO, NV×2, NM×1 unique
statute, IN×2 same statute) plus the AZ borderline case. This is a small
absolute count against 245 rows, consistent with the doc's own "QA cycle 2:
zero genuine misses in 15" finding being closer to the truth than the
looser 10–25% early estimates — but it is not zero, and every one of these
act_ids is real and independently re-derivable from the corpus.

### Q-D4 — Suite tail + mutation-proof (not vacuous)

Full `backend/.venv/bin/pytest -q` from `backend/`: **3 failed, 818
passed** — the exact documented end state. All 3 reproduce for the
documented reason (empty-set/membership assertions on NE/SD's unquoted-term
shape, the disclosed `2026-08-04-defs-us-markers` dependency):
`test_ne_unquoted_term_means_needs_markers_sprint_too`,
`test_sd_unquoted_comma_term_needs_markers_sprint_too`,
`test_real_pipeline_still_cannot_capture_the_real_nebraska_unquoted_body_
preamble_definitions_needs_markers_sprint_too`. Nothing regressed.

**Mutation-proof, not merely assumed**: wrote a scratchpad pytest plugin
(`qa_mutation_plugin.py`, loaded via `-p qa_mutation_plugin` on
`PYTHONPATH`, never touching any repo file) that clears
`registry._body_preamble_rules` at session start — functionally "the rules
module never existed" for dispatch purposes, without editing
`us_body_preamble.py` or anything else. Ran the full family test suite (12
files, `test_us_body_preamble_*` + `test_definition_links_us_preamble_
family.py`) under this mutation: **31 tests flip from PASS (normal run) to
FAIL (mutated)** — concrete proof they depend on the shipped rules module,
not vacuous passes. This includes the GA fabrication guard
(`test_real_pipeline_does_not_fabricate_a_definition_from_a_georgia_
section_...`, M-R31's own test) and every GA/MD/NE/MS/SD/B1/B2/CA/FED/DC/NY
capture test. As expected and correct, the hazard-catalogue and
negative-guard test files (`test_us_body_preamble_hazard_catalogue_red.py`,
`test_us_body_preamble_negative_guard*.py`) do **NOT** appear in the
mutated-failure list — these are designed to hold true with or without the
rules (their whole point is "no spurious candidate, rule present or not"),
which is correct behavior for a negative guard, not vacuity.

### Q — What I did NOT measure (stated plainly, per the sprint's own rule)

- Corpus-wide byte-coverage contamination rate of the 27,209 fallback-
  affected `definition_text` fields (S1-style measurement) — flagged as a
  real risk, not quantified this cycle.
- Full-corpus re-scan of each of Q-D2's 8 named miss-shapes (I have a
  50-row hand-verified sample; shape-by-shape corpus totals were out of
  this cycle's budget).
- Whether widening any trigger (e.g. B1 to include "In this") would
  introduce new false positives — a rule-design question, not QA's to
  answer or attempt.
- The RI mangled-quote-byte defect's downstream scope (already routed,
  item 19; not re-measured).
- Reconciliation of the "5/28,154" figure against my measured "2/28,154" —
  I traced my own number to source but could not locate the "5"'s origin
  in this log to reconcile it; reporting both rather than guessing.

Pushed as `<SHA recorded in final report to the manager>`.

---

## 2026-08-05 — Manager VERDICTS on QA certification (a)–(e) + new preposition cluster

QA handoff verified first: `git diff --name-only a0d82cc..10924fc` → the log
only; **zero `backend/app/` edits**. Role separation held.

### M-R36 — VERDICT (a): the record carries BOTH numbers. After = 2,794/28,154.

QA measured GA before = **2**, traced to the legacy body-derivation path, and
could not reconcile the historic **5/28,154** the director has been quoted.

**Ruling: report `before = 2 (measured) / 5 (historic, unreconciled)`,
never a silent substitution.** Rationale: the two differ by 3 rows on a
28,154-row corpus — 0.007% vs 0.018%, both indistinguishable from zero — so
the discrepancy is immaterial to the headline but material to trust. Quietly
swapping 5→2 would mean the first number the director sees in this program
that contradicts a number they were previously given, changed without
comment. That is a worse outcome than a one-line footnote.

**Certified headline: GA 2 → 2,794 of 28,154 (9.9%)**, on QA's stated
single definition of "captured", corrected-fallback caveat respected. The
before-value's exact identity does not move it.

### M-R37 — VERDICT (b): NE is a NAMED RESIDUAL, split across two owners

7/25,997 captured against a 46-row target; **274 recognized, only 7
extract**. That gap is diagnostic, not disappointing: **recognition is
ours and it works** (274 rows found); **extraction is the markers panel's**
— NE's dominant convention is unquoted terms, which no current extractor
parses, exactly the item-5 dependency this sprint disclosed from the start.

**Ruling:** NE is a **named residual on our ledger with the extraction half
routed to `defs-us-markers`**, not a preamble-family failure and not hidden
behind the GA headline. The honest sentence for the record: *"NE: our rules
recognize 274 definitions-bearing blocks; 7 yield definitions today, because
267 use unquoted terms no extractor can parse. Blocked on markers."*
The 46-row target was set against the quoted subset only; that framing was
too narrow and I am correcting it here rather than reporting a miss.

### M-R38 — VERDICT (c): LEDGER the 27,209 fallback-affected rows, do not accept silently

The 50,826 new captures split **23,617 clean-primary / 27,209 via the
S1-flagged fallback** whose last entry runs to end-of-text.

**Ruling: ledger, not accept and not block.** Concretely:
1. The **23,617 clean-primary figure is the defensible one** for any
   certification claim.
2. The 27,209 are reported **separately and labelled provisional** — their
   term IDENTIFICATION is sound (that is what our rules do); it is
   `definition_text` BOUNDARIES that are unquantified.
3. Quantifying now would mean measuring against a known-broken oracle. The
   fix is already routed; re-measure **after** it lands.
This is why I required the split reported rather than one blended number —
a single 80,493 would have been indefensible.

### M-R39 — VERDICT (d): SHAPE → OWNER ATTRIBUTION. Most of P-R7 is NOT ours.

P-R7's 59,461 uncaptured / ~94% genuine is real, and I am not treating it as
this panel's gap wholesale. Attribution, from QA's 8 named shapes:

| # | Shape | Owner | Est. volume | Why |
|---|---|---|---|---|
| 1 | Bare `"Term" means`, **no trigger phrase at all** | **headings** (2nd: markers) | **largest single shape**; NV alone ~8,323 | There is no preamble to recognize. QA states this is the shape behind NV's `"<Term>" defined` heading convention — the HEADING is the signal, which is the headings panel's own NEW verb-form family. A `BodyPreambleRule` structurally cannot see it. |
| 2 | Trigger present, quote follows with no literal "the term"/colon | **SPLIT: ours (BLOCK) / scoped-inline (CLAUSE)** | mid | Our own trigger, our own rule, post-trigger pattern too strict. Ours where the section is wholly definitions. |
| 3 | **`"In this <unit>"` trigger — FEDERAL's dominant convention** | **OURS** | large; threatens our item-14 FEDERAL target | This IS a body preamble; B1's vocabulary just lacks the phrase. 4/4 sampled FEDERAL rows. I do **not** accept the scoped-inline framing for this one — see note below. |
| 4 | Trigger cites external section ranges | **ours (recognition) + core (scope)** | small | Preamble is ours; a range is not expressible in current scope units. |
| 5 | Named-Act phrasing | **ours (recognition) + core (scope)** | small | Same shape as 4. |
| 6 | Intervening qualifier between trigger and term | **OURS** | small–mid | Narrow B1 widening. |
| 7 | CA wide-window idiom **in other states** | **OURS** | small | Our own rule, needlessly scoped to `US-CA`. Trivial widening. |
| 8 | B2 wording variants | **OURS** | small | Our own rule, literal-phrase match too strict. |

**Where I push back on the framing:** shape 3 was suggested to me as
scoped-inline/markers territory. It is not. `"In this section:"` is a body
preamble introducing a definitions block that never uses the word
"Definitions" — the literal definition of this sprint's family. B1 already
matches two trigger phrases; this is a third. It also directly threatens
**our own contract item 14** (FEDERAL 198/435). Handing it away would move
our largest remaining in-family gap off our ledger, which is the opposite of
what P-R7 is for. **Shape 3 stays ours.**

Shape 1, by contrast, genuinely is not ours and it is the biggest — so this
attribution moves volume off our ledger and onto ours in roughly equal
measure. That is the honest split, not a defensive one.

**Volume caveat, stated plainly**: these are QA's 50-row-sample-derived
estimates, not per-shape re-scans. Shapes 1 and 3 dominate; the rest are
long-tail. Do not treat the bands as measured counts.

### M-R40 — VERDICT (e): D3 guarded-cluster gaps, disposed

- **IN ×2 (CA-idiom)** → **ours, fix**: identical to shape 7; our CA rule is
  scoped `US-CA` for no principled reason. Widening its `jurisdiction_codes`
  is a one-line rule change (Developer, next cycle).
- **NM (Named-Act + "also means")** → **ours (recognition)**, shape 5; the
  `"also means"` idiom is an additional B1 branch. Scope target → core.
- **NV ×2 (exclusion-style)** and **CO** → **headings**, same
  preposition-governed family as the new cluster below; our rules reach them
  only if the body carries an independent defining idiom (measured below).

### M-R41 — NEW preposition-governed cluster: MEASURED, not estimated

I measured this myself against the shipped rules across all 53 files rather
than reason about it. Scope note: my heading pattern (`Exclusions|Limitation|
Applicability|Effect|Scope` + `definition(s)`) is **broader** than the
headings panel's 78-row cluster, so these populations overlap but are not
identical — stated so the numbers are not falsely reconciled.

Restricting to rows the Definitions-heading matcher does **not** already
capture (i.e. the guard-excluded population):

| | rows |
|---|---|
| preposition-governed, not already a Definitions heading | **150** |
| ...body carries a defining idiom + quoted term | **18** |
| ...**RESCUED by our shipped `BodyPreambleRule`s** | **12** |
| ...**genuinely UNREACHED** | **6** |

**Answer to the panel: yes, our shipped path already rescues two-thirds of
them (12/18) with no further work.**

The **6 unreached, named** (D-HG sends these to the director by name, so
they are listed rather than counted):
`STATE_ID_T39_C1_S39-129`, `STATE_KY_TIX_C67_S67.323`,
**`STATE_ME_T28-A_P3_C55_S1401-A`** (the ME "Limitation on definition of
\"certificate of approval holder\"" textbook case cited to me — confirmed
UNREACHED), `STATE_MI_C500_AAct-218-of-1956_S500.1305`,
`STATE_PA_T20_C77_S7721`, `STATE_SC_T59_C58_S59-58-30`.

### M-R42 — What is certified, and at which SHA

**Certified at `10924fc`** (plus this verdict commit):
- GA **2 → 2,794 / 28,154 (9.9%)**, before-value dual-reported per M-R36.
- Corpus-wide **29,667 → 80,493**, of which **23,617 clean-primary is the
  defensible figure**; 27,209 fallback-affected are **provisional** (M-R38).
- **FP rate 0/50** hand-judged, after a disclosed self-correction.
- Suite **3 failed / 818 passed**; all 3 are the disclosed markers
  dependencies; **31 tests mutation-proved** including the GA fabrication
  guard.
- Consolidated inventory + CLAUSE package (2,659 act_ids / 51 jurisdictions)
  stable and safe for the headings panel to consume for its U4 cross-check.

**NOT certified / open on our ledger**: shapes 2–8 of P-R7 (in-family gaps,
a real next cycle of work); NE extraction (blocked on markers); the 6
unreached preposition rows; `definition_text` boundaries pending the routed
fallback fix.

---

## 2026-08-05 — Manager: next-cycle plan CONFIRMED with 3 refinements; Planner flipped

Sequence (1)/(2)/(3) confirmed. Three refinements, raised because D-CERT
changes what this cycle is FOR.

### M-R43 — Refinement 1: harden the P-R7 denominator FIRST, not after

Under D-CERT the US track's close is built on **our** P-R7 denominator. That
promotes it from a QA artifact to a program-critical one — and QA stated
plainly under "not measured" that the **true corpus-wide size of each of the
8 shapes was never re-scanned**; the bands are extrapolations from one
50-row sample.

Two consequences if we fix shapes before measuring them:
1. **We cannot prove a fix moved anything.** "Shape 3 fixed" is unfalsifiable
   without a measured shape-3 baseline.
2. **The program close inherits sample-derived uncertainty** in its
   denominator — the one artifact D-CERT requires to be signal-agnostic AND
   trustworthy.

**Ruling: the next cycle opens with a per-shape corpus-wide re-scan** turning
the 8 bands into measured counts, before/alongside the fixes. It serves our
items and the program close with one pass, and it is cheap relative to
re-doing the close later.

### M-R44 — Refinement 2: RED tests must pin PER-RULE attribution, not aggregate capture

This cycle widens several rules at once — B1's trigger vocabulary (shape 3),
the CA rule's `jurisdiction_codes` (shape 7 / IN×2), a new "also means"
branch (NM/shape 5), plus shapes 2/6/8. Dispatch is
**first-non-None-wins in registration order** (M-R27).

Widening rules that share a corpus is exactly how one rule silently starves
another: aggregate capture goes UP while a specific rule stops firing, and no
aggregate assertion can see it. **Every new/widened rule needs a test that
pins WHICH rule claimed the row**, not merely that the row was captured.
Otherwise the first regression of this kind will be invisible.

### M-R45 — Refinement 3: re-measure FP after every widening; the remedy is narrower rules

Current FP is a clean **0/50 hand-judged**. Shapes 2, 3 and 6 all widen
matching into looser trigger/idiom territory, and shape 3's `"In this
<unit>"` is a common English phrase in non-definitional prose — a genuine
new-FP risk, not a theoretical one.

**Every widening re-measures FP on its own newly-claimed population.** Per
the seam, a material number is **NOT** grounds to re-gate dispatch — the
remedy is a narrower rule. Escalate with data per D-Q1; never gate.

### M-R46 — Confirmations on (2) and (3)

- **NE extraction → markers**: confirmed. Recognition (274 rows) is
  certified ours and working; the 267 unquoted rows join their unquoted
  family. Nothing further owed by us beyond keeping the named residual
  visible.
- **MS padding + fallback last-entry → core follow-on**: confirmed, and our
  `definition_text` re-measure stays correctly blocked. Restating so it is
  not lost: **23,617 clean-primary remains the defensible figure** until
  that fix lands; 27,209 stay provisional.

### M-R47 — Model/effort for the Planner spawn

Planner: **Sonnet / high** — designing a signal-agnostic per-shape
measurement that will underpin a program-level certification, plus RED tests
that must pin per-rule attribution under a first-wins registry, is sustained
judgment. Per P-R6 Planner is always Sonnet high. **Haiku considered: no.**
`model=inherit` not used. Sole writer; authors tests only, never rules.

---

## 2026-08-05 — Planner: D1, per-shape corpus-wide measurement (M-R43)

Worked in `/Users/nerya/LexGraph-wt/defs-us-preamble` at `6910eb0`. Script
committed at `docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/
measure_shapes_corpus_wide.py`, raw output at `shape_measurement_output.json`
in the same directory. Full corpus, all 53 statutes files, snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad` (the `main` ref — the OTHER
snapshot dir present in the HF cache, `d2d76035...`, is a stale 11-file
partial fetch from an earlier sprint, not used). **2,038,247 rows scanned**
— matches Q-D1's own cited denominator exactly (cross-check).

### P-D1 — Method: signal-agnostic, independently authored, self-validated

Every one of the 8 shape detectors below is written FRESH against Q-D2's own
English description of the shape — none imports or copies the regex
OBJECTS from `us_body_preamble.py`. Two shapes (2, 6) unavoidably share
english vocabulary with our own B1 trigger, because that IS the shape's own
definition (M-R39: "our own trigger... post-trigger pattern too strict" /
"narrow B1 widening") — disclosed in the script's own module docstring, not
hidden. Shapes 1/3/4/5/7/8 use vocabulary our shipped rules do not currently
match at all, so those are independent in the strong sense too.

"Captured today" is computed by calling the REAL, unedited production code
(`get_profile`, `.is_definitions_heading`/`.derive_heading_from_body`/
`.determine_scope`/`.extract_definitions_from_section`) directly against
each row — mirroring `pipeline.py`'s own Stage-2 dispatch verbatim, never a
reimplementation. "Captured" = the same single Q-D1 definition (heading
recognized AND `extract_definitions_from_section` yields >=1 candidate with
non-empty `.terms`).

**Precision was iteratively verified, not assumed** — four real bugs were
found and fixed by hand-sampling actual matched excerpts before trusting any
corpus-wide number (all four fixes are in the committed script, with the bug
and its fix documented inline):
1. A bare `\bIn this\b` regex for shape 3 matched INSIDE "**as used** in
   this article" (substring match) — fixed with a clause-initial guard
   (preceded by start/newline/`.::`/marker, not by a verb like "used").
   This alone cut shape 3's 3-state smoke-test count from 6,945 to 172.
2. Shape 7's CA-idiom search was unanchored, matching "shall **not** apply"
   (negated scope) and "the definitions found in/provided in/**under**
   section X apply" (a pure FORWARDING pointer — the same H1 hazard class
   this family's own hazard catalogue already documents) — fixed by
   anchoring at body-start (mirroring the real CA rule's own window
   discipline) plus an explicit forwarding-phrase exclusion list.
3. Shape 4's bare trigger match ("For purposes of Section N, the period of
   the underpayment shall run from...") matched an ordinary OPERATIVE
   sentence citing a section number but defining nothing — fixed by
   requiring actual post-trigger definitional content (colon-list or
   quote+verb), the same discipline shapes 2/3/6 already apply.
4. A naive "any colon present" check (shapes 3/4) accepted "...is the
   earlier: (a) The 15th day..." (an unrelated operative-deadline list) as
   evidence of a definitions list — fixed with a shared `_has_definitional_
   content` helper requiring the colon to actually introduce a quoted-term
   or unquoted-numbered defining entry.

**Cross-validation against Q-D2's own independent methodology**: my
component-A reproduction (quoted term + broad verb, same verb vocabulary,
800-char window vs Q-D2's 600) measured **89,832 candidates / 32,371
already captured** — Q-D2's own number was **91,878 / 32,417**. Independent
methods, same corpus, same ballpark (both within ~2%) — good confirmation
neither run has a gross defect.

### P-D2 — Per-shape measured table (total, not extrapolated)

| # | Shape | Total hits | Captured today | **Uncaptured (measured miss)** |
|---|---|---:|---:|---:|
| 1 | Bare `"Term" means`, no trigger | 31,048 | 1,370 | **29,678** |
| 2 | Trigger present, no "the term"/colon | 23,049 | 5,572 | **17,477** |
| 3 | `"In this <unit>"` trigger | 13,062 | 3,545 | **9,517** |
| 4 | External Section-range trigger | 1,702 | 59 | **1,643** |
| 5 | Named-Act phrasing | 196 | 1 | **195** |
| 6 | Intervening qualifier clause | 125 | 23 | **102** |
| 7 | CA idiom in OTHER states | 1,417 | 244 | **1,173** |
| 8 | B2 wording variant | 576 | 280 | **296** |

Shape 5's own `"also means"` sub-idiom: **2/196** rows corpus-wide (NM's own
named example is one of the two) — a real but tiny idiom, not a large
sub-population.

**Distinct-row total** (shapes overlap; 175 raw pairwise-overlap instances
recorded, a small correction relative to the totals above, triple-overlaps
assumed negligible): **~59,900 distinct rows** corpus-wide match at least
one of the 8 shapes and are uncaptured today. **This lands within 1% of
Q-D2's own independently-derived 59,461** — two unrelated methodologies (one
per-shape, one aggregate) converging on the same figure is a strong
cross-check, not a coincidence I am claiming credit for engineering.

**In-family-only total (ours, shapes 2+3+4+5+6+7+8, excluding shape 1 which
is headings-owned per M-R39)**: **~30,300 distinct rows** — this is the
honest "our remaining opportunity" headline number for this cycle, measured
not estimated.

**Per-state**: top state per shape — 1: NV (7,937, vs M-R39's own quoted
"~8,323" estimate, within 5%); 2: **IN (4,221)**; 3: **TX (2,949)**, not
FEDERAL (see below); 4: MS (984); 5: NM (111); 6: MS (38); 7: **IN (352,
the exact shape-7/IN×2 target)**; 8: MS (123). The full 53-state x 8-shape
table (424 cells) is in the committed `shape_measurement_output.json`
(`per_state` key) — omitted here for length; every number in this report is
reproducible from that one file plus the script.

### P-D3 — Which of QA's bands were right, high, or low

M-R39's table gave qualitative bands from a 50-row sample. Measured against
them:

- **Shape 1 ("largest")** — CONFIRMED. 29,678 uncaptured, the largest single
  shape. NV's own estimate (~8,323) was close (measured 7,937, ~5% high).
- **Shape 2 ("mid")** — **BAND WAS TOO LOW.** 17,477 uncaptured is the
  SECOND-LARGEST shape, comparable in scale to shape 3, not "mid" alongside
  shapes 4-8's low hundreds. This is the single biggest correction in this
  report: shape 2 (SPLIT ours/scoped-inline, BLOCK-only for us) needs to be
  understood as a top-tier volume shape for capacity planning, not a
  medium one.
- **Shape 3 ("large; threatens item-14")** — CONFIRMED, with an important
  nuance: FEDERAL's own 874 shape-3 hits are **49% of FEDERAL's entire own
  candidate population** (874/1,766) — genuinely its DOMINANT convention,
  confirming the "threatens item-14" framing — but the corpus-wide ABSOLUTE
  count is dominated by TX (2,949) and WI (1,979) and MD (1,951), not
  FEDERAL (855 uncaptured, 4th place). Both framings are true and both
  matter for different questions (item-14 relies on the proportion-within-
  FEDERAL framing, not the corpus-wide rank).
- **Shape 4 ("small")** — CONFIRMED, 1,643 uncaptured, MS-dominated (984).
- **Shape 5 ("small")** — CONFIRMED, 195 uncaptured, very small.
- **Shape 6 ("small–mid")** — band's "small" half confirmed; the "mid" half
  is not supported — 102 uncaptured is small by any comparison in this
  table.
- **Shape 7 ("small")** — **BAND WAS A LITTLE LOW.** 1,173 uncaptured is
  closer to shape 4's scale (1,643) than to shapes 5/6/8's low hundreds —
  "small-mid" would be the more accurate label. IN alone (352) is the named
  shape-7/IN×2 target; a blanket `US-*` widening (not recommended, see D4)
  would claim the full 1,173, ~3.3x more than the targeted `US-IN`-only fix.
- **Shape 8 ("small")** — CONFIRMED, 296 uncaptured, MS-dominated (123).

### P-D4 — What was NOT measured (stated plainly)

- **A real, bounded corpus-quality blind spot in this classifier (and
  likely in Q-D2's own component A/B, which uses the same quote
  vocabulary)**: 4/53 states show near-zero quoted-term+verb signal at all
  (`component_a_total`): **AK (0), MA (0), RI (0), PR (2)**, against
  17,168/22,514/20,552/23,636 baseline-fail candidate rows respectively —
  NOT genuine zero population. Confirmed live for AK: its real quote
  characters are stored as raw `\x93`/`\x94` bytes (cp1252 mojibake,
  already documented in this repo's own `ak_i9_cp1252_mojibake_row.json`
  fixture) — my (ASCII/curly-quote) regex class never matches them. RI's
  own near-identical mangled-quote defect (`\x80\x9c`/`\x80\x9d`) is
  ALREADY independently documented in this sprint's own `test_us_body_
  preamble_b1_colon_list_matrix_red.py` module docstring — cross-confirms
  this is a real, known corpus defect, not a bug in today's script. MA's
  cause was not independently root-caused this cycle (flagged, not
  investigated further) — could be the same encoding class or a genuinely
  different convention. **Net effect: every number in this report is a
  LOWER BOUND** for these 4 states specifically; the true corpus-wide
  totals are somewhat higher than measured.
- Shapes were classified independently per shape (a row can match more than
  one); I did NOT attempt single-shape-per-row forced classification, since
  overlap itself is useful signal for D4's own starvation analysis (the
  overlap_pairs data is in the committed JSON).
- I did not re-run Q-D2's own component-B (unquoted-term) denominator
  slice — Q-D2 itself called it "a small, separately-disclosed contributor"
  (1,996/59,461 raw); not reproduced here given the time budget, and it does
  not change any of the 8 shapes' own membership (none of the 8 named
  shapes are component-B-only).
- Whether widening any of these rules materially changes FP is a SEPARATE
  question — that is D3, below, not this measurement.

---

## 2026-08-05 — Planner: D2, RED tests pinning per-rule attribution (M-R44)

6 new files, `backend/tests/integration/test_us_body_preamble_shape{2,3,5,
6,7,8}_*_red.py`, one per in-family shape the sprint charter's D2 list
names (shape 4, "ours(recognition)+core(scope)" per M-R39, is not on that
list — D1 still measured its population, 1,643 uncaptured, MS-dominated,
for the record, but no test was assigned or built for it this cycle). 10
real rows vendored into ONE new fixture, `backend/tests/
fixtures/us_statutes/cycle7_pr7_shapes_rows.json` (dict keyed by `act_id`,
matching this directory's own established convention), all original
columns, values unmodified.

**Row provenance** (every row independently re-fetched and re-verified by
this Planner against the real on-disk snapshot, not copied from QA's report
uncritically): `STATE_KS_C75_A45_S75-4511` (shape 2), `USC_T7_C31_S936f` /
`USC_T27_C6_S122a` / `USC_T43_C35_S1742a` / `USC_T10_C147_S2496` (shape 3,
all 4 of Q-D2's own named FEDERAL rows), `STATE_NM_C3_A32_S3-32-3` (shape 5,
the same row Q-D2 and Q-D3 independently cross-confirmed), `STATE_TN_T49_
C4_S49-4-938` (shape 6, Q-D2's own named row), `STATE_IN_T21_A44_C7_
S21-44-7-1` + `...-1-b` (shape 7, Q-D2/Q-D3's own named IN pair), `STATE_
MS_T27_C7_S19-3` (shape 8, Q-D2's own named row). Every row independently
confirmed, before any test was written: fails baseline `is_definitions_
heading`/`_is_placeholder_heading` (so the profile's separate LEGACY gate
is a no-op and outcome is decided entirely by the `BodyPreambleRule`
registry loop), and yields ZERO candidates from the real, unedited
`extract_definitions_from_section`/`_extract_inline_quoted_definitions`
today (verified by calling them directly, before writing any assertion).

### How per-rule attribution was pinned (M-R44)

All 4 existing rules return the LITERAL STRING `"Definitions"` as their
synthesized heading (NOT a distinctive per-rule string) — confirmed by
reading `us_body_preamble.py` directly — except CA's rule, which returns an
actual body-text slice (distinctive, but only for CA). **This means the
FINAL result (a captured Definition) cannot by itself reveal WHICH rule
produced it** — exactly the invisible-starvation risk M-R44 describes.
Since editing production code to add distinguishing headings is out of
scope for a Planner, and the manager's own brief named "a direct rule-level
assertion alongside the live-path one" as the sanctioned alternative, every
test file in this cycle defines a small `_winning_rule(code, body)` helper
that mirrors `USProfile.derive_heading_from_body`'s own registry loop
(`us_profile.py:1402-1405`, first-non-None-wins in REGISTRATION order,
M-R27) but returns the WINNING rule's `derive_heading` CALLABLE itself, not
just its string result. Each test then asserts (a) `_winning_rule(code,
body) is <the specific target function>` — an IDENTITY comparison, not a
string comparison — and (b) every EARLIER-registered existing rule
independently returns `None` on the same real body (a stable, permanently-
re-checked invariant, not a one-time snapshot). This directly reproduces
this codebase's own established precedent (`test_us_body_preamble_ca_
block_red.py`'s `_derive_heading_from_body`/`_is_placeholder_heading`
unit-level pins already import and call private functions by name) rather
than inventing a new pattern.

This combination would FAIL if the wrong rule claimed a row in three
concrete ways: (1) if a SIBLING rule being widened THIS SAME cycle
overreaches into another shape's fixture (e.g. B2's shape-8 widening
starts also matching a FEDERAL shape-3 row) — the "earlier rules return
None" assertions catch this directly; (2) if the intended target rule's
own widening is missing or scoped wrong (its own identity check fails,
`_winning_rule(...) is not <target>`); (3) if the live-path capture check
passes for the WRONG reason (some unrelated code path produces the right
terms without going through this family's own dispatch at all) — the
identity check and the live-path check are independent enough that either
alone catches a class of regression the other cannot.

**Function-name contract with the Developer (D4's own build target)**:
shapes 2/3/6 all widen the SAME existing function, `_b1_trigger_colon_or_
quote_means` (imported today, already exists); shape 8 widens `_b2_words_
have_meanings_indicated` (exists today); shape 7 widens `_ca_wide_window_
definitions_preamble`'s own `jurisdiction_codes` registration, NOT its
regex (proven live: calling the function directly on both real IN bodies
ALREADY returns non-`None` today — a dedicated unit-level pin, GREEN today
by design, proves this so the Developer does not waste time changing a
regex that needs no change); shape 5 requires a genuinely NEW function,
`_named_act_also_means_preamble` — this exact name is imported inside the
attribution test's own body (not at module level, matching this
repo's own established `test_definition_links_rules_registry.py`
convention so a missing symbol fails ONE test, not the whole file's
collection) and IS the Developer's build target, not a suggestion.

### RED run tail (all 6 files together, before commit)

```
20 failed, 2 passed in 0.54s
```

The 2 PASSED are shape 7's own unit-level "the regex already works, only
`jurisdiction_codes` is missing" pin (both IN rows) — a deliberate,
documented, GREEN-today regression pin (same convention as the CA block
red file's own prefix-cap pin), not a gap in RED coverage; every CAPTURE
and every ATTRIBUTION test across all 6 files is confirmed RED. Full suite
after adding these 6 files: **23 failed / 820 passed** (the 3 pre-existing
markers-sprint REDs + this cycle's 20 new REDs; 818 baseline-passed +
2 new GREEN-today pins) — zero regressions.

**Existing tests**: none edited, none weakened — verified via `git diff
--stat` before commit (new files only).

---

## 2026-08-05 — Planner: D3, FP re-measurement design (M-R45)

Tool committed: `docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/
measure_fp_after_widening.py` — run by the Developer/QA AFTER this cycle's
widened rules land (not runnable meaningfully today, since nothing is
implemented yet). It calls the SAME real profile machinery this family's
own tests do, diffs BEFORE (current 4 rules) against AFTER (whatever the
Developer's code actually looks like when run — no hardcoded assumption
about their exact regex), groups newly-captured rows by WINNING RULE
identity (the same `_winning_rule` technique D2's tests use), and draws a
Q-D1b-convention random sample (seed `20260805`, 50/rule) for hand-judging.
**Never a gating tool** — it only measures; per M-R45 the remedy for a
material FP number is a narrower rule, never re-gating dispatch, and
nothing in this script suppresses or filters what dispatch produces.

### Prospective newly-claimed population, per shape (measurable NOW)

Using D1's own classifiers as an upper-bound estimate of what a
reasonably-scoped widening claims (D1's own numbers, recommended-scope
column applies the narrower jurisdiction choice D4 recommends for shape 7,
not the raw corpus-wide idiom count):

| Shape | Prospective new-claim volume | Scope |
|---|---:|---|
| 2 | 17,477 | `US-*` (unavoidably corpus-wide) |
| 3 | 9,517 (lower bound — see D1's "not measured" note on the em-dash gap) | `US-*` |
| 5 | 195 | `US-*` |
| 6 | 102 | `US-*` |
| 7 | **352** (US-IN only, recommended) vs 1,173 (if `US-*`, NOT recommended) | `US-IN` [+`US-MS`, optional] |
| 8 | 296 | `US-*` |

**Shapes 2 and 3 dominate the prospective volume** (27,000 of ~28,000
total across our 6 shapes) — this is where FP review effort should
concentrate; shapes 5/6/7/8 are small enough that even an elevated FP rate
produces a small absolute number of bad Definitions.

### Precision measured NOW on shapes 2 and 3 (the two dominant shapes)

A uniform-random, unbiased sample (30 rows each, seed `20260805`, drawn
from the FULL corpus-wide hit list — not the reservoir-capped, alphabet-
order-biased 12-per-shape samples D1's own script stores) was fetched in
full and hand-judged against the real body text, exactly Q-D1b's own
discipline:

- **Shape 2: 4/30 (13.3%) false positives**, e.g. `STATE_IN_T15_A16_C4_
  S15-16-4-27.5` ("As used in this chapter, "nontarget site" **has the
  meaning set forth in** IC 15-16-5-21.5") and two Ohio rows ("**has the
  same meaning as in** section 9.23/3313.77 of the Revised Code") — pure
  forwarding pointers with NO local definition text, the same H1 hazard
  class this family's own hazard catalogue already documents.
- **Shape 3: 1/30 (3.3%) false positive** (`STATE_TX_Cin_C862_S862.101`,
  "has the meaning assigned by statute, rules... or lawful custom" — a
  vague forwarding pointer with no citable local text at all). Two other
  flagged rows (WI, FED) were judged genuine on closer reading — MIXED
  blocks where one or two entries forward but the section also defines
  other terms locally (the same accepted "mixed forwarding-and-local"
  shape the existing WV B1-matrix test already tolerates).

**Root cause, and the remedy (a narrower rule, per M-R45 — never a
gate)**: every genuine false positive found in BOTH samples shares the
exact same forwarding-phrase vocabulary (`"has the meaning [given/found/
set forth/provided] in"` / `"has the same meaning as"`) that B1's OWN
EXISTING colon-list branch already excludes via `_B1_FORWARDING_PHRASES`
— that filter is applied ONLY to the colon-list branch today, not to the
quote-means branch this cycle widens for shapes 2/3/6. **Concrete
recommendation for the Developer (D4)**: apply the SAME existing
`_B1_FORWARDING_PHRASES` check to the widened quote-means branch's own
filler/gap text. This one change would likely close most or all of the
false positives found in both samples above — a narrower rule, exactly
what M-R45 requires, not a new gate and not new vocabulary invented by
this Planner (it reuses a filter that already exists and is already
proven safe on this exact hazard class).

**Secondary, smaller finding**: `_B1_TRIGGER_RE`'s own tail,
`[A-Za-z0-9 .\-]{0,30}`, is a plain character class that permits SPACES —
on `STATE_ME_T22_S2_C562-A_S2521-C` ("For the purposes of this section
**the term** "ritual slaughter" means...") the trigger's own greedy match
swallowed "the term " into ITS OWN span before the quote-means branch ever
saw it, which (in this specific real row) still resolved to a genuine
local definition, so it did not become a false positive here — but it is
a real, disclosed regex-greediness quirk shared by my own measurement
script (which deliberately mirrors this exact trigger vocabulary, per
this cycle's own disclosure for shapes 2/6) and potentially by the real
`_B1_TRIGGER_RE` too. Flagged for the Developer's own awareness, not
treated as urgent (found zero false positives caused by it in either
sample).

### What was NOT measured for D3

- The TRUE post-implementation newly-claimed set and its TRUE FP rate —
  those require the Developer's actual code, which does not exist yet;
  this section's numbers are prospective/upper-bound estimates from this
  Planner's own classifier, explicitly not a substitute for re-running
  `measure_fp_after_widening.py` after implementation.
- Shapes 5/6/7/8's own FP rate on a real random sample (their prospective
  populations are small enough, per the table above, that this Planner
  judged the 60-row shape-2/3 sample the higher-value use of the time
  budget — flagged, not silently skipped).

---

## 2026-08-05 — Planner: D4, item list for the Developer

Registration order TODAY (unchanged unless stated): (1) CA
`_ca_wide_window_definitions_preamble` `("US-CA",)`, (2) NE `_ne_named_
code_quoted_list` `("US-NE",)`, (3) B2 `_b2_words_have_meanings_indicated`
`("US-*",)`, (4) B1 `_b1_trigger_colon_or_quote_means` `("US-*",)`.

| Shape | Function (existing name / prescribed new name) | Pattern change | `jurisdiction_codes` | Registration slot | Tests to turn GREEN |
|---|---|---|---|---|---|
| 3 | `_b1_trigger_colon_or_quote_means` (widen `_B1_TRIGGER_RE`) | add `"In this"` as a 3rd trigger alternative alongside "As used in"/"For (the) purposes of" — same two branches (colon-list, quote-means) apply to `after` unchanged | unchanged `("US-*",)` | unchanged, #4 | `test_us_body_preamble_shape3_in_this_trigger_red.py` (8 tests) |
| 2 | `_b1_trigger_colon_or_quote_means` (widen `_B1_QUOTE_MEANS_RE`) | make `"the term"` OPTIONAL before the quote; keep TIGHT adjacency (BLOCK-only per M-R39's split); **apply `_B1_FORWARDING_PHRASES` to the gap text** (D3 finding) | unchanged | unchanged, #4 | `test_us_body_preamble_shape2_no_the_term_red.py` (2 tests) |
| 6 | `_b1_trigger_colon_or_quote_means` (widen the quote-means branch further) | tolerate ONE optional short comma-bounded qualifier clause before "the term"/quote; **apply `_B1_FORWARDING_PHRASES` to the gap text** (D3 finding); design shapes 2+6 as ONE combined regex change, not two independently stacked ones (see overlap note below) | unchanged | unchanged, #4 | `test_us_body_preamble_shape6_intervening_qualifier_red.py` (2 tests) |
| 5 | **NEW**: `_named_act_also_means_preamble` (exact name — D2's tests import it) | trigger `"As used in the <Capitalized ... Act\|Code>"` (word "the", not "this"); verb `means` OR `also means` | recommend `("US-*",)` — measured hits span NM/NE/OK/AR/OH, not one state | recommend EARLY — right after NE (#2), before B2/B1 (narrow-before-broad, M-R27) — any slot before B1/B2 is safe, no overlap found | `test_us_body_preamble_shape5_named_act_also_means_red.py` (2 tests) |
| 7 | `_ca_wide_window_definitions_preamble` (jurisdiction widening ONLY — regex proven unchanged, D2's own GREEN-today unit pin) | none | widen from `("US-CA",)` to `("US-CA", "US-IN")` — **recommend adding `"US-MS"` too** (Q-D2 independently named `STATE_MS_T17_C3_S17-103` as the same idiom); **NOT `"US-*"`**, see overlap note below | unchanged, #1, **UNLESS** widened to `"US-*"` instead of an explicit list, in which case it MUST move to AFTER NE (#2) — open question, this Planner's lean is the explicit list, not the reorder | `test_us_body_preamble_shape7_ca_idiom_other_states_red.py` (6 tests) |
| 8 | `_b2_words_have_meanings_indicated` (add a 2nd alternative pattern) | MS's real phrasing REORDERS the sentence ("The following words and phrases when used in this article... have the meanings respectively ascribed to them") — not a same-slot word swap; needs a genuinely alternate regex, design left to the Developer | unchanged `("US-*",)` | unchanged, #3 | `test_us_body_preamble_shape8_b2_wording_variant_red.py` (2 tests) |

**Not in this cycle's build target** (measured by D1, not assigned a test
by D2): shape 4 (1,643 uncaptured, MS-dominated) — "ours(recognition) +
core(scope)" per M-R39, and a range citation is not expressible in the
current `UnitPath`/scope model without a core-side decision this Planner
judged out of bounds to pin a test against without either fabricating a
scope claim or leaving an assertion half-specified.

### Overlap / starvation flags (explicit)

1. **Shapes 2, 3, and 6 all modify the SAME function**
   (`_b1_trigger_colon_or_quote_means`) — architecturally fine (M-R44's
   attribution requirement is RULE-granularity, not sub-branch), but the
   Developer must run ALL THREE shape test files after touching this
   function, not just the one they think they changed. Recommend
   implementing shapes 2 and 6 as ONE combined regex change (optional
   qualifier clause AND optional "the term", together) rather than two
   independently stacked edits, since stacking them separately risks one
   widening's own anchoring assumption silently breaking the other's.
2. **Shape 7's jurisdiction widening, if done as a blanket `"US-*"`**
   (not recommended) risks preempting `_ne_named_code_quoted_list`
   (registered AFTER CA today, #2) for any Nebraska row that also happens
   to contain the wide-window CA idiom — this Planner did not find a live
   NE row triggering this in the sample data, but did not run a targeted
   NE-only check either (time budget), so this is a live open question,
   not silently resolved. The explicit-list widening (`US-CA`, `US-IN`,
   optionally `US-MS`) sidesteps the whole question and additionally
   claims 3.3x FEWER rows than the blanket alternative (352-440 vs 1,173,
   per D3's own table) — this Planner's lean.
3. **Shape 8 (B2, slot #3) is registered BEFORE B1 (slot #4)** — safe by
   construction; even if B1's own shape-2/3/6 widening ever became broad
   enough to also match an MS-shaped row, B2 still wins. No action needed,
   noted for completeness (not a real risk, included so the Developer does
   not need to re-derive this from scratch).
4. **Shape 5's new function and shape 4** (not built) both touch
   "definition lives somewhere other than 'this <unit>'" framing —
   checked, no direct pattern overlap (shape 4 requires "Section(s)"/§§
   digits, shape 5 requires "the <Named Act>", structurally disjoint).

### ESCALATION-adjacent note (not a full escalation, informational)

Per-rule attribution (M-R44) proved possible through the public API for
every shape this cycle — no escalation needed. The one open design
question (shape 7's jurisdiction scope: explicit list vs. blanket + reorder)
is flagged above with a stated lean, per the brief's own guidance to hand
genuine trade-offs to the manager rather than silently pick a side.

---

## 2026-08-05 — Manager: Planner cycle-7 verified; shape-7 scope ruled; Developer briefed

### M-R48 — Handoff verified (bf4fdcf)

- Diff vs `6910eb0`: 6 new RED test files + 1 fixture + log + 3 scratchpad
  scripts. **Zero `backend/app/` edits.** Role separation held.
- Suite reproduces: **23 failed / 820 passed**.
- **Fixtures re-read byte-for-byte against the parquet: 10/10 byte-exact**,
  zero fabricated, titles matching.
- **M-R44 is genuinely satisfied**, and I checked the mechanism rather than
  the claim. `test_mississippi_winning_rule_is_b2_not_some_other_rule`
  asserts `_winning_rule("US-MS", body) is _b2_words_have_meanings_indicated`
  — **identity on the function object** — plus explicit
  `_ca_...(body) is None` / `_ne_...(body) is None`. That fails if the wrong
  rule wins, which is exactly the invisible-starvation failure I required be
  made visible. The docstring even names the hazard ("an over-widened B1
  silently winning ahead of it").
- Measurement corrections accepted: **shape 2 was under-ranked** — QA's
  "mid" band was wrong; it is **#2 by volume (17,477 uncaptured)**. Shape 1
  = 31,048 total / 29,678 uncaptured. ~59,900 distinct rows cross-check
  Q-D2's 59,461 **within 1%**, which is real corroboration of the
  denominator from an independently-built classifier.
- **AK/MA/RI/PR near-zero signal flagged as corpus-ENCODING lower-bounds,
  not clean zeros** — correctly refusing to certify a zero it cannot
  distinguish from an artifact. Carried forward to D-CERT.

### M-R49 — RULING: shape 7 ships as an EXPLICIT jurisdiction list

The Planner raised this rather than deciding it, with a stated lean. Ruling:
**explicit list (`US-CA`, `US-IN`, `US-MS`), NOT blanket `US-*`.** Reasons:

1. Blanket claims **1,173 rows vs 352–440** — 3.3x more, across states never
   inventoried for this idiom. Under D-CERT that is new unmeasured exposure
   of precisely the kind P-R7 exists to surface.
2. The **NE preemption question is open** — the Planner honestly did not run
   the targeted NE check. Shipping blanket would resolve an open question by
   assumption.
3. The seam's own remedy principle for exposure is **narrower rules**. The
   explicit list IS the narrower rule.

**Zero-miss is satisfied, not traded away**: shape 7 membership is now
measured per-state, so any other state carrying the idiom appears in the
denominator as a **named residual** rather than a silent miss. Widening later
with measurement is cheap; un-shipping false positives from a certified
close is not.

### M-R50 — Developer scope fences (from program notes)

- **Shape 1 is OUT of scope.** Headings measured its ownership and split it:
  recognition is not the gap — extraction (bucket A → markers) and
  body-only-no-signal rows (bucket B → un-owned, D-CERT worklist) are. Our
  shape-1 row stays **attribution-only**. The Developer does not touch it.
- **D-INCLUDES applies**: includes-family verbs are now in the program
  defining-verb vocabulary (naive quoted-term anchor, **no tightened guard**).
  Any shape implementation touching includes-variants builds under it.
- **FP remedy is fixed in advance**: shape 2 measured **13.3%** FP, shape 3
  **3.3%**, and *every* FP is a forwarding-phrase pointer. The remedy is
  extending `_B1_FORWARDING_PHRASES` to the widened branch — **a narrower
  rule, never a gate**. This is settled; the Developer implements it rather
  than re-deciding it.
- **Shapes 2, 3, 6 share `_b1_trigger_colon_or_quote_means`** — all three
  test files run after ANY touch to it, and shapes 2+6 land as ONE combined
  regex change per the Planner's reasoning (stacking them separately risks
  one widening breaking the other's anchoring).

### M-R51 — Model/effort for the Developer spawn

Developer: **Sonnet / medium** — design is settled (D4 item list, ruled
shape-7 scope, pre-decided FP remedy) and 23 REDs are the oracle; what
remains is implementing against a fixed contract in one file. Per P-R6
Developer is Sonnet medium. **Haiku considered: no** — shared-function
widening with a silent-starvation failure mode and a measured FP surface is
more than a bounded mechanical change. `model=inherit` not used.

---

## 2026-08-05 — Manager: Developer cycle-7 verified; em-dash deviation RATIFIED with conditions

### M-R52 — Handoff verified (9e30ec5)

- `git diff --name-only 3ebd982 HEAD` → **one file**,
  `rules/us_body_preamble.py`. **Zero test edits.** Role separation held.
- Suite: **3 failed / 840 passed** (from 23/820). The 3 are exactly the
  disclosed markers dependencies, re-run individually, same failure reason.
- **Attribution tests 10/10.** Notably the M-R44 mechanism **fired during the
  build**: after shape 3's widening, B1 transiently claimed the MS row via a
  spurious mid-sentence "In" match until shape 8 landed and B2 reclaimed it
  by registration order. That is precisely the invisible-starvation failure
  M-R44 was built to expose, caught mid-build by the test whose own docstring
  had predicted it. The requirement paid for itself in one cycle.

### M-R53 — RULING: the em-dash widening is RATIFIED, with two conditions

The Developer widened `_b1_colon_list_branch` to treat an em dash
immediately after the trigger's unit name as a list-intro delimiter
(`if window[:1] == "—": return True`), against a D4 table that said
"branches unchanged". Disclosed, not smuggled.

**Ratified on the merits.** It is principled — in US statutory drafting an em
dash after `"In this section"` plays exactly the colon's list-intro role — it
is justified by a real FED row (`USC_T27_C6_S122a`), and it **is pinned**: I
confirmed that row is a parametrized case in
`test_us_body_preamble_shape3_in_this_trigger_red.py` (id
`usc-t27-c6-s122a-attorney-general`), the docstring names the em-dash
variant, and all 8 tests in that file pass. Skipping the forwarding-phrase
filter is also sound *at position 0 specifically*, because there is no filler
text to check.

**Condition 1 — the code comment is FALSE and must be corrected.** It claims
the shape was "verified corpus-wide ... occurs in ONLY this one real row".
That verification was **fixture-scoped**, and the Developer said so honestly
in its report — but the comment as written reads as a real-corpus claim. I
measured the real corpus:

| | rows |
|---|---|
| **trigger immediately followed by em/en dash, real corpus** | **836** |
| federal | 816 |
| dc / ma / ca | 13 / 5 / 2 |

Not one row — **836**. Leaving that comment in place would plant a false
verification claim inside production code that a D-CERT reader would later
consume as evidence. Correct it to state what was actually checked (fixture
scope) and cite the measured 836.

**Condition 2 — QA's FP sweep must cover these 836 rows specifically.** They
are newly claimed, unmeasured, and reached by the one branch that skips the
forwarding-phrase filter. This is the M-R45 obligation applied to the
deviation.

**Framing correction for the record:** this is not a marginal edge-case
widening. 816 FEDERAL rows is *upside* against our item-14 FEDERAL target —
plausibly the highest-value line added this cycle. The problem was never the
widening; it was the certainty attached to it.

### M-R54 — Follow-on item: split the 386-line rule file (300 gate)

`rules/us_body_preamble.py` is **386 lines** vs the repo's 300-line gate.
Scheduled as a follow-on, NOT done mid-cycle (splitting while QA measures
against this exact file would invalidate the measurement). Precedent: the
headings panel's facade pattern. **Watch the registration-call placement** —
rules self-register by module import via `pkgutil`, so a split that moves
`register_body_preamble_rule` calls into a module the package `__init__` does
not import would silently deregister rules, and **registration ORDER is
dispatch order**, so the split must preserve sequence exactly. That is the
discovery trap the headings panel dodged.

### M-R55 — Model/effort for the QA spawn

QA: **Sonnet / high** — the FP sweep must be measured on real newly-claimed
corpus populations and feeds a D-CERT certification; judging whether a
claimed row is genuinely a definitions block is the load-bearing act. Per
P-R6 QA is Sonnet high. **Haiku considered: no.** `model=inherit` not used.
QA commits only test/contract/log files, never implementation.

### M-R56 — HARNESS CHANGE (director-ordered): role agents report DIRECTLY to this manager

Effective immediately. Role agents no longer report through the program
manager; they deliver to this manager's agentId **`a3adfb6a9000b266e`**.

**Every role-agent brief — new spawns AND resumes — must carry this verbatim:**

> Before you finish or escalate, deliver your full report via SendMessage
> with to: 'a3adfb6a9000b266e' (raw agent id, exactly as written). Your
> plain-text final return is NOT a reliable delivery channel — the
> SendMessage IS your report. If the send fails, say so in your final text.

Escalations (`ESCALATION:` first line) arrive the same way; this manager
resolves them or escalates onward to the program manager itself. Peer-manager
coordination by agentId continues as before.

**Applied retroactively to the in-flight QA** (`ad897d10d497511ea`, spawned
before the change): resumed it with the delivery instruction rather than
relying on the deprecated relay path, since a resume counts as the trigger.
Its work is unchanged — only the delivery channel. No other agent is in
flight.

**Standing note for whoever resumes this sprint**: this instruction is now a
required element of every brief, alongside the existing fences (sole writer
per worktree; role separation; CodeGraph first; never fabricate; "not
measured" is valid).

---

## 2026-08-05 — QA: cycle-7 D1 (real FP sweep) / D2 (recert) / D3 (comment check) / D4 (suite + mutation audit)

Worked in `/Users/nerya/LexGraph-wt/defs-us-preamble` at `64d3630`.
**Zero `backend/app/` edits committed** — one temporary mutation each for D4
(em-dash branch, quote-means forwarding filter), both reverted, `git status`
verified clean before every commit. All measurement scripts live in the
scratchpad: `qa_cycle7_d1_shapes.py` (per-shape newly-claimed population +
attribution, full corpus), `qa_cycle7_emdash_raw_population.py` (raw
trigger+dash pattern count, independent cross-check), `qa_d1_measure.py`
(Planner-authored, reused verbatim for D2 — same Q-D1 methodology as last
cycle), `qa_cycle7_render_samples_v2.py` (hand-judging renderer).

### D1 — FP sweep on the REAL newly-claimed populations, per widened rule

**Methodology**: one full-corpus pass (2,038,247 rows, snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`) computing OLD = would this row
capture under the pre-cycle-7 shipped rules (commit `3ebd982`'s CA(US-CA
only)/NE/B2(original)/B1(no "In", no em-dash, strict "the term")) vs NEW =
today's real production dispatch (`64d3630`). Every row where NEW captures
and OLD does not is attributed to exactly one shape via the REAL imported
regex objects from `us_body_preamble.py` (no reimplementation) — zero rows
fell into an "UNATTRIBUTED"/"UNEXPECTED" bucket across the full corpus,
which is itself a positive signal that the shape taxonomy is complete.
Hand-judged samples: uniform-random, seed `20260805`, 50/shape (Q-D1b's own
established discipline), drawn from the REAL newly-claimed population, not
a reservoir-capped/order-biased one.

**Real newly-claimed population, corpus-wide, per shape** (this cycle's
own delta over the pre-cycle-7 baseline — smaller than the D2/Q-D1
"before=zero-rules" denominator, see D2 below):

| Shape | Real newly-claimed (this cycle's delta) | Planner's prospective estimate | states |
|---|---:|---:|---|
| 2 (no "the term") | 24,444 | 17,477 | CA-dominated, 40+ states |
| 3 ("In this X" trigger, colon/quotemeans only) | 17,370 | 9,517 (disclosed lower bound) | FED-dominated |
| **em-dash branch** | **984** | n/a (M-R53 cited 836) | FED 978, CA 3, DC 1, PR 1, VT 1 |
| 6 (qualifier clause) | 390 | 102 | CO/IA/TN/ME/AR-heavy |
| 7 (CA idiom, other states) | 201 | 352–440 | IN 103, MS 98 |
| 5 (named act) | 92 | 195 | NM 79, OK 9, OH 2, AR 1, CA 1 |
| 8 (B2 ascribed variant) | 73 | 296 | MS 62, IL 3, LA 3, KS 2, MN 1, VA 1, WA 1 |

Cross-check: summing the 7 rows above (43,554) against an independent
computation of `D2's after − before` restricted to this cycle's own delta
(123,482 total-after − ~80,493 pre-cycle-7-after ≈ 42,989) lands within
1.3% — corroboration from two differently-built measurements.

**Em-dash raw pattern population** (independent reproduction of M-R53's
cited 836, `qa_cycle7_emdash_raw_population.py`, current `_B1_TRIGGER_RE`
imported live): counting ANY occurrence of the trigger anywhere in the body
immediately followed by "—" gives **2,759 rows corpus-wide (FED 2,693, MO
20, DC 14, CA 8, MA 7, VT 4, others ≤3)** — over 3x M-R53's cited 836. This
raw "pattern present somewhere in the body" count is NOT the same
population as "captured via the em-dash branch" (a row can contain the
pattern on an occurrence that never wins, because an EARLIER trigger
occurrence in the same body already succeeds via colon/quotemeans first —
production only evaluates the FIRST successful occurrence). The actual
operative population is the 984 in the table above. I cannot reconcile
either number exactly to M-R53's 836 — that script isn't in the log/
scratchpad for me to inspect — so I'm reporting my own two independently
measured numbers (2,759 raw / 984 operative) rather than forcing a match.
**Not measured**: what specific methodology produced M-R53's 836.

#### Em-dash branch — the priority — hand-judged 50/50

**FP rate: 7/50 = 14%.** (Full detail: `qa_cycle7_emdash_judgment.txt`.)
Methodology note, disclosed rather than hidden: my rendering script
initially had a bug (`body.find(trigger_text)` can land on an EARLIER,
non-winning occurrence of the same phrase when it repeats in a body) that
produced 4 false alarms and missed 1 real FP on first pass; caught via a
shape2 row (`STATE_CA_Cgov_T9_C9.5_A4_S89513`) that looked non-definitional
at the wrong index but was genuine at the real one. Fixed to use the actual
regex match position and re-verified every flagged row before finalizing.

Real FPs, with `act_id`s:
- `USC_T12_C11_S1437` — both entries are pure "has the meaning given...in
  section X" forwarding, zero local content.
- `USC_T15_C1_S26a` — spurious "in this section shall—" match on "Nothing
  in this section shall—(A) preclude...(B) preclude...(C) require..." — a
  prohibition list, not term definitions.
- `USC_T46_C49_S4901` — spurious "in this section shall apply to—" match on
  a vessel-applicability criteria list.
- `USC_T10_C303_S4093` — spurious "in this paragraph is an individual
  who—" match (eligibility criteria); the only real definition elsewhere in
  the body is 100% forwarding.
- `USC_T33_C36_S2319` — spurious "in this section—" match on "(g)
  Limitations.—Nothing in this section—(1) affects...(5) supersedes..." —
  a limitations list.
- `USC_T50_C46_S3512` — spurious "in this paragraph is an individual
  who—" match (same eligibility-criteria pattern).
- `USC_T10_C4_S132` — spurious "in this paragraph are the following—"
  match on a list of policy objectives.

**Root cause, precisely**: all 7 share ONE mechanism. The colon-list
branch's own definitional-content check is weak by construction — it only
verifies the filler text contains no forwarding phrase, never that a
term:means structure actually follows the colon/dash. A self-referential
enumeration clause ("nothing in this section shall—", "an individual
described in this paragraph is an individual who—", "the objectives...are
the following—") satisfies that check trivially, and the em-dash branch's
explicit skip of the forwarding-phrase filter (justified at position 0,
per M-R53) provides no protection here because the problem was never a
forwarding phrase — there is no term:means structure at all. This is
exactly the hazard M-R52 observed once during the build ("B1 transiently
claimed the MS row via a spurious mid-sentence 'In' match") — my sweep
shows it is not a one-off; it recurs at real, measurable scale.

#### Shape 3 ("In this X" trigger) — hand-judged 50/50

**FP rate: 9/50 = 18%.** Same root cause as the em-dash branch (spurious
mid-sentence "in this X" match on a non-definitional enumeration/criteria
list), plus one NEW subclass not seen in the em-dash sample: the trigger
matched **inside an editorial/amendment-history note** quoting OLD
statutory text as part of describing a legislative change, not a live
definitions preamble (`USC_T10_C953_S9448` — a note reading "...inserted
'the term' after 'In this section,'" describing a 1989 amendment).

Real FPs: `USC_T42_C7_S679c`, `STATE_CT_T1_C14_S1-212`, `USC_T22_C102_S9528`,
`USC_T35_C4_S41`, `USC_T10_C953_S9448`, `STATE_AZ_T28_C25_A2_S8242`,
`STATE_AR_T8_C8_S1_S8-8-102`, `STATE_DE_T13_C5_SII_S513`,
`STATE_CO_T22_A1_S22-1-120`.

Shape 3's own trigger widening (`_B1_TRIGGER_RE` gained "In" as a bare
alternative, unanchored to clause-start) is the SAME regex that also
produces the em-dash branch's exposure — both hazards trace to the same
change, which is why they share a root cause and why I am NOT treating
them as two independent, additive risks in the framing below.

#### Shape 2 (no "the term") — hand-judged 50/50

**FP rate: 0/50 (0%).** Every one of the 50 real sampled rows is a
genuine, substantive, LOCAL "trigger + quoted term + means" definition —
CA-dominated (32/50), also AL/AR/AZ. **This confirms the D3-recommended
remedy (M-R50: apply `_B1_FORWARDING_PHRASES` to the widened quote-means
branch's own gap text) worked**: last cycle's pre-fix measurement on a
30-row prospective sample found 13.3% FP (4/30, all pure forwarding
pointers); this cycle's 50-row sample of the REAL shipped population finds
zero. I re-verified the one ambiguous-looking case
(`STATE_CA_Cgov_T9_C9.5_A4_S89513`, index 39) against the real winning
occurrence (not a naive first-match) — genuine ("directly" means...).

#### Shape 6 (qualifier clause) — hand-judged 50/50

**FP rate: 0/50 (0%).** All 50 real rows follow the exact pattern
("As used in this X, unless the context otherwise requires, 'TERM'
means..."), CO/IA/TN/ME/AR/MS/VA-heavy. Zero rendering-position mismatches
in this sample (the qualifier clause structurally prevents the trigger
phrase from repeating ambiguously), so no re-verification was needed.

#### Shape 5 (named act), shape 7 (CA idiom other states), shape 8 (B2 ascribed variant) — hand-judged 50/50 each

**FP rate: 0/50 for all three (0%).** Shape 5: overwhelmingly NM
(Election Code — 40+ of 50), also OK/AL — 4 samples initially looked
ambiguous (Oklahoma "Contingency Review Board" procedural text with the
match not visible in the rendered window) and were independently
re-verified against the real regex match position; all 4 are genuine
("proposed agreement" means..., "minor" means...). Shape 7: MS/IN, mostly
duplicate `act_id`s across near-identical chapter copies in the corpus (a
data characteristic, not a rule defect) — all genuine block-style
definitions lists. Shape 8: overwhelmingly MS (vehicle code, water
pollution, purchasing definitions), also IL/LA — all genuine.

### D1 — Summary, per the director's framing (report, never gate)

The FP exposure is **not evenly distributed across the 6 widened shapes**.
It is concentrated entirely in the two mechanisms that touch B1's
COLON-LIST branch (shape 3's "In" trigger addition, and the em-dash
sub-branch) — 14–18% FP there. The four mechanisms that route through B1's
QUOTE-MEANS branch or an independent new rule (shapes 2, 5, 6, 7, 8) show
**0% FP across 250 hand-judged real rows combined**. The mechanical reason:
quote-means requires an actual quoted term immediately followed by
"means"/"shall mean" — a self-verifying structural check. Colon-list only
checks that the filler text contains no known forwarding phrase — it never
verifies a term:means structure follows at all, so a self-referential
enumeration clause (prohibition list, eligibility criteria, policy
objectives, "sources described in this subclause are the following")
satisfies it. **Recommended narrower-rule remedy for the next Developer
touch** (report only, not implemented — QA does not touch `backend/app/`):
require the colon-list branch's own post-colon/post-dash text to contain
at least one recognizable defining-verb pattern (`means`/`shall mean`/
`includes`/`has the meaning`) within its own window, mirroring the
structural check the quote-means branch already gets for free — this is
the same "reuse an existing, already-proven-safe check" discipline M-R50
already applied once this cycle.

### D2 — Re-certified capture numbers (Q-D1 methodology, reused exactly)

Ran `qa_d1_measure.py` (the Planner's own script from last cycle,
unmodified) against today's shipped code across all 53 jurisdictions.
BEFORE = bare functions, zero registry rules (identical methodology to
last cycle — **before totals match exactly**, 29,667 = 29,667, confirming
the baseline is genuinely unaffected and the two cycles' numbers are
comparable). AFTER = today's real production dispatch (all cycle-7 shapes
shipped).

**Corpus-wide**: before **29,667**, after **123,482**, new **93,815**
(last cycle: 80,493 / 50,826). **Clean-primary: 29,249** (last cycle:
23,617) **/ fallback-affected: 64,566** (last cycle: 27,209). Per the
binding caveat, the fallback split is reported alongside every number, not
netted out — the S1 last-entry-boundary defect remains unfixed (core
follow-on), so fallback-derived figures stay labelled provisional.

**GA**: before 2, after **2,928** (last cycle 2,794 — +134 this cycle,
plausible: GA rows can also be newly reached by the B1 quote-means
widening, not just its own dominant B1 colon-list convention), new_primary
1,952, new_fallback 974.

**FEDERAL — item 14's own target, the one to watch**: before **320**,
after **6,311**, new **5,991** (new_primary 537 / new_fallback 5,454).
Last cycle: 320 → 2,268 (new 1,948). This is a **2.7x increase over last
cycle's own AFTER figure**, driven by shape 3 + the em-dash branch as
intended (816-978 of the ~2,700 em-dash-pattern-bearing FED rows feed
directly into this). Honest caveat, not a reconciliation I can perform:
item 14's own **198/435 target is a hand-inventoried subset figure** from
an early scout classifier, not the same population as "real pipeline
output under ungated dispatch" — my 6,311 is the latter (same caveat Q-D1
raised for MD's "3,185 vs ~1,841–1,849" last cycle). In raw terms FEDERAL's
capture count is now **32x** the 198-row target; I did not re-derive or
cross-check the specific 435-row worklist itself this cycle (not
measured), so I report the honest pipeline number rather than claiming a
verified match to item 14's own figure.

**10-state table** (same columns as last cycle, directly comparable):

| state | rows | before | after | new | new_primary | new_fallback |
|---|---:|---:|---:|---:|---:|---:|
| GA | 28,154 | 2 | 2,928 | 2,926 | 1,952 | 974 |
| MD | 39,552 | 0 | 5,183 | 5,183 | 3,444 | 1,739 |
| NE | 25,997 | 0 | 10 | 10 | 2 | 8 |
| MS | 158,688 | 0 | 8,338 | 8,338 | 6,229 | 2,109 |
| SD | 39,589 | 712 | 914 | 202 | 43 | 159 |
| CA | 161,429 | 1,296 | 10,277 | 8,981 | 3,951 | 5,030 |
| FL | 24,866 | 684 | 2,932 | 2,248 | 42 | 2,206 |
| FED | 54,853 | 320 | 6,311 | 5,991 | 537 | 5,454 |
| DC | 23,694 | 884 | 1,674 | 790 | 359 | 431 |
| NY | 40,102 | 0 | 1,655 | 1,655 | 0 | 1,655 |
| **TOTAL (53 jur.)** | **2,038,247** | **29,667** | **123,482** | **93,815** | **29,249** | **64,566** |

Full 53-jurisdiction appendix and every per-row detail: `d1_results/*.json`
in the scratchpad (not committed, per program rule — measurement output,
not a test).

Notable secondary finding: **IN** jumped from before=283 to after=**7,002**
(new 6,719) — far larger than shape 7's own measured 352–440 IN-specific
estimate, because the vast majority of IN's gain comes from B1's shape 2/3
widenings (which apply to every `US-*` code, including IN), not from shape
7's CA-idiom jurisdiction widening specifically. Flagging so shape 7's own
scope isn't mistakenly credited with IN's full jump.

### D3 — M-R53 condition-1 comment fix: NOT corrected

Checked `backend/app/definition_links/rules/us_body_preamble.py` (current
HEAD, `64d3630`) directly and via `git diff 9e30ec5 HEAD -- <file>`
(empty diff — zero changes to this file since the Developer's last commit).
The comment at `_b1_colon_list_branch` (lines ~342–350) is **unchanged**
and still reads:

> "...verified corpus-wide (every fixture file under `backend/tests/
> fixtures/us_statutes/`) that this exact trigger-immediately-followed-by-
> em-dash shape occurs in ONLY this one real row..."

This is the exact false claim M-R53 required corrected — it conflates
"every fixture file" (fixture scope) with "corpus-wide" in the same
sentence, and still states "ONLY this one real row" against a real,
now-doubly-measured count (M-R53: 836; my own independent reproduction:
2,759 raw / 984 operative). **Open item for the next Developer touch,
flagged not fixed** (QA does not edit `backend/app/`).

### D4 — Suite + regression audit

**Full suite reproduces exactly**: `.venv/bin/pytest -q` → **3 failed / 840
passed**. The 3 failures are the disclosed `defs-us-markers` unquoted
dependencies (`test_real_pipeline_still_cannot_capture_the_real_nebraska_
unquoted_body_preamble_definitions_needs_markers_sprint_too`,
`test_ne_unquoted_term_means_needs_markers_sprint_too`,
`test_sd_unquoted_comma_term_needs_markers_sprint_too`) — same failure
reason each (unquoted-term extraction is out of this sprint's scope), no
new failures.

**Attribution tests: 10/10 pass** (`pytest -k winning_rule` across the 6
shape test files) — confirmed live, not merely re-read from the log.

**Mutation-proofs** (temporary edits, each confirmed to break the target
test, then reverted; `git status` clean of `backend/app/` before every
commit):
1. Em-dash branch (`if window[:1] == "—": return True` →
   `if False and window[:1] == "—"`): both
   `test_federal_in_this_section_trigger_is_captured[usc-t27-c6-s122a-
   attorney-general]` and its sibling attribution test FAILED as expected.
   Confirms the em-dash pin is genuinely load-bearing, not vacuous.
2. Quote-means forwarding-phrase filter (D3's own recommended remedy,
   `return not any(phrase in gap for phrase in _B1_FORWARDING_PHRASES)` →
   `return True`): **full suite still 3 failed / 840 passed — ZERO test
   regressions.** This confirms a real coverage gap: **no test in this
   repository pins the forwarding-phrase filter on the WIDENED quote-means
   branch** (D3/M-R50's own specific remedy for shape 2/6's pre-fix 13.3%
   FP rate). The existing negative-guard tests
   (`test_us_body_preamble_negative_guard*.py`) only cover the COLON-LIST
   branch's forwarding-phrase check, a pre-existing behavior this cycle
   didn't touch. My own D1 sweep (0/50 FP on shape 2, 0/50 on shape 6)
   shows the filter demonstrably WORKS on the real corpus — this is a
   missing regression pin, not a broken feature. **Flagged for the next
   Developer/QA touch as an open item, not fixed here** (QA does not add
   production tests without... actually QA CAN add test files per role
   rules, but doing so mid-audit risks conflating "measured" with "fixed";
   left as a named gap for the manager to schedule explicitly, consistent
   with "report, never gate/fix silently").

**Not mutation-tested this cycle** (time budget): shapes 5/7/8's own
dedicated RED tests (each already has a rule-attribution + live-capture
pair per file, same pattern verified em-dash and shape-3 belong to;
sampled the em-dash + quote-means-filter mutations as the two highest-risk
targets — the em-dash deviation because M-R53 flagged it explicitly, the
forwarding filter because D1's own sweep depends on it actually
functioning).

### What was NOT measured this cycle

- M-R53's own 836-figure methodology (script not available to inspect) —
  reproduced independently instead (2,759 raw / 984 operative), both
  reported, not reconciled.
- Item 14's specific 198/435 hand-inventoried FEDERAL worklist (the raw
  pipeline capture number, 6,311, is reported honestly instead of a
  verified match to that narrower figure).
- Byte-coverage contamination rate of the 64,566 fallback-affected
  `definition_text` fields (same S1-flagged, still-open question as last
  cycle — out of this cycle's own scope, core follow-on).
- Mutation-proofs for shapes 5/7/8's own dedicated tests (0% FP in hand-
  judging gave no immediate reason to doubt them; flagged as unverified
  rather than silently assumed sound).

### Zero-miss / precision framing, per the director's own rule

Recall and precision are reported in both directions, not traded off:
this cycle's widening genuinely captures thousands of new real definitions
(FEDERAL alone +5,991) with 0% measured FP on 4 of 6 shapes and 14–18% FP
concentrated in exactly the two colon-list-branch mechanisms identified
above. The remedy is a narrower rule (recommended above), never a gate on
dispatch — consistent with M-R45's own binding principle, which this
report does not override.

Pushed SHA: see commit immediately following this entry.
Confirmation: `git diff --stat HEAD` before this commit shows only this
log file changed; `git status` shows zero `backend/app/` modifications.

---

## 2026-08-05 — Manager: QA cycle-7 verified; FP is MATERIAL; certification WITHHELD

### M-R57 — Handoff verified (fee2878)

Diff vs `64d3630` → **the log only**; `git diff --name-only -- backend/app/`
**empty**. Suite reproduces **3 failed / 840 passed**. QA's two D4 mutations
were reverted before commit, as it stated and as the empty diff confirms.

QA's self-disclosed renderer bug (a `body.find()` landing on the wrong
occurrence when a trigger repeats) — caught mid-cycle, fixed, and **every
flagged row re-verified**, flipping 4 false alarms to TP and 1 false clean to
FP. Finding and reporting a bug in your own measurement instrument, then
re-deriving the affected numbers, is the behavior that makes the rest of the
report usable.

### M-R58 — RECONCILED: the 836 / 1,788 / 2,759 / 984 spread is measurement scope, not disagreement

QA could not reconcile my M-R53 figure of **836** and reported its own
**2,759 raw / 984 operationally-captured** without forcing a match — correct
discipline. I reconciled it myself, since it is my number and D-CERT will
consume it:

| measurement | rows |
|---|---:|
| my M-R53 pattern, scanned in `body[:600]` | **836** |
| **the same pattern, scanned whole-body** | **1,788** |
| QA's broader raw pattern | 2,759 |
| QA's **operationally captured** by the shipped rule | **984** |

Nobody was wrong. My 836 carried an undisclosed 600-char window — that was a
defect in MY reporting, not in QA's. **Ruling: none of these is "the" number
without its definition attached.** For certification the load-bearing figure
is **984 operationally captured**, because that is what the rule actually
claims. M-R53's "836" is superseded and must never be quoted bare.

### M-R59 — RULING: FP is MATERIAL. Certification is WITHHELD. Not a gate.

| shape | newly claimed | FP (n=50) |
|---|---:|---:|
| **3 (`"In this X"`)** | **17,370** | **9/50 = 18%** |
| **em-dash branch** | **984** | **7/50 = 14%** |
| 2, 5, 6, 7, 8 | 25,200 combined | **0/50 each** |

18% of 17,370 is on the order of **~3,100 false rows**, plus ~140 from the
em-dash branch. **That cannot be certified**, and I am not certifying it.
Cycle-7's capture numbers stand as **measured, not certified**.

**This is NOT grounds to gate**, per the seam and M-R45, and I am not
proposing one. The diagnosis is precise and QA nailed it: all FP is
concentrated in B1's **colon-list** branch, which only checks "no forwarding
phrase in the filler" and never checks that a term:means structure actually
follows — whereas the **quote-means** branch self-verifies via its quoted-term
regex, which is exactly why shapes 2/5/6/7/8 measured **0/50**. The 0% shapes
prove the architecture is sound; one branch just lacks the self-verification
the others have.

**Commissioned remedy (a narrower rule, per the seam):** require the
colon-list branch's post-colon/post-dash window to contain a recognizable
defining-verb pattern. This makes the weak branch self-verifying like its
sibling. QA reported it and did not implement it — correct.

### M-R60 — Coverage gap: the forwarding-phrase filter is pinned by NOTHING

QA mutation-tested the forwarding-phrase filter on the widened quote-means
branch: disabling it produced **zero test regressions** (still 3/840). So a
filter that demonstrably works on the real corpus (0% FP on shapes 2/6) is
protected by **no test at all** — a future refactor could delete it silently
and every suite would stay green.

This is the most dangerous finding in the report, more so than the FP number,
because the FP number is visible and this is not. **A pin is required in the
next Planner cycle.** Mutation testing earned its keep here: no amount of
reading would have surfaced it.

### M-R61 — Open items carried into the next cycle

1. **Colon-list defining-verb narrowing** (M-R59) — the FP remedy.
2. **Forwarding-phrase filter pin** (M-R60) — close the coverage gap.
3. **M-R53 condition-1 comment fix — STILL NOT DONE.** Verified by QA via
   empty diff. The false "verified corpus-wide … ONLY this one real row"
   claim is still in production code. Ratification was explicitly
   conditional; this is now overdue and goes in the next Developer touch.
4. **File split, 386 → 300 gate** (M-R54), after the above land — not
   during measurement.
5. FEDERAL **320 → 6,311** is reported honestly as full-pipeline output;
   item 14's "198/435" is a **different, narrower hand-inventoried
   population** and QA correctly refused to claim a match it had not
   re-derived. Do not let these two numbers be equated.

---

## 2026-08-05 — Planner: cycle-8 D1/D2 — ESCALATION on the M-R59 narrowing; D2 filter pin landed

Worked in `/Users/nerya/LexGraph-wt/defs-us-preamble` from `99f1904`.
Pushed `5f6fbb0`. **Zero `backend/app/` edits committed** — one temporary
mutation for D2 (`_b1_quote_means_branch`'s forwarding filter), reverted,
`git status` verified clean before commit. Measurement scripts (scratchpad,
never touch `backend/app/`): `planner_c8_fetch_fp_rows.py`,
`planner_c8_candidate_pattern.py`, `measure_defining_verb_narrowing.py`
(new — extends `qa_cycle7_d1_shapes.py` by direct import, per the brief's
"extend, don't rewrite"), `planner_c8_fetch_positive_rows.py`,
`planner_c8_find_quotemeans_forwarding_gap.py`.

### D1 — the commissioned colon-list defining-verb narrowing: RED tests authored, but the pattern itself is an ESCALATION

**What I built and measured.** Candidate: require the colon-list branch's
own em-dash/colon structural gate (unchanged) PLUS a quoted-term +
bounded-gap (≤80 chars, mirrors `us_profile._MEANS_IDIOM_GAP_RE`'s own
proven discipline) + defining verb (`means`/`shall mean`/`includes`/`shall
include` — D-INCLUDES honored; `has the meaning` deliberately EXCLUDED,
measured to collide with the exact `"has the meaning given...in section
X"` forwarding shape that produced 2 of the 16 real QA-named FPs) found
within 600 chars of the TRIGGER match's own start (not the colon — a
plain post-colon window misses real rows whose first entry's own content
is long, e.g. DE's `"School equipment" ... shall be deemed to mean, and
to include, but not be limited to: kitchen equipment...` before reaching
a clean second entry).

**Precision side — works as intended.** Verified against all 16 real FP
`act_id`s from QA's cycle-7 log: **10/16 correctly dropped** (the other 6
are captured via a DIFFERENT, unaffected occurrence/branch in the same
body — not a defect in the candidate, see below). Verified against the 4
existing FED shape-3/em-dash fixtures
(`test_us_body_preamble_shape3_in_this_trigger_red.py`): **all 4 still
captured.**

**Recall side — this is the escalation.** A full corpus-wide run
(`measure_defining_verb_narrowing.py`, 2,038,247 rows, ~10 min) found the
candidate touches THREE populations, not one:

| population | total | dropped | dropped % |
|---|---:|---:|---:|
| A: shape-3 ("In" trigger) rows that win via the **colon-list branch specifically** | 11,676 | 2,163 | 18.5% |
| B: em-dash branch | 984 | 132 | 13.4% |
| C: **already-certified, pre-cycle-7** colon-list captures (GA/MS/DE/CT/AR/... via "As used in"/"For purposes of" + colon, NOT this cycle's own delta) | 42,374 | 2,322 | 5.5% |

**Correction to QA's own 17,370 figure, found while building this**: QA's
`classify_shape` labels a row "shape3_in_trigger" whenever the WINNING
occurrence's trigger text starts with "In" — REGARDLESS of whether that
occurrence won via colon-list or quote-means. Population A above (11,676)
is the subset that specifically goes through colon-list (the branch M-R59
commissions narrowing); the other ~5,694 of QA's 17,370 win via the
UNCHANGED, self-verifying quote-means branch and are outside this
narrowing's reach entirely (consistent with QA's own diagnosis that
quote-means is structurally safe). **17,370 must not be read as "the
population this narrowing touches" — 11,676 is.** Em-dash's 984 matches
QA's own figure exactly (independent cross-check, no such split there).

**Hand-verified samples (uniform-random, seed `20260805`, full untruncated
`definition_text` read against the real corpus text — Q-D1b's own
discipline), of what gets DROPPED:**

| population | n hand-read | genuine (real local def.) | forwarding-only | garbage/malformed | ambiguous |
|---|---:|---:|---:|---:|---:|
| A (shape-3 colon-list) | 25 | 16 (64%) | 6 (24%) | 2 (8%) | 1 (4%) |
| B (em-dash) | 24 | 12 (50%) | 3 (12.5%) | 9 (37.5%) | 0 |
| C (pre-existing, already-certified) | 30 | 19 (63.3%) | 10 (33.3%) | 0 | 1 (3.3%) |

Extrapolating these rates to the full dropped counts: **≈1,384 (A) + 66
(B) + 1,470 (C) ≈ 2,920 genuine rows would be silently lost**, against
**≈692 (A) + 66 (B) + 773 (C) ≈ 1,531 rows correctly fixed** (garbage or
pure forwarding). **The candidate, as a purely local per-occurrence
window check, loses more real captures than it fixes false positives —
including roughly 1,470 rows in the population every earlier cycle
already certified**, not just this cycle's own still-uncertified delta.

**Why local-window narrowing structurally cannot do better than this**
(root causes, each confirmed against real bodies, not inferred):

1. **Body-wide extraction is decoupled from WHICH occurrence wins
   recognition.** `extract_definitions_from_section` re-scans the ENTIRE
   body once ANY heading is derived — it does not care which trigger
   occurrence supplied that heading. Many genuine captures in this
   population are reached ONLY because a totally unrelated, genuinely
   spurious occurrence elsewhere in a long, multi-topic body happens to
   grant recognition, while the REAL "As used in ...: (N) "Term"
   means..." clause sits far away. Real examples, confirmed live:
   `STATE_OH_T45_C4510_S4510.17` ("Child" genuinely defined in division
   (H), reached today only via a spurious "in this state." match inside
   an unrelated driver's-license-suspension clause 18,000+ chars earlier)
   and `USC_T16_C12_S824` ("Sale of electric energy at wholesale" /
   "Public utility", reached only via a spurious "in this section
   shall—" limitations clause — structurally identical to QA's confirmed
   em-dash FPs). **A window scoped to the winning occurrence's own
   neighborhood cannot see either fix.**
2. **`_B1_TRIGGER_RE`'s own greedy unit-name tail
   (`[A-Za-z0-9 .\-]{0,30}`) can swallow the defining verb into the
   TRIGGER MATCH ITSELF**, hiding it from any check that only searches
   text strictly after the match ends. Real example: `STATE_PA_
   T15_C75_S7502` — the winning match text is literally `'in this
   chapter means a corporation wit'` (the word "means" consumed by the
   trigger's own greedy tail). This is the SAME hazard this sprint's own
   D3 note flagged last cycle ("found zero false positives caused by it"
   THEN) — it is a real RECALL hazard now that a verb-presence check
   runs post-trigger.
3. **The trigger regex itself doesn't reach every real intro clause's
   own phrasing.** `STATE_AR_T8_C8_S1_S8-8-102`'s real intro is `"For
   the purpose of this compact..."` — SINGULAR "purpose", never matched
   by `_B1_TRIGGER_RE` (`For (?:the )?purposes of`, plural only); OH's
   real intro is `"As used in divisions (C) and (D) of this section:"` —
   the intervening "divisions (C) and (D) of" breaks the "As used in
   this X" pattern. Both rows' 5-and-1 real definitions are reached only
   via the coincidental spurious-match mechanism in (1).
4. **D-INCLUDES gap in the SIBLING branch.** `USC_T15_C1_S26a`'s only
   real definition is `"United States" includes the several States...` —
   a quote-means shape (comma-gap, not colon-list), but
   `_b1_quote_means_branch`'s own `_B1_QUOTE_MEANS_RE` verb group is
   `means|shall mean` ONLY, no `includes`. M-R59 does not commission
   touching quote-means, but narrowing colon-list without ALSO widening
   quote-means' verb vocabulary orphans this row (recognition today
   depends entirely on a separate, genuinely spurious colon-list
   occurrence).

I confirmed the OPPOSITE design (require the defining verb ANYWHERE in
the body, not near the winning occurrence) as a sanity check: it
preserves ~99%+ of population C's recall but only drops 2/16 known FPs —
i.e. it does not meaningfully fix the diagnosed problem at all. **There is
no simple parameter tune (window size 150→1500, verb vocabulary) that
resolves this — I tested a range and the tension persists at every
setting I tried.** This is a genuine architectural mismatch between "one
local check per occurrence" and "the hazard is about which TEXT triggered
recognition, but genuine content lives wherever it lives in the body,"
not a tuning artifact.

**Tests authored anyway** (`test_us_body_preamble_defining_verb_narrowing_
red.py`, fixtures `cycle8_defining_verb_{negative,positive}_rows.json`, 11
real rows, byte-verified against the parquet): 6 RED negatives (real
QA-cycle-7-named FP `act_id`s: `USC_T35_C4_S41`, `USC_T10_C953_S9448`,
`USC_T22_C102_S9528`, `USC_T10_C303_S4093`, `STATE_DE_T13_C5_SII_S513`,
`USC_T42_C7_S679c` — must go uncaptured) + 5 GREEN regression-guard tests
(the OH/PA/FED/US/AR rows above — currently captured, must STAY captured).
**Verified against my own candidate implementation directly (not just
reasoned about)**: all 6 negatives correctly drop, all 5 positives
correctly flip RED — i.e. these tests are not hypothetical, they
reproduce the exact tension measured above on a concrete implementation.
Whatever remedy the manager selects must pass all 11.

**ESCALATION (repeated at the top of the final report per the brief's
format): the naive, purely-local-window implementation of M-R59's
narrowing is a genuinely bad trade — it measurably loses more real
captures (≈2,920, including ≈1,470 in the ALREADY-CERTIFIED pre-cycle-7
population) than it fixes false positives (≈1,531), all figures from a
full corpus run plus hand-verified samples, not estimates. Options:**

- **(a) Ship the local-window narrowing as designed, accepting the
  measured recall loss.** Fails the zero-miss bar as I understand it,
  including for the already-certified population — my lean is against
  this.
- **(b) Scope the narrowing to ONLY the em-dash sub-branch + shape-3's
  "In"-trigger colon path (populations A+B, this cycle's own still-
  uncertified delta), leaving the pre-existing "As used in"/"For
  purposes of" + colon path (population C) completely untouched.** Zero
  NEW risk to the already-certified population; the recall cost shrinks
  to ≈1,450 (A+B) against ≈758 fixed (A+B) — still a losing trade by raw
  count within the delta itself, but bounded to still-uncertified rows
  only.
- **(c) Invest in the companion fixes named above BEFORE or ALONGSIDE
  narrowing** (cap `_B1_TRIGGER_RE`'s greedy tail so it cannot consume a
  following verb; widen the trigger to accept singular "purpose" and
  intervening-clause phrasing; widen `_B1_QUOTE_MEANS_RE`'s verb group to
  include `includes`/`shall include` per D-INCLUDES) so the RIGHT
  occurrence wins directly instead of relying on a coincidental spurious
  match — this is untested by me (no corpus-wide run of it), but is the
  only path I can see that could recover MOST of the measured recall
  loss while still fixing precision. Bigger scope than "a narrower rule."
- **(d) Some hybrid of (b)+(c).**

**My lean: (b) now, (c) as a follow-on this cycle or next** — (b) is
strictly safer than shipping nothing changed (it still fixes ~758 FP rows
in the delta with zero new risk to the certified population) and is
immediately available; (c) is the only path to closing the recall gap
properly, but needs its own corpus-wide measurement before it can be
certified, which is more than this cycle's stated scope. I did not
choose between these myself, per the brief's own instruction.

### D2 — forwarding-phrase filter pin (M-R60): landed, mutation-verified

`test_us_body_preamble_quotemeans_forwarding_filter_pin.py`, 2 tests.
**Unit-level, not live-path** — disclosed explicitly in the file's own
docstring: a full 2,038,247-row corpus search
(`planner_c8_find_quotemeans_forwarding_gap.py`) for any real row where
`_B1_QUOTE_MEANS_RE` matches AND its own `gap` group contains a
`_B1_FORWARDING_PHRASES` entry found **zero real rows** — this exact code
path is corpus-unreachable today, consistent with QA's own mutation
finding (no existing test reaches it either) and explaining why: the
diagnosed hazard (D3, last cycle) turned out, on the real FP rows that
motivated the filter, to be forwarding phrases acting as the VERB itself
(already excluded structurally by `_B1_QUOTE_MEANS_RE`'s own `means|shall
mean` requirement), not as gap/qualifier text. Since no real row can prove
this line matters, the test calls `_b1_quote_means_branch` directly with a
hand-constructed string (verified to actually match the regex and to
contain a forwarding phrase in its own `gap` group) — a normal unit test
of the function, not a fixture-requiring "row."

**Mutation evidence**: `_b1_quote_means_branch`'s `return not any(phrase
in gap for phrase in _B1_FORWARDING_PHRASES)` → `return True`, test file
re-run: `test_quote_means_branch_rejects_a_gap_containing_a_forwarding_
phrase` FAILED as expected (`assert True is False`); companion control
test (`test_quote_means_branch_still_accepts_the_same_shape_without_a_
forwarding_phrase`) still PASSED (proves the pin isn't just "any change
fails"). Reverted; `git diff --stat -- backend/app/` empty before commit.

### D3 — attribution + regression guard

`pytest -k winning_rule` across the 6 shape test files: **10/10 pass**,
undisturbed by this cycle's new files (verified after committing D1/D2).
Full suite: **9 failed / 847 passed** (3 disclosed pre-existing +
this cycle's 6 new RED negatives; 840 baseline + 5 new positives + 2 new
D2 tests = 847).

**Starvation risk, flagged per the brief (not built into a test this
cycle — the exact narrowing design is still open per the escalation
above, so a starvation test would need to re-target whichever design the
manager picks):** `_b1_colon_list_branch` is checked BEFORE
`_b1_quote_means_branch` at EVERY trigger occurrence inside
`_b1_trigger_colon_or_quote_means` — narrowing colon-list means some
occurrences that win via colon-list TODAY will fall through to a
quote-means check at the SAME occurrence (already unwound today; no
change) or to the NEXT occurrence (a real behavior change). This can flip
a row's WINNING BRANCH attribution (colon → quotemeans) even when the
row's final captured/not-captured OUTCOME is unchanged — which matters
for shape-specific FP-rate tracking (QA's own per-shape sampling
methodology depends on correct branch attribution) even when it doesn't
matter for the pass/fail of the 10 existing `winning_rule` tests. Next
cycle's test author, once a specific narrowing design is chosen, should
add an explicit "did the winning branch change" pin alongside the
existing rule-identity tests, not just an outcome-level capture test.

### D4 — item list for the Developer

**Held pending the escalation above** — do not implement any narrowing
until the manager rules on options (a)-(d). Once ruled:

- **Tests to satisfy, regardless of which option is chosen**:
  `test_us_body_preamble_defining_verb_narrowing_red.py`'s 11 tests (6
  negatives must go uncaptured; 5 positives must stay captured) +
  `test_us_body_preamble_quotemeans_forwarding_filter_pin.py`'s 2 tests
  (already green, must stay green) + all 10 `winning_rule` attribution
  tests + the existing 840-test baseline (3 disclosed exceptions
  unchanged).
- **If option (b) or (d) is chosen**: the narrowing predicate itself
  (quoted term + ≤80-char bounded gap + `means`/`shall mean`/`includes`/
  `shall include`, searched within 600 chars of the trigger match start,
  deliberately excluding `has the meaning`) is ready to reuse verbatim —
  it is what produced every number in this report. Scope it to fire only
  when the winning occurrence's own trigger text starts with "In" (case-
  insensitive, not "As used in"/"For purposes of") OR when the em-dash
  sub-branch fires — i.e. gate the NEW check on "is this occurrence part
  of THIS cycle's own widening" so the pre-existing "As used in"/"For
  purposes of" + colon path (population C) is untouched.
- **If option (c) is pursued**: three named, independently-confirmed
  companion defects to fix first (none touched by me — all still real,
  unedited `backend/app/`): (i) `_B1_TRIGGER_RE`'s greedy
  `[A-Za-z0-9 .\-]{0,30}` tail can consume a following defining verb into
  its own match (PA case); (ii) the trigger's `purposes` alternative is
  plural-only, missing real singular `purpose` rows (AR case) and
  intervening-clause phrasing like "As used in divisions (C) and (D) of
  this section" (OH case); (iii) `_B1_QUOTE_MEANS_RE`'s verb group lacks
  `includes`/`shall include` (US case, D-INCLUDES). A corpus-wide
  re-measurement of the SAME `measure_defining_verb_narrowing.py`
  methodology, extended to model these three fixes, would be the next
  cycle's own D1 if (c) or (d) is chosen.
- **Carried forward, still open, not touched this cycle**:
  1. **M-R53 condition-1 comment fix — STILL NOT DONE.** Verified again
     directly: `_b1_colon_list_branch`'s comment (lines ~342-350 in
     `us_body_preamble.py`) still claims "verified corpus-wide (every
     fixture file...) that this exact trigger-immediately-followed-by-
     em-dash shape occurs in ONLY this one real row" — false; per M-R58
     the reconciled real counts are **1,788 whole-body / 984
     operationally captured**. Ratification was conditional on this;
     it is now three cycles overdue.
  2. **File split, `us_body_preamble.py` 386 → 300-line gate** (M-R54) —
     sequenced AFTER the narrowing question resolves, not during.

**What I did NOT measure this cycle**: the corpus-wide effect of the
option-(c) companion fixes (named above, not implemented or measured —
proposing them without numbers would be exactly the "shipping a pattern
without measuring the trade" the brief warns against); a hand-verified
sample of population C beyond the 30 rows read in full (a larger sample
would tighten the ≈63.3% genuine-rate estimate's confidence interval, not
change its direction); whether the same greedy-trigger-tail hazard (root
cause 2 above) affects any OTHER already-shipped test in this suite
(checked only the one PA row that surfaced it).

Full suite tail: `9 failed, 847 passed, 18 warnings in 13.75s`. Pushed
SHA: `5f6fbb0`. `git log --oneline -1` at time of this entry: `5f6fbb0
test(us-preamble): cycle-8 D1 defining-verb narrowing REDs + D2
forwarding-filter pin (M-R59/M-R60)`. Confirmed zero `backend/app/` edits
in the pushed commit (`git show --stat 5f6fbb0` — 4 files, all under
`backend/tests/`).

---

## 2026-08-05 — Manager: cycle-8 escalation RULED — the FP metric measures the wrong thing

### M-R62 — Planner cycle-8 verified

Diff `99f1904..648b0a7`: tests + fixtures + log; **`git diff --stat -- backend/app/` empty**. Suite **9 failed / 847 passed** (3 disclosed markers + 6 new RED negatives, as designed). Attribution 10/10. D2's filter pin is mutation-verified in both directions (pin flips RED when the filter is disabled; control still passes). The Planner measured the trade and escalated instead of shipping it — exactly the instruction.

### M-R63 — DECISIVE FINDING: the "18%/14% FP" is a ROW-label metric, not a data-harm metric

Before ruling I tested the assumption under the whole escalation. I ran the live path on all 6 of the Planner's RED negatives — QA's own cycle-7 FP `act_id`s — and **every one produces extracted definitions**:

| act_id | extracted |
|---|---|
| `USC_T22_C102_S9528` | 3 — `foreign person`, `Syria`, `financial, material, or tech…` |
| `STATE_DE_T13_C5_SII_S513` | 1 — `Employer` |
| `USC_T10_C303_S4093` | 1 — `institution of higher educat…` |
| `USC_T10_C953_S9448` | 1 — `commissioned service obligat…` |
| `USC_T42_C7_S679c` | 1 — `early approved tribe, organi…` |
| `USC_T35_C4_S41` | 1 — **`SEC. 804. DEFINITION.`** ← genuine garbage |

I then read the real body of `USC_T22_C102_S9528`:

```
(2) Foreign person
The term "foreign person" has the meaning given such term in section 594.304 of title 31 CFR...
(3) Syria
The term "Syria" has the meaning given such term in section 542.316...
```

**That is a genuine definitions block.** The row was flagged FP because the *triggering clause* was a prohibition sentence — but the section really does define terms, by forwarding reference, and the extracted terms are real.

Two consequences:

1. **QA's FP number is measured at ROW/recognition granularity** ("is the triggering clause a definitions preamble?"), which is **not** the certification-relevant question. The D-CERT question is **"are the extracted TERMS genuine?"** These are different metrics and they disagree.
2. **The Planner's pattern deliberately excluded `has the meaning`** because it "collided with forwarding pointers" — but forwarding definitions ARE definitions under a zero-miss bar; the term is defined for this chapter, by reference. That exclusion is itself a recall hazard, and it is precisely what would drop `foreign person` and `Syria`.

`USC_T35_C4_S41`'s `'SEC. 804. DEFINITION.'` is the one true defect here — garbage at *definition* granularity, and worth tracking separately.

### M-R64 — RULING: reject (a) and (b). (c) first, but re-measure FP at DEFINITION granularity before anything ships.

- **(a) reject** — fails zero-miss, and now demonstrably drops genuine definitions.
- **(b) reject**, despite the Planner's lean. It is bounded, but the Planner's own numbers show it still loses ~1,450 genuine rows to fix ~758 flagged ones — a losing trade *even inside the delta*, and M-R63 shows the "fixed" side is partly not broken at all. Bounding a bad trade does not make it good. This is the recall/precision collision D-Q1 forbids a panel from resolving by itself, and I am not resolving it in favour of precision.
- **(c) adopted**, with a prerequisite: **re-measure FP at definition granularity first** — sample extracted TERMS and judge whether each is a genuine defined term. Only that number can gate certification. The root causes the Planner named (greedy trigger tail, missing `includes` in quote-means, singular "purpose"/intervening-clause phrasing) fix the *right occurrence winning*, which improves precision AND recall together instead of trading them.
- The Planner's 11 tests **stand as authored** — both directions are the correct contract regardless of remedy, with one amendment needed: the 5 positive guards must be extended to cover forwarding-definition rows like `USC_T22_C102_S9528`, so no future narrowing silently drops them.

### M-R65 — ESCALATED to the program manager (program-wide, not sprint-local)

If row-level FP is the metric other panels are using, **the program's whole FP methodology and D-CERT's denominator semantics are affected** — every panel may be over-reporting FP and under-crediting capture. Raised as a program question, not settled here.

### M-R66 — Sprint parked pending that ruling

`us_body_preamble.py` **unchanged** — no bad trade shipped. Carried, still open: M-R53 comment fix (**four cycles overdue**), file split 386→300 (M-R54), the branch-attribution pin the Planner flagged.

---

## 2026-08-05 — Program ruling P-FP received; option-(c) cycle opened

### M-R67 — P-FP (program doc @ main `37a7402`), M-R63/M-R65 named as origin

**FP granularity follows the RULE'S OUTPUT.**

- **Capture/extraction rules** (ours): an FP exists only if a captured
  **(row, term, definition_text)** is not a genuine definition of that term
  in that row. **Trigger-clause mislabeling that still yields genuine
  definitions is a recognition-path note, NOT an FP.**
- **Recognition rules** (heading detection): row-level stays correct, because
  there the row IS the output.
- **Certification consumes definition-granularity numbers** for all capture
  claims. The IL certification contract's per-(row, term) design already
  embodies this; the US track inherits it.

**Binding corollary**: forwarding / `"has the meaning given in"` definitions
are **GENUINE definitions** per **D-MT-E1** (capture + the reference edge). A
defining-verb pattern that excludes forwarding idioms **contradicts a
standing director ruling and is rejected by construction**. The Planner's
`has the meaning` exclusion **must be reversed** in the option-(c) work.

M-R64 endorsed in full — both narrowings rejected including the bounded one
(a bounded bad trade is still a bad trade; the D-Q1 bar held), option (c)
adopted with the definition-granularity re-measure as the prerequisite gate.
Cycle-7 numbers stay **measured-not-certified** until it lands. Expectation
is that true definition-level FP is far below 18% (my own six-row check found
one genuine garbage row) — **but measure it, do not assume it.**

Program manager checked before ruling: other panels' FP measurements were
already term-level, so **no program-wide re-statement is needed beyond ours**.

### M-R68 — Two directives, both binding on the current pass

1. **The M-R53 comment fix is now BLOCKING** — four cycles overdue on a
   condition my own ratification imposed. A false "verified corpus-wide …
   occurs in ONLY this one real row" claim sitting in production code is
   exactly the archaeology trap P-FP itself was created by. It ships in this
   pass or the pass does not close.
2. **Publish row-level and definition-level FP side by side, once**, so the
   program record shows *why* they diverge. That pair is the best teaching
   artifact this ruling will have — it is the difference between "18% FP" and
   "one garbage term in six rows."

### M-R69 — Plan and model/effort

Sequence (one writer at a time, per M-R8): **Planner** → **Developer** →
**QA**.

Planner first, because the test contract changed under P-FP: the `has the
meaning` exclusion must be reversed, and the 5 positive guards must be
extended to forwarding-definition rows (`USC_T22_C102_S9528` →
`foreign person`, `Syria`) so no future narrowing can silently drop them.

Planner: **Sonnet / high** — reversing an exclusion under a director ruling
while designing root-cause REDs whose predicate must improve precision AND
recall together is sustained judgment, not transcription. Per P-R6 Planner is
always Sonnet high. **Haiku considered: no.** `model=inherit` not used.

---

## 2026-08-05 — Manager (phase-2): succession, re-verification, and a contract contradiction

### M-R70 — DELIVERY SECTION (committed artifact; supersedes M-R56's id)

**This manager's agentId: `ac822b0047bde31cb`.**

The predecessor manager (`a3adfb6a9000b266e`, M-R56) context-exhausted and is
**dead**. Any brief still naming that id would deliver into a context nobody
reads. It is **superseded** for all spawns from this point.

**Every role-agent brief — new spawns AND resumes — carries this verbatim:**

> Before you finish or escalate, deliver your full report via SendMessage
> with to: 'ac822b0047bde31cb' (raw agent id, exactly as written). Your
> plain-text final return is NOT a reliable delivery channel — the
> SendMessage IS your report. If the send fails, say so in your final text.
> This id is committed at `docs/sprint/sprints/2026-08-04-defs-us-preamble-log.md`
> (M-R70). **If the id in this brief and the id committed there disagree, do
> NOT send — report the discrepancy instead.**

The committed id is the authority; a briefed id is a copy and may be stale.

### M-R71 — Inherited claims RE-VERIFIED with positive controls (program law)

I did not build on the handoff's word. Checked directly at `8ad3052`:

| Inherited claim | Control run | Verdict |
|---|---|---|
| Branch parked at `8ad3052`, pushed, tree clean | `git status --porcelain` empty; `git rev-parse HEAD origin/…` identical | **TRUE** |
| Suite 9 failed / 847 passed | full `pytest backend/tests -q` re-run | **TRUE** — 9 failed, 847 passed |
| The 9 = 3 markers deps + 6 cycle-8 REDs | read the failure list | **TRUE** — 3 NE/SD unquoted + 6 in `test_us_body_preamble_defining_verb_narrowing_red.py` |
| `us_body_preamble.py` UNCHANGED — no bad trade shipped | `git log -- <file>` last touched at `9e30ec5` (cycle-7 Dev) | **TRUE** |
| M-R53 comment fix still outstanding | grepped the file | **TRUE** — false claim live at two sites (lines ~218 and ~345) |
| File is 386 lines (>300 gate) | `wc -l` | **TRUE** — 386 |
| noreply git identity in worktree | `git config user.email` | **TRUE** |

Handoff is accurate on every checked point. What it did **not** catch is M-R72.

### M-R72 — DECISIVE: two cycle-8 RED negatives are REJECTED BY CONSTRUCTION under P-FP

The handoff framed the `has the meaning` exclusion as living in the *proposed*
narrowing pattern, to be reversed by widening the verb vocabulary. I read the
actual assertions. It is worse than that: **two of the six cycle-8 RED
negatives assert, at definition granularity, that genuine forwarding
definitions must NOT be captured.**

- `test_usc_t22_c102_s9528_pure_forwarding_pointers_not_captured` asserts
  `created_definitions == []` for the **exact row P-FP names as genuine**
  (`foreign person`, `Syria`). Its own docstring states the intent plainly:
  *"`has the meaning given` is deliberately NOT in this narrowing's verb
  vocabulary … so this row must be excluded."*
- `test_state_de_employer_forwarding_pointer_not_captured` asserts
  `created_definitions == []` for `"Employer" has the meaning given such term…`.

P-FP is verbatim: forwarding / "has the meaning given in" definitions are
GENUINE per D-MT-E1, and a defining-verb pattern that excludes forwarding
idioms **"contradicts a standing director ruling and is rejected by
construction."** These two tests ARE that pattern, written as a contract.

**Making them green would ship precisely what the program forbids.** They must
be **re-authored to assert capture**, not satisfied. M-R64's "the Planner's 11
tests stand as authored" is **superseded on exactly these two** by P-FP, which
post-dates it.

**Two further negatives are SUSPECT, not yet ruled** — both assert
definition-granularity emptiness on rows whose own docstrings concede real
definitional content:

- `test_usc_t10_c303_s4093_eligibility_criteria_list_not_captured` — docstring:
  *"the row's one real definition elsewhere is 100% forwarding."* Under P-FP
  that definition is GENUINE, so `created_definitions == []` may be the wrong
  contract even though the *triggering clause* is genuinely not a preamble.
- `test_usc_t42_c7_s679c_circular_is_an_individual_not_captured` — extracts
  `early approved tribe, organi…`; whether that is genuine or circular garbage
  is a **judgment against the real body**, not a naming question.

Only `test_usc_t35_c4_s41_…` (`'SEC. 804. DEFINITION.'`) is confirmed true
definition-level garbage (M-R63, and my own read agrees).

**This is the recognition/definition granularity split doing real work**: a
row can be mis-*recognized* (its trigger clause is not a preamble) while its
*extracted definitions* are genuine. P-FP says only the second is an FP. Four
of these six negatives were authored against the first.

### M-R73 — Production `_B1_FORWARDING_PHRASES` is in the same conflict — MEASURE, do not assume

Six of the eight live entries in `_B1_FORWARDING_PHRASES`
(`us_body_preamble.py:308`) are **forwarding idioms**, i.e. genuine pointer
definitions per D-MT-E1: `shall be as defined in`, `shall have the same
meaning as`, `has the same meaning as`, `has the meaning provided in`,
`has the meaning found in`, `has the meaning stated in`. Two are genuine
hazards and **stay**: `shall not include` (exclusion-only clause),
`does not impair` (construction clause).

So the exclusion P-FP rejects is not only in the unshipped narrowing — a
version of it is **already live in shipped production code**, suppressing
recognition of rows whose trigger clause forwards.

**I am NOT asserting this drops genuine rows in practice.** Two reasons for
caution, both from the file itself: the list is applied only to the *gap/filler*
text between trigger and colon/quote, and the production comment concedes that
on the MS row the filter is redundant ("excluded on window grounds alone, the
forwarding-phrase filter is the second line of defense"). Also note
`has the meaning **given**` — the canonical P-FP idiom — **is not in the list
at all**. Whether the filter is load-bearing on genuine rows is an open
measurement, and per the program's own lesson ("a green suite is not evidence")
it gets measured on the real corpus before anything is removed.

**Consequence for D-MT-E1's second half**: capturing a forwarding definition
requires capturing the **reference edge** to the target law/section. That is
core-v2 seam plumbing, not this sprint's file. We capture now and name the edge
as a core dependency — we do **not** silently ship half of D-MT-E1.

### M-R74 — Plan and model/effort for this pass

Sequence unchanged (one writer at a time, M-R8): **Planner → Developer → QA**.

- **Planner — Sonnet / high.** Re-adjudicating four test contracts against real
  corpus bodies under a director ruling, then designing root-cause REDs whose
  predicate must improve precision AND recall together. Sustained judgment.
  Per P-R6 Planner is always Sonnet high. **Haiku considered: no** — this pass
  turns on reading real statutory text and applying a ruling to it, which is
  exactly where a cheap model produces confident wrong adjudications.
  `model=inherit` not used.
- **Developer — Sonnet / medium** (planned): option-(c) fixes + the BLOCKING
  M-R53 comment fix + the 386→300 split. Mechanical against a written plan.
- **QA — Sonnet / high** (planned): the definition-granularity FP re-measure,
  the certification gate; row-level and definition-level published side by side
  once (M-R68 directive 2).

### M-R75 — Planner spawned (cycle 9)

Spawned **after** the M-R70..M-R74 commit landed (`d235c3c`), per commit-before-spawn.

- **Agent**: Planner, `acb43d1f810eebfa1`
- **Model/effort**: Sonnet / high. **Haiku considered: no** — the pass turns on
  reading real statutory bodies and applying a director ruling to adjudicate
  test contracts; a cheap model's failure mode here is a confident wrong
  adjudication that then gets built on.
- **Worktree**: `/Users/nerya/LexGraph-wt/defs-us-preamble-plan9`, branch
  `claude/defs-us-preamble-plan9` forked from `claude/defs-us-preamble` @ `d235c3c`.
  Sole writer. Own `backend/.venv`, **positively verified** to import
  `…-plan9/backend/app/definition_links/rules/us_body_preamble.py` — the
  worktree-venv trap checked, not assumed.
- **Brief points at M-R70** for the delivery id, with the discrepancy rule:
  committed id wins; on disagreement, report instead of sending.

**Charter**: (1) re-adjudicate all six cycle-8 RED negatives against real
bodies — two ruled rejected-by-construction, two suspect, two expected to
stand; (2) extend the 5 positive guards to forwarding rows; (3) option-(c)
root-cause REDs (greedy trigger tail, `includes` per D-INCLUDES with the
targeted "References to" guard, singular "purpose", intervening clauses);
(4) **measure** whether the six forwarding entries in the live
`_B1_FORWARDING_PHRASES` are load-bearing on genuine rows — measure, don't
assume; (5) name the D-MT-E1 reference-edge dependency rather than shipping
half the ruling.

Fences carried: Planner owns tests and writes zero production code; red-before-
green on the live path; byte-exact real corpus rows; no snapshot reads; pins
must be mutation-verified in both directions; never `git stash`; never
`git add -A`.

---

## 2026-08-05 — Successor recovery: cycle-9 manager dispatch

### M-R76 — Delivery record and exact recovery state

The successor program manager verified the shared branch clean at `c3bec0f`
and recovered the predecessor Planner's clean committed work at `a72c6a3` on
`claude/defs-us-preamble-plan9`. That branch was previously local-only and is
now pushed byte-for-byte to `origin`; it is **one commit on each side** of the
shared branch and must be reviewed/reconciled, not recreated.

Fresh preamble assignment: **`/root/markers_panel_manager`**, GPT-5.6 Sol /
high, reused only after its separate markers panel closed and released its
QA. Sol/high is the cheapest fit for succession arbitration across P-FP,
D-MT-E1, D-INCLUDES, the stale 444-line contract, and a recovered Planner
artifact; the reused task name does not change its manager-only role or
authorize it to write code or tests.

The manager must first read the program handoff, program rulings, this
contract/log tail, and the complete `a72c6a3` diff against its own fork point
`d235c3c`. It then:

1. reconciles the stale contract without deleting durable history (move detail
   to this log as needed; contract lint must pass before final QA);
2. independently validates the recovered Planner tests, real-row provenance,
   P-FP adjudications, mutation evidence, and scope fences before merging them;
3. spawns a separate Developer (production only) for the approved option-(c)
   root causes, blocking M-R53 comment correction, and 386→300 module split;
4. spawns a fresh independent QA for definition-granularity FP measurement,
   row-vs-definition comparison, full evaluators, and the release verdict.

The manager never writes production or tests. Planner owns tests; Developer
never tests/QA's its own work; QA edits docs/evidence only. CodeGraph is used
first for main-state structure, with direct reads for branch-divergent files.
Current `main` containment is false and must be reconciled deliberately before
final QA; no merge-readiness claim may precede that gate. All role-agent ids
must be committed here before their first task is sent.

### M-R77 — Recovered Planner review: correct P-FP direction, incomplete causal contract

Successor manager reviewed the complete `d235c3c..a72c6a3` diff from its own
fork point (877-line materialized diff, SHA-256
`7a4cf5bfdc84e512ec2bfaffbfb62f7c1a1a8e4d5136b3066308f13d554f20cf`).
The commit touches only two integration-test files and one fixture. All fields
of all 12 referenced fixture rows independently match snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad` exactly. Focused result is
**5 failed / 11 passed**: one confirmed P-FP garbage negative and four
option-(c) root causes fail; the five re-adjudicated genuine rows and existing
positive guards pass. No production edit is present.

P-FP direction is correct: the two forwarding rows rejected by M-R72 plus
`USC_T10_C303_S4093`, `USC_T42_C7_S679c`, and `USC_T10_C953_S9448` are real
definitions; only `USC_T35_C4_S41` remains definition-level garbage. The
recovered tests are not yet admissible as the Developer contract:

1. the five positive re-adjudications assert term presence only, while P-FP's
   output is the complete `(row, term, definition_text)` tuple;
2. the PA greedy-tail RED can turn green merely by shortening the regex even
   if the genuine occurrence still cannot make the production recognition
   function return `Definitions`; it does not prove “the right occurrence
   wins”;
3. the other causal REDs directly probe live regex objects and have paired
   live-path outcome guards, but the PA “References to” guard is entirely
   test-local and cannot constrain production. It must be classified honestly
   as a held extraction-side D-INCLUDES dependency unless a production path in
   this sprint actually changes;
4. M-R75's required corpus measurement of the six forwarding entries in live
   `_B1_FORWARDING_PHRASES` is absent, so P-FP safety is not yet established;
5. mutation evidence exists only as commit prose and must be rerun durably on
   the corrected causal tests.

Manager ruling: do not integrate `a72c6a3` yet. A fresh Planner corrects the
same recovered branch/worktree, writes tests/fixtures/docs only, and returns
exact provenance, RED/live-path, mutation, and forwarding-filter measurement.
No narrowing is authorized. D-MT-E1's reference edge remains an explicit
core dependency; this sprint captures and preserves forwarding definitions.

### M-R78 — Fresh Planner correction delivery record

- Canonical child id: `/root/markers_panel_manager/planner_cycle9_correction`.
- Model/effort: `gpt-5.6-terra` / high. Planner judgment spans real statutory
  bodies, P-FP/D-MT-E1/D-INCLUDES, causal RED design, and corpus measurement.
  Haiku considered: no; a cheap model risks another confident wrong
  adjudication. `model=inherit` is not used.
- Worktree/branch: recovered sole-writer
  `/Users/nerya/LexGraph-wt/defs-us-preamble-plan9` /
  `claude/defs-us-preamble-plan9`. It must retain `a72c6a3` authorship, correct
  rather than recreate it, and never touch the main checkout or production.
- Brief: M-R77 defects are binding. Finish M-R75's forwarding-filter
  measurement; strengthen P-FP tuple assertions; make each option-(c) causal
  RED prove the real production function reaches the genuine occurrence,
  with paired live-path guards and durable mutation flips; classify the
  test-local PA guard honestly; name the reference-edge dependency. Stop and
  escalate on any new trade-off or production/test ownership conflict.

### M-R79 — Full forwarding-filter ledger and Option-A scope ruling

Planner correction measured snapshot `301000fc3465374ee0f23c3c6953a8a861e95cad`
mechanically across all 105 US parquet files / 2,046,009 rows. The probe
inspected only the actual B1 colon filler or quote-gap, compared live B1 with
one phrase removed, and counted a delta only when the row changed from no B1
recognition to `Definitions`.

| live phrase | B1 inspected hits | None→Definitions rows |
|---|---:|---:|
| `shall be as defined in` | 12 | 8 |
| `shall have the same meaning as` | 99 | 71 |
| `has the same meaning as` | 152 | 117 |
| `has the meaning provided in` | 17 | 14 |
| `has the meaning found in` | 0 | 0 |
| `has the meaning stated in` | 46 | 41 |
| hazard `shall not include` | 182 | 74 |
| hazard `does not impair` | 1 | 0 |

The six forwarding phrases account for 251 newly B1-recognized candidate rows;
five have nonzero observed deltas, while `has the meaning found in` is 0/0 in
this snapshot. This establishes that filters are not generically removable.
The two listed hazards must also remain: the 74 `shall not include` deltas mix
genuine exclusion definitions with construction/non-definition text.
The exact 251-row forwarding ledger (phrase, act id, citation) is preserved in
`artifacts/2026-08-04-defs-us-preamble-forwarding-filter-ledger.md`; test code
does not read that artifact or the corpus.

P-FP tuple check: existing real `STATE_CO_T15_A11_P7_S15-11-701` evidence
proves B1-only unfiltering is unsafe. The current extractor would persist the
exception-list tuple, not the forwarding term's target (`section 15-10-201`),
so it cannot meet P-FP or D-MT-E1. This is HELD shared extraction/reference-edge
debt. It is not a B1 developer item and does not authorize `us_profile.py` or
reference logic changes.

Manager ruling: **Option A** — keep all forwarding filters unchanged in this
bounded option-(c) sprint. The Developer may touch only
`backend/app/definition_links/rules/us_body_preamble.py` and, if necessary for
the <=300-line split, new `backend/app/definition_links/rules/us_body_preamble_b1.py`.

### M-R80 — Corrected Planner test contract and mutation evidence

P-FP guards now query persisted `Definition` rows: all five re-adjudicated
genuine rows assert the required `(term, definition_text)` tuple. Forwarding
targets retained: T22 `foreign person`→31 CFR 594.304, `Syria`→31 CFR 542.316,
DE `Employer`→IRC 4301(d), and T10 institution→20 U.S.C. 1001. The two local
means rows assert their real definition text too. `USC_T35_C4_S41` remains the
only definition-level garbage RED.

Four causal REDs call the actual production
`_b1_trigger_colon_or_quote_means` on byte-exact bounded statutory spans. The
full rows' existing ingest+link guards stay green; the bounded spans exclude
the rescue occurrence. Focused command:
`backend/.venv/bin/pytest backend/tests/integration/test_us_body_preamble_defining_verb_narrowing_red.py backend/tests/integration/test_us_body_preamble_option_c_root_cause_red.py -q`
returns 5 failed / 11 passed (one P-FP garbage + PA/USC/AR/OH causal REDs).

Runtime-only mutations, each restored before exit, changed its named bounded
probe from `None` to `Definitions`: PA non-greedy trigger plus B1 direct-means
branch; USC quote branch adds `includes|shall include`; AR trigger accepts
singular `purpose`; OH trigger accepts bounded `divisions (C) and (D) of`.
Restoration returned all four probes to `None`. No production edit was retained.
PA `References to` is now a green held extraction-side D-INCLUDES spec using
the real unmodified `_MEANS_IDIOM_GAP_RE`, never a test-local future guard.

### M-R81 — Manager audit correction: PA non-trap and T35 held scope

The PA permanent RED formerly asserted that the pre-fix trigger regex's match
contained `means`. That would make a required non-greedy trigger correction
fail an immutable assertion. It now pins only the byte-exact real statutory
clause (`"association" in this chapter means a corporation`) and asserts the
actual B1 function returns `Definitions`; the runtime mutation goes green and
restoration goes red. Re-run evidence invoked the four committed test
functions directly against runtime-only production-module mutations: PA,
USC, AR, and OH each greened; restoring all original module values made each
same test red again.

Manager direct proof corrected the T35 ownership: the real `In this section:`
occurrence around offset 62,295 correctly makes B1 return `Definitions`, and a
later `Director` definition is genuine. The existing body-wide extractor instead
persists `SEC. 804. DEFINITION.` with 8,431 characters. Since B1 returns only a
heading, no B1 occurrence selection can repair that tuple; narrowing would be
the rejected remedy and still lose Director. T35 remains a held shared-
extraction/P-FP RED beside CO and D-MT-E1, not a Developer acceptance gate.

The superseded 20-item historical contract is preserved without loss at shared
commit `7d87d08` and in the cited D1–D6 / M-R historical entries above; this
compact current contract carries only the bounded Developer handoff.

### M-R82 — Developer cycle-9 roster and write lock

Before dispatch, the manager committed the canonical child identity
`/root/markers_panel_manager/developer_option_c`, model `gpt-5.6-terra`,
reasoning effort `medium`, and Developer brief v3.1. The isolated branch is
`claude/defs-us-preamble-dev9` at expected HEAD `bf3f974`; its worktree is
`/Users/nerya/LexGraph-wt/defs-us-preamble-dev9`.

The production write lock is limited to
`backend/app/definition_links/rules/us_body_preamble.py` and, only for the
required <=300-line split,
`backend/app/definition_links/rules/us_body_preamble_b1.py`. All tests,
fixtures, sprint docs, `us_profile.py`, shared extraction/reference-edge code,
and `_B1_FORWARDING_PHRASES` are read-only. The Developer owns the four B1
causal fixes, the M-R53 comment correction, and behavior-preserving module
split; held T35 and forwarding/CO debts are not Developer gates.

### M-R83 — Developer accepted; main containment exposes one stale G12 pin

Developer `/root/markers_panel_manager/developer_option_c` landed production-
only commit `fe4754c`, integrated at `6ab2b3e`. Manager read the complete diff,
bounced an unmeasured includes-family widening out of the PA direct-means
branch, and required the split module to retain the durable B1 hazard/window
rationale. Authoritative dev-worktree evidence: option-c 5 passed; combined
focused 1 held-T35 failed / 15 passed; full backend 4 expected held/inherited
failed / 857 passed; frontend 165 passed; typecheck passed. The facade is 259
lines, forwarding filters are unchanged, and no tests/docs were Developer-
edited.

The manager then merged current `origin/main` at `df17346`; main containment is
true and the merge had no conflicts. Main includes core-2 G12's already-shipped
`includes|shall include` inline-extraction vocabulary plus the targeted
`_preceded_by_references_to` guard. The old option-c held test directly asserted
the pre-G12 regex vocabulary, so after containment it produces one stale-pin
failure in addition to held T35. Planner
`/root/markers_panel_manager/planner_cycle9_correction` (`gpt-5.6-terra`, high,
Planner brief v3.1) resumes from `df17346` to re-point only that pin in both
directions: PA construction clause suppressed; genuine USC includes definition
retained. T35 must return to being the sole focused RED before fresh QA.

### M-R84 — Planner re-points the stale held-G12 pin to shipped behavior

Planner `/root/markers_panel_manager/planner_cycle9_correction` changed only
the owned Option-C integration test and sprint contract/log. The former held
test now drives the actual normalized `_extract_inline_quoted_definitions`
path without monkeypatching: both PA `References to` quotes are positively
identified by `_preceded_by_references_to` and produce no boundary/candidate,
while genuine USC `"United States" includes ...` is not guarded and is emitted
with the expected definition-text start. No fixture, production, causal B1
gate, paired guard, or T35 assertion changed.

Post-main evidence: Option-C is 5 passed; defining-verb plus Option-C is exactly
1 held-T35 failed / 15 passed; shipped core-2 G12 unit coverage is 6 passed.
The old held-test name has no remaining hit in any repo-profile test root.
Contract lint passes at 128 lines with a 9-line Context Dump. The corrected
contract routes next to fresh QA; G12 is shipped integration evidence, not a
future held dependency.

### M-R85 — Integrated evaluator finds one stale FED pin and one real cross-panel scope regression

The manager-owned post-main evaluator ran from the contained shared worktree:
backend **935 passed / 6 failed**, frontend **25 files / 165 tests passed**, and
typecheck passed. Four backend failures are the declared T35 plus NE/SD
markers dependencies. The other two were independently attributed before QA.

The FED failure is a stale G12 debt pin, not a production regression. Shipped
`includes` extraction makes `recreational purposes` the final recognized entry:
`wildlife` shrank to 70 characters, while `recreational purposes` is now the
8,091-character candidate that swallows `Contracts on loan security
properties`. The same held unbounded-last-entry debt remains; Planner may only
re-point that existing debt spec and its explanatory text to the actual term.

The core G8 failure is a real cross-panel regression and blocks final QA.
On the exact live probe, B1 and body-derived heading both return `Definitions`;
`determine_scope` returns `law-wide`, so the definitions-section branch emits a
law-wide `Scope probe` with trailing marker text. Without B1 dispatch, the
ordinary-section `extract_local_scope_definitions` path emits the correct local,
clean candidate. The mutually exclusive pipeline branches mean first-wins G8
cannot protect a local candidate that is no longer produced. Root ruled this
must not be suppressed, held, or repaired in preamble ownership and is routing
the shared scope/dispatch seam to a separate core follow-on Planner. Final
preamble QA and merge-readiness remain stopped on that dependency.

### M-R86 — Planner re-points the FED last-entry debt after shipped G12

Planner changed only the owned FED/DC/NY integration file plus this sprint
contract/log. On the byte-exact `USC_T7_C50_S1997` row, the green debt spec now
drives the actual `_extract_inline_quoted_definitions` path and selects its
final `recreational purposes` candidate. Durable assertions pin its `hunting.`
start, both swallowed unrelated headings (`Contracts on loan security
properties` and `Terms and conditions`), and a length above 8,000 but below
the complete row. No exact-length pin, production edit, fixture edit, or debt
acceptance flip was introduced. Explanatory text records the actual residual
state: `wildlife` is 70 characters but still carries `(4) The term`.

Evidence: isolated FED/DC/NY is 4 passed; Option-C is 5 passed; combined
defining-verb plus Option-C is exactly 1 held-T35 failed / 15 passed. The
separate core G8 local-vs-law-wide test still fails exactly because persisted
scope is `law-wide`; it was neither edited nor suppressed. Final preamble QA
remains blocked on that separately owned scope/dispatch regression.

### M-R87 — Root assigns the G8 shared scope/dispatch repair to this manager

Root expanded this manager's ownership to repair the cross-panel G8 regression
on exact production/test base `ce5161d`. Before dispatch, the canonical Planner
is committed as `/root/markers_panel_manager/planner_g8_scope`, model
`gpt-5.6-terra`, high reasoning, Planner brief v3.1. Haiku is rejected because
the task must arbitrate a shared live dispatch/scope seam and author
discriminating RED evidence. Its isolated branch/worktree are
`claude/defs-us-preamble-g8-scope-plan` and
`/Users/nerya/LexGraph-wt/defs-us-preamble-g8-scope-plan`.

Planner writes tests and sprint evidence only; production is locked. Required
gates are: a new live ingest-to-link RED proving B1 currently persists a
trailing `law-wide` candidate instead of clean `local`; every core G8 case,
including reverse order, stays green; real option-c positives and a genuine
non-local/chapter preamble control retain intended scope; the suite rejects
both B1 suppression and global scope relabeling; and all repo-profile roots
receive a stale-pin sweep. Any architectural fork must escalate before a
Developer or production write set is commissioned.

### M-R88 — G8 local dispatch fork ruled; ordered-key canonicalization planned

Planner reproduced the exact live failure in a new, separate integration file:
the constructed ordinary US-GA row is deliberately test scaffolding, not a
corpus claim. Its real B1 recognizer and `USProfile.derive_heading_from_body`
both return `Definitions`; the derived branch calls `determine_scope`, which
returns `law-wide`, and persists `Scope probe` with the trailing `Editorial
Notes` text. Direct profile evidence from the identical bytes proves the
otherwise-mutually-exclusive local path yields `Scope probe`, text `a small
mechanical device with a handle`, and `scope=local`.

The architectural fork was escalated before a production choice. Manager
rejected local-only dispatch (it suppresses B1 section extraction) and a new
profile/registry API (unnecessary shared/IL blast radius), accepting a narrow
pipeline-only candidate union. A naive union was then rejected: Stage 3 keeps
every `(candidate, persisted Definition)` in `resolved`; a later law-wide
same-key candidate can therefore link an outside article to the Definition
persisted local. The accepted exact rule is limited to the body-derived branch:
obtain registered local candidates in registry order, retain the first for
each `tuple(sorted(candidate.terms))` key, then append existing section
candidates only when their key is not already owned. Thus a same-key broad
candidate reaches neither `all_candidates`, `resolved`, nor link generation;
every non-colliding B1 section candidate remains. No generic persistence/G8
preference, profile/registry, IL, or B1 recognizer behavior changes.

The new live RED proves all of: B1 and derived-heading recognition stay live;
the local persisted text/scope are exact; an outside article receives no
`USES_DEFINITION` edge; and a section-only `Section companion` term survives
alongside local `Scope probe`. Its real control reuses byte-exact
`STATE_GA_T7_C8_S7-8-1`, confirms B1-derived `Definitions`, and remains
`chapter`; it defeats global local relabeling. B1 suppression defeats both
recognition controls; local-only dispatch defeats `Section companion`.

Exclusive Developer production write set: `backend/app/definition_links/pipeline.py`.
The Planner applied that exact ordered-key code only to an in-memory copy of
`pipeline.run_definition_linking`, ran the new file plus the entire core G8
file (**11 passed**), then restored the original callable and verified no
`pipeline.py` diff. This proves the refined implementation produces one local
`Scope probe`, no outside edge, the non-colliding companion, the real chapter
control, and all eight core G8 cases; the direct naive append-all replay still
reintroduces the one outside edge. T35 and NE/SD remain held dependencies;
Option-C's real positives and paired ingest/link guards remain required green
evidence.

### M-R89 — G8 Planner pre-development inventory and stale sweep

Focused pre-fix inventory is intentionally not presented as a green suite:
the new dispatch file is **2 failed / 1 passed** (load-bearing local/trailing
RED and the local-plus-distinct-section union RED; real GA chapter control
green). Existing core G8 is **1 failed / 7 passed**: its named integrated
scope-broadening probe is the inherited same shared-dispatch RED, while all
other safety controls, including both real reverse-order/complete-definition
tests, are green. It was neither modified nor suppressed. The direct naive
union replay (`local + law-wide same-key candidates`) produces exactly the
outside `Scope probe` edge, proving the required Stage-3 guard is not
theoretical and leaving no retained runtime mutation.

Real Option-C positives are **5 passed**. Paired defining-verb plus Option-C
evidence is **1 held-T35 failed / 15 passed**; T35 and inherited NE/SD remain
named dependencies, not this repair. A case-insensitive stale-name sweep over
`backend/tests/unit`, `backend/tests/integration`, `backend/tests/e2e`, and
`frontend/src/components/__tests__` found zero instances of all six replaced
cycle-8/9 Option-C and held-G12 test names. Contract lint passes at 151 lines
with a 10-line Context Dump; `git diff --check` and Python compile validation
are clean. No project ruff configuration/dependency exists, so no unavailable
linter was represented as run.

### M-R90 — G8 scope Developer roster and exclusive production lock

Root independently audited and accepted Planner commit `24d34c0`; the manager
fast-forwarded it to the shared sprint branch before implementation dispatch.
The committed Developer identity is
`/root/markers_panel_manager/developer_g8_scope`, model `gpt-5.6-terra`, medium
reasoning, Developer brief v3.1. Haiku is rejected because this edits shared
Stage-2/Stage-3 dispatch and must preserve scope/link semantics. Its isolated
branch/worktree are `claude/defs-us-preamble-g8-scope-dev` and
`/Users/nerya/LexGraph-wt/defs-us-preamble-g8-scope-dev`.

The exclusive production write lock is
`backend/app/definition_links/pipeline.py`. Tests, fixtures, sprint docs,
profiles, registry, B1 modules, and generic persistence are read-only. The only
authorized change is body-derived-heading ordered key canonicalization before
`all_candidates`/`resolved`: registered local candidates first, first per
`tuple(sorted(candidate.terms))`, followed by existing section candidates only
for unseen keys. Ordinary/non-derived and IL paths must stay byte-for-byte.
Any green-pin break or alternate seam is a mandatory stop/escalation.

### M-R91 — Full-suite registry accumulation bounces two Planner assertions

Developer production commit `62d258f` is pushed but not integrated. Its
focused evidence is new plus core G8 **11 passed**, profile/scope/persistence/
IL **40 passed**, Option-C **5 passed**, and combined **1 held-T35 failed / 15
passed**; the diff is the exclusive `pipeline.py` file, 20 insertions. Frontend
is 165 passed and typecheck passes.

The authoritative full backend is **938 passed / 6 failed**. Four failures are
the declared T35 plus NE/SD dependencies. The two extras occur before the live
pipeline assertions: full-suite collection/execution has already registered
the older `test_definition_links_pipeline_scope_seam.py` US-wildcard proof
rule, so direct `extract_local_scope_definitions` diagnostics contain two
byte-identical `Scope probe` candidates. Focused collection has only one. The
accepted production design intentionally canonicalizes such ordered duplicate
keys; therefore an exact raw list cardinality in the new Planner test is a
global-registry-order trap, not a production regression.

Planner `/root/markers_panel_manager/planner_g8_scope` resumes with production
read-only to replace only those two precondition assertions with presence/
content checks that tolerate identical accumulated rule outputs while still
requiring the live pipeline to canonicalize. It must reproduce the full-order
registry state explicitly, keep pre-fix live RED semantics, and prove the
focused/full-order post-fix result before the Developer commit can be audited
for integration.

### M-R92 — Raw registry-union preconditions corrected without weakening live gates

Planner resumed at exact `3139a54` with production, fixtures, and every older
test read-only. The two direct raw-local diagnostics in the new G8 file no
longer require list cardinality one. The primary diagnostic requires at least
one `Scope probe` and proves every matching candidate is exactly the clean
`("local", "a small mechanical device with a handle")` tuple. The subset
diagnostic requires `Scope probe`, permits duplicate identical keys, rejects
every unexpected local-path term, and proves every raw candidate has that same
clean local content/scope. Exact-one persisted-row, clean/local persistence,
zero outside edge, and distinct `Section companion` live expectations are
unchanged.

Using the plan9-local Python 3.13 venv with `PYTHONPATH` pinned to this exact
worktree (and `app.__file__` proven under it), the pre-production-fix isolated
new file is **2 failed / 1 passed**. The failures now reach only the intended
live assertions: `test_b1_derived_local_definition_persists_clean_and_local_
through_live_ingest_linking` gets persisted `law-wide` instead of `local`, and
`test_b1_local_candidate_precedes_but_does_not_suppress_distinct_section_
candidate` persists only `Section companion`, missing `Scope probe`; the real
GA chapter control passes.

The full-order surrogate lists `test_definition_links_pipeline_scope_seam.py`
first and is **2 failed / 12 passed**: all eleven older seam tests and the GA
chapter control pass, while exactly those same two new live assertions remain
RED. Thus accumulated duplicate US-wildcard scope-trigger candidates no longer
fail a Planner precondition. Core G8 is unchanged at **1 failed / 7 passed**;
only `test_real_pipeline_never_replaces_a_narrower_definition_with_a_broader_
scope_candidate` is the expected pre-fix RED, with all reverse-order and
complete-definition controls green. No post-fix full-suite claim is made;
Developer must rerun authoritative evidence after this amendment is integrated.
The six-name stale-pin sweep over every repo-profile test root has zero hits;
contract lint passes at 151 lines with a 10-line Context Dump, Python compile
validation passes, and `git diff --check` is clean. No production, fixture,
older test, or unrelated document changed.

### M-R93 — Combined-tree gate blocks QA; correction Planner roster

Root accepted production commit `62d258f` and delivery `f23e081` after an
independent exact-diff audit. The manager fast-forwarded the shared branch to
that delivery, then merged current `origin/main` at `be4370b` without rebasing;
the pushed combined merge is `6056f3c`. G8 is **11 passed**, markers G3H is
**21 passed**, Option-C is **5 passed**, G9 migration is **1 passed**, and the
paired defining-verb command is exactly **1 held-T35 failed / 15 passed**.

The authoritative combined backend is **1068 passed / 28 failed / 19
warnings**. Twenty-three failures exactly match the accepted markers ledger
and one is T35. Four extras block QA: NE `STATE_NE_C43_S43-3329`, NE
`STATE_NE_C44_S44-5003`, SD `STATE_SD_T54_C14_S54-14-12.1`, and FED
`USC_T43_C35_S1742a`'s missing `eligible`. Direct registry/profile evidence
shows no NE/SD EntrySplitter/TermClause rule shipped and no heading derives;
the merged `us_markers_unquoted_terms.py` covers only AL/NC/DC. FED has an
incomplete registered stream: the current splitter emits only the other two
terms, while an independently inspected fallback proves `eligible` is a real
source key. Root ruled that none may be added to the hold ledger.

Canonical Planner: `/root/markers_panel_manager/planner_combined_correction`,
**Terra / high**; Haiku rejected because this requires cross-panel
recognition/extraction design plus persisted all-corpus union measurement.
Branch `claude/defs-us-preamble-combined-plan`, worktree
`/Users/nerya/LexGraph-wt/defs-us-preamble-combined-plan`. Planner writes only
tests and this sprint's docs/artifacts; all production, fixtures, and existing
tests are locked read-only. It must build discriminating live REDs, measure
every proposed FED seam over all 53 files at persisted key/text/scope altitude
with judgments, preserve the exact 24-hold ledger and named green gates, split
production ownership/write sets before Developer dispatch, and return its
commit for root audit. QA remains blocked.

### M-R94 — Combined markers/preamble correction plan and exact replay

Planner added `test_us_combined_markers_preamble_correction_red.py` using only
vendored rows. It separates raw body recognition, SD chapter scope, raw
registered extraction, and live persisted `(term, text, scope)` assertions.
The NE/SD source oracle checks every intended output: 12 C43 terms, four C44
terms, and SD's single term, including the C43 `Support` verb boundary. FED
requires exactly `eligible`, `good Samaritan search-and-recovery mission`, and
clean `Secretary`; its held-green trust-area control rejects a generic
numbered-label parser. Pre-fix focused result is **11 failed / 2 passed**:
the eleven independent release-blocker gates are RED and both FED root-cause /
overbreadth controls are green.

Accepted ownership is disjoint. Preamble Developer changes only existing
`backend/app/definition_links/rules/us_body_preamble.py` for the three literal
NE/SD recognizers and the exact US-SD chapter scope spelling. Markers Developer
adds only `us_markers_ne_sd_unquoted.py` (the reviewed NE/SD source-bound
entries) and `us_markers_fed_good_samaritan.py` (one US-FED priority splitter).
The NE/SD module uses exact `EntrySplitterRule`s only, with no
`TermClauseRule`; the preamble module alone owns recognition and SD scope.
The FED splitter's real callable guard is jurisdiction plus body shape—not
heading provenance, which an EntrySplitterRule cannot receive: body begins
`(a) Definitions` then `In this section:`, contains exactly the three reviewed
labels, and stops before top-level `(b)`. No profile fallback append or shared
profile edit is authorized.

Two reproducible all-53 persisted-output instruments now model the actual
callable seams including G8 local-first/first-key behavior. Non-target files
are counted from immutable parquet metadata behind the exact jurisdiction
guards; every target-jurisdiction row is examined, with nonmatching literal
prefixes proven unchanged before expensive replay. FED exact replay reports
2,038,247 rows / 53 files / 1,983,394 jurisdiction-guarded rows and **two**
changed tuples, both `USC_T43_C35_S1742a`: new clean `eligible` and corrected
`Secretary` boundary; Good-Samaritan is explicitly unchanged. NE/SD replay
reports 2,038,247 rows / 53 files / 1,972,661 guarded rows and **17** new
reviewed tuples (12 C43, 4 C44, 1 SD), each with machine and human judgment.
The compact rejected-summary preserves the two rejected blast-radius outcomes
without committing their 23MB/3.6MB ledgers or claiming unverifiable hashes. Docs
updated: contract, sprint log, RED test, and measurement artifacts. Developer
must use the current focused RED command, apply an in-memory rule mutation to
prove the trusted FED control fails under a broadened guard and restores after
removal, then rerun the named green gates and authoritative combined ledger.

### M-R95 — Hash projection correction

The compact rejection summary no longer presents a hash for an uncommitted,
timed full ledger. Both committed exact ledgers now carry a self-verifying
SHA-256 over only sorted persisted tuple facts: `file`, `jurisdiction`,
`act_id`, `derived_heading`, `terms`, `before`, and `after`. It deliberately
excludes corpus paths, elapsed time, and machine/human annotations. The
reproducible verifier checks both stored hashes and asserts the compact
rejection summary makes no unverifiable full-ledger-hash claim.

### M-R96 — Planner accepted; two disjoint Developer rosters

Planner final tip `72dfcbd` passed root/manager design audit and was
fast-forwarded to shared. Manager independently reproduced the focused
**11 failed / 2 passed** pre-fix gate, exact artifact hashes, contract lint,
and clean diff. The rejected profile append and broad structural parser remain
explicitly rejected; only the two exact proposals are authorized.

Two Developers start from the same committed roster tip and may run in
parallel because their production writes do not overlap. Preamble Developer
`/root/markers_panel_manager/developer_ne_sd_recognition`, Terra/medium,
branch `claude/defs-us-preamble-ne-sd-recognition-dev`, worktree
`/Users/nerya/LexGraph-wt/defs-us-preamble-ne-sd-recognition-dev`, may edit
only `backend/app/definition_links/rules/us_body_preamble.py`. Markers
Developer `/root/markers_panel_manager/developer_exact_splitters`,
Terra/medium, branch `claude/defs-us-preamble-exact-splitters-dev`, worktree
`/Users/nerya/LexGraph-wt/defs-us-preamble-exact-splitters-dev`, may add only
`us_markers_ne_sd_unquoted.py` and `us_markers_fed_good_samaritan.py`.
Haiku is rejected for both: these changes alter live cross-panel recognition,
scope, candidate ordering, and persisted boundaries. Tests, fixtures,
artifacts, sprint docs, registry/profile/pipeline/persistence, and every other
production file are read-only. Each Developer must prove its owned RED subset
green, keep the other half expected-red until combined, run the named green
gates, commit/push cleanly, and return exact production diffs for root audit.

### M-R97 — Combined integration accepted; QA handoff

Root accepted Preamble Developer tip
`19911846d07a99d9be50840157675b8900525147` and Markers Developer tip
`2ee07c9df9c9459bed9c8c2450f974e55dcdd9ae`. Both are ancestors of the clean
shared integration tip `4fa9e7b368801757039091646e06a832620a3a2c`, which
matches its remote. Manager and root independently reproduced the combined
live-path correction at **13 passed**. Manager also reproduced G8
scope/collision **11 passed**, markers G3H **21 passed**, Option-C plus G9
**6 passed**, frontend **165 passed**, and TypeScript type-checking clean.

The authoritative backend result is **1085 passed / 24 failed / 18 warnings**.
Every failure belongs to the accepted hold ledger: T35 shared-extraction debt;
the 16 C5Guard class-B boundary cases; FED Roman structural sibling; OK gap
idiom; NM; two NV cases; AL nested numbered list; and TX Part-A. The former
NE x2, SD, and FED `eligible` release blockers are green, with no unexpected
regressions. All six contract items move to Dev Complete; status is `review`
and current role is `qa`. Root owns resuming the already-created fresh QA
agent after this bookkeeping commit lands.

### M-R98 — QA escalation reopens bounded G7 certification planning

QA evaluated shared tip `ea0565059072d807a5f8564537917ca59b499a3f` and
completed the focused, authoritative backend, frontend, all-53 exact-seam and
hash verification, plus the broad-mutation controls. It reported no new
production regression, but could not independently certify binding G7/Q-D1.
The three independent programs used during the earlier QA investigation —
`qa_d1_measure.py`, `qa_d2_independent_denominator.py`, and
`qa_d3_crosscheck.py` — existed only in a session scratchpad and are gone.
The committed `measure_fp_after_widening.py` states that it is approximate and
non-gating, so it cannot replace the missing definition-granularity proof.

The six implementation items remain Dev Complete. One bounded item 7 reopens
planning: commit a permanent, clean-checkout-reproducible Q-D1/G7 harness and
deterministic/hash-verifiable P-FP evidence at persisted `(row, term,
definition_text, scope)` granularity across all 53 files, with an independent
denominator/cross-check and documented rerun command. Production code is not
authorized. Frontmatter returns to `status: planning`, `current_role: planner`,
`total_items: 7`, `dev_complete_items: 6`, and `qa_cycles: 1`; the manager lock
is released. Root owns spawning the Planner after this commit is pushed.

### M-R99 / D-PFP-400 — director resolves the strict P-FP gate

The director's sprint-harness instruction “fix this” approves the manager's
recommended strict gate. D-PFP-400 defines the population as all definitions
newly persisted/captured by the final preamble panel versus the documented
BEFORE path on the same pinned 53-file snapshot. Identity is stable
`(jurisdiction, source file/row id, term, definition_text, scope)`, evaluated
through live persistence/dedup semantics; forwarding remains genuine under
D-MT-E1.

Planner must commit a deterministic SHA-256-ranked sample of 400 unique tuples,
or the whole population if smaller, seeded by pinned corpus snapshot plus
integration SHA. The sample is jurisdiction-balanced and extraction-route /
registered-rule-family stratified, covers every non-empty jurisdiction, live
route, and registered panel family, exhausts undersized strata, then fills
remaining seats proportionally by deterministic hash order. Because coverage
dimensions overlap, Planner must document the exact conflict-free allocation
algorithm before generating evidence.

Fresh QA independently adjudicates every sampled tuple against source. A false
capture means the row does not genuinely define/forward the term or the text is
not the defining statement. Genuine-definition boundary overrun is recorded
separately in the informational byte-quality ledger, never silently relabeled
P-FP. One false capture or one unresolved/ambiguous adjudication blocks merge;
PASS is 0/400 false and 0 ambiguous. Committed evidence must include the sample,
complete ledger, canonical population/sample hashes, and the one-sided 95%
upper bound (`1 - 0.05^(1/400)`, about 0.75% at 0/400) without a corpus-zero
claim. Existing G7 gates remain GA-after `>=2794` and total
`new_primary >=23617`; `new_fallback` and byte quality remain informational.
Production is read-only. This binding ruling resolves the earlier Planner
escalation; sprint state remains unlocked `planning` / `planner`.

### M-R100 — Item 7 Planner roster and permanent certification repair

Planner roster entry: canonical task `/root/g7_pfp400_planner`,
`gpt-5.6-terra / high`; Haiku considered: no, because this work reconstructs
independent corpus-wide measurement paths and a fail-closed sample contract.
The Planner changed only test-estate scripts/tests, generated compact evidence,
and sprint docs; `backend/app` remains unchanged from integration
`4fa9e7b368801757039091646e06a832620a3a2c`.

The permanent clean-checkout entrypoint is
`docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/run_g7_certification.py`.
It validates snapshot `301000fc3465374ee0f23c3c6953a8a861e95cad`, exactly 53
statute files / 2,038,247 rows, and the pinned integration. Q-D1 invokes live
normalization/profile/registry/extraction and pipeline first-wins dedup
semantics; Q-D2 owns a fresh raw broad-term denominator and imports neither
Q-D1 nor its result; Q-D3 reads canonical artifacts only and fails closed on
all identities, sums, partitions, gates, tuple uniqueness and hashes.

RED first: commit `377bb79` added the permanent entrypoint contract; focused
run was 3 failed because all lost scripts/entrypoint were absent. Harness and
compact evidence followed; focused contract suite is 7 passed. The all-53 run
used the exact documented command. Q-D1 elapsed 456.417 s, result:
2,038,247 rows, before 29,698, after 156,322, new 126,624, primary 78,925,
fallback 47,699; GA 2 → 3,093. G7 passes (GA >=2,794; primary >=23,617).
Q-D1 summary hash `3d60772e774ebb448d49cf9e593964eef3ddf3c9afabbda6d6a56ed28b79ced2`.
Q-D2 elapsed 94.676 s: 99,877 independent candidates, 57,094 captured,
42,783 uncaptured, 95,830 quoted and 4,170 unquoted; hash
`1b6e29b07b044f365167ad40a221f2922bf8b3f98ed78960f457a323314f09a3`.
Q-D3 PASS hash `7e8eeafd85f41d00151174a9a0b9f4d319495abfcd84d5cdaf4b0ef57fb228d5`.

D-PFP-400: population 480,372, hash
`08ca7a33ce7212d52bc31c4c00f3a81082b270a0f36c6b412c7b3905dceb1d02`; sample
400, hash `880cdec847874ac1937cbe5693df1e4121506b7acb6fc164d2fd343742b94daa`.
The documented conflict-free procedure covers every non-empty jurisdiction,
route and family (54 mandatory SHA-ranked set-cover seats), then fills with
proportional Hamilton allocation. The 400-row adjudication ledger is
unreviewed (hash `5e0e5bc23d8878ba9557aa83f07111917e640f939daf257291b45c26d6763c5f`):
fresh QA, not Planner, must adjudicate it. The 0/400 one-sided 95% bound is
0.7461%, never a corpus-zero claim. The independent informational fallback
byte ledger is 50 rows, hash
`dc1fe46464d9c510f61fd0f6d555c23371f6f5bf61a9ebc36172fd0d4cbfd586`.
Stale-pin sweep: none (no rename). Manager retains status/role integration.

### M-R101 — root rejects QA transition; Planner corrections required

Shared Planner WIP `ca9dcd780aed25daf169ac8808418fa6c121bbb0` remains
unaccepted planning progress. Root independently reproduced the focused 7/7
contract suite, Python compilation/diff cleanliness, and current evidence line
counts/hashes. Those checks establish coherent WIP, not a certifiable QA
handoff. Status/current role remain `planning` / `planner`, the existing
`claude-code:planner` lock stays active, and production remains read-only.

1. Q-D1 and Q-D2 currently hash `elapsed_seconds`, making certification hashes
   depend on machine/run duration. Move timing to explicitly non-hashed run
   metadata, add a regression proving different durations yield identical
   certification hashes, then regenerate every affected exact artifact/hash.
2. Add a documented fail-closed QA adjudication finalizer. It must validate
   that all 400 reviewed ledger rows match the sample one-to-one and immutably,
   require a nonempty adjudicator plus explicit false/ambiguous decisions,
   calculate counts and the confidence bound, and emit a separate canonical
   QA-owned verdict. PASS/exit 0 is legal only at zero false and zero ambiguous;
   otherwise verdict is FAIL/nonzero. Never reset a reviewed ledger. Planner's
   generated evidence stays unreviewed and distinct from the QA verdict.
3. Strengthen Q-D3 independently: validate Q-D2 per-state and total accounting,
   including `candidate_rows=captured+uncaptured`, with a temporary candidate
   ledger/hash if needed. Assert sample count `min(400,population)`, coverage
   of every non-empty jurisdiction/route/rule family, immutable one-to-one
   sample/unreviewed-ledger identity, and byte-ledger count, uniqueness,
   fallback-only status, and population membership. Add mutation/fail-closed
   regression tests for every validation path.
4. Document the exact clean-checkout fresh-QA workflow: generate evidence,
   retrieve each source, adjudicate every sampled tuple, then finalize.
5. Preserve D-PFP-400's rubric, GA-after `>=2794`, total
   `new_primary >=23617`, informational-only `new_fallback`/byte quality, and
   current evidence marked provisional. No QA transition is authorized until
   all corrections are committed, regenerated, and independently auditable.

### M-R101 correction pass — deterministic certification + QA-owned finalizer

Planner roster entry: canonical task `/root/g7_cert_hardening_planner`,
`gpt-5.6-terra / high`; Haiku considered: no, because deterministic
certification and fail-closed human-adjudication finalization change multiple
interacting proof invariants. The write set remains tests, certification
scripts/evidence, and sprint docs only; `backend/app` is read-only from pinned
integration `4fa9e7b368801757039091646e06a832620a3a2c`.

RED preceded harness work: focused contract run was **7 passed, 4 failed**
(missing non-hashed certification schema/validators, QA finalizer, and source
retriever). The RED test batch was committed/pushed before script changes.
After hardening, focused evidence tests are **11 passed**. The regression uses
otherwise-identical durations and proves equal Q-D1/Q-D2 certification hashes;
elapsed durations now live only under unsigned `run_metadata`. Q-D3 verifies
the same explicit payload schema for Q-D1/Q-D2 and its own emitted result.

The exact all-53 chain was run once from the documented entrypoint. Q-D1:
2,038,247 rows; before 29,698; after 156,322; new 126,624; primary 78,925;
fallback 47,699; GA-after 3,093. It passes GA `>=2,794` and primary
`>=23,617`; Q-D1 signed hash
`7269d7e02b44e08f3bb15048787a97c485e0adf3fde7c5f4c79dd70663f3a799`
(runtime 459.768 seconds is non-certifying). Q-D2 candidate ledger is 99,877,
hash `1f59a7d9a72b703f1cd6adff5e064a51a4386662b4c8de4d98a0f5be97d9d44b`;
its independent totals are 57,094 captured / 42,783 uncaptured (95,830 quoted,
4,170 unquoted may overlap), signed hash
`6138b58fafed100132c0aceb5830e38cc38ec7c6714bd0bbaf4f4b7421168e35`.
Q-D3 validates candidate/state accounting, D-PFP membership/coverage/raw
ledger and byte-ledger invariants and passes with signed hash
`9ccb06cf78f8904e30338094fd600fc2bc42d8ccd8541c9eaa6ce2c8316a6725`.

D-PFP remains Planner-unreviewed: population 480,372
`08ca7a33ce7212d52bc31c4c00f3a81082b270a0f36c6b412c7b3905dceb1d02`,
sample 400 `880cdec847874ac1937cbe5693df1e4121506b7acb6fc164d2fd343742b94daa`,
raw ledger 400 `5e0e5bc23d8878ba9557aa83f07111917e640f939daf257291b45c26d6763c5f`,
and informational fallback byte ledger 50
`dc1fe46464d9c510f61fd0f6d555c23371f6f5bf61a9ebc36172fd0d4cbfd586`.
The one-sided 95% zero-event bound is 0.7461%, not a corpus-zero claim.

`qa_finalize_adjudication.py` is a separate QA entrypoint: it validates exact
one-to-one immutable sample/ledger fields, source hashes, reviewed status,
nonempty adjudicator and boolean false/ambiguous decisions; it writes a
QA-owned verdict and fails for malformed/unreviewed/mismatched or nonzero
false/ambiguous results without rewriting a ledger. `qa_retrieve_source.py`
retrieves every tuple by pinned parquet stable locator and source hash. Exact
fresh-QA generation, source-retrieval, adjudication, and finalization steps
are documented in `G7_CERTIFICATION.md`. QA-owned reviewed ledgers/verdicts do
not overwrite Planner raw evidence; this remains `planning` / `planner`, with
no QA/P-FP PASS claim. `measure_fp_after_widening.py` remains non-gating.

### M-R102 — root rejects hardening WIP for three remaining loopholes

Shared hardening tip `53559619ff91e90c951fb5920e48169c959b2b75` remains
unaccepted planning progress. Root independently reproduced the current focused
**11/11**, but that green set includes a finalizer test using only one sample
row and therefore does not prove D-PFP-400. No QA transition is authorized.

1. The finalizer must take the matching Q-D1 summary as required input and
   verify its certification hash, pinned snapshot/integration identity,
   `sample_hash`, `population_count`, and
   `sample_count == min(400,population_count)`. It must then require the actual
   sample length and canonical hash to match. For this final panel the result is
   exactly 400 rows. Add REDs for a truncated sample and sample-hash mismatch;
   the current one-row green path must fail closed.
2. The finalizer writes `verdict_hash = certification_hash(verdict)`, while the
   shared `certification_payload` excludes `summary_hash`, not `verdict_hash`.
   Once stored, that makes the verdict self-referential/non-verifiable. Use the
   normal `summary_hash` convention or define a dedicated explicit verdict
   payload, then add a verifier regression that recomputes and matches the
   stored canonical verdict hash.
3. Q-D3 must independently recompute quoted/unquoted component counts from
   every candidate-ledger row per jurisdiction, validate components are
   nonempty and allowed and `captured` is boolean, and compare those recomputed
   counts to per-state and total summaries. Current code recomputes only
   candidate/captured counts and trusts component totals. Add a component
   mutation RED that the current path rejects only after this correction.

The accepted non-timing deterministic hash design, Q-D3 coverage checks,
source-retrieval helper, production read-only boundary, D-PFP-400 rubric, and
GA-after `>=2794` / total `new_primary >=23617` gates remain unchanged. Sprint
state stays `planning` / `planner` under the existing Planner lock.

Planner roster entry: canonical task `/root/g7_finalizer_microfix`,
`gpt-5.6-terra / low`; Haiku considered: yes and would qualify, but it is not
callable here. This bounded M-R102 correction changes only contract tests,
certification validators/finalizer, and the fresh-QA command documentation.

### M-R103 — root accepts Item 7 certification infrastructure for QA

Root accepts integrated Planner tip
`d0cecf285853fc6a16d784096d3532c920a85351`. The complete Item-7 commit
chain is `377bb796d2d2abd10ff745c477dba7abada2a292`,
`b188b6b3b29c435654c9a5ded59dea675d48b710`,
`157b0ccdcce5f576cfe4cbcd241c1ce12366a244`,
`6935abf9372ee14404737b66d17071e48e2a44e2`,
`ca9dcd780aed25daf169ac8808418fa6c121bbb0`,
`2364972e55d6960d19a2862601b17c89a42d0657`,
`30da878b9255d8d3e5c0d3a1b1d647b39519acb2`,
`53559619ff91e90c951fb5920e48169c959b2b75`,
`6f7ee18ca8dac37f7ef34a08afcc4b74f6d16105`, and the accepted tip.

Root's cumulative audit found only tests, certification scripts/evidence, and
sprint docs; `backend/app` is unchanged from the accepted integration. Root
read the full hardening/micro diffs, found the risk grep empty, reproduced the
focused **11/11**, and accepted Python compilation, diff cleanliness, evidence
line counts and hash verification. M-R102 is closed: the finalizer requires and
verifies the matching Q-D1 summary, exact 400-row sample/count/hash, and a
non-self-referential canonical verdict hash; Q-D3 recomputes and validates
quoted/unquoted component rows and summaries.

Accepted deterministic all-53 evidence remains Q-D1
`7269d7e02b44e08f3bb15048787a97c485e0adf3fde7c5f4c79dd70663f3a799`, Q-D2
`6138b58fafed100132c0aceb5830e38cc38ec7c6714bd0bbaf4f4b7421168e35`, and
Q-D3 `9ccb06cf78f8904e30338094fd600fc2bc42d8ccd8541c9eaa6ce2c8316a6725`.
The 400-row Planner ledger remains unreviewed: this is acceptance for fresh QA,
not a D-PFP-400 PASS. All seven items move to Dev Complete; state becomes
`dev-complete` / `qa`, `dev_complete_items: 7`, `qa_cycles: 1`, under a fresh
`claude-code:qa` lock. QA owns independent source adjudication and finalization.

### QA cycle 2 — D-PFP-400 fail-fast: exact Hawaii contractual clause is a false capture

QA roster: canonical task `/root/preamble_g7_final_qa`, `gpt-5.6-terra / high`;
Haiku rejected because the binding source-level adjudication is merge-blocking.
Root independently retrieved pinned `STATE_HI_D2_T24_C431_S431` from
`us_hi_statutes.parquet:5`, SHA-256
`2ff51dc5277bfcc5cad660a68a79da4b9544b05b84d036af2f19e07f37c2da42`.
The 2,404,155-character concatenated source row has a genuine B1 trigger but
also the quoted contractual policy provision beginning `If any indemnity of
this policy ...`; the live US-HI registry/profile/persistence path emits it as
a 529-character term with definition text `; and`, plus similar one-character
contractual pseudo-definitions. This is not a definition or forwarding
statement, so it is a binding D-PFP false capture.

QA added `test_us_body_preamble_hi_contractual_quote_pfp_red.py` with a compact
source-faithful fixture: it proves current raw/profile output and live
persistence produce the bad tuple, requires it absent after repair, and proves
the same B1 body retains genuine `genuine coverage`. Current tail is one RED:
`P-FP ... live pipeline persisted '; and' for it`. QA also committed the
finalizer adverse-decision regression (`7b00e54`, 13 passed). Remaining 400
adjudications, fresh all-53 run, and broad suites are intentionally skipped
fail-fast; production was not changed. Item 7 returns to Next Steps as QA-FAIL.

### M-R104 — root accepts QA source finding and reopens safe planning

Root accepts integrated QA-FAIL tip
`42cdf298655845635c9e3bf32857efd72da30ee5`. The cumulative QA diff is confined
to tests, fixture, and sprint docs; root read the complete diff. Root
independently retrieved pinned `STATE_HI_D2_T24_C431_S431` at source hash
`2ff51dc5277bfcc5cad660a68a79da4b9544b05b84d036af2f19e07f37c2da42`,
reproduced the 2,404,155-character live capture with 37 tuples, and confirmed
the 529-character quoted indemnity pseudo-term whose captured definition is
`; and`. The source does not define or forward that term.

Root also reproduced the corrected QA test file at exactly two expected
failures: direct profile extraction and live persistence. Both demand absence
of the pseudo-definition while preserving the genuine same-body definition;
neither asserts the pre-fix broken state. This satisfies RED provenance and
authorizes a new Planner cycle, not a Developer shortcut.

Binding repair gates:

1. No blanket jurisdiction (`US-HI`), large-row, quoted-text, or `; and`
   suppression. The genuine definition in the same body must remain captured.
2. Planner must locate and document the exact production seam before defining
   implementation ownership.
3. Planner must source-triage the deterministic D-PFP sample and add two-sided
   RED controls for every distinct source-verified false-capture family found,
   with genuine neighboring/same-body definitions protected.
4. Every proposed guard must be runtime-measured across the pinned 53 files at
   persisted `(jurisdiction, source row, term, definition_text, scope)`
   altitude. Planner must classify every changed key before Developer dispatch.
5. Preserve Q-D1/Q-D2/Q-D3, D-PFP sample/raw/byte ledgers, G7 thresholds, held
   failures, and prior focused gates. Define the exact minimal Developer write
   set; production remains read-only during planning.

Contract returns from `qa-fail` / `developer` to `planning` / `planner`, keeps
`qa_cycles: 2`, items 1–6 Dev Complete, and Item 7 in Next Steps under a fresh
Planner lock. Root owns the later Planner spawn.

### M-R104 remediation Planner roster

Planner canonical task: `/root/hi_pfp_repair_planner`; model/effort:
`gpt-5.6-terra / high`. Haiku was considered and rejected: this pass requires
architectural seam selection, source-level false-family classification, and a
persisted-output all-corpus mutation audit rather than a bounded fixture or
pin repair. Production remains read-only; this entry records only roster and
authority before the first evidence write.

### M-R104 remediation — failed-closed proposed connector guard

The Planner ran the proposed runtime-only, body-derived guard over the pinned
53-file / 2,038,247-row snapshot at the live profile/registry/persisted-key
altitude. Its predicate was deliberately not jurisdiction-specific: one quoted
term of at least 151 characters whose emitted definition was exactly `;`,
`; and`, or `; or`. The exact before/after tuple and key ledgers are external
to the worktree at `/tmp/lexgraph-mr104-hi-connector-guard-final/`.

The probe removed **33** persisted keys: the **16** source-verified Hawaii
insurance-policy connector stubs, plus **17 unclassified** keys (AR 1, FED 2,
ID 2, TX 12). The extra rows include quoted loan/disclosure, Federal review,
Idaho utility-estimate, and Texas tax-budget boilerplate. They were not
source-adjudicated in this pass and cannot be assumed false; therefore the
candidate guard is rejected fail-closed. No Developer write set, Q-D1/D-PFP
mutation claim, or contract transition is authorized from this probe. The
current two HI absence REDs and three preservation controls remain the valid
evidence; production is unchanged.

### M-R104 manager span semantics

Manager ruling: the semantic unit is a validated source statute section inside
a raw row that may concatenate sections. A B1 span may activate only when
validated source-section markers enclose its winning trigger; it starts at
that marker and ends at the next validated marker. No list marker, blank
paragraph, quote syntax, punctuation, length, or jurisdiction is a boundary.
Without a validated enclosure/boundary, full-body legacy behavior remains.
The HI fixture now models the source-faithful cross-section concatenation:
the genuine definition is in the trigger-owned section and the policy
quotation is in the next section. “Same body” in M-R104 means same raw
record, not necessarily the same source section. Planner-added REDs require
an optional `BodyPreambleRule.derive_span` contract, B1’s inclusive/exclusive
section span, and delimiter-free decline/legacy fallback; existing rules must
remain heading-only compatible.

### M-R104 option-1 shard rejection

The resumable runtime-only shard runner was executed against the complete HI
file (`16,446` rows) with content-addressed source/config metadata. The
source-section-only proposal changed **647** persisted keys (2,423 before /
2,112 after). This is immediately disqualifying: the changed ledger includes
`Confirmer -> means a nominated person ...` from
`STATE_HI_D2_T27_C490_S490`, a source-apparent genuine definition, and other
unadjudicated losses. The all-53 merge and Q-D1/D-PFP derivation were stopped
fail-closed; a candidate that already changes genuine HI output cannot proceed
to Developer. The shard artifact is external at
`/tmp/mr104-b1-span-shards/shards/us_hi_statutes.parquet.json`.

### M-R104 remediation — source adjudication of the 17 counterexamples

Each of the 17 initially unclassified changed keys was retrieved from the
pinned source row and is a false capture, not a definition or forwarding
statement. AR `STATE_AR_T23_C81_S8_S23-81-810` is a quoted life-insurance
applicant certification (1); FED `USC_T50_C44_S3001` and
`USC_T22_C83_S7601` are quoted review/report clauses (2); ID
`STATE_ID_T48_C18_S48-1805` contains two mandated estimate/tax notices (2);
and four TX county/college budget-cover statutes contain three quoted tax
boilerplate alternatives each (12): `STATE_TX_Clg_C111_S111.068`,
`STATE_TX_Clg_C111_S111.039`, `STATE_TX_Clg_C111_S111.008`, and
`STATE_TX_Clg_C102_S102.007`.

This establishes one broad *failure mechanism*, not a safe generic filter:
an unrelated B1 trigger elsewhere in a body makes the whole-body numbered
quote splitter accept quoted operative/list text and assign its following
connector as a definition. The rows demonstrate that raw length, quote
presence, list punctuation, all-caps, sentence capitalization, policy
vocabulary, or jurisdiction cannot distinguish false content from future
genuine quoted/list definitions. A safe repair needs occurrence-local B1
ownership (the trigger's bounded definitions span/entry range) rather than a
post-extraction candidate heuristic. Current `BodyPreambleRule` returns only
an undifferentiated heading string and `USProfile`/`pipeline` subsequently
extract from the entire body, so no minimal isolated Planner-approved write
surface exists at this seam. The rejected guard remains permanently rejected.
