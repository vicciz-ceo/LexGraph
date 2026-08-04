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
