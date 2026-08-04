"""Live-path RED integration tests for sprint 2026-08-04-defs-core-scope
(gates C1, C4, M8(a); seam spec `## Seam spec (published)` in the sprint
contract).

Unlike `test_definition_links_us_profile_definitions_section_end_to_end.py`
(profile-methods chained directly), every test here drives the REAL
production entry point, `run_definition_linking`, against a REAL
DB-backed matter -- the structural-wiring-gate requirement that a new
module/function/dispatcher branch has a live call-site test proving the
production path actually reaches it, not merely a unit test on the new
piece in isolation.
"""

from __future__ import annotations

import pathlib

from sqlalchemy import select

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- M8(a): a bare-`@`-marked section must not lose its definitions on the
# --- REAL `run_definition_linking` path (unit-level RED already pins the
# --- `parse_articles` gap directly; this proves it is not silently masked
# --- or recovered somewhere downstream in the full pipeline). -------------


def test_run_definition_linking_does_not_lose_a_definition_behind_a_bare_at_marker(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    wiki_text = (
        "@\n"
        "פרשנות\n"
        ':- "מונח יסודי" - הגדרה שאף פעם לא נקלטת בעולם האמיתי.\n'
        "@ 2. הוראה נוספת\n"
        "התוכן מזכיר מונח יסודי כאן.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק לדוגמה עם סימון @ חסר",
        wiki_text=wiki_text,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {tuple(d["terms"]) for d in result["created_definitions"]}
    assert ("מונח יסודי",) in created_terms, (
        "the bare-`@`-marked section's own definition ('מונח יסודי') must "
        "be captured by the real run_definition_linking path -- today it "
        "is silently unreachable because sections.parse_articles never "
        "attaches it to any Article at all (M8(a))."
    )


# --- C4: a rule module registered into `app.definition_links.rules` must
# --- be reachable through the REAL `run_definition_linking` path, not
# --- just importable/callable in isolation. -------------------------------


def test_a_registered_scope_trigger_rule_is_reached_by_the_real_pipeline(
    db_session, matter_with_users
):
    """C4's structural-wiring proof: register a throwaway English
    scope-trigger rule (mirroring the seam spec's own worked example) and
    confirm `run_definition_linking`, run over a REAL US-jurisdiction
    document, actually produces a `Definition` row from it -- proving the
    rule registry is consumed by the production path (`profile.
    extract_local_scope_definitions`), not merely constructible."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    # This import is expected to fail today (module doesn't exist) --
    # the RED signal for this test.
    from app.definition_links.rules.registry import (  # noqa: F401
        RuleContext,
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate

    def _extract(article_body, ctx):
        import re

        pattern = re.compile(
            r'As used in this section,\s*"([^"]+)"\s*means\s+(.*?)(?=\.\s|$)',
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="local",
                source_article_number=ctx.article_number,
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    wiki_text = (
        '@ 5. Ordinary provision\n'
        'As used in this section, "Local widget" means a widget sold '
        "only within city limits.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test US Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    rows = (
        db_session.execute(
            select(Definition).where(Definition.matter_id == m["matter_id"])
        )
        .scalars()
        .all()
    )
    assert any("Local widget" in row.terms for row in rows), (
        "a ScopeTriggerRule registered for 'US-*' must be reached by the "
        "REAL run_definition_linking path via profile."
        "extract_local_scope_definitions -- today no such method/registry "
        "exists, so this English scoped-inline definition is never "
        "captured for a US document (C2/C4)."
    )


# --- M9: enumerated/ranged local scope, live-path proof (seam spec v2.1
# --- §1/v2.2 §2, SD 3-14-5-shaped real fact pattern: "when used in
# --- section 3-14-3 or 3-14-4"). Unit-level coverage already exists
# --- (test_definition_links_matcher.py::test_link_articles_to_
# --- definitions_respects_enumerated_local_scope); this proves the SAME
# --- tuple-valued `source_article_number` shape survives end-to-end
# --- through the REAL run_definition_linking path, reached via a
# --- registered ScopeTriggerRule (same C4 registry mechanism as the proof
# --- test above -- article numbers are plain digits here rather than
# --- SD's real hyphenated citation form, since sections._ARTICLE_MARKER_RE
# --- only parses `\d+[Hebrew-letters]*` article numbers in this wiki
# --- fixture format; SD's own hyphenated numbering is a citation-format
# --- detail orthogonal to what this test pins, which is the ENUMERATED-
# --- SCOPE containment mechanism itself). -----------------------------


def test_an_enumerated_local_scope_links_every_member_article_and_excludes_a_non_member_live(
    db_session, matter_with_users
):
    """A definition's local scope may be an ENUMERATED SET of article
    numbers, not a single scalar -- 'when used in Section 3 or Section 4'
    scopes ONE definition to TWO member articles (M9). A mention of the
    identical defined-term surface form in a THIRD, non-member article
    must NOT link, even though nothing about its own text distinguishes
    it from the member articles' mentions."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    # This import is expected to fail today (module doesn't exist) -- the
    # RED signal for this test (same pattern as the C4 proof test above).
    from app.definition_links.rules.registry import (  # noqa: F401
        RuleContext,
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate

    def _extract(article_body, ctx):
        import re

        pattern = re.compile(
            r'"([^"]+)" when used in Section (\d+) or Section (\d+) means '
            r'(.*?)(?=\.\s|$)',
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(4).strip(),
                scope="local",
                source_article_number=(match.group(2), match.group(3)),
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    term = "Enumerated widget"
    wiki_text = (
        f'@ 5. Term scope note\n'
        f'"{term}" when used in Section 3 or Section 4 means a specially '
        f"regulated item.\n"
        f"@ 3. Member section one\n"
        f"A {term} is regulated under this section.\n"
        f"@ 4. Member section two\n"
        f"A {term} is also regulated under this section.\n"
        f"@ 9. Non-member section\n"
        f"A {term} is mentioned here too, but this section is not "
        f"enumerated in the scope trigger above.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test SD-3-14-5-Shaped Enumerated Scope Statute",
        wiki_text=wiki_text,
        jurisdiction="US-SD",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    linked_propositions = " | ".join(e["proposition"] for e in uses_edges)
    assert "Article 3 " in linked_propositions or linked_propositions.count("Article 3") >= 1, (
        f"expected member article 3 to be linked; created assertions were: "
        f"{linked_propositions!r}"
    )
    assert "Article 4" in linked_propositions, (
        f"expected member article 4 to be linked; created assertions were: "
        f"{linked_propositions!r}"
    )
    assert "Article 9" not in linked_propositions, (
        "a non-member article sharing the identical defined-term surface "
        "form must NOT be linked -- the enumerated scope's member set is "
        "{'3', '4'} only (M9); created assertions were: "
        f"{linked_propositions!r}"
    )


# --- M10 tie-pinning, live path (manager ruling M10, obligation (a)).
# --- The previous Planner attempted this and deliberately REMOVED it
# --- after discovering its first version didn't construct a genuine tie
# --- (only one Definition row existed, so it passed today for the wrong
# --- reason) -- an honestly-open item was judged better than a
# --- misleading green. This version constructs the tie the spec itself
# --- already names as a concrete, unambiguous instance (seam v2.1 §1,
# --- "Consequence for M4(c)"): "a local def and a set-valued local def
# --- covering the same article are rank-EQUAL ... it falls out of the
# --- M10 resolution automatically" -- no cross-kind ("chapter" vs.
# --- "part") comparison is needed, only two "local"-scope candidates
# --- (one scalar, one enumerated) from TWO DIFFERENT owning articles
# --- (so they persist as two DISTINCT Definition rows -- the pipeline's
# --- existing dedup key is (owning_article_id, sorted(terms)), and these
# --- two owning articles differ) that both scope-contain the SAME target
# --- article. -----------------------------------------------------------


def test_two_same_rank_local_scoped_definitions_that_tie_both_get_a_uses_definition_assertion_live(
    db_session, matter_with_users
):
    """Genuine tie, constructed live: Definition X (housed in article 5,
    scope="local", source_article_number="12", scalar) and Definition Y
    (housed in article 6, scope="local", source_article_number=("12",
    "13"), enumerated) are two DISTINCT Definition rows -- different
    owning articles -- that both scope-contain article 12 at the SAME
    rank ("local"). A single mention of "Tied term" in article 12 must
    receive TWO USES_DEFINITION assertions, one per surviving Definition
    row (M10: "one of the resulting assertions is factually wrong -- we
    just don't know which" -- zero-miss-safe default is BOTH survive,
    deliberately, not emergently)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion
    from app.models.definition import Definition

    # This import is expected to fail today (module doesn't exist) -- the
    # RED signal for this test (same pattern as the C4 proof test above).
    from app.definition_links.rules.registry import (  # noqa: F401
        RuleContext,
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate

    def _extract_scalar(article_body, ctx):
        import re

        pattern = re.compile(
            r'"([^"]+)" applies specially in Section (\d+) per rule one\.',
            re.IGNORECASE,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text="First rule's own definition text.",
                scope="local",
                source_article_number=match.group(2),
            )
            for match in pattern.finditer(article_body)
        ]

    def _extract_enumerated(article_body, ctx):
        import re

        pattern = re.compile(
            r'"([^"]+)" applies specially in Section (\d+) and Section (\d+) '
            r"per rule two\.",
            re.IGNORECASE,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text="Second rule's own definition text.",
                scope="local",
                source_article_number=(match.group(2), match.group(3)),
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract_scalar)
    )
    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract_enumerated)
    )

    m = matter_with_users
    wiki_text = (
        '@ 5. Term scope note one\n'
        '"Tied term" applies specially in Section 12 per rule one.\n'
        '@ 6. Term scope note two\n'
        '"Tied term" applies specially in Section 12 and Section 13 per '
        "rule two.\n"
        "@ 12. Target section\n"
        "A Tied term is mentioned here for use-checking purposes.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test M10 Tie Statute",
        wiki_text=wiki_text,
        jurisdiction="US-MT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    tied_definitions = [d for d in result["created_definitions"] if "Tied term" in d["terms"]]
    assert len(tied_definitions) == 2, (
        "expected TWO distinct Definition rows for 'Tied term' (one per "
        "owning article, 5 and 6) -- got "
        f"{tied_definitions!r}"
    )
    tied_definition_ids = {d["id"] for d in tied_definitions}

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    matching_object_ids = {
        db_session.get(Assertion, e["id"]).object_entity_id
        for e in uses_edges
        if db_session.get(Assertion, e["id"]).object_entity_id in tied_definition_ids
    }
    assert matching_object_ids == tied_definition_ids, (
        "expected a USES_DEFINITION assertion pointing at EACH of the two "
        "tied Definition rows for the article-12 mention of 'Tied term' -- "
        "today's flat term_to_definition dict (pipeline.py Stage 3) keeps "
        "only whichever candidate was processed last, so at most ONE "
        "assertion is created regardless of how many same-rank "
        f"Definitions genuinely tie (M10). Got object ids: "
        f"{matching_object_ids!r}, expected: {tied_definition_ids!r}"
    )


# --- Pointer definitions, internal (same-law) targets (director ruling,
# --- seam spec v2.1 §4). No typed pointer field exists or may be added --
# --- a consumer determines pointer-ness ONLY by checking whether a
# --- DERIVES_FROM_LAW assertion exists with subject_entity_id equal to
# --- the Definition's own id, so this test pins the EDGE itself, live-
# --- path, not a flag. ------------------------------------------------


def test_a_whole_definition_pointer_to_an_internal_same_law_article_emits_a_derives_from_law_edge_to_that_article(
    db_session, matter_with_users
):
    """A definition whose ENTIRE `definition_text` is consumed by a
    defining-idiom trigger + citation (a "whole-definition pointer", not
    an incidental same-law aside inside a longer substantive definition)
    must redirect to an Article-targeted DERIVES_FROM_LAW edge instead of
    being silently excluded as same-document/same-chapter internal-
    reference noise (today's `_SAME_LAW_RE` behavior). Target resolved
    the same way Stage 3 already resolves same-document article numbers:
    the bare 'Section 5' citation -> the Article whose `.number == "5"`
    in the SAME document. Both halves of the emission are asserted: the
    Definition row itself (unaffected, already created today) AND the
    new pointer edge (the RED part)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.article import Article
    from app.models.assertion import Assertion
    from sqlalchemy import select as _select

    m = matter_with_users
    wiki_text = (
        "@ 5. Ordinary provision\n"
        "This provision states an ordinary rule unrelated to definitions.\n"
        "@ 101. Definitions\n"
        '(1) "Foo" has the meaning specified in Section 5 of this chapter.\n'
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test US Statute With An Internal Pointer Definition",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    foo_definitions = [d for d in result["created_definitions"] if "Foo" in d["terms"]]
    assert len(foo_definitions) == 1, (
        "the definition row itself must still be created (unaffected by "
        "the pointer-emission fix) -- got "
        f"{result['created_definitions']!r}"
    )
    foo_definition_id = foo_definitions[0]["id"]

    target_article = (
        db_session.execute(
            _select(Article).where(
                Article.matter_id == m["matter_id"], Article.number == "5"
            )
        )
        .scalars()
        .one()
    )

    matching = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "DERIVES_FROM_LAW"
        and db_session.get(Assertion, a["id"]).subject_entity_id == foo_definition_id
        and db_session.get(Assertion, a["id"]).object_entity_type == "Article"
        and db_session.get(Assertion, a["id"]).object_entity_id == target_article.id
    ]
    assert matching, (
        "expected a DERIVES_FROM_LAW assertion whose subject is the 'Foo' "
        "Definition and whose object is Article '5' (the internal, same-"
        "law pointer target) -- today the same-law exclusion "
        "(_SAME_LAW_RE) silently drops this edge entirely instead of "
        "redirecting it to the internal article (v2.1 §4); created "
        f"assertions were: {result['created_assertions']!r}"
    )


# --- Sub-article USES_DEFINITION anchoring (director ruling D-ANCHOR,
# --- Option C, final -- structured path now, write path kept
# --- B-promotion-compatible; NOT storage-shape-pinned per the explicit
# --- instruction -- asserted through a RETRIEVAL SEAM so a later
# --- promotion to first-class sub-article entities extends this test
# --- rather than invalidating it). ----------------------------------------


def test_a_mention_inside_a_specific_subsection_resolves_to_the_correct_unit_path_live(
    db_session, matter_with_users
):
    """A mention inside article 12's subsection (ב) must resolve, through
    the REAL run_definition_linking path, to a unit path identifying
    subsection (ב) specifically -- not just 'article 12' (today's
    coarsest-available anchor) and not a hard-coded storage column name/
    type (deliberately not asserted -- see seam spec v2.2 §6/D-ANCHOR).
    Retrieval seam: `get_mention_unit_paths(session, assertion_id) ->
    list[UnitPath]`, a NEW query helper this test requires to exist --
    whatever the eventual storage shape (additive column today, possible
    `Unit` entity later per D-ANCHOR), this helper is the stable contract
    a consumer reads through."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    term = "מונח תת סעיפי"
    wiki_text = (
        f'@ 12. נושא\n'
        f'לענין זה, "{term}" - הגדרה מקומית.\n'
        f"סעיף קטן (א): {term} הוזכר כאן לראשונה.\n"
        f"סעיף קטן (ב): {term} הוזכר כאן שוב, בתת-סעיף שונה.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק לדוגמה עם תת-סעיפים",
        wiki_text=wiki_text,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert len(uses_edges) >= 1

    # At least one USES_DEFINITION assertion's mention must resolve to a
    # unit path that is STRICTLY DEEPER than the bare article -- i.e. it
    # identifies a specific subsection, not merely "somewhere in article
    # 12". The retrieval seam is what a consumer calls; this test does
    # NOT assert which column/field backs it.
    found_sub_article_path = False
    for edge in uses_edges:
        assertion_row = db_session.get(Assertion, edge["id"])
        paths = get_mention_unit_paths(db_session, assertion_row.id)
        if any(len(path) > 0 for path in paths):
            found_sub_article_path = True
            break
    assert found_sub_article_path, (
        "no USES_DEFINITION assertion resolved to a sub-article unit path "
        "-- today mentions are only anchored at the whole-Article level, "
        "so a consumer cannot distinguish subsection (א) from (ב) for the "
        "same defined term in the same article (D-ANCHOR)."
    )
