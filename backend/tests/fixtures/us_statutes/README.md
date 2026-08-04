# US statute fixtures (sprint 2026-08-02-us-state-law, ruling R6)

Two files, same 3 REAL rows (all 24 original parquet columns, values
unmodified) out of `vaquill/open-us-law`'s `us_de_statutes.parquet` file:

- `de_sample_rows.json` — for any test that only needs to read the row data
  (no `pyarrow` install required). This is what the deterministic-engine
  tests (`test_definition_links_us_profile.py`,
  `test_us_profile_definitions_section_end_to_end.py`) use.
- `de_sample_rows.parquet` — a REAL, byte-valid Parquet file (10.5 KB,
  written from the exact same 3 rows via `pyarrow.Table.from_pylist` +
  `pyarrow.parquet.write_table`, round-trip-verified byte-identical back to
  `de_sample_rows.json`) — for the dataset-ingester item's CLI/parquet-
  reading tests, so they exercise a REAL local parquet file without
  downloading the 21 MB real one. **Caveat**: because all 3 sample rows
  happen to have `null` for `chapter_name` and `last_amended_year`, pyarrow
  infers those two columns as the `null` type in THIS fixture, not the real
  file's actual `string`/`int64` types -- the ingester must handle the real
  file's typing, not assume this fixture's degenerate schema for those two
  columns specifically.

Rows picked to cover the cases named in the sprint contract's R6:

1. **`STATE_DE_T5_C7_SVIII_S796`** — a real "Definitions" section (`§ 796`,
   Delaware Code Title 5). Multi-term, numbered-subsection body using
   `"Term" has the meaning specified in ...` as its definition idiom (not
   `"Term" means ...`), with BOTH a same-chapter internal cross-reference
   (`§ 770 of this chapter`) and two federal cross-references
   (`12 U.S.C. § 1841(k)`, `12 U.S.C. § 1813(c)`). Covers G2 (Definitions
   detection) and half of G4 (citation grammar).
2. **`STATE_DE_T29_C60A_S6060`** — NOT a Definitions section (heading is
   "Employer Match Plan"); short body containing a clean U.S.C. citation
   (`26 U.S.C. § 401(a)`). Covers G4 in isolation from G2.
3. **`STATE_DE_T31_C52_SIII_S5227`** — the edge case: a one-sentence
   cross-TITLE reference (`as defined in § 901 of Title 10` — a different
   law/title than this section's own Title 31), which is the US analogue of
   the Hebrew engine's cross-law derivation (`derivation.py`). Its own
   section heading ("Definition.", singular) is also a definitions-heading
   variant distinct from row 1's plural "Definitions.".

## A real data-quality issue this fixture surfaces (not injected)

**Every** row pulled from `us_de_statutes.parquet` (not just these three —
verified across all 21,649 rows) has a `section_title` value corrupted by a
double-encoding/scrape artifact: the literal section-symbol-plus-nbsp
sequence renders as `"§ Â\r\n        796. Definitions."` (mojibake `Â`, a
raw CR/LF, and indentation whitespace, all before the actual section number
and heading text). An English "Definitions"-heading matcher that assumes a
clean `"796. Definitions"`-shaped string (mirroring the Hebrew engine's
`_DEFINITIONS_HEADING_RE`, which matches at the START of an already
marker-stripped heading) will not match this heading verbatim — the US
profile's heading detector must either tolerate/strip this noise or match
on a substring/contains basis. This is the "edge case" R6 asks for; it did
not need to be hand-picked, it is the norm for this file.

## `qa_cycle3_rows.json` — QA cycle 3 findings (2026-08-02)

8 REAL rows (full original columns, values unmodified), one or two per
defect, pulled from **6 different real state files the Developer never
tested** (`us_il_statutes.parquet`, `us_tx_statutes.parquet`,
`us_fl_statutes.parquet`, `us_oh_statutes.parquet`, `us_pa_statutes.parquet`,
`us_ca_statutes.parquet`) — independent QA verification per the cycle-3
brief's Q1/Q2 mandate to test files beyond the Developer's DE/NY pair:

1. **`STATE_IL_C325_A7_S15`** — real Illinois row. `section_title` is the
   generic `"Section 15"` (verified: **99.6% of all 72,456 real IL rows**,
   and separately **100% of all 161,429 real CA rows**, and **100% of all
   28,154 real GA rows**, have this shape — `section_title` never carries
   descriptive heading text for these three states at all). The real,
   genuine "Sec. 15. Definitions." heading only exists inside the row's
   `text` body, which `is_definitions_heading` never sees (it is only ever
   called on `Article.heading`, sourced from `section_title` —
   `pipeline.py` Stage 2). No regex fix can recover this: the input field
   itself carries no heading. Proves a 100%, state-wide G2 miss for at
   least 3 of the ~53 real jurisdictions (~260,000+ rows), independent of
   and additional to the heading-matcher regex defects below.
2. **`STATE_TX_Ctn_C452_S452.351`** — real Texas row, heading
   `"§ 452.351. DEFINITION."` (Texas's real, standard ALL-CAPS statutory
   heading convention). `is_definitions_heading` is case-sensitive
   (`Definitions?` requires a capital `D`, lowercase rest) and **matches 0
   of the real `us_tx_statutes.parquet` file's 5,033 genuine ALL-CAPS
   Definitions headings** — a complete, state-wide G2 miss for Texas.
3. **`STATE_FL_TXLVII_C941_PI_S941.34`** — real Florida row, heading
   `"941.34 Definition of "state.""`. Florida's (and Ohio's, and others')
   real section-number convention is dot-separated (`NNN.NNN`), which
   `_SECTION_NUMBER_TOKEN_RE` (`\d+[A-Za-z]*(?:-\d+[A-Za-z]*)*\.?`) does not
   fully consume — it stops after the first `.`, leaving a numeric
   fragment (`"34"`) stuck in front of "Definition", breaking both the
   first-word and last-word rules. Verified: **127 of 748 real FL
   capital-D "Definition(s)" headings (17%)** are under-matched this exact
   way.
4. **`STATE_OH_T45_C4513_S4513.01`** — real Ohio row, heading
   `"§ 4513.01. Traffic laws - equipment - load definitions"` (lowercase
   `definitions` as the heading's genuine last word — Ohio's normal
   sentence-case convention, not the DE/PA capital-D convention the fix was
   validated against). Same case-sensitivity defect as row 2, on a
   different real-data shape: **747 of 970 real OH "definition"-containing
   headings (77%)** use this lowercase convention and can never match.
5/6. **`STATE_PA_T74_C7_S7` / `STATE_PA_T51_C7_S7`** — two REAL, genuinely
   DIFFERENT Pennsylvania sections (different citations, `74 Pa.C.S. § 7`
   vs `51 Pa.C.S. § 7`) that share an identical `(section_number="7",
   section_title="Status of certain businesses.", text=...)` triple
   (byte-identical cross-title boilerplate). Disproves the wave-4 fix's own
   claim that "two distinct real sections essentially never share
   byte-identical body text": verified **9 such collision groups / 11 rows
   silently merged, out of only 14,547 real PA rows** — on a file the
   Developer never checked.
7/8. **`STATE_CA_Cwic_S7` / `STATE_CA_Cins_S7`** — the same collision
   shape on California (`section_title` is *also* always the generic
   `"Section N"` there, compounding both defects at once): verified **83
   collision groups / 176 rows silently merged, out of 161,429 real CA
   rows** (the single largest state file in the corpus).

Provenance: same dataset/commit as the rows above, fetched 2026-08-02 by
QA cycle 3 into a disposable scratch directory outside `backend/.venv`
(ruling R6 — the committed tests below load only this committed JSON, never
the network).

## Retrieval (fixture creation only — never run by the test suite, R6)

```
backend/.venv/bin/python -c "
from huggingface_hub import hf_hub_download
p = hf_hub_download(repo_id='vaquill/open-us-law', filename='us_de_statutes.parquet', repo_type='dataset')
import pyarrow.parquet as pq
t = pq.read_table(p)
print(t.schema)
print(t.slice(0, 3).to_pylist())
"
```

`huggingface_hub`/`pyarrow` are NOT installed in `backend/.venv` as of this
sprint (verified `ModuleNotFoundError` for both, plus `pandas`) — the
Planner fetched these rows using a disposable venv outside the repo
(`pip install huggingface_hub pyarrow` into a scratch venv), never touching
`backend/.venv` or `backend/pyproject.toml`. Adding `huggingface_hub`/
`pyarrow` as real dependencies (dev or production, per what the ingester
needs) is the Developer's job for the G6 (dataset ingester) item.

## Provenance

- Source: `vaquill/open-us-law` (HF dataset), file `us_de_statutes.parquet`,
  dataset commit `d2d760358de8bea543f016c226ad979b0adf2a85` (same sha the
  recon dossier's §4 verified via the HF API), fetched 2026-08-02.
- Format: JSON (not parquet) — deliberate choice so RED/regression tests
  that load this fixture never need `pyarrow` installed just to read three
  rows; the schema (24 string/int/JSON-string columns) is fully preserved
  as JSON types (`null` for the source's nulls, JSON-encoded-string values
  kept as-is for `breadcrumb`/`cross_references_usc`/`cross_references_cfr`/
  `public_laws_referenced`, matching the parquet column's actual on-disk
  type — these are strings containing JSON, not native list columns).
- License: CC-BY-4.0 (dataset), underlying statutory text public domain
  (government edicts doctrine) — per dossier §4.
- Why Delaware specifically: the existing frontend test fixture already
  uses `"US-DE"` as its jurisdiction literal
  (`frontend/src/pages/__tests__/AssertionDetailPage.test.tsx:80`) — reusing
  the same state keeps the sprint's fixtures consistent end-to-end.

## `qa_cycle4_rows.json` — QA cycle 4 precision audit findings (2026-08-03)

2 REAL rows (full original columns, values unmodified), both pulled from
`us_ca_statutes.parquet` — found by a full-corpus scan (ruling R15a) that
replayed `pipeline.py`'s exact Stage-2 dispatch over all 161,429 real CA
rows and manually judged a random sample plus every length-outlier
candidate, rather than sampling a handful of rows up front:

1. **`STATE_CA_Cshc_D1_C1_A6.5_S217`** — real CA row, "§ 217. Definitions"
   (Job Order Contracting article). Entry (a)'s own body uses the SAME
   left-curly quote character (`“`) on BOTH sides of its term
   ("Adjustment factor"), instead of a matching `“...”` pair — a real
   mojibake/scrape shape. Initially suspected to garble term extraction
   (the raw text alone reproduces the garbling), but does NOT survive the
   live path: `pipeline.py` calls `normalize_for_parsing` before Stage 2
   extraction, which collapses all curly-quote variants to plain `"`,
   making the pair consistent again. Kept as a green regression guard, not
   a bounce proof.
2. **`STATE_CA_Cgov_T5_D2_P1_C5_A8_S54221`** — real CA row, Surplus Land Act
   definitions (32,477-char body, `section_title` the generic `"Section
   54221"` placeholder). Contains "Dispose" plus at least 3 more distinct
   defined terms ("Open-space purposes", "Sectional planning area",
   "Sectional planning area document") — the shared numbered-entry
   extractor (`USProfile.extract_definitions_from_section`) fails to
   recognize the entry boundary after "Dispose"'s own lettered sub-clauses
   and swallows all 3 remaining terms into one 26,715-character
   `definition_text`. Genuine, live-path-confirmed defect (item 3 bounce).

## `ny_m14_newline_defect_row.json` — M14 newline-defect RED test fixture (2026-08-04)

1 REAL row, `STATE_NY_ABNK_A15_T6_S6021` ("Preemptive rights", N.Y. Banking
Law § 6021, 7,019-char body, 6 real defined terms across 14
lettered/numbered entries), copied byte-for-byte from the real
`us_ny_statutes.parquet` snapshot — extracted by this sprint's Scout S2
pass (`scout_S2_findings.md`/`scout_S2_full_rows.json`, never downloaded or
read directly by this Planner or by any test, ruling R6).

**What it proves**: `us_ny_statutes.parquet`'s `text` column stores every
line break as the LITERAL two-character sequence `\n` (backslash + letter
"n"), never a real newline byte — verified corpus-wide by the Scout,
40,102/40,102 real NY rows. `USProfile.extract_definitions_from_section`'s
`_split_into_numbered_blocks` does `text.split("\n")` (a REAL newline) to
find each entry's own line; against NY's literal-`\n` bodies this always
returns the WHOLE body as one unsplittable line, so zero entries are ever
recognized — corpus-wide, every one of NY's 1,479 already-heading-
recognized "Definitions" sections yields zero candidates from this
extractor. This is the single largest known contributor to the sprint's
34,017 zero-yield count.

Fields present are exactly what the Scout's extraction preserved (`act_id,
citation, citation_short, section_title, breadcrumb, display_path, chapter,
chapter_name, title_number, title_name, text, word_count`) — a subset of
the full 24-column schema (unlike `de_sample_rows.json`'s complete-column
convention), since the Scout's saved artifact does not carry every original
column. `chapter`, `section_title`, and `text` (the columns
`ingest_us_statute_rows`/extraction actually read) are all real,
unmodified values.

This row's own `section_title` ("Preemptive rights") is NOT itself
heading-recognized as "Definitions" — that is a separate, already-known NY
defect (heading detection), out of scope for M14. The RED test using this
fixture (`test_ingest_us_statutes_ny_newline_defect.py`) deliberately calls
`get_profile("US-NY").extract_definitions_from_section` directly rather
than relying on `pipeline.py`'s heading-dispatch gate, so its assertion is
discriminated purely by the newline defect.

## `d_cf_structural_reference_rows.json` — D-CF case-fold structural-context guard fixture (QA-fail cycle 2, item I10, 2026-08-04)

4 REAL rows (full original columns, values unmodified), pulled from 4
different real state files (`us_al_statutes.parquet`,
`us_il_statutes.parquet`, `us_ak_statutes.parquet`,
`us_ar_statutes.parquet`) by this Planner, measured directly against the
real `vaquill/open-us-law` corpus before writing any test assertion —
director ruling D-CF (program doc, panel log Round 17): case-folding
(I6/M8(b)) stays, but a case-fold match sitting inside a structural-
reference pattern (a unit word immediately followed by a numbering token
— "division (ii)", "part (a)", "title 5") must be suppressed; a genuine
lowercase re-mention in ordinary prose must NOT be suppressed.

1. **`STATE_AL_T41_C10_S41-10-592`** (Alabama) — "All bonds issued
   pursuant to this division (i) shall be issued and sold...". Verified:
   the row's ONLY "division"/"Division" occurrence, and it DOES match
   under plain `re.IGNORECASE` case-folding today (pre-guard) — the
   negative-direction case for the word "Division".
2. **`STATE_IL_C35_A505_S13a`** (Illinois) — "...comprised of 2 parts.
   Part (a) shall be at the rate established by Section 2... Part (b)
   shall be at the rate established by subsection (2)...". Verified: the
   row's ONLY two "Part"/"part" occurrences, both structural, both match
   today — the negative-direction case for "Part".
3. **`STATE_AK_T6_C06.45_S06.45.160`** (Alaska) — "...insurance obtained
   under Title 1 of the National Housing Act is adequate security."
   Verified: the row's ONLY "Title"/"title" occurrence, a bare-number
   structural reference (D-CF's own named "title 5" shape) — the
   negative-direction case for "Title".
4. **`STATE_AR_T20_C48_S6_S20-48-603`** (Arkansas) — genuinely DEFINES
   "Division" ("(3) \"Division\" means the Division of Developmental
   Disabilities Services..."), then re-mentions it lowercase in ordinary
   prose with no numbering token nearby ("...staff of the division where
   the context...", "...home licensed by the division..." x2) — the
   POSITIVE-direction case proving D-CF must not undo I6/M8(b). This
   row's own `text` field contains its content duplicated verbatim (a
   real corpus artifact, not injected) — 6 genuine lowercase matches
   total (3 per copy × 2 copies), verified by running `find_term_uses`
   against the real text before writing the test's expected count.

Provenance: same dataset/commit as the rows above (`vaquill/open-us-law`,
`d2d760358de8bea543f016c226ad979b0adf2a85`), fetched 2026-08-04 into this
worktree's scratchpad (never `backend/.venv`), never read by the committed
test suite itself (program rule prior-R6 — suites run offline).
## `us_scoped_inline_rows.json` — sprint 2026-08-04-defs-us-scoped-inline (Planner, D4)

25 REAL rows (full original columns, values unmodified), fetched directly
from the on-disk HF snapshot (never downloaded — same cache path every
other fixture here uses:
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/
301000fc3465374ee0f23c3c6953a8a861e95cad/us_<st>_statutes.parquet`).
Verified live against the REAL current code (`is_definitions_heading`,
`extract_local_definitions`, `extract_adhoc_definitions`,
`_is_placeholder_heading`) — every row's heading is NOT recognized as a
Definitions section, is NOT a placeholder heading (so no body-derivation
rescue applies), and both Hebrew-only local/adhoc extractors return `[]` —
i.e. every genuine positive row here is a confirmed, live, 100% miss today
(family 1's exact root cause, `pipeline.py`'s `else:` branch).

Covers the convention-inventory (D1) variant space actually found across
the 12 lead states (UT/OH/ME/MO/MT/TN/VT/OR/RI/SC/PA/TX — MO/RI not
separately vendored here, already well covered by the other 10):

- **Trigger axis**: `As used in this <unit>`, `For purposes of this <unit>`,
  `For the purpose(s) of this <unit>`, `When used in this <unit>`, bare
  `In this <unit>` (strict-adjacency only — see below), marker-prefixed
  (`(a) As used in...`, `(a)(1) When used in...`), and the trigger appearing
  AFTER its term (`"State facilities," when used in this chapter, shall
  mean...` — `STATE_VT_T3_C45_S2291`). Scope units covered: section,
  subsection, chapter, part, subchapter, article, title.
- **Body axis**: bare `"X" means`, numbered/lettered `(N)`/`(a)` `"X" means`,
  `the term "X" includes/means`, `"X" shall mean`, `"X" has the meaning`
  (incl. the real OH cross-reference shape `"X" has the same meaning as in
  section N` — `STATE_OH_T33_C3313_S3313.906`), `"X" includes` (TX,
  `STATE_TX_Cwa_C55_S55.047`), colon-then-numbered-list, colon-then-lettered-
  list (incl. Oregon's real capital-letter `(A)(B)` convention), and nested
  roman-numeral sub-clauses inside a lettered entry (`STATE_UT_T53G_S53G_
  10_402`'s `(b) "Refusal skills" means instruction: (i)...(iv)`) that must
  stay part of THAT entry's `definition_text`, not spawn spurious entries.
  A single definition's own body-internal numbered/lettered sub-list (no
  new quoted term at each item — `STATE_MT_T23_C5_P8_S23-5-801`,
  `STATE_TN_T36_C5_S36-5-910`, `STATE_VT_T11C_C7_S701`) must likewise stay
  part of the ONE preceding term's `definition_text`, not be misread as
  unnamed additional entries.
- **Multi-scope-in-one-body**: `STATE_VT_T3_C45_S2291` defines 3 terms in
  one section body under 3 DIFFERENT scope units (title/chapter/chapter) —
  scope must be resolved per-entry, never once for the whole body.
- **Negative controls (false-positive bait)**: `STATE_UT_T10_S10_21_302`
  (`"...is the same as defined in Section 15A-1-302"` — unquoted term, no
  recognized idiom); `STATE_UT_T11_S11_59_603` (bare "in this section"
  mid-sentence, no adjacent quote/colon at all — proves bare `In`/`in`
  cannot be a standalone trigger, see Planner's precision measurement in
  the sprint log: bare `in this <unit>` is only ~21% genuine across the 12
  lead states, 72.7% pure prose noise).
- **Escalation-flagged boundary case (NOT auto-included as a positive)**:
  `STATE_PA_T15_C57_S5749` — `"For the purposes of this subchapter: (1)
  References to \"other enterprises\" shall include..."` — a construction/
  interpretation clause about how OTHER text should be read, not a
  `"X" means Y`-shaped definition. Real, genuinely ambiguous; see the
  sprint log's D2 section for the Planner's lean (exclude) and the
  escalation to the manager.
- **Baseline regression-guard rows** (U5): `STATE_MT_T76_C13_P1_S76-13-107`,
  `STATE_IN_T13_A23_C12_S13-23-12-3`, `STATE_NY_ATAX_A9_S197-D` — real rows
  from 3 of the program's 12 baseline states, verified to contain NO
  family-1 trigger phrase at all (ordinary substantive prose) — the new
  rule module must return `[]` for every one of these, never a false
  positive. (An earlier candidate, `STATE_MT_T87_C1_P2_S87-1-217`, was
  DROPPED from this set once its full text was read closely: it turns out
  to itself be a rich, genuine multi-trigger F1 row — `"(3) For the
  purposes of this subsection, "problem wolves" means..."` PLUS `"(6) As
  used in this section: (a) "consultation" means... (b) "large game
  species" means... (c) "large predators" means..."`, i.e. FOUR terms
  across TWO different scope units, subsection and section/local, in one
  body. Not wired into any test in this sprint's fixture set — flagged
  here as a real example worth a future test if this family's coverage is
  ever revisited, and as a reminder that a row's opening sentence is not
  reliable evidence of its whole body.)

### Added 2026-08-04, Planner pass 2 (D11 — routed CLAUSE package absorption)

- **`STATE_MO_C44_S44.091`** — a NEW body-shape variant D1's original 12-lead-
  state inventory missed: `"Term" , definition` (quote, then a bare comma,
  then the definition text directly — no idiom keyword — `means`/`shall
  mean`/`includes`/etc. — anywhere in the entry at all). Found while
  verifying a random 147-row sample (3 per jurisdiction, stratified across
  all 51) of the `defs-us-preamble` panel's routed CLAUSE package
  (`docs/sprint/sprints/2026-08-04-defs-us-preamble-clause-package.json`,
  `origin/claude/defs-us-preamble` @ `8a8837a`) against the real corpus —
  see the `-log.md`'s D11 section for the full verification methodology and
  measured accuracy. This convention is MO's own dominant, pervasive house
  style (all 3 entries in this one row use it; MO is the single largest
  contributor to the routed package at 456 rows) and was invisible to D1's
  original idiom-keyword-based genuineness heuristic, which is exactly why
  a real independent verification pass against a differently-sourced
  population (the preamble panel's own discriminator, not ours) was worth
  doing rather than trusting corpus coverage from one inventory pass alone.

Provenance: same dataset/commit as every other fixture in this directory,
fetched 2026-08-04 by the Planner via the worktree's own read of the local
HF cache (no network I/O — `pyarrow` already present in this worktree's
venv, unlike the disposable-venv note above from the 2026-08-02 sprint).
Analysis/fetch scripts (scratchpad, not committed):
`/private/tmp/claude-501/-Users-nerya-LexGraph/87b55b0a-5a38-44b6-887d-1e093b526197/scratchpad/f1_inventory.py`,
`f1_precision.py`, `fetch_fixture_rows.py` (pass 1); `d8_part_subchapter_measure.py`,
`d8_breadcrumb_structural.py`, `d11_verify_clause_package_v2.py` (pass 2).

## `planner_pass6_missed_conventions_rows.json` — Planner pass 6, 3 of QA cycle 1's unpinned root causes (2026-08-04)

4 REAL rows (full original columns, values unmodified), pulled from 4
different real state files (`us_fl_statutes.parquet`, `us_dc_statutes.
parquet`, `us_ms_statutes.parquet`, `us_or_statutes.parquet`) — this
worktree's own independent fetch from the same local HF snapshot, run
TWICE and diffed (`section_title` + `text`, 4/4 byte-identical both times)
before either row was written into this fixture.

QA cycle 1 confirmed 8 distinct in-vocabulary root causes but committed RED
tests for only 6 (`qa_cycle1_missed_conventions_rows.json`, above) to stay
under the style gate. This fixture pins the remaining 2 root causes plus
one deliberately-added second confirmation of an already-pinned cause
(`test_us_scoped_inline_planner_pass6_missed_conventions.py`):

1. **`STATE_FL_TXVIII_C253_S253.04`** — period-style list markers (`1.`
   `2.` instead of `(1)` `(2)`) inside an `As used in this subsection, the
   term:` colon-list. `_MARKER_RE` requires a literal parenthesized
   marker, so `_multi_entries` finds zero markers and the whole two-term
   block (`Seagrass`, `Seagrass scarring`) is lost.
2. **`STATE_DC_T47_C20_S47-2002.01`** — `the term:` with NO space before
   the colon. `_STRONG_CONNECTOR_RE`'s `the term\s+` alternative requires
   trailing whitespace before it can even attempt to match, so it never
   consumes "the term:" at all; the trailing colon-detection group is then
   tried at the wrong position and also fails. All 4 marker-prefixed
   entries lost.
3. **`STATE_MS_T27_C29_S51-5`** — `shall have meanings as follows:`
   connector phrase, entirely outside the recognized connector vocabulary
   (`(the following terms) mean(s)` / `the term` / `a`/`an`). Chosen over
   `STATE_NY_ARPP_A8_S280-D` (the row QA cycle 1 also names for this same
   connector gap) because NY's "definitions" are entirely UNQUOTED labeled
   paragraphs (verified: zero quote characters anywhere in its `text`) —
   a separate, deliberately-excluded convention (the unquoted-term
   precision tradeoff) that would keep a NY-based test RED even after the
   connector gap is fixed. MS's row uses quoted terms throughout, so it
   cleanly isolates just the connector-vocabulary gap.
4. **`STATE_OR_T62_C835_S835.200`** — a SECOND, independent confirmation
   of QA's already-pinned "intervening secondary citation clause" root
   cause (its own pin: `STATE_DE_T6_C15_SIX_S15-901`). Added because OR's
   citation shape (`"and ORS 835.210 (Application by political
   subdivision for special regulation) , "seaplane" means..."`) nests a
   parenthetical INSIDE the citation itself, structurally distinct from
   DE's/OH's plain-prose citation shape — real regression value for a
   future citation-tolerance fix, not redundant bulk. (`STATE_OH_T17_
   C1707_S1707.47`, QA's other named confirmation row, was NOT
   additionally pinned: its citation shape is plain prose, already fully
   covered by DE's pin.)

## `planner_pass6_gate_isolation_rows.json` — Planner pass 6, Task 2 gate-isolation fixture (2026-08-04)

1 REAL row (full original columns, values unmodified), pulled from
`us_al_statutes.parquet`, independently byte-verified across 2 separate
fetches, used by `test_marker_quote_adjacency_gate_is_load_bearing_alabama`
in `test_us_scoped_inline_rules_negative_controls.py`:

- **`STATE_AL_T13A_C11_S13A-11-1`** — "Definitions" section, Alabama Title
  13A, Chapter 11: `"The following definitions apply in this article:
  (1) OBSTRUCT. To "obstruct" means to render impassable... (2) PUBLIC
  PLACE. A place to which... (3) TRANSPORTATION FACILITY. Any
  conveyance..."`. Used to mutation-isolate `_MARKER_QUOTE_RE`'s
  marker-immediately-followed-by-quote rule from the idiom-vocabulary gate
  that redundantly (and misleadingly) protects the suite's existing PA
  construction-clause test — see that test's corrected docstring. Marker
  `(1)` here is followed by `OBSTRUCT. To ` (14 non-whitespace chars, well
  inside a QA-cycle-1-style <=20-char widened gap) before its quoted term,
  so today's whitespace-only adjacency rule correctly does NOT treat it as
  a fresh entry — the entire list (a real, pervasive "(N) LABEL. To/The
  term "X" means" corpus convention, out of this Planner pass's Task 1
  scope) is silently dropped today, which is exactly why it works as an
  isolation vehicle: unlike the PA row, this row's idiom ("means") IS
  recognized, so nothing downstream masks a marker-adjacency regression.
