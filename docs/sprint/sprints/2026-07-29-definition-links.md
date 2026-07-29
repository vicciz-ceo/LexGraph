---
id: "2026-07-29-definition-links"
status: dev-complete
current_role: qa
branch: sprint/2026-07-29-definition-links
locked_by: "claude-code:qa"
locked_at: 2026-07-29T18:51:49Z
last_agent: "claude-code:developer"
last_updated: 2026-07-29T18:51:49Z
lint: "PASS 178 2026-07-29T15:01:35Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 13
completed_items: 12
dev_complete_items: 1
qa_cycles: 3
prd_sections: []
design_sections: []
---

# Sprint: Definition-based article linking (2026-07-29)

Director mandate (verbatim intent): refine the LexGraph repo based on what was
done in the POC found in `/Users/nerya/AI for others` (subprojects:
AI-for-Lawyers, israeli-boi-directives, israeli-laws-wiki,
lexgraph-assertions-db); add **wholly deterministic** code that (a) connects
articles within a law via the definitions the law contains, and (b) connects
laws to each other when a definition is derived from another law. Research the
approach first, then execute. Broad mandate — manager proceeds autonomously,
gates reported to director.

## Draft acceptance gates (manager, pending recon refinement)

- G1: Given a law's text containing a definitions section, the system
  deterministically extracts each defined term and links every article in that
  law that uses the term to the definition — same input always yields the same
  links, no LLM/ML in the path.
- G2: When a definition explicitly derives from another law ("כהגדרתו
  בחוק..." / "as defined in..."), the system creates a law-to-law link that
  names both laws and the term.
- G3: POC learnings from AI-for-others are reflected in the repo (data model
  / parsing conventions), with the specifics enumerated by recon.
- G4: Full evaluator (backend pytest + frontend vitest) green.
- G5 (POC finding 1): a USES_DEFINITION link's cited article is the article
  where the match actually occurred, even when a document reuses the same
  article number (no cross-attribution; the money-laundering-order dual
  "17" case resolves to the article containing the text).
- G6 (POC finding 2): definitions whose body is only a repeal marker
  ((נמחקה) etc.) produce no Definition rows and no links.
- G7 (POC finding 3): cross-law derivations resolve when the target law's
  official title carries a parenthetical qualifier, and trailing sentence
  punctuation never blocks resolution.

## Manager rulings

- M1 (schema): director mandate requires article-level linking → ADDITIVE schema
  extension authorized: new `Article` + `Definition` tables; existing tables
  unchanged. "Frozen post-F1" yields to the explicit new mandate; reported to
  director as a deviation.
- M2 (representation): structure lives in `Article`/`Definition`; the LINKS are
  Assertions with new vocabulary entries (uses-definition, derives-from-law —
  exact names Planner's call, consistent with existing ALLOWED_ASSERTION_TYPES
  style), origin=system_generated, status=proposed, POC confidence tiering
  (structural ≥0.9 / prose-derived lower).
- M3 (fixtures): vendor a SMALL slice of israeli-laws-wiki (the edge-case files
  named in the review doc, trimmed if huge; target <500KB total) into
  backend/tests/fixtures/; never the full corpus; tests read fixtures offline.
- M4 (ingestion): never import from the POC path at runtime; port
  normalize_title/WIKILINK_RE *patterns* into repo code; new article-aware
  wiki-format parser lives in-repo.
- M5 (unresolved cross-law derivations): emit with target_law_id=null + raw
  matched string preserved, at reduced confidence — recorded exception to the
  POC drop-not-guess rule (string preserved, resolution not fabricated).
- M6 (surface): CLI `link-definitions` required (parity with enrich); API route
  optional stretch; NO frontend UI this sprint.
- M7 (degraded text): bidi-sanity guard required at linker input; degraded
  files are flagged + skipped, never auto-corrected.
- M8 (env repair): `mcp>=1.0` resolves to 2.0.0 which removed
  `mcp.server.fastmcp`, breaking 6 pre-existing tests (manager-verified at
  app/mcp/server.py:39). Ruled: minimal pin `mcp>=1.0,<2.0` as item DL10;
  mcp 2.x migration deferred to a future sprint. Supersedes Planner chip
  task_ad884976.
- M9 (re-open, director-approved "fix then merge" 2026-07-29): sprint
  re-opened for the 3 POC-verified findings (see
  2026-07-29-definition-links-poc-run.md §8+§12). Fix directions: (a)
  Issue 1 — attribution by article IDENTITY, not number: additive
  `article_index` on the matcher edge; pipeline maps by index; number kept
  as provenance only. (b) Issue 2 — extraction rejects candidates whose
  normalized body is solely a parenthesized repeal marker (only forms
  observed in corpus, e.g. נמחקה/נמחק/בוטלה/בוטל inflections). (c) Issue 3
  — `_LAW_REF_RE` allows one balanced parenthetical in the law name and
  strips trailing sentence punctuation before title matching; the greedy
  trailing-clause swallow (spot-check U2) is fixed only if achievable by a
  deterministic boundary rule, else documented as known-remaining. New
  gates G5-G7; determinism and existing green tests preserved.

## Next Steps

(empty — DL11 fix cycle complete; awaiting QA cycle 4. Cycle-3 bounce
rationale: see -log.md.)

## Stale-pin sweep

Swept `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/e2e/`,
`frontend/src/components/__tests__/*.test.tsx` for strings this track's items
change (`ALLOWED_ASSERTION_TYPES` membership/count, model/table-count
assertions, fixture placeholder texts, `app/models/__init__.py::__all__`,
`Base.metadata`/`create_all` assumptions, entity_type enumerations in graph
projection tests, assertion-type `<select>` dropdowns in frontend forms).

Result: **none** — additive feature, no hits.
- No test anywhere asserts an exact `ALLOWED_ASSERTION_TYPES` count/set
  (`grep -rn "len(ALLOWED_ASSERTION_TYPES)\|ALLOWED_ASSERTION_TYPES =="` — 0
  hits), so adding `USES_DEFINITION`/`DERIVES_FROM_LAW` breaks nothing.
- No test asserts a fixed model/table count (`grep -rn "13 table\|model_count"`
  — 0 hits) — F1's own docstring narrative ("13 tables") is prose, not a
  test assertion.
- `tests/unit/test_graph_projection.py` uses opaque entity ids/types with no
  closed-set assertion — new "Article"/"Definition" entity types are inert
  to it.
- `frontend/src/components/AssertionSuggestionForm.tsx`'s `assertionType`
  field is free-text (`useState("")` + plain input), not an enumerated
  `<select>` — confirmed via source read, not just grep. The only
  hardcoded `<select>` in that file is unrelated (`evidence_role`:
  supports/contradicts). Matches M6 (no frontend UI this sprint): zero
  frontend files need touching.
- `tests/conftest.py` gained two new raw-SQL seed helpers (`seed_article`,
  `seed_definition`) — additive, no existing helper signature changed.

### Cycle 2 (DL11-DL13, ruling M9)

Swept ALL test roots (`backend/tests/unit/`, `backend/tests/integration/`,
`backend/tests/e2e/`, `frontend/src/**/__tests__/`) for pins on
`ArticleUsesTermEdge` fields, `article_number` usage in
matcher/pipeline/QA-regression tests (explicitly including
`test_qa_regression_definition_links.py` and
`test_definition_links_pipeline_dual_unresolved_derivation.py` per the
brief), and any `_LAW_REF_RE`/`target_law_name` pins that DL13's regex
widening could affect.

Result: **none** — zero re-points needed; all three fixes are
behavior-preserving for every existing pinned scenario:

- `grep -rn "article_number\|ArticleUsesTermEdge\|number_to_article"` across
  `backend/tests/` (pre cycle-2 additions) hit only
  `test_definition_links_matcher.py` (reads `.article_number` off
  edges — an "at least" field per its own docstring, unaffected by the
  additive `.article_index`) and `test_definition_links_extract.py`
  (`.source_article_number`, a DIFFERENT, unrelated provenance field on
  `DefinitionCandidate`). **Zero hits** in
  `test_qa_regression_definition_links.py` or
  `test_definition_links_pipeline_dual_unresolved_derivation.py` —
  confirmed directly, not inferred.
- No existing matcher/pipeline test constructs an `ArticleUsesTermEdge`
  directly (all obtain edges via `link_articles_to_definitions`/
  `run_definition_linking`'s return value) and none exercises a
  duplicate-numbered-article scenario — every existing fixture/synthetic
  test has at most one article per number per document, so switching
  attribution from number-keyed to index-keyed changes nothing observable
  for any of them (verified by running the full suite post-change-authoring
  and diffing failures against exactly the 28 new RED tests, 0 unexpected
  breaks).
- DL13's `_LAW_REF_RE` widening (allow one balanced parenthetical + strip
  trailing punctuation) only changes behavior for input text containing a
  `(` immediately after a law-reference base name, or a law reference
  ending directly in sentence punctuation with no `,`/`;` boundary. Checked
  every existing `detect_cross_law_derivations` call site's input text
  (unit tests + the 3 vendored pipeline fixtures that reach Stage 4:
  `חוק להגנת רכוש מופקד.wiki`, `חוק הגנת הפרטיות_excerpt.wiki`, `חוק
  המחשבים_stub.wiki`) — none contains a paren-adjacent or
  punctuation-terminated law reference, so no existing resolved/unresolved
  count changes.
- Full suite run post-authoring: `backend/.venv/bin/pytest tests -q` →
  **388 passed, 28 failed** (the 28 are exactly the new cycle-2 RED tests
  — see `## Next Steps`; 0 previously-green tests broke).

## Dev Complete

- DL11 — matcher claimed-spans keyed by article identity (fix, cycle 4):
  backend/app/definition_links/matcher.py @ e0ec9bb (2 lines, as ruled);
  cycle-3 RED pin green; dev full backend 419 passed; manager probe 26 green.

(empty — QA cycle 3 resolved DL12/DL13: both moved to Completed (12/13);
DL11 bounced back to Next Steps above, qa_cycles: 3.)

## Completed

- DL12 — repeal-marker guard (G6, ruling M9(b)) @ 0926323. Probe: 21
  passed. QA fresh-corpus probe (פקודת רופאי השיניים, not in Dev's
  fixtures) confirms; full-corpus: 0 exact-shape marker definitions
  survive (2,981→1,063 residual, fully explained — see QA Notes). PASS.
- DL13 — law-name capture fix (G7, ruling M9(c)) @ 9ab1c09. Probe: 16
  passed. QA fresh-corpus probe (צו בנק ישראל, not in Dev's fixtures)
  confirms; full-corpus unresolved DERIVES_FROM_LAW 1,565→1,086 (-479),
  concrete חוק הבנקאות (רישוי) resolution verified. PASS.
- DL10 — mcp<2.0 pin (M8) @ 821a597. Probe: `-k "mcp"` 7 passed; RED
  provenance pre-sprint (log). Regression: installed-version check. PASS.
- DL1 — Article/Definition models + vocabulary @ 10ab30f. Probe: 8 passed.
  Regression: nested-Definition ORM round trip. PASS.
- DL2 — Stage 0 normalization @ 3f9b347. Probe: 11 passed. Regression:
  compound normalization chain. PASS.
- DL3 — Stage 1 article parsing @ 99e2992. Probe: 8 passed. Regression: QA
  suite (test_qa_regression_definition_links.py). PASS.
- DL4 — Stage 2 extraction @ 7be404b. Probe: 10 passed. Regression: QA suite
  (same file). PASS.
- DL5 — Stage 3 matcher @ 507ce85. Probe: 10 passed. Regression: 3 extra
  מאגר מידע surface forms. PASS.
- DL6 — Stage 4 derivation + guards @ 474e34d. Probe: 20 passed. Regression:
  כאמור בחוק non-trigger. PASS (guards partially unwired — see log). 
- DL7 — Article-aware ingestion @ 1799c8b. Probe: 4 passed, live path traced.
  Regression: ingest-twice non-dedup. PASS.
- DL8 — Pipeline identity-key fix @ 2f27703. Probe: 3-term clause → 3 edges,
  rerun 0 new rows. Regression: three_term_shared_derivation_clause. PASS.
- DL9 — CLI link-definitions @ 7cf2fe6. Probe: 5 passed, rows visible via
  GET /api/v1/assertions. Regression: missing-arg usage error. PASS.

## Evaluation Notes

DL1-DL9 all Dev Complete. Scoped track (unit + integration
`test_definition_links_*`): 84 passed, 0 failed (matches the pre-verified
RED baseline count exactly — every formerly-RED test now green, none
weakened).

Full authoritative pass:
- `backend/.venv/bin/pytest backend/tests -v` → **374 passed, 0 failed**
  (includes the 84 definition-links tests plus the 6 previously-broken
  `mcp` tests, repaired by DL10's `mcp<2.0` pin).
- `npm --prefix frontend run test -- --run` → **62 passed** (11 test
  files), unchanged from baseline — no frontend files touched (M6: no
  frontend UI this sprint).

Deviations from brief: none. Escalations: none — no Planner test looked
wrong or under-specified; every pinned public API (module paths, function
signatures, return shapes) in the RED tests was implementable as written.

### Cycle 2 (DL11-DL13, ruling M9)

DL11-DL13 all Dev Complete. Baseline confirmed 28 failed, 388 passed before
any change. Scoped per item, iteratively green: DL11 13 passed; DL12 21
passed; DL13 16 passed — all 28 formerly-RED cycle-2 tests now green, 0
weakened, 0 unexpected breaks against the pre-existing 388.

Full authoritative pass:
- `backend/.venv/bin/pytest backend/tests -v` → **416 passed, 0 failed**
  (388 + 28).
- `npm --prefix frontend run test -- --run` → **62 passed** (11 test
  files), unchanged — no frontend files touched (M6: no frontend UI this
  sprint).

Deviations from brief: none. Escalations: none — all three M9 fix
directions (additive `article_index`, repeal-marker guard, `_LAW_REF_RE`
parenthetical widening + trailing-punctuation strip) were implementable
exactly as specified. Greedy trailing-clause swallow (poc-run.md §9 U2)
confirmed left KNOWN-REMAINING per M9(c)'s explicit allowance — no
deterministic, corpus-grounded boundary rule found; no test was written for
it (matches contract).

## QA Notes

- **2026-07-29T15:10Z QA cycle 1 (sonnet/high).** Independent evaluator: 374
  backend + 62 frontend passed, no flakes. 9/10 PASS with per-item probes
  matching claimed counts; live paths traced (CLI→pipeline, rows via GET
  /api/v1/assertions, ingest→pipeline). E2E on 5 real laws: 91 assertions /
  92 definitions, deterministic over 3 runs. DL8 FAIL — identity-key collapse
  (dual-unresolved + 3-term resolved variants); RED pin @ b64d26e; 9
  regression tests @ d98f6ab. Full transcript: 2026-07-29-definition-links-log.md.
- **2026-07-29T14:56Z QA cycle 2 (sonnet/high), DL8 only.** Independent
  evaluator: 384 backend + 62 frontend passed, no flakes. Fix 2f27703
  diff-confirmed (pipeline.py, 2 lines); cycle-1 RED pin green; the 3-term
  clause now persists 3 resolved edges; rerun creates 0 new rows. DL8 PASS →
  Completed (10/10). Regression @ 69b1be6. Status review, qa_cycles 2. Full
  transcript: 2026-07-29-definition-links-log.md.
- **2026-07-29T21:45Z QA cycle 3 (sonnet/high), DL11-DL13.** Evaluator 416
  backend + 62 frontend, no flakes (twice). DL12/DL13 PASS (own
  fresh-corpus probes beyond Dev's fixtures). DL11 FAIL — manager-flagged
  `claimed_spans` cross-suppression (see Next Steps); RED pin @ 57fe773.
  Full-corpus before/after (pocrun2, fresh ingest+link): נמחקה-edges
  2,981→1,063 (0 exact-shape defs remain, residual explained); unresolved
  DERIVES_FROM_LAW 1,565→1,086 (-479); dual-"17" 13/13 correct at scale;
  determinism PASS (0 new rows). Regression @ b47987f. qa-fail, cycles 3.

## Context Dump

QA cycle 3: 12/13 items Completed, DL11 bounced (qa_cycles 3, status
qa-fail, current_role developer). Evaluator green apart from the
intentional DL11 RED pin (418 backend incl. 1 designed fail + 62
frontend). Full-corpus re-verification (pocrun2, 6,133 laws, ~19min):
DL12/DL13 fixes confirmed at scale (see QA Notes); DL11's core
attribution fix (article_index) also confirmed at scale for the named
dual-"17" case, but the manager-flagged claimed_spans registry bug is
separate and open. Follow-ups for the next Developer pass: (1) fix
`claimed_spans` keying in `matcher.py` to be per-article, not per-number
(DL11 reopen); (2) guards.py Stage-5 helpers partially unwired into the
live path (see log); (3) mcp 2.x migration deferred (M8); (4) no Alembic
migration — new tables rely on metadata create_all; (5) optional API
route + frontend UI for definition links (M6 stretch); (6) bulk-corpus
ingestion CLI out of scope; (7) greedy trailing-clause swallow (poc-run.md
§9 U2) left KNOWN-REMAINING per M9(c) — no test written, no deterministic
fix found. Worktree venv at backend/.venv. Recon dossier:
2026-07-29-definition-links-review.md; history: -log.md; corpus
verification: 2026-07-29-definition-links-poc-run.md.
