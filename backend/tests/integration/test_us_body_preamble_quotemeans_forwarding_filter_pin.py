"""Planner cycle-8 (sprint 2026-08-04-defs-us-preamble, D2, manager ruling
M-R60): pin the forwarding-phrase filter on the WIDENED quote-means branch
(`_b1_quote_means_branch`'s `not any(phrase in gap for phrase in
_B1_FORWARDING_PHRASES)` check).

QA's cycle-7 D4 mutation-tested this exact line (`return not any(...)` ->
`return True`) and found **zero test regressions** across the full suite
(still 3 failed / 840 passed) -- a filter that demonstrably works on the
real corpus (QA's own D1 hand-judging: 0/50 FP on shapes 2 and 6, the two
shapes this filter protects) was pinned by NOTHING. M-R60: "A pin is
required in the next Planner cycle."

**Why this is a UNIT-level test, not a live-path fixture test (disclosed,
not a shortcut).** This Planner searched the FULL real corpus (all 53
US-* parquet files, 2,038,247 rows, script `planner_c8_find_
quotemeans_forwarding_gap.py` in the sprint scratchpad) for ANY real row
where `_B1_QUOTE_MEANS_RE` matches AND its own `gap` group (the optional
short qualifier clause between the trigger and the quoted term) contains
one of `_B1_FORWARDING_PHRASES`. Result: **zero real rows** -- this exact
code path is currently UNREACHABLE by any row in the corpus. That is
consistent with QA's own mutation finding (no existing test exercises it
either) and explains WHY the mutation caused zero regressions: the
diagnosed hazard the filter was built for (D3, last cycle -- forwarding
phrases such as `"has the meaning set forth in"`/`"has the same meaning
as"`) turned out, on the real FP rows that motivated it, to appear as the
DEFINING VERB itself (which `_B1_QUOTE_MEANS_RE`'s own `means|shall mean`
verb alternation already excludes structurally, independent of this
filter) rather than as qualifier-clause TEXT before the quote. Because no
real row can prove this specific line matters, this test calls
`_b1_quote_means_branch` directly with a hand-constructed string -- a
normal, legitimate unit test of the function's own logic (the same
pattern this file's sibling tests already use for rule-identity checks),
not a "row" requiring fixture-vendoring. No test in this file reads the
parquet snapshot; the corpus-wide zero-hit search that established the
above is a measurement script only.

**Mutation verified by this Planner directly** (not merely asserted):
`_b1_quote_means_branch`'s `return not any(...)` was temporarily changed
to `return True` in this worktree, this test was re-run and FAILED as
expected, and the file was restored before committing (`git status`
verified clean of `backend/app/` before every commit in this cycle) --
see this cycle's `-log.md` entry for the exact command transcript.
"""

from __future__ import annotations


def test_quote_means_branch_rejects_a_gap_containing_a_forwarding_phrase():
    """Direct unit test of `_b1_quote_means_branch`. The `after` text
    below is a hand-constructed string (verified live to actually match
    `_B1_QUOTE_MEANS_RE`: gap=', has the same meaning as elsewhere, ',
    term='foo') whose gap contains `"has the same meaning as"`, one of
    `_B1_FORWARDING_PHRASES`. Today (filter present) this must return
    False -- a quoted term immediately preceded by forwarding-phrase-
    bearing qualifier text is a forwarding pointer dressed up as a
    quote-means shape, not a genuine local definition, mirroring the
    SAME discipline `_b1_colon_list_branch`'s own filler-text filter
    already applies (this filter is the widened branch's sibling check,
    per M-R50's own "reuse an existing, already-proven-safe check"
    principle)."""
    from app.definition_links.rules.us_body_preamble import (
        _B1_QUOTE_MEANS_RE,
        _b1_quote_means_branch,
    )

    after = ', has the same meaning as elsewhere, "foo" means bar and baz.'

    # Confirm the fixture text actually exercises the code path this test
    # claims to pin -- if this assertion ever fails, the constructed
    # string no longer matches `_B1_QUOTE_MEANS_RE` at all and the test
    # below would pass VACUOUSLY (returning False for the wrong reason).
    match = _B1_QUOTE_MEANS_RE.match(after)
    assert match is not None, (
        "fixture string must match _B1_QUOTE_MEANS_RE for this test to "
        "exercise the forwarding-phrase filter at all"
    )
    assert "has the same meaning as" in match.group("gap").lower(), (
        "fixture string's own matched 'gap' group must contain a "
        "_B1_FORWARDING_PHRASES entry -- this is what the filter checks"
    )

    assert _b1_quote_means_branch(after) is False, (
        "_b1_quote_means_branch must reject a quote-means match whose own "
        "gap text contains a forwarding phrase (here: 'has the same "
        "meaning as') -- if this fails, the forwarding-phrase filter on "
        "the widened quote-means branch (M-R50/M-R60) has been weakened "
        "or removed"
    )


def test_quote_means_branch_still_accepts_the_same_shape_without_a_forwarding_phrase():
    """Companion GREEN control: the SAME structural shape (comma +
    qualifier clause + quoted term + means) with an ORDINARY qualifier
    (no forwarding phrase) must still be accepted -- proves the filter
    discriminates on the forwarding-phrase vocabulary specifically, not
    on the mere presence of a qualifier clause (which is shape 6's own
    legitimate, already-tested widening)."""
    from app.definition_links.rules.us_body_preamble import _b1_quote_means_branch

    after = ', unless the context otherwise requires, "foo" means bar and baz.'
    assert _b1_quote_means_branch(after) is True, (
        "an ordinary qualifier clause with no forwarding phrase must still "
        "be accepted by the quote-means branch (shape 6's own real "
        "TN-shaped convention) -- if this fails, the filter has become "
        "over-broad, not just under-tested"
    )
