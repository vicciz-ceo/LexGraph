"""D1 (sprint 2026-08-04-defs-us-preamble, next cycle, manager ruling M-R43):
per-shape CORPUS-WIDE measurement of QA's 8 named P-R7 miss-shapes
(`-log.md` Q-D2), turning "one 50-row sample" bands into measured counts.

**Signal-agnostic discipline (P-R7's core constraint, restated in M-R43)**:
every shape detector below is written FRESH against the shape's own English
description in Q-D2 -- none of them imports or copies the regex OBJECTS
from `backend/app/definition_links/rules/us_body_preamble.py`. Two shapes
(2 and 6) are, BY THEIR OWN DEFINITION (M-R39: "our own trigger, our own
rule, post-trigger pattern too strict" / "narrow B1 widening"), a variant
of the SAME trigger phrase our shipped B1 rule keys on ("As used in this
X"/"For (the) purposes of this X") -- there is no way to describe "shape 2"
or "shape 6" without that shared vocabulary, since the shape IS "our
trigger, different tail". This is disclosed here, not hidden: for those two
shapes, the TRIGGER prefix is inevitably shared english wording; what is
independent is the POST-trigger classification logic (presence/absence of
"the term"/colon/qualifier-clause), which is what actually decides shape
membership. Every other shape (1, 3, 4, 5, 7, 8) uses trigger vocabulary
our shipped rules do NOT currently match at all (e.g. "In this X" is not in
B1's vocabulary; "the <Named Act>" is not "this <unit>"), so those are
independent in the strong sense too.

**"Captured today" (AFTER)** is computed by calling the REAL, unedited
production code (`app.definition_links.profiles.get_profile`,
`USProfile.is_definitions_heading` / `.derive_heading_from_body` /
`.determine_scope` / `.extract_definitions_from_section`) directly against
each row's real `text`, mirroring `pipeline.py`'s own Stage-2 dispatch
verbatim (lines 237-268 at this worktree's HEAD) -- never a reimplementation
of that logic, so this script cannot silently drift from what the real
pipeline does. "Captured" = `is_definitions_section` resolves True AND
`extract_definitions_from_section` yields >=1 candidate with a non-empty
`.terms` tuple (the SAME single definition Q-D1 states and uses
throughout).

**Candidate population**: restricted to rows whose ORIGINAL heading already
fails the bare `is_definitions_heading` check (matches Q-D2's own
"our rules' own candidate population" restriction) -- a row already
correctly captured via ordinary heading matching is not part of any of
these 8 miss-shapes by construction.

No test reads this file or the parquet snapshot (program rule). This
script DOES read the real on-disk vaquill/open-us-law snapshot -- allowed
for a measurement script, never for a test.

Usage: backend/.venv/bin/python <this file> [--sample-only]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

BACKEND = "/Users/nerya/LexGraph-wt/defs-us-preamble/backend"
sys.path.insert(0, BACKEND)

import pyarrow.parquet as pq  # noqa: E402

from app.definition_links.profiles import get_profile  # noqa: E402
from app.definition_links.us_profile import is_definitions_heading  # noqa: E402
from app.services.jurisdiction import JURISDICTION_CODES  # noqa: E402

SNAPSHOT = (
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)

WINDOW = 800  # generous vs. Q-D2's 600, to give shapes 4/5 (longer trigger
# clauses -- external section ranges / named-act titles) room; Q-D1/Q-D2
# both used 600 for their own component A/B, noted below for cross-check.

_QUOTE = r'["“]'
_CQUOTE = r'["”]'
_TERM = rf'{_QUOTE}([^"”]{{1,150}})[{_CQUOTE[1:-1]}"]'
_VERB = (
    r"(?:means|shall\s+mean|has\s+the\s+meaning|has\s+the\s+same\s+meaning|"
    r"is\s+defined\s+as|are\s+defined\s+as|shall\s+have\s+the\s+meaning)"
)
_TERM_VERB_RE = re.compile(_TERM + r"\s*" + _VERB, re.IGNORECASE)

# --- Q-D2 parity check (component A only -- component B is a small,
# separately-disclosed contributor, not reproduced here) ------------------
_COMPONENT_A_RE = re.compile(_TERM + r"\s*" + _VERB, re.IGNORECASE)

# --- Trigger-clause building blocks (independently authored; shapes 2/6
# unavoidably share the "As used in this"/"For (the) purposes of this"
# prefix with our own B1 rule -- see module docstring) --------------------
_TRIGGER_THIS_RE = re.compile(
    r"(?:As used in|For (?:the )?purposes of)\s+this\s+[A-Za-z][A-Za-z0-9 .\-]{0,30}",
    re.IGNORECASE,
)
_SHAPE3_TRIGGER_RE = re.compile(r"\bIn this\s+[A-Za-z][A-Za-z0-9 .\-]{0,30}", re.IGNORECASE)
_B2_PHRASE_RE = re.compile(
    r"the following words?\s+have\s+the\s+meanings?\s+indicated", re.IGNORECASE
)
# Precision guard for shape 3: a bare `\bIn this\b` regex also matches
# INSIDE "As used in this article" / "specified in this section" (a
# completely different, already-B1-vocabulary shape, not "In this X" as
# its OWN clause-initial trigger -- confirmed live during smoke-testing:
# without this guard, shape 3's count was dominated by "As used in this"
# substrings). Shape 3's real signature (Q-D2 #3, FEDERAL's convention) is
# "In this <unit>:" opening its OWN clause -- so a candidate match is kept
# only when it is clause-initial (start of window/body, after a newline,
# after sentence-ending punctuation, or after a "(a)"/"(1)"-style marker)
# AND not immediately preceded by a verb that makes it someone else's
# object ("...as USED IN THIS...", "...SPECIFIED IN THIS...").
_SHAPE3_REJECT_PRECEDING_WORDS = {
    "used", "specified", "described", "referred", "provided", "set", "stated",
    "defined", "included", "named", "codified", "interested", "resulting",
    "contained", "found", "identified", "listed", "mentioned", "noted",
    "required", "outlined", "prescribed", "applicable", "governed",
    "addressed", "expressed", "authorized", "recognized",
}
_SHAPE3_MARKER_TAIL_RE = re.compile(r"\(\s*[\w]{1,4}\s*\)\s*$")
_SHAPE3_PREV_WORD_RE = re.compile(r"([A-Za-z]+)\s*$")


def _shape3_clause_initial(window: str, start: int) -> bool:
    context = window[:start].rstrip(" \t")
    if not context or context[-1] in ".:;\n":
        return True
    if _SHAPE3_MARKER_TAIL_RE.search(context):
        return True
    prev_word_m = _SHAPE3_PREV_WORD_RE.search(context)
    if prev_word_m and prev_word_m.group(1).lower() in _SHAPE3_REJECT_PRECEDING_WORDS:
        return False
    return False  # conservative default: only accept a clean clause start
_SHAPE4_RE = re.compile(
    r"(?:As used in|For (?:the )?purposes of)\s+(?:Sections?|§§?)\s*"
    r"[\d][\d\w.\-]*(?:\s*(?:through|to|-|–)\s*[\d][\d\w.\-]*)?",
    re.IGNORECASE,
)
_SHAPE5_RE = re.compile(
    r"As used in the\s+([A-Z][A-Za-z0-9&'\-]*(?:\s+[A-Za-z0-9&'\-]+){0,8}\s+(?:Act|Code))\b"
)
_SHAPE5_ALSO_MEANS_RE = re.compile(r"\balso\s+means\b", re.IGNORECASE)
# Shape 7 IS, by its own Q-D2 definition, "CA's own idiom, in OTHER
# states" -- there is no way to describe it independently of that idiom's
# vocabulary (disclosed, like shapes 2/6, in the module docstring).
# Anchored at the body's own opening (`.match`, not `.search`, mirroring
# the real rule's own window discipline) -- NOT anchoring caused a real
# smoke-test false-positive class during development: an unanchored
# search matched "shall NOT apply" (negated scope) and "the definitions
# ... shall apply" as a mid-body FORWARDING reference to another section,
# neither of which is the wide-window preamble idiom shape 7 names.
_SHAPE7_RE = re.compile(
    r"^.{0,200}?\bDefinitions?\b(?=.{0,150}?\b(?:appl(?:y|ies|ied)|govern|shall\s+apply)\b)",
    re.IGNORECASE | re.DOTALL,
)
_SHAPE8_RE = re.compile(
    r"\bwords?(?:\s+and\s+phrases)?\b.{0,60}?\bhave\b.{0,10}?\bthe\s+meanings?\b"
    r".{0,10}?\b(?:respectively\s+)?ascribed\s+to\s+them\b",
    re.IGNORECASE | re.DOTALL,
)
_NE_TRIGGER_RE = re.compile(
    r"^(?:\([^)]{0,40}\)\s*)?(?:In the|For purposes of the)\s+[^:\n]{1,100}:", re.IGNORECASE
)
# Union of every trigger-ish phrase, for shape-1's "no trigger anywhere
# before this quote" exclusion test.
_ANY_TRIGGER_RE = re.compile(
    r"(?:As used in|For (?:the )?purposes of)\s+(?:this\s+[A-Za-z]|the\s+[A-Z]|Sections?\b|"
    r"§)|In this\s+[A-Za-z]|In the\s+[A-Z]",
)


# Shared post-trigger content check for shapes 3/4 (both accept a
# colon-list branch): a bare colon is NOT enough evidence on its own --
# smoke-testing found "...is the earlier: (a) The 15th day..." (an
# unrelated operative-deadline list, the same H3 hazard class this whole
# family's own hazard catalogue already documents) satisfies a naive
# "colon present" check. Require the colon to actually introduce a
# defining entry: either a quoted term + verb, or an unquoted numbered/
# lettered entry immediately followed by a defining verb (NE's own real
# "(1) Account means ..." shape, `_leading_quote_candidate`'s unquoted
# sibling).
_UNQUOTED_ENTRY_RE = re.compile(
    r"\(\s*\w{1,4}\s*\)\s*[A-Z][A-Za-z\-]+(?:\s+[a-z][A-Za-z\-]+){0,4}\s+" + _VERB,
    re.IGNORECASE,
)


def _has_definitional_content(after: str) -> bool:
    if _TERM_VERB_RE.search(after[:190]):
        return True
    colon_idx = after.find(":")
    if colon_idx == -1:
        return False
    tail = after[colon_idx + 1 : colon_idx + 1 + 180]
    return bool(_TERM_VERB_RE.search(tail) or _UNQUOTED_ENTRY_RE.search(tail))


def shape2_match(body: str) -> re.Match | None:
    for m in _TRIGGER_THIS_RE.finditer(body[:WINDOW]):
        after = body[m.end() : m.end() + 150]
        tv = _TERM_VERB_RE.search(after[:110])
        if tv is None:
            continue
        filler = after[: tv.start()].lower()
        if "the term" not in filler and ":" not in filler:
            return m
    return None


def shape6_match(body: str) -> re.Match | None:
    for m in _TRIGGER_THIS_RE.finditer(body[:WINDOW]):
        after = body[m.end() : m.end() + 220]
        tt = re.search(r"the term\s+" + _QUOTE, after, re.IGNORECASE)
        if tt is None:
            continue
        filler = after[: tt.start()]
        if re.search(r",\s*[A-Za-z][^,:;]{2,100},\s*$", filler):
            return m
    return None


def shape3_match(body: str) -> re.Match | None:
    window = body[:WINDOW]
    for m in _SHAPE3_TRIGGER_RE.finditer(window):
        if not _shape3_clause_initial(window, m.start()):
            continue
        after = body[m.end() : m.end() + 220]
        if _B2_PHRASE_RE.search(after):
            continue  # this is B2's own already-captured shape
        if _has_definitional_content(after):
            return m
    return None


def shape4_match(body: str) -> re.Match | None:
    # Smoke-testing found the bare trigger (e.g. "For purposes of Section
    # 19142, the period of the underpayment shall run from...") matches an
    # ordinary OPERATIVE sentence that cites a section number but defines
    # nothing -- the same H1/H3-family hazard this whole family already
    # guards against. Require actual definitional content (a colon-list or
    # a quoted term + defining verb) to follow within a short window,
    # mirroring the same discipline shapes 2/3/6 already apply.
    for m in _SHAPE4_RE.finditer(body[:WINDOW]):
        after = body[m.end() : m.end() + 220]
        if _has_definitional_content(after):
            return m
    return None


def shape5_match(body: str) -> tuple[re.Match, bool] | None:
    m = _SHAPE5_RE.search(body[:WINDOW])
    if m is None:
        return None
    tail = body[m.end() : m.end() + 400]
    also_means = bool(_SHAPE5_ALSO_MEANS_RE.search(tail))
    return m, also_means


# Smoke-testing (GA/NE) surfaced a SECOND, sharper hazard than the
# anchoring fix above catches: "the definitions found in sections 38-1005
# to 38-1056 apply" (a pure FORWARDING pointer to definitions living
# elsewhere -- exactly this family's own documented H1 hazard class, see
# `test_us_body_preamble_hazard_catalogue_red.py`) and "...shall NOT
# apply" (negated scope) both satisfy the bare "Definitions...apply"
# lookahead but are not a local preamble at all. Excluded here by
# inspecting the actual gap text between "Definitions" and the verb --
# this is a real, disclosed finding for D3 (shape 7's idiom is inherently
# ambiguous between a local block and a forwarding pointer), not swept
# under the rug by the exclusion.
_SHAPE7_FORWARDING_GAP_RE = re.compile(
    r"\bfound in\b|\bprovided in\b|\bset forth in\b|\bcontained in\b|\breferenced in\b|\bnot\b"
    r"|\bin sections?\b|\bin §§?\b|\bunder §\b|\bunder section\b",
    re.IGNORECASE,
)


def shape7_match(body: str, code: str) -> re.Match | None:
    if code == "US-CA":
        return None  # CA already owns this idiom; shape 7 = OTHER states
    m = _SHAPE7_RE.match(body[:WINDOW])
    if m is None:
        return None
    gap = body[m.end() : m.end() + 150]
    if _SHAPE7_FORWARDING_GAP_RE.search(gap):
        return None
    return m


def shape8_match(body: str) -> re.Match | None:
    m = _SHAPE8_RE.search(body[:WINDOW])
    if m is None:
        return None
    if "indicated" in body[m.start() : m.end() + 20].lower():
        return None  # that's B2's own literal wording, not a "variant"
    return m


def shape1_match(body: str) -> re.Match | None:
    window = body[:WINDOW]
    for m in _TERM_VERB_RE.finditer(window):
        prefix = window[: m.start()]
        if _ANY_TRIGGER_RE.search(prefix) or _NE_TRIGGER_RE.match(window):
            continue
        return m
    return None


def classify_shapes(body: str, code: str) -> dict[int, re.Match | tuple]:
    """Returns {shape_number: match_object_or_tuple} for every shape this
    body matches (a row may match more than one -- overlap is reported,
    not hidden)."""
    hits: dict[int, object] = {}
    m2 = shape2_match(body)
    if m2:
        hits[2] = m2
    m3 = shape3_match(body)
    if m3:
        hits[3] = m3
    m4 = shape4_match(body)
    if m4:
        hits[4] = m4
    m5 = shape5_match(body)
    if m5:
        hits[5] = m5
    m6 = shape6_match(body)
    if m6:
        hits[6] = m6
    m7 = shape7_match(body, code)
    if m7:
        hits[7] = m7
    m8 = shape8_match(body)
    if m8:
        hits[8] = m8
    # shape 1 is intentionally computed LAST and only reported if none of
    # the trigger-anchored shapes above matched anywhere in the window --
    # shape 1's own definition is "no trigger phrase at all" (Q-D2 #1), so
    # a row that also independently matches e.g. shape 3 or 5 is not a
    # "shape 1" row even if some OTHER quote+verb occurrence in the same
    # window has no trigger before it.
    if not hits:
        m1 = shape1_match(body)
        if m1:
            hits[1] = m1
    return hits


def after_captured(profile, heading: str, body: str) -> bool:
    """Mirrors `pipeline.py`'s Stage-2 dispatch verbatim (lines 237-268 at
    this worktree's HEAD): baseline heading check, then body-derived
    heading (registry-consulted), then real extraction; "captured" means
    >=1 candidate with a non-empty `.terms` tuple -- the exact Q-D1
    definition."""
    is_def = profile.is_definitions_heading(heading, body)
    used_derived = False
    if not is_def:
        derived = profile.derive_heading_from_body(heading, body)
        if derived is not None and profile.is_definitions_heading(derived, body):
            is_def = True
            used_derived = True
    if not is_def:
        return False
    scope = profile.determine_scope(body)
    candidates = profile.extract_definitions_from_section(
        body, scope=scope, heading_was_derived=used_derived
    )
    return any(c.terms for c in candidates)


def jurisdiction_code_for_filename(stem: str) -> str | None:
    # stem like "us_ak_statutes" -> "US-AK"; "us_federal_statutes" -> "US-FED"
    # (the dataset's own filename says "federal" in full, but the app's
    # controlled vocabulary -- `JURISDICTION_CODES` -- uses "US-FED"; bug
    # caught by this script's own first full-corpus run, which silently
    # SKIPPED the federal file entirely under the naive "US-FEDERAL"
    # guess -- fixed here, re-run before trusting any total below).
    assert stem.endswith("_statutes")
    st = stem[len("us_") : -len("_statutes")]
    if st == "federal":
        return "US-FED"
    candidate = f"US-{st.upper()}"
    if candidate in JURISDICTION_CODES:
        return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-only", action="store_true", help="run on 3 states only, fast smoke test")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    files = sorted(Path(SNAPSHOT).glob("*_statutes.parquet"))
    if args.sample_only:
        files = [f for f in files if f.stem in ("us_ga_statutes", "us_ca_statutes", "us_ne_statutes")]

    shape_names = {
        1: 'Bare "Term" means, no trigger phrase at all',
        2: 'Trigger present, quote follows w/o "the term" wording or colon',
        3: '"In this <unit>" trigger (not "As used in"/"For purposes of")',
        4: "Trigger cites external Section range instead of \"this <unit>\"",
        5: "Named-Act phrasing (\"As used in the <Named Act>\")",
        6: "Intervening qualifier clause between trigger and quoted term",
        7: "CA wide-window idiom in OTHER (non-CA) states",
        8: 'B2 wording variant ("...have the meaning(s) ...ascribed...")',
    }

    per_state: dict[str, dict] = {}
    totals = {
        "rows_scanned": 0,
        "baseline_fail": 0,
        "component_a_total": 0,
        "component_a_captured": 0,
        "shape_total": {n: 0 for n in range(1, 9)},
        "shape_captured": {n: 0 for n in range(1, 9)},
        "shape5_also_means": 0,
        "overlap_pairs": {},
    }
    samples: dict[int, list] = {n: [] for n in range(1, 9)}
    rng = random.Random(20260805)

    t_start = time.time()
    for path in files:
        stem = path.stem
        code = jurisdiction_code_for_filename(stem)
        if code is None:
            print(f"SKIP {stem}: no jurisdiction code mapping", file=sys.stderr)
            continue
        table = pq.read_table(path, columns=["act_id", "section_title", "text"])
        profile = get_profile(code)
        state_stats = {
            "rows": table.num_rows,
            "baseline_fail": 0,
            "component_a_total": 0,
            "component_a_captured": 0,
            "shape_total": {n: 0 for n in range(1, 9)},
            "shape_captured": {n: 0 for n in range(1, 9)},
            "shape5_also_means": 0,
        }
        act_ids = table["act_id"].to_pylist()
        headings = table["section_title"].to_pylist()
        bodies = table["text"].to_pylist()
        for act_id, heading, body in zip(act_ids, headings, bodies):
            heading = heading or ""
            body = body or ""
            totals["rows_scanned"] += 1
            if is_definitions_heading(heading):
                continue
            totals["baseline_fail"] += 1
            state_stats["baseline_fail"] += 1

            comp_a = bool(_COMPONENT_A_RE.search(body[:600]))
            hits = classify_shapes(body, code)
            if not comp_a and not hits:
                continue

            captured = after_captured(profile, heading, body)

            if comp_a:
                totals["component_a_total"] += 1
                state_stats["component_a_total"] += 1
                if captured:
                    totals["component_a_captured"] += 1
                    state_stats["component_a_captured"] += 1

            for shape_no in hits:
                totals["shape_total"][shape_no] += 1
                state_stats["shape_total"][shape_no] += 1
                if captured:
                    totals["shape_captured"][shape_no] += 1
                    state_stats["shape_captured"][shape_no] += 1
                elif len(samples[shape_no]) < 12:
                    hit = hits[shape_no]
                    match_obj = hit[0] if isinstance(hit, tuple) else hit
                    start = max(0, match_obj.start() - 40)
                    samples[shape_no].append(
                        {
                            "act_id": act_id,
                            "code": code,
                            "excerpt": body[start : start + 400],
                        }
                    )
            if 5 in hits and hits[5][1]:
                totals["shape5_also_means"] += 1
                state_stats["shape5_also_means"] += 1

            if len(hits) > 1:
                pair_key = ",".join(str(x) for x in sorted(hits))
                totals["overlap_pairs"][pair_key] = totals["overlap_pairs"].get(pair_key, 0) + 1

        per_state[code] = state_stats
        print(
            f"{code:8s} rows={table.num_rows:7d} baseline_fail={state_stats['baseline_fail']:7d} "
            f"shapes={sum(state_stats['shape_total'].values()):5d} "
            f"elapsed={time.time() - t_start:6.1f}s",
            file=sys.stderr,
        )

    result = {
        "snapshot": SNAPSHOT.rsplit("/", 1)[-1],
        "window": WINDOW,
        "shape_names": shape_names,
        "totals": totals,
        "per_state": per_state,
        "samples": samples,
    }
    out_path = args.out or "/private/tmp/claude-501/-Users-nerya-LexGraph/87b55b0a-5a38-44b6-887d-1e093b526197/scratchpad/shape_measurement_output.json"
    Path(out_path).write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_path}", file=sys.stderr)
    print(f"Total elapsed: {time.time() - t_start:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
