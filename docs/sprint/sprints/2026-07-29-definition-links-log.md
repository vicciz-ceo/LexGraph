# Sprint log — 2026-07-29-definition-links

Append-only overflow sink. Never auto-loaded.

## Agent roster

(manager appends role → agentId at every spawn)

- 2026-07-29T13:12Z recon workflow → run wf_753f95c2-4c1 (task wyqqk0lxl); 3 scouts (poc-map sonnet/med, repo-map haiku/med, def-research sonnet/med) + synthesizer (sonnet/high). Dossiers in session scratchpad; synthesis to docs/sprint/sprints/2026-07-29-definition-links-review.md.
- 2026-07-29T13:26Z planner → agent a12edbf5471a421c2 (sonnet/high; Haiku considered: no — forbidden for Planner). Gates G1-G4 + R1-R9 under M1-M7; delivered DL1-DL9, 84 RED tests @ 1a7e7bd. Manager verified: diff containment PASS (tests/fixtures/conftest/contract only), RED spot-run 84 failed as claimed, mcp diagnosis confirmed.
- 2026-07-29T14:00Z DL10 developer (pending spawn) → haiku/low; Haiku considered: yes — bounded mechanical config pin, exhaustive spec in DL10, RED committed (6 pre-existing failures), no auth/persistence/migration surface.
- 2026-07-29T14:00Z DL1-DL9 developer (pending spawn) → sonnet/medium; Haiku considered: yes, rejected — schema/persistence surface (new models, pipeline writes), well beyond bounded-mechanical.
- 2026-07-29T14:05Z DL10 developer → agent a679da5a3fd224059 (haiku/low) — DONE @ 821a597; manager anti-gaming diff check PASS (1 file, 1 line), probe 7 passed.
- 2026-07-29T14:06Z DL1-DL9 developer → agent a81cf7a86d36367f2 (sonnet/medium) — DONE @ 704c91e; manager checks: containment PASS (0 test files), risk-classed diff read of models/validation/ingest/pipeline/cli PASS, live-path probe 17 passed. Flag for QA: unresolved-derivation dedup key collapses distinct unresolved targets from one definition.
- 2026-07-29T14:33Z qa (pending spawn) → sonnet/high; Haiku considered: no — policy fixes QA at Sonnet high.
- 2026-07-29T15:10Z qa → this agent (sonnet/high) — DONE. 9/10 items PASS (DL1-DL7, DL9, DL10), moved to Completed. DL8 `[QA-FAIL]`: confirmed the roster's own flag above — dual-unresolved cross-law derivation collapse in `pipeline.py`'s idempotency key; RED integration test committed, DL8 bounced to Next Steps. qa_cycles: 1, status: qa-fail, current_role: developer.
- 2026-07-29T14:49Z manager qa-fail gates: QA containment PASS (2 test files + contract docs only); RED provenance verified by manager run (1 failed by design); pin-collision pre-check PASS — QA regression pins structural, and the `len(derives_edges)==1` Planner pin probed safe (fixture yields exactly 1 clause). Fix ruling: add deterministic `proposition` to BOTH identity-key constructions in `_create_assertion`/`existing_keys` (pipeline.py) — distinguishes per-edge, preserves rerun idempotency, also fixes QA's corroborated resolved-target 3-term variant.
- 2026-07-29T14:49Z DL8-fix developer (pending spawn) → haiku/low; Haiku considered: yes — QA-fail mechanical fix row: single surface (pipeline.py, one function), fully specified by manager ruling, RED committed @ b64d26e; fresh spawn, never a resume-down.
- 2026-07-29T14:50Z DL8-fix developer → agent af25788bd8733c764 (haiku/low) — DONE @ 2f27703 (2 lines, exactly as ruled); manager checks: diff exact, RED pin green, 18 scoped tests green.
- 2026-07-29T14:56Z qa cycle 2 (DL8 re-verify only) → this agent (sonnet/high) — DONE. Full evaluator 384+62 passed, 0 flakes. Commit 2f27703 diff-confirmed (pipeline.py, 2 lines). Cycle-1 RED pin green. E2E probe on real fixtures: 3-term clause (חוק הגנת הפרטיות_excerpt.wiki line 17) now persists 3 DERIVES_FROM_LAW edges, one per term, all resolving to חוק המחשבים; idempotent rerun (0 new rows). DL8 PASS, moved to Completed (10/10). Regression test added @ 69b1be6. qa_cycles: 2, status: review, current_role: planner.

## DL8 QA-FAIL rationale (cycle 1, moved from contract Next Steps at fix time)

`run_definition_linking`'s idempotency de-dup key `(assertion_type,
subject_entity_type, subject_entity_id, object_entity_type,
object_entity_id)` omitted any per-edge component. For UNRESOLVED
DERIVES_FROM_LAW edges object is always (None, None) and the subject is the
same Definition row, so two independently-unresolved cross-law derivations in
one definition body collapsed to ONE persisted assertion — contradicting the
review doc's Stage 4 worked example (one edge PER TERM). Corroborated on the
real corpus: חוק הגנת הפרטיות_excerpt line 17 (3 terms sharing one derivation
clause to the ingested חוק המחשבים) persisted 1 assertion instead of 3 —
same collapse, resolved-target variant. RED pin:
backend/tests/integration/test_definition_links_pipeline_dual_unresolved_derivation.py
(committed @ b64d26e, asserts the SPEC'D 2-edge outcome). Fixed @ 2f27703 by
adding the deterministic proposition to both identity-key constructions.

## Completed-entry full detail (moved from contract at Phase-6 compression, 2026-07-29T15:00Z)

## Completed

- DL10 — mcp pin repair (M8): backend/pyproject.toml @ 821a597; `-k "mcp"` →
  7 passed, 0 failed (QA-reverified independently: 7 passed). mcp 2.0.0 →
  1.29.0 confirmed at the INSTALLED-PACKAGE level
  (`importlib.metadata.version("mcp")`), not just pyproject.toml's text.
  QA confirmed the 6 formerly-failing tests
  (`test_mcp_search_fetch_tools.py` x2, `test_mcp_tools_live.py` x2,
  `test_qa_regression_local_first_platform.py` x1,
  `test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries`
  x1) pre-date this sprint (added in sprint/2026-07-26-local-first-platform,
  commits 42f1a05/236a6fa/e450010) — genuine RED provenance, not
  sprint-authored tests. PASS.
- DL1 — Schema + assertion-type vocabulary (M1, M2): `app/models/article.py`,
  `app/models/definition.py`, `app/models/__init__.py`,
  `app/services/validation.py` @ 10ab30f; test_definition_links_models.py +
  test_definition_links_assertion_vocabulary.py → 8 passed, 0 failed
  (QA-reverified). PASS.
- DL2 — Stage 0 text normalization: `app/definition_links/normalize.py`
  @ 3f9b347; test_definition_links_normalize.py → 11 passed, 0 failed
  (QA-reverified). PASS.
- DL3 — Stage 1 article/section parsing: `app/definition_links/sections.py`
  @ 99e2992; test_definition_links_sections.py → 8 passed, 0 failed
  (QA-reverified). PASS.
- DL4 — Stage 2 term/definition extraction: `app/definition_links/extract.py`
  @ 7be404b; test_definition_links_extract.py → 10 passed, 0 failed
  (QA-reverified). PASS.
- DL5 — Stage 3 term matching + article-linking:
  `app/definition_links/matcher.py` @ 507ce85;
  test_definition_links_matcher.py → 10 passed, 0 failed (QA-reverified).
  PASS.
- DL6 — Stage 4 cross-law derivation + Stage 5 guards + M7 bidi guard:
  `app/definition_links/derivation.py`, `app/definition_links/guards.py`
  @ 474e34d; test_definition_links_derivation.py +
  test_definition_links_guards.py → 20 passed, 0 failed (QA-reverified).
  PASS. (QA note, non-blocking: `guards.py`'s `is_plain_quotation`,
  `is_rejectable_term`, `resolve_law_title` are unit-tested but never
  imported/called by `extract.py`/`derivation.py`/`pipeline.py` — only
  `is_bidi_degraded` is wired in. No current test/fixture exercises a
  false-positive this would have caught; flagged for future-sprint
  follow-up, not a blocker this cycle.)
- DL7 — M4 article-aware wiki ingestion: `app/definition_links/ingest.py`
  @ 1799c8b; test_definition_links_ingest.py → 4 passed, 0 failed
  (QA-reverified). Live-path (c) confirmed: `ingest_wiki_law` persists
  real `Article`+`SourceSpan` ORM rows that `pipeline.py` subsequently
  reads via `select(Article)...`/`session.get(SourceSpan, ...)`. PASS.
- DL8 — Persistence pipeline idempotency-key fix (cycle 2 QA-reverified):
  `app/definition_links/pipeline.py` @ 2f27703. PASS — cycle-1 RED pin green.
  E2E probe: `חוק הגנת הפרטיות_excerpt.wiki` line 17's 3-term clause now
  persists 3 DERIVES_FROM_LAW edges (one per term, all → `חוק המחשבים`),
  idempotent under the new key (rerun: 0 new rows). Regression:
  `test_three_term_shared_derivation_clause_persists_three_resolved_edges`.
- DL9 — M6 CLI `link-definitions`: `app/definition_links/cli.py` @ 7cf2fe6;
  test_definition_links_cli.py + test_definition_links_no_network_dependencies.py
  → 5 passed, 0 failed (QA-reverified). Live-path (a) confirmed by source
  read: `cli.py::main` calls `run_definition_linking` directly (no
  subprocess/reimplementation). Live-path (b) confirmed: created
  `Assertion`/`Definition` rows are visible via the EXISTING
  `GET /api/v1/assertions` route (already exercised by this item's own
  tests). `docs/RUNBOOK.md` updated @ cabda01. PASS.

## QA Notes — full transcripts (moved from contract at Phase-6 compression)

## QA Notes

- **2026-07-29T15:10Z QA cycle 1 (sonnet/high).** Independent evaluator
  pass (own numbers, not reused from Developer):
  `backend/.venv/bin/pytest backend/tests -v` → 374 passed, 0 failed;
  `npm --prefix frontend run test -- --run` → 62 passed (11 files), 0
  failed. No flakes.
  Per-item reverification (exact contract test commands): DL1 8p, DL2
  11p, DL3 8p, DL4 10p, DL5 10p, DL6 20p, DL7 4p, DL9 5p, DL10 7p — all
  match Dev Complete's claimed counts, 0 failed. DL8's own 8 tests also
  pass, but QA's own live-corpus probe + a new integration test exposed
  a spec violation not caught by the Developer's 8 tests (see below) →
  **DL8 FAIL**.
  Live-path traces: (a) PASS — `cli.py::main` calls
  `run_definition_linking` directly, confirmed by source read. (b) PASS
  — CLI-created `Assertion`/`Definition` rows visible via the existing
  `GET /api/v1/assertions` route (DL9's own tests already exercise this
  end-to-end; re-run and confirmed). (c) PASS — `ingest_wiki_law`
  persists real `Article`+`SourceSpan` rows that `pipeline.py` reads via
  `select(Article)...` / `session.get(SourceSpan, ...)`.
  Independent E2E probe (own script, scratch sqlite, real vendored
  fixtures, CLI invoked via subprocess): ingested 5 laws (24 articles) →
  `link-definitions` → 91 assertions / 92 definitions. G1 PASS (79
  USES_DEFINITION edges linking real articles to real extracted
  definitions, e.g. "נכס" §1→§2/§3/§7). G2 PASS ("חומר מחשב"/"מחשב"/"פלט"
  כהגדרתם [[בחוק המחשבים]] in חוק הגנת הפרטיות resolves DERIVES_FROM_LAW
  to the ingested `חוק המחשבים` document, naming both laws + term).
  Determinism PASS: 2 additional reruns produced byte-identical link sets
  and 0 new rows both times (91/92 → 91/92 → 91/92).
  **Manager-flagged edge (dual unresolved derivations, sprint log line
  14): CONFIRMED COLLAPSED.** `_create_assertion`'s idempotency key
  `(assertion_type, subject_entity_type, subject_entity_id,
  object_entity_type, object_entity_id)` omits the derivation's
  term/matched-text; two independently-unresolved `DERIVES_FROM_LAW`
  edges from the SAME Definition both key to `(..., Definition, <id>,
  None, None)` and collide — the second is silently dropped. Also
  reproduced on the REAL corpus in the RESOLVED-target variant: a
  single 3-term definition (`חוק הגנת הפרטיות_excerpt.wiki` line 17,
  "חומר מחשב"/"מחשב"/"פלט" all → `חוק המחשבים`) persists only 1
  DERIVES_FROM_LAW assertion instead of 3 (one per term, per the review
  doc's own worked example) — same root cause. `[QA-FAIL]` on DL8. RED
  test committed (never modifies implementation):
  `backend/tests/integration/test_definition_links_pipeline_dual_unresolved_derivation.py`
  — 1 failed as expected (proves the collapse; asserts the SPEC'D
  2-edge outcome, not a flip-to-red trap).
  Bug-fix pin check (DL10): the 6 formerly-failing mcp tests pre-date
  this sprint (git history: added in sprint/2026-07-26-local-first-platform
  @ 42f1a05/236a6fa/e450010) — genuine RED provenance — and now pass;
  `mcp` resolves to 1.29.0 (< 2.0) at the installed-package level.
  Regression tests added for every PASSED item (9 tests,
  `backend/tests/integration/test_qa_regression_definition_links.py`):
  DL1 nested-Definition ORM round trip, DL2 compound Stage-0
  normalization, DL5 three additional documented `מאגר מידע` surface
  forms, DL6 `כאמור בחוק` non-trigger, DL7 ingest-twice non-dedup, DL9
  missing-required-arg usage error, DL10 installed-package version
  check.
  Full suite with both new files: 384 collected, 383 passed, 1 failed
  (the intentional DL8 RED pin) — everything else green.
  Non-blocking observation (not a FAIL, no test currently exercises it):
  `guards.py`'s Stage 5.1/5.2 functions (`is_plain_quotation`,
  `is_rejectable_term`) and Stage 5.4's `resolve_law_title` are unit-
  tested but never imported by `extract.py`/`derivation.py`/
  `pipeline.py` — only `is_bidi_degraded` is wired into the live path.
  Deviations: none beyond the DL8 bounce. Escalations: none.
  Status set: qa-fail, current_role: developer, qa_cycles: 1.
- **2026-07-29T14:56:28Z QA cycle 2 (sonnet/high), DL8 re-verify only.**
  HEAD confirmed at 37208f7. Independent full evaluator (own numbers):
  `backend/.venv/bin/pytest backend/tests -v` → 384 passed, 0 failed;
  `npm --prefix frontend run test -- --run` → 62 passed (11 files), 0
  failed. No flakes.
  Commit 2f27703 confirmed: diff touches only `pipeline.py`, 2 lines
  added (deterministic `proposition` in both identity-key constructions).
  Cycle-1 RED pin (`test_definition_links_pipeline_dual_unresolved_derivation.py`)
  now green. E2E probe on real vendored fixtures: ingested
  `חוק המחשבים_stub.wiki` + `חוק הגנת הפרטיות_excerpt.wiki` into one
  matter — the 3-term shared clause at line 17 ("חומר מחשב"/"מחשב"/"פלט"
  כהגדרתם [[בחוק המחשבים]]) now persists exactly 3 `DERIVES_FROM_LAW`
  assertions, one per term, each naming its term and each resolving
  (`object_entity_type="Document"`) to the ingested `חוק המחשבים` row —
  confirms the cycle-1-corroborated resolved-target collapse is fixed.
  Idempotency: a second pipeline run over the same matter created 0 new
  assertions/definitions; persisted `(assertion_type, subject_entity_id,
  object_entity_id, proposition)` key sets identical across both runs.
  **DL8 PASS.** Regression test added:
  `test_three_term_shared_derivation_clause_persists_three_resolved_edges`
  in `test_qa_regression_definition_links.py` @ 69b1be6; full backend
  suite re-run with it included → 385 passed, 0 failed.
  DL8 moved Dev Complete → Completed (all 10 items now Completed).
  Deviations: none. Escalations: none.
  Status set: review, current_role: planner, qa_cycles: 2.

## Planner-era Context Dump archive (moved from contract at Phase-6 compression)

## Context Dump

Recon complete: see docs/sprint/sprints/2026-07-29-definition-links-review.md
(POC map, repo gaps, full deterministic algorithm, refinements R1-R9, open
questions — resolved by Manager rulings M1-M7 above).

**Planner pass complete (2026-07-29).** Venv built fresh inside this worktree
per repo-profile (`cd backend && python3.13 -m venv .venv && .venv/bin/pip
install -e '.[dev]'`); canary confirmed `import app` resolves to THIS
worktree's `backend/app/__init__.py`. Frontend `npm --prefix frontend
install` run (node_modules was missing).

**Fixtures vendored** (ruling M3, `backend/tests/fixtures/wiki_laws/`, 4
files + 2 synthetic, ~46KB total, well under the 500KB cap):
- `חוק להגנת רכוש מופקד.wiki` — full file (3.8KB), byte-identical copy from
  the POC corpus (`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/`)
  — clean small example (M3).
- `חוק הגנת הפרטיות_excerpt.wiki` — curated excerpt (§1, §3 definitions incl.
  nested sub-def + cross-law derivation, §8 usage w/ construct-state/plural
  inflections + local scoped def) — NOT byte-identical to the source file
  (trimmed per M3), but every included line is a verbatim quote from it.
- `חוק העונשין_excerpt.wiki` — curated excerpt (§34כד chapter-scoped
  הגדרות incl. qualifier-before-dash + list-form; §35/§35א local scoped
  defs; §51א second chapter-scoped הגדרות) — trimmed per the review doc's
  explicit instruction (full file is 492KB).
- `חוק הבנקאות (שירות ללקוח)_excerpt.wiki` — curated excerpt (§1 definitions
  incl. the `חוק הבנקאות` ambiguous-law-name edge case; §3 unquoted `(להלן -
  X)`; §7ו curly-quote/en-dash normalization case).
- `חוק המחשבים_stub.wiki` — small SYNTHETIC stub (hand-authored, not from
  the POC corpus) used only to seed a second, resolvable target law for the
  cross-law-derivation-resolved integration test.
- `degraded_bidi_sample.wiki` — small SYNTHETIC scrambled-word-order fixture
  (hand-derived by reversing each line's word order from the already-
  vendored clean `חוק להגנת רכוש מופקד.wiki`) for the M7 bidi guard — NOT
  sourced from `israeli-boi-directives` (out of this sprint's read-only
  scope; the path granted was `israeli-laws-wiki` only).

**Design decisions made while authoring tests** (Planner's call per M2's
"exact names/columns Planner's call" precedent — none needed escalation):
- Assertion-type names: `USES_DEFINITION`, `DERIVES_FROM_LAW`.
- `Definition.terms` stored as a JSON list column (not a join table) — a
  deliberately minimal additive design for this sprint's scope.
- `articles.source_span_id` is NOT NULL (every ingested article always gets
  a backing `SourceSpan`, so `AssertionEvidence` needs no schema change).
- `DefinitionCandidate` carries `source_article_number`/`source_chapter` as
  provenance fields (`None` from extract.py itself; filled by pipeline.py)
  so `matcher.py` can enforce chapter/local scope isolation.
- Confidence tiering left as a RANGE, not a magic number: USES_DEFINITION
  ≥0.9; DERIVES_FROM_LAW resolved ≥0.8 and strictly greater than the
  unresolved case's confidence (M2's "structural ≥0.9 / prose-derived
  lower" gives the shape, not exact constants).
- A leading Hebrew prefix letter (Stage 3.1) is part of the MATCHED SPAN
  itself, not a separate lookbehind — `match.group(0)` for `במאגר המידע`
  is the full prefixed string.

**Caveat found in the real corpus, encoded into a test on purpose**:
`חוק העונשין` §34כד's list-form entry `"עובד הציבור" -` has every numbered
sub-item (1)-(11) ALREADY ending in its own `;` — the dossier's "no closing
`;` until the final item" description undersells the real trap: a naive
"stop at the first `;`" parser truncates at item (1). See
`test_extract_list_form_definition_spans_to_the_next_top_level_entry`.

**Pre-existing, OUT-OF-SCOPE environment anomaly found (not caused by this
sprint, not fixed by this sprint)**: `backend/pyproject.toml`'s `mcp>=1.0`
constraint resolves to `mcp==2.0.0` in a fresh venv, which removed
`mcp.server.fastmcp` — `app/mcp/server.py` (unrelated pre-existing module)
now fails to import. 6 pre-existing tests fail because of this
(`test_mcp_search_fetch_tools.py` x2, `test_mcp_tools_live.py` x2,
`test_qa_regression_local_first_platform.py` x1,
`test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries`
x1) — confirmed unrelated to definition-links (no file these tests touch
was changed by this track). Full-evaluator green will require someone to
pin `mcp` to a compatible 1.x range or update `app/mcp/server.py`'s import
— flagged for the Manager/director, out of this Planner's write-scope
(pyproject.toml/app/mcp are not test files).
- 2026-07-29T15:20Z POC corpus verifier (director-requested, review-phase ops probe) → sonnet/medium; Haiku considered: yes, rejected — corpus-scale triage/failure classification needs judgment. Read-only vs repo+POC; scratch DB in session scratchpad.
- 2026-07-29T16:20Z POC corpus verifier — DONE. Full-corpus run + determinism PASS; 3 confirmed engine issues (1 HIGH, 2 MEDIUM); report persisted to docs/sprint/sprints/2026-07-29-definition-links-poc-run.md with manager addendum (headline numbers SQL-verified; Issue-2 radius corrected to 2,981 edges corpus-wide).
- 2026-07-29T17:31Z sprint re-opened (director: "fix, then merge"); ruling M9 + gates G5-G7 added; planner cycle-2 (pending spawn) → sonnet/high; Haiku considered: no — forbidden for Planner.
- 2026-07-29T18:02Z planner cycle 2 → DONE @ f3966c4 (DL11-DL13, 28 RED, 2 fixtures; sweep zero re-points). Manager verified: containment PASS, RED spot-run 28 failed/22 passed as claimed. DL11-DL13 developer (pending spawn) → sonnet/medium; Haiku considered: yes, rejected — multi-module engine changes (matcher/pipeline/extract/derivation), regex judgment.
- 2026-07-29T18:15Z DL11-DL13 developer → DONE @ 67be162; manager checks: containment PASS (4 owned files + contract), full diff read PASS (fixes match M9 exactly, matched_text preserved raw), probe 69 passed. Manager flag for QA cycle 3: matcher claimed_spans still keyed by article.number — probe span-suppression across duplicate-numbered articles (same G5 family, distinct mechanism). qa cycle 3 (pending spawn) → sonnet/high; Haiku considered: no — policy.
- 2026-07-29T21:45Z QA cycle 3 (sonnet/high) → DONE. Independent evaluator: 416 backend + 62 frontend passed, no flakes (run twice). DL12 PASS: 21 scoped tests match; own fresh-corpus probe (`פקודת רופאי השיניים.wiki:22`, not in Dev's fixtures) confirms the repeal guard rejects the real entry while siblings survive. DL13 PASS: 16 scoped tests match; own fresh-corpus probe (`צו בנק ישראל (מידע בעניין יתרות ניירות ערך).wiki:27`, not in Dev's fixtures) confirms the widened `_LAW_REF_RE` resolves a different target-law family. DL11 FAIL: manager-flagged probe confirmed — `matcher.py`'s `claimed_spans` is keyed by `article.number`; two articles sharing a number, each with a genuine same-offset use of a term in their OWN body, cross-suppress (only 1 of 2 expected edges produced). RED pin committed @ 57fe773 (`test_definition_links_matcher.py`, `-k cross_suppress`, 1 failed by design). Full-corpus before/after re-run (fresh ingest+link over all 6,133 laws, method reused from cycle-1's pocrun/ scripts, adapted into a new `…/scratchpad/pocrun2/`; run1 1150.3s ≈ baseline's 1106.5s, run2 determinism 0 new rows): (a) USES_DEFINITION edges citing a נמחקה-marker definition 2,981→1,063 — 0 definitions in the full corpus DB now match DL12's exact pure-repeal-marker shape (guard works perfectly for every corpus-documented shape); residual fully explained: 16 edges from 3 definitions with an unobserved "כהוראת שעה" (temporary-provision-with-date-range) wrapping variant not in DL12's documented scope, plus 1,047 edges from 91 definitions where the marker is one sub-item among several real list items in the same entry (never "solely" a marker at the entry level — correctly out of scope per M9(b)). (b) unresolved DERIVES_FROM_LAW 1,565→1,086 (−479, comfortably ≥100); concrete verified example: `"תאגיד בנקאי" כהגדרתו חוק הבנקאות (רישוי), התשמ"א-1981` (source doc `היתר הפיקוח על המטבע`) now resolves to Document `חוק הבנקאות (רישוי)` — unresolved in the cycle-1 baseline's top-unresolved list, absent from cycle-3's. (c) money-laundering-order dual-"17" case verified at full-corpus scale: the real document has two Article rows numbered "17" (one real, quote_text len 1359; one empty, len 0) — all 13 persisted "פעולה" USES_DEFINITION edges for this document cite ONLY the real, non-empty Article, confirming DL11's article_index attribution fix holds at scale for the exact named case (the manager-flagged registry bug is separate/narrower — requires BOTH duplicates non-empty with colliding offsets, not this document's shape). (d) determinism: run2 created 0 new assertions/0 new definitions, identical 277 degraded-skip count — PASS. Regression: 2 new tests (fresh-corpus DL12/DL13 probes formalized) @ b47987f. Contract: DL12/DL13 → Completed (12/13); DL11 bounced to Next Steps with RED pin. Status qa-fail, current_role developer, qa_cycles 3. Full transcript: this log entry (see docs/sprint/sprints/2026-07-29-definition-links.md QA Notes for the compressed version).
