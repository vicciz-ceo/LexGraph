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
