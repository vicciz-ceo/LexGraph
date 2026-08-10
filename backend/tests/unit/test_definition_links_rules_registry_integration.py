"""RED registry-integration test (sprint 2026-08-04-defs-us-headings, gate
U3 "rules ship as registry modules; zero shared-module edits" and gate U5
"nothing regresses").

Two things this file proves, independently:

1. **Self-registration** (U3): importing
   `app.definition_links.rules.us_heading_variants` calls the PUBLISHED
   registry function `register_heading_rule` exactly THREE TIMES (amended
   2026-08-04, cycle 5, item 13 -- see below; previously exactly two,
   D-DF's unconditional/gated pair; before that exactly once,
   `matches is module.matches_heading_variant`, before `body_confirms`
   existed) -- with an UNCONDITIONAL
   `HeadingRule(jurisdiction_codes=("US-*",),
   matches=matches_heading_variant_unconditional)` registered FIRST, D-DF's
   GATED `HeadingRule(jurisdiction_codes=("US-*",),
   matches=matches_defined_for_heading, body_confirms=defines_in_body)`
   registered SECOND, and cycle 5 item 13's GATED `HeadingRule(
   jurisdiction_codes=("US-*",), matches=matches_defined_qualifier_heading,
   body_confirms=defines_qualifier_in_body)` registered THIRD -- same
   design reasoning as D-DF (a real, evidenced precision risk on the VA
   row means this shape cannot ship unconditional either; see
   `test_definition_links_us_heading_variants_cycle5.py`'s module
   docstring, "Item 13" section, for the full rationale). This is tested
   by patching `register_heading_rule` itself (the only part of the
   registry's surface the seam spec actually publishes/fixes -- see
   `## Seam spec (published)`, "Seam 2" -> "Registration") and observing
   all three calls, rather than guessing at an unpublished internal
   storage accessor (`registry.py`'s read-side API is core's own internal
   detail, not part of the documented family-panel surface). Items 10, 11,
   12, and 15 do NOT add a new registration (10/11/15 widen the existing
   unconditional rule's own regex; 12 folds into the existing
   unconditional union too, per that item's own "UNCONDITIONAL" design
   choice) -- only item 13 changes this test's shape.

   **Why two rules, and why this order** -- full design rationale (D-DF
   cannot be a single-rule change without gating all ~20,307 recognized
   headings on body content; the ordering is what makes the design safe
   under either plausible reading of "first-positive-wins" dispatch) is in
   `test_definition_links_us_heading_variants_d_df.py`'s module docstring
   -- this file only pins the REGISTRATION SHAPE, not the rule bodies'
   behavior (that belongs to the D-DF-specific test file, which owns the
   fixture rows).

2. **Baseline-first, registry-second consumption is safe** (U5): this
   test hand-composes the documented consumption contract ("the profile's
   EXISTING baseline logic runs first ... only if baseline returns False
   does the profile try registered rules") using TODAY's real
   `us_profile.is_definitions_heading` plus our new rule's `matches`
   callable, and proves the combination (a) still returns True for every
   baseline-True heading (first branch fires, second branch never
   reached), (b) returns True for our new family-4 headings, (c) returns
   False for the negative guards. This is NOT a test of the real
   `profiles.py` wiring (that is core's own C4 work, landing in
   `claude/defs-core-scope`) -- it is a test that OUR module's `matches`
   callable is safe to plug into that contract once core lands. The real
   wiring gets its own proof after core merges (see the sprint contract's
   Next Steps).

RED signal (test 1, `test_module_self_registers_exactly_one_heading_rule_for_us_star`,
original core-blocked history): `ModuleNotFoundError: No module named
'app.definition_links.rules'` -- same as the unit test file, for the same
reason (core sprint had not merged into this worktree yet). Both this
test's dependencies -- `app.definition_links.rules.registry`
(core-authored) AND `app.definition_links.rules.us_heading_variants`
(Developer-authored, this sprint) -- were missing at that point; that test
was doubly blocked until both landed. Core has since merged (`1d17d81`) and
the original single-registration shape shipped and went green.

RED signal (2026-08-04 amendment, D-DF): the SAME test asserted the
two-registration shape; that landed and went green (dev cycle 4).

RED signal (2026-08-04 amendment, cycle 5, item 13): the SAME test now
asserts the NEW three-registration shape -- it fails today with
`AssertionError: mock_register.call_count == 3` (actual: 2), a genuine
"feature absent" failure, not an import error -- the module's registration
site has not yet grown a third call. Stays red until the Developer adds
item 13's `matches_defined_qualifier_heading`/`defines_qualifier_in_body`
functions AND their registration call.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_heading_variants_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_module_self_registers_exactly_one_heading_rule_for_us_star():
    """Amended 2026-08-04, cycle 5, item 13 -- see this file's module
    docstring item 1 and `test_definition_links_us_heading_variants_
    cycle5.py`'s module docstring ("Item 13") for the full design
    rationale. Name kept (not renamed) so the git blame/history on this
    exact assertion stays traceable across BOTH amendments (D-DF's
    one-to-two, and this one's two-to-three) -- the CONTRACT it pins has
    changed from one registration, to two (D-DF), to three (item 13).

    D-DF shape (dev cycle 4, shipped): `assert mock_register.call_count ==
    2`. That count is now stale -- item 13's `defined (qualifier)`/
    `defined to [verb]` shape carries a real, evidenced precision risk
    (the VA "Evidence of habit or routine practice; defined..." row) of
    exactly the same kind D-DF's `defined for` alternation did, so it
    ships as a THIRD gated rule, not folded into the existing unconditional
    union."""
    from app.definition_links.rules import registry

    with patch.object(registry, "register_heading_rule") as mock_register:
        # Force a fresh import so the module-level registration calls at
        # the bottom of us_heading_variants.py actually run during this
        # patch's lifetime, regardless of any earlier import in this test
        # session (pytest may import test modules in any order, and the
        # rules package's own __init__.py auto-discovery may have already
        # imported this module once before this test runs).
        sys.modules.pop("app.definition_links.rules.us_heading_variants", None)
        module = importlib.import_module("app.definition_links.rules.us_heading_variants")

    assert mock_register.call_count == 3, (
        "us_heading_variants.py must call register_heading_rule exactly THREE "
        "TIMES at import time (module-level, not inside a function): an "
        "UNCONDITIONAL rule first, D-DF's GATED 'defined for' rule second, and "
        "cycle-5 item 13's GATED 'defined (qualifier)'/'defined to [verb]' rule "
        "third -- see module docstring item 1"
    )

    (unconditional_rule,), _ = mock_register.call_args_list[0]
    assert unconditional_rule.jurisdiction_codes == ("US-*",)
    assert unconditional_rule.matches is module.matches_heading_variant_unconditional, (
        "the FIRST registered rule must be the unconditional one -- registering a "
        "gated rule first is unsafe under a 'stop at first matching rule' dispatch "
        "reading (see the D-DF test file's docstring)"
    )
    assert getattr(unconditional_rule, "body_confirms", None) is None, (
        "the unconditional rule must NOT be body-gated -- every shape except "
        "'defined for'/item 13's qualifier shape stays unconditional"
    )

    (gated_rule,), _ = mock_register.call_args_list[1]
    assert gated_rule.jurisdiction_codes == ("US-*",)
    assert gated_rule.matches is module.matches_defined_for_heading, (
        "the SECOND registered rule's matches must be the NARROW 'defined for'-only "
        "predicate, not the full matches_heading_variant union -- see the D-DF test "
        "file's docstring for why narrowness matters for dispatch safety"
    )
    assert gated_rule.body_confirms is module.defines_in_body, (
        "the gated rule's body_confirms must be the D-DF self-definition-marker "
        "predicate"
    )

    (qualifier_rule,), _ = mock_register.call_args_list[2]
    assert qualifier_rule.jurisdiction_codes == ("US-*",)
    assert qualifier_rule.matches is module.matches_defined_qualifier_heading, (
        "the THIRD registered rule's matches must be cycle-5 item 13's NARROW "
        "'defined (qualifier)'/'defined to [verb]' predicate, not the full union"
    )
    assert qualifier_rule.body_confirms is module.defines_qualifier_in_body, (
        "the qualifier rule's body_confirms must be item 13's own self-definition-"
        "marker predicate (a superset of defines_in_body's verb whitelist, adding "
        "include(s)/shall (not) include -- see test_definition_links_us_heading_"
        "variants_cycle5.py's module docstring)"
    )


def test_baseline_first_registry_second_contract_is_safe_to_compose():
    """Hand-composes the documented consumption contract; see module
    docstring for exactly what this does and does not prove."""
    from app.definition_links.rules.us_heading_variants import matches_heading_variant
    from app.definition_links.us_profile import is_definitions_heading

    def combined(heading: str) -> bool:
        return is_definitions_heading(heading) or matches_heading_variant(heading)

    rows = _load_rows()

    # (a) baseline-True headings stay True (first branch; registry never
    # reached, but combined() must still return True end-to-end).
    already_true_headings = [
        "Definitions.",
        "796. Definitions.",
        "SECTION 57-5-880. Transportation improvement projects; definitions",
    ]
    for heading in already_true_headings:
        assert is_definitions_heading(heading) is True, (
            f"test precondition failed: {heading!r} must already be baseline-True"
        )
        assert combined(heading) is True

    # (b) our new family-4 headings are picked up by the second branch.
    positive_act_ids = [
        "STATE_CT_T42a_C9_S42a-9-102",
        "STATE_MO_C334_S334.043",
        "STATE_DC_T28_C_S28:2A-103",
        "STATE_WI_C939_S939.22",
        "STATE_CT_T36a_C668_S36a-636",
    ]
    for act_id in positive_act_ids:
        heading = rows[act_id]["section_title"]
        assert is_definitions_heading(heading) is False, (
            f"test precondition failed: {heading!r} must be baseline-False "
            "(this is exactly what makes it family-4's job, not a regression "
            "of an existing capability)"
        )
        assert combined(heading) is True, f"{heading!r} must be recovered via the registry rule"

    # (c) negative guards stay False through BOTH branches.
    negative_act_ids = [
        "STATE_TX_Cfa_C101_S101.001",
        "STATE_AZ_T33_C6.1_A1_S821",
        "STATE_AR_T23_C64_S1_S23-64-103",
        "STATE_NY_ANPC_A4_S406",
        "STATE_AK_T32_C32.06_S32.06.406",
    ]
    for act_id in negative_act_ids:
        heading = rows[act_id]["section_title"]
        assert combined(heading) is False, f"{heading!r} must stay False through both branches"
