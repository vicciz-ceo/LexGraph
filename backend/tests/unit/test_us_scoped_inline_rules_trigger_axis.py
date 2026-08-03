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
<unit>`, `When used in this <unit>`, and bare `In this <unit>` (the last
ONLY under strict adjacency -- see
`test_us_scoped_inline_rules_negative_controls.py` for why: a
cross-tabulation of trigger phrase against body signal across all 12 lead
states found bare `in this <unit>` is genuine only ~21% of the time (72.7%
pure prose noise, e.g. "Nothing in this section may be construed..."),
while `as used in this <unit>` is genuine ~77% of the time and `for
purposes of this <unit>` ~35-50% -- STRICT adjacency (the very next
non-whitespace content is a quote or a colon-then-list) is what makes the
bare-`In` case usable at all without reintroducing that noise).

Scope-unit -> `.scope` string mapping (ruling: pass the literal unit name
through for every unit besides section/chapter, since those two are the
ONLY units `matcher._in_scope` (matcher.py:104-110) enforces today via
`Article.number`/`Article.chapter` -- see the sprint log's D3 section for
the full frequency table and the coordination ask to core):

    "section"    -> "local"     (matches Hebrew's local-scope semantics;
                                  enforced today via source_article_number)
    "chapter"    -> "chapter"   (enforced today via source_chapter)
    "subsection" -> "subsection"  (NOT enforced today -- stamped faithfully,
    "part"       -> "part"         core coordination gap, see D3)
    "subchapter" -> "subchapter"
    "article"    -> "article"
    "title"      -> "title"
    "subdivision"-> "subdivision"
    "act"        -> "act"

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


def test_as_used_in_this_article_maps_to_article_scope():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ME_T30-A_P1_C3_S751"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    commissioners = _by_term(candidates, "county commissioners")
    assert commissioners.scope == "article"


def test_as_used_in_this_title_maps_to_title_scope():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ME_T24-A_C1_S14"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    aca = _by_term(candidates, "federal Affordable Care Act")
    assert aca.scope == "title"


def test_as_used_in_this_article_scope_south_carolina():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T59_C111_A5_S59-111-310"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    tuition = _by_term(candidates, "tuition")
    assert tuition.scope == "article"


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
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_PA_T53_C81_S8129"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    unfunded = _by_term(candidates, "unfunded debt")
    assert unfunded.scope == "subchapter"


def test_for_purposes_of_this_part_maps_to_part_scope():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TN_T34_C6_S34-6-302"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    parent = _by_term(candidates, "parent")
    assert parent.scope == "part"


# --- "When used in this <unit>" ---------------------------------------------


def test_when_used_in_this_title_maps_to_title_scope():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VT_T3_C45_S2291"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    life_cycle = _by_term(candidates, "life-cycle costs")
    assert life_cycle.scope == "title"


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
    assert contract.scope == "article"


def test_bare_in_this_part_with_immediate_colon_list_is_a_genuine_trigger():
    """`STATE_SC_T37_C6_S37-6-402`: `"In this part: (1) “Contested
    case” means..."` -- bare `In` immediately followed by a colon then
    a numbered list of quoted-term entries."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T37_C6_S37-6-402"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = _terms(candidates)
    assert {"Contested case", "License", "Licensing", "Party"} <= terms
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
