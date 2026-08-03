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
