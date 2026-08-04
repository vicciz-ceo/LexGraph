# Panel log — Sprint 2026-08-04-defs-us-pr (Puerto Rico, Spanish)

Append-only. Panel mode (program P-R3 / director order): Planner, Developer and
QA speak with one another THROUGH the sprint manager; every exchange is recorded
here. Escalations that the panel cannot settle go to the program manager.

---

## 2026-08-04 — Manager: sprint open, workspace ready

**Workspace.** Worktree `/Users/nerya/LexGraph-wt/defs-us-pr` on branch
`claude/defs-us-pr`, created from `origin/main` (`83532fe`). Own backend venv
built (`python3.13`, `pip install -e '.[dev]'`, exit 0, Python 3.13.12) — the
main checkout's venv is NOT usable here (known worktree trap). Git identity
verified: `256402398+vicciz-ceo@users.noreply.github.com`. Nobody on this panel
works in `/Users/nerya/LexGraph` (program manager owns it).

**CodeGraph.** The `.codegraph/` index lives in the main checkout only. All
agents run `codegraph explore "<question>"` from `/Users/nerya/LexGraph`
(read-only) or pass `projectPath=/Users/nerya/LexGraph` to the MCP tool. The
index was built at `origin/main`, which is exactly what this worktree is based
on, so it is current for pre-sprint code.

**Manager's own live re-confirmation of the recon premise** (worktree venv,
real code, not "the dossier said so"):

```
PR in registry: True
profile: USProfile  code=US-PR
is_definitions_heading('Artículo 3. Definiciones') -> False
is_definitions_heading('Section 3. Definitions')   -> True
```

So PR resolves to the generic English `USProfile` and its real Spanish
Definiciones headings are invisible. Recon §6/B3b premise holds.

**Core-sprint coordination status.** `origin/claude/defs-core-scope` exists at
`5b93ef8` ("acquire planner lock, open panel log, record C5 baseline"). Its
contract names a `## Seam spec (published)` section as the core Planner's FIRST
deliverable, but that section is **not yet present**. Per the sprint contract's
Coordination clause this panel plans and authors RED tests meanwhile, and polls
`git fetch origin && git show origin/claude/defs-core-scope:docs/sprint/sprints/2026-08-04-defs-core-scope.md`.

**Manager note for the Planner (not a finding, a lead):** the HF snapshot also
contains `us_pr_constitutions.parquet` alongside `us_pr_statutes.parquet`. The
sprint contract scopes this sprint to the statutes file (23,636 rows). If the
constitutions file carries definition-bearing Spanish text, that is an
out-of-contract observation to report, not to silently absorb.

---

## 2026-08-04 — Planner: full-corpus survey detail, seam proposal, item plan, RED tests

**Environment.** Worktree venv already has `pyarrow==25.0.0` installed
(`backend/.venv/bin/pip list`) — unlike the 2026-08-02 sprint's venv, no
disposable scratch venv was needed to read the parquet file; still never
read from anything under `backend/tests` (all survey scripts live in the
scratchpad, not the repo). CodeGraph used for all code understanding
(`profiles.py`, `us_profile.py`, `pipeline.py`, `matcher.py`, `extract.py`)
before any Read — one `codegraph explore` call each replaced what would
otherwise have been several grep+Read round trips.

**Core seam poll** (re-run at survey time, same result as the manager's
entry above): `origin/claude/defs-core-scope` is at `5b93ef8`; its
contract's `## Seam spec (published)` heading exists with no body. Not
blocking — planned and authored RED tests against the Planner's own
proposed interfaces, with the one genuinely core-blocked test file
(`test_pr_profile_scope.py`, P3) explicitly `xfail`-marked with the poll
command and reasoning in its own docstring.

### Survey detail (full tables; contract has the dense summary)

**Heading variant census** (652 `defini`-substring rows → 635 genuine after
excluding the `Aportaciones Definidas`/`sentencia definitiva`/stray-verb-form
false positives):

| Bucket | Count | Note |
|---|---|---|
| Bare `DEFINICIONES` (post-prefix-strip, plural) | 463 | e.g. `STATE_PR_LEY_249_2003_ART3` |
| Bare `DEFINICIÓN` (singular) | 10 | |
| Bare `(DEFINICIONES)` (parenthesized) | 2 | |
| Compound heading (Definici* embedded in longer text) | 160 | incl. Civil-Code `"X; definición"` single-term style |
| `section_title` > 120 chars (truncated-into-body artifact) | 9 | 1.4% of 635; real example dumped below |
| False positives excluded | 17 | 12 `Definidas`, 2 `definitiva`, 3 other |

**Idiom candidate frequency** (rows containing ≥1 match; corpus-wide n=23,636
/ within 635 canonical rows) — corrected, final numbers:

| Idiom | Corpus-wide rows | Canonical-section rows |
|---|---|---|
| `significa` | 596 | 322 |
| `significará` | 340 | 119 |
| `significan` | 12 | 6 |
| `significarán` | 19 | 10 |
| `se entenderá por` | 62 | 9 |
| `se entiende por` | 15 | 2 |
| `se entenderán por` | 5 | 1 |
| `quiere decir` | 7 | 3 |
| `tendrá el significado` | 15 | 7 |
| `tendrán el significado` | 309 | 238 |
| `tendrá(n) los significados` | 71 | 60 |
| `denota` | 1 | 1 |
| `comprende` | 145 | 24 |
| `incluye` | 2,350 | 233 |
| `se define`/`se define como` | 398 / 23 | 85 / 13 |
| `definido como` | 24 | 8 |
| `según se define` | 265 | 54 |

Headline: `significa(rá/n)` (322+119+6+10=457 canonical rows) and
`tendrá(n) el/los significado(s)` (7+238+60=305 canonical rows) are
CO-DOMINANT — the recon's lead named only `significa` (1,006 in a 4,000-row
sample) and `se entenderá por` (26) as its top signals; `se entenderá por`
is real but a minor idiom (9/635 canonical rows) compared to the
`tendrá(n) el/los significado(s)` family the recon's guess-based lead missed
entirely.

**Entry marker shapes** (within 635 canonical rows, ≥2 occurrences required
to count as a genuine list, not a coincidental single hit — regex required
a preceding `[.;]\s` or start-of-string, since bodies have zero newlines):

| Marker shape | Rows (≥1) | Rows (≥2, genuine list) |
|---|---|---|
| `(a)` letter-full-paren | 299 | 272 |
| `(1)` digit-full-paren | 121 | 109 |
| `a)` letter-close-paren-only | 87 | 82 |
| `1.` digit-period | 51 | 44 |
| `a.` letter-period | 41 | 34 |
| `1)` digit-close-paren-only | 18 | 13 |

461/635 (72.6%) have ≥1 genuine list marker of these 6 shapes; 174/635
(27.4%) have none (single-entry Civil-Code-style articles, or a marker shape
not yet catalogued — flagged as residual risk for QA's P4 sweep). Of those
174, 20 start with a repeated-term + em-dash single-inline-entry shape
(`"Term. — Definition"`).

Quote style within canonical bodies: curly `“”` 437/635, straight `"` 76/635,
mojibake byte-corruption (`\x80\x9c` etc., or `�`) **0/635 and 0/23,636
corpus-wide** — confirmed PR does NOT share RI's mojibake defect.

**Scope phrase census** (corpus-wide / within 635 canonical rows, `\b`-
boundary-corrected):

| Phrase | Corpus-wide | Canonical |
|---|---|---|
| `A los fines de este Artículo` | 16 | 0 |
| `A los fines de este Capítulo` | 5 | 2 |
| `A los fines de esta Ley` | 101 | 51 |
| `A los fines de este Título` | 1 | 0 |
| `A los fines de este inciso` | 7 | 1 |
| `A los fines de este apartado` | 13 | 2 |
| `A los fines de esta sección` | 15 | 1 |
| `Para los fines de` (general) | 224 | 33 |
| `Para los efectos de` (general) | 101 | 23 |
| `A los efectos de este Artículo` | 13 | 0 |
| `A los efectos de este Capítulo` | 5 | 5 |
| `A los efectos de esta Ley` | 58 | 30 |
| `A los efectos de` (general) | 256 | 48 |
| `Para propósitos de este Artículo` | 26 | 0 |
| `Para propósitos de esta Ley` | 99 | 65 |
| `Para propósitos de` (general) | 444 | 98 |

Note: an earlier pass of this survey had a regex bug (`[Aa]\s+los...` with
no leading `\b`) that let "Par**a** los fines de..." bleed into the "A los
fines de..." bucket via its own trailing "-a" — caught and corrected before
publishing (compare: uncorrected `"A los fines de este Artículo"` showed 31
corpus-wide / 0 canonical; corrected shows 16 / 0 — the canonical-column
verdict, the one the item plan depends on, was unaffected either way, but
the corpus-wide count was overstated by ~2x uncorrected). Real corrected
example, `STATE_PR_LEY_77_1957_ART4_140` (a "Límite de riesgo" article, NOT
Definiciones-headed): `"...(2) Para los fines de este Artículo, objeto de
seguro en lo que respecta a seguro contra incendio... incluye las
propiedades aseguradas..."` — a second real ad-hoc example alongside the
one used in the fixture (`STATE_PR_LEY_85_2018_ART9_04`), not vendored, but
confirms the phrase family is not a one-off.

**Citation grammar** (corpus-wide, n=23,636):

| Shape | Rows | Occurrences |
|---|---|---|
| `Artículo N de esta Ley` | 1,123 | 1,498 |
| `Artículo N de la Ley Núm. M` | 331 | 369 |
| `Ley Núm. N de <fecha>` | 2,194 | 3,459 |
| `Ley N-YYYY` (dash form) | 7,052 | 10,932 |
| `sección N de esta Ley` | 8 | 9 |
| `Capítulo N de esta Ley` | 32 | 53 |
| `§ N` (bare symbol) | 2,249 | 2,722 |
| `L.P.R.A.` | 2,498 | 3,042 |
| `sec. N` (abbrev) | 37 | 45 |

**Non-canonical inline-definition signals** (corpus-wide / excluding
canonical rows):

| Signal | Corpus-wide | Non-canonical rows |
|---|---|---|
| `(en adelante, "X")` | 49 | 47 |
| `(en lo sucesivo, "X")` | 1 | 1 |
| `denominado/a` | 182 | 171 |
| `conocido/a como` | 2,191 | 2,060 |
| `que en lo sucesivo se denominará` | 2 | 2 |
| `(por sus siglas en X, "Y")` | 155 | 120 |
| `(en inglés, "X")` | 5 | 3 |
| `mejor conocido/a como` | 110 | 103 |

`conocido como`/`denominado` are REAL but overwhelmingly law-title-naming
idioms (`"conocida como 'Ley de...'"`), not term definitions — sampled
examples confirm this; NOT recommended as a P2 extraction trigger without
much narrower gating (would need to distinguish "names a LAW" from "defines
a TERM", which these two phrases alone don't disambiguate). `en adelante`
sampled clean (both examples pulled were genuine term-defining appositions).

### Data-quality artifact (real, not injected) — title/text split mid-word

Verified on `STATE_PR_LEY_135_1979_ART1`: `section_title` (212 chars) ends
`"...tendrán el significado que a su lado se expresa: a) \"Oficina\":
significará la Oficina de Personal del Estado Libre Asoc"`; `text` (83
words) begins `"iado de Puerto Rico. Rev. 16 de abril de 2024..."`. The word
"Asociado" is torn in half across the two columns at whatever fixed-length
boundary the scrape used. Consequence: entry (a) ("Oficina")'s own
definition text is NOT PRESENT in the `text` column at all — no extractor
running over `text` alone can recover it. This is the PR analog of this same
fixtures directory's DE-mojibake and PA-collision findings: a genuine corpus
limitation, not a code defect, flagged for QA rather than built into an
item's acceptance test. 9/635 canonical rows (1.4%) share this exact
`section_title` > 120 chars artifact — see contract for the full list of
`act_id`s (in the pr_sample_rows.json README addition).

### Seam proposal and item plan

Published in the sprint contract's `## Seam proposal` and `## Next Steps`
sections (not duplicated here — append-only discipline, the contract is the
canonical copy). Headline for the core Planner: **PRProfile as a distinct
profile class, registered under `"US-PR"` only** — reuse audit against
`USProfile` found near-zero exploitable overlap at every layer (heading
regex, entry-marker splitting — PR bodies have ZERO newlines within a
section, breaking `USProfile`'s line-based splitter outright — citation
grammar, cross-law-derivation idioms), and the distinct-class option gives
gate P5 a type-level (registry-keying) guarantee instead of relying solely
on an internal `if self.code == "US-PR"` branch inside otherwise-shared
code.

### RED test proof

Six new files under `backend/tests/unit/`:
`test_pr_profile_headings.py`, `test_pr_profile_extraction.py`,
`test_pr_profile_ad_hoc_definitions.py`, `test_pr_profile_citations.py`,
`test_pr_profile_no_english_regression.py`, `test_pr_profile_scope.py`.
Fixture: `backend/tests/fixtures/us_statutes/pr_sample_rows.json` (10 real
rows, README section appended documenting provenance and which shape each
row proves), plus the existing `de_sample_rows.json` reused unmodified for
the P5 English-regression file (no new DE fixture needed).

```
$ backend/.venv/bin/pytest backend/tests/unit/test_pr_profile_headings.py \
    backend/tests/unit/test_pr_profile_extraction.py \
    backend/tests/unit/test_pr_profile_ad_hoc_definitions.py \
    backend/tests/unit/test_pr_profile_citations.py \
    backend/tests/unit/test_pr_profile_no_english_regression.py \
    backend/tests/unit/test_pr_profile_scope.py --continue-on-collection-errors -q
...
ERROR backend/tests/unit/test_pr_profile_ad_hoc_definitions.py
ERROR backend/tests/unit/test_pr_profile_citations.py
ERROR backend/tests/unit/test_pr_profile_extraction.py
ERROR backend/tests/unit/test_pr_profile_headings.py
ERROR backend/tests/unit/test_pr_profile_no_english_regression.py
6 xfailed, 5 errors in 0.04s
```

Every `ERROR` is `ModuleNotFoundError: No module named
'app.definition_links.pr_profile'` — the exact same legitimate RED signal
the 2026-08-02 sprint's `test_definition_links_us_profile.py` used before
`USProfile` existed (precedent read via CodeGraph before writing these
tests). `test_pr_profile_scope.py`'s 6 tests `xfail` cleanly (not error) —
by design, since P3 is explicitly core-seam-gated and the file's own
`pytestmark` documents why.

Full existing suite re-run to confirm no regression from the new files
themselves (README edit, new fixture, 6 new test files — no production code
touched):

```
$ backend/.venv/bin/pytest backend/tests --continue-on-collection-errors -q
...
641 passed, 6 xfailed, 18 warnings, 5 errors in 13.69s
```

641 passed matches the pre-existing baseline exactly (repo-profile.md's
"2026-08-02: 504/504" note is stale per that same file's own caveat — 641 is
this worktree's real current count, unaffected by this pass).

### For the Developer (sequencing)

Items 1/2/4 (+ item 3's two functions, NOT their pipeline wiring) and item
6 (the `PRProfile` class itself, NOT registry wiring) are pre-core OK —
start there. Items 5 (scope), 7 (registry), and item 3's pipeline wiring
wait on `2026-08-04-defs-core-scope` publishing its seam spec; item 8 (full
pipeline E2E test) is not yet authored and is flagged to the manager as this
sprint's next planning increment once core lands, not silently treated as
covered by the current six files.

### For QA

The survey's measured signal tables above are the ground truth for gate
P4's zero-miss sweep — please sweep the full 23,636-row file against them
(idiom list, marker shapes, scope phrases, citation grammar, non-canonical
signals), not just against the 10 vendored fixture rows. Two explicit
residual-risk flags from this survey worth independent verification: (a)
the 174/635 canonical rows with no genuine multi-entry marker (may hide
marker shapes this survey didn't catalogue), and (b) `conocido como`/
`denominado` (real signals, but overwhelmingly law-title-naming rather than
term-defining in this survey's sample — worth QA's own independent check
before anyone is tempted to add them as a P2 trigger).

### Escalations

None. No panel-level conflict of the P-R2 class (zero-miss vs.
zero-false-positive) was hit in this pass — `conocido como`/`denominado`
came close (real signal, high false-positive risk) but this Planner's own
lean (exclude from this pass's item plan, flag for QA/future follow-up
rather than build a narrow-enough gate blind) did not require director-
level arbitration; recorded as a documented follow-up instead, not a
silent drop.

---

## 2026-08-04 — Manager: verification of the Planner handoff (ACCEPTED)

I do not accept "the Planner said so". Everything below is a check I ran
myself in this worktree against the real corpus and the real code.

**Role boundary — HELD.** `git diff --name-only 969140d...HEAD | grep -E
'^backend/app/|^frontend/src/'` returns NOTHING. Ten files changed: 6 new
test files, 1 new fixture, 1 purely-additive fixtures README (`--numstat`:
`99 0`, zero deletions), contract, log. No existing test was edited — the
program's standing "editing an existing test to fit is a planning bug"
constraint is satisfied by construction, not by assertion.

**Fixtures are REAL, verbatim corpus rows — verified, not trusted.** I read
`us_pr_statutes.parquet` directly and compared all 10 vendored rows on BOTH
`section_title` and `text`:

```
EXACT MATCH: STATE_PR_LEY_249_2003_ART3 / _63_2023_ART3 / _77_1957_ART30_020
             _77_1957_ART1_090 / _85_2018_ART9_04 / _160_2013_ART5_4
             _165_2020_ART1_2 / _135_1979_ART1 / _15_2024_ART3 / _70_1997_ART1
RESULT: 10 exact, 0 problems, of 10 fixture rows
```

Nothing was paraphrased, cleaned, or invented — including the ugly ones (the
truncated-mid-word `STATE_PR_LEY_135_1979_ART1` title artifact is real).
This mattered: a Spanish-language sprint is exactly where a fabricated
fixture would be hardest to spot by eye.

**Survey headline numbers — independently reproduced.** My own script, my
own regex, no reference to the Planner's code:

```
rows: 23636
section_title contains 'defini':                    652
of those, matching stem definici(on|ones):          635   <- Planner: 635
excluded (no stem):                                  17   <- Planner: 17
genuine-heading rows whose BODY contains a newline:   0
ANY corpus row whose body contains a newline:         0   <- structural claim CONFIRMED
rows with mojibake markers:                           0   <- PR does NOT share RI's defect
genuine PR Definiciones headings recognized by CURRENT code: 0 / 635
```

Three consequences I am treating as established fact for the rest of this
sprint: (1) the recon's "~529 Definiciones headings" undercounted — it is
**635**; (2) the before-rate for gate P4 really is **0/635**, so the gate's
"before = 0" is measured, not assumed; (3) **zero newlines anywhere in the
corpus** means `USProfile`'s line-based `_split_into_numbered_blocks` is not
merely mis-vocabularied for Spanish, it is structurally inapplicable. That
third point is the strongest single argument in the seam proposal and it
holds up.

**Idiom counts — reconciled, one immaterial delta.** The Planner's counts
did not match my first (case-sensitive substring) pass, so I re-ran under
three counting methods to find out why rather than reporting a discrepancy
I hadn't explained. Case-insensitive word-boundary counting reproduces
**6 of 7** exactly (`significa` 596, `tendrán el significado` 309, `tendrá
el significado` 15, `se entenderá por` 62, `quiere decir` 7, `se entiende
por` 15). The seventh, `significará`, is **337 by my count vs. 340
reported** — a 0.9% delta, immaterial to rule design and to every
conclusion drawn from it. Recorded here so QA does not re-discover it as a
mystery; QA should feel free to re-derive rather than inherit.

The survey's load-bearing NEW finding survives verification: the
`tendrá(n) el/los significado(s)` family (309 rows for one variant alone,
exact match) is co-dominant with `significa` and was **absent from the
recon's lead entirely**. Ruling M-R2 (own survey, not the recon's list) paid
for itself — had the panel built to the recon's inventory, this sprint would
have shipped a large silent miss straight through a zero-miss gate.

**RED proof — re-run by me, not quoted from the Planner.**

```
$ backend/.venv/bin/pytest backend/tests --continue-on-collection-errors -q
641 passed, 6 xfailed, 18 warnings, 5 errors in 13.58s
ERROR ...test_pr_profile_{headings,extraction,citations,ad_hoc_definitions,no_english_regression}.py
```

And the baseline, with the six new files excluded, to prove the 641 are
pre-existing and untouched:

```
$ backend/.venv/bin/pytest backend/tests -q --ignore=<the 6 new files>
641 passed, 18 warnings in 13.48s
```

So: baseline 641 passed / 0 xfailed, unchanged; all 6 new xfails are the
core-gated P3 scope tests; 5 files RED via `ModuleNotFoundError`.

**Manager's caveat on the RED signal.** `ModuleNotFoundError` is a *weak*
red — it proves the module is absent, not that each assertion discriminates.
I therefore read every test body rather than trusting the count. They are
substantive: exact candidate counts (9/6/6/1) against named real Spanish
terms, a guard that entry (c) re-quoting its own term must not swallow entry
(d), false-positive guards on real `Aportaciones Definidas` and a real
table-of-contents heading, and — for P5/M-R4 — the real Delaware fixture fed
through `PRProfile` directly. The P5 test would genuinely fail if the
Spanish rules were made language-blind, because the English word
"Definitions" contains the substring `defin`; that is the collision M-R4
exists to catch, and it is now pinned. **M-R4 satisfied.**

**Verdict: Planner handoff ACCEPTED.** Item plan (9 items) frozen as the
sprint's scope. Honest gap the Planner flagged rather than hid: item 8, the
end-to-end `run_definition_linking` live-path test, is NOT yet authored and
is sequenced after core — I am carrying that forward as an open obligation,
not a completed item.

### Manager ruling M-R5 — Developer proceeds now on seam-agnostic work

The seam proposal (`PRProfile` as a distinct class) is published on this
branch for the core panel to review per M-R3, and I am relaying it to the
program manager. I am **not** stalling the sprint on that review, because
the work splits cleanly:

- The Spanish RULE LOGIC — heading stem detector, continuous-string entry
  extractor, local/ad-hoc extractors, citation grammar — is identical under
  BOTH seam options. It lives in a NEW module (`pr_profile.py`), touches no
  shared file, and is buildable today. Items 1, 2, 3 (functions), 4, 6.
- Only REGISTRATION differs between the options, and registration is a
  shared-module edit (`profiles.py::_REGISTRY`) that M-R3 already forbids
  before core publishes. Items 5, 7, 8 stay parked.

Residual risk, stated plainly: if the core panel rejects the distinct-class
proposal, the `PRProfile` wrapper and the tests' import surface get rehomed.
That is roughly the wrapper plus import lines — the rule functions and every
assertion about Spanish behavior survive untouched. I judge that cheaper
than idling an entire implementation phase behind a review I cannot
synchronously obtain. Recorded as a deliberate trade, not an oversight.

---

## 2026-08-04 — Developer: implementation of items 1/2/3(functions)/4/6

**Scope held.** One new file only:
`backend/app/definition_links/pr_profile.py` (537 lines). `git status
--short` before commit shows exactly one untracked file — no edit to
`profiles.py`, `pipeline.py`, `extract.py`, `matcher.py`, `us_profile.py`,
`sections.py`, `normalize.py`, or any model/migration; no test file
touched. Registry wiring (item 7), scope determination (item 5), and
pipeline dispatch (item 3's wiring, item 8) were not implemented, per
M-R3/M-R5 — confirmed by `grep -n "pr_profile" backend/app/definition_
links/pipeline.py` returning nothing.

**Method.** Read the contract's survey tables and the panel log's raw
per-shape counts, then the six RED test files as the literal spec (per
the developer brief: "READ THEM AS YOUR SPECIFICATION"), then
`codegraph explore` for `USProfile`/`HebrewProfile`/`DefinitionCandidate`/
`extract_local_definitions`/`extract_adhoc_definitions`/
`_extract_inline_quoted_definitions`/the `JurisdictionProfile` Protocol
before writing a line — one call surfaced verbatim source for all of
`profiles.py`, `us_profile.py`, `extract.py`, and the relevant
`pipeline.py` slice in a single round trip. Before touching the real
module file, every regex (heading detector, entry-marker scanner,
term/separator splitter, local/adhoc triggers, citation grammar) was
prototyped against the actual 10 vendored fixture rows in a scratch
script — this caught one real design gap before it ever reached a test
run (below) and is the reason the first full test run inside the actual
module still needed one fix (a transcription slip between the verified
prototype and the production file, also below).

**Design choices forced by the tests / worth recording:**

- **Entry-marker anchor needed THREE boundary characters, not two.**
  The contract's survey note ("regex required a preceding `[.;]\s` or
  start-of-string") undercounts the real anchor set needed for a
  zero-miss *extractor* (as opposed to a frequency-counting survey
  script): `STATE_PR_LEY_249_2003_ART3`'s and `STATE_PR_LEY_77_1957_
  ART30_020`'s own FIRST markers each follow the section's lead-in
  colon ("...significado: a. ..."), not a period — so the anchor class
  had to be `[.;:]`, colon included, or entry (a) of two of the five
  extraction tests silently vanishes into the (nonexistent) preceding
  block. Separately, `STATE_PR_LEY_77_1957_ART30_020` entry (i) follows
  a mid-body scrape artifact — a `[Ley 77 de 19 de Junio de 1957, según
  enmendada]` page-break annotation — so its marker `(i)` is preceded by
  `]`, not by any sentence punctuation at all. Final anchor:
  `(?:^|(?<=[.;:\]])\s+)`, three boundary characters plus start-of-string.
  This is additive to the contract's survey note, not a contradiction of
  it — the survey was counting marker FREQUENCY across the corpus, not
  solving "how do I find this specific marker's own left edge," and the
  colon/bracket cases only surface once you try to actually split real
  bodies into blocks.
- **Self-caught regression: parenthesization slip on the first pass
  through the real module.** The prototype script (never committed,
  scratch-only) had the anchor correctly as
  `(?:^|(?<=[.;:\]])\s+)` — `\s+` INSIDE the second alternative only, so
  the `^`-at-absolute-start branch needs no whitespace to match. When I
  hand-transcribed this into the production file I mis-grouped it as
  `(?:^|(?<=[.;\]]))\s+` (colon dropped AND `\s+` moved outside the
  alternation, so even the start-of-string branch now required leading
  whitespace that doesn't exist when a marker IS the first character,
  e.g. `STATE_PR_LEY_63_2023_ART3`'s `(a) Instituto...` and `STATE_PR_
  LEY_15_2024_ART3`'s `a) Composta...`). This produced 4 real test
  failures on the first `pytest` run inside the module (all four
  "missing entry (a)" shaped) — caught immediately by running the actual
  target test files, not asserted away. Fixed by restoring the exact
  prototyped form. Recording this because it is the one place my own
  hand-transcription, not test-driven design, introduced a defect — the
  test suite is what caught it, which is the discipline working as
  intended, not a close call.
- **`extract_adhoc_definitions`' `definition_text` needed a real
  antecedent, not a trivial echo.** The Hebrew analog
  (`extract.extract_adhoc_definitions`) sets `definition_text=term` (the
  short name echoed back at itself) since Hebrew's `(להלן - X)` idiom
  carries no separate long-form phrase in that function's scope. The
  Spanish `(en adelante, X)` idiom's OWN semantics (per the contract:
  "an inline parenthetical apposition restating an immediately-preceding
  long noun phrase under a short name") make that echo actively
  misleading for PR — "Comité" defined as "Comité" says nothing. Neither
  test file asserts `definition_text`'s exact content for this function
  (only `.terms`/`.scope`), so this was a judgment call, not a forced
  test outcome: I capture the noun phrase immediately preceding the
  parenthetical (back to the nearest `.;:()` boundary or string start,
  found by a plain `rfind` scan, not a regex lookbehind trick) as
  `definition_text`, falling back to the term itself only if that
  antecedent is empty. Flagging this because it is real behavior beyond
  what any test pins down — QA or a future caller should not assume it
  is contractually guaranteed the way the tested fields are.
- **`is_definitions_heading`'s Spanish-preposition exclusion list has no
  real-corpus example in the 10 vendored fixture rows.** The contract
  names the shape ("first-word-OR-last-word-with-Spanish-preposition-
  exclusion") and I implemented a `_SPANISH_PREPOSITIONS` set mirroring
  `USProfile`'s `_PRECEDING_EXCLUSION_WORDS` (de, del, a, al, en, para,
  por, según, con, sin, sobre, entre, hasta, desde, ante, bajo, contra,
  durante, mediante, salvo, tras), but every negative-guard test in
  `test_pr_profile_headings.py` is independently excluded already by the
  stem-match requirement itself (`Definidas`/`definitiva` don't contain
  the literal `ci` the stem needs) or by the last-word check simply
  failing (the TOC row's real last token is the truncated `"Ar"`, not
  `"Definiciones"`) — none of the ten fixture rows exercises the
  preposition-exclusion branch on a stem match that would otherwise be a
  false positive. Implemented for design fidelity to the contract and
  because `USProfile` carries the same shape, but it is currently
  UNVERIFIED against any real PR corpus example. Flagging for QA's
  zero-miss sweep to find (or fail to find) a real corpus heading like
  "Aplicación de Definiciones a ..." that would actually exercise it.

**Verification (my own, not asserted):**

```
$ backend/.venv/bin/pytest backend/tests/unit/test_pr_profile_headings.py \
    backend/tests/unit/test_pr_profile_extraction.py \
    backend/tests/unit/test_pr_profile_ad_hoc_definitions.py \
    backend/tests/unit/test_pr_profile_citations.py \
    backend/tests/unit/test_pr_profile_no_english_regression.py \
    backend/tests/unit/test_pr_profile_scope.py -v
...
53 passed, 6 xfailed in 0.07s
```

All 6 `test_pr_profile_scope.py` tests still `xfail` (not error, not
xpass) — `determine_chapter_scope` was not implemented, per scope
(confirmed by reading the tail of the `-v` output: every one reports
`XFAIL`, none reports `XPASS`). `test_registering_us_pr_does_not_change_
what_us_de_resolves_to` in the no-english-regression file now runs for
real (module import succeeds) and passes — `get_profile("US-DE")` still
resolves to `USProfile`, confirming the registry was genuinely untouched,
not merely un-diffed.

```
$ backend/.venv/bin/pytest backend/tests -q
694 passed, 6 xfailed, 18 warnings in 12.38s
```

694 = the 641 pre-existing baseline + 53 new PR tests, exactly. Re-run
with the six new files excluded to prove the 641 are unmoved:

```
$ backend/.venv/bin/pytest backend/tests -q --ignore=<6 new files>
641 passed, 18 warnings in 11.96s
```

**Protocol conformance, checked directly (not just "it compiles"):**

```
$ backend/.venv/bin/python -c "
from app.definition_links.pr_profile import PRProfile
from app.definition_links.profiles import JurisdictionProfile
p = PRProfile(code='US-PR')
for m in [m for m in dir(JurisdictionProfile) if not m.startswith('_')]:
    print(m, hasattr(p, m))
"
detect_cross_law_derivations True
extract_definitions_from_section True
find_citations True
find_term_uses True
is_definitions_heading True
normalize_for_parsing True
```

**Lint/format.** No `ruff`/`black` config in `backend/pyproject.toml`, and
neither tool is installed in this worktree's venv (`python -m ruff`/
`python -m black` both `No module named ...`) — same absence the Planner
would have hit had this item been in the RED-test pass. Checked manually
against the file's own longest lines (max 99 chars, consistent with
`us_profile.py`'s existing ~92-char lines) and confirmed `py_compile`
succeeds cleanly.

**File size note (not a violation of anything this sprint's contract
asks for).** `pr_profile.py` is 537 lines — the contract's item plan
explicitly assigns items 1/2/3(functions)/4/6 to ONE module ("Same
module" repeated at every item), so this is the assigned shape, not a
drift from it; `us_profile.py` (546 lines) is the closest precedent in
this exact package for a single-file per-jurisdiction profile at this
size.

**For QA:** the zero-miss full-corpus sweep should pay particular
attention to (a) the entry-marker anchor set (`.`/`;`/`:`/`]`/
start-of-string) against markers this Developer's 10-row fixture sample
didn't exercise — the survey's own 174/635-no-marker and 27.4% figures
suggest real diversity beyond what's tested here; (b) the Spanish-
preposition exclusion branch in `is_definitions_heading`, unverified
against any real corpus row per the note above; (c) the two items the
Planner already flagged (`conocido como`/`denominado` narrow-gating,
and the `STATE_PR_LEY_135_1979_ART1`-style truncated-title corpus
limitation) — neither was in this Developer's scope, both still open.

**Escalations:** none. No test looked wrong; nothing required editing a
shared module; no P-R2 zero-miss-vs-false-positive judgment call arose
that wasn't already resolved by the Planner's own survey (the `en
adelante` vs. `conocido como`/`denominado` line was already drawn by the
Planner, and this Developer's scope only implements the safe side of
that line, per item 3).

---

## 2026-08-04 — Manager: Developer verification + GENERALIZATION GAP (cycle 1 rejected as incomplete)

**Boundaries — HELD.** `git diff --name-only 044a2c0...HEAD` shows exactly
two files: the new `backend/app/definition_links/pr_profile.py` and this
log. No shared module, no test, no fixture touched. Role separation intact.

**Tests — re-run by me.** `694 passed, 6 xfailed` full suite; `641 passed`
with the six new files ignored (baseline exactly reproduced); the 6 scope
tests confirmed `xxxxxx` = XFAIL, not XPASS, not error. Everything the
Developer reported is true.

**But passing the tests is not passing the gate.** The tests pin 5 real
fixture rows. Gate P4 is a zero-miss sweep of all 23,636. So I ran the NEW
module over the FULL corpus myself — the check the test suite structurally
cannot make — and the result changes the sprint's state:

```
ground-truth canonical rows (stem in section_title):   635
headings detected by new code:                         620   (0 false positives)
MISSED headings:                                        15   (13 real + 2 correct TOC rejections)

detected sections EXCLUDING the 10 vendored fixtures:  614
  yielding >=1 candidate:                              346
  yielding ZERO:                                       268
  extraction rate on rows the panel never saw:       56.4%
```

**56.4% is not zero-miss.** Before this sprint the rate was 0%, so this is
real progress and the Developer's work is sound as far as it was specified —
but the specification (the test suite) under-determined the corpus. This is
a PLANNING gap, not a Developer failure: the Developer implemented exactly
what was pinned, and I will not have him "fix" it by guessing at unpinned
behavior. Cycle goes back to the Planner for test extension, per role
separation.

**I categorized the 268 zero-yield rows so the panel gets a workload, not a
number** (full dump with `act_id` + body head:
`scratchpad/pr_miss_workload.json`):

| Bucket | Rows | Character | Settled? |
|---|---|---|---|
| **A** | 153 | Has ≥2 real entry markers AND a real defining idiom, still yields zero — e.g. `STATE_PR_LEY_77_1957_ART39_050`: `Según se emplean en este Capítulo: (1) "Cuenta" significa ... (2) "Asociación" significa ...`. Full-paren digit marker + curly quote + `significa`, all three catalogued in the survey. | **Unambiguous bug.** No judgment needed. |
| **B** | 7 | ≥2 markers, no canonical idiom — `(a) Diabetes tipo 1: es un desorden autoinmune…`. The marker list itself establishes definitional context. | Settled — safe inside a marker list. |
| **C** | 22 | Real idiom, marker shape not in the survey's six — `A.` UPPERCASE-letter-period (`A. "Estado Libre Asociado" significa…`) and `a. —` marker-plus-dash. | **Marker-inventory gap.** Settled. |
| **D** | 86 | Copulative/prose definitions with no marker and no canonical idiom — `Son bienes las cosas o derechos que pueden ser apropiables…` (Civil Code), `los pasivos se definirán como…`, `asegurador del país del Plan de Lloyd es una sociedad…`. Substantively these ARE definitions. | **NOT settled — P-R2 / program Q-1.** |

Bucket A quote style: curly 124 / straight 9 / unquoted 20 — so it is not a
single quote-character bug; several distinct shapes are failing.

**The 13 real heading misses** form clean families, not noise:
- Civil-Code mid-token compound `X; definición y <noun>` — 7 rows
  (`Subrogación; definición y alcance`, `Tutela; definición y objeto`,
  `Parentesco; definición y alcance`, `Acto jurídico; definición y
  clasificación`, `Inoponibilidad; definición y clases`, `Retención;
  definición y ejercicio`, `Las normas de la compraventa; definición y
  aplicabilidad`). "definición" is neither first nor last substantive word.
- Parenthesized whole heading `(Definiciones)` — 2 rows
  (`STATE_PR_LEY_60_1963_ART100`, `STATE_PR_LEY_77_1964_ART1`). The
  Planner's own survey COUNTED these 2 and no test pinned them.
- Trailing-preposition `…, definición de` — 2 rows.
- Em-dash compound `—Definición de Términos` — 1 row.
- `Microseguros, definición y clases autorizadas` — 1 row.

The 2 Table-of-Contents rows are CORRECT rejections and must stay rejected —
there is already a test pinning one of them.

### Manager ruling M-R6 — cycle 2 scope, and what escalates

- **Planner authors RED tests for buckets A, B, C and the 13 heading
  misses.** These are settled: they need no director input, only real
  coverage. Vendor new real fixture rows for each family. This is the
  Planner's job because the Developer must never write tests, and it is the
  Planner's under-specification that let a 56.4% implementation pass.
- **Bucket D does NOT get silently decided by this panel.** 86 real
  copulative/prose definitions is exactly program ruling P-R2 and standing
  question Q-1 ("when zero-miss and zero-false-positive conflict, which
  yields?"). Capturing `Son bienes las cosas o derechos…` requires matching
  Spanish copulative prose, which will fire on ordinary substantive text
  across the corpus. Under the director's ABSOLUTE ZERO-MISS bar these 86
  are misses and P4 fails; under precision-first they are an accepted
  limitation. I escalate this to the program manager with these real
  examples rather than picking a side.
- **Lesson recorded for the program**: a test suite built from N hand-picked
  fixture rows cannot prove a zero-miss gate, no matter how real the rows
  are. Every family panel should run its implementation over its full corpus
  BEFORE declaring dev-complete. I found this in cycle 1 only because I ran
  the corpus myself instead of accepting a green suite.

## 2026-08-04 — Planner: cycle-2 re-diagnosis, RED tests, corpus-shaped floor

Read the full workload dump (`scratchpad/pr_miss_workload.json`, buckets
`heading_misses`/A/B/C/D) and this log's M-R6 entry in full before touching
anything. Per M-R6: buckets A, B, C and the 13 real heading misses are mine
to test; bucket D stays escalated; role separation holds — I read
`pr_profile.py` to diagnose, I did not edit it.

### Method

Rather than trust M-R6's bucket characterizations as final, I re-ran the
LIVE `pr_profile.py` code (via a disposable scratch script,
`scratchpad/diagnose_bucket_a.py` and siblings, reading the already-cached
`us_pr_statutes.parquet` snapshot on disk — same discipline as every prior
fixture-vendoring pass, never touching `backend/.venv` or any committed
test) against every named example in M-R6's buckets, and against a broader
sample from the raw workload dump, printing exactly which regex/pattern
matched or failed and why. This surfaced two things M-R6's prose summary
could not: (1) bucket C's own named examples are NOT actually blocked by a
marker-regex gap (both markers already match live) — M-R6's
characterization was a reasonable first-pass hypothesis from the outside,
wrong on the mechanism; (2) three genuinely NEW defects hiding inside
bucket B that M-R6 never named at all (a two-letter Spanish marker gap, a
marker false-positive on spaced abbreviations, and a dispatch-logic gap).

### Bucket-A root cause (for the Developer — full detail in the contract's
`### Cycle-2 corrections` and in `test_pr_profile_extraction_cycle2.py`'s
module docstring)

`_extract_term_and_definition` tries exactly 3 separator patterns:
quoted+colon, quoted+typographic-dash (`–—` only), unquoted+typographic-
dash. Every one of the 153 bucket-A rows I live-checked fails because its
real separator shape is none of those three — NOT because of quote-
character handling (curly `“”` and straight `"` are both already accepted
by the existing patterns' character classes). Six distinct, independently
confirmed shapes, each with a live example:

| Shape | Example | Real row |
|---|---|---|
| Quoted term, idiom verb, NO separator at all (curly) | `"Cuenta" significa...` | `STATE_PR_LEY_77_1957_ART39_050` |
| Same, straight quotes | `"Body Piercer" significa...` | `STATE_PR_LEY_73_2003_ART2` |
| Quoted term + comma + idiom | `"Análisis Clínico", significará...` | `STATE_PR_LEY_167_1988_ART2` |
| Quoted term + ASCII hyphen `-` + idiom | `"Activo" - significa...` | `STATE_PR_LEY_189_1996_ART2` |
| Quoted term, no separator, NO idiom verb | `"Activos líquidos" Aquellos activos que...` | `STATE_PR_LEY_214_1995_ART2` |
| Unquoted term + colon | `Certificación: documento oficial...` | `STATE_PR_LEY_33_2017_ART3` |
| Unquoted term + own trailing period | `Agencia. Cualquier departamento...` | `STATE_PR_LEY_66_1975_ART3` |

The first shape alone (quoted+idiom+no-separator, both quote styles) is
~133/153 of bucket A. There is no `_UNQUOTED_TERM_COLON_RE` in the module
at all today — only a dash variant exists for unquoted terms.

### Bucket-C re-diagnosis (correction, not confirmation, of M-R6)

Live-checked BOTH of M-R6's own named C examples directly:

- `STATE_PR_LEY_430_2000_ART3` (`A.`/`B.`/`C.`... uppercase-letter-period
  markers): `_ENTRY_MARKER_RE.finditer` finds all 26 real markers
  correctly — the period-marker alternative's `[a-zA-Z]` class is
  case-insensitive by construction. Zero-yield here is plain bucket-A
  (quoted term + `significa`, no separator). Not a marker gap.
- `STATE_PR_LEY_190_1995_ART2` (`a. —`/`b. —`... markers): also matched
  correctly, 12/12. What fails is the BLOCK content: `a. — "Nueva
  programación" significa...` has a decorative em-dash between the marker
  and the term that no separator pattern expects a block to start with.
  This genuinely IS new (A5 in the test file), but it's a block-prefix
  gap, not a marker-regex gap.

So the "marker-inventory gap" framing in M-R6 does not hold for either
named example. It DOES hold, but for a THIRD, different real row I found
by diagnosing bucket B instead: `STATE_PR_LEY_46_2008_ART3` uses the
traditional Spanish alphabetical sequence where "ch" is its own letter,
producing a genuine two-character marker `ch)` that
`_ENTRY_MARKER_RE`'s single-character classes cannot match at all
(confirmed live: only 6/7 real markers found, `ch)` silently absorbed into
entry `c)`'s block). I re-surveyed the marker inventory specifically
looking for more shapes like this across the rest of bucket A/B/C's real
bodies and found no further gap beyond this one and the A5 dash-prefix
case — the marker alternatives (paren/close-paren/period, letter/digit)
otherwise hold up across every row checked.

### An incidental precision defect, found via bucket B

`STATE_PR_LEY_51_2003_ART2`'s body contains the spaced abbreviation `"U.
S. Geological Survey"` three times inside entry prose. `S.` alone (single
letter, preceded by `U. ` ending in period+space) is indistinguishable
from a genuine letter-period entry marker today — `_ENTRY_MARKER_RE` finds
7 "markers" in this row (`1. S. S. 2. S. 3. 4.`) where only 4 are real,
fragmenting entry 1's `definition_text` mid-sentence. This is the mirror
image of a zero-miss defect: it is a FALSE marker match, not a missed one,
and it would not have been caught by any zero-miss sweep — only by reading
the actual extracted `definition_text` for a row that superficially
"succeeds." Pinned in `test_a6_captures_all_four_entries_despite_spaced_
abbreviation_marker_misfire`.

### A dispatch-logic gap, found via bucket B, not named in M-R6 at all

`STATE_PR_LEY_77_1957_ART9_040` (`"Agente General, definición"`) is a
single-entry, no-top-level-marker Civil-Code article: `"Agente General es
la persona nombrada por un asegurador..."`. Its body also contains an
enumerated `(1)`..`(11)` list of the SAME term's own duties — sub-clauses
of one definition, not 11 separate entries. `extract_definitions_from_
section`'s dispatch is all-or-nothing (`if not markers: <single-entry>;
else: <markers-path>`) — because `(1)`..`(11)` exist somewhere in the
text, the whole body takes the markers path, which has no "entry −1" for
text before the first marker: the term and its lead-in are silently
dropped, 11 bogus fragments are produced instead. Pinned in
`test_single_no_marker_entry_survives_a_trailing_incidental_sub_list`.

### Heading misses: one clause-scoping gap, one orthogonal gap, not 5

`is_definitions_heading` only checks the first-or-last substantive token
of the WHOLE tail. Live-checking each of the 13 real misses individually:
11 share ONE root cause — the stem sits as the first (or trailing-
preposition-suffixed) word of an INNER clause (semicolon-, comma-, or
em-dash-delimited), not of the whole tail. One row
(`STATE_PR_LEY_26_1941_ART78`) needs clause-splitting at TWO levels
(comma inside semicolon) since "definición" is neither the first nor last
word of the whole tail OR of the outer semicolon-clause, only of the
innermost comma-sub-clause. The remaining 2 (`"(Definiciones)"`, fully
parenthesized) need an orthogonal fix: parentheses aren't in
`_TAIL_TOKEN_SPLIT_RE`'s split class, so the whole parenthesized string
tokenizes as one un-matchable token — needs enclosing-paren stripping
before the existing rule runs. Both real TOC rejections
(`STATE_PR_LEY_165_2020_ART1_2` from cycle 1, `STATE_PR_LEY_51_2020_
ART1_2` newly vendored this cycle) are re-pinned and confirmed to stay
rejected under this diagnosis — I did not just trust that a clause-based
widening would leave them alone, I checked: neither has "Definiciones"
adjacent to any semicolon/comma/em-dash boundary of ITS OWN heading tail.

### Fixtures vendored

24 REAL rows, `backend/tests/fixtures/us_statutes/pr_sample_rows_cycle2.json`
(sibling file, cycle 1's `pr_sample_rows.json` untouched), byte-compared
against a fresh read of the live parquet immediately before committing
(script output: `ALL BYTE-IDENTICAL`, field-count check also passed). Full
per-row provenance and family mapping in the fixtures README's new
`## pr_sample_rows_cycle2.json` section. `act_id`s: `STATE_PR_LEY_
77_1957_ART39_050`, `STATE_PR_LEY_73_2003_ART2`, `STATE_PR_LEY_189_
1996_ART2`, `STATE_PR_LEY_214_1995_ART2`, `STATE_PR_LEY_33_2017_ART3`,
`STATE_PR_LEY_39_1988_ART2`, `STATE_PR_LEY_493_1952_ART1`, `STATE_PR_LEY_
318_1999_ART2`, `STATE_PR_LEY_167_1988_ART2`, `STATE_PR_LEY_60_1988_ART1`,
`STATE_PR_LEY_66_1975_ART3`, `STATE_PR_AMBIENTAL_ART51`, `STATE_PR_LEY_
190_1995_ART2`, `STATE_PR_LEY_199_2015_ART2`, `STATE_PR_LEY_46_2008_ART3`,
`STATE_PR_LEY_51_2003_ART2`, `STATE_PR_LEY_77_1957_ART9_040`, `STATE_PR_
LEY_52_2019_ART3`, `STATE_PR_CIVIL_ART365`, `STATE_PR_LEY_77_1964_ART1`,
`STATE_PR_LEY_15_1931_SEC22`, `STATE_PR_MUNICIPAL_ART7_212`, `STATE_PR_
LEY_77_1957_ART15_020`, `STATE_PR_LEY_51_2020_ART1_2`.

### Tests authored, RED proof

3 new files: `test_pr_profile_extraction_cycle2.py` (20 tests),
`test_pr_profile_headings_cycle2.py` (13 tests),
`test_pr_profile_corpus_floor_cycle2.py` (the deliverable-4 aggregate
floor — 4 parametrized groups + 1 bookkeeping test, 33 rows total: 10
cycle-1 + 23 of cycle 2's 24). No existing test file edited.

```
backend/.venv/bin/pytest backend/tests -q
...
53 failed, 719 passed, 6 xfailed, 18 warnings in 13.36s
```

719 = cycle 1's 694-passed baseline + this cycle's 25 correctly-passing
assertions (negative/false-positive guards, the correct-zero guard, and
cycle-1 rows re-asserted at floor granularity) — confirmed by running the
3 new files in isolation first (53 failed, 25 passed there alone) before
running the full suite, so the 719 total is provably not hiding a
collection error. Every one of the 53 failures is a genuine assertion
failure (not an import/collection error) against the still-unfixed live
`pr_profile.py` — proof the tests exercise real gaps, not typos.

### Deliverable 4 — is the corpus-shaped floor the right idea?

Yes, and I built it as specified rather than substituting my own judgment:
`test_pr_profile_corpus_floor_cycle2.py` vendors 33 real rows (not a fresh
33 — reuses cycle 1's already-committed 10 plus 23 of this cycle's 24, so
no fixture bloat) and asserts a FLOOR, not exact behavior: every row
independently known to be genuinely capturable yields >=1 candidate, every
known-rejection row yields 0. It deliberately does not assert exact term
sets/counts (that's the family-specific files' job) — the coarser
granularity is exactly what would have caught cycle 1's 56.4% gap without
needing to re-predict the extractor's exact internals. One risk I flag
rather than hide: because it's a FLOOR, it will not itself tell a future
Planner WHICH shape broke if it fails — the family-specific tests remain
the diagnostic layer, this file is the tripwire.

### ESCALATION: 3 of the manager's 7 bucket-B rows are not clean per-term
marker lists — same character as bucket D, not folded into P-R2 by name

M-R6 called bucket B "settled — safe to capture" for all 7 rows. Diagnosing
all 7 individually against the real text, 4 are genuinely clean per-marker
term lists (already tested: `STATE_PR_LEY_199_2015_ART2`,
`STATE_PR_LEY_46_2008_ART3`, `STATE_PR_LEY_51_2003_ART2`,
`STATE_PR_LEY_77_1957_ART9_040`). The other 3 are NOT:

- `STATE_PR_LEY_77_1957_ART36_030` (`"Definiciones—Forma representativa de
  gobierno"`): body is `"Se considerará que una sociedad tiene una forma
  representativa de gobierno cuando: (a) Disponga en su constitución...;
  (b) los representantes electos constituyan mayoría...; ..."` — the
  `(a)`/`(b)`/... items are CONDITIONS of one single concept ("forma
  representativa de gobierno"), not separate defined terms.
- `STATE_PR_RENTAS_SEC2022_01` (`"Definición de Caudal Relicto Bruto"`) and
  `STATE_PR_RENTAS_SEC2042_01` (`"Definición de Donaciones"`): both bodies
  are `"(a) En General.- El [término] incluirá..."` — the article's own
  HEADING names the one term being defined; the `(a)`/`(b)`/`(1)`/`(2)`...
  markers are subsection labels ("En General", etc.) of ONE definition's
  own elaboration, not a list of distinct terms.

Forcing a per-marker-term extraction on these 3 would fabricate terms that
are not in the text — exactly the discipline `_extract_term_and_
definition`'s own docstring already protects ("skipped, not fabricated").
The only way to correctly capture these 3 is either (a) treat the whole
body (or its "(a) En General" clause) as ONE candidate whose TERM comes
from the article's own HEADING, not from the body — a capability neither
`extract_definitions_from_section` nor any PR extractor function has today
(the module's own docstring frames it as strictly body-only, scope passed
in by the caller) — or (b) leave them at zero, an accepted limitation.
That is the same substantive fork as bucket D (capture-via-heading-context
vs. accept-the-miss), just arrived at from a different starting bucket.

Options, with real examples above:
1. **Fold these 3 into bucket D's escalation** — same P-R2/Q-1 call,
   decided together with the other 86 D rows, so the program gets one
   coherent ruling on "heading-named-term, body-has-no-explicit-term"
   definitions rather than two separate ones.
2. **Treat as a distinct, narrower question**: unlike bucket D's free-form
   copulative prose, these 3 (and likely more like them corpus-wide) have
   a STRUCTURAL tell — a singular, semicolon/comma-joined Civil-Code-style
   heading (`"X, definición de Y"` / `"Y; definición"`) naming exactly one
   term, with a body that has NO quoted/colon/dash term-marker anywhere.
   That structural signal is narrower and higher-precision than bucket
   D's "any copulative sentence" risk — worth asking whether it's safe to
   decide on its own rather than folding into the wider D question.
3. **Leave as accepted misses, no further action this sprint** — the 3
   rows do not move the needle on P4's real capture rate (3/268) and item
   10 already fixes the other 4/7 of bucket B.

My lean: **option 2**, narrowly. The "heading names the one term, body
elaborates via unlabeled subsections" shape is common enough in the Civil
Code and PR Rentas Internas families (I saw the same shape recur across
several rows I only spot-checked, not fully catalogued) that it may be
worth its own measured survey rather than either lumping it into D's 86 or
silently dropping it — but I have NOT surveyed its full corpus-wide count,
so I am not asserting it is safe, only that it looks structurally
distinguishable from D. Not blocking cycle 2's handoff; flagging for the
manager to route.

---

## 2026-08-04 — Manager: cycle-2 Planner verified + ruling M-R7 (bucket-B escalation settled in-panel)

**Verified myself, not accepted on report.**
- Role boundary: `git diff --name-only 0f6823d...HEAD | grep '^backend/app/'`
  → NOTHING. No existing test modified (`--diff-filter=M` over
  `backend/tests/unit/` → nothing). Tests-only, as required.
- All **24** cycle-2 fixture rows byte-compared against the live parquet on
  BOTH `section_title` and `text`: **24 byte-exact, 0 problems.** Vendored
  data is real, again.
- RED re-run by me: `53 failed, 719 passed, 6 xfailed`. The 53 are genuine
  assertion failures against unmodified `pr_profile.py`, not import errors —
  a materially stronger red than cycle 1's `ModuleNotFoundError`, because
  each one now discriminates real behavior.

**The Planner corrected me, and it was right to.** My bucket-C label
("marker-inventory gap") was wrong for both examples I named: `A.` and
`a. —` markers already match `_ENTRY_MARKER_RE` today. My categorizer was a
crude proxy regex and I over-read it. The real bucket-A root cause is
narrower and better than my framing: `_extract_term_and_definition` only
tries **3 separator patterns**, and the corpus needs **6** — quoted+idiom
with no separator at all (~133 of the 153, the dominant shape),
quoted+comma+idiom, quoted+ASCII-hyphen+idiom, quoted-bare, unquoted+colon
(no such pattern exists today), unquoted+own-trailing-period. Likewise 11 of
the 13 heading misses collapse into ONE gap (the rule checks first/last word
of the whole tail, but real headings put "definición" first inside an inner
semicolon/comma/dash clause), not the 5 unrelated families I listed. A panel
that only confirms its manager is not worth running; recorded as a
correction to my M-R6 analysis, not buried.

Incidental finds I did not have: the traditional Spanish two-character `ch)`
marker (`STATE_PR_LEY_46_2008_ART3`), a marker false-positive on spaced
abbreviations, and a dispatch-logic bug.

### Ruling M-R7 — the 3 bucket-B rows are correct-zero, NOT misses, and do NOT escalate

The Planner flagged `STATE_PR_LEY_77_1957_ART36_030`,
`STATE_PR_RENTAS_SEC2022_01`, `STATE_PR_RENTAS_SEC2042_01` as sharing bucket
D's character and asked me to route them. I read them and I am settling this
in-panel rather than spending the director's attention on it:

- `ART36_030` body is `"Se considerará que una sociedad tiene una forma
  representativa de gobierno cuando: (a) Disponga en su constitución…"` —
  the `(a)`/`(b)` items are **conditions**, not defined terms.
- `SEC2022_01` body is `"(a) En General.- El caudal relicto bruto…"` —
  `"En General"` is a **subsection label**, not a term.

These are not a zero-miss-versus-precision tradeoff, which is what makes
them different from bucket D. Extracting them would not capture a definition
imprecisely; it would **fabricate a defined term that does not exist**
(`"En General"` is not a term of art in this statute). Gate P4's own wording
is "every hit captured **or proven not-a-definition**" — this is the
proven-not-a-definition branch, and the proof is the text itself.

**Ruling:** the 3 rows are correct-zero. The Planner's instinct to refuse to
force extraction was right. They stay uncaptured, documented here as
proven-not-a-definition, and QA must treat them as expected-zero in the P4
sweep rather than as outstanding misses. Bucket D remains the only genuine
director question from this sprint.

---

## 2026-08-04 — Developer: cycle-2 implementation, 53 RED tests -> green

Read the cycle-2 Planner entry, rulings M-R6/M-R7, and the contract's
`### Cycle-2 corrections` before touching anything. Worked only in
`pr_profile.py`; touched no test, no fixture, no shared module.

### What changed

- **`_extract_term_and_definition`**: added the 6 diagnosed separator
  shapes. Quoted patterns: comma+idiom (with an optional `"TermA" o
  "TermB"` alt-term prefix, real row `STATE_PR_LEY_60_1988_ART1`/
  `STATE_PR_LEY_3_2022_ART4`-shaped rows), ASCII-hyphen dash (added to
  the existing typographic-dash character class), and a bare-no-
  separator shape split into TWO patterns -- idiom-required and
  capitalized-required -- rather than one permissive "quote then
  anything" rule. Unquoted patterns: colon (new) and own-trailing-period
  (new). A leading-decorative-dash strip handles A5
  (`STATE_PR_LEY_190_1995_ART2`'s `a. — "Term" significa...`).
- **`_ENTRY_MARKER_RE`**: added the "ch" two-character marker
  (`STATE_PR_LEY_46_2008_ART3`) and a lookbehind excluding a marker
  candidate whose qualifying period is a lone single-letter abbreviation
  token (fixes the `"U. S. Geological Survey"` false-positive marker
  misfire, `STATE_PR_LEY_51_2003_ART2`).
- **`extract_definitions_from_section` dispatch**: checks whether the
  LEAD-IN text before the first marker matches a narrow bare-copulative-
  idiom shape (`"Agente General es la persona..."`); if so, the whole
  body is one entry with an incidental enumerated sub-list, not a
  multi-entry list (`STATE_PR_LEY_77_1957_ART9_040`).
- **`is_definitions_heading`**: extracted the existing single-clause
  rule into `_matches_definicion_stem`, added enclosing-parenthesis
  stripping (gap 2), and clause-splits the tail on `;`/`,`/em-dash
  before applying the stem rule to each clause (gap 1) -- a flat split
  turned out to handle the one row needing two delimiter levels
  (`STATE_PR_LEY_26_1941_ART78`) without any hierarchical logic, since
  comma and semicolon are both clause delimiters at the same flat level.

### Precision bugs found and fixed beyond the pinned tests

The 53 tests went green well before the corpus self-check was clean.
Three real precision regressions turned up only by running the fixes
over the full parquet, all now fixed (self-check numbers below are
post-fix):

1. **M-R7 violation**: an early, unbounded version of the new unquoted-
   period pattern fabricated a huge bogus "term" out of an entire
   paragraph for `STATE_PR_RENTAS_SEC2022_01`/`_SEC2042_01` (`"(a) En
   General.- El caudal relicto bruto..."` -- the ASCII-hyphen subsection
   label has no whitespace right after its own period, so `\.\s+`
   correctly skipped it, but the pattern then kept expanding across the
   whole block hunting for ANY later period+capital-letter). Fixed by
   excluding any `.-` sequence from ever being absorbed into the term
   (fails closed instead of running away), not by an arbitrary length
   cap -- a flat 80-char cap was tried first and cost real corpus recall
   on genuinely longer valid terms, so it was replaced with this
   structural exclusion.
2. **Quoted-block fallthrough**: a block starting with a quote but using
   an idiom outside the recognized set (`"se refiere a"`, not one of
   `significa/significará/será/es`) fell through to the UNQUOTED
   patterns, which don't exclude quote characters and searched arbitrarily
   far into the definition for their own separator
   (`STATE_PR_LEY_4_2022_ART1_03` entry (e)). Fixed by splitting the
   pattern list into a quoted group and an unquoted group, gated on
   whether the block starts with a quote character -- a quoted block that
   matches no quoted pattern now returns `None` rather than falling
   through.
3. **Unbounded forward search**: `_UNQUOTED_TERM_COLON_RE`/`_DASH_RE`/
   `_PERIOD_RE` all search forward non-greedily for their own separator
   with no bound, so a block with no EARLY separator (colon/dash/period)
   near its real start could match a much LATER, unrelated one deep in
   the definition text (`STATE_PR_CIVIL_ART326`: no markers, `"Poder es
   la facultad..."`, no colon/dash near the front) or the WRONG one when
   colon (tried first) reaches past a correct, nearer dash to a colon
   sitting inside the definition's own prose (`STATE_PR_LEY_3_2022_ART4`:
   `"Comandante de Operaciones Regionales – Significa ... a saber: Región
   1..."` -- colon inside the list intro, dash is the real separator).
   Fixed by bounding all three unquoted patterns' term group to <=100
   chars (the longest real term across every fixture is 72 chars).

None of these three were caught by the 53 pinned tests or the 641-row
baseline -- only running the full corpus surfaced them. Flagging this
explicitly per the brief's "tell me if a fix starts capturing prose"
instruction, even though these are precision fixes rather than a bucket-D
widening: the corpus self-check step is what caught them, not the test
suite, which is exactly the cycle-1 lesson the corpus-floor test file
exists to institutionalize.

### Full suite

```
backend/.venv/bin/pytest backend/tests -q
772 passed, 6 xfailed, 18 warnings
```

719 (cycle-1 baseline + cycle-1 PR tests) + 53 (cycle-2 RED tests) = 772,
zero failures. The 6 xfails are all `test_pr_profile_scope.py` (verified
individually via `-rxX`, all core-gated per M-R3, none XPASSed). Role
boundary self-check: `git diff --name-only` against the prior commit
shows only `backend/app/definition_links/pr_profile.py` touched -- no
test, no fixture, no shared module.

### Corpus self-check (real `us_pr_statutes.parquet`, 23,636 rows, read
once from the on-disk HF snapshot via a disposable scratchpad script --
never downloaded, never committed, same discipline as every prior pass)

- **Headings**: 633/635 genuine headings detected (0 false positives
  corpus-wide). The 2 misses are exactly the 2 correct-reject TOC rows
  (`STATE_PR_LEY_165_2020_ART1_2`, `STATE_PR_LEY_51_2020_ART1_2`) --
  every row that is genuinely NOT a TOC listing is now detected.
- **Extraction**: 513/633 detected sections yield >=1 candidate --
  **81.0%**, up from cycle 1's measured 56.4%.
- **Fabrication guard**: 0 candidates corpus-wide with a term longer than
  120 chars (checked after the 3 precision fixes above; an earlier,
  pre-fix version of this same self-check had 290 such candidates out of
  5936 total -- a 6x-higher rate than the unmodified cycle-1 baseline's
  28/3490 -- which is what drove the precision-bug hunt documented
  above).
- **M-R7 rows re-verified directly**: `STATE_PR_LEY_77_1957_ART36_030`,
  `STATE_PR_RENTAS_SEC2022_01`, `STATE_PR_RENTAS_SEC2042_01` all yield
  `[]` (0 candidates) against the live corpus text, matching the ruling.

### For QA

- The 120 remaining zero-yield detected sections (633 - 513) are, on
  spot-check, overwhelmingly bucket-D-shaped (copulative/passive prose:
  `"Son bienes las cosas..."`, `"los pasivos se definirán como..."`) or
  use an idiom outside the measured set (`"se refiere a"` as a QUOTED-
  term idiom, distinct from the already-handled UNQUOTED `"se refiere
  a"` in bucket B) -- none were force-fixed, per the brief's explicit
  instruction not to widen into bucket D. Not re-catalogued into buckets
  by name; flagging so QA's P4 sweep does not mistake "still zero" for
  "newly regressed."
- Every candidate corpus-wide was swept for a >120-char term as a
  fabrication tripwire (see above); QA may want to re-run a similar
  sweep independently rather than trusting this report's number alone,
  per the sprint's "I will run my own version of this check" standing
  instruction.
- No `determine_chapter_scope` work done; `test_pr_profile_scope.py`
  stays xfail, unchanged, core-gated per M-R3.

### Design choices / residual risk on the record

- The quoted-idiom set (`significa`/`significará`/`será`/`es`) is
  deliberately NOT widened to include `se refiere a` (seen used both as
  an unquoted-colon idiom, already handled, and as a quoted-bare idiom,
  NOT handled) -- widening the idiom alternation used by the bare-idiom
  patterns has a wider blast radius (it's shared with the dispatch-
  fallback lead-in check) than I was willing to take unilaterally against
  a corpus-wide check I could only run once at the end. Flagging as a
  candidate follow-up, not fixing now.
- The 100-char bound on the 3 unquoted forward-searching patterns and the
  quoted-vs-unquoted pattern-group split are both NEW precision
  disciplines this cycle needed that weren't anticipated by the RED
  tests (which only pin recall on the diagnosed shapes, not corpus-wide
  precision) -- worth the Planner/manager knowing this class of "search
  forward for a distant separator" bug exists as a pattern to watch for
  in any future extension of this module.

### Pushed

```
d02ffed dev: cycle-2 fixes for PR extraction/heading gaps (53 RED tests -> green)
```
Branch `claude/defs-us-pr`, pushed to origin.

---

## 2026-08-04 — Manager: cycle-2 verification, TWO ESCALATIONS, sprint paused

### Verification of the Developer's cycle 2 (all run by me)

- Boundaries: `git diff --name-only 6d94809...HEAD` → `pr_profile.py` + this
  log ONLY. No test, no fixture, no shared module. Held.
- Full suite: **`772 passed, 6 xfailed`**, zero failures. The 6 xfails are
  all `test_pr_profile_scope.py` (core-gated); none XPASSed.
- My own full-corpus run (independent script, not the Developer's):

```
headings detected: 633/635, false positives: 0
  the only 2 not detected are the 2 Table-of-Contents rows — CORRECT rejections
extraction on rows the panel never vendored: 507/627 = 80.9%   (cycle 1: 56.4%)
total terms extracted: 5,594
```

Heading detection is now effectively **635/635 correct decisions with zero
false positives** corpus-wide. Extraction went 0% → 56.4% → 80.9%.

- **Precision audit** (mine — the failure mode I most expected after a
  widening pass): term length min 2 / median 16 / p95 45 / **max 102**;
  **0 terms over 120 chars**, 0 empty terms, 9 of 5,594 terms containing ≥2
  periods. Before the Developer's own precision fixes there were 290
  fabricated long terms — he found that himself via a corpus check and fixed
  it structurally rather than with a length cap. No fabrication smell remains.
- **Ruling M-R7 re-verified live**: all three correct-zero rows still return
  exactly 0 candidates.

### Residual 120 zero-yield sections — categorized, and they are NOT one thing

| Class | Rows | Disposition |
|---|---|---|
| **D — copulative/prose definitions** | **84** | **ESCALATION 2 (director)** |
| M-R7 correct-zero (conditions / `"En General"` labels) | 3 | Settled, correctly zero |
| Still-fixable panel workload | **33** | Cycle 3 — no director input needed |

The 33 are ordinary remaining gaps, e.g. `El término "equipo solar"
significa todo equipo…` (`STATE_PR_LEY_133_1979_ART1` — the `El término
"X" significa` lead-in shape), `a) Documento acreditativo - significará…`
(`STATE_PR_LEY_209_2016_ART2`), `(a) Sociedad.- … el término "sociedad"
incluye…` (`STATE_PR_RENTAS_SEC1070_01`). These are a normal Planner→
Developer cycle, not a judgment call. I am NOT folding them into the
director question and I am NOT letting them be mistaken for done.

### ESCALATION 1 — cross-sprint seam conflict (M-R3), for the program manager

Core published its `## Seam spec` while this sprint's cycle 2 was running
(`origin/claude/defs-core-scope` @ `9272f6e`). It is a **rule-registry**
model: `register_heading_rule` / `register_entry_splitter_rule` /
`register_term_clause_rule` / `register_scope_trigger_rule`, keyed by
`jurisdiction_codes`, consumed **baseline-first, registry-second** — and it
states family panels build "new rule MODULES registered into the seam —
broader phrase/marker/heading coverage, **not new mechanism**."

That contradicts this sprint's published seam proposal (`PRProfile` as a
distinct Spanish profile class, the `HebrewProfile` sibling), which core's
Planner wrote its spec without having seen. Core's spec keeps IL on
`HebrewProfile` and puts every `US-*` code on `USProfile` + registered
rules; it contains no carve-out for a non-English US jurisdiction.

Mechanically core's model *can* carry PR — `USProfile`'s baseline returns
False on Spanish headings and empty on Spanish bodies (zero newlines defeat
its line splitter), so PR rules would always get their turn under
baseline-first. The disagreement is about guarantees, not feasibility, and
it is a real one, so it goes up rather than getting decided by me.

### ESCALATION 2 — bucket D, program standing question Q-1 (P-R2)

84 real PR definitions are copulative/prose with no entry marker and no
canonical defining idiom. Under ABSOLUTE ZERO-MISS they are misses and gate
P4 fails. Capturing them means matching Spanish copulative prose, which will
fire on ordinary substantive text corpus-wide — the exact zero-miss vs.
zero-false-positive conflict P-R2 says panels must never settle silently.
Real examples are in the escalation returned to the program manager.

### Sprint state at pause

Not blocked in the harness sense (`qa_cycles` is 0, not 5) — paused on two
escalations plus a known 33-row cycle-3 workload. **QA has not yet run**:
every verdict in this log is Planner + Developer + my own independent
verification, which is NOT the same thing as the independent QA role, and
gate P4 formally belongs to QA. Recorded honestly rather than claimed.

---

## 2026-08-04 — Planner: cycle 3 — both escalations resolved, heading-anchored
bucket-D rule, idiom re-triage, ordinary-workload recount, item 8 authored

Both escalations from cycle 2 are RESOLVED by the director: bucket D gets a
NARROW heading-anchored rule (in scope THIS cycle, per the ruling — no
general Spanish prose matcher); the seam question (B) is routed to core, and
I keep `pr_profile.py`'s Spanish rule logic as plain module-level functions
(seam-agnostic, survives either ruling on core's side). Read the full brief,
CodeGraph-explored `pr_profile.py`/`profiles.py`/`matcher.py` before any Read
(per the director's mandatory-tooling order), read every existing PR test
file to match established conventions before writing new ones. Role
boundary held throughout: I read `pr_profile.py` to diagnose, I did not edit
it (`git status --short` confirms only fixtures/tests/contract/log touched).

### Method — I did not trust the manager's crude bucket-D split or my own
first pass

The manager's own split script (`scratchpad/mgr_bucketD_split.py`) is a
regex-substring heuristic run once and handed off as 65/19. I re-derived the
split LIVE against `pr_profile.py` in three escalating passes (scripts in
`scratchpad/planner_c3_survey.py`/`planner_c3_survey2.py`, never committed),
each pass catching a real defect in the previous one:

1. **First pass** reproduced the crude 65/19 almost exactly, then simulated
   widening the idiom set to include `se refiere a`/`se referirá a` (by
   monkey-patching copies of the module's regex objects in a scratch script
   — never touching the real file) to see which residue rows the director's
   framing predicted would move. Only 1 of the director's 4 named rows
   (`STATE_PR_LEY_66_2011_ART3`) is actually solved by idiom-widening alone.
2. **Second pass** found my own first classification heuristic (crude
   "does the body contain ANY quote character" check) was ALSO wrong on two
   fronts: (a) a REAL, previously-uncatalogued corpus artifact — a
   page-break scrape footer (`"Rev. <date> www.ogp.pr.gov Página N de M
   "<Law Title>" de <year> [Ley N-YYYY, según enmendada]"`, 370 corpus-wide
   rows) — can inject an UNRELATED quoted law title anywhere mid-body,
   wrongly reclassifying 5 genuinely copulative Civil-Code rows (e.g.
   `STATE_PR_CIVIL_ART1223`, `"La retención es la facultad..."`) as
   "quote-mechanical gaps" they are not; (b) a naive substring check on
   the heading-anchor term missed the "Definición de X" single-clause shape
   entirely (no `;`/`,`/em-dash delimiter at all).
3. **Third pass** fixed both: stripped the footer boilerplate before any
   quote-presence check (regex `Rev\.\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s+
   www\.ogp\.pr\.gov\s+Página\s+\d+\s+de\s+\d+\s+["“][^"”]+["”]\s+de\s+\d{4}
   \s+\[Ley[^\]]*\]`), added a "Definición de X" single-clause anchor
   extraction (the term is the prepositional object of "de" WITHIN the same
   clause that also satisfies the stem match — reused `pr_profile.py`'s own
   `_matches_definicion_stem`/`_CLAUSE_DELIM_RE` for this, imported for
   analysis, never duplicated), and searched the FULL body (no artificial
   window) since one real anchor (`STATE_PR_LEY_77_1957_ART36_020`'s
   "Sistema de logias") sits at the very END of a 472-char single-sentence
   body.

### Bucket D final result: 70 anchored / 7 residue (down from crude 65/19)

Full accounting (verified self-consistent): 120 zero-yield sections total
(post-cycle-2, unchanged) = 3 M-R7 correct-zero (unchanged, not
re-litigated) + 1 fully solved by idiom-widening + 1 NEW correct-zero found
+ 70 heading-anchored + 7 residue + 37 ordinary workload. 70+7+37+1+1+3=119
... plus the 1 idiom-widening-solved row = 120. Every number reconciles.

The manager's ORIGINAL anchored set (65) and my refined set (70) are NOT
the same 65 rows plus 5 more — 5 of the manager's original 65 got
reclassified OUT (the footer-artifact false positives, item 2 above) while
5 DIFFERENT rows got reclassified IN (the "Definición de X" shape recovers
4; the footer-strip fix recovers `STATE_PR_LEY_77_1957_ART36_020` itself,
whose OWN footer sits early enough to have tripped my first-pass
mis-classification too before I fixed it). Net: same count, materially
different — and more correct — membership.

**Final residue (7, by `act_id`, each independently diagnosed — full table
in the contract's `## Bucket D final split (cycle 3)`)**:
`STATE_PR_CIVIL_ART1526` (nominalization mismatch), `STATE_PR_LEY_
77_1957_ART35_020` (bare heading, no term named), `STATE_PR_LEY_
77_1957_ART42_010` (term never repeated verbatim), `STATE_PR_CIVIL_ART1293`
(heading/body term MISMATCH — heading names "las normas de la compraventa",
body actually defines "permuta"), `STATE_PR_LEY_77_1957_ART4_010`
(meta-heading about definitions in general), `STATE_PR_PENAL_ART15` (second
bare-heading example), `STATE_PR_LEY_77_1957_ART5_030` (non-contiguous
term — "un activo es uno no admitido" vs. heading's "Activo no Admitido").

**For the Developer**: the new function is `extract_heading_anchored_
definition(heading, body, *, scope) -> list[DefinitionCandidate]`. I did
NOT implement it (role boundary) — the tests pin the OUTCOME (which real
rows must yield exactly 1 candidate with which term, which must yield []),
not the mechanism. My own scratch-script prototype (never committed) used:
strip section-number prefix (reuse `_SECTION_LABEL_RE`/
`_SECTION_NUMBER_TOKEN_RE`), strip a fully-enclosing paren wrapper (reuse
the existing gap-2 logic), clause-split on `_CLAUSE_DELIM_RE`, for each
clause either (a) if it does NOT match `_matches_definicion_stem`, strip a
leading Spanish article and treat it as a candidate term, or (b) if it DOES
match the stem AND is shaped `"Definici(ón|ones) de X"`, capture `X` (article-
stripped) as an ADDITIONAL candidate term. Then, for each candidate term
(longest/most specific first, my prototype didn't need to disambiguate
since no real row had 2 competing candidates), fold-normalize (NFD +
strip combining marks) both term and a FOOTER-STRIPPED copy of the body,
and require a `\b`-word-boundary literal match. If found, definition_text
should be the SENTENCE containing the match (or the whole body if no
sentence boundary is obvious) minus any footer boilerplate — my prototype
used a plain sentence-boundary heuristic; the exact `definition_text`
extraction is NOT pinned by any test beyond "contains the real prose,
excludes footer noise" (see `test_page_break_footer_boilerplate_does_
not_block_or_corrupt_the_real_anchor`).

### Idiom re-triage: `se refiere a`/`se referirá a` — a real recall-vs-FP
conflict, resolved in-panel (not escalated)

Corpus survey (full 23,636 rows, live-derived): `se refiere a` 180
corpus-wide/85 canonical/3 among current zero-yield; `se referirá(n) a` 22/
9/2; `se entenderá(n)` (excl. already-handled `...por`) 646/52/4; `se
considera(rá) como` 303/30/5 (a further sibling idiom, found via
re-triaging `STATE_PR_LEY_155_1937_SEC1` — only 1 of its 5 zero-yield rows
diagnosed this cycle, the other 4 flagged as follow-up, NOT built into this
cycle's item plan).

Simulated widening `_DEFINING_IDIOM_ALTERNATION` to include `se refiere
a`/`se referirá a` (scratch monkey-patch, never touching the real file):
safe when scoped to the per-block QUOTED patterns
(`_QUOTED_TERM_COMMA_IDIOM_RE`/`_QUOTED_TERM_BARE_IDIOM_RE` — these only
ever fire on a block that already starts with a quote character). UNSAFE
when the SAME widened alternation reaches the DISPATCH-FALLBACK check
(`_UNQUOTED_BARE_IDIOM_TERM_RE`): `STATE_PR_LEY_214_2004_ART2`'s real body
opens `"Todo término utilizado en esta Ley para referirse a una persona o
puesto se refiere a ambos géneros..."` (a gender-neutrality boilerplate
disclaimer) — widened, this disclaimer ITSELF satisfies the dispatch
fallback's bare-idiom shape and swallows the row's entire 26-real-term
marked list into ONE fabricated "term" (verified live: 26 correct terms →
1 fabricated term). Per the standing director policy this is exactly a
recall-vs-false-positive conflict CLASS — but I did NOT escalate it,
because it resolves the same way M-R4/P5's English-preamble collision
already does in this exact codebase (widen, but pin a SCOPED regression
guard proving the dangerous path stays closed) — a precedented, in-panel-
resolvable pattern, not a genuinely undecidable tradeoff needing director
arbitration. Pinned as a permanent regression guard
(`test_widening_must_not_swallow_a_markers_lead_in_disclaimer_into_
one_fabricated_term`, GREEN from day one since the unfixed code has no
`se refiere a` recognition at all yet to regress).

**Correction to the director's own framing** (recorded honestly, not
buried): of the 4 rows the director named as "se refiere a"/idiom-shaped,
only `STATE_PR_LEY_66_2011_ART3` is a PURE idiom gap. The other 3
(`STATE_PR_LEY_26_1941_ART57`, `STATE_PR_LEY_141_2002_ART6`,
`STATE_PR_LEY_420_2004_ART2`) are all the SAME "unquoted lead-in before a
quoted term" family — the block does not START with a quote character, so
`_extract_term_and_definition` never even tries the quoted patterns where
a widened idiom would help (per its own documented, deliberate quoted-vs-
unquoted pattern-group split). `STATE_PR_LEY_141_2002_ART6`/`_420_2004_
ART2`'s own idiom word is `es` — ALREADY recognized; their defect is purely
structural (lead-in), not idiom vocabulary. All 3 moved to the ordinary-
workload bucket, not the residue and not the idiom file.

### Ordinary workload recount: 37 (up from crude 33)

Per the brief's explicit instruction to recount rather than trust the
crude 33. Six independently-diagnosed shapes (full detail + real examples
in `test_pr_profile_extraction_cycle3.py`'s module docstring): (1) `"El
término 'X' <idiom>"` unquoted lead-in, no marker
(`STATE_PR_LEY_133_1979_ART1`); (2) same family with an interjecting scope
phrase (`STATE_PR_LEY_141_2002_ART6`); (3) a NEW idiom, `se considera
como`, behind the same lead-in shape (`STATE_PR_LEY_155_1937_SEC1`); (4)
unquoted term with a scope clause INTERJECTED between the term and its own
idiom verb (`STATE_PR_LEY_9_2020_ART2`, `"Mujer trabajadora, a los fines de
esta Ley, significará..."`); (5) the corrected `se referirá a` row
(`STATE_PR_LEY_26_1941_ART57`, see above); (6) the highest-marker-count
(37) remaining row, a `"Label.-El término 'X' se interpretará que
significa"` shape (`STATE_PR_RENTAS_SEC1010_01`) — pinned at FLOOR
granularity only (>=1 candidate), not exact terms, since the correct
mechanism (label vs. re-quoted term) is a genuine Developer design choice.

**A new correct-zero guard found via re-triage, not a gap**:
`STATE_PR_LEY_48_2018_ART3` — `"...se adoptan las definiciones de la Ley
38-2017, conocida como, "Ley de Procedimiento Administrativo Uniforme...""`
— a WHOLESALE cross-law/TITLE deferral, the SAME shape as the already-
pinned `STATE_PR_LEY_52_2019_ART3` guard. The quote is a LAW TITLE via
`conocido como` (already flagged by the cycle-1 survey as overwhelmingly
law-naming, not term-defining) — pinned as MUST-STAY-ZERO, guarding
against a future `se considera como`/`conocido como` widening fabricating
a "term" out of a law's own title.

### Item 8 — authored, xfail, core-gated (per program manager instruction,
not dropped a third time)

`backend/tests/integration/test_pr_profile_definitions_section_
end_to_end.py`, mirroring `test_us_profile_definitions_section_end_to_
end.py`'s exact Stage-1-to-3 chain shape. Live-confirmed the CURRENT
failure point before writing the xfail reason (not guessed):
`get_profile("US-PR")` resolves to `USProfile(code="US-PR")` today
(`is_definitions_heading('Artículo 3. Definiciones')` → `False` under that
profile) since `PRProfile` is not yet registered (item 7, core-gated).
Confirmed via `--runxfail` that the test fails EXACTLY at the Stage-1
assertion, not at an unrelated import/collection error. Reuses the
already-vendored `STATE_PR_LEY_249_2003_ART3` (cycle 1) — no new fixture
needed.

### Fixtures vendored

25 REAL rows, `backend/tests/fixtures/us_statutes/pr_sample_rows_cycle3.
json`, byte-compared against a fresh parquet read immediately after
writing (`25 rows checked, 0 problems — ALL BYTE-IDENTICAL`). Full
per-row provenance in the fixtures README's new `## pr_sample_rows_
cycle3.json` section. `act_id`s: `STATE_PR_CIVIL_ART236`, `STATE_PR_LEY_
77_1957_ART5_020`, `STATE_PR_CIVIL_ART1264`, `STATE_PR_CIVIL_ART1508`,
`STATE_PR_CIVIL_ART326`, `STATE_PR_RENTAS_SEC2030_03`, `STATE_PR_LEY_
77_1957_ART36_020`, `STATE_PR_CIVIL_ART1139`, `STATE_PR_CIVIL_ART1526`,
`STATE_PR_LEY_77_1957_ART35_020`, `STATE_PR_LEY_77_1957_ART42_010`,
`STATE_PR_CIVIL_ART1293`, `STATE_PR_LEY_77_1957_ART4_010`, `STATE_PR_
PENAL_ART15`, `STATE_PR_LEY_77_1957_ART5_030`, `STATE_PR_LEY_66_2011_
ART3`, `STATE_PR_LEY_214_2004_ART2`, `STATE_PR_LEY_26_1941_ART57`,
`STATE_PR_LEY_133_1979_ART1`, `STATE_PR_LEY_141_2002_ART6`, `STATE_PR_LEY_
155_1937_SEC1`, `STATE_PR_LEY_9_2020_ART2`, `STATE_PR_LEY_48_2018_ART3`,
`STATE_PR_RENTAS_SEC1010_01`, `STATE_PR_CIVIL_ART263`. Plus 1 REUSED row
from cycle 2 (`STATE_PR_LEY_15_1931_SEC22`, no duplicate vendoring).

### Tests authored, RED proof

5 new files: `test_pr_profile_bucket_d_heading_anchored.py` (18 tests, all
RED via `ImportError` — `extract_heading_anchored_definition` does not
exist yet), `test_pr_profile_idiom_widening_cycle3.py` (1 RED + 1
GREEN-from-day-one regression guard), `test_pr_profile_extraction_
cycle3.py` (6 RED + 1 GREEN correct-zero guard), `test_pr_profile_corpus_
floor_cycle3.py` (extends the item-12 floor pattern with 5 new
parametrized groups — 23 RED + 3 GREEN), `backend/tests/integration/
test_pr_profile_definitions_section_end_to_end.py` (1 xfail, item 8). No
existing test file edited (`git status --short` confirms).

```
$ backend/.venv/bin/pytest backend/tests -q
48 failed, 777 passed, 7 xfailed, 18 warnings in 13.51s
```

777 = cycle-2's 772 baseline + 5 new GREEN regression/correct-zero guards
(1 idiom-widening precision guard, 1 correct-zero guard in extraction_
cycle3, 3 in corpus_floor_cycle3 — the correct-zero guard, the
must-not-collapse guard, and the bookkeeping sanity test). 7 xfailed =
6 baseline (`test_pr_profile_scope.py`) + 1 new (item 8). Re-run with the
5 new files excluded to confirm the 772 baseline is unmoved:

```
$ backend/.venv/bin/pytest backend/tests -q --ignore=<5 new files>
772 passed, 6 xfailed, 18 warnings in 13.22s
```

`--runxfail` confirms item 8's test fails exactly at Stage 1
(`is_definitions_heading` assertion), not an unrelated error:

```
$ backend/.venv/bin/pytest backend/tests/integration/test_pr_profile_definitions_section_end_to_end.py --runxfail -v
AssertionError: assert False is True
 +  where False = is_definitions_heading('Artículo 3. Definiciones')
 +    where is_definitions_heading = USProfile(code='US-PR').is_definitions_heading
```

### For the Developer (sequencing)

Items 13-16 are pre-core OK (same module, `pr_profile.py`, no shared-
module edit) — start there. Item 17 (item 8) stays `xfail` until items 6/7
land (registry wiring is still core-gated per M-R3). Diagnoses to save you
re-discovery time: (1) the page-break footer-boilerplate regex (module
docstring of `test_pr_profile_bucket_d_heading_anchored.py`) — strip it
BEFORE any quote-presence check anywhere you add one, not just for the
heading-anchor rule; (2) the idiom-widening scope boundary (per-block
quoted patterns only, never the dispatch-fallback check) — do not widen
`_DEFINING_IDIOM_ALTERNATION` itself if it's shared by both; consider a
SEPARATE, wider alternation used only by the two quoted-block patterns;
(3) the "Definición de X" single-clause anchor extraction needs the SAME
article-stripping as the existing multi-clause path — I found this by
testing, not by inspection, so double-check your own implementation
against `test_definicion_de_x_family_bare_string_cases` and
`test_definicion_de_x_single_clause_anchor_real_row` directly, don't
assume the shape is obvious from the docstring alone.

### Escalations

None. The `se refiere a` recall-vs-FP conflict (above) was real but
resolved in-panel per precedent (M-R4/P5), not escalated, per the standing
policy's own text ("escalates... rather than deciding it" — this was
decided with data and a precedented resolution pattern already in the
codebase, not a coin-flip).

### Pushed

```
06032fd planner: cycle-3 heading-anchored bucket-D rule, idiom re-triage, item 8
```
Branch `claude/defs-us-pr`, pushed to origin.

---

## Archived from contract (manager, 2026-08-04) — contract_lint size budget

Moved verbatim out of `2026-08-04-defs-us-pr.md` so the contract fits its
400-line budget. Nothing is edited; this is relocation, not revision.


### Archived from contract — Spanish idiom survey

## Spanish idiom survey (measured)

Planner survey, run against the FULL `us_pr_statutes.parquet` (23,636 rows,
never downloaded — read once from the on-disk HF snapshot via a scratchpad
script, no test reads it). Supersedes the recon's 4,000-row translation-guess
lead per M-R2. Full per-shape tables, real `act_id` examples, and the raw
survey scripts' output are in the panel log
(`2026-08-04-defs-us-pr-log.md`, "Planner survey detail" entry); this section
is the dense summary the item plan below is built on.

**Headings.** 652 rows contain the `defini` substring; only 635 are genuine
(12 are "Aportaciones **Definidas**" — Defined Contributions, a pension term
of art; 2 are "sentencia **definitiva**" — final judgment; 3 are unrelated
verb forms in amendment-text headings). Of the 635 genuine rows: **475 are a
bare `Definiciones`/`Definición` heading** (after stripping the
`Artículo N.`/`Sección N.` prefix — 463 plural, 10 singular, 2
parenthesized), **160 are compound** (`"Definiciones Generales"`,
`"Bienes; definición"` (single-term Civil-Code-style), `"Definiciones
aplicables a las Zonas de Oportunidad"`, etc.). **9/635 (1.4%) have a REAL,
not-injected data-quality artifact**: `section_title`/`text` are split at a
fixed ~200-char boundary that lands mid-word (verified: `STATE_PR_LEY_
135_1979_ART1`'s heading ends `"...Estado Libre Asoc"`, `text` resumes
`"iado de Puerto Rico..."` — one word torn across both columns), the PR
analog of the DE mojibake / PA-collision findings in this same fixtures
directory. **Verdict**: a first-word-OR-last-word-with-Spanish-preposition-
exclusion rule (mirroring `USProfile.is_definitions_heading`'s shape, but
matching the stem `[Dd]efinici[oó]n(es)?`, never the bare substring `defin`)
handles all measured cases, including the truncated-artifact rows (first-
word-anchored) and correctly rejects a Table-of-Contents listing that merely
names a "Definiciones" article as one line-item (neither first nor last
word of ITS OWN heading).

**Definition idioms in bodies** (rows containing ≥1 match, corpus-wide /
within the 635 canonical rows): `significa` 596/322, `significará` 340/119,
**`tendrán el significado` 309/238 and `tendrá(n) los significados` 71/60 —
combined ~305/635, i.e. comparable in frequency to `significa` itself and
MISSING from the recon's lead entirely**, `incluye` 2350/233
(mostly substantive prose, not a defining idiom on its own — high false-
positive risk as a standalone signal), `se define`/`se define como` 398+23/
85+13, `según se define` 265/54, `comprende` 145/24, `se entenderá por`
62/9 (the recon's #3 lead — real, but far rarer than `tendrá(n) el/los
significado(s)`), `se entiende por` 15/2, `quiere decir` 7/3, `denota` 1/1
(negligible). **Verdict**: `significa(rá/n)` and `tendrá(n) el/los
significado(s)` are CO-DOMINANT, not one dominant idiom — an idiom list
built only from the recon's lead would silently miss ~40% of canonical
sections' own idiom vocabulary.

**Entry markers** (within the 635 canonical rows, ≥2 occurrences =
genuine list, not a coincidental single hit): letter-full-paren `(a)` 272,
digit-full-paren `(1)` 109, letter-close-paren-only `a)` (no opening paren —
a distinct, newer-law convention) 82, digit-period `1.` 44, letter-period
`a.` 34, digit-close-paren-only `1)` 13 — **461/635 (72.6%) have a genuine
multi-entry marker of one of these 6 shapes**. **174/635 (27.4%) have NO
list marker at all** — mostly single-term Civil-Code-style articles (one
definition, sometimes the term repeated inline with an em-dash: `"Secretario.
— Significa el Secretario de Hacienda."`, sometimes not repeated at all:
`"Son bienes las cosas o derechos que pueden ser apropiables..."` for heading
`"Bienes; definición"`). **Critical structural finding: PR body text has
ZERO newlines within a Definiciones section (0/635 verified)** — unlike the
DE/CA English fixtures, every marker sits inline in one continuous string,
so `USProfile._split_into_numbered_blocks`'s `text.split("\n")`-based
approach cannot be reused as-is; a Spanish extractor must scan the
continuous string directly (closer in shape to `pipeline.py`'s
`_extract_inline_quoted_definitions`). Term/definition separator: quote+colon
26 rows, quote/unquoted+em-dash 220 rows combined, or no punctuation at all —
the verb idiom itself is the separator (`Significa`/`Es`/`Será` directly
after the term). Quote style: curly `""`  437/635, straight `"` 76/635, ZERO
mojibake byte-corruption anywhere in the 23,636-row corpus (unlike RI's
`us_statutes.parquet`) — not a PR data-quality issue.

**Scope phrases** (corrected for a `\b`-boundary bug in an earlier pass that
inflated the "A los..." counts by bleeding in "Para los..." — see log for
detail). Within the 635 canonical rows: LAW-WIDE phrasing dominates —
`Para propósitos de (general)` 98, `A los efectos de (general)` 48, `Para
propósitos de esta Ley` 65, `A los fines de esta Ley` 51, `A los efectos de
esta Ley` 30. CHAPTER scope is rare but real — `A los efectos de este
Capítulo` 5, `A los fines de este Capítulo` 2 (real example:
`STATE_PR_LEY_77_1957_ART30_020` opens `"A los fines de este Capítulo,
..."`). **ARTICLE scope (`"local"`) NEVER sets a canonical section's own
scope — 0/635 for `A los fines/efectos/propósitos de este Artículo` inside a
canonical section**; corpus-wide (i.e. OUTSIDE canonical sections) the same
phrase occurs 16 times (`A los fines de este Artículo`) + 26 times (`Para
propósitos de este Artículo`), always as an AD-HOC definition embedded in an
ordinary substantive article (real example: `STATE_PR_LEY_85_2018_ART9_04`,
`'A los fines de este Artículo "cualquier tipo de arma" incluye...'`) — a
clean, corpus-confirmed, mutually-exclusive split mirroring Hebrew's
section-heading-scope vs. `extract_local_definitions` split exactly.

**Citation grammar** (corpus-wide row counts): `Ley N-YYYY` dash form
(e.g. `"Ley 404-2000"`) 7,052 — the dominant PR citation shape, no English
analog; `Ley Núm. N de <date>` 2,194; `Artículo N de esta Ley` 1,123; bare
`§ N` 2,249 (the symbol itself is language-neutral); `L.P.R.A.` 2,498
(PR's own citation-reporter abbreviation, PR's analog of `U.S.C.`).

**Definitions OUTSIDE canonical Definiciones sections** (director mandate,
gate P2): `(en adelante, "X")` 49 corpus-wide (genuine short-name
apposition, no idiom verb, no quotes — `"...Comité de Acción... (en
adelante, Comité)..."`); `(en lo sucesivo, "X")` 1; `denominado/a` 182 (MIXED
— some are genuine appositions, many are fund/program naming, e.g. `"fondo
especial denominado 'Fondo de los Títulos V y VI'"` — a false-positive risk
if treated as a blanket signal); `conocido/a como` 2,191 (OVERWHELMINGLY a
law-title-naming idiom — `"conocida como 'Ley de...'"` — NOT a term
definition in the vast majority of instances; a high-precision-risk signal,
flagged for the zero-false-positive discipline, not recommended as a P2
extraction trigger without much narrower gating). **Verdict**: `A los fines/
propósitos de este Artículo` (ad-hoc local, 42 corpus-wide) and `en
adelante` (inline apposition, 49 corpus-wide) are the two SAFE, high-
precision non-canonical signals; `conocido como`/`denominado` are real but
need much narrower gating than a bare substring match before they could be
added without a false-positive blowup — flagged as a documented follow-up,
not built into this pass's item plan.

**Out-of-contract observation** (per the manager's note): `us_pr_
constitutions.parquet` was NOT surveyed (out of contract scope) — flagging
to the manager per instruction, not absorbing into this sprint's scope.

### Cycle-2 corrections (Planner, cycle 2, 2026-08-04)

Cycle 1's survey above stands; nothing in it was wrong. What follows are
CORRECTIONS/ADDITIONS the manager's full-corpus sweep forced (694 passed / 6
xfailed on the fixture suite, but only 56.4% real extraction coverage and
15/635 real heading misses when run over the full 23,636 rows — see the
log's "Manager: Developer verification + GENERALIZATION GAP" entry and
ruling M-R6). Full diagnosis with live-verified transcripts is in this
cycle's panel log entry and in `test_pr_profile_extraction_cycle2.py` /
`test_pr_profile_headings_cycle2.py`'s module docstrings; this is the dense
summary.

**Entry-marker inventory: two genuine new gaps found, one false lead ruled
out.** M-R6 characterized 22 zero-yield rows as bucket C, "marker-inventory
gap." Live-diagnosing both of M-R6's own named examples
(`STATE_PR_LEY_430_2000_ART3`'s `A.`/`B.`/`C.`... markers,
`STATE_PR_LEY_190_1995_ART2`'s `a. —`/`b. —`... markers) against the live
code shows `_ENTRY_MARKER_RE` **already matches both** — the period-marker
alternative's `[a-zA-Z]` class is case-insensitive by construction, and the
regex has no trouble with a marker immediately followed by a decorative
dash. Neither is a marker-recognition gap. But the re-survey mandate DID
turn up two real, previously-uncatalogued gaps while diagnosing bucket A/B
rows directly:
  - **A genuine new marker shape**: traditional Spanish alphabetical
    enumeration treats **"ch" as its own letter**, producing a real
    TWO-CHARACTER letter marker `ch)` (`STATE_PR_LEY_46_2008_ART3`:
    `"...c) expresiones...; ch) normas de seguridad..."`).
    `_ENTRY_MARKER_RE`'s letter alternatives are all single-character
    (`[a-zA-Z]`) — `ch)` matches none of them (confirmed live: this row's
    marker scan finds only 6 markers, `a) b) c) d) e) f)`, never `ch)`).
  - **A genuine block-prefix gap** (not a marker gap): a marker can be
    followed by a DECORATIVE em-dash before the actual term
    (`STATE_PR_LEY_190_1995_ART2`: `a. — "Nueva programación"
    significa...`) — the marker itself matches, but no separator pattern
    expects the block to start with a bare dash before the term.
  - **An entry-marker FALSE-POSITIVE, found via bucket B, not bucket C**:
    `_ENTRY_MARKER_RE` misfires on spaced abbreviations. `STATE_PR_LEY_
    51_2003_ART2`'s body contains `"U. S. Geological Survey"` three times
    inside entry prose; `S.` alone (single letter, preceded by `U. ` which
    ends in a period+space) is indistinguishable from a genuine
    letter-period marker today, fragmenting `definition_text` mid-sentence.
    This is a PRECISION defect (over-splitting), the mirror image of the
    zero-miss recall gaps — flagged distinctly because it is not caught by
    any zero-miss sweep, only by reading a row's actual extracted text.

**Real root cause of the 153-row bucket A (all zero-yield despite real
markers + real idioms — corrected from suspicion to live-verified fact):**
`_extract_term_and_definition`'s 3 separator patterns
(quoted+colon, quoted+typographic-dash, unquoted+typographic-dash) do not
cover the shapes that actually dominate the corpus. Six independently
confirmed failure shapes (see extraction test file docstring for the exact
live-diagnosed examples and mechanism for each): quoted term + idiom verb
with NO separator character at all (curly or straight quotes — the
majority shape, ~133/153 rows); quoted term + comma + idiom; quoted term +
ASCII hyphen-minus (not a typographic em/en dash) + idiom; quoted term, no
separator, no idiom verb (bare capitalized definition); unquoted term +
colon (no `_UNQUOTED_TERM_COLON_RE` exists at all); unquoted term + its OWN
trailing period (not colon, not dash) + bare definition. None of these are
quote-character bugs — the quote character was never the issue.

**A dispatch-logic gap, found via bucket B, not named in M-R6 at all**:
`extract_definitions_from_section`'s dispatch is all-or-nothing — `if not
markers: <single-entry path> else: <markers path>`. When a genuinely
single-entry, no-top-level-marker article (`STATE_PR_LEY_77_1957_ART9_040`:
`"Agente General es la persona nombrada..."`) happens to contain an
INCIDENTAL enumerated sub-list of that one term's own duties
(`(1)`..`(11)`), the presence of ANY marker anywhere sends the whole body
down the markers path, which has no "entry −1" for text before the first
marker — the term and its lead-in definition are silently discarded and 11
bogus fragment entries are produced instead.

**Heading misses: re-diagnosed as one clause-scoping gap plus one
orthogonal parenthesis-stripping gap, not 5 unrelated shapes.**
`is_definitions_heading` only checks the first-or-last substantive token of
the WHOLE heading tail. Live-checking each of the 13 real misses shows 11
of them share ONE root cause: real PR headings frequently place
"definición(es)" as the first (or trailing-preposition-suffixed) word of an
INNER semicolon-, comma-, or em-dash-delimited CLAUSE, not of the whole
tail (`"Parentesco; definición y alcance"`, `"Microseguros, definición y
clases autorizadas"`, `"Obrero o empleado, definición de"`, `"...
—Definición de Términos"`, and — needing clause-splitting at BOTH a comma
AND a semicolon level — `"Agregado, Definición de; Limitado a Un Solo
Predio; ..."`). The remaining 2 (`"(Definiciones)"`, both fully
parenthesized) need an orthogonal, independent fix: strip an enclosing
`(...)` wrapper before the existing rule runs — parentheses are not in
`_TAIL_TOKEN_SPLIT_RE`'s split class today, so `"(Definiciones)"` tokenizes
as one un-matchable token. Both TOC rejections
(`STATE_PR_LEY_165_2020_ART1_2`, `STATE_PR_LEY_51_2020_ART1_2`) stay
correctly rejected under this diagnosis: neither has "Definiciones"
adjacent to a semicolon/comma/em-dash boundary of ITS OWN heading tail — it
is buried inside a whitespace-joined TOC run-on instead.

**Correct-zero guard**: `STATE_PR_LEY_52_2019_ART3` (a real bucket-A-
workload row) is a Definiciones section whose entire body defers wholesale
to another law's definitions and defines zero local terms. This is a
correct rejection, not a miss — flagged so the fix is not over-widened to
fabricate terms out of a cross-reference sentence.

**Bucket D unchanged**: still 86 rows, still escalated, still out of
scope for this Planner pass — see M-R6.

### Cycle-3 corrections (Planner, cycle 3, 2026-08-04)

Both escalations are resolved (director rulings, see the sprint's cycle-3
brief): bucket D gets a NARROW heading-anchored rule, not a general
prose matcher; the seam question is routed to core, and the Developer
proceeds building `pr_profile.py`'s Spanish rule logic as plain module-
level functions (seam-agnostic, survives either ruling). What follows are
CORRECTIONS/ADDITIONS to the cycle-1/2 survey this cycle's re-triage
forced — cycle 1/2 stand, nothing in them was wrong.

**`se refiere a` / `se referirá a` / sibling idiom survey** (full corpus,
23,636 rows, re-derived live against the current `pr_profile.py`, not the
manager's crude categorizer):

| Idiom | Corpus-wide rows | Canonical-section rows | Among CURRENT zero-yield rows |
|---|---|---|---|
| `se refiere a` | 180 | 85 | 3 |
| `se referirá(n) a` | 22 | 9 | 2 |
| `se entenderá(n)` (excl. already-handled `...por`) | 646 | 52 | 4 |
| `se considera(rá) como` | 303 | 30 | 5 |

**Verdict, with the recall-vs-false-positive data the standing policy
requires**: `se refiere a`/`se referirá a` are safe to add to the
per-block QUOTED idiom alternation (`_QUOTED_TERM_COMMA_IDIOM_RE`,
`_QUOTED_TERM_BARE_IDIOM_RE`) — those patterns only ever fire on a block
that already starts with a quote character, so a wider idiom vocabulary
cannot suddenly start matching unrelated unquoted prose. Simulated live
(scratchpad `planner_c3_survey.py`/`planner_c3_survey2.py`, never
committed): this alone fully captures `STATE_PR_LEY_66_2011_ART3` (1 row)
with zero fabricated long terms across all 635 canonical rows re-run
under the widening.

**But the SAME widening is UNSAFE if it also reaches the DISPATCH-
FALLBACK check** (`_UNQUOTED_BARE_IDIOM_TERM_RE`, which decides whether a
MARKED body's own lead-in text before its first marker is itself a bare
single-entry definition). Confirmed live: `STATE_PR_LEY_214_2004_ART2`'s
real body OPENS with a gender-neutrality disclaimer, `"Todo término
utilizado en esta Ley para referirse a una persona o puesto se refiere a
ambos géneros..."` — widened to recognize `se refiere a`, this disclaimer
itself satisfies the dispatch-fallback shape and swallows the entire
26-real-term marked list into ONE fabricated "term" (26 correct terms →
1 fabricated term, verified live). This is the SAME structural collision
class the Developer's own cycle-2 dispatch fix already guards against for
an English preamble (`"As used in this subchapter:"`) — a different real
trigger phrase, same mechanism. Pinned as a permanent regression guard in
`test_pr_profile_idiom_widening_cycle3.py` /
`test_pr_profile_corpus_floor_cycle3.py`. **This did not need a director
escalation** — it resolves the same way M-R4/P5's English-preamble
collision already does (widen, but pin a scoped regression guard), not a
genuinely undecidable recall-vs-precision tradeoff.

`se considera como` is a real sibling idiom (303/30/5) found via
re-triaging `STATE_PR_LEY_155_1937_SEC1` — only that ONE of its 5
zero-yield rows is diagnosed and pinned this cycle
(`test_pr_profile_extraction_cycle3.py`); the other 4 need their own
individual diagnosis before a blanket widening, per the same discipline
above. Flagged as a further follow-up, not built into this cycle's item
plan.

**Idiom-gap re-triage of the 19 "residue" rows — corrected framing.** The
director named 4 rows suspected to be idiom gaps. Individually
re-diagnosed against the real text:
- `STATE_PR_LEY_66_2011_ART3` — genuinely a pure idiom gap, fully solved
  by the safe widening above (a MARKED, quoted-term row).
- `STATE_PR_LEY_26_1941_ART57` — **correction**: uses `se referirá a`,
  but is NOT a pure idiom gap. The block does not start with a quote
  character (`"Para los fines de esta Ley el término "persona
  jurídica"..."`), so `_extract_term_and_definition` never even reaches
  the quoted patterns where a widened idiom would help — it needs the
  SAME unquoted-lead-in-strip fix as `STATE_PR_LEY_133_1979_ART1` (see
  below), not idiom widening. Moved to the ordinary-workload bucket, not
  the residue.
- `STATE_PR_LEY_141_2002_ART6` / `STATE_PR_LEY_420_2004_ART2` — the
  director's own framing named these "idiom" gaps, but the actual idiom
  word here is `es` — ALREADY in the recognized alternation. The real,
  distinct defect is the same unquoted-lead-in shape (`"A los fines de la
  aplicación de esta Ley, "Sistema de Clasificación de Películas", es
  aquel..."` — unquoted scope-phrase lead-in before the quoted term).
  Moved to the ordinary-workload bucket.


### Archived from contract — Seam proposal

## Seam proposal (Planner recommendation, D2/M-R3 — cross-sprint, core Planner to review)

**Recommendation: PR becomes a distinct profile class, `PRProfile`,
registered under `"US-PR"` only — the Spanish-language sibling of
`HebrewProfile`, NOT a rule-set layered onto `USProfile`.**

Reuse audit (the deciding evidence — how much of `USProfile` a PR rule-set
could actually share):

- `is_definitions_heading`: **0% reusable.** English-literal (`Definitions?`
  stem) vs. Spanish-literal (`[Dd]efinici[oó]n(es)?` stem) — different
  regex vocabulary top to bottom, even though the SHAPE (prefix-strip,
  first-word-or-last-word-with-preposition-exclusion) is a pattern worth
  copying, not code worth sharing.
- `extract_definitions_from_section`: **~0% directly reusable, and
  structurally incompatible as-is.** `USProfile._split_into_numbered_
  blocks` is LINE-based (`text.split("\n")`) because the DE/CA fixtures'
  bodies have real newlines between entries; the real PR corpus has **zero
  newlines within any of the 635 canonical Definiciones bodies measured** —
  every marker sits inline in one continuous string. A Spanish extractor
  needs a `finditer`-based continuous-string scan (closer to `pipeline.py`'s
  `_extract_inline_quoted_definitions`), not the line-splitter. PR also has
  3 marker shapes `USProfile` has no analog for at all (letter-period `a.`,
  letter-close-paren-only `a)`, unquoted-term+em-dash with no idiom verb).
- `find_citations`: **~0% reusable.** PR's dominant citation shapes (`Ley
  N-YYYY` dash form, 7,052 rows; `Ley Núm. N de <fecha>`, 2,194 rows;
  `Artículo N`) have no English analog at all; only the bare `§ N` symbol
  coincidentally overlaps (language-neutral punctuation, not grammar).
  `L.P.R.A.` (PR's own reporter abbreviation) is PR's analog of `U.S.C.`,
  not a shared pattern.
- `detect_cross_law_derivations`: **0% reusable** — English trigger phrases
  (`"has the meaning specified in"`, `"as defined in"`) have no Spanish
  overlap; PR's idiom set (`según se define en`, `tiene el significado que
  se le asigna en`) is entirely separate vocabulary.
- `normalize_for_parsing`: 100% "reusable" only because it is a no-op
  passthrough for BOTH — not meaningful code reuse, just a coincidence that
  neither language's corpus needs wikilink/bidi handling here.

Given near-zero exploitable overlap at every layer except a no-op, forcing
PR's Spanish logic to live INSIDE `USProfile`'s shared dataclass methods
(branching on `self.code == "US-PR"`) buys nothing structurally and costs
real safety:

- **P5 consequence, by construction vs. by discipline.** A distinct
  `PRProfile`, registered ONLY under `"US-PR"` in `profiles.py`'s
  `_REGISTRY`, makes "PR rules never fire on English text" a TYPE-LEVEL
  guarantee — no `Document.jurisdiction` other than `"US-PR"` ever resolves
  to a `PRProfile` instance, the exact same registry-keying argument that
  already isolates `HebrewProfile` from every US code today. Under the
  rule-set-under-`USProfile` option, Spanish logic would have to live behind
  an `if self.code == "US-PR":` branch inside shared, ALREADY-multi-tenant
  methods every other US code's calls also pass through — a single
  misplaced or wrongly-scoped branch is a live cross-language-firing risk
  that only a test (M-R4's own test, which this sprint already authored)
  would catch, with no structural backstop underneath it. `PRProfile` needs
  that same test too (and this sprint has it,
  `test_pr_profile_no_english_regression.py`) — but it ALSO has the
  registry-level guarantee behind it, not relying on the test alone.
- **Recon's own framing.** The dossier explicitly calls PR "distinct from
  Hebrew (which has its own profile)" while diagnosing PR's problem as
  "registered under the generic `USProfile`, which assumes English" — i.e.
  the recon already frames Hebrew's solution as the template PR is missing,
  not USProfile's.
- **The line this proposal draws**: "different natural language" (PR) is a
  materially different problem from "different drafting CONVENTION within
  the same language" (VA/WA/WV's `"X" defined` verb-form heading, SC's
  bare-digit markers, DC's unquoted-term shape — all correctly handled by
  sibling family sprints as USProfile-owned rule variants). Only PR crosses
  the language line among all 53 non-IL codes; a `PRProfile` is not the
  first domino toward a 53-way profile explosion.

**Cost / what this asks of core's C4 registry**: `profiles.py`'s current
`_REGISTRY` construction (`{"IL": HebrewProfile()} .update({code:
USProfile(code=code) for code in JURISDICTION_CODES if code != "IL"})`)
needs a THIRD carve-out (`if code not in ("IL", "US-PR")`) plus one explicit
`"US-PR": PRProfile()` line — a small, shared-module edit, sequenced after
core per M-R3, not before. This sprint asks core's C4 registry design to key
on `{code: JurisdictionProfile}` (which is already `_REGISTRY`'s declared
type) rather than narrow to `{code: RuleSet-under-fixed-USProfile}` —
otherwise PR (and any future non-English US-family jurisdiction) has no
clean way to register at all.


### Archived from contract — Core seam coordination status

## Core seam coordination status (D3)

Polled per the sprint contract's Coordination clause:
`git fetch origin && git show origin/claude/defs-core-scope:docs/sprint/
sprints/2026-08-04-defs-core-scope.md`. As of this planning pass, core is at
`5b93ef8` ("acquire planner lock, open panel log, record C5 baseline") and
its contract's `## Seam spec (published)` heading exists as a TODO marker
only — no seam spec body is published yet. Confirmed via direct read of the
core contract (not just a grep for the heading text). This sprint plans and
authors RED tests against the Planner's own proposed interfaces per the
Coordination clause; `test_pr_profile_scope.py` (P3) is explicitly
`xfail`-marked pending core's C2 publication, with the exact poll command
and reasoning in its module docstring, so the deferral is visible to anyone
running the suite, not just documented in prose.


### Archived from contract — Next Steps

## Next Steps

Every item's test file(s) live under `backend/tests/unit/`. "Core-dependent"
= must not merge/land before `2026-08-04-defs-core-scope` publishes its seam
spec and this sprint aligns to it (M-R3); "pre-core OK" = safe to implement
now, touches no shared module.

1. **Spanish heading detection.** New module `backend/app/definition_links/
   pr_profile.py`, function `is_definitions_heading(heading) -> bool` (stem
   `[Dd]efinici[oó]n(es)?`, first-word-or-last-word-with-Spanish-
   preposition-exclusion shape, `Artículo N.`/`Sección N.` prefix-strip).
   Serves **P1**. Proven by `test_pr_profile_headings.py` (14 tests: 8
   positive incl. the real truncated-title artifact, 6 negative incl. the
   `Aportaciones Definidas` and TOC-listing false-positive guards).
   **Pre-core OK** (new module only).
2. **Spanish entry extraction.** Same module, `extract_definitions_from_
   section(text, *, scope) -> list[DefinitionCandidate]` — a continuous-
   string `finditer` scan (NOT line-based; see survey's "zero newlines"
   finding) recognizing all 6 measured marker shapes and both quoted/
   unquoted + colon/em-dash/idiom-verb separator families, plus the
   174/635-row no-marker single-entry shape. Serves **P1, P2**. Proven by
   `test_pr_profile_extraction.py` (7 tests across 5 real fixture rows,
   incl. a same-entry-re-quotes-its-own-term regression guard). **Pre-core
   OK.**
3. **Ad-hoc/local + apposition definitions outside canonical sections.**
   Same module, `extract_local_definitions(article_body)` (the `"A los
   fines/propósitos de este Artículo ..."` family, scope="local" — Spanish
   analog of Hebrew's `extract_local_definitions`) and
   `extract_adhoc_definitions(text)` (the `"(en adelante, X)"` apposition
   family, scope="local" — analog of `extract_adhoc_definitions`). Serves
   **P2** (director's "definitions outside the usual place" mandate) and
   half of **P3** (the in-scope/article-scope proof direction — the
   out-of-scope direction is matcher-level, already jurisdiction-agnostic
   per recon §1). Proven by `test_pr_profile_ad_hoc_definitions.py` (7
   tests, 2 real fixture rows). **Split dependency**: the two functions
   themselves are pre-core OK (standalone, no shared-module edits); WIRING
   them into `pipeline.py`'s Stage-2 dispatch is core-dependent — recon §1
   confirms `pipeline.py`'s current non-definitions-section branch calls
   the bare Hebrew-only `extract.extract_local_definitions`/`extract_adhoc_
   definitions` unconditionally for every article regardless of profile
   (the "Deviation" finding); moving that dispatch behind the profile seam
   is core sprint C3's job. Until C3 lands, PR's local/adhoc functions are
   implemented and unit-tested but not yet reachable from a real ingest run.
4. **Spanish citation grammar.** Same module, `find_citations(text) ->
   list[str]` (`Ley N-YYYY`, `Ley Núm. N de <fecha>`, `Artículo N`, bare
   `§ N`, `L.P.R.A.` — priority-ordered, non-overlapping, mirroring
   `USProfile.find_citations`'s claimed-span shape). Supports **P1/P2**
   (recon §1: the one Protocol method already "cleanly abstracted" per
   profile). Proven by `test_pr_profile_citations.py` (7 tests). **Pre-core
   OK.**
5. **Chapter-scope determination for Spanish scope phrases.** Interface
   TBD by core's C2 (Planner's placeholder proposal:
   `determine_chapter_scope(body_text) -> str`, recognizing `A los fines/
   efectos de este Capítulo`, `En este Capítulo` → `"chapter"`, else
   `"law-wide"` — never `"local"`, since article-scope is item 3's domain,
   corpus-confirmed mutually exclusive). Serves **P3** (scope-granularity
   determination for canonical sections). Proven by `test_pr_profile_
   scope.py`, 6 tests, all `xfail(strict=False)` with an explicit reason
   naming the core seam. **Core-dependent** — do not implement against this
   sprint's placeholder signature until core publishes; re-align once it
   does.
6. **`PRProfile` assembly + Protocol conformance.** Same module, `@dataclass
   PRProfile` wrapping items 1/2/4 (and a Spanish `detect_cross_law_
   derivations`, idiom set `según se define en`/`tiene el significado que
   se le asigna en` — lower priority, not gated by name in P1-P5, minimal
   test coverage only) — mirrors `HebrewProfile`/`USProfile`'s exact shape.
   Serves **P5** (constructed directly, `PRProfile(code="US-PR")`, no
   registry dependency). Proven by `test_pr_profile_no_english_
   regression.py` (6 tests against the real, already-vendored DE
   baseline-state fixture — 5 run for real now, 1 registry-level check
   `importorskip`'d pending item 7). **Pre-core OK** for the class itself.
7. **Registry wiring.** Edit `profiles.py`'s `_REGISTRY` construction to
   carve out `"US-PR"` → `PRProfile()` (see Seam proposal's "Cost" note for
   the exact change). Closes the loop so `get_profile("US-PR")` returns
   `PRProfile` for real. Serves **P1** (end-to-end) and the registry-level
   half of **P5**. No new test file — activates the existing `xfail`
   sub-test in `test_pr_profile_no_english_regression.py`. **Core-
   dependent** (shared module, M-R3 — do not edit before core's seam spec
   is published and this sprint's item 6 has landed).
8. **Live-path pipeline integration test** (not yet authored this pass —
   flagged, not silently dropped). Once items 3/6/7 land, an end-to-end
   `run_definition_linking` test over a real PR document (mirroring
   `test_us_profile_definitions_section_end_to_end.py`'s shape) is the
   natural closing proof for **P1**'s "real PR statutes parse" on the full
   pipeline, not just the profile layer. Sequenced after core; the manager
   should schedule this as this sprint's next planning increment once core
   lands, not treat its absence now as complete.
9. **QA zero-miss full-corpus sweep** (gate **P4**) — QA's task, not the
   Planner's (role separation). This survey's measured signal list (idioms,
   markers, scope phrases, non-canonical signals above) is the grounded
   basis QA should sweep the full 23,636-row file against — every hit
   captured or proven not-a-definition, before/after capture rate reported
   (before = 0, per gate text).


### Archived from contract — Cycle-2 item plan

## Cycle-2 item plan (Planner, 2026-08-04 — numbering continues from item 9)

Cycle 1's items 1-9 are unchanged above. The manager's full-corpus sweep
(56.4% real extraction coverage, 15/635 real heading misses) showed items 1
and 2 as SPECIFIED were under-determined by cycle 1's 5 hand-picked
fixtures (M-R6). These 3 new items extend items 1/2's test coverage against
the real workload; they do not change items 1/2's public signatures.

10. **Bucket A/B/C extraction fixes — separator-pattern + marker-inventory
    + dispatch-logic gaps.** Extends item 2's `extract_definitions_from_
    section`. Six independently-diagnosed `_extract_term_and_definition`
    separator shapes (quoted+idiom-no-separator in both quote styles,
    quoted+comma+idiom, quoted+ASCII-hyphen+idiom, quoted-no-separator-no-
    idiom, unquoted+colon, unquoted+trailing-period); one new marker shape
    (two-character Spanish "ch)" letter marker); one new block-prefix case
    (marker + decorative dash + term); one marker false-positive fix
    (spaced-abbreviation misfire, e.g. "U. S."); one dispatch-logic fix
    (a no-top-level-marker single entry must not be discarded when its
    body contains an incidental, non-entry sub-list). Serves **P1, P4**.
    Proven by `test_pr_profile_extraction_cycle2.py` (20 RED tests across
    17 real fixture rows) and re-asserted at floor granularity by item 12.
    **Pre-core OK** (same module as item 2, no shared-module edit).
11. **Heading-widening fixes — clause-scoped matching + parenthesis
    stripping.** Extends item 1's `is_definitions_heading`. Two
    independently-diagnosed structural gaps: (a) the existing first-word/
    last-word rule needs to run per semicolon/comma/em-dash-delimited
    CLAUSE of the heading tail, not just once over the whole tail
    (covers 11 of the 13 real misses); (b) an orthogonal fix strips a
    fully-enclosing `(...)` wrapper before the existing rule runs (covers
    the 2 parenthesized-whole-heading misses). Both TOC false-positive
    rejections (cycle 1's `STATE_PR_LEY_165_2020_ART1_2` and this cycle's
    `STATE_PR_LEY_51_2020_ART1_2`) must stay rejected — heading precision
    stays at 0 false positives. Serves **P1, P4, P5** (precision
    preserved). Proven by `test_pr_profile_headings_cycle2.py` (13 RED
    tests: 6 real fixture rows + 7 real-string parametrize cases covering
    the remaining named family members + both TOC guards + 3 clause-
    splitting false-positive regression guards). **Pre-core OK.**
12. **Corpus-shaped regression floor.** A NEW test shape, not a fixed
    interface — deliverable 4 of the cycle-2 brief, direct response to the
    cycle-1 lesson ("a test suite built from N hand-picked rows cannot
    prove a zero-miss gate"). Vendors 33 real rows (10 cycle-1 + 23 of
    cycle 2's 24) spanning every independently-diagnosed family and
    asserts an AGGREGATE floor — every row known (by direct human reading,
    not by re-deriving from the extractor) to be genuinely capturable
    yields >=1 candidate; every known-correct-rejection row yields 0 — so
    a future regression of this CLASS (not just of these exact rows) shows
    up here even if every narrower family-specific test still passes.
    Serves **P4** directly (a standing, re-runnable proxy for the manager's
    own full-corpus sweep, cheap enough to run in the fixture suite).
    Proven by `test_pr_profile_corpus_floor_cycle2.py` (4 parametrized
    assertion groups + 1 bookkeeping sanity test). **Pre-core OK.**

Bucket D (86 rows, copulative/prose definitions with no marker and no
canonical idiom) remains OUT OF SCOPE for items 10-12 per M-R6 — ESCALATED
to the director, program ruling P-R2 / standing question Q-1. No test in
items 10-12 targets a bucket-D row; if implementing items 10-12 causes any
rule to incidentally start capturing bucket-D-shaped prose, that is a
precision regression to report to the manager, not a feature to keep.

---

## 2026-08-04 — Developer: cycle-3 implementation, 48 RED tests -> green

Read the cycle-3 Planner entry, the contract's `## Bucket D final split
(cycle 3)` and item-13-through-17 plan, and every named test file's module
docstring as the literal spec before touching anything. Worked only in
`backend/app/definition_links/pr_profile.py`; touched no test, no fixture,
no shared module (`git diff --name-only` against the prior commit shows
exactly `pr_profile.py` + this log entry).

### What changed (items 13-16; item 17/8 stays xfail, untouched, core-gated)

- **`extract_heading_anchored_definition(heading, body, *, scope)`** (item
  13, NEW function). Two-condition rule per the director's ruling: (1) the
  heading's own non-"definición(es)" clause names a term — reused
  `is_definitions_heading`'s own machinery by factoring its label-strip +
  paren-unwrap preprocessing into a shared `_heading_tail` helper (pure
  refactor, no behavior change — confirmed by the full suite staying at
  the pre-existing 772/6 baseline before I added a single new test
  assertion), then clause-split on the existing `_CLAUSE_DELIM_RE`; a
  clause that does NOT match the stem is a candidate (leading Spanish
  article stripped); a clause that DOES match the stem and is shaped
  "Definici(ón|ones) de X" (new `_DEFINICION_DE_X_RE`) yields X as an
  additional candidate. (2) that exact term is corroborated verbatim,
  word-boundary, case-insensitive, ACCENT-FOLDED somewhere in the body.
  Folding is char-by-char NFD-decompose-and-drop-combining-marks with a
  same-character fallback when a decomposition isn't exactly one base
  character (`_fold_char`/`_fold`) — this guarantees the folded string is
  the exact same LENGTH as the original, so a match found in the folded
  copy can be sliced directly out of the real body with no separate
  offset-mapping step. `definition_text` is the SENTENCE containing the
  match (`_sentence_containing`, split on `.!?`+whitespace, falls back to
  the whole body when no boundary is found), computed against a
  footer-stripped copy of the body (`_PAGE_BREAK_FOOTER_RE`, matching all
  3 real footer shapes I found in the fixtures: quoted-title-with-year,
  quoted-title-no-year, and unquoted-title — a non-greedy `.*?` between
  the fixed "Página N de M" prefix and the closing "[Ley...]" bracket
  handles all three without three separate patterns).
- **Idiom widening, scoped correctly (item 15)**: added a SEPARATE, WIDER
  alternation (`_QUOTED_DEFINING_IDIOM_ALTERNATION`, adds `se refiere a`/
  `se referirá a`) used ONLY by the two per-block QUOTED patterns
  (`_QUOTED_TERM_COMMA_IDIOM_RE`, `_QUOTED_TERM_BARE_IDIOM_RE`).
  `_DEFINING_IDIOM_ALTERNATION` itself — used by the dispatch-fallback
  check — is UNCHANGED, exactly per the Planner's diagnosis and the
  pinned regression guard.
- **New unquoted pattern, shape 4 (item 16)**:
  `_UNQUOTED_TERM_INTERJECTED_SCOPE_IDIOM_RE` — term, comma, a bounded
  Spanish scope-phrase clause (`a/para los fines/efectos de...`, `para
  propósitos de...`), comma, idiom lookahead. Term group excludes
  `.,:;` like every other unquoted pattern, so it fails closed (matches
  nothing) on any block opening with the M-R7 "(a) En General.-" shape —
  confirmed live, not assumed.
- **New lead-in fallback, `_extract_lead_in_then_quoted_term` (item 16,
  shapes 1/2/3/5)**: tried only when a block does NOT start with a quote
  AND every existing unquoted pattern already failed (tried first,
  unchanged, so nothing already working can regress). Finds the first
  quote in the block; if it's within 60 chars, crosses no REAL sentence
  boundary (a semicolon, or a period NOT immediately followed by a hyphen
  — reusing the exact `\.(?!-)` discipline that already protects the
  M-R7 rows, which is what makes `STATE_PR_RENTAS_SEC1010_01`'s "(2)
  Corporación.-El término..." block reachable), and does not contain the
  `conocido/a como`/`denominado/a` law-title-naming idiom (belt-and-
  suspenders on top of the length bound, checked directly against the
  85-char `STATE_PR_LEY_48_2018_ART3` correct-zero guard), it (a) re-tries
  the ordinary QUOTED patterns at the quote, else (b) if the lead-in ends
  with a recognized cue ("el término", "se considera(rá)(n) como"), takes
  the quoted term with `definition_text` bounded to the SENTENCE
  immediately following it (not "everything after" — avoids fabricating
  one bloated definition out of several distinct entries when a block
  wasn't fully split by the marker scanner).
- I did **NOT** touch `_ENTRY_MARKER_RE` at all. I originally thought
  shape 6 (`STATE_PR_RENTAS_SEC1010_01`, 37 markers) needed a marker-
  boundary change (adding `-` to the boundary lookbehind) to split its
  "(1) Persona.-..." sub-entry out from the "(a)" preamble it's fused
  into. Checking the LIVE marker output first (before writing any fix)
  showed the ALREADY-unmodified regex finds 37 markers total — "(1)" is
  the only one absorbed into "(a)"'s block (hyphen-preceded, not in the
  boundary set), but "(2)" onward are already correctly split (period-
  preceded). "(2)"'s own block ("Corporación.-El término
  "corporación"...") is short enough to reach my new lead-in fallback and
  yields a real candidate on its own — floor granularity (`>=1`) is
  satisfied without touching a shared, heavily-relied-upon regex at all.
  Recording this because it's a real "checked before assuming" catch: I
  nearly made a broader, riskier change than the row actually needed.

### A real finding, caught by my own corpus self-check, not by any test —
### and fixed, not silently absorbed

Running `extract_heading_anchored_definition` over the FULL corpus (not
just the 53 pinned assertions) surfaced that it ALSO fired on ruling
M-R7's three correct-zero rows (`STATE_PR_LEY_77_1957_ART36_030`,
`STATE_PR_RENTAS_SEC2022_01`, `STATE_PR_RENTAS_SEC2042_01`) — each has a
heading that genuinely names a term (`"Definiciones—Forma representativa
de gobierno"` -> "Forma representativa de gobierno";
`"Definición de Caudal Relicto Bruto"` -> "Caudal Relicto Bruto";
`"Definición de Donaciones"` -> "Donaciones") AND that term genuinely
appears verbatim in the body, so my two-condition rule alone was not
sufficient to keep these at zero. This is a real tension worth recording
plainly: `STATE_PR_RENTAS_SEC2022_01` ("Definición de Caudal Relicto
Bruto") and the REQUIRED positive `STATE_PR_RENTAS_SEC2030_03` (same
exact heading text) are structurally near-identical from a pure
heading-anchor perspective — I could find no heading-shape signal that
distinguishes them. What DOES distinguish them: all three M-R7 rows have
`_ENTRY_MARKER_RE` marker structure (`(a)`, `(b)`, `(1)`... — confirmed
live), while every one of the 9 required-positive and 7 required-residue
bucket-D rows has ZERO markers (also confirmed live, all 16). This
matches bucket D's OWN definition, stated in the test file's own module
docstring: "no entry marker and no canonical defining idiom." I added
this as a third precondition gate (`if _ENTRY_MARKER_RE.search(body):
return []`, right after the `is_definitions_heading` gate) rather than
inventing an ad-hoc per-row exclusion list. This is a PRINCIPLED fix (it
uses bucket D's own stated definition as the guard, not a hardcoded
`act_id` blocklist) but I'm flagging it explicitly rather than treating it
as obviously correct: the sprint brief's "must keep returning exactly 0
candidates" for these 3 rows is unqualified (doesn't scope itself to
`extract_definitions_from_section` alone), and I read it as a hard,
director-level constraint I have no authority to relax even though a
heading-anchored capture of `STATE_PR_LEY_77_1957_ART36_030` (whose own
body literally defines "forma representativa de gobierno" via its (a)-(h)
conditions, as ONE candidate, not fragmented) is arguably a legitimate,
narrow capture in the spirit of the director's ruling. I fixed it to
comply with the explicit instruction rather than deciding unilaterally
that the instruction was stale now that item 13 exists. Flagging for the
manager/director: is capturing these 3 via heading-anchor (not via
marker-fragmentation, which is what M-R7 actually objected to) something
that should be revisited, or does M-R7 stand as originally ruled,
mechanism-independent? I implemented the conservative, brief-literal
choice and did not silently pick the other one.

### Full suite

```
$ backend/.venv/bin/pytest backend/tests -q
825 passed, 7 xfailed, 18 warnings in 13-25s (re-run several times, stable)
```

825 = the 777-passed cycle-3 baseline + 48 newly-green RED tests, exactly.
7 xfailed = the 6 pre-existing `test_pr_profile_scope.py` tests (P3,
core-gated) + item 8's end-to-end test — confirmed via `-rxX` that all 7
report `XFAIL`, zero `XPASS`. Re-run with the 5 new cycle-3 test files
targeted directly first (53 passed in isolation, matching the 48-RED +
5-already-green accounting from the Planner's handoff) before the full
suite, so the 825 total is provably not hiding a collection error.

Role boundary: `git status --short` shows exactly one file touched,
`backend/app/definition_links/pr_profile.py`. No `profiles.py`,
`pipeline.py`, `extract.py`, `matcher.py`, `us_profile.py`, `sections.py`,
`normalize.py`, model, or migration edited. No test or fixture edited.

### Corpus self-check (full `us_pr_statutes.parquet`, 23,636 rows, read
once via a disposable scratchpad script — never committed, never read by
any test)

```
headings detected: 633/635, false positives: 0
  the only 2 not detected are the 2 Table-of-Contents rows -- CORRECT rejections
  (unchanged from cycle 2 -- item 13/15/16 touch extraction, not heading detection)

detected sections: 633
  yielding >=1 candidate (extract_definitions_from_section): 529  (83.6%, up from cycle 2's 80.9%)
  zero-yield: 104

heading-anchored fired on 71 of those 104 zero-yield sections
  (contract's own Planner survey estimated 70 -- 71 live is a very close,
  expected small delta, same order as the 0.9% idiom-count delta noted in
  cycle 1; all 9 contract-named positive rows + all 7 contract-named
  residue rows verified individually correct via the pinned tests, and a
  spot-check of every 6th of the 71 live captures -- printed in full in my
  own verification, not just counted -- shows clean, correct single-term
  Civil-Code-shape captures, no fabrication smell)
  33 still zero after the heading-anchor attempt (unrelated follow-up
  idiom gaps explicitly flagged as out of THIS cycle's scope by the
  Planner -- se considera como's other 4 rows, se entenderá family, etc.
  -- not silently re-labeled as "fixed")

COMBINED (either function fires): 600/633 = 94.8%

total terms extracted (both functions combined): 5749
  min=2 max=104 median=16 p95=45
  terms >120 chars: 0
  empty terms: 0

M-R7 rows (after the marker-precondition fix above):
  STATE_PR_LEY_77_1957_ART36_030: extract_definitions=0 heading_anchored=0  OK
  STATE_PR_RENTAS_SEC2022_01:     extract_definitions=0 heading_anchored=0  OK
  STATE_PR_RENTAS_SEC2042_01:     extract_definitions=0 heading_anchored=0  OK

Other pinned correct-zero guards re-verified directly against the live corpus:
  STATE_PR_LEY_52_2019_ART3 (cycle 2): 0 candidates  OK
  STATE_PR_LEY_48_2018_ART3 (cycle 3): 0 candidates  OK
```

### Design choices / residual risk on the record

- **The M-R7-vs-heading-anchor tension above** is the main thing I want
  the manager/director to see, not just the numbers. I resolved it
  conservatively (comply with the explicit "must stay 0" instruction) but
  it is a real, principled alternative reading, not a bug I stumbled past.
- **Footer-stripping was applied inside `extract_heading_anchored_
  definition` only**, not inside `extract_definitions_from_section`'s main
  body/entry-marker scan. I checked: every cycle-3 ordinary-workload test
  row's FIRST relevant quote occurs before any footer text in its own
  body, so footer-stripping was not load-bearing for those tests either
  way — but `extract_definitions_from_section` already has many cycle-1/2
  pinned exact-assertion tests over rows that themselves contain
  footer-shaped text (`STATE_PR_LEY_249_2003_ART3`,
  `STATE_PR_LEY_77_1957_ART30_020`, and 6 more), so I judged the
  regression risk of touching that function's shared text-scanning path
  higher than the benefit, and scoped footer-stripping to the brand-new
  function that actually needed it and is proven by a dedicated test
  (`test_page_break_footer_boilerplate_does_not_block_or_corrupt_the_
  real_anchor`). Flagging as a deliberate, not accidental, scope choice.
- **`_MAX_LEAD_IN_LEN = 60`** was checked directly against the real
  correct-zero guard's exact length (85 chars for `STATE_PR_LEY_
  48_2018_ART3`'s lead-in), not picked arbitrarily, and backed by a
  SECOND, independent guard (the explicit `conocido/a como`/`denominado`
  exclusion) so the bound isn't the only thing standing between recall and
  a fabricated law-title capture.
- **Multiple candidate terms per heading** (`_find_corroborated_term`
  tries longest-first): no real row in this cycle's fixtures actually
  produces more than one candidate term per heading, so this ordering is
  unverified against a real multi-candidate row — flagged for a future
  cycle/QA if the corpus turns one up.

### For QA

- Please independently re-run a full-corpus sweep, not just the 53 pinned
  assertions — that discipline is what caught the M-R7 collision above
  before it shipped.
- The "23 already-nonzero sections where heading-anchored ALSO fires"
  (informational in my self-check) is not wired into any pipeline output
  this cycle (item 13 is a standalone function, not registered anywhere) —
  it only matters once core's registry wiring lands and something decides
  how to combine the two functions' outputs, which is out of this cycle's
  scope.
- `test_pr_profile_scope.py` (6) and item 8's end-to-end test (1) stay
  xfail, core-gated, unchanged, confirmed via `-rxX` (zero XPASS).

### Escalations

None in the "stop and ask before proceeding" sense — no test looked
wrong, no shared module needed editing, and the one real recall-vs-
precision-shaped question I found (the M-R7 tension above) I resolved
in-panel by deferring to the more conservative, explicitly-stated
instruction, the same "decide with data, flag it plainly" discipline the
Planner used for the `se refiere a` dispatch-fallback question in the
prior entry — but I want it read carefully rather than skimmed past.

### Pushed

```
30609c9 dev: cycle-3 heading-anchored bucket-D rule, idiom widening, ordinary workload (48 RED tests -> green)
```
Branch `claude/defs-us-pr`, pushed to origin.

---

## 2026-08-04 — Manager: cycle-3 verified, ruling M-R9, handing to QA

**Boundaries held**: `pr_profile.py` + this log only. No test, no fixture, no
shared module. Suite `825 passed, 7 xfailed` with `-rxX` confirming 7 XFAIL
(6 scope + item 8) and zero XPASS.

**My own full-corpus run** (independent script, exercising BOTH the section
extractor and the new heading-anchored path):

```
ground truth 635 | detected 633 | false positives 0
undetected = exactly the 2 Table-of-Contents rows (correct rejections)

section extractor yield : 529/633 = 83.6%
heading-anchored rescues:  71
COMBINED                : 600/633 = 94.8%
still zero              :  33

terms 5,749 | median 16 | max 104 | >120 chars: 0 | empty: 0
M-R7 rows: all 0 via BOTH functions — held
```

**Puerto Rico went from 0% to 94.8%** with zero heading false positives and
no term fabrication. The director's heading-anchored ruling was the right
call: it rescued 71 rows on its own, and the Planner's 70-row estimate was
accurate to one.

### Ruling M-R9 — M-R7 is REFINED, not overturned; the open part goes to QA

The Developer flagged, honestly and unprompted, that his heading-anchored
rule would have fired on all three M-R7 rows, and that he gated it on
"no entry markers" to comply with my ruling — while noting that capturing
e.g. `STATE_PR_RENTAS_SEC2022_01` as ONE clean candidate might be legitimate
under the spirit of the director's ruling. He also found that this row and
the required-positive `STATE_PR_RENTAS_SEC2030_03` share **identical heading
text**, so no heading-shape signal separates them.

He was right to raise it and right not to decide it. My ruling:

- **M-R7 stands as to what it actually decided**: do not fabricate one term
  per `(a)`/`(b)` item when those items are conditions or subsection labels
  (`"En General"`). That reasoning is untouched.
- **M-R7 did NOT decide** whether such a section defines its heading's term
  once. I over-read my own ruling as "this section defines nothing" when
  what I proved was "these markers are not terms". `SEC2022_01`'s heading is
  `Definición de Caudal Relicto Bruto` and its body does define that term —
  so a single heading-anchored candidate is plausibly a genuine recall win.
- **Disposition**: the marker-structure gate SHIPS as-is for now (it is
  principled — bucket D is by definition the no-marker class, and widening
  the anchored rule to marker-bearing rows changes its risk profile). The
  open question goes to **QA** to evaluate independently on the real corpus.
  If QA agrees it is a recall win, it becomes a cycle-4 Planner item — with
  the test change authored by the Planner, never by the Developer.

### Handing to QA — which has never run

Every verdict in this log so far is Planner + Developer + my own
verification. That is **not** the independent QA role, and gate **P4**
formally belongs to QA. QA runs next with a mandate to disagree with all of
us, including me. Known open item for it: 33 sections still yield zero, and
several look ordinary rather than accepted-gap (`a) Documento acreditativo -
significará…`, `Productor. — Es la persona que…`, `Los siguientes términos y
frases tendrán los significados…`) — I am NOT declaring those done.

---

## 2026-08-04 — QA: independent verification, P4 sweep, FAIL on P2/P4

**Method.** Worktree venv, `codegraph`/direct Read of `pr_profile.py` (read
only — never edited, `git status --short` before commit shows only test
files, one new fixture, README, contract, log). Independent full-corpus
scripts in the scratchpad (never touching `backend/tests`), reading the
same on-disk `us_pr_statutes.parquet` snapshot
(`301000fc3465374ee0f23c3c6953a8a861e95cad`, 23,636 rows) via `pyarrow`
directly. Re-derived every panel number from scratch rather than trusting
it — including hitting the EXACT `\b`-boundary bug (`"Para los..."`
bleeding into `"A los..."`) the manager already found and fixed once; my
own first-pass regex had the same bug, caught and fixed before reporting
any count from it.

### Per-gate verdicts

**P1 — PASS.** `backend/.venv/bin/pytest backend/tests -q` → `825 passed,
7 xfailed`. My own heading sweep: GT (own regex, `[Dd]efinici[oó]n(es)?`
case-insensitive) = 635; `is_definitions_heading` detects 633/635, 0 false
positives; the 2 undetected are exactly the 2 correct TOC rejections
(`STATE_PR_LEY_165_2020_ART1_2`, `STATE_PR_LEY_51_2020_ART1_2`). Exact
match to the panel's numbers, independently reproduced.

**P2 — FAIL.** The director's explicit mandate ("if a definition appears
in another article… it should be captured as well") is not honestly met.
Three independent lines of evidence:
1. `extract_local_definitions`/`extract_adhoc_definitions` are NOT wired
   into `pipeline.py` for any non-`"IL"` profile — confirmed by direct
   read: `pipeline.py:30-34` imports `extract_local_definitions`/
   `extract_adhoc_definitions` from `app.definition_links.extract` (the
   Hebrew/English module), not from `pr_profile`, and calls them
   unconditionally at `pipeline.py:437,440` for every non-canonical
   article regardless of jurisdiction. Live path capture for PR ad-hoc/
   local definitions today: **zero**, corpus-wide, regardless of what the
   PR-owned unit functions can do standalone (already flagged as a known
   deviation in the item-3 test file's own docstring — I confirm it
   independently, not a new finding).
2. Even as a standalone unit function, `extract_local_definitions` (the
   PR-owned Spanish version) captures far less than its own measured
   target signal. Full sweep of both implemented trigger phrases (`A los
   fines de este Artículo` 16 rows + `Para propósitos de este Artículo`
   26 rows = 42, after fixing the same boundary bug noted above): only
   **8/42 (19%)** produce ≥1 candidate. A third, fully-measured synonymous
   trigger phrase from the Planner's OWN cycle-1 survey table, `A los
   efectos de este Artículo` (13 corpus-wide rows), is **entirely absent**
   from `_LOCAL_TRIGGER_RE`'s alternation — **0/13** captured, not
   attempted. Root cause of the 34/42+13=55-row miss pool: the function
   only recognizes ONE narrow shape (a QUOTED term immediately after the
   trigger phrase, optional comma) — unquoted terms (`"el término mayoría
   significará…"`, 5 near-identical rows in the UPR law alone), marker-
   list multi-term intros (`STATE_PR_MUNICIPAL_ART1_017`, `STATE_PR_
   PENAL_ART300`), and lead-in idioms other than the bare comma-then-quote
   shape (`"se define X como…"`) are all unhandled. Real, unambiguous
   examples pinned as RED tests (see Deliverables below):
   `STATE_PR_LEY_20_2017_ART4_14`, `STATE_PR_LEY_1_1966_ART8`, `STATE_PR_
   LEY_77_1957_ART9_400`.
3. **The single largest finding of this pass**: a corpus-wide signal sweep
   of definition idioms OUTSIDE the 635 canonical rows (not just the
   narrow `A los fines/efectos/propósitos de este Artículo` trigger set)
   found hundreds of further real candidates. Random 20-row sample of the
   274 non-canonical rows containing `significa`: **19/20 genuine
   definitions** (article- or law-scoped, e.g. `"Municipio: Significa el
   Gobierno Local…"`, `STATE_PR_LEY_81_2021_ART3`), only 1/20 ordinary
   prose ("esto no significa que…"). A second, independent 15-row sample
   of the 221 non-canonical `significará`/`significara` rows: **14/15
   genuine**. I did not exhaustively classify the full non-canonical
   idiom population (`significa` 274, `significará` 221, `se entenderá
   por` 53, `tendrá el significado` 89, `se considera como` 273, etc. —
   over 1,000 combined hits) — flagging that as unfinished, not claiming
   zero-miss there — but two independent random samples at ~95%/93%
   genuine-hit rates make the scale unambiguous: on the order of several
   hundred real Spanish definitions live in ordinary (non-Definiciones)
   PR articles today, corpus-wide, and none of them are captured by
   anything in `pr_profile.py`.
4. **A concrete, single-law-concentrated example at scale, verified not
   estimated**: `STATE_PR_TRANSITO_ART1_*` (Puerto Rico's Vehicle & Traffic
   Code, Article 1) has **128 rows**; only **1** is `is_definitions_
   heading`-canonical (`STATE_PR_TRANSITO_ART1_02`, heading `"Artículo
   1.02. Definiciones"`, body truncated to just the intro sentence — a
   real data-truncation artifact, see below). The other up-to-127 rows
   are each headed `"Artículo 1.NN. <Term>"` (the bare TERM itself as the
   heading, no "definición" word anywhere) with a body starting `"Término"
   Significará/Significa X` (after an optional `[9 L.P.R.A § 5001 Inciso
   (N)]` citation-bracket prefix) — e.g. `STATE_PR_TRANSITO_ART1_75`
   (`"Artículo 1.75. Paso de peatones"`), `STATE_PR_TRANSITO_ART1_96`
   (`"Superintendente" Significará el Superintendente de la Policía…`). A
   conservative, narrow signature match (quoted term ≤60 chars directly
   followed by a recognized idiom word, citation-bracket-stripped) finds
   **116 corpus-wide non-canonical rows matching this exact shape, 115 of
   them from this ONE law**. This is a genuinely NEW class no existing
   function even attempts: the heading names the term directly (no
   "definición" stem at all, so `is_definitions_heading` is correctly
   False and `extract_heading_anchored_definition`'s own first gate
   excludes it too), and neither ad-hoc trigger phrase applies. Likely
   explains why `STATE_PR_TRANSITO_ART1_02`'s own body is empty — the
   source scrape appears to have split ONE long Definiciones article into
   ~127 one-term rows. This single law alone is a larger miss population
   than the entire 33-row within-canonical-section residue.

**P3 — Correctly and honestly DEFERRED, not gradable pass/fail this
sprint.** Read `test_pr_profile_scope.py` in full: 6 tests, all
`xfail(strict=False)` with an explicit, accurate reason naming the exact
core-seam blocker; `determine_chapter_scope` genuinely does not exist in
`pr_profile.py` (confirmed by reading the whole 1,176-line file). Re-polled
core live: `origin/claude/defs-core-scope` is now at seam spec **v2.4**
(far more advanced than the v1 "baseline-first registry" this sprint's
contract describes), but `origin/main` (`09aca8e`) still has NOT merged
core — `profiles.py` on main still has no `PRProfile`/`"US-PR"`-specific
registration. The deferral is still accurate as of this fetch; not hiding
anything.

**P4 — FAIL. This is my call.** Before = 0% (confirmed independently: 0/635
canonical headings recognized by the pre-sprint registry). After, WITHIN
the 633 detected canonical sections: combined capture (section extractor
OR heading-anchor) = **600/633 = 94.8%**, terms 5,749, max term length
104, 0 empty — I independently reproduced every one of these numbers
exactly via my own script and regexes (not copy-pasted from any panel
script). That is real, substantial, well-tested progress and I am not
disputing it. But it is not zero-miss, on two levels:
- **Within the 33 canonical zero-yield rows**, I classified all 33
  individually (not just spot-checked), see table below: only 9/33 are
  confirmed-correct accepted gaps; 17/33 (52%) are genuine ordinary misses
  across at least 14 distinct, individually-verified root causes (not one
  repeated defect); the remaining 7/33 are a marker-precondition-gate
  tension (5 rows, see M-R9 ruling below) plus 2 more accepted-gap-shaped
  rows the panel's documentation never named.
- **Outside the 635 canonical rows**, P2's evidence above (55-row known
  trigger-phrase pool at 15% capture, ~300+ likely real hits in the
  broader idiom sweep by sampled rate, 115+ confirmed in one law alone)
  is P4's territory too — a zero-miss sweep that only covers canonical
  Definiciones headings is not a zero-miss sweep of the corpus.

### Classification of the 33 canonical zero-yield rows (full, not spot-checked)

| Bucket | Rows | Disposition |
|---|---|---|
| Documented residue (7) + correct-zero guards (2) | 9 | CONFIRMED correct, re-verified live |
| Marker-precondition-gate suppression (M-R7's 3 + 1 new twin `STATE_PR_RENTAS_SEC2041_03` + 1 new `STATE_PR_CIVIL_ART1267`) | 5 | Recall-win lean, see M-R9 ruling |
| Accepted-gap-shaped, undocumented (`STATE_PR_LEY_77_1957_ART36_010` singular/plural inflection mismatch; `STATE_PR_TRANSITO_ART1_02` data-truncation, same class as the already-documented 9/635 title-truncation artifacts) | 2 | Recommend adding to contract's gap table |
| Genuine ordinary misses, cycle-4 workload | 17 | NOT accepted-gap — see root-cause groups below |

Root-cause groups for the 17 (real rows named, full detail in
`test_pr_profile_qa_cycle4_findings.py` and my scratchpad
`qa_pr_classify33_out.txt`-equivalent transcripts):
(A) unquoted term + bare/comma idiom **per-block inside a marker loop** —
completely unhandled except as the ONE special-cased pre-marker lead-in
check (`STATE_PR_LEY_137_1968_SEC1` 7 terms, `STATE_PR_LEY_1_1966_ART14`
10 terms, `STATE_PR_LEY_97_1971_SEC1` 6 terms — 23+ individual terms in
just these 3 rows); (B) same shape, single no-marker whole-body block, no
quote anywhere (`STATE_PR_LEY_154_2004_ART2`, `STATE_PR_MUNICIPAL_
ART7_100`); (C) `"se entiende por"`/unquoted `"se entenderá por"` not a
recognized pre-quote cue (`STATE_PR_LEY_15_1931_SEC22` — a CYCLE-2 REUSED
fixture that itself still yields zero — `STATE_PR_LEY_45_1935_ART36`,
which also loses ~8 more terms to the single-match-only limitation of a
7,781-char unmarked body); (D) alt-term joiner `"y"` not recognized, only
`"o"` (`STATE_PR_LEY_77_1964_ART1`); (E) plural `"los términos"` not a
recognized pre-quote cue, only singular `"el término"` (same row, stacks
with D); (F) `"quiere decir"` idiom never implemented despite being in the
Planner's own cycle-1 survey (`STATE_PR_LEY_82_1964_ART3`, 3 terms); (G)
ASCII hyphen never added to `_UNQUOTED_TERM_DASH_RE` (only the quoted
sibling got cycle 2's fix) (`STATE_PR_LEY_209_2016_ART2`, 2 terms); (H)
quoted term + period + idiom, no comma/dash (`STATE_PR_LEY_77_1957_
ART26_030`); (I) quoted term + comma + bare apposition, no idiom word at
all (`STATE_PR_LEY_55_1996_ART2`, 9 terms); (J) 60-char lead-in bound too
short when a citation bracket precedes the real cue (`STATE_PR_LEY_
271_2004_ART2`, measured 71 chars); (K) multi-term list, no markers,
lead-in bound too short for the full intro sentence (`STATE_PR_LEY_
55_1963_SEC3`, already named by the manager); (L) dash-shaped single-entry
lead-in not recognized by the dispatch check, only bare-copulative is
(`STATE_PR_LEY_77_1957_ART9_020`, already named by the manager); (M)
inverted idiom order `"Por X se entenderá Y"` (`STATE_PR_LEY_34_1966_
ART10`); (N) deeply-nested subsection quoted-term shapes, lower
confidence (`STATE_PR_RENTAS_SEC1115_09`).

### Rulings on the four routed questions

1. **M-R9 (marker-precondition gate).** My lean: **recall win**, agreeing
   with the Developer's instinct and the Manager's own M-R9 framing — but
   with NEW data neither had: `STATE_PR_RENTAS_SEC2041_03` is a 4th real
   row sharing the EXACT shape of the two already-named Rentas rows
   (`"(a) Definición General.- Donaciones tributables significa…"`) that
   the panel never noticed as a twin, and `STATE_PR_CIVIL_ART1267` proves
   the gate's blast radius extends beyond the M-R7 family entirely (a
   clean, unconditioned defining sentence with an incidental examples
   sub-list — the SAME shape `extract_definitions_from_section`'s own
   cycle-2 dispatch fix already protects for `STATE_PR_LEY_77_1957_
   ART9_040`, just never ported to the heading-anchor gate). This is NOT a
   P-R2 zero-miss-vs-false-positive class needing director arbitration —
   it resolves the same way the Planner's `se refiere a` question did
   (narrow the gate with a more targeted condition, e.g. "is the
   CORROBORATING SENTENCE itself marker-free" rather than "is the whole
   body marker-free anywhere"), a precision refinement, not a genuine
   recall/precision tradeoff. Recommend: cycle-4 Planner item. Pinned
   `xfail(strict=True)` in `test_pr_profile_qa_cycle4_findings.py` (not
   RED — the exact narrower condition is a Developer design choice, not
   something QA prescribes).
2. **The 33 remaining zero-yield sections.** Do NOT accept as done — see
   the classification table above. 17/33 confirmed genuine ordinary
   misses (52%), not accepted gap.
3. **The 7 anchor-less residue rows.** Accurate as far as it goes — all 7
   independently re-verified to produce `[]` from
   `extract_heading_anchored_definition` with no corroborating heading
   term. But "7, the FINAL documented gap" undercounts by at least 1:
   `STATE_PR_LEY_77_1957_ART36_010` (heading `"Sociedades fraternales
   benéficas—Definiciones"`) has the identical CHARACTER as the
   documented nominalization-mismatch residue (`STATE_PR_CIVIL_ART1526`)
   — a singular/plural inflection mismatch (heading's plural "Sociedades…
   benéficas" vs. body's singular "una sociedad fraternal benéfica") — and
   is not in the table. Recommend adding it as an 8th documented residue
   row (documentation completeness, not a code change).
4. **P2's "outside canonical sections" half.** Cannot honestly be called
   met — see P2 verdict above. Not "partially met, needs polish": zero
   live-path capture (not wired), 15-19% capture on the narrowly-
   implemented standalone signal, a fully-unimplemented third trigger
   phrase, and a ~300-700-real-definition-scale gap in the broader
   non-canonical idiom population that nothing currently attempts.

**P5 — PASS.** `backend/.venv/bin/pytest backend/tests -q
--ignore=<all pr_profile test files>` → `641 passed`, exact pre-existing
baseline, unchanged. `test_pr_profile_no_english_regression.py` (M-R4, the
two-sided gate) re-run directly: `9 passed`. Role boundary: `git diff
--name-only` against `origin/main`'s merge-base across the WHOLE sprint
(`git diff --name-only $(git merge-base origin/main HEAD)...HEAD`) shows
exactly ONE file under `backend/app/` touched in the entire sprint —
`pr_profile.py` — confirmed myself, not inherited from the log.
`get_profile("US-DE")` still resolves to plain `USProfile` (registry
untouched, confirmed via direct read of `profiles.py`'s `_REGISTRY`).

### Deliverables added (tests/fixtures only, role boundary held throughout)

- `backend/tests/unit/test_pr_profile_qa_cycle4_findings.py` — 6 tests (5
  RED, pinning findings 1-4 above with real vendored rows; 1
  `xfail(strict=True)` pinning the M-R9-adjacent finding, see ruling 1
  above), all independently re-run: `5 failed, 1 xfailed`.
- `backend/tests/fixtures/us_statutes/pr_sample_rows_qa_cycle4.json` — 6
  REAL rows, byte-compared against a fresh parquet read immediately before
  commit (`6 rows checked, 0 problems`). README section appended
  documenting provenance.
- Full suite after my additions: `backend/.venv/bin/pytest backend/tests
  -q` → `5 failed, 825 passed, 8 xfailed` — the 825/8(-1 new xfail=7 old)
  baseline is exactly unmoved; the 5 new failures are the intended RED
  signal for cycle 4, isolated to my own new file (confirmed by re-running
  the rest of the suite with my file excluded: unchanged `825 passed, 7
  xfailed`).

### Not done, flagged not hidden

I did not exhaustively hand-classify the full non-canonical idiom
population (~1,000+ combined hits across `significa`/`significará`/`se
entenderá por`/`tendrá el significado`/`se considera como`/etc.) — two
independent ~95%/93%-genuine random samples make the SCALE unambiguous,
but a row-by-row corpus-wide classification (and a similar sweep for
other laws sharing TRANSITO's one-term-per-row convention) is real
follow-up work I am handing to the Planner, not claiming to have finished.
