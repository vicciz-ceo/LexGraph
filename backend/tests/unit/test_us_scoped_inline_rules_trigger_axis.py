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

Scope-unit -> `.scope` string mapping -- AMENDED, Planner pass 4 (ruling
S-R11), against the SHIPPED seam (`rules/registry.py`, `matcher.py:136`
`_in_scope`). Live-enforced: `"chapter"` (`article.chapter == definition.
source_chapter`), `"local"` (`article.number == definition.
source_article_number`). `"subsection"` was believed live-enforced (S-R4)
but pass 3's S-R10 live-path test proved it dead: `_subsection_label` and
`profile.resolve_unit_path` are independent derivations that never agree
(format + level-semantics mismatch, plus a core resolver bug), so
`_subsection_contains_offset` always returns False. S-R11 (interim, self-
alarmed via `test_us_scoped_inline_pipeline_subsection_live.py`'s
`xfail(strict=True)`): maps to `"local"`, the narrowest REPRESENTABLE
enclosing unit -- zero-miss-safe, over-link bounded by one article,
reverts once core's fix lands. Any OTHER literal kind falls into
`_in_scope`'s generic branch (`getattr(article, "structural_units", ())`
-- absent on a real `MatcherArticle`), returning `False` for every
article including the definition's own (ruling S-R5).

    "section"     -> "local"      (enforced, source_article_number)
    "chapter"     -> "chapter"    (enforced, source_chapter)
    "subsection"  -> "local"      (RESOLVED, S-R11, pass 4, interim --
                                    narrowest REPRESENTABLE enclosing unit;
                                    reverts once core's resolve_unit_path
                                    fix lands. Was "subsection".)
    "act"         -> "law-wide"   (D3: "this act" == the whole document ==
                                    already-unenforced law-wide semantics,
                                    no coordination gap, just a name map)
    "article"     -> "law-wide"   (residue kind, ~4% combined volume; rather
    "title"       -> "law-wide"    than stamp a GUARANTEED-dead literal,
                                    falls back to core's OWN AK-range
                                    unrepresentable-narrowing precedent:
                                    zero-miss-safe, precision cost recorded)
    "part"        -> "law-wide"   (RESOLVED, S-R9, pass 3, 13.9% combined
    "subchapter"  -> "law-wide"    volume, same residue-kind treatment: a
                                    single Maine Part spans 106 chapters, so
                                    a chapter-fallback would silently MISS
                                    105 of them. Was "part"/"subchapter".)

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


def test_for_the_purpose_of_this_subchapter_falls_back_to_law_wide_scope():
    """Ruling S-R9 (resolves the D8/S-R5 PENDING question): `"subchapter"`
    is a residue kind, same treatment as `"article"`/`"title"` above --
    `_in_scope`'s generic branch reads `article.structural_units`, absent
    on a real `MatcherArticle`, so a literal `scope="subchapter"` would
    link ZERO mentions. D8 found 0/1,861 genuine hits even have a
    breadcrumb "subchapter" node -- no sound fallback but law-wide. Was
    `scope == "subchapter"` pre-ruling; amended Planner pass 3."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_PA_T53_C81_S8129"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    unfunded = _by_term(candidates, "unfunded debt")
    assert unfunded.scope == "law-wide"


def test_for_purposes_of_this_part_falls_back_to_law_wide_scope():
    """Ruling S-R9 (resolves the D8/S-R5 PENDING question): `"part"` is a
    residue kind. D8 measured a chapter-fallback UNSOUND -- a single Maine
    Part spans 106 distinct chapters (`title > part > chapter > section`),
    so `scope="chapter"` would silently MISS 105 of them. `_in_scope`'s
    generic branch is also dead on the live path (S-R5), so a literal
    `scope="part"` would link nothing at all. Falls back to `"law-wide"`,
    zero-miss-safe. Was `scope == "part"` pre-ruling; amended pass 3."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TN_T34_C6_S34-6-302"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    parent = _by_term(candidates, "parent")
    assert parent.scope == "law-wide"


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
    case” means..."` -- bare `In` immediately followed by a colon then a
    numbered list of quoted-term entries; orthogonal to the scope-fallback
    question below."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_SC_T37_C6_S37-6-402"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = _terms(candidates)
    assert {"Contested case", "License", "Licensing", "Party"} <= terms
    # Ruling S-R9: "part" is a residue kind, falls back to "law-wide" -- see
    # test_for_purposes_of_this_part_falls_back_to_law_wide_scope. Was
    # scope == "part".
    for term in ("Contested case", "License", "Licensing", "Party"):
        assert _by_term(candidates, term).scope == "law-wide"


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
