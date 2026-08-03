# Sprint log — 2026-08-02-us-state-law (overflow sink)

Full narration, rationale, and test-run output that doesn't fit the
≤400-line contract. Contract stays the authoritative summary; this file is
where the Planner's reasoning and raw command output live.

## R4 — true test baseline (established before any RED test was written)

```
$ backend/.venv/bin/pytest backend/tests -q
........................................................................ [ 14%]
........................................................................ [ 28%]
........................................................................ [ 42%]
........................................................................ [ 57%]
........................................................................ [ 71%]
........................................................................ [ 85%]
........................................................................ [100%]
504 passed, 14 warnings in 10.51s
```

```
$ npm --prefix frontend run test -- --run
 Test Files  20 passed (20)
      Tests  151 passed (151)
```

```
$ npm --prefix frontend run typecheck
> tsc --noEmit
(exit 0, no output)
```

**Conclusion: the repo-profile.md snapshot (126 backend / 39 FAILED / 87
ERROR; 59 frontend RED) is stale and wrong as of 2026-08-02.** Backend is
504/504 green, frontend is 151/151 green (20 files), typecheck is clean.
Whatever fixed the pre-existing red happened in a prior sprint
(2026-07-31-admin-provisioning, PR #17, merged per `git log`) and was never
reflected back into `repo-profile.md`. This sprint starts from an
all-green baseline — any red from this point on is this sprint's own.

## Full backend RED confirmation run (continue-on-collection-errors)

```
$ backend/.venv/bin/pytest backend/tests -q --continue-on-collection-errors
...
19 failed, 507 passed, 14 warnings, 4 errors in 10.94s
```

507 passed = 504 pre-existing (untouched, still green) + 3 new "must keep
passing" guard/sanity assertions the Planner added alongside the RED ones
(`test_jurisdiction_api_validation.py::test_create_assertion_still_accepts_null_jurisdiction`,
`::test_create_assertion_accepts_a_real_controlled_vocabulary_code` is
itself counted in the 5 "target" failures — correction: the 2 passing
guards are `test_create_assertion_accepts_a_real_controlled_vocabulary_code`
is actually one of the 5 that... see per-file breakdown below) — exact
per-file breakdown:

| File | Failed | Passed | Collection error |
|---|---|---|---|
| `test_jurisdiction_vocabulary.py` | — | — | yes (ImportError) |
| `test_jurisdiction_api_validation.py` | 5 | 2 | — |
| `test_definition_links_profiles.py` | — | — | yes (ImportError) |
| `test_definition_links_pipeline_profile_dispatch.py` | 3 | — | — |
| `test_us_profile_definitions_section_end_to_end.py` | — | — | yes (ImportError) |
| `test_definition_links_us_profile.py` | — | — | yes (ImportError) |
| `test_definition_links_pipeline_jurisdiction_stamping.py` | 2 | — | — |
| `test_ingest_us_statutes.py` | 6 | — | — |
| `test_ingest_us_statutes_cli.py` | 3 | 1 | — |

19 failed + 4 collection errors = 23 RED signals, all confirmed individually
(see each file's own run below) to fail for the RIGHT reason
(`ModuleNotFoundError`/`ImportError`/`TypeError: unexpected keyword
argument`/genuine assertion failures against real behavior) — never a typo
or an unrelated collection error. 504 pre-existing tests are untouched and
still green (507 - 3 new passing guards = 504).

## Full frontend RED confirmation run

```
$ npm --prefix frontend run test -- --run
 Test Files  5 failed | 20 passed (25)
      Tests  10 failed | 151 passed (161)
```

151 passed = exactly the pre-existing baseline, untouched. 20 passed files
= the pre-existing 20 files. 5 new files, all RED (1 as a whole-suite
import failure with 0 counted tests — `jurisdictions.test.ts` — plus 4
files contributing 10 individually-failing tests, matching each file's `it`
count exactly: `AssertionSuggestionForm.jurisdiction.test.tsx` (3),
`KnowledgeBasePage.jurisdiction_filter.test.tsx` (2),
`ReviewQueuePage.jurisdiction_filter.test.tsx` (2),
`ProfilePage.jurisdiction_preference.test.tsx` (3)).

## Design decisions not fully spelled out in the contract's item bodies

### Jurisdiction vocabulary module location + shape

`backend/app/services/jurisdiction.py`, mirroring the existing
`ALLOWED_ASSERTION_TYPES`/`validate_assertion_type` pattern already in
`backend/app/services/validation.py` (same package, same
"controlled-vocabulary constant + validate_* raises ValidationError"
shape — read directly by the Planner before choosing this). Exports
`JURISDICTION_CODES` (ordered tuple, not a set) and `validate_jurisdiction`
(raises the SAME `ValidationError` class every other validator in this
codebase raises, not a new exception type). Case-sensitive, exact-match
only — no fuzzy/normalized matching, matching `guards.resolve_law_title`'s
existing "no fabricated guess" discipline elsewhere in this codebase.

### Frontend vocabulary: endpoint vs mirror (R5's explicit either/or)

Recommended AND pinned in tests: `GET /api/v1/jurisdictions` (new route)
is the RUNTIME source of truth (so a dropdown can never drift from the
backend list without a code change on BOTH sides being required to even
compile/pass tests). `frontend/src/constants/jurisdictions.ts` is a
compile-time TS literal mirror (`JURISDICTION_CODES`, `JURISDICTION_OPTIONS`)
so `Assertion["jurisdiction"]` and form state can be statically typed — a
drift-detection contract test (comparing this mirror against a live/mocked
fetch of the new endpoint) is listed as a FOLLOW-UP acceptance criterion
in the vocabulary item, not written by the Planner (no endpoint exists yet
to fetch against).

### `EU` in `seed_demo.py` — a real, pre-existing conflict with the new vocabulary

`backend/app/seed_demo.py` sets `jurisdiction="EU"` four times (lines
253, 297, 382, 391) and creates assertions through the REAL HTTP API
(`TestClient`, per its own module docstring) — `backend/tests/integration/
test_bootstrap_cli.py` calls `seed_demo` end-to-end. `"EU"` is NOT in the
director's controlled vocabulary (`IL` + `US-*` only). Once the vocabulary
item's API validation lands, `seed_demo.py` will start failing its own
API calls (422) unless `EU` is changed to a valid code FIRST. This is not
a test-root stale pin (seed_demo.py is application code, not a test file)
so it falls outside the mechanical stale-pin sweep below, but it is a real,
concrete regression the vocabulary item's Developer must fix in the SAME
commit that adds API validation — recorded here so it isn't missed.
Recommended replacement: `"IL"` (the demo content is jurisdiction-generic;
no state-specific meaning is lost).

### G1 seam shape

`app.definition_links.profiles.get_profile(code) -> JurisdictionProfile`,
additive registry, NOT a rename of the existing bare module functions
(`sections.is_definitions_heading` etc. stay exactly as they are — ~20
existing test files import them directly by name and ruling R2 forbids
editing them). `HebrewProfile` (`"IL"`) is a thin wrapper delegating to
those unchanged functions. Minimum surface: `.code`, `.is_definitions_heading`,
`.normalize_for_parsing`, `.find_term_uses`, `.detect_cross_law_derivations`
— each keeping the wrapped function's exact parameter names/order/defaults.

Deviation from the director's literal decision text (which names only
"sections/matcher/derivation/normalize"): the Planner also extended the
profile surface to `.extract_definitions_from_section` (extract.py's
concern) and `.find_citations` (a NEW capability, no Hebrew analog) —
because gate G2 ("extracts its terms") and G4 ("§ 101" detected with NO
trigger phrase nearby) are literally unsatisfiable without them. Recorded
transparently, not silently expanded.

### `Document.jurisdiction` + `ingest_wiki_law(..., jurisdiction="IL")`

New NOT NULL column on `Document`, defaulting to `"IL"`. `ingest_wiki_law`
gains a keyword-only `jurisdiction` parameter defaulting to `"IL"` —
deliberately a DEFAULT, not a required kwarg, because ~20 existing Hebrew
integration tests call `ingest_wiki_law(...)` with no such kwarg at all
(grep-verified across `backend/tests/integration/test_definition_links_*.py`,
`test_qa_regression_*.py`, `test_assertion_standing_api.py`,
`test_definition_links_pipeline_duplicate_article_attribution.py`,
`test_definition_links_pipeline_law_ref_parenthetical_qualifier.py`,
`test_definition_links_pipeline_repeal_marker_guard.py`,
`test_definition_links_pipeline_live.py`, `test_definition_links_ingest.py`,
`test_definition_links_cli.py`) and R2 forbids editing them. This is the
ONLY signature shape that satisfies both "the pipeline must always know a
document's jurisdiction" (G1's dispatch key, G5's stamp source) and "zero
Hebrew test edits". Verified via grep that NO existing test asserts on
`Document.jurisdiction` or on any created assertion's `.jurisdiction`
value in the definition-links test estate — so changing the pipeline's
stamped value from the current hardcoded `None` to `"IL"` (the new
default) breaks nothing.

Profile dispatch is PER DOCUMENT (not once per matter/pipeline run) —
a matter may hold documents from more than one jurisdiction side by side.

### `link_articles_to_definitions(definitions, articles, *, profile=None)`

New keyword-only `profile` parameter, default `None` (preserves today's
Hebrew-only `find_term_uses` call for every existing call site — grep-
verified all 8 existing call sites in `test_definition_links_matcher.py`
plus `pipeline.py`'s own call are positional-only, 2 args, no kwargs).
When a profile is given, term-matching delegates to `profile.find_term_uses`
instead of the module-level Hebrew-specific function.

### US dataset ingester: one Document per parquet FILE, one Article per ROW

Mirrors `ingest_wiki_law`'s "one Document per ingested law/file" shape —
simplest, matches the director's "bulk-ingest everything" framing (109
files -> 109 Documents), scales predictably. `jurisdiction` is REQUIRED
(no default) on the new `ingest_us_statute_rows` — unlike `ingest_wiki_law`,
this is a brand-new function with zero existing call sites, so there is no
backward-compatibility reason to default it.

### Profile preference: frontend-only, localStorage

No backend user-preference mechanism exists anywhere in this codebase
today (`User` model has only `id`/`email`/`display_name`; zero
`localStorage` usage found anywhere in `frontend/src` before this sprint).
Scoped as a frontend-only preference (`lexgraph:default-jurisdiction:<userId>`
in `localStorage`, set on `ProfilePage`) — no backend schema change. A
backend-persisted, cross-device preference is a reasonable future upgrade,
out of scope this sprint.

## Real dataset fixture — full retrieval session

Fetched via a disposable venv OUTSIDE this repo (`pip install
huggingface_hub pyarrow` into a scratch venv under the session's
scratchpad directory) — `backend/.venv` was never touched;
`backend/pyproject.toml` was never touched. Verified directly: `backend/
.venv` has NEITHER `huggingface_hub` NOR `pyarrow` NOR `pandas` installed
(`ModuleNotFoundError` for all three) as of this sprint.

```
$ backend/.venv/bin/python -c "import huggingface_hub"
ModuleNotFoundError: No module named 'huggingface_hub'
$ backend/.venv/bin/python -c "import pyarrow"
ModuleNotFoundError: No module named 'pyarrow'
```

Downloaded `us_de_statutes.parquet` (21,649 rows) via
`hf_hub_download(repo_id="vaquill/open-us-law", filename="us_de_statutes.parquet",
repo_type="dataset")` — confirms dossier §4's schema exactly (24 columns:
`act_id, citation, citation_short, state, jurisdiction, document_type,
title_number, title_name, chapter, chapter_name, section_number,
section_title, breadcrumb, display_path, act_status, text, word_count,
source_url, last_amended_year, subsection_count, cross_references_usc,
cross_references_cfr, public_laws_referenced, year`).

**New finding not in the dossier**: EVERY row's `section_title` (verified
across all 21,649 Delaware rows, not just the 3 picked) is corrupted by a
scrape/double-encoding artifact —
`"§ Â\r\n        796. Definitions."` instead of a clean
`"796. Definitions"`-shaped string. An English Definitions-heading matcher
that assumes clean input (mirroring Hebrew `sections.py`'s exact-anchor
match) will not match ANY row's heading verbatim. The US profile's heading
detector must match on a substring/contains basis, not an anchored regex.
Full detail + the 3 picked rows' complete field-by-field content:
`backend/tests/fixtures/us_statutes/README.md`.

3 rows picked (Delaware — matches the pre-existing frontend test literal
`"US-DE"` at `AssertionDetailPage.test.tsx:80`):
1. `STATE_DE_T5_C7_SVIII_S796` — real Definitions section, 3 terms
   ("Affiliate", "Branch office", "Insured depository institution"),
   mixing a same-chapter internal ref (`§ 770 of this chapter`) with two
   federal cross-refs (`12 U.S.C. § 1841(k)`, `12 U.S.C. § 1813(c)`).
2. `STATE_DE_T29_C60A_S6060` — NOT a Definitions section; clean short
   `26 U.S.C. § 401(a)` citation in prose.
3. `STATE_DE_T31_C52_SIII_S5227` — cross-TITLE reference
   (`as defined in § 901 of Title 10`, a different law/title than its own
   Title 31) — the US analogue of Hebrew's cross-law derivation.

Committed as BOTH `de_sample_rows.json` (used by every
deterministic-engine test — no `pyarrow` needed to read it) and
`de_sample_rows.parquet` (10.5 KB, a REAL byte-valid Parquet file written
from the identical 3 rows via `pyarrow.Table.from_pylist` +
`pq.write_table`, round-trip-verified byte-identical back to the JSON —
used only by the CLI/parquet-reading test, which is legitimately RED via
`ModuleNotFoundError: pyarrow` today).

## Stale-pin sweep — full detail

Case-insensitive `grep -riE` for jurisdiction-related literals across all
4 test roots (`backend/tests/unit/`, `backend/tests/integration/`,
`backend/tests/e2e/` [empty for this concern], `frontend/src/**/__tests__/`)
plus `*.snap` (none exist in this repo — `find frontend/src -name "*.snap"`
returns nothing).

**Backend**: `grep -rn 'jurisdiction' backend/tests --include="*.py"` —
only 3 hits outside `conftest.py`'s `jurisdiction: None` default builder
(itself compatible, `None` stays a legal value): two unrelated prose
matches (`test_search_sort.py`'s "a proposition about jurisdiction",
`test_review_workflow.py`'s "Please clarify jurisdiction." comment body)
— neither is a jurisdiction VALUE, both are just the word appearing in
unrelated proposition/comment text. Zero backend test hardcodes an
invalid-per-the-new-vocabulary jurisdiction value.

**Frontend**: `grep -rn '"US-DE"\|"IL"\|"EU"' frontend/src --include="*.tsx" | grep -i jurisdiction`
found exactly 6 hits, ALL already valid under the chosen vocabulary format
(`"IL"` x4, `"US-DE"` x2 — `ContestedPage.test.tsx:74`,
`KnowledgeBasePage.test.tsx:59`, `ProfilePage.test.tsx:70`,
`ReviewQueuePage.test.tsx:91`, `AssertionDetailPage.test.tsx:80,132`).
**Zero re-pointing needed** — these values already match the director's
`IL`/`US-<postal>` format exactly, which is WHY Delaware was picked as
this sprint's real-data pilot state (keeps the whole sprint's fixtures
consistent with what the existing test estate already assumes).

**Conclusion: no test-root stale pins exist.** The one real drift risk
found (`seed_demo.py`'s `"EU"`) is APPLICATION code, not a test file — see
above, flagged as a required same-commit fix for the vocabulary item's
Developer, not something this sweep re-points itself (out of the sweep's
defined scope: test roots only).

## QA cycle 2 — full detail (overflow from `## QA Notes`)

### Q3 full finding — item 3's wave-3 heading fix is broken two ways

**(a) Catastrophic backtracking (ReDoS) in `_DEFINITIONS_HEADING_RE`.**
`us_profile.py`'s tightened regex is
`^(?:[^A-Za-z]+|Section\s+\d+\.?)*Definitions?\b`. The `Section\s+\d+\.?`
alternative never fires on real data (real headings use `§`, never the
spelled-out word "Section"), so the only alternative that ever matches the
leading noise is `[^A-Za-z]+`, repeated inside an outer `*` — the textbook
`(X+)*` catastrophic-backtracking shape: when the overall match ultimately
fails, the engine tries every way of partitioning the non-letter run across
repetitions of the group before giving up, which is exponential in the
run's length.

Synthetic confirmation (isolated from real data, to characterize the growth
curve):
```
n=25 (25 spaces + non-matching letter): 1.10s
n=30: still running after 5s (capped)
```
Real-data confirmation: scanned all 21,649 real rows of
`us_de_statutes.parquet` for the length of each heading's leading non-letter
run (cheap `^[^A-Za-z]*` prefix match, no backtracking risk). Distribution:
`>=15`: 21,522 rows (nearly all — the mojibake scrape-noise prefix alone is
~10-15 chars); `>=20`: 1,483; `>=25`: 23; `>=30`: 1; `>=40`: 1 (max 43,
`STATE_DE_T10_C54_S5402`). That single real row's real heading:
```
'§ Â\r\n        5402. \r\n                  @*@*Evans v. State@*END@*\r\n                  @*bold@* [See Evans v. State, 872 A.2d 539 (Del. 2005) concerning unconstitutionality of this section.].@*END@*'
```
`is_definitions_heading(...)` on this exact string, capped with a SIGALRM(8),
did not return — confirmed hang, not merely "slow." The PRE-fix unanchored
`\bDefinitions?\b` substring check (no nested quantifier, linear time)
returns instantly on the same input, so this is a regression introduced BY
the wave-3 tightening, not a pre-existing issue. First attempt at a full
21,649-row `DEF_RE.match` sweep (2s-per-row SIGALRM cap) itself ran past
120s and had to be killed — independent circumstantial confirmation that
MANY real headings, not just the one committed to the fixture, trigger slow
backtracking (the 20-43-char-prefix population above, ~1,500+ rows in this
one state file alone).

**(b) Under-match: letter-embedded section numbers break the "first word"
assumption.** Filtered to the 973 real DE headings containing the word
"Definition(s)" (`\bDefinitions?\b` search — no backtracking risk, plain
substring). Of these, 938 have a short (<20 char) non-letter prefix, safe to
regex-test directly without ReDoS risk; the other 35 were skipped in this
sweep (risky/slow, would need the same bounded-deadline treatment as (a) to
test safely — not attempted, out of scope for this pass, but several of
them — e.g. `'§ Â\r\n        3-103. Definitions.'`,
`'§ Â\r\n        9-102. Definitions and index of definitions.'` — visibly
SHOULD match and would be worth re-checking once (a) is fixed). Of the 938
safe ones: 786 matched, **152 did not** (16.2% of the safe subset, 15.6% of
the full 973). Every one of the 152 shares the same root cause: the section
number itself contains a letter (`12D-102`, `4A-103`, `9002A`, `10201A`,
`8102A`, `3-103`... — this list is large; full 152-row dump captured during
investigation, not reproduced here, sample of ~150 shown in QA's terminal
history). Representative real example used in the committed test/fixture:
`STATE_DE_T6_A4A_P1_S4A-103`, heading `"§ Â\r\n        4A-103. Payment order
â Definitions."`, body is a genuine 5-term UCC-style Definitions section
(`"Payment order"`, `"Beneficiary"`, `"Beneficiary's bank"`, `"Receiving
bank"`, `"Sender"`, each `"Term" means ...`) — this exact numbered-block/
leading-quote shape is what `extract_definitions_from_section` already knows
how to parse; only the heading gate is wrongly excluding it.

Real full JSON rows for both `STATE_DE_T10_C54_S5402` and
`STATE_DE_T6_A4A_P1_S4A-103` are committed at
`backend/tests/fixtures/us_statutes/de_qa_cycle2_rows.json`, alongside the
Q2 blanked-chapter row, per ruling R6 (no network access in the committed
suite; these were fetched once during investigation via
`huggingface_hub.hf_hub_download`, same recipe as the existing fixture
README documents).

### Q5 full finding — bulk-run readiness concerns, in order of severity

1. **Blocking: Q3a's ReDoS.** `run_definition_linking` calls
   `profile.is_definitions_heading(art.heading)` once per Article with no
   timeout anywhere in the call chain. At ~2M real articles across 109
   files, hitting even one heading shaped like `STATE_DE_T10_C54_S5402`'s
   (and DE alone already has one, plus ~1,500 rows with a >=20-char
   non-letter prefix that are at least at meaningfully elevated risk) is
   expected to hang the definition-linking pass indefinitely. This must be
   fixed before the manager's planned bulk run, not treated as a nice-to-
   have.
2. **N+1 query pattern.** `ingest_us_statute_rows`'s per-row
   `existing_article` lookup (`select(Article).where(...)`) plus two
   `session.flush()` calls per new row means ~2M+ individual round trips
   across the full corpus — a real wall-clock cost (not a correctness
   issue) worth batching/bulk-checking before a from-scratch 109-file run,
   given R3 requires the run to be measured and honest about timing.
3. **Session identity-map growth across a whole file.** The CLI's
   `ingest_us_statutes_cli.py` opens ONE `Session` for the whole file and
   only closes it in a `finally` after all `iter_batches()` batches are
   processed; `ingest_us_statute_rows` commits per batch, but a commit does
   not evict already-flushed ORM objects from the session's identity map —
   they accumulate for the life of the file. The docstring's "keeps memory
   bounded" claim is true only for the raw pyarrow row buffers, not for the
   accumulated SQLAlchemy object graph. Largest real files: federal
   statutes 88.7MB, CA statutes 71.1MB (recon dossier §4) — likely
   hundreds of thousands of rows each. Worth watching (`session
   .expunge_all()` after each batch commit, or periodic session
   recycling) if the manager sees memory growth during the real run.
4. **Mid-file corruption not distinguished from a clean zero-row failure.**
   `pq.ParquetFile(input_path)`'s own open-time errors are caught and
   reported cleanly (exit 1, clear stderr message). A corruption that only
   surfaces mid-iteration (inside the `for batch in
   parquet_file.iter_batches()` loop, e.g. a bad row group later in a
   large file) is NOT caught by the narrow `except (ValidationError,
   ValueError)` around that loop — it propagates as an uncaught pyarrow
   exception. The process still exits non-zero (Python's default
   unhandled-exception behavior), so the runbook's `|| echo "FAILED: $f"
   >> failures.log` loop still correctly logs the file as failed and moves
   on to the next one (no abort-whole-run risk) — but batches that
   committed before the crash stay committed, and `failures.log` alone
   can't tell the operator "this file ingested 0 rows" from "this file
   ingested 40,000 rows then crashed" without a DB query. Low severity
   given the idempotent re-run story (fixing/re-fetching the file and
   re-running is safe), but worth a documented caveat in RUNBOOK.md.
5. **No automated filename → jurisdiction-code mapping.** The RUNBOOK's
   documented bulk-run loop leaves `<jurisdiction-code-for-this-file>` as a
   manual per-file fill-in the operator must supply (the dataset's own
   `us_<state>_statutes.parquet` naming makes this mechanical, but nothing
   in this codebase automates the mapping). Low severity: `validate
   _jurisdiction` fails loudly and immediately on a wrong/unrecognized
   code (never silently mistags a document), so the failure mode is safe,
   just not maximally convenient for a 109-file run.

## QA cycle 3 (2026-08-02) — full detail

Method: downloaded 12 real state files beyond the Developer's DE/NY pair
(FL, IL, DE, NY, CA, TX, PR, WA, OH, GA, PA — plus DE/NY re-checked) into a
scratch dir outside `backend/.venv` (ruling R6), ran the real
`is_definitions_heading`/`ingest_us_statute_rows`/CLI code directly against
them, cross-checked every claim against the actual DB where applicable.
None of this touched implementation code; only committed test files +
fixtures + this contract were modified.

### Q1 — item 3, full accuracy breakdown per state (case-INsensitive "definition" as the candidate pool, matching manager methodology restricted to exact-capital-D gives an incomplete picture — see below)

| file | rows | any-case candidates | exact-capital-D candidates | matched | missed-among-capD |
|---|---|---|---|---|---|
| DE | 21,649 | 1,036 | 973 | 973 | 0 |
| NY | 40,102 | 1,547 | 1,416 | 1,416 | 0 |
| FL | 24,866 | 852 | 748 | 621 | **127** |
| TX | 122,535 | 5,033 | **0** | 0 | 0 (never had a capD candidate at all — ALL-CAPS convention) |
| WA | 51,498 | 2,007 | 1,974 | 1,785 | **189** |
| OH | 33,161 | 970 | 223 | 154 | **69** |
| PA | 14,547 | 547 | 532 | 532 | 0 |
| GA | 28,154 | 0 | 0 | 0 | 0 (section_title never contains descriptive text at all — see below) |

The manager/Developer's "0 missed / 0 false positives" claim is TRUE for
DE/NY specifically, restricted to capital-D candidates — but does NOT
generalize: FL/WA/OH all show real misses even under that same narrow
methodology, before even reaching the case-sensitivity or structural
defects below.

**Root-caused missed cases (samples, all real headings):**
- FL dotted-number ("941.34 Definition..." → "34 Definition..." after
  partial number-strip → neither first-word nor last-word rule fires):
  `250.542 Definitions; mutual aid.`, `686.501 Definitions; ss.
  686.501-686.506.`, `409.403 Definitions; Interstate Compact...`
- WA/OH same root cause plus their own dash-heavy citation conventions:
  `RCW 58.04.003: Definition of surveyor.`, `§ 3113.45. Definitions for
  sections 3113.451 to 3113.459`

**Case-sensitivity, verified separately (any-case candidates minus
exact-capital-D candidates = "can never match regardless of any other
fix"):** DE 63, NY 131, FL 104, TX **5,033 (100% of TX's candidates)**, WA
33, OH **747 (77% of OH's candidates)**, PA 15.

**Structural defect (`section_title` carries no descriptive heading text
at all, verified against every row in the file, not a sample):**
- IL: 72,162/72,456 rows (99.6%) have `section_title` exactly matching
  `"Section <N>"`; confirmed via a real row (`STATE_IL_C325_A7_S15`,
  "Sec. 15. Definitions.", 5 real defined terms) that the real
  `ingest_us_statute_rows → run_definition_linking` path creates ZERO
  definitions from.
- CA: 161,422/161,429 rows (100%) — same shape.
- GA: `section_title` is always a bare citation string ("Georgia Code
  Title 2. Agriculture § 2-12-8"), 0/28,154 rows contain the word
  "definition" anywhere in `section_title`; grep of `text`'s first 150
  chars for a "Definitions" pattern still finds 48 real GA rows that are
  genuine Definitions sections, all silently unreachable via heading
  detection.

**Adversarial stoplist probe (constructed real-shaped headings):**
correctly rejects `"Repeal of Definitions"`, `"Exceptions/Amendments to
Definitions"`, `"Subject to Definitions"`, `"Provisions Without
Definitions"`; correctly accepts `"General/Other Definitions"`,
`"Payment Order-Definitions"`, `"Terms and Definitions"`. Found a real gap:
`_PRECEDING_EXCLUSION_WORDS` includes "including"/"except" but NOT
"excluding"/"containing"/"having"/"governing" — constructed cases like
`"Chapter Excluding Definitions"`, `"Rules Governing Definitions"` over-
match (return True) when they arguably shouldn't. Scanned all ~700k real
headings sampled across 12 files for this exact gerund-before-Definitions
shape: **0 real occurrences found**. Reporting honestly per the brief's
instruction ("find the edges... even if you still PASS") — this edge is
real but currently theoretical, not itself a bounce reason.

### Q2 — item 5, collision-key verification beyond DE

Collision count of `(section_number, section_title, text)` across full
real files: IL 72,456 rows / 0 collisions; FL 24,866 / 0; **CA 161,429 rows
/ 176 collisions across 83 groups**; **PA 14,547 rows / 11 collisions
across 9 groups** (both confirmed genuinely different sections by
different `citation`/title, e.g. PA's `74 Pa.C.S. § 7` vs `51 Pa.C.S. § 7`
sharing verbatim cross-title boilerplate). `citation` would have correctly
disambiguated every one of these (all citations differ), even though
`citation` alone was correctly rejected earlier for its own single known DE
duplicate — no single field the dataset provides is safe alone; a
composite key including `citation` (falling back only when `citation`
itself collides) may be the right shape, but that is an implementation
decision for the Developer, not QA's to make.

`section_title`/`text` emptiness swept across ALL rows of 12 real files
(~460k rows total): `section_title` empty in 0.00% of rows in every file
checked — not an observed real risk in this dataset, though the code path
(`heading = row.get("section_title") or ""`) is still exercised safely if
it ever occurs (would only collide with another row sharing the exact same
number+empty-title+text, which — per the same argument the wave-4
docstring makes for `text` — is not observed).

`chapter` emptiness, for context: DE 3.0%, CA 4.6%, **NY 100%** (every
single one of NY's 40,102 rows has an empty `chapter` — the wave-4 fix is
maximally load-bearing for this state specifically), all others checked
0%.

### Q3 — bulk mode, real run

Ran `ingest_us_statutes_cli.py --input-dir` against a directory of 3 real
files: `us_pa_statutes.parquet` (valid), `some_random_filename.parquet`
(real IL data under an unmappable name), `us_wy_statutes.parquet` (a
truncated/corrupt 2KB stub under a valid-looking name). Result: correctly
SKIPPED the unmappable filename (reason printed, added to `files_failed`,
continued), correctly FAILED the corrupt file with a clear
"Parquet magic bytes not found" message (continued), correctly ingested
the valid file with per-batch progress, correct non-zero exit code (1),
and a final summary listing both failures with reasons plus the numeric
totals for the one successful file.

Cross-checking the summary against the DB (first invocation reported
"14,547 ingested, 0 skipped" for `us_pa_statutes.parquet`; DB afterward
held exactly 14,536 real `Article` rows for that Document) surfaced the PA
collision class documented under Q2 above — the CLI's own "ingested"
number silently double-counts collision-merged rows as if they were newly
created, which is not distinguishable from the summary alone.

Timing (real full-file, un-truncated, SQLite backing store, `--batch-size
5000`, single-file `--input` mode): `us_fl_statutes.parquet` (24,866 rows)
= 34.68s wall-clock end to end (25.06s user + 7.22s system, 93% CPU) =
~717 rows/sec. Honest extrapolation to a 2,000,000-row corpus at this same
rate: ~2,789s ≈ **46.5 minutes**, on SQLite, on this machine, assuming
every file behaves like FL (some are far larger — CA alone is 161,429
rows/71MB, federal statutes ~88.7MB per the recon dossier). This is a
*best case*: production likely runs against a networked Postgres, where
the same N+1 per-row SELECT-then-flush pattern (confirmed again by direct
code read of `ingest_us_statute_rows`: one `session.execute(lookup)` +
up to 2 `session.flush()` calls per row, no batch-level pre-fetch or bulk
upsert) would multiply per-round-trip network latency by roughly 2-4x per
row, plausibly pushing the real number well past an hour. The single
`session` object is reused for the ENTIRE bulk run across every file
(`_run_bulk` creates one `session_factory()` before the file loop and only
closes it in `finally` after all files) — confirmed by direct code read
that nothing calls `session.expunge_all()` or recycles the session between
files, so cycle 2's identity-map-growth concern is structurally still
present and unaddressed, just not independently re-measured at full 2M-row
scale this cycle (that scale run is the manager's job, post-signoff, per
the brief).

**Separately noted (not itself a code defect, but affects G6's "all 109
files" framing):** `huggingface_hub.list_repo_files` against the real
`vaquill/open-us-law` dataset returns **105** `.parquet` files (53
`*_statutes.parquet` + 52 `*_constitutions.parquet` — every jurisdiction
has a statutes file; DC is the only jurisdiction with no separate
constitutions file), not 109. The manager should use 105 as the real
target count for G6's "measured report", or reconcile the discrepancy
before the full run, so the eventual report isn't scored against a wrong
denominator.

### Q4 — Hebrew, full detail

`backend/tests/integration/test_definition_links_pipeline_live.py` +
`test_definition_links_pipeline_profile_dispatch.py` +
`test_definition_links_pipeline_jurisdiction_stamping.py` (13 tests) plus
the full `unit/test_definition_links_*` Hebrew-specific modules all green.
`grep -rn "find_citations" backend/app` shows exactly 3 non-definitional
hits: the function's own definition and docstring reference in
`us_profile.py`, and `profiles.py`'s Protocol declaration + `HebrewProfile`
wrapper (which itself trivially returns `[]`, per that file's own
docstring, "no citation grammar in scope for Hebrew"). `pipeline.py` calls
only `is_definitions_heading`, `extract_definitions_from_section`, and
`detect_cross_law_derivations` on the dispatched profile — never
`find_citations` — confirming it remains dead code for both jurisdiction
families, unchanged from cycle 2's finding.

### Q5 — full gate table (this cycle's own evidence)

- **G1 (Hebrew unharmed):** PASS. Q4 above; no Hebrew test or behavior
  touched this cycle.
- **G2 (a real US statute parses):** **FAIL.** Item 3's defects 1-4 above
  mean this is false for large real slices of the corpus: 0% for
  Illinois/California/Georgia (structural), 0% for Texas (case), 77%
  under-match for Ohio, 17% under-match for Florida.
- **G3 (English term linking, word-boundary):** Effectively **FAIL** as a
  practical matter — G3 only fires once G2 has found a Definitions
  section to extract terms from; for the states above there is nothing to
  link. `find_term_uses`'s own word-boundary logic (unit-tested,
  untouched this cycle) is not itself defective.
- **G4 (US citations recognised):** PASS, unchanged from cycle 2 —
  `find_citations`/`detect_cross_law_derivations` were not touched by
  wave 4 and were not part of this cycle's probes; no new evidence either
  way beyond re-running the existing green suite.
- **G5 (jurisdiction stamped/validated):** PASS, re-confirmed — Item 1/4's
  regressions (drift-guard, null-jurisdiction-unreachable) still green.
- **G6 (whole corpus loads):** **CODE ONLY, NOT PASS.** Bulk-mode
  continue-past-failure behavior verified correct (Q3); its own summary
  accuracy is NOT trustworthy without a DB cross-check (Q3); item 3/5's
  defects will cause additional real silent loss during the actual run;
  the real dataset has 105 files, not 109 (see Q3); the full 109/105-file
  run has NOT been executed by QA — that is the manager's job after
  sign-off, per the brief, and must not be read as done here.
- **G7 (reviewer works state-by-state):** PASS, unchanged — frontend
  165/165, typecheck clean, no probes this cycle found new UI-side risk.


## Manager rulings R7-R13 (moved from contract, 2026-08-03)

- **R7 — Manager live-path + real-data findings (2026-08-02, after wave 3).**
  (a) Live path VERIFIED by the manager directly: 3 real Delaware rows through
  the real `ingest_us_statute_rows` -> `run_definition_linking` produce 3
  definitions (`Affiliate`, `Branch office`, `Insured depository institution`)
  and 2 DERIVES_FROM_LAW assertions incl. real federal cite `12 U.S.C. § 1813(c)`,
  all stamped `US-DE`, zero nulls. Pre-fix the same probe produced 0 and 0.
  (b) **NEW DEFECT, item 5, found by manager probe of the REAL dataset:** the
  wave-3 idempotency fix skips any row with an empty `chapter`. On the real
  `us_de_statutes.parquet` (21,649 rows) **647 rows (3.0%) have an empty
  `chapter`** and would be dropped — real law lost, one state alone. `citation`
  is null/empty in **0%** of rows and is the canonical unique legal identifier
  (e.g. `5 Del. C. § 796`). QA must reproduce this and bounce item 5.

- **R8 — Wave 4 verified by the manager directly (2026-08-02).** Heading matcher:
  linear time confirmed (0.0009 ms flat; 0.018 ms at 4,000-char noise — was
  15,800 ms at 29 chars). Accuracy on REAL data: **0 missed / 0 false positives**
  across `us_de_statutes` (21,649 headings, 973 candidates) AND `us_ny_statutes`
  (40,102 headings, 1,416 candidates); both over-match cases still rejected.
  Ingester: Developer found a THIRD defect the manager had missed — chapter codes
  collide ACROSS titles (179 collisions merging 293 real sections) — and correctly
  refuted the manager's `citation`-as-key suggestion (1 duplicate pair in 21,649).
  Final key `(section_number, section_title, text)` verified collision-free on all
  21,649 real DE rows; full real-file ingest 21,649 -> 21,649 Articles, 0 skipped,
  idempotent on re-run. Suite: **632 passed / 0 failed**.

- **R9 — Wave 5 heading matcher: manager-verified per-state coverage (2026-08-02).**
  Independently reproduced the Developer's table on 10 real state files. Zero
  false positives in every state; timing 0.002 ms/call (linear held).
  | st | rows | cands | missed | miss% |
  |----|------|-------|--------|-------|
  | tx | 122,535 | 5,033 | 24 | **0.5%** (was 100%) |
  | oh | 33,161 | 970 | 20 | **2.1%** (was 84.1%) |
  | fl | 24,866 | 852 | 47 | **5.5%** (was 27.1%) |
  | de | 21,649 | 1,036 | 16 | 1.5% |
  | ny | 40,102 | 1,547 | 68 | 4.4% |
  | pa | 14,547 | 547 | 4 | 0.7% |
  | wa | 51,498 | 2,007 | 207 | 10.3% |
  | ca / il / ga | 262,039 | **0** | — | structural, see R10 |
  Residual misses are multi-topic headings ("APPLICABILITY OF DEFINITIONS",
  "...; definitions; penalties.") where definitions is not the section's own
  subject — deliberately not chased, to hold false positives at zero.
- **R10 — CA/IL/GA root cause FOUND (Developer escalation, accepted).** Not
  unknowable after all: `section_title` for these states is a bare placeholder
  (`"Section 103-9"`, `"Section 22970.21"`, or a bare citation for GA). The real
  heading text lives inside the `text` body (`"Sec. 15. Definitions. As used in
  this Act..."`), which Stage 2 never receives. No change to `us_profile.py` can
  recover it — the fix is a `pipeline.py` Stage-2 input change. 262,039 rows
  across 3 states affected. Escalated to the director; NOT fixed in wave 5 per
  the director's binding "characterise, do not guess" ruling.
- **R11 — Wave 5 ingester agent did not complete.** It blocked on a background
  notification and pushed nothing; its work is lost. Cause: the manager omitted
  the standing "never block on Monitor" rule from the wave-5 brief preamble.
  Manager fault, not agent fault. Re-spawned fresh in wave 5b.

- **R12 — Director approved wave 6 (CA/IL/GA), and QA's IL unit test is INVALID.**
  Director ruling (AskUserQuestion, 2026-08-03): fix CA/IL/GA rather than defer.
  Manager ruling on the test estate: `test_is_definitions_heading_cannot_recognize_
  a_state_whose_section_title_carries_no_heading_text` asserts
  `is_definitions_heading("Section 15") is True`. That is a planning bug — making
  it pass would return True for ANY `"Section N"` heading, destroying the
  zero-false-positive result of R9 across all 10 states. The Developer's
  escalation was correct. The VALID spec is the sibling live-path test
  `test_real_pipeline_misses_a_real_illinois_definitions_section_end_to_end`.
  Wave 6 splits accordingly: a test-owning agent rewrites the invalid unit test;
  a Developer changes `pipeline.py` Stage 2 to derive the heading from the body
  when `section_title` is a bare placeholder. Developers may not touch tests.

- **R13 — Wave 5b ingester: manager-verified (2026-08-03).** Key is now the
  dataset's own per-row `act_id` (e.g. `STATE_PA_T74_C7_S7`). Manager checked it
  independently across **10 real state files / 570,397 rows: 0 duplicates, 0
  null-or-empty**. Prior keys each failed on the next file tried; this one is the
  data's own identity, not an inferred composite. Developer additionally ran PA
  (14,547) and CA (161,429) fully through the real CLI twice each: ingested count
  == real DB Article count exactly, second run 0 new / 0 duplicates. CLI summary
  now separates "newly ingested" from "already present" — the conflation that hid
  the earlier 14,547-vs-14,536 discrepancy. Suite: 637 passed / 2 failed (both the
  IL items owned by wave 6).

## QA cycle 4 (2026-08-03) — full detail

### Q1 — precision audit (R15a), the headline probe

Replayed `pipeline.py`'s exact Stage-2 dispatch (derive heading from body when
`section_title` is a placeholder → try `USProfile.extract_definitions_from_
section` first → fall back to `_extract_inline_quoted_definitions` only if
that yields nothing) over **every real row** in `us_il_statutes.parquet`
(72,456 rows) and `us_ca_statutes.parquet` (161,429 rows), and the original
(`is_definitions_heading` on the row's own `section_title` directly) path over
`us_de_statutes.parquet` (21,649) and `us_tx_statutes.parquet` (122,535).
Candidate counts reproduced the manager's numbers exactly: **IL 9,661** (100%
via the inline-quote fallback), **CA 6,960** (5,163 fallback / 1,797 via the
profile's own extractor on a derived heading), confirming the probe replicates
production behaviour, not an approximation.

Random sample of 30 terms per state (seeded, reproducible): **IL 30/30
genuine**, **CA 30/30 genuine**, **DE 30/30 genuine**, **TX 30/30 genuine** —
no sentence fragments, no citations-as-terms, no empty/1-char terms in any
sample. Automated full-corpus outlier scan (term length, definition length,
empty/tiny values) found:

- **IL**: 0 confirmed junk extractions. 8 "tiny" (≤2-char) terms are all
  genuine real abbreviations (`VA`, `PC`, `LO`, `LP`, `AD`, `Wd`×3). 11 "long"
  (>80-char) terms are genuine (if unusual) phrase-as-term drafting, e.g.
  "Costs incurred in connection with the development, construction,
  acquisition or improvement of a project" — a real defined term repeated
  verbatim across 4 different IL acts. 83 verbose (>1,500-char) definitions
  are genuine multi-clause definitions (e.g. "employee" spanning
  subsections (a)-(o) in a single pension-law sentence), not boundary bleed.
- **CA**: one initially-suspected defect (a real row where entry (a)'s term
  uses the SAME left-curly quote character on both sides —
  `STATE_CA_Cshc_D1_C1_A6.5_S217`, "Adjustment factor") does **NOT** survive
  the live path: `pipeline.py` calls `normalize_for_parsing` (collapses all
  curly-quote variants to plain `"`, `normalize.py`'s `_QUOTE_VARIANTS_RE`)
  BEFORE Stage 2 extraction runs, which fixes the mismatch. Proven wrong by a
  live-path test (kept as a green regression guard, not a bounce — see below).
  **One genuine, live-path-confirmed defect remains**: real row
  `STATE_CA_Cgov_T5_D2_P1_C5_A8_S54221` produces a single "Dispose"
  `Definition` whose `definition_text` is **26,715 characters** and contains
  the complete text of 3 OTHER separately-defined terms ("Open-space
  purposes", "Sectional planning area", "Sectional planning area document")
  concatenated inside it — none of the 3 is ever recovered as its own row.
  This is in `USProfile.extract_definitions_from_section` (the ORIGINAL
  DE/TX-shared extractor, not new wave-6 code), newly EXPOSED to CA bodies by
  wave 6's heading-derivation dispatch (CA never reached this function
  before). 1 confirmed instance / 1,797 CA candidates via this path (0.06%).
- **DE**: 0 confirmed junk (0 empty, 0 tiny defs; largest single definitions,
  up to 12,064 chars, checked for embedded OTHER-term swallow — none found).
- **TX**: a distinct, comparable-severity defect in the ORIGINAL extractor
  (not new): one real row (`STATE_TX_Cin_C1305_S1305.004`, a semicolon-
  separated list of cross-referenced terms — `"compensable injury," "doctor,"
  ...` all "have the meanings assigned by Section X") produces 11 terms with
  degenerate `";"` definition text plus 1 fully empty definition (12/20,695 ≈
  0.058%).

**Verdict**: precision is high (>99.9%) for all four states; the wave-6
fallback's own precision (IL: 0 confirmed defects found; CA fallback path
specifically: 0, since the sole surviving defect is in the shared extractor,
not the fallback) is not materially worse than the original extractor's own
real-data defect rate (TX: 0.058%). **Item 3 bounces anyway** for the one
concrete, reproducible, live-path-proven "Dispose" boundary-swallow defect
(RED test `test_real_pipeline_swallows_three_other_terms_into_one_bloated_
california_definition`, `test_qa_regression_us_state_law_cycle4_FAIL.py`) —
a single 26 KB garbled record is exactly the "reviewers must clean up"
failure mode ruling R15a warns about, regardless of its low incidence rate.

### Q2 — ingest integrity, a file never touched before (Washington)

Wave-5b Developer verified PA/CA; this cycle used `us_wa_statutes.parquet`
(51,498 real rows, untouched by any prior wave/cycle) through the REAL CLI
(`ingest_us_statutes_cli.py`, single-file mode) against a fresh sqlite DB,
then cross-checked the DB myself (not just trusting the printed summary):

- Run 1: CLI printed "51,498 newly ingested, 0 matched, 0 skipped" — DB query
  confirms exactly 51,498 `Article` rows, 1 `Document`. Honest.
- Run 2 (re-ingest same file): CLI printed "0 newly ingested, 51,498 matched,
  0 skipped" — DB `Article` count unchanged at 51,498. Idempotent.
- 1,026 distinct `section_number` values are each shared by 2+ Articles (e.g.
  "001" shared by ~90 different WA chapters) — all correctly produced as
  distinct Articles (`act_id` keying holds; no collision-driven merge).
- Timing: 51,498 rows / 13.8s ≈ 3,732 rows/sec (first ingest), 51,498 / 5.5s ≈
  9,363 rows/sec (re-ingest, lookup-only). Separately ran the single largest
  file in the whole corpus, `us_ca_statutes.parquet` (161,429 rows): 41.15s
  wall (≈ 3,923 rows/sec), peak RSS 278 MB / peak footprint 380 MB
  (`/usr/bin/time -l`).
- Empty-`chapter` ingestion: WA has zero empty-`chapter` rows to exercise
  (data-completeness difference, not a code path difference) — already
  verified on 647 real DE rows in wave 4/QA cycle 2 and untouched by any
  ingest-key change since (the key is `act_id` alone; `chapter` is
  informational only, never part of the key).

### Q3 — Hebrew fidelity (G1), final re-check

167 Hebrew/definition-link tests pass unchanged (`pytest -k "hebrew or
definition_link"`). `HebrewProfile.code == "IL"` (`profiles.py:86`), and
`pipeline.py`'s body-derivation guard explicitly excludes
`profile.code != "IL"` — Hebrew documents structurally cannot reach
`_derive_heading_from_body` / `_extract_inline_quoted_definitions` regardless
of heading shape. Unchanged from cycle 3.

### Q4 — placeholder-heading misfire probe, adversarial, all 7 working states

Ran `_is_placeholder_heading` against every real `section_title` in
DE/NY/TX/OH/FL/PA/WA (308,358 rows total): **0 misfires** in DE, TX, OH, FL,
WA; **1** in NY (`STATE_NY_AENV_A30_S30-0101`, the Developer's own known
case) and **6 NEW in PA** (`STATE_PA_T23_C29_S2904`,
`STATE_PA_T13_C27_S2707`, `STATE_PA_T12_C23_S2309`,
`STATE_PA_T16_C13_S1301`, `STATE_PA_T61_C97_S9762`,
`STATE_PA_T71_C51_S5102`) — all 7 are ordinary `"Section N"` headings that
happen to match the bare-placeholder pattern. For every one of the 7, ran
`_derive_heading_from_body` on the row's real body: **all 7 return `None`**
(neither the IL embedded-heading nor the CA/GA preamble convention appears in
any of these ordinary, non-Definitions bodies), so `is_definitions_section`
never flips to `True` — **0 real behavioural misfires**, confirmed live, not
just at the pattern-match level.

### Q5 — Georgia (R15c), quantified

`us_ga_statutes.parquet`: 28,154 total rows, **5 detected** (matches R15c).
**438 rows (1.56%)** open with the exact stated convention (case-insensitive
`"As used in this chapter, the term"` in the first 300 chars of body) — the
real, quantified scope of the follow-up (a body-preamble convention with no
"definitions" word at all, distinct from CA/IL's, deliberately not chased
this sprint per the zero-false-positive priority). Only 71 rows have the word
"definition" anywhere in the first 300 chars, most of which is the 5 already
detected via other means.

### Q6 — bulk-run readiness, full evidence

Real timing: WA 51,498 rows / 13.8s; CA (largest file) 161,429 rows / 41.15s;
a 3-file bulk-mode run (DE+FL+WA, 98,013 rows combined) / 24.44s ≈ 4,011
rows/sec. Extrapolated to the full ~2,000,000-row corpus at this machine's
measured rate: **~8-9 minutes** best case (faster than cycle 3's ~46-minute
estimate — likely batch-size/hardware variance; both numbers reported
honestly, not reconciled). Memory: CA alone peaked at 380 MB footprint / 278
MB RSS; the 3-file combined run peaked at 354 MB (footprint), not obviously additive
across files at this scale — but bulk mode holds ONE session across ALL 105
files without ever expunging, so the SQLAlchemy identity map grows with
TOTAL rows processed in the run, not per-file; extrapolating the observed
≈2.5-3.6 KB/row overhead across 2,000,000 rows suggests **several GB peak
RSS** for the true full run — a real, quantified risk worth the manager
monitoring during the actual G6 run, not a blocker.

**Go/no-go: GO**, with the memory-growth caveat above flagged for the
manager's own run to watch.

### Gate sign-off (cycle 4, full table)

- **G1 (Hebrew unharmed)**: PASS — Q3 above.
- **G2 (English Definitions parses)**: PASS overall, with the item-3 bounce
  above as a live, scoped defect (not a gate-wide failure — DE/TX/IL still
  parse correctly; the "Dispose" case is one CA row's boundary detection).
- **G3 (term linking, word-boundary)**: PASS — unchanged since cycle 2/3,
  no new evidence against it this cycle.
- **G4 (US citations recognised)**: PASS — unchanged since cycle 2/3.
- **G5 (jurisdiction stamped + validated)**: PASS — unchanged (item 4
  regression guard still green in the 640-passed run).
- **G6 (full corpus loads)**: CODE-ONLY PASS — Q2/Q6 evidence above; the
  manager's own full ~105-file run is the actual gate-closing deliverable.
- **G7 (reviewer works state-by-state)**: PASS — unchanged, frontend 165/165
  green, typecheck clean.

