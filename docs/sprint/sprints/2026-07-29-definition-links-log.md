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
