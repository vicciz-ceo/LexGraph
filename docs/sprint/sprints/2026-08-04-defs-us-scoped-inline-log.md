# Panel log — sprint 2026-08-04-defs-us-scoped-inline

Append-only. Panel members (Planner / Developer / QA) speak to one another
THROUGH the sprint manager; every exchange is recorded here (program ruling
P-R3). Manager rulings for this sprint are numbered `S-Rn`.

---

## 2026-08-04 — Manager: sprint opened

Workspace: `/Users/nerya/LexGraph-wt/defs-us-scoped-inline`, branch
`claude/defs-us-scoped-inline` off `origin/main` (`83532fe`). Own backend venv
built (python3.13, `pip install -e '.[dev]'`, `import app` OK). Git identity
verified `256402398+vicciz-ceo@users.noreply.github.com`.

CodeGraph note for all panel agents: the `.codegraph/` index lives at
`/Users/nerya/LexGraph` (the program manager's checkout), NOT in this
worktree. Run `codegraph explore "<question>"` from `/Users/nerya/LexGraph`,
or pass `projectPath=/Users/nerya/LexGraph` to the MCP tool. The indexed tree
is the same code this branch starts from. CodeGraph BEFORE grep/find/Read.

### Manager architecture read (verified against on-disk source, not assumed)

- `run_definition_linking` (`backend/app/definition_links/pipeline.py:311`) is
  the live-path entry point. Stage 2 is `pipeline.py:386-442`.
- The F1 hook is the `else:` branch at `pipeline.py:436-442`: for an article
  whose heading is NOT a definitions heading, the pipeline calls
  `extract_local_definitions` / `extract_adhoc_definitions` (`extract.py:183`,
  `:202`) unconditionally for EVERY profile, including US. Both are
  Hebrew-regex-only (`extract.py:28-33`), so every US article takes this
  branch and yields zero candidates. That is family 1's exact root cause,
  re-confirmed live rather than taken from the dossier.
- Scope enforcement is `matcher._in_scope` (`matcher.py:104-110`): `"chapter"`
  → `article.chapter == definition.source_chapter`; `"local"` →
  `article.number == definition.source_article_number`; anything else
  (including `"law-wide"`) → unrestricted. There is **no subsection or part
  granularity today** — `Article` (`backend/app/models/article.py:23`) carries
  only `number`, `heading`, `chapter`. Family 1's triggers name section,
  subsection, chapter AND part, so finer granularity is core's to deliver.
- Vendored-fixture convention already exists:
  `backend/tests/fixtures/us_statutes/*.json` (list of raw corpus row dicts,
  e.g. `de_sample_rows.json`). Tests read these, never the HF snapshot.

### S-R1 — Test targets are chosen to not depend on core's unpublished API

Core sprint `2026-08-04-defs-core-scope` has NOT published its `## Seam spec`
yet (checked `origin/claude/defs-core-scope` @ `5b93ef8` — the only match for
"Seam spec" in that contract is the promise to publish one). Rather than
block, the Planner authors RED tests now against two targets that core cannot
invalidate:

1. **Pure rule module** — a NEW file this sprint owns outright. Unit tests
   import it directly. Conflicts with nothing.
2. **Pipeline live path** — integration tests drive `run_definition_linking`
   and assert on persisted `Definition.scope` + `USES_DEFINITION` assertions.
   This is behaviour, not API surface, so the seam spec can change the wiring
   without rewriting the tests.

Tests must NOT be written against the registry-registration API until the
seam spec publishes. The registration adapter is a thin, later commit.

### S-R2 — Developer work is fenced until core merges

Per the sprint contract's Coordination section and program P-R1: developers
implement ONLY the new pure rule module until core's merge lands on `main`.
Zero edits to `pipeline.py`, `extract.py`, `matcher.py`, `profiles.py`,
`us_profile.py`, `sections.py` (gate U3: "zero edits to shared modules").
After core merges: rebase, then add the registry-registration module.

