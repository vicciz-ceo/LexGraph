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
