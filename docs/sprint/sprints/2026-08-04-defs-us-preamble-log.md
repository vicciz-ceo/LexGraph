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
