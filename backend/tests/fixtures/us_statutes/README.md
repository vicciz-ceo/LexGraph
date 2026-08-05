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

## `us_g8_ar_occurrence_embedded_continuation_row.json` — G8 candidate-collision-preference RED fixture (2026-08-05)

1 REAL row (all original parquet columns, values unmodified),
`STATE_AR_T27_C14_S23_S27-14-2301` (Ark. Code Ann. Section 27-14-2301,
"Definitions"), pulled from `us_ar_statutes.parquet` — sprint
`2026-08-05-defs-core-follow-on-2`, gate G8 ("a baseline bad candidate
must not silently beat a cleaner same-term candidate from a registered
rule at persistence").

**What it proves**: this row's own `text` field carries its content
duplicated verbatim by the source dataset (the SAME real corpus artifact
already documented above for `STATE_AR_T20_C48_S6_S20-48-603`, D-CF
fixture #4 — evidently common across `us_ar_statutes.parquet`, not a
one-off). For the term "Occurrence", baseline's own
`extract_definitions_from_section` (zero registered rules needed)
produces THREE candidates sharing the identical `(article_id,
("Occurrence",))` persistence key: a 155-char one (FIRST in list order —
wins today) that illegally contains a structurally separate sub-item's
own marker+quote (`(B) "Occurrence"`) glommed into its own
`definition_text`, and two later, correctly-bounded ones (64 and 73
chars). `pipeline.py`'s Stage 2 persists whichever same-key candidate it
encounters first and never revisits that row — the 155-char candidate
wins, silently discarding the clean one.

**Why this row, not the WA newline-collapse rows** (`claude/defs-us-markers`
QA fixture, read but never cherry-picked here): the WA swallow is caused
by `_split_into_numbered_blocks` finding the entire body as ONE line — the
exact shape gate G3 (`us_profile.py:346`, unbounded last entry) targets in
the same sprint. This AR row's collision is provably G3-independent: the
section is genuinely multi-block (properly newline-separated), and the
winning candidate's own block is never the row's last block (verified by
`test_occurrence_is_not_the_last_entry_g3_cannot_be_the_mechanism_here` in
`test_us_g8_candidate_collision_preference.py`) — a fix scoped to the
LAST entry's boundary cannot reach it, whatever shape that fix takes.

Provenance: `vaquill/open-us-law` dataset snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`, file `us_ar_statutes.parquet`,
fetched 2026-08-05 by this Planner directly into this worktree's own
`backend/.venv` (`pyarrow` already installed there for this sprint), never
read by the committed test suite itself (program rule prior-R6 — suites
run offline). SHA-256 of the row's `text` field:
`3fe2c0d1bc4213dda7d56b0aa79677a6460341722bdafe7ead42cda9bd95ec67`.

## `g12_il_base_rates_competitive_service_row.json`, `g12_il_government_person_motion_dropped_row.json`, `g12_pa_references_to_construction_clause_row.json` — G12 `includes`-idiom RED fixtures (2026-08-05)

3 REAL rows (all original parquet columns, values unmodified) — sprint
`2026-08-05-defs-core-follow-on-2`, gate G12 (director ruling
D-INCLUDES: widen `_MEANS_IDIOM_GAP_RE` to the `includes`/`shall
include` defining-verb class, boundary AND emission together, with a
mandatory targeted "References to" construction-clause guard).

1. **`STATE_IL_C220_A5_S16-102`** (220 ILCS 5/16-102, Illinois Public
   Utilities Act), from `us_il_statutes.parquet` — genuine SWALLOWING:
   the real `"Base rates" means ...` entry's `definition_text` today
   illegally runs on to absorb the immediately following, separately
   quoted `"Competitive service" includes ...` entry whole (1,047 chars
   instead of the true ~737), because `includes` is not yet a
   recognized entry-starting idiom. SHA-256 of `text`:
   `88c0b8caffd8f5679b57f6ea9459d0f023d2e5b923e74744aed3258b185e5b30`.
2. **`STATE_IL_C735_A110_S10`** (735 ILCS 110/10, Illinois Code of Civil
   Procedure), from `us_il_statutes.parquet` — genuine DROP: "Government",
   "Person", and "Motion" are each real `"..." includes ...` entries
   that appear BEFORE the row's first `means`-idiom entry ("Moving
   party") — today they are not swallowed into anything (nothing
   recognized precedes them), they simply never appear in the output at
   all. Proves the manager ruling's "boundary-without-emission would be
   a silent-drop bug" concern is not hypothetical. SHA-256 of `text`:
   `df62b18f3c5f732acedb4b6eb1755fe1b785a8a45917284d5632064651492fd8`.
3. **`STATE_PA_T15_C57_S5749`** (15 Pa.C.S. Section 5749, PA nonprofit
   corporation law), from `us_pa_statutes.parquet` — the mandatory PA
   construction-clause guard shape: `"For the purposes of this
   subchapter: (1) References to "other enterprises" shall include
   employee benefit plans and references to "serving at the request of
   the corporation" shall include ..."` — a rule about how OTHER text
   should be read, not a `"X" means Y` definition. This row's own real
   `section_title` ("Application to employee benefit plans.") is a
   genuine heading (PA is one of the 7 states already working off
   `section_title`), so it does not reach `heading_was_derived=True` in
   the live pipeline today — the fixture's own test forces that kwarg
   deliberately (documented in the test file) because the guard is a
   REQUIRED, program-wide property of `_extract_inline_quoted_
   definitions` itself, not a property of which jurisdiction happens to
   reach it via IL/CA/GA's placeholder-heading convention. Verified
   live: this row's primary `"(N)"`-block splitter also yields nothing,
   so forcing the kwarg exercises the same fallback function real
   placeholder-heading rows do. SHA-256 of `text`:
   `f57e15bb1708feba189d952d400b750ceb9624d2cb448c22715b54fcf2c2fe0a`.

Provenance (all 3): `vaquill/open-us-law` dataset snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`, fetched 2026-08-05 by this
Planner directly into this worktree's own `backend/.venv` (`pyarrow`
already installed for this sprint), never read by the committed test
suite itself (program rule prior-R6 — suites run offline).
