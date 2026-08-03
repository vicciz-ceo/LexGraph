# Definitions-Completeness Program — Merged Recon Dossier

## 1. Code map + scope-semantics verdicts

**Profile registry & dispatch**
- `backend/app/definition_links/profiles.py:53-76` — `JurisdictionProfile` Protocol.
- `profiles.py:79-116` — `HebrewProfile` (code="IL"), thin wrapper; `find_citations` trivially `[]` (:108-111).
- `backend/app/definition_links/us_profile.py:509-546` — `USProfile` dataclass, one instance per US-* code.
- `profiles.py:125-128` — `_REGISTRY = {"IL": HebrewProfile()} + {code: USProfile(code) for code in JURISDICTION_CODES}`.
- `profiles.py:131-141` — `get_profile(code)` raises `ValueError` on unknown code, no silent fallback.
- `pipeline.py:361-367` — `_profile_for_document` resolves+caches profile per document; Stage 2 (pipeline.py:387-442) and Stage 3/4 dispatch through `profile.*`.

**Deviation — non-profile-owned logic lives inline in pipeline.py**
- `_derive_heading_from_body` (pipeline.py:177-213) + `_BARE_SECTION_LABEL_RE`/`_BARE_CITATION_LABEL_RE` (:106-109), `_LEADING_PARENTHETICAL_RE` (:141), `_BODY_EMBEDDED_HEADING_RE` (:149-152), `_BODY_DEFINITIONS_PREAMBLE_RE` (:171-…) — called pipeline.py:411-414.
- `_extract_inline_quoted_definitions` (pipeline.py:246-289, regexes :227, :240-243) — fallback called pipeline.py:429-432, only when `used_body_derived_heading` (:405/:429) and `profile.code != "IL"` (:408).

**SCOPE semantics — critical finding**
- Determination: `_determine_scope(body_text)` (pipeline.py:304-308) checks first non-blank line against `_CHAPTER_SCOPE_TRIGGERS` (pipeline.py:62-68, **Hebrew-only phrases**, e.g. `לענין פרק זה`, `בפרק זה`) → `"chapter"` or `"law-wide"`. Called once, pipeline.py:417, for both IL and US profiles.
- Persisted: `Definition.scope` (`backend/app/models/definition.py:35`, `String(32)`), set from `candidate.scope` at row creation (pipeline.py:469).
- Enforcement: `matcher._in_scope` (`backend/app/definition_links/matcher.py:104-110`) — `"chapter"` → same-chapter only, `"local"` → same-article only, else (incl. `"law-wide"`) → unrestricted. Called from `link_articles_to_definitions` (matcher.py:142).
- **Verdict IL**: respected — `"chapter"`/`"local"` scopes are producible (via `_determine_scope` + `extract_local_definitions`/`extract_adhoc_definitions`, extract.py:196/216) and enforced.
- **Verdict US**: architecturally present but **structurally unreachable** — `_CHAPTER_SCOPE_TRIGGERS` and `extract.py`'s `_LOCAL_TRIGGER_RE`/`_ADHOC_RE` (extract.py:28-33) are Hebrew-only regex literals; no English trigger exists. Every US `Definition` row is therefore `"law-wide"`, and Stage 3 places zero scope restriction on any US `USES_DEFINITION` edge. `_in_scope` would enforce chapter/local scoping for US rows if any existed — none are ever produced. This is confirmed independently by Report 2/3's live measurements: every state's "scoped inline" convention (`As used in this section…`) is dropped entirely, not mis-scoped.

**Extraction entry points**
- IL: `extract_local_definitions` (extract.py:183-199, trigger `_LOCAL_TRIGGER_RE` :28-30, always `scope="local"`); `extract_adhoc_definitions` (extract.py:202-218, trigger `_ADHOC_RE` :33, always `scope="local"`); Definitions-section path via `HebrewProfile.extract_definitions_from_section` → extract.py:168-180 → `_parse_block`.
- US: Definitions-section splitter `us_profile.py:361-…` (`"(N)"`-block); fallback `_extract_inline_quoted_definitions` (pipeline.py:246-289) only fires when the US splitter returns 0 candidates AND heading was body-derived; records whatever `_determine_scope` returned (always `"law-wide"` for US text).

**Plug-in points for a new jurisdiction**
- Heading regex: IL `sections._DEFINITIONS_HEADING_RE` (sections.py:33-56); US `us_profile._SECTION_LABEL_RE`/`_FIRST_WORD_DEFINITIONS_RE`/`_LAST_WORD_DEFINITIONS_RE` (us_profile.py:118-130).
- Body-preamble/placeholder-heading detection: pipeline.py-owned, NOT profile-dispatched (pipeline.py:106-126, 141-213) — a new jurisdiction with this problem must edit pipeline.py directly.
- Entry splitter: IL `extract._split_into_blocks`/`_ENTRY_START_RE` (extract.py:19,99-113); US `us_profile._split_into_numbered_blocks`/`_MARKER_TOKEN_RE`/`_BARE_DIGIT_MARKER_RE` (us_profile.py:304-358); pipeline fallback `_QUOTE_TERM_RE`/`_MEANS_IDIOM_GAP_RE` (pipeline.py:227,240-243).
- **Scope-phrase lists — biggest structural gap**: `_CHAPTER_SCOPE_TRIGGERS` (pipeline.py:62-68) and `extract._LOCAL_TRIGGER_RE`/`_ADHOC_RE` (extract.py:28-33) are Hebrew-only and NOT profile-dispatched. Any new jurisdiction needing chapter/local scoping must add its own trigger lists here, or its definitions stay permanently `"law-wide"` — the same failure mode already confirmed for all 18+18 US states sampled.
- Citation grammar: `find_citations` Protocol method IS cleanly abstracted (profiles.py:72; IL profiles.py:108-111; US us_profile.py:409-437) — the one plug-in point that already works as designed.

---

## 2. US conventions — merged convention-family table

Reconciling Report 2 (AL–LA), Report 3 (ME–OK), and Report 4 (OR/PA/RI/SC/SD/TN/TX/UT/VT/VA/WA/WV/WI/WY/DC/PR/federal — **no findings delivered**, see §4/§5).

| Family | Description | States confirmed (capture rate / freq where given) | Captured today? |
|---|---|---|---|
| **Scoped-inline, no Definitions heading** (R2:F1, R3:(b) — same convention, same root cause) | `"As used in this section…"` / `"For purposes of this section…"` inside an ordinary substantive section; heading never matches `is_definitions_heading`, body never reached | AL(~40/400), FL(103/400), IA(53/400), AZ, HI, IN, KS, KY, CT, DE, CO (R2, freq 6-103/400); ME(39%), MO(33%), OH(47%, highest observed), NC, NM, NJ, MN, MI, MT, NV, NY, NH, MD, MS, NE, ND, MA, OK (R3, 11-47%) — **18/18 R3 states affected**, dominant miss class in both reports | **NO** — 0% everywhere tested; no English analog of Hebrew `extract_local_definitions` exists (confirms §1 scope-trigger gap) |
| **Body preamble present but literal word "Definitions" absent** (R2:F2 "GA-style" vs R3:(a) "worse than GA-style") | `_BODY_DEFINITIONS_PREAMBLE_RE` requires literal "Definitions"; GA says `"the term:"`, MD/NE never use the word at all, heading is a bare citation | GA (0/400, 173/400 preamble instances missed) (R2); MD (0/300, heading never carries "Definitions") and NE (0/300) (R3) — **R3 reports MD/NE as strictly worse than GA** since even the heading signal is absent | **NO** |
| **Heading found, entry-marker format mismatch** (R2:F3) | Heading correctly recognized as Definitions, but extractor's `(N)`/`(letter)`+quoted-term rule rejects the real marker shape (bare digit-dot, unquoted ALL-CAPS, mojibake curly quotes, unnumbered continuous run) | AL (unquoted caps), AZ (bare digit-dot), AK (cp1252 mojibake quotes), IL (0/400 despite heading found), AR (single non-list def) | **NO** on extraction despite heading capture — distinct sub-gap from the other two |
| **Heading-variant miss** (R3:(e) — not identified in R2's state range) | `_FIRST_WORD_DEFINITIONS_RE`/`_LAST_WORD_DEFINITIONS_RE` only match "Definitions" as literal first/last token; misses mid-token/compound headings | MO (`"Reciprocity — definitions — procedure — fees."`, 20/300), NV, NH (`"Definition of Terms."`), NY, MI | **NO** |
| **Multi-term shared-clause definitions ("TX-style")** (R3:(d); R2:F5 is a related-but-distinct compact-document variant) | `The term(s) "X", "Y", and "Z" mean(s)…` — one clause covers several terms; splitter assumes one term/entry | MT(7/300), MI(4/300), NH(2/300), ND(4/300), NY(4/300), OK(3/300); R2's AR compact-document case (F5) is a different mechanism (heading gate rejects a reproduced interstate-compact body) but the internal shape is the same `(N) "Term" means` pattern | **NO** |
| **Inline parenthetical definitions** `("Term")` (R3:(c) only) | Apposition abbreviations, no means/shall-mean idiom follows → rejected even by inline fallback's idiom-gap check | MI, MT, NH, ND, NY, OK (~1-2/300 each) | **NO** |
| **Data-quality artifact, not a matcher gap** (R2:F6) | Duplicate verbatim entry in source row | GA `STATE_GA_T12_C3_S12-3-231` | N/A — corpus issue |
| **Working baseline (contrast)** (R2:F4, R3 "working cases") | Heading literally is/ends "Definitions" AND body is `(N)`/`(letter) "Term" means` blocks | R2: IN, CO, KY, LA, DE, ID. R3: NJ, MI, MT, ND, NY, OK — **regression-guard set for any fix** | YES |

**Aggregate capture rates measured**: R2 (AL-LA, n≤400/state): AL 6, AK 1, AZ 5, AR 133*(inflated by compact-doc coincidence), CA 18, CO 109, CT 54, DE 100, FL 45, **GA 0**, HI 2, ID 71, **IL 0**, IN 7, IA 75, KS 73, KY 115, LA 49.
R3 (ME-OK, n≈250-300/state): ME 22%, **MD 0%**, **MA 0%**, MI 28%, MN 20%, **MS 0%**, MO 17%, MT 27%, **NE 0%**, NV 2%, NH 16%, NJ 23%, NM 25%, NY 10%, NC 14%, ND 25%, OH 9%, OK 14%.

**Reconciled remediation priority** (merging R2's and R3's proposed groupings — same structure, same fix order in both):
1. Scoped-inline fix (English `extract_local_definitions` analog) — highest leverage, both reports agree, affects nearly every state sampled.
2. Preamble-trigger widening beyond literal "Definitions" — GA/MD/NE/MS priority (zero-heading-signal states).
3. Entry-marker splitter hardening (bare digit-dot, unquoted caps, mojibake, no-marker single-term).
4. Heading-variant regex loosening (mid-token "definitions").
5. Multi-term shared-clause splitting.
6. Inline-parenthetical/apposition handling (lowest volume).

---

## 3. IL corpus + conventions

**Corpus**: `/Users/nerya/AI for others/israeli-laws-wiki` — 6,133 laws, `data/laws/<title>.wiki` + `.meta.json`, 168M (`data/`), source he.wikisource.org, CC BY-SA, version-pinned. Format matches backend ingest: `@ N. heading`, `==chapter==`/`===siman===`, `:-` entry starts, `::` continuation, `[[wikilink]]`.

**Current IL machinery** (`backend/app/definition_links/{extract.py,sections.py,normalize.py,profiles.py}`):
- `is_definitions_heading`: `הגדרות|הגדרת מונחים|הגדרות ופירוש|הגדרה`.
- `extract_definitions_from_section`: splits on `:-`, handles multi-term/qualifier, `::` continuations, repeal markers, nested `לעניין הגדרה זו,` (`_NESTED_MARKER_RE`) — this nested case IS captured (verified live).
- `extract_local_definitions`: only `לענין זה,` / `בסעיף זה,` (extract.py:28-30).
- `extract_adhoc_definitions`: only `(להלן - X)` / `(להלן: X)` (extract.py:33).
- `normalize_for_parsing` collapses curly-quote/dash variance before extraction — quote style is NOT a gap.

**Missed today (confirmed live via `.venv/bin/python`)**:
- `בפרק זה` scoped quoted definitions (act_id example: חוק זכות מטפחים של זני צמחים art.15; חוק החברות הממשלתיות art.50א) — `extract_local_definitions` → `[]`. Corpus freq: `בפרק זה` 498 files, `בסימן זה` 200, `בחלק זה` 68, `לפרק זה` 46.
- `לענין סעיף זה` / `לעניין סעיף זה` (3-word variant vs. hardcoded 2-word `לענין זה`) — act_id example: חוק איסור הלבנת הון art.3 — `[]`. Combined freq ~589 files (331+258).
- Adhoc parenthetical scope markers `(בפרק זה - X)` / `(בסימן זה - X)` — act_id example: חוק רכבת תחתית (מטרו) art.13 — `extract_adhoc_definitions` → `[]` (only recognizes `להלן`).
- **Most severe — structural silent-loss**: חוק החברות הממשלתיות art.16, heading `הגדרה` correctly matched by `is_definitions_heading`, but body is prose (`בפרק זה, "X" - Y.`) with zero `:-` markers → `extract_definitions_from_section(body, scope='global')` → `[]`. Section is *found* but yields nothing; distinct from the `extract_local_definitions` gap since this body never reaches that function.

**Captured today (confirmed)**: repeal-marker suppression; nested `לעניין הגדרה זו` inside a `:-`-formatted entry (act_id examples: חוק איסור הלבנת הון art.1, חוק רכבת תחתית (מטרו) art.1 — 2-candidate extraction incl. `parent_term`, verified).

---

## 4. Contradictions between reports

1. **State-group boundary overlap/gap vs. Report 4's non-delivery.** Reports 2 and 3 jointly and rigorously cover AL–LA and ME–OK (36 states). Report 4 was assigned OR/PA/RI/SC/SD/TN/TX/UT/VT/VA/WA/WV/WI/WY/DC/PR/federal (17 jurisdictions) but delivered **no findings** — only a list of files consulted and a data-path confirmation. This is not a contradiction of fact between reports, but a **coverage gap**: 17 of ~55 US jurisdictions have zero convention-family data in this dossier. Flagged as escalation in §5.
2. **AR classification differs in framing between R2 (F3) and R2 itself (F5).** Not a cross-report contradiction (both are within Report 2) but worth noting for the merged table: AR appears twice — once as a marker-format miss (single non-list definition, F3) and once as a compact-document heading-gate miss (F5, inflated 133/400 capture count flagged by R2 itself as a misleading outlier). No other report contradicts this; retained as two distinct sub-findings in §2's merged table.
3. **No factual disagreement found between Report 1 (code map), Report 5 (IL), and Reports 2/3 (US)** on the core architectural claim — all four agree scope/local-definition triggers are Hebrew-regex-only and that this is the root cause of both the IL gaps (§3) and the systemic US "scoped-inline" miss (§2, family 1). This is convergent confirmation, not a contradiction.

No other contradictions identified.

---

## 5. Escalations raised by any agent (verbatim)

None of the five reports contains a line explicitly labeled "ESCALATION" or equivalent flagged-escalation marker. The following is the closest material requiring director attention, presented as-is from the source reports (not itself a verbatim "ESCALATION:" line since none exists):

- Report 4 delivered no convention-family findings for its assigned scope (OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY, DC, PR, federal) — only a "Files/functions consulted" list and confirmation that the parquet data is present locally. This leaves 17 US jurisdictions unassessed in this recon round.

---

## 6. B3 re-recon addendum (2026-08-04, workflow wf_7f1827d1-1a7) — the 17 jurisdictions the first pass left unassessed

=== B3a ===
ESCALATION: not needed — task completed successfully. Below is the full B3a deliverable.

```markdown
# B3a — Definition-introducing convention inventory: OR PA RI SC SD TN TX UT VT

Method: real code tested via `USProfile.is_definitions_heading` / `.normalize_for_parsing` /
`.extract_definitions_from_section` (backend/app/definition_links/us_profile.py, imported and
called live from backend/.venv). Data: HF snapshot cache
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law`, `us_<st>_statutes.parquet`. Per state:
regex-prefiltered candidate rows (keywords means/As used in/For purposes of/the term/`" means`/
shall mean/Definitions), then a random sample of 500 candidates run through the real functions.
`pipeline.py`'s inline fallback (`_extract_inline_quoted_definitions`, `_derive_heading_from_body`)
reviewed via CodeGraph but not separately re-run (its trigger condition — placeholder
`section_title` — never fires for these 9 states, all of which carry real `section_title` text).

Families found: F1 scoped-inline-no-heading, F2 body-preamble-lacking-word-"Definitions",
F3 heading-found-entry-marker-mismatch, F4 heading-variant-miss (compound/mid-token), F5
multi-term-shared-clause, F6 inline-parenthetical apposition. No NEW family beyond these 6 was
observed in any of the 9 states.

## OR (sample 500 of 14,511 candidates / 36,202 total rows)
- F1 (54, ~11%): `STATE_OR_T51_C659a_S659a.390` — `"(1) As used in this section:\n\n(a) "No-rehire provision" means..."` — heading is the plain section caption, no "Definitions" word. Captured today: NO (`is_definitions_heading` on that heading → False, extractor never invoked).
- F3 (7, ~1.4%): `STATE_OR_T19_C197a_S197a.348` — heading `"197A.348 Definition of "needed housing.""` — `is_definitions_heading` returns **True** (matches first/last-word rule loosely) but `extract_definitions_from_section` returns **0** candidates on the real normalized body (entries are prose, not the extractor's expected block markers). Captured today: NO (miss is silent — heading detected, body not parsed).
- F6 (1): `STATE_OR_T41_C496_S496.716` — `"(a) "Enforcement officer" has the meaning given that term in ORS 153.005 (Definitions)."` cross-reference-style inline quote. Captured today: NO.
- F2 (1): `STATE_OR_T29_C316_S316.302` — heading `"316.302 "Nonresident estate or trust" defined"`, body `"For purposes of this chapter, a "nonresident estate or trust" means..."`. Captured today: NO.

## PA (sample 500 of 2,730 / 14,547)
- F3 (63, ~12.6%, dominant miss): `STATE_PA_T42_C83_S8322`, heading `"Definition."` → `is_definitions_heading` True, body `'As used in this subchapter "joint tort-feasors" means...'`, extractor returns 0 (no `(N)`-style markers). Captured today: NO.
- F1 (15, 3%): `STATE_PA_T73_C43_S4355`, heading `"Nonprofit art corporations."` — no def-word in heading at all even though body defines terms. Captured today: NO.
- F4 (3): `STATE_PA_T16_C167_S16701`, heading `"Authority, definitions and application of chapter."` — mid-token, neither first nor last word → `is_definitions_heading` False. Captured today: NO.
- F2 (1): `STATE_PA_T3_C41_S4132`, `'The word "weight" as used in this subchapter... shall mean net weight.'`, heading `"Sale by net weight."`. Captured today: NO.

## RI (sample 500 of 3,013 / 21,107)
- F3 (75, 15%, dominant): `STATE_RI_T35_C35-13_S35-13-2`, heading `"§ 35-13-2. Definitions."` → detected True, but body's quote marks are **mojibake** (`\x80\x9c`/`\x80\x9d` — a mis-decoded curly-quote byte sequence), so the extractor's quote-based entry parser finds 0 terms. This is the "mojibake quotes" sub-case of family 3 explicitly called out in the brief. Captured today: NO.
- F2 (11, 2.2%): `STATE_RI_T5_C5-29_S5-29-16`, `'The term \x80\x9cunprofessional conduct\x80\x9d as used in this chapter includes...'`, heading `"§ 5-29-16. Unprofessional conduct."` (no "Definitions" word). Captured today: NO.
- F1 (23, 4.6%): `STATE_RI_T31_C31-25_S31-25-27.10`, `"For purposes of this section, a commercial vehicle is defined as..."`, heading is a road-name caption. Captured today: NO.
- F4 (4): `STATE_RI_T23_C23-19_S23-19-13.4`, heading `"§ 23-19-13.4. Host community assessment committee — Definit[ions]"` — em-dash-joined compound heading; "Definitions" is the trailing clause after a dash, likely truncated/mid-token depending on exact form. Captured today: NO (borderline — needs confirmation on full untruncated heading, but the sampled instance did not match).

## SC (sample 500 of 5,219 / 29,947)
- F3 (96, 19.2%, dominant): `STATE_SC_T5_C1_S5-1-20`, heading `"SECTION 5-1-20. Definitions."` detected True; body `'As used in Chapters 1 through 17...: (1) "Municipality" means...'` — bare `(1)`/`(2)` numeric markers with no letter suffix, real extractor's block splitter returns 0 (format mismatch: bare-digit-paren markers, not the expected form). Captured today: NO.
- F1 (20, 4%): `STATE_SC_T11_C44_S11-44-65`, `'(A) For purposes of this section: (1) "Angel investor taxpayer" means...'`, heading is the tax-credit section caption. Captured today: NO.
- F4 (4): `STATE_SC_T57_C5_A5_S57-5-880`, heading `"SECTION 57-5-880. Transportation improvement projects; defin[itions]"` — semicolon-joined compound, "definitions" lowercase mid/trailing token. Captured today: NO.
- F2 (7): `STATE_SC_T43_C33_A7_S43-33-560`, `'"handicap" and "handicapped" as used in this article mean...'`, heading names the terms, not "Definitions". Captured today: NO.
- F5 (4): `STATE_SC_T1_C11_A1_S1-11-400` — sampled hit was a false-positive trigger of the regex heuristic (references "terms of Nelson v. Leeke", not a definitions clause); no genuine F5 instance surfaced in this SC sample. Reported as observed-but-unconfirmed.

## SD (sample 500 of 3,984 / 39,589)
- F2 (17, 3.4%, dominant miss type here): `STATE_SD_T10_C45_S10-45-94.1`, heading `"Direct mail defined"`, body `'For the purposes of this chapter, the term, direct mail, means...'`. Captured today: NO.
- F1 (12, 2.4%): unrelated-caption headings with `"As used in this section"` bodies (e.g. `STATE_SD_T34_C45_S34-45-4.2` — actually a false-positive keyword hit, no real definition; genuine F1 instances exist elsewhere in the sample at lower confidence). Captured today: NO.
- F5 (1): `STATE_SD_T3_C14_S3-14-5`, heading `"Definitions"`, body `'The terms "office," "officer," "executive," and "administrative,"... mean...'` — a genuine multi-term shared-clause under a proper heading; `is_definitions_heading` is True here, but whether the extractor correctly splits the 4-term shared clause was not separately isolated (extraction count not confirmed >0 for this exact row in the raw dump). Flag for follow-up.
- F4 (3): `STATE_SD_T49_C32_S49-32-10`, heading `"Overhead high voltage line safety--Definition of terms"` — dash-joined compound, mid-token. Captured today: NO.
- F3 (7, 1.4%): lower frequency than PA/RI/SC/UT — SD's real `"Definitions"` headings more often DO use letter+digit markers the extractor expects.

## TN (sample 500 of 6,414 / 32,693)
- F1 (49, 9.8%, dominant): `STATE_TN_T69_C9_S69-9-227`, heading is the section caption, body `'(a) As used in this section: (1) "In the aggregate" means...'`. Captured today: NO.
- F2 (4): `STATE_TN_T49_C6_S49-6-104`, `'(a) As used in this part, "at-risk children" means...'`, heading is a program-name caption. Captured today: NO.
- F4 (6): `STATE_TN_T38_C8_S38-8-134`, heading `"Section definitions - Development of drone policy..."` — dash-joined compound, "definitions" not first/last word. Captured today: NO.
- F3 (2): `STATE_TN_T50_C2_S50-2-115`, heading `"Chapter definitions"` (lowercase-first-word form) → matched True, body `'As used in this chapter, "work": (1) Has the same meaning...'` — extractor returns 0 for this colon-then-list shape.

## TX (sample 500 of 16,866 / 122,535)
- F3 (25, 5%): `STATE_TX_Cfi_C37_S37.001`, heading `"§ 37.001. DEFINITION."` (ALL CAPS, singular) → True, body `'In this chapter, "emergency" means...'` (single inline entry, no block markers) → extractor returns 0. Captured today: NO.
- F1 (11, 2.2%): `STATE_TX_Coc_C702_S702.252`, `"(b) For purposes of..."`, ordinary section caption heading. Captured today: NO.
- F4 (1): `STATE_TX_Cfa_C101_S101.001`, heading `"§ 101.001. APPLICABILITY OF DEFINITIONS."` — "DEFINITIONS" is last word but preceded by "APPLICABILITY OF", i.e. **last-word match should succeed** per `_LAST_WORD_DEFINITIONS_RE`'s anchoring (`^Definitions?$` — actually this is a multi-word heading so the *last-word* rule requires the ENTIRE heading to equal "Definitions", which it does not); only `_FIRST_WORD_DEFINITIONS_RE` (heading starts with the word) would need to fire, and it doesn't since heading starts with "APPLICABILITY". Confirmed miss. Captured today: NO.
- F2 (1): `STATE_TX_Cgv_C411_S411.0252` — sampled hit is a false-positive keyword match (offenses list, not a definitions clause).

## UT (sample 500 of 6,995 / 25,880) — highest miss volume of the 9
- F1 (173, 34.6%, by far the dominant miss in this state): `STATE_UT_T10_S10_1_410`, heading is a plain section caption, body `'(1) For purposes of this section, "nontelecommunications services" means...'`. Utah's statutory drafting style very heavily favors scoped-inline "For purposes of this section" clauses without a "Definitions" heading. Captured today: NO.
- F3 (121, 24.2%, also very high): `STATE_UT_T75B_S75B_1_301`, heading `"§ 75B-1-301. Definitions for part."` → True, body `'As used in this part: (1) "Asset protection trust" means: (a) that is irrevocable...'` — nested lettered sub-clauses under numbered top-level entries; extractor returns 0 on this nesting shape. Captured today: NO.
- F2 (2): `STATE_UT_T20A_S20A_11_104`, `'(1)(a) As used in this chapter, "personal use expenditure" means...'`. Captured today: NO.
- F4 (1): `STATE_UT_T59_S59_12_1401`, heading `"§ 59-12-1401. Purpose statement -- Definitions -- Scope of part"` — dash-joined 3-part compound, mid-token. Captured today: NO.

## VT (sample 500 of 4,376 / 23,521)
- F1 (43, 8.6%, dominant): `STATE_VT_T23_C13_S1006c`, heading is a section caption (`"§ 1006c. Chain requirements..."`), body `'(a) As used in this section, "chains" means link chains...'`. Captured today: NO.
- F3 (8, 1.6%): `STATE_VT_T23_C35_S3700`, heading `"§ 3700. Definition; mail"` → True (first word "Definition"), body is a single-sentence multi-term shared clause (`'"mail," "mails," "mailing," and "mailed" mean...'`) with no block markers → extractor returns 0. This row is simultaneously an F5 (multi-term shared clause) and F3 (extractor 0-yield) case.
- F2 (3): sampled, lower volume than other states; no strong single example beyond generic `"For purposes of this title..."` clauses under non-"Definitions" captions.
- No F4 or F6 hits surfaced in this VT sample of 500.

## Proposed family assignment per jurisdiction
- **OR**: primarily F1, secondarily F3 (real-heading-but-extractor-format-miss) and F2/F6 at low volume.
- **PA**: primarily F3 (extractor format mismatch on genuinely-detected headings), secondarily F1 and F4.
- **RI**: primarily F3, with a **mojibake-quote sub-variant** (byte-decode corruption breaks quote-based parsing) as the leading cause; secondarily F2 and F1.
- **SC**: primarily F3 (bare `(N)` numeric markers), secondarily F1, F2, F4; F5 unconfirmed in this sample.
- **SD**: primarily F2 (body preamble without heading word), secondarily F1 and F3; one F5 candidate flagged for follow-up confirmation of extractor yield.
- **TN**: primarily F1, secondarily F4 and F2; F3 lower-volume here since TN's real "Definitions" headings tend to already use extractor-compatible markers.
- **TX**: primarily F3 (ALL-CAPS singular "DEFINITION." heading + single inline entry, no block markers), secondarily F1; one confirmed F4 (last-word-anchoring gap on multi-word compound headings ending in "DEFINITIONS").
- **UT**: dominant F1 AND F3 in near-equal, very high volume (58.8% combined of sampled candidates) — Utah's drafting convention combines heavy scoped-inline usage with heavily nested lettered sub-clause structure under proper "Definitions" headings; this is the highest-miss-rate state of the 9.
- **VT**: primarily F1, secondarily a combined F3+F5 case (multi-term shared clause under a detected heading that the extractor still can't parse) and F2.

No jurisdiction among the 9 showed zero misses; every one has at least F1 or F3 present at >1% of its sampled candidate rows.
```

=== B3b ===
# B3b — Definition-Introducing Convention Inventory: VA, WA, WV, WI, WY, DC, PR, FED

**Method**: For every jurisdiction, loaded the real `us_<code>_statutes.parquet` from the on-disk HF snapshot (`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`), then imported and called the **actual current code** — `is_definitions_heading`/`extract_definitions_from_section` from `backend/app/definition_links/us_profile.py` and `_is_placeholder_heading`/`_derive_heading_from_body`/`_extract_inline_quoted_definitions` from `backend/app/definition_links/pipeline.py` — replicating the exact Stage-2 pipeline logic (heading match → optional body-derivation → extractor → fallback-extractor-only-if-body-derived). "Captured" = heading recognized as a Definitions section AND ≥1 `DefinitionCandidate` actually extracted.

## Cross-cutting finding #1 (VA, WA, WV, WI, WY, DC, FED): the inline-quote fallback exists but is wired shut for real-heading articles

`pipeline.py`'s `_extract_inline_quoted_definitions` (pure `"Term" means ...` sentences, no `(N)` markers) is only invoked when `used_body_derived_heading` is True — i.e. only for the small placeholder-heading (CA/IL/GA-style) path. For every jurisdiction below, the section's own real `section_title` already literally says "Definitions", so it never goes through body-derivation, and this fallback is **never called at all**, even though `extract_definitions_from_section`'s `(N)`-paren-marker extractor returns **zero** candidates on this near-universal shape: `"As used in this chapter... "Term" means ..."` (no leading `(N)` before the quote).

| Jur | rows w/ "Definitions" in heading | heading matched, 0 candidates extracted | of those, rescuable by the already-existing (but unwired) inline fallback |
|---|---|---|---|
| VA | 1,117 | 1,085 (97%) | 1,038 (93%) |
| WA | 2,007 | 1,975 (98%) | 1,810 (90%) |
| WV | 1,138 | 335 (29%) | 282 (25%) |
| WI | 548 | 66 (12%) | 43 (8%) |
| WY | 522 | 62 (12%) | 30 (6%) |
| DC | 1,233 | 339 (27%) | 117 (9%) |
| FED | 1,949 | 1,628 (84%) | 1,499 (77%) |

Example (VA, `STATE_VA_T23.1_SI_C3_S23.1-300`, heading=`"Definitions"`): `As used in this chapter, unless the context requires a different meaning: "College degree" means an undergraduate degree from an accredited...` — heading is captured, extractor returns `[]`, but `_extract_inline_quoted_definitions` on the same text returns 9 candidates. **Family: (3) heading found but entry-marker format mismatch** — but more precisely a sub-case not in the known list: *no marker at all before the quote* (bare inline `"Term" means`). VA and WA are dominated by this; WV/DC/FED have it as a large minority; WI/WY less so (their bodies more often do use `(N)` markers).

## Cross-cutting finding #2 (VA, WA, WV, WY, DC, FED): "X defined" verb-form headings — NEW family, 100% missed

`is_definitions_heading` requires the literal noun "Definition(s)" as first/last word. Real headings using the past-participle verb form (`"Person" defined`, `Employee defined`, `Words and phrases defined`) never match — no "Definitions" token present at all, so this isn't covered by any of the 6 known families.

| Jur | count of `"defin"`-containing, non-"Definitions" headings sampled | captured-today |
|---|---|---|
| VA | 57 | 0/57 |
| WA | 279 | 0/279 |
| WV | 204 | 0/204 |
| WI | 16 | 0/16 |
| WY | 45 | 0/45 |
| DC | 38 | 0/38 |
| FED | 163 | 0/163 |

Example: WA `STATE_WA_T48_C01_S050`, heading=`RCW 48.01.050: "Insurer" defined.` — never reaches the extractor at all (`is_definitions_heading` returns False). **New family: verb-form heading (`"X" defined`) vs. current code's noun-only "Definitions" check.**

## Per-jurisdiction detail

**VA** (33,856 rows, sample n=4,000 for keyword scan): dominant miss is Finding #1 (pure inline-quote, no markers) — 1,085/1,117 Definitions-headed articles yield 0 candidates. Secondary: Finding #2 (57 "X defined" headings, 0 captured). Family assignment: (3) entry-marker mismatch [dominant] + NEW verb-form-heading family.

**WA** (51,498 rows): same as VA, even more extreme — 98% of Definitions-headed sections use pure inline-quote convention with zero markers (e.g. `RCW 47.14.020: Definitions.` → `"Right-of-way" means...(2) "Airspace" means...` — numbered but the numbers are topical sub-items, not entry-opening markers immediately before quotes in the extractor's expected shape). Family: (3) [dominant] + NEW verb-form family (279 instances, 0 captured).

**WV** (25,460 rows): heading matcher works reasonably (771/1,138 = 68% captured outright via `(N)`-marker bodies, real WV convention: `“Circuit court” means...` after `(a)`-lettered markers the extractor does parse in many cases). Miss: 282/1,138 rescuable via Finding #1 (pure inline no-marker), 53 genuinely uncaptured (cross-references like `"The definitions in W.S. ... apply to this article."` — correctly empty, not a miss). Family: (3) [minority but real] + NEW verb-form family (204 instances, 0 captured).

**WI** (18,158 rows): best-performing of the seven — 479/548 (87%) captured (WI's real convention nests `(1) Insurance marketing intermediaries. (a) Activities...` bracket-lettered markers the extractor handles). Miss: 43/548 rescuable via Finding #1; some `"Definitions"` sections are pure cross-references (`"The definitions in ss. 851.01 to 851.31 apply..."`) correctly empty. NEW verb-form family present but small (16 instances, 0 captured: `Employee defined.`, `Words and phrases defined.`).

**WY** (10,219 rows): 439/522 (84%) captured. Miss: 30 rescuable via Finding #1 (e.g. `§ 36-12-109. Definition` singular, matched by heading but body is unmarked inline). NEW verb-form family: 45 instances (`"insurable interest" defined`), 0 captured.

**DC** (23,694 rows): 884/1,233 (72%) captured. 339 zero-candidate: 117 rescuable via Finding #1 (e.g. `§ 5-601. Definitions.` → `As used in this chapter: (1) The term "Mayor" means...`), remainder mostly `Repealed.`/`Expired.` bodies (correctly empty, not a real miss) plus a handful of **NEW family: unquoted-term definitions** — e.g. `STATE_DC_T28_C25_S28-2501`: `"A bond, when required by or referred to in this Code, means an obligation..."` — no quote marks around the term at all, neither extractor's quote-anchored logic can find it. NEW verb-form family: 38 instances, 0 captured.

**FED** (54,853 rows, `us_federal_statutes.parquet`): heading matcher works (1,949 Definitions headings recognized) but only 320/1,949 (16%) actually extract candidates — the largest raw-count miss of all seven, 1,499 of the 1,629 zero-candidate cases rescuable via Finding #1 (`(a) As used in this chapter— (1) The term "administrator" means...` — federal statutes overwhelmingly use `The term "X" means` prose inside lettered/numbered outline paragraphs that don't align with the extractor's `(N)`-immediately-before-quote rule). NEW verb-form family: 163 instances (`"Wages" defined`, `Subpart F income defined`), 0 captured.

**PR** (23,636 rows): **entirely different language — Spanish.** Real headings use `"Definiciones"` (529 rows contain `Definici*` in `section_title`, e.g. `STATE_PR_LEY_249_2003_ART3`: `"Artículo 3. Definiciones"`). `is_definitions_heading("Artículo 3. Definiciones")` → `False` (verified by direct call) — the regex only recognizes the English literal "Definitions". English keyword sample (`means`, `As used in`, `Definitions`, etc.) returns near-zero hits (0–1) because the corpus is essentially all Spanish — `"significa"` (Spanish "means") appears 1,006 times in a 4,000-row sample, `"A los fines de"` (Spanish "for purposes of") 261 times, `"se entenderá por"` (Spanish "shall be understood as") 26 times. **100% of PR's ~529 real Definitions sections are invisible to the current pipeline.** This is not any of the 6 known families — **NEW family: non-English-jurisdiction convention (Spanish drafting idiom) entirely outside the English-only US profile's vocabulary**, distinct from Hebrew (which has its own profile) — PR is registered under the generic `USProfile`, which assumes English.

## Proposed family assignment (per jurisdiction)

- **VA**: (3) entry-marker mismatch — no-marker inline-quote sub-case [dominant, ~93% of misses] + NEW verb-form-heading family
- **WA**: (3) same sub-case [dominant, ~90%] + NEW verb-form-heading family
- **WV**: (3) same sub-case [~25% of headed sections] + NEW verb-form-heading family
- **WI**: (3) same sub-case [minor, ~8%] + NEW verb-form-heading family
- **WY**: (3) same sub-case [minor, ~6%] + NEW verb-form-heading family
- **DC**: (3) same sub-case [~9%] + NEW unquoted-term-definition family + NEW verb-form-heading family
- **FED**: (3) same sub-case [dominant, ~77%] + NEW verb-form-heading family
- **PR**: **NEW family — Spanish-language jurisdiction convention** (not a match to any of the 6 known English-drafting families; USProfile is English-only and PR is 100% missed)

**Files consulted**: `backend/app/definition_links/us_profile.py`, `backend/app/definition_links/pipeline.py`, `backend/app/definition_links/profiles.py`; data from `us_va_statutes.parquet`, `us_wa_statutes.parquet`, `us_wv_statutes.parquet`, `us_wi_statutes.parquet`, `us_wy_statutes.parquet`, `us_dc_statutes.parquet`, `us_pr_statutes.parquet`, `us_federal_statutes.parquet` (all present at the existing HF snapshot path, no download needed). Analysis scripts (scratchpad, not committed): `/private/tmp/claude-501/-Users-nerya-LexGraph/87b55b0a-5a38-44b6-887d-1e093b526197/scratchpad/b3b_deep.py` and `b3b_gap.py`.