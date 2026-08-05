# Sprint log: 2026-08-05-defs-il-certification

**Why a new log file, not an append to `2026-08-04-defs-il-log.md`:** that
file is 7,368 lines and belongs to a DIFFERENT, now-closed sprint
(`2026-08-04-defs-il`, `status: qa-fail`, D-1/QA-cycle-4 history). This
sprint has its own contract, its own 5-cycle valve, and its own gates
(C1-C5) -- a fresh file keeps this sprint's own history readable without
forcing every future reader through the parent's Phase A-D archaeology.
Cross-references to the parent log (M18, M22, M23, M25, M28, M29, M30,
M31) are by ruling number, not by inclusion.

---

## 2026-08-05 -- Planner (Sonnet/high), worktree `defs-il-cert-plan1`

### Scope discipline (M14), verified before and after

Worktree `/Users/nerya/LexGraph-wt/defs-il-cert-plan1`, branch
`claude/defs-il-certification`, at `a27698d`, clean at start. Own venv
verified: `import app` -> this worktree's `backend/app`. `git config
user.email` -> the noreply address, confirmed. Baseline reproduced
myself before writing anything: `backend/.venv/bin/pytest backend/tests
-q` -> **`2 failed, 843 passed`** -- exact match to the brief. `git diff
--name-status HEAD -- backend/app` -> empty, verified before AND after
every write this session. Did not touch
`test_definition_links_il_siman_chelek_containment_live.py` -- read only,
never edited, still RED at the end (confirmed below). No existing test
edited (all new files, see "Files" at the end).

### Read first (per the brief)

The certification contract (`2026-08-05-defs-il-certification.md`, 302
lines, both amendments), the parent contract's residual/gate-status
section, and the parent log's M18, M19-EXT, M20, M22, M23, M25, M26,
M28, M29, M30, M31 in full (not skimmed) before writing anything. Traced
the actual code: `pipeline.py:188` (`profile.normalize_for_parsing
(raw_body)`), `normalize.normalize_for_parsing` (collapses U+201C/U+201D/
U+05F4 to U+0022, en/em-dash/maqaf to `-`), `sections.parse_articles`
(article boundaries), `ingest.py:66` (only `parsed_article.body` is
persisted, never `.heading`), `profiles.py`'s `HebrewProfile` (confirmed
every method is a byte-identical passthrough to the frozen module-level
functions), and `il_law_wide_vocabulary.py`'s own documented residual
(`אכרזה זאת`).

---

## Job 1 (C1) -- the denominator, re-derived and reproducible

### Method

Committed script: `backend/tests/certification/c1_denominator.py`.
Never part of `pytest` (same "no test reads the corpus" discipline
`ingest_wiki_corpus_cli.py`'s own docstring states, for the identical
reason). For every one of the 6,133 real `*.wiki` files: read raw UTF-8
(byte-identical to `ingest_wiki_corpus.py`'s own `read_text(encoding=
"utf-8")` -- zero decode errors measured across all 6,133 files first,
matching production exactly, not assumed); split into articles via
`sections.parse_articles` (the exact function `ingest_wiki_law` calls);
normalize each article's **body** (not heading -- see below) via
`normalize.normalize_for_parsing` (the exact function `pipeline.py:188`
calls); scan every `"` character (there is exactly one quote codepoint
left after normalization); classify word-internal (cluster 1's
predicate, Hebrew letter both sides, no intervening whitespace) vs
eligible; pair eligible characters sequentially WITHIN each article
(never across an article boundary).

### A methodology decision I had to make, not inherited: heading vs body

The contract's own denominator table doesn't say whether "every article"
means body only or heading+body. I measured **three** configurations
against the real corpus before picking one:

```
                                          quote chars   word-internal
whole raw file (incl. pre-article-1 metadata)  528,564   58.1%
article HEADING + BODY, normalized             389,351   52.2%
article BODY ONLY, normalized                  276,815   33.1%
```

Only **body-only** reproduces the panel manager's own M31-corrected
figures **exactly** -- not "within tolerance," an exact digit-for-digit
match. This is also the methodologically correct choice independent of
matching the number: `ingest.py:66` persists only `parsed_article.body`
as `SourceSpan.quote_text`; the heading text is normalized/scanned
NOWHERE in the production extraction path. Scanning whole-file text
massively overcounts because of citation-heavy front-matter blocks (a
spot check of `פקודת הפרשנות.wiki`'s own pre-article-1 metadata block
shows dozens of word-internal gershayim in law-citation abbreviations
like `חא"י`/`ע"ר`/`דמ"י`/`תשי"ד` before article 1 even starts) -- text
that never reaches `pipeline.py` at all.

**Named consequence, not buried:** a quote-delimited span living
entirely inside an article's HEADING line (the `אכרזה זאת` residual --
`il_law_wide_vocabulary.py`'s own docstring names this exact case,
unprompted, before I even went looking) is OUTSIDE this denominator by
construction. See "Job 5" below for how this is carried forward.

### Reproduction (exact, not "within 3 spans")

```
files                                6,133
articles (sections.parse_articles)  128,234
raw quote chars (article bodies)    276,815
word-internal (cluster 1)            91,611   (33.1%)
eligible                            185,204
naive eligible/2 estimate           ~92,602
```

This matches M31's own post-QA-cycle-4 normalized re-measurement on
every digit. **The earlier 0.07% delta the contract asks C1 to "explain
or eliminate" (M19-EXT 92,598 vs M23 92,605) was between two RAW-text
measurements, both already superseded by M31's normalization fix -- there
is no residual delta left once both derivations run on production-
normalized, body-only text.** I am not absorbing an unexplained delta;
there genuinely isn't one left to explain at this methodology.

### A more precise span count than the naive estimate -- 91,764, not ~92,602

The naive `eligible / 2` arithmetic silently assumes every article has
an EVEN eligible-quote count. Measured: **1,676 of 128,234 articles
(1.3%) do not.** My script pairs sequentially WITHIN each article (never
letting an odd trailing quote in one article pair with the next
article's first quote) and reports these 1,676 unpaired trailing quotes
explicitly (`unpaired_trailing_quotes` in `c1_summary.json`) rather than
silently manufacturing a cross-article phantom pair. Consequence: the
real, article-bounded candidate-span count is **91,764**, not the naive
~92,602 -- a 0.9% delta, explained, not absorbed. This is the number
`c1_span_population.jsonl` and the C2 backbone test actually use.

### A measured, load-bearing correction candidate to cluster 1 ITSELF

Tracing the 1,676-article anomaly to real corpus text (not assumed) found
a genuine **false positive** in cluster 1's own contract-specified
predicate. `"רכב" ו"דרך"` ("car" AND "road", two real, distinct terms
joined by a bare vav conjunction with no space before the second quote):
the second term's OPENING quote has `prev_char='ו'` and `next_char`
being the first Hebrew letter of the second term -- both sides are
Hebrew letters, so cluster 1's literal predicate classifies it
word-internal, even though it is a genuine term-delimiting quote, not an
abbreviation marker.

**Measured corpus-wide** (`vav_conjunction_false_positive_candidate` in
`c1_summary.json`, diagnostic only, NOT applied to cluster 1's own
bucketing this round): **2,096 of the 91,611 word-internal disposals
(2.3%), across 1,004 files.** Independent confirmation, not just a
plausible story: correcting for this pattern drops the odd-parity-
article count from 1,676 to **282** (an **83% reduction**), and raises
the naive eligible/2 span estimate from ~92,602 to **~93,650** (+1.1%).

I did **not** apply this correction to cluster 1's own bucketing in the
committed script or the manifest -- cluster 1 is the contract's own
stated template, verbatim, and unilaterally rewriting it is a
methodology change for the panel manager to confirm, not something a
Planner substitutes silently. Reported as a NAMED, precisely-measured
candidate refinement (`clusters.is_vav_conjunction_false_positive`,
`clusters.PROPOSED_CLUSTERS["vav_conjunction_word_internal_false_
positive"]`), reproducible by re-running the committed script.

**This is the honest answer to "if my ~92,600 is wrong, say so":** it is
not WRONG -- both independent historical derivations and mine agree
exactly at this methodology -- but it is **provably an undercount by
~1.1%** once the vav-conjunction pattern is accounted for, and I am
reporting that rather than quietly matching the inherited number and
moving on.

### A second, unrelated, load-bearing finding: MediaWiki table markup is 14.2% of the denominator

Sampling the ~16% of spans whose `term_text` contains no Hebrew letter at
all surfaced real values like `'100px'`, `'table-layout: fixed; width:
100%;'`, `'ltr'`. These are **not** foreign-language content -- they are
**MediaWiki table/HTML attribute quotes** (`! width="200px" | ... !!
width="100px" | ...`), using `"` as an attribute delimiter inside table
markup embedded in the corpus's own wiki source. Verified against the
real source of `הודעת מס הכנסה (רשימת יישובים מוטבים לשנת 2024).wiki`.

**Measured, corpus-wide, via a precise, falsifiable predicate**
(`[A-Za-z][A-Za-z-]*=` immediately before the quote -- `align=`/`width=`/
`style=`/`colspan=`/`rowspan=`/`dir=`/`class=`, in that frequency order):
**13,041 of the 91,764 candidate spans (14.2%), across 244 files.** This
is now a REAL, implemented cluster (`clusters.
cluster_wiki_table_markup_attribute`, bucket `proven-not-a-definition`),
not merely proposed -- see "Job 3" below.

**Why this matters beyond its own count:** a certification that
naively treated "16% of spans have no Hebrew letter" as "16% ambiguous/
foreign-language noise" would have missed that the great majority of it
is a SINGLE, precisely mechanical, zero-judgment-required markup
artifact. Measuring the actual character class here (per M-D3/M23's own
lesson, one level deeper) turned a vague worry into a disposed cluster.

### A genuine production precision bug, found as a byproduct of C2's own double-assignment check

15 spans are BOTH `wiki_table_markup_attribute` AND `production_captured`
-- all `term_text='ltr'` bar one. Traced live: `צו המועצות המקומיות
(מועצה מקומית תעשייתית נאות חובב).wiki` article 1 (heading `הגדרות`, a
real definitions-heading article) has `dir="ltr"` HTML markup embedded in
its body; the REAL, unmodified `HebrewProfile.extract_definitions_from_
section` dispatch (reproduced live, this session, via the exact
production call) genuinely produces
`DefinitionCandidate(terms=('ltr','ltr',...), definition_text=
'בשלמותם;', qualifier='>100158_6</span>, 100177, ...')` -- HTML
tag/table-cell fragments swallowed as a "qualifier," with the markup
attribute value `'ltr'` captured as if it were a defined TERM. This is a
**real false-positive capture already shipping in production today**,
found purely as a byproduct of building a mechanical, whole-population
classifier -- exactly the kind of thing D-CERT's inverted method exists
to surface and a forward variant-hunt would never stumble onto. **Not
fixed this round** (zero production code, per the hard constraint) --
named precisely (file, article, root cause) for C4's fix loop or a direct
escalation, whichever the panel manager prefers.

### Wall time, determinism

`c1_denominator.py`: ~36-47s per full run (measured twice, consistent
output both times -- deterministic, no randomness anywhere in this
script). `c1_complement_scout.py`: ~3-4s.

---

## Job 2 (C1's bounded scout item, contract amendment 1) -- probing the complement

### Role of the trigger vocabulary here, stated explicitly per the contract's own instruction

In this script (`backend/tests/certification/c1_complement_scout.py`),
the known trigger/marker vocabulary (`il_law_wide_vocabulary.
law_wide_preamble_phrases()` plus every `ScopeTriggerRule` module's own
`_TRIGGER_RE` words, gathered by reading each file directly) plays the
role of a **PROBE testing whether the quoted-span denominator's own
boundary is in the right place** -- not the role of a denominator. M18
governs the denominator (C1 stays signal-agnostic); it does not forbid
using known vocabulary to test the denominator's own scope, per the
contract's own explicit carve-out.

### Method

For every line inside every article's normalized body with **zero**
quote characters: flag it if it (a) starts with `:-`/`::-` (the
list-shape entry-start grammar's own shape, `entry_marker`), or (b)
contains a known trigger phrase AND a `-`/`:` (`trigger_word`).
Deterministic seeded sample (seed `20260805`, committed) hand-judged by
me.

### Measured result -- NOT near-zero; the assumption is FALSE

```
total complement hits (zero-quote definitional-marker lines): 31,301
  trigger_word: 30,970   (dominated by bare "להלן" -- 12,136 of these,
                          mostly ordinary cross-reference prose, "as
                          detailed below", not definitional -- a real
                          weakness of this probe's precision, named
                          honestly, not hidden)
  entry_marker:    331
```

**Sample 1** (n=120/31,301, seed 20260805, `c1_complement_scout_sample.
jsonl`, hand-read in full): 37 lines are the `(TRIGGER - X)` unquoted
parenthetical-apposition shape. Cross-checked against the REAL
production dispatch (not eyeballed): **33/37 (89%) are ALREADY
captured** today -- `extract_adhoc_definitions` (frozen, `להלן` only) and
`il_adhoc_scope_triggers.py` (5 more trigger words, shipped this
program) never required quotes in the first place; they strip them if
present. 4/37 measured missed, root cause not fully traced this round
(honest gap).

**Sample 2** (the full `entry_marker` population, n=331, NOT sampled --
small enough to fully enumerate): classified by shape --

```
math/formula-notation ("<math>D</math> = ...", single-letter variables)   177
genuine natural-language unquoted term definitions                        22
other / not yet characterized                                            132
```

The 22 are REAL: `שנה - תקופה של 12 חדשים רצופים` ("year" - a period of
12 consecutive months), `טונה - טונה מטרית של 1000 קילוגרם` ("tonne" -
...), `רשיון פרטי/מיוחד/סיור/קו - ...` (four license-type definitions),
`השר - שרי האוצר והפיתוח`, etc. -- across 4 files: `חוק זכיון ים המלח`
(13), `תקנות התעבורה` art.386 (5), `פקודת הפרשנות` (2), `תקנות מס הכנסה
(כללים לאישור ולניהול קופות גמל)` (2). **Verified live, not assumed**:
`חוק זכיון ים המלח` article 1 (heading `הגדרות`,
`is_definitions_heading=True`) -- the real, unmodified
`extract_definitions_from_section` call returns **0 candidates** for
this article; all 13 real terms are 100% uncaptured, because
`extract._QUOTE_RE`-based term parsing cannot see an unquoted header at
all. This is an OLDER Mandate/early-state-era drafting convention (this
specific law predates the gershayim-quoting convention this whole
program's grammar assumes).

**Connection to the parent sprint's own residual:** `פקודת הפרשנות`
appears in BOTH this scout's hit list and M31's own residual (6) ("29
never-reached entry lines incl. ... פקודת הפרשנות art.1"). This scout's
finding likely explains (at least in part) why that law's definitions
list is never reached -- not investigated further this round (time-
boxed), named as a lead for whoever closes that residual.

### Verdict, per the contract's own explicit branching

**Not near-zero. "Unquoted definitional constructions" is OPENED as a
named cluster** (`clusters.PROPOSED_CLUSTERS["unquoted_definitional_
constructions"]`), with its two measured sub-populations kept distinct
rather than blended into one number:
- Sub-population A (parenthetical apposition): mostly ALREADY captured
  (89% sampled); a small residual, not fully root-caused.
- Sub-population B (unquoted list-entry headers): genuinely, precisely
  measured at 22 real definitions / 4 files, currently 100% uncaptured
  for the largest case -- a real, NEW, previously-unnamed buildable class
  for a future C4 cycle.

### Honest limitation of this probe, named rather than hidden

The `trigger_word` category's 30,970 hits are dominated by ordinary,
non-definitional prose ("as detailed below", cross-references) -- a
precision weakness of using bare trigger-word presence as a probe
signal. The entry_marker category (331, no quote at all on a list-entry
line) is a MUCH cleaner signal and is where the real finding came from.
A future iteration of this probe should narrow `trigger_word` to require
the SAME "-" position discipline the real quote-first grammars use
(dash immediately follows the trigger, not merely present anywhere in
the line) rather than the loose "contains a dash somewhere" check this
round used.

---

## Job 3 -- the cluster model

### Two populations, two cluster levels -- an ambiguity in the contract, resolved and flagged

The contract uses "candidate row" at two granularities that cannot both
be literally true simultaneously: cluster 1's own disposal count (33.1%
of 276,815 raw quote CHARACTERS) and C2's "~92,600-row population" (a
SPAN count). **Resolution adopted** (`clusters.py`'s own module
docstring states this in full): **Level 0** (character level, cluster 1
only) is total and disjoint BY CONSTRUCTION -- every quote character is
Hebrew-letter-flanked or not, no third option -- and is how the Level-1
population gets CONSTRUCTED (word-internal characters excluded before
pairing), not itself a partition of it. **Level 1** (span level,
clusters 2+) is the ~91,764-row population C2's backbone test actually
iterates, matching the contract's literal "~92,600-row" wording. **Flagged
explicitly for the panel manager to confirm or correct** -- this is a
Planner judgment call on an underspecified point, not asserted as
obviously right.

### Clusters implemented this round (real, executable, run over the full 91,764-row population)

| cluster_id | bucket | count | % | predicate (see `clusters.py` for the full function) |
|---|---|---:|---:|---|
| `wiki_table_markup_attribute` | proven-not-a-definition | 13,041 | 14.2% | quote preceded by `ATTR=` (align/width/style/colspan/rowspan/dir/class) |
| `production_captured` | captured | 49,640 | 54.1% | `term_text` in the real `HebrewProfile` dispatch's own captured terms for its article |
| `interpretation_laws_never_reached` | director-named residual | 131 | 0.1% | exact (file, article) match, uncaptured -- M31 residual (6) |
| **unassigned** | -- | 28,967 | 31.6% | (no predicate matches yet -- expected, honest RED) |
| **double-assigned** | -- | 15 | 0.02% | both markup AND captured -- the real `'ltr'` over-capture bug above |

(Cluster 1, `word_internal_quote`, disposes 91,611 CHARACTERS at Level 0,
separately from this Level-1 table -- see above.)

### Clusters PROPOSED, not implemented this round (Job 3's own explicit instruction: "do not attempt all 20-40")

Six more, each named with its seed residual, a predicate SKETCH, and a
bucket, in `clusters.PROPOSED_CLUSTERS` (read the file for full text,
not reproduced here to keep this log from re-deriving 400 lines of
contract prose):

1. `vav_conjunction_word_internal_false_positive` -- the cluster-1
   refinement candidate above (a correction, not a new residual).
2. `definitions_heading_uncaptured_numbered_subitems` -- parent residual
   (1), 44 articles / ~202 terms.
3. `class_c_local_scope_under_claims` -- parent residual (2), 15/44;
   noted as NOT expressible as a pure span-text predicate (it is a
   containment-side check).
4. `cross_path_separator_divergence_and_position_zero_anchor` -- parent
   residual (3).
5. `siman_chelek_captured_but_uncontained` -- parent residual (4); noted
   as NOT a span predicate at all (these spans already sit inside
   `production_captured`) -- tracked by the existing, frozen,
   still-RED containment test instead (see "Job 5").
6. `akraza_zot_heading_embedded` -- parent residual (5); noted as OUTSIDE
   this denominator's own population by construction (heading text) --
   an open question for the panel manager, not decided here.
7. `unquoted_definitional_constructions` -- the scout's own finding
   (Job 2), with its measured sub-population breakdown.

### Why the coarser, trivially-exhaustive alternative was rejected

An earlier draft of this module considered a 4-cluster design
(`production_captured` / `is_definitions_heading_article and not
captured` / `not is_definitions_heading_article and not captured` /
done) that would make C2 GREEN immediately by construction. Rejected:
it would launder six textually-distinct, previously-NAMED residual
classes into one undifferentiated boolean bucket, which is exactly the
"narrative, not a cluster" failure mode C2's own text warns against. The
honest, if less tidy, choice is a genuinely incomplete cluster set that
is RED for a stated, itemized reason.

---

## Job 4 (C2) -- the backbone test, authored RED

`backend/tests/integration/
test_definition_links_il_certification_c2_span_exhaustiveness.py` (not
`_live.py` -- it runs no real pipeline call, it classifies a committed
manifest; the `_live` suffix in this suite's convention denotes a real
pipeline/corpus-fixture run, which this deliberately is not, to keep
"no test reads the corpus" true by construction rather than by
discipline).

**Three tests:**
1. `test_manifest_is_the_real_whole_population_not_a_sample` -- pins the
   manifest at exactly 91,764 rows (a deliberate, deliberately-brittle
   pin -- C5 wants a stale/truncated manifest to fail LOUDLY here, not
   silently pass a smaller population below). PASSES.
2. `test_c2_every_span_carries_exactly_one_cluster_id` -- THE backbone
   test. Runs every `clusters.SPAN_CLUSTERS` predicate over all 91,764
   rows. **FAILS**, reporting BOTH failure modes separately (not
   blended): `28,967/91,764 spans are UNASSIGNED` and
   `15/91,764 spans are DOUBLE-ASSIGNED` (with a sample of each, and the
   double-assignment's own root cause documented in the test's own
   docstring -- the real `'ltr'` over-capture bug above). **This is the
   expected RED**, for the stated reason: the cluster set is
   deliberately incomplete this round (Job 3), and one small, genuine
   precision bug was found rather than hidden.
3. `test_c2_cluster_1_word_internal_quote_is_total_and_boolean` --
   Level-0's own falsifiability check (see "two populations" above):
   proves cluster 1 cannot return anything but a definite `bool` for
   any character pair actually observed in the vendored manifest plus a
   set of structural edge cases. PASSES.

**Full-suite confirmation, my own run:**

```
backend/.venv/bin/pytest backend/tests -q
-> 3 failed, 845 passed, 18 warnings
```

845 = 843 (baseline, unchanged) + 2 new passing (tests 1 and 3 above).
3 failed = 2 pre-existing core-blocked containment REDs (untouched,
still RED, confirmed below) + 1 new RED (test 2, the backbone test).
**Matches the sprint's expected end state exactly.**

**Confirmed the 2 pre-existing REDs are unchanged and for the same
reason** (not merely "still red" -- re-read the failure tails):
`test_besiman_zeh_scoped_definition_containment_holds_in_both_
directions_live` and `test_bechelek_zeh_...` both still fail on `assert
any("Article 9"/"Article 73" in p for p in uses_props)` with `got []` --
byte-identical failure shape to the parent sprint's own last recorded
run. `git diff HEAD -- backend/tests/integration/test_definition_links_
il_siman_chelek_containment_live.py` is empty -- this file was read, not
edited.

---

## Job 5 -- seeding the cluster set with the parent's six inherited residuals

| # | parent residual | this round's disposition |
|---|---|---|
| 1 | 44 articles / ~202 terms, class-(d) numbered sub-items, zero capture | Named, PROPOSED cluster `definitions_heading_uncaptured_numbered_subitems` (not implemented -- needs a real structural detector). Falls inside this round's 28,967 unassigned today. |
| 2 | 15/44 class-C under-claims | Named, PROPOSED cluster `class_c_local_scope_under_claims`. Noted explicitly: NOT expressible as a span-text predicate (it's a containment-side check on ALREADY-captured definitions) -- would need this manifest's row shape extended with mention data, out of scope this round. |
| 3 | ~67-254 cross-path separator divergences + `parse_entry`'s position-0 anchor | Named, PROPOSED cluster `cross_path_separator_divergence_and_position_zero_anchor`. Falls inside 28,967 unassigned today. |
| 4 | 2 core-blocked containment REDs (M20/M27) | Named, PROPOSED cluster `siman_chelek_captured_but_uncontained`, explicitly marked NOT a span predicate -- these spans are ALREADY inside `production_captured` (capture shipped; only containment is blocked). Tracked by the existing, frozen, confirmed-still-RED `test_definition_links_il_siman_chelek_containment_live.py`, per Job 4 above. Closing condition unchanged from the parent contract's amendment 2 (core-2 G9 merge + our own `scope_value` fix, M27) -- not re-litigated, not re-verified this round (out of scope: nothing in core-2's G9 status changed during this Planner session). |
| 5 | `אכרזה זאת`, 1 file | Named, PROPOSED cluster `akraza_zot_heading_embedded`, explicitly marked OUTSIDE this denominator's own population (heading text, never scanned -- see Job 1's "heading vs body" methodology decision). Open question raised for the panel manager: does C1's population need a documented, additive heading-scan extension, or does this stay a permanent named exception? Not decided here. |
| 6 | 29 never-reached entry lines incl. both Interpretation Laws | **Precisely implemented, not merely proposed**: cluster `interpretation_laws_never_reached` (131 spans, exact file+article match, `production_captured=False` required). Additionally: Job 2's complement scout independently found `פקודת הפרשנות` again, via its OWN unquoted-definitions finding -- a plausible (not proven) partial root-cause lead for why this residual's lines are never reached, named for whoever closes it next. |

---

## Suite, lint, boundaries -- final verification

```
backend/.venv/bin/pytest backend/tests -q
-> 3 failed, 845 passed, 18 warnings

bash scripts/contract_lint.sh 2026-08-05-defs-il-certification
-> PASS 302

git diff --name-status HEAD -- backend/app
-> (empty)

git diff --name-status HEAD -- backend/tests/integration/test_definition_links_il_siman_chelek_containment_live.py
-> (empty -- read only, never edited)
```

Zero production code. Zero existing tests edited (all new files -- see
"Files" below). The 2 pre-existing containment REDs are unchanged and
confirmed RED for the same reason as before this session.

## Files (all new, nothing modified)

- `backend/tests/certification/c1_denominator.py` -- C1's committed
  denominator + span-manifest generator script.
- `backend/tests/certification/clusters.py` -- the cluster model:
  predicates, buckets, `SPAN_CLUSTERS` registry, `PROPOSED_CLUSTERS`.
- `backend/tests/certification/c1_complement_scout.py` -- Job 2's
  bounded scout script.
- `backend/tests/integration/
  test_definition_links_il_certification_c2_span_exhaustiveness.py` --
  C2's backbone test (3 tests, 1 deliberately RED).
- `backend/tests/fixtures/certification/c1_summary.json` -- committed
  aggregate denominator report (small, ~1KB).
- `backend/tests/fixtures/certification/c1_span_population.jsonl` --
  committed, vendored span-level manifest (91,764 rows, ~32MB -- the
  full, whole-corpus population C2 iterates; large because the sprint's
  own standard is "no sampling, full population," not because of
  padding -- see schema in `c1_denominator.py`'s own docstring).
- `backend/tests/fixtures/certification/c1_complement_scout_sample.
  jsonl` -- the hand-judged n=120 seeded sample (60KB).
- `backend/tests/fixtures/certification/c1_complement_scout_summary.
  json` -- small aggregate scout report.
- This log file.

**Deliberately NOT committed:** `c1_complement_scout_hits.jsonl` (the
FULL 31,301-row hit list, ~15MB) -- nothing reads it at test time (only
the seeded sample above is a vendored, test-relevant artifact), and it
is trivially reproducible by re-running the committed, deterministic
script against the read-only corpus. Keeping it out of git avoids
carrying a large, test-unread file for no reproducibility benefit; C5's
"re-run and diff" still holds because the SCRIPT is committed and
deterministic.

---

## Honest gaps (all of them, not a curated subset)

1. **The Level-0/Level-1 population-granularity resolution (see Job 3)
   is a Planner judgment call, not confirmed by the panel manager.** If
   wrong, the C2 backbone test's own row count/shape would need to
   change, not just its cluster set.
2. **The vav-conjunction false-positive candidate (2,096 chars, 2.3% of
   cluster 1's disposals) is reported, not applied.** If confirmed, it
   changes cluster 1's own predicate, the denominator's own headline
   count (~92,602 -> ~93,650, +1.1%), and invalidates the currently-
   pinned 91,764-row manifest -- a re-run and re-pin, not a small patch.
3. **The complement scout's `trigger_word` category (30,970 hits) is
   dominated by non-definitional noise** (bare "להלן" cross-references);
   the useful signal came from the much smaller, cleaner `entry_marker`
   category. A future iteration should tighten the trigger-word marker
   shape (require the dash to immediately follow the trigger, not merely
   be present anywhere in the line).
4. **4/37 sampled parenthetical-apposition unquoted hits are measured
   missed but not root-caused** (Job 2) -- flagged, not chased, given
   this scout is explicitly bounded.
5. **The "other" 132/331 entry_marker lines are not characterized** --
   time-boxed; likely a mix of citation labels, table-row data (e.g. the
   `גוש N - ...` land-parcel rows), and residual noise, not examined
   further this round.
6. **`production_captured` is a STRING-membership check, not offset
   identity** (documented in `clusters.py`'s own docstring for
   `cluster_production_captured`) -- a term captured from a DIFFERENT
   entry in the same article, textually identical to an unrelated span,
   is indistinguishable from this span being the captured one. Named as
   a known limitation of this round's classifier, not fixed.
7. **Did not re-verify core-2's G9 status** (parent residual 4's closing
   condition) -- nothing in this Planner session touched or re-checked
   that dependency; carried forward exactly as the parent contract left
   it.
8. **The 300-line style gate was not applied to anything I wrote**
   (`c1_denominator.py` 371 lines, `clusters.py` 324 lines) -- per the
   sprint's own hard constraint ("production files under 300 lines (you
   write none); test modules are exempt"), and since everything here
   lives outside `backend/app`, I read the gate as not applying at all,
   consistent with the separator Planner's own M29-accepted reasoning
   for test files. Flagging the reasoning rather than silently assuming.
9. **Did not attempt C3 (measured error rate per bucket) or C4 (the fix
   loop) this round** -- out of scope per the brief ("planning only this
   round"; C3/C4 apply once a Developer is committed against a
   panel-manager-reviewed cluster shape).

## What I would want the panel manager to explicitly rule on before a Developer spawns

1. Confirm or correct the Level-0/Level-1 population resolution (Job 3).
2. Decide whether the vav-conjunction correction (Job 1) should be
   applied to cluster 1 itself, becoming a contract amendment, or stays
   a separately-tracked refinement cluster.
3. Decide whether the `אכרזה זאת` heading-scope gap (Job 5, item 5)
   should widen C1's population to include heading text, or stay a
   permanent named exception.
4. Decide the routing for the `'ltr'` production over-capture bug (Job
   1/4) -- C4's fix loop, or a direct escalation outside this sprint.

---

## 2026-08-05 -- Round 2 -- Planner (same session), responding to ruling M33

Panel manager merged Round 1 (`aa62dda`) and independently re-verified
both load-bearing claims before ruling (the vav-conjunction FP on
`"רכב" ו"דרך"`, byte-identical to my own probe; the `'ltr'` bug's true
size, 19 candidates / 8 spurious, one article). Five rulings (M33), in
priority order: (1) two-level model CONFIRMED; (2) apply the vav
correction, re-run, re-pin, own unit test; (3) headings get a separately-
measured population; (4) author the `'ltr'` RED first; (5) the manager's
own hygiene reversal (32MB population stays committed) -- no action
needed from me, already resolved in my favor.

Continued in the SAME worktree/branch (`defs-il-cert-plan1`,
`claude/defs-il-certification`), on top of my own `8fde401` -- did not
merge the panel manager's `claude/defs-il` tip into this branch (M14:
the panel manager merges, not me); read the amended contract and M33 via
`git show` against the shared object database instead, never altering
my own branch's history to do so.

### Ruling 2 -- vav-conjunction correction APPLIED

`clusters.is_word_internal_quote` now takes a third character of context
(`char_before_prev`) and excludes the standalone-vav-conjunction case
directly, per the ruling's own text. New dedicated unit test:
`backend/tests/unit/test_certification_clusters_word_internal_quote.py`
(6 tests) -- pins the `"רכב" ו"דרך"` case byte-for-byte (harvests the
real quote positions from the string, asserts they match the claimed
`(prev, next, before)` tuple before testing the predicate, so a future
edit to the test string cannot silently drift), a start-of-text variant,
a NEGATIVE control (a vav that genuinely IS part of a longer word must
stay word-internal -- the ruling's own "cuts both ways" concern), the
unaffected original case, the base Hebrew-letter gate, and totality.

**Re-ran `c1_denominator.py` (not a patch) and the delta is explained,
not absorbed, per the ruling's own instruction:**

```
                        Round 1 (pre-fix)   Round 2 (post-fix)   delta
word-internal (cl. 1)        91,611 (33.1%)   89,515 (32.3%)    -2,096
eligible                       185,204          187,300         +2,096
unpaired_trailing_quotes         1,676              282           -83%
paired candidate spans          91,764           93,509         +1,745
```

The span-count delta (+1,745) is LARGER than the raw character
correction (2,096 reclassified chars would naively predict ~+1,048
spans, half of 2,096) -- traced, not left as a discrepancy: fixing the
predicate doesn't just add the 2,096 directly-corrected characters as
new eligible spans, it also RE-ALIGNS the open/close PARITY of every
downstream eligible quote in the same article for the rest of that
article's sequential pairing. One mid-article misclassification was
silently shifting which quotes played "opener" vs "closer" for
everything after it. This is also the most direct evidence for WHY the
fix mattered beyond its own raw count:

```
                        Round 1   Round 2   delta
production_captured      49,640    58,750   +9,110  (54.1% -> 62.8%)
wiki_table_markup_attr   13,041    13,061      +20  (unaffected, ~flat)
interp._laws_never_reached  131       134       +3
unassigned                28,967    21,579  -7,388  (31.6% -> 23.1%)
double_assigned               15        15        0  (the 'ltr' bug,
                                                        unrelated to vav)
```

`production_captured` jumped nearly +9,000 -- almost 4x the 2,096 raw
correction -- because correct pairing recovered many DOWNSTREAM spans in
affected articles that were previously misaligned, not just the vav
quotes themselves. Re-pinned `c1_span_population.sha256` in the same
commit as the regenerated manifest, replacing the "STALE" marker the
panel manager's own file carried (`git show` read only, never merged
into my branch -- I authored my own copy with fresh content matching the
same convention).

### Ruling 3 -- heading population, separately measured

New script: `backend/tests/certification/c1_heading_denominator.py`.
Scans `Article.heading` text RAW (not normalized -- confirmed by
exhaustive grep that heading text never reaches `normalize_for_parsing`
anywhere in production, unlike body text), checking all four quote
codepoints individually (re-applying M23's own lesson fresh, since raw
heading text cannot be assumed single-codepoint the way normalized body
text can). Reuses the SAME refined `is_word_internal_quote` (codepoint-
agnostic by construction -- it only inspects neighbors).

```
raw quote chars in headings   112,536
  by codepoint: U+0022 105,536 / U+05F4 6,943 / U+201C 0 / U+201D 57
word-internal                 111,799  (99.3% -- headings are almost
                                         entirely abbreviation noise,
                                         e.g. "(תיקון: תש"ף)")
eligible                          737
paired candidate spans            353
```

New cluster (`clusters.HEADING_CLUSTERS`): `heading_quoted_span_
unreached` -- matches ALL 353 rows, verified `production_captured=False`
by the SAME exhaustive-grep method Round 1 used for the body population
(`art.heading` is used ONLY as a boolean match target for `is_
definitions_heading`, never scanned for content, anywhere in
`backend/app/definition_links`). New test: `test_definition_links_il_
certification_c2_heading_span_exhaustiveness.py` -- **GREEN**, and its
own docstring states explicitly why a green mechanical test here is not
a weaker standard than the RED body test (a uniform, verified fact, not
underinvestigated differentiation).

**A correction to ruling M33-3's own framing, found while building
this** (verified against the real file, not assumed, before reporting):
the panel manager's ruling named this heading population "the honest
home for residual (5) `אכרזה זאת`". Checked directly -- it is not. The
real marker line is `@ (תיקון: תשפ"ג) : באכרזה זאת, "..." - ...`, which
has NO number between `@` and `(תיקון`, so it matches NEITHER
`sections._ARTICLE_MARKER_RE` NOR `_BARE_ARTICLE_MARKER_RE`.
`sections.parse_articles` on the real file returns **ZERO Article
objects** -- there is no `.heading` string for this population to
contain in the first place. Measured the true scope of this gap rather
than leaving it as one anecdote: **21,498 `@`-prefixed lines / 1,646
files** match neither marker regex corpus-wide, and **121 whole files
(2.0% of the corpus) end up with ZERO articles** as a result -- a
`sections.py` (frozen) gap, distinct from the already-fixed bare-`@`
case (P-E3/M8(a)), closer in shape to M20's סימן/חלק breadcrumb blocker
than to anything a rule-module-only file can address. New PROPOSED
cluster: `numberless_at_marker_zero_article_files`. New test in the
heading-population file pins the correction itself
(`test_akraza_zot_file_is_confirmed_absent_from_this_population`) so a
future fix to `sections.py` is expected to flip it, not silently leave
it green for the wrong reason.

### Ruling 4 -- the `'ltr'` over-capture RED, authored

New fixture (real, byte-verified before AND after vendoring): `צו
המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)_art1_excerpt.wiki`
(article 1 in full, 44 lines). New test file: `test_definition_links_il_
certification_ltr_markup_overcapture_live.py`, using the real pipeline
(`ingest_wiki_law` + `run_definition_linking`), matching this suite's
`_live.py` convention.

**Root cause traced precisely** (not merely "markup confuses the
parser" -- read in full in the test file's own docstring): the article
defines `"תחום המועצה"` as ONE multi-line `:-` entry whose continuation
lines are `::-`-prefixed land-block rows; baseline correctly treats the
whole thing as one block. But a registered `EntrySplitterRule` (the
D-1b `::-`-list-shape class) ALSO treats each `::-` line as its own
independent block, and `extract_definitions_from_section` UNIONS
baseline's blocks with every splitter's blocks (by design, for zero-miss
recall). Most per-line re-parses correctly produce nothing (no quoted
span in a plain `גוש 39774 - ...` line). But 8 lines contain `<span
dir="ltr">NNNNNN_N</span>` markup (forcing LTR digit rendering inside
RTL text -- a typographic device, unrelated to legal drafting), and
`dir="ltr"` itself is a genuine `"..."`-quoted span `extract._QUOTE_RE`
cannot distinguish from a legal-drafting quote. Two tests: the RED itself
(zero `'ltr'`-bearing `Definition` rows expected; today produces 2,
correctly deduped from the 8 originally-spurious candidates by
`pipeline.py`'s own `(article, sorted(terms))` idempotency key -- 7
single-`'ltr'` candidates collapse to 1 row, plus the 1 seven-`'ltr'`-
tuple row = 2 distinct rows, exactly reconciling with the panel
manager's own "8 spurious" candidate-level count); and a sanity control
(all 11 genuine terms, including `"תחום המועצה"`'s own definition_text,
survive) -- confirmed GREEN today, so it stays green through whatever
fix a Developer builds, not a second RED.

**A factual correction to my OWN Round 1 test docstring, caught while
writing this file:** `test_definition_links_il_certification_c2_span_
exhaustiveness.py`'s own module docstring named the WRONG law for this
bug (`חוק זכיון ים המלח` -- an unrelated law, actually the complement
scout's own unquoted-definitions finding). Fixed in place this round;
the panel manager's own M33 text had the correct law throughout, so only
my own artifact needed the correction.

### Priority 4 -- growing the cluster set

Measured the composition of the remaining 21,579 unassigned spans before
adding anything further: 81.6% (17,614) sit in ORDINARY articles, only
18.4% (3,970) in definitions-heading ones -- the opposite of what I
expected going in, and a useful correction to my own prior assumption
that class-(d)'s numbered-subitem shape would dominate the remainder.

Found and closed one small, precise gap while investigating: MediaWiki's
own `{{=}}` template-escape for a literal `=` inside a style attribute
(`<div style{{=}}"padding: ...">`) is the SAME `wiki_table_markup_
attribute` phenomenon Round 1 already named, just a different literal
token before the quote. Measured before widening (5 quote chars / 1
file) -- folded into the existing regex rather than a near-duplicate
cluster.

**Honest stop point, stated plainly rather than padded with a weak
cluster to look more complete:** a random sample of 25 unassigned
"ordinary article" spans shows a genuinely MIXED population -- plausible
short real terms (~60% of the sample, by eye), self-citations of a law's
own title in quotes (~12%), spans that are pairing artifacts of THIS
denominator's own simple sequential-pairing construction rather than
real corpus phenomena at all (~24%, e.g. a span whose text is a whole
clause fragment starting mid-sentence), and residual markup (~4%). This
is an INFORMAL, eye-classified estimate on a small sample -- explicitly
NOT a C3-grade hand-verified measurement, and not proposed as one. No
new cluster was added for any of these without the same falsifiable-
predicate discipline Round 1 held to; inventing a coarse "ordinary
article, plausible-length term" cluster now would repeat exactly the
laundering the panel manager praised Round 1 for refusing. Handing this
off as a measured STARTING POINT for whoever continues C4's cluster
growth, not as a finished characterization.

### Suite, lint, boundaries -- Round 2 final verification

```
backend/.venv/bin/pytest backend/tests -q
-> 4 failed, 855 passed, 18 warnings
```

855 = 845 (Round 1 end state) + 6 (new word-internal-quote unit tests)
+ 3 (new heading-population tests, all green) + 1 (the `'ltr'` sanity
control, green). 4 failed = 3 (Round 1: C2 body backbone RED + 2
pre-existing core-blocked containment REDs, all still red for the same
reasons, re-verified) + 1 new (`'ltr'` RED). `git diff --name-status
HEAD -- backend/app` empty throughout. `git diff --name-status HEAD --
backend/tests/integration/test_definition_links_il_siman_chelek_
containment_live.py` empty -- still read-only, still untouched.

### Files -- Round 2 (modified + new)

Modified: `c1_denominator.py` (refined predicate call sites, applied-not-
diagnostic reporting, widened markup regex), `clusters.py` (refined
predicate, HEADING_CLUSTERS, corrected `akraza_zot_heading_embedded`
entry, new `numberless_at_marker_zero_article_files` entry),
`c1_span_population.jsonl` + `c1_summary.json` (regenerated),
`test_definition_links_il_certification_c2_span_exhaustiveness.py` (pin
93,509, corrected the wrong-law docstring bug, ruling references).

New: `c1_heading_denominator.py`, `c1_heading_span_population.jsonl` +
`.sha256` + `c1_heading_summary.json`, `test_definition_links_il_
certification_c2_heading_span_exhaustiveness.py`, `test_certification_
clusters_word_internal_quote.py`, `test_definition_links_il_
certification_ltr_markup_overcapture_live.py`, its fixture (`צו
המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)_art1_excerpt.wiki`),
`c1_span_population.sha256`.

### Honest gaps -- Round 2

1. The 282 residual odd-parity articles (post-vav-fix) are not further
   root-caused -- carried forward exactly as Round 1 left them.
2. The "other" 132/331 entry_marker complement-scout lines are still not
   characterized (Round 1's own gap, untouched this round).
3. The unassigned-population characterization above (60/12/24/4%) is
   explicitly informal and sample-size-small (n=25) -- a lead, not a
   measurement.
4. Did not attempt `class_c_local_scope_under_claims` or `cross_path_
   separator_divergence_and_position_zero_anchor` as real clusters --
   both need containment/mention-level data this manifest's row shape
   does not carry, named as PROPOSED with that limitation stated
   already in Round 1, unchanged this round.
5. Did not re-verify core-2's G9 status (parent residual 4) -- still out
   of scope for this Planner's own session.
6. The `'ltr'` RED test's own root-cause trace (the EntrySplitterRule
   union interacting with embedded markup) is diagnostic, not a fix
   proposal -- deliberately, per M33-4's own instruction that a Developer
   decides the mechanism.
