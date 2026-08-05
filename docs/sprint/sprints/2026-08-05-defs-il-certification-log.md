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

## 2026-08-05 — M33: certification Planner ACCEPTED and merged; five rulings, one of which reverses a ruling I made an hour earlier

### Boundaries (verified BY ME)

`git diff --name-status origin/claude/defs-il...HEAD -- backend/app` →
**empty**. Nine additions, nothing edited; containment test untouched
(last commit on it remains `bc54e1a`). Suite: **`3 failed, 845 passed`**
— 843 baseline unchanged, +2 new passing, +1 new RED. Lint PASS 302.
Good discipline noted: the 15MB complement-scout hit list was
deliberately NOT committed (nothing reads it at test time, deterministic
to regenerate) while the 32MB span population WAS — that distinction
turns out to be exactly right, see ruling 5.

### Both load-bearing claims verified BY ME, not accepted on report

**The vav-conjunction false positive is REAL, and it is MY error.** Direct
probe of the contract's own cluster-1 predicate on `"רכב" ו"דרך"`:

```
idx 7: quote  prev='ו'  next='ד'  word_internal=True   <-- WRONG
```

That quote is the OPENING delimiter of the second term. Two real terms
joined by a bare conjunction vav defeat the predicate I wrote into the
signed-off contract. Measured 2,096/91,611 disposals (2.3%), 1,004 files.

**The `'ltr'` over-capture is REAL and worse than reported.** Ran the real
`HebrewProfile` dispatch on `צו המועצות המקומיות (מועצה מקומית תעשייתית
נאות חובב)` art.1 (heading `הגדרות`): **19 candidates, 8 of them
spurious**, including one `DefinitionCandidate` carrying **seven** `'ltr'`
terms:

```
('ltr','ltr','ltr','ltr','ltr','ltr','ltr') | 'בשלמותם;'
('ltr',)                                    | 'חלק מחלקה 1 כמסומן במפה;'   (x6 more)
```

`ltr` is an HTML `dir` attribute value. **This is the program's FIRST
over-capture defect** — every prior finding across every cycle was a
recall gap. In a legal product a spurious definition is strictly worse
than a missed one: it manufactures false `USES_DEFINITION` assertions.
It was found by nothing but whole-population mechanical classification,
which is the single best argument for D-CERT this program has produced.

### RULINGS

**Ruling 1 — the two-level population model: CONFIRMED.** The contract
used "candidate row" at two irreconcilable granularities and that
ambiguity was mine. **Level 0 = characters** (cluster 1 only, exhaustive
by construction); **Level 1 = spans** (clusters 2+, what C2 asserts
over). C2's exhaustiveness/disjointness are asserted at Level 1. Contract
amended.

**Ruling 2 — apply the vav-conjunction correction; re-run and re-pin.**
Not a patch: the manifest must be regenerated and the checksum re-pinned,
and the refined predicate must carry **its own committed unit test
pinning the `ו"` case**. Rationale: cluster 1 is the contract's stated
falsifiable template, and a template that is measurably 2.3% false is
worse than none. The 83% collapse in the odd-eligible-quote diagnostic
(1,676 → 282) is independent evidence the correction is right rather than
merely different. Expect the naive span estimate to move ~92,602 →
~93,650 and the bounded count off 91,764; **that delta is explained, not
absorbed**, which is what C1 demands.

**Ruling 3 — denominator stays BODY-only; headings get their OWN measured
population.** Body-only is the configuration that reproduces the
M31-corrected figures digit-for-digit, so it stays primary. But excluding
headings because "the dispatch path differs" is **precisely** the
signal-dependence I outlawed for `הגדרות`-headed articles in this
contract's own mandate — I came within one ruling of repeating my own
named error. Headings therefore get a separately-measured population with
their own clusters. This is also the honest home for residual (5)
`אכרזה זאת` and for the class-C heading findings.

**Ruling 4 — the `'ltr'` over-capture goes FIRST in C4's fix loop.**
Precision defects outrank recall gaps in a legal product. It is
mechanically bounded and needs a Planner-authored RED before any fix
(red-before-green). Note for whoever builds it: the 15 double-assigned
spans understate it — one article alone yields 8 spurious candidates.

**Ruling 5 — I was WRONG, within the hour, and reversed myself.** I first
ruled the 32MB `c1_span_population.jsonl` should not be committed,
replacing it with a deterministic script plus a SHA-256 pin on
repo-hygiene grounds. **That ruling was wrong and I reversed it.** The C2
test reads that manifest **specifically so it never reads the corpus** —
the program's own standing constraint. My hygiene ruling would have made
the test pass locally (the file still existed on disk, merely untracked)
and fail on a clean checkout, which is the worst possible failure mode:
green where it is written, broken where it is verified. I caught it only
because I checked the test's actual file dependency before finalizing.
**The population stays committed.** The checksum file is retained as a
genuine C5 integrity pin alongside it, and now documents this reversal in
its own text so the next reader does not re-litigate it.

Recording this at length because the reversal is more instructive than
the original ruling: I made a plausible-sounding infrastructure call
outside my verified knowledge, and the only thing that caught it was
running the check before committing to the position.

### What the Planner did that I want repeated

- **Measured the heading-vs-body scope question against three
  configurations instead of assuming one**, and reported that only
  body-only reproduces the figures exactly — digit match, not "within
  tolerance".
- **Refused a coarser 4-cluster design that would have made C2 trivially
  green**, on the explicit grounds that it would launder six named
  residual classes into one undifferentiated bucket. That is the
  certification's whole integrity in one decision.
- **Reported both corrections rather than applying them**, correctly
  treating cluster 1 as my contract's own template and not its own to
  edit.
- Kept the C2 RED's **two failure reasons unblended** (28,967 unassigned
  by design; 15 double-assigned = a real bug), so neither hides the other.

### Open, carried forward

Complement scout is **NOT near-zero** — "unquoted definitional
constructions" opens as a named cluster. `חוק זכיון ים המלח` art.1 (a
real `הגדרות`-headed article) returns **0 candidates for all 13 real
terms** under the unmodified production call: a genuinely new, previously
unnamed buildable class. `פקודת הפרשנות` also surfaced here, a plausible
root cause for the parent's residual (6).
