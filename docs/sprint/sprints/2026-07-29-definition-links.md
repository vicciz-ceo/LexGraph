---
id: "2026-07-29-definition-links"
status: planning
current_role: planner
branch: sprint/2026-07-29-definition-links
locked_by: "claude-code:planner"
locked_at: 2026-07-29T13:24:00Z
last_agent: "claude-code:manager"
last_updated: 2026-07-29T13:24:00Z
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
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

## Next Steps

(Planner to fill.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

Recon complete: see docs/sprint/sprints/2026-07-29-definition-links-review.md
(POC map, repo gaps, full deterministic algorithm, refinements R1-R9, open
questions — resolved by Manager rulings M1-M7 above). Planner: turn gates
G1-G4 + refinements R1-R9 into items with RED tests. Worktree has NO backend
venv — build a fresh one per repo-profile venv_setup and verify
`import app` resolves inside THIS worktree before trusting any run.
