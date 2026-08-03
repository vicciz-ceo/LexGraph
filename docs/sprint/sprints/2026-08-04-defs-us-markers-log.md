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
