# Gate-2 footprint investigation — sprint 2026-08-20-defs-boundary-idioms

Investigator pass, 2026-08-21. Read-only against `backend/`/`frontend/`; the
only artifacts this pass writes are this file and its own commit. Verified
`git log --oneline -1` == `919b3f1` before starting.

Evidence base: `docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/run/compare/{changed.jsonl,summary.json}`
(committed), `run/baseline/records.jsonl` and `run/current/records.jsonl`
(gitignored, read-only), the pinned corpus snapshot
(`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad`),
and direct re-execution of the extraction pipeline (both the archived
pre-fix source at `run/baseline-src` and the current worktree) via
throwaway scripts under this session's scratchpad — never written into the
repo. `git diff --stat d660849163df9c46aae97157424ba0bb5420ffce..HEAD --
backend/` confirms the ENTIRE code delta between baseline and current is
the single line in `backend/app/definition_links/rules/us_markers_boundary.py`
changing `_TIGHT_IDIOM_RE` (commit `a51b1de`) — nothing else in `backend/`
differs, so every effect measured below is attributable to that one regex
edit.

Numbers reconfirmed independently against `changed.jsonl` before any other
work: 8,725 changed records → 7,584 distinct `(jurisdiction, source_file,
source_row, term)` anchors: 6,309 pure additions, 1,141 both-removed-and-
added, **134 pure removals**. Exact match with the committed `summary.json`.

---

## Q1 — the 134 pure removals

### Mechanism

All 134 removed terms (100 distinct rows) were traced by replaying
`USProfile.extract_definitions_from_section`'s own internal steps in-process,
with `us_markers_boundary._TIGHT_IDIOM_RE` monkeypatched between the
baseline and current forms (the only variable the real commit changes).
**All 134/134 terms reproduce exactly**: present in the baseline replay's
pre-filter candidate list, absent from the current replay's — a 100% match
against the committed gate-2 diff, confirming the replay methodology.

**The mechanism is uniform across all 100 rows: fallback suppression, not
boundary shrinkage.** `USProfile.extract_definitions_from_section`
(`backend/app/definition_links/us_profile.py:2551-2552`) contains:

```python
if not candidates and heading_was_derived:
    candidates = _extract_inline_quoted_definitions(text, scope=scope)
```

`candidates` here is the union of baseline's own numbered-block splitter
plus every registered `EntrySplitterRule`'s contribution — for FED, VA, UT,
TX, SC, AZ, NJ, MI, ND, NY, OK, NM, NV, WA (`us_markers_inline_quote.py`)
and OH/ME's own wrapper modules (`us_markers_oh_trailing_clause.py`,
`us_markers_me_pl_citation.py`), that EntrySplitterRule calls
`us_markers_boundary.extract_quote_anchored_entries` directly — the exact
function the widened `_TIGHT_IDIOM_RE` changes. `_extract_inline_quoted_
definitions` is a **completely separate, broader fallback** defined in
`us_profile.py` itself: it has its own idiom regex (`_MEANS_IDIOM_GAP_RE`,
unchanged by this sprint, and which **already** recognizes bare `includes`
in addition to `means`/`shall mean`/`has the meaning`/`shall include`), and
critically **no `TRAILING_STOP_RE` cutoff at all** — it scans the entire
section body regardless of "Editorial Notes"/citation-block boundaries.

The guard is **all-or-nothing per row**: the fallback runs only when the
primary engine's block-derived `candidates` list is **completely empty**.
Before the widening, many rows' primary engine found *zero* recognized
entries (their only idiom occurrences were unrecognized shapes: bare
`includes`, "shall include" before this widening, or terms sitting past a
`TRAILING_STOP_RE` cutoff the primary engine refuses to cross) — so the
broader fallback ran and picked up every term it could find, unbounded.
The instant the widened `_TIGHT_IDIOM_RE` makes the primary engine
recognize **even one** entry anywhere in that row's body, `candidates` is
no longer empty, the guard flips, and the fallback **never runs** —
discarding every *other* term only the fallback could reach, even though
the widening did nothing to fix (or even touch) how those other terms are
recognized.

Verified end to end on 5 concrete rows, replaying the real production
pipeline for both baseline (archived pre-fix source at `run/baseline-src`)
and current (this worktree):

1. **`USC_T29_C4C_S50` (FED row 12889).** Baseline: primary engine finds 0
   entries (`trailing_stop_limit` cuts the body at 650 chars, right after
   `"State" shall include the District of Columbia.` — before "shall
   include" was recognized, even this one entry was invisible to the
   primary engine) → fallback runs, unbounded, and finds **8** terms
   (`State`, `Registered Apprenticeship`, `Pre-Apprenticeship`,
   `Labor-Management Forum`, `agencies`, `participating agencies`,
   `interested agencies`, `Labor-Management Forum agencies`) deep inside an
   Executive Order quoted in the section's "Editorial Notes" annotation
   block. Current: primary engine now recognizes `"State" shall include...`
   as one clean entry (`"the District of Columbia."`) → fallback is
   skipped → the other **7** terms vanish entirely.
2. **`STATE_OH_T11_C1109_S1109.22` (OH row 3296).** Same shape: baseline
   fallback finds `Derivative transaction` and `Person`; current's primary
   engine recognizes an unrelated `"Loans and extensions of credit" ...
   shall include ...` entry elsewhere in the body, suppressing the
   fallback and losing both terms.
3. **`STATE_WA_T10_C99_S080` (WA row 717, "Penalty assessment").** Baseline
   fallback finds `"convicted" includes a plea of guilty, ...` (bare
   `includes` — never recognized by the primary engine even after this
   widening) and a badly over-run `"domestic violence"` (bleeding into an
   unrelated judges'-instructions clause). Current's primary engine now
   recognizes `"domestic violence" has the same meaning as ...` as its own
   clean, correctly-bounded entry → fallback skipped → `"convicted"` is
   lost even though **the widened idiom set still cannot recognize
   "convicted" on its own** (bare `includes` was never added).
4. **`USC_T43_C35_S1732` (FED row 2476).** Baseline fallback finds 5 terms
   (`invasive species`, `locally adapted`, `native plant species`,
   `nonnative`, `plant material`) from a quoted pilot-program Act embedded
   mid-section; current's primary engine recognizes an unrelated
   `"conservation system unit" ... has the meaning ...` cross-reference
   earlier in the body, suppressing the fallback and losing all 5.
5. **Direct `pre_fallback_count` instrumentation across all 100 rows**
   (`extract_definitions_from_section`'s own per-block candidate count,
   before the fallback substitution) confirms the pattern is universal:
   **100/100 rows have `pre_fallback_count == 0` in baseline and `> 0` in
   current** — including 5 rows where `recognized_by_registered_rule` is
   true (heading recognized directly, not `b1_winner`-derived) rather than
   the body-preamble path, proving the mechanism is not specific to
   `b1_winner` rows — any row reachable through this guard is exposed.

This is a genuinely different defect class from the "new `starts` entry
shrinks/truncates a neighbor" hypothesis framed in the brief: the removal
is not a boundary-arithmetic side effect of `close_entries` — it is a
control-flow guard in a *different* function (`us_profile.py`, not
`us_markers_boundary.py`) reacting to the primary engine's candidate count
going from 0 to >0.

### Classification of all 134

`was_in_baseline_candidates=True, still_in_current_candidates=False` for
all 134 (verified directly, 0 exceptions) — every removal is a genuine
disappearance from the extraction output, not a boundary artifact of the
diff key. Cross-checked for replaced-by-variant (same definition surviving
under a differently-spelled term key at the same row): **zero** true
matches — every apparent substring overlap (e.g. `owner` / `former owner`,
`Insurer` / `Captive insurer`) is a different, separately-defined term with
different definition text, not a rename.

**Classification: 130 genuine loss, 4 phantom-removal, 0 replaced-by-variant.**

The 4 phantom-removals are baseline fallback false-positives whose captured
"term" is not a real definiendum at all — a legislative-history caption or
a stray preposition, evidently mis-paired by the fallback's own quote
scanning against annotation text, not the widened idiom's doing:

- FED row 2333, term `for` — definition text is Editorial-Notes amendment
  prose (`"...deleted in cl. (1) "other" before "official signs"..."`), not
  a definition.
- FED row 4978, term `2010—Subsec. (b)(1). Pub. L. 111–203, §610(a)(1),
  substituted` — a legislative-history caption captured as if it were a
  quoted term.
- FED row 4978, term `for` — a preposition; the attached definition text
  ("all direct or indirect advances of funds...") is real loan/credit
  content but keyed to the wrong (nonsensical) term.
- FED row 34432, term `2006—Subsec. (e)(2). Pub. L. 109–181 added par. (2)
  and struck out former par. (2) which read as follows:` — same caption
  pattern.

One further row (FED 11310, term `Continental United States\n\nPub. L.
86–70, §48, June 25, 1959, 73 Stat. 154, provided that:`) has a similarly
garbled *term key* (a real term, "Continental United States", glued to a
trailing citation fragment by the same fallback quote-pairing weakness),
but its definition text (`"the 49 States on the North American Continent
and the District of Columbia, unless otherwise expressly provided."`) is
unambiguously the real, correct definition — counted as genuine loss with
a pre-existing term-formatting caveat, not phantom.

The remaining 130 were spot-checked across every affected jurisdiction
(FED/ME/MI/NJ/NY/OH/OK/SC/VA/WA) and are real statutory content: clean
single-sentence definitions (`WA "recovery"` → `"all damages except loss
of consortium."`), full Executive Order definitions (FED 12889's 7 terms),
enumerated-list definitions (OH's many `"X" means all of the following: (a)
...(b)...`), and forwarding cross-references (FED `"Executive Director"` →
`"given such term by section 8401(13) of title 5, United States Code."`).
Several baseline captures were already imperfect *in their own right*
(bleeding a few words into the next entry's marker, e.g. FED 12889's
`"...(b) The term"` tail, or in one case — FED row 72 `emergency` —
running unbounded through the entire remainder of a very long section's
amendment history because the fallback has no ceiling or trailing-stop
awareness at all) — but in every genuine case the *core* definitional
content is real and is now completely absent, not merely re-bounded.

### Full 134-row table

| # | Jurisdiction | act_id (statute evidence) | Term | Mechanism | Classification | definition_text (baseline, truncated) |
|---|---|---|---|---|---|---|
| 1 | US-FED | USC_T15_C2B_S78l (row 72) | emergency | FALLBACK_SUPPRESSION | GENUINE LOSS | —  (A) a major market disturbance characterized by or constituting—  (i) sudden and excessive fluctuations of |
| 2 | US-FED | USC_T23_C1_S131 (row 2333) | for | FALLBACK_SUPPRESSION | PHANTOM-REMOVAL | that after January 1, 1968, such signs, displays, and devices", deleted in cl. (1) "other" before "official si |
| 3 | US-FED | USC_T43_C35_S1732 (row 2476) | invasive species | FALLBACK_SUPPRESSION | GENUINE LOSS | , with respect to a particular ecosystem, a nonnative organism, the introduction of which causes or is likely |
| 4 | US-FED | USC_T43_C35_S1732 (row 2476) | locally adapted | FALLBACK_SUPPRESSION | GENUINE LOSS | , with respect to plants, plants that—  "(A) originate from an area that is geographically proximate to a plan |
| 5 | US-FED | USC_T43_C35_S1732 (row 2476) | native plant species | FALLBACK_SUPPRESSION | GENUINE LOSS | , with respect to a particular ecosystem, a species that, other than as a result of an introduction, historica |
| 6 | US-FED | USC_T43_C35_S1732 (row 2476) | nonnative | FALLBACK_SUPPRESSION | GENUINE LOSS | , with respect to a particular ecosystem, an organism, including the seeds, eggs, spores, or other biological |
| 7 | US-FED | USC_T43_C35_S1732 (row 2476) | plant material | FALLBACK_SUPPRESSION | GENUINE LOSS | a plant or the seeds, eggs, spores, or other biological material of a plant capable of propagating the species |
| 8 | US-FED | USC_T5_C83_S8351 (row 3651) | Executive Director | FALLBACK_SUPPRESSION | GENUINE LOSS | given such term by section 8401(13) of title 5, United States Code. |
| 9 | US-FED | USC_T5_C83_S8351 (row 3651) | election period | FALLBACK_SUPPRESSION | GENUINE LOSS | a period afforded under section 8432(b) of title 5, United States Code; and  "(B) the term |
| 10 | US-FED | USC_T12_C2_S84 (row 4978) | 2010—Subsec. (b)(1). Pub. L. 111–203, §610(a)(1), substituted | FALLBACK_SUPPRESSION | PHANTOM-REMOVAL | — |
| 11 | US-FED | USC_T12_C2_S84 (row 4978) | derivative transaction | FALLBACK_SUPPRESSION | GENUINE LOSS | any transaction that is a contract, agreement, swap, warrant, note, or option that is based, in whole or in pa |
| 12 | US-FED | USC_T12_C2_S84 (row 4978) | for | FALLBACK_SUPPRESSION | PHANTOM-REMOVAL | all direct or indirect advances of funds to a person made on the basis of any obligation of that person to rep |
| 13 | US-FED | USC_T1_C1_S1 (row 11310) | Continental United States \n Pub. L. 86–70, §48, June 25, 1959, 73 Stat. 154, provided that: | FALLBACK_SUPPRESSION | GENUINE LOSS (term-key corrupted, pre-existing) | the 49 States on the North American Continent and the District of Columbia, unless otherwise expressly provide |
| 14 | US-FED | USC_T1_C1_S1 (row 11310) | oath | FALLBACK_SUPPRESSION | GENUINE LOSS | affirmation, and |
| 15 | US-FED | USC_T1_C1_S1 (row 11310) | officer | FALLBACK_SUPPRESSION | GENUINE LOSS | any person authorized by law to perform the duties of the office;  "signature" or |
| 16 | US-FED | USC_T1_C1_S1 (row 11310) | subscription | FALLBACK_SUPPRESSION | GENUINE LOSS | a mark when the person making the same intended it as such; |
| 17 | US-FED | USC_T1_C1_S1 (row 11310) | sworn | FALLBACK_SUPPRESSION | GENUINE LOSS | affirmed; |
| 18 | US-FED | USC_T1_C1_S1 (row 11310) | writing | FALLBACK_SUPPRESSION | GENUINE LOSS | printing and typewriting and reproductions of visual symbols by photographing, multigraphing, mimeographing, m |
| 19 | US-FED | USC_T29_C4C_S50 (row 12889) | Labor-Management Forum | FALLBACK_SUPPRESSION | GENUINE LOSS | a nonadversarial forum for managers, employees, and employees' union representatives to discuss how Federal Go |
| 20 | US-FED | USC_T29_C4C_S50 (row 12889) | Labor-Management Forum agencies | FALLBACK_SUPPRESSION | GENUINE LOSS | all agencies subject to chapter 71 of title 5, United States Code.  Sec. 3. Registered Apprenticeship Interage |
| 21 | US-FED | USC_T29_C4C_S50 (row 12889) | Pre-Apprenticeship | FALLBACK_SUPPRESSION | GENUINE LOSS | set forth in 29 CFR 30.2.  (c) The term |
| 22 | US-FED | USC_T29_C4C_S50 (row 12889) | Registered Apprenticeship | FALLBACK_SUPPRESSION | GENUINE LOSS | an industry-driven career pathway through which employers can develop and prepare their future workforces and |
| 23 | US-FED | USC_T29_C4C_S50 (row 12889) | agencies | FALLBACK_SUPPRESSION | GENUINE LOSS | the Department of State, the Department of the Treasury, the Department of Defense, the Department of the Inte |
| 24 | US-FED | USC_T29_C4C_S50 (row 12889) | interested agencies | FALLBACK_SUPPRESSION | GENUINE LOSS | agencies as defined in subsection (d) of this section, the heads of which are not listed in section 3(b) of th |
| 25 | US-FED | USC_T29_C4C_S50 (row 12889) | participating agencies | FALLBACK_SUPPRESSION | GENUINE LOSS | agencies led by the heads of agencies listed in section 3(b) of this order.  (f) The term |
| 26 | US-FED | USC_T18_C113_S2319A (row 34432) | 2006—Subsec. (e)(2). Pub. L. 109–181 added par. (2) and struck out former par. (2) which read as follows: | FALLBACK_SUPPRESSION | PHANTOM-REMOVAL | transport, transfer, or otherwise dispose of, to another, as consideration for anything of value, or make or o |
| 27 | US-FED | USC_T4_C4_S104 (row 45011) | lease | FALLBACK_SUPPRESSION | GENUINE LOSS | a contract. |
| 28 | US-ME | STATE_ME_T30-A_P2_C187_S4353-A (row 505) | structures necessary for access to or egress from the dwelling | FALLBACK_SUPPRESSION | GENUINE LOSS | ramps and associated railings, walls or roof systems necessary for the safety or effectiveness of the ramps. [ |
| 29 | US-ME | STATE_ME_T35-A_P6_C61_S6109-A (row 1027) | lease | FALLBACK_SUPPRESSION | GENUINE LOSS | a lease of any length, including leases that may be defined as sales for income tax purposes. [PL 2003, c. 267 |
| 30 | US-ME | STATE_ME_T24-A_C23_S2169 (row 1783) | policy | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, any temporary contract or binder, by whatever name known, under the terms of which in |
| 31 | US-ME | STATE_ME_T20-A_P7_C606-B_S15689-A (row 4663) | secondary student | FALLBACK_SUPPRESSION | GENUINE LOSS | a student in a home instruction program pursuant to section 5001‑A, subsection 3, paragraph A , subparagraph ( |
| 32 | US-ME | STATE_ME_T36_P2_C111_S1483 (row 5405) | person on active duty serving in the Armed Forces of the United States | FALLBACK_SUPPRESSION | GENUINE LOSS | a member of the National Guard or the Reserves of the United States Armed Forces as long as the person satisfi |
| 33 | US-ME | STATE_ME_T10_P3_C205-A_S1210-B (row 5529) | credit services | FALLBACK_SUPPRESSION | GENUINE LOSS | any extension of credit and any product or service that a supervised lender is authorized by law or regulation |
| 34 | US-ME | STATE_ME_T32_C69_S4668 (row 9589) | credit services | FALLBACK_SUPPRESSION | GENUINE LOSS | any extension of credit and any product or service that a supervised lender is authorized by law or regulation |
| 35 | US-ME | STATE_ME_T28-B_C3_S1501 (row 11069) | remuneration | FALLBACK_SUPPRESSION | GENUINE LOSS | a donation or any other monetary payment received directly or indirectly by a person in exchange for goods or |
| 36 | US-ME | STATE_ME_T35-A_P6_C61_S6113 (row 16584) | protection of public water supply | FALLBACK_SUPPRESSION | GENUINE LOSS | watershed protection, groundwater protection or wellhead protection reasonably necessary to minimize the poten |
| 37 | US-ME | STATE_ME_T24-A_C23_S2168 (row 18220) | policy | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, any temporary contract or binder, by whatever name known, under the terms of which in |
| 38 | US-MI | STATE_MI_C500_AAct-218-of-1956_S500.8106 (row 10463) | person | FALLBACK_SUPPRESSION | GENUINE LOSS | a person who exercises control directly or indirectly over activities of the insurer through a holding company |
| 39 | US-NJ | STATE_NJ_T43_C21_S21-7 (row 1732) | wages | FALLBACK_SUPPRESSION | GENUINE LOSS | the first $4,800.00 paid during calendar year 1975, for services performed either within or without this State |
| 40 | US-NJ | STATE_NJ_T52_C17B_S17B-71e (row 2286) | deceptive conduct | FALLBACK_SUPPRESSION | GENUINE LOSS | but not be limited to: (a) a sustained finding that a law enforcement officer filed a false report or submitte |
| 41 | US-NJ | STATE_NJ_T2C_C21_S21-15 (row 11124) | Fiduciary | FALLBACK_SUPPRESSION | GENUINE LOSS | trustee, guardian, executor, administrator, receiver and any person carrying on fiduciary functions on behalf |
| 42 | US-NJ | STATE_NJ_T26_C2H_S2H-7 (row 13259) | person | FALLBACK_SUPPRESSION | GENUINE LOSS | a corporation, company, association, society, firm, partnership, and joint stock company, as well as an indivi |
| 43 | US-NJ | STATE_NJ_T2C_C58_S58-3.4 (row 21386) | collector | FALLBACK_SUPPRESSION | GENUINE LOSS | any person who devotes time and attention to acquiring firearms for the enhancement of the person's collection |
| 44 | US-NJ | STATE_NJ_T2A_C18_S18-61.6 (row 23205) | owner | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, lessee, successor owner and lessee, and other successors in interest. e. An owner sha |
| 45 | US-NY | STATE_NY_ARPT_A4_T3_S491*2 (row 601) | natural resources | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, agricultural lands defined as open lands actually used in bona fide agricultural prod |
| 46 | US-NY | STATE_NY_ARPT_A4_T2_S459-C (row 691) | income | FALLBACK_SUPPRESSION | GENUINE LOSS | the "adjusted gross income" for federal income tax purposes as reported on the applicant's federal or state in |
| 47 | US-NY | STATE_NY_APBA_A3_T3_S553 (row 1504) | structures | FALLBACK_SUPPRESSION | GENUINE LOSS |  and include buildings used as and for hospitals, schools, community and religious institutions, cultural and |
| 48 | US-NY | STATE_NY_AGBS_A26_S399-Q (row 1978) | Bakery basket | FALLBACK_SUPPRESSION | GENUINE LOSS | to transport, store or carry bakery products.   b. |
| 49 | US-NY | STATE_NY_AGBS_A26_S399-Q (row 1978) | Bakery tray | FALLBACK_SUPPRESSION | GENUINE LOSS | to transport, store or carry bakery products.   c. "Container". A bakery basket, bakery tray, dairy case, egg |
| 50 | US-NY | STATE_NY_AGBS_A26_S399-Q (row 1978) | Dairy case | FALLBACK_SUPPRESSION | GENUINE LOSS | to transport, store or carry dairy products.   e. |
| 51 | US-NY | STATE_NY_AGBS_A26_S399-Q (row 1978) | Egg basket | FALLBACK_SUPPRESSION | GENUINE LOSS | to transport, store or carry eggs.   f. "Laundry cart". A basket which is mounted on wheels and used in a coin |
| 52 | US-NY | STATE_NY_AGBS_A26_S399-Q (row 1978) | Poultry box | FALLBACK_SUPPRESSION | GENUINE LOSS | to transport, store or carry poultry.   j. "Shopping cart". A basket which is mounted on wheels, or a similar |
| 53 | US-NY | STATE_NY_APBH_A28_S2801-A (row 2032) | Controlling person | FALLBACK_SUPPRESSION | GENUINE LOSS | any person who by reason of a direct or indirect ownership interest (whether of record or beneficial) has the |
| 54 | US-NY | STATE_NY_APBH_A28_S2801-A (row 2032) | Principal member | FALLBACK_SUPPRESSION | GENUINE LOSS | any person who beneficially owns, holds or has the power to vote, ten percent or more interest determined by s |
| 55 | US-NY | STATE_NY_APBH_A28_S2801-A (row 2032) | Principal stockholder | FALLBACK_SUPPRESSION | GENUINE LOSS | any person who beneficially owns, holds or has the power to vote, ten percent or more of any class of securiti |
| 56 | US-NY | STATE_NY_ALFN_A2_T8_S107.00 (row 2768) | current funds | FALLBACK_SUPPRESSION | GENUINE LOSS | only budgetary appropriations for capital improvements or equipment which appropriations have not lapsed, or t |
| 57 | US-NY | STATE_NY_ALFN_A2_T8_S107.00 (row 2768) | net indebtedness | FALLBACK_SUPPRESSION | GENUINE LOSS | the total net indebtedness as ascertained pursuant to section 138.00 of this chapter. The percentage of debt-c |
| 58 | US-NY | STATE_NY_ARPT_A4_T2_S467 (row 4091) | income | FALLBACK_SUPPRESSION | GENUINE LOSS | the "adjusted gross income" for federal income tax purposes as reported on the applicant's federal or state in |
| 59 | US-NY | STATE_NY_AGMU_A2_S6-C (row 4747) | governing board | FALLBACK_SUPPRESSION | GENUINE LOSS | the board of trustees thereof; insofar as it is used in reference to a town, shall mean the town board thereof |
| 60 | US-NY | STATE_NY_AGMU_A2_S6-C (row 4747) | obligations | FALLBACK_SUPPRESSION | GENUINE LOSS | bonds, notes, certificates or other evidences of indebtedness.   2. The governing board of any county, city, v |
| 61 | US-NY | STATE_NY_ACVS_A8_TA_S115 (row 5396) | protected class | FALLBACK_SUPPRESSION | GENUINE LOSS | age, race, creed, color, national origin, sexual orientation, gender identity or expression, military status, |
| 62 | US-NY | STATE_NY_ARPT_A4_T3_S491 (row 6869) | natural resources | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, agricultural lands defined as open lands actually used in bona fide agricultural prod |
| 63 | US-NY | STATE_NY_ARPT_A4_T3_S491-A*2 (row 7009) | natural resources | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, agricultural lands defined as open lands actually used in bona fide agricultural prod |
| 64 | US-NY | STATE_NY_AGMU_A5_S92-A (row 7103) | retired officer | FALLBACK_SUPPRESSION | GENUINE LOSS |  any former school board member with twenty years or more service in such position. The total cost of particip |
| 65 | US-NY | STATE_NY_ALAB_A7_S204 (row 9087) | unfired pressure vessel | FALLBACK_SUPPRESSION | GENUINE LOSS | containers for the containment of internal or external pressure which may be obtained from an external source |
| 66 | US-NY | STATE_NY_AEXC_A22_S631 (row 10039) | necessary court appearances | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, any part of trial from arraignment through sentencing, pre and post trial hearings an |
| 67 | US-NY | STATE_NY_AEXC_A22_S631 (row 10039) | support agency for survivors of crime | FALLBACK_SUPPRESSION | GENUINE LOSS |    (i) a governmental agency responsible for child and/or adult protective services pursuant to title six of a |
| 68 | US-NY | STATE_NY_AEXC_A22_S631 (row 10039) | victim services provider | FALLBACK_SUPPRESSION | GENUINE LOSS | a city or state contracted victim service provider who has provided services to the victim of the crime, or ot |
| 69 | US-NY | STATE_NY_AVAT_T5_A19_S501 (row 13882) | school | FALLBACK_SUPPRESSION | GENUINE LOSS |  instruction, education or training licensed or approved by a department or agency of the state or training co |
| 70 | US-NY | STATE_NY_ARPT_A4_T3_S491-B (row 16586) | natural or scenic resources | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, agricultural lands defined as open lands actually used in bona fide agricultural prod |
| 71 | US-NY | STATE_NY_ARPT_A4_T3_S491-A (row 19198) | natural or scenic resources | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, agricultural lands defined as open lands actually used in bona fide agricultural prod |
| 72 | US-NY | STATE_NY_ALAB_A2_S44 (row 26977) | Construction | FALLBACK_SUPPRESSION | GENUINE LOSS | , but not be limited to, any work involving the construction, reconstruction, alteration, rehabilitation, repa |
| 73 | US-NY | STATE_NY_AENG_A21_S21-106 (row 27664) | related facilities | FALLBACK_SUPPRESSION | GENUINE LOSS | any land, work, system, building, improvement, instrumentality or thing necessary or convenient to the constru |
| 74 | US-NY | STATE_NY_ABNK_A3_S105 (row 27958) | village | FALLBACK_SUPPRESSION | GENUINE LOSS | either an incorporated or an unincorporated village.   5. (a) A bank or trust company may, if the merger or as |
| 75 | US-NY | STATE_NY_ACPL_P1_TD_A60_S60.45 (row 29376) | involuntarily made | FALLBACK_SUPPRESSION | GENUINE LOSS | of any other improper conduct or undue pressure which impaired the defendant's physical or mental condition to |
| 76 | US-OH | STATE_OH_T15_C1509_S1509.074 (row 1511) | Owner | FALLBACK_SUPPRESSION | GENUINE LOSS | a person that is an authorized agent of an owner. |
| 77 | US-OH | STATE_OH_T33_C3326_S3326.51 (row 2752) | STEM school sponsoring district | FALLBACK_SUPPRESSION | GENUINE LOSS | a municipal, city, local, or exempted village school district that governs and controls a STEM school pursuant |
| 78 | US-OH | STATE_OH_T11_C1109_S1109.22 (row 3296) | Derivative transaction | FALLBACK_SUPPRESSION | GENUINE LOSS | any transaction that is a contract, agreement, swap, warrant, note, or option that is based, in whole or in pa |
| 79 | US-OH | STATE_OH_T11_C1109_S1109.22 (row 3296) | Person | FALLBACK_SUPPRESSION | GENUINE LOSS | an individual; sole proprietorship; partnership; joint venture; association; trust; estate; business trust; co |
| 80 | US-OH | STATE_OH_T3_C341_S341.26 (row 3447) | Prisoner | FALLBACK_SUPPRESSION | GENUINE LOSS | a person confined in a jail or multicounty correctional center following a conviction of or plea of guilty to |
| 81 | US-OH | STATE_OH_T57_C5747_S5747.062 (row 4820) | Recipient | FALLBACK_SUPPRESSION | GENUINE LOSS | a transferee. "Lottery prize award" does not include a prize award from a video lottery terminal and does not |
| 82 | US-OH | STATE_OH_T57_C5747_S5747.062 (row 4820) | lottery prize award | FALLBACK_SUPPRESSION | GENUINE LOSS | winnings from lottery sports gaming wagers placed through a terminal described in division (B)(3) of section 3 |
| 83 | US-OH | STATE_OH_T3_C323_S323.122 (row 4941) | Dependent parent | FALLBACK_SUPPRESSION | GENUINE LOSS | a parent who, at the time the member was activated, received from the member at least half of the dependent pa |
| 84 | US-OH | STATE_OH_T31_C3123_S3123.89 (row 6141) | Lottery prize award | FALLBACK_SUPPRESSION | GENUINE LOSS | a prize award from a video lottery terminal but does not include winnings from lottery sports gaming, except f |
| 85 | US-OH | STATE_OH_T63_C6301_S6301.23 (row 6791) | Ohio career-technical associations | FALLBACK_SUPPRESSION | GENUINE LOSS | all of the following: (a) The Ohio association of career and technical education; (b) The Ohio association of |
| 86 | US-OH | STATE_OH_T21_C2131_S2131.08 (row 6965) | Exercisable by deed | FALLBACK_SUPPRESSION | GENUINE LOSS | a power that can be exercised during the power holder's lifetime by an instrument that takes effect immediatel |
| 87 | US-OH | STATE_OH_T39_C3923_S3923.57 (row 7807) | individual | FALLBACK_SUPPRESSION | GENUINE LOSS | the association of which the individual is a member. For purposes of this section, any policy issued pursuant |
| 88 | US-OH | STATE_OH_T29_C2901_S2901.13 (row 9540) | aggrieved person | FALLBACK_SUPPRESSION | GENUINE LOSS | any of the following individuals with regard to a violation of section 2907.13 of the Revised Code: (i) A pati |
| 89 | US-OH | STATE_OH_T29_C2901_S2901.13 (row 9540) | offense is directly related to the misconduct in office of a public servant | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, a violation of section 101.71 , 101.91 , 121.61 or 2921.13 , division (F) or (H) of s |
| 90 | US-OH | STATE_OH_T29_C2945_S2945.49 (row 9694) | victim | FALLBACK_SUPPRESSION | GENUINE LOSS | any person who was a victim of a felony violation identified in division (B)(1) of this section or a felony of |
| 91 | US-OH | STATE_OH_T45_C4511_S4511.701 (row 11936) | viable communication | FALLBACK_SUPPRESSION | GENUINE LOSS | a cellular or satellite telephone, a radio, or any other similar electronic wireless communications device. (D |
| 92 | US-OH | STATE_OH_T3_C313_S313.10 (row 12152) | Full and complete records of the coroner | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, the following: (a) The detailed descriptions of the observations written by the coron |
| 93 | US-OH | STATE_OH_T3_C307_S307.022 (row 12352) | Correctional facilities | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, jails, detention facilities, workhouses, community-based correctional facilities, and |
| 94 | US-OH | STATE_OH_T33_C3345_S3345.40 (row 12756) | The actual loss of the person who is awarded the damages | FALLBACK_SUPPRESSION | GENUINE LOSS | all of the following: (i) All wages, salaries, or other compensation lost by an injured person as a result of |
| 95 | US-OH | STATE_OH_T7_C742_S742.41 (row 13220) | Personal history record | FALLBACK_SUPPRESSION | GENUINE LOSS | a member's, former member's, or other system retirant's name, address, telephone number, social security numbe |
| 96 | US-OH | STATE_OH_T3_C305_S305.171 (row 13992) | County officer or employee | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, a member or employee of the county board of elections. (2) "County-operated municipal |
| 97 | US-OH | STATE_OH_T29_C2925_S2925.42 (row 15375) | Law enforcement agencies | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, the state board of pharmacy and the office of a prosecutor. (2) "Prosecutor" has the |
| 98 | US-OH | STATE_OH_T57_C5751_S5751.033 (row 16260) | delivery of tangible personal property by motor carrier or by other means of transportation | FALLBACK_SUPPRESSION | GENUINE LOSS | the situation in which a purchaser accepts the property in this state and then transports the property directl |
| 99 | US-OH | STATE_OH_T29_C2945_S2945.482 (row 17614) | Victim with a developmental disability | FALLBACK_SUPPRESSION | GENUINE LOSS | a person with a developmental disability who was a victim of a violation identified in division (B)(1) of this |
| 100 | US-OH | STATE_OH_T21_C2152_S2152.811 (row 18568) | Victim with a developmental disability | FALLBACK_SUPPRESSION | GENUINE LOSS | any of the following persons: (a) A person with a developmental disability who was a victim of a violation ide |
| 101 | US-OH | STATE_OH_T61_C6119_S6119.37 (row 18663) | Regional water and sewer district | FALLBACK_SUPPRESSION | GENUINE LOSS | a district organized under this chapter that has been designated as either a regional water district or a regi |
| 102 | US-OH | STATE_OH_T39_C3901_S3901.17 (row 18782) | Insurer | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to, any person that is an affiliate of or affiliated with the insurer, as defined in sect |
| 103 | US-OH | STATE_OH_T29_C2935_S2935.032 (row 20067) | The offense of violating a protection order | FALLBACK_SUPPRESSION | GENUINE LOSS | the former offense of violating a protection order or consent agreement or anti-stalking protection order as s |
| 104 | US-OH | STATE_OH_T7_C703_S703.377 (row 20117) | Legislative authority | FALLBACK_SUPPRESSION | GENUINE LOSS | the legislative authority of a municipal corporation or board of trustees of a township. (B) During the period |
| 105 | US-OH | STATE_OH_T5_C505_S505.375 (row 22284) | Governmental agency | FALLBACK_SUPPRESSION | GENUINE LOSS | all departments, boards, offices, commissions, agencies, colleges, universities, institutions, and other instr |
| 106 | US-OH | STATE_OH_T29_C2945_S2945.491 (row 22796) | Victim with a developmental disability | FALLBACK_SUPPRESSION | GENUINE LOSS | a person with a developmental disability who was a victim of a felony violation identified in division (B)(1) |
| 107 | US-OH | STATE_OH_T61_C6101_S6101.50 (row 24054) | direct obligations of, or obligations guaranteed as to payment by, the United States | FALLBACK_SUPPRESSION | GENUINE LOSS | rights to receive payment or portions of payments of the principal of, or interest or other investment income |
| 108 | US-OH | STATE_OH_T7_C709_S709.023 (row 25046) | buffer | FALLBACK_SUPPRESSION | GENUINE LOSS | open space, landscaping, fences, walls, and other structured elements; streets and street rights-of-way; and b |
| 109 | US-OH | STATE_OH_T33_C3319_S3319.285 (row 29285) | Eligible military individual | FALLBACK_SUPPRESSION | GENUINE LOSS | any of the following: (a) An active-duty member of any branch of the United States armed forces; (b) A veteran |
| 110 | US-OH | STATE_OH_T37_C3701_S3701.17 (row 29721) | Protected health information | FALLBACK_SUPPRESSION | GENUINE LOSS | information, in any form, including oral, written, electronic, visual, pictorial, or physical that describes a |
| 111 | US-OH | STATE_OH_T45_C4511_S4511.75 (row 29882) | School bus, | FALLBACK_SUPPRESSION | GENUINE LOSS | a bus that is owned and operated by a head start agency, is equipped with an automatically extended stop warni |
| 112 | US-OH | STATE_OH_T29_C2905_S2905.12 (row 30073) | Threat | FALLBACK_SUPPRESSION | GENUINE LOSS | a direct threat and a threat by innuendo. (2) "Community control sanction" has the same meaning as in section |
| 113 | US-OH | STATE_OH_T5_C505_S505.44 (row 31324) | State agency | FALLBACK_SUPPRESSION | GENUINE LOSS | all departments, boards, offices, commissions, agencies, colleges, universities, institutions, and other instr |
| 114 | US-OH | STATE_OH_T11_C1115_S1115.06 (row 31905) | Control | FALLBACK_SUPPRESSION | GENUINE LOSS | either of the following: (a) Power, directly or indirectly, to direct the management or policies of a state ba |
| 115 | US-OH | STATE_OH_T11_C1115_S1115.06 (row 31905) | State bank | FALLBACK_SUPPRESSION | GENUINE LOSS | any bank holding company that controls a state bank, and any other company that controls a state bank and is n |
| 116 | US-OH | STATE_OH_T55_C5553_S5553.042 (row 32464) | Service facilities | FALLBACK_SUPPRESSION | GENUINE LOSS | any conduit, cable, wire, tower, pole, or other equipment or appliance of a public utility or electric coopera |
| 117 | US-OK | STATE_OK_T63_S63-2-309 (row 4467) | Prescription | FALLBACK_SUPPRESSION | GENUINE LOSS | a written, oral or electronic order by a practitioner to a pharmacist for a controlled dangerous substance f |
| 118 | US-OK | STATE_OK_T63_S63-2-309 (row 4467) | Registered practitioner | FALLBACK_SUPPRESSION | GENUINE LOSS | a licensed practitioner duly registered with the Oklahoma State Bureau of Narcotics and Dangerous Drugs Cont |
| 119 | US-OK | STATE_OK_T14A_S14A-5-203 (row 5753) | creditor | FALLBACK_SUPPRESSION | GENUINE LOSS | sellers, lessors, lenders, persons who regularly offer to lease or arrange to lease under consumer leases an |
| 120 | US-OK | STATE_OK_T21_S21-1111v1 (row 8656) | Employee of an institution of higher education | FALLBACK_SUPPRESSION | GENUINE LOSS | faculty, adjunct faculty, instructors, volunteers, or an employee of a business contracting with an institut |
| 121 | US-SC | STATE_SC_T17_C5_A7_S17-5-555 (row 404) | unexpected death | FALLBACK_SUPPRESSION | GENUINE LOSS | all vulnerable adult deaths that, before investigation, appear possibly to have been caused by trauma, suspici |
| 122 | US-SC | STATE_SC_T44_C56_A1_S44-56-200 (row 3814) | media | FALLBACK_SUPPRESSION | GENUINE LOSS | the following portions of the environment: (a) soil; (b) surface water; (c) sediments; (d) ambient, noncontain |
| 123 | US-SC | STATE_SC_T6_C1_A1_S6-1-130 (row 7246) | political subdivision | FALLBACK_SUPPRESSION | GENUINE LOSS | , but is not limited to a municipality, county, school district, special purpose district, or public service d |
| 124 | US-SC | STATE_SC_T59_C1_A3_S59-1-210 (row 18781) | Hours of instruction | FALLBACK_SUPPRESSION | GENUINE LOSS | in-person instruction, virtual instruction, self-guided learning, and experiential learning through approved o |
| 125 | US-VA | STATE_VA_T40.1_C3_A2_S40.1-29 (row 3366) | Wages | FALLBACK_SUPPRESSION | GENUINE LOSS | any remuneration an employer owes to an employee, including hourly wages, minimum wages, piece rate wages, day |
| 126 | US-VA | STATE_VA_T60.2_C6_A6_S60.2-633 (row 7729) | benefits under this title | FALLBACK_SUPPRESSION | GENUINE LOSS | benefits under an unemployment benefit program of the United States or of any other state. In the event the cl |
| 127 | US-VA | STATE_VA_T38.2_C2_S38.2-209 (row 9693) | Individual, | FALLBACK_SUPPRESSION | GENUINE LOSS | and include any person, group, business, company, organization, receiver, trustee, security, corporation, part |
| 128 | US-VA | STATE_VA_T18.2_C4_A6_S18.2-60.3 (row 13341) | Electronically transmitted communication | FALLBACK_SUPPRESSION | GENUINE LOSS | communication by telephone, computer, or other electronic device.  "Family or household member" has the same m |
| 129 | US-VA | STATE_VA_T18.2_C4_A6_S18.2-60.3 (row 13341) | release | FALLBACK_SUPPRESSION | GENUINE LOSS | a release of the offender from a state correctional facility or a local or regional jail (i) upon completion o |
| 130 | US-WA | STATE_WA_T10_C99_S080 (row 717) | convicted | FALLBACK_SUPPRESSION | GENUINE LOSS | a plea of guilty, a finding of guilt regardless of whether the imposition of the sentence is deferred or any p |
| 131 | US-WA | STATE_WA_T30A_C56_S010 (row 1171) | bank | FALLBACK_SUPPRESSION | GENUINE LOSS | savings banks, mutual savings banks, and trust companies, and |
| 132 | US-WA | STATE_WA_T50_C04_S116 (row 9202) | American employer | FALLBACK_SUPPRESSION | GENUINE LOSS | a person who is: (a) An individual who is a resident of the United States; or (b) A partnership if two-thirds |
| 133 | US-WA | STATE_WA_T9A_C64_S020 (row 19155) | Descendant | FALLBACK_SUPPRESSION | GENUINE LOSS | stepchildren and adopted children under eighteen years of age; (b) "Sexual contact" has the same meaning as in |
| 134 | US-WA | STATE_WA_T51_C24_S030 (row 31321) | recovery | FALLBACK_SUPPRESSION | GENUINE LOSS | all damages except loss of consortium. |

---

## Q2 — additions genuineness + goal coverage

### (a) Deterministic stratified sample of 80

Method: proportional allocation by jurisdiction (largest-remainder rounding)
across the 17 jurisdictions present in the 6,309 pure additions, then
`random.Random(20260820).sample(...)` (seed = sprint date, disclosed) per
jurisdiction stratum, applied to each stratum's anchors pre-sorted into a
deterministic order. Allocation: AZ 10, FED 6, ME 8, ND 1, NJ 2, NY 5, OH
28, OK 2, SC 1, UT 2, VA 4, WA 11 (MI/NM/NV/RI/TX rounded to 0 — their
population share is below 1 in 80).

Every one of the 80 was read directly (term + captured definition text);
three initially-ambiguous rows were resolved by fetching the real corpus
row's raw text: NY row 12867 `family contract` (confirmed a genuine
extending clause of the term, present verbatim in NY insurance law — `A
"family contract" may provide coverage to any child or children not over
nineteen years of age... any unmarried child until attaining age
twenty-five`), OK row 20225 `Utilization management` and OK row 2382
`Health benefit plan` (both confirmed genuine top-level entries in a
numbered list of *separate* defined terms — `4. "Utilization management"
shall include ...; and 5. "Self-advocacy organizations" means ...` — not a
false-positive split of one term's own internal enumeration).

**Result: 80/80 GENUINE, 0 FALSE POSITIVE, 0 AMBIGUOUS (FP rate 0%).**

The dominant shape (≈55/80, concentrated in OH/AZ/UT/VA/WA/ME) is the
`"X" has the (same/following) meaning as/in/provided in <citation>` forward-
reference pattern this item's `has the (following|same) meaning` addition
specifically targets — an extremely common drafting convention in these
states' Revised/Annotated Codes, explaining both the genuineness and the
volume. The remainder are genuine `"X" shall include <substantive text>`
entries.

| # | Jurisdiction | source_row | Term | Classification | definition_text (added, truncated) |
|---|---|---|---|---|---|
| 1 | US-AZ | 12407 | Security interest | GENUINE | prescribed in section 47-1201. |
| 2 | US-AZ | 15321 | public forum | GENUINE | prescribed in section 15-1861. |
| 3 | US-AZ | 19308 | Adult theater | GENUINE | prescribed in section 11-811. |
| 4 | US-AZ | 5245 | Telehealth | GENUINE | prescribed in section 36-3601. |
| 5 | US-AZ | 19830 | Modified adjusted gross income | GENUINE | prescribed in 42 United States Code section 1396a(e)(14). |
| 6 | US-AZ | 10601 | Breach | GENUINE | prescribed in 45 Code of Federal Regulations, part 164, subpart D. |
| 7 | US-AZ | 16765 | Agency | GENUINE | prescribed in section 41-1371 but includes a public body as defined in section 39-121.01, subsection A, paragraph 2. |
| 8 | US-AZ | 18549 | Broker-dealer | GENUINE | as dealer prescribed in section 44-1801. |
| 9 | US-AZ | 11255 | Entity identifying information | GENUINE | prescribed in section 13-2001. |
| 10 | US-AZ | 17533 | Candidate | GENUINE | as in section 16-901. |
| 11 | US-FED | 31871 | Federal Government | GENUINE | that the term "United States" had in the Act of March 3, 1931 (ch. 411, 46 Stat. 1494) (known as the Davis-Bacon Act). (2) Wages, ... |
| 12 | US-FED | 6691 | management of parking supply | GENUINE | any requirement providing that any new facility containing a given number of parking spaces shall receive a permit or other prior ... |
| 13 | US-FED | 14481 | community development financial institution | GENUINE | as in section 4702(5) of this title. |
| 14 | US-FED | 13327 | international organization | GENUINE | as in section 1116(b)(5) of this title; (10) the term "armed conflict" does not include internal disturbances and tensions, such ... |
| 15 | US-FED | 645 | nonimmigrant visa | GENUINE | as in section 101(a)(26) of the Immigration and Nationality Act (8 U.S.C. 1101(a)(26)). |
| 16 | US-FED | 7462 | offer | GENUINE | every attempt or offer to dispose of, or solicitation of an offer to buy, a security or interest in a security, for value. The ter... |
| 17 | US-ME | 3902 | prepaid wireless consumer | GENUINE | as in Title 25, section 2921, subsection 13‑A . |
| 18 | US-ME | 10483 | Houseboat | GENUINE | as in Title 12, section 13001, subsection 12‑B . |
| 19 | US-ME | 24791 | Insulin | GENUINE | as in Title 32, section 13786‑D, subsection 1, paragraph A and includes insulin or an insulin pen that is licensed under the feder... |
| 20 | US-ME | 8765 | Firearm | GENUINE | as in Title 17‑A, section 2, subsection 12‑A . [PL 2001, c. 549, §4 (NEW).] B. |
| 21 | US-ME | 16365 | Renewable resource | GENUINE | as in section 3210, subsection 2, paragraph C . |
| 22 | US-ME | 10791 | Medical debt | GENUINE | as in Title 32, section 11002, subsection 7‑A . |
| 23 | US-ME | 1118 | Resident | GENUINE | as in section 2736‑C, subsection 1, paragraph C‑2 . |
| 24 | US-ME | 19772 | Scheduled drug | GENUINE | as found in Title 17‑A, section 1101, subsection 11 . [PL 1989, c. 536, §§1, 2 (NEW); PL 1989, c. 604, §§2, 3 (AFF).] |
| 25 | US-ND | 25360 | Health benefit plan | GENUINE | as in section 26.1-36.3-01. b. |
| 26 | US-NJ | 13985 | Public body | GENUINE | the State of New Jersey, any of its political subdivisions, any authority created by the Legislature of the State of New Jersey, a... |
| 27 | US-NJ | 35123 | Public entertainment event | GENUINE | a sporting event, a simulcast, or other social, charitable, or athletic event. A license issued under the provisions of this secti... |
| 28 | US-NY | 21607 | Renewable energy resources | GENUINE | sources which are capable of being continuously restored by natural or other means or are so large as to be useable for centuries ... |
| 29 | US-NY | 12867 | family contract | GENUINE (verified against raw corpus text) | any other unmarried child, regardless of age, who is incapable of self-sustaining employment by reason of mental illness, developm... |
| 30 | US-NY | 21372 | fiduciaries | GENUINE | any fiduciary or fiduciaries holding funds for investment, and the term "banking organizations" shall have the same meaning as in ... |
| 31 | US-NY | 13405 | member of the armed forces | GENUINE | active duty military personnel; members of the reserve components of the armed forces; members of the national guard on active dut... |
| 32 | US-NY | 13205 | Director | GENUINE | one of the managers charged with the management of a limited liability trust company as set forth in its articles of organization. |
| 33 | US-OH | 3161 | Affiliated group | GENUINE | as in section 1504 of the Internal Revenue Code. |
| 34 | US-OH | 20640 | Dating relationship | GENUINE | as in section 3113.31 of the Revised Code. |
| 35 | US-OH | 32668 | Person | GENUINE | as in division (C) of section 1.59 of the Revised Code and also includes governmental entities. |
| 36 | US-OH | 27075 | PASSPORT administrative agency | GENUINE | as in section 173.42 of the Revised Code. |
| 37 | US-OH | 20475 | County correctional facility | GENUINE | as in section 341.42 of the Revised Code. |
| 38 | US-OH | 18704 | Inmate account | GENUINE | as in section 2969.21 of the Revised Code. |
| 39 | US-OH | 3703 | Person | GENUINE | as in section 1.59 of the Revised Code and includes an individual, corporation, business trust, estate, trust, partnership, and as... |
| 40 | US-OH | 5021 | Occupant restraining device | GENUINE | as in section 4513.263 of the Revised Code. |
| 41 | US-OH | 18995 | Person with a disability that limits or impairs the ability to walk | GENUINE | as in section 4503.44 of the Revised Code. |
| 42 | US-OH | 3419 | Expenditure | GENUINE | as in section 101.70 of the Revised Code when used in relation to activities of a legislative agent, and the same meaning as in se... |
| 43 | US-OH | 20648 | Skilled nursing facility | GENUINE | as in section 5165.01 of the Revised Code. |
| 44 | US-OH | 17419 | Community addiction services provider | GENUINE | as in section 5119.01 of the Revised Code. |
| 45 | US-OH | 27640 | Disability | GENUINE | as in the "Americans with Disabilities Act of 1990," 42 U.S.C. 12102. |
| 46 | US-OH | 12381 | Theft offense | GENUINE | as in section 2913.01 of the Revised Code. |
| 47 | US-OH | 13729 | qualified long-term care | GENUINE | given in section 7702B(c) of the Internal Revenue Code. Solely for purposes of division |
| 48 | US-OH | 18856 | Depository institution | GENUINE | as in section 3 of the "Federal Deposit Insurance Act," 12 U.S.C. 1813(c), and also includes any credit union. |
| 49 | US-OH | 10614 | Manufactured home | GENUINE | as in section 3781.06 of the Revised Code. |
| 50 | US-OH | 1676 | Business | GENUINE | as in section 1349.19 of the Revised Code. |
| 51 | US-OH | 18803 | internet identifier of record | GENUINE | as in section 9.312 of the Revised Code. |
| 52 | US-OH | 18995 | Vehicle | GENUINE | as in section 4511.01 of the Revised Code. |
| 53 | US-OH | 13991 | Mental health client or patient | GENUINE | as in section 2305.51 of the Revised Code. |
| 54 | US-OH | 26033 | Trade marketing professional | GENUINE | as in section 4301.171 of the Revised Code. |
| 55 | US-OH | 8234 | Psychologist | GENUINE | as in section 4732.01 of the Revised Code. |
| 56 | US-OH | 25122 | Insurer | GENUINE | as in section 3901.32 of the Revised Code. |
| 57 | US-OH | 21152 | Formula ADM | GENUINE | as in section 3317.02 of the Revised Code. |
| 58 | US-OH | 912 | Distressed area | GENUINE | as in section 122.16 of the Revised Code. |
| 59 | US-OH | 5661 | Peace officer | GENUINE | as in section 2935.01 of the Revised Code. |
| 60 | US-OH | 3348 | Controlled substance | GENUINE | as in section 3719.01 of the Revised Code. |
| 61 | US-OK | 20225 | Utilization management | GENUINE (verified against raw corpus text) | step therapy, prior authorization restrictions and the use of formulary restrictions to restrict access to a drug or other healt... |
| 62 | US-OK | 2382 | Health benefit plan | GENUINE (verified against raw corpus text) | as provided by Section 6060.4 of Title 36 of the Oklahoma Statutes; and |
| 63 | US-SC | 14882 | gross revenues | GENUINE | only those revenues that are attributable to cable or video services based on the provider's books and records, such revenues to b... |
| 64 | US-UT | 544 | Indian tribe | GENUINE | as defined in Section 9-9-402. |
| 65 | US-UT | 23849 | Bodily injury | GENUINE | as defined in Section 76-1-101.5. |
| 66 | US-VA | 26664 | Articles of incorporation | GENUINE | as specified in § 13.1-603 . |
| 67 | US-VA | 26664 | Stock corporation | GENUINE | as "domestic corporation" as specified in § 13.1-603 . 2016, c. 288 . |
| 68 | US-VA | 29598 | Employer | GENUINE | as provided in 29 U.S.C. § 203. |
| 69 | US-VA | 1059 | Elementary or secondary | GENUINE | as provided in § 22.1-1 . |
| 70 | US-WA | 47045 | carrier | GENUINE | as in RCW 48.43.005 . |
| 71 | US-WA | 20178 | Vulnerable adult | GENUINE | as provided in RCW 74.34.020 . |
| 72 | US-WA | 42416 | Extended warranty | GENUINE | as in RCW 82.04.050 (7). |
| 73 | US-WA | 40839 | Landlord | GENUINE | as in RCW 59.20.030 ; |
| 74 | US-WA | 28151 | Affiliate | GENUINE | as in RCW 48.31B.005 (1). |
| 75 | US-WA | 10236 | Pacific Northwest | GENUINE | as defined for the Bonneville power administration in section 3 of the Pacific Northwest electric power planning and conservation ... |
| 76 | US-WA | 6093 | Sexual assault | GENUINE | as in RCW 70.125.030 . |
| 77 | US-WA | 32192 | Affordable housing | GENUINE | as in RCW 36.70A.030 . |
| 78 | US-WA | 46948 | Project permit | GENUINE | as defined in RCW 36.70B.020 . |
| 79 | US-WA | 27125 | Peer supporter | GENUINE | as defined in RCW 5.60.060 . |
| 80 | US-WA | 2515 | Institution of higher education | GENUINE | as in RCW 28B.10.016 . |

### (b) Goal coverage against the Planner's 118-anchor inventory

**Finding stated plainly: the Planner's 118-anchor loss inventory is not a
retrievable list.** Per the log doc's own §1, the 118 count came from "one
throwaway pytest probe, deleted before any commit — not part of this
sprint's committed test set," and the underlying candidate/loss artifacts
"no longer exist on disk in any worktree." No enumerated row/term list for
"the 118" exists anywhere in the committed repo. An anchor-by-anchor
coverage check against the true 118 is therefore **not possible** from any
committed evidence.

What the log doc *does* name concretely (§2, §4) are 4 specific rows:

| Row (act_id) | Term | Named in log as | Found among gate-2 additions? |
|---|---|---|---|
| `STATE_NJ_T27_C1A_S1A-3.1` (row 8866) | Department | The issue's own director-verified `shall include` recovery example | **Yes** — `pure_added` |
| `STATE_NJ_T34_C1A_S1A-1.16` (row 13985) | Public body | 2nd committed representative loss (`has the same meaning`) | **Yes** — `pure_added` |
| `USC_T12_C13_S1715r` (row 5247) | approved percentage | `has the following meaning` recovery (not used as a committed fixture, due to an unrelated pre-existing digit-paren-run artifact) | **Yes** — `pure_added` |
| `STATE_NJ_T48_C10_S10-3` (row 48126) | Pipeline | Discovered during the §3 collateral-risk sweep (c5guard re-pin) | **Yes** — `pure_added` |

All 4 confirmed present (exact act_id match verified against the pinned
snapshot). **0 of the 4 named rows are missing.**

The log's own §8 adjudication states, of the 118: **~60 have no
distinguishable next-quoted-term at all** in the remaining text (a
different defect family — un-quote-adjacent marker recognition, explicitly
scoped OUT of this item by the director's own ruling: "recovery goes
through idiom vocabulary only") and **~40 are dominated by citation noise**
(quoted Act names before a P.L./Pub.L. citation, not a defining idiom) with
"no further CLEAN, evidence-backed idiom" identified at planning altitude.
By the Planner's own explicit scoping, **neither of these ~100 buckets was
ever expected to be recovered by this widening** — their absence from
`pure_added` (which cannot be checked directly, since their identities were
never persisted) is not evidence of a shortfall against this item's own
goal.

---

## Q3 — the 1,141 re-bounded anchors

Stratified sample of 40 (same seed+1, same jurisdiction-proportional
method as Q2a): FED 7, ME 7, MI 1, ND 1, NJ 5, NY 6, OH 2, OK 2, VA 8, WA 1.

**39/40 are pure prefix truncations** — the NEW definition text is an
exact prefix of the OLD (`old.startswith(new)`) — which is structurally
guaranteed by `close_entries`'s own construction to land on a real
boundary (either an existing hard-stop marker, unaffected by this change,
or a newly-recognized quote+idiom pair): corruption mid-sentence is not
possible through this mechanism. Spot-checks across the largest cuts (FED
`liability` 7729→152 chars, FED `moneys received` 7801→1093 chars, VA
`Servicer` 3802→76 chars, NY `disposition` 11318→2763 chars) confirm the
NEW cutoff lands on a coherent sentence/clause end immediately followed by
a genuine sibling term or marker — every one is **MORE FAITHFUL**: the OLD
capture was swallowing unrelated trailing content (a next sibling's own
"has the same meaning"/"shall include" clause, previously unrecognized)
that NEW correctly excludes.

**1/40 is a genuine FLAGGED HAZARD**, matching gate 3's own named risk
("an idiom INSIDE a definition body wrongly splits it"): `STATE_WA_T13_
C38_S040` (WA row 148), term `active efforts`. Traced against the raw
corpus row: the section defines `"Active efforts"` (capitalized) via
`(1) "Active efforts" means the following: (a) [long paragraph] ... At a
minimum "active efforts" shall include: (i)...(ii)...(iii)...(iv)... (b)
[a different circumstance] "active efforts" means a documented, concerted,
and good faith effort ...`. The lowercase `"active efforts"` text is thus
quoted **twice** in the same section: once inside branch (a)'s own
"shall include" enumeration (a continuation of that branch's body, not a
new top-level term), and once as branch (b)'s own complete, self-contained
alternate definition. Before the widening, only the (b) occurrence
("means") was recognized, so it won the term-key. After the widening, the
(a) occurrence ("shall include") is *also* recognized, and because
`extract_definitions_from_section`'s term-key dedup is first-occurrence-
wins in text order, (a)'s occurrence — which comes first in the text —
now wins instead, and its own `close_entries` boundary runs all the way to
branch (b)'s quote (the next recognized start), swallowing the entire
(i)-(iv) enumeration as `active efforts`'s definition **and displacing
the previously-kept, complete (b) definition entirely**. The new content
is real and on-topic (not garbage), but it represents only one circumstance
of a two-branch definition, where before the fix a different, self-
contained branch was kept — a genuine quality regression, not merely a
re-bounding.

A supplementary full-population check (not part of the 40-sample, run to
gauge how common this specific hazard is) computed, across all 1,141
"both" anchors, whether NEW is a prefix of OLD *or* OLD is a prefix of NEW
in either direction: **1,114/1,141 (97.6%)** are one of these two
monotonic shapes (either a truncation, as above, or — the mirror image,
seen repeatedly in OH's `"X" has the same meaning as in section Y, but/and
also includes Z"` idiom — an *expansion* that recovers a previously-missing
lead-in the old fallback anchored past, e.g. OH row 3982 `health benefit
plan`: OLD = `"both of the following: (1) A public employee..."`, NEW =
`"as in section 3924.01 of the Revised Code and also includes both of the
following: (1) A public employee..."`). The remaining **27/1,141 (2.4%)**
are non-monotonic (term text quoted at multiple distinct points in the
same section). Manual inspection of all 27 found: 3 genuine completions,
2 genuine re-anchors to different-but-real content, **4 more instances of
the same swap-hazard pattern** (FED `compensation` row 2893, NY `related
person` row 103, WA `final action` row 35293, and — the clearest case —
FED `correct` row 42191, where NEW replaced a detailed multi-part
enumeration with a single vague forwarding sentence), and **1 outright
corruption**: NY row 6675, term `General service lamp` — OLD was a real,
substantive lighting-code definition; NEW is `"the following definitions:"`
— a bare list-introducer phrase, not a definition at all, captured because
the widened idiom matched at the wrong quote occurrence.

| # | Jurisdiction | source_row | Term | OLD len | NEW len | Prefix? | Classification |
|---|---|---|---|---|---|---|---|
| 1 | US-FED | 1129 | Foundation | 236 | 114 | yes | MORE FAITHFUL (bounded truncation) |
| 2 | US-FED | 14356 | moneys received | 7801 | 1093 | yes | MORE FAITHFUL (bounded truncation) |
| 3 | US-FED | 6121 | farming business | 444 | 87 | yes | MORE FAITHFUL (bounded truncation) |
| 4 | US-FED | 24591 | associated person of a securities holding company | 834 | 133 | yes | MORE FAITHFUL (bounded truncation) |
| 5 | US-FED | 7306 | card issuer | 239 | 144 | yes | MORE FAITHFUL (bounded truncation) |
| 6 | US-FED | 5014 | liability | 7729 | 152 | yes | MORE FAITHFUL (bounded truncation) |
| 7 | US-FED | 37273 | modification | 740 | 670 | yes | MORE FAITHFUL (bounded truncation) |
| 8 | US-ME | 2293 | waiver | 480 | 379 | yes | MORE FAITHFUL (bounded truncation) |
| 9 | US-ME | 22994 | light-duty motor vehicle | 193 | 77 | yes | MORE FAITHFUL (bounded truncation) |
| 10 | US-ME | 3066 | Likelihood of foreseeable harm | 654 | 500 | yes | MORE FAITHFUL (bounded truncation) |
| 11 | US-ME | 6120 | Notice | 2083 | 1522 | yes | MORE FAITHFUL (bounded truncation) |
| 12 | US-ME | 23500 | administrator | 396 | 145 | yes | MORE FAITHFUL (bounded truncation) |
| 13 | US-ME | 3898 | family | 410 | 259 | yes | MORE FAITHFUL (bounded truncation) |
| 14 | US-ME | 2234 | Working waterfront activity | 510 | 412 | yes | MORE FAITHFUL (bounded truncation) |
| 15 | US-MI | 5961 | State | 1137 | 667 | yes | MORE FAITHFUL (bounded truncation) |
| 16 | US-ND | 22973 | Hospital | 146 | 66 | yes | MORE FAITHFUL (bounded truncation) |
| 17 | US-NJ | 45562 | Impairment or insolvency | 916 | 484 | yes | MORE FAITHFUL (bounded truncation) |
| 18 | US-NJ | 28829 | Contractor | 479 | 295 | yes | MORE FAITHFUL (bounded truncation) |
| 19 | US-NJ | 36203 | Fiduciary | 297 | 226 | yes | MORE FAITHFUL (bounded truncation) |
| 20 | US-NJ | 5346 | Carrier | 1382 | 1212 | yes | MORE FAITHFUL (bounded truncation) |
| 21 | US-NJ | 43973 | Board | 488 | 168 | yes | MORE FAITHFUL (bounded truncation) |
| 22 | US-NY | 26421 | residential building plot | 628 | 317 | yes | MORE FAITHFUL (bounded truncation) |
| 23 | US-NY | 9534 | disposition | 11318 | 2763 | yes | MORE FAITHFUL (bounded truncation) |
| 24 | US-NY | 22871 | administration | 244 | 87 | yes | MORE FAITHFUL (bounded truncation) |
| 25 | US-NY | 3888 | property | 399 | 308 | yes | MORE FAITHFUL (bounded truncation) |
| 26 | US-NY | 17209 | commercial property | 2492 | 1649 | yes | MORE FAITHFUL (bounded truncation) |
| 27 | US-NY | 19603 | Interior furnishing | 488 | 221 | yes | MORE FAITHFUL (bounded truncation) |
| 28 | US-OH | 20648 | Administrative agency | 735 | 299 | yes | MORE FAITHFUL (bounded truncation) |
| 29 | US-OH | 28230 | Critical infrastructure facility | 4043 | 2603 | yes | MORE FAITHFUL (bounded truncation) |
| 30 | US-OK | 4169 | instructional activities | 2290 | 268 | yes | MORE FAITHFUL (bounded truncation) |
| 31 | US-OK | 12042 | Manufactured home dealer | 2635 | 891 | yes | MORE FAITHFUL (bounded truncation) |
| 32 | US-VA | 2511 | Land surveyor | 999 | 708 | yes | MORE FAITHFUL (bounded truncation) |
| 33 | US-VA | 21060 | Exchange | 507 | 429 | yes | MORE FAITHFUL (bounded truncation) |
| 34 | US-VA | 20912 | Affected area | 460 | 288 | yes | MORE FAITHFUL (bounded truncation) |
| 35 | US-VA | 1865 | Health plan | 1267 | 1182 | yes | MORE FAITHFUL (bounded truncation) |
| 36 | US-VA | 20912 | Law-enforcement agency | 347 | 252 | yes | MORE FAITHFUL (bounded truncation) |
| 37 | US-VA | 1658 | Disposition | 178 | 110 | yes | MORE FAITHFUL (bounded truncation) |
| 38 | US-VA | 5317 | Servicer | 3802 | 76 | yes | MORE FAITHFUL (bounded truncation) |
| 39 | US-VA | 31379 | transportation facilities | 1702 | 310 | yes | MORE FAITHFUL (bounded truncation) |
| 40 | US-WA | 148 | active efforts | 200 | 1901 | no | FLAGGED HAZARD (idiom-inside-body dedup swap — see narrative) |

**Counts: 39/40 sample MORE FAITHFUL, 1/40 sample FLAGGED HAZARD.**
Full-population supplementary check: 1,114/1,141 (97.6%) monotonic
(faithful by construction), 27/1,141 (2.4%) non-monotonic, of which ~7
(including the 1 sampled) show the swap hazard and 1 is outright corrupted.

---

## Q4 — reconciling the estimate gap

The Planner's §3 "collateral-risk sweep" measured `extract_quote_anchored_
entries`'s own raw output, diffed current-vs-widened-regex, **against every
row in the 34 files under `backend/tests/fixtures/us_statutes/*.json`** —
a curated set of regression-pin fixtures (dozens of hand-selected rows,
each vendored to pin a *specific*, already-known defect or guard), filtered
down further to the 21 jurisdictions where the function is reachable in
production. That method found 5 changed rows. Gate 2 (this sprint) ran the
**entire real production pipeline** (`capture()`, unconditionally on both
sides — the documented `--current` trap, preserved) against all
2,038,247 real rows across all 53 corpus files, with no B1-winner
population restriction. Two structural gaps separate these numbers, not
merely sample size:

1. **What was diffed.** The Planner's method diffs the boundary engine's
   own function output in isolation. Gate 2 diffs the *persisted records*
   coming out of `USProfile.extract_definitions_from_section`, which
   include the `if not candidates and heading_was_derived: candidates =
   _extract_inline_quoted_definitions(...)` fallback-suppression guard Q1
   identified — a control-flow interaction the fixture-level diff could
   never observe, because it never calls that surrounding function at all.
   Every one of the 134 pure removals (and a meaningful share of the 6,309
   additions, which are frequently the *cause* that flips the guard) is
   invisible to a raw-engine-output diff by construction.
2. **What population was sampled.** 34 hand-picked fixture files, most
   authored specifically to pin *other* already-known defects (digit-run
   membership, exclusion-clause bridging, compound idioms, etc.), are not
   a statistical sample of real statutory drafting frequency. The `"X" has
   the (same|following) meaning as/in/provided in <citation>` forwarding
   idiom this item specifically widens for is one of the single most common
   definitional conventions in OH's Revised Code and comparably common in
   AZ/UT/VA/WA/ME — occurring thousands of times across the real 2-million-
   row corpus, but represented by only a handful of instances (if any) in
   34 curated fixture files. The fixture population structurally cannot
   surface a footprint whose size is driven by corpus-wide idiom
   prevalence rather than by known-defect density.

Net: the Planner's scan correctly validated that the widening does not
regress any *pinned, already-asserted* test behavior (1358/1359 unaffected,
the 1 hit correctly re-pointed) — that is real and valuable evidence for
regression safety. It was never capable of estimating the *production
footprint size*, because it measured a different, narrower question (does
this change any row a human already chose to pin?) than gate 2 measures
(what does this change do across the whole corpus, including its
interaction with a fallback-suppression guard the fixture-level diff
cannot see?). For future planning scans in this program: a fixture-diff
collateral-risk sweep is necessary but not sufficient — it must be paired
with either a full-corpus (or large-random-sample) run of the *actual
persisted-record* diff before a footprint estimate is quoted, specifically
because family-3's own architecture (primary engine + all-or-nothing
fallback) can turn a single newly-recognized match into a much larger,
non-local effect the isolated-function view cannot see.

---

## Implications

**Evidence, not a decision — for the director/program to adjudicate.**

- **Net effect is a large recall win with a small, mostly-benign but
  non-zero precision cost.** 6,309 pure additions sampled at 0% FP (80/80
  genuine); 1,141 re-bounded anchors are 97.6% monotonic improvements by
  construction; 134 pure removals are 97% genuine real content that is now
  completely gone (130/134), with only 4/134 phantom (net-neutral loss) and
  1 flagged/~7 supplementary swap-hazard-class defects found among the
  removals+re-boundings combined (out of 7,584 total anchors, well under
  0.1%). Under D-RECALL-FP's framing (a miss is the expensive defect; a
  small FP rate is tolerated), the footprint reads as a strong net
  recovery — but "small FP rate" in that ruling was calibrated against
  *false positives*, not against a mechanism that silently deletes ~130
  *unrelated, previously-correct* real definitions as collateral damage of
  fixing something else. That is a materially different risk shape than
  the ruling was written for and worth an explicit call on whether it
  still applies.
- **The removal mechanism is fixable independently of the idiom widening
  itself.** The fallback-suppression guard (`if not candidates and
  heading_was_derived: candidates = _extract_inline_quoted_definitions(...)`,
  `us_profile.py:2551`) is the root cause of all 134 removals, not the
  widened regex per se — the widening only *triggers* the guard more often
  by making the primary engine non-empty on more rows. A structural fix
  (e.g., unioning the fallback's OWN candidates that don't term-collide
  with the primary engine's, instead of skipping the fallback outright
  once `candidates` is non-empty) would recover the 130 genuine losses
  *without* narrowing this item's own idiom widening at all. This is a
  separate, well-scoped follow-up, not a reason to revert this item.
- **Can the widening be narrowed to "bounding-only" (closing existing
  entries without opening new `starts`)?** Based on this session's reading
  of `us_markers_boundary.py`: **no, not without a structural change** to
  `extract_quote_anchored_entries`. `_TIGHT_IDIOM_RE` is consumed in
  exactly one place — the main `starts`-building loop (`idiom_re.match(text,
  m.end(), limit)`) — which is what both recognizes a term as its own new
  entry AND supplies the `next_start` boundary that closes the *previous*
  entry (`close_entries`'s `next_start = starts[idx+1][0]`). Bounding and
  opening are the same regex match; there is no second, narrower gate that
  could recognize "this is a real end-of-entry marker" without also
  recognizing "this is a new entry's own idiom." Splitting that would
  require either a second regex family (idioms that ONLY close, never
  open — awkward, since the whole reason `_TIGHT_IDIOM_RE` finds a
  boundary at all is that it recognizes a *quote followed by an idiom*,
  i.e., a candidate entry) or accepting the new `starts` entries but
  suppressing their own emission as top-level terms while still using them
  as closing boundaries for their predecessor — a real, buildable change,
  but a new engine capability, not a narrowing of the existing one.
- **Targeted follow-up over broad narrowing.** Given the small,
  characterizable defect surface (fallback-suppression: 134 anchors, one
  fixable guard; swap-hazard: ~7 anchors, one dedup-ordering interaction;
  phantom terms: 4 anchors, pre-existing fallback quote-mispairing
  unrelated to this widening), a targeted fix to the fallback-suppression
  guard is more proportionate than re-scoping the idiom vocabulary itself,
  which independent sampling shows is overwhelmingly correct (Q2, 0% FP)
  and overwhelmingly improves existing captures where it collides with
  them (Q3, 97.6% monotonic improvement).
- **Certifiable as-is under a sampling policy?** The footprint is large
  (7,584 anchors) but *characterized*, not merely counted: every class in
  it has now been sampled and traced to a specific, named mechanism, with
  no unexplained residue. Whether 7,584 anchors clears a sampling-based
  certification bar, and whether the 130 genuine-but-collateral losses are
  acceptable to certify without the fallback-suppression fix landing
  first, is a program-level tradeoff this investigation surfaces but does
  not resolve.

---

Committed alongside this file: none (documentation-only change; the
analysis scripts and intermediate JSON that produced these tables were
run from this session's scratchpad and are not part of the repo).
