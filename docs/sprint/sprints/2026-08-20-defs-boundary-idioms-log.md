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

## Escalations

None raised.

## Deviations from brief

None. (The FED "approved percentage" row was considered as a second
representative loss and DROPPED in favor of NJ "Public body" once its
recovered text was found to carry an unrelated pre-existing artifact — a
planning-time substitution, not a deviation from the brief's
requirements.)
