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


# --- Sprint 2026-08-04-defs-core-scope, QA-fail cycle 2, item I10, director
# --- ruling D-CF -------------------------------------------------------------
#
# D-CF (binding, program doc + panel log Round 17): case-folding STAYS (I6's
# `re.IGNORECASE` fix is not reverted) but gains a structural-context guard
# -- a case-fold match is SUPPRESSED where the hit sits inside a structural-
# reference pattern, i.e. a unit word (division/part/title/...) immediately
# followed by a numbering token ("division (ii)", "part (a)", "title 5").
# The defect: a statute defines "Division" as a term (real, common shape --
# an independent corpus scan by this Planner found 905 real US rows genuinely
# defining "Division", e.g. as an agency name); case-folding then makes every
# ordinary STRUCTURAL cross-reference like "...pursuant to this division (i)
# ..." match as a USE of that defined term. Those are structural navigation
# references, not term uses.
#
# Fixture material (program rule prior-R6: no test may read the corpus) --
# REAL, byte-for-byte vendored rows, `backend/tests/fixtures/us_statutes/
# d_cf_structural_reference_rows.json` (see that directory's README.md for
# full provenance), measured directly by this Planner against the real
# `vaquill/open-us-law` corpus (105 parquet files) before writing any
# assertion below -- verified today's (pre-guard) `find_term_uses` output on
# each real row first, so every expected value below reflects real, observed
# behavior, not a guess:
#
#   - `STATE_AL_T41_C10_S41-10-592` (Alabama): "...bonds issued pursuant to
#     this division (i) shall be issued..." -- ONE real, genuine lowercase
#     "division (i)" structural cross-reference, no other "division"/
#     "Division" occurrence anywhere in the row.
#   - `STATE_IL_C35_A505_S13a` (Illinois): "...comprised of 2 parts. Part (a)
#     shall be at the rate... Part (b) shall be at the rate..." -- TWO real
#     "Part (a)"/"Part (b)" structural cross-references, no other "Part"/
#     "part" occurrence anywhere in the row.
#   - `STATE_AK_T6_C06.45_S06.45.160` (Alaska): "...insurance obtained under
#     Title 1 of the National Housing Act..." -- ONE real "Title 1" bare-
#     number structural reference (D-CF's own named "title 5" shape, same
#     pattern, different number), no other "Title"/"title" occurrence.
#   - `STATE_AR_T20_C48_S6_S20-48-603` (Arkansas): genuinely DEFINES
#     "Division" ("(3) \"Division\" means the Division of Developmental
#     Disabilities Services...") and later, in ordinary prose, genuinely
#     RE-MENTIONS it in lowercase, twice, with NO numbering token anywhere
#     nearby ("...licensed by the division that provides room and board...",
#     entries (4) and (5)) -- the exact "I6 must survive" positive case.
#     (This row's own `text` field contains its content duplicated verbatim
#     -- a real corpus artifact, not injected by this Planner; both listed
#     match counts below account for it.)
#
# P-R7 denominator note: these are targeted, hand-verified real examples
# (the program's own D-CF ruling already cites the corpus-wide measurement
# -- "14,501-extra-match / 47%-of-terms exposure" -- that justified the
# guard; re-deriving that exact corpus-wide count is not this Planner's
# task per the brief). Each assertion below is checked against ONE
# concrete, fully-quoted real row, not a heading/trigger-derived population,
# so the denominator for each individual claim is exactly "this real row's
# own text," independent of any capture signal.


DCF_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "d_cf_structural_reference_rows.json"
)


def _load_dcf_rows() -> dict[str, dict]:
    rows = json.loads(DCF_FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def dcf_rows():
    return _load_dcf_rows()


def test_us_profile_find_term_uses_case_fold_guard_suppresses_a_lowercase_division_structural_reference(
    dcf_rows,
):
    """D-CF: 'division (ii)'-shaped structural reference must NOT be
    returned as a use of a defined term named 'Division'. Real row
    `STATE_AL_T41_C10_S41-10-592`: 'All bonds issued pursuant to this
    division (i) shall be issued...' -- verified today (pre-guard) that
    this is the row's ONLY 'division' occurrence and that it DOES match
    under plain case-folding (RED: the guard does not exist yet, so this
    assertion fails today)."""
    from app.definition_links.us_profile import find_term_uses

    text = dcf_rows["STATE_AL_T41_C10_S41-10-592"]["text"]
    assert "division (i)" in text.lower()  # sanity: fixture really has this shape
    matches = find_term_uses("Division", text)
    assert matches == [], (
        "D-CF: 'division (i)' is a structural cross-reference (unit word + "
        "numbering token), not a use of a defined term named 'Division' -- "
        f"it must be suppressed. Got matches at "
        f"{[(m.start(), m.end(), text[m.start():m.end()]) for m in matches]!r}"
    )


def test_us_profile_find_term_uses_case_fold_guard_suppresses_lowercase_part_structural_references(
    dcf_rows,
):
    """D-CF: 'part (a)'-shaped structural references must NOT be returned
    as uses of a defined term named 'Part'. Real row
    `STATE_IL_C35_A505_S13a`: 'Part (a) shall be at the rate... Part (b)
    shall be at the rate...' -- verified today (pre-guard) both are the
    row's ONLY 'Part'/'part' occurrences and both DO match under plain
    case-folding (RED today)."""
    from app.definition_links.us_profile import find_term_uses

    text = dcf_rows["STATE_IL_C35_A505_S13a"]["text"]
    assert "Part (a)" in text and "Part (b)" in text  # sanity
    matches = find_term_uses("Part", text)
    assert matches == [], (
        "D-CF: 'Part (a)'/'Part (b)' are structural cross-references (unit "
        "word + numbering token), not uses of a defined term named 'Part' "
        f"-- both must be suppressed. Got matches at "
        f"{[(m.start(), m.end(), text[m.start():m.end()]) for m in matches]!r}"
    )


def test_us_profile_find_term_uses_case_fold_guard_suppresses_a_bare_number_title_structural_reference(
    dcf_rows,
):
    """D-CF's third named example shape ('title 5' -- a unit word followed
    by a BARE number, no parens): must NOT be returned as a use of a
    defined term named 'Title'. Real row
    `STATE_AK_T6_C06.45_S06.45.160`: '...insurance obtained under Title 1
    of the National Housing Act...' -- verified today (pre-guard) this is
    the row's ONLY 'Title'/'title' occurrence and it DOES match under
    plain case-folding (RED today)."""
    from app.definition_links.us_profile import find_term_uses

    text = dcf_rows["STATE_AK_T6_C06.45_S06.45.160"]["text"]
    assert "Title 1" in text  # sanity
    matches = find_term_uses("Title", text)
    assert matches == [], (
        "D-CF: 'Title 1' is a structural cross-reference (unit word + bare "
        "numbering token), not a use of a defined term named 'Title' -- it "
        f"must be suppressed. Got matches at "
        f"{[(m.start(), m.end(), text[m.start():m.end()]) for m in matches]!r}"
    )


def test_us_profile_find_term_uses_case_fold_guard_does_not_suppress_a_genuine_lowercase_re_mention(
    dcf_rows,
):
    """D-CF is a GUARD, not a reversion of I6/M8(b) -- a genuine lowercase
    re-mention of a defined term in ORDINARY prose (no numbering token
    anywhere nearby) must still be returned. Real row
    `STATE_AR_T20_C48_S6_S20-48-603` genuinely defines 'Division' and later
    re-mentions it lowercase THREE times in ordinary prose, per copy of the
    row's own text ('...staff of the division where the context...',
    '...home licensed by the division...' x2, entries (3)-(5)) -- doubled
    to 6 real occurrences because this row's own `text` field contains its
    content duplicated verbatim, a real corpus artifact, confirmed by
    running `find_term_uses` against the real fixture text before writing
    this assertion (not guessed). This is the explicit reason I6 survives
    D-CF -- pinned so a future guard implementation cannot accidentally
    over-suppress and silently undo M8(b). GREEN today (no guard exists
    yet to suppress anything) and MUST STAY GREEN once the guard lands."""
    from app.definition_links.us_profile import find_term_uses

    text = dcf_rows["STATE_AR_T20_C48_S6_S20-48-603"]["text"]
    assert "licensed by the division" in text  # sanity: fixture really has this shape
    matches = find_term_uses("Division", text)
    lowercase_prose_matches = [
        m for m in matches if text[m.start() : m.end()] == "division"
    ]
    assert len(lowercase_prose_matches) == 6, (
        "D-CF must NOT suppress a genuine lowercase re-mention with no "
        "numbering token nearby -- 'staff of the division'/'licensed by "
        "the division' (x3 per copy, doubled by this row's own real "
        f"duplicated-text artifact = 6) must still be returned. Got "
        f"lowercase matches: "
        f"{[(m.start(), m.end(), text[max(0,m.start()-25):m.end()+25]) for m in lowercase_prose_matches]!r}"
    )


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


# --- Sprint 2026-08-04-defs-core-scope, seam v2.3 -- the THIRD M12 defect --
#
# `_TRIGGER_PHRASES` (us_profile.py:443) is `("has the meaning specified
# in", "as defined in")` today -- missing the three real idioms below,
# needed for `detect_cross_law_derivations` to fire AT ALL on these rows
# (`claude/defs-us-multiterm@f1011f0`'s own
# `test_*_reference_edge_needs_both_*_and_iii_fixed`; read-only fetch, not
# checked out). This is a literal phrase-list addition to the EXISTING
# tuple, not a new rule kind (v2.3: M12 itself is scoped to
# `find_citations`/`_CITATION_PATTERNS`) -- core fixes this alongside the
# other two defects as one baseline change, so QA checks all three.
#
# Each test below uses an ALREADY-recognized "Section N" citation shape
# (no decimal point) rather than the exact real fixture's decimal-numbered
# citation, so the RED signal here isolates the phrase-list gap alone --
# distinct from the two `find_citations` defects already pinned above,
# which stay RED/green independently of whether the phrase is recognized.


def test_us_profile_detect_cross_law_derivations_recognizes_the_has_the_meaning_given_that_term_in_idiom():
    """v2.3's third defect, idiom 1 of 3: 'has the meaning given that term
    in' (the real OR row's own idiom) is not in `_TRIGGER_PHRASES` today,
    so this real defining clause is entirely invisible to
    `detect_cross_law_derivations` -- not merely mis-parsed, not detected
    at all."""
    from app.definition_links.us_profile import detect_cross_law_derivations

    entry_text = '"Enforcement officer" has the meaning given that term in Section 5.'
    edges = detect_cross_law_derivations(
        entry_text, source_term="Enforcement officer", known_law_titles={}
    )
    assert len(edges) >= 1, (
        "expected at least one derivation edge -- `_TRIGGER_PHRASES` does "
        "not include 'has the meaning given that term in' today, so this "
        "real idiom (the OR 'Enforcement officer' row) is invisible to "
        "detect_cross_law_derivations."
    )
    assert any("has the meaning given that term in" in e.trigger_phrase.lower() for e in edges)


def test_us_profile_detect_cross_law_derivations_recognizes_the_has_the_meaning_assigned_by_idiom():
    """v2.3's third defect, idiom 2 of 3: 'has the meaning assigned by'
    (the real TX 'Governmental body' row's own idiom, singular form)."""
    from app.definition_links.us_profile import detect_cross_law_derivations

    entry_text = '"Governmental body" has the meaning assigned by Section 6.'
    edges = detect_cross_law_derivations(
        entry_text, source_term="Governmental body", known_law_titles={}
    )
    assert len(edges) >= 1, (
        "expected at least one derivation edge -- `_TRIGGER_PHRASES` does "
        "not include 'has the meaning assigned by' today, so this real "
        "idiom (the TX 'Governmental body' row) is invisible to "
        "detect_cross_law_derivations."
    )
    assert any("has the meaning assigned by" in e.trigger_phrase.lower() for e in edges)


def test_us_profile_detect_cross_law_derivations_recognizes_the_have_the_meanings_assigned_by_idiom():
    """v2.3's third defect, idiom 3 of 3: 'have the meanings assigned by'
    (plural form -- the real TX six-term shared PARENT CLAUSE idiom, one
    clause introducing several terms at once)."""
    from app.definition_links.us_profile import detect_cross_law_derivations

    entry_text = "The following terms have the meanings assigned by Section 7:"
    edges = detect_cross_law_derivations(
        entry_text, source_term="Governmental body", known_law_titles={}
    )
    assert len(edges) >= 1, (
        "expected at least one derivation edge -- `_TRIGGER_PHRASES` does "
        "not include 'have the meanings assigned by' today, so the real TX "
        "six-term shared parent clause is invisible to "
        "detect_cross_law_derivations."
    )
    assert any("have the meanings assigned by" in e.trigger_phrase.lower() for e in edges)
