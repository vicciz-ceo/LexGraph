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
