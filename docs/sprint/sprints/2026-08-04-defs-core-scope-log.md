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

### Round 1 — Planner Stage A (exploration + seam spec)

**Tooling note**: this worktree had no `.codegraph/` (it's gitignored, not
shared across worktrees — only the main checkout's index existed, and the
brief forbids touching main). Ran `codegraph init .` in THIS worktree
(196 files, 2,386 nodes, 5,435 edges, 338ms) — an indexing operation
entirely local to this worktree, not a main-checkout touch, and squarely
what the director's CodeGraph mandate calls for. Every exploration below
used `codegraph_explore`, not Read/Grep.

**Full pipeline.py read** (not just the recon excerpts) to trace exactly
how a `DefinitionCandidate` becomes a persisted `Definition` + a
`USES_DEFINITION` `Assertion`, confirming several details the recon dossier
didn't spell out:

1. `_in_scope`/`link_articles_to_definitions` operate on `DefinitionCandidate`
   objects (transient, Stage-2-fresh, in-memory), NEVER on reloaded
   `Definition` ORM rows — every `run_definition_linking` call re-extracts
   candidates from current article bodies before matching. This is why
   `source_chapter`/`source_article_number` aren't persisted columns today
   (recoverable via `Definition.article_id`'s FK to the owning article's own
   `.chapter`/`.number`) — and why `source_subsection` genuinely NEEDS its
   own persisted column: there's no FK path to recover it (subsections
   aren't a stored entity).

2. **Attribution bug found, not in the recon dossier**: `pipeline.py`
   Stage 3 builds `term_to_definition: dict[str, Definition]` — ONE flat
   dict per document, keyed by bare term STRING. When two different
   `Definition` rows share a term name (e.g. two different chapter-scoped
   or subsection-scoped redefinitions of "person"), the dict silently keeps
   only the LAST one processed, and every matcher edge for that term string
   — regardless of which specific definition's scope actually authorized
   it — gets attributed to whichever row currently occupies the dict slot.
   `_in_scope` correctly gates the MATCHER's article scan (edges only exist
   for genuinely-in-scope (candidate, article, position) triples), but
   pipeline.py's post-processing throws that distinction away. Grepped
   `test_definition_links_matcher.py` for a same-term-different-scope
   case — none exists; this is untested today, presumably rare for IL's
   current chapter-scope usage, but subsection scoping (this sprint) plus
   scoped-inline (defs-us-scoped-inline) make "same term name, many
   per-article/per-subsection local redefinitions" the COMMON case, not the
   exception (real-world statute pattern: "person" redefined section-by-
   section across a title).

   Considered escalating this per the brief's "mention-span plumbing that
   changes the assertion write path" trigger, but decided NOT to: the fix
   (re-resolve each edge's definition via its own `article_index`/
   `char_offset` instead of the flat dict; emit one assertion per distinct
   in-scope definition on genuine ambiguity) does not change
   `ArticleUsesTermEdge`'s public shape or `_create_assertion`'s dedup key
   — it's an internal pipeline.py Stage-3 fix, zero surface change for the
   6 family panels (their tests exercise `run_definition_linking`
   end-to-end and will simply see MORE CORRECT attribution, never a
   different call signature). Recorded as a decision in the seam spec's
   "Attribution fix" bullet, and flagged prominently in the Stage A report
   as a risk item in case the sub-manager wants a second look before Stage B
   tests pin the behavior.

3. Confirmed precisely why C2's gate text ("English triggers... in shared
   pipeline/matcher/extract code") names `extract.py` even though
   `extract.py`'s Hebrew regexes aren't literally moving: the violation is
   that `pipeline.py` calls `extract_local_definitions`/
   `extract_adhoc_definitions` UNCONDITIONALLY (no jurisdiction check) —
   the wrong MECHANISM (bypassing profile dispatch entirely), not merely
   "the wrong language of regex". Fix is `profile.extract_local_scope_
   definitions(...)`; the Hebrew regexes stay physically in `extract.py`
   but become reachable ONLY via IL's registered `ScopeTriggerRule`s.

**Subsection design — decided, not escalated.** Two designs were on the
table:

- **(A) Offset-span-based** (chosen): a NEW profile method
  `split_into_subsections(article_body) -> list[Subsection]` computed
  FRESH every call from the same normalized body string both extraction
  and matching already share (never persisted as raw offsets — only the
  `.label` string is persisted, on `Definition.source_subsection`, mirroring
  how `.scope` itself is already persisted string-only). Enforcement
  becomes a label-equality check after locating which transient
  `Subsection` a match's char offset falls into.
- **(B) Identifier-only, no spans**: require every subsection-scoped rule
  to independently invent and persist a subsection ID with no positional
  grounding. Rejected: nothing to enforce against at match time without
  re-deriving position anyway, and it duplicates work (B) would still need
  (A)'s splitter to make the ID meaningful.

Chose (A). Did not escalate per the brief's explicit guidance ("adding a
column... does not by itself require escalation... choose the design you
believe is right") — this doesn't touch `Article`'s meaning, doesn't touch
existing IL behavior (subsection is a strictly-new, additive scope value;
`"chapter"`/`"local"` byte-identical), and the exact subsection-marker
regex per jurisdiction is core sprint's OWN Stage B work, not something
family panels need to implement or even see.

**Rule-registry mechanism — auto-discovery over an append-only file.** The
brief asked me to name ONE file family panels append a registration line
to, and asked me to propose an alternative if that can't be conflict-free.
Chose the alternative outright: `rules/__init__.py` auto-imports every
sibling module via `pkgutil.iter_modules` (sorted, deterministic), and each
rule module calls its own `register_*` at its OWN module's import time. A
family panel's only repo change is ADDING a new file — new-file-creation
never produces a merge conflict, which is strictly better than an
append-only shared line (still a shared-file edit, still theoretically
collidable if two panels pick the same line-insertion point). No
escalation needed; this is the design I believe is right per the same
"choose it, record it" guidance.

**Not escalated, but flagged as an open question for the panel** (see
report): whether `HeadingRule`/`EntrySplitterRule`/`BodyPreambleRule`'s
"baseline-first, first-registered-match-wins on filename sort order" rule
is fine-grained enough once 4-5 family panels' heading/marker/preamble
rules are all live simultaneously — recon's families were assigned to
states with (as far as recon shows) non-overlapping conventions, so I don't
expect real collisions, but I haven't proven pairwise disjointness across
all 6 families' trigger shapes against the corpus. Flagged for
Developer/QA to watch for during Stage B/implementation, not blocking
Stage A.

