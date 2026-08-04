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

**MANAGER PLACEHOLDER — see "Round 1 — Manager review" below for the
sub-manager's verification of everything in this Round 1 entry.**

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


---

### Round 1 — Manager review of Planner Stage A (sub-manager, Opus/high)

**What I verified MYSELF (not "the agent said so"):**

1. **Planner wrote zero production code.** `git diff --name-only
   5b93ef8..5610fb1` → exactly two paths, both under `docs/sprint/`.
   Role separation intact.
2. **Push is real.** `git ls-remote origin claude/defs-core-scope` →
   `5610fb106808d2cfba2d547d6a9413a16b07a14d`, matching local HEAD. The seam
   spec IS readable by the other panels right now.
3. **The attribution bug the Planner reported is REAL** — I read
   `pipeline.py:568-606` myself rather than accepting the claim:

   ```
   572  term_to_definition: dict[str, Definition] = {}
   573  for candidate, definition_row in doc_candidates:
   574      for term in candidate.terms:
   575          term_to_definition[term] = definition_row     # last-wins
   ...
   584      definition_row = term_to_definition.get(edge.term) # by bare term
   ```

   One flat per-document dict keyed by the bare term STRING, last write wins.
   `ArticleUsesTermEdge` (matcher.py:81-93) carries `article_index`, `term`,
   `char_offset` — but NOT the definition that authorized the edge. So when
   two `Definition` rows in one document share a term name, `_in_scope`
   correctly restricts which (definition, article, position) triples become
   edges, and then Stage 3 throws that away and attributes every edge for
   that term to whichever row landed in the dict last. Confirmed; the
   Planner's diagnosis is accurate and its significance assessment (rare
   today, COMMON once subsection scoping lands) is sound.

**Seam spec assessment.** Accepted in substance. Two things I rate as
genuinely good calls, recorded so the family panels can rely on them:
`rules/__init__.py` auto-discovery via `pkgutil.iter_modules` makes a family
panel's only repo change an ADDED FILE — new-file creation cannot merge-
conflict, so six concurrent panels are conflict-free by construction, which
is strictly stronger than the append-only shared line the brief asked for.
And baseline-first consumption is what protects C5 (the 7 working US states
and all of IL keep byte-identical behavior).

**Manager ruling M1 (seam refinement, made BEFORE any panel has consumed the
spec).** Seam 2's consumption contract says detection kinds are
"first-matching-registered-rule-wins by filename sort", and groups
`EntrySplitterRule` with the detection kinds. I am moving `EntrySplitterRule`
to the union side:

- `HeadingRule` — first-positive-wins STAYS. The verdict is boolean, so
  trying rules in order until one says yes is already an OR/union; nothing
  can be silently dropped.
- `BodyPreambleRule` — first-non-None-wins STAYS. Output is one synthesized
  heading string; there is no coherent union of two. Sort order must be
  deterministic (filename sort, as specified).
- `EntrySplitterRule` — CHANGED to **union of all matching rules' blocks,
  deduped downstream**. Rationale: a section body can legitimately carry two
  marker conventions at once (recon §2 family 3 mixes bare-digit-dot,
  unquoted-caps and single-non-list shapes; family 5's multi-term clauses
  ride inside the same `(N) "Term" means` shape), and under an ABSOLUTE
  zero-miss bar a splitter that silently claims a body and drops the other
  convention's entries is exactly the failure mode this program exists to
  kill. Union is cheap and low-risk here because (a) `TermClauseRule` only
  emits a candidate for a recognizable `"Term" means` shape, so a bad split
  yields nothing rather than garbage, and (b) duplicates already dedup on
  pipeline.py's existing `(article_id, sorted(terms))` key — the Planner
  identified that key itself. This is a mechanism choice with no
  zero-miss/zero-FP tradeoff, so it is my ruling, not an escalation — but it
  IS a change to a published seam, so it is reported upward in the same
  breath (see escalation below) rather than slipped in.

**Manager ruling M2 (Planner open question 2 — cross-family rule
collisions).** The Planner could not prove pairwise disjointness of the six
families' trigger shapes against the corpus and asked whether that blocks.
It does not block this sprint: with M1, the only remaining first-wins kinds
are `HeadingRule` (union-equivalent) and `BodyPreambleRule` (single-valued
by nature). Collision risk is therefore confined to `BodyPreambleRule`, and
proving it empirically needs all six families' rules to EXIST, which they do
not yet. Ruling: this becomes a named gate for the program-close integration
QA (all six panels merged, full-corpus run, assert no body-preamble rule is
shadowed), and the core sprint's QA adds a unit test proving deterministic
ordering. Recorded here for the program manager to carry into the roster.

**Manager ruling M3 (Planner open question 1 — sanity-check the attribution
fix).** Verified above: the bug is real. The FIX, however, is not mine to
finish deciding — choosing what to emit when a mention sits inside two
definitions' scopes at different granularities is a zero-miss vs
zero-false-positive conflict, which program ruling P-R2 forbids any panel
from settling silently. Escalated (below). Stage B is held until answered,
because the answer determines what the C1 RED tests assert.

**Not escalated (deliberate, recorded):** the `Definition.source_subsection`
column + `add_definition_subsection_column.py` migration. The brief
pre-authorized this class of change, the repo has a working precedent
(`backend/app/migrations/add_raw_text_columns.py` +
`backend/tests/integration/test_migration_raw_text_columns.py`), the column
is nullable with no backfill, and `"chapter"`/`"local"` stay byte-identical
so no existing IL test's expected value moves. Approved as-is.

### Round 1 — Manager → Program Manager (ESCALATION E-1)

Raised: multi-scope precedence (which definition governs a mention that is
in scope of two). Full text in the sub-manager's return report. Sprint
status held at `planning`, Planner agent `a6f809d491c471d13` left resumable
for Stage B the moment an answer lands.

---

## 2026-08-04 — Round 2: E-1 ANSWERED + seam spec v2 mandate

### DIRECTOR RULING on E-1 (relayed via program manager) — BINDING

**Option A — narrowest scope governs**: subsection > article/local >
chapter/part > law-wide. The general definition still fires wherever no
narrower one was detected in scope; emit ONLY the governing definition's
assertion. This also AUTHORIZES the attribution fix: each matcher edge must
carry or resolve to its authorizing definition so that `_in_scope`'s
filtering survives attribution (pipeline.py:572-584's flat
`term_to_definition` dict is the thing being replaced).

**Standing director policy (new, applies to every panel):** every
recall-vs-false-positive conflict class escalates WITH DATA. No silent
trades. Measure, then escalate; never pick a side quietly.

**Manager ruling M1 (union entry-splitters): ACCEPTED by the program
manager.** It stands as written in Round 1.

### Cross-panel asks against seam v1 (five, all with measured demand)

Relayed by the program manager. Manager rulings follow each, so the Planner
enters Stage B with no unresolved architectural fork.

**Ask 1 — generic scope units.** The fixed 4-tier vocabulary cannot express
real scopes. Measured: US `chapter` = 23.7% of the scoped-inline family's
29,033 hits (already enforceable by `matcher._in_scope`'s existing chapter
branch); `part` 2,187 + `subchapter` 1,861 (13.9%); IL סימן 200 files, חלק
68 (the IL panel's E1); KY "Definitions for section" and AK multi-chapter-
range headings (headings panel enumerated all 10 such rows). Two panels
independently recommend a generic `(unit_kind, unit_value)` pair.

> **MANAGER RULING M4 — adopt generic scope units, with a mandatory total
> order.** The Planner owns the concrete shape (columns, dataclass), but the
> design MUST satisfy all four constraints below, because the director's
> Option A ruling is unimplementable without them:
> (a) Scope is expressed as a generic `(unit_kind, unit_value)` pair, not a
>     closed tier enum — a NEW unit kind must be shippable from a rule
>     module with zero shared-module edits (same bar as C4).
> (b) There MUST be a total specificity ORDER over unit kinds, and a rule
>     module registering a new kind MUST supply its rank. "Narrowest scope
>     governs" is meaningless over an unordered vocabulary — this is the
>     load-bearing coupling between M4 and the director's E-1 ruling, and
>     the single thing most likely to be missed.
> (c) Two definitions whose scopes are NOT comparable under that order
>     (neither contains the other) is a real state and the spec must say
>     what happens. Per the director's standing policy this is a
>     conflict class: if the answer trades recall against precision,
>     escalate with data rather than choosing.
> (d) Existing `"chapter"` / `"local"` / `"law-wide"` behavior stays
>     byte-identical for IL (C5, prior R2). Migration is additive.
> Multi-chapter RANGES (AK) may be explicitly deferred with a recorded
> fallback — Planner's call, but v2 must state which and what the fallback
> is. Silence is not acceptable; ten enumerated real rows are waiting.

**Ask 2 — `ScopeTriggerRule.extract` signature.** Today a rule receives only
`(article_body, article_number)` and therefore can never stamp an
enforceable chapter/part scope (scoped-inline panel's S-R3, measured 23.7%
of its volume). The Definitions-section path already stamps the source unit
from the owning article.

> **MANAGER RULING M5 — pass a context OBJECT, not more positional args.**
> The rule receives the owning article's context (number, chapter, and
> whatever unit fields M4 introduces) as a single frozen context dataclass.
> Rationale: six panels are about to write `extract(...)` implementations
> against this signature; every future context addition would otherwise be
> a breaking change across all six. A context object makes context growth
> additive. The caller may still stamp defaults, but the rule must be ABLE
> to stamp a non-local unit itself.

**Ask 3 — M-R7(a), is registry dispatch gated by the placeholder-heading
gate?** Preamble panel needs UNGATED: MD 3,327 real preamble rows (recon's
"1" was wrong), NE 559, MS 637, SD 218. Under the gated reading SD is
permanently unreachable — its headings are genuinely descriptive, not
placeholders.

> **MANAGER RULING M6 — UNGATED.** Registry rules are tried whenever
> baseline detection yields nothing, NOT only behind
> `_is_placeholder_heading`. The data is decisive and matches the
> director's escalate-with-data policy: gating makes 4,741 measured real
> rows unreachable and SD structurally unreachable forever, which is a
> zero-miss breach by construction. Precision-guard expectation, stated
> here so the preamble panel can measure against it: baseline-first
> ordering is unchanged, so no currently-working row can change behavior;
> the new exposure is confined to rows where baseline finds NOTHING today
> (i.e. rows currently contributing zero definitions), so the FP risk is
> additive-only and cannot regress a working state. The preamble panel
> measures corpus-wide FP exposure on that population and escalates with
> data if it is material.

**Ask 4 — PR seam form: rule modules under `USProfile`, or a distinct
`PRProfile`?** PR panel verified `USProfile`'s baseline returns nothing on
Spanish, so registry rules always get their turn. They proceed as rule
modules meanwhile.

> **MANAGER RULING M7 — rule modules under `USProfile` for now, and v2 must
> state the escape hatch.** Cheapest reversible choice, consistent with
> v1's "modules not mechanism", and reversible later without invalidating
> the PR panel's rule modules (profiles resolve by code; rules register by
> code-match — a later `PRProfile` can inherit the same registered rules).
> BUT v2 MUST name what rule modules CANNOT override — on my reading of
> the seam that is at least `find_term_uses` (term matching) and
> `find_citations` (citation grammar), neither of which is a rule kind. If
> Spanish needs different term-matching or citation grammar, that is a
> profile-class problem, not a rule problem. Say so explicitly in v2 so the
> PR panel escalates early instead of discovering the wall late.

**Ask 5 — two NEW core items** (measured zero-miss breaches in modules THIS
sprint owns; both have RED evidence ready from other panels):
- (a) `sections.parse_articles` requires `@ N.`; **124 of 6,133** Israeli
  laws use a bare `@` and parse to ZERO articles. 12 contain unambiguous
  definitions. IL panel proved this end-to-end on a named file.
- (b) `find_term_uses` is case-sensitive; real GA rows re-mention
  capitalized defined terms in lowercase (`STATE_GA_T7_C8_S7-8-1` defines
  "Access area", `S7-8-3` uses "access area") — silent under-linking for
  every English family.

> **MANAGER RULING M8 — both accepted as core sprint items with
> Planner-authored RED tests.** Item (b) carries two explicit
> constraints: case-folding must be proven not to disturb Hebrew (Hebrew is
> caseless, so a naive `re.IGNORECASE` is *probably* inert — but "probably"
> is not evidence; the full IL suite passing UNCHANGED is the evidence, and
> editing an IL test to fit is a planning bug → escalate to me, prior R2);
> and case-insensitive matching is itself a recall/precision trade (a
> defined term that is also a common lowercase word will over-link), so per
> the director's standing policy the Planner MEASURES the exposure and
> escalates with data rather than choosing silently.

### Round 2 — Manager → Planner (resume into Stage B)

Planner agent `a6f809d491c471d13` resumed in-session (its Stage A
exploration context is exactly what Stage B needs — a fresh spawn would
re-pay for it). Instruction: publish seam spec **v2** in the same contract
section, versioned, and PUSH IT AS THE FIRST ACT (four panels are parked on
it), then continue into RED tests without a second stop. The manager
reviews the pushed v2 while the Planner works and sends corrections
mid-flight if needed.

### Round 2 — Planner v2 authoring notes

Confirmed the resume message against the actual repo before acting on it:
`git fetch` showed `origin/claude/defs-core-scope` at `d421a57`, two commits
ahead of the Planner's own last push (`5610fb1`) — `9272f6e` (manager review
+ rulings M1-M3, escalation E-1) and `d421a57` (director ruling on E-1 +
manager rulings M4-M8). Read both in full before writing v2; not acting on
the resume message's summary alone.

**M4(c) non-comparable scopes — decided NOT to escalate**, despite the
resume message listing it as an escalate-if-true trigger. Reasoning (also
in the seam spec itself): "both survive, both get an assertion" is not a
recall/precision trade because nothing is suppressed (recall-safe) and
nothing fabricated is asserted (each surviving definition's scope claim is
independently true for that mention). A trade would require a scenario
where keeping both creates a FALSE claim or dropping one creates a MISS;
neither holds. This is a mechanism choice within the "choose it, record it"
authority the brief already grants, not a P-R2 conflict class. Recorded
prominently (here + the seam doc + the Stage B report) specifically so the
sub-manager can override if they read the tradeoff differently — the point
of NOT escalating a call I'm confident about is to keep the critical path
moving, not to hide the reasoning.

**M8(b) measurement — genuinely could not produce it, said so.** Searched
this worktree and every path this sprint is authorized to touch for a local
copy of the US parquet corpus or the israeli-laws-wiki corpus (`find` for
`*us_ga_statutes*`, `*state_ga*`, `*statutes*`, `*israeli-laws*` from `/`,
maxdepth 3-5) — nothing found. The other panels' cited figures (29,033
hits, MD 3,327, etc.) evidently came from sessions with corpus access this
worktree does not have. Rather than fabricate an exposure number to satisfy
the "measure and escalate with data" instruction, recorded the gap
explicitly in the seam spec's M8(b) section and scoped the RED test to the
exact fact pattern already handed down verbatim (term "Access area", act
ids `STATE_GA_T7_C8_S7-8-1`/`S7-8-3`) rather than inventing corpus rows.
This is a deliberate escalation-by-omission-avoidance: I would rather say
"I can't measure this from here" than produce a number I can't stand
behind. Not blocking Stage B — the fix itself (word-boundary literal-term
case-fold, narrowly scoped) proceeds with the measurement gap flagged for
the sub-manager to route to whichever panel has corpus access.

**Rank-tie default for unregistered/uncertain nesting (M4b)**: chose
"tie never costs recall, only a possible redundant-but-true assertion" as
the safe default for a family panel unsure how its new unit kind nests
against an existing one. This mirrors the M4(c) non-comparable-scopes
reasoning exactly (same "both survive" resolution), so I did not treat it
as a second separate decision needing its own escalation — it falls out of
the same rule.

---

## 2026-08-04 — Round 3: manager review of seam v2 (pushed `6c449fc`)

Reviewed the pushed v2 myself against rulings M4–M8. `git diff --name-only
d421a57..6c449fc` → two paths, both under `docs/sprint/` — Planner still at
zero production code, role separation intact.

**Accepted as written:** M4(a) `ScopeUnit(kind, value)`; M4(b)
`register_scope_unit_kind(kind, *, rank)` with `rank_for` raising `KeyError`
instead of fabricating a guess (correct, and consistent with the codebase's
existing `resolve_law_title` discipline); M4(d) keeping `"chapter"`/`"local"`
on their existing dedicated fields so IL comparisons are literally untouched
— that is the design choice that makes C5 cheap. M5/M6/M7/M1 all render
correctly. The Planner flagged its own M4(c) call for override rather than
burying it, which is what surfaced the M11 hole below.

**Three corrections issued (M9 already sent separately, M10/M11 new):**

**Overruled — AK multi-chapter-range deferral.** v2 §1 defers with the
fallback "scope stays `law-wide`". A program ruling landed mid-write:
the fallback may NOT be a silent law-wide stamp; the multiterm panel's
manager refused exactly this. The Planner's justification ("zero-miss-safe —
law-wide never narrows away a legitimate match") is true for recall and wrong
overall: stamping law-wide on a definition governing chapters 5-9 doesn't
lose a match, it manufactures assertions across every other chapter. M9
(sets + set-membership `_in_scope`) supersedes it and covers SD's enumerated
sections with the same mechanism.

**MANAGER RULING M10 — equal-rank ties: behavior stands, reasoning
corrected, class stays OPEN.** The Planner resolved M4(c) as "both survive,
both get an assertion" and argued it is not a recall/precision trade because
"each surviving assertion's scope claim is independently, factually true —
the mention genuinely sits inside both units". That reasoning is wrong. The
emitted assertion is not "the mention sits inside unit U"; it is
`USES_DEFINITION` pointing at ONE specific `Definition` row. A term at one
mention has one meaning, so when two different definitions of the same term
both get an assertion, one of them is factually FALSE — we just don't know
which. That is a false positive with a knowable rate. Same correction applies
to the spec's "register at the same rank as the nearest known kind — a tie
never costs recall, only a possible duplicate-but-true assertion": there is no
duplicate-but-true here. Ruling: KEEP the behavior (it is the zero-miss-safe
side and the director's bar is absolute), but record it as a NAMED OPEN
conflict class under the director's escalate-with-data policy, with (a) a test
pinning the tie behavior so it is deliberate not emergent, and (b) a QA-time
full-corpus measurement of equal-rank/different-kind tie frequency, escalated
with the number if material. Planner does not spend Stage B time measuring.

**MANAGER RULING M11 — the seam needs a `StructuralUnitRule` (load-bearing;
this is a C4 breach as v2 stands).** v2 §1 says core populates
`structural_units` for `"chapter"` only and that populating it for any new
kind is "that kind's OWN family panel's responsibility". But the generic
containment check compares `definition.scope_value` against the owning
article's `structural_units` — so a `part`/`siman`-scoped definition can
NEVER match unless something stamps a `ScopeUnit("part", …)` onto the
article. v2 gives panels a way to register a kind + rank, and a way to stamp
a scope onto a DEFINITION, but no way to put the unit onto the ARTICLE. A
panel needing `part`/`subchapter`/`siman`/`chelek` must therefore edit
`parse_articles`/`pipeline.py` directly — six panels colliding on one file,
exactly what P-R1 exists to prevent. Not a corner case: `part` 2,187 +
`subchapter` 1,861 (13.9% of the scoped-inline family) plus the IL panel's
סימן 200 / חלק 68 — the MAJORITY of Ask 1's measured demand routes through
the one path the seam doesn't provide. Ruling: add a structural-unit rule
kind, registered the same import-time way, unioned across matching rules
(genuinely additive here — an article legitimately nests in a part AND a
chapter at once, unlike the `USES_DEFINITION` case). If the raw structural
context a panel needs (IL's `==`/`===` heading stack, US title/part
breadcrumbs) is not reachable from the article at that pipeline point, that
is an INGEST-CONTRACT question → Planner tells me and I route it, rather than
six panels each discovering it independently.

### Round 3 — Program manager → Manager → Planner: two more v2 items

**Enumerated-section scope kind** (multiterm E2): SD 3-14-5 defines terms
"when used in § 3-14-3 or 3-14-4" — two named sibling sections; local/
chapter/law-wide all misfire. Ruled M9 (adopt as sets, don't defer); lean
recorded: model an enumerated scope as expanding to a SET of same-rank unit
scopes, so it inherits its members' rank and M4(b)'s total order survives
untouched. Consequence to state: a `local` def and a `section_enum` def over
the same article become rank-EQUAL, i.e. an M10 tie.

**Pointer definitions — DIRECTOR RULING** (7,610 rows, 32 jurisdictions):
entries like `"Enforcement officer" has the meaning given that term in ORS
153.005` ARE definitions, must be captured now, AND the reference must be
captured too — definition row + reference assertion to the target, internal
same-law section targets included. Manager notes passed to the Planner:
`find_citations` is the right parsing plug-in (keep family panels out of the
citation-parsing business); Stage 4 `derivation.py` is the natural emitter
BUT `_BESAIF_RE` (:39) deliberately excludes `בסעיף N` as "Stage 3
territory", so internal targets sit outside Stage 4's current contract and
may force a new edge type → escalate to me if so (this sprint's gates are
backend-only; a new assertion type plausibly reaches the frontend's
assertion-type rendering, which is out of my scope to absorb silently).
**Reconciliation ruled:** pointer extraction runs INDEPENDENTLY of the
markers panel's "correctly-empty" cross-reference classifier, and a non-empty
pointer result OVERRIDES "correctly empty" — a section cannot be both, and
under an absolute zero-miss bar that is the only safe ordering.

**DIRECTOR CLARIFICATION (relayed same round):** **no typed "pointer" field,
now or ever.** The reference EDGE is the typing. No `is_pointer` flag, no
pointer column on `Definition`, no new assertion field, no follow-up item
proposing one. Consumers read pointer-ness off the presence of the reference
edge. A transient carrier on `DefinitionCandidate` is still fine (in-memory
plumbing, not schema); if the target is recoverable by running
`find_citations` over the definition text alone, prefer that — fewer moving
parts. Superseded my own earlier note that could have been read as
authorizing a persisted pointer-target column.

All of Round 3 was delivered to Planner `a6f809d491c471d13` as three queued
messages while it was mid-write on v2.1. Sprint remains `planning`; no
production code and no RED tests exist yet.


### Round 3 — Planner v2.1 authoring notes

Three messages arrived in quick succession while v2 was already pushed
(`6c449fc`): (1) M9 + pointer definitions, (2) manager review of v2 with
the AK-deferral overrule + M10 + M11, (3) director's narrowing of the
pointer-definition design (no persisted field, ever). Read all three fully
before writing v2.1 rather than reacting to the first one alone — the third
message specifically superseded part of the first.

**Where I pushed back vs. accepted outright:**

- AK deferral overrule (M9): accepted without argument — the correction is
  right. "Zero-miss-safe" was true in isolation but I hadn't priced in that
  a broadening fallback (law-wide) is itself a false-positive generator
  across every OTHER unit of the law. Should have caught this myself before
  publishing v2; recorded as a genuine miss on my part, not just a
  difference of opinion.
- M10 (ties reclassified): accepted the correction to my OWN reasoning, not
  just the outcome. My v2 argument ("not a trade because each claim is
  independently true") conflated "the scope containment fact is true" with
  "the resulting USES_DEFINITION assertion is true" — those are different
  claims, and only the first one is guaranteed true. Fixed the log entry
  above (Round 2 notes) is now superseded by this one on that specific
  point; not editing the old entry (append-only), just noting the
  supersession here.
- M11 (StructuralUnitRule): did not have this in v2 at all — a genuine gap
  the review caught, not a disagreement. Designed the fix (§3 of v2.1) and,
  per the explicit instruction, did NOT guess at US parquet-column
  availability — said plainly that it's unverified this session rather than
  assert it works. This is the one open item in v2.1 I'd flag as most
  likely to need a follow-up round.
- Pointer definitions: the FIRST message's design (transient pointer-target
  field + "check before deciding on a new assertion type") was already
  heading toward "reuse DERIVES_FROM_LAW, no new type" before the director's
  narrowing landed — verified `Assertion.object_entity_type` is a free-text
  `String(255)` (backend/app/models/assertion.py:42) and that the frontend
  renders entity refs generically (`AssertionDetailPage.tsx:328`'s
  `EntityChip`, `SuggestAssertionPage.tsx`'s type list is explicitly
  "guidance only") before concluding no new type/frontend work is needed —
  did not skip the "check the frontend first" instruction just because the
  narrowing arrived mid-check. The narrowing itself (no persisted field at
  all) is a pure simplification of what I was already converging on; folded
  in directly, no disagreement.

**Time-pressure note, recorded honestly:** four rounds of spec revision
(v1 -> v2 -> v2.1) before a single RED test exists is exactly the kind of
back-and-forth Stage A/B split was meant to front-load and absorb — better
here than after 6 family panels had already coded against a wrong v1/v2.
Moving to RED tests immediately after this push; v2.1's `StructuralUnitRule`
US-side gap and M10's QA-time measurement obligation are both explicitly
NOT blocking Stage B and are carried forward as open items in the Stage B
report rather than chased further here.

---

## 2026-08-04 — Round 4: DIRECTOR requirement — recursive sub-article connection targets

**Director, verbatim intent (relayed via program manager):**

> "We want the connections to subsections, not necessarily to articles. In
> some law systems the article is a small enough unit; in some, subsections
> are the main unit, and every subsection may have its own subsections.
> Research what is the main unit in each law system."

**Design consequence.** Connection TARGETS — definition anchors,
reference/pointer targets, AND `USES_DEFINITION` mention anchors — must be
addressable at sub-article granularity, RECURSIVELY nested: an ordered unit
path under an article (article 5 → (a) → (2)), not the `Article` row as a
blanket anchor. Arbitrary depth; no two-level assumption. Each jurisdiction
profile declares its system's main working unit; where that main unit is the
subsection, connections resolve there.

**Program manager's operative instruction, relayed verbatim in substance:**
the SAME unit machinery must serve BOTH scope containment AND connection
addressing — design it once. This is the important part. As of v2 the sprint
had TWO half-machineries aimed at the same problem: `Subsection(label,
start, end)` spans below the article, and `ScopeUnit`/`structural_units`
above it. Shipping both would make six panels learn two unit systems.

**Manager lean passed to the Planner (explicitly labeled a lean, rejectable
with reasons).** One ordered UNIT PATH per addressable location, running top
of law → down: `[part:II, chapter:3, article:5, subsec:a, subsec:2]`. Then
(a) scope containment becomes PREFIX-MATCHING — a definition governs a
mention iff the definition's path is a prefix of the mention's path — one
predicate replacing `_in_scope`'s special-cased chapter/local/subsection
branches, with `law-wide` falling out for free as the empty path; (b)
"narrowest governs" becomes LONGEST-MATCHING-PREFIX, i.e. specificity rank
becomes path DEPTH, which if it holds would largely dissolve M4(b)'s
hand-registered rank registry and most of M10's equal-rank ties, because
nesting order stops being a cross-jurisdiction judgment call and becomes an
intrinsic property of the document's own structure; (c) M11's structural-unit
rule kind collapses into the single "how does this jurisdiction derive an
article's unit path" seam, above AND below the article, instead of two seams.
Candidate break named for the Planner to test: M9's enumerated scopes are a
SET of paths rather than one path — probably fine as "matches if ANY member
path is a prefix", but the Planner must verify rather than assume.

**Two binding cautions relayed:**
1. Do NOT invent the per-system main-unit table. A 4-system research swarm
   (IL, US states, US federal, PR) is measuring real unit hierarchies,
   nesting depths and citation shapes from the corpora; dossier lands within
   the hour. v2.1 leaves the per-system main unit as a DECLARED PROFILE
   PARAMETER fed by that research — design the mechanism, parameterize the
   data. Planner does not block on the dossier and does not guess it.
2. Stop-and-escalate is sharpened, not softened. Sub-article addressing
   plausibly forces persisted sub-article entities (new table/entity type)
   and/or an assertion-schema change: today `_create_assertion` anchors
   `USES_DEFINITION` with `subject_entity_type="Article"`,
   `subject_entity_id=using_article.id`. If honoring this needs schema or
   frontend-visible change beyond this sprint's backend-only gates C1-C5,
   the Planner escalates WITH THE DESIGN rather than absorbing it, and is
   explicitly forbidden from standing up a new persisted entity type on its
   own authority.

**Sequencing instruction given.** v2.1 = Round 3's four items + this
unification, which SUPERSEDES any part of Round 3 that assumed
article-granular anchoring. If the unification is a bigger rewrite than v2.1
can carry, the Planner is told to push a v2.1 that fixes the overruled items
and states the unified unit model as the DIRECTION with open questions named,
then report — an honest in-progress spec beats a stale confident one for four
parked panels. And if this changes what Stage B's RED tests should assert,
say so BEFORE writing them.

**Manager risk note (carried up to the program manager, not resolved here).**
This is real scope growth on the critical path: gates C1-C5 as written cover
scope containment, not connection addressing. Splitting it into a follow-on
core sprint was considered and rejected — the panels would build against an
addressing model that then changes under them, which is worse than waiting.
Recorded so the delay to the six parked panels is attributed honestly to a
director requirement change, not to panel slippage.

### Round 4 — Planner v2.2: unit-path unification + one held escalation

Unified `ScopeUnit`/`structural_units` (v2) and `Subsection` (v1) into one
`UnitPath` (ordered `UnitStep` tuple) per the director's recursive
sub-article requirement, relayed mid-flight. Scope containment becomes
prefix-matching; narrowest-governs becomes longest-matching-prefix (path
depth), which withdraws M4(b)'s hand-registered rank mechanism as no
longer needed (kind strings are now labels only) -- a real simplification,
verified against the actual call pattern (`_in_scope` only ever compares
paths within one document, so no cross-jurisdiction rank calibration
question was ever real). M10's tie class survives unchanged in behavior
and obligations, just restated as equal-length matching prefixes.

**Escalated, not decided:** whether a sub-article `USES_DEFINITION` mention
anchor needs a new persisted entity (Option B) or can carry its unit path
as an additive nullable column on the existing `Article`-anchored assertion
(Option A). My lean is Option A (provably stays backend-only/gates-C1-C5,
matches every other additive-column decision this sprint has made) but I
am not building either without an answer, per the explicit instruction not
to create a new persisted entity type on my own authority. Every OTHER
Stage B item is unblocked and proceeding in parallel -- only sub-article
`USES_DEFINITION` anchoring specifically is held.

**Rework of already-written tests:** the 3 matcher tests + 1 profile test
written just before this message landed (subsection isolation, generic
`ScopeUnit`/`structural_units` containment, `split_into_subsections`) were
built against the pre-unification two-mechanism model. Reworking them to
the `UnitPath`/prefix-matching model next, before writing any further new
scope-containment tests, rather than leaving stale-model tests in the
suite alongside the new spec.

---

## 2026-08-04 — Round 5: `find_citations` defects land on the pointer item

Relayed by the program manager from the multiterm panel, pinned as RED
assertions on `claude/defs-us-multiterm` @ `f1011f0`:

1. **Decimal section numbers TRUNCATE.** `Section 552.003` matches as
   `Section 552` — a DIFFERENT real section. This is a **wrong-target**
   defect, not a miss. Under the director's ruling that the reference EDGE
   carries the semantics (Round 3), a wrong edge is strictly worse than an
   absent one. Higher severity of the two.
2. **State-code citation shapes return nothing.** `ORS 153.005` → no
   citation at all.

Both sit under v2.2's pointer plumbing: 7,610 pointer definitions across 32
jurisdictions route through `find_citations`, so unfixed they emit wrong or
empty reference edges AT SCALE. Ruled: fixed as part of the pointer-definition
item, NOT deferred to a family panel.

**Manager instruction — verify before pinning.** The Planner reproduces both
itself against `us_profile.find_citations` (us_profile.py:409-437) with the
worktree venv before writing anything. I am relaying a claim; core owns the
fix, so core confirms the defect. A defect that will not reproduce comes back
to me rather than getting a test written around it.

**Manager instruction — do NOT duplicate the multiterm panel's pins.** Goal is
that core's fix turns THEIR existing pins green, not that a second set of
tests asserting the same behavior grows on this branch. Planner: fetch and
READ their tests at `f1011f0` read-only (never check that branch out over the
work, never edit their files, never cherry-pick); author core's RED tests in
core-owned files with expected values IDENTICAL to theirs for shared
behavior; cover what they do NOT pin (IL unaffected; pointer emission
end-to-end; internal same-law target); and record in the contract which of
their `file::test` ids core's fix should turn green, so integration QA checks
it rather than rediscovering it. Divergent expectations across two branches
that merge later is the failure mode being avoided.

**MANAGER RULING M12 — `find_citations` becomes rule-extensible. This
REVERSES part of my own M7.**

M7 said `find_citations` is not a rule kind and that a jurisdiction needing
different citation grammar is a profile-class problem. That was correct while
the only consumer was PR/Spanish. It is wrong now: pointer definitions make
citation parsing a **32-jurisdiction** concern, and `ORS 153.005` is merely
Oregon's shape — every state code has its own. Under the seam as published,
all 32 grammars land in `us_profile.py` — precisely the shared-file collision
P-R1 exists to prevent, and the identical argument that produced M11.
Ruling: add a citation rule kind, registered the same import-time way,
consulted by `profile.find_citations` alongside its baseline. Constraints:
baseline-first so nothing currently green moves (C5) and
`HebrewProfile.find_citations` keeps returning `[]` unless an IL rule is
registered; **core fixes BOTH defects in the BASELINE**, not in a rule module
(decimal truncation is a shared-regex bug and must be fixed for everyone; the
common `<CODE> <n>.<n>` state-code form should work out of the box, with the
rule kind reserved for genuinely idiosyncratic grammars); union semantics on
extraction, consistent with M1/M9. M12 also **resolves the M7 limitation for
PR** — v2.2 must update M7's paragraph rather than leave two contradictory
statements in the spec, since the PR panel was told the opposite.

**Severity note carried into the design:** decimal truncation produces a
SILENTLY WRONG edge, so at least one test must assert that `Section 552.003`
does NOT resolve to `552`. A test that merely checks "a citation was found"
passes on the bug — that trap is called out explicitly in the brief.

**Sequencing given:** folds into v2.2 alongside the Round 4 unit-path
unification, with permission to publish v2.2 with open questions NAMED rather
than let it grow into a document that never ships — four panels are parked and
one of them now holds RED tests waiting on core.

### Sprint state at end of Round 5

`planning`. Zero production code, zero RED tests on this branch (verified:
`git diff --name-only 61f7168..0c0f14c` filtered for non-`docs/sprint/` paths
returns nothing). v2.1 published at `0c0f14c` and verified by the manager
against M9/M10/M11 + the pointer ruling — all four correctly addressed. v2.1
does NOT contain Round 4's unit-path unification or Round 5's citation work;
v2.2 carries both. Planner `a6f809d491c471d13` alive, four messages queued/
delivered across Rounds 3-5.

---

## 2026-08-04 — Round 6: v2.2 published; Planner escalation E-2 routed UP

**v2.2 published at `ce8fd29`** — manager-verified doc-only
(`git diff --name-only 5ee39b9..ce8fd29` filtered for non-`docs/sprint/`
paths → nothing). The Planner ADOPTED the unit-path unification: one ordered
`UnitPath`, scope containment becomes prefix-matching, narrowest-governs
becomes longest-matching-prefix, and **M4(b)'s hand-registered rank registry
is WITHDRAWN** as a consequence — the simplification I leaned toward in Round
4 survived contact with the cases. Recorded as the Planner's call, taken on
its own analysis, not merely accepted from me.

**ESCALATION E-2 (Planner → manager → program manager → director).** Does a
sub-article `USES_DEFINITION` mention anchor need a NEW PERSISTED ENTITY?
Today `_create_assertion(subject_entity_type="Article",
subject_entity_id=using_article.id)` — the assertion's SUBJECT is the whole
`Article` row, but recursive sub-article addressing means a mention's true
location is `(article_id, mention_unit_path)`, finer than the row.
Option A = additive nullable column, no new entity, no frontend impact.
Option B = new `Unit` table + `subject_entity_type="Unit"`, first-class and
deep-linkable but a new write-path shape plus frontend work. Planner's lean:
A. Planner behavior was correct: designed both, decided neither, and narrowed
the hold to sub-article ANCHORING tests only — scope containment, M8(a),
M8(b), rule-registry existence, C2/C3 profile methods and C4 auto-discovery
all proceed meanwhile, so the sprint is not stalled.

**Manager position carried up** (full text in the return report): route UP
per the program manager's standing instruction that schema-or-frontend-
visible change beyond gates C1-C5 escalates rather than gets absorbed. Two
manager additions to the Planner's framing — (1) I rule AGAINST encoding the
unit path into the assertion's `proposition` free text under either option:
the proposition is user-visible prose and an unparseable carrier; if A is
chosen it must be the structured nullable column, not the prose; (2) I name
an **Option C** the Planner did not: take A's storage NOW but shape the value
as structured data and keep the write path B-compatible, so materializing
`Unit` rows later is additive rather than a rewrite — decided when the
4-system research dossier lands, since real nesting DEPTHS are exactly what
distinguishes "a column is fine" from "a column gets ugly". The substantive
question for the director: "connections to subsections" — does that mean a
traversable graph EDGE to the subsection (B), or the connection recorded AT
subsection precision (A)? In a graph product that distinction is the whole
question, and it is product judgment, not engineering preference.

### Round 6/7 — Planner v2.3: find_citations rule kind (M12), defects verified

Reproduced both `find_citations` defects myself before writing anything,
per the explicit instruction (`backend/.venv/bin/python`, output pasted
into the seam doc verbatim: decimal truncation confirmed --
`find_citations("...Section 552.003...")` returns `["Section 552"]`;
state-code shape confirmed invisible -- `find_citations("...ORS
153.005")` returns `[]`).

Fetched (read-only, via `refs/remotes/origin/defs-us-multiterm-snapshot`,
never checked out over this worktree's own files)
`claude/defs-us-multiterm@f1011f0`'s
`backend/tests/unit/test_definition_links_e1_pointer_reference_capture.py`
and copied its exact expected values into v2.3 rather than inventing a
second set: `["ORS 153.005"]`, `["Section 552.003"]`, `["Section
2001.003"]`. Also found (not previously in this spec) that their file
pins a THIRD defect in the same idiom-recognition path -- `_TRIGGER_
PHRASES` missing 3 real idioms -- noted in v2.3 as part of the same
baseline fix set even though M12 itself only names `find_citations`.

M7's PR paragraph corrected in place (marked with strikethrough +
superseding text) rather than left contradicting M12 elsewhere in the
document -- a panel reading the whole spec top-to-bottom should not hit
two different answers to "can PR use a rule for citation grammar."

---

## 2026-08-04 — Round 7: E-2 ANSWERED — Option C authorized (provisional)

**Ruling (program manager, on the manager's escalation E-2):** **Option C**
— the sequencing option the manager named, not the Planner's A or B.

- A's storage NOW, unit path as **STRUCTURED data**. The manager's
  no-prose-encoding sub-ruling is **endorsed and BINDING**: the unit path
  never goes into the assertion's `proposition` text under any option.
- Write path kept **B-compatible** so materializing `Unit` entities later is
  additive, not a rewrite. Design as though B is coming; do not build B.
- **The A-vs-B decision itself — whether subsections become first-class graph
  citizens — is PRODUCT JUDGMENT and goes to the DIRECTOR together with the
  4-system research dossier** (nesting depths, main units, citation shapes).
  The program manager will not put it to the director data-blind. Deliberate
  sequencing, recorded as such.

**Test-shape constraint (the operative part, and the easiest to get wrong).**
Sub-article anchoring MAY now be pinned against C's shape, but **phrased so a
later B-promotion EXTENDS rather than INVALIDATES the pins**; anything that
only makes sense under one of A/B stays **UNPINNED** until the director rules.
Manager translation sent to the Planner: **assert through a RETRIEVAL seam,
not the storage shape.** "The mention's unit path is `5(a)(2)`, retrievable
through the live path" survives a B-promotion; "the `subject_unit_path` column
equals that string" does not — and the Developer cannot edit a broken test, so
pinning storage shape would be a red-before-green violation waiting to happen
(prior R2). Explicitly DO pin: correct unit path via the live production path;
`5(a)`-scoped definition governs a mention in `5(a)(2)` and not one in `5(b)`.
Explicitly DO NOT pin: column name, type, serialization format, or
`subject_entity_type` staying `"Article"`. If proving C's shape needs a
storage-level assertion, LEAVE IT OUT and note the deliberate gap in the
contract so QA reads it as intentional rather than an oversight.

**Also confirmed upward:** the M12 coordination approach (reproduce the
`find_citations` defects independently; expected values identical to the
multiterm panel's pins at `claude/defs-us-multiterm` @ `f1011f0`) was endorsed
as correct. And v2.2's rank-registry withdrawal was noted upward as the best
available signal this design is CONVERGING rather than accreting — spec
getting smaller under pressure. Instruction passed to the Planner: keep that
instinct; where a remaining item can be expressed by the unit-path model
instead of its own mechanism, prefer that.

**Sprint state:** every Stage B item is now UNBLOCKED; nothing is held. The
Planner proceeds through the full RED set — C1-C5, M8(a) bare-`@` articles,
M8(b) case-folding with the Hebrew-unchanged proof and the FP measurement, the
rule registry, the two citation defects, pointer emission. The manager's
structural wiring gate was restated in the same message: **no Developer will
be spawned for any item introducing a new module, function, or dispatcher
branch without a named live call-site test as `file::test`** — a unit test on
the new module in isolation does not satisfy it.

### Round 7 — Planner Stage B complete: RED suite committed and pushed

17 new tests (unit + live-path integration) genuinely RED across gates
C1, C2, C3, C4, M8(a), M8(b), M12; 3 new guard/proof tests pass today
(word-boundary discipline under case-folding, IL-unaffected for both
`find_term_uses` and `find_citations`) and must stay green through
Stage C. Full suite: 644 passed / 17 failed / 1 collection error
(`app.definition_links.rules` doesn't exist yet), 0 regressions --
`backend/.venv/bin/pytest backend/tests -q --continue-on-collection-errors`
run twice for stability, identical result both times.

Deliberately NOT authored this pass, named explicitly in the contract's
"Next Steps" closing note rather than left silent: M10's obligation (a)
tie-pinning live-path test; M9 enumerated-scope live-path proof; the
sub-article `USES_DEFINITION` anchoring retrieval-seam test (E-2/Option C
now unblocks it, but it arrived very late in this session); the pointer-
definition end-to-end emission path; `_TRIGGER_PHRASES` idiom-addition
tests (same fixture rows as M12, noted but not pinned). Frontend/
typecheck not re-run -- zero frontend files touched this sprint.

Frontmatter updated: `status: planned`, `current_role: developer`,
`total_items: 7`, `completed_items: 0`, `dev_complete_items: 0`,
`qa_cycles: 0`. Stale-pin sweep section added -- result: none of the 9
swept symbols need any existing test edited (5 have zero references
outside `pipeline.py`; the other 4's existing assertions are subset-safe
under this sprint's additive fixes, confirmed empirically via the full
suite run, not merely reasoned).

Planner `a6f809d491c471d13` returning its Stage B report now.

---

## 2026-08-04 — Round 8: SPEC FINAL. Two director rulings + dossier. Stage B released.

**D-ANCHOR — "path now, graph nodes later" is FINAL** (director, main @
`321ddab`). Option C is the ruling, no longer a provisional posture.
Assertions anchor at the row-level unit + a structured subsection path of
ARBITRARY depth; promoting referenced subsections to first-class entities is
a possible LATER phase, explicitly not this program. The manager's
retrieval-seam test-shape rule is CONFIRMED at director level and stays
binding — precisely because tests written that way survive a future
promotion. Sub-article anchoring may now be pinned FULLY; the deliberate
storage-shape gap stays recorded in the contract for QA.

**D-PREAMBLE-ALL — manager ruling M6 CONFIRMED at director level**, with a
scope mandate attached: the director explicitly requires ALL states
researched AND coded. That mandate belongs to the PREAMBLE PANEL, not to
core. The preamble panel's QA-measured 5,915-row ungated exposure is resolved
by full per-state inventory + rules, NOT by gating. No core spec change
required — but the Planner was instructed to tighten M6's precision-guard
wording if it is even slightly re-readable as authorizing a gate later. A
future reader must not be able to mistake the precision guard for a gating
condition.

**Research dossier landed** — `docs/sprint/programs/2026-08-04-law-system-units.md`
(48 lines, `origin/main` @ `e3e7633`). Manager verified it is reachable from
this worktree via `git cat-file -e origin/main:<path>` before pointing the
Planner at it. **Read-only access instructed (`git show origin/main:<path>`);
explicitly NO merge of main into this branch — the program manager owns
merges and the manager has deliberately not performed one.**

Measured main units, now the declared per-system profile parameter (fed by
research, NOT invented — the Round 4 caution honored end-to-end): **IL סעיף /
US states Section / US federal Section-but-subsection-de-facto (35.4%
sub-section citations, an 8-LEVEL ladder) / PR Artículo.** Convergent finding
across all four systems: **no system ever cites a bare sub-unit without its
parent** — which validates the row-anchor + path model empirically. Planner
instructed to state that in the spec as the design's evidential basis rather
than leaving the model looking like a preference.

**Three dossier consequences flagged to the Planner as test-relevant:**
(1) the federal 8-level ladder is a REAL depth requirement — nothing may
hard-code depth 2 or 3, and at least one test must exercise genuinely deep
nesting, since a path model that quietly assumes two levels passes every
shallow test and fails on federal; (2) "never a bare sub-unit without its
parent" is an INVARIANT worth pinning, not merely an observation — a path is
always rooted at its article row; (3) the per-system main unit is populated
from measured values only, and a value the dossier does not give comes back
to the manager rather than being guessed.

**Stage B RELEASED — nothing held.** The program manager confirms the spec is
stable and no further revisions are queued from above. All items live: C1-C5,
M8(a), M8(b), rule registry, both `find_citations` defects, pointer emission,
sub-article anchoring. Standing gates restated to the Planner unchanged:
structural wiring gate (no Developer spawn without a named live call-site
test as `file::test`), M8(b)'s Hebrew proof = full IL suite passing UNCHANGED
(the caseless-Hebrew argument is reasoning, not evidence), genuine RED, offline
fixtures, stale-pin sweep, batched pushes, frontmatter to `planned`/`developer`.

**Manager note for the record.** Eight rounds, four published seam revisions,
one withdrawn mechanism (M4(b)'s rank registry), one self-reversal (M12
reversing M7) — and zero lines of production code or throwaway tests written.
The two-stage Planner structure plus stop-before-tests is what made the churn
cheap; had tests been authored in Round 2 against article-granular anchoring
and a 4-tier scope enum, essentially all of them would have been discarded.
Recorded as a process datum for future programs on a moving spec.

---

## 2026-08-04 — Round 9: manager handoff verification of the RED suite

**Non-delegable checks I ran MYSELF (not accepted from the Planner's report):**

1. **Three-dot diff, materialized to file** (`git diff origin/main...HEAD` →
   scratchpad, then read). 8 files: 6 under `backend/tests/`, 2 under
   `docs/sprint/`. Filter for anything outside those two roots →
   **NONE. Zero production code.** Role separation intact after 9 rounds.
2. **Risk grep on the materialized diff** (`fetch|axios|/api/|Authorization|
   Bearer|localStorage|process.env|NODE_ENV|import.meta.env|
   navigator.webdriver|CI`) → 10 hits, ALL benign: prose uses of "fetch"
   in the log, and `CI` matching inside the word "PRECISION". No flagged
   hunk. Checked rather than assumed.
3. **Pre-existing test edits.** `--numstat` across all four pre-existing test
   files: only `test_definition_links_matcher.py` has ANY removed lines (2).
   Read them: they are the `source_article_number`/`source_chapter` field
   **type annotations** on a test-helper dataclass, widened to
   `str | tuple[str, ...] | None` for M9, with defaults unchanged. No
   assertion, no input, no expected value touched; Python does not enforce
   dataclass annotations at runtime, so this cannot change any outcome.
   **Not an R2 violation** — ruled acceptable.
4. **RED tail reproduced independently.** `backend/.venv/bin/pytest
   backend/tests -q --continue-on-collection-errors` →
   **`17 failed, 644 passed, 18 warnings, 1 error in 13.76s`** — byte-identical
   to the Planner's reported numbers. Claim verified.
5. **New "greens" are not vacuous.** The three added guards are named
   discriminating assertions, not tautologies: word-boundary preservation
   under case-folding, IL `find_term_uses` unaffected by M8(b), IL
   `find_citations` unaffected by M12 — each would FAIL if the corresponding
   fix over-reached into Hebrew. That is the correct shape for a guard.

**DEFECT I FOUND — the evaluator command aborts the suite.** My FIRST run used
the contract's actual evaluator (`pytest backend/tests`, no extra flags) and
got **`Interrupted: 1 error during collection` — 0 tests executed**, not
644 passed. `test_definition_links_rules_registry.py:35` imports
`app.definition_links.rules.registry` at MODULE level; the module does not
exist yet (correctly — the Developer builds it), so collection dies and takes
the whole suite with it. The Planner's numbers are real but only reachable
with `--continue-on-collection-errors`, which is NOT the contract's evaluator.
Harness rule is explicit that a test must fail "for the right reason, not a
collection error". Ruling: **do not paper over this by adding the flag to the
evaluator** — that would mask every future genuine collection error (typos,
syntax breaks) across the whole suite. Fix the test pattern (import inside the
test body so it fails as a test FAILURE) so the suite stays runnable. Mitigating
fact: I4 is first in the Developer's scope and creating `rules/registry.py`
self-resolves this within minutes; the Developer is told the workaround for its
baseline run only.

**OPEN QUESTION CLOSED BY MANAGER PROBE — `StructuralUnitRule` US-side data
reachability.** Flagged twice in the spec as unresolved. Answered against a
REAL parquet file, not the docs, per the program manager's instruction:
`backend/tests/fixtures/us_statutes/de_sample_rows.parquet` schema is
`['act_id','citation','citation_short','state','jurisdiction','document_type',
'title_number','title_name','chapter','chapter_name','section_number',
'section_title','breadcrumb','display_path','act_status','text','word_count',
'source_url','last_amended_year','subsection_count','cross_references_usc',
'cross_references_cfr','public_laws_referenced','year']`. **`breadcrumb`,
`display_path`, `chapter`, `chapter_name`, `title_number`, `section_number`
and `subsection_count` are all present — US-side structural unit data IS
reachable.** The question is closed; no ingest-contract escalation needed.

**I3 — manager ruling M13: TAKE the grep-shaped guard test.** The Planner
rejected a structural absence-of-symbol test as "low-value churn" and proposed
closing I3 by code review. The program manager's second opinion favors the
guard; I agree and rule for it. C3's entire content is "pipeline.py retains no
jurisdiction-specific literals" — a property that regresses silently and that
no other test covers, since I1/I2's tests prove the seam EXISTS, not that the
old literals are GONE. A cheap mechanical assertion converts a code-review
promise into a regression-proof check. Authored by the Planner (it is a test).

**Sequencing decision (manager).** Two spawns, concurrent, on disjoint write
sets — Developer writes only `backend/app/**`, Planner writes only
`backend/tests/**` + the contract:
- **Developer scope LIMITED to I4 (registry), I5 (bare-`@`), I6 (case-fold)**
  — the three items with complete RED coverage that do not touch the
  unit-path seam, in three distinct files (`rules/`, `sections.py`,
  `us_profile.py`).
- **Planner Stage C (FRESH spawn, not a resume)** authors the missing RED:
  M10 tie-pinning live test, M9 enumerated-scope live proof, sub-article
  anchoring retrieval-seam live test (now authorized FINAL by D-ANCHOR),
  pointer-emission end-to-end, the 3 `_TRIGGER_PHRASES` idioms, the I3 grep
  guard, and the collection-error pattern fix.
- I1/I2/I3/I7 are **explicitly EXCLUDED from this Developer's brief** — nobody
  builds sub-article anchoring, tie behavior, enumerated-scope enforcement or
  pointer emission ahead of its tests. A second Developer takes them once
  Stage C lands.
- **Fresh Planner rather than resume**, per harness resume-vs-respawn
  economics: the seam spec is now stable and fully written down, so the
  context a resume would preserve is exactly the context that is already on
  disk. A resume of that 9-round transcript costs multiples of a bounded
  fresh spawn.
