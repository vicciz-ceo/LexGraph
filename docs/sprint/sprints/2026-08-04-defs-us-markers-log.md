# Panel log — sprint 2026-08-04-defs-us-markers

Append-only. Per program ruling P-R3 the Planner, Developer and QA speak with
one another THROUGH the sub-manager; every exchange is recorded here.
Escalations the panel cannot settle go to the program manager (and from there
to the director).

---

## M0 — sprint manager setup (2026-08-04)

**Manager (Opus/high).** Read in mandated order: program doc, recon dossier
(§2 family 3 + §6 addendum findings #1/#2 + per-jurisdiction detail), this
sprint's contract, `docs/sprint/repo-profile.md`. Also read the prior sprint's
`## Known limitations at sprint close` (2026-08-02-us-state-law.md:234-269) to
pin the boundary-precision residual this sprint inherits.

Workspace established per brief:
- Worktree `/Users/nerya/LexGraph-wt/defs-us-markers`, branch
  `claude/defs-us-markers`, based on `origin/main` @ `83532fe`.
- Own backend venv built (`python3.13`, `pip install -e '.[dev]'`, rc=0,
  Python 3.13.12) — the known worktree-venv trap avoided.
- `git config user.email` verified =
  `256402398+vicciz-ceo@users.noreply.github.com` before any commit.
- CodeGraph verified working (`codegraph` CLI on PATH; index at
  `/Users/nerya/LexGraph/.codegraph` was built against `main` @ `83532fe`,
  which is exactly this worktree's base commit — so the index is current for
  our base tree).

**Coordination state at spawn time.** `origin/claude/defs-core-scope` exists
with one commit (`5b93ef8`, planner lock + C5 baseline). Its contract declares
the `## Seam spec (published)` section as the core Planner's FIRST deliverable
but that section is **not yet published**. Per this sprint's brief the Planner
plans and authors RED tests meanwhile, and polls for the seam spec.

**Baseline measured by the manager in THIS worktree** (not inherited from a
doc): `backend/.venv/bin/pytest backend/tests -q` →
`641 passed, 18 warnings in 17.24s`. This matches the prior sprint's recorded
close-out number (641), so the tree is clean at `83532fe`. Any RED the Planner
introduces must be visible against exactly this number.

---

## M1 — manager rulings (standing, this sprint)

- **U-R1 — "Captured" means captured CLEANLY.** Inherited from the prior
  sprint's residual (2026-08-02 known limitations): a definition counts as
  captured only with the right term AND the right boundary. Explicitly NOT
  captured: 21,174-char swallow-the-neighbour bodies, sentence-fragment
  "terms", degenerate near-empty definitions (prior measured rates: corpus
  424/258,472 = 0.16% over 5,000 chars; TX letter-led recovered subset 17.33%
  degenerate). The Planner must express this as measurable RED assertions, not
  prose.
- **U-R2 — The fallback rewiring is a JOINT decision with the core panel.**
  `_extract_inline_quoted_definitions` (pipeline.py:246-289) is gated on
  `used_body_derived_heading` (pipeline.py:405/429) and is the single
  highest-impact fix in the program (VA 93% / WA 90% / FED 77% of misses
  rescuable). It lives in the exact code core's C3 gate is migrating. No
  Developer of this sprint touches it until both Planners have recorded the
  boundary IN WRITING in both contracts. Disagreement escalates to the program
  manager.
- **U-R3 — Correctly-empty classifier is a first-class deliverable.** Pure
  cross-reference sections ("The definitions in ss. 851.01 to 851.31 apply…"),
  `Repealed.`/`Expired.` bodies are correctly empty and must NOT be counted as
  misses — but the classifier must be defined by the Planner and independently
  verified by QA, not asserted by the Developer to explain away a residue.
- **U-R4 — P-R2 applies per conflict class.** Any sub-case where zero-miss
  can only be bought with a false-positive risk stops and escalates with real
  statute rows; the panel never silently picks a side.

---

## P1 — planner pass 1 (2026-08-04)

Sonnet/high. Read in mandated order (contract, this log's §M0/§M1, program
doc, recon dossier §2/§6, prior sprint's known-limitations, fixtures
README). CodeGraph used first for all code location (`pipeline.py`'s Stage-2
dispatch, `us_profile.py`, `profiles.py`, `extract.py`) — then the worktree
files were Read directly before any test was written. Core seam polled:
`git -C /Users/nerya/LexGraph fetch origin && git show
origin/claude/defs-core-scope:docs/sprint/sprints/2026-08-04-defs-core-scope.md`
still shows only the planner-lock skeleton (no `## Seam spec (published)`
section) — unchanged since `5b93ef8`. Proceeding per the brief: RED tests
authored now against the real production entry point, implementation
sequencing left to the boundary proposal below.

### 1. Live re-confirmation (real code, real vaquill rows, this worktree's venv)

All 12 named sub-cases were run against the REAL current functions
(`is_definitions_heading`, `extract_definitions_from_section`,
`_extract_inline_quoted_definitions`, all imported unmodified from
`app.definition_links`) over the REAL named row (or, where the dossier
named no row, a row found by scanning the real parquet file). Method:
`backend/.venv/bin/python` (pyarrow 25.0.0 is present in this worktree's
venv — no separate scratch venv needed this pass), reading directly from
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`
(read-only, per data policy; nothing downloaded, no test reads this path).

| Sub-case | Row | `is_definitions_heading` | extractor candidates | inline-fallback candidates | Reproduces recon? |
|---|---|---|---|---|---|
| No-marker inline-quote (VA) | `STATE_VA_T23.1_SI_C3_S23.1-300` | True | 0 | **9** | YES (recon: 9) |
| Bare `(N)` numeric (SC) | `STATE_SC_T5_C1_S5-1-20` | True | 0 | 2 (boundary-noisy: "Municipality"'s captured text ends with a literal `"(2)"` fragment) | YES |
| Mojibake curly quotes (RI) | `STATE_RI_T35_C35-13_S35-13-2` | True | 0 | **0** — mojibake `\x80\x9c`/`\x9d` bytes are not recognized as quote chars by EITHER path | YES, and note: unlike VA/WA/FED, RI is **not** rescued by wave-1's mechanism at all; it needs its own normalization fix first (see wave plan) |
| Nested lettered sub-clauses (UT) | `STATE_UT_T75B_S75B_1_301` | True | 0 | 5 (Asset protection trust, Creditor, Domestic support obligation, Insolvent, Transfer) | YES, and: the existing inline fallback already handles UT's nesting shape acceptably — UT is **largely auto-rescued by wave 1's mechanism**, not a separate implementation item |
| Colon-then-list (TN) | `STATE_TN_T50_C2_S50-2-115` | True | 0 | **0** — idiom is "Has the same meaning as interpreted by...", which does not match `_MEANS_IDIOM_GAP_RE`'s literal `has the meaning` | YES, and: TN is **not** rescued by wave 1 either; needs its own idiom-shape handling |
| ALL-CAPS singular DEFINITION (TX) | `STATE_TX_Cfi_C37_S37.001` | True | 0 | 1 (`emergency`, 738 chars, clean) | YES, and: TX is auto-rescued cleanly by wave 1's mechanism |
| Prose body under matched heading (OR) | `STATE_OR_T19_C197a_S197a.348` | True | 0 | 1 (`needed housing`, 3,182 of 3,332 body chars — swallows nearly the whole section; needs closer inspection before calling this "clean", flagged for a later wave) | YES |
| Prose body under matched heading (PA) | `STATE_PA_T42_C83_S8322` | True | 0 | 1 (`joint tort-feasors`, 171 chars, clean — the whole body IS this one definition) | YES |
| Unquoted terms (DC) | `STATE_DC_T28_C25_S28-2501` | True | 0 | **0** — no quote characters anywhere in the body (`A bond ... means an obligation ...`) | YES, and: DC's unquoted-term shape needs a wholly separate (non-quote-anchored) extraction rule; not touched by wave 1 |
| Multi-term shared clause + F3 (VT) | `STATE_VT_T23_C35_S3700` | True | 0 | **0** — each of the 4 comma-joined quoted terms (`"mail," "mails," "mailing," "mailed"`) is immediately followed by another quote character, which `_MEANS_IDIOM_GAP_RE`'s negated-quote gap can never cross | YES. **Flagging the family-3/family-5 overlap to the program manager per the brief — not claiming this row unilaterally; it needs the `defs-us-multiterm` sprint's own splitting logic before VT's shape can be captured cleanly** |
| Unquoted ALL-CAPS terms (AL) | `STATE_AL_T1_C19_S22-19-141` | True | 0 | **0** — body is `(1) ORGAN. Organs, tissues, ...` (all-caps term, no quotes, period-terminated marker) | YES (recon: AL "unquoted caps"). Full-corpus AL: **1,603/1,653 (97.0%)** Definitions-headed sections yield 0 — a much larger miss than recon's small 400-row sample suggested (6/400 ≈ 1.5% capture ⇒ ~98.5% miss, consistent at scale). Not rescued by wave 1 (no quotes at all) |
| Bare digit-dot (AZ) | `STATE_AZ_T15_C14_A7_S1871` | True | 0 | 17 (clean: `Account`, `Account owner`, ...) | YES, and: AZ's bare `"1."` markers (vs `"(1)"`) still precede quoted terms, so wave 1's quote-anchored fallback **already rescues most AZ rows** without any AZ-specific code. Full-corpus AZ: 2,985/3,015 (99.0%) zero-candidate |

**Everything reproduces.** No recon claim needed correction this pass. Two
items sharpen recon's picture rather than contradict it: AL's miss rate is
far higher at full-corpus scale (97.0%) than the 400-row sample implied on
its own, and VT is confirmed to sit at the family-3/family-5 boundary (flag,
not a unilateral claim).

### Cross-cutting finding #1 table — full-corpus re-verification

Recon's table (dossier §6) was built from a 500-row keyword-prefiltered
sample per state. This pass re-ran the exact same live functions over the
**entire** real parquet file for all 7 states in the table (not a sample):

| Jur | total rows | Definitions-headed | zero-candidate | % | rescuable by (unmodified) inline fallback | % of zero |
|---|---|---|---|---|---|---|
| VA | 33,856 | 1,096 | 1,065 | 97.2% | 1,025 | 96.2% |
| WA | 51,498 | 1,800 | 1,778 | 98.8% | 1,682 | 94.6% |
| WV | 25,460 | 1,068 | 297 | 27.8% | 263 | 88.6% |
| WI | 18,158 | 541 | 62 | 11.5% | 42 | 67.7% |
| WY | 10,219 | 495 | 56 | 11.3% | 25 | 44.6% |
| DC | 23,694 | 1,216 | 332 | 27.3% | 114 | 34.3% |
| FED | 54,853 | 1,920 | 1,600 | 83.3% | 1,477 | 92.3% |

Recon's percentages (VA 97%, WA 98%, WV 29%, WI 12%, WY 12%, DC 27%,
FED 84%; rescuable 93/90/84/65/48/35/92% of zero) all reproduce within
1-3 points — a genuine full-corpus confirmation, not a correction. Absolute
row counts differ slightly (recon sampled ≤500/state and reported implied
totals; this pass scanned every real row), so this pass's numbers are the
more authoritative ones going forward for U6's before/after tracking.

### A material finding beyond recon's own claims: FED's "rescuable" bucket is not clean

Recon's cross-cutting finding #1 measured only WHETHER the existing fallback
returns >0 candidates on the zero-candidate rows — it never checked the
BOUNDARY QUALITY of what comes back. This pass did, because U-R1 requires
it, and found a real, quantifiable, FED-specific hazard distinct from the
prior sprint's CA "swallow to end of section" precedent:

- Across VA+WA+FED's 36,694 total inline-fallback candidates (all rows,
  full corpus), 414 (1.13%) are >=5,000 chars — VA 0.073%, WA 0.111%,
  **FED 3.30%** (30-45x VA/WA's rate).
- Of FED's Definitions-headed zero-candidate sections, **1,328/1,600
  (83.0%) contain an appended "Editorial Notes"/"Amendments"/"Statutory
  Notes"/"References in Text" block** — non-operative historical/amendment
  commentary the vaquill dataset bundles into the same `text` field as the
  operative statute.
- Of the 390 FED candidates >=5,000 chars, **387 (99.2%) come from a row
  with that appended-notes shape.** Worst observed: `USC_T8_C12_S1101`
  (the Immigration and Nationality Act's famous mega Definitions section,
  354,159 raw chars) — naively firing the unmodified inline fallback over
  its full text produces a 128,319-char "definition" whose captured "term"
  is itself a sentence fragment of amendment commentary (`.\n\nSubsec.
  (a)(43). Pub. L. 103-416, §222(a), amended par. (43) generally...`), not
  a real defined term at all.
- This is NOT limited to pathological mega-rows: even a small, otherwise
  clean 3-term FED row (`USC_T16_C65_S4503d`, 1,025 chars) has its LAST
  entry ("State") swallow the trailing citation plus "Editorial Notes"
  header (626-char definition_text, containing the literal string
  "Editorial Notes") — this is systematic on FED's LAST recognized entry
  whenever notes are present, not a corner case.

This is why wave 1's RED tests (below) assert content-based boundary
guards (no `"Editorial Notes"`/`"References in Text"` leakage, no
degenerate near-empty collapse, no phantom nested term) rather than only
`len(created_definitions) > 0` — a naive "just delete the
`used_body_derived_heading` gate" fix would pass a bare-existence test and
still fail these. Two more real, small-row-confirmed defects, independent
of the notes issue: VA's `STATE_VA_T4.1_SII_C6_S4.1-600` ("sell" collapses
to a 1-char `"."` definition via a false idiom match on unrelated prose
"...by any means.") and WA's `STATE_WA_T9A_C04_S110` ("Vehicle" collapses
to `"a"` because its own definition contains a nested quoted phrase,
`"motor vehicle"`, which the fallback misreads as a second top-level term).
Full detail, byte-exact, is in the RED test file's docstrings (§4 below).

This does not rise to a P-R2 escalation (zero-miss vs. zero-false-positive):
truncating a FED body at its own "Editorial Notes"/"Amendments" boundary
before extraction serves BOTH zero-miss (the real definitions before that
boundary are still captured) AND zero-false-positive (notes commentary is
correctly excluded) at once. It is an engineering requirement for wave 1's
implementation, not a value tradeoff — recorded here, and reflected in the
RED tests, rather than escalated.

### 2. The correctly-empty classifier (gate U4, ruling U-R3)

Defined and applied live against the SAME 7-state zero-candidate set above
(1,600+1,065+1,778+297+62+56+332 = 5,190 real rows), in strict priority
order (a row is classified by the FIRST rule it matches):

1. **Terminal-status body.** The entire (whitespace-stripped) body is
   exactly one of `Repealed.` / `Expired.` / `Reserved.` / `Renumbered.` /
   `Recodified as ...` / `Omitted.` / `Vacant.` (optionally bracketed,
   optional trailing period) — the section carries no operative text at
   all because the law itself says so. Real examples: DC
   `STATE_DC_T47_C28_S47-2843` (body: `"Repealed."`), DC
   `STATE_DC_T2_C3_S2-308.13` (body: `"Recodified as § 2-381.01."`).
   Measured: **DC 178/332 (53.6%)** of DC's zero-candidate set is this
   class alone — the single largest component of DC's apparent "miss."
2. **Pure cross-reference body.** The entire body states that the
   definitions governing this text live in ANOTHER section/chapter/article,
   with no operative defining content of its own (pattern: `(the )?
   definitions? (contained |set forth )?in <citation> (apply|shall apply|
   govern|are applicable)`, matched at the START of the stripped body,
   case-insensitive). Real examples: WI `STATE_WI_C851_S851.002` (`"The
   definitions in ss. 851.01 to 851.31 apply to chs. 851 to 882."`), WY
   `STATE_WY_T99_C3_S99-3-1101` (`"The definitions in W.S. 99-3-101 apply
   to this article."`). Measured: **WA 734/1,778 (41.3%)**, WY 19/56
   (33.9%), WI 2/62 (3.2%), VA 2/1,065 (0.2%). WA's true "rescuable" share
   (see table above, 94.6% of zero-candidate) is measured BEFORE this
   classifier is subtracted out — once cross-reference rows are correctly
   excluded, WA's genuine-miss population is smaller and cleaner than the
   raw zero-candidate count implies. This regex is a first pass (real,
   decidable, and independently re-runnable by QA) — it does not yet catch
   the reverse phrasing (`"X" is defined in <citation>`, seen once in WA:
   `STATE_WA_T4_C92_S005`) or single-term cross-references
   (VA `STATE_VA_T38.2_C8_A2_S38.2-808`: `'"agent" shall have the meaning
   as set forth in § 38.2-1800'`) — both real, both currently fall into
   class 4 below, flagged as a classifier follow-up, not silently dropped.
3. **Rescuable by the (already-existing) inline-quote fallback** — not
   "correctly empty," a genuine wave-1-fixable MISS. Rates: see the
   cross-cutting table above.
4. **Other / needs further triage.** Everything not matched by 1-3. Spot
   inspection (10-15 rows per state, all 7 states) shows this bucket is
   mostly further, already-named family-3 shapes — a defining idiom wave
   1's `_MEANS_IDIOM_GAP_RE` does not recognize (`shall include`,
   `includes`, `shall be deemed to refer to`, single-term
   `"X" shall have the meaning set forth in <cite>`) — not a new family,
   but genuinely NOT auto-fixed by wave 1 either; sized at VA 40/1,065
   (3.8%), WA 88/1,778 (4.9%), FED 123/1,600 (7.7%), DC 40/332 (12.0%),
   WV 34/297 (11.4%), WY 12/56 (21.4%), WI 18/62 (29.0%). **QA must
   independently re-run this classifier (it is 3 real regexes, committed
   nowhere yet -- see the follow-up below) against the full 7-state
   zero-candidate set per U-R3** before any zero-miss sweep (gate U4)
   treats bucket 4 as fully triaged; this pass sampled it, it did not
   exhaustively classify it.

**Follow-up for whoever implements the classifier for real**: this pass's
classifier regexes live only in a scratchpad script
(`/private/tmp/claude-501/.../scratchpad/classify_zero_candidate.py`, not
committed — per data policy, no committed code reads the parquet snapshot).
A wave item should port the terminal-status and cross-reference regexes
into a committed, testable module (candidate home: a new
`app/definition_links/correctly_empty.py`, profile-dispatched per U3) so
QA's independent re-verification (U-R3) has a real function to call, not
just a description in this log.

### 3. Wave / item plan (see contract `## Next Steps` for the short form)

Ordered by corpus impact (zero-candidate row count from the tables above),
each independently testable, each naming its gate(s):

1. **Wave 1 (THIS PASS — RED tests authored below).** No-marker
   inline-quote, VA/WA/FED, + boundary-precision guards (degenerate
   near-empty, phantom nested term, editorial-notes swallow). Serves U1,
   U6. Corpus impact: 1,065+1,778+1,600 = 4,443 zero-candidate rows in
   these 3 states alone. **Side effect, not separately implemented**: the
   SAME underlying fix (once it stops swallowing notes/false-idioms
   correctly) also rescues UT's nested-lettered-subclause shape and TX's
   ALL-CAPS-singular shape and most of AZ's bare-digit-dot shape, all
   confirmed live this pass — these get their own named-row RED tests in a
   thin follow-up wave for QA-independent verification, but are not a new
   implementation item. **BLOCKED on the core seam** (touches
   `pipeline.py`'s exact `_extract_inline_quoted_definitions` /
   `used_body_derived_heading` gate, which is core's C3). Tests are NOT
   blocked — authored and RED now against the real production entry point.
2. **Wave 2 — idiom-set broadening.** Recognize `shall include`,
   `includes`, `shall be deemed to refer to`, and single-term
   `"X" shall have the meaning set forth in <cite>` as valid entry
   boundaries (shrinks bucket 4 of the classifier above). Serves U1, U4.
   Corpus impact: VA 40, FED 123 residual rows (this pass's sample; not
   yet a full count). **BLOCKED on core** (same shared code area as wave
   1 — same file, same function family).
3. **Wave 3 — SC/AZ residual bare-marker splitting.** SC's bare `(N)`
   without letter suffix (confirmed: extractor 0, fallback rescues but
   with boundary noise -- `"Municipality"`'s captured text ends with a
   literal `"(2)"` fragment, needs a boundary fix even where "rescuable").
   AZ's small residual (its dominant shape auto-rescues per wave 1, but a
   minority of rows use no quotes at all, same shape as OR/PA prose). Serves
   U1. **Possibly NOT blocked on core** if the registry seam (C4) supports
   an additive per-jurisdiction splitter rule rather than editing the
   shared extractor — open question for the boundary proposal below.
4. **Wave 4 — RI/AK mojibake-quote normalization.** RI confirmed live:
   NEITHER path recognizes `\x80\x9c`/`\x9d` mojibake bytes as quote
   characters, so RI is NOT auto-rescued by wave 1 (unlike UT/TX/AZ).
   Needs `normalize_for_parsing` (or a profile-level override of it) to
   also collapse this specific mojibake byte sequence to a plain quote.
   Corpus impact: RI's dominant miss cause, 75/500 (15%) per recon,
   full-corpus count not yet run. Serves U1. **Open question for the
   boundary proposal**: `normalize_for_parsing` is one of the profile
   Protocol's dispatched methods (per dossier §1) -- broadening its
   mojibake table is purely additive (recognizes MORE input, changes no
   existing passing behavior) and arguably safe to do independent of
   core's C3/C4 timing. Flagged to core rather than assumed.
5. **Wave 5 — DC unquoted-term definitions.** Confirmed live: zero quote
   characters anywhere in the body (`A bond ... means an obligation...`) --
   needs a wholly separate, non-quote-anchored extraction rule, not a
   variant of the inline-quote fallback. Corpus impact: a minority of DC's
   332 zero-candidate rows (most of DC's zero-candidate set is class-1
   "Repealed." per the classifier above, not this shape). Serves U1.
   Ships as a NEW registry module per U3 -- likely not blocked on core's
   C3 (doesn't touch the inline-quote fallback at all), though it likely
   DOES need core's C4 registry seam to exist first to have a home.
6. **Wave 6 — TN colon-then-list.** Confirmed live: NOT rescued by wave 1
   (idiom "has the same meaning as interpreted by" doesn't match the
   literal `has the meaning` check). Needs bespoke handling. Serves U1.
   Corpus impact: TN's dominant family-3 volume is actually F1
   (scoped-inline, that sprint's territory per the recon's per-state
   table) -- this specific colon-then-list shape is a minority within TN.
7. **Wave 7 — OR prose-body boundary check.** `needed housing` on the
   named OR row captures 3,182 of 3,332 body chars (nearly the whole
   section) -- not yet confirmed clean or swallowing; needs closer
   per-row inspection before being folded into wave 1's "auto-rescued"
   list. Serves U1.
8. **VT overlap -- flagged to the program manager, not claimed.**
   `STATE_VT_T23_C35_S3700` is simultaneously family 3 (detected heading,
   0 candidates) and family 5 (multi-term shared clause,
   `"mail," "mails," "mailing," "mailed"` -- each quoted term is
   immediately followed by another quote, which defeats the fallback's
   negated-quote gap regardless of idiom recognition). Per the brief, this
   belongs to `defs-us-multiterm`'s splitting logic, not claimed here.
9. **Not yet assigned a wave: AL's unquoted-ALL-CAPS shape** (confirmed
   live, 1,603/1,653 = 97.0% zero-candidate, NOT rescued by wave 1 -- no
   quotes at all, same non-quote-anchored problem as DC). Belongs with
   wave 5's non-quote-anchored rule, or its own wave -- left for the next
   planner pass to size once wave 1 lands and the core seam is known;
   flagged here so it is not lost. AL was NOT one of the sub-cases with
   RED tests authored this pass (only VA/WA/FED wave-1 tests were, per the
   brief's explicit scope for this pass).
10. **Correctly-empty classifier, committed for real** (see §2 follow-up
    above) -- needed before U4's zero-miss sweep can rely on it
    independent of this log.

### 4. RED tests authored this pass (wave 1 only, per the brief's scope)

New fixture: `backend/tests/fixtures/us_statutes/us_markers_wave1_rows.json`
-- 6 real rows, full original parquet columns, values unmodified, vendored
from `us_va_statutes.parquet` (2), `us_wa_statutes.parquet` (2),
`us_federal_statutes.parquet` (2):

- `STATE_VA_T23.1_SI_C3_S23.1-300` -- clean rescue, 9 real terms (recon's
  own named VA row).
- `STATE_VA_T4.1_SII_C6_S4.1-600` -- real VA cannabis-law Definitions
  section, 48 genuine terms + the "sell"-collapses-to-1-char defect.
- `STATE_WA_T47_C14_S020` (`RCW 47.14.020: Definitions.`) -- clean rescue,
  2 real terms, the exact row recon's own dossier quotes for WA.
- `STATE_WA_T9A_C04_S110` (`RCW 9A.04.110: Definitions.`) -- real WA
  criminal-code Definitions section, the "Vehicle"/"motor vehicle"
  phantom-nested-term defect.
- `USC_T16_C65_S4503d` -- small (1,025-char) clean-LOOKING FED rescue, 3
  real terms, but exposes the trailing-notes-swallow-on-last-entry defect.
- `USC_T15_C12_S431` -- small (3,239-char) FED row exposing the
  editorial-notes-swallow defect directly (`"agricultural products"`
  swallows 5 other real entries plus the notes tail).

New test file:
`backend/tests/integration/test_us_markers_wave1_inline_quote_fallback.py`
(under the 300-line style gate; 7 tests). Drives the REAL production call
path end-to-end (`ingest_us_statute_rows` -> `run_definition_linking`,
both imported unmodified) -- never a re-implementation of the matching
logic, so any fix landing anywhere behind the seam turns these green with
no test edits, as long as the observable behavior matches.

**Proven RED** (`backend/.venv/bin/pytest
backend/tests/integration/test_us_markers_wave1_inline_quote_fallback.py -v`,
run in this worktree):

```
test_all_six_wave1_fixture_headings_are_recognized_as_definitions_sections PASSED
test_real_pipeline_recovers_all_nine_va_no_marker_definitions_end_to_end FAILED
test_real_pipeline_recovers_both_wa_no_marker_definitions_end_to_end FAILED
test_real_pipeline_recovers_fed_no_marker_definitions_without_leaking_editorial_notes FAILED
test_real_pipeline_never_produces_a_degenerate_near_empty_definition_on_the_va_defect_row FAILED
test_real_pipeline_never_produces_a_phantom_nested_term_on_the_wa_defect_row FAILED
test_real_pipeline_never_swallows_editorial_notes_into_a_fed_definition FAILED
6 failed, 1 passed in 0.23s
```

Sample real failure (the VA clean-rescue test -- today's pipeline creates
zero definitions, full stop):

```
AssertionError: expected all 9 real VA terms, got []
assert set() == {'College deg...tutions', ...}
```

Full backend suite after adding these: `backend/.venv/bin/pytest
backend/tests -q` -> `6 failed, 642 passed, 18 warnings in 12.16s` -- the
641 baseline holds exactly (642 = 641 + 1 new green sanity test), the 6
new RED failures are the only change, zero regressions.

### 5. Boundary proposal with core -- see contract `## Boundary with core sprint`

Full proposal text lives in the contract (size-budgeted); rationale for
each point is the live findings above. Two open questions are relayed to
core rather than assumed: (a) whether `normalize_for_parsing`'s mojibake
table can be broadened independent of C3/C4 timing (wave 4), and (b)
whether SC/AZ residual splitting (wave 3) and DC/AL non-quote-anchored
extraction (waves 5/9) can ship as pure registry additions under C4 without
touching pipeline.py at all, or still need to wait behind C3.

### Escalation check

Nothing in this pass met the STOP-and-return bar: no recon claim failed to
reproduce, no zero-miss-vs-zero-false-positive conflict (the FED
notes-swallow issue is a clean engineering fix, not a tradeoff -- see
above), no boundary disagreement with core exists yet (core has not
published anything to disagree with), and the one out-of-family overlap
(VT, family 3 + family 5) is flagged to the program manager per the brief's
own instruction, not escalated as a panel deadlock.

---

## M2 — manager verification of planner pass 1 (2026-08-04)

I verified the handoff MYSELF rather than accepting the Planner's report.
Three-dot diff materialized to scratchpad (`git diff origin/main...HEAD`),
`--stat` reviewed, and the test file read in full (it is the load-bearing
artifact of this handoff).

**CHECK 1 — role separation held.** `git diff origin/main...HEAD --name-only`
filtered for anything outside `docs/` and `backend/tests/` → **empty**. The
Planner touched no production code. 5 files: contract, log, fixtures README,
one fixture JSON, one test file.

**CHECK 2 — tests are genuinely RED on the live path.**
`backend/.venv/bin/pytest backend/tests/integration/test_us_markers_wave1_inline_quote_fallback.py -q`
→ **`6 failed, 1 passed`**. The single pass is the deliberate sanity test
(headings ARE already recognized — proving the miss is purely extraction, not
detection). The tests drive the REAL production path
(`ingest_us_statute_rows` → `run_definition_linking`, both imported
unmodified), not a re-implementation.

**CHECK 3 — no regressions.** Full suite `backend/.venv/bin/pytest
backend/tests -q` → **`6 failed, 642 passed`**. Baseline was 641 passed; 641
+ 1 new sanity pass = 642, and exactly the 6 new tests are red. Nothing that
was green went red.

**CHECK 4 — no test reads the corpus snapshot.** Grepped `backend/tests/` for
`huggingface`/`datasets--vaquill`/`snapshots/301000` → the only hit is a prose
line in an existing docstring, no path read. The new tests read only the
vendored `us_markers_wave1_rows.json`.

**CHECK 5 — fixtures are VERBATIM real corpus rows (independently proven).** I
loaded the real parquet files myself and compared field-by-field. All 6 rows
located; `section_title` and `text` byte-identical to the fixture for every
one:

| act_id | title verbatim | text verbatim | chars |
|---|---|---|---|
| `STATE_VA_T23.1_SI_C3_S23.1-300` | True | True | 2,472 |
| `STATE_VA_T4.1_SII_C6_S4.1-600` | True | True | 14,629 |
| `STATE_WA_T47_C14_S020` | True | True | 332 |
| `STATE_WA_T9A_C04_S110` | True | True | 7,318 |
| `USC_T16_C65_S4503d` | True | True | 1,025 |
| `USC_T15_C12_S431` | True | True | 3,239 |

**CHECK 6 — the Planner's headline NEW finding reproduces under MY OWN run.**
This is the finding that justifies the tests' extra strictness, so I did not
take it on report. Running the UNMODIFIED `_extract_inline_quoted_definitions`
(i.e. simulating a naive "just flip the `used_body_derived_heading` gate" fix)
against the real fixture bodies:

| row | current extractor | naive fallback | defect I observed |
|---|---|---|---|
| `USC_T15_C12_S431` | 0 | 1 | `agricultural products` = **3,169 chars, contains "Editorial Notes"** |
| `USC_T16_C65_S4503d` | 0 | 3 | `State` = 626 chars, **contains "Editorial Notes"** |
| `STATE_VA_T4.1_SII_C6_S4.1-600` | 0 | 48 | `sell` = **1 char (degenerate)** |
| `STATE_WA_T9A_C04_S110` | 0 | 19 | `Vehicle` = **1 char**, plus phantom top-level term `motor vehicle` |

Confirmed: the recon dossier's "77-93% rescuable" counts only WHETHER
candidates come back, never their QUALITY. A naive gate flip would ship real
garbage into the corpus. The Planner caught this independently and encoded it
as assertions that FAIL against the naive fix — exactly what ruling U-R1
demands. **Verdict: planner pass 1 ACCEPTED.**

**Manager arbitration on the Planner's boundary proposal (d).** I do NOT
forward the Planner's division of labour unchanged. The Planner proposes the
CORE Developer wire the gate replacement AND carry wave 1's boundary fixes in
the same change. I disagree: that puts family-3 BEHAVIOUR change inside the
core sprint, where neither the RED tests nor the family expertise live, and
leaves my QA verifying another panel's implementation. My lean is recorded in
the escalation to the program manager (see §M3).

---

## P2 -- planner pass 2 (2026-08-04)

Sonnet/high. Read in mandated order: this contract, this log's `## P1`/`## M2`,
program doc, prior sprint's known-limitations, fixtures README, pass 1's own
test files. CodeGraph used first (`codegraph explore` over the
definition_links directory, extract.py/us_profile.py symbols) before Reading
any file directly. Polled `origin/claude/defs-core-scope`: **the seam spec is
now published** (`## Seam spec (published)`, `EntrySplitterRule`/
`TermClauseRule`/`ScopeTriggerRule` registry kinds, profile-overridable
`normalize_for_parsing`) -- noted in the contract's boundary section; full
re-reconciliation deferred (out of this pass's assigned priorities).
Worktree confirmed clean at `2e8a8d5`; baseline re-verified
`backend/.venv/bin/pytest backend/tests -q` -> `6 failed, 642 passed` before
any new test was written, matching the manager's M2 figure exactly.

### Priority 1 -- correctly-empty classifier RED tests (gate U4, ruling U-R3)

New file: `backend/tests/unit/test_definition_links_correctly_empty.py` (15
tests). Defines the required contract for a NOT-YET-IMPLEMENTED module:

```python
# backend/app/definition_links/correctly_empty.py
from dataclasses import dataclass
from typing import Literal

CorrectlyEmptyReason = Literal["terminal_status", "cross_reference"]

@dataclass(frozen=True)
class CorrectlyEmptyResult:
    is_correctly_empty: bool
    reason: CorrectlyEmptyReason | None  # None iff is_correctly_empty is False

def classify_correctly_empty(body_text: str) -> CorrectlyEmptyResult: ...
```

Pure function of `body_text`; caller is responsible for the two preconditions
(Definitions-recognized heading, zero extracted candidates) -- documented in
the test file's module docstring, not re-checked by the function itself.
Priority order: (1) terminal-status (whole stripped body is exactly
`Repealed.`/`Expired.`/`Reserved.`/`Renumbered.`/`Omitted.`/`Vacant.`/
`Recodified as ...`), (2) cross-reference (see correction below), (3)
otherwise MISS.

To avoid a missing-module collection error aborting the WHOLE suite's
collection (verified: a top-level `from app.definition_links.correctly_empty
import ...` produces `!!!! Interrupted: 1 error during collection !!!!` and
runs ZERO tests, backend-wide -- unacceptable, it would hide the 642-passed
baseline), the import is deferred inside a `_classify` helper so each test
fails individually AT RUN TIME with a clear `ModuleNotFoundError`, and
collection of every other file proceeds normally. Verified:
`pytest backend/tests -q` -> `21 failed, 642 passed` at this point (6 wave-1 +
15 new), no collection abort, no regressions.

**Real vendored rows** (new fixture `us_markers_correctly_empty_rows.json`,
10 rows, byte-verified against the source parquet this pass -- all `True`):
terminal-status class from DC (`Repealed.`/`Expired.`/`Recodified as
...`/`Reserved.`, the last one caveated -- see fixture README, no row in the
full 53-state corpus combines a `Reserved.` body with a Definitions-
recognized heading, verified exhaustively); genuine cross-reference class
from WI/WY/WA (one each, all short single-sentence other-citations).

**A material, corpus-proven correction to my OWN pass-1 classifier
design**, found by testing it against the FULL real corpus rather than
pass 1's WI/WY spot-checks: pass 1's cross-reference rule ("matched at the
START of the stripped body") is dangerously over-broad. Reproducing it
against real WA/VA data:

- **727 of WA's 734 naive-rule hits (99.0%) are SELF-referential**
  ("The definitions set forth in this section apply throughout this
  chapter.") immediately followed by real defining content -- including
  `STATE_WA_T47_C14_S020`, **wave 1's own flagship WA test row** (2 real
  captured terms). The naive rule would have called this "correctly empty"
  and silently erased a proven miss -- precisely the failure mode ruling
  U-R3 exists to prevent.
- Two real VA rows independently prove the same failure: `STATE_VA_T29.
  1_C7_A2.1_S29.1-733.2` (9,658 chars, **46 real quoted definitions**, opens
  "The definitions in this section do not apply to...") and `STATE_VA_
  T58.1_SI_C17_A9_S58.1-1735` (3,726 chars, **7 real quoted definitions**,
  opens "The definitions in § 46.2-1408 shall apply..." -- names a REAL
  other citation, same surface shape as a genuine cross-reference, but with
  substantial content of its own following it).
- **Corrected rule**: requires the ENTIRE stripped body (after removing an
  optional trailing `History: ...` amendment-citation annotation -- WI's
  real convention) to be nothing but the cross-reference sentence, not
  merely to start with one. Verified against all known evidence (script,
  scratchpad, not committed): WI x2, WY, WA-genuine all still classify
  correctly-empty; the WA flagship row and both VA rows now correctly
  classify as MISS.
- **Recomputed full-corpus rate** (corrected rule, run against real
  `is_definitions_heading`/`extract_definitions_from_section`, this pass):
  **WA 4/1,778 (0.2%)**, not pass 1's reported 734/1,778 (41.3%); **VA
  0/1,065 (0.0%)**, not 2/1,065 (0.2%). DC (0/332), WI (2/62, 3.2%), WY
  (19/56, 33.9%) are unchanged -- the fix only matters for jurisdictions
  whose dominant idiom is a self-referential "definitions apply to this
  section" preamble immediately followed by real content (VA/WA), not for
  states whose genuine cross-references are short standalone sentences.

This is not a P-R2 escalation (zero-miss vs. zero-false-positive): the fix
serves BOTH simultaneously, same as wave 1's FED editorial-notes fix -- an
engineering correction to an under-specified rule, not a value tradeoff.

Three negative tests directly encode rows 8-10 above (the two VA rows plus
the WA flagship row) as the "critical guard" the brief asked for; a fourth
parametrized test reuses wave 1's own 5 remaining fixture rows (VA/WA/FED
defect + clean rows) as further negative evidence, no new vendoring needed.

### Priority 2 -- auto-rescue sub-case RED tests (UT/TX/AZ)

New file: `backend/tests/integration/test_us_markers_wave1_auto_rescue_
subcases.py` (4 tests: 1 sanity + UT/TX/AZ). Live-path (`ingest_us_statute_
rows` -> `run_definition_linking`, unmodified), same discipline as wave 1.
`pytest ... -q` -> `3 failed, 1 passed` (today's real pipeline returns 0 for
all three, same gate as VA/WA/FED).

Reproducing pass 1's claim by calling the CURRENT, unmodified
`_extract_inline_quoted_definitions` directly (same live-path method the
manager used to verify pass 1's VA/WA/FED findings) found the claim needed
CORRECTION for two of the three rows, not rejection:

- **TX** (`STATE_TX_Cfi_C37_S37.001`): confirmed genuinely clean, as
  claimed. 1 term ("emergency"), 738 chars, the whole body IS this one
  definition (same shape as pass 1's own PA row).
- **UT** (`STATE_UT_T75B_S75B_1_301`): NEW defect found this pass.
  "Insolvent"'s captured definition_text swallows the two FOLLOWING entries
  ("Paid and delivered", "Personal property") whole (599 chars, ends
  mid-marker "...(7)") because their idiom ("does not include"/"includes")
  isn't "means"/"shall mean"/"has the meaning", so `_MEANS_IDIOM_GAP_RE`
  never recognizes them as a boundary. Same defect CLASS as VA's "sell"
  collapse / FED's editorial-notes swallow (pass 1's own log) -- missed for
  UT specifically because pass 1 measured only candidate existence on this
  row, not boundary quality. Test asserts the 5 real "means"-idiom terms
  with `"Insolvent"` capped under 260 chars and neither forbidden term
  string present.
- **AZ** (`STATE_AZ_T15_C14_A7_S1871`): NEW defect found this pass, same
  class as SC's already-named `"(2)"` leak (contract wave 3): "Qualified
  higher education expenses"'s captured definition_text ends
  `"...internal revenue code.\n\n13."` -- it swallows the NEXT entry's bare
  digit-dot marker. Test asserts all 17 real terms, none degenerate, and no
  entry ends with a leaked trailing marker (`\d{1,3}\.\s*$`).

Contract's `## Next Steps` updated: item 1 now cites this correction; item 3
(wave 3, SC/AZ) now explicitly covers AZ's marker-leak too, not just its
no-quote minority.

### Priority 3 -- not-yet-rescued sub-case RED tests (AL/DC/RI/AK/TN/SC)

New file: `backend/tests/integration/test_us_markers_not_yet_rescued_
subcases.py` (7 tests: 1 sanity + 6 sub-cases). `pytest ... -q` -> `6 failed,
1 passed` (today's real pipeline returns `[]` for all six -- no existing code
path, main or fallback, can see any of these shapes).

Highest corpus impact first, as directed:

- **AL** (highest value): `STATE_AL_T1_C19_S22-19-141`, unquoted ALL-CAPS
  `(N) TERM. Sentence.` shape, no quotes anywhere. Re-confirmed this pass:
  1,603/1,653 = 97.0% of AL's Definitions-headed sections zero-candidate,
  full corpus (unchanged from pass 1's measurement). Test asserts exact
  terms `ORGAN`/`ATTENDING PHYSICIAN` with exact clean definition text
  (both single-sentence, no boundary ambiguity on this row).
- **DC unquoted-term shape**: `STATE_DC_T28_C25_S28-2501`. Zero quotes; the
  term is the grammatical SUBJECT of its own sentence (`"A bond, ...,
  means ..."`, `"An undertaking means ..."`) -- structurally harder than
  AL's numbered-marker shape. Test asserts terms `bond`/`undertaking` with
  substring + no-cross-swallow checks (not exact string match, given the
  subject-extraction ambiguity is real implementation-design territory).
- **RI/AK mojibake**: corrected this pass -- RI and AK use TWO DIFFERENT
  byte sequences (RI `\x80\x9c`/`\x9d`, AK `\x93`/`\x94`), not one shared
  shape as the contract's prose implied. A fix for one does NOT cover the
  other. AK's full-corpus rate (new measurement, not previously stated):
  **766/767 (99.9%)** zero-candidate -- larger than RI's known 15%. RI test
  (`STATE_RI_T35_C35-13_S35-13-2`) asserts exactly 14 real terms -- NOT 15:
  entry 11 ("Public entity") re-mentions "public entity" (mojibake-quoted
  again) inside its OWN definition prose; a naive quote-scanner that
  doesn't distinguish an entry-opening quote from an in-body re-quote would
  over-count by one, same defect CLASS as wave 1's WA "motor vehicle"
  phantom-nested-term guard. Verified the true count via a marker-anchored
  regex (quote immediately after `"(N) "`), not a bare quote-pair scan. AK
  test (`STATE_AK_T44_C44.42_S44.42.900`) asserts only the 2 unambiguous
  "means"-idiom terms (`commissioner`/`department`) as a subset, not an
  exact set -- entries 3-4 ("transportation"/"transportation mode") share
  one clause via "or" and use the "includes" idiom, needing BOTH wave 4 AND
  wave 2 before capture is even possible, and may overlap
  `defs-us-multiterm`'s territory (same overlap class as pass 1's flagged
  VT row) -- flagged, not claimed.
- **TN colon-then-list**: `STATE_TN_T50_C2_S50-2-115`, re-confirmed NOT
  rescued by wave 1 (idiom mismatch, as pass 1 found). New observation this
  pass: the row's real `text` field itself contains the SAME statutory
  content duplicated (once flowing, once line-broken) -- a genuine,
  non-injected data-quality quirk. Test asserts content presence +
  trailing-citation-annotation exclusion, not an exact length, to avoid
  over-specifying how a future implementation should handle the
  duplication (not this pass's job to resolve).
- **SC bare-`(N)` boundary noise**: `STATE_SC_T5_C1_S5-1-20`, the
  contract's own named row. Confirmed SC IS reachable via the CURRENT
  fallback once wave 1's gate is removed (same mechanism as VA/WA/FED) but
  NOT cleanly -- the contract's own named defect (`"Municipality"` ends
  with a leaked `"(2)"` fragment) PLUS a SECOND, previously-unrecorded
  defect found this pass: `"Publicly-owned property"` swallows a trailing
  "Effect of Amendment" commentary annotation (a FED-editorial-notes-shaped
  hazard). SC therefore stays RED even after wave 1 lands -- wave 3's
  marker-splitter fix is a separate, not-yet-implemented item. Test asserts
  both terms' exact clean text and both forbidden-leak guards.

### Fixtures

Two new files, both byte-verified against the source parquet this pass
(`section_title` and `text`, all 19 new rows, all `True`):
`us_markers_correctly_empty_rows.json` (10 rows) and
`us_markers_wave2_subcases_rows.json` (9 rows). README updated with full
per-row provenance and rationale (not duplicated here). No committed test
reads the corpus snapshot (grepped `huggingface`/`datasets--vaquill`/
`snapshots/301000` across all three new test files -- zero hits).

### Full suite after this pass

```
backend/.venv/bin/pytest backend/tests -q
...
30 failed, 644 passed, 18 warnings in 12.75s
```

644 = 642 (pass-1 baseline) + 2 new sanity-passing tests (one per new
integration file). 30 failed = 6 (wave 1, unchanged) + 15 (priority 1) + 3
(priority 2) + 6 (priority 3). Every new failure is RED against the real
production entry point or (priority 1 only) a clear, deliberately
non-collection-aborting `ModuleNotFoundError` for a not-yet-implemented
module. No regressions: every test green before this pass is still green.

### Contract updates

`## Next Steps` rewritten: items 1/3/4/5/6/10 now note which RED tests
exist and what corrections were found; item 9 (AL) retired, folded into
item 5 (DC). `## Boundary with core sprint` status line updated: the seam
spec is now published (noted, full reconciliation deferred to the next
pass). `total_items` left at 10 (the renumbered/folded list still has 10
entries).

### Escalation check

Nothing in this pass met the STOP-and-return bar. The WA/VA cross-reference
over-match and the UT/AZ boundary defects are engineering corrections that
serve BOTH zero-miss and zero-false-positive at once (same shape as wave 1's
FED finding) -- not P-R2 conflicts. No recon or pass-1 claim was rejected
outright; TX's auto-rescue claim reproduced exactly as stated, UT/AZ's
needed correction but not rejection, and the RI/AK "shared mojibake shape"
wording needed a factual split (two byte sequences) but both remain
real, in-scope, not-yet-implemented misses. No new boundary disagreement
with core (its seam spec, now published, already matches this sprint's own
pass-1 request in the parts I checked this pass -- full line-by-line
reconciliation is deferred, not a disagreement).

**Commit**: local only, not pushed, per the brief. Exact SHA reported to the
manager alongside this pass's summary.

---

## M3 — manager verification of planner pass 2 + boundary RESOLVED (2026-08-04)

### Verification of pass 2 (done by me, not accepted on report)

**CHECK 1 — role separation held.** `git diff origin/main...HEAD --name-only`
outside `docs/` and `backend/tests/` → **empty**. Still zero production code.

**CHECK 2 — suite state.** Full run → **`30 failed, 644 passed`**. 644 = 642
+ 2 new deliberate sanity passes; the 30 red = 6 (wave 1, unchanged) + 24 new.
Nothing previously green went red.

**CHECK 3 — all 19 NEW fixture rows are verbatim real corpus rows.** I loaded
the real parquet files myself and compared `section_title` and `text`
field-by-field for every row in both new fixture files: **19/19 located,
0 mismatches.** (Combined with pass 1: 25/25 vendored rows proven verbatim.)

**CHECK 4 — the classifier self-correction is REAL and it matters.** This is
the most consequential thing in pass 2, so I reproduced it independently
against the full real WA parquet rather than taking the number on report.

- WA Definitions-headed, zero-candidate rows: **1,778** — matches the
  Planner's count exactly.
- A cross-reference rule anchored at the START of the body (pass 1's design)
  classifies **683 of 1,778 (38.4%)** of them as "correctly empty" (the
  Planner, with their slightly broader regex, measured 734 / 41.3%; my
  independent reconstruction used a narrower pattern, hence the small
  delta — same order, same conclusion).
- The CORRECTED rule (the whole body must be nothing but the cross-reference
  sentence) classifies **0** of 1,778 by my reconstruction (Planner: 4).
- Decisive evidence on the flagship row `STATE_WA_T47_C14_S020`: its body
  literally opens `"The definitions set forth in this section apply
  throughout this chapter."` and then goes on to define **2 real terms**
  (`Right-of-way`, `Airspace`) — the very row wave 1's headline test asserts
  we must recover.

**This was the loophole that would have let this sprint claim zero-miss while
silently writing off ~700 real WA misses as "correctly empty."** Ruling U-R3
(classifier is a Planner deliverable, independently verified, never the
Developer's explanation for a residue) is exactly what caught it, and the
Planner caught it on itself. **Verdict: planner pass 2 ACCEPTED**, and the
corrected classifier is now a gating deliverable, not a footnote.

### Manager ruling U-R5 — the core boundary is RESOLVED; no escalation needed

Core published its `## Seam spec (published)` (branch `claude/defs-core-scope`
@ `5610fb1`, plus manager rulings @ `9272f6e`). I read it myself. It changes
the answer to our open boundary question:

1. **We do NOT need to remove the `heading_was_derived` gate, and we do not
   need core's Developer to carry our behaviour change.** The seam keeps that
   gate on the *moved-verbatim* legacy inline extractor (C3 is a
   behaviour-preserving migration). Separately, Seam 2 gives us
   `EntrySplitterRule` + `TermClauseRule` in a new file
   `backend/app/definition_links/rules/us_entry_marker_variants.py`, and the
   consumption contract is **baseline-first, registry-second**: the `(N)`-block
   splitter runs first and returns EMPTY on exactly our family-3 bodies —
   which is precisely when our registered rule fires, *regardless of how the
   heading was found*. That is a complete, legal path to wave 1 with **zero
   shared-module edits** (gate U3 satisfied by construction).
2. This is strictly BETTER than flipping the gate: flipping it would have
   re-used the defective legacy function that my §M2 check proved emits
   3,169-char editorial-notes swallows and 1-char definitions. Registering our
   own boundary-correct rule means we never inherit those defects.
3. Core's manager ruling **M1** moved `EntrySplitterRule` from
   first-match-wins to **union of all matching rules**, so our family-3 rule
   cannot be silently pre-empted by another family's rule — favourable to us
   and to the zero-miss bar.

**Therefore the Planner's pass-1 boundary proposal (d) — that core's Developer
wire the gate replacement and carry wave 1's boundary fixes — is SUPERSEDED
and withdrawn.** Family-3 behaviour change stays in this sprint, where the RED
tests and the family expertise live, which was my §M2 arbitration lean. No
escalation to the program manager is required on the boundary.

### Ruling U-R6 — what this sprint's Developer may do NOW

Core has published DOCS ONLY: `git ls-tree origin/claude/defs-core-scope --
backend/app/definition_links/` shows **no `rules/` directory** — the registry
is spec, not code. Therefore:
- **BLOCKED until core merges to main:** waves 1-7 (every rule module), since
  `rules/registry.py` does not exist to register against.
- **NOT BLOCKED:** `backend/app/definition_links/correctly_empty.py`. It is a
  standalone NEW module with no registry dependency, QA calls it directly for
  gate U4's zero-miss sweep, and it already has 15 RED tests. It is dispatched
  now.

---

## M4 — manager verification of Developer (correctly_empty.py): **BOUNCED**

**CHECK 1 — scope discipline: PASS.** `git diff ea09e23..HEAD --stat` → exactly
one file, `backend/app/definition_links/correctly_empty.py` (+159). Zero files
under `backend/tests/` touched. Zero shared-module edits. Full read of the
module: no fixture `act_id` hardcoding anywhere, pure function of `body_text`,
159 lines (within the 300-line budget), documented with rationale.

**CHECK 2 — suite: PASS.** `15 failed, 659 passed` — exactly the 15 target
tests turned green, the other 15 (blocked waves) unchanged. No regressions.

**CHECK 3 — ADVERSARIAL live-corpus check: FAIL.** The unit tests only exercise
the vendored rows, so I ran the classifier over the FULL real parquet for
WA/VA/FED/DC/WI/WY: every Definitions-headed, zero-candidate section, asking
the question the tests cannot ask — *does any row this classifier calls
"correctly empty" actually contain extractable real definitions?*

| Jur | zero-candidate | called correctly-empty | terminal/xref | **FALSE correctly-empty** |
|---|---|---|---|---|
| WA | 1,778 | 8 | 0/8 | **4** |
| VA | 1,065 | 0 | 0/0 | 0 |
| FED | 1,600 | 0 | 0/0 | 0 |
| DC | 332 | 184 | 184/0 | 0 |
| WI | 62 | 2 | 0/2 | 0 |
| WY | 56 | 19 | 0/19 | 0 |

**4 of WA's 8 cross-reference classifications are wrong — a 50% error rate in
that bucket.** Real examples, each carrying ~20 genuine defined terms:
`STATE_WA_T82_C23A_S010` (`Petroleum product`, `Possession`, `Control`…),
`STATE_WA_T18_C44_S011` (`Committee`, `Department`, `Designated escrow
officer`…), `STATE_WA_T70A_C30_S010`. The terminal-status half is clean
(DC 184/184 correct); the defect is confined to `_CROSS_REFERENCE_RE`.

**Exact mechanism (diagnosed, not guessed).** `_CROSS_REFERENCE_RE`'s citation
group `[^\n]+?` is lazy but unrestricted — it may swallow arbitrary text
INCLUDING sentence-ending periods. `STATE_WA_T82_C23A_S010` opens with the
self-referential preamble `"The definitions in this section apply throughout
this chapter…"` (offset 32) and, 1,800 characters of real definitions later,
happens to CLOSE with a genuine cross-reference sentence: `"…the definitions
in chapters 82.04, 82.08, and 82.12 RCW apply to this chapter."` (second
`apply` at offset 1826). The regex anchors on that SECOND `apply`, the citation
group swallows all the intervening real law, the trailing clause consumes
` to this chapter`, and `fullmatch` succeeds. The "entire body must be nothing
but the cross-reference sentence" intent is therefore defeated by any section
that merely ENDS with such a sentence.

The trailing clause already forbids crossing a sentence boundary; the citation
group does not. That asymmetry is the bug.

**Ruling U-R7 — this bounces to the panel, and the TEST comes first.** The
Developer's work was in-scope and disciplined; the miss is a test-coverage
gap, which is Planner territory. Role separation holds: the **Planner**
authors the RED test (vendoring the real WA rows above), THEN the **Developer**
fixes the regex. The Developer does not write the test; the Planner does not
touch the module.

This is the second time the same failure mode has been caught on this
deliverable (§M3 was the first, in the Planner's own design). It vindicates
ruling U-R3: an unverified "correctly empty" classifier is the single easiest
way to fake a zero-miss result, and unit tests over hand-picked rows cannot
prove its absence — only a full-corpus adversarial sweep can.

---

## P3 -- planner bounce-cycle fix (ruling U-R7) (2026-08-04)

Sonnet/high. Worktree already held the Developer's `correctly_empty.py`
(commit `d266489`) and the manager's bounce verification (`2648be4`) --
same shared worktree, no fetch/rebase needed (local HEAD was already at
`2648be4`). Read `correctly_empty.py` in full (permitted -- I author tests
against it, I do not edit it) to diagnose the exact regex mechanism before
writing anything.

**Root cause, confirmed by reading the shipped regex + the 4 real rows**:
`_CROSS_REFERENCE_RE`'s citation group (`[^\n]+?`) is lazy but otherwise
unbounded, and the trailing-clause group tolerates any non-period
character. All 4 real offending rows have **zero newline characters**
(confirmed: `"\n" not in body` for all four) -- the genuine cross-reference
rows are short single sentences with nothing to swallow, so this never
showed up there. Two distinct exploitable shapes, both present among the 4
real rows (diagnosed independently, not merely copied from the manager's
report):

- **Shape (a)** -- self-referential opening, real content, and a SECOND
  later occurrence of `apply`/`are applicable` closes the match via
  backtracking across the whole (newline-free) line.
  `STATE_WA_T82_C23A_S010`'s second occurrence is a genuine (if
  misapplied) cross-citation sentence; `STATE_WA_T18_C44_S011` and
  `STATE_WA_T70A_C30_S010` are more interesting -- their `text` fields
  each concatenate a SECOND, wholly UNRELATED section's content with no
  separator (a real, non-injected vaquill data-artifact: escrow-licensing
  text runs straight into health-care "Insurance producer" licensing text;
  shellfish-sanitation text runs straight into vehicle-emissions text) --
  the regex latches onto that unrelated block's own trailing
  "...are applicable to..."/"...do not apply with respect to..." (the
  latter NEGATED, same shape as pass 2's own VA finding), proving the
  defect doesn't even need a genuinely relevant second citation.
- **Shape (b)** -- `STATE_WA_T70_C28_S008`: only ONE trigger occurrence
  (the self-referential opening). Its 2 real entries are SEMICOLON-
  separated with no internal periods, so the trailing-clause group's
  `[^.\n]` branch swallows everything up to the body's own final period
  without ever needing a second trigger. A fix that only checks "does the
  trigger phrase occur twice" would close shape (a) but not shape (b).

**Fixture**: appended the 4 real WA rows to the existing
`us_markers_correctly_empty_rows.json` (10 -> 14 rows), byte-verified
against `us_wa_statutes.parquet` this pass (`section_title`/`text`, all
4, all `True`). Manager's addendum row (`STATE_WA_T70_C28_S008`) included.
README updated with full per-row rationale (rows 11-14 section).

**Tests authored**, appended to
`backend/tests/unit/test_definition_links_correctly_empty.py` (my own
file from pass 2 -- extended, not replaced):

1. `test_real_wa_false_positive_rows_are_not_correctly_empty` --
   parametrized over the 4 real rows, each asserting `is_correctly_empty
   is False` plus a sanity floor on real `"Term" means` occurrences and a
   sanity check that the body genuinely has zero newlines (pins the
   mechanism, not just the symptom).
2. `test_general_guard_real_content_before_any_genuine_cross_reference_suffix_is_never_correctly_empty`
   -- the GENERAL guard the brief asked for, not just 3 more row-specific
   cases. Recombines, at test-run time, each offending row's real leading
   content (self-referential opening + real definitions, its own
   accidental trailing content sliced off via a documented cut marker)
   with a DIFFERENT already-vendored row's real, independently-verified
   genuine cross-reference sentence (WI/WY/WA-genuine, rows 5-7). All 4
   cross-combinations were confirmed (before writing the assertion) to
   ALSO reproduce the same false positive against the shipped module --
   this is live evidence the defect is general (any real content + any
   genuine trailing cross-reference sentence, not memorized byte-strings),
   not a hypothetical. A fix tuned only to the 4 named rows above (e.g. a
   lookup table, or "reject if the trigger phrase repeats") would still
   fail this test.
3. `test_genuine_cross_reference_class_is_not_disabled_by_the_fix` --
   restates the 3 existing genuine-positive assertions (WI/WY/WA-genuine)
   as an explicit anti-overcorrection guard, per the addendum's explicit
   instruction not to let the fix collapse the `cross_reference` class to
   never firing (which would make gate U4 unfalsifiable in the other
   direction). Not new evidence -- a regression guard placed next to the
   defect it must not overcorrect.

**Proven RED against the current (buggy) module**:

```
backend/.venv/bin/pytest backend/tests/unit/test_definition_links_correctly_empty.py -v
...
5 failed, 16 passed
```

5 failed = the 4 named-row tests + the general guard test (all 4
recombinations inside it). 16 passed = the original 15 (all green since
the Developer's fix landed) + the new anti-overcorrection regression
guard (currently passing, as it should -- nothing to fix there yet).

**Full suite**:

```
backend/.venv/bin/pytest backend/tests -q
...
20 failed, 660 passed, 18 warnings in 12.27s
```

660 = 659 (manager's post-fix baseline) + 1 new passing test
(anti-overcorrection guard). 20 failed = 15 (unchanged: 6 wave-1 + 3
auto-rescue + 6 not-yet-rescued, all still awaiting their own
implementations) + 5 new bounce-cycle RED. No regressions -- every test
green before this pass is still green.

**Corpus scale, recorded per the manager's explicit request**: 34,241
Definitions-headed zero-candidate sections corpus-wide (all 53
jurisdiction files), of which only 228 (0.67%) are currently provable
correctly-empty by the shipped classifier -- the real size of what this
sprint's remaining waves (2 through 7, 9 folded into 5) must still
capture, far larger than recon's original 7-jurisdiction sample implied.

**Role separation**: `correctly_empty.py` not touched (diffed --
zero production-code files in this pass's changes, only the fixture and
the one test file). No test reads the corpus snapshot (grepped, zero
hits).

**Commit**: local only, not pushed, per U-R7 role separation. SHA reported
to the manager alongside this pass's reply.

---

## M5 — bounce cycle closed; Developer fix VERIFIED (2026-08-04)

**Planner (b3ec520) — ACCEPTED.** Tests/docs only, zero production files. Added
5 RED tests: the 4 real offending WA rows plus a GENERAL guard
(`test_general_guard_real_content_before_any_genuine_cross_reference_suffix_
is_never_correctly_empty`) so a future regex tweak cannot re-open the hole
row-by-row. All 14 `correctly_empty` fixture rows re-verified byte-identical
to the real parquet by me. Suite moved 15→20 failed, 659→660 passed: exactly
+5 RED, nothing else disturbed.

**Developer (8daee65) — ACCEPTED, and it went deeper than my diagnosis.** One
production file, zero test files. Suite: **`15 failed, 665 passed`** — exactly
the target (5 new tests green, original 15 classifier tests still green, the 15
blocked-wave failures untouched).

The Developer found a SECOND shape my diagnosis had missed, which is why my
proposed sentence-boundary fix would have been insufficient:
- **(a)** my diagnosed shape — a later `apply` on the same line lets the lazy
  citation group swallow the real middle (`STATE_WA_T82_C23A_S010`,
  `STATE_WA_T18_C44_S011`, `STATE_WA_T70A_C30_S010`).
- **(b)** `STATE_WA_T70_C28_S008` — only ONE trigger occurrence, and its real
  entries are separated by `;`/`:` rather than `.`, so a period-based sentence
  boundary never fires at all. Bounding to a line or a sentence does not fix
  this row.

Their fix instead uses a stronger corpus-wide invariant: a genuine citation or
scope clause never contains a literal `"`, while every real definition entry
does — so quote characters are barred from the citation and trailing spans.

**MY adversarial re-verification (the decisive check — not their claim).**
Re-ran the full sweep over all 53 jurisdiction parquet files, and added a NEW
probe for the risk their invariant creates: an UNQUOTED definition body (the
DC `A bond… means…` shape) has no quote characters, so a quote-based invariant
could in principle wave it through.

| metric | before fix | after fix |
|---|---|---|
| Definitions-headed zero-candidate sections | 34,241 | 34,241 |
| called correctly-empty | 228 | **224** |
| **[A] FALSE correctly-empty** (quoted real terms extractable) | **4** | **0** |
| **[B] SUSPECT** (cross-ref verdict + means-idiom + >300 chars, i.e. possible unquoted-definition false-empty) | — | **0** |

Only the 4 bad verdicts were removed; the 224 genuine ones survive (DC 184,
WY 19, MN 6, UT 5, WA 4, TX 2, WI 2, AL 1, NC 1). **No over-correction — the
cross_reference class did not collapse**, which was the failure mode I warned
both roles against. **Bounce cycle CLOSED.**

## Honest state of gate U4 (for the program manager)

The classifier is now trustworthy, and it tells us the real size of the
problem: **34,241 Definitions-headed sections corpus-wide extract zero
candidates, and only 224 (0.65%) are provably correctly-empty.** The
remaining ~34,017 are real misses. That is the true scale of this sprint's
zero-miss bar — far larger than the recon dossier's 7-jurisdiction detail
implied, and it is now measured rather than estimated.

## Context Dump

Sprint blocked on the core sprint, not on this panel.
1. Branch `claude/defs-us-markers`; own worktree + venv; baseline was 641.
2. Delivered: 30 live-path RED tests (wave 1 VA/WA/FED, auto-rescue UT/TX/AZ,
   not-yet-rescued AL/DC/RI/AK/TN/SC, gate-U4 classifier) + the shipped
   `correctly_empty.py`. Suite now `15 failed, 665 passed`.
3. The 15 remaining RED are ALL blocked: they need `rules/registry.py`, which
   core has published as SPEC ONLY (no `rules/` dir on `claude/defs-core-scope`).
4. Boundary with core is RESOLVED (U-R5): wave 1 ships as an
   `EntrySplitterRule`+`TermClauseRule` in a NEW file
   `rules/us_entry_marker_variants.py` under baseline-first/registry-second
   consumption. No shared-module edit, no gate removal, no escalation needed.
5. On re-spawn: wait for core to merge to main, rebase, then Developer
   implements the rule modules against the real registry, then QA.
6. QA has NOT run on this sprint yet — that is the main outstanding role.
7. All 25+14 vendored fixture rows verified byte-identical to the real parquet.

---

## M6 — REBASED onto core; sprint unblocked (2026-08-04)

Program manager relayed that core is on main. Rebased
`claude/defs-us-markers` onto `origin/main` (now `0d57228`).

**Rebase was NOT clean — one conflict, resolved.**
`backend/tests/fixtures/us_statutes/README.md`: core appended their own
fixture sections (`ny_m14_newline_defect_row.json`,
`d_cf_structural_reference_rows.json`, the AK cp1252 row) while this sprint
appended three of its own. Both sides were purely additive documentation, so I
kept BOTH — no content dropped from either side. All 10 of this sprint's
commits replayed; branch head is now `1e14d15`.

**Post-rebase verification (mine):**
- Venv refreshed (`pip install -e '.[dev]'`).
- `backend/app/definition_links/rules/` now EXISTS on our tree
  (`registry.py`, `__init__.py`, `il_scope_triggers.py`,
  `us_scope_trigger_proof.py`) — the registry is real code, not spec.
- Suite: **`15 failed, 724 passed`** (was 665 passed pre-rebase; core added
  ~59 tests, all green). Our 15 RED are unchanged and still fail for the
  right reason: no family-3 rules are registered yet, not a rebase breakage.

**Shipped registry rule kinds (read from `rules/registry.py`, the source of
truth, not the doc):** `HeadingRule`, `BodyPreambleRule`, `EntrySplitterRule`,
`TermClauseRule`, `ScopeTriggerRule`, `StructuralUnitRule`, `CitationRule`.
Note `ScopeTriggerRule.extract` now takes `(article_body, RuleContext)` — v2.5
changed it from the two-positional-args shape I planned against in v2.

### Ruling U-R8 — mojibake normalization has NO registry seam; use rule-internal repair first

Core's `us_profile.py:770-786` explicitly leaves cp1252 mojibake "for a
jurisdiction-specific `normalize_for_parsing` override … exactly the dispatch
seam I9 exists to make reachable." But I checked `rules/registry.py`: **there
is no normalization rule kind.** `USProfile.normalize_for_parsing` is a single
method shared by every US code, so a genuine "jurisdiction-specific override"
would require editing a shared module — which gate U3 forbids.

Options: (a) ask core to add a `NormalizationRule` kind (seam change →
escalation); (b) edit `us_profile.normalize_for_parsing` (U3 violation);
(c) repair mojibake INSIDE our own `EntrySplitterRule`/`TermClauseRule`, which
receive the section body and can repair it before splitting — no shared-module
edit, no seam change, available today.

**Ruling: take (c) first.** Its one known weakness is that repair would not
reach Stage 3 term-matching (`find_term_uses` against article bodies that
still carry mojibake), so an extracted term might fail to match its own
mentions. That is a REAL risk and it is testable: the Planner must author a
live-path test asserting a mojibake-body definition also LINKS to a mention.
**If that test cannot be made green under (c), escalate to the program manager
for (a)** — do not quietly ship extraction-without-linking and call it
captured.

### Corpus facts from the program manager — to be VERIFIED, not assumed

Relayed as verified by core's managers; per this sprint's own standard they
are re-confirmed live by the Planner before any rule is written against them:
1. **AK mojibake is raw cp1252 control bytes U+0093/U+0094/U+0097** (~32K
   occurrences / 17,935 rows), NOT `â€`-style sequences (only 2 rows
   corpus-wide, both KY). A rule written against `â€` matches nothing.
   **This contradicts the recon dossier**, which described AK/RI as
   `\x80\x9c`/`\x9d`. Our own pass-2 finding (RI and AK use two DIFFERENT
   byte sequences) already pointed this way; now it must be pinned exactly.
2. **NY's literal-`\n` blackout is FIXED at ingest (core I8)** — NY was 1,479
   of our 34,241 zero-yield population, so **every U6 baseline in this
   sprint's log is now stale** and must be re-measured post-rebase.
3. **Unbounded-last-entry contamination reproduces corpus-wide** (FED 86% of
   last entries, DC 91.7%, NY 79.8%; FL 540.11 ~100% claimed vs ~12% true) —
   squarely this sprint's U1 boundary-precision mandate, and much larger than
   the prior sprint's residual implied.
4. **NC and AL use unquoted-term conventions** (NC `TermName.--definition`,
   AL `ALLCAPS TERM. definition`) invisible to quote-anchored extractors —
   added to the sub-case inventory alongside DC's.

VT `S3700` boundary stands as agreed: splitting mechanics ours, per-term
fan-out multiterm's; a parent-redirect clause and its lettered children stay
in ONE block (their M-R8 corollary).

---

## M7 — P-R8 verified; ruling U-R5 SUPERSEDED; sprint PARKED (2026-08-04)

### P-R8 confirmed by my own inspection (not accepted on relay)

The program manager reported that 5 of 7 registry rule kinds are dead on the
live path. I verified it directly against the merged tree:

- **Accessors DEFINED** in `rules/registry.py`: `heading_rules_for`,
  `body_preamble_rules_for`, `entry_splitter_rules_for`,
  `term_clause_rules_for`, `scope_trigger_rules_for`,
  `structural_unit_rules_for`, `citation_rules_for` — all 7.
- **Accessors CALLED anywhere in production**: only `citation_rules_for` and
  `scope_trigger_rules_for` (in `profiles.py` and `us_profile.py`).
- **Therefore DEAD: `heading`, `body_preamble`, `entry_splitter`,
  `term_clause`, `structural_unit`** — 5 of 7, exactly as P-R8 states, and the
  two this sprint depends on most (`entry_splitter`, `term_clause`) are among
  them. `extract_definitions_from_section` never consults the registry.

**Developer spawn for rule modules is HELD.** Any rule module written today
would be inert — it would register successfully and never be called, and a
test that only asserted "the rule is registered" would pass while capturing
nothing.

### Ruling U-R5 is SUPERSEDED — and I record why I got it wrong

In §M3 I ruled the core boundary "RESOLVED", reasoning that wave 1 could ship
as an `EntrySplitterRule` consumed baseline-first. That reasoning was sound
against core's PUBLISHED SPEC and wrong against the SHIPPED CODE: the spec
described a consumption contract the implementation never wired. I verified
the document, not the live path.

That is precisely this repo's recorded lesson — *a named wiring test is not a
live-path test* — and I repeated it at the manager level. The corrective
standard for this sprint going forward: **before any rule module is written,
a test must prove the registry kind we depend on is actually REACHED by
`extract_definitions_from_section` on a real row.** Core's reopened
dispatch-completion sprint is expected to deliver exactly that; we verify it
ourselves on merge rather than assuming it.

### U6 baselines re-measured post-rebase — plus a methodology correction

My first re-measurement read the parquet directly and reported the population
UNCHANGED at 34,241 / 224 correctly-empty. That was a **methodology error on
my part**: core's NY fix (I8) lives at the INGEST layer
(`ingest_us_statutes.py:237`, `text.replace("\\n", "\n")`), so reading parquet
directly bypasses it. Re-measured on the post-ingest path for NY:

| NY Definitions-headed sections | zero-yield | rate |
|---|---|---|
| reading parquet raw (wrong path) | 1,479 | 100.0% |
| after the ingest `\n` repair (real path) | **1,262** | **85.3%** |

So the fix recovers **217 NY sections (14.7%)** — real, but far from solving
NY. Corrected corpus figures: zero-yield **34,024** (was 34,241), provably
correctly-empty **224**, **real remaining misses ≈ 33,800**.

Post-rebase per-jurisdiction zero-yield rates (measured by me, all 53 files):
AK 766/767 (99.9%), RI 555/555 (100%), UT 1,667/1,709 (97.5%), AL 1,603/1,653
(97.0%), VA 1,065/1,096 (97.2%), WA 1,778/1,800 (98.8%), FED 1,600/1,920
(83.3%), NC 522/1,007 (51.8%), DC 332/1,216 (27.3%), NY 1,262/1,479 (85.3%).
**NC at 51.8% confirms the program manager's fact 4 is worth its own sub-case.**

### Planner pass 3 — INCOMPLETE (API failure), partial work salvaged

The Planner was terminated mid-pass by an API error, before writing its `## P3`
log entry, so its measurements are lost. Its uncommitted artifacts run and are
genuinely RED, so I have committed them rather than discard them:
`test_us_markers_unbounded_last_entry.py` (incl. the FL `540.11` case),
`test_us_markers_nc_unquoted_term.py`,
`test_us_markers_mojibake_definition_links_to_mention.py` (the U-R8 linking
probe), plus 2 fixture files. **These are UNVERIFIED by me** — I have not
byte-checked their vendored rows against the parquet, unlike the 39 rows
before them. A future pass must do that before relying on them.

## Context Dump

1. Branch `claude/defs-us-markers` @ pushed head; rebased on main `0d57228`;
   own worktree + venv. Suite `19 failed, 724 passed` after salvage.
2. **BLOCKED on core's reopened dispatch-completion sprint** (P-R8): the
   `entry_splitter` + `term_clause` registry kinds this sprint needs are
   defined but never called by `extract_definitions_from_section`.
3. Shipped production code (on OUR branch, unmerged): `correctly_empty.py`,
   gate-U4's classifier — verified corpus-wide by me (false correctly-empty
   4→0, genuine verdicts preserved 228→224).
4. ~34 RED live-path tests covering wave 1 (VA/WA/FED), auto-rescue
   (UT/TX/AZ), not-yet-rescued (AL/DC/RI/AK/TN/SC), NC, unbounded-last-entry,
   and the mojibake-linking probe.
5. Honest miss population: **~33,800 real remaining misses** corpus-wide.
6. U-R8 stands: mojibake has no registry seam; repair inside our own rules and
   escalate if the linking test cannot go green.
7. QA has NEVER run on this sprint — the main outstanding role.
8. On wake: verify core's dispatch is live on a REAL row (do not trust the
   spec — see U-R5's failure above), re-verify the 3 salvaged test files'
   fixtures byte-for-byte, then Developer, then QA.

---

## M8 — dispatch VERIFIED LIVE; Developer building (2026-08-04)

Rebased onto `origin/main` @ `fbb6c9e` (dispatch sprint merged); all 13 sprint
commits replayed clean, no conflicts; venv refreshed.

**I did NOT trust the spec this time (the U-R5 lesson).** Two checks:
1. Accessors now CALLED in production: `heading_`, `body_preamble_`,
   `entry_splitter_`, `term_clause_`, `scope_trigger_`, `scope_kind_`,
   `structural_unit_`, `citation_rules_for` — all of them. Was 2 of 7.
2. **Live probe on a REAL row**: I registered a spy `EntrySplitterRule` for
   `US-VA` and called `extract_definitions_from_section` on the real
   `STATE_VA_T23.1_SI_C3_S23.1-300` body. **The spy was invoked — dispatch is
   LIVE**, not merely wired in source. Baseline still yields 0 on that row, so
   our RED tests remain behaviorally correct.

**P-R8 closed. Ruling U-R6 (all waves blocked) is LIFTED.** Developer
dispatched to build the family-3 rule modules.

Routing accepted from the program manager: `STATE_NY_ARPP_A8_S280-D` (NY
unquoted lettered-paragraph, `"(a) Reverse mortgage loan. A reverse mortgage
loan as defined…"`) joins our unquoted-term family with DC/NC/AL. Binding
caveat carried into the Developer brief: **`scope_unit_kind` declarations come
from each state's OWN measured convention, never the illustrative table**
(M-D3 erratum, seam v2.7).

---

## M9 — Developer build VERIFIED and ACCEPTED (2026-08-04)

**CHECK 1 — scope discipline: PASS.** `git diff b30e4f8..HEAD --name-only`
outside `rules/` and `docs/` → **empty**. Six NEW rule modules only
(`us_markers_boundary.py` 239, `us_markers_unquoted_terms.py` 81,
`us_markers_fl_scope_trigger.py` 65, `us_markers_tn_idiom.py` 61,
`us_markers_mojibake.py` 56, `us_markers_inline_quote.py` 39 = 541 lines).
Zero test files, zero shared-module edits, all well under the 300-line budget.
Gate **U3 satisfied by construction**.

**CHECK 2 — suite: `1 failed, 814 passed`** (65.9s; the suite is ~4x slower now
that rules are active — worth watching). The single failure is the FED
last-entry test the Developer flagged honestly as out of reach: the defect is
in `us_profile.py`'s baseline `_split_into_numbered_blocks`, which runs before
any registered rule and wins the dedup race. Correctly NOT fixed by a
shared-module edit.

**CHECK 3 — corpus claims re-measured by ME, independently.** I re-ran the
sweep through the real profile with rules auto-discovered:

| Jur | headed | zero-yield | my rate | Dev claim | >5,000-char | <10-char |
|---|---|---|---|---|---|---|
| VA | 1,096 | 48 | **4.4%** | 4.4% | 0 | 1 |
| WA | 1,800 | 116 | **6.4%** | 6.4% | 3 | 5 |
| AL | 1,653 | 230 | **13.9%** | 13.9% | 0 | 7 |

**Every claimed number reproduces exactly.** This is the first agent report in
this sprint whose corpus figures I could confirm to the decimal without
correction — accepted.

Headline recall movement (Developer-measured, VA/WA/AL independently
confirmed): VA 97.2→4.4, WA 98.8→6.4, FED 83.3→7.3, UT 97.5→2.3, SC 97.8→4.3,
RI 100→7.2, AK 99.9→4.6, AZ 99.0→13.7, AL 97.0→13.9, NC 51.8→14.1,
TX 21.3→3.3, DC 27.3→27.2 (DC barely moved — reported honestly, not
overclaimed).

**Residual boundary damage — NOT zero, recorded honestly under U-R1.** WA still
carries 3 definitions over 5,000 chars; VA/WA/AL carry 1/5/7 under 10 chars.
The Developer caught and fixed three larger swallows pre-ship (TN 153,837-char,
AZ 20,925-char, FED 26,028-char) via a list-introducer exclusion plus a
3,000-char ceiling. The remainder is small but real and belongs to QA's sweep,
not to a claim of "clean".

**Ruling U-R9 — the FL scope-trigger module is out of family.**
`us_markers_fl_scope_trigger.py` implements an ordinary-article
`ScopeTriggerRule`, which is `defs-us-scoped-inline` territory, not family 3.
It was built per my own brief's instruction, is narrowly gated to `US-FL`, and
harms nothing — but I am flagging it to the program manager as a boundary
encroachment for that panel to adopt or veto, rather than letting it merge
silently as ours.

## M10 — three queued items from the program manager: positions recorded

None require action before this build lands; all are accepted into this
sprint's ledger with a position, so the next pass starts informed.

**Q-A — boilerplate-label classification (joint with scoped-inline).** Accepted
as ours. Our share is deciding when a `(N) LABEL.` token is a real entry
boundary versus a generic structural sub-header, plus the blocklist ("in
general", "en general", "generally", "definitions", …). Position: the hazard is
real and matches what we already hit — capturing "in general" as a term would
match nearly everywhere in scope, the same false-positive class as the phantom
`motor vehicle` term we killed in wave 1. **Preferred interface: a shared
helper, not a registry rule** — classification is a predicate, and the
registry's kinds are all producers; a `TermClauseRule` would force scoped-inline
to consume our rule's output rather than our judgment. I will coordinate the
interface with the scoped-inline manager when we plan it. Their load-bearing
zero-gap mutation test stays untouched.

**Q-B — multiterm's two registered EntrySplitterRules.** Noted, and I accept
the ruling that they stay registered. Design-time authority is ours, and the
flagged risk is real: `entry_splitter` contributions are additive and their TX
splitter **re-contributes the whole section text**, which is exactly the shape
that produced our worst swallows. Our TX/VT splitters will be designed after
reading their two modules and contract. **The TX `2009.003` residual (4
pre-existing degenerate 1-term rows causing double `USES_DEFINITION`
assertions) is ours by M-R5 and folds into our entry-boundary work**, which is
the same defect class as the <10-char residuals in CHECK 3 above.

**Q-C — `STATE_WA_T50_C29_S030` (headings panel, H-R1).** Accepted into our
zero-yield mandate alongside the NY unquoted-paragraph row. Acceptance
condition understood: extraction must yield at least the term the
heading/citation pair implies so their pointer-row edge can attach. **Not yet
confirmed fixed** — my sweep did not surface this row through the
heading-recognized path, so its status is genuinely unknown and it needs an
explicit named-row RED test from the Planner next pass. I will coordinate the
expected term with their manager if it is ambiguous.

---

## M11 — NE accepted into the unquoted family; the 267 CANNOT yet be re-derived

Treated the preamble panel's numbers as claims to re-derive, per instruction.

**The 267 is NOT re-derivable in this tree, and here is the proof:**
- NE rows in the corpus: **25,997**. Rows heading-recognized as Definitions by
  MY tree: **0**.
- Rows whose `section_title` even CONTAINS the substring `efinition`: **0**.

So NE's recognition depends entirely on the preamble panel's own
`BodyPreambleRule`, which lives on THEIR branch and is not merged here. Their
274/267 split may well be right; I simply cannot confirm or refute it until
that rule lands. **Recorded as unverified. It must be re-derived after their
merge, before any NE rule is written against it.**

**What I COULD verify — recognition-independent, and it corroborates the
family assignment.** Scanning all 25,997 NE rows for a `mean` idiom regardless
of heading: **4,068 have NO quote character at all vs 351 that do — 92.1%
unquoted dominance.** That is the strongest unquoted signal of any state in
our family (AL, NC, DC), so **NE is accepted as a member on evidence I derived
myself**, even though its worklist size is still someone else's claim.

**`STATE_WA_T50_C29_S030` — status resolved.** The row IS present in
`us_wa_statutes.parquet`; it did not surface in my M9 sweep because it is not
heading-recognized either. So it is a recognition-side miss reaching us as an
extraction request. The promised named-row RED test stays on the Planner's
list, and the test must NOT assume the heading path — it should drive
extraction directly, the way core's NY newline test does.

**D-CERT (director) — accepted, and it changes our QA priorities.** Program
close is by inverted certification over a signal-agnostic denominator, so
everything we leave dirty surfaces there. Our named residuals are exactly that
population and QA disposes of them FIRST, not last:
- WA's 3 remaining >5,000-char definitions;
- VA/WA/AL's 1/5/7 remaining <10-char definitions;
- TX `2009.003`'s 4 pre-existing degenerate 1-term rows (ours by M-R5);
- the single still-RED FED last-entry test, whose defect is in
  `us_profile.py`'s baseline splitter and needs a shared-module owner.

A signal-agnostic denominator also means NE's 25,997 rows enter the count
whether or not anyone recognizes their headings — which makes the unresolved
NE recognition dependency a certification risk, not just a planning detail.

---

## M12 — bucket A re-measured on MY branch: the number is BIGGER, and NV is much smaller

Probe-sanity run as instructed, corpus-wide (53 files) through the real
profile with my family-3 rules auto-discovered.

| | headings panel (their branch) | MY branch (rules live) |
|---|---|---|
| heading-recognized | (69,009 rows scanned) | **61,075** |
| bucket A (recognized, zero yield) | **12,869** | **21,072** |
| provably correctly-empty | — | 224 |
| **real residual misses** | — | **20,848** |

**The expectation that my build shrinks bucket A is WRONG at corpus level —
it grew.** My rules did exactly what was claimed *inside my own coverage*:

- **in my 13 covered jurisdictions: 1,794** zero-yield remaining
- **NOT covered: 19,278** — 91.4% of the residual

So the two numbers are not measuring the same denominator; theirs cannot be a
strict superset of mine. Either their scan covered fewer jurisdictions or
recognized fewer headings (mine recognizes 61,075 of 69,009). **This needs
reconciling with the headings panel before either number is quoted at
certification** — I am not going to assume mine is the right one.

**NV is NOT ~6,866 — I measure 1,262.** NV: 1,262 heading-recognized,
1,262 zero-yield (**100%**). It is a real, total, unowned gap and a fair
candidate engine jurisdiction, but it is ~5.4x smaller than attributed.

**The real residual is concentrated in TEN uncovered jurisdictions**, none of
them family-3 members today:
NJ 2,372/2,379 (99.7%), NM 1,578 (97.1%), NY 1,479 (100%), NV 1,262 (100%),
OK 1,146 (94.4%), MI 1,116 (38.8%), ND 1,023 (99.7%), MN 1,016 (91.7%),
ME 1,000 (99.9%), OH 949 (99.9%).

**Note NJ, MI, ND, NY and OK are the program's "working baseline"
regression-guard states** — they are recognized and yielding zero at 94-100%.
That is a much bigger claim than "NV needs an engine", and it is the single
most important thing I found this pass. Routing is the program manager's
call; I flag it rather than absorb it silently, since absorbing ~19,278 rows
across ten jurisdictions is a program-scope decision, not a panel one.

**Dispositions accepted:** core-follow-on-2 owns the FED last-entry defect
(G3) — my held RED stays red until it merges, by design. Merge order
core-2 → us → preamble resolves the NE ordering concern.

---

## M13 — phase-2 manager: inherited state RE-VERIFIED with positive AND kill controls (2026-08-05)

Predecessor context-exhausted and clean-exited at `c4baf7ce`; QA deliberately
NOT spawned. Per program law I re-verified every inherited claim I intend to
build on, before spawning anything. Nothing below is quoted from a doc.

**V1 — tree identity.** Worktree clean, `HEAD == origin/claude/defs-us-markers
== c4baf7cebaf849bb89e1371dab32e26c62d514b8`. `git config user.email` =
`256402398+vicciz-ceo@users.noreply.github.com`. Six family-3 rule modules
present in `backend/app/definition_links/rules/`.

**V2 — suite: `1 failed, 814 passed`** (14.5s), re-run by me in this worktree.
The single RED is exactly the expected one:
`test_us_markers_unbounded_last_entry.py::test_real_pipeline_does_not_let_fed_
part_time_career_employment_swallow_the_amendment_history_tail` — the FED
last-entry defect in `us_profile.py`'s baseline splitter, owned BY AGREEMENT by
sprint 2026-08-05-defs-core-follow-on-2 (gate G3). It stays red here until
core-2 merges. `us_profile.py` is not this panel's to touch.

**V3 — zero-yield rates reproduced EXACTLY (positive control).** My own sweep
(`markers-mgr-p2-sweep.py`, P-R9 slug-prefixed), through the real `USProfile`
with `rules/` auto-discovered, over the real parquet corpus:

| Jur | headed | zero-yield | my rate | inherited |
|---|---|---|---|---|
| VA | 1,096 | 48 | **4.4%** | 4.4% |
| WA | 1,800 | 116 | **6.4%** | 6.4% |
| AL | 1,653 | 230 | **13.9%** | 13.9% |

**V4 — KILL CONTROL, the check the inherited numbers had never had.** I re-ran
the identical sweep with the registry blinded to family-3 kinds only
(`entry_splitter_rules_for`/`term_clause_rules_for` → `[]`, everything else
untouched): **VA 97.2%, WA 98.8%, AL 97.0%** — the exact recorded PRE-build
rates. So the probe moves when and only when the rules are removed: the
before→after table is confirmed by me at BOTH ends, and the rules are proven
load-bearing on the live path (not merely registered). This upgrades the M9
claim from "reproduced" to "reproduced with a control that could have failed".

**V5 — the ten-jurisdiction extension numbers RE-DERIVED (all ten exact).**

| Jur | headed | zero-yield | rate |
|---|---|---|---|
| NJ | 2,379 | 2,372 | 99.7% |
| NM | 1,625 | 1,578 | 97.1% |
| NY | 1,479 | 1,479 | 100.0% |
| NV | 1,262 | 1,262 | 100.0% |
| OK | 1,214 | 1,146 | 94.4% |
| MI | 2,879 | 1,116 | 38.8% |
| ND | 1,026 | 1,023 | 99.7% |
| MN | 1,108 | 1,016 | 91.7% |
| ME | 1,001 | 1,000 | 99.9% |
| OH | 950 | 949 | 99.9% |
| **TOTAL** | **14,923** | **12,941** | 86.7% |

**Arithmetic correction carried up to the program manager.** The ten named
jurisdictions sum to **12,941** zero-yield rows, not 19,278. The 19,278 figure
is M12's TOTAL uncovered residual across ALL uncovered jurisdictions; these ten
are 12,941 of it (67.1%), and the remaining ~6,337 sit in the long tail of
other uncovered jurisdictions. Both numbers are right; conflating them
overstates this phase's reachable target by ~49%. Phase-2's honest headline
target is 12,941, with the tail named separately.

---

## QA1 — phase-2 QA cycle 1 (2026-08-05)

Sonnet/high, independent QA, own worktree (`/Users/nerya/LexGraph-wt/
defs-us-markers-qa`, branch `claude/defs-us-markers-qa` off `claude/
defs-us-markers` @ `2a35362`) and own venv (confirmed `.venv/bin/python`
resolves inside this worktree before trusting any measurement).
`git config user.email` verified = `256402398+vicciz-ceo@users.noreply.
github.com` before first commit. Never touched `us_profile.py`, any
shared module, or any `rules/*.py` file — diffed clean throughout (only
`backend/tests/**` files added, listed at the end).

**VERDICT: PASS.** Six real, reproducible defects found and pinned with
RED tests, all correctly attributed to their owning layer (four to shared
`us_profile.py`/`pipeline.py` code this panel cannot touch; two to this
sprint's own `us_markers_boundary.py`, a genuinely new finding). Zero
regressions: suite is `7 failed, 829 passed` = the 1 permitted FED RED
(unchanged, byte-identical failure) + 6 new REDs I added, `814 + 15`
newly-passing diagnostic/regression-guard tests. No RED required forcing —
every RED reproduced on first write against the real, unmodified build.

### STEP 0 — probe sanity (P-R10), before anything else

Reproduced the manager's positive control exactly, with my own copy of
their sweep script (P-R9 slug `markers-qa-p2-sweep.py`): **VA 1,096
headed / 48 zero = 4.4%, WA 1,800/116 = 6.4%, AL 1,653/230 = 13.9%.**
Then the kill control (`registry.entry_splitter_rules_for` monkeypatched
to `[]`): **VA 97.2%, WA 98.8%, AL 97.0%** — the exact pre-build rates.
Both ends confirmed by me independently; my probe is calibrated. Every
number below builds on this.

### Q1 — WA's 3 remaining >5,000-char definitions

**Named**: `STATE_WA_T82_C04_S065` "800 service" (10,838 chars),
`STATE_WA_T43_C88_S020` "Administrative expenses" (6,515 chars),
`STATE_WA_T82_C04_S192` "Digital audio works" (8,769 chars). Exactly 3,
matching the manager's own independent count and worst-case value.

**Classification: all 3 are boundary SWALLOWS**, not genuine long
definitions — each real definition is 105-303 chars (verified with our
own engine below); what gets persisted swallows every sibling entry in
the same section.

**Attribution (per-row, with a kill control that could have failed)**:
all 3 attribute to BASELINE (`us_profile.py`'s `_split_into_numbered_
blocks`), not our family-3 `EntrySplitterRule`. Root mechanism: all 3
bodies pack their ENTIRE run of `(1) "Term" means ... (2) "Term2" means
...` entries onto ONE line with zero internal newlines; baseline's
line-anchored splitter recognizes only the first `(1)` and returns one
degenerate block spanning to end of text. Confirmed with our OWN engine
called directly (`extract_quote_anchored_entries`): produces the CLEAN
303/188/105-char candidates for all 3 terms, 0 entries ≥5,000 chars — the
rule module this sprint owns is not at fault. Kill control (family-3
blinded): baseline alone STILL reproduces the exact swallowed length for
all 3 rows.

**A second, distinct finding, one layer deeper**: even though our own
engine already produces the CLEAN candidate for the same term, the
SWALLOW wins in the real persisted output. Root cause diagnosed in
`pipeline.py` (not `us_markers_boundary.py`): `all_blocks = baseline_
blocks + extra_blocks` puts baseline first, and the idempotent-by-key
persistence loop (`key = (article_id, sorted(terms))`) keeps whichever
candidate is enumerated FIRST on a collision — baseline's bad candidate
wins, our clean one is silently discarded. This is a genuinely NEW defect
class (candidate-collision ordering), distinct from the FED unbounded-
last-entry defect, though it lives in the same shared, not-ours-to-touch
code.

**RED pinned**: `backend/tests/integration/test_us_markers_qa_q1_wa_
newline_collapse_swallow.py`. Node ids: `test_fixture_rows_are_directly_
definitions_headed_not_body_derived` (PASS, sanity), `test_our_own_
family_3_engine_already_produces_the_clean_candidate` (PASS, proves the
engine is clean), `test_kill_control_baseline_alone_already_produces_the_
swallow` (PASS, proves attribution), `test_real_pipeline_does_not_let_
the_baseline_swallow_beat_our_clean_candidate` (**RED** — the load-
bearing pin, on the real `ingest_us_statute_rows`→`run_definition_
linking` path). Fixture: `us_markers_qa_wa_newline_collapse_rows.json`
(3 real rows, byte-verified).

**Manager exchange, mid-pass**: reported this exact per-row attribution
to the manager before they finished measuring it themselves (both
independently landed on "all 3 baseline"); flagged the collision-ordering
finding as separate and possibly NOT automatically fixed by core-2's G3
(depends on whether G3 stops baseline from emitting a bad candidate at
all, or just shrinks it).

### Q2 — the <10-char definitions: VA 1, WA 5, AL 7

All 13 named and inspected against real body context.

- **VA 1/1 genuine**: `STATE_VA_T64.2_SV_C27_A1_S64.2-2700` "Instrument" =
  "a record." — clean, correctly bounded.
- **WA 5/5 genuine**: "Sex" = "gender." (×2, two titles), "Comestible" =
  "edible.", "Cancel or cancellation" = "to void.", "Instrument" =
  "a record." — all real terse statutory definitions, all correctly
  bounded.
- **AL 1/7 genuine, 6/7 DEGENERATE (U-R1 violation)**:
  `STATE_AL_T45_C37A_S45-37A-51.120` "EMPLOYER" = "The city." is genuine.
  The other 6 ("Acquire"/"Bank holding company"/"Out-of-state bank
  holding company" from `5-13B-2`; "Bank supervisory agency"/"Home
  state"/"Interstate merger transaction" from `5-13B-21`) are ALL
  degenerate: real bodies read `(x) "Term" means:` (or just `"Term":`)
  followed by a NESTED `(1)/(2)/(3)` list that IS the definition — what
  persists is only the colon/"means:" fragment, the whole nested list is
  silently dropped.

**Root cause diagnosed**: baseline's `_entry_start_remainder` treats
EVERY bare `"(N)"` at a line start as an unconditional block boundary (by
design, to close non-defining interleaved paragraphs) — but it has no
list-introducer exception the way this sprint's OWN `us_markers_
boundary.py` engine does. It misreads a defining entry's own nested
numbered sub-list as a sibling top-level entry. Not rescuable by any
family-3 rule this sprint owns: AL is only registered for ALL-CAPS
unquoted terms; these 6 rows use quoted, mixed-case terms, a different
shape entirely. Noted, not implemented: `us_markers_boundary`'s existing
list-introducer-aware engine parses these 2 rows correctly when called
directly — would need `US-AL` added to `us_markers_inline_quote.py`'s
jurisdictions to fire live, an ownership question for the manager, not
something this pass implements.

**RED pinned**: `backend/tests/integration/test_us_markers_qa_q2_short_
definitions.py`. Node ids: `test_genuine_short_definitions_stay_
captured_correctly` (PASS, regression guard for the 7 genuine cases),
`test_al_nested_numbered_list_definitions_are_not_truncated_to_the_colon`
(**RED**). Fixture: `us_markers_qa_q2_short_definitions_rows.json` (9
real rows).

### Q3 — TX `2009.003`'s 4 degenerate 1-term rows

Confirmed reproduced exactly on this build: `contested case`→`;`,
`party`→`;`, `person`→`; and`, `rule.`→`''` (empty). Same baseline
entry-boundary mechanism as Q2 (letter/digit markers wrongly treated as
sibling boundaries instead of a shared parent-redirect clause's own
children) — ownership confirmed as markers' by M-R5/M-R8.

**A genuinely NEW finding, not previously named anywhere in this
sprint**: OUR OWN `us_markers_boundary.py` has a real, live truncation
bug on this SAME row. `"Governmental body" has the meaning assigned by
Section 552.003.` — our engine (`extract_quote_anchored_entries`)
captures this as `'assigned by Section'`, silently dropping `' 552.003.'`.
Root cause: `_TRAILING_MARKER_CHAIN_RE` (meant to strip a next-entry's
leaked marker fragment, e.g. a literal `"(2)"` or `"13."`) cannot
distinguish a genuine statutory citation of the shape `"NNN.NNN."` from
two back-to-back digit-dot marker tokens, and strips the whole citation.

**Currently MASKED, not absent, on this exact row**: baseline ALSO
produces a correct "Governmental body" candidate and wins the
`pipeline.py` collision (same mechanism as Q1), so today's real persisted
output for this row happens to be fine — pinned as a passing regression
guard so if the masking ever breaks, this file turns RED immediately
rather than silently.

**Measured corpus-wide how material this is** (all 7 jurisdictions
`us_markers_boundary.py` covers, VA/WA/FED/UT/TX/SC/AZ): of 144,706
quote-anchored entries, **1,842 (1.27%) had a citation-shaped tail
(`\d{1,3}\.\d{1,3}\.`) stripped by `_TRAILING_MARKER_CHAIN_RE`.**
Per-jurisdiction: VA 88/14,577 (0.60%), WA 18/20,788 (0.09%), FED 7/30,728
(0.02%), UT 373/26,392 (1.41%), **TX 1,261/28,009 (4.50%)**, SC 3/10,800
(0.03%), AZ 92/13,412 (0.69%). TX and UT are disproportionately hit.
Sampled VA rows confirm the pattern is real and severe: e.g. `"Servicer"`
loses its statutory citation number the same way. This is a corpus-wide,
material precision defect in shipped family-3 code, not a one-off.

**RED pinned**: `backend/tests/integration/test_us_markers_qa_q3_tx_
2009_003.py`. Node ids: `test_fixture_row_is_directly_definitions_
headed` (PASS), `test_part_a_the_4_baseline_degenerate_terms_still_
reproduce_on_this_build` (PASS, confirms Part A unchanged),
`test_part_a_red_the_4_terms_should_carry_the_real_cross_reference_not_a_
stub` (**RED**), `test_part_b_red_our_own_engine_truncates_governmental_
body_citation_tail` (**RED**), `test_part_b_masking_confirmed_todays_
real_pipeline_happens_to_be_fine_here` (PASS, documents the masking).
Fixture: `us_markers_qa_q3_tx_2009_003_row.json` (1 real row).

### Q4 — the 3,000-char ceiling and list-introducer exclusion, audited

**Measured, corpus-wide across the 7 jurisdictions the ceiling actually
gates** (`markers-qa-q4-ceiling-audit.py`): 144,706 entries kept (≤3,000
chars), **1,308 (0.9%) DROPPED** (>3,000 chars — the code DROPS the whole
candidate, it never truncates to 3,000; confirmed by reading
`us_markers_boundary.py:223`).

**Finding 1 — no spike at the boundary.** Histogram 2,000-2,999 in
100-char bins is a smooth, monotonic decline (196 → 91), then essentially
nothing above (1 entry exactly at 3,000, zero above). The brief's
hypothesis ("a spike is evidence of truncation") is **not confirmed** in
the literal sense — reported honestly rather than rounded to fit.

**Finding 2 — the real defect is a pure MISS, and manual inspection of a
15-row VA sample shows a genuine MIX**, not "all correctly-excluded
swallows": several ARE real swallows (interstate-compact article
bleed-through, amendment-history tails — correctly excluded); **at least
one is proven, byte-verified GENUINE**: `STATE_VA_T47.1_C1_S47.1-2`
(Notary Act Definitions), `"Satisfactory evidence of identity"` — a real
~3,020-char definition enumerating acceptable ID documents/methods,
bounded cleanly right before the next real term `"Seal"`. Captured by
NO path today (no numbered-block structure for baseline; dropped by our
ceiling) — a real, clean, silent U-R1 miss.

**Finding 3 — a separate boundary bug found while diagnosing Finding 2**:
`_LETTER_MARKER_RE`'s hard-stop false-fires on the parenthetical
abbreviation `"(PIV)"` because the CLOSING quote of the SAME already-open
quoted phrase sits within its 40-char lookahead window. Diagnosed, not
separately pinned this pass (a corpus sweep for "parenthetical acronym
near any quote" is real follow-up work) — recorded so it isn't lost;
means Finding 2's 1,308-entry drop count is itself an under-count in an
unknown number of cases (true spans are sometimes longer than measured).

**RED pinned**: `backend/tests/integration/test_us_markers_qa_q4_
ceiling_audit.py`. Node ids: `test_fixture_row_is_directly_definitions_
headed` (PASS), `test_the_real_definition_is_genuinely_long_not_a_
swallow` (PASS, proves the classification), `test_red_our_engine_
silently_drops_the_genuine_long_definition` (**RED**),
`test_red_real_pipeline_never_captures_this_genuine_definition_at_all`
(**RED**, end-to-end). Fixture: `us_markers_qa_q4_va_notary_definitions_
row.json` (1 real row, all 26 of its OTHER terms captured correctly —
confirmed in the RED test's own failure output).

### Q5 — `STATE_WA_T50_C29_S030` named-row test

**Implied term derived from the real row**: `section_title` = `'RCW
50.29.030: "Wages" defined for purpose of prorating benefit charges.'` —
unambiguous, **"wages"**. Real body: `'For the purpose of prorating
benefit charges "wages" shall mean "wages" as defined for purpose of
payment of benefits in RCW 50.04.320 .'` No ambiguity to report.

**Finding: this ALREADY PASSES at the extraction layer, un-fixed** — a
genuinely positive result, not forced into a RED shape. Confirmed:
`is_definitions_heading` False, `derive_heading_from_body` returns
`None` (this row IS the recognition-side miss the manager's binding
constraint described). Drove `extract_definitions_from_section` DIRECTLY
(same layer-agnostic pattern as core's NY newline test — `ingest_us_
statute_rows` → `profile.normalize_for_parsing` → `get_profile("US-WA").
extract_definitions_from_section`, never touching heading dispatch): 
**yields "wages" cleanly** — `US-WA` is registered in `us_markers_
inline_quote.py`, and "shall mean" is one of `_TIGHT_IDIOM_RE`'s
recognized idioms. The manager's acceptance condition ("extraction must
yield at least the implied term") is met at this layer today.

**The other half, also confirmed**: through the REAL, unmodified
end-to-end pipeline (`run_definition_linking`), this row still creates
**ZERO** definitions, because `pipeline.py`'s heading-dispatch gate never
reaches `extract_definitions_from_section` for it — it falls through to
`extract_local_scope_definitions` (the ordinary-article path), which also
yields zero. The gap is entirely RECOGNITION-side (headings panel's
H-R1/Q-C), not extraction-side (this sprint's).

**Tests (all PASS, no RED needed)**: `backend/tests/integration/test_us_
markers_qa_q5_wa_t50_c29_s030.py`. Node ids: `test_row_is_confirmed_
recognition_side_miss_not_heading_recognized`, `test_extraction_layer_
directly_yields_the_heading_implied_term`, `test_real_full_pipeline_
still_creates_zero_definitions_today_recognition_gap_confirmed`. Fixture:
`us_markers_qa_q5_wa_t50_c29_s030_row.json`. **To relay to the headings
panel's manager**: once recognition closes, the extraction-layer edge is
already provably ready to attach.

### Q6 — the correctly-empty classifier, independently re-derived + false-positive swept

**Re-derivation, corpus-wide (53 jurisdictions), current build**
(`markers-qa-q6-correctly-empty-sweep.py`): the claimed 224 (184 DC
terminal + 40 cross-reference: WY19/MN6/UT5/WA4/TX2/WI2/AL1/NC1)
reproduces EXACTLY as a subset — but only on the direct-title-recognition
denominator (21,072 zero-yield rows). On the body-derived-heading-
inclusive denominator (21,642 — the basis this pass's OWN sweep scripts
use, matching the manager's style), I measure **267**: the same 224 plus
43 more (42 CA + 1 GA, both `cross_reference`) that exist only because
CA/GA are reachable at all via `derive_heading_from_body`. **This is the
SAME denominator-basis ambiguity the manager flagged for Q7** (21,072 vs
21,642) — reported here explicitly rather than silently picking a basis.

**False-positive sweep — the check that had never been done.** The
manager's own M4/M5 full-corpus adversarial sweep (the one that
previously found and fixed 4 real WA false positives) covered only
WA/VA/FED/DC/WI/WY. **AL/CA/GA/MN/NC/TX/UT's 58 `cross_reference` hits
were inspected EXHAUSTIVELY this pass (all 58, not a sample) against
their real bodies: ZERO false positives.** Every one is, verbatim,
nothing but a single genuine cross-reference sentence. Also re-confirmed
WA(4)/WI(2)/WY(19)'s cross-reference rows against current real bodies
(all clean) and a random 10-row spot-sample of DC's 184 terminal rows
(all clean).

**Tests (all PASS — a genuinely clean result, not forced RED)**:
`backend/tests/unit/test_us_markers_qa_q6_correctly_empty_verification.
py`, one representative real row per newly-verified jurisdiction
(AL/CA/GA/MN/NC/TX/UT) committed as a permanent regression guard. Node
ids: `test_all_7_rows_are_genuinely_definitions_headed_or_body_derived`,
`test_zero_candidates_extracted_precondition_holds`, `test_all_7_never_
before_checked_jurisdictions_classify_correctly_empty_true`. Fixture:
`us_markers_qa_q6_correctly_empty_new_jurisdictions_rows.json` (7 real
rows).

### Q7 — P-R7 signal-agnostic denominator

**What my zero-miss judgment used elsewhere in this pass (STEP 0, Q1-Q6)
stated explicitly**: the heading-recognized population (`is_definitions_
heading` direct OR `derive_heading_from_body`-then-recognized), matching
the manager's own sweep-script convention. **This is NOT signal-
agnostic** — it is exactly the heading-signalled construction P-R7 warns
against, and it is vulnerable to the SAME failure mode P-R7 was written
for (proven live by Q5: `STATE_WA_T50_C29_S030` has a genuine definition
and is invisible to every heading-denominated sweep in this sprint).

**Signal-agnostic population constructed** (`markers-qa-q7-signal-
agnostic-sweep.py`): scanned EVERY row (regardless of heading) across all
13 covered jurisdictions for a defining-idiom shape (quoted-term +
means/shall mean/has the meaning/shall have the meaning/is defined as;
mojibake-quote variant; AL's ALL-CAPS marker shape; DC's unquoted "A/An
X means" shape) — deliberately simpler than the actual extraction
grammar (M18), presence-only, no boundary reasoning.

**The full, honest number, even though it is much worse**: **44,038
idiom-bearing rows corpus-wide across the 13 jurisdictions; 23,839 yield
zero captures = 54.1% miss.** Reported as-is, not rounded to look better.

**But this conflates two different families' scope**, and I decomposed
it rather than quote it whole: of the 44,038, only 19,179 are even
heading-recognized as Definitions sections (family 3's actual mandate);
the other 24,859 are ordinary (non-Definitions) articles with an
incidental defining idiom — spot-checked several (`STATE_VA_T59.1_C22_
S59.1-279` "qualified business firm", `STATE_VA_T38.2_C33_A1_S38.2-3300`
"As used in this article, 'individual life insurance' means...") and
confirmed these are genuine `defs-us-scoped-inline` (family 1) territory,
not family 3's — that bucket's miss rate is 94.9% (23,579/24,859), almost
total, because family 3 has never claimed ordinary articles at all.

**The fairer, still-signal-agnostic (within family 3's own scope) number:
of the 19,179 idiom-bearing AND heading-recognized rows, 260 yield zero
captures = 1.4%.** Per jurisdiction, dominated by AL 2.1% (31/1,451), TN
2.5% (28/1,118), **NC 13.4% (74/554), DC 11.2% (111/994)** — NC/DC stand
out badly. Sampled NC/DC's own zero-capture rows and found a real,
previously-unnamed shape driving most of it: `The term/word/phrase "X"
means/is hereby defined to be/shall be deemed and held to be...` — a
lead-in-phrase wrapper before the quoted term that neither baseline
(quote must be first, no prefix) nor either state's own family-3 rule
(both require UNQUOTED terms) recognizes. Real examples: `STATE_NC_
C87_S87-21` (`"plumbing"` defined via "The word ... is hereby defined to
be..."), `STATE_DC_T44_C9_S44-902` (`"Hospital"` via "The term ...
means..."). Not pinned with a RED this pass (a new rule module is
implementation, not QA's to write) — named here as a concrete, real,
previously-unidentified family-3 sub-case for the manager/Planner.

**Explicit limitation, labeled, not hidden**: my idiom detector covers
only the means/shall-mean/has-the-meaning family plus AL/DC's own
shapes — it does NOT include other known residual idioms (`includes`,
`shall be deemed to refer to`, single-term pointer definitions) P1's own
log named as a smaller "bucket 4" population. **My 1.4% headed-only
figure is therefore a LOWER BOUND**, not an exhaustive number — the true
family-3 residual under a fully exhaustive idiom vocabulary is somewhat
higher. No test artifact for Q7 (a measurement/methodology finding, not a
single defect to pin) — full sweep scripts are scratchpad-only per data
policy, numbers reported here and reproducible from this section's
methodology.

### Q8 — no regression

Full suite, run repeatedly through this pass (final run below): **`7
failed, 829 passed`** = 1 pre-existing FED RED (`test_us_markers_
unbounded_last_entry.py::test_real_pipeline_does_not_let_fed_part_time_
career_employment_swallow_the_amendment_history_tail`, owned by
`2026-08-05-defs-core-follow-on-2` gate G3, byte-identical failure to
what M9/M13 recorded) + exactly the 6 REDs added this pass (Q1×1, Q2×1,
Q3×2, Q4×2). `829 = 814 + 15` newly-passing diagnostic/regression-guard
tests (Q1×3, Q2×1, Q3×3, Q4×2, Q5×3, Q6×3). No other failure anywhere —
confirmed by `git status --short`: only new files under `backend/tests/`
(6 test files, 6 fixture files), zero production-code diffs.

### What rests on a control that could have failed vs. what does not

**Rests on a control that could have failed (and passed)**: STEP 0's
kill control; Q1's per-row kill control (family-3 blinded, baseline alone
still swallows); Q1/Q3's "our own engine already produces the clean
candidate" proofs (could have failed if the engine were also broken).

**Does not rest on a control, but IS independently re-derived from real
data**: Q2/Q3's degenerate-capture diagnoses (read the actual regex
mechanism, not assumed); Q3's citation-shaped-tail corpus sweep (a fresh
measurement, no prior claim to compare against); Q4's histogram/no-spike
finding and the "Satisfactory evidence of identity" genuine-long
classification (read the real body, checked for swallow markers
explicitly); Q5's implied-term derivation and both extraction-layer/
full-pipeline results; Q6's exhaustive 58-row false-positive inspection;
Q7's signal-agnostic sweep and its headed/not-headed decomposition.

**Explicitly labeled unverifiable / out of this pass's scope**: Q4's
Finding 3 (the "(PIV)" false-hard-stop) is diagnosed but its corpus-wide
prevalence is NOT measured — labeled as an open question, not claimed
either way. Q7's 1.4% headed-only figure is labeled a lower bound, not an
exhaustive number. Whether core-2's G3 fix will ALSO close Q1's
pipeline.py collision-ordering finding is explicitly NOT claimed either
way — reported to the manager as an open, testable prediction, not
assumed.

### Files (test-only, no production code touched)

New test files: `backend/tests/integration/test_us_markers_qa_q1_wa_
newline_collapse_swallow.py`, `test_us_markers_qa_q2_short_definitions.
py`, `test_us_markers_qa_q3_tx_2009_003.py`, `test_us_markers_qa_q4_
ceiling_audit.py`, `test_us_markers_qa_q5_wa_t50_c29_s030.py`,
`backend/tests/unit/test_us_markers_qa_q6_correctly_empty_verification.
py`. New fixtures (all byte-verified against the real parquet corpus this
pass): `us_markers_qa_wa_newline_collapse_rows.json`, `us_markers_qa_q2_
short_definitions_rows.json`, `us_markers_qa_q3_tx_2009_003_row.json`,
`us_markers_qa_q4_va_notary_definitions_row.json`, `us_markers_qa_q5_
wa_t50_c29_s030_row.json`, `us_markers_qa_q6_correctly_empty_new_
jurisdictions_rows.json`.

