"""RED tests for sprint 2026-08-04-defs-us-multiterm, family 5 (dossier §2 +
§6 addendum): "The term(s) 'X', 'Y', and 'Z' mean(s)..." -- ONE clause
defines SEVERAL terms; today's US extractors only ever recover the FIRST
quoted term of a block (`us_profile._LEADING_QUOTE_RE.match(block)`) or
silently absorb the rest into the definition text of whatever term was
already open.

Every fixture row below is REAL, vendored verbatim from
`vaquill/open-us-law` at `backend/tests/fixtures/us_statutes/
multiterm_f5_rows.json` -- the SAME fixture file
`test_multiterm_f5_shared_clause.py`/`test_multiterm_f5_blocked_on_markers.py`
use for their full-pipeline (integration) proof of these rows; this file
tests the extractor FUNCTION directly, one layer below those (see that
directory's `README.md` for provenance) -- no test here downloads the
corpus.

Live-path discipline: every test calls the REAL, current
`app.definition_links.us_profile.extract_definitions_from_section` (the
same function `USProfile.extract_definitions_from_section` delegates to,
and the same one `pipeline.py` calls at Stage 2) directly on the real row
body -- not a mock, not a hand-shortened string. Assertions target the
SET of terms found across all returned candidates (`{t for c in
candidates for term in c.terms}`), the same "stable behavioral surface"
idiom `test_definition_links_us_profile.py`'s existing DE test already
uses -- robust to whichever internal shape (one N-term candidate vs. N
one-term candidates) the eventual fix picks, since `matcher.
link_articles_to_definitions` already resolves `definition.terms`
individually either way (matcher.py:132-134) -- see this sprint's log
entry for the live-code trace proving that.

RED signal for every test below: a real assertion failure (a term the
current code silently drops, or a definition_text the current code
truncates to a near-empty fragment) -- never an ImportError/collection
error, since every symbol imported here already exists and is already
exercised by the sprint-2026-08-02 suite.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.profiles import get_profile
from app.definition_links.us_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "multiterm_f5_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _extract(row: dict) -> list:
    # Sprint 2026-08-04-defs-us-multiterm, ruling M-R9: `pipeline.
    # _determine_scope` was moved behind the core-scope seam (now private
    # to `us_profile.py`). Repointed to the PUBLIC seam -- the profile's
    # own `determine_scope` Protocol method, reached via `get_profile`,
    # the same call shape `pipeline.py` itself uses -- rather than a new
    # private import. Behavior verified byte-identical to the old direct
    # call (see this sprint's log entry): `USProfile.determine_scope`
    # ignores `self.code` entirely, so which US code is resolved here
    # cannot change the returned value; the row's own state code is used
    # anyway for documentation fidelity.
    profile = get_profile("US-" + row["act_id"].split("_")[1])
    scope = profile.determine_scope(row["text"])
    return extract_definitions_from_section(row["text"], scope=scope)


# --- VT STATE_VT_T23_C35_S3700 -- simultaneously F3 (zero-yield) + F5 ------
# "As used in this chapter, "mail," "mails," "mailing," and "mailed" mean
# any method of delivery..." -- heading "§ 3700. Definition; mail" IS
# recognized as a Definitions heading (verified live, sprint log), but the
# body carries NO "(N)" markers at all, so the block splitter never even
# starts a block. Root cause (verified live, sprint log): even the
# existing inline-quote fallback's idiom-gap regex
# (`pipeline._MEANS_IDIOM_GAP_RE`) requires literal "means"/"shall mean"/
# "has the meaning" -- a run-on multi-term subject correctly takes the
# PLURAL verb "mean" (no "s"), which that regex never matches, and even
# patched to "means" it would only ever catch the LAST quoted term (no
# quote characters are allowed inside the idiom-gap, so terms 1..N-1,
# each immediately followed by another quote rather than the verb, can
# never satisfy the check individually).


def test_vt_s3700_all_four_shared_terms_are_extracted():
    row = _load_rows()["STATE_VT_T23_C35_S3700"]
    candidates = _extract(row)
    all_terms = {t for c in candidates for t in c.terms}
    assert {"mail", "mails", "mailing", "mailed"} <= all_terms, (
        f"expected all 4 terms sharing the one 'mean any method of delivery...' "
        f"clause to be extracted; got candidates={candidates!r}"
    )


# --- SD STATE_SD_T3_C14_S3-14-5 -- F5, extractor yield now CONFIRMED zero -
# Dossier §6 addendum flagged this row's extractor yield as UNCONFIRMED
# ("not separately isolated"). Live re-run for this sprint (sprint log)
# confirms it is IDENTICAL in shape and outcome to VT above: heading
# "Definitions" matches, body is un-marked prose ('The terms "office,"
# "officer," "executive," and "administrative,"... mean and apply to...'),
# both the real block extractor and the inline fallback return 0
# candidates today.


def test_sd_s3_14_5_all_four_shared_terms_are_extracted():
    row = _load_rows()["STATE_SD_T3_C14_S3-14-5"]
    candidates = _extract(row)
    all_terms = {t for c in candidates for t in c.terms}
    assert {"office", "officer", "executive", "administrative"} <= all_terms, (
        f"SD's extractor yield for this exact row was flagged 'UNCONFIRMED' in "
        f"the recon dossier; live re-run for this sprint confirms it is a "
        f"genuine zero-yield row today (see sprint log). Got candidates="
        f"{candidates!r}"
    )


# --- TX STATE_TX_Cgv_C2009_S2009.003 -- F5, "parent-clause pointer" list --
# '(4) The following terms have the meanings assigned by Section 2001.003:
# (A) "contested case"; (B) "party"; (C) "person"; and (D) "rule."' --
# post-wave-7 (prior sprint 2026-08-02, ruling R16), the letter-led block
# splitter DOES now produce 4 candidates for (A)-(D), but each one's
# definition_text is the DEGENERATE leftover punctuation after its own
# quote (";", "; and", "") -- the real shared definition ("have the
# meanings assigned by Section 2001.003") lives on the PARENT "(4)" line,
# which itself has no leading quote and is dropped by the splitter. This
# is the prior sprint's recorded "13 of 75 degenerate recovered terms"
# residual, root-caused precisely for this exact row (sprint log).


def test_tx_s2009_003_parent_clause_terms_get_the_real_shared_definition_text():
    row = _load_rows()["STATE_TX_Cgv_C2009_S2009.003"]
    candidates = _extract(row)
    by_term = {t: c for c in candidates for t in c.terms}
    for term in ("contested case", "party", "person", "rule."):
        assert term in by_term, f"term {term!r} missing entirely from {candidates!r}"
        definition_text = by_term[term].definition_text.strip()
        assert len(definition_text) > 10, (
            f"term {term!r} has a DEGENERATE definition_text {definition_text!r} "
            f"-- the real shared definition ('have the meanings assigned by "
            f"Section 2001.003') lives on the parent '(4)' line and is being "
            f"dropped instead of attached to each of its 4 terms"
        )


# --- MT STATE_MT_T16_C11_P4_S16-11-402 -- F5 nested WITHIN a working entry
# Entry (2) ("Affiliate" means...) is captured correctly by today's code --
# but its OWN definition text contains a second, nested multi-term shared
# clause ('the terms "owns," "is owned" and "ownership" mean ownership of
# an equity interest...') plus a nested single-term one ('the term
# "person" means an individual, partnership...'). None of "owns"/"is
# owned"/"ownership"/"person" become their own extracted terms today --
# they are silently absorbed into "Affiliate"'s definition_text with no
# trace. This is the SAME family as VT/SD/TX above, just occurring inside
# an already-well-formed section rather than being the section's only
# content.


def test_mt_s16_11_402_top_level_terms_are_unaffected():
    """Sanity/regression anchor: 8 of the 9 top-level '(N) "Term" means'
    entries in this real section already extract correctly today -- any
    fix for the nested clause must not disturb this baseline.

    NOT asserted here: entry (1) "Adjusted for inflation" -- an
    OUT-OF-FAMILY defect this fixture happens to also expose (reported
    separately, not this sprint's to fix per the contract's routing rule):
    the real row's `text` column repeats the section number/heading
    ("16-11-402 . Definitions. ") on the SAME physical line as entry (1)'s
    own "(1)" marker, so `_split_into_numbered_blocks`'s line-based
    entry-start check (which requires the marker at the very start of its
    line) never fires for that one line, and the entire line -- heading
    recap AND entry (1) together -- is silently dropped before block (2)
    starts on its own line. Independently reproducible, unrelated to
    multi-term shared clauses.
    """
    row = _load_rows()["STATE_MT_T16_C11_P4_S16-11-402"]
    candidates = _extract(row)
    all_terms = {t for c in candidates for t in c.terms}
    assert {
        "Affiliate",
        "Allocable share",
        "Cigarette",
        "Master Settlement Agreement",
        "Qualified escrow fund",
        "Tobacco Product Manufacturer",
        "Units sold",
    } <= all_terms


def test_mt_s16_11_402_nested_shared_clause_terms_are_extracted():
    """Scope note (reconciled during this planning pass): "person" is
    DELIBERATELY NOT required here. Its own nested clause ('the term
    "person" means an individual, partnership...') is a SINGLE-term nested
    sub-definition, not a multi-term SHARED clause -- structurally it is
    the English analogue of Hebrew's ALREADY-SOLVED recursive case
    (`extract._NESTED_MARKER_RE`/`parent_term`), an out-of-family gap this
    fixture happens to also expose (reported to the program manager per
    the contract's routing rule, not claimed here). A compliant fix may
    incidentally also recover "person" as a side effect of whatever
    mechanism recognizes the embedded "owns"/"is owned"/"ownership" clause
    -- welcome, but not required by this test."""
    row = _load_rows()["STATE_MT_T16_C11_P4_S16-11-402"]
    candidates = _extract(row)
    all_terms = {t for c in candidates for t in c.terms}
    assert {"owns", "is owned", "ownership"} <= all_terms, (
        f"the nested multi-term shared clause inside entry (2) 'Affiliate' -- "
        f"'the terms \"owns,\" \"is owned\" and \"ownership\" mean...' -- is "
        f"silently absorbed into Affiliate's own definition_text today; none "
        f"of its 3 terms become their own candidates. Got all_terms="
        f"{sorted(all_terms)!r}"
    )
