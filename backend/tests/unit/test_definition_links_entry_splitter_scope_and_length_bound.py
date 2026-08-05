"""RED tests for sprint 2026-08-04-defs-us-multiterm, program ruling U-R10:
both of this sprint's `EntrySplitterRule`s are registered with
`jurisdiction_codes=("US-*",)`, re-contributing the WHOLE section body as
one extra block to EVERY US jurisdiction:

- `rules/us_multiterm_shared_clause.py` -- `_split_parent_redirect_whole_text`
- `rules/us_inline_parenthetical.py` -- `_split_apposition_whole_text`

`entry_splitter` is an ADDITIVE dispatch kind (`all_blocks = baseline_blocks
+ extra_blocks`, `us_profile.py`'s `USProfile.extract_definitions_from_
section`), so this inflates the block population for EVERY panel scanning
EVERY US jurisdiction's bodies, not just this sprint's own two accepted
shapes. The markers panel's merged-tree simulation measured the cost (WA
oversized population 3 -> 7, worst case 11,314 chars). U-R10 requires (1)
narrowing each registration to the jurisdiction(s) its accepted item(s)
actually need, and (2) a contribution length bound, so neither splitter can
ever re-contribute an unbounded whole-section blob regardless of
jurisdiction.

**Jurisdiction sets -- DERIVED empirically, not guessed** (2026-08-05):
temporarily made each splitter return `[]` unconditionally (simulating "this
splitter never fires"), ran the full suite, and recorded exactly which
CURRENTLY-PASSING tests newly failed -- then reverted (`git diff --stat
backend/app/` empty before committing this file, confirmed both before and
after the experiment).

- Disabling `_split_parent_redirect_whole_text` broke exactly 3 tests, all
  on TX fixture rows (`STATE_TX_Cgv_C2009_S2009.003` /
  `STATE_TX_Cgv_C2002_S2002.001`): `test_multiterm_f5_shared_clause.py::
  test_tx_parent_clause_redirect_list_2009_003`,
  `::test_tx_parent_clause_redirect_list_2002_001`,
  `test_definition_links_multiterm_shared_clause.py::
  test_tx_s2009_003_parent_clause_terms_get_the_real_shared_definition_text`.
  Derived set: **`("US-TX",)`**.
- Disabling `_split_apposition_whole_text` broke exactly 1 test:
  `test_definition_links_inline_parenthetical.py::
  test_nh_s1_act_apposition_is_extracted_as_a_definition`
  (`STATE_NH_TXXVII_C301-B_S1`). Derived set: **`("US-NH",)`**.
  (NH's OTHER F6 row, `STATE_NH_TXXXVII_C408-C_S14` in `test_multiterm_f6_
  blocked_on_core_seam.py`, and ND's `STATE_ND_T26.1_C26.1-59_S26.1-59-01`,
  reach the apposition shape through the `ScopeTriggerRule` registration
  instead -- `_extract_ordinary_body`, for an ORDINARY non-Definitions-
  heading body -- a DIFFERENT rule kind, out of scope for U-R10, which
  names only the two `EntrySplitterRule`s. Confirmed unaffected by the
  disable experiment: neither test broke.)

Both derived sets match the sprint manager's own stated expectation (TX /
NH) exactly -- reported per the brief's instruction either way.

**Length bound -- `_MAX_CONTRIBUTION_CHARS = 2000`, evidence-based:** the
real rows this sprint's two accepted items actually need are 855 chars
(`STATE_TX_Cgv_C2009_S2009.003`), 881 chars (`STATE_TX_Cgv_C2002_S2002.001`)
and 99 chars (`STATE_NH_TXXVII_C301-B_S1`) -- measured directly off the
committed fixtures. 2000 chars gives >2.2x headroom over the largest real
accepted need (881) while sitting >5.6x BELOW markers' measured 11,314-char
worst case -- comfortably blocking that worst case with margin on both
sides, not a bound picked to just barely clear today's real rows.

Live-path discipline: every test drives the REAL, current
`USProfile.extract_definitions_from_section` -- the dispatching profile
METHOD, reached via `get_profile(...)`, that unions in registered
`EntrySplitterRule`/`TermClauseRule` output (repo memory: a test asserting
a rule is merely *registered* proves nothing -- the bare module-level free
function never consults the registry at all, sprint 2026-08-04-defs-core-
dispatch/ruling M-R11).

Every test below is RED under TODAY's code (both splitters still
`("US-*",)`, no length bound implemented at all) for exactly the reason
its own assertion names -- proved live, output captured in the sprint log
entry for this ruling. The two POSITIVE controls (in-scope jurisdiction
still fires) are expected GREEN both today and after the Developer's fix --
included because the brief asked for paired positive/negative controls,
not because they pin new behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.profiles import get_profile

_F5_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)
_F6_UNIT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "inline_parenthetical_sample_rows.json"
)

# Evidence for this number is in the module docstring above.
_MAX_CONTRIBUTION_CHARS = 2000

# SYNTHETIC padding -- deliberately NOT a corpus claim, contains no quoted
# terms and no defining idiom of its own, so it cannot itself trigger any
# extraction rule; used only to push a real accepted clause's OWN body past
# `_MAX_CONTRIBUTION_CHARS` for the length-bound negative controls below.
_SYNTHETIC_FILLER = (
    "This filler sentence contains no quoted terms and no defining idiom "
    "whatsoever, and exists purely to push this synthetic test body past "
    "the contribution length bound. "
) * 13


def _load(path: Path) -> dict[str, dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


# --- TX parent-redirect splitter (rules/us_multiterm_shared_clause.py) ----

_TX_ROW = _load(_F5_FIXTURE_PATH)["STATE_TX_Cgv_C2009_S2009.003"]
_TX_REDIRECT_TERMS = ("contested case", "party", "person", "rule.")


def test_tx_parent_redirect_fires_for_us_tx_positive_control():
    """Positive control: US-TX is the derived in-scope jurisdiction --
    stays green both before and after the Developer's narrowing."""
    profile = get_profile("US-TX")
    scope = profile.determine_scope(_TX_ROW["text"])
    candidates = profile.extract_definitions_from_section(_TX_ROW["text"], scope=scope)
    assert any(c.terms == _TX_REDIRECT_TERMS for c in candidates), (
        f"expected the combined parent-redirect candidate {_TX_REDIRECT_TERMS!r} "
        f"for the real, in-scope US-TX row. Got candidates={[(c.terms) for c in candidates]!r}"
    )


def test_tx_parent_redirect_does_not_fire_for_an_out_of_scope_jurisdiction():
    """Negative control (U-R10): the IDENTICAL real TX-shaped text, run
    through a DIFFERENT jurisdiction's profile (US-CA, confirmed by the
    disable experiment above to have zero currently-passing dependents on
    this splitter). Only `self.code` differs between this call and the
    positive control above -- this isolates the EntrySplitterRule's
    jurisdiction gate specifically. RED today: both splitters are
    currently `("US-*",)`, so US-CA also gets the whole-text contribution
    and produces the same combined candidate."""
    profile = get_profile("US-CA")
    scope = profile.determine_scope(_TX_ROW["text"])
    candidates = profile.extract_definitions_from_section(_TX_ROW["text"], scope=scope)
    assert not any(c.terms == _TX_REDIRECT_TERMS for c in candidates), (
        f"US-CA is NOT in the derived jurisdiction set for the parent-redirect "
        f"EntrySplitterRule (only US-TX is) -- it must not receive the whole-"
        f"section-text contribution and must not produce {_TX_REDIRECT_TERMS!r}. "
        f"Got candidates={[c.terms for c in candidates]!r}"
    )


def test_tx_parent_redirect_contribution_exceeding_length_bound_is_not_emitted():
    """Negative control (U-R10, length bound): a SYNTHETIC body (real TX
    parent-redirect clause, verbatim, padded with idiom-free filler to
    exceed `_MAX_CONTRIBUTION_CHARS`) under the in-scope US-TX profile.
    RED today: no length bound exists at all, so the oversized whole-text
    block is still contributed and still produces the combined candidate."""
    oversized_text = _SYNTHETIC_FILLER + _TX_ROW["text"]
    assert len(oversized_text) > _MAX_CONTRIBUTION_CHARS, "test setup: padding must exceed the bound"
    profile = get_profile("US-TX")
    scope = profile.determine_scope(oversized_text)
    candidates = profile.extract_definitions_from_section(oversized_text, scope=scope)
    assert not any(c.terms == _TX_REDIRECT_TERMS for c in candidates), (
        f"a whole-section contribution of {len(oversized_text)} chars exceeds the "
        f"{_MAX_CONTRIBUTION_CHARS}-char bound and must NOT be emitted by "
        f"_split_parent_redirect_whole_text, even for the in-scope US-TX "
        f"jurisdiction -- got the combined candidate {_TX_REDIRECT_TERMS!r} anyway. "
        f"Got candidates={[c.terms for c in candidates]!r}"
    )


# --- NH apposition splitter (rules/us_inline_parenthetical.py) ------------

_NH_ROW = _load(_F6_UNIT_FIXTURE_PATH)["STATE_NH_TXXVII_C301-B_S1"]


def test_nh_apposition_fires_for_us_nh_positive_control():
    """Positive control: US-NH is the derived in-scope jurisdiction --
    stays green both before and after the Developer's narrowing."""
    profile = get_profile("US-NH")
    scope = profile.determine_scope(_NH_ROW["text"])
    candidates = profile.extract_definitions_from_section(
        _NH_ROW["text"], scope=scope, heading_was_derived=True
    )
    all_terms = {t for c in candidates for t in c.terms}
    assert "Act" in all_terms, (
        f"expected the apposition candidate 'Act' for the real, in-scope US-NH "
        f"row. Got candidates={[c.terms for c in candidates]!r}"
    )


def test_nh_apposition_does_not_fire_for_an_out_of_scope_jurisdiction():
    """Negative control (U-R10): the IDENTICAL real NH apposition text, run
    through US-CA's profile instead (confirmed by the disable experiment to
    have zero currently-passing dependents on this splitter). RED today:
    both splitters are currently `("US-*",)`, so US-CA also gets the
    whole-text contribution and also produces "Act"."""
    profile = get_profile("US-CA")
    scope = profile.determine_scope(_NH_ROW["text"])
    candidates = profile.extract_definitions_from_section(
        _NH_ROW["text"], scope=scope, heading_was_derived=True
    )
    all_terms = {t for c in candidates for t in c.terms}
    assert "Act" not in all_terms, (
        f"US-CA is NOT in the derived jurisdiction set for the apposition "
        f"EntrySplitterRule (only US-NH is) -- it must not receive the whole-"
        f'section-text contribution and must not produce "Act". Got '
        f"candidates={[c.terms for c in candidates]!r}"
    )


def test_nh_apposition_contribution_exceeding_length_bound_is_not_emitted():
    """Negative control (U-R10, length bound): a SYNTHETIC body (real NH
    apposition sentence, verbatim, padded with idiom-free filler to exceed
    `_MAX_CONTRIBUTION_CHARS`) under the in-scope US-NH profile. RED today:
    no length bound exists at all, so the oversized whole-text block is
    still contributed and still produces "Act"."""
    oversized_text = _SYNTHETIC_FILLER + _NH_ROW["text"]
    assert len(oversized_text) > _MAX_CONTRIBUTION_CHARS, "test setup: padding must exceed the bound"
    profile = get_profile("US-NH")
    scope = profile.determine_scope(oversized_text)
    candidates = profile.extract_definitions_from_section(
        oversized_text, scope=scope, heading_was_derived=True
    )
    all_terms = {t for c in candidates for t in c.terms}
    assert "Act" not in all_terms, (
        f"a whole-section contribution of {len(oversized_text)} chars exceeds the "
        f"{_MAX_CONTRIBUTION_CHARS}-char bound and must NOT be emitted by "
        f"_split_apposition_whole_text, even for the in-scope US-NH jurisdiction "
        f'-- got "Act" anyway. Got candidates={[c.terms for c in candidates]!r}'
    )
