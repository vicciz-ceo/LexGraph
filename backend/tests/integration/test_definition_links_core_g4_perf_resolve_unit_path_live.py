"""RED (work-count, live path) -- sprint 2026-08-10-core-g4-discriminator-perf.

Sibling of the unit-level `test_definition_links_core_g4_perf_bounded_
window.py`, which calls `_citation_or_xref_context` directly at isolated
positions. This module instead drives the REAL public entry point,
`JurisdictionProfile.resolve_unit_path` (the same seam every caller --
`resolve_unit_path`'s own docstring, the scoped-inline panel's
`_resolve_subsection_scope`, and the merge-tree pipeline -- goes through),
over a body with MANY marker tokens, and proves the discriminator's
bounded-window property holds when exercised through
`resolve_unit_path`'s own per-token loop (`us_profile.py:1638-1656`), not
just in isolation.

**Why this body is safe to run today.** `resolve_unit_path`'s loop calls
`_citation_or_xref_context` once per candidate token up to `char_offset`
(`us_profile.py:1654`), so total probe work today is O(tokens x average
position) -- quadratic in the token count for a body where tokens are
evenly spread. 220 tokens across ~98,000 characters keeps this module's
run time under a couple of seconds even on the UNBOUNDED-lookback code (this
is deliberately far smaller than the sprint contract's real 150-225KB
pathological rows, which the manager already measured at >30s each -- this
test only needs to prove the SHAPE of the defect, not reproduce its worst
case).

**Self-mock ban compliance:** `resolve_unit_path` is called live and
unpatched -- it is one of the three acceptance targets and is never
stubbed. Only the five suffix-regex objects it (transitively, via
`_citation_or_xref_context`) calls are wrapped, purely to record the
`(pos, endpos)` arguments each call actually used; the wrapper always
forwards to the real `.search`, so the discriminator's real answer, and
therefore `resolve_unit_path`'s real return value, is unchanged.

**Gate 2 grounding (`test_pathological_federal_row_probe_window_stays_
bounded`, below).** The synthetic tests above prove the SHAPE of the
defect; this one ties it to the sprint contract's own cited evidence: real
federal row `USC_T17_C1_S115` (150,551 bytes, measured 4.07s on the merged
tree, one of the three named rows in the contract's "Measured evidence"
table) -- extracted once from the pinned corpus into the committed fixture
`../fixtures/us_statutes/core_g4_perf_pathological_federal_row.json` (M-R107:
cited as evidence, not depended on for its content -- only its realistic
size/marker density matters here) rather than read live from the
HuggingFace cache at test time, matching every other fixture in this test
suite and keeping this test independent of any one machine's corpus
snapshot being present.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links import us_profile
from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article

_FEDERAL_ROW_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "core_g4_perf_pathological_federal_row.json"
)

_SUFFIX_RE_NAMES = (
    "_STRUCTURAL_UNIT_WORD_SUFFIX_RE",
    "_FULL_USC_CITATION_SUFFIX_RE",
    "_SECTION_CITATION_SUFFIX_RE",
    "_LONE_SECTION_CITATION_SUFFIX_RE",
    "_BARE_STATE_CODE_CITATION_SUFFIX_RE",
)

# Same generous-headroom bound as the sibling unit test -- see that module's
# docstring for the "40x over the longest real branch match" justification.
_MAX_SANE_WINDOW = 4096

_FILLER = "lorem ipsum dolor sit amet consectetur adipiscing elit "
_NUM_TOKENS = 220
_FILLER_REPEATS = 6


class _WindowRecorder:
    def __init__(self, pattern):
        self._pattern = pattern
        self.windows: list[tuple[int, int]] = []

    def search(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.search(string, pos, endpos)

    def match(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.match(string, pos, endpos)

    def fullmatch(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.fullmatch(string, pos, endpos)


def _many_marker_tokens_body() -> str:
    """A realistic-shaped body: plain filler prose (no citation/structural
    vocabulary, so every token is a genuine marker candidate) interspersed
    with `_NUM_TOKENS` parenthesized upper_alpha tokens, spread across
    ~98,000 characters -- many tokens at many document positions, exactly
    the shape the mandate names as the defect's multiplier (O(tokens x
    position))."""
    parts = []
    for i in range(_NUM_TOKENS):
        parts.append(_FILLER * _FILLER_REPEATS)
        parts.append(f"({chr(65 + (i % 26))}) ")
    return "".join(parts)


def test_resolve_unit_path_probe_window_stays_bounded_across_many_tokens():
    body = _many_marker_tokens_body()
    article = Article(number="1", heading="Definitions", body=body, chapter="1")
    profile = get_profile("US-FED")

    originals = {name: getattr(us_profile, name) for name in _SUFFIX_RE_NAMES}
    recorders = {name: _WindowRecorder(pattern) for name, pattern in originals.items()}
    for name, recorder in recorders.items():
        setattr(us_profile, name, recorder)
    try:
        profile.resolve_unit_path(article, char_offset=len(body))
    finally:
        for name, pattern in originals.items():
            setattr(us_profile, name, pattern)

    windows = [w for recorder in recorders.values() for w in recorder.windows]
    assert windows, "expected resolve_unit_path to have run at least one suffix probe"

    oversized = [w for w in windows if (w[1] - w[0]) > _MAX_SANE_WINDOW]
    assert not oversized, (
        f"resolve_unit_path's live per-token discriminator loop scales with "
        f"document position: {len(oversized)} of {len(windows)} probe(s) across "
        f"{_NUM_TOKENS} tokens searched a window wider than {_MAX_SANE_WINDOW} "
        f"chars (largest window={max(w[1] - w[0] for w in windows)}, body "
        f"length={len(body)}) -- the lookback is unbounded on the live path, "
        f"not just in the isolated unit test."
    )


def test_resolve_unit_path_total_probe_work_grows_linearly_not_quadratically_with_tokens():
    """Same shape at half the token count: total summed probe work
    (`sum(endpos - pos)` across every suffix-regex call) must scale roughly
    LINEARLY with the number of tokens once the lookback is bounded (each
    token then costs O(1) probe work). Today it is quadratic: halving the
    token count roughly QUARTERS total work (both token count and average
    per-token window halve), not merely halves it. This is the
    complexity-ratio check from the sprint contract's fallback shape,
    included here as a second, independent angle on the same defect."""
    full_body = _many_marker_tokens_body()
    half_tokens = _NUM_TOKENS // 2
    half_parts = []
    for i in range(half_tokens):
        half_parts.append(_FILLER * _FILLER_REPEATS)
        half_parts.append(f"({chr(65 + (i % 26))}) ")
    half_body = "".join(half_parts)

    def _total_probe_work(body: str) -> int:
        article = Article(number="1", heading="Definitions", body=body, chapter="1")
        profile = get_profile("US-FED")
        originals = {name: getattr(us_profile, name) for name in _SUFFIX_RE_NAMES}
        recorders = {
            name: _WindowRecorder(pattern) for name, pattern in originals.items()
        }
        for name, recorder in recorders.items():
            setattr(us_profile, name, recorder)
        try:
            profile.resolve_unit_path(article, char_offset=len(body))
        finally:
            for name, pattern in originals.items():
                setattr(us_profile, name, pattern)
        return sum(
            (end - pos)
            for recorder in recorders.values()
            for (pos, end) in recorder.windows
        )

    full_work = _total_probe_work(full_body)
    half_work = _total_probe_work(half_body)

    assert full_work > 0, "expected at least some discriminator probe work on full body"
    assert half_work > 0, "expected at least some discriminator probe work on half body"

    # A bounded (O(1)-per-token) lookback gives each token roughly the SAME
    # probe budget, so halving the token count should roughly halve total
    # work -- generously, no more than a 3x reduction (vs. the ~4x this
    # defect actually produces, since both the token count and the average
    # window halve together under O(tokens x position)).
    assert half_work * 3 >= full_work, (
        f"resolve_unit_path's total discriminator probe work is superlinear "
        f"in token count: {_NUM_TOKENS} tokens -> {full_work} total probe chars; "
        f"{half_tokens} tokens -> {half_work} total probe chars "
        f"(ratio={full_work / half_work if half_work else float('inf'):.2f}x "
        f"for a 2x token increase) -- consistent with O(tokens x position), "
        f"not the O(tokens) a bounded lookback would produce."
    )


def test_pathological_federal_row_probe_window_stays_bounded():
    """Gate 2, grounded in the sprint contract's own named evidence: the
    LAST marker token in the real `USC_T17_C1_S115` row (150,551 bytes)
    must not force a suffix probe to search a window wider than
    `_MAX_SANE_WINDOW`. Calls `_citation_or_xref_context` directly (not the
    full per-token loop) at that one late position -- proving the window is
    bounded is what makes the FULL row (all ~1,165 tokens) tractable; this
    test does not itself wait through the >30s the unbounded lookback would
    take to process the whole row, since a bounded probe window is exactly
    what removes that wait.
    """
    rows = json.loads(_FEDERAL_ROW_FIXTURE.read_text(encoding="utf-8"))
    row = next(r for r in rows if r["act_id"] == "USC_T17_C1_S115")
    text = row["text"]
    assert len(text) == 150_551, "fixture drifted from the contract's measured evidence"

    tokens = us_profile._iter_us_unit_marker_tokens(text)
    assert tokens, "expected at least one marker token in the real row"
    last_start, _end, _token = tokens[-1]

    originals = {name: getattr(us_profile, name) for name in _SUFFIX_RE_NAMES}
    recorders = {name: _WindowRecorder(pattern) for name, pattern in originals.items()}
    for name, recorder in recorders.items():
        setattr(us_profile, name, recorder)
    try:
        us_profile._citation_or_xref_context(text, last_start)
    finally:
        for name, pattern in originals.items():
            setattr(us_profile, name, pattern)

    windows = [w for recorder in recorders.values() for w in recorder.windows]
    assert windows, "expected at least one suffix-regex probe to run at the last marker token"
    oversized = [w for w in windows if (w[1] - w[0]) > _MAX_SANE_WINDOW]
    assert not oversized, (
        f"real evidenced row USC_T17_C1_S115 (150,551 bytes, contract-measured "
        f"4.07s on the merged tree) still shows an unbounded discriminator "
        f"window at its last marker token (position {last_start}): "
        f"{len(oversized)} of {len(windows)} probe(s) exceeded "
        f"{_MAX_SANE_WINDOW} chars (largest={max(w[1] - w[0] for w in windows)})."
    )
