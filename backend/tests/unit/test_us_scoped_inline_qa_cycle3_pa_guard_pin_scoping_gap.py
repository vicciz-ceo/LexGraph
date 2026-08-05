"""QA cycle 3, item 8 (sprint 2026-08-04-defs-us-scoped-inline). Verifies
whether `test_pa_construction_clause_guard_is_load_bearing_under_widened_
vocabulary` (`test_us_scoped_inline_rules_negative_controls.py`) actually
isolates the SHIPPED `_preceded_by_references_to` guard, per this cycle's
brief: "confirm it passes for the RIGHT reason by mutating away the
SHIPPED `_preceded_by_references_to` and checking the test fails."

FINDING: it does NOT. The existing test's `monkeypatch.setattr(shapes,
"_MARKER_QUOTE_RE", widened_marker_quote_re)` patches the ATTRIBUTE on
`us_scoped_inline_shapes` -- but `us_scoped_inline_entries.py` (where
`_multi_entries`/`_unmarked_multi_entries`/`_split_idiom_chain` actually
live and actually resolve `_MARKER_QUOTE_RE`/`_IDIOM_RE`) imported those
names with `from ...shapes import (_IDIOM_RE, _MARKER_QUOTE_RE, ...)` --
a SEPARATE binding in `entries.__dict__`, decoupled from `shapes.__dict__`
after import time (the classic "from X import Y" gotcha: reassigning
`X.Y` does not change an already-bound `Y` in the importing module's
namespace). So the existing test's marker-widening never reaches the code
that actually needs it, the PA row's `(1) References to "other
enterprises"` marker-adjacency gap is NEVER neutralized, and the row stays
unreachable via `_multi_entries`/`_unmarked_multi_entries` for THAT reason
alone -- identical to the exact "SECOND finding" trap the test's own
docstring already names and believes it closed ("An isolated probe must
ALSO neutralize this marker-adjacency accident ... or it would pass for
THAT reason alone, guard or no guard"). It closes it in a scratch-copy
FILE EDIT (which correctly propagates, since a real file edit changes the
one object everyone imports fresh) but not in the COMMITTED monkeypatch
(which does not).

Net effect: the committed test passes VACUOUSLY -- it would pass
identically whether `_preceded_by_references_to` exists or not, proven
directly below. The underlying guard mechanism itself IS real and load-
bearing (proven below too, once the widening is scoped correctly) -- this
is a defect in the TEST's isolation, not in `backend/app/`.

Per QA's role boundary: this file proves the defect; `backend/app/` and
the existing test file are both READ-ONLY to QA.
"""

from __future__ import annotations

import json
import pathlib
import re

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)


def _row() -> dict:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == "STATE_PA_T15_C57_S5749")


def _widened_marker_quote_re(marker_re: str) -> re.Pattern:
    return re.compile(rf'{marker_re}\s*(?:references? to\s+)?["“]', re.IGNORECASE)


def test_the_committed_tests_own_monkeypatch_scope_never_reaches_entries_module(monkeypatch):
    """Reproduces EXACTLY the existing test's own monkeypatch target
    (`shapes._MARKER_QUOTE_RE` only) and shows the PA row stays unreachable
    -- EVEN WITH the guard separately neutralized. If the existing test's
    widening actually made the row reachable, neutralizing the guard here
    would flip the result to a capture; it does not, proving the existing
    test's own probe never gets past the (still-unwidened, in the module
    that actually matters) marker-adjacency gate to exercise the guard at
    all."""
    import app.definition_links.rules.us_scoped_inline as mod
    import app.definition_links.rules.us_scoped_inline_entries as entries
    import app.definition_links.rules.us_scoped_inline_shapes as shapes

    row = _row()
    widened_idiom_re = re.compile(
        r"\s*(?:has the same meaning as|have the same meaning as|has the meaning|shall be construed to mean"
        r"|shall include|shall mean|does not include|is defined as|includes?|means|is)\b,?\s*",
        re.IGNORECASE,
    )
    monkeypatch.setattr(shapes, "_IDIOM_RE", widened_idiom_re)
    monkeypatch.setattr(mod, "_IDIOM_RE", widened_idiom_re)
    monkeypatch.setattr(shapes, "_MARKER_QUOTE_RE", _widened_marker_quote_re(shapes._MARKER_RE))
    # Neutralize the SHIPPED guard entirely -- if the row were genuinely
    # reachable under the patches above, this alone would surface "other
    # enterprises".
    monkeypatch.setattr(entries, "_preceded_by_references_to", lambda body, pos: False)

    candidates = mod.extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "other enterprises" not in terms, (
        "unexpected: the existing test's own monkeypatch scope reached the guard after all -- "
        "this finding would be moot"
    )


def test_pa_guard_is_load_bearing_once_the_widening_is_correctly_scoped_to_entries_module(monkeypatch):
    """The CORRECTLY-scoped version of the existing isolation probe:
    patches `_IDIOM_RE`/`_MARKER_QUOTE_RE` on `us_scoped_inline_entries`
    itself (where `_multi_entries`/`_unmarked_multi_entries`/`_split_idiom_
    chain` actually resolve those names), matching what the scratch-copy
    FILE EDIT in the existing test's own "MUTATION EVIDENCE" paragraph
    actually did. With this correct scope: guard present -> silent; guard
    neutralized -> "other enterprises" captured. This is the proof that
    `_preceded_by_references_to` really is load-bearing -- the underlying
    mechanism is sound, only the committed test's monkeypatch target was
    wrong."""
    import app.definition_links.rules.us_scoped_inline as mod
    import app.definition_links.rules.us_scoped_inline_entries as entries
    import app.definition_links.rules.us_scoped_inline_shapes as shapes

    row = _row()
    widened_idiom_re = re.compile(
        r"\s*(?:has the same meaning as|have the same meaning as|has the meaning|shall be construed to mean"
        r"|shall include|shall mean|does not include|is defined as|includes?|means|is)\b,?\s*",
        re.IGNORECASE,
    )
    widened_marker_quote_re = _widened_marker_quote_re(shapes._MARKER_RE)
    monkeypatch.setattr(entries, "_IDIOM_RE", widened_idiom_re)
    monkeypatch.setattr(entries, "_MARKER_QUOTE_RE", widened_marker_quote_re)

    # Guard PRESENT (shipped, untouched): must stay silent.
    candidates_guarded = mod.extract_us_scoped_inline_definitions(row["text"])
    terms_guarded = {t for c in candidates_guarded for t in c.terms}
    assert "other enterprises" not in terms_guarded, (
        "with the row correctly made reachable and the SHIPPED guard intact, 'other enterprises' "
        f"should stay suppressed -- got {candidates_guarded!r}"
    )

    # Guard NEUTRALIZED: must now be captured -- proving the guard, not
    # some other accident, was doing the work.
    monkeypatch.setattr(entries, "_preceded_by_references_to", lambda body, pos: False)
    candidates_unguarded = mod.extract_us_scoped_inline_definitions(row["text"])
    terms_unguarded = {t for c in candidates_unguarded for t in c.terms}
    assert "other enterprises" in terms_unguarded, (
        "expected removing the guard (with the row otherwise reachable) to capture 'other "
        f"enterprises' -- the guard is not load-bearing here, or something else is masking it -- "
        f"got {candidates_unguarded!r}"
    )
