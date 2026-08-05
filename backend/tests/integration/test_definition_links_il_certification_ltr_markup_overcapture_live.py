"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, Round 2,
ruling M33-4 (panel manager, `2026-08-05-defs-il-certification-log.md`).

**The finding, and why it matters more than a recall gap.** Round 1's C2
backbone test found 15 spans that are BOTH `wiki_table_markup_attribute`
AND `production_captured` -- a genuine precision defect, not a test bug.
The panel manager re-ran the real dispatch independently and found the
true size: **19 candidates, 8 of them spurious**, for ONE article,
including a single `DefinitionCandidate` carrying **seven** `'ltr'`
terms at once. Ruling M33-4: "precision defects outrank recall gaps in a
legal product... it is mechanically bounded and needs a Planner-authored
RED before any fix" -- this file is that RED.

## Root cause, traced precisely (not merely "markup confuses the
## parser")

`צו המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)` art.1 (heading
`הגדרות`) defines `"תחום המועצה"` (the council's territory) as ONE
multi-line `:-` entry whose continuation lines are `::-`-prefixed land-
block ("גוש") rows -- baseline `extract._split_into_blocks` correctly
treats this whole thing as ONE block (`::-` lines do not start a new
block; only `:-` does), so baseline alone produces the correct single
`DefinitionCandidate(terms=('תחום המועצה',), ...)`.

But a registered `EntrySplitterRule` (built for the D-1b `::-`-list-shape
class) ALSO recognizes each `::-` line as an INDEPENDENT block start, and
`profiles.HebrewProfile.extract_definitions_from_section` UNIONS
baseline's blocks with every registered splitter's blocks (by design,
for zero-miss recall -- see `profiles.py`'s own docstring). So the SAME
land-block list gets parsed TWICE: once correctly as part of the whole
`"תחום המועצה"` entry, and AGAIN, independently, one `::-` line at a
time. Most of those per-line re-parses correctly produce NO candidate
(`extract._parse_terms_and_qualifier` finds no quoted span in a plain
`גוש 39774 - ...` line, so `terms` is empty and `_parse_block` returns
`[]`). But EIGHT of those lines contain `<span dir="ltr">NNNNNN_N</span>`
markup -- a typographic wrapper forcing left-to-right digit rendering
inside an otherwise-RTL document, unrelated to any legal-drafting
convention -- and `dir="ltr"` itself contains a genuine `"..."`-quoted
span. `extract._QUOTE_RE` cannot distinguish a legal drafting quote from
an HTML attribute quote, so each such line's OWN independent re-parse
manufactures a spurious `DefinitionCandidate(terms=('ltr',...))`. This
is the SAME `wiki_table_markup_attribute` pattern C2's own span
classification already names (`clusters.py`) for the unrelated MediaWiki
table-header case -- here it additionally interacts with an
EntrySplitterRule's own union-of-blocks design to produce a REAL,
persisted, false `Definition` row, not merely a mis-tagged candidate.

## What this test asserts, and why it is a RED, not a proposal for how
## to fix it

Per M33-4's own instruction ("author its RED before any fix... a
Developer will fix"), this test pins the DESIRED end state without
prescribing the mechanism: no `'ltr'` term is ever captured from this
article, while every GENUINE definition (11 of them, including the
multi-line `"תחום המועצה"` entry itself, definition_text intact) is
still captured. It deliberately does NOT assert anything about
`EntrySplitterRule`'s own union design in general (a legitimate,
zero-miss-motivated mechanism for the `::-`-list-shape class this same
rule correctly serves elsewhere) -- only that ITS OWN re-parse of a line
whose only quoted content is an HTML attribute must not manufacture a
term.

## Fixture

Real, unedited, byte-verified excerpt (verified independently before
AND after writing the vendored copy, both against the real corpus file):
`צו המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)_art1_excerpt.wiki`
-- article 1 in full, `@ 1. הגדרות...` marker line through the line
before the next `==` heading break, programmatically sliced, nothing
hand-edited.
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_span_dir_ltr_markup_must_never_be_captured_as_a_defined_term_live(
    db_session, matter_with_users
):
    """Live re-confirmation (this Planner, before writing this test):
    running the real, unmodified `run_definition_linking` over this exact
    fixture today produces a `Definition` row whose `terms` include
    `'ltr'` -- a spurious "definition" sourced from `dir="ltr"` HTML-
    table markup, not Hebrew legal-drafting text. Expected RED: today's
    `created_definitions` contains an `'ltr'`-bearing row; the assertion
    below is the desired FUTURE state, not today's.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="צו המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)",
        wiki_text=_read(
            "צו המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)_art1_excerpt.wiki"
        ),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    ltr_definitions = [d for d in result["created_definitions"] if "ltr" in d["terms"]]
    assert ltr_definitions == [], (
        f"expected ZERO Definition rows with 'ltr' among their terms -- "
        f"'ltr' is an HTML dir= attribute value from <span dir=\"ltr\">"
        f"NNNNNN_N</span> markup wrapping land-block numbers, never a "
        f"Hebrew legal-drafting term; got {ltr_definitions!r}"
    )


def test_genuine_definitions_in_the_same_article_survive_the_fix_live(
    db_session, matter_with_users
):
    """Sanity control (both directions, same discipline as this sprint's
    other containment tests): whatever fixes the 'ltr' over-capture must
    not blunt-force the whole article to zero. All 11 genuine
    `:-`-prefixed entries -- including the multi-line `"תחום המועצה"`
    entry whose OWN correct parse is what the buggy EntrySplitterRule
    re-parses per-line -- must still be captured, with `"תחום המועצה"`'s
    definition_text still containing the real land-block list content
    (`'בשלמותם'`, the closing word of its first continuation line).
    Live re-confirmation (this Planner): today's real run already
    captures all 11 correctly, ALONGSIDE the 8 spurious ones -- this
    test is a control that stays green through the fix, not a second RED.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="צו המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)",
        wiki_text=_read(
            "צו המועצות המקומיות (מועצה מקומית תעשייתית נאות חובב)_art1_excerpt.wiki"
        ),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    all_terms: set[str] = set()
    for d in result["created_definitions"]:
        all_terms.update(d["terms"])

    expected_genuine_terms = {
        "המועצה",
        "תחום המועצה",
        "נכסים",
        "בעל",
        "מחזיק",
        "בנין",
        "קרקע תפוסה",
        "אדמת בנין",
        "השר",
        "השרים",
        "צו (א)",
    }
    missing = expected_genuine_terms - all_terms
    assert not missing, (
        f"expected every genuine defined term to survive whatever fixes "
        f"the 'ltr' over-capture; missing {missing!r} out of "
        f"{all_terms!r}"
    )

    territory_defs = [
        d for d in result["created_definitions"] if "תחום המועצה" in d["terms"]
    ]
    assert len(territory_defs) == 1, territory_defs
    # `created_definitions` (the pipeline's own return payload) carries
    # only id/terms/scope -- fetch the real persisted row for its
    # `definition_text`, matching how `get_mention_unit_paths` and other
    # retrieval code in this package reads back through the ORM rather
    # than the transient return dict.
    territory_row = db_session.get(Definition, territory_defs[0]["id"])
    assert territory_row is not None
    assert "בשלמותם" in territory_row.definition_text, (
        f"expected the multi-line 'תחום המועצה' entry's own definition "
        f"text to still contain its real land-block list content; got "
        f"{territory_row.definition_text!r}"
    )
