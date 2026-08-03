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
## `pr_sample_rows.json` — Puerto Rico Spanish-language fixtures (sprint
2026-08-04-defs-us-pr, Planner, 2026-08-04)

10 REAL rows (full original columns, values unmodified) pulled from
`us_pr_statutes.parquet` (HF snapshot
`datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`,
23,636 rows, never downloaded by any test — read once by the Planner via a
disposable scratch script outside `backend/.venv`, same discipline as R6).
Picked from a full-corpus survey (every row scanned, not a sample) to cover
every entry-marker/idiom shape measured — see the sprint contract's
`## Spanish idiom survey (measured)` section and this sprint's log for the
full counts. One row per shape:

1. **`STATE_PR_LEY_249_2003_ART3`** — bare canonical heading (`"Artículo 3.
   Definiciones"`). Body: 9 entries, letter-period markers (`a.` .. `i.`),
   curly-quoted terms, colon separator (`“Término”: definición`). The
   dominant canonical shape (`letter-period` marker family, `quote+colon`
   separator family).
2. **`STATE_PR_LEY_63_2023_ART3`** — compound/truncated heading (`section_
   title` runs on past "Definiciones" into the body's own opening prose —
   see item 8's note below for why; here it merely runs into the section's
   own scope-setting sentence, not into an entry). 6 entries, `(a)`..`(f)`
   full-paren markers, UNQUOTED terms + em-dash + verb idiom (`Es`/
   `Significará`/`Será`) — no colon, no quotes at all.
3. **`STATE_PR_LEY_77_1957_ART30_020`** — heading `"Artículo 30.020.
   Definiciones:"` (trailing colon variant). Body opens `"A los fines de
   este Capítulo, ..."` — the CHAPTER-scope trigger phrase, the only one of
   these 10 rows with non-law-wide section scope. 9 entries, `(a)`..`(i)`
   full-paren markers, quoted terms + colon + `Significa`/`Es`.
4. **`STATE_PR_LEY_77_1957_ART1_090`** — heading `"Secretario, definición"`
   (singular, semicolon/comma-joined single-term Civil-Code-style variant).
   Body is a SINGLE entry with NO list marker at all: `"Secretario. —
   Significa el Secretario de Hacienda."` — 27.4% of all canonical rows
   (174/635) have no genuine multi-entry marker; this is the minimal real
   example of that shape.
5. **`STATE_PR_LEY_85_2018_ART9_04`** — heading `"Posesión de Armas y
   Sustancias Controladas en las Escuelas"` (NOT a Definiciones heading —
   `is_definitions_heading` must return `False`). Body contains an AD-HOC,
   article-scoped definition embedded in an ordinary substantive article:
   `'A los fines de este Artículo "cualquier tipo de arma" incluye
   todas las armas...'` — the Spanish analog of Hebrew's `extract_local_
   definitions` (`לענין זה, "X" - ...`), scope="local". Director-mandated
   "definitions outside the canonical placement" case (P2), and the P3
   article-scope proof case.
6. **`STATE_PR_LEY_160_2013_ART5_4`** — heading `"...Programa de
   Aportaciones Definidas"` ("Defined Contributions Program" — a pension-
   law term of art). FALSE-POSITIVE GUARD: contains the `defini*` substring
   but is NOT a definitions heading (`is_definitions_heading` must return
   `False`). 12/635 `defini*`-containing headings corpus-wide share this
   `Aportaciones Definidas` stem — a naive substring check would wrongly
   flag every one.
7. **`STATE_PR_LEY_165_2020_ART1_2`** — heading is a Table-of-Contents
   listing (`"Tabla de Contenido ... Artículo 1.4 Definiciones Ar[tículo
   1.5...]"`, truncated) that happens to mention "Definiciones" as one item
   in a TOC, not as this article's own subject. FALSE-POSITIVE GUARD:
   `is_definitions_heading` must return `False` (neither first-word nor
   last-word position — see item 8).
8. **`STATE_PR_LEY_135_1979_ART1`** — a REAL, NOT-INJECTED data-quality
   artifact (this dataset's PR analog of the DE mojibake / PA collision
   findings above): `section_title` and `text` are split at a fixed
   ~200-character boundary that lands MID-WORD — the heading ends
   `"...Estado Libre Asoc"` and `text` resumes `"iado de Puerto Rico..."`
   (one word, "Asociado", torn in half across the two columns). Verified
   9/635 canonical rows (1.4%) have a `section_title` > 120 chars from this
   exact artifact. Consequence: entry (a) ("Oficina") is defined entirely
   inside the truncated `section_title` overflow and is **absent from
   `text`** — no regex over `text` alone can recover it; this is a genuine
   corpus-quality limitation, not a code defect (same category as the PA
   collision/CA quote-mismatch findings above), flagged for QA. Despite the
   garbage tail, `is_definitions_heading` MUST still return `True` for this
   heading (via a first-word-position rule: "Definiciones" is the first
   token after the "Artículo 1." prefix, even though the string keeps
   running past it) — proving the heading rule needs first-word-anchored
   matching, not last-word-only. Body (from `text`, entries b-e only):
   letter-close-paren-only markers (`b)`, `c)`, `d)`, `e)`), quoted terms +
   colon + `significará`.
9. **`STATE_PR_LEY_15_2024_ART3`** — bare canonical heading. Body: 6
   entries, `a)`..`f)` letter-CLOSE-PAREN-ONLY markers (no opening paren —
   this newer-law convention appears in 82/635 canonical rows), UNQUOTED
   terms + period + em-dash, no verb idiom needed (definition text starts
   directly with a noun phrase, e.g. `"Composta. — Proceso de
   descomposición..."`).
10. **`STATE_PR_LEY_70_1997_ART1`** — heading `"Comité de Acción para la
    Prevención de la Mortalidad Infantil"` (NOT a Definiciones heading).
    Body contains `"(en adelante, Comité)"` — the Spanish inline apposition
    family (`en adelante`, "hereinafter"), 49 corpus-wide occurrences,
    mechanically distinct from the `A los fines de` ad-hoc family (item 5):
    no idiom verb, no quoted term — just a parenthetical restating the
    immediately-preceding noun phrase as its own short name. Spanish analog
    of Hebrew's `extract_adhoc_definitions` (`(להלן - X)`), scope="local".

Provenance: same dataset/commit as the US-state rows above
(`vaquill/open-us-law`, CC-BY-4.0, underlying text public domain), fetched
2026-08-04 via a disposable scratch script (`pyarrow` is present in THIS
sprint's own worktree venv — `backend/.venv/bin/pip list` shows
`pyarrow==25.0.0` already installed, unlike the 2026-08-02 sprint's venv —
so no separate scratch venv was needed this time; the parquet file itself
was still never read by anything under `backend/tests`).

## `pr_sample_rows_cycle2.json` — cycle-2 miss-workload fixtures (sprint
2026-08-04-defs-us-pr, Planner, cycle 2, 2026-08-04)

24 REAL rows (full original columns, values unmodified), all pulled from
the SAME `us_pr_statutes.parquet` snapshot as `pr_sample_rows.json` above
(`301000fc3465374ee0f23c3c6953a8a861e95cad`), byte-compared against the
live on-disk parquet after writing (script output: `ALL BYTE-IDENTICAL`).
A SIBLING file to `pr_sample_rows.json`, not a merge into it, per the
manager's cycle-2 brief — cycle 1's fixture rows and their tests are
untouched.

**Why these rows exist.** Cycle 1's 5-fixture extraction suite and 9-
fixture heading suite all passed, yet the manager's full-corpus sweep found
56.4% real extraction coverage and 15/635 real heading misses (`docs/
sprint/sprints/2026-08-04-defs-us-pr-log.md`, "Manager: Developer
verification + GENERALIZATION GAP"). Every row below was picked from the
manager's own measured miss workload
(`scratchpad/pr_miss_workload.json`, buckets A/B/C and the 13 real heading
misses — bucket D is explicitly OUT of scope, per ruling M-R6) to pin one
independently-diagnosed root cause each. Full root-cause diagnosis lives in
each test file's module docstring
(`backend/tests/unit/test_pr_profile_extraction_cycle2.py`,
`test_pr_profile_headings_cycle2.py`) and in the sprint log's cycle-2
Planner entry — this section is the provenance/inventory, not the
diagnosis.

**Extraction rows** (bucket A — extractor separator-pattern gaps; bucket C
re-diagnosis; bucket B — settled):

1. `STATE_PR_LEY_77_1957_ART39_050` — A1: curly-quoted term directly
   followed by `significa`, no separator character at all (14 top-level
   entries, one with a nested `(a)`–`(g)` sub-list).
2. `STATE_PR_LEY_73_2003_ART2` — A1: same shape, STRAIGHT quotes (proves
   the fix is not curly-quote-specific).
3. `STATE_PR_LEY_189_1996_ART2` — A2: quoted term + ASCII hyphen-minus `-`
   (not a typographic em/en dash) + idiom.
4. `STATE_PR_LEY_214_1995_ART2` — A3: quoted term, no separator, NO idiom
   verb either — a bare capitalized noun-phrase definition.
5. `STATE_PR_LEY_33_2017_ART3` — A4: unquoted term + colon (no
   `_UNQUOTED_TERM_COLON_RE` exists in `pr_profile.py` today).
6. `STATE_PR_LEY_39_1988_ART2` — A1, minimal (3-entry) confirmatory row.
7. `STATE_PR_LEY_493_1952_ART1` — A1 confirmatory row.
8. `STATE_PR_LEY_318_1999_ART2` — A1 confirmatory row.
9. `STATE_PR_LEY_167_1988_ART2` — A1-variant: quoted term + COMMA + idiom.
10. `STATE_PR_LEY_60_1988_ART1` — A1-variant: quoted term + comma + idiom,
    with an alternate-term "o" construct in entry (a).
11. `STATE_PR_LEY_66_1975_ART3` — A6: unquoted term + its OWN trailing
    period (not colon, not dash) + bare definition.
12. `STATE_PR_AMBIENTAL_ART51` — A6 confirmatory row, digit-period marker
    family.
13. `STATE_PR_LEY_190_1995_ART2` — A5 (bucket-C re-diagnosis): marker
    followed by a decorative em-dash, THEN the quoted term
    (`a. — "Nueva programación" significa...`). `_ENTRY_MARKER_RE` already
    matches this row's `a.`–`k.` markers correctly (live-verified) — this
    is a block-prefix gap, not a marker-inventory gap.
14. `STATE_PR_LEY_199_2015_ART2` — bucket B, settled: unquoted + colon
    (A4-class), several entries use lowercase `es`/no canonical survey
    idiom at all — the marker list itself establishes definitional
    context (M-R6).
15. `STATE_PR_LEY_46_2008_ART3` — bucket B, settled: unquoted + colon
    (A4-class) PLUS a genuinely NEW, distinct marker-inventory finding:
    traditional Spanish alphabetical enumeration treats "ch" as its own
    letter, producing a real two-character marker `ch)` that
    `_ENTRY_MARKER_RE`'s single-character-class alternatives never match
    (confirmed live: only 6/7 real markers found, `ch)` silently
    swallowed into entry `c)`'s block).
16. `STATE_PR_LEY_51_2003_ART2` — bucket B, settled: A6 (unquoted term +
    trailing period) PLUS an independent, previously-undiscovered defect:
    `_ENTRY_MARKER_RE` misfires on the spaced abbreviation `"U. S.
    Geological Survey"` inside entry bodies (`S.` alone matches the
    letter-period marker alternative), fragmenting entry 1's
    `definition_text` mid-sentence even once the A6 separator gap is
    fixed.
17. `STATE_PR_LEY_77_1957_ART9_040` — bucket B, settled: a no-top-level-
    marker single-entry Civil-Code-style article (`"Agente General es la
    persona nombrada..."`) whose body ALSO contains an incidental `(1)`–
    `(11)` sub-list of the SAME term's own duties. Today's all-or-nothing
    marker dispatch takes the markers path because `(1)`–`(11)` exist
    somewhere in the text, silently discarding the term/lead-in text
    before the first marker and fragmenting the body into 11 bogus
    entries instead of the correct single one.
18. `STATE_PR_LEY_52_2019_ART3` — a CORRECT-ZERO guard, not a miss: the
    entire body defers wholesale to another law's definitions
    (`"...se entenderán de aplicación las definiciones de la Ley Núm. 228
    ..."`) and defines zero local terms. Must continue to yield zero
    candidates.

**Heading rows** (the 13 real heading misses, gap re-diagnosed as clause-
scoped first-word matching plus a separate parenthesis-stripping need — see
`test_pr_profile_headings_cycle2.py`'s module docstring for the full
per-family breakdown):

19. `STATE_PR_CIVIL_ART365` — Civil-Code semicolon-compound family
    (`"Parentesco; definición y alcance"`). 6 more real headings of this
    same family (verbatim `section_title` strings, verified live against
    the corpus) are pinned as bare-string `parametrize` cases in the test
    file rather than re-vendored as full fixture rows.
20. `STATE_PR_LEY_77_1964_ART1` — parenthesized whole heading
    (`"(Definiciones)"`). The second real corpus row sharing this exact
    shape, `STATE_PR_LEY_60_1963_ART100` (a 3,470-word row, not worth
    vendoring in full for a heading-only check), is pinned as a bare
    heading string instead.
21. `STATE_PR_LEY_15_1931_SEC22` — trailing-preposition family
    (`"Obrero o empleado, definición de"`).
22. `STATE_PR_MUNICIPAL_ART7_212` — em-dash compound family
    (`"Tasación y Cobro de Deficiencia —Definición de Términos"`).
23. `STATE_PR_LEY_77_1957_ART15_020` — comma-delimited mid-token compound,
    same family as #19 but a different delimiter and a different real law
    (`"Microseguros, definición y clases autorizadas"`).
24. `STATE_PR_LEY_51_2020_ART1_2` — the SECOND real Table-of-Contents
    false-positive guard (cycle 1 only vendored the first,
    `STATE_PR_LEY_165_2020_ART1_2`). Both must stay rejected after the
    heading-rule widening — this is the row M-R6 explicitly named as the
    widening's own regression risk.

Provenance: same dataset/commit/license as `pr_sample_rows.json` above,
fetched 2026-08-04 by the Planner via a disposable scratch script
(`/private/tmp/.../scratchpad/diagnose_bucket_a.py` and siblings — outside
`backend/.venv`, never committed), reading directly from the already-cached
HF snapshot on disk (`~/.cache/huggingface/hub/datasets--vaquill--open-us-
law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/us_pr_statutes.
parquet`) — no network download performed this cycle, the snapshot was
already local from cycle 1. Every row's fields were verified byte-identical
against a fresh `pyarrow.parquet.read_table` of that same file immediately
before committing.
