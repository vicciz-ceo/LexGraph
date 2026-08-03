# US State Law Compatibility — Recon Dossier (2026-08-02)

Recon completed 2026-08-02. Sections 1 and 4 re-run after first-pass scout failures.

Branch: `claude/us-state-law-compat-6d3ae8`. Compiled from 4 recon reports (deterministic engine, corpus data model/ingestion, API+UI jurisdiction surfaces, test/dev environment), plus two targeted re-recon passes on the deterministic engine (§1) and the vaquill/open-us-law dataset (§4).

## 1. Deterministic engine as it stands today

### Entry points

- `backend/app/definition_links/pipeline.py:90` — `run_definition_linking(session, *, matter_id, triggered_by_user_id) -> dict`. The sole processing entry point; loads already-ingested `Article` rows for a matter and runs Stages 2-5.
- `backend/app/definition_links/ingest.py:27` — `ingest_wiki_law(session, *, repository_id, matter_id, title, wiki_text) -> dict`. Parses raw wiki text into `Article`/`SourceSpan` rows (must run before `run_definition_linking`).
- `backend/app/definition_links/cli.py:53` — `main(argv=None) -> int`, invoked as `python -m app.definition_links.cli --matter-id <id> --triggered-by-user-id <id>` (`cli.py:36-50`). Calls `run_definition_linking` directly.
- No HTTP route calls this pipeline: `grep -rn "run_definition_linking\|ingest_wiki_law" backend/app --include="*.py"` outside `definition_links/` returns only a docstring reference in `backend/app/models/article.py:6`. Confirmed via recon dossier too (`docs/sprint/sprints/2026-07-30-deterministic-assertions-review.md:24`: "Article-mentions-article detection: none exists in this repo").

### End-to-end trace

1. `ingest.py:54` `parse_articles(wiki_text)` (delegates to `sections.py:59`) splits raw wiki text on `@ N.` markers into parsing-only `Article` dataclasses.
2. `ingest.py:55-72` persists one `SourceSpan` (`quote_text=parsed_article.body`) and one ORM `Article` row per parsed article; `session.commit()` at `ingest.py:77`.
3. `pipeline.py:109-111` loads all `Article` ORM rows for `matter_id`.
4. `pipeline.py:115-125` per article: fetch its `SourceSpan.quote_text`, guard with `is_bidi_degraded` (`guards.py:43`), else `normalize_for_parsing` (`normalize.py:36`) then `strip_wikilinks` (`normalize.py:52`), producing a `MatcherArticle`.
5. `pipeline.py:130-142` Stage 2: for each article, if `is_definitions_heading(art.heading)` (`sections.py:52`) → `extract_definitions_from_section` (`extract.py:168`) with a scope from `_determine_scope` (`pipeline.py:83`); else → `extract_local_definitions` (`extract.py:183`) + `extract_adhoc_definitions` (`extract.py:202`).
6. `pipeline.py:158-179` persist a `Definition` row per unique `(owning_article, sorted terms)` key (idempotent reuse via `definitions_by_key`).
7. `pipeline.py:268-301` Stage 3, per document: `link_articles_to_definitions` (`matcher.py:113`) finds term-uses in article bodies and creates `USES_DEFINITION` `Assertion` rows via `_create_assertion` (`pipeline.py:206`), keyed by `edge.article_index` not `edge.article_number` (`pipeline.py:286-290`, dedupe safety for repeated numbers).
8. `pipeline.py:306-338` Stage 4: for each resolved definition/term, `detect_cross_law_derivations` (`derivation.py:93`) scans the definition text for trigger phrases + law references, creating `DERIVES_FROM_LAW` assertions (resolved via `known_law_titles`, else `object_entity_id=None`).
9. `pipeline.py:340` `session.commit()` persists everything; return dict of created rows (`pipeline.py:342-346`).

### The 3 hardest Hebrew/Israel couplings to remove

1. **Hebrew agglutinative prefix-letter surface-form expansion** — `backend/app/definition_links/matcher.py:14,22-52` (`_PREFIX_LETTERS = "ובלכמשה"`, `_surface_variants`). This builds term-match variants for Hebrew's one-letter prefixes/conjunctions attached with no space; English has no equivalent morphology, so the whole matching strategy behind Stage 3 is inapplicable to English text, not just parametrizable.
2. **Cross-law derivation trigger phrases + law-reference grammar** — `backend/app/definition_links/derivation.py:14-25` (10 Hebrew inflections of "as defined by") and `derivation.py:53-59` (`_LAW_REF_RE` hardcoding חוק/פקודת/פקודה, plus Hebrew-year-suffix stripping for law-title identity, e.g. `תשכ"ה-1964`). No English/US equivalent phrase or citation grammar (`Pub. L. No.`, `U.S.C.`) is recognized.
3. **Definitions-heading + article-marker detection** — `backend/app/definition_links/sections.py:21` (`_ARTICLE_MARKER_RE`, assumes wiki-scrape `@ N.` prefix with Hebrew-letter-suffixed article numbers) and `sections.py:33-35` (`_DEFINITIONS_HEADING_RE`, matches only literal Hebrew words for "Definitions"). Without these two regexes matching, Stage 1 parsing and Stage 2 definitions-section detection never fire at all on a US statute — this is the first gate the whole pipeline passes through.

### Extension seam

None. Every stage is called directly, in a fixed linear sequence, with no interposed interface — `pipeline.py:130-142` calls `is_definitions_heading`, `extract_definitions_from_section`, `extract_local_definitions`, `extract_adhoc_definitions` as bare module-level functions imported directly at `pipeline.py:29-39`; `matcher.py`'s `link_articles_to_definitions` and `derivation.py`'s `detect_cross_law_derivations` are likewise plain function calls, not dispatched through any registered strategy. No `Protocol`/`ABC`/plugin registry/config flag exists anywhere in `backend/app/definition_links/`. All Hebrew-specific regexes are hardcoded module-level constants in the same files as the calling logic — a second jurisdiction would require forking or rewriting every module (`sections.py`, `extract.py`, `derivation.py`, `matcher.py`, `normalize.py`, `guards.py`), not implementing a new adapter.

### Test coverage

- Unit tests (`backend/tests/unit/test_definition_links_*.py`) cover each stage's regex/logic function-by-function, using inline Hebrew string literals as test input.
- `test_definition_links_no_network_dependencies.py` confirms the "deterministic" framing (no network/model calls).
- Integration tests (`backend/tests/integration/test_definition_links_*.py`, `test_qa_regression_definition_links.py`, `test_qa_regression_deterministic_assertions.py`) run end-to-end against a real DB and real Hebrew fixture files.
- All 9 vendored fixtures at `backend/tests/fixtures/wiki_laws/` are real Israeli statute excerpts in Hebrew (e.g. `חוק להגנת רכוש מופקד.wiki`) — no jurisdiction-neutral or English fixture exists anywhere in this test estate.

### Honest gaps

- Per-assertion detail inside most integration test files was not opened line-by-line — coverage claims above are based on file names plus one file read in full.
- Not verified whether the sibling `backend/app/enrich/pipeline.py` (which this pipeline explicitly mirrors) has any jurisdiction/language abstraction this one lacks.
- Not verified whether `docs/RUNBOOK.md` discusses multi-jurisdiction plans (a prior sprint log references a RUNBOOK sync but it was not opened).

## 2. Corpus data model + ingestion

Legal content is modeled by five plain SQLAlchemy tables under `backend/app/models/`: `documents`, `articles`, `definitions`, `source_spans`, plus the assertion family (`assertions`, `assertion_revisions`, `assertion_evidence`, `assertion_ratings`, `assertion_comments`, `audit_events`) that reference them.

- Document/Article/Definition/SourceSpan carry **no jurisdiction, country, or locale field at all** (`backend/app/models/document.py:17-25`, `article.py:23-36`, `definition.py:23-40`, `source_span.py:17-25`; also `repository.py:17-24`, `matter.py:17-24`, `organization.py:17-20`).
- The only jurisdiction-like field anywhere is a free-text nullable `jurisdiction: str | None` on `Assertion` and `AssertionRevision` — no enum, no allow-list, no default (`backend/app/models/assertion.py:50`, `backend/app/models/assertion_revision.py:45`).
- Ingestion entrypoint is `ingest_wiki_law()` (`backend/app/definition_links/ingest.py:27-83`), which parses a specific Israeli-legislation MediaWiki-style text format via `backend/app/definition_links/sections.py`.
- Article numbering regex explicitly supports Hebrew construct-letter suffixes (Israeli legislative numbering convention): `_ARTICLE_MARKER_RE = re.compile(r"^@\s+(?P<number>\d+[א-ת]*)\.\s*(?P<heading>.*)$")` (`sections.py:15-21`).
- Definitions-heading detection matches a fixed set of Hebrew phrases only: `_DEFINITIONS_HEADING_RE` matching הגדרות ופירוש / הגדרת מונחים / הגדרות / הגדרה (`sections.py:33-35`).
- Cross-law citation/derivation detection (`backend/app/definition_links/derivation.py:14-25,53-59`) is regex over Hebrew trigger phrases (כהגדרתו, כמשמעותו) and Hebrew law-reference syntax (בחוק/פקודת/פקודה), including Hebrew-year-suffix stripping for canonical law identity.
- Hebrew niqqud/maqaf normalization is built into matching (`backend/app/definition_links/normalize.py:14-28`).
- None of the above (sections.py, matcher.py, derivation.py, normalize.py) is abstracted behind a jurisdiction/locale concept — Hebrew parsing is structural, not configurable.
- Separately, `app/seed_demo.py` seeds English-language demo MSA/DPA contract data via the real HTTP API (not law-text ingestion) — it is not a second corpus-ingestion path, just demo fixtures (`seed_demo.py:1-25, 42-54, 253`).
- No Alembic. Schema changes ship as hand-rolled `upgrade(engine)/downgrade(engine)` raw-DDL modules under `backend/app/migrations/` (`migrations/__init__.py:1-9`; example `add_raw_text_columns.py:31-45`); otherwise `Base.metadata.create_all()` builds the schema from current ORM models (`backend/app/db.py`).
- All primary keys are Python-generated UUID strings (`String(36)`, `uuid.uuid4()`), not DB sequences — e.g. `document.py:20`, `article.py:26`, `definition.py:26`.
- Real Israeli-law wiki fixtures live at `backend/tests/fixtures/wiki_laws/` (e.g. `חוק להגנת רכוש מופקד.wiki`), using niqqud, maqaf dashes, and MediaWiki-style `[[wikilink|display]]`/`<שם>`/`<מקור>` syntax (`normalize.py:14-28`; fixture file lines 1-13).
- Frontend types mirror the backend: `frontend/src/api/types.ts` — `jurisdiction: string | null`, no enum; `frontend/src/components/AssertionSuggestionForm.tsx:278-284` — jurisdiction is a plain `<input type="text">`.

Open question (from report 2, UNVERIFIED): whether a bulk/batch corpus importer exists beyond `ingest_wiki_law` + the `app/definition_links/cli.py` CLI — not found in `scripts/` or `backend/app/` in this repo; a larger corpus-loading capability may exist in the separate POC location (`/Users/nerya/AI for others`, out of scope for this repo per user memory).

## 3. API + UI jurisdiction surfaces

Jurisdiction is accepted, stored, and optionally filtered end-to-end in the assertions surface only — no other resource (documents/articles/definitions/reviews/ratings/comments) carries or filters on it.

- `POST /api/v1/assertions` accepts optional `jurisdiction` (`backend/app/routers/assertions.py:142`, `AssertionCreate.jurisdiction: str | None = None`).
- `GET /api/v1/assertions` filters via `stmt.where(Assertion.jurisdiction == jurisdiction)` with **no validation or allow-list** (`assertions.py:625` param, `:647` filter).
- `PATCH /api/v1/assertions/{id}` and `POST /api/v1/assertions/{id}/revisions` both accept jurisdiction updates (`assertions.py:158, 824-825, 973-974`).
- Serialization includes jurisdiction in both assertion and revision payloads (`assertions.py:222, 252`).
- `GET /api/v1/matters/{matter_id}/graph` does **not** surface or filter by jurisdiction (`graph.py:142-164`).
- Frontend: jurisdiction is a free-text input in `AssertionSuggestionForm.tsx:278-284`, submitted as `jurisdiction: jurisdiction || undefined` (`:151`).
- Displayed (read-only, no filter control) in: `AssertionDetailPanel.tsx:167-168` (Overview tab), `KnowledgeBasePage.tsx:391-392` (inline) and `:186,200` (CSV export column), `ReviewQueuePage.tsx:312-313` (chip), `ContestedPage.tsx:471` (inline), `ProfilePage.tsx:180` (metadata).
- No page defines a `JURISDICTION_OPTIONS` constant — contrast with existing `STATUS_OPTIONS`/`ORIGIN_OPTIONS` on the same pages — confirming there is no controlled vocabulary or filter UI anywhere today.
- Test fixtures use unconstrained free-string values: `"EU"` (`seed_demo.py:253`), `"IL"` (`ReviewQueuePage.test.tsx:91`, `KnowledgeBasePage.test.tsx:59`, `ContestedPage.test.tsx:74`), `"US-DE"` (`AssertionDetailPage.test.tsx:80`), and `null` (multiple test files) — demonstrating the field already tolerates arbitrary strings including a US-state-shaped value, but with no semantics attached.
- No i18n/locale/RTL machinery found anywhere in the frontend (no `i18n/*.ts`, `locale/*.ts`, `l10n/*.ts`, no `dir="rtl"` usage).

## 4. The vaquill/open-us-law dataset (verified facts only)

Re-recon confirms the dataset is real, public, and non-gated (the first-pass "nothing found" result was a tooling/access issue, not a real absence). `GET https://huggingface.co/api/datasets/vaquill/open-us-law` returned HTTP 200 (`"private": false, "gated": false, "disabled": false`, `sha: d2d760358de8bea543f016c226ad979b0adf2a85`, `lastModified: 2026-07-31T12:33:31Z`). No auth wall on the dataset card, file tree, or first-rows preview API.

**Layout**: 105 files — `README.md`, `SHA256SUMS.json`, a thumbnail, and 102 Parquet files: one `us_<state>_statutes.parquet` + one `us_<state>_constitutions.parquet` per jurisdiction (50 states + DC + PR), plus `us_federal_statutes.parquet`/`us_federal_constitutions.parquet`. `us_dc_constitutions.parquet` is absent (DC has no state constitution). Format: Parquet, two HF dataset configs (`statutes`, `constitutions`), single `train` split each. Total size ~1.1 GB (`usedStorage: 1,182,309,942` bytes); largest file `us_federal_statutes.parquet` (88.7 MB), largest state `us_ca_statutes.parquet` (71.1 MB).

**Schema** (confirmed verbatim via the HF datasets-server first-rows API, identical for both configs): `act_id, citation, citation_short, state, jurisdiction, document_type, title_number, title_name, chapter, chapter_name, section_number, section_title, breadcrumb (JSON list), display_path, act_status, text, word_count, source_url, last_amended_year, subsection_count, cross_references_usc (JSON list), cross_references_cfr (JSON list), public_laws_referenced (JSON list), year`. Example row (Alaska statute): `act_id: "STATE_AK_T11_C11.76_S11.76.115"`, `citation: "Alaska Stat. § 11.76.115"`, `act_status: "in_force"`, `word_count: 103`.

**Coverage**: per the dataset card, 1,983,394 state/territorial statute sections (52 jurisdictions) + 54,853 USC sections + 7,762 constitution sections (52 jurisdictions) — ~2.05M sections total. Snapshot labeled "v2026.07, 2026-07-21". Statutes and constitutions only — no case law or regulations (the `cross_references_cfr` field is a reference list inside statute text, not a CFR corpus). `act_status` allows filtering in-force vs. repealed/reserved/omitted statutes.

**License**: `license: cc-by-4.0` per dataset tags/cardData. Per a summarized (not byte-verified) read of the README: underlying statutory text is public domain (government edicts doctrine), the compiled/structured dataset is CC BY 4.0, and the separate scraper repo (`github.com/Vaquill-AI/open-us-law`) is Apache-2.0.

**Per-state pull**: no auth token required. Cheapest path is `huggingface_hub.hf_hub_download(repo_id="vaquill/open-us-law", filename="us_tx_statutes.parquet", repo_type="dataset")` then `pandas.read_parquet(path)`; equivalently `datasets.load_dataset("vaquill/open-us-law", data_files={"train": "us_tx_statutes.parquet"}, split="train")`; or a raw `curl -L` against the `resolve/main/<file>.parquet` URL (LFS-tracked, redirects to CDN).

**Biggest unknown**: the license-layering description and the "quarterly updates" claim come from a WebFetch-summarized rendering of the README, not byte-verified quotes — re-confirm the raw README text before relying on either for a compliance/licensing sign-off.

## 5. Test estate + environment

- 61 backend test files / 468 test functions total: unit 22 files / 214 tests, integration 37 files / 252 tests, e2e 2 files / 2 tests.
- Frontend: 151 vitest test cases across `frontend/src/components/__tests__` (11 files) and `frontend/src/pages/__tests__` (9 files), jsdom + React Testing Library, setup at `frontend/src/test/setup.ts:1`.
- 9 Hebrew-law `.wiki` fixture files at `backend/tests/fixtures/wiki_laws/` (Banking Law, Privacy Law, Criminal Code, Penal Code, etc.) used by definition-link/corpus tests.
- Backend venv present at `backend/.venv` with Python 3.13.12; CI matrix runs backend on Python 3.12 & 3.13 (`.github/workflows/ci.yml:25`; `backend/pyproject.toml:6` requires `>=3.12`); local Python 3.12 interpreter not installed (per `docs/sprint/repo-profile.md`).
- Test commands: backend `backend/.venv/bin/pytest backend/tests -v`; frontend `npm --prefix frontend run test -- --run`; typecheck `npm run typecheck` (`docs/sprint/repo-profile.md:13-14`; `.github/workflows/ci.yml:39,57,59`).
- No Alembic/DB-migration test dependency; local-first SQLite via `tmp_path` DB in `backend/tests/conftest.py:44-81`.
- Core fixtures: `app`, `client`, `db_session`, `matter_with_users` (org/repo/matter + 4 users: contributor, rater/contributor, reviewer, outsider) at `conftest.py:287-322`; `assertion_payload`/`rating_payload` builders at `:328-349`.
- Repo-profile snapshot (UNVERIFIED as current — dated note): 126 backend tests with 39 FAILED / 87 ERROR "legitimate per contract", and 59 frontend tests with import-resolution RED (`docs/sprint/repo-profile.md:30-35`). Exact failing modules not enumerated in any report — **open question, not resolved**.
- CI: 3 jobs — backend (matrix 3.12/3.13), frontend (typecheck + vitest, Node 24), contracts (sprint contract lint) (`.github/workflows/ci.yml:16-103`).

## 6. Israel-specific hardcoding — exhaustive inventory

| What | file:line | Why it blocks US law |
|---|---|---|
| Article-number regex allows trailing Hebrew construct letters (א-ת) | `backend/app/definition_links/sections.py:15-21` | US state statute numbering (e.g. "§ 12.5-3(a)", "Cal. Civ. Code § 1798.100") doesn't follow Hebrew construct-letter suffix conventions; the marker regex would not recognize US section headers at all |
| Definitions-heading detection is a fixed Hebrew-phrase regex | `backend/app/definition_links/sections.py:33-35` | US statutes use "Definitions", "Definitions and Interpretation", etc.; none of these English headings match, so no definitions section would ever be detected in a US-law document |
| Cross-law citation/derivation trigger phrases are Hebrew legal idioms | `backend/app/definition_links/derivation.py:14-25` (כהגדרתו, כמשמעותו) | US legal cross-references use different phrasing ("as defined in", "within the meaning of") — none recognized, so derivation/citation linking would silently find zero matches on US corpora |
| Law-reference syntax regex matches Hebrew "בחוק/פקודת/פקודה" patterns, incl. Hebrew-year-suffix stripping | `backend/app/definition_links/derivation.py:53-59` (`_LAW_REF_RE`, `_YEAR_TAIL_RE`) | US statute citations follow entirely different conventions (e.g. "Cal. Civ. Code §", "N.Y. Gen. Bus. Law §", "15 U.S.C. § 1"); the Hebrew year-tail stripping logic (e.g. תשכ"ה-1964) has no US equivalent and no fallback |
| Hebrew niqqud/maqaf normalization baked into text matching | `backend/app/definition_links/normalize.py:14-28` | Irrelevant/no-op for English text, but signals the normalization layer was designed exclusively for Hebrew orthography, not built as a pluggable per-locale normalizer |
| Ingestion parser (`ingest_wiki_law`) targets a specific Israeli-legislation MediaWiki dialect | `backend/app/definition_links/ingest.py:27-83` | No ingestion path exists for any other document format/dialect (e.g. plain text, HTML, XML US state legislative formats); a new parser would be needed, not a config switch |
| Wiki fixtures use Hebrew-specific markup (`<שם>`, `<מקור>`, `[[wikilink|display]]`) | `backend/tests/fixtures/wiki_laws/חוק להגנת רכוש מופקד.wiki:1-13` | Confirms the ingestion format itself (not just the parser) is coupled to the Israeli legislative wiki corpus source; a US corpus in a different format could not reuse these fixtures or the format assumptions behind them |
| Only Assertion/AssertionRevision have a jurisdiction field; Document/Article/Definition do not | `backend/app/models/document.py:17-25`, `article.py:23-36`, `definition.py:23-40`, `source_span.py:17-25` vs. `assertion.py:50` | Laws/documents themselves carry no jurisdiction — there is no way to scope a corpus of US-state statutes as distinct from Israeli law at the document/article level; jurisdiction only exists downstream on user-authored assertions |
| jurisdiction column has no enum/allow-list/default | `backend/app/models/assertion.py:50`, `assertion_revision.py:45` | Any string is accepted for any request today (already tolerates "US-DE" per test fixture), but nothing enforces a controlled US-state vocabulary — this is a permissive gap, not a blocker, but must be designed before "US state law" becomes a first-class concept |
| No jurisdiction filter UI (no `JURISDICTION_OPTIONS`) on any page | `KnowledgeBasePage.tsx`, `ReviewQueuePage.tsx`, `ContestedPage.tsx` (per report 3, contrasted with existing `STATUS_OPTIONS`/`ORIGIN_OPTIONS`) | Users cannot filter/browse by jurisdiction today even though the data field exists; multi-state corpora would be unnavigable without this |
| No i18n/locale/RTL infrastructure in frontend | Absence noted across `frontend/src` (report 3) | Confirms the frontend was never built with a locale-abstraction layer — not itself a blocker for US-English content, but no precedent exists for jurisdiction-conditional UI/logic to build on |
| Definition entry marker | `backend/app/definition_links/extract.py:19` (`r"^\s*:-\s?"`) | MediaWiki definition-list syntax specific to the israeli-laws-wiki scrape format, not a general legal-text convention |
| Nested-definition trigger | `backend/app/definition_links/extract.py:23` (`"לעניין הגדרה זו,\s*"`) | Literal Hebrew phrase ("for this definition"); no English equivalent detection |
| Local-scope trigger | `backend/app/definition_links/extract.py:28-30` | Literal Hebrew "for this purpose"/"in this section, ..."; also assumes quote-dash definition punctuation style |
| Ad-hoc "hereinafter" marker | `backend/app/definition_links/extract.py:33` (`"להלן"`) | Hebrew "hereinafter"; US drafting uses a bare parenthetical `("Term")` with no lead-in word |
| Repeal/deletion markers | `backend/app/definition_links/extract.py:43-45` | Hebrew inflected verb forms for "repealed/deleted"; US repealed-section conventions read differently (e.g. "[Reserved]") |
| Same-law reference exclusion | `backend/app/definition_links/derivation.py:39` (`r"^בסעיף\s+\d"`) | Hebrew "in section N"; US equivalent "in Section N"/"§ N" not recognized |
| Anaphoric law reference | `backend/app/definition_links/derivation.py:43` | Hebrew "that law"/"the said law" pattern, no English equivalent |
| RTL bidi-degradation guard | `backend/app/definition_links/guards.py:43-63` (`is_bidi_degraded`) | Detects RTL-reversal artifacts from naive PDF extraction of Hebrew text; meaningless for LTR US statutes |
| Hebrew agglutinative prefix-letter surface-form expansion | `backend/app/definition_links/matcher.py:14,22-52` (`_PREFIX_LETTERS = "ובלכמשה"`) | Builds term variants for Hebrew one-letter prefixes attached with no space; English has no equivalent morphology, so this entire matching strategy doesn't transfer |
| Hebrew punctuation treated as word boundary | `backend/app/definition_links/matcher.py:18-19` (`_BEFORE_OK`/`_AFTER_OK` include maqaf `־`) | Uses a Hebrew-tuned boundary set instead of `\b`; English tokenization needs ordinary word-boundary regex |
| Chapter/division-scope trigger phrases | `backend/app/definition_links/pipeline.py:62-68` (`"לענין פרק זה", "בסימן זה"`, etc.) | Hebrew phrases for "for this chapter"/"in this division"; "סימן" (division) is an Israeli drafting unit with no fixed US equivalent |
| `jurisdiction` column always null at write time | `backend/app/definition_links/pipeline.py:233` (`jurisdiction=None,`) | The pipeline never populates the one jurisdiction column that exists, so multi-jurisdiction data isn't distinguished at the DB level even where the schema allows it |

## 7. Candidate seams for multi-jurisdiction support (options, with trade-offs)

Confirmed via §1's fresh recon: the pipeline has **no** extension seam today — every stage (`sections.py`, `extract.py`, `derivation.py`, `matcher.py`, `normalize.py`, `guards.py`) is called as bare module-level functions in a fixed linear sequence, with no `Protocol`/`ABC`/registry/config flag anywhere in `backend/app/definition_links/`. The options below are real design choices against that confirmed-absent seam, not speculative hypotheses.

1. **Add a jurisdiction/format concept to Document, and dispatch ingestion parser by it** (vs. today's single hardcoded `ingest_wiki_law` path).
   - Trade-off: requires a new column + migration (hand-rolled, per §2) on Document, plus building the parser-registry abstraction over `sections.py`/`extract.py`/`derivation.py`/`matcher.py`/`normalize.py`/`guards.py` that §1 confirms does not exist today. Larger upfront investment — effectively all 6 modules need a second implementation or a generalized/pluggable form — but the only path that lets Document/Article/Definition (not just Assertion) know their own jurisdiction.

2. **Write a parallel US-law ingestion + linking pipeline alongside the existing Hebrew one** (vs. generalizing the existing modules to be locale-agnostic).
   - Trade-off: parallel implementation is faster to ship and lower-risk (doesn't touch working Hebrew-corpus code/tests at `backend/tests/fixtures/wiki_laws/`), but duplicates 6 modules' worth of structure (parsing, extraction, derivation, matching, normalization, bidi guarding) long-term. Generalizing the existing regex-driven modules into locale-pluggable sets is more work now but avoids a permanent fork; given §1's finding that the Hebrew-specific logic (agglutinative prefix matching, RTL bidi guard) has no English analog at all, full generalization may not be meaningfully cheaper than a parallel build for the matcher/guard layers specifically.

3. **Constrain the existing free-text `jurisdiction` column into a controlled vocabulary** (US state codes) **vs. leaving it free text and only adding a curated frontend dropdown**.
   - Trade-off: DB-level enum/CHECK constraint is stronger but requires a migration and backfill decision for existing "IL"/"EU"/null values (compounded by §1's finding that the pipeline itself never populates `jurisdiction`, per `pipeline.py:233` — any constraint design must also decide what the pipeline should write going forward). Frontend-only dropdown is fast to ship but doesn't stop bad data entering via the API directly.

4. **Keep US-law content out of Document/Article entirely and represent it only via Assertion.jurisdiction** (status quo minimal-change path) **vs. Option 1's full corpus modeling**.
   - Trade-off: zero schema change, ships fastest, but assertions would have no backing Document/Article/SourceSpan for US statutes — evidence quoting (`source_spans`) and definition-cross-linking (§1 confirms this is the deterministic engine's actual core purpose, not a placeholder) would not function for US content at all.

5. **Ingest the real vaquill/open-us-law dataset (per §4) now, one state at a time, vs. hand-picked sample fixtures first.**
   - Trade-off: §4 confirms the dataset is real, public, non-gated, and cheap to pull per-state (`hf_hub_download`, no auth) with a documented schema (`text`, `citation`, `act_status`, etc.) — so a real pilot state is now low-cost to obtain. But the dataset's `text` field is plain statute prose with none of the wiki-markup structure (`@ N.` markers, `:-` definition lists, `[[wikilink]]`) the current parser depends on (§1, §6) — a real adapter must be written against this schema, not assumed from the existing Hebrew wiki-fixture shape. A hand-picked sample (e.g. one state's Parquet rows converted to a small fixture set) de-risks parser design before committing to full-corpus ingestion.

## 8. Open questions for the director

1. §1 confirms there is no extension seam in the deterministic engine at all — every US-law option in §7 requires either forking 6 modules or generalizing them, both real engineering investments. Which of §7's options (1/2 combined, vs. 4's minimal-change path) should be scoped for this sprint?
2. §4 confirms `vaquill/open-us-law` is a real, usable, CC-BY-4.0-licensed dataset (~2.05M sections, per-state Parquet files, no auth needed) — but the license-layering claim (public-domain text + CC-BY compilation) was read from a summarized fetch, not the raw README bytes. Should someone byte-verify the README before this dataset is relied on for a compliance sign-off, or is the summarized reading sufficient to proceed with a pilot ingestion?
3. Is there a larger/bulk corpus-ingestion capability outside this repo (e.g. in the POC at "/Users/nerya/AI for others" per prior session memory) that should inform whether §7 Option 1 or Option 2 is preferred, or is this repo expected to own US-law ingestion independently against the vaquill dataset directly?
4. Should `jurisdiction` become a controlled US-state vocabulary now, and if so, does it also need to support federal/state hierarchy or multi-jurisdiction assertions (e.g. an assertion applicable to both federal and one state)? §1 shows the pipeline never writes to this column today (`pipeline.py:233`), so this decision also determines what the pipeline should start writing.
5. What is the current pass/fail state of the backend/frontend test suites right now? The only data point (126 backend / 39 FAILED / 87 ERROR "legitimate per contract"; 59 frontend RED on import resolution) is an undated snapshot from `docs/sprint/repo-profile.md` with no enumerated failing modules — needs a fresh test run before this dossier's test-estate section can be trusted as current.
6. Should jurisdiction filtering be added to the graph projection endpoint (`GET /matters/{id}/graph`, `graph.py:142-164`), which today ignores jurisdiction entirely — relevant if US multi-state graphs need to be scoped per state.
