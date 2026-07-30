# Recon dossier — 2026-07-30-deterministic-assertions

Two read-only recon passes (2026-07-30). Verified findings for the Planner;
`file:line` pointers were reported by recon agents — re-verify before pinning
tests to exact lines.

## LexGraph repo (this repo)

- Status is a plain string on `backend/app/models/assertion.py:46`; observed
  vocabulary: draft, proposed, accepted, rejected, disputed,
  revision_requested, superseded, withdrawn. No enum; no "deterministic"
  flag — derivation is encoded in `origin` (line 45): `system_generated`
  (deterministic pipelines), `model_suggested` (AI heuristics),
  `user_suggested` (humans).
- Deterministic definition-links pipeline assigns "proposed":
  `backend/app/definition_links/pipeline.py:49` (`_STATUS = "proposed"`),
  applied at line 230 with `origin="system_generated"`. This is the
  LexGraph-side violation to fix.
- User submissions: `backend/app/routers/assertions.py:526,534` —
  `save_as: Literal["draft","proposed"]`, origin `user_suggested`. NOT
  deterministic; out of mandate scope (flagged to director).
- AI heuristics: `backend/app/enrich/suggester.py` → `model_suggested`;
  "proposed" remains CORRECT there (the reserved use).
- Article-mentions-article detection: none exists in this repo.
- Tests pinning "proposed" (stale-pin sweep targets):
  `backend/tests/unit/test_graph_projection.py:47,62,65`;
  `backend/tests/integration/test_definition_links_cli.py:33` (asserts all
  pipeline output is "proposed" — direct collision with this sprint);
  `frontend/src/components/__tests__/AssertionCard.test.tsx:13,25` and
  `AssertionReviewPanel.test.tsx` (proposed fixtures — likely legitimate,
  "proposed" stays a valid status for model_suggested; sweep decides).
- Articles: `backend/app/models/article.py:26-36`; article text lives on
  `backend/app/models/source_span.py:25` (`quote_text`). Laws:
  `backend/app/models/document.py`.

## lexgraph-assertions-db (POC builder, "/Users/nerya/AI for others/lexgraph-assertions-db")

- Own git repo, NO remote. Sprint baseline of director WIP: `984593b`
  (provisions build +700 lines, graph script, tests, README).
- Single status choke point: `build_assertions_db.py:1122`
  (`status="proposed"` inside `make_entity_assertion()`, lines ~1095-1180;
  origin="system_generated" at 1121). ALL builder emissions are
  deterministic rule extraction.
- Emitted types (all currently "proposed"): AMENDED_BY 22,750 |
  CANCELLED_BY 13 | DEFINES 41,864 | ENACTED_UNDER 4,555 |
  INCORPORATES_DEFINITION_FROM 8,766 | REFERENCES 14,983 |
  REFERENCES_DEFINITION 5,814 | REFERENCES_PROVISION 63,891. Total 162,636
  assertions; provisions 129,828; defined_terms 41,864; documents 6,384;
  evidence 166,671.
- DB `status` values currently: only "proposed" (100%).
- `generate_shareable_graph.py:207,242` — SVG labels say "proposed
  rule-extracted … status=proposed"; must follow the status change.
- Intra-document article→article mentions: NOT detected today.
  REFERENCES_PROVISION exists but recon reports no same-document
  provision→provision mention edges; Planner must characterize exactly what
  REFERENCES_PROVISION captures before designing the new pass (corpus is
  Hebrew; section references like סעיף N).
- Inputs: israeli-laws-wiki (6,133 laws) + israeli-boi-directives.
  Tests: `tests/test_provision_extraction.py` only (extraction unit tests).
  Builder imports LexGraph backend models from /Users/nerya/LexGraph —
  interpreter must be the LexGraph backend venv (Planner confirms).

## Manager rulings recorded from this recon

- R2 (scope, resolved): dual-repo. LexGraph receives the status-semantics
  fix for its deterministic pipeline (+ test sweep). POC builder receives
  the status fix AND the intra-law article-mention pass — the director's
  verification target is the POC DB. Mention derivation inside the LexGraph
  app pipeline is explicitly OUT of this sprint (surfaced to director as a
  possible follow-up).
- R3 (replacement status): deterministic assertions get **"accepted"** —
  they need no human rating (director's stated semantics); derivation
  method stays encoded in origin=system_generated; reviewed_by/reviewed_at
  remain null. "accepted" is already in the status vocabulary of both
  repos.
