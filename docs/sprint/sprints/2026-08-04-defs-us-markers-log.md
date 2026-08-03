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
