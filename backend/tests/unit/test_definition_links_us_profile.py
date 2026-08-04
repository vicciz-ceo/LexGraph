"""RED tests for the US jurisdiction profile (sprint 2026-08-02-us-state-law,
director decision #1, gates G2 "a real US statute parses", G3 "English
term linking works", G4 "US citations are recognised").

`get_profile("US-DE")` (and any other `US-*`/`US-FED` code) does not exist
yet -- RED via the registry lookup failing (`ImportError` for
`app.definition_links.profiles` itself if the G1 seam item hasn't landed
either, or a `KeyError`/`ValueError` from `get_profile` if the seam exists
but no US profile is registered -- either is a legitimate RED signal for
"this feature does not exist yet").

Fixture data: REAL rows from `vaquill/open-us-law`'s `us_de_statutes.parquet`
(ruling R6), committed at `backend/tests/fixtures/us_statutes/de_sample_rows.json`
-- see that file's sibling `README.md` for full provenance and why each row
was picked. Loaded as JSON here specifically so this test needs no
`pyarrow`/`huggingface_hub` install.

Design calls this test pins for the US profile (evidence: the real fixture
rows themselves, read directly by the Planner):

  - `is_definitions_heading` must tolerate the REAL scrape-artifact noise
    present in EVERY Delaware `section_title` value (`"§ Â\r\n innerhalb
    796. Definitions."` -- mojibake `Â`, a raw CRLF, leading whitespace,
    all BEFORE the actual number+heading) -- a heading matcher that only
    handles a clean `"796. Definitions"`-shaped string will fail on 100%
    of this real dataset's rows. It must therefore match on a
    substring/contains basis (unlike Hebrew's `sections.py`, which
    anchors at the START of an already marker-stripped heading) rather
    than assume clean input.
  - `find_term_uses` uses ordinary `\\b`-word-boundary matching (no
    Hebrew-style prefix-letter surface-form expansion) and must NOT match
    a defined term as a substring of a longer word (e.g. `"Affiliate"`
    inside `"Affiliates"`/`"disaffiliate"`).
  - `detect_cross_law_derivations` recognizes English defining idioms
    (`"has the meaning specified in"`, `"as defined in"`, at minimum --
    real fixture text uses the former, not `"means"`) followed by a law
    reference, and EXCLUDES same-document/same-chapter internal
    references (`"...of this chapter"`) from being reported as cross-law,
    mirroring Hebrew derivation.py's `_BESAIF_RE` same-law exclusion
    philosophy -- never a fabricated resolution (M5's discipline, ported):
    an unresolved federal/statutory reference is still emitted, with
    `target_law_id=None`.
  - `find_citations` is a NEW capability with no Hebrew analog (G4's gate
    text names bare citations -- "§ 101", "15 U.S.C. § 1" -- as
    something that must be "detected ... rather than silently dropped"
    even with NO defining trigger phrase nearby): every profile exposes
    `.find_citations(text) -> list[str]` (matched citation substrings);
    the Hebrew (`"IL"`) profile trivially returns `[]` (no citation
    grammar in scope for Hebrew this sprint) -- covered as a companion
    assertion in `test_definition_links_profiles.py`'s existing
    `il_profile` fixture usage is NOT required to change for this reason;
    that file is untouched by this item.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# RED: no US profile is registered yet (ImportError if `profiles` itself
# doesn't exist -- G1 not yet landed -- or KeyError/ValueError if it does
# exist but "US-DE" isn't a registered code yet).
from app.definition_links.profiles import get_profile

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def us_profile():
    return get_profile("US-DE")


@pytest.fixture()
def de_rows():
    return _load_fixture_rows()


# --- G2: Definitions-heading detection --------------------------------------


def test_us_profile_recognizes_the_real_de_definitions_heading_despite_scrape_noise(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    assert "Definitions" in row["section_title"]  # sanity: fixture really has this word
    assert us_profile.is_definitions_heading(row["section_title"]) is True


def test_us_profile_recognizes_the_singular_definition_heading_variant(us_profile, de_rows):
    row = de_rows["STATE_DE_T31_C52_SIII_S5227"]
    assert us_profile.is_definitions_heading(row["section_title"]) is True


def test_us_profile_does_not_flag_an_ordinary_heading_as_a_definitions_section(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T29_C60A_S6060"]
    assert us_profile.is_definitions_heading(row["section_title"]) is False


@pytest.mark.parametrize(
    "heading",
    [
        "Definitions",
        "Definitions.",
        "Definitions and Interpretation",
        "§ 101. Definitions",
        "Section 101. Definitions.",
    ],
)
def test_us_profile_recognizes_clean_synthetic_definitions_headings(us_profile, heading):
    assert us_profile.is_definitions_heading(heading) is True


# --- G3: English word-boundary term matching --------------------------------


def test_us_profile_find_term_uses_matches_a_real_defined_term_in_real_body_text(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    matches = us_profile.find_term_uses("Affiliate", row["text"])
    assert len(matches) >= 1


def test_us_profile_find_term_uses_does_not_false_match_inside_a_longer_word(us_profile):
    text = 'The "Affiliate" definition applies. Affiliates and disaffiliated parties are different concepts.'
    matches = us_profile.find_term_uses("Affiliate", text)
    matched_spans = [(m.start(), m.end()) for m in matches]
    for start, end in matched_spans:
        # Every match must be the bare word "Affiliate", never a substring
        # of "Affiliates" or "disaffiliated".
        assert text[start:end] == "Affiliate"
        before = text[start - 1] if start > 0 else " "
        after = text[end] if end < len(text) else " "
        assert not before.isalpha()
        assert not after.isalpha()


def test_us_profile_find_term_uses_matches_a_multi_word_term(us_profile, de_rows):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    matches = us_profile.find_term_uses("Branch office", row["text"])
    assert len(matches) >= 1


# --- G4: US citation grammar -------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_substring",
    [
        ("as defined in Section 5, the term applies.", "Section 5"),
        ("The threshold set by § 101 controls.", "§ 101"),
        ("Compliance follows 15 U.S.C. § 1 in all cases.", "15 U.S.C. § 1"),
    ],
)
def test_us_profile_find_citations_detects_named_reference_forms(
    us_profile, text, expected_substring
):
    citations = us_profile.find_citations(text)
    assert any(expected_substring in c for c in citations)


def test_us_profile_find_citations_detects_the_real_fixtures_federal_citation(us_profile, de_rows):
    row = de_rows["STATE_DE_T29_C60A_S6060"]
    citations = us_profile.find_citations(row["text"])
    assert any("U.S.C." in c for c in citations)


def test_us_profile_detect_cross_law_derivations_resolves_a_federal_cross_reference(
    us_profile, de_rows
):
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    entry_text = (
        '"Insured depository institution" has the meaning specified in 12 U.S.C. § 1813(c).'
    )
    edges = us_profile.detect_cross_law_derivations(
        entry_text, source_term="Insured depository institution", known_law_titles={}
    )
    assert len(edges) >= 1
    assert any("1813" in edge.matched_text or "U.S.C." in edge.matched_text for edge in edges)
    # M5's discipline, ported: unresolved (no matching known_law_titles entry)
    # is still emitted, never dropped, target_law_id stays None.
    assert all(edge.target_law_id is None for edge in edges)


def test_us_profile_detect_cross_law_derivations_excludes_a_same_chapter_reference(
    us_profile, de_rows
):
    """"Branch office" ... "has the meaning specified in § 770 OF THIS
    CHAPTER" -- an internal, same-document reference must NOT be reported
    as a cross-law derivation (mirrors Hebrew derivation.py's `_BESAIF_RE`
    same-law exclusion)."""
    entry_text = '"Branch office" has the meaning specified in § 770 of this chapter.'
    edges = us_profile.detect_cross_law_derivations(
        entry_text, source_term="Branch office", known_law_titles={}
    )
    assert edges == []


# --- G2 (continued): extracting DEFINED TERMS out of a located US
# Definitions section. NOT one of the 4 modules the director's decision
# text named ("sections/matcher/derivation/normalize") -- but G2's plain-
# language gate ("extracts its terms") is unsatisfiable without it: the
# real fixture's Definitions body is a numbered-paragraph list
# (`"(1) \"Term\" has the meaning specified in ..."`), structurally
# nothing like Hebrew's `:-`-prefixed entry markers (`extract.py`'s
# `_ENTRY_START_RE`). The Planner extends the profile surface to
# `.extract_definitions_from_section(text) -> list[DefinitionCandidate]`
# by necessity -- flagged as a deviation from the director's literal
# 4-module list in the sprint contract, not a silent scope change.


def test_us_profile_extracts_every_defined_term_from_the_real_definitions_section(
    us_profile, de_rows
):
    from app.definition_links.extract import DefinitionCandidate

    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    candidates = us_profile.extract_definitions_from_section(row["text"], scope="law-wide")
    assert all(isinstance(c, DefinitionCandidate) for c in candidates)

    all_terms = {term for c in candidates for term in c.terms}
    assert "Affiliate" in all_terms
    assert "Branch office" in all_terms
    assert "Insured depository institution" in all_terms
    assert len(candidates) == 3


# --- Sprint 2026-08-04-defs-core-scope, manager ruling M8(b) ------------
#
# `find_term_uses` uses `\b`-word-boundary matching but is case-SENSITIVE
# (`re.compile(r"\b" + re.escape(term) + r"\b")`, no `re.IGNORECASE`).
# Real rows re-mention a capitalized defined term in lowercase later in
# the same law (`STATE_GA_T7_C8_S7-8-1` defines "Access area",
# `STATE_GA_T7_C8_S7-8-3` uses "access area" -- exact fact pattern from
# the ruling; this Planner has no local corpus copy to pull the byte-
# real rows from, see the panel log). Fix must be scoped narrowly
# (case-fold the literal term only, still word-boundary-anchored -- never
# a fuzzy/substring match) per the seam spec's stated exposure-limiting
# rationale.


def test_us_profile_find_term_uses_matches_a_lowercase_mention_of_a_capitalized_defined_term():
    """M8(b): 'Access area' (as defined) must also match its later
    lowercase mention 'access area' in running text -- today's exact-case
    `\\b`-boundary regex misses it entirely."""
    from app.definition_links.us_profile import find_term_uses

    text = 'The "Access area" shall be maintained. Later, the access area must be inspected annually.'
    matches = find_term_uses("Access area", text)
    matched_texts = {text[m.start() : m.end()] for m in matches}
    assert "access area" in matched_texts, (
        f"expected a case-insensitive word-boundary match on the lowercase "
        f"mention; got only {matched_texts!r}"
    )


def test_us_profile_find_term_uses_case_insensitive_match_still_respects_word_boundaries():
    """The M8(b) fix must stay word-boundary-anchored even case-folded --
    'Access area' must NOT match as a substring inside a longer word run
    (guards against widening the fix into a fuzzy/substring matcher,
    which the seam spec explicitly rules out as the false-positive risk
    to avoid)."""
    from app.definition_links.us_profile import find_term_uses

    text = "Subaccess areatransition zones are unrelated to the defined term."
    matches = find_term_uses("Access area", text)
    assert matches == []


def test_il_hebrew_find_term_uses_is_unaffected_by_the_m8b_case_fold_fix():
    """Explicit proof requirement (M8(b), binding): case-folding
    `us_profile.find_term_uses` must not disturb Hebrew's OWN, separate
    `matcher.find_term_uses` -- different function, different module,
    verified directly rather than merely assumed 'probably inert because
    Hebrew is caseless'. This test alone is not the full proof (the FULL
    IL suite passing unchanged is -- see the Stage B report's run tail);
    it pins the specific claim that the two functions remain independent."""
    from app.definition_links import matcher as hebrew_matcher
    from app.definition_links import us_profile

    assert hebrew_matcher.find_term_uses is not us_profile.find_term_uses
    text = "מאגר מידע נוצר בהתאם לחוק זה."
    before = [(m.start(), m.end()) for m in hebrew_matcher.find_term_uses("מאגר מידע", text)]
    # Calling the US profile's function (which M8(b) modifies) must have
    # no observable effect on the Hebrew function's own behavior.
    us_profile.find_term_uses("Access area", "irrelevant english text")
    after = [(m.start(), m.end()) for m in hebrew_matcher.find_term_uses("מאגר מידע", text)]
    assert before == after


# --- Sprint 2026-08-04-defs-core-scope, manager ruling M12 --------------
#
# `find_citations` (`_CITATION_PATTERNS`/`_SECTION_WORD_RE`) has two
# verified defects (reproduced directly by this Planner,
# `backend/.venv/bin/python`, before writing these tests -- see the panel
# log): decimal section numbers truncate to a WRONG, real, existing
# section (worse than a miss); state-code citation shapes (`ORS 153.005`)
# are invisible. Expected values below are copied VERBATIM from
# `claude/defs-us-multiterm@f1011f0`'s
# `test_definition_links_e1_pointer_reference_capture.py` (read-only
# fetch, not checked out) so one core fix turns both test sets green.


def test_us_profile_find_citations_does_not_truncate_a_decimal_section_number():
    """Defect (ii), pinned as an explicit WRONG-target equality assertion
    (not membership) -- the failure mode is a citation to a DIFFERENT,
    real section, not merely an absent one."""
    from app.definition_links.us_profile import find_citations

    citations = find_citations('"Governmental body" has the meaning assigned by Section 552.003.')
    assert citations == ["Section 552.003"], (
        f"expected the WHOLE decimal section number; got {citations!r} -- "
        f"`_SECTION_WORD_RE` stops at the decimal point, silently "
        f"truncating to a citation for a DIFFERENT real section."
    )


def test_us_profile_find_citations_recognizes_a_state_code_citation_shape():
    """Defect (i): a generic `<CODE> <n>.<n>` state-code shape (covering
    Oregon's ORS and similarly-shaped codes) must be recognized by
    baseline, not silently invisible."""
    from app.definition_links.us_profile import find_citations

    citations = find_citations(
        '“Enforcement officer” has the meaning given that term in ORS 153.005 (Definitions) .'
    )
    assert citations == ["ORS 153.005"]


def test_us_profile_find_citations_still_detects_the_six_term_parent_clause_citation():
    """Same wrong-target shape, on the six-term TX shared parent clause
    (`claude/defs-us-multiterm`'s
    `test_tx_parent_clause_2001_003_citation_is_truncated_to_a_wrong_target`)
    -- pinned here too so core's fix is verified against both real rows,
    not just one."""
    from app.definition_links.us_profile import find_citations

    citations = find_citations(
        "The following terms have the meanings assigned by Section 2001.003:"
    )
    assert citations == ["Section 2001.003"]


def test_il_hebrew_find_citations_is_unaffected_by_the_m12_baseline_fix():
    """C5/IL-unaffected proof for the citation-grammar fix, mirroring the
    same discipline as the M8(b) proof above -- `HebrewProfile.
    find_citations` stays trivially `[]` (v1's documented behavior)
    regardless of what baseline gains for US."""
    from app.definition_links.profiles import HebrewProfile

    profile = HebrewProfile()
    assert profile.find_citations("כל טקסט לדוגמה עם Section 552.003 בתוכו") == []
