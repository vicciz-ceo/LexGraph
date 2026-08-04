"""RED integration test -- sprint 2026-08-04-defs-us-markers, planner pass
3, priority 5 (ruling U-R8).

U-R8's directive: mojibake repair must happen INSIDE this family's own
`EntrySplitterRule`/`TermClauseRule` (no registry seam exists for
normalization). Its named risk: repair done only inside a rule's own
`split`/`parse` callable would not reach Stage 3 term-matching
(`find_term_uses` against article bodies, which are never re-normalized
by a rule -- only `USProfile.normalize_for_parsing`, a SHARED method, and
that is confirmed NOT to touch AK's real cp1252 control bytes), so a term
extracted from a mojibake body might fail to link to its own mentions
elsewhere in the same document. Directive: author a live-path test
asserting a mojibake-body definition actually LINKS to a mention (a
`USES_DEFINITION` assertion) -- escalate if it cannot be made green under
rule-internal repair alone.

**This test could not be evaluated against a real candidate implementation
this pass -- escalated instead (see sprint log `## P3`), for a reason
UPSTREAM of and MORE FUNDAMENTAL than the linking risk U-R8 named:**
`entry_splitter_rules_for`/`term_clause_rules_for` (`rules/registry.py`)
are registered-and-lookupable but consulted by NO production code path
anywhere in this codebase (verified: `grep -rn` across all of
`backend/app` for both names outside `registry.py` itself and its own
unit test returns zero hits). Only `ScopeTriggerRule` and `CitationRule`
are actually wired end-to-end; `HeadingRule`, `BodyPreambleRule`,
`EntrySplitterRule`, `TermClauseRule`, and `StructuralUnitRule` are not.
A scratch investigative script (not committed) confirmed this directly: a
hand-registered `EntrySplitterRule`+`TermClauseRule` pair for `US-AK`,
targeting this exact fixture's mojibake shape, produced ZERO extracted
candidates when run through the real `run_definition_linking` path --
`extract_definitions_from_section` (`us_profile.py`) never asks the
registry for either kind. So U-R8's Stage-3-matching risk remains
genuinely UNTESTED (neither confirmed nor refuted) pending that wiring
gap's resolution -- this test pins the REQUIRED final behavior (extraction
AND linking, not merely `len(...) > 0`) so it is ready to run the moment
the gap is closed, but is not evidence either way about the Stage-3 risk
itself yet.

Real rows, both already vendored/verified this pass: the mojibake
Definitions row is the ALREADY-COMMITTED
`us_markers_wave2_subcases_rows.json` row `STATE_AK_T44_C44.42_S44.42.900`
(cp1252 `\\x93`/`\\x94` control bytes, byte-verified pass 2); the mention
row is NEW this pass, `STATE_AK_T44_C44.42_S44.42.220` (same chapter
44.42, real AK "Meetings; hearings; records." section, genuinely mentions
"the commissioner" in running prose with no mojibake at all), vendored
into `us_markers_nc_and_ak_mention_rows.json`, byte-verified against the
source parquet this pass.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.assertion import Assertion
from app.models.definition import Definition

WAVE2_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_wave2_subcases_rows.json"
)
MENTION_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_nc_and_ak_mention_rows.json"
)


def _load(path: Path) -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))}


def test_real_ak_mojibake_definition_links_to_a_real_plain_text_mention(
    db_session, matter_with_users
):
    """Both rows live in the SAME real AK chapter (44.42): the Definitions
    section (`S44.42.900`) defines "commissioner" (mojibake-quoted) and
    "department"; the mention row (`S44.42.220`) genuinely uses "the
    commissioner" in ordinary prose, with no mojibake at all. Once
    "commissioner" is extracted (clean ASCII term, mojibake bytes stripped
    by whatever rule repairs them), `find_term_uses("commissioner", ...)`
    is a plain `\\b`-word-boundary regex over EVERY article body in the
    document (`matcher.py`) -- it does not require the MENTION's own body
    to be mojibake-free, only the extracted TERM string to be. This test
    requires BOTH a `Definition` row for "commissioner" AND a
    `USES_DEFINITION` assertion whose subject is the mention article --
    "captured" per ruling U-R1 means linked, not merely extracted."""
    def_row = _load(WAVE2_FIXTURE)["STATE_AK_T44_C44.42_S44.42.900"]
    mention_row = _load(MENTION_FIXTURE)["STATE_AK_T44_C44.42_S44.42.220"]

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="AK mojibake definition-links-to-mention",
        rows=[
            {k: v for k, v in def_row.items() if not k.startswith("_")},
            {k: v for k, v in mention_row.items() if not k.startswith("_")},
        ],
        jurisdiction="US-AK",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term = {t: d for d in definitions for t in d.terms}
    assert "commissioner" in by_term, (
        f"expected \"commissioner\" to be extracted from the mojibake-quoted AK "
        f"Definitions section; got {sorted(by_term)!r}"
    )
    commissioner_definition = by_term["commissioner"]

    assertions = [db_session.get(Assertion, a["id"]) for a in result["created_assertions"]]
    uses_definition = [a for a in assertions if a.assertion_type == "USES_DEFINITION"]
    linking_to_commissioner = [
        a
        for a in uses_definition
        if a.object_entity_type == "Definition"
        and a.object_entity_id == commissioner_definition.id
    ]
    assert linking_to_commissioner, (
        '"commissioner" was extracted but no USES_DEFINITION assertion links the '
        "real mention row (S44.42.220, \"...as requested by the commissioner...\") "
        "to it -- extraction without linking is not \"captured\" per ruling U-R1. "
        f"all USES_DEFINITION assertions: "
        f"{[(a.subject_entity_id, a.object_entity_id) for a in uses_definition]!r}"
    )
