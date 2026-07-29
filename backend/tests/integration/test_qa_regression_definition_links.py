"""QA regression coverage — sprint 2026-07-29-definition-links.

Independent QA pass (separate agent from every Developer on this sprint).
These tests close edge-case gaps not already exercised by the Developer's
per-item tests (DL1-DL7, DL9, DL10 -- every item that PASSED this QA cycle;
DL8 is bounced separately by
`test_definition_links_pipeline_dual_unresolved_derivation.py`), following
the existing pattern in `test_qa_regression_local_first_platform.py`:

- DL1: `Definition.parent_definition_id`'s self-referential nested-definition
  link persists and reads back through the ORM (not just a raw-SQL row) --
  the Developer's own model test seeds via raw SQL; this exercises the
  actual mapped relationship end to end.
- DL2: `normalize_for_parsing` composes ALL of niqqud-stripping, curly-quote
  collapsing, and maqaf-collapsing correctly in a SINGLE call over one
  string, not merely in isolation (each transformation has its own
  Developer test; the composition itself was untested).
- DL5: two of the review doc's 8 documented `"מאגר מידע"` surface forms
  that the Developer's own matcher tests never exercised
  (`במאגרי מידע` -- prefix + construct-plural combined; `מאגרי המידע` --
  construct-plural + definite-article-insertion combined; `שבמאגר המידע` --
  stacked two-letter prefix).
- DL6: `כאמור בחוק` (dossier trigger-phrase table: "rare, ... treat like
  `לפי חוק`" -- i.e. NOT a cross-law-derivation trigger) must NOT be
  detected as a derivation edge. No existing test asserts this negative
  case for this specific phrase.
- DL7: ingesting the SAME wiki text into the SAME matter twice via
  `ingest_wiki_law` creates two INDEPENDENT `Document` rows (ingestion
  itself performs no dedup) -- confirms idempotency is a pipeline-level
  concern (DL8), not silently assumed at the ingest layer.
- DL9: the CLI's `--triggered-by-user-id` argument is genuinely required --
  omitting it is an argparse usage error (exit code 2), not a silent
  no-op.
- DL10: the fix is verified at the INSTALLED-PACKAGE level, not just in
  `pyproject.toml`'s text -- `importlib.metadata.version("mcp")` in this
  exact venv must be less than 2.0.

QA cycle 2 (DL8 fix re-verify, commit 2f27703):

- DL8: the corroborated resolved-target variant of the identity-key
  collapse -- distinct from `test_definition_links_pipeline_dual_unresolved_derivation.py`'s
  synthetic 2-edge UNRESOLVED-target regression, which cycle 1's RED pin
  already covers. This exercises the REAL vendored fixtures: ingesting
  `חוק המחשבים_stub.wiki` then `חוק הגנת הפרטיות_excerpt.wiki` into the
  same matter must persist THREE `DERIVES_FROM_LAW` assertions for the
  3-term definition at line 17 ("חומר מחשב", "מחשב" ו"פלט" - כהגדרתם
  [[בחוק המחשבים]]) -- one per term, each naming its term in the
  proposition and each RESOLVING (`object_entity_type="Document"`) to the
  ingested חוק המחשבים `Document` row -- plus idempotency: a second
  pipeline run over the same matter creates zero new assertions/definitions
  and leaves the persisted link set unchanged.

QA cycle 3 (DL12/DL13 re-verify; DL11 bounced -- see
`test_definition_links_matcher.py`'s
`test_link_articles_to_definitions_does_not_cross_suppress_duplicate_numbered_articles_with_overlapping_offsets`
for that cycle's `[QA-FAIL]` RED pin, not duplicated here):

- DL12: a FRESH real-corpus repeal-marker entry the Developer's own tests
  never touched -- `פקודת רופאי השיניים.wiki:22`'s `"מחלה מסכנת" -
  (((נמחקה);))` (Developer's fixtures only exercised `חוק החברות`'s
  `"בית המשפט"` and `חוק הבנקאות (שירות ללקוח)`'s vendored entry) --
  confirms the guard generalizes across documents, not just the two
  corpus laws already vendored.
- DL13: a FRESH real-corpus paren-qualified cross-law reference the
  Developer's own tests never touched -- `צו בנק ישראל (מידע בעניין
  יתרות ניירות ערך).wiki:27`'s `"קופת גמל", "קרן השתלמות", "קרן פנסיה" -
  כהגדרתן [[בחוק הפיקוח על שירותים פיננסיים (קופות גמל), התשס"ה-2005]]`
  (Developer's tests only exercised `חוק הבנקאות`/`חוק מיסוי מקרקעין`/
  `חוק הסעד` paren-qualifier resolutions) -- confirms the widened
  `_LAW_REF_RE` generalizes to a different target law family
  (`חוק הפיקוח על שירותים פיננסיים`), independently named in
  poc-run.md §8 Issue 3 as the OTHER law accounting for the bulk of the
  unresolved-derivation gap.
"""

from __future__ import annotations

import importlib.metadata
import pathlib

import pytest


# --- DL1: nested Definition self-reference through the real ORM ------------


def test_definition_parent_definition_id_round_trips_through_the_orm(
    db_session, matter_with_users
):
    from app.models.definition import Definition
    from tests.conftest import seed_article, seed_document, seed_source_span

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])
    article_id = seed_article(
        db_session, document_id=doc_id, matter_id=m["matter_id"], source_span_id=span_id
    )

    outer = Definition(
        id="outer-def-1",
        document_id=doc_id,
        matter_id=m["matter_id"],
        article_id=article_id,
        terms=["מידע אישי"],
        definition_text="נתון הנוגע לאדם מזוהה...",
        scope="law-wide",
    )
    db_session.add(outer)
    db_session.flush()

    inner = Definition(
        id="inner-def-1",
        document_id=doc_id,
        matter_id=m["matter_id"],
        article_id=article_id,
        terms=["אדם הניתן לזיהוי"],
        definition_text="מי שניתן לזהותו...",
        scope="local",
        parent_definition_id=outer.id,
    )
    db_session.add(inner)
    db_session.commit()

    fetched_inner = db_session.get(Definition, "inner-def-1")
    assert fetched_inner.parent_definition_id == "outer-def-1"
    fetched_outer = db_session.get(Definition, fetched_inner.parent_definition_id)
    assert fetched_outer.terms == ["מידע אישי"]


# --- DL2: normalize_for_parsing composes all Stage 0 steps together --------


def test_normalize_for_parsing_composes_niqqud_curly_quotes_and_maqaf_in_one_call():
    from app.definition_links.normalize import normalize_for_parsing

    raw = 'הַגְדָּרָה: “מָנוֹחַ” – מֻנָּח כְּלָלִי, וְ“מוּעֶדֶת־'
    out = normalize_for_parsing(raw)

    # niqqud (U+0591-U+05C7) fully stripped
    assert not any(0x0591 <= ord(ch) <= 0x05C7 for ch in out)
    # curly quotes collapsed to the plain quote class
    assert "“" not in out and "”" not in out
    assert '"' in out
    # en dash and maqaf both collapsed to canonical hyphen
    assert "–" not in out and "־" not in out
    assert "-" in out


# --- DL5: uncovered documented surface forms of "מאגר מידע" ----------------


@pytest.mark.parametrize(
    "text,expected_surface",
    [
        ("המידע מאוחסן במאגרי מידע שונים ברחבי הארץ.", "במאגרי מידע"),
        ("כל מאגרי המידע נבדקים אחת לשנה.", "מאגרי המידע"),
        ("הנתונים שבמאגר המידע חסויים.", "שבמאגר המידע"),
    ],
)
def test_find_term_uses_matches_additional_documented_surface_forms(text, expected_surface):
    from app.definition_links.matcher import find_term_uses

    matches = find_term_uses("מאגר מידע", text)
    surfaces = [m.group(0) for m in matches]
    assert expected_surface in surfaces


# --- DL6: 'כאמור בחוק' is excluded from the derivation-trigger set ----------


def test_kaamur_bachok_does_not_trigger_a_cross_law_derivation():
    from app.definition_links.derivation import detect_cross_law_derivations

    text = "התשלום ישולם כאמור בחוק התקציב, התשפ״ה-2025."
    edges = detect_cross_law_derivations(text, source_term="תשלום", known_law_titles={})
    assert edges == []


# --- DL7: ingest_wiki_law performs no dedup -- that's a pipeline concern ----


def test_ingest_wiki_law_twice_into_the_same_matter_creates_two_independent_documents(
    db_session, matter_with_users
):
    import pathlib

    from app.definition_links.ingest import ingest_wiki_law

    m = matter_with_users
    fixtures = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"
    wiki_text = (fixtures / "חוק להגנת רכוש מופקד.wiki").read_text(encoding="utf-8")

    first = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=wiki_text,
    )
    second = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=wiki_text,
    )

    assert first["document_id"] != second["document_id"]
    assert len(first["article_ids"]) == len(second["article_ids"]) > 0
    assert set(first["article_ids"]).isdisjoint(second["article_ids"])


# --- DL9: --triggered-by-user-id is a genuinely required CLI argument ------


def test_cli_missing_triggered_by_user_id_is_an_argparse_usage_error(matter_with_users):
    from app.definition_links.cli import main

    m = matter_with_users
    with pytest.raises(SystemExit) as exc_info:
        main(["--matter-id", m["matter_id"]])
    assert exc_info.value.code == 2


# --- DL10: the installed package, not just pyproject.toml's text -----------


def test_installed_mcp_package_version_is_pinned_below_2_0():
    version = importlib.metadata.version("mcp")
    major = int(version.split(".")[0])
    assert major < 2, f"expected mcp<2.0 installed, got {version}"


# --- DL8 (QA cycle 2): 3-term resolved-target identity-key regression ------


def test_three_term_shared_derivation_clause_persists_three_resolved_edges(
    db_session, matter_with_users
):
    """Vendored-fixture corroboration of the cycle-1 `[QA-FAIL]` (see
    docs/sprint/sprints/2026-07-29-definition-links-log.md, "DL8 QA-FAIL
    rationale"): before commit 2f27703, the definition at
    `חוק הגנת הפרטיות_excerpt.wiki` line 17 -- three terms ("חומר מחשב",
    "מחשב", "פלט") sharing one derivation clause to `[[בחוק המחשבים]]` --
    collapsed to a SINGLE persisted `DERIVES_FROM_LAW` assertion, because
    the pre-fix idempotency key omitted `proposition` and every term's
    edge shared the same (subject Definition, resolved object Document)
    pair. Post-fix, each term's distinct proposition keeps its edge
    separate: exactly three assertions, one per term, all resolving to
    the same ingested Document.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    fixtures = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"

    computers_text = (fixtures / "חוק המחשבים_stub.wiki").read_text(encoding="utf-8")
    privacy_text = (fixtures / "חוק הגנת הפרטיות_excerpt.wiki").read_text(encoding="utf-8")

    # Ingest the target law FIRST so `known_law_titles` resolves it.
    computers_doc = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק המחשבים, התשנ"ה-1995',
        wiki_text=computers_text,
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הגנת הפרטיות, התשמ"א-1981',
        wiki_text=privacy_text,
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    computer_derives = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "DERIVES_FROM_LAW"
        and any(f'"{t}"' in a["proposition"] for t in ("חומר מחשב", "מחשב", "פלט"))
    ]
    assert len(computer_derives) == 3, computer_derives

    for term in ("חומר מחשב", "מחשב", "פלט"):
        matches = [a for a in computer_derives if f'"{term}"' in a["proposition"]]
        assert len(matches) == 1, f"expected exactly 1 edge naming {term!r}, got {matches}"
        row = db_session.get(Assertion, matches[0]["id"])
        assert row.object_entity_type == "Document"
        assert row.object_entity_id == computers_doc["document_id"]

    # Idempotency under the new (proposition-inclusive) key: a second run
    # over the same, unchanged matter creates nothing new and leaves the
    # persisted assertion set unchanged.
    before_keys = {
        (row.assertion_type, row.subject_entity_id, row.object_entity_id, row.proposition)
        for row in db_session.query(Assertion).filter(Assertion.matter_id == m["matter_id"]).all()
    }

    result2 = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert result2["created_assertions"] == []
    assert result2["created_definitions"] == []

    after_keys = {
        (row.assertion_type, row.subject_entity_id, row.object_entity_id, row.proposition)
        for row in db_session.query(Assertion).filter(Assertion.matter_id == m["matter_id"]).all()
    }
    assert after_keys == before_keys


# --- QA cycle 3: DL12 re-verify, a fresh real-corpus document -------------


def test_repeal_marker_guard_rejects_a_fresh_corpus_law_not_used_in_developer_tests():
    """Real corpus clause (verbatim, `פקודת רופאי השיניים.wiki:20-23`) --
    a document never touched by DL12's own Developer tests (which only
    vendored `חוק החברות` and `חוק הבנקאות (שירות ללקוח)`):

        :- "המנהל" - המנהל הכללי של משרד הבריאות, ...;
        :- "השר" - שר הבריאות;
        :- "מחלה מסכנת" - (((נמחקה);))
        :- "מרפא שיניים" - מורשה לריפוי שיניים לפי [[סעיף 2(2)]];

    "מחלה מסכנת" ("dangerous disease") is a REAL repealed definitions
    entry in a law the Developer never vendored -- confirms the guard
    generalizes past the two corpus laws already covered, while its three
    genuine siblings in the same block are unaffected.
    """
    from app.definition_links.extract import extract_definitions_from_section

    text = (
        ':- "המנהל" - המנהל הכללי של משרד הבריאות, לרבות משנהו וכל נושא משרה '
        "במשרד הבריאות שהמנהל מינה אותו למלא תפקידים על פי פקודה זו;\n"
        ':- "השר" - שר הבריאות;\n'
        ':- "מחלה מסכנת" - (((נמחקה);))\n'
        ':- "מרפא שיניים" - מורשה לריפוי שיניים לפי סעיף 2(2);\n'
    )

    candidates = extract_definitions_from_section(text, scope="law-wide")
    all_terms = {t for c in candidates for t in c.terms}

    assert "מחלה מסכנת" not in all_terms
    assert {"המנהל", "השר", "מרפא שיניים"} <= all_terms


# --- QA cycle 3: DL13 re-verify, a fresh real-corpus paren-qualified law ---


def test_law_ref_paren_qualifier_resolves_a_fresh_corpus_target_law_not_used_in_developer_tests():
    """Real corpus clause (verbatim, `צו בנק ישראל (מידע בעניין יתרות ניירות
    ערך).wiki:27`) -- a target law family (`חוק הפיקוח על שירותים
    פיננסיים`) DL13's own Developer tests never referenced (which only
    exercised `חוק הבנקאות`/`חוק מיסוי מקרקעין`/`חוק הסעד` paren-qualifier
    resolutions), and independently named in poc-run.md §8 Issue 3 as the
    OTHER law family (alongside חוק הבנקאות) responsible for the bulk of
    the corpus's unresolved-derivation gap:

        :- "קופת גמל", "קרן השתלמות", "קרן פנסיה" - כהגדרתן
        [[בחוק הפיקוח על שירותים פיננסיים (קופות גמל), התשס"ה-2005]];

    Confirms the widened `_LAW_REF_RE` (one balanced parenthetical +
    trailing year-clause) generalizes beyond the specific laws the
    Developer's own tests happened to pick.
    """
    from app.definition_links.derivation import detect_cross_law_derivations

    text = (
        '"קופת גמל", "קרן השתלמות", "קרן פנסיה" - כהגדרתן בחוק הפיקוח על '
        'שירותים פיננסיים (קופות גמל), התשס"ה-2005;'
    )

    edges = detect_cross_law_derivations(
        text,
        source_term="קופת גמל",
        known_law_titles={
            "חוק הפיקוח על שירותים פיננסיים (קופות גמל)": "law-pikuach-kupot-gemel-id"
        },
    )

    assert len(edges) == 1
    assert edges[0].target_law_id == "law-pikuach-kupot-gemel-id"
    assert edges[0].target_law_name == "חוק הפיקוח על שירותים פיננסיים (קופות גמל)"
