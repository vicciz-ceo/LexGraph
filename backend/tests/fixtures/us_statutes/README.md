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
## `multiterm_f5_rows.json` / `multiterm_f6_rows.json` / `inline_parenthetical_sample_rows.json` — sprint 2026-08-04-defs-us-multiterm (families 5+6)

All rows below are REAL, vendored verbatim (full original parquet columns,
values unmodified except where a row is explicitly noted as a TRIMMED
excerpt via its own `_fixture_note` field) from the local HF snapshot at
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law` (no test reads
that path directly — every test reads only these committed JSON files).
Every row was independently pulled from the real parquet file and, for the
3 rows this sprint's Planner did not personally re-pull a second time
(`STATE_TX_Cgv_C2002_S2002.001`, `STATE_MI_C388_AAct-94-of-1979_S388.1606`,
`STATE_NH_TXXXVII_C408-C_S14`, `STATE_ND_T26.1_C26.1-59_S26.1-59-01`),
byte-diffed against the real corpus file before being committed (see the
sprint log's Planner entry for the verification trace).

**Correction (2026-08-04, post-peer-review):** an automated byte-substring
audit run against ALL 11 rows in this section (`excerpt_text in real_text`,
for every row, full or trimmed) found exactly ONE that failed:
`STATE_OK_T74_S74-6106`'s excerpt had been hand-typed from a truncated
terminal printout rather than sliced programmatically from the real text,
and had silently dropped a stray `TM` token (a trademark-superscript
artifact of the source PDF's extraction, appearing on its own line between
"United" and "States Geological Survey" in the real corpus). That is a
content edit, not whitespace normalization, and the row's own
`_fixture_note` at the time incorrectly called it "byte-verbatim." Fixed:
the excerpt is now the real text's own exact substring (paragraph breaks
included, `TM` included), re-verified programmatically
(`excerpt in real_text` → `True`) — see that row's own `_fixture_note` and
the sprint log's dated correction entry for the full before/after. The
other 10 rows' byte-exactness (full-row or genuine-substring, per their own
`_fixture_note` where trimmed) was re-confirmed correct by the same audit,
not just re-asserted.

**`multiterm_f5_rows.json`** (family 5, "The term(s) 'X', 'Y', and 'Z'
mean(s)..." shared clauses) — used by both
`backend/tests/unit/test_definition_links_multiterm_shared_clause.py`
(extractor-function level) and
`backend/tests/integration/test_multiterm_f5_shared_clause.py` +
`test_multiterm_f5_blocked_on_markers.py` (full production-pipeline level):

1. `STATE_VT_T23_C35_S3700` — VT, `"mail," "mails," "mailing," and
   "mailed" mean...`, no `(N)` markers at all (simultaneously family 3
   zero-yield). Full row, 194-char body.
2. `STATE_SD_T3_C14_S3-14-5` — SD, `The terms "office," "officer,"
   "executive," and "administrative,"... mean...` under a genuine
   "Definitions" heading (dossier's "extractor yield UNCONFIRMED" row —
   this sprint confirms it live as zero-yield, identical shape to VT).
   Full row, 578-char body.
3. `STATE_MT_T16_C11_P4_S16-11-402` — MT, a working 9-entry "Definitions"
   section whose entry (2) ("Affiliate") body contains a NESTED shared
   clause (`"owns," "is owned" and "ownership" mean...`) plus a nested
   single-term one (`"person" means...`). Full row, 4,728-char body.
4. `STATE_MI_C388_AAct-94-of-1979_S388.1606` — MI, TRIMMED excerpt
   (entries 9-13 of a 26-entry, 50,376-char real section) containing one
   genuine top-level 3-term shared clause plus 4 ordinary single-term
   entries kept as an in-fixture regression guard.
5. `STATE_TX_Cgv_C2009_S2009.003` / `STATE_TX_Cgv_C2002_S2002.001` — TX,
   both full rows — the "parent-clause pointer" shape named in the prior
   sprint's (`2026-08-02-us-state-law`) recorded residual ("13 of 75
   degenerate recovered terms"): a lettered list of bare quoted terms
   whose shared definition ("have the meanings assigned by Section
   2001.003") sits on the PARENT line, not attached to any child entry.

**`multiterm_f6_rows.json`** (family 6, inline parenthetical/cross-reference
definitions) — used by
`backend/tests/integration/test_multiterm_f6_blocked_on_core_seam.py`:

1. `STATE_OR_T41_C496_S496.716` — OR, full row (3,002-char body), the
   dossier's cross-reference variant (`"Enforcement officer" has the
   meaning given that term in ORS 153.005...`). Live-confirmed this
   sprint: the idiom-gap check itself is NOT the blocker (it matches "has
   the meaning" fine when reached directly) — the row is never REACHED by
   any extractor in the real pipeline (heading is a genuine substantive
   caption, not a Definitions heading or a placeholder).
2. `STATE_NH_TXXXVII_C408-C_S14` — NH, full row (4,083-char body), Nurse
   Licensure Compact withdrawal article: `...may withdraw from the compact
   ("withdrawing state") by enacting a statute...` — a genuine apposition
   with no means-idiom, unreachable for the same "else-branch is
   Hebrew-only" reason as ND below.
3. `STATE_ND_T26.1_C26.1-59_S26.1-59-01` — ND, TRIMMED excerpt (Article
   XIV "Withdrawal" of a 46,007-char interstate-compact document)
   reproducing the identical `("withdrawing state")` apposition shape in a
   second real state, confirming it is not an NH-specific artifact.

**`inline_parenthetical_sample_rows.json`** (family 6, extractor-FUNCTION
level, complementary to `multiterm_f6_rows.json` above — these two rows
test a DIFFERENT F6 sub-case: true idiom-gap rejection, not reachability)
— used by `backend/tests/unit/test_definition_links_inline_parenthetical.py`:

1. `STATE_NH_TXXVII_C301-B_S1` — NH, full row (99-char body), a short-title
   apposition (`This act may be cited as ... (the "Act").`) that would be
   rejected by `_MEANS_IDIOM_GAP_RE` even if reached (no "means"/"shall
   mean"/"has the meaning" anywhere in the sentence) — the "pure" family-6
   case the recon dossier's own wording describes.
2. `STATE_OK_T74_S74-6106` — OK, TRIMMED excerpt (one paragraph of a
   14,913-char interstate boundary compact) containing a parenthesized
   quoted string that names DASH CHARACTERS on a map
   (`("-..-")`), not a legal term — the FALSE-POSITIVE GUARD fixture:
   pins that whatever new apposition-detection logic gets built must NOT
   treat this shape as a definition.

**Provenance note on file duplication:** three of these test files
(`test_multiterm_f5_shared_clause.py`,
`test_multiterm_f5_blocked_on_markers.py`,
`test_multiterm_f6_blocked_on_core_seam.py`, and their two `_rows.json`
fixtures) were written by an earlier Planner spawn for this same sprint
that crashed before completing or committing (sprint log: "Planner spawn
attempt 1"). The current Planner found these uncommitted
files still present in the worktree, independently re-verified every real
row against the live parquet snapshot byte-for-byte (see sprint log), found
them accurate and non-redundant with its own work, and adopted them as part
of this sprint's deliverable rather than discarding verified real-world
analysis.

## `f6_apposition_duplicate_rows.json` — ruling M-R14, F6 apposition duplicate-term fixture (2026-08-05)

1. `STATE_DE_T18_C35_SIV_S3578` — DE, full row (12,725-char body), Title 18
   `§ 3578` (Insurance coverage for serious mental illness). Real row,
   vendored verbatim (all 24 original parquet columns, values unmodified,
   no trimming) from `us_de_statutes.parquet`, dataset snapshot
   `301000fc3465374ee0f23c3c6953a8a861e95cad`, retrieved via `pyarrow`
   directly against the local HF cache (`~/.cache/huggingface/hub/
   datasets--vaquill--open-us-law`, same dataset as every other fixture in
   this file) and written straight to JSON — no manual retyping, so
   byte-exactness holds BY CONSTRUCTION. Re-verified anyway with an
   independent second parquet read (fresh `pyarrow.parquet.read_table` +
   filter, a separate process from the one that wrote the fixture),
   diffed field-by-field against the committed JSON: zero mismatched
   fields, `real_row == fixture_row` `True`.

   Used by `backend/tests/unit/test_definition_links_f6_apposition_
   duplicate_terms.py`. The row's own `("ASAM")` parenthetical shorthand
   for "American Society of Addiction Medicine" appears TWICE in the real
   body — once inside entry (1)'s own `"ASAM criteria" means ...`
   definition, once again, unrelatedly, in subsection (d)(1)c's prose —
   so F6's apposition path (`_apposition_candidates` in `rules/
   us_inline_parenthetical.py`, which scans the WHOLE article body
   unconditionally) emits it as TWO separate `DefinitionCandidate`s, not
   one. Picked over the sprint manager's other measured example
   (`STATE_DC_T50_C14_S50-1401.01`, dup `"BOP"`) as the smallest/cleanest
   real reproduction (2 terms extracted, 1 distinct), per the manager's
   own instruction.

## `f6_cross_reference_duplicate_rows.json` — ruling M-R17, F6 cross-reference duplicate-term fixture (2026-08-05)

1. `STATE_AR_T4_C28_S2_S4-28-208` — AR, full row (5,425-char body), Title 4
   `§ 4-28-208` (Private foundations — Amendment of articles of
   incorporation by operation of law). Real row, vendored verbatim (all 24
   original parquet columns, values unmodified, no trimming) from
   `us_ar_statutes.parquet`, dataset snapshot
   `301000fc3465374ee0f23c3c6953a8a861e95cad` (same dataset as every other
   fixture in this file), retrieved via `pyarrow` directly against the
   local HF cache and written straight to JSON — no manual retyping, so
   byte-exactness holds BY CONSTRUCTION. Re-verified anyway with an
   independent second parquet read (fresh `pyarrow.parquet.read_table` +
   filter, a separate process from the one that wrote the fixture), diffed
   field-by-field against the committed JSON: zero mismatched fields,
   `real_row == fixture_row` `True`.

   Used by `backend/tests/unit/test_definition_links_f6_cross_reference_
   duplicate_terms.py`. The row's real `text` column itself repeats an
   entire paragraph verbatim (a genuine scrape artifact, not injected), so
   the cross-reference idiom `"private foundation" as defined in section
   509 of the Internal Revenue Code of 1954...` appears TWICE in the real
   body — F6's cross-reference path (`_cross_reference_candidates` in
   `rules/us_inline_parenthetical.py`, which has no `seen_terms`-style
   dedup — M-R14 added that guard to `_apposition_candidates` only) emits
   it as TWO separate `DefinitionCandidate`s, not one. Picked over the
   sprint manager's other measured example (`STATE_GA_T38_C3_S38-3-42`,
   dup `"rule"`) as the smaller of the two real rows (5,425 vs 7,654
   chars), per the manager's own instruction.

## `m_r23_hyphen_marker_recall_rows.json` — ruling M-R23, hyphen-suffixed-marker recall-regression RED fixture (2026-08-05)

2 REAL rows, vendored byte-exact (all 24 original parquet columns, values
unmodified, no trimming), from `us_tx_statutes.parquet`, dataset snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad` (same dataset as every other
fixture in this file). Written straight to JSON by a script reading the
parquet directly (no manual retyping, so byte-exactness holds BY
CONSTRUCTION), then independently re-verified by a SEPARATE second
parquet read (a fresh process from the one that wrote the fixture),
diffed field-by-field against the committed JSON: zero mismatched fields
across all 24 columns for both rows, `real_row == fixture_row` `True` for
both.

Found by the sprint manager's corpus kill-experiment (ruling M-R23): the
M-R18 guard in `rules/us_inline_parenthetical.py` introduced a silent
RECALL regression (not merely a duplication/precision defect like M-R16/
M-R17/M-R18's own original finding) — a term is lost ENTIRELY (1 -> 0),
not double-counted.

1. **`STATE_TX_Coc_C2310_S2310.001`** (Tex. Occupations Code § 2310.001,
   `"§ 2310.001. DEFINITIONS."`) — entry `(9-a) "Supplier" has the
   meaning assigned by Section 162.001, Tax Code.`
2. **`STATE_TX_Cin_C228_S228.001`** (Tex. Insurance Code § 228.001,
   `"§ 228.001. GENERAL DEFINITIONS."`) — entry `(5-a) "Low-income
   community" has the meaning assigned by Section 45D(e), Internal
   Revenue Code of 1986.`

Both `section_title`s are genuinely heading-recognized by
`is_definitions_heading` (verified live, not assumed) — both rows reach
`USProfile.extract_definitions_from_section` via the real production
Definitions-section path, not `extract_local_scope_definitions`'s
ordinary-body path.

**Root cause (why these two, mechanism):** `us_profile.py`'s baseline
entry-start recognizer (`_MARKER_TOKEN_RE = re.compile(r"\(\w+\)\s*")`)
requires a parenthesized marker to contain only `\w` characters — `\w`
excludes the hyphen, so a suffixed marker like `(9-a)`/`(5-a)` (Texas's
real convention for inserting a definition between two existing numbered
entries without renumbering the whole list) is never recognized as an
entry start; baseline yields NOTHING for that entry. F6's cross-reference
scan (`_cross_reference_candidates`) is the only rule that could still
capture it — but the M-R18 guard's own `_ENTRY_LEADING_QUOTE_RE`
(`\([^\s()]{1,10}\)`, unlike baseline's `\w`-only pattern) DOES match the
hyphen, so it wrongly treats the term as "already captured by baseline
elsewhere" and discards F6's candidate too. Net effect: the term is lost
entirely, invisible to the suite until this corpus kill-experiment found
it (no existing test covered either of these two rows).

**Significant scope finding, reported not silently acted on:** an
exhaustive scan of the full real `us_tx_statutes.parquet` file for this
exact shape (non-`\w` marker immediately followed by a quoted term
immediately followed by a cross-reference idiom) found **111 occurrences
across 91 distinct real TX sections**, not merely these 2 — this
hyphen-suffixed-marker drafting convention is pervasive in Texas. The
same scan against 8 other already-fixtured state files (DE, NY, CA, IL,
FL, OH, PA, GA, AR) found ZERO occurrences in any of them — this class
appears to be Texas-specific, not corpus-wide. This fixture and its test
deliberately pin only the 2 named rows per the assigned task's scope; the
other 89 sections are not vendored or asserted on here.

Used by `backend/tests/unit/test_definition_links_m_r23_hyphen_marker_
recall_regression.py`.
