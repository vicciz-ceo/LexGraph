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


# --- M8(a) RETARGET (sprint 2026-08-04-defs-core-scope, ruling R19): the
# --- test this replaced (`test_run_definition_linking_does_not_lose_a_
# --- definition_behind_a_bare_at_marker`) asserted CAPTURE of a definition
# --- from a synthetic fixture shaped like `@` / heading / `:- "term" -
# --- ...`. Measuring the real 6,133-law israeli-laws-wiki corpus found
# --- that shape does not exist: of 331 real bare-`@` occurrences, 100% are
# --- followed by wiki table/markup and ZERO are followed by a definitions
# --- heading. The fixture below is a real (byte-for-byte vendored) excerpt
# --- of "רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות.wiki"
# --- (source: israeli-laws-wiki/data/laws/, lines 9-13 + 102-119) --
# --- CONFIRMING that shape: line 9 is a bare `@` immediately followed by
# --- table markup (no heading at all), and this specific real document has
# --- NO other `@ N.` marker anywhere -- its entire remaining body (lines
# --- 10-119+, including the `::- "..." - ...` nested entries at lines
# --- 116-119, introduced by "בפרט זה -" at line 115, themselves nested
# --- inside numbered item (3) of item 43's own sub-list) collapses into
# --- ONE bare-`@` section. Before M8(a)'s merged fix, THIS real document's
# --- own failure mode is total-document loss: `current_number` never
# --- becomes non-`None`, so `parse_articles` returns an empty list and
# --- every one of these real rows vanishes from the pipeline entirely --
# --- not "merged into a neighbouring article" (this file has none), the
# --- OTHER failure mode named in `sections.py`'s own bare-marker comment,
# --- which applies to a bare-`@` section that follows an already-open
# --- numbered article -- a shape this particular file's real rows do not
# --- contain, so it is not independently re-demonstrated here.
# ---
# --- What this test pins: REACHABILITY, not capture. The bare-`@`
# --- section's real body (both regions) must survive ingestion as a
# --- genuine `Article` row and must reach Stage 2's extraction call
# --- (`profile.extract_local_scope_definitions`, via the real
# --- `run_definition_linking` path) rather than being silently dropped.
# --- What this test deliberately does NOT assert: capture of the four
# --- `::-` / "בפרט זה" nested definitions ("סיווג", "צד קשור", "קטגוריה",
# --- "שליטה") as `Definition` rows. That double-colon-nested,
# --- "בפרט זה"-triggered idiom is a previously-uninventoried Hebrew
# --- scope-trigger variant -- core's `extract_local_scope_definitions`
# --- only recognizes "לענין זה,"/"בסעיף זה," (see `_LOCAL_TRIGGER_RE` in
# --- extract.py), not "בפרט זה". Whether/how to capture it is the IL
# --- panel's contractual territory, not core's; core's obligation ends at
# --- reachability (director ruling, this sprint).


def test_run_definition_linking_reaches_a_bare_at_markers_section_body_without_dropping_it_live(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.article import Article
    from app.models.source_span import SourceSpan

    m = matter_with_users
    wiki_text = _read(
        "רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות_excerpt.wiki"
    )
    ingest_result = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות",
        wiki_text=wiki_text,
    )

    # 1. NOT SILENTLY DROPPED: this real document is built ONLY of a bare
    # `@` marker -- before M8(a)'s fix, `current_number` never became
    # non-`None`, so `parse_articles` returned an empty list and
    # `ingest_wiki_law` persisted ZERO `Article` rows for it.
    assert len(ingest_result["article_ids"]) == 1, (
        "the bare-`@`-only real document must still parse into its own "
        "section -- got "
        f"{len(ingest_result['article_ids'])} Article row(s), expected "
        "exactly 1 (M8(a))."
    )
    article = db_session.get(Article, ingest_result["article_ids"][0])
    assert article.heading == "", (
        "this section came from a BARE `@` marker (no heading text) -- "
        f"got heading={article.heading!r}."
    )

    # 2. BOTH real regions of the section's body survived persistence --
    # the line-9 bare-`@` region (table markup, no heading) and the
    # line-116-119 nested-definitions region (the `::- "..." - ...`
    # entries under "בפרט זה -").
    span = db_session.get(SourceSpan, article.source_span_id)
    assert "שירותי בזק פנים-ארציים נייחים" in span.quote_text, (
        "the line-9 bare-`@` region's own real content (item 1 of the "
        "wiki table) must survive into the section's persisted body."
    )
    for term in ("סיווג", "צד קשור", "קטגוריה", "שליטה"):
        assert f'::- "{term}"' in span.quote_text, (
            f"the line-116-119 nested-definitions region's real "
            f"'::- \"{term}\"' entry must survive into the section's "
            "persisted body (content preservation, NOT a claim that it "
            "gets captured as a Definition -- see module-level comment)."
        )

    # 3. REACHES THE REAL EXTRACTION PATH: `run_definition_linking` must
    # process this Article like any other non-definitions-heading
    # article -- i.e. NOT skip it as bidi-degraded (which would mean it
    # never reaches `profile.extract_local_scope_definitions` at all) --
    # and must complete without raising.
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert article.id not in result["skipped_degraded_article_ids"], (
        "the bare-`@` section's Article must not be skipped as "
        "bidi-degraded -- if it were, it would never reach Stage 2's "
        "extraction call at all, and reachability would not hold."
    )
    assert "created_assertions" in result and "created_definitions" in result, (
        "run_definition_linking must complete and return its normal "
        f"result shape for a matter containing this document -- got {result!r}."
    )

    # Deliberately NOT asserted (out of core's scope for this sprint --
    # see module-level comment): whether "סיווג"/"צד קשור"/"קטגוריה"/
    # "שליטה" appear (or don't) in `result["created_definitions"]`. That
    # is a capture question for the IL panel's "בפרט זה" scope-trigger
    # work, not a reachability question for core.


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


def test_a_subsection_scoped_definition_links_a_mention_inside_its_own_subsection_live(
    db_session, matter_with_users
):
    """QA finding (independent re-verification, sprint QA phase): C1
    states 'Subsection granularity is new design work: mentions must be
    scope-checked below article level' and the seam doc lists C1
    ('subsection-granularity enforcement') under 'Done here (assume it,
    do not rebuild it)'. This test proves that claim does NOT hold on the
    live `run_definition_linking` path.

    A throwaway `ScopeTriggerRule` (same registration pattern as this
    sprint's own C4 proof test above) stamps a `scope="subsection"`
    `DefinitionCandidate` for a term defined specifically for subsection
    (b) of an article that ALSO has a mention of the identical surface
    form in subsection (a). Per C1, the subsection (b) mention should
    link and the subsection (a) mention should not.

    Today NEITHER links -- not because containment picks the wrong
    subsection, but because the mechanism is entirely inert on the live
    path. Root cause, verified by direct source read (not inferred):

    - `matcher._subsection_contains_offset` reads
      `getattr(article, "subsections", ())`. The REAL object
      `run_definition_linking` constructs and passes through
      (`app.definition_links.sections.Article`, aliased `MatcherArticle`
      in `pipeline.py`) is a frozen dataclass with exactly four fields --
      `number`, `heading`, `body`, `chapter` (see `sections.py`) -- it
      never carries a `.subsections` attribute, on any code path. So
      `_subsection_contains_offset` returns `()` -> `any(...)` over an
      empty sequence -> `False`, UNCONDITIONALLY, for every
      `scope="subsection"` definition on the live path -- not merely for
      out-of-scope mentions, for its OWN in-scope mention too.
    - No rule shipped by this sprint (`rules/il_scope_triggers.py`,
      `rules/us_scope_trigger_proof.py`) stamps `scope="subsection"` on
      any candidate either (grep across `backend/app/` confirms the only
      non-comment occurrence of `scope="subsection"` in production code
      is the docstring in `matcher.py` describing the branch, not a call
      site) -- there is no live PRODUCER either.
    - The one test that touches "subsection" on the live path,
      `test_a_mention_inside_a_specific_subsection_resolves_to_the_correct_unit_path_live`
      below, is a D-ANCHOR *anchoring* test (its definition is
      `scope="local"`, i.e. whole-article -- BOTH subsections' mentions
      link; it only checks which `UnitPath` each resolves to via
      `get_mention_unit_paths`). Anchoring (recording WHERE a mention
      is) and containment (RESTRICTING WHICH mentions a definition
      covers) are two different claims -- D-ANCHOR is explicitly a
      "retrieval seam only" ruling; it does not stand in for C1's
      containment requirement, and no other live test covers containment.
    - The unit-level tests in `test_definition_links_matcher.py`
      (`test_link_articles_to_definitions_respects_subsection_scope_isolation`
      et al.) pass today, but only via a `SimpleNamespace` stub
      (`_article_with_subsections`) that the test file's own docstring
      concedes real `_Article` "doesn't declare" -- confirming the
      mechanism is unit-tested-only, never wired to a live producer or a
      live-shaped consumer object. This is the same failure class the QA
      brief names explicitly (a green test proving the wrong thing) --
      here at the C1/subsection-containment level rather than the M10
      tie level.

    Expected once fixed: the subsection-(b) mention links, the
    subsection-(a) mention does not. This test currently fails already at
    the weaker "AT LEAST ONE assertion exists" assertion -- proving total
    inertness, a stronger and clearer failure than a mere mis-scoping.

    QA-fail cycle 2, follow-up 1a (post-C1-fix strengthening, `86e0bbe`):
    the fix landed and this file's weaker "at least one edge" assertion
    now passes -- but that alone does not prove containment picked the
    RIGHT mention. `_create_assertion`'s dedup key is
    `(article_id, term, definition_id, ...)` -- it does NOT include
    `char_offset` -- so a definition with exactly one owning article and
    one term can never produce more than ONE USES_DEFINITION assertion
    regardless of how many mentions (in-scope or not) match inside that
    article. An over-inclusive bug (subsection (a) wrongly treated as
    in-scope too) would therefore be INVISIBLE to an "at least one
    assertion" or even a "count of assertions" check -- both mentions
    collapsing to the same one row either way. The genuine discriminator
    (per the QA manager's own suggestion) is `get_mention_unit_paths`:
    Stage 3 processes edges in the TEXT order `term_uses` finds them, and
    `_create_assertion`'s dedup means only the FIRST edge to reach it
    actually creates the row and gets its position recorded as
    `subject_unit_path` -- every subsequent edge sharing the same key is
    silently skipped. Since subsection (a)'s mention appears BEFORE
    subsection (b)'s in this fixture's own text, an over-inclusive bug
    would let (a) win that race and the assertion would resolve to
    subsection (a), not (b) -- so asserting the surviving assertion's own
    recorded path is anchored at (b) is airtight in the direction that
    matters (it would go RED under the specific bug this mechanism most
    plausibly has, not just under total inertness)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate
    from app.models.assertion import Assertion

    def _extract(article_body, ctx):
        import re

        pattern = re.compile(
            r'"([^"]+)" applies only within subsection \(b\) of this '
            r"section, and means (.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="b",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    term = "Subsection widget"
    wiki_text = (
        f'@ 12. Target section\n'
        f'"{term}" applies only within subsection (b) of this section, '
        f"and means a specially regulated item.\n"
        f"(a) A {term} is mentioned here, in subsection (a), for contrast.\n"
        f"(b) A {term} is mentioned here, in subsection (b), where it is "
        f"actually defined.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test Subsection Scope Containment Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a scope='subsection' definition must link AT LEAST the mention "
        "inside its own defining subsection (b) -- C1's 'mentions must be "
        "scope-checked below article level' -- got ZERO USES_DEFINITION "
        "assertions. Root cause (see docstring above): the live "
        "MatcherArticle carries no `.subsections` attribute, so "
        "matcher.py's `_subsection_contains_offset` returns False "
        "unconditionally, making every scope='subsection' definition "
        f"inert on the live path. created_assertions={result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, (
        "expected exactly ONE USES_DEFINITION assertion (the dedup key has "
        "no char_offset component, so this alone does not prove correct "
        f"scoping -- see the directional check below). Got {uses_edges!r}"
    )

    # The STRONGER, directional check (follow-up 1a): the ONE surviving
    # assertion's own recorded mention position must be anchored inside
    # subsection (b) -- the mention that is ACTUALLY in scope -- not (a),
    # which appears earlier in the fixture's text and would win the
    # dedup race first if containment wrongly let it through.
    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], (
        f"expected a single, non-empty sub-article unit path for the "
        f"surviving assertion; got {paths!r}"
    )
    resolved_path = paths[0]
    assert resolved_path[0].value == "b", (
        "C1 directional proof: the surviving USES_DEFINITION assertion's "
        "own recorded mention position must resolve to subsection (b) -- "
        "the ONLY in-scope mention -- not (a). If this resolves to 'a', "
        "containment is over-inclusive (it let the out-of-scope "
        "subsection-(a) mention win instead of excluding it). Got "
        f"resolved_path={resolved_path!r}"
    )


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


# --- D-E1 (director ruling, binding): narrowest scope governs, STRICT
# --- (non-tied) case, live path. The sprint's own M10 tie test proves
# --- the EQUAL-rank case (both survive); no existing test constructs two
# --- DIFFERENT-rank candidates (chapter vs. local) covering the SAME
# --- mention to prove the broader one is actually SUPPRESSED, or that
# --- the broader definition still fires elsewhere in its own chapter
# --- where no narrower one applies. QA gap fill (Duty C). -----------------


def test_narrowest_scope_governs_a_local_definition_suppresses_a_same_term_chapter_definition_but_the_chapter_definition_still_fires_where_no_local_one_applies_live(
    db_session, matter_with_users
):
    """D-E1: 'A mention inside multiple definitions' scopes links ONLY to
    the narrowest (subsection > article/local > chapter/part > law-wide);
    the general definition still fires wherever no narrower one was
    detected.' Constructs BOTH halves live, in one document:

    - Article 1 (a real Definitions section, heading 'Definitions', body
      opening with 'For purposes of this chapter, ...') stamps a
      scope='chapter' Definition for 'Term', chapter '9'.
    - Article 10 (ordinary article, chapter '9') registers a throwaway
      scope='local' ScopeTriggerRule match ('As used in this section,
      "Term" means ...', the sprint's own C2 proof-rule shape) AND
      contains a SEPARATE, genuine mention of 'Term' in its own body.
    - Article 20 (ordinary article, SAME chapter '9', no local rule
      match) contains a genuine mention of 'Term' with nothing narrower
      covering it.

    Expected (D-E1): article 10's mention links ONLY to the local
    Definition (the chapter Definition must NOT also fire there — it is
    strictly narrower-governed, not a tie); article 20's mention links to
    the chapter Definition (no narrower candidate applies there, so the
    broader one is not suppressed globally, only locally)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate
    from app.models.assertion import Assertion

    def _extract(article_body, ctx):
        import re

        pattern = re.compile(
            r'D-E1-PROOF-TRIGGER: "([^"]+)" means (.*?)(?=\.\s|$)',
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
        "==9==\n"
        '@ 1. Definitions\n'
        "For purposes of this chapter, the following definitions apply:\n"
        '(1) "Term" means a chapter-wide default meaning.\n'
        "@ 10. Local override article\n"
        'D-E1-PROOF-TRIGGER: "Term" means a locally overridden meaning.\n'
        "A Term is mentioned here for testing, inside the locally-scoped "
        "article itself.\n"
        "@ 20. Plain chapter-scoped article\n"
        "A Term is mentioned here too, but this article has no local "
        "override -- the chapter-wide definition must still govern it.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test D-E1 Narrowest-Governs Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    chapter_def = next(
        d for d in result["created_definitions"] if d["terms"] == ["Term"] and d["scope"] == "chapter"
    )
    local_def = next(
        d for d in result["created_definitions"] if d["terms"] == ["Term"] and d["scope"] == "local"
    )
    assert chapter_def["id"] != local_def["id"]

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    article_10_edges = [e for e in uses_edges if "Article 10 " in e["proposition"]]
    article_20_edges = [e for e in uses_edges if "Article 20 " in e["proposition"]]

    assert article_10_edges, "expected article 10's mention to link at all"
    article_10_targets = {
        db_session.get(Assertion, e["id"]).object_entity_id for e in article_10_edges
    }
    assert article_10_targets == {local_def["id"]}, (
        "D-E1: article 10's mention sits inside BOTH the chapter-scoped "
        "and the local-scoped 'Term' definitions -- only the NARROWER "
        "(local) one may govern; the broader (chapter) one must be "
        f"suppressed there, not tied. Got target ids: {article_10_targets!r} "
        f"(local={local_def['id']!r}, chapter={chapter_def['id']!r})"
    )

    assert article_20_edges, "expected article 20's mention to link at all"
    article_20_targets = {
        db_session.get(Assertion, e["id"]).object_entity_id for e in article_20_edges
    }
    assert article_20_targets == {chapter_def["id"]}, (
        "D-E1: article 20's mention has no narrower (local) definition "
        "covering it, so the broader chapter-scoped definition must still "
        f"fire there. Got target ids: {article_20_targets!r} "
        f"(chapter={chapter_def['id']!r})"
    )


# --- QA-fail cycle 2, deliverable 1 (gap 3): C1 demands scope containment
# --- proven live-path in BOTH directions. QA cycle 1 found IN-scope US
# --- chapter containment live-tested (`test_a_registered_scope_trigger_
# --- rule_is_reached_by_the_real_pipeline` and the D-E1 test just above
# --- both prove a chapter definition FIRES inside its own chapter), but no
# --- live test anywhere proves the negative direction: that a chapter-
# --- scoped definition does NOT link an identical-term mention sitting in
# --- a DIFFERENT chapter of the same document. This test adds exactly that
# --- missing exclusion direction -- it deliberately does not re-prove the
# --- positive direction the D-E1 test above already covers.
def test_a_chapter_scoped_definition_links_a_mention_inside_its_own_chapter_but_not_an_identical_term_mention_in_a_different_chapter_live(
    db_session, matter_with_users
):
    """C1: 'proven live-path in BOTH directions (in-scope mention links;
    out-of-scope mention does not)', for US chapter scope specifically.

    One document, two chapters:
    - Chapter 9: article 1 is a real Definitions section, heading
      'Definitions', body opening with 'For purposes of this chapter, ...'
      (`us_profile.determine_scope`'s own recognized trigger phrase) --
      stamps a scope='chapter' Definition for 'Widget', chapter '9'.
      Article 5, ALSO in chapter 9, contains a genuine mention of
      'Widget'.
    - Chapter 10: article 6 contains an IDENTICAL-surface-form mention of
      'Widget', but sits in a different chapter -- outside the chapter-9
      definition's scope, and no other definition of 'Widget' exists
      anywhere in the document.

    Expected: article 5's mention links to the chapter-9 'Widget'
    Definition; article 6's mention produces NO USES_DEFINITION assertion
    at all (there is no in-scope definition of 'Widget' covering it)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    wiki_text = (
        "==9==\n"
        '@ 1. Definitions\n'
        "For purposes of this chapter, the following definitions apply:\n"
        '(1) "Widget" means a specially regulated device.\n'
        "@ 5. In-chapter article\n"
        "A Widget is mentioned here, inside chapter 9, where the "
        "chapter-scoped definition applies.\n"
        "==10==\n"
        "@ 6. Different-chapter article\n"
        "A Widget is mentioned here too, but this article sits in "
        "chapter 10 -- a different chapter from the one the definition "
        "above was scoped to.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test Chapter Scope Exclusion Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    chapter_defs = [
        d for d in result["created_definitions"] if d["terms"] == ["Widget"] and d["scope"] == "chapter"
    ]
    assert len(chapter_defs) == 1, (
        f"expected exactly one chapter-scoped 'Widget' Definition, got {chapter_defs!r}"
    )
    chapter_def = chapter_defs[0]

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    article_5_edges = [e for e in uses_edges if "Article 5 " in e["proposition"]]
    article_6_edges = [e for e in uses_edges if "Article 6 " in e["proposition"]]

    assert article_5_edges, (
        "expected article 5's in-chapter mention of 'Widget' to link to "
        f"the chapter-9 definition; created_assertions={result['created_assertions']!r}"
    )
    article_5_targets = {
        db_session.get(Assertion, e["id"]).object_entity_id for e in article_5_edges
    }
    assert article_5_targets == {chapter_def["id"]}, (
        "article 5's in-chapter mention must link to the chapter-9 "
        f"'Widget' definition. Got target ids: {article_5_targets!r} "
        f"(chapter={chapter_def['id']!r})"
    )

    assert not article_6_edges, (
        "C1 out-of-scope direction: article 6 sits in chapter 10, outside "
        "the chapter-9-scoped 'Widget' definition's scope, and no other "
        "'Widget' definition exists in this document -- article 6's "
        "mention must NOT produce a USES_DEFINITION assertion. Got "
        f"{article_6_edges!r}"
    )


# --- QA-fail cycle 2, follow-up 1b: genuinely multi-level subsection
# --- nesting. The C1 fix's `_subsection_contains_offset` live-path branch
# --- compares ONLY `mention_path[0].value` -- the OUTERMOST sub-article
# --- step -- against a subsection-scoped definition's `scope_value`. The
# --- Developer traced `resolve_unit_path`'s replace-ancestor/push-new-
# --- rung stack semantics by hand for ONE level ("(a)" vs "(b)") only.
# --- Per seam v2.4 §3 there is explicitly NO depth cap (the real US
# --- federal 8-level ladder is measured, at scale). This test exercises
# --- genuine 3-level nesting -- (a)>(1)>(A) -- both directions: a
# --- definition scoped to outermost subsection "a" must cover a mention
# --- buried 2 levels deeper inside it ((a)(1)(A)), and must NOT cover an
# --- identical-term mention buried the SAME depth under a DIFFERENT
# --- outermost sibling ((b)(1)(A)).
def test_a_subsection_scoped_definition_covers_a_mention_nested_three_levels_deep_under_it_but_not_an_identical_sibling_mention_at_the_same_depth_live(
    db_session, matter_with_users
):
    """C1 + D-ANCHOR no-depth-cap (seam v2.4 §3): a definition scoped to
    outermost subsection "a" of an article must govern a mention nested
    (a)>(1)>(A) deep inside it (three real marker levels: lower_alpha,
    digit, upper_alpha), and must NOT govern an identical-term mention
    nested (b)>(1)>(A) -- same depth, different outermost sibling.

    Discriminator (same reasoning as the strengthened test above, needed
    for the same dedup-key-has-no-char_offset reason): the out-of-scope
    (b)(1)(A) mention is placed BEFORE the in-scope (a)(1)(A) mention in
    the fixture's own text, so an over-inclusive bug would let (b) win
    the single-assertion dedup race and the surviving assertion would
    resolve to subsection 'b', not 'a' -- `get_mention_unit_paths` catches
    that directly.

    Fixture-construction note: the definition-trigger sentence and every
    mention's surrounding prose are written with ZERO parenthesized
    letter/digit tokens of their own (no "(b)(1)(A)"-style inline
    notation) -- `resolve_unit_path` scans the WHOLE article body's
    `_US_UNIT_MARKER_RE` matches unconditionally, so any incidental
    `(x)`-shaped text in descriptive prose is indistinguishable from a
    real structural marker and corrupts the stack for every mention
    positioned after it. Verified directly against the real regex before
    settling on this wording (an earlier draft that spelled out
    "(b)(1)(A)" in an explanatory clause produced a corrupted, truncated
    path from that self-inflicted pollution, not from a real defect)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.definition_links.extract import DefinitionCandidate
    from app.models.assertion import Assertion

    def _extract(article_body, ctx):
        import re

        pattern = re.compile(
            r'"([^"]+)" governs only within subsection a of this section, '
            r"three marker levels deep and below, and means "
            r"(.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="a",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(
        ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    )

    m = matter_with_users
    term = "Nested widget"
    wiki_text = (
        f'@ 30. Deeply nested subsection article\n'
        f'"{term}" governs only within subsection a of this section, '
        f"three marker levels deep and below, and means an item "
        f"regulated only at that specific depth.\n"
        f"(b) Sibling subsection, out of scope entirely.\n"
        f"(1) A nested numbered clause under the sibling subsection.\n"
        f"(A) A {term} is mentioned here, deep under the sibling "
        f"subsection -- a sibling at the SAME depth as the in-scope "
        f"mention below, but under a DIFFERENT outermost subsection.\n"
        f"(a) The actually-scoped subsection.\n"
        f"(1) A nested numbered clause under the scoped subsection.\n"
        f"(A) A {term} is mentioned here too, deep under the scoped "
        f"subsection -- genuinely three marker levels below the "
        f"outermost scoped subsection.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test Deep Subsection Nesting Statute",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "a scope='subsection' definition scoped to outermost subsection "
        "'a' must link the mention nested (a)(1)(A) deep inside it -- got "
        f"ZERO USES_DEFINITION assertions. created_assertions="
        f"{result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, (
        "expected exactly ONE USES_DEFINITION assertion (dedup key has no "
        f"char_offset component). Got {uses_edges!r}"
    )

    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], (
        f"expected a single, non-empty sub-article unit path; got {paths!r}"
    )
    resolved_path = paths[0]
    assert len(resolved_path) >= 3, (
        "expected genuine 3-level nesting (lower_alpha > digit > "
        f"upper_alpha) to be resolved, not a shallow/capped path. Got "
        f"resolved_path={resolved_path!r}"
    )
    assert resolved_path[0].value == "a", (
        "the surviving assertion's own recorded mention position must be "
        "anchored under outermost subsection 'a' -- the ONLY in-scope "
        "sibling, 3 levels deep. If this resolves to 'b', containment is "
        "over-inclusive at depth (it let the (b)(1)(A) sibling mention "
        f"win instead of excluding it). Got resolved_path={resolved_path!r}"
    )


# --- QA-fail cycle 2, independent QA verification (re-QA cycle 2, Area 1
# --- close-out): the C1 fix threads `profile` through
# --- `definition_covers_mention`/`link_articles_to_definitions`, bound at
# --- `pipeline.py` Stage 3 via `profile = _profile_for_document(document_id)`
# --- INSIDE the per-document loop. The manager's Round 18 log entry records
# --- checking this by READING the source ("bound PER DOCUMENT... not a stale
# --- binding leaking across documents") but no committed test exercises TWO
# --- documents of DIFFERENT jurisdictions in the SAME `run_definition_linking`
# --- call to prove it live. Mutation-tested by this QA cycle (temporarily
# --- hoisting the Stage 3 `profile` lookup to always resolve the FIRST
# --- document's profile via `git checkout --`-reverted edits) -- confirmed
# --- this test goes RED under that specific leak shape. -----------------------


def test_profile_binding_does_not_leak_across_documents_in_one_multi_jurisdiction_run_live(
    db_session, matter_with_users
):
    """One matter, ONE `run_definition_linking` call, TWO documents of
    DIFFERENT jurisdictions (a Hebrew IL law and a US-DE statute). If
    `pipeline.py` Stage 3's per-document `profile` binding ever leaked
    (e.g. a future edit hoists the `_profile_for_document(document_id)`
    call outside the per-document loop, or an iteration-order bug reuses a
    stale reference), the WRONG profile would be used for one of the two
    documents:

    - The IL document's mention uses a Hebrew prefix-letter surface form
      ("ב" + term, construct-state) that ONLY `matcher.find_term_uses`
      (Hebrew's own engine) recognizes -- `USProfile.find_term_uses`'s
      plain `\\b`-word-boundary English matcher would not produce this
      surface-form match at all.
    - The US document's mention is `scope="subsection"`-scoped; a leaked
      Hebrew profile would call `HebrewProfile.resolve_unit_path`, which
      returns at most a single Hebrew-marker step (profiles.py's own
      `_IL_SUBSECTION_MARKER_RE`) and would not recognize the US federal
      lettered-marker ladder `USProfile.resolve_unit_path` uses -- so the
      subsection containment check would silently fail differently.

    Both directions are checked: the Hebrew mention must link at all (proves
    Hebrew's own matcher ran for the IL document), and the US mention must
    resolve to the correct subsection 'b' specifically (proves USProfile's
    own `resolve_unit_path` ran for the US document, not Hebrew's, AND that
    subsection containment still discriminates correctly when interleaved
    with a second document in the same run)."""
    import re

    from app.definition_links.extract import DefinitionCandidate
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.models.assertion import Assertion

    m = matter_with_users

    il_term = "מונח עברי"
    il_wiki_text = (
        f'@ 1. נושא\n'
        f'לענין זה, "{il_term}" - הגדרה מקומית.\n'
        f"נעשה שימוש ב{il_term} כאן.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק בדיקה עברי לבידוד פרופיל",
        wiki_text=il_wiki_text,
    )

    us_term = "Isolation widget"

    def _extract(article_body, ctx):
        pattern = re.compile(
            r'"([^"]+)" applies only within subsection \(b\) of this '
            r"section, and means (.*?)(?=\.\s|$)",
            re.IGNORECASE | re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="b",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))

    us_wiki_text = (
        f'@ 12. Target section\n'
        f'"{us_term}" applies only within subsection (b) of this section, '
        f"and means a specially regulated item.\n"
        f"(a) An {us_term} is mentioned here, in subsection (a), for contrast.\n"
        f"(b) An {us_term} is mentioned here, in subsection (b), where it is "
        f"actually defined.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test Isolation Statute",
        wiki_text=us_wiki_text,
        jurisdiction="US-DE",
    )

    # ONE run_definition_linking call processes BOTH documents.
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]

    il_edges = [e for e in uses_edges if il_term in e["proposition"]]
    assert il_edges, (
        "Hebrew document's mention did not link -- possible cross-document "
        f"profile leak (US profile applied to the IL document). "
        f"uses_edges={uses_edges!r}"
    )

    us_edges = [e for e in uses_edges if us_term in e["proposition"]]
    assert len(us_edges) == 1, f"expected exactly one US edge, got {us_edges!r}"
    assertion_row = db_session.get(Assertion, us_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert paths and paths[0] and paths[0][0].value == "b", (
        "US document's subsection containment mis-resolved in a "
        f"multi-document run -- possible cross-document profile leak. "
        f"paths={paths!r}"
    )
