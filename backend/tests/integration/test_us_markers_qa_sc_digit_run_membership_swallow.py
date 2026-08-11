"""QA finding -- sprint 2026-08-10-green-the-suite, green-the-suite QA cycle.

Spot-checking 20 of the corpus-wide rows lengthened by issue #21's citation-
vs-marker discriminator (per the QA brief's own mandate: this population had
never been hand-checked and was named as "the discriminator's main risk"),
19/20 were genuine recoveries (mostly truncated citation-tail digits and
dropped internal-enumeration continuations). This ONE case is a genuine,
real over-capture -- confirmed byte-for-byte against the real corpus row
(`STATE_SC_T31_C3_A1_S31-3-20`, pulled verbatim from `us_sc_statutes.parquet`,
vaquill/open-us-law), not a hypothetical.

Root cause: `us_markers_boundary._digit_paren_run_internal_content_starts`
(issue #21's "digit-paren run's membership" mechanism) derives a WHOLE
consecutive digit-paren run's sibling-vs-internal status from what item 1
of that run opens with -- a quoted term or an ALL-CAPS label. This SC row's
run starts `(1) The term "director" shall mean the Secretary of Commerce;
(2) "Authority" ... (3) "Mayor" ... ... (15) "Persons of low income" means
...; and (16) "Obligee of the authority" or "obligee" shall include ...;
(17) "Persons of moderate to low income" means ...`. Item 1 opens with the
prose `The term "` (a quote preceded by two words), which is NEITHER a bare
leading quote (`_AFTER_MARKER_QUOTE_RE`) NOR an ALL-CAPS label
(`_ALL_CAPS_LABEL_OPEN_RE`) -- so the run-membership check misclassifies the
ENTIRE STRICTLY CONSECUTIVE run (2)-(17)+ as "internal enumeration content",
and every digit-paren marker in it loses its hard-stop protection. Item
(16)'s own idiom ("shall include") is not one `_TIGHT_IDIOM_RE` recognizes,
so (16) never becomes its own `starts` entry either -- with BOTH the
digit-marker hard-stop AND the quote+idiom boundary unavailable, item (15)
"Persons of low income" runs straight through the whole of (16) and only
stops at (17)'s own quote (which DOES carry a recognized "means" idiom).

This is the SAME family of defect issue #21 itself fixes (a genuine,
independently-defining entry wrongly absorbed into its neighbour), just
triggered by a run-opener shape ("The term "X" shall mean") the fix's own
opener detection doesn't recognize -- not a new, unrelated bug class.

Not filed as an xfail (D-GREEN-TRIAGE: this is a genuine content-swallow --
"Persons of low income" carries a whole unrelated definition's text glued
onto its own -- not a mere quality shortfall) and not one of this sprint's
7 named items' own scope, so it is pinned here as a new RED rather than
folded into any of their gate files.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_sc_digit_run_membership_swallow.json"
)

_ACT_ID = "STATE_SC_T31_C3_A1_S31-3-20"
_TERM = "Persons of low income"
_SWALLOWED_MARKER = "Obligee of the authority"


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == _ACT_ID)


def test_fixture_is_a_provenanced_verbatim_real_row_with_the_run_membership_shape():
    """Sanity: guards against this RED silently going vacuous if the
    fixture is ever edited. The row must still have its real Definitions
    heading, its own numbered-list run whose item 1 opens with `The term
    "..."` (not a bare quote), and both the victim and swallowed terms."""
    row = _load_row()
    assert is_definitions_heading(row["section_title"]) is True
    text = row["text"]
    assert 'The term "director" shall mean' in text, (
        "fixture's own item (1) no longer opens with the non-bare-quote "
        "prose shape this defect depends on -- test would be vacuous"
    )
    assert f'"{_TERM}"' in text
    assert f'"{_SWALLOWED_MARKER}"' in text
    # the swallowed marker's own item must sit AFTER the victim term in
    # the raw source, and use an idiom ("shall include") this engine's
    # _TIGHT_IDIOM_RE does not recognize -- both preconditions for the
    # swallow this test pins.
    assert text.index(f'"{_TERM}"') < text.index(f'"{_SWALLOWED_MARKER}"')
    assert '"obligee" shall include' in text


def test_real_pipeline_persons_of_low_income_does_not_swallow_the_next_unrelated_entry(
    db_session, matter_with_users
):
    """RED: through the REAL `ingest_us_statute_rows` -> `run_definition_
    linking` pipeline (the exact live path, not a stubbed call), `"Persons
    of low income"`'s persisted `definition_text` must end at its own real
    boundary (`"...beneficiary class"; and`) and must NOT contain any part
    of the unrelated `"Obligee of the authority"` entry that structurally
    follows it in the source. Today it does -- a genuine over-capture
    (content from a DIFFERENT term's definition glued onto this one), found
    via this sprint's own mandated spot-check of rows the #21 discriminator
    lengthened, confirmed byte-for-byte against the real corpus row."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="SC 31-3-20 (QA digit-run-membership swallow)",
        rows=[row],
        jurisdiction="US-SC",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list[Definition]] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d)

    assert _TERM in by_term, f"{_TERM!r} not captured at all -- got {sorted(by_term)!r}"
    texts = [d.definition_text for d in by_term[_TERM]]
    assert any(_SWALLOWED_MARKER not in t for t in texts), (
        f"{_TERM!r}: every captured definition_text illegally contains the "
        f"unrelated next entry {_SWALLOWED_MARKER!r} -- {texts!r}"
    )
    assert any(t.rstrip().endswith('"beneficiary class"; and') for t in texts), (
        f"{_TERM!r}: no captured definition_text ends at its own real boundary "
        f"(should end '...\"beneficiary class\"; and') -- {texts!r}"
    )
