# Log — sprint 2026-08-20-defs-boundary-idioms

## Planner pass (2026-08-21)

### 1. Re-deriving the current loss set live

The stale count (41 ceiling-tripped anchors, 2026-08-11 manager triage) predates
the #21/#25/#28 boundary fixes and the #19 "refers to" widening. The
triage artifacts (`mgr_lost_term_triage_result.json`,
`devD_item21_blast_radius_result.json`) were never committed (per QA1 Q4
fixture-vendoring norm) and no longer exist on disk in any worktree.

Reproduced live instead, in two stages:

1. **Direct-function scan.** For each of the 14 jurisdictions
   `us_markers_inline_quote._OTHER_JURISDICTIONS` registers (WA/VA/FED/UT/
   TX/SC/AZ/NJ/MI/ND/NY/OK/NM/NV), loaded every real Definitions-headed row
   (`profile.is_definitions_heading(heading, "")`) from the local
   `vaquill/open-us-law` snapshot cache, applied the same
   `normalize_for_parsing` + `strip_wikilinks` preprocessing production
   uses, and called `extract_quote_anchored_entries` twice per row: once
   at the real 3,000-char ceiling, once with the ceiling monkeypatched to
   `10**9` (mirroring the original manager triage's own methodology).
   Sanity-checked against the issue's own two named examples —
   `USC_T5_C75_S7511` "furlough" (uncapped 3,017 chars) and
   `STATE_NJ_T27_C1A_S1A-3.1` "Department" (uncapped 10,319 chars,
   next-term "New Jersey tolling entity" idiom "shall include") — both
   reproduced byte-for-byte. Result: **165 ceiling-tripped candidate
   anchors** across the 14 jurisdictions.
2. **Live persistence verification.** Ingested all 165 candidates' real
   rows through the REAL `ingest_us_statute_rows` -> `run_definition_
   linking` pipeline (one throwaway pytest probe, deleted before any
   commit — not part of this sprint's committed test set) and checked
   term presence in the persisted `Definition` rows (matched back to
   source via `Article.id = _derive_article_id(document_id, act_id)`,
   since a naive per-term dict collapses same-named terms across
   different rows). **118 of the 165 are TRUE current losses** (absent
   from every extraction path today, not merely present-but-shorter via
   some other rule); the other 47 are captured by baseline or another
   registered rule despite the ceiling drop in `us_markers_boundary`
   alone.

**The set has materially changed from the stale 41.** 118 real losses,
not 41. This is expected given the intervening #19/#21/#25/#28 landings
changed which rows even reach this shape; no attempt was made to
reconcile against the original 66-row population (not reproducible — see
above) and none is needed per P-R11 (run first, adjudicate the real
delta).

### 2. Idiom vocabulary — derived from evidence, not guessed

Of the 118 real losses, only 58 have ANY subsequent quoted string in the
remaining text at all; of those, most are noise (citation-quoted Act
names — `"Administrative Procedure Act," P.L.1968, c.410 (C.52:14B-1...)`
— not a defining idiom) or self-references picked up by a naive
`.search`. Re-scanned with a corrected probe requiring (a) a DISTINCT
quoted term (not the same term repeating itself) and (b) the idiom word
sitting in the TIGHT gap immediately after the closing quote (the same
shape `_TIGHT_IDIOM_RE.match` itself requires). Clean, verified findings:

| Idiom (real, observed) | Row | Verified recovery |
|---|---|---|
| `shall include` | `STATE_NJ_T27_C1A_S1A-3.1` "Department" | `"the Department of Transportation."` — matches the issue's own director-verified text exactly |
| `has the following meaning` | `USC_T12_C13_S1715r` "approved percentage" | Clean ~515-char recovery, but the row ALSO carries an unrelated, pre-existing digit-paren-run-membership artifact (same defect family as #21/#28) in its trailing boundary — **not used as a committed fixture** for that reason (see below) |
| `has the same meaning` | `STATE_NJ_T34_C1A_S1A-1.16` "Public body" | Clean, single-sentence recovery, no artifacts — **used as the second committed representative loss** |

`shall include` is independently corroborated a THIRD way:
`test_us_markers_qa_sc_digit_run_membership_swallow.py`'s own docstring
(issue #28, unrelated investigation) names `STATE_SC_T31_C3_A1_S31-3-20`'s
`"Obligee of the authority"`/`"obligee"` item as using "shall include", an
idiom `_TIGHT_IDIOM_RE` does not recognize — that row is not itself
ceiling-tripped (already protected by the digit-marker run-membership
override), but it is a second, independent real-corpus confirmation of
the idiom string.

`includes` (bare, no "shall") was investigated and REJECTED for this
item: real evidence exists (`STATE_MI_..._S750.219a` "Unlawful
telecommunications access device" -> "Value of the telecommunications
service obtained..."), but its collateral-risk profile (below) is far
worse than "shall include" alone, and the director's ruling requires
"no speculative additions" — deferred, not part of this item.

### 3. Collateral-risk sweep (gate 3)

Method: ran `extract_quote_anchored_entries` against EVERY row in EVERY
fixture under `backend/tests/fixtures/us_statutes/*.json` (34 files),
current regex vs. four widened candidates, diffed per-row term sets and
text; then filtered to only rows whose act_id implies a jurisdiction
where `extract_quote_anchored_entries` is actually reachable in production
(the 14 `us_markers_inline_quote` jurisdictions + US-FL/MN/RI/AK/ME/OH/TN,
whose sibling rule modules also call it directly — 21 total). Naive,
unfiltered fixture-row diffs are NOT evidence of real collateral risk —
several early "hits" (e.g. `STATE_AR_..._S26-18-104` "Person" corrupted
into a duplicated fragment) turned out to be for jurisdictions (AR) with
NO registered rule reaching this function at all, hence unreachable in
production; only the jurisdiction-filtered rows matter.

| Variant | Relevant (registered-jurisdiction) rows changed | Rows with EXISTING capture text changed |
|---|---|---|
| A: `+shall include` only | **5** | 2 (both investigated, see below) |
| B: `+includes` (bare) | 32 | multiple, incl. NV UCC #25 flagship fixture and the VA "sell" nested-means flagship guard |
| C: `+includes` + has-variants | 32 (same as B) | same as B |
| D: `+shall include` + has-variants (no bare `includes`) | **5 (identical set to A)** | 2 (same as A) |

Variant D (this item's actual scope) touches exactly the same 5 rows as
"shall include" alone — the has-meaning variants add zero additional
collateral risk. Each of the 5 traced to its actual test assertions (not
just the raw fixture diff):

- `STATE_FL_TXLVII_C941_PI_S941.34` — only `is_definitions_heading` is
  asserted on this row anywhere; unaffected.
- `STATE_NJ_T48_C10_S10-3` (c5guard_nj "Board"/"Pipeline") — REAL
  collateral, traced and RESOLVED: see §4 below.
- `STATE_VA_T58.1_SI_C17_A9_S58.1-1735` ("Rental in the
  Commonwealth"/"Commonwealth") — only `is_correctly_empty`/`.count('"
  means')` asserted, never this term's own text; unaffected.
- `STATE_VA_T47.1_C1_S47.1-2` ("notary"/"Oath", QA1 Q4 ceiling-audit
  fixture) — that file's own tests pin ONLY `"Satisfactory evidence of
  identity"` (a different term in the same row, bounded by the
  already-recognized "means"/next-term exemption, wholly unaffected by
  this widening); confirmed GREEN unchanged
  (`test_us_markers_qa_q4_ceiling_audit.py`, 4 passed, both before and
  after). "notary"/"Oath" are not asserted anywhere.
- `STATE_SC_T31_C3_A1_S31-3-20` (issue #28 fixture) — adds `obligee`,
  `Community facilities`, `Government`, `Project`, `bonds`, `mortgage`,
  `real property` as new anchors; `Persons of low income`'s own text is
  UNCHANGED (verified: still ends `..."beneficiary class"; and`, still
  excludes `Obligee of the authority`). `test_us_markers_qa_sc_digit_run_
  membership_swallow.py`'s two tests only check `Persons of low income`'s
  presence/absence properties, never an exact term SET — confirmed GREEN
  unchanged, both tests, both before and after.

**Full-suite proof (not just the 5 rows):** ran the entire `backend/tests`
suite (1359 tests) with `_TIGHT_IDIOM_RE` monkeypatched to the widened
form. Result: **1358 passed, exactly 1 failed** —
`test_us_markers_c5guard_nj.py::test_c5_guard_state_nj_t48_c10_s10_3`
(the only real collateral hit, re-pinned this pass, see §4). No other
regression anywhere in the backend suite.

### 4. The one real stale pin — `test_c5_guard_state_nj_t48_c10_s10_3`

`STATE_NJ_T48_C10_S10-3`'s `"Board"` capture comes from BASELINE
(`_split_into_numbered_blocks` + `_leading_quote_candidate`), which wins
its term-set dedup ahead of the family-3 rule's own contribution in
`extract_definitions_from_section` (`all_blocks = baseline_blocks +
priority_blocks + extra_blocks`, first-writer-wins on `candidate_key =
tuple(sorted(candidate.terms))`). Verified directly (real DB pipeline,
widened-regex monkeypatch): `"Board"`'s `definition_text` is
BYTE-IDENTICAL before and after the widening. The widening's only visible
effect on this row is a NEW, independently genuine anchor: `"Pipeline"`
-> `"compressor plants and other facilities integrated with pipeline
operations. L.1952, c. 166, p. 540, s. 2, eff. May 9, 1952."` (previously
never captured by any path — `"Pipeline"` uses `"shall include"`, not
`"means"`).

Re-pinned this pass (only the Planner may edit tests): term-set assertion
now includes `'Pipeline'`, with a content spot-check. This single test
change is simultaneously (a) this sprint's stale-pin re-point, (b) an
extra representative-loss RED test (using an ALREADY-vendored real row —
no new fixture needed), and (c) a live negative control proving gate 3
directly against a real corpus row (`"Board"`'s own long capture is
provably unsplit).

### 5. Stale-pin sweep (mandatory, full)

`grep -rniE "shall\s+include|_TIGHT_IDIOM_RE|has the meaning|includes"`
across `backend/tests/{unit,integration,e2e,fixtures}` (the four test
roots) is far too broad to trace line-by-line by hand (hundreds of hits,
mostly unrelated fixture body text). Traced narrowly instead: (a) every
`.py` file importing any `us_markers_boundary`/sibling rule module (29
files) that ALSO contains the literal string `"shall include"` — 3 hits:
`test_us_markers_c5guard_nj.py` (re-pointed, §4), `test_us_markers_fx7_
ceiling_known_closed_scope.py` (docstring evidence only, no functional
dependency — its own fixture text is deliberately marker-AND-idiom-free
prose, unaffected, confirmed GREEN unchanged: 2 passed both before and
after), `test_us_markers_qa_sc_digit_run_membership_swallow.py`
(docstring only, functionally unaffected — §3 above); (b) the full
jurisdiction-filtered fixture-diff sweep in §3, which is a STRONGER,
behavioral check than grep and is the one actually load-bearing here.

**Current-behavior pin specifically checked per the brief**: issue #28's
SC test docstring documents `"shall include"` as NOT recognized today.
Traced its actual assertions (not just the docstring prose) — neither
test in that file asserts non-recognition; both check presence/absence
properties orthogonal to whether `"obligee"` itself becomes its own
anchor. **No pin flips.** Confirmed live: both tests GREEN, unchanged,
under the widened regex.

**Result: 1 hit requiring re-pointing (`test_us_markers_c5guard_nj.py`,
done this pass), 0 others.**

### 6. Baseline

Full backend suite, current HEAD, before any test additions:

```
PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly
1359 passed, 18 warnings in 30.56s
```

After this pass's 8 new/re-pointed RED-for-cause tests: `1362 passed, 8
failed` (all 8 for the intended reason — see item's Next Steps entry).

### 7. Gate-2 plumbing

**Correction beyond the known `--current` trap.** The reusable pattern in
`docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/run_gate2.sh`
was built for a B1 (body-preamble-derived) item. Read closely,
`measure_actual_production.measure()`'s `--current` branch does TWO
things bundled into one flag: (a) makes `capture()`'s `recognized_by_
registered_rule` match production's real, unconditional computation (the
documented trap — this part IS a real, general requirement, keep it), AND
(b) restricts the entire `members`/`records` population to ONLY rows
where `registered_b1_winner(...)` is true (skips every other row before
`capture()` is even called). `STATE_NJ_T27_C1A_S1A-3.1`'s heading is
recognized directly by BASELINE `is_definitions_heading` (not
body-derived) — confirmed live — so it is NOT a B1 winner, and neither is
any other row this item's family-3 widening touches. **Run `run_gate2.sh`
unmodified for this item and the acceptance delta will read ~0** — not
because nothing changed, but because the harness's own row-admission gate
excludes the affected population entirely.

Recommended correction for whoever runs gate 2 (Developer/QA, not this
pass — out of Planner scope per the brief): in a COPY of
`measure_actual_production.py` for this sprint's own scripts dir, remove
the `if not registered_b1_winner(...): continue` skip from the `--current`
branch (keep `members.append(...)` unconditional, or drop the members
list requirement entirely and diff `records.jsonl` directly), while
KEEPING `capture(..., current=True)` on both sides (the real trap). Do
NOT hand-author an expected-change ledger (P-R11) — run the corrected
harness first, then adjudicate the actual delta.

Exact commands to reuse (BASE_SHA and paths per the existing pattern,
correction applied as above):

```bash
BASE_SHA=<pre-item commit, this branch>
PY=/Users/nerya/LexGraph/backend/.venv/bin/python
MEASURE=<corrected copy of measure_actual_production.py, see above>
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad
RUN=docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/run
git archive "$BASE_SHA" | tar -x -C "$RUN/baseline-src"
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$REPO" --out "$RUN/current" --current
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$RUN/baseline-src" --out "$RUN/baseline" --current
```

Not executed this pass (Planner scope explicitly excludes running the
full all-53).

### 8. Adjudication of the unrecovered remainder (gate 1)

Of the 118 live-verified real losses, this item recovers those whose true
next-term idiom is `shall include`/`has the (following|same) meaning`.
The rest are NOT silently dropped:

- **~60 have no distinguishable next-quoted-term at all** in the
  remaining text (e.g. `USC_T5_C75_S7511` "furlough" — verified directly:
  its true boundary is a bare `"(b) This subchapter does not apply..."`
  LETTER marker with no quote in the 40-char lookahead
  `_QUOTE_WITHIN_LOOKAHEAD_RE` requires, a completely different defect
  family — un-quote-adjacent marker recognition, not idiom vocabulary).
  Out of this item's scope (director ruling: "recovery goes through idiom
  vocabulary only" for THIS item; a marker-boundary fix would be its own,
  separate item).
- **The remaining ~40-odd with a next quote** are dominated by citation
  noise (quoted Act names followed by a P.L./Pub.L. citation, not a
  defining idiom) once traced individually; no further CLEAN,
  evidence-backed idiom emerged at planning altitude beyond the three in
  §2. Full corpus-wide recovery accounting is deferred to gate-2
  acceptance (Developer/QA), consistent with "full-corpus discovery is
  NOT required at planning altitude."

## Developer pass (2026-08-21)

### Steps 1-7: implementation, tests, full pass -- all clean

Synced at `d660849` (verified). Scoped RED re-run before any code change
reproduced the brief's stated baseline exactly: 8 failed / 11 passed across
the four target files. Widened `_TIGHT_IDIOM_RE`
(`backend/app/definition_links/rules/us_markers_boundary.py:296`) per
Item 1's spec exactly:

```
r'(?:means|shall mean|shall include|has the (?:following |same )?meaning)\b:?\s*'
```

(previously `r'(?:means|shall mean|has the meaning)\b:?\s*'`). Re-run: 19/19
green across the four target files. Guard estate (16 c5guard class-B + 5
discriminator safety guards + SC #28 (2) + NV #25 UCC bridge (6) + FX7
ceiling (2) = 31 tests): 31/31 green. `git diff -- backend/app/` touches
only `us_markers_boundary.py` (1 line changed). Full backend suite: 1370
passed (baseline 1359 + Planner's 11 new, 0 failed -- matches the brief's
exact expected count). Frontend: 165/165 passed (25 files). Typecheck:
clean, zero errors. Committed `a51b1de` ("feat: recognize 'shall include'
and 'has the following/same meaning' as entry boundaries (issue #27)
(sprint/2026-08-20-defs-boundary-idioms)"), pushed to
`claude/defs-boundary-idioms`.

### Step 8: Gate-2 execution -- STOP-and-escalate triggered

Built the corrected harness per this doc's own §7: a copy of
`measure_actual_production.py` (this sprint's
`measure_actual_production_all_rows.py`) with the `registered_b1_winner`
population-restriction removed from the `--current` branch (every corpus
row is now a measured "member", not just B1 winners) while
`capture(..., current=True)` is unchanged (the real, general `--current`
trap, preserved). Dropped the prior sprint's hard-coded
`EXPECTED_MEMBERS`/`EXPECTED_MEMBERS_HASH`/`EXPECTED_CHANGED*` constants
(B1-sprint-specific, inapplicable to this item's population) and the
`compare()`/`--compare` mode entirely; diffing done instead by a
`diff_gate2.py` copy (same pattern as
`2026-08-12-defs-b1-refers-to-scripts/diff_gate2.py`, no hard-coded
certified-ledger hash -- P-R11, run then adjudicate).

Ran `run_gate2.sh` (`BASE_SHA=d660849163df9c46aae97157424ba0bb5420ffce`,
the pre-fix commit on this branch; current = post-fix working tree @
`a51b1de`). Both sides measured with `--current` (2,038,247 rows / 53
files each, matching `EXPECTED_ROWS`). Raw result:

```
current:  766,928 records (members=2,038,247 -- full corpus, confirms the
          population-restriction correction took effect)
baseline: 760,753 records
changed:            8,725  (added 7,450 / removed 1,275)
distinct_anchors_row_term: 7,584
  anchors_pure_added:              6,309
  anchors_pure_removed:              134
  anchors_both_removed_and_added:  1,141
```

**All three of the brief's STOP conditions are triggered simultaneously**:

- `anchors_pure_removed = 134` -- anchors removed with NO same-anchor
  re-add (the brief's first STOP condition, "any anchor is REMOVED with no
  same-anchor re-add").
- `distinct_anchors_row_term = 7,584` -- roughly 25x the brief's "~300"
  ceiling (second STOP condition).
- The scale itself: 7,584 real-corpus anchors touched by a one-line regex
  change is not plausibly the same population as the Planner's 118-anchor
  loss inventory, even accounting for the corrected harness now measuring
  the FULL 2,038,247-row corpus rather than the Planner's 34-fixture /
  21-jurisdiction collateral-risk sweep (third STOP condition: "the
  additions don't plausibly correspond to the loss inventory").

No adjudication performed (out of Developer scope, per brief and per
P-R11/P-R15 -- QA's job, not this pass's). Per the brief's explicit
instruction ("STOP and `ESCALATION:` before committing further"), the
Developer pass halts here: the "chore: gate-2 all-53 execution artifacts"
commit was NOT made, step 9 (`qa_g7_common.INTEGRATION_SHA` re-pin +
evidence regeneration) was NOT run (the SHA-re-pin edit made in
preparation was reverted, working tree clean again), and step 10 (Dev
Complete bookkeeping) was NOT performed. Item 1 stays out of Dev Complete;
the sprint contract frontmatter/Next-Steps/Dev-Complete sections are
untouched by this pass.

**Evidence preserved on local disk, NOT committed** (per the STOP
instruction), for whoever adjudicates next:
`docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/` --
`measure_actual_production_all_rows.py`, `diff_gate2.py`, `run_gate2.sh`,
`.gitignore`, `run_g7_repin.sh` (prepared, not yet run), and
`run/run.log` + `run/compare/{summary.json,changed.jsonl}` (the full
7,584-anchor raw delta; `run/current/`, `run/baseline/`,
`run/baseline-src/` are the multi-hundred-MB raw record dumps, per the
`.gitignore`). A plausible, UNVERIFIED hypothesis for the scale (offered
as a lead, not an adjudication): `_TIGHT_IDIOM_RE` / `extract_quote_
anchored_entries` may be reachable from more of the 53 corpus
jurisdictions in live production than the Planner's fixture-bounded
collateral sweep (34 files, 21 jurisdictions) sampled -- but this is
exactly the kind of thing gate 2's own STOP thresholds exist to catch
before assuming it, not something this pass is positioned to confirm.

## Escalations

**ESCALATION (Developer pass, 2026-08-21):** Gate-2 all-53 execution (run
under the log doc's own §7-corrected harness, not adjudicated) measured
7,584 distinct (row, term) anchors changed by this item's one-line regex
widening across the real 2,038,247-row production corpus -- 6,309 pure
additions, 134 pure removals, 1,141 anchors both added-and-removed. All
three of the brief's numeric STOP conditions trip at once (a pure removal
exists; changed-anchor count is ~25x the "~300" ceiling; the scale does
not plausibly match the Planner's 118-anchor loss inventory even after
accounting for the corrected harness's full-corpus vs. fixture-sample
population difference). The Developer pass halted per instruction rather
than adjudicating or proceeding: gate-2 artifacts were NOT committed,
`qa_g7_common.INTEGRATION_SHA` was NOT re-pinned, and Item 1 was NOT moved
to Dev Complete. Full raw numbers and the corrected-harness methodology
are in "Developer pass (2026-08-21)" above; raw evidence sits uncommitted
under `docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/run/`
for the next adjudicating pass. The code fix itself (`a51b1de`) is
committed, pushed, and independently green against every scoped/guard-
estate/full-suite/frontend/typecheck check run this pass -- the open
question is strictly the true production collateral scope, not the RED
tests or the regex correctness against them.

## Deviations from brief

Step 8 did not reach the "Commit artifacts" instruction and steps 9-10
were not started, per the STOP-and-escalate trigger documented above under
Escalations -- not a scope deviation, the brief's own conditional halt.
Otherwise none. (The FED "approved percentage" row was considered as a
second representative loss and DROPPED in favor of NJ "Public body" once
its recovered text was found to carry an unrelated pre-existing artifact --
a planning-time substitution, not a deviation from the brief's
requirements.)

## Agent roster (manager bookkeeping, append-only)

- planner → af1fb30796df25f99 (spawned 2026-08-20T21:55Z, exited clean @ fa58834; manager verified: diff scope tests+docs only, RED re-run 8F/11P reproduced, c5guard_nj re-point strengthens assertions)

## Manager: gate-2 evidence preserved + director ruling pending (2026-08-21)

Developer STOP was correct per brief. Manager committed the small gate-2
evidence (compare/ + run.log + scripts; record dumps gitignored on disk).
Delta decomposition: 7,584 anchors = 6,309 pure additions + 1,141 re-bounded
+ 134 pure removals, vs the 118-anchor recovery inventory. Investigation
spawned per the director's sprint-1 precedent (investigate before QA);
product ruling on the mass-addition footprint goes to the director with the
findings.

- developer → ad944ba8200be8116 (spawned 2026-08-20T22:40Z, escalated clean @ ad6619f)

## Director ruling on the gate-2 escalation (2026-08-21, manager)

Ruling A: amend the sprint — fix the fallback-suppression guard here (Item 2),
gate 7 bound widened to name that seam. Ruling B: fold the ~9 degraded
re-boundings into scope (Item 3) — nothing ships degraded. One combined
certification run; zero genuine losses to ship. Gate 3 codifies the
sampling+structural adjudication policy per investigation.md.

- investigator (read-only, Sonnet high) → a4c4b766a332fcc7e (delivered investigation.md @ 494b0b4)

## Planner pass 2 (2026-08-21, amendment)

### Item 2 design — candidates measured, footprint, and choice

Enumerated three credible designs for the guard site (`us_profile.py`
~2551):

- **(a) Full union, no per-term filter.** Every call to
  `extract_definitions_from_section` with `heading_was_derived=True` runs
  the fallback and appends ALL of its candidates, regardless of term
  collision with the primary engine. **Rejected**: strictly dominated by
  (b) — measured identical new-term footprint (same set-difference), PLUS
  it reintroduces the EXACT same-term-collision hazard Item 3 fixes,
  site-wide: on the 200-row seeded sample below (rows where primary
  already finds ≥1 entry), the fallback's own term set overlapped the
  primary's on 200/200 rows (100%) — every one of those becomes a NEW
  same-key collision under (a), landing on whichever candidate is
  first-in-list (no protection at all).
- **(b) Per-term admission (chosen).** Admit a fallback candidate only
  when its own term does not collide with any primary-engine term on that
  row, further filtered by a narrow, evidence-derived implausible-capture
  rejection (below). Recovers all 130 genuine losses (full population,
  verified — see "130/130 recovery check"). Cannot ever reintroduce a
  same-term collision (that is the filter's entire purpose), so it cannot
  create NEW Item-3-shape hazards.
- **(c) Structurally cleaner variant (positional overlap-avoidance).**
  Considered: admit a fallback candidate only when its own text span does
  not overlap the primary engine's own claimed span. Rejected as
  currently unbuildable within bounds: this requires span/position
  tracking inside `_extract_inline_quoted_definitions`, whose own
  internals are explicitly forbidden by the amended gate 7.

**Footprint measurement** (methodology: direct-function replay of
`USProfile.extract_definitions_from_section`/`_extract_inline_quoted_
definitions`, the same approach investigation.md's Q1 validated as 100%
accurate against the real gate-2 diff; scripts run from this session's
scratchpad, not committed):

- **130-row genuine-loss population** (investigation.md's full table,
  minus the 4 phantom rows): 130/130 recovered under design (b) with the
  evidence-derived junk filter; 0 false rejects.
- **Seeded 200-row sample** (seed `f"{20260821}:{jurisdiction}"`,
  proportional draw across the 16 jurisdictions reachable through
  family-3/OH/ME, filtered to rows where the primary engine already finds
  ≥1 entry today): 61/200 rows (30.5%) gain ≥1 new fallback term under
  design (b), 122 new terms total — extrapolates (rough, not a certified
  count) to roughly 13,100 of the ~42,974 defs-headed rows across those
  16 jurisdictions. **Precision spot-check (20 of the 122, full text, not
  display-truncated) is MIXED**: several are clean, complete real
  definitions (e.g. VA "facilitates the sale", a coherent multi-part
  statutory exclusion); several others carry the fallback's own
  documented no-trailing-stop-cutoff weakness, bleeding into the next
  entry's own lead-in text (e.g. FED "Iran" -> `"...the District of
  Columbia.\n\n(4) Person\n\nThe term"`; FED "trust" similarly); one is an
  outright false positive with a garbage numeric term key ("1501") paired
  with 1,029 chars of unrelated Executive Order text. This is a
  MATERIALLY different, more mixed precision profile than Item 1's own
  widening (80/80 sampled genuine, 0% FP) — flagged here for gate-2/QA to
  sample this specific sub-population (rows where primary already had
  ≥1 entry, now gaining more) separately from the 130-row recovery (which
  IS clean by construction: every one of those 130 is a real, previously-
  captured statutory definition, verified in investigation.md's own
  table). Not resolved by this pass — the amended gate 7 authorizes the
  guard-site fix; it does not pre-adjudicate the new population's
  precision, and building a broader quality filter would require touching
  `_extract_inline_quoted_definitions`'s own internals (forbidden) or
  guessing at additional vocabulary (against the sprint's own "no
  speculative additions" discipline) — a QA sampling pass against the
  real gate-2 corpus-wide diff is the right next check, not a Planner-
  authored heuristic.

**The implausible-capture filter** (needed to satisfy the brief's
negative-control requirement — literal per-term admission alone
resurfaces investigation.md's 4 phantom terms, verified directly): reject
an otherwise-admissible fallback candidate when (a) its term, stripped, is
a bare common English function word (closed list: for/and/or/the/a/an/of/
in/to/with/by — matches the observed "for" shape) or (b) its term OR
definition_text begins with `^\d{4}[—–-]` (a 4-digit year immediately
followed by an em/en dash or hyphen — matches the observed "2010—Subsec.
..."/"2006—Subsec. ..." shape). Validated: 0 false rejects across the
full 130-row genuine population; 100% correct rejection of all 4 known
phantom terms (FED rows 2333/4978/34432). This filter applies uniformly
(both to the always-existed zero-candidate path and the new merge path) —
a strict quality improvement wherever it fires, not scoped narrowly to
just these 4 rows.

### Item 3 design — one mechanism covers both named shapes

Diagnosed directly against real corpus text (WA row 148, NY row 6675, and
spot-checked FED "correct" row 42191 from investigation's own "4 more
instances" list): all three exhibit the IDENTICAL shape — the same exact
term string quoted twice in one section body, once via an idiom
`_TIGHT_IDIOM_RE` recognized BEFORE this sprint's Item 1 widening
(`means`/`shall mean`/bare `has the meaning`) and once via an idiom ONLY
the widening added (`shall include`/`has the following meaning`/`has the
same meaning`). `extract_quote_anchored_entries` builds `starts` in text
order with no per-term collision handling; downstream, whichever
occurrence reaches `all_candidates` first wins the persist-time dedup
(`pipeline.py` ~line 400, `key = (owning_art.id, tuple(sorted(candidate.
terms)))`, first-occurrence-wins, unchanged by this item). In every
verified instance the NEW (widened-idiom) occurrence sits textually
BEFORE the pre-existing one, so it wins and displaces the correct one.
This is investigation's "displacement family" AND the "list-introducer
corruption" at once — not two defects, one.

Fix lives entirely inside `extract_quote_anchored_entries`
(`us_markers_boundary.py`, already an authorized file) — the
term-set-dedup fallback allowance in the amended gate 7 was NOT needed;
the seam is upstream of it. Filtering `starts` before `close_entries`
means a term with only one recognized occurrence (the validated-genuine
6,309 additions, and the 1,114/1,141 monotonic re-boundings) is
structurally untouched by construction — the filter only ever acts on a
term with 2+ occurrences in one call.

**NY row 6675 diagnosis correction.** investigation.md's Q3 names this row
as the sprint's "1 outright corruption." Diagnosed this pass, verified TWO
independent ways (a direct `extract_definitions_from_section` call, and
the real `ingest_us_statute_rows` -> `run_definition_linking` pipeline):
this row does NOT reproduce the corruption at persistence altitude. NY
carries 38 baseline blocks (`_split_into_numbered_blocks`), so `all_blocks
= baseline_blocks + priority_blocks + extra_blocks` puts baseline FIRST;
baseline's own `_leading_quote_candidate` already finds sub-item (c)'s
clean "means" candidate as its own block, and NY has no
`priority_before_single_baseline=True` registration (only US-WA,
`us_markers_inline_quote.py`, and US-FED, `us_markers_fed_good_
samaritan.py`, do) — so family-3's own colliding candidates (bad AND
good) are appended AFTER baseline's, and the FIRST-occurrence-wins
persist dedup picks baseline's already-correct entry both before and
after Item 1's widening. This explains why the "displacement family" (~8
rows) and NY's row are grouped separately in the mandate: the
displacement family requires a jurisdiction where family-3 wins ordering
ahead of baseline (WA/FED, both `priority_before_single_baseline=True`);
NY does not have that property for this row. Kept in the test suite as a
verified regression pin (currently green, must stay green), not a RED —
the general mechanism is still real (proven via the WA row and two fully
synthetic M-R107 controls reproducing BOTH named shapes cleanly). Flagged
for the director/manager: this is a genuine discrepancy with
investigation.md's own characterization, not a re-litigation of it — the
underlying gate-2 "records.jsonl" this session cannot access directly
might reflect a detail not captured by this pass's direct-function/
full-pipeline replay; worth a second look if it matters for certification
sign-off, but does not change what Item 3 must fix (the general
mechanism, not this one row).

### Stale-pin sweep (Items 2-3)

Traced (not just grepped): every file importing `_extract_inline_quoted_
definitions` (19 files) or referencing `heading_was_derived` (22 files)
across all four test roots — cross-referenced against `git grep -l
"extract_definitions_from_section\|extract_quote_anchored_entries"`.
Confirmed via direct execution (this pass's monkeypatched simulation of
BOTH specs together, run against each candidate file, then the full
suite) rather than by inspection alone.

- **`test_us_body_preamble_g8_local_scope_dispatch_red.py`** — ONE real
  hit, re-pointed this pass. `test_b1_local_candidate_precedes_but_does_
  not_suppress_distinct_section_candidate` pinned `extract_definitions_
  from_section`'s own return value as EXACTLY `[("Section companion",)]`;
  Item 2's merge additionally (harmlessly) surfaces "Scope probe" as a
  second section-candidate (the broader fallback, now always run, finds
  it independently of the primary engine's own numbered-block
  segmentation). Verified this is inert at persistence altitude:
  pipeline.py's EXISTING `used_body_derived_heading` inner dedup
  (unchanged by this item) already discards any section-candidate whose
  term-key collides with an already-registered LOCAL candidate key before
  it reaches the final persist dedup — the row's actual persisted
  Definitions are byte-identical before and after. Re-pinned to assert
  "Section companion" is present and no OTHER term besides "Scope probe"
  leaks in, rather than an exact single-element list.
- **`test_us_g8_candidate_collision_preference.py`** (514 lines, pins the
  EXACT `pipeline.py` first-occurrence-wins persist dedup Item 3 could
  have touched) — traced and run explicitly: its fixture is a real
  Arkansas row, and AR has NO registered `EntrySplitterRule` reaching
  `extract_quote_anchored_entries` at all (confirmed:
  `us_markers_inline_quote._OTHER_JURISDICTIONS` and the OH/ME wrapper
  modules never name `"US-AR"`) — Item 3's fix, scoped entirely inside
  that function, cannot reach this row by construction. 8/8 tests in this
  file pass unchanged under the full Item 2+3 simulation.
- **`test_us_markers_wave1_inline_quote_fallback.py`,
  `test_us_markers_not_yet_rescued_subcases.py`,
  `test_us_markers_wave1_auto_rescue_subcases.py`** (the other files most
  directly exercising `_extract_inline_quoted_definitions`/
  `heading_was_derived`, from the ancestor 2026-08-04-defs-us-markers
  sprint) — 27/27 tests across these three files pass unchanged under the
  full simulation.
- Full suite under the full Item 2+3 simulation: 1386/1388 pass; the 2
  non-passing are both expected artifacts, not regressions — (1) this
  pass's OWN sanity test asserting "today's" (pre-fix) primary-only
  behavior, which is inherently incompatible with a GLOBAL method-level
  patch (the assertion's whole point is to document the UNPATCHED state);
  (2) the pre-existing, already-broken `test_g7_integration_pin_is_
  ancestral_and_production_is_frozen_after_it` (stale `qa_g7_common.
  INTEGRATION_SHA`, dating to Item 1's own `a51b1de` landing — confirmed
  via `git stash` + direct re-run that this fails identically with NONE
  of this pass's files present; explicitly out of Planner scope per the
  Developer pass's own STOP note, "step 9 ... was NOT run").

No other hits across `backend/tests/{unit,integration,e2e,fixtures}`
required re-pointing.

### Simulation methodology

`_TIGHT_IDIOM_RE`-style monkeypatch is insufficient here (Item 2/3's
fixes change CONTROL FLOW, not a single swappable regex constant).
Verification script (scratchpad, not committed) patches
`USProfile.extract_definitions_from_section` with a faithful
reimplementation (copied from the real method, only the guard section
changed to Design (b)+filter) via `unittest.mock.patch.object`, and
separately patches `extract_quote_anchored_entries` (module-level, plus
every test/rule module that imported it by name — Python binds a fresh
reference at import time, so patching the defining module's attribute
alone does not reach already-`from`-imported names) with a reimplementation
of the starts-building loop plus Item 3's collision filter, delegating to
the REAL, unmodified `close_entries`/`compute_hard_stops`. Both patches
active together for every run reported above.

## Director ruling: wave + filter (2026-08-23, manager)

Expansion-wave precision sample (expansion_precision.md @ a9653f6): census
8,708 terms / 4,419 rows / 16 jurisdictions; 90/9/1 GENUINE/FP/AMBIGUOUS;
term-key filter (reject `Pub. L.` / `Subsec.\(` keys) cuts FP to 4/100 with
zero genuine collateral. Director ruled: ship wave + extended filter;
restore-only rejected under D-RECALL-FP (~7,837 genuine forfeited);
next-entry-bleed byte quality named tracked debt under D-MAP. Item 2 spec
amended in the contract. Next: Planner micro-pass pins the extended filter
(RED negative controls), then Developer implements Items 2+3.

- precision sampler (read-only, Sonnet high) → a1e8399ebf3c24f79 (delivered expansion_precision.md @ a9653f6; first attempt a2f644504ea003c2f died to machine sleep mid-git-compare — worktree restored by manager, containment rule added to the retry brief)
