"""RED tests -- sprint 2026-08-04-defs-core-scope, item I9 (manager ruling
M15).

The `profiles` seam (`backend/app/definition_links/profiles.py`) advertises
`normalize_for_parsing` as a profile-dispatched method -- the `Jurisdiction
Profile` Protocol declares it, `HebrewProfile.normalize_for_parsing` and
`USProfile.normalize_for_parsing` both implement it -- but on the LIVE
pipeline path (`app.definition_links.pipeline.run_definition_linking`) it
is dead code: `pipeline.py` calls the bare shared
`app.definition_links.normalize.normalize_for_parsing(raw_body)` directly,
and does so BEFORE the per-document profile is even resolved
(`_profile_for_document` is first called several lines later, for
`is_definitions_heading`). `grep -rn "profile\\.normalize_for_parsing"
backend/app/` returns nothing -- no call site anywhere reaches the profile
method.

Manager ruling M15: close this gap in the direction the spec already
promises (real dispatch), not by deleting the advertised method, because a
named family panel (recon dossier's family 3: AK's cp1252 mojibake curly
quotes) already needs a jurisdiction-specific `normalize_for_parsing`
override to work on the live path -- if dispatch stays dead, that panel's
override would silently do nothing, the worst failure mode (a mysterious
zero-yield, not an error).

These tests pin the CONTRACT -- "the live path dispatches through the
profile, per document, and a US-specific override actually changes
extraction, while Hebrew stays byte-identical" -- not any particular
internal call shape or line number, so they survive Developer #2's
in-flight `pipeline.py`/`profiles.py` refactor for I1/I2/I3.

Live path only: every test drives the real `ingest_wiki_law` /
`ingest_us_statute_rows` + `run_definition_linking` entrypoints against
in-memory fixture data (offline; no corpus reads, per ruling R6). No
function that is an acceptance target of this sprint is mocked/stubbed:
the "spy" tests below wrap a REAL profile method with a call-recording
wrapper that still delegates to (and returns) the real implementation, and
the mojibake-repair test registers a REAL, fully-functional profile
subclass through the profile registry (`profiles._REGISTRY`) -- the same
registration mechanism `profiles.py` itself uses to register `USProfile`
under every US jurisdiction code -- rather than mocking
`normalize_for_parsing`'s dispatch mechanics.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read_wiki(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_live_pipeline_dispatches_normalize_for_parsing_through_each_documents_own_profile(
    db_session, matter_with_users, monkeypatch
):
    """The live call-site test: pins that `run_definition_linking` reaches
    `profile.normalize_for_parsing(...)` -- not merely that the method
    exists (it already does, and is already dead) -- for BOTH an IL and a
    US document living side by side in the same matter, each routed
    through ITS OWN profile's method (never a single matter-wide one).

    Implemented as a "spy": the real `HebrewProfile.normalize_for_parsing`
    / `USProfile.normalize_for_parsing` implementations are wrapped to
    record their calls and then delegate to (and return) the original,
    unmodified implementation -- so this test observes dispatch without
    mocking away any real behavior.

    RED today: `pipeline.py` normalizes via the bare module-level
    `normalize.normalize_for_parsing(raw_body)` BEFORE any profile is
    resolved, so neither spy is ever invoked and both call lists stay
    empty.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.profiles import HebrewProfile
    from app.definition_links.us_profile import USProfile

    il_calls: list[str] = []
    us_calls: list[str] = []

    original_il_normalize = HebrewProfile.normalize_for_parsing
    original_us_normalize = USProfile.normalize_for_parsing

    def spy_il_normalize(self, text):  # noqa: ANN001 - test spy, mirrors real signature
        il_calls.append(text)
        return original_il_normalize(self, text)

    def spy_us_normalize(self, text):  # noqa: ANN001 - test spy, mirrors real signature
        us_calls.append(text)
        return original_us_normalize(self, text)

    monkeypatch.setattr(HebrewProfile, "normalize_for_parsing", spy_il_normalize)
    monkeypatch.setattr(USProfile, "normalize_for_parsing", spy_us_normalize)

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read_wiki("חוק להגנת רכוש מופקד.wiki"),
        jurisdiction="IL",
    )
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Title 9 (I9 dispatch probe)",
        rows=[
            {
                "act_id": "I9-DISPATCH-PROBE-1",
                "section_number": "9-101",
                "section_title": "Definitions",
                "text": '(1) "Widget" means a thing of value.',
                "chapter": "",
            }
        ],
        jurisdiction="US-DE",
    )

    run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    assert il_calls, (
        "HebrewProfile.normalize_for_parsing was never invoked on the live "
        "run_definition_linking path -- normalization is not dispatched through "
        "the IL document's own profile"
    )
    assert us_calls, (
        "USProfile.normalize_for_parsing was never invoked on the live "
        "run_definition_linking path -- normalization is not dispatched through "
        "the US document's own profile"
    )


def test_overriding_us_profile_normalize_for_parsing_changes_what_the_live_pipeline_extracts(
    db_session, matter_with_users, monkeypatch
):
    """The assertion that would have caught the dead-code bug: registering
    a REAL alternate `USProfile` subclass under `"US-DE"` -- one whose
    `normalize_for_parsing` repairs a realistic mojibake artifact (UTF-8
    curly-quote bytes mis-decoded as a single-byte codepage, the same
    FAMILY of defect recon dossier family 3 flags for AK's cp1252 mojibake
    curly quotes) -- must change what `run_definition_linking` actually
    extracts for a document under that code. Registered via
    `profiles._REGISTRY`, the exact mechanism `profiles.py` itself uses to
    register `USProfile` under every US jurisdiction code -- a real
    registration, not a mock of the dispatch seam under test.

    RED today: the bare shared normalizer (`app.definition_links.normalize
    .normalize_for_parsing`) that `pipeline.py` actually calls collapses
    ONLY genuine curly-quote Unicode codepoints (U+201C/U+201D) and never
    touches this mojibake byte sequence, and the registered profile is
    never consulted at all -- so the term is not extracted either before
    OR after the registry swap, and the second assertion below fails.
    """
    from dataclasses import dataclass

    from app.definition_links import profiles
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.us_profile import USProfile

    # A realistic mojibake artifact: real curly quotes, UTF-8 encoded, then
    # mis-decoded one byte at a time -- exactly the class of corruption
    # recon dossier family 3 documents for AK's real rows. Computed here
    # (not hand-typed illegible bytes) so the fixture is verifiably
    # reproducible.
    mojibake_open = "“".encode("utf-8").decode("latin-1")
    mojibake_close = "”".encode("utf-8").decode("latin-1")
    raw_text = f"(1) {mojibake_open}Widget{mojibake_close} means a thing of value."

    @dataclass(frozen=True)
    class _MojibakeRepairingUSProfile(USProfile):
        def normalize_for_parsing(self, text: str) -> str:
            return text.replace(mojibake_open, '"').replace(mojibake_close, '"')

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Title 9 (I9 mojibake probe)",
        rows=[
            {
                "act_id": "I9-MOJIBAKE-PROBE-1",
                "section_number": "9-102",
                "section_title": "Definitions",
                "text": raw_text,
                "chapter": "",
            }
        ],
        jurisdiction="US-DE",
    )

    # Baseline: the REAL, unmodified USProfile is registered for "US-DE" --
    # its normalize_for_parsing is a documented no-op passthrough for
    # plain English text, so the mojibake quotes are never repaired and no
    # "Widget" definition is extracted.
    baseline = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert not any("Widget" in d["terms"] for d in baseline["created_definitions"]), (
        "test setup invariant violated: the unmodified USProfile unexpectedly "
        "extracted 'Widget' from mojibake-quoted text"
    )

    # Register the mojibake-repairing profile for the SAME "US-DE" code and
    # re-run (idempotent re-run over the same, already-ingested Article).
    monkeypatch.setitem(
        profiles._REGISTRY, "US-DE", _MojibakeRepairingUSProfile(code="US-DE")
    )

    repaired = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert any("Widget" in d["terms"] for d in repaired["created_definitions"]), (
        "overriding USProfile.normalize_for_parsing for 'US-DE' had no effect on "
        "what the live pipeline extracted -- pipeline.py is not dispatching "
        "normalization through the resolved per-document profile"
    )


def test_live_pipeline_hebrew_normalization_stays_byte_identical_through_the_passthrough(
    db_session, matter_with_users, monkeypatch
):
    """The IL guard rail: once dispatch is wired, Hebrew must route through
    `HebrewProfile.normalize_for_parsing` (a real, called dispatch -- not
    just a coincidentally-matching output) AND produce EXACTLY the same
    counts already pinned by the passing
    `test_definition_links_pipeline_profile_dispatch.py::
    test_pipeline_produces_identical_hebrew_output_through_the_profile_dispatch_path`
    -- `HebrewProfile.normalize_for_parsing` is a byte-identical passthrough
    to the same shared function `pipeline.py` calls today, so correct
    dispatch must not change a single Hebrew number.

    RED today (for the dispatch half): the spy on `HebrewProfile.normalize
    _for_parsing` is never invoked, because `pipeline.py` calls the bare
    module function directly instead of going through the resolved
    profile.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.profiles import HebrewProfile

    il_calls: list[str] = []
    original_il_normalize = HebrewProfile.normalize_for_parsing

    def spy_il_normalize(self, text):  # noqa: ANN001 - test spy, mirrors real signature
        il_calls.append(text)
        return original_il_normalize(self, text)

    monkeypatch.setattr(HebrewProfile, "normalize_for_parsing", spy_il_normalize)

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read_wiki("חוק להגנת רכוש מופקד.wiki"),
        jurisdiction="IL",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    assert il_calls, (
        "HebrewProfile.normalize_for_parsing was never invoked on the live "
        "run_definition_linking path -- Hebrew normalization is not dispatched "
        "through the profile"
    )

    # Byte-identical output invariant (same numbers as the already-passing
    # dispatch-fidelity test) -- must hold BOTH before and after dispatch is
    # wired, since HebrewProfile's method is a pure passthrough.
    definitions = result["created_definitions"]
    asset_definitions = [d for d in definitions if "נכס" in d["terms"]]
    assert len(asset_definitions) == 1

    uses_edges = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    assert len(uses_edges) >= 1

    derives_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "DERIVES_FROM_LAW"
    ]
    assert len(derives_edges) == 1
    assert "האפוטרופוס הכללי" in derives_edges[0]["proposition"]
