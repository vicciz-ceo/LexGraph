# Sprint log — 2026-08-23-defs-debt-31 (append-only overflow)

Full test output, QA transcripts, per-round narration, and superseded notes
land here. Never auto-loaded.

## Agent roster

- 2026-08-23T18:54Z manager: sprint opened by claude-code manager (Fable 5),
  branch `claude/defs-debt-31` from main @ 8850401.
- 2026-08-23T18:56Z planner spawned: agentId ad8cac9fc7a8dba62 (Sonnet, high).

## Planner pass (2026-08-23)

### Preflight + reading

HEAD verified `5962c98` (main + sprint docs) before starting; a small
concurrent roster commit (`96a35e4`, manager) landed mid-pass, no conflict.
Read: contract, `gh issue view 31`, the three evidence files
(`investigation.md`, `expansion_precision.md`, `expansion_precision_2.md`),
prior sprint contract + `-log.md` (Item 1 pass, FX7 adjudication §8), and
the program doc's rulings (P-R11/12/15/16/18, M-R107, D-MAP, D-RECALL-FP).
CodeGraph (`.codegraph` at the MAIN checkout, `/Users/nerya/LexGraph`, not
this worktree) used for `us_profile.py`/`us_markers_boundary.py` structure;
direct `Read` used to confirm exact current line numbers since HEAD is not
`main`.

### Code reading — the seam, precisely

- `USProfile.extract_definitions_from_section` (`us_profile.py:2568`):
  `if heading_was_derived: candidates = _merge_fallback_candidates(candidates, text, scope=scope)`
  (line ~2619-2620) — the merge ALWAYS runs when `heading_was_derived`,
  regardless of whether `candidates` is empty (Item 2 of the PRIOR sprint's
  own fix, already landed). `_merge_fallback_candidates` (line ~2462) calls
  `_extract_inline_quoted_definitions` unconditionally, admits a fallback
  candidate per-term (no primary-term collision) filtered by
  `_is_implausible_fallback_capture` (stopword/caption-year/`Pub. L.`/
  `Subsec.\(` — the director's 2026-08-23 extension already shipped; NO
  single-letter filter exists today, confirmed by `grep` — the
  `_FALLBACK_SINGLE_LETTER_TERM_RE` constant from the reverted `877c970` is
  gone entirely).
- `_extract_inline_quoted_definitions` (`us_profile.py:1077`): its own
  idiom gate is `_MEANS_IDIOM_GAP_RE = r'^[^"“”]{0,200}?\b(?:means|shall
  mean|has the meaning|shall include|includes)\b:?\s*'` — a NON-GREEDY
  0-200-char gap tolerance, which is exactly why a genuine `"X" symbol
  means...` (NV, ~8-char gap) and a phantom `"e", subparagraph (2),
  eligible service includes...` (IA, ~38-char gap through an intervening
  noun phrase) BOTH pass today — there is no adjacency/proximity signal at
  all, confirming the round-1/round-2 evidence's own "no positional/
  ownership check" finding. Each entry's definition runs to the START of
  the next recognized entry or `len(text)` — NO `TRAILING_STOP_RE`, NO
  `MAX_CLEAN_DEFINITION_LENGTH` ceiling of its own (confirmed by reading
  the whole function body — no such call exists).
- `us_markers_boundary.close_entries`'s OWN `bounded = bool(candidate_stops)
  or has_next_term` / `MAX_CLEAN_DEFINITION_LENGTH` ceiling is the FX7
  ceiling itself — confirmed via `test_us_markers_fx7_ceiling_known_closed_
  scope.py` (already shipped, GREEN, zero RED tests by design — the file's
  own docstring proves widening `bounded` to recover the 41 would flip the
  genuine-runaway safety test). **Item 1 must NOT touch this** — it is a
  DIFFERENT, already-protected mechanism; Item 1 adds an INDEPENDENT new
  trim path to `_extract_inline_quoted_definitions` itself, which today has
  none at all (not "widen an existing one").
- `us_markers_oh_trailing_clause._split` (OH's own EntrySplitterRule) calls
  `extract_quote_anchored_entries` (PRIMARY engine) then applies
  `_LAST_UPDATED_TAIL_RE`/`_TRAILING_LETTER_CLAUSE_RE` — this cleanup is
  PRIMARY-path only; a fallback-sourced OH term (bare `includes`, never
  `_TIGHT_IDIOM_RE`-recognized) never reaches it. Confirmed live
  (`STATE_OH_T49_C4905_S4905.331` "Proceeding" — bare `includes`, fallback-
  only, "Last updated" tail present in the current capture).

### Real-row exemplars (live-verified against HEAD before any test was
written; snapshot `.../301000fc3465374ee0f23c3c6953a8a861e95cad`)

Fetched via `pandas.read_parquet` (per-jurisdiction files), vendored as
JSON fixtures matching the existing schema (`us_markers_c5guard_nj_rows.json`
convention), then run through the REAL `ingest_us_statute_rows` ->
`run_definition_linking` pipeline to ground every expected string in actual
observed output (never hand-guessed):

- `STATE_NY_ASOS_A6_T1_S390` "Enrolled legally exempt provider": true def
  341 chars ending "...regulations of the office of children and family
  services."; TODAY captures 3,154 chars, bleeding through "2. * (a) Child
  day care centers..." into a THIRD unrelated subsection.
- `STATE_OH_T49_C4905_S4905.331` "Proceeding": true def 93 chars; TODAY
  captures 1,373 chars including the OH "Last updated July 9, 2025 at
  12:24 PM" scrape stamp — ONE real row demonstrates BOTH gate-1-named
  exemplar types at once.
- `USC_T5_C75_S7511` "furlough": **finding** — this was one of the ORIGINAL
  118 FX7-remainder rows (total ceiling-drop). On this worktree's HEAD it
  is now CAPTURED (144-char true def, bleeding into "(b) This subchapter
  does not apply..."), because the already-landed idiom widening
  incidentally gave it a downstream boundary via a different, newly-
  recognized entry elsewhere in the section. It has migrated from Class 4
  (FX7 remainder) into Class 1 (bleed) — used as a 3rd real Item-1
  exemplar, NOT re-used for Item 4. No fresh corpus-wide re-census of "how
  many of the ~100 remainder rows are still genuinely 0%-today" was run at
  planning altitude (that census is Dev/QA's job against the real code,
  per P-R11 — not a Planner-predicted ledger); Item 4's own file uses
  M-R107 synthetic controls instead, modeled precisely on the evidence's
  documented shape for both named families.
- `STATE_IA_TIII_C97B_S97B.49B` "e": confirmed live, WRONGLY admitted
  today (`.../97B.49C.\n\n(1) (d)` — a mis-paired capture bleeding into the
  next entry's own marker too). Real exemplar for Item 2's "distant"
  (reject) direction, sub-mechanism 1 (lettered cross-reference citation,
  14/19 of the corpus census).
- `STATE_NV_T43_C484B_S484B.307` "X" (source `“ X ”`, padded): confirmed
  live, correctly admitted today, ALSO currently bleeding (true def ends
  "...red signal is shown.", captures continue into "13. A local
  authority..."). Item 2's protected-anchor exemplar (presence-only
  assertion — byte-exact trim is Item 1's concern, kept independent).

### Stale-pin sweep (mandatory, full — `grep -riE` across all four test
roots for every behavior these items change)

**5 hits requiring re-pointing, all in `test_us_markers_fallback_guard_
recovery.py`** (prior sprint's own Item-2 recovery file, real-row fixtures
already vendored, currently GREEN): its own docstring stated expected
texts were "the fallback function's OWN existing output... unchanged by
this item -- `_extract_inline_quoted_definitions`'s internals are out of
bounds per the amended [PRIOR sprint's] gate 7" — a premise THIS sprint's
gate 8 explicitly reverses (the seam is now open, needed for Item 1). Five
exact-match assertions baked in the very bleed tails Item 1 targets as
REQUIRED substrings:
- FED 12889 "Pre-Apprenticeship": required `"...29 CFR 30.2.\n\n(c) The
  term"` (next entry's own lead-in) -> re-pointed to end at "...29 CFR
  30.2."
- WA 717 "convicted": required `"...or the levying of a fine. For the
  purposes of this section,"` (list-introducer-stub bleed) -> re-pointed
  to end at "...or the levying of a fine."
- OH 3296 "Derivative transaction": required `"...or other assets. (2)"`
  (next entry's own marker) -> re-pointed to end at "...or other assets."
- NY 1978 "Bakery basket"/"Dairy case": required `"...products.\n  b."`/
  `"...products.\n  e."` (next lettered entry's own marker+quote) ->
  re-pointed to end at "...products."

All 4 test functions in that file re-run RED (for the correct reason —
bleed present today) after re-pointing; this file is now ALSO Item 1
real-row RED coverage (4 more real rows: FED/WA/OH/NY), on top of the 3 I
vendored fresh (NY/OH/FED-furlough) -- **7 real-row bleed exemplars
total**, well beyond the brief's 2-exemplar minimum.

**Checked, NOT stale (verified, not assumed)**:
- `test_us_markers_fallback_guard_single_letter_negative_control.py` (5
  tests, GREEN): both its fixtures (`"B"`/`"C"` immediately followed by
  their idiom, ZERO gap) are already the "adjacent" shape under ANY
  reasonable adjacency threshold — re-run confirmed GREEN unchanged; left
  untouched.
- `test_qa_regression_defs_boundary_idioms.py` (7 tests, GREEN): its NV
  "X" excerpt test uses a SHORT excerpt with no trailing bleed content
  (unaffected by Item 1); its synthetic single-letter term is named `"Q"`,
  immediately adjacent to `"means"` (unaffected by Item 2's adjacency
  rule) — **collision avoided**: my own Item 2 file originally also used
  `"Q"` for the OPPOSITE (distant/reject) case; renamed to `"K"` to avoid
  reader confusion across files (no runtime collision either way — locally
  scoped strings). This file's 3 gate-2-certificate pins (byte-identity to
  `f267644`, summary counts, `changed.jsonl` checksum) are a DELIBERATE
  tripwire, by their own docstrings — they WILL go RED the moment Items
  1-4 land code changes to `backend/app/`. This is correct, expected
  behavior, not a stale pin to fix now: re-pointing them to the fresh
  gate-2 certificate's SHA/counts requires the certificate to exist first
  (P-R11 — run, then adjudicate; never hand-author), so it is Item 5's own
  closing work, needing a Planner return-pass once real numbers exist.
  Flagged in the contract's Known traps.
- `test_us_markers_ext_b_oh.py` (2 tests, GREEN): a DIFFERENT OH row
  (`STATE_OH_T21_C2108_S2108.61`), reached via the PRIMARY engine (OH's own
  EntrySplitterRule, "means" idiom) — already protected by that same
  `_LAST_UPDATED_TAIL_RE` cleanup at the PRIMARY layer since an earlier
  sprint. Confirms the primary-path OH cleanup precedent exists; not
  reached by my fallback-only fix, not stale.
- `test_us_markers_fallback_guard_phantom_negative_control.py`,
  `test_us_markers_fallback_guard_term_key_negative_control.py`: use
  `startswith`/presence checks, not exact-match bleed-tail pins; unaffected
  by trimming. Not stale.
- `test_us_markers_not_yet_rescued_subcases.py`,
  `test_us_markers_wave1_inline_quote_fallback.py`,
  `test_us_markers_wave1_auto_rescue_subcases.py` (19 tests, GREEN): older
  sprint's AL/DC/RI/AK/TN/SC unquoted-term/mojibake/marker shapes, none
  reached by `_extract_inline_quoted_definitions`'s standard quoted-term
  gate; SC's own "Effect of Amendment" trailing-annotation protection is
  `TRAILING_STOP_RE` (PRIMARY-path `trailing_stop_limit`), unaffected. Not
  stale.
- `test_us_markers_ext_b_mn.py`: "single-letter" grep hit is about
  `_LETTER_DOT_MARKER_RE`-style MARKER tokens, not single-letter fallback
  TERMS. Unrelated, not stale.
- "mis-paired"/"Crime Stoppers"/"apprenticeship" hits elsewhere: either
  describe DIFFERENT, already-fixed defect classes (garbage term key,
  legislative-history caption) using the same English phrase, or are plain
  statutory text containing the word "apprenticeship". Not stale.

Full backend suite run AFTER all fixture/test additions and re-points:
**1414 passed, 12 failed, 0 errors** (baseline before this pass: 1408
passed). The 12 failures are EXACTLY the intended RED set (3 bleed-trim
real-rows + 3 bleed-trim structural + 2 single-letter adjacency + 4
re-pointed fallback-guard-recovery) — zero unexpected collateral, zero
collection errors, confirming the sweep was complete relative to the
current suite.

### Item 3 / Item 4 design note (why no RED test in either file)

Both classes have an explicit EITHER-outcome-legitimate gate (fix OR
adjudicate). A test asserting "the code recovers X" would foreclose the
adjudicated-unrecoverable outcome; a test asserting "X stays absent/
mis-paired" is the literal forbidden pattern ("never assert the pre-fix
broken state in a test the Developer cannot edit") -- if a fix IS found
this sprint (the seam for Item 3 is WIDER than the prior sprint's, see
above), that assertion would need to flip and only the Planner may edit
tests. Precedent already shipped in this exact codebase:
`test_us_markers_fx7_ceiling_known_closed_scope.py`'s own docstring: "there
is no RED test in this file" -- GREEN structural proof of why a
hypothesized fix's premise does not hold. Both new files here follow that
precedent: pure evidence (Item 3: term-key/payload-shape signal-identity
between real matched genuine/mis-paired pairs, restated with novel
identifiers; Item 4: text-level structural facts about the two named
families' own documented shapes, calling no production code at all so
they cannot flip red under any Dev/QA resolution).
- 2026-08-23T19:38Z developer spawned (solo, Items 1-5): agentId a84542532f2c9fbac (Sonnet, medium). Left uncommitted deliberately so the Developer's HEAD sync check still sees b33d994; rides in its first commit.

## Developer pass (2026-08-23/24)

### Sync + RED verification

HEAD matched `b33d994` at start. Scoped RED run confirmed 12 RED (3
real-row + 3 structural bleed-trim, 2 single-letter adjacency, 4
re-pointed fallback_guard_recovery) / 10 GREEN controls, matching the
Planner's own count exactly.

### Item 1 (bleed trim) — investigation before implementation

Direct-execution tracing (not hand-analysis) of all 3 real-row RED
exemplars found the Planner's own stated seam was INCOMPLETE for 2 of
3: NY `STATE_NY_ASOS_A6_T1_S390` "Enrolled legally exempt provider" and
FED `USC_T5_C75_S7511` "furlough" both reach their FINAL, winning,
persisted `Definition.definition_text` via BASELINE's own `_split_into_
numbered_blocks`/`_leading_quote_candidate` (the "(g)" lettered-list
block splitter / FED's own numbered-block splitter), not via `_extract_
inline_quoted_definitions` at all -- confirmed by directly calling each
candidate mechanism in isolation and comparing byte-for-byte against
the real, live pipeline's own persisted output. FED's own row is
additionally reached with `heading_was_derived=False` (its "Definitions;
application" heading is directly, baseline-recognized -- one of the 7
already-`section_title`-working states), meaning `_merge_fallback_
candidates` (the ONLY place a first implementation attempt scoped the
trim to) never runs for it at all. Only OH `STATE_OH_T49_C4905_
S4905.331` "Proceeding" is genuinely fallback-sourced as originally
assumed.

Implementation: `_fallback_bleed_trim_end`/`_clean_fallback_trailing_
bleed`/`_trim_fallback_candidate_bleed` (new, in `us_profile.py`),
reusing `us_markers_boundary.compute_hard_stops` unmodified plus two
narrow, period-gated relaxed checks (a letter-paren marker and a non-
line-anchored digit-dot marker, both requiring a LITERAL PERIOD
immediately before -- narrower than `_preceded_by_sentence_or_clause_
boundary`, chosen specifically to exclude a marker glued right after an
idiom and a semicolon-joined internal enumeration, both real risks a
looser check would have hit). First implementation attempt applied the
trim to EVERY baseline-block candidate for EVERY jurisdiction
(reasoning: matches where the real defect lives) -- live full-suite run
regressed 19 pre-existing tests (`c5guard` MI/ND/NJ/NY/OK, WA's own
newline-collapse "kill control", TX 2009.003, NE/SD preamble, FED Good
Samaritan, mr121, term-key-negative-control). Root cause: `_trim_
definition_at_structural_sibling`'s own pre-existing docstring already
documents that "no marker-structure-only signal separates FED's real
over-capture from several OTHER jurisdictions' own PINNED,
intentionally-kept baseline captures of the identical shape" -- missed
on the first pass, found by reading that function's own commentary
after the regression. Corrected: scoped to `heading_was_derived`
articles (covers NY, zero-risk for the 7 already-working states by
construction) OR `self.code == "US-FED"` specifically (covers furlough,
matching `_trim_definition_at_structural_sibling`'s own precedent
exactly) -- re-run: down to 8 failures (2 pre-existing mr121 + 2
Item-2-not-yet-implemented + the term-key-negative-control + 3 others).
Narrowed `_merge_fallback_candidates`'s own trim application from
"every candidate in `merged`" to "only newly fallback-admitted
candidates" (the broader form was ALSO touching `EntrySplitterRule`-
and `TermClauseRule`-sourced candidates it should never see) plus added
an abbreviation-before-marker guard (`_FALLBACK_TRIM_ABBREVIATION_
BEFORE_RE`, catches `"Subsec.` /`"Pub.` -shaped citation abbreviations
whose own period is not a sentence end) -- down to the 2 mr121 stale
pins + 2 pre-existing cross-sprint frozen-production tripwires (gate-2
certificate + `qa_g7_common.INTEGRATION_SHA`), stable from there.

**Performance regression found and fixed** (same item, before first
commit): `_fallback_bleed_trim_end` originally called `compute_hard_
stops(text, end)` fresh per candidate -- cProfile on the real corpus
found `USC_T5_C6_S601` (403,285 chars, 42 candidates) cost 19.6s for
that one row alone. `compute_hard_stops`'s own marker-run tracking is a
strictly sequential left-to-right scan, so computing it ONCE per row
with `limit=len(text)` (a safe superset) and filtering the same
precomputed list per candidate is byte-identical to computing it fresh
each time -- `_whole_text_hard_stops` fixed this, same row now 1.657s.
Remaining cost identified (not fixed, out of scope) as a pre-existing
O(n)-per-call inefficiency in `us_markers_boundary._preceded_by_list_
introducer` (slices the whole text prefix instead of a bounded
lookback) -- flagged as a follow-up task (`task_ddf8102c`).

**Critical correctness bug found via Item 4's own investigation, fixed
before Item 1 was considered done**: building Item 4's population
census surfaced a severe-reduction pattern in Item 1's OWN population
measurement data (146 candidates in a 10-jurisdiction sample collapsed
from genuine multi-hundred/thousand-char content down to ~11-17 chars).
Root-caused (after first discovering and fixing an unrelated row-
attribution bug in the measurement script's own instrumentation
ordering) to `compute_hard_stops`'s reused digit-marker check firing on
the REVERSE of its intended shape: a per-paragraph quote-REOPEN
followed by an internal list item of the SAME quoted block (real FED
`USC_T50_C44_S3024` "covered element of the intelligence community"
means the following:\n\n"(1) The Office...\n\n"(2) The Central
Intelligence Agency...) -- `compute_hard_stops`'s own `_AFTER_MARKER_
UPPER_RE` branch is designed for MARKER-then-quote/uppercase (a NEW
term), has no notion a quote can come FIRST as a paragraph-reopen (the
exact shape `_extract_inline_quoted_definitions`'s own `_is_paragraph_
start_quote` already handles for TERM-pairing, invisible to `compute_
hard_stops`). Fixed: `_hard_stop_is_inside_quoted_block` excludes any
REUSED hard-stop immediately preceded by a quote character. Verified on
the real row (`USC_T50_C44_S3024`'s definition now correctly kept
intact, all 280 chars). Full backend suite unchanged after the fix
(same 4 known failures). This is exactly the P-R16/"measure the actual
pipeline" discipline paying off -- no hand-picked unit test happened to
carry this shape; only population-scale measurement surfaced it.

Scoped tests: 13/13 green throughout. Full backend suite stable at 4
failures from the second corrected pass onward (2 pre-existing mr121
stale pins on a genuinely fallback-sourced mis-paired "Borealia"
capture whose OWN trailing bleed Item 1 now correctly trims -- same
class as the 5 pins the Planner already re-pointed in `test_us_markers_
fallback_guard_recovery.py`, just outside this sprint's own swept file
set; 2 pre-existing cross-sprint frozen-production tripwires that fire
on ANY future sprint touching `backend/app/`, by their own design, not
specific to this sprint).

**Two MORE bugs found on re-running the population measurement after
the quoted-block fix** (same discipline: measure, don't assume the
first fix was complete):

- **Abbreviation guard too narrow.** The first fix
  (`_FALLBACK_TRIM_ABBREVIATION_BEFORE_RE`) only excluded a short word-
  then-period when immediately preceded by a QUOTE character
  (`"Subsec.`). Real FED `USC_T21_C13_S801`'s own baseline-block
  candidate -- itself a pre-existing, out-of-scope primary-engine
  defect (a numbered clause from a quoted Executive Order mis-split as
  a fake "term") -- has its OWN `definition_text` starting `"Sec. 5.
  The Attorney General..."` with NOTHING before "Sec." at all, not even
  a quote (it sits right at `definition_start` itself), so the quote-
  specific guard missed it, collapsing 5148 chars down to 4 ("Sec.").
  Generalized: `_period_precedes_a_real_sentence` finds the nearest
  preceding clause boundary (a quote OR an earlier period, bounded
  60-char lookback, deliberately NOT a newline -- real prose hard-wraps
  mid-sentence, e.g. NY's own validated "...family\nservices." stop)
  and requires the clause between that boundary and the current period
  to contain at least one whitespace character (more than one word) --
  generalizes to ANY short label, not just the two named abbreviations.
- **Reused hard-stops with no minimum-content floor.** A BASELINE-
  sourced candidate's `definition_text` (via `_leading_quote_candidate`)
  is never idiom-stripped -- "means"/"shall mean" stays the literal
  first word(s), unlike `_extract_inline_quoted_definitions`'s own
  candidates. When such a definition legitimately opens with an
  enumeration marker right after its own idiom (real NY `STATE_NY_
  ATAX_A8_S171-T`'s own `"Debt" means (i), for purposes of state debt,
  a "tax debt" as\ndefined in section...`), `compute_hard_stops`'s own
  REUSED letter-marker check found a quote shortly after that FIRST
  marker (`"tax debt"`, a nested cross-reference within the SAME first
  enumerated item, not a sibling entry) and treated it as a hard-stop --
  collapsing a 1015-char candidate down to the bare idiom word itself
  ("means", 5 chars). `_period_precedes_a_real_sentence` structurally
  guards this module's OWN two relaxed checks (a period can never
  appear within a handful of characters of `definition_start`), but the
  REUSED `hard_stops` list had no such requirement of its own. Fixed
  with `_MIN_CONTENT_BEFORE_REUSED_STOP` (20 chars): a genuine
  definition is never just its own bare idiom word.

Found by classifying the FULL "severe reduction" population (77 cases
remaining after the first fix, before>200 chars / after<20 chars) by
whether the TERM ITSELF looks genuine vs. citation-noise-shaped --
IMPORTANT finding along the way: the large majority of the 77 (69/77)
turned out to be genuine trim SUCCESSES, not bugs (a badly-bleeding
1000s-char capture correctly reduced to its TRUE short definition, e.g.
real `"spouse"` -> `"a widower."`, `"consolidation"` -> `"a merger."`,
`"regulation"` -> `"an order."` -- all plausible, complete, correct US
Code definitions). Raw "before/after size ratio" alone is NOT a
reliable defect signal for this population; only a handful of the 77
were genuinely broken, and both are now fixed. Also fixed in the same
pass: a pre-existing row-attribution bug in the measurement script
ITSELF (`measure_item1_bleed_trim_population.py`'s own `_current_row_
ctx` was updated AFTER `derive_body_preamble_match`'s own internal pre-
check call, mis-attributing a trim event's act_id to whatever row had
most recently updated the dict) -- confirmed live (a flagged record's
own act_id genuinely did not contain the term it was filed under)
before either of the two bugs above could be correctly traced to their
real source rows.

Full backend suite unchanged after both fixes: 1422 passed, 4 failed
(same known/documented set, stable throughout).

**Fourth bug, same discipline, found re-running the population
measurement AGAIN after the third fix**: classified the (now-reduced,
63-case) "severe reduction" list once more by term-shape; almost all
were confirmed-genuine short definitions again (same stable set: spouse
-> a widower., consolidation -> a merger., etc.), but one new case
stood out on spot-check -- real FED `USC_T16_C24_S1151`'s own `"Party"
or "parties" means the United States of America, Canada, Japan, and
Russia (except that as used in subsection (b) of this section,
"party" and...`. A marker-based stop (mid-sentence, at the "(b)"
cross-reference's own nearby quote -- a lower-severity residual variant
of the same "ordinary cross-reference marker followed shortly by an
unrelated quote" class the quoted-block and min-content fixes already
partially address, not fully chased further given this sprint's time
bounds) left an un-terminated tail. `_clean_fallback_trailing_bleed`'s
own "dangling tail" heuristic then searched that tail for the broadest
terminal-char set (including bare quotes) and found `"parties"`'s own
closing quote -- a nested term name early in the sentence, not a
sentence end -- cutting there and discarding the real definitional
content (`means the United States of America, Canada, Japan, and
Russia`) entirely, leaving just `or "parties"` (12 chars). Fixed:
split into `_SENTENCE_ALREADY_TERMINAL_CHARS` (broad, gates whether to
attempt a back-trim -- ending in a quote is a legitimate way to already
be complete) and `_SENTENCE_SEARCH_BACK_CHARS` (narrow: period/
semicolon only -- what it searches backward FOR). A quote closing a
short quoted phrase is not a reliable "sentence complete" signal the
way a period/semicolon is. Verified: now keeps the real content (109
chars ending "...as used in subsection" -- still cut short by the
"(b)" marker misfire, a materially better outcome than losing the
content, not a full fix of that residual). Full suite unchanged: 1422
passed, 4 failed (same set).

**Stopping point (time-bounded, not exhaustive):** four independent,
confirmed bug classes found and fixed via repeated population-scale
re-measurement, each verified live against a real corpus row, each
re-confirmed against the full scoped test suite AND the full backend
suite with zero new regressions. A final population re-verification
pass is running now (`item1_population_run/`, 4th rerun) to confirm
`term_dropped` stays at zero and the residual "severe reduction"
population stays the same stable, already-classified-as-genuine set
before this item is treated as fully done. Any FURTHER, smaller-still
residual imprecision in this specific reused-marker-heuristic class
(the "(b)"-style ordinary cross-reference followed coincidentally by an
unrelated quote) is accepted as a known, documented, lower-severity
characteristic rather than chased indefinitely -- it never drops an
anchor (D-RECALL-FP holds throughout, confirmed zero `term_dropped`
across every population run) and only ever affects the BYTES of an
already-imperfect population, consistent with Item 1's own "trim, not
achieve perfect precision on every corner case" mandate.

### Item 2 (single-letter adjacency)

Corpus-computed (not guessed) the exact idiom-gap distance for every
named exemplar: NV 484B.307 "X" = 8 chars, this item's own synthetic
"Z" control = 11 chars (both must ADMIT); IA 97B.49B "e" = 37 chars,
this item's own synthetic "K" control = 93 chars (both must REJECT) --
wide, unambiguous margin, threshold set at 20 chars.
`_single_letter_term_lacks_adjacent_idiom` wired into both `_extract_
inline_quoted_definitions` entry points (ordinary + nested block-quote
path). 9/9 scoped tests green on first implementation attempt, zero
new regressions in the full suite.

### Item 3 (mis-paired quotes) — no-code, adjudicated

Investigated the positional/span-tracking signal gate 3 reopened.
Found it real (all 4 named real mis-paired exemplars live-verified to
cross a marker or a genuine sentence-terminating period between their
quote's close and their matched idiom; matched genuine pairs do not).
But a real-corpus scoped search for the specific counter-example a
naive implementation would need to survive found 8 GENUINE definitions
with the identical marker-crossing shape in the first 6 non-empty FED
rows checked (FED's own extremely common `"(N) Label.--The term 'X'
means Y."` numbered-definition-list convention) -- confirmed via direct
corpus read, not speculated. A safe implementation would need the same
class of dedicated, multi-round corpus-hardening machinery
`us_markers_boundary._digit_paren_run_internal_content_starts` already
required for the primary engine's own digit-paren-run discrimination --
not buildable within this item's "scoped populations, not full all-53
runs" exploration bound. Full write-up: `-scripts/item3_mispaired_
quote_adjudication.md`. Evidence test unchanged, GREEN throughout.

### Item 4 (FX7 remainder) — in progress

Research (dedicated `Explore` agent pass) confirmed the prior sprint's
own "118 live-verified ceiling-tripped losses" was never persisted
anywhere in the committed repo at any point -- its source artifacts
were a deliberately-uncommitted throwaway pytest probe (`docs/sprint/
sprints/2026-08-20-defs-boundary-idioms-log.md` §1: "deleted before any
commit"). No act_id-level list exists to read; the only individually-
named row across the entire cluster of prior-sprint documents is
`USC_T5_C75_S7511` "furlough" itself (already confirmed migrated into
Item 1, per that item's own real-row exemplar). Live-re-deriving the
population now via `measure_item4_fx7_remainder_census.py` (real-
ceiling-vs-monkeypatched-unbounded-ceiling comparison across the 14
`us_markers_inline_quote.py`-registered jurisdictions, on this
worktree's CURRENT code -- i.e. what the ceiling drops even after
Items 1-2 already landed).

### Item 5 (certification) — in progress

Full all-53 baseline (`main` @ `8850401`) vs current run via the
corrected `run_gate5_certification.sh` (adapted verbatim from
`2026-08-12-defs-b1-refers-to-scripts/run_gate2.sh`'s own corrected
pattern -- `--current` on both sides). `measure_actual_production.py`'s
own `capture()` calls `profile.extract_definitions_from_section`/
`extract_local_scope_definitions` directly (not a reimplementation) --
P-R16 satisfied without modifying the shared harness: it automatically
reflects every Items-1-4 change. 100%-anchor-granularity delta
adjudication script (`adjudicate_gate5_delta.py`) ready, classifies
every changed anchor into text-change / true-removal / true-addition
per the standing "decompose at (row,term) granularity" lesson, plus the
P-R15 deletion-side screen.
- 2026-08-24T05:20Z developer complete: 5/5 Dev Complete @ 1853479; manager
  re-verified diff containment (only us_profile.py, zero test files), reran
  full backend (1422P/4F, identical reconciliation), spot-verified gate5
  certificate (P-R15 0/30, additions 0, NV 484B.307 X kept, removals all
  single-char phantoms). 4 failures = tripwire pins (test estate).
- 2026-08-24T05:20Z planner return-pass spawned: re-point gate-2 tripwire +
  2 mr121 R7 pins + g7 INTEGRATION_SHA/evidence. Lock -> claude-code:planner.
- 2026-08-24T05:22Z planner return-pass agentId a5d31c4c1a24a1ea7 (Sonnet, high). Uncommitted append (HEAD-check preservation), rides in its commit.
