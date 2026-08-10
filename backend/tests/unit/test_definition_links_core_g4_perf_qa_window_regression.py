"""QA regression guard -- sprint 2026-08-10-core-g4-discriminator-perf.

Written independently by QA on top of the Planner's three RED files
(`test_definition_links_core_g4_perf_bounded_window.py`,
`test_definition_links_core_g4_perf_resolve_unit_path_live.py`,
`test_definition_links_core_g4_perf_equivalence.py`), which are ALL GREEN
today (the Developer's fix, commit `4c0ff01` -- `_SUFFIX_PROBE_WINDOW = 512`
bounding `_citation_or_xref_context`'s five suffix-regex probes). This file
adds two things those three do not cover on their own:

1. A TIGHTER, independently-chosen window ceiling than the Planner's 4096
   (generous 40x headroom over the ~100-char worst case). 4096 would not
   catch a partial regression -- e.g. the window silently drifting from 512
   to a few thousand chars during later refactors still passes a 4096-char
   check. `_MAX_SANE_WINDOW_QA` below is 1024: still 2x the shipped 512 (so
   it cannot false-positive on the current, correct implementation) but
   tight enough to fail if the window is ever silently widened toward
   "unbounded in practice" without anyone touching the 4096 ceiling.

2. A corpus-grounded lower-bound check: QA independently scanned the full
   pinned corpus (`vaquill/open-us-law`, snapshot
   `301000fc3465374ee0f23c3c6953a8a861e95cad`, all 105 parquet files,
   2,046,009 rows) for the longest REAL match of each of the five suffix
   patterns (structural-word alternation, full-U.S.C., `Section N`, lone
   `§ N`, bare state code). The longest observed anywhere in the corpus was
   24 characters. This test builds synthetic bodies (M-R107 compliant --
   generic filler plus the same closed pattern shapes the module itself
   defines over, no corpus row IDs/content depended on) containing a
   citation/structural-word context up to 100 characters before a marker
   token (>4x the corpus-observed real-world max, generous safety margin)
   at BOTH a near and a very far document position, and asserts the
   citation is still recognized (token rejected as non-genuine) at every
   position. This is the "citation longer than the window being dropped"
   guard named in the QA brief: it would fail if the window were ever
   shrunk below what real corpus citations need, or if `probe_start`'s
   arithmetic were broken in a way that clips a still-in-window match.

Self-mock ban compliance: `_citation_or_xref_context` and
`_is_citation_or_xref_context` are called live and unpatched throughout.
The window-recorder in test 1 only wraps the five suffix-regex objects
(not acceptance targets) to observe, not alter, the `(pos, endpos)`
arguments actually used -- same non-mutating-forward pattern as the
Planner's own recorder, independently reimplemented here rather than
imported, so this file has no import-time coupling to the Planner's test
module.
"""

from __future__ import annotations

from app.definition_links import us_profile

_SUFFIX_RE_NAMES = (
    "_STRUCTURAL_UNIT_WORD_SUFFIX_RE",
    "_FULL_USC_CITATION_SUFFIX_RE",
    "_SECTION_CITATION_SUFFIX_RE",
    "_LONE_SECTION_CITATION_SUFFIX_RE",
    "_BARE_STATE_CODE_CITATION_SUFFIX_RE",
)

# Tighter than the Planner's 4096-char ceiling (see module docstring, item
# 1): still 2x the shipped 512-char window, so the correct implementation
# clears it comfortably, but tight enough to catch a silent widening that
# would slip past a looser check.
_MAX_SANE_WINDOW_QA = 1024

_FILLER = "no citation or structural vocabulary appears anywhere in here "


class _QaWindowRecorder:
    """Forwards to the real compiled pattern's `.search` -- never alters the
    match decision -- while recording the `(pos, endpos)` args used."""

    def __init__(self, pattern):
        self._pattern = pattern
        self.windows: list[tuple[int, int]] = []

    def search(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.search(string, pos, endpos)


def _recorded_windows(body: str, token_start: int) -> list[tuple[int, int]]:
    originals = {name: getattr(us_profile, name) for name in _SUFFIX_RE_NAMES}
    recorders = {name: _QaWindowRecorder(pattern) for name, pattern in originals.items()}
    for name, recorder in recorders.items():
        setattr(us_profile, name, recorder)
    try:
        us_profile._citation_or_xref_context(body, token_start)
    finally:
        for name, pattern in originals.items():
            setattr(us_profile, name, pattern)
    return [w for recorder in recorders.values() for w in recorder.windows]


def test_suffix_probe_window_stays_within_a_tight_independent_ceiling():
    """A token 250,000+ characters into a body with no matchable context
    must not cause any suffix probe to search a window wider than
    `_MAX_SANE_WINDOW_QA` (1024) -- tighter than the Planner's own 4096
    ceiling, so a partial regression that widens the window well past 512
    but still under 4096 is still caught."""
    body = (_FILLER * (250_000 // len(_FILLER) + 1))[:250_000] + "(Z) "
    token_start = len(body) - 4

    windows = _recorded_windows(body, token_start)

    assert windows, "expected at least one suffix-regex probe to run (non-vacuity guard)"
    largest = max(w[1] - w[0] for w in windows)
    assert largest <= _MAX_SANE_WINDOW_QA, (
        f"G4 discriminator probe window ({largest} chars) exceeds QA's tighter "
        f"{_MAX_SANE_WINDOW_QA}-char ceiling at document position {token_start} -- "
        f"the lookback window may have been silently widened back toward unbounded."
    )


def test_realistic_citation_context_recognized_regardless_of_document_position():
    """Corpus-grounded floor check (see module docstring, item 2): a
    citation/structural-word context up to 100 characters before a marker
    token -- generous 4x+ margin over the 24-character longest real match
    QA found scanning the full pinned corpus -- must still be recognized as
    citation/cross-reference context (the token rejected), whether the
    marker sits near the start of the document or ~200,000 characters in.
    A window shrunk below this floor, or a broken `probe_start` calculation
    that clips an in-window match, would flip these to accepted (False)."""
    # 85-char synthetic full-U.S.C.-shaped citation, immediately followed
    # by whitespace and a parenthesized token -- exercises the
    # `_FULL_USC_CITATION_SUFFIX_RE` branch at (well) under half the
    # shipped 512-char window.
    citation = "42  U.S.C.  § 12345-6-7-8-9-10-11-12-13-14-15-16-17-18-19-20"
    assert 60 <= len(citation) <= 100, f"fixture drifted out of the intended 60-100 char band: {len(citation)}"
    # The citation must sit IMMEDIATELY before the marker token (only
    # whitespace between them) -- `_citation_or_xref_context` trims
    # whitespace back from `token_start` and anchors every probe's `\Z` at
    # that trimmed position, so any non-whitespace text between the
    # citation and the marker would place the citation outside the probe
    # window's anchor point, not just outside its reach.
    tail = f"Some introductory clause citing {citation} (A) "

    near_body = tail
    near_token_start = near_body.index("(A)")

    far_prefix = (_FILLER * (200_000 // len(_FILLER) + 1))[:200_000]
    far_body = far_prefix + tail
    far_token_start = far_body.index("(A)", len(far_prefix))

    for label, body, token_start in (
        ("near", near_body, near_token_start),
        ("far", far_body, far_token_start),
    ):
        identity, _trimmed_end = us_profile._citation_or_xref_context(body, token_start)
        assert identity == "full_usc", (
            f"[{label}] a realistic ~{len(citation)}-char full-U.S.C. citation "
            f"immediately before the marker token was NOT recognized as citation "
            f"context (got identity={identity!r}) -- the lookback window may have "
            f"been shrunk below what real corpus citations need, or `probe_start` "
            f"clipped an in-window match."
        )

        rejected = us_profile._is_citation_or_xref_context(
            body, token_start, token_start + 3, "parenthesized"
        )
        assert rejected is True, (
            f"[{label}] _is_citation_or_xref_context did not reject the token "
            f"immediately following a realistic full-U.S.C. citation."
        )
