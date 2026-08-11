"""RED integration test -- sprint 2026-08-10-green-the-suite (second-pass
Planner). NV UCC's `"TERM," (as distinguished from|except as used in)
"excluded phrase(s)," means ...` double-quote disambiguation idiom loses the
real definiendum under its correct name.

Classification: FIX-class, not xfail-class (D-RECALL-FP) -- this is an
anchor LOSS, not a capture-quality defect: the real term is entirely absent
from `by_term` today, replaced by a spuriously-named entry (the excluded
phrase nearest "means") carrying the real term's own definition text under
the WRONG name. Tracked at https://github.com/vicciz-ceo/LexGraph/issues/25.

Live path: `ingest_us_statute_rows` -> `run_definition_linking` -> persisted
`Definition` rows, the same pattern as the `test_us_markers_ext_b_*` files --
this exercises the real, shipped `extract_quote_anchored_entries` engine on
post-ingest body text, not a stubbed call.

M-R107: the expected (term, definition-content) pairs below are DERIVED from
each fixture row's own raw source text by `_IDIOM_RE`, a structural parser
for the disambiguation shape above -- not a hardcoded list of the terms
named in issue #25. The 7 terms issue #25 names (Agreement, Contract, Party,
Account, Accounting, Assignee, Record) are what this parser happens to find
on these two real rows today; they are evidence of the defect, not the spec
asserted against. A fix that repairs the general shape passes this test
regardless of whether NV amends these rows' wording later, and the test
would also catch the defect on a future row this parser matches that nobody
has spot-checked by hand.

Fixture: `us_markers_ext_c25_nv_ucc_except_as_used_in.json` -- the two full,
verbatim real rows (`STATE_NV_T8_C104_S104.1201`, `STATE_NV_T8_C104_S104.9102`)
pulled directly from `us_nv_statutes.parquet` (vaquill/open-us-law), same
schema shape as `us_markers_ext_b_nv.json`."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_ext_c25_nv_ucc_except_as_used_in.json"
)

# Structural parser for NV UCC's double-quoted disambiguation idiom:
#   "TERM," (as distinguished from|except as used in) "excluded...," means ...
# Matches only when the exclusion clause immediately follows the
# definiendum's OWN closing quote (comma/whitespace only in between) and
# resolves at the NEAREST following "means" -- the same "means" the real
# engine anchors its own entry boundary on. This deliberately does NOT match
# shapes like `"Original debtor" means, except as used in subsection 3 of
# NRS 104.9310, ...` (no quoted exclusion, and "means" precedes "except as
# used in" rather than following it) -- those are not this defect.
_IDIOM_RE = re.compile(
    r"“\s*(?P<term>[^“”]+?)\s*,?\s*”\s*,?\s*"
    r"(?:as distinguished from|except as used in)\s*"
    r"(?P<excluded_span>.*?)"
    r"\bmeans\b",
    re.DOTALL,
)

_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


def _derive_expected(text: str) -> list[tuple[str, str]]:
    """Structurally parse `text` for the disambiguation idiom. Returns
    (real_term, content_probe) pairs -- `content_probe` is a verbatim
    ~50-char slice of the row's OWN text immediately after "means", used to
    confirm the real term's captured content is the real definition, not
    just that the key happens to exist."""
    expected: list[tuple[str, str]] = []
    for m in _IDIOM_RE.finditer(text):
        term = _norm(m.group("term"))
        probe = _norm(text[m.end() : m.end() + 50])
        expected.append((term, probe))
    return expected


def _load_row(act_id: str) -> dict:
    rows = {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}
    return rows[act_id]


def _ingest_and_link(db_session, matter, *, act_id: str, row: dict) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=f"NV UCC except-as-used-in probe ({act_id})",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-NV",
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    return [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]


def test_nv_ucc_fixtures_headings_are_recognized_as_definitions_sections():
    """Sanity: both fixture rows already have a recognized Definitions
    heading -- the defect below is purely a boundary/naming mistake inside
    an already-reached section, not a heading-detection miss."""
    for act_id in ("STATE_NV_T8_C104_S104.1201", "STATE_NV_T8_C104_S104.9102"):
        row = _load_row(act_id)
        assert is_definitions_heading(row["section_title"]) is True, (
            f"{act_id}: {row['section_title']!r} must already be recognized"
        )


def test_idiom_parser_finds_the_disambiguation_shape_on_both_fixture_rows():
    """Sanity on the test's OWN structural parser, not the extraction
    engine: guards against the RED tests below silently going vacuous if a
    future fixture edit removes the disambiguation idiom this issue is
    about."""
    for act_id in ("STATE_NV_T8_C104_S104.1201", "STATE_NV_T8_C104_S104.9102"):
        row = _load_row(act_id)
        expected = _derive_expected(row["text"])
        assert len(expected) >= 1, (
            f"{act_id}: fixture text no longer contains the 'except as used "
            "in'/'as distinguished from' double-quote idiom this issue is "
            "about -- the test below would be vacuous"
        )


def _assert_real_terms_survive_disambiguation(db_session, matter_with_users, act_id: str) -> None:
    row = _load_row(act_id)
    expected = _derive_expected(row["text"])
    assert expected, f"{act_id}: structural parser found no disambiguation idiom instances"

    definitions = _ingest_and_link(db_session, matter_with_users, act_id=act_id, row=row)
    by_term = {t: d for d in definitions for t in d.terms}

    for term, content_probe in expected:
        assert term in by_term, (
            f"{act_id}: real term {term!r} is missing from the real pipeline's output "
            f"({sorted(by_term)!r}) -- lost under its correct name by the 'except as "
            "used in'/'as distinguished from' double-quote disambiguation defect "
            "(issue #25)"
        )
        dtext = _norm(by_term[term].definition_text)
        assert content_probe in dtext, (
            f"{act_id}: {term!r} is captured but its definition_text does not contain "
            f"the real content {content_probe!r} that structurally follows this term's "
            f"own 'means' in the source -- got {dtext!r}"
        )


def test_nv_ucc_104_1201_real_terms_survive_except_as_used_in_disambiguation(
    db_session, matter_with_users
):
    """`STATE_NV_T8_C104_S104.1201` (NV UCC Article 1, general definitions):
    the real pipeline must produce Agreement/Contract/Party-shaped terms (as
    derived from the row's own text) under their correct names, not lose
    them to the `as distinguished from "excluded-phrase,"` aside.

    sprint 2026-08-10-green-the-suite (second pass): confirmed live -- today
    the real pipeline produces 0 of these terms; instead the excluded phrase
    from each pair (e.g. 'contract ,') is captured as its own spurious entry
    carrying the real term's definition text. Tracked at
    https://github.com/vicciz-ceo/LexGraph/issues/25."""
    _assert_real_terms_survive_disambiguation(
        db_session, matter_with_users, "STATE_NV_T8_C104_S104.1201"
    )


def test_nv_ucc_104_9102_real_terms_survive_except_as_used_in_disambiguation(
    db_session, matter_with_users
):
    """`STATE_NV_T8_C104_S104.9102` (NV UCC Article 9, definitions and index
    of definitions): the real pipeline must produce Account/Accounting/
    Assignee/Record-shaped terms (as derived from the row's own text) under
    their correct names, not lose them to the `except as used in
    "excluded-phrase(s),"` aside.

    sprint 2026-08-10-green-the-suite (second pass): confirmed live -- today
    the real pipeline produces 0 of these terms; instead the LAST excluded
    phrase in each list (e.g. 'statement of account', 'record owner,') is
    captured as its own spurious entry carrying the real term's definition
    text. Tracked at https://github.com/vicciz-ceo/LexGraph/issues/25."""
    _assert_real_terms_survive_disambiguation(
        db_session, matter_with_users, "STATE_NV_T8_C104_S104.9102"
    )


# --- Regression coverage: the excluded-phrase artifact returning ----------
#
# green-the-suite QA cycle (anti-gaming/regression-coverage requirement):
# `_assert_real_terms_survive_disambiguation` above only checks the REAL
# term is present and correct -- it does not check that the EXCLUDED phrase
# (the thing issue #25's own defect wrongly captured as its own spurious
# entry) has actually stopped being captured. A future regression that
# broke the bridge's own `excluded_spans` bookkeeping (see
# `us_markers_boundary.extract_quote_anchored_entries`'s main loop) could
# reintroduce the spurious entry ALONGSIDE the now-also-correct real term,
# and the tests above would keep passing -- this guard closes that gap.
_NORM_WS_RE = re.compile(r"\s+")


def _excluded_phrases(text: str) -> list[str]:
    """The exact excluded-phrase strings issue #25's own defect used to
    capture as spurious entries: the LAST quoted phrase inside each
    disambiguation clause's own excluded span, normalized/comma-stripped
    the same way a real captured term would be. Derived structurally from
    the row's own text (M-R107), not a hardcoded list."""
    phrases = []
    for m in _IDIOM_RE.finditer(text):
        quotes = re.findall(r"“([^“”]+)”", m.group("excluded_span"))
        if quotes:
            phrases.append(_norm(quotes[-1]).removesuffix(",").strip())
    return phrases


def _assert_excluded_phrases_are_not_their_own_spurious_entries(
    db_session, matter_with_users, act_id: str
) -> None:
    row = _load_row(act_id)
    excluded = _excluded_phrases(row["text"])
    assert excluded, f"{act_id}: structural parser found no excluded phrases to check"

    definitions = _ingest_and_link(db_session, matter_with_users, act_id=act_id, row=row)
    by_term = {t: d for d in definitions for t in d.terms}

    for phrase in excluded:
        assert phrase not in by_term, (
            f"{act_id}: the excluded phrase {phrase!r} is captured as its OWN "
            f"spurious entry ({by_term[phrase].definition_text!r}) -- the "
            "except-as-used-in/as-distinguished-from bridge (issue #25) has "
            "regressed and stopped consuming this exclusion clause"
        )


def test_nv_ucc_104_1201_excluded_phrases_are_not_their_own_spurious_entries(
    db_session, matter_with_users
):
    """Regression guard: none of `STATE_NV_T8_C104_S104.1201`'s own excluded
    phrases (`contract`, `agreement`, `third party` -- the exact artifacts
    issue #25's defect used to produce) may reappear as their own top-level
    `Definition` once the real term itself is also correctly captured."""
    _assert_excluded_phrases_are_not_their_own_spurious_entries(
        db_session, matter_with_users, "STATE_NV_T8_C104_S104.1201"
    )


def test_nv_ucc_104_9102_excluded_phrases_are_not_their_own_spurious_entries(
    db_session, matter_with_users
):
    """Regression guard: none of `STATE_NV_T8_C104_S104.9102`'s own excluded
    phrases (`statement of account`, `accounting for`, `assignee for
    benefit of creditors`, `record owner`) may reappear as their own
    top-level `Definition` once the real terms are also correctly
    captured."""
    _assert_excluded_phrases_are_not_their_own_spurious_entries(
        db_session, matter_with_users, "STATE_NV_T8_C104_S104.9102"
    )
