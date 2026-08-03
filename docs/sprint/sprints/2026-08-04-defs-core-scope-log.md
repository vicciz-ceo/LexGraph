# Sprint log — 2026-08-04-defs-core-scope (append-only)

Panel workflow per program ruling P-R3: Planner ⇄ Developer(s) ⇄ QA speak
THROUGH the sub-manager. Every question, answer, and ruling is recorded here.
Never auto-loaded; never pasted into director-facing reports.

---

## 2026-08-04 — Sub-manager session 1 (Opus/high)

**Setup**

- Worktree: `/Users/nerya/LexGraph-wt/defs-core-scope`, branch
  `claude/defs-core-scope`, created from `origin/main` @ `ba1b398`.
- Backend venv built in the worktree (`backend/.venv`, python3.13,
  `pip install -e '.[dev]'`); verified it imports the WORKTREE's
  `backend/app/__init__.py`, not the main checkout's (known trap).
- `git config user.email` verified =
  `256402398+vicciz-ceo@users.noreply.github.com` (GH007 guard).
- Frontend deps installed via `npm --prefix frontend install`.
- **Baseline (C5 datum, manager-run, before any code change):**
  `backend/.venv/bin/pytest backend/tests -q` → **641 passed, 18 warnings in
  18.82s**, exit 0, at `ba1b398`. Frontend baseline run separately.

**Manager pre-brief diagnosis (read-only, CodeGraph first)**

`codegraph explore "matcher._in_scope link_articles_to_definitions
_determine_scope _CHAPTER_SCOPE_TRIGGERS Definition.scope …"` confirmed the
recon dossier §1 verbatim and surfaced the C1 design problem precisely:

```
matcher.py:104-110
def _in_scope(definition, article) -> bool:
    scope = definition.scope
    if scope == "chapter":
        return article.chapter == definition.source_chapter
    if scope == "local":
        return article.number == definition.source_article_number
    return True  # law-wide (or any other/unspecified scope)
```

Enforcement granularity today is exactly {chapter, article(=`local`),
law-wide}. `link_articles_to_definitions` (matcher.py:140-161) iterates
`for article in articles` and filters whole articles; a scope BELOW article
level has no representation on either side of the comparison — neither on
`Definition` (no subsection column) nor on the matcher's `Article`. C1's
subsection granularity is therefore genuinely new design, exactly as the
contract states, and the manager expects the Planner to reach an
architecture fork here. Blast radius noted: `link_articles_to_definitions`
has 11 call sites in `pipeline.py` and is covered by
`backend/tests/unit/test_definition_links_matcher.py` +
`backend/tests/integration/test_us_profile_definitions_section_end_to_end.py`;
`_determine_scope` and `_CHAPTER_SCOPE_TRIGGERS` have NO covering tests
(codegraph blast-radius warning) — a hole the Planner must close.

**Manager standing instruction to the panel (recorded once, applies to all
roles):** CodeGraph before grep/find/Read for all code understanding —
`codegraph explore "<symbols or question>"` from the worktree root.

---

## Panel dialogue

### Round 1 — Manager → Planner (spawn)

Brief summary: publish the `## Seam spec (published)` contract section FIRST
(critical path, 6+ panels blocked on it), commit+push it, and only then
author RED tests for gates C1–C5. Full brief in the spawn record below.

