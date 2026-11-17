"""The sanitizer's fixpoint loop is capped, so hostile markup cannot burn CPU.

`sanitize_for_storage` re-runs `_sanitize_once` until its output stops
changing (rulings R13, R14/R16(a)). Each pass peels one raw-text wrapper, so a
field of nested `<title>`, `<textarea>`, `<xmp>` or `<script>` tags at the
100,000-character cap used to take up to ~14,000 passes and ~8 s of CPU, and a
create request sanitizes two such fields. The loop is now capped at
`_MAX_SANITIZE_PASSES`; input that needs more fails closed (""), exactly as the
loop's existing termination guard always did.

These tests pin both halves: the pathological input is cheap and fails closed,
and the cap changes nothing for any input that converges within it (compared
against an uncapped reference over the sanitizer test strings and a seeded
random corpus of hostile token mixes).
"""

from __future__ import annotations

import ast
import random
import time
from pathlib import Path

import pytest

from app.services import validation
from app.services.validation import _MAX_SANITIZE_PASSES, sanitize_for_storage

_TESTS = Path(__file__).resolve().parents[1]

# A whole field at the 100,000-character cap; generous for slow CI runners
# (about 0.15 s locally; the uncapped loop took 1-8 s per field).
_BUDGET_SECONDS = 2.0


def _uncapped_reference(text: str) -> tuple[str, int]:
    """The loop as it was before the cap: (fixpoint output, passes used)."""
    current = text
    for passes in range(1, len(text) + 3):
        sanitized = validation._sanitize_once(current)
        if sanitized == current:
            return sanitized, passes
        current = sanitized
    return "", len(text) + 2


@pytest.mark.parametrize(
    "hostile",
    [
        pytest.param("<title>" * 14_285, id="title"),
        pytest.param("<textarea>" * 10_000, id="textarea"),
        pytest.param("<title><textarea>" * 5_882, id="alternating"),
        pytest.param("<xmp>" * 20_000, id="xmp"),
        pytest.param("<script>" * 12_500, id="script"),
        pytest.param("law <title>" * 9_090, id="text-between-wrappers"),
    ],
)
def test_nested_raw_text_wrappers_at_the_cap_fail_closed_quickly(hostile: str) -> None:
    assert len(hostile) <= 100_000
    started = time.perf_counter()
    result = sanitize_for_storage(hostile)
    elapsed = time.perf_counter() - started
    assert result == ""
    assert elapsed < _BUDGET_SECONDS, f"sanitizing took {elapsed:.2f}s"


def test_a_wrapper_chain_within_the_cap_still_converges_to_the_same_text() -> None:
    within = "<title>" * 200 + "Clause 8.4 applies."
    expected, passes = _uncapped_reference(within)
    assert passes <= _MAX_SANITIZE_PASSES
    assert sanitize_for_storage(within) == expected


def test_a_wrapper_chain_beyond_the_cap_fails_closed() -> None:
    beyond = "<title>" * (_MAX_SANITIZE_PASSES + 50) + "Clause 8.4 applies."
    assert sanitize_for_storage(beyond) == ""


def _test_strings() -> list[str]:
    found: list[str] = []
    for name in (
        "unit/test_validation.py",
        "unit/test_validation_length_cap.py",
        "integration/test_hostile_input.py",
    ):
        path = _TESTS / name
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 20_000:
                found.append(node.value)
    return found


_TOKENS = [
    "<title>", "</title>", "<textarea>", "</textarea>", "<iframe>", "</iframe>", "<xmp>", "</xmp>",
    "<noembed>", "</noembed>", "<noframes>", "</noframes>", "<plaintext>", "<script>", "</script>",
    "<style>", "</style>", "<img src=x onerror=alert(1)", "<img src=x onerror=alert(1)>", "<b>", "</b>",
    "<!--", "-->", "<!x>", "<?p?>", "<![CDATA[", "]]>", "&amp;", "&", "&#160a", "<", ">", " ", "\n",
    "Clause 8.4", " a < b ", "x > y", "'", '"', "=", "/", '<a href="', '">', "</",
    "<svg onload=alert(2) ", "<TITLE>", "</TiTlE >", "<title/>", "<textarea a=1>", "text", "ס",
    "<x", "<x y=", "</title", "<script type=x>", "</script ", "<math>", "<template>", "law ",
]


def _random_corpus(count: int) -> list[str]:
    rng = random.Random(20261117)
    return ["".join(rng.choice(_TOKENS) for _ in range(rng.randint(1, 40))) for _ in range(count)]


def test_the_cap_changes_no_output_that_converges_within_it() -> None:
    corpus = _test_strings() + _random_corpus(4_000)
    assert len(corpus) > 4_000
    for text in corpus:
        expected, passes = _uncapped_reference(text)
        assert passes <= _MAX_SANITIZE_PASSES, f"{text!r} needs {passes} passes"
        assert sanitize_for_storage(text) == expected, f"output changed for {text!r}"
