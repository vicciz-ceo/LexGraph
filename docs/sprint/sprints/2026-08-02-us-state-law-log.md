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
