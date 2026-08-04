"""Sprint 2026-08-04-defs-us-scoped-inline (Planner, D5, target 1: pure rule
module). RED today with `ModuleNotFoundError` -- `app.definition_links.rules
.us_scoped_inline` does not exist yet (ruling S-R1: this is the legitimate
RED signal until the Developer writes the module; ruling S-R2: the
Developer is fenced to this NEW file only until core merges, zero edits to
`pipeline.py`/`extract.py`/`matcher.py`/`profiles.py`/`us_profile.py`/
`sections.py`).

Public API this file pins (Phase A, gates U1/U2):

    extract_us_scoped_inline_definitions(body: str) -> list[DefinitionCandidate]

A PURE function -- no heading, no article/document context, just the raw
(already `normalize_for_parsing`'d, already `strip_wikilinks`'d -- English
US text needs neither) article body text in, `DefinitionCandidate`s out.
Reuses the EXISTING `app.definition_links.extract.DefinitionCandidate`
dataclass (read-only import, not an edit to `extract.py`) so Phase B's
wiring can hand its output straight to `pipeline.py`'s existing candidate
list, matching `extract_local_definitions`'s own established shape.

This file: the TRIGGER axis -- which scope-naming phrases are recognized,
and what `.scope` string each names. Real corpus evidence (Planner's
2026-08-04 corpus scan, 12 lead states, see the sprint log's D1/D3
sections): the trigger vocabulary that actually occurs is `As used in this
<unit>`, `For (the) purposes of this <unit>`, `For the purpose of this
<unit>`, `When used in this <unit>`, and bare `In this <unit>` under
STRICT adjacency only (see `test_us_scoped_inline_rules_negative_
controls.py`: bare `in this <unit>` is genuine only ~21% of the time,
72.7% pure prose noise, vs. ~77% for `as used in`).

Scope-unit -> `.scope` string mapping -- AMENDED, Planner pass 2 (sprint
`2026-08-04-defs-us-scoped-inline`, post-core-merge), against the SHIPPED
seam (`rules/registry.py`, `matcher.py:136` `_in_scope`), which is
authoritative over the seam doc's prose per the sprint's own instruction.
Shipped, live-enforced kinds (ruling S-R4, 82.0% of measured genuine
volume): `"chapter"` (`article.chapter == definition.source_chapter`),
`"local"` / `"subsection"` (`article.number == definition.
source_article_number`, subsection additionally offset-checked). Any OTHER
literal kind string falls into `_in_scope`'s generic branch, which reads
`getattr(article, "structural_units", ())` -- a real `MatcherArticle` has
no such attribute, so that branch returns `False` for every article,
including the definition's own (ruling S-R5: a structurally GUARANTEED
zero-miss violation for any mention of the term, anywhere, if a candidate
were stamped with a dead kind literal).

    "section"     -> "local"      (enforced, source_article_number)
    "chapter"     -> "chapter"    (enforced, source_chapter)
    "subsection"  -> "subsection" (enforced, offset-checked)
    "act"         -> "law-wide"   (D3: "this act" == the whole document ==
                                    already-unenforced law-wide semantics,
                                    no coordination gap, just a name map)
    "article"     -> "law-wide"   (residue kind, ~4% combined volume;
    "title"       -> "law-wide"    manager agreed to defer asking core for
                                    dedicated enforcement -- rather than
                                    stamp a GUARANTEED-dead literal, this
                                    falls back to core's OWN established
                                    precedent for an unrepresentable
                                    narrowing, seam spec v2 S1's AK
                                    multi-chapter-range fallback:
                                    zero-miss-safe, precision cost recorded,
                                    not silently dropped)
    "part"        -> PENDING      (13.9% combined genuine volume -- ruling
    "subchapter"  -> PENDING       S-R5 explicitly left this open for D8
                                    measurement + a manager ruling; see
                                    those tests below and the `-log.md`'s
                                    D8 section for the measured numbers.
                                    NOT resolved by this pass -- do not
                                    treat the literal "part"/"subchapter"
                                    strings these specific tests still
                                    assert as a final answer)

All fixture rows load from the vendored, real, un-modified corpus rows in
`tests/fixtures/us_statutes/us_scoped_inline_rows.json` (ruling: no test
reads the parquet -- see `test_definition_links_no_network_dependencies.py`
for this codebase's existing no-network guard culture, extended here to
"no test opens the HF snapshot directly either", matching the established
`de_sample_rows.json`-style convention).
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def _terms(candidates) -> set[str]:
    out = set()
    for c in candidates:
        out.update(c.terms)
    return out


def _by_term(candidates, term):
    hits = [c for c in candidates if term in c.terms]
    assert hits, f"{term!r} not found among extracted terms {sorted(_terms(candidates))!r}"
    return hits[0]


# --- "As used in this <unit>" -----------------------------------------------


def test_as_used_in_this_section_maps_to_local_scope():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T61_S61_1_18.8"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    concurrence = _by_term(candidates, "concurrence")
    assert concurrence.scope == "local"


def test_as_used_in_this_article_falls_back_to_law_wide_scope():
    """`"article"` (ME/SC's sense: a chapter subdivision spanning several
    of OUR `Article` rows -- not a synonym for `"local"`) is a dead residue
    kind (S-R5); falls back to law-wide, core's own AK-range precedent.
    Was `scope == "article"` pre-merge; amended Planner pass 2."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ME_T30-A_P1_C3_S751"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    commissioners = _by_term(candidates, "county commissioners")
    assert commissioners.scope == "law-wide"


def test_as_used_in_this_title_falls_back_to_law_wide_scope():
    """Same residue-kind fallback as above. Was `scope == "title"`
    pre-merge; amended Planner pass 2."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ME_T24-A_C1_S14"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    aca = _by_term(candidates, "federal Affordable Care Act")
    assert aca.scope == "law-wide"


def test_as_used_in_this_article_south_carolina_falls_back_to_law_wide_scope():
    """Same fallback, SC's `Title > Chapter > Article > Section` convention.
    Was `scope == "article"` pre-merge; amended Planner pass 2."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T59_C111_A5_S59-111-310"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    tuition = _by_term(candidates, "tuition")
    assert tuition.scope == "law-wide"


# --- "For (the) purpose(s) of this <unit>" ----------------------------------


def test_for_purposes_of_this_section_maps_to_local_scope():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T61_S61_1_18.8"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    # "For purposes of this section" is the actual trigger text in this row
    # (not "As used in") -- both phrasings must resolve to the same "local"
    # scope for the same "this section" unit.
    assert "concurrence" in _terms(candidates)


def test_for_the_purpose_of_this_subchapter_maps_to_subchapter_scope():
    """PENDING D8/S-R5 ruling, NOT amended this pass: 100% non-null
    row-level `chapter` field (12 lead states) but 0/1,861 genuine hits
    have a breadcrumb "subchapter" node -- structurally UNVERIFIABLE, not
    confirmed. See the `-log.md` D8 section; literal "subchapter" is a
    placeholder pending the manager's fallback ruling."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_PA_T53_C81_S8129"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    unfunded = _by_term(candidates, "unfunded debt")
    assert unfunded.scope == "subchapter"


def test_for_purposes_of_this_part_maps_to_part_scope():
    """PENDING D8/S-R5 ruling, NOT amended this pass -- see the `-log.md`
    D8 section: 2,187 genuine `"part"` hits, 100% non-null `chapter`
    field, but a real breadcrumb counter-example (Maine: `part` CONTAINS
    multiple chapters, `title > part > chapter > section`) that would make
    a naive chapter-fallback UNDER-link. Literal "part" is a placeholder
    pending the manager's ruling."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TN_T34_C6_S34-6-302"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    parent = _by_term(candidates, "parent")
    assert parent.scope == "part"


# --- "When used in this <unit>" ---------------------------------------------


def test_when_used_in_this_title_falls_back_to_law_wide_scope():
    """Residue-kind fallback, was `scope == "title"` pre-merge. This row's
    OTHER two entries stay chapter-scoped -- see
    `test_trigger_embedded_after_the_term_is_still_recognized` below."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T3_C45_S2291"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    life_cycle = _by_term(candidates, "life-cycle costs")
    assert life_cycle.scope == "law-wide"


# --- bare "In this <unit>" under strict adjacency ---------------------------


def test_bare_in_this_article_with_immediate_quote_is_a_genuine_trigger():
    """`STATE_VT_T11C_C7_S701`: `"In this article, “marketing contract”
    means..."` -- the trigger word is bare `In`, not `As used in`/`For
    purposes of`, but the very next non-whitespace content after `this
    article` is a comma then an immediately-adjacent quoted term: this is
    the strict-adjacency case that keeps bare `In` usable (see this file's
    module docstring for why bare `In` needs this restriction at all)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T11C_C7_S701"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    contract = _by_term(candidates, "marketing contract")
    # residue-kind fallback (was scope == "article" pre-merge; see the
    # module docstring's mapping table) -- this test's OWN purpose (bare
    # `In` + strict-adjacency recognition) is orthogonal to the fallback
    # question and is unaffected by it.
    assert contract.scope == "law-wide"


def test_bare_in_this_part_with_immediate_colon_list_is_a_genuine_trigger():
    """`STATE_SC_T37_C6_S37-6-402`: `"In this part: (1) “Contested
    case” means..."` -- bare `In` immediately followed by a colon then
    a numbered list of quoted-term entries."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T37_C6_S37-6-402"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = _terms(candidates)
    assert {"Contested case", "License", "Licensing", "Party"} <= terms
    # PENDING D8/S-R5 ruling -- see test_for_purposes_of_this_part_maps_to_
    # part_scope's docstring above; not amended this pass.
    for term in ("Contested case", "License", "Licensing", "Party"):
        assert _by_term(candidates, term).scope == "part"


# --- marker-prefixed (mid-sentence) trigger variant -------------------------


def test_marker_prefixed_trigger_is_recognized():
    """`STATE_TX_Cwa_C55_S55.047`: `"(a) As used in this section: (1)
    “city” includes..."` -- a leading `(a)` subsection marker
    before the trigger phrase itself must not block recognition."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TX_Cwa_C55_S55.047"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = _terms(candidates)
    assert "city" in terms
    assert "unincorporated area" in terms
    for term in ("city", "unincorporated area"):
        assert _by_term(candidates, term).scope == "local"


def test_double_marker_prefixed_trigger_is_recognized():
    """`STATE_VT_T3_C45_S2291`: `"(a)(1) When used in this title,
    “life-cycle costs” shall mean..."` -- a CHAIN of two markers
    (`(a)` then `(1)`) before the trigger."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T3_C45_S2291"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert "life-cycle costs" in _terms(candidates)


# --- trigger appearing AFTER its own term (not a leading preamble) ----------


def test_trigger_embedded_after_the_term_is_still_recognized():
    """`STATE_VT_T3_C45_S2291`'s 2nd and 3rd entries: `"“State
    facilities,” when used in this chapter, shall mean..."` and
    `"“State fleet,” as used in this chapter, shall mean..."` --
    the trigger phrase sits BETWEEN the quoted term and the defining idiom,
    not as a block-leading preamble. Real, both in the SAME body as the
    title-scoped entry above -- proves scope must be resolved per-entry,
    never once for the whole body (see the multi-scope test in
    `test_us_scoped_inline_rules_body_axis.py`)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T3_C45_S2291"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    facilities = _by_term(candidates, "State facilities")
    fleet = _by_term(candidates, "State fleet")
    assert facilities.scope == "chapter"
    assert fleet.scope == "chapter"
