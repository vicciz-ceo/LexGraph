# Item 4 (issue #31 debt class 4, FX7 remainder) — per-row ledger

**Status: COMPLETE.** 101 ceiling-tripped candidates found and
individually adjudicated. All 101 are UNRECOVERABLE within this
sprint's own bounds, each with a common, structural, stated reason
(below) — a legitimate outcome per gate 4 ("recovered ... or
individually adjudicated unrecoverable with a stated reason").

## Methodology (P-R11: no hand-authored expected-change ledger)

Research (`Explore` agent pass, this sprint) confirmed the prior
sprint's own "118 live-verified ceiling-tripped losses" was never
persisted anywhere in the committed repo — its source artifacts were a
deliberately-uncommitted throwaway probe (`docs/sprint/sprints/
2026-08-20-defs-boundary-idioms-log.md`, §1: "one throwaway pytest
probe, deleted before any commit"). No act_id-level list exists to
read. This ledger LIVE-RE-DERIVED the population on this worktree's
current code (all 4 Item-1 fixes + Item 2 landed), using the prior
sprint's own documented two-stage methodology exactly:

1. For every row in the 14 jurisdictions `us_markers_inline_quote.py`
   registers for the shared `us_markers_boundary.extract_quote_
   anchored_entries` engine (VA, FED, UT, TX, SC, AZ, NJ, MI, ND, NY,
   OK, NM, NV, WA) that is a recognized-or-derived Definitions section:
   computed candidates twice — once with the REAL `MAX_CLEAN_DEFINITION_
   LENGTH` ceiling (3000), once with it monkeypatched to `10**9`
   (effectively unbounded).
2. A term present in the unbounded run but absent from the real run is
   ceiling-tripped TODAY, on this worktree's current code — the genuine
   Item-4-relevant population: whatever the ceiling still drops even
   after this sprint's own bleed-trim and adjacency fixes.
3. Each ceiling-tripped candidate was checked against the REAL, current
   (ceiling-respecting) `profile.extract_definitions_from_section` --
   is the term captured by SOME other path today? If yes: RECOVERED. If
   no: UNRECOVERABLE, with a stated reason.

Scripts: `measure_item4_fx7_remainder_census.py` (census, chunked per
jurisdiction, resumable) + `adjudicate_item4_ledger.py` (per-row
verdict). Raw output: `item4_census_run/` (101 records) and
`item4_ledger.jsonl` (101 verdicts).

## Result: 101 found, 0 recovered, 101 individually adjudicated unrecoverable

| Jurisdiction | Definitions rows scanned | Ceiling-tripped count |
|---|---|---|
| US-VA | 3,071 | 0 |
| US-FED | 8,592 | 12 |
| US-UT | 4,225 | 1 |
| US-TX | 8,963 | 3 |
| US-SC | 2,054 | 12 |
| US-AZ | 3,511 | 4 |
| US-NJ | 4,503 | 45 |
| US-MI | 5,582 | 19 |
| US-ND | 1,943 | 0 |
| US-NY | 3,989 | 1 |
| US-OK | 2,841 | 2 |
| US-NM | 3,519 | 1 |
| US-NV | 13,098 | 0 |
| US-WA | 4,217 | 1 |
| **Total** | **70,107** | **101** |

101 closely matches the prior sprint's own cited "~100 remainder rows"
figure — a reassuring, independent confirmation that this live
re-derivation reproduces the same population the prior sprint
identified by a different (now-lost) method, without ever having their
actual list to check against.

## Why all 101 are structurally unrecoverable within this sprint's own scope

Every one of the 101 is a candidate reached via a registered
`EntrySplitterRule` built on `us_markers_boundary.extract_quote_
anchored_entries` → `close_entries` — the SAME shared primary engine
the FX7 ceiling (`MAX_CLEAN_DEFINITION_LENGTH`) itself lives inside.
`close_entries`'s own ceiling fires ONLY when `bounded` is `False` --
no hard-stop marker found AND no next quoted+idiom term found anywhere
later in the text (see that function's own module docstring: "the
ceiling therefore applies ONLY to candidates with NO real closing
boundary found"). Spot-checked several unbounded tails directly (e.g.
AZ `STATE_AZ_T32_C19.1_A4_S2091` "sexual intercourse" bleeds thousands
of characters into a wholly unrelated `"(dd)"`/`"(ee)"`-lettered
professional-ethics-violations list with no boundary found before the
ceiling trips) — these are genuinely, structurally unbounded within
`close_entries`'s own boundary-finding, not merely badly-bounded.

Gate 8 and this sprint's own Known Traps are explicit and
unambiguous: **Item 1 must NOT touch `close_entries`'s own `bounded`/
`MAX_CLEAN_DEFINITION_LENGTH` ceiling calculation** ("that IS the FX7
ceiling ... already proven unsafe to widen" in a prior sprint). Item
1's own trim mechanism (`_trim_fallback_candidate_bleed` and friends)
is therefore, BY DESIGN, never applied to `EntrySplitterRule`-sourced
candidates at all (confirmed: it is scoped to baseline-block-sourced
candidates and newly-fallback-admitted candidates only — see Item 1's
own commit history and code comments). Since every one of these 101
candidates is `EntrySplitterRule`-sourced, and their own ceiling-drop
reason (`bounded=False`, no boundary found at all) is exactly the
FX7-protected mechanism, NONE of them can be "recovered" by anything
this sprint is permitted to ship. This was verified empirically, not
merely reasoned: `adjudicate_item4_ledger.py` ran all 101 against the
real, current `extract_definitions_from_section` and found 0 recovered.

**Stated reason (common to all 101, individually confirmed per row in
`item4_ledger.jsonl`):** term absent from the current, real (ceiling-
respecting) `extract_definitions_from_section` output; the census's
own unbounded-ceiling probe is the only path that finds it, and that
probe monkeypatches the FX7-protected `MAX_CLEAN_DEFINITION_LENGTH`
constant, which this sprint's own gates forbid touching in production.

## Family classification (secondary; not fully resolved)

The two named families from the prior sprint's own evidence (~60
no-next-quoted-term, ~40 citation-noise) describe *why the primary
engine's own boundary-finding, independent of the ceiling, never finds
a stop* — a finer-grained characterization than gate 4's own hard
requirement ("recovered or individually adjudicated unrecoverable with
a stated reason", satisfied above for all 101). An automated per-row
family classifier was attempted (`adjudicate_item4_ledger.py`'s
`classify_family`) but its own bounded-lookahead heuristic did not
cleanly separate the two shapes on this population within the time
this pass had available — every row landed in a shared "other" bucket
rather than a reliable no-next-quoted-term/citation-noise split. Given
the CORE gate-4 requirement (recovered-or-adjudicated, stated reason)
is fully satisfied and independently verified for all 101 rows, this
finer classification is left as a known gap rather than a blocking
one; a QA/Planner pass wanting the family breakdown can re-run
`item4_ledger.jsonl`'s own `unbounded_definition_text_tail` field
(already captured per row) through a more careful classifier without
re-deriving the population itself.

## Cross-check against Item 5

Every one of the 101 rows must show NO change for its own anchor in
Item 5's own certified all-53 delta (still absent on both baseline and
current) — since none are recovered, none should appear as an anchor
ADDITION or TEXT CHANGE in that delta. Checked as part of Item 5's own
100%-anchor-granularity adjudication.

## Named finding (already recorded in Item 1's own commit/contract)

`USC_T5_C75_S7511` "furlough" — one of the prior sprint's own two
individually-named examples (the OTHER being `STATE_NJ_T27_C1A_S1A-
3.1` "Department", which was already RECOVERED by that same sprint's
own idiom widening, not a remainder row) — is CONFIRMED, live, no
longer part of the FX7 remainder on this worktree's HEAD: the already-
landed idiom widening incidentally gave it a downstream boundary via a
different, newly-recognized entry, converting it from "total ceiling
drop" into an ordinary next-entry bleed, which this sprint's own Item 1
then trimmed to its correct 144-char definition. It is used as a real
Item-1 exemplar (`test_us_markers_defs_debt_31_bleed_trim_real_rows_
red.py`), not re-counted here — consistent with it NOT appearing
anywhere in this census's own 101-row FED list.
