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

`huggingface_hub`/`pyarrow` were NOT installed in `backend/.venv` as of THIS
sprint's Planner work (verified `ModuleNotFoundError` for both, plus
`pandas`, at the time) — the Planner fetched these rows using a disposable
venv outside the repo (`pip install huggingface_hub pyarrow` into a scratch
venv), never touching `backend/.venv` or `backend/pyproject.toml`. Adding
`huggingface_hub`/`pyarrow` as real dependencies (dev or production, per
what the ingester needs) was the Developer's job for the G6 (dataset
ingester) item.

**Correction (QA, sprint 2026-08-04-defs-us-preamble, M-R10(b)):** as of
that later sprint, `pyarrow` IS installed in `backend/.venv` and IS a
declared dependency (`pyarrow>=17.0`, `backend/pyproject.toml:15`). Only
`huggingface_hub` remains absent — the on-disk vaquill/open-us-law HF
snapshot is fetched directly via `pyarrow.parquet` against the cache path
(`~/.cache/huggingface/hub/datasets--vaquill--open-us-law`), never via the
`huggingface_hub` API, so no test or fixture-building script in this
sprint needed it. Left uncorrected, the paragraph above would send a future
agent to build a scratch venv it does not need.

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

## `{ga,md,ne,ms,sd}_preamble_rows.json` / `us_preamble_rows.json` — sprint
   2026-08-04-defs-us-preamble (US family 2: body preambles without the
   literal word "Definitions")

Real, verbatim, unmodified full parquet row dicts (never downloaded by any
test — pulled live from the on-disk vaquill snapshot by the Planner, per
this sprint's D1/D2/D3; see `docs/sprint/sprints/2026-08-04-defs-us-
preamble-log.md` for the full inventory each row was selected from).

- `{state}_preamble_rows.json` (one file per state, `ga`/`md`/`ne`/`ms`/
  `sd`, list-of-row-dict shape matching `de_sample_rows.json`): each file's
  FIRST row(s) are POSITIVE examples (a real body-preamble definitions
  block, today captured by neither gate) used by
  `test_us_body_preamble_capture_red.py`; the LAST row in each is a
  NEGATIVE example (the family's trigger vocabulary present, but nothing is
  actually defined — a cross-reference, an administrative/operative
  sentence, a legal rule) used by `test_us_body_preamble_negative_guard
  .py`. `ne`/`sd` each carry an extra row documenting a shape that is
  captured by heading-recognition alone but still can't be EXTRACTED by any
  current code (unquoted term text) — a confirmed `2026-08-04-defs-us-
  markers` cross-sprint dependency, not a bug in this sprint's rule.
- `us_preamble_rows.json` (dict keyed by `act_id`, NOT the list shape —
  inherited as-is from a surviving untracked file left by this sprint's
  Planner attempt #1, which died mid-session before committing anything
  but after writing real work directly into the worktree; independently
  verified and adopted by attempt #2 rather than duplicated, per
  `test_definition_links_us_preamble_family.py`'s own docstring for full
  provenance of each of its 4 rows).

Provenance: same dataset/commit as the rows above (`vaquill/open-us-law`),
fetched 2026-08-04 from the local HF snapshot already on disk at
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law` — never
downloaded by any committed test.
   `definition_text`. Genuine, live-path-confirmed defect (item 3 bounce).

## `us_heading_variants_rows.json` — sprint 2026-08-04-defs-us-headings (family 4)

16 REAL rows (all 24 original columns, values unmodified), one per candidate
rule or negative-guard case, pulled 2026-08-04 from 10 different real state
files (`us_ct_statutes.parquet`, `us_mo_statutes.parquet`,
`us_dc_statutes.parquet`, `us_ak_statutes.parquet`, `us_co_statutes.parquet`,
`us_wi_statutes.parquet`, `us_nv_statutes.parquet`, `us_al_statutes.parquet`,
`us_tx_statutes.parquet`, `us_az_statutes.parquet`, `us_ar_statutes.parquet`,
`us_ny_statutes.parquet`) via a disposable scratch venv outside
`backend/.venv` (same retrieval method as the 2026-08-02 fixtures below —
`huggingface_hub`/`pyarrow` are still not installed in `backend/.venv`;
never run by the test suite, ruling R6). Dataset commit
`301000fc3465374ee0f23c3c6953a8a861e95cad` (the corpus was re-synced since
the 2026-08-02 fixtures' `d2d76035...` commit — that older snapshot is a
10-file partial download and can no longer reproduce the full 52-file
census; `301000fc...` is what both the sprint's evidence scout and this
fixture were pulled from, confirmed by reproducing the scout's headline
census numbers exactly: 83,303 `defin*` titles / 61,075 already-recognized
/ 22,228 miss pool, live, against this exact snapshot).

Every row's live behavior against the REAL `us_profile.is_definitions_heading`
and `us_profile.extract_definitions_from_section` (base commit `b4f7833`,
before this sprint's rule module exists) is asserted in
`backend/tests/unit/test_definition_links_us_heading_variants.py` and
`backend/tests/integration/test_us_heading_variants_end_to_end.py` — the
numbers below are reproduced there, not just asserted here:

**Positive — a family-4 candidate rule should flip this heading False→True:**

1. **`STATE_CT_T42a_C9_S42a-9-102`** (`"Sec. 42a-9-102. Definitions and
   index of definitions."`) — R-SEC (own `Sec.`/`Secs.`/`Art.`/`Article`
   label-strip candidate): today's `_SECTION_LABEL_RE` only accepts the
   spelled-out word `Section`, so this abbreviated-label CT UCC heading is a
   baseline miss. Body parses TODAY (before any rule change) into **82
   real candidates** via `extract_definitions_from_section` — the
   sprint's flagship U1 live-path proof (heading recognition alone, once
   shipped, immediately produces 82 real `Definition` rows end-to-end).
2. **`STATE_CT_T36a_C668_S36a-636`** (`"Sec. 36a-636. Defintions."`) —
   R-MISSPELL. Body parses into **3 real candidates** today — a second,
   independent end-to-end proof, isolated from R-SEC (the misspelling
   defeats R-SEC's own first/last-word check too, so this row is captured
   by R-MISSPELL alone, not by rule overlap).
3. **`STATE_MO_C334_S334.043`** (`"334.043 Reciprocity — definitions —
   procedure — fees."`) — R-MID (mid-token candidate: any tail token,
   regardless of position, exactly `Definition(s)`). Near-verbatim match to
   the program dossier's own cited family-4 example. Body parses into **6
   real candidates** today.
4. **`STATE_DC_T28_C_S28:2A-103`** (`"§ 28:2A-103. Definitions and index
   of definitions."`) — R-MID again, on DC's UCC title-colon-chapter
   numbering (`28:2A-103`). Chosen deliberately to demonstrate that R-MID's
   plain token scan recovers this shape WITHOUT any dedicated colon-aware
   number-stripping rule (see Planner's report: a prototyped R-COLON rule
   was measured and dropped as 100% redundant with R-MID — 0 of its 31
   target rows were not already covered by R-MID alone). Body parses into
   **27 real candidates** today.
5. **`STATE_AK_T13_C13.06_S13.06.050`** (`"General definitions for AS
   13.06 — AS 13.36."`) — R-MID (mid-token; "General" precedes
   "definitions" so baseline's first-word rule never fires). Body parses
   into **0 candidates today** (the body is one unbroken paragraph with no
   line break before its first `"(1)"` marker, so the extractor's
   line-anchored entry-boundary scan never finds a start — a markers-family
   defect, hand off, do not fix here). Also the sprint's chosen worked
   example for the U2 scope-seam question: the heading names a specific
   multi-chapter range (`AS 13.06` through `AS 13.36`), a scope granularity
   the published core seam's `determine_scope` (chapter | law-wide only)
   cannot express — see the Planner's report/log for the full escalation.
6. **`STATE_CO_T2_A3_P1_S2-3-110.5`** (title ends `"...access to records -
   definitio"`, CO's real source-data truncation) — R-TRUNC (last tail
   token is a strict, verified-not-a-real-word prefix of `"definitions"` of
   length ≥5: `defin`/`defini`/`definit`/`definiti`/`definitio`, checked
   against `/usr/share/dict/words` on this machine — none are real English
   words). Body parses into **9 real candidates** today — the title
   truncation does NOT affect the body, which is complete.
7. **`STATE_CO_T22_A33_P1_S22-33-106.3`** (title ends `"...student
   statements - definitio"`) — R-TRUNC again, deliberately chosen as a
   **zero-yield** companion to row 6: body parses into **0 candidates**
   today (a normal single-topic disciplinary-investigations section whose
   own defined term, if any, isn't in the `(N) "Term" means` shape the
   extractor recognizes) — hand off, do not fix here. Live full-population
   re-check: R-TRUNC's target cluster is exactly 117 CO rows (matches the
   panel log exactly); body-yield across all 117 (not a 30-row sample) is
   **67/117 (57.3%)**, refining the log's 20/30 (67%) sample estimate
   rather than contradicting it.
8. **`STATE_WI_C939_S939.22`** (`"Words and phrases defined."`, WI's
   real criminal-code Definitions section) — R-VERB-bare (last tail token
   exactly `defined`), the sprint mandate's own cited verb-form example.
   Body parses into **27 real candidates today** — an important
   correction to the panel log's "verb-form yields 0/85 sampled, expected"
   framing: it is NOT literally zero population-wide. Live re-check across
   the full WA/WV/WI/WY/DC/FED verb-form miss cluster (9,813 rows):
   **46/9,813 (0.47%) yield ≥1 candidate today**, concentrated in WV
   (20/234, 8.5%), WI (10/24, 41.7%!), WY (7/66, 10.6%) — NV, which
   supplies 8,850 of those 9,813 rows (90%), is confirmed still **0/8,850
   (0%)**, so the log's NV-specific "0/25 re-check" finding stands exactly;
   only the blanket "verb-form" framing needed narrowing to "verb-form
   outside Nevada."
9. **`STATE_NV_T58_C706_S706.074`** (`'"Hazardous material" defined'`) —
   R-VERB-bare, chosen as the **representative zero-yield** row for NV's
   dominant 8,829-row bare-verb-form cluster (52% of the entire family-4
   miss pool): confirmed **0 candidates** today — hand off, do not fix
   here, per ruling H-R1.
10. **`STATE_AL_T25_C9_S25-9-276`** (`'Section 25-9-276 "Blasting Agent"
    and "Explosives" Defined; Storage and Transportation of Blasting
    Agents, Explosives, and Detonators Generally'`) — R-VERB-extended
    ("defined" immediately followed by `;` then more clause text, the
    census's "verb-form extended" shape). Body parses into **1 real
    candidate today** — the one non-zero example found while re-checking
    this sub-cluster (otherwise 0/30 as logged); most R-VERB-extended rows
    remain a markers-family hand-off.

**Negative — must STAY False under every family-4 rule (precision guards):**

11. **`STATE_TX_Cfa_C101_S101.001`** (`"§ 101.001. APPLICABILITY OF
    DEFINITIONS."`) — re-verified TRUE NEGATIVE per the panel log: real
    body is `"(a) Definitions in this chapter apply to this title. (b) If
    ... a term defined by this chapter has a meaning different ..."` — a
    precedence clause defining zero terms. No family-4 rule fires on it.
12. **`STATE_AZ_T33_C6.1_A1_S821`** (`"33-821 Exemption from
    definition"`) — real corpus instance of the preposition-exclusion
    guard (`"from"` immediately precedes `"definition"`): pins that R-MID's
    own copy of `_PRECEDING_EXCLUSION_WORDS`-equivalent logic must also
    reject this, not just baseline's.
13. **`STATE_AR_T23_C64_S1_S23-64-103`** (`"Exceptions to definitions"`)
    — same guard, `"to"` preposition, different state.
14. **`STATE_NY_ANPC_A4_S406`** (`"Private foundation, as defined in the
    United States internal revenue code of 1954: provisions included in
    the certificate of incorporation"`) — real corpus instance of the
    `"... as defined in ..."` verb-form guard: "defined" is followed by
    `" in "`, not directly by `;`/`:`, so R-VERB-extended must not fire,
    and it is nowhere near the last tail token, so R-VERB-bare must not
    fire either.
15. **`STATE_AK_T32_C32.06_S32.06.406`** (`"Continuation of partnership
    beyond definite term or particular undertaking."`) — real morphology
    guard: `"definite"`, not `"definition(s)"`/`"defined"` — must stay
    False under every rule (R-MID's `^Definitions?$` token match and
    R-VERB's `^defined$` token match both require an EXACT token, so
    `"definite"` cannot satisfy either).
16. **`STATE_TX_Cgv_C2001_S2001.175`** (`"§ 2001.175. PROCEDURES FOR
    REVIEW UNDER SUBSTANTIAL EVIDENCE RULE OR UNDEFINED SCOPE OF
    REVIEW."`) — real morphology guard, `"undefined"` — same reasoning,
    different word, ALL-CAPS convention (also exercises R-SEC's
    label-strip path finding no `Sec.`/`Section` label and correctly
    falling through unmatched).

Row 6's negative-guard companion for the existing bare-`"Section N"`-
placeholder guard (ruling R9/R12) is NOT re-vendored here — the tests
reuse the existing real IL row (`STATE_IL_C325_A7_S15`) already committed
in `qa_cycle3_rows.json` above, loaded via that file's existing loader.

### A correction to the panel log's evidence (misspelled cluster count)

Live re-verification (full 52-file token-frequency census, every
`\w*defin\w*` token counted) finds the misspelled cluster
(`Defintions`/`definitons`-shaped, excluding correctly-non-heading
morphology like `definite`/`undefined`) is **6 rows exactly** — 5×
`"Defintions"` (3 in `us_al_statutes.parquet`, 1 in `us_ct_statutes.parquet`,
1 in `us_mi_statutes.parquet`) + 1× `"definitons"`
(`us_nj_statutes.parquet`) — not the panel log's cited **16**. No `16th`
row exists anywhere in the corpus under any `defin*`-prefixed misspelling
pattern searched. Reported to the manager as a correction, not silently
fixed.

### Retrieval (fixture creation only — never run by the test suite, R6)

Same disposable-scratch-venv method as above
(`huggingface_hub`/`pyarrow` installed outside `backend/.venv`), reading
directly from the local HF cache
(`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`)
rather than re-downloading — the full 52-file corpus was already cached
locally for this sprint's evidence scout.
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

## G8 reverse-order fixtures — containment replacement safety (2026-08-05, Phase 14 correction)

Three REAL rows (all original parquet columns, values unmodified), beginning with
`STATE_AR_T27_C14_S23_S27-14-2301` (Ark. Code Ann. Section 27-14-2301,
"Definitions"), pulled from `us_ar_statutes.parquet` — sprint
`2026-08-05-defs-core-follow-on-2`, gate G8. Phase 14 supersedes the
original "shorter same-term candidate is cleaner" interpretation: a
same-term `includes`/`does not include` continuation is definitional content
under D-INCLUDES/P-ALT, so containment alone is not a safe persistence
preference.

**Occurrence fixture — what it proves**: this row's own `text` field carries its content
duplicated verbatim by the source dataset (the SAME real corpus artifact
already documented above for `STATE_AR_T20_C48_S6_S20-48-603`, D-CF
fixture #4 — evidently common across `us_ar_statutes.parquet`, not a
one-off). For the term "Occurrence", baseline's own
`extract_definitions_from_section` (zero registered rules needed)
produces THREE candidates sharing the identical `(article_id,
("Occurrence",))` persistence key. The first 155-char candidate contains
`(B) "Occurrence" includes ...`; this is the complete same-term definition,
not a distinct-term leak. The later 64- and 73-char candidates are incomplete
fragments. The live-path RED now pins that a later contained fragment must
not replace the complete first candidate. On the pre-G8 parent
`8943d96^`, first-wins would have preserved this first candidate; the G8
containment update is what makes the RED fail.

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
read from the local read-only snapshot on 2026-08-05, never read by the
committed test suite itself (program rule prior-R6 — suites run offline).
SHA-256 of the Occurrence row's `text` field:
`3fe2c0d1bc4213dda7d56b0aa79677a6460341722bdafe7ead42cda9bd95ec67`.

**Virtual currency fixture** —
`us_g8_ar_virtual_currency_reverse_order_row.json` is the unmodified, full
`STATE_AR_T23_C55_S23-55-102` row from the same snapshot/file. Its first
`"Virtual currency"` candidate is the complete 528-character `means` plus
same-term `(B) ... does not include` definition; a later 276-character
exclusion-only candidate is a literal substring. This is the real-row
live-path RED for G8's damaging replacement direction. Its row remains a
fully offline fixture; tests never open the corpus. SHA-256 of its source
row's `text` field:
`9fd823ff0fce7c1ad082a7c369219b56fd585a8276c8c601d6af32db970a546a`.

**Partnership fixture** —
`us_g8_ar_partnership_structural_boundary_row.json` is the unmodified, full
`STATE_AR_T26_C18_S1_S26-18-104` row from the same snapshot/file. It is a
positive control: `"Partnership"`'s initial candidate runs into the next,
different quoted `"Partner"` entry, while the shorter prefix ends exactly
before that entry. It documents the narrow class of real beneficial trims
measured by the Phase-14 artifact; it does not authorize a U.S. grammar
heuristic in jurisdiction-neutral `pipeline.py`. SHA-256 of its source row's
`text` field:
`bbe0ad8ce303966493415505caaa13503a601524cc76f28e62c5cfa4cf960051`.

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
## `us_markers_wave1_rows.json` — sprint 2026-08-04-defs-us-markers, wave 1 (2026-08-04)

6 REAL rows (full original columns, values unmodified), pulled from
`us_va_statutes.parquet` (2), `us_wa_statutes.parquet` (2), and
`us_federal_statutes.parquet` (2) — family 3's "no-marker inline-quote"
sub-case (a real Definitions-headed section whose body is `"Term" means
...` sentences with NO `(N)`-paragraph markers, which
`USProfile.extract_definitions_from_section` cannot parse). Confirmed live
against the real, unmodified `_extract_inline_quoted_definitions`
(pipeline.py:246-289) and `run_definition_linking` end to end; full
methodology and measured rates in this sprint's log, `## P1 — planner pass
1`.

1. **`STATE_VA_T23.1_SI_C3_S23.1-300`** — clean rescue, 9 real terms
   (College degree, Cost of education, Educational and general fees,
   Educational and general services, student enrollment, Fiscal year, Peer
   institutions, STEM, Student), each 44-658 chars. The recon dossier's own
   named VA example row.
2. **`STATE_VA_T4.1_SII_C6_S4.1-600`** — real VA Cannabis Control Act
   Definitions section (14,629-char body), 48 genuine terms (32-1,108
   chars each) plus a real false-positive trap: "sell" (inside `"Sale" and
   "sell" includes ... by any means.`) sits ~170 chars before the literal
   word "means" in UNRELATED prose — the naive fallback's bounded
   idiom-gap match treats that as sell's own defining idiom, collapsing
   its captured `definition_text` to a single `"."` character.
3. **`STATE_WA_T47_C14_S020`** (`RCW 47.14.020: Definitions.`) — clean
   rescue, 2 real terms (Right-of-way, Airspace). The exact row the recon
   dossier's own dossier quotes for WA's dominant miss shape.
4. **`STATE_WA_T9A_C04_S110`** (`RCW 9A.04.110: Definitions.`) — real WA
   criminal-code Definitions section (7,318-char body), 18 genuine terms
   plus a real nested-quote trap: "Vehicle"'s own definition contains
   `a "motor vehicle" as defined in ...` — the naive fallback treats
   "motor vehicle" as a second, phantom top-level term (no defining
   sentence of its own in this statute), truncating "Vehicle" itself to a
   single `"a"` character.
5. **`USC_T16_C65_S4503d`** — small (1,025-char), real, clean-LOOKING FED
   Definitions section, 3 real terms (Institutes of Tropical Forestry,
   Secretary, State). Exposes a SEPARATE, systematic defect: the LAST
   recognized entry ("State") swallows the row's trailing citation plus
   appended "Editorial Notes" header (its naive definition_text is 626
   chars and contains the literal string "Editorial Notes") — this
   happens on essentially every FED row that carries the dataset's
   appended-notes shape, not just pathological ones.
6. **`USC_T15_C12_S431`** — small (3,239-char), real FED Definitions
   section. Only entry (a) ("agricultural products") uses the fallback's
   recognized "means" idiom; entries (b)-(f) use idioms it doesn't
   recognize as a boundary ("shall be held to include and mean", "shall
   be construed to mean") — so the naive fallback swallows ALL of (b)-(f)
   plus the row's appended "Editorial Notes"/"References in Text" tail
   into "agricultural products"'s own definition_text (3,169 of 3,239
   chars). Full-corpus check (this sprint's log): 83.0% of FED
   zero-candidate Definitions sections carry this same appended-notes
   shape, and 99.2% of all >=5,000-char inline-fallback candidates across
   VA+WA+FED come from a row with it — FED's dominant, and previously
   unmeasured, boundary hazard.

## `us_markers_correctly_empty_rows.json` — planner pass 2, gate U4 classifier (2026-08-04)

14 REAL rows (full original 24 columns, values unmodified — 10 from
planner pass 2, 4 more from the bounce cycle below), for
`test_definition_links_correctly_empty.py`'s RED tests defining/pinning
the `app.definition_links.correctly_empty` module's contract (sprint log
`## P2`/bounce cycle, gate U4, rulings U-R3/U-R7). All verified
byte-identical to the source parquet (`section_title` and `text`, every
row, every check `True`).

**Terminal-status class** (all real DC rows — DC's zero-candidate set is
53.6%/178/332 this class alone, this sprint's log `## P1`):
1. `STATE_DC_T47_C28_S47-2843` — body `"Repealed."`.
2. `STATE_DC_T42_C36_S42-3631` — body `"Expired."`.
3. `STATE_DC_T2_C3_S2-308.13` — body `"Recodified as § 2-381.01 ."`.
4. `STATE_DC_T33_C1_S33-112.03` — body `"Reserved."`. **Caveat, checked
   exhaustively this pass**: no row in the full 53-state corpus combines
   a `Reserved.`/`Renumbered.`/`Omitted.`/`Vacant.` body with a heading
   `is_definitions_heading` recognizes (0 hits, all 53 `*_statutes.parquet`
   files scanned) — this row's OWN heading is `"§ 33-112.03. [Reserved]."`,
   not Definitions-shaped. Vendored anyway because the classifier's
   contract is a pure function of `body_text` (see module docstring in the
   test file) and this is REAL corpus text proving the `Reserved.` literal
   shape genuinely exists — not because this specific row would ever reach
   the classifier in production.

**Cross-reference class** — corrected this pass, see below:
5. `STATE_WI_C851_S851.002`, 6. `STATE_WY_T99_C3_S99-3-1101`,
   7. `STATE_WA_T43_C99N_S010` — three real, genuine other-citation
   cross-references (one per jurisdiction), each a single short sentence
   naming a DIFFERENT section/chapter than the one it's in, with nothing
   operative after it (WI has a trailing `History: ...` amendment-citation
   annotation, real, carries no defining content).

**NEGATIVE class — critical guard, must classify as MISS, not
correctly-empty:**
8. `STATE_WA_T47_C14_S020` — wave-1's OWN flagship WA test row (2 real
   terms, `Right-of-way`/`Airspace`). Its body opens with `"The
   definitions set forth in this section apply throughout this
   chapter."` — a SELF-referential preamble (the definitions are right
   HERE, not elsewhere) immediately followed by real defining content.
9. `STATE_VA_T29.1_C7_A2.1_S29.1-733.2` — real VA watercraft-titling
   Definitions section, 9,658 chars, **46 real quoted definitions**. Body
   opens `"The definitions in this section do not apply to..."`.
10. `STATE_VA_T58.1_SI_C17_A9_S58.1-1735` — real VA rental-tax Definitions
    section, 3,726 chars, **7 real quoted definitions**. Body opens
    `"The definitions in § 46.2-1408 shall apply, mutatis mutandis, to
    this article."` — names a REAL other citation, same surface shape as
    the genuine cross-reference rows above, but followed by substantial
    operative content of its own.

**Why rows 8-10 matter (material correction to pass 1's classifier
measurement, sprint log `## P2`):** pass 1's log defined the
cross-reference rule as matched "at the START of the stripped body" with
no requirement that the match consume the WHOLE body. Applying that
literal rule to the full real corpus this pass (not merely the WI/WY
examples pass 1 checked) finds it is dangerously over-broad: **727 of
WA's 734 naive "cross-reference" hits (99.0%) — including row 8, wave
1's own flagship test row — are self-referential preambles with real
defining content immediately after them, not actual cross-references.**
Both VA rows above are further proof: 46 and 7 real definitions
respectively, both opening with a citation-shaped sentence that a
start-anchored-only match would misclassify as "correctly empty." The
corrected rule (requires the ENTIRE stripped body, after an optional
trailing `History:` annotation, to be short — nothing substantial follows
the cross-reference sentence) reclassifies all three of rows 8-10 as MISS
and leaves rows 1-7 unaffected. Recomputed full-corpus rate with the
corrected rule: **WA 4/1,778 (0.2%)**, not pass 1's reported 734/1,778
(41.3%) — VA drops from 2/1,065 (0.2%) to 0/1,065 (0.0%). DC/WI/WY numbers
are unchanged (unaffected by the fix). Full detail in the sprint log's
`## P2` entry.

## Rows 11-14 — bounce cycle, real defect in the SHIPPED module (2026-08-04)

4 more real WA rows (same 24-column schema, byte-verified), added after
the manager's adversarial full-corpus sweep (34,241 real Definitions-
headed zero-candidate sections, all 53 jurisdiction files) found the
Developer-shipped `correctly_empty.py` calls 228 of them correctly-empty,
of which exactly these 4 are WRONG (ruling U-R7) — every other
jurisdiction's verdicts are clean:

11. `STATE_WA_T82_C23A_S010` (1,848 chars, 7 `"Term" means` entries:
    Petroleum product, Possession, Previously taxed petroleum product,
    Rack, Wholesale value, plus nested `Control`/`Actual possession`/
    `Constructive possession`). Opens with the same self-referential
    preamble as row 8 above; the shipped regex's citation group crosses
    all ~1,800 intervening chars (the body has ZERO newlines) to latch
    onto a SECOND, genuine "...the definitions in chapters 82.04, 82.08,
    and 82.12 RCW apply to this chapter." sentence at the very end.
12. `STATE_WA_T18_C44_S011` (4,021 chars, 11 real entries: Committee,
    Controlling person, Department, Designated escrow officer, Director,
    ..., Split escrow). Same mechanism; the row's own `text` field
    concatenates a SECOND, unrelated section's content (a real,
    non-injected vaquill data-artifact — the escrow-licensing text abruptly
    becomes health-care "Insurance producer" licensing text mid-string,
    no separator) whose own trailing "...are applicable to a disability
    insurance producer." is what the regex actually latches onto — proves
    the defect doesn't need a genuinely relevant second citation, just the
    bare trigger words appearing anywhere later on the same (newline-free)
    line.
13. `STATE_WA_T70A_C30_S010` (2,677 chars, 12 real entries: Approved
    shellfish tag or label, Commercial quantity, Department, ...,
    Shellstock). Same concatenated-unrelated-content artifact as row 12
    (shellfish-sanitation text becomes vehicle-emissions text mid-string);
    closes on "...do not apply with respect to..." — a NEGATED "apply"
    (same shape as pass 1's VA `STATE_VA_T29.1_C7_A2.1_S29.1-733.2`
    finding above) — the regex does not parse negation, only the bare
    word.
14. `STATE_WA_T70_C28_S008` (386 chars, 2 real entries: Department,
    Secretary, plus a third unquoted "Tuberculosis control"). A DIFFERENT
    exploit shape from 11-13: only ONE trigger occurrence (the
    self-referential opening) — the real entries are semicolon-separated
    with no internal periods, so the shipped regex's trailing-clause
    group (which tolerates any non-period character) swallows all of it
    without ever needing a second trigger. Proves a fix that merely
    rejects "trigger phrase occurs twice" would still miss this row.

`test_definition_links_correctly_empty.py`'s general guard test
additionally recombines each row's real leading content (self-referential
opening + real definitions, its own accidental trailing content dropped)
with a DIFFERENT row's real genuine cross-reference sentence (rows 5-7),
at test-run time — proving the required fix is general, not a lookup
table keyed on these 4 exact byte-strings. All 4 recombinations reproduce
the same false positive against the currently shipped module.

## `us_markers_wave2_subcases_rows.json` — planner pass 2, priorities 2 & 3 (2026-08-04)

9 REAL rows (full original 24 columns, values unmodified), for two new
integration test files verifying (a) pass 1's claimed wave-1
"auto-rescue" side effects on UT/TX/AZ, corrected per U-R1 boundary
rigor, and (b) the sub-cases wave 1 does NOT rescue (AL/DC/RI/AK/TN/SC).
Full per-row rationale, exact expected term sets, and the two NEW
boundary defects found this pass (UT's swallow-through-non-means-idiom,
AZ's leaked-next-marker) are in the sprint log's `## P2` entry and each
test's own docstring — not duplicated here per this file's size budget.

Rows: `STATE_UT_T75B_S75B_1_301`, `STATE_TX_Cfi_C37_S37.001`,
`STATE_AZ_T15_C14_A7_S1871` (priority 2); `STATE_AL_T1_C19_S22-19-141`,
`STATE_DC_T28_C25_S28-2501`, `STATE_RI_T35_C35-13_S35-13-2`,
`STATE_AK_T44_C44.42_S44.42.900`, `STATE_TN_T50_C2_S50-2-115`,
`STATE_SC_T5_C1_S5-1-20` (priority 3).

## `d_df_defined_for_rows.json` — director ruling D-DF, `body_confirms` RED fixture (2026-08-04)

7 REAL rows (all 24 original columns, values unmodified), pulled 2026-08-04
from 5 real state files (`us_ky_statutes.parquet`, `us_ct_statutes.parquet`,
`us_al_statutes.parquet`, `us_id_statutes.parquet`, `us_nj_statutes.parquet`)
plus `us_federal_statutes.parquet`, via a disposable scratch venv outside
`backend/.venv` (same retrieval method as `us_heading_variants_rows.json`
above — `pyarrow` installed only in the scratch venv; never run by the
committed test suite, ruling R6). Dataset commit
`301000fc3465374ee0f23c3c6953a8a861e95cad` (same snapshot as
`us_heading_variants_rows.json`).

**Director ruling D-DF**: a `defined for` heading (one alternation of the
closed connector whitelist `for|as|term` inside `_VERB_EXTENDED_RE`,
`us_heading_variants.py:169`, shipped `a0419a4`) must capture ONLY when the
**body** also carries a self-definition marker — the bare rule measured
86–89% precision (below the ~90% floor) across two independent human
samples plus the manager's own full-population scan (72/110 = 65.5% with a
detectable marker, 7 cross-reference-only, 31 neither). Program ruling P-R8
accepted this panel's `body_confirms` design as an additive optional field
on `HeadingRule`, consumed as `matches(heading) and (body_confirms is None
or body_confirms(body))` — see
`backend/tests/unit/test_definition_links_us_heading_variants_d_df.py`'s
module docstring for the full design rationale (why the module must
register TWO `HeadingRule`s, not one, and the ordering that makes it safe)
and the `defines_in_body` predicate spec.

**Confirmed independently**: a full 53-file corpus scan for
`\bdefined\s+for\b` in `section_title` finds **exactly 110 rows** —
reproducing the sprint contract's documented figure exactly, on
independently written code (script not committed, throwaway, same pattern
as prior evidence scripts).

1. **`STATE_KY_TXVIII_C214_S214.280`** (`214.280 "Mattress" defined for KRS
   214.290 to 214.310`) — D-DF POSITIVE. Body: `As used in KRS 214.290 to
   214.310, "mattress" means any mattress, mattress pad or cushion...` — a
   clean, local `"Term" means` self-definition marker. Must be captured.
2. **`STATE_CT_T45a_C802c_S45a-502`** (`Sec. 45a-502. (Formerly Sec.
   45-96a). "Majority" defined for trusts executed prior to October 1,
   1972.`) — D-DF NEGATIVE (primary, the whole point of the ruling). Full
   body is two lines: `Annotation to former section 45-96a:\n\nCited. 168
   C. 144.` — zero defining content of any kind, not even a
   cross-reference. Almost certainly the same already-documented CT "`text`
   column omits subsection (a)" data-quality artifact noted elsewhere in
   this sprint (the real definition of "Majority" likely lives in a
   missing subsection (a) this corpus's `text` field never captured) — that
   provenance note does not change the correctness of D-DF's behavior here:
   whatever body text the production pipeline actually has access to
   carries no marker, so it must not be captured. Verified live against the
   shipped (pre-D-DF) module: this heading is captured SOLELY via
   `_rule_verb_extended`'s `for` alternation — `_rule_sec`, `_rule_mid`,
   `_rule_verb_bare`, `_rule_trunc`, `_rule_misspell`, and baseline
   `is_definitions_heading` are all `False` — so gating this one alternation
   cleanly isolates the fix with no interaction with any other rule.
3. **`STATE_AL_T43_C8_S43-8-230`** (`Section 43-8-230 Construction of
   Generic Terms to Accord with Relationships as Defined for Intestate
   Succession; When Person Born Out of Wedlock Treated as Child of
   Father`) — D-DF NEGATIVE (secondary). Body is a construction-of-terms
   RULE about how half-bloods/adoptees/children-born-out-of-wedlock are
   treated in class-gift terminology for intestate succession — it never
   itself defines any single quoted term. Same isolation property verified
   as row 2 (captured solely via the `for` alternation).
4. **`STATE_ID_T18_C58_S18-5817`** (`18-5817 "ABANDON" DEFINED AS LEAVING TO
   ATTRACT CHILDREN.`) — blast-radius guard: the sibling whitelist connector
   `as` must stay UNCONDITIONAL (D-DF touches `for` only). Body:
   `"Abandon" means leaving unattended and uninclosed such appliance...` —
   also usable as an additional real positive for the `defines_in_body`
   predicate itself (bonus, not required by D-DF).
5. **`USC_T15_C122_S9801`** (`Defined term`) — blast-radius guard: the
   sibling whitelist connector `term` must stay unconditional. Body:
   `In this title, the term "COVID–19 public health emergency"— (1) means
   the public health emergency first declared on January 31, 2020...` — the
   marker sits past a dash-then-numbered-subclause, a shape deliberately
   NOT pinned against `defines_in_body` either direction (see the test
   module's "known limits" note) — this row is used only to prove the
   `term` connector stays unconditional.
6. **`STATE_NJ_T58_C16A_S16A-102`** (`"Emergency supplies" defined,
   regional directory database.`) — blast-radius guard: the comma
   punctuation form must stay unconditional. Body: `As used in this section
   "emergency supplies" means, but is not limited to: ...`.
7. **`STATE_CT_T31_C567_S31-232l`** (`Sec. 31-232l. Ineligibility for
   extended benefits. Suitable work defined. Duties of State Employment
   Service.`) — blast-radius guard: the period punctuation form must stay
   unconditional. Body carries its `"suitable work" means ...` marker deep
   past an unrelated `(b)` cross-reference to a different section — proves
   `defines_in_body` must scan the full body text, not a short prefix.

Rows 4–7 also directly answer "must remain unconditional... in both
directions" for the connector words: `STATE_CO_T22_A33_P1_S22-33-106.3` and
`STATE_NV_T58_C706_S706.074` (already vendored in
`us_heading_variants_rows.json` above) supply the OTHER direction — real
rows already known to be captured unconditionally (R-TRUNC, R-VERB-bare)
whose bodies carry only a CROSS-REFERENCE marker (`has the same meaning as
that term is defined in section 19-2.5-102`, `has the meaning ascribed to
it in NRS 459.7024`) and no self-definition — proving the unconditional
rule fires without ever consulting `defines_in_body` at all, in contrast to
the gated `defined for` rule which would (correctly) refuse both.

Colon and dash punctuation forms are not independently re-vendored here:
D-DF touches only the `for` word alternation, not the punctuation/dash
branches of `_VERB_EXTENDED_RE` at all, and both are already covered by
pre-existing regression evidence (BUG2/cycle-2, see the module's own
docstring) — mechanically unaffected by this change.

## Cycle-5 fixtures (sprint 2026-08-04-defs-us-headings, dev cycle 5)

Six new files, 42 REAL rows total (all 24 original parquet columns, values
unmodified), pulled 2026-08-04 from the same locally-cached corpus snapshot
(`301000fc3465374ee0f23c3c6953a8a861e95cad`) via a disposable script outside
`backend/.venv` reading directly from
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc.../`
(never downloaded by a committed test, ruling R6). Every row's provenance is
the manager's own measured gap-class evidence
(`.../scratchpad/headings_mgr3_gap_rows.json`,
`.../scratchpad/headings_mgr3_class5_evidence.json`, both handed to this
Planner by exact path, P-R9), not re-discovered independently. **Byte-identity
verified for all 42 rows across all 24 columns** by an INDEPENDENT re-read
(`scratchpad/plan5_verify_byte_identity.py`, a fresh `pyarrow.read_table` call
per row, never reusing the builder script's in-memory state) — zero mismatches.

### `cycle5_defined_and_rows.json` — item 10, R-VERB-extended `and` connector (6 rows)

Manager-measured population: 45 rows / 19 states. Six representative rows,
one per state, chosen from the manager's own "hand-verified genuine" list:
`STATE_MI_C440_AAct-174-of-1962_S440.4952` (`"Creditor process" defined and
explained.`, body literally `As used in this section, "creditor process"
means levy, attachment, garnishment...`), `STATE_IA_TXVI_C701_S701.7`
(`Felony defined and classified.`), `STATE_KS_C79_A11_S79-1130`, `STATE_ND_
T29_C29-17_S29-17-33`, `STATE_NV_Tpreliminary-chapter_C0_S0.040` (`
"Physician" defined and limited`, body `"physician" means a person who
engages in the practice of medicine...`), and `STATE_LA_Crevised-statutes_
T38_S3009` — the Louisiana templated `"pollution defined and prohibited"`
shape (ledger L4) whose body genuinely never mentions "pollution" (verified:
0 occurrences in the 3,598-char body), vendored specifically to prove H-R1's
"capture the heading regardless of body yield" requirement with a real,
body-empty row, not a synthetic one.

### `cycle5_mojibake_rows.json` — item 11, RI mojibake dash/quote normalization (4 rows)

Manager-measured population: 10 genuine rows, all Rhode Island. Three
positive rows (`STATE_RI_T24_C24-8_S24-8-27`, `STATE_RI_T44_C44-18_
S44-18-15.2`, `STATE_RI_T5_C5-11_S5-11-1.1` — the last one also exercising
the mojibake `and`-joined multi-term-list shape, `"Hawkers," "peddlers,"
and "door-to-door salespersons" defined`) plus the REQUIRED negative guard
`STATE_RI_T34_C34-11_S34-11-37` (`Indefinite references to "trustee".`,
same mojibake bytes, `defin` substring from "Indefinite" — ledger L6). All
four carry the real `\x80\x94`/`\x80\x9c`/`\x80\x9d` CP1252-artifact byte
sequences verbatim (confirmed via `repr()` on the loaded JSON string, not
just visual inspection — JSON round-trips these bytes as literal ``-
range codepoints, preserved exactly).

### `cycle5_pointer_table_rows.json` — item 12, D-MT-E1 pointer-table headings (9 rows)

The manager's full population (9 rows / 7 states — CO, CT, IA, ME, OK, SC
x3, WY — exceeding QA cycle 3's own 7-row/6-state count by finding
`STATE_OK_T14A_S14A-1-303` and `STATE_WY_T40_C14_S40-14-142`, both
independently confirmed genuine pointer tables by this Planner from their
real body text). Vendored in full (not a sample) because the class is small
and every member is directly asserted in
`test_definition_links_us_heading_variants_cycle5.py`.

### `cycle5_defined_qualifier_rows.json` — item 13, `defined (qualifier)` / `defined to [verb]` (7 rows)

The manager's full population (KY 1, MO 4, PA 1 repealed, VA 1 — the
judgment-call row). Vendored in full; every row is directly asserted. The
VA row's FULL 758-char body (`STATE_VA_T8.01_C14_A4_S8.01-397.1`) is what
the judgment call in the test module's own docstring is based on — fetched
independently of, and materially different from, the manager's 400-char
`body_head` evidence snippet, which cuts off exactly before subsection B's
decisive "Habit and routine practice defined. A "habit" is a person's
regular response..." sentence.

### `cycle5_class5_connector_rows.json` — item 15, manager course-correction (11 rows)

Delivered mid-cycle after the manager independently classified the FULL
1,224-row U4 residual (not a sample) and found a fifth capture class the
original four items didn't cover. Six positive rows (the `further`/`when`/
`in case of` word-connector shapes and the trailing-digit/bracket scrape-
artifact shape, one per manager-cited candidate act_id that this Planner's
measured, corpus-wide-precision-checked design actually captures — see the
test module's own docstring for the full recall/precision numbers and why
a broader "inversion" design was measured and rejected) plus five negative
guards, one per named excluded shape (`STATE_IN_T27_A1_C50_S27-1-50-2`
adjectival jargon, `STATE_AK_T11_C11.81_S11.81.220` all-offenses-by-statute,
`STATE_FL_TXLVI_C800_S800.05` as-defined-in-elsewhere cross-reference,
`STATE_WA_T43_C41_S109` + `STATE_ND_T1_C1-01_S1-01-09` defined-by-rule/
by-statute delegation).

### `cycle5_u2_scope_rows.json` — item 14, U2 scope-expressibility (5 rows)

`STATE_AK_T13_C13.06_S13.06.050` (the chapter-range worked example, already
vendored for heading-recognition purposes in `us_heading_variants_rows.json`
row 5 — re-vendored here as its own standalone file so the scope-focused
test files don't need to reach into a differently-themed fixture) plus all
4 of the U2 ledger's KY rows (`STATE_KY_TIII_C17_S17.185`, `STATE_KY_TXIII_
C156_S156.106`, `STATE_KY_TXI_C139_S139.486`, `STATE_KY_TXXI_C246_
S246.420`) — only one of the four (156.106) declares an ENUMERATED scope
("...for this section and KRS 161.605..."); the other three declare a
plain single-article local scope ("...Definitions for section."), vendored
together so `test_definition_links_us_heading_variants_cycle5_scope_parse.py`
can assert the DISTINCTION between "no additional scope member" (empty
tuple) and "not this heading shape at all" (`None`) using real, contrasting
rows rather than a single cherry-picked example. The other 5 of the 10 U2
act_ids (CT, NJ, TN, UT, VA) are NOT vendored here — no test in this cycle
references them; their real body text (fetched and read by this Planner
for the per-row U2 verdict in the report to the manager) lives in
`scratchpad/plan5_item14_u2_rows_full.json`, not as a committed fixture,
since nothing in this codebase's test suite exercises it.
