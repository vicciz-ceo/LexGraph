---
id: "2026-07-29-definition-links"
status: planning
current_role: planner
branch: sprint/2026-07-29-definition-links
locked_by: null
locked_at: null
last_agent: "claude-code:manager"
last_updated: 2026-07-29T13:10:42Z
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

## Next Steps

(Planner to fill.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

Sprint opened by manager 2026-07-29. Recon of the POC directory and repo
state runs next; Planner brief will reference the recon dossier at
docs/sprint/sprints/2026-07-29-definition-links-review.md (to be created).
