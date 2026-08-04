"""QA regression test — sprint 2026-08-04-defs-core-scope, item I9,
residual concern #1 (QA manager brief): "The CA curly-quote/newline
regression and the AK mojibake case are DIFFERENT BYTE FAMILIES ... do
not treat one pin as covering the other."

**Independent corpus finding.** I9's own existing dispatch test
(`test_definition_links_pipeline_normalize_dispatch.py::
test_overriding_us_profile_normalize_for_parsing_changes_what_the_live_pipeline_extracts`)
simulates "a realistic mojibake artifact ... the same FAMILY of defect
recon dossier family 3 flags for AK's cp1252 mojibake curly quotes" by
computing `"“".encode("utf-8").decode("latin-1")` -- a genuine
Unicode curly quote's UTF-8 bytes mis-decoded one byte at a time as
Latin-1, producing a THREE-character garbled sequence (`â\x80\x9c`).

Scanning the real `us_ak_statutes.parquet` snapshot (17,935 rows) for
that exact pattern -- and for genuine Unicode curly quotes (U+201C/
U+201D) -- finds ZERO occurrences of either. What the real AK text
column actually contains, 11,875 / 11,874 times respectively, is the
single RAW C1 CONTROL-CHARACTER codepoints U+0093 / U+0094 sitting
in place of a curly quote -- i.e. a Windows-1252 SINGLE BYTE (0x93/0x94,
which cp1252 maps to left/right curly double quote) that was carried
into the string as its raw byte value instead of being decoded through
cp1252. This is a genuinely DIFFERENT corruption mechanism (and a
different resulting character sequence -- one control character, not
three mojibake letters) than the sprint's own dispatch test simulates.
Neither `USProfile.normalize_for_parsing` baseline (collapses ONLY
U+201C/U+201D, confirmed by direct source read -- see
`_CURLY_QUOTE_VARIANTS_RE` in `us_profile.py`) nor the sprint's own
mojibake-repair test profile (targets the UTF-8-as-Latin-1 three-
character sequence) touches U+0093/U+0094 at all -- confirmed empirically
below (baseline run) before asserting the override half.

This does NOT mean I9 is broken: I9's OWN job (ruling M15) was making the
`normalize_for_parsing` DISPATCH mechanism live, not repairing AK's
specific defect (that repair is explicitly left to "a jurisdiction-
specific normalize_for_parsing override", i.e. future family-panel work,
per the sprint's own docstrings). This test verifies the dispatch
mechanism I9 built generalizes to AK's ACTUAL real-byte defect, not only
to the differently-shaped defect the sprint's own test happened to
simulate -- closing the "verify each pin independently against real
bytes" gap named in the QA brief.

Vendors ONE real, byte-for-byte AK row (`STATE_AK_T11_C11.76_S11.76.115`,
AS 11.76.115, "confidential information" bracketed by the real \x93/\x94
control-character pair -- copied from the live `us_ak_statutes.parquet`
snapshot, never downloaded or read by this test itself, per ruling R6).
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "ak_i9_cp1252_mojibake_row.json"
)

_AK_MOJIBAKE_OPEN = ""
_AK_MOJIBAKE_CLOSE = ""


def _load_row() -> dict:
    rows = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_real_ak_rows_defect_is_a_raw_cp1252_control_byte_not_the_utf8_as_latin1_sequence():
    """Fixture-integrity sanity check, not a claim about production code:
    confirms the vendored real AK row actually carries the SINGLE raw
    control-character bytes (U+0093/U+0094), not the three-character
    UTF-8-mis-decoded-as-Latin-1 sequence the sprint's own dispatch test
    simulates -- so a future reader can trust this file exercises the
    genuinely different byte family the QA brief flagged, not a
    coincidentally-similar one."""
    row = _load_row()
    text = row["text"]
    assert _AK_MOJIBAKE_OPEN in text
    assert _AK_MOJIBAKE_CLOSE in text

    utf8_as_latin1_open = "“".encode("utf-8").decode("latin-1")
    utf8_as_latin1_close = "”".encode("utf-8").decode("latin-1")
    assert utf8_as_latin1_open not in text
    assert utf8_as_latin1_close not in text
    assert "“" not in text and "”" not in text  # no genuine curly quotes either


def test_baseline_us_profile_normalize_for_parsing_does_not_touch_the_real_ak_control_bytes():
    """Baseline (the fix I6/I9 actually ship) is scoped to genuine Unicode
    curly quotes only -- confirms it leaves AK's real control-byte defect
    untouched, so the override test below is discriminated purely by
    dispatch, not confounded by an unexpected baseline effect."""
    from app.definition_links.us_profile import normalize_for_parsing

    row = _load_row()
    normalized = normalize_for_parsing(row["text"])
    assert _AK_MOJIBAKE_OPEN in normalized
    assert _AK_MOJIBAKE_CLOSE in normalized


def test_live_pipeline_dispatches_an_ak_specific_normalize_override_that_repairs_the_real_control_bytes(
    db_session, matter_with_users, monkeypatch
):
    """The mechanism proof, on AK's ACTUAL real-byte defect: register a
    REAL alternate `USProfile` subclass under `"US-AK"` (same registration
    mechanism `profiles.py` itself uses -- `profiles._REGISTRY`, not a
    mock) whose `normalize_for_parsing` repairs the real cp1252 control-
    byte pair. A spy wraps it to also capture what was actually passed
    in and returned, so this test discriminates "dispatch never reached
    the override" from "the override fired but didn't change anything".
    """
    from app.definition_links import profiles
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.us_profile import USProfile

    @dataclass(frozen=True)
    class _AkMojibakeRepairingUSProfile(USProfile):
        def normalize_for_parsing(self, text: str) -> str:
            return text.replace(_AK_MOJIBAKE_OPEN, '"').replace(_AK_MOJIBAKE_CLOSE, '"')

    captured: list[str] = []
    original_repair = _AkMojibakeRepairingUSProfile.normalize_for_parsing

    def _spy(self, text):
        result = original_repair(self, text)
        captured.append(result)
        return result

    monkeypatch.setattr(_AkMojibakeRepairingUSProfile, "normalize_for_parsing", _spy)

    m = matter_with_users
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Alaska Statutes Title 11 (I9 real cp1252 mojibake fixture)",
        rows=[row],
        jurisdiction="US-AK",
    )

    monkeypatch.setitem(
        profiles._REGISTRY, "US-AK", _AkMojibakeRepairingUSProfile(code="US-AK")
    )

    run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    assert captured, (
        "the AK-registered normalize_for_parsing override was never "
        "invoked on the live run_definition_linking path for a US-AK "
        "document -- dispatch does not reach a per-code override"
    )
    normalized_output = captured[0]
    assert _AK_MOJIBAKE_OPEN not in normalized_output
    assert _AK_MOJIBAKE_CLOSE not in normalized_output
    assert '"confidential information"' in normalized_output, (
        "expected the AK-specific override's repair of the real cp1252 "
        "control-byte pair to survive into the normalized text used by "
        f"the live pipeline -- got {normalized_output!r}"
    )
