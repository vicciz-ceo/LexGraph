# Sprint log — 2026-08-04-defs-us-headings (append-only)

Recreated 2026-08-12 for a contract-hygiene pass (unblocking PR #20's
`sprint contract lint` CI check, which lints every contract in
`docs/sprint/sprints/`, not just the active one). The original panel log
for this sprint was intentionally dropped from the shipped tree at
`9c7d6ea` ("sprint: drop per-sprint process logs from the shipped tree" —
full panel dialogue remains readable in git history on this branch). This
file is NOT a recreation of that narration; it holds only the specific
contract sections moved out of `2026-08-04-defs-us-headings.md` in this
pass to bring the contract under the lint's 400-line budget, verbatim and
labeled by origin section, per the "move, never delete" rule.

## Archived from contract (2026-08-12)

Moved verbatim from the sprint contract (`2026-08-04-defs-us-headings.md`)
during a contract-hygiene pass to bring the contract under the 400-line
lint budget. Nothing summarized or dropped — each section below is the
exact prior contract text, moved because CI's `sprint contract lint`
lints every contract with frontmatter, not just the active one. The
contract now carries a short summary + pointer to each section here.

### Dev Complete narrative (the free-standing text between Item 2 and Item 4)

Full suite: **669 passed, 2 failed** (baseline 641 → +28 green, zero
regressions). The 2 failures are the core-blocked pair, item 3's dependency.

**Manager's independent full-corpus verification** (not the fixture suite —
`scratchpad/manager_verify_u4_u6.py`, all 2,014,611 rows, 52 files):
newly recognized **20,307 / 22,228 miss pool = 91.4%**, reproducing the
Planner's figure exactly on independently written code. WA 74.3%→96.5%,
FL 84.6%→98.5%, NY 91.4%→98.6% (U6's named states). Precision: **zero**
false positives — 0 rows matched without a `defin` substring, and the 123
non-canonical-token matches are exactly 117 R-TRUNC + 6 R-MISSPELL intended
captures with 0 morphology noise and 0 unexplained. Details in `-log.md`.

### Dev Complete, Item 1

- **Item 1 — `rules/us_heading_variants.py`** (dev `c986001`). Six rules
  (R-SEC, R-MID, R-VERB-bare, R-VERB-extended, R-TRUNC, R-MISSPELL), 269
  lines, pure function, no `__init__.py`, no registration call (ruling
  H-R5). CHECK PASSED: unit suite **19 passed**; `git diff --stat -- backend/app/`
  = exactly one new file (U3); `-- backend/tests/` = empty (role separation).

### Dev Complete, Item 2

- **Item 2 — composed deterministic-engine end-to-end** (no extra code).
  CHECK PASSED: `TestComposedDeterministicEngine` **8 passed**, incl. the 4
  positive yields (CT 82, MO 6, WI 27, CT-misspelled 3), the term-use
  link-back proof, and the 3 zero-yield hand-offs pinned as documented
  markers-family routing (H-R1).

### Dev Complete, Item 4

- **Item 4 — `HeadingRule` self-registration** (dev `f461371`, phase-2 manager).
  The `register_heading_rule(HeadingRule(("US-*",), matches_heading_variant))`
  call H-R5 deferred out of Phase A, added now that core is merged. CHECKS
  PASSED: registry-integration unit suite **2/2**; auto-discovery live check
  registers exactly **1** rule for `US-CT` and **0** for `IL`; full suite
  **729 passed / 1 failed**; `git diff --stat -- backend/tests/` empty.
  Manager proved all executable code byte-identical to the prior commit apart
  from the import + registration line. File 304 lines (soft-300 convention
  overage, entirely preserved rationale — recorded, not cut).

### Context Dump (phase-2 "parked" narrative, superseded 2026-08-12)

**Parked cleanly, waiting on core's dispatch sprint (ruling P-R8).**

What the phase-2 manager did: verified the inherited state, merged core into
this branch (`1d17d81`, merge not rebase — accepted deviation, see log), landed
Phase B item 4 (`f461371`), escalated both seam gaps, and got them ruled.

**Suite state: 728 passed / 13 failed — all 13 red by design.** 12 are the
Planner's pre-authored D-DF REDs (11 `ImportError` on symbols the Developer
has not written yet, 1 registration-count assertion); the 13th is
`test_us_heading_variants_end_to_end.py::TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline`,
the core dispatch gap. **Zero unexplained failures.** Accounting from the
pre-Planner 729/1: 729−1 passed (the amended registration test flipped RED
deliberately), 1+11+1 = 13 failed.

**Resume point (when the program manager wakes this panel):**

1. Re-run the suite. The CT pipeline test should go green with **no change from
   this panel** once core wires heading-rule consumption — if it does not, that
   is the first thing to diagnose.
2. **Developer implements D-DF against the Planner's already-committed RED**
   (`7f6964d`), which locks the design precisely: register **TWO**
   `HeadingRule`s — unconditional FIRST
   (`matches_heading_variant_unconditional` = today's union minus the `for`
   alternation, `body_confirms=None`), then the narrow gated one
   (`matches_defined_for_heading`, `body_confirms=defines_in_body`). Three new
   symbols required. `matches_heading_variant` **keeps its exact current
   meaning** (27 tests depend on it; an equivalence test pins the
   decomposition). **The trap:** attaching `body_confirms` to the existing
   single union rule would body-gate all ~20,307 recognized headings instead
   of the 110 `defined for` rows. Order and rule-2 narrowness are load-bearing,
   not stylistic — see the D-DF test module docstring.
3. QA cycle 3 (`qa_cycles` is 2 of 5): U1 live-path leg, U6 re-measurement,
   U4 + the P-R7 cross-reference against the preamble panel's consolidated
   body-driven inventory (request the pointer through the program manager —
   do NOT re-scan the corpus). Our 22,228-row miss pool is `defin`-substring-
   derived and so cannot certify U4 alone. **Additionally:** re-confirm the
   `body_confirms` dispatch semantics against core's ACTUAL implementation —
   the design is proven safe under both plausible readings of
   "first-positive-wins", but which one core shipped is unobservable until
   then. Consider renaming
   `test_module_self_registers_exactly_one_heading_rule_for_us_star`, whose
   name is now stale (it asserts two registrations; kept deliberately for
   git-blame traceability).

**Corrections to earlier context, both recorded at program level:** the
"defined for" rule is COMMITTED (`a0419a4`), so D-DF *changes shipped
behavior*; and QA cycle 2's "sixth gap" was already closed in dev cycle 3.

**Standing items, unchanged:** the U2 10-row known limitation (recheck against
seam v2 now that core is reopening); the 245-row D-HG guarded cluster handed
off in `-guarded-cluster.md`; the ~19 UNCLEAR Connecticut rows and
`STATE_CT_T38a_C704_S38a-818` ("not so defined" defeats the negation guard via
an intervening "so") on the program data-quality list.

### H-R5 (Phase A item 1's original correction essay)

**Manager correction (ruling H-R5) — item 1 as originally written was
internally inconsistent** ("write the registration call, accept
`ModuleNotFoundError`" cannot coexist with "unit tests fully green": a
module-level import error fails all 19). Corrected shape, verified live
by the manager:
- The `rules/` package does **not exist on this branch or on
  `origin/claude/defs-core-scope`** — core has not written it yet.
  `rules/__init__.py` and `rules/registry.py` are **core-authored and
  stable forever** per the seam; **the Developer must NOT create
  either** (doing so guarantees a rebase collision and forks the
  auto-discovery implementation).
- Manager verified empirically that **PEP 420 namespace packages work
  here**: a `rules/` directory containing only our module, with NO
  `__init__.py`, imports fine as
  `app.definition_links.rules.us_heading_variants`.
- **Phase A therefore ships the PURE FUNCTION ONLY**: create
  `rules/us_heading_variants.py` containing `matches_heading_variant`
  and its own normalization helpers, with **no `__init__.py` and no
  `register_heading_rule` import/call**. All 19 unit tests go green
  now, with zero core dependency.
- The `register_heading_rule(...)` call is added in **Phase B, item 3**
  (post-rebase), when `rules/registry.py` actually exists.

### item 9 (original escalation text, before condensing to "[RESOLVED]")

9. **[RESOLVED — see the ruling above] U2 scope-seam gap for scope-unit-naming headings** (e.g. AK's real
   `"General definitions for AS 13.06 — AS 13.36."`, `STATE_AK_T13_C13.06_S13.06.050`
   — a genuine family-4 R-MID capture). The published core seam's
   `determine_scope` returns only `"chapter" | "law-wide"` for the
   Definitions-SECTION path; it has no slot for a named multi-chapter
   range, and no registered-rule kind exists to teach it one (`ScopeTriggerRule`
   is the ORDINARY-ARTICLE path, a different code path). Recognizing this
   heading (item 1) is correct and safe on its own; claiming its scope is
   CORRECTLY enforced is not yet true. Full analysis, options, and the
   Planner's lean are in the panel log — routed to the manager for
   forwarding to the program manager per the brief's instruction (report,
   do not unilaterally decide). Not gated on Phase A/B; can resolve on its
   own timeline. If unresolved by ship time, ship item 1 anyway (heading
   recognition, U1) with this gap explicitly flagged as a known limitation
   in the Completed entry, not silently papered over with a guessed scope
   value.

### U2 Option C ruling (original narrative, before condensing)

**Program manager ruling, 2026-08-04: Option C accepted.** Ship the verified
recall win; record the 10 enumerated rows as a NAMED KNOWN LIMITATION; the
scope-model gap is routed to the core panel. **Seam v2 will carry a generic
`(unit_kind, unit_value)` scope mechanism**, which may make these 10
expressible — **recheck once core pushes seam v2; if expressible, capturing
their true scope becomes a normal sprint item, not a limitation.**

These headings are correctly RECOGNIZED (U1); their declared scope is not
expressible in the seam's current 2-value model (`chapter`/`law-wide`), so
they take whatever `determine_scope` computes — recorded here rather than
passed off as correct. Not new exposure: the same shapes occur in headings
the baseline already recognized before this sprint. (The 10-row act_id list
itself is unchanged in the contract, not moved here.)

### Panel protocol (full text, before condensing)

## Panel protocol — role-agent reporting (director-ordered, 2026-08-05)

**BINDING ON EVERY SPAWN AND EVERY RESUME. Survives manager handoff — a
successor manager MUST keep applying this.**

Role agents now interact DIRECTLY with the panel manager, not via the program
manager. The program manager no longer relays agent reports. This panel
manager's agentId is **`a1d2487867915919a`**.

Every role-agent brief (new spawn OR resume) must include this text verbatim:

> Before you finish or escalate, deliver your full report via SendMessage with
> to: 'a1d2487867915919a' (raw agent id, exactly as written). Your plain-text
> final return is NOT a reliable delivery channel — the SendMessage IS your
> report. If the send fails, say so in your final text.

Escalations (`ESCALATION:` as the first line) arrive by the same channel; the
panel manager resolves them or escalates onward to the program manager itself.
Peer-manager coordination by agentId continues as before.

**Why this is load-bearing here:** this panel already lost an agent's report
once — the `includes` FP scout died after completing its scan and sampling, and
its measurement only reached the panel second-hand. A report that is not
delivered is a report that did not happen.

### BLOCKED section (full text, before condensing)

## BLOCKED — two core-owned seam gaps (RESOLVED by ruling P-R8; awaiting core)

**Both blockers are ruled, not open questions.** Program ruling **P-R8**
(main `0f4e8fc`): core reopens for a dispatch-completion sprint covering all
five dead rule kinds, the ungated `derive_heading_from_body` (this panel's
D-PREAMBLE-ALL non-implementation finding = core's scope item 2), and **this
panel's `body_confirms` design accepted as-is** (core's scope item 4, credited
to this panel). The PR panel independently found the same dead dispatch.

**This sprint stays `blocked` until core's dispatch merges — the program
manager wakes this panel.** Phase B items 3, 5, 6, dev cycle 4 (D-DF), and
gates U1 (live-path leg) / U2 / U4 / U6 remain gated on that merge. Full
evidence in `-log.md` § "Manager phase 2 — takeover verification".

- **Blocker A — `HeadingRule` is registered but never consumed.** 5 of the 7
  rule kinds (heading, body_preamble, entry_splitter, term_clause,
  structural_unit) have **zero production callers** on merged main; only
  `ScopeTriggerRule` and `CitationRule` are wired. Proven live-path: an
  everything-matching `HeadingRule` is returned by `heading_rules_for("US-CT")`
  yet `profile.is_definitions_heading` still returns False. This sprint's
  entire measured recall win (20,307 headings, 91.4%→94.7%) therefore has
  **zero production effect** today. Gates **U1** (live-path recognition) and
  **U3** (zero shared-module edits) cannot both be met by this panel: the fix
  is an edit to core-owned `us_profile.py`. Also blocks the markers, multiterm,
  and preamble panels.
- **Blocker B — D-DF is not expressible in any rule kind.** `HeadingRule.matches`
  receives the heading only; no kind in the seam receives **both** heading and
  body, which is exactly what D-DF's body-confirmed capture requires. Note the
  body (`matcher_article.body`) is already in scope at the detection call site
  (`pipeline.py:198`), so this needs no new plumbing — only a seam decision.
