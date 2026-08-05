"""RED tests -- sprint 2026-08-05-defs-core-follow-on-2, gate G12
(director ruling D-INCLUDES, program doc `2026-08-04-definition-
completeness.md` @ `6a56a84`; gate opened by the program-manager log
@ `e4032c7`).

**The defect.** `_MEANS_IDIOM_GAP_RE` (`backend/app/definition_links/
us_profile.py`, used by `_extract_inline_quoted_definitions`, the
placeholder-heading/`heading_was_derived=True` fallback `extract_
definitions_from_section` falls back to when the primary `"(N)"`-block
splitter finds nothing) recognizes only `means | shall mean | has the
meaning`. A quoted term introduced by `includes` or `shall include`
never starts its own `entries` boundary, so it is either (a) silently
swallowed into the immediately PRECEDING recognized entry's
`definition_text` (contamination -- real IL row
`STATE_IL_C220_A5_S16-102` below), or (b) if no entry precedes it,
dropped from the output entirely (real IL row
`STATE_IL_C735_A110_S10` below) -- both are the SAME root cause
(`_MEANS_IDIOM_GAP_RE`'s missing vocabulary), just manifesting
differently depending on the swallowed entry's position relative to
other recognized entries.

**MANAGER RULING (relayed in G12's brief, verified in the program log's
Phase 3b): implement BOTH boundary AND emission, together.** Boundary-
without-emission would convert a contamination bug into a silent-drop
bug -- today the swallowed content is at least PRESENT (wrongly
attached to the preceding entry); terminating without emitting would
make it vanish entirely, a regression in kind under this program's
zero-miss bar.

**DIRECTOR RULING D-INCLUDES (program doc @ `6a56a84`).** The `includes`
defining-verb class is CAPTURED with the naive quoted-term anchor,
program-wide (50,528 anchor occurrences / 32,199 rows corpus-wide;
100/100 hand-read occurrences definitional across two independent
seeds; tightened guards measured to cost 32-56% of TRUE definitions for
no measured precision gain -- rejected). Consequences: `includes`/
`shall include` -- these two forms exactly, not a broader `include`-
family -- join the program-wide defining-verb vocabulary. The PA
construction-clause guard (`References to "X" shall include Y`) is
REQUIRED and must be TARGETED: suppress only when the quote is
immediately preceded by "References to"/"Reference to" -- never by
idiom-absence, never a broader guard (the ruling explicitly rejected
tightened guards as pure recall loss).

**Scope boundary vs. the G3-sibling gate (still pending its own
both-sides sample, per `us_profile.py`'s own G3 comment block above
`_split_into_numbered_blocks`).** G3-sibling's job is wiring
`_trailing_notes_boundary` into `_extract_inline_quoted_definitions`'s
OWN unbounded-last-entry fallback (`end = ... else len(text)`) --
whether the trailing text after the LAST recognized entry should be cut
at a trailing-notes marker. This gate (G12) does not touch that logic
at all: every fixture below is chosen so the entry whose boundary/
emission is under test is NOT the row's last entry (see each fixture's
own sanity test), so this gate's REDs cannot be accidentally satisfied
or defeated by G3-sibling's independent, not-yet-landed fix.

**Denominator discipline (P-R7/M18).** The corpus-wide measurement in
this gate's report is built from STRUCTURAL signals only -- which rows
reach `_extract_inline_quoted_definitions` at all (`heading_was_derived`
would be `True` AND the primary `"(N)"`-block splitter yields nothing)
and, within those rows, every quoted-term occurrence
(`_QUOTE_TERM_RE`, idiom-agnostic) -- never by which idiom words are
present, since that is the very vocabulary being widened.

**Live path.** Every RED below calls `USProfile.extract_definitions_
from_section` (the exact method `pipeline.py` calls once a section is
recognized as a Definitions section) directly on a real, byte-verified
corpus row's `text`, preceded by `profile.normalize_for_parsing`
(matching `pipeline.py`'s own Stage-0/Stage-2 order). `heading_was_
derived=True` is passed explicitly rather than re-deriving it from
`pipeline.py`'s own heading-recognition dance, matching the established
precedent in this same test directory
(`test_us_core_g1_ms_padding_strip_red.py`) for calling the module-level
extraction function directly when the row's own recognition machinery
is not itself the thing under test. Each fixture's own sanity test
proves this kwarg matches what production would actually compute for
that row (`is_definitions_heading` False on the raw heading,
`derive_heading_from_body` non-`None` and itself recognized), so the
`True` passed here is not a fabricated bypass.

No test in this file reads the corpus. All three fixture rows are
byte-verified, vendored verbatim (every original parquet column, values
unmodified) at `backend/tests/fixtures/us_statutes/g12_*.json` --
provenance and SHA-256 of each row's `text` field recorded in this
directory's `README.md`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.definition_links.us_profile import (
    USProfile,
    _leading_quote_candidate,
    _split_into_numbered_blocks,
    derive_heading_from_body,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load_row(fixture_name: str) -> dict:
    rows = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


# --- Fixture 1: STATE_IL_C220_A5_S16-102 -- genuine SWALLOWING -------------
# (220 ILCS 5/16-102), real Illinois Public Utilities Act definitions
# section. "Base rates" is a real `"..." means ...` entry whose real
# drafting immediately continues with a SECOND, separately-quoted term,
# `"Competitive service" includes (i) any service that has been
# declared to be competitive pursuant to Section 16-113 of this Act,
# (ii) contract se[rvice]...` -- today, because `includes` is not in
# `_MEANS_IDIOM_GAP_RE`, "Competitive service" never starts its own
# entry, so its quote+idiom+definition text is swallowed whole into
# "Base rates"'s own `definition_text` (which today runs 1,047 chars
# instead of the true ~737).

IL_BASE_RATES_FIXTURE = "g12_il_base_rates_competitive_service_row.json"
IL_BASE_RATES_ACT_ID = "STATE_IL_C220_A5_S16-102"


def test_il_base_rates_row_reaches_the_fallback_via_a_derived_heading_not_the_primary_splitter():
    """Sanity/mechanism proof (not the RED itself): confirms `heading_was_
    derived=True` used by the tests below is not a fabricated bypass, and
    that the primary `"(N)"`-block splitter genuinely yields NOTHING for
    this row -- so `_extract_inline_quoted_definitions` (this gate's own
    target) is what actually runs, not `_leading_quote_candidate`."""
    row = _load_row(IL_BASE_RATES_FIXTURE)
    assert row["act_id"] == IL_BASE_RATES_ACT_ID
    assert row["section_title"] == "Section 16-102", (
        "fixture must reproduce IL's real bare-placeholder section_title shape"
    )
    profile = USProfile(code="US-IL")
    body = profile.normalize_for_parsing(row["text"])

    assert profile.is_definitions_heading(row["section_title"], body) is False, (
        "sanity: the raw placeholder heading must NOT be recognized directly -- "
        "otherwise heading_was_derived would be False in the real pipeline"
    )
    derived = derive_heading_from_body(row["section_title"], body)
    assert derived is not None and profile.is_definitions_heading(derived, body), (
        "sanity: the IL embedded 'Sec. N. Definitions.' convention must be "
        "found in the body, matching what pipeline.py would compute"
    )

    primary_blocks = _split_into_numbered_blocks(body)
    primary_candidates = [
        c for b in primary_blocks if (c := _leading_quote_candidate(b, scope="x")) is not None
    ]
    assert primary_candidates == [], (
        "sanity: the primary '(N)'-block splitter must yield NOTHING for this row "
        f"(no digit-numbered markers in the real text) -- got {len(primary_candidates)} "
        "candidates, which would mean the fallback under test never actually runs"
    )


def test_il_competitive_service_terminates_base_rates_and_becomes_its_own_candidate():
    """THE LOAD-BEARING RED (boundary AND emission, together). Today
    "Competitive service"'s quote+`includes`+definition is swallowed
    whole into "Base rates"'s own `definition_text` (1,047 chars,
    containing the literal substring '\"Competitive service\" includes').
    Once `_MEANS_IDIOM_GAP_RE` recognizes `includes`, "Competitive
    service" must (a) TERMINATE "Base rates" at its own quote's start
    (boundary) and (b) become its own `DefinitionCandidate` (emission)."""
    row = _load_row(IL_BASE_RATES_FIXTURE)
    profile = USProfile(code="US-IL")
    body = profile.normalize_for_parsing(row["text"])

    candidates = profile.extract_definitions_from_section(body, scope="law-wide", heading_was_derived=True)
    by_term = {c.terms[0]: c for c in candidates}

    assert "Competitive service" in by_term, (
        f"'Competitive service' must be recovered as its own candidate once the "
        f"'includes' idiom is recognized -- got terms {sorted(by_term)!r}"
    )
    assert by_term["Competitive service"].definition_text.startswith(
        "(i) any service that has been declared to be competitive"
    ), (
        "'Competitive service''s own definition_text must start right after its "
        f"own 'includes' idiom -- got {by_term['Competitive service'].definition_text[:80]!r}"
    )

    assert "Base rates" in by_term, "'Base rates' itself must still be recovered"
    base_rates_text = by_term["Base rates"].definition_text
    assert "Competitive service" not in base_rates_text, (
        "'Base rates'.definition_text must be TERMINATED at 'Competitive service''s "
        f"own quote -- it still illegally contains the swallowed entry: "
        f"{base_rates_text[-120:]!r}"
    )
    assert base_rates_text.endswith("notice and hearing."), (
        f"'Base rates' must end exactly where 'Competitive service' begins -- got "
        f"{base_rates_text[-60:]!r}"
    )
    assert len(base_rates_text) < 800, (
        f"'Base rates' must shrink from today's contaminated 1,047 chars to its true "
        f"~737 once the swallowed entry is cleanly split off -- got {len(base_rates_text)}"
    )


# --- Fixture 2: STATE_IL_C735_A110_S10 -- genuine DROP (no preceding -------
# --- entry to swallow into) -------------------------------------------------
# (735 ILCS 110/10), real Illinois Civil Practice Law. "Government",
# "Person", and "Motion" are each real `"..." includes ...` entries that
# appear BEFORE the row's first `means`-idiom entry ("Moving party").
# Today `entries` (in `_extract_inline_quoted_definitions`) starts only
# at "Moving party" -- everything before that position is not attached
# to ANY candidate, so "Government"/"Person"/"Motion" are not merely
# contaminated, they vanish from the output entirely. This is the
# "boundary-without-emission would be a silent-drop bug" scenario the
# manager ruling names, proven on a row where it already occurs today
# for a related reason (idiom-absence, not a hypothetical).

IL_DROPPED_FIXTURE = "g12_il_government_person_motion_dropped_row.json"
IL_DROPPED_ACT_ID = "STATE_IL_C735_A110_S10"


def test_il_dropped_row_reaches_the_fallback_via_a_derived_heading_not_the_primary_splitter():
    """Sanity/mechanism proof, mirroring the Base-rates fixture's own
    check above."""
    row = _load_row(IL_DROPPED_FIXTURE)
    assert row["act_id"] == IL_DROPPED_ACT_ID
    assert row["section_title"] == "Section 10"
    profile = USProfile(code="US-IL")
    body = profile.normalize_for_parsing(row["text"])

    assert profile.is_definitions_heading(row["section_title"], body) is False
    derived = derive_heading_from_body(row["section_title"], body)
    assert derived is not None and profile.is_definitions_heading(derived, body)

    primary_blocks = _split_into_numbered_blocks(body)
    primary_candidates = [
        c for b in primary_blocks if (c := _leading_quote_candidate(b, scope="x")) is not None
    ]
    assert primary_candidates == [], (
        f"sanity: primary splitter must yield nothing -- got {len(primary_candidates)}"
    )


def test_il_government_person_and_motion_are_recovered_before_the_first_means_entry():
    """THE LOAD-BEARING RED for the drop-shaped manifestation. Today
    `extract_definitions_from_section` returns exactly 2 candidates for
    this row ("Moving party", "Responding party") -- "Government",
    "Person", and "Motion" are silently absent, not merely mis-bounded,
    because nothing recognized precedes them for them to be swallowed
    into. Once `includes` is recognized, all 5 real defined terms must
    come back, each correctly bounded (none containing a NEXT term's own
    quote+idiom)."""
    row = _load_row(IL_DROPPED_FIXTURE)
    profile = USProfile(code="US-IL")
    body = profile.normalize_for_parsing(row["text"])

    candidates = profile.extract_definitions_from_section(body, scope="law-wide", heading_was_derived=True)
    by_term = {c.terms[0]: c for c in candidates}

    for missing_term in ("Government", "Person", "Motion"):
        assert missing_term in by_term, (
            f"{missing_term!r} must be recovered as its own candidate once 'includes' is "
            f"recognized -- got terms {sorted(by_term)!r} (today this term is silently "
            "dropped entirely, not merely contaminated, because no recognized entry "
            "precedes it in this row)"
        )

    assert by_term["Government"].definition_text.startswith(
        "a branch, department, agency, instrumentality"
    )
    assert "Person" not in by_term["Government"].definition_text.split(".", 1)[0], (
        "'Government' must terminate before 'Person' starts, not run into it"
    )
    assert by_term["Person"].definition_text.startswith("any individual, corporation")
    assert by_term["Motion"].definition_text.startswith("any motion to dismiss")

    # Non-regression half: the two ALREADY-correctly-recognized `means`
    # entries must be completely unaffected by the widening.
    assert by_term["Moving party"].definition_text.startswith(
        "any person on whose behalf a motion"
    )
    assert by_term["Responding party"].definition_text.startswith(
        "any person against whom a motion"
    )


# --- Fixture 3: STATE_PA_T15_C57_S5749 -- the mandatory PA guard -----------
# (15 Pa.C.S. Section 5749), real Pennsylvania nonprofit-corporation
# indemnification statute. `"For the purposes of this subchapter: (1)
# References to "other enterprises" shall include employee benefit
# plans and references to "serving at the request of the corporation"
# shall include ..."` -- a construction/interpretation clause about how
# OTHER text in the subchapter should be READ, not a `"X" means Y`-
# shaped definition. D-INCLUDES's mandatory condition #1: this shape
# must be suppressed by a TARGETED guard (quote immediately preceded by
# "References to"/"Reference to"), never by idiom-absence.
#
# This real row's OWN `section_title` ("Application to employee benefit
# plans.") is a genuine heading, not a placeholder -- PA is one of the
# "7 states already working off their own section_title" the module
# docstring names, so this row does NOT reach `heading_was_derived=True`
# in the live pipeline today. `heading_was_derived=True` is forced here
# deliberately (see module docstring on why this is not a fabricated
# bypass: this gate's guard is a REQUIRED, program-wide property of
# `_extract_inline_quoted_definitions` itself -- it must hold for
# WHATEVER row reaches that function, not only the specific rows that
# happen to reach it via IL/CA/GA's placeholder-heading convention
# today). Verified live below: this row's own primary `"(N)"`-block
# splitter ALSO yields nothing (its 3 real digit-marked blocks never
# start with a quote), so forcing the kwarg exercises exactly the same
# fallback function real placeholder-heading rows do.

PA_FIXTURE = "g12_pa_references_to_construction_clause_row.json"
PA_ACT_ID = "STATE_PA_T15_C57_S5749"

_WIDENED_MEANS_IDIOM_GAP_RE = re.compile(
    r'^[^"“”]{0,200}?\b(?:means|shall mean|has the meaning|shall include|includes)\b:?\s*',
    re.IGNORECASE,
)


def test_pa_row_reaches_the_fallback_when_forced_and_is_not_the_rows_last_entry():
    """Sanity/mechanism proof: confirms the primary splitter yields
    nothing for this real row (so forcing `heading_was_derived=True`
    genuinely exercises `_extract_inline_quoted_definitions`, not a
    no-op), and that the guarded quote ("other enterprises") is NOT the
    row's last quoted span -- ruling out any interaction with the
    separate, not-yet-landed G3-sibling last-entry fix."""
    row = _load_row(PA_FIXTURE)
    assert row["act_id"] == PA_ACT_ID
    assert row["section_title"] == "Application to employee benefit plans."
    profile = USProfile(code="US-PA")
    body = profile.normalize_for_parsing(row["text"])

    primary_blocks = _split_into_numbered_blocks(body)
    assert len(primary_blocks) == 3, f"expected the row's 3 real digit-marked blocks, got {len(primary_blocks)}"
    primary_candidates = [
        c for b in primary_blocks if (c := _leading_quote_candidate(b, scope="x")) is not None
    ]
    assert primary_candidates == [], (
        "sanity: none of this row's 3 real blocks start with a quote (each starts with "
        f"ordinary prose) -- got {len(primary_candidates)} candidates"
    )

    assert '"fines."' in body, (
        "sanity: a THIRD quoted span ('fines.') exists after the guarded pair, proving "
        "'other enterprises' is not this row's last quoted term either"
    )


def test_pa_construction_clause_guard_is_load_bearing_under_widened_vocabulary():
    """THE LOAD-BEARING RED for D-INCLUDES's mandatory condition #1.

    Today, real unmodified code silently drops BOTH 'other enterprises'
    and 'serving at the request of the corporation' -- but for the WRONG
    reason (idiom-absence: 'shall include' is not yet in `_MEANS_IDIOM_
    GAP_RE`), not because any guard exists. Asserted first below as a
    documented control, matching this codebase's own established
    convention (`test_us_scoped_inline_rules_negative_controls.py`'s
    sibling re-authored pin) for telling apart "protected by accident"
    from "protected by design".

    The actual RED: `_MEANS_IDIOM_GAP_RE` is monkeypatched to the
    WIDENED regex this gate's own boundary+emission items above require
    (items G12-1a/G12-1b) -- simulating that fix landing, in isolation,
    with NO guard. Verified live (this Planner's report) that under this
    exact simulation, on this exact real row, BOTH quoted terms get
    WRONGLY captured as their own candidates. The assertion below (that
    they must NOT be captured) therefore FAILS today -- RED for the
    right reason: the vocabulary widening alone is not sufficient, the
    targeted 'References to' guard is a REQUIRED, separate mechanism.
    Expected GREEN once the Developer's guard ships alongside the
    widening; RED again if the guard is ever removed while the widened
    vocabulary stays (the contract this style of test is built to hold,
    per the sibling panel's own precedent)."""
    row = _load_row(PA_FIXTURE)
    profile = USProfile(code="US-PA")
    body = profile.normalize_for_parsing(row["text"])

    import app.definition_links.us_profile as m

    # Control: today's REAL, unmodified code -- silent for the OLD reason.
    today = profile.extract_definitions_from_section(body, scope="law-wide", heading_was_derived=True)
    today_terms = {t for c in today for t in c.terms}
    assert "other enterprises" not in today_terms
    assert "serving at the request of the corporation" not in today_terms

    # Isolate the guard: simulate the widened vocabulary (this gate's own
    # fix) landing with NO guard, and confirm the construction clause
    # WOULD be wrongly captured without one.
    original_re = m._MEANS_IDIOM_GAP_RE
    m._MEANS_IDIOM_GAP_RE = _WIDENED_MEANS_IDIOM_GAP_RE
    try:
        widened = profile.extract_definitions_from_section(
            body, scope="law-wide", heading_was_derived=True
        )
    finally:
        m._MEANS_IDIOM_GAP_RE = original_re

    widened_terms = {t for c in widened for t in c.terms}
    assert "other enterprises" not in widened_terms, (
        "simulated D-INCLUDES vocabulary widening (means|shall mean|has the meaning|"
        "shall include|includes) captured the PA construction-clause term 'other "
        "enterprises' -- the targeted 'References to' guard is missing or not "
        f"load-bearing -- got candidates {[c.terms for c in widened]!r}"
    )
    assert "serving at the request of the corporation" not in widened_terms, (
        "same construction clause's second 'references to \"X\" shall include Y' span "
        f"was also wrongly captured -- got candidates {[c.terms for c in widened]!r}"
    )

    # Positive control (informational, not part of the RED contract): a
    # genuine, non-'References to' 'includes' term on this SAME row must
    # stay reachable once the guard exists (the corpus row itself has no
    # bare '"fines" includes ...' shape to probe here -- '"fines."' is
    # itself the definiendum-free tail of item (2), not a defined term --
    # so this is deliberately left as a named gap, not asserted false-
    # positive-free here; the boundary+emission REDs above already prove
    # genuine 'includes' terms ARE captured once the guard is scoped
    # correctly to ONLY the 'References to' shape).
