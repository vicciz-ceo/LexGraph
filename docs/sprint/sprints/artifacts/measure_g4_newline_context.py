#!/usr/bin/env python3
"""Reproduce and audit core-2 G4's two cross-newline populations.

Run from the repository root:

  backend/.venv/bin/python \
    docs/sprint/sprints/artifacts/measure_g4_newline_context.py CORPUS_DIR

The corpus is read-only.  Tests never invoke this script or read the corpus.
It writes deterministic summary/full JSON beside this file.
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

import app.definition_links.us_profile as up
from app.definition_links.rules.registry import UnitStep

SNAPSHOT = "301000fc3465374ee0f23c3c6953a8a861e95cad"
STRUCTURAL_WORDS = (
    "division|subdivision|article|part|section|title|chapter|paragraph|"
    "subsection|subchapter"
)
CITATION_PREFIX = (
    r"(?:\d+\s+U\.S\.C\.\s+§\s*\d+(?:[.\-]\d+)*"
    r"|\bSection\s+\d+(?:[.\-]\d+)*"
    r"|§\s*\d+(?:[.\-]\d+)*"
    r"|\b[A-Z]{2,6}\s+\d+(?:[.\-]\d+)*)"
)
STRUCTURAL_PREFIX = rf"(?i:\b(?:{STRUCTURAL_WORDS}))"
CANDIDATE_TOKEN = (
    r"(?:\((?:[A-Za-z]+|\d+)\)"
    r"|(?:\d+(?:-[A-Za-z]{1,2})?|[A-Za-z]{1,2})\.(?=\s))"
)
# Enumerates the full cross-line surface. Every emitted case is subsequently
# validated against the production suffix regex and candidate-token union.
CROSSLINE_CASE_PATTERN = re.compile(
    rf"(?P<context>{CITATION_PREFIX}|{STRUCTURAL_PREFIX})"
    rf"(?P<gap>\s*[\r\n]\s*)(?P<candidate>{CANDIDATE_TOKEN})"
)
# Arrow/RE2 prefilter uses the complete set for which Python `str.isspace()`
# is true, not shorthand `\s`, so Unicode whitespace cannot be omitted.
_WHITESPACE_CLASS = "[" + "".join(
    character for codepoint in range(0x110000) if (character := chr(codepoint)).isspace()
) + "]"
_ARROW_CANDIDATE = (
    rf"(?:\((?:[A-Za-z]+|\d+)\)"
    rf"|(?:\d+(?:-[A-Za-z]{{1,2}})?|[A-Za-z]{{1,2}})\.{_WHITESPACE_CLASS})"
)
ARROW_CITATION_PATTERN = (
    rf"{CITATION_PREFIX}{_WHITESPACE_CLASS}*[\r\n]"
    rf"{_WHITESPACE_CLASS}*{_ARROW_CANDIDATE}"
)
ARROW_STRUCTURAL_PATTERN = (
    rf"(?i){STRUCTURAL_PREFIX}{_WHITESPACE_CLASS}*[\r\n]"
    rf"{_WHITESPACE_CLASS}*{_ARROW_CANDIDATE}"
)
CITATION_BRANCHES = (
    ("usc_section_symbol", re.compile(r"\d+\s+U\.S\.C\.\s+§\s*\d+(?:[.\-]\d+)*\Z")),
    ("section_word", re.compile(r"\bSection\s+\d+(?:[.\-]\d+)*\Z")),
    ("section_symbol", re.compile(r"§\s*\d+(?:[.\-]\d+)*\Z")),
    ("bare_state_code", re.compile(r"\b[A-Z]{2,6}\s+\d+(?:[.\-]\d+)*\Z")),
)
LEGACY_STRUCTURAL_GAP = re.compile(r"[ \t]*\n[ \t]*\Z")
_CITATION_SUFFIX_AT_EACH_POSITION = re.compile(
    rf"(?=({up._CITATION_NUMBER_SUFFIX_RE.pattern.removesuffix(r'\Z')}))",
    up._CITATION_NUMBER_SUFFIX_RE.flags,
)
_STRUCTURAL_SUFFIX_AT_EACH_POSITION = re.compile(
    rf"(?=({up._STRUCTURAL_UNIT_WORD_SUFFIX_RE.pattern.removesuffix(r'\Z')}))",
    up._STRUCTURAL_UNIT_WORD_SUFFIX_RE.flags,
)
_USC_SUFFIX_AT_EACH_POSITION = re.compile(
    rf"(?=({CITATION_BRANCHES[0][1].pattern.removesuffix(r'\Z')}))"
)
_BARE_STATE_SUFFIX_AT_EACH_POSITION = re.compile(
    rf"(?=({CITATION_BRANCHES[3][1].pattern.removesuffix(r'\Z')}))"
)

# Exhaustive hand judgment of the full 747-case citation delta surface.
# Every case not named here was hand-read as a genuine entry. Population,
# branch/form, and decision/judgment assertions below make corpus drift loud.
CITATION_CONTINUATION_IDS = {
    "STATE_NY_AUDC_A18_S1803@1942": "(a) of this act",
    "STATE_NY_AEXC_A19-G_T1_S501-E@985": "year (1965),",
    "STATE_NY_AUDC_A19_S1906-A@524": "(a)(1) of this act",
    "STATE_NY_AUCT_A19_S1906-A@525": "(a)(11) of this act",
    "STATE_NY_ACCA_A18_S1803@1933": "(a) of this act",
    "STATE_OK_T10A_S10A-2-9-102@700": "year (1965), across a blank line",
}

# Exhaustive occurrence-level judgment of the 86 bare-state-code cases.
# The remaining 37 are genuine entries, but the safe proposal deliberately
# leaves all 86 rejected because this branch has no zero-error discriminator.
BARE_CODE_NONSTRUCTURAL_IDS = {
    "STATE_IN_T2_A1_C14_S2-1-14-7@125",
    "STATE_KS_C94_A0_S94-00@20623",
    "STATE_KS_C94_A0_S94-00@28416",
    "STATE_KS_C94_A0_S94-00@29475",
    "STATE_KS_C94_A0_S94-00@30142",
    "STATE_LA_Crevised-statutes_T3_S2803@2068",
    "STATE_LA_Crevised-statutes_T3_S2803@2216",
    "STATE_LA_Crevised-statutes_T3_S2803@2458",
    "STATE_LA_Crevised-statutes_T3_S2803@4132",
    "STATE_LA_Crevised-statutes_T3_S2803@4201",
    "STATE_LA_Crevised-statutes_T3_S2803@4498",
    "STATE_LA_Crevised-statutes_T3_S2803@4610",
    "STATE_LA_Crevised-statutes_T3_S2803@5174",
    "STATE_LA_Crevised-statutes_T3_S2803@5457",
    "STATE_LA_Crevised-statutes_T3_S2803@5648",
    "STATE_LA_Crevised-statutes_T3_S2803@5760",
    "STATE_LA_Crevised-statutes_T3_S2803@5821",
    "STATE_LA_Crevised-statutes_T3_S2803@5888",
    "STATE_LA_Crevised-statutes_T3_S2803@5971",
    "STATE_LA_Crevised-statutes_T3_S2803@6059",
    "STATE_LA_Crevised-statutes_T3_S2803@6287",
    "STATE_LA_Crevised-statutes_T3_S2803@6351",
    "STATE_LA_Crevised-statutes_T3_S2803@6435",
    "STATE_LA_Crevised-statutes_T3_S2803@6539",
    "STATE_LA_Crevised-statutes_T3_S2803@6704",
    "STATE_LA_Crevised-statutes_T3_S2803@6767",
    "STATE_LA_Crevised-statutes_T3_S2803@6845",
    "STATE_LA_Crevised-statutes_T3_S2803@6908",
    "STATE_LA_Crevised-statutes_T3_S2803@6981",
    "STATE_LA_Crevised-statutes_T3_S2803@7043",
    "STATE_LA_Crevised-statutes_T3_S2803@7094",
    "STATE_LA_Crevised-statutes_T3_S2803@7147",
    "STATE_LA_Crevised-statutes_T3_S2803@7231",
    "STATE_LA_Crevised-statutes_T3_S2803@7337",
    "STATE_LA_Crevised-statutes_T3_S2803@7387",
    "STATE_LA_Crevised-statutes_T3_S2803@7451",
    "STATE_LA_Crevised-statutes_T3_S2803@7513",
    "STATE_LA_Crevised-statutes_T3_S2803@7558",
    "STATE_LA_Crevised-statutes_T3_S2803@7679",
    "STATE_LA_Crevised-statutes_T3_S2803@7732",
    "STATE_LA_Crevised-statutes_T3_S2803@7799",
    "STATE_LA_Crevised-statutes_T3_S2803@7914",
    "STATE_LA_Crevised-statutes_T3_S2803@8022",
    "STATE_LA_Crevised-statutes_T3_S2803@8142",
    "STATE_LA_Crevised-statutes_T3_S2803@8348",
    "STATE_LA_Crevised-statutes_T3_S2803@8454",
    "STATE_LA_Crevised-statutes_T3_S2803@8517",
    "STATE_LA_Crevised-statutes_T3_S2803@8582",
    "STATE_LA_Crevised-statutes_T17_S3621@420",
}
PERIOD_NONSTRUCTURAL_IDS = {"STATE_HI_D5_T37_C704_S704-400@558"}

# Exhaustive hand judgment of the 62 structural cases not decided by the
# closed continuation grammar below.  These 13 rows contain 16 genuine
# marker occurrences (the AENV table contributes three); every other
# residual was read and judged a continuation.
STRUCTURAL_GENUINE_CASES = {
    "STATE_DC_T1_C2_S1-204.24b@2472",
    "STATE_DC_T2_C12_S2-1227.05@2493",
    "STATE_DC_T11_C17_S11-1732@5558",
    "STATE_NY_AABP_A1_S103@36",
    "STATE_NY_AENV_A11_T9_S11-0907@7732",
    "STATE_NY_AENV_A11_T9_S11-0907@16411",
    "STATE_NY_AENV_A11_T9_S11-0907@17289",
    "STATE_NY_ASCP_A13_S1310@77",
    "STATE_NY_ALAB_A18_T5_S563@2314",
    "STATE_NY_AEDN_T8_A137_S6813@438",
    "STATE_NY_AEPT_A6_P6_S6-6.4@22",
    "STATE_NY_ACVP_A78_S7802@248",
    "STATE_NY_AEDN_T1_A5_P1_S216-A@1209",
    "STATE_NY_ALAB_A18_T4_S552@2111",
    "STATE_TN_T2_C6_S2-6-304@5552",
    "STATE_TN_T2_C6_S2-6-304@7475",
}
OBVIOUS_CONTINUATION = re.compile(
    r"^(?P<bucket>of\b|[,.;:]|or\b|and\b|hereof\b|hereinabove\b|thereof\b)", re.I
)
PROPOSED_CITATION_CONTINUATION = re.compile(
    r"^[ \t]*(?:,|(?:\((?:[A-Za-z]+|\d+)\)[ \t]*)*of[ \t]+this[ \t]+act\b)", re.I
)


def normalize_ingested_text(text: str | None) -> str:
    """The only ingest normalization relevant to line populations."""
    return (text or "").replace("\\n", "\n")


def _citation_branch(matched_prefix: str) -> str:
    return next(name for name, pattern in CITATION_BRANCHES if pattern.search(matched_prefix))


def _case(
    population: str,
    file_name: str,
    act_id: str,
    text: str,
    token: tuple[int, int, str],
    context_start: int,
    context_text: str,
    gap: str,
) -> dict:
    start, end, marker = token
    case_id = f"{act_id}@{context_start}"
    tail = text[end : end + 160]
    marker_form = "parenthesized" if text[start] == "(" else "period"
    if population == "citation":
        context_branch = _citation_branch(context_text)
        if context_branch == "bare_state_code":
            audit_stratum = "bare_state_code_all_marker_forms"
        elif marker_form == "period":
            audit_stratum = "section_or_symbol_period"
        elif gap.count("\n") + gap.count("\r") == 1:
            audit_stratum = "section_or_symbol_parenthesized_single_break"
        else:
            audit_stratum = "section_or_symbol_parenthesized_multiple_breaks"
        if case_id in BARE_CODE_NONSTRUCTURAL_IDS or case_id in PERIOD_NONSTRUCTURAL_IDS:
            judgment = "nonstructural_token"
        elif case_id in CITATION_CONTINUATION_IDS:
            judgment = "citation_continuation"
        else:
            judgment = "genuine_entry"
        if judgment == "citation_continuation":
            reason = f"hand-read citation continuation: {CITATION_CONTINUATION_IDS[case_id]}"
        elif judgment == "nonstructural_token":
            if case_id.startswith("STATE_LA_Crevised-statutes_T3_S2803"):
                reason = "hand-read highway abbreviation, not a structural marker"
            elif case_id.startswith("STATE_KS_C94_A0_S94-00"):
                reason = "hand-read year/date label, not a structural marker"
            elif case_id in PERIOD_NONSTRUCTURAL_IDS:
                reason = "hand-read commentary heading, not an operative statutory unit"
            else:
                reason = "hand-read abbreviation/table text, not a structural marker"
        elif context_branch == "bare_state_code":
            reason = "hand-read genuine entry; retained as named recall debt for precision"
        elif marker_form == "period":
            reason = "hand-read genuine period entry; retained as named recall debt for precision"
        elif gap.count("\n") + gap.count("\r") > 1:
            reason = "hand-read paragraph-separated structural entry"
        else:
            reason = "hand-read single-line-break structural entry"
        eligible_for_exception = (
            context_branch in {"section_word", "section_symbol"}
            and marker_form == "parenthesized"
        )
        proposed_decision = (
            "accept"
            if eligible_for_exception
            and not PROPOSED_CITATION_CONTINUATION.match(text[end:])
            else "reject"
        )
    else:
        legacy_subset = marker_form == "parenthesized" and bool(
            LEGACY_STRUCTURAL_GAP.fullmatch(gap)
        )
        if legacy_subset:
            obvious = OBVIOUS_CONTINUATION.match(tail.lstrip(" \t"))
            judgment = (
                "genuine_entry" if case_id in STRUCTURAL_GENUINE_CASES else "continuation"
            )
            reason = "new structural entry" if judgment == "genuine_entry" else (
                f"closed continuation grammar: {obvious.group('bucket').lower()}"
                if obvious
                else "hand-read residual continuation"
            )
        else:
            judgment = "unchanged_outside_legacy_audit"
            reason = "proposal preserves production rejection; no behavioral classification needed"
        proposed_decision = "reject"
        context_branch = "structural_word"
        audit_stratum = (
            "legacy_exact_one_lf_parenthesized"
            if legacy_subset
            else "unchanged_outside_legacy_audit"
        )
    return {
        "case_id": case_id,
        "population": population,
        "source_file": file_name,
        "act_id": act_id,
        "context_start": context_start,
        "token_start": start,
        "end": end,
        "token": marker,
        "marker_form": marker_form,
        "context_branch": context_branch,
        "audit_stratum": audit_stratum,
        "gap": gap,
        "line_break_count": gap.count("\n") + gap.count("\r"),
        "matched_text": text[context_start:end],
        "judgment": judgment,
        "proposed_token_decision": proposed_decision,
        "reason": reason,
        "context": text[max(0, context_start - 120) : min(len(text), end + 180)],
    }


def scan(root: Path) -> tuple[list[dict], int, list[str]]:
    files = sorted(root.glob("us_*_statutes.parquet"))
    cases: list[dict] = []
    row_total = 0
    for file in files:
        table = pq.read_table(file, columns=["act_id", "text"])
        row_total += table.num_rows
        texts = pc.replace_substring(
            pc.fill_null(table["text"], ""), pattern="\\n", replacement="\n"
        )
        mask = pc.or_(
            pc.match_substring_regex(texts, pattern=ARROW_CITATION_PATTERN),
            pc.match_substring_regex(texts, pattern=ARROW_STRUCTURAL_PATTERN),
        )
        if not pc.any(mask).as_py():
            continue
        ids = pc.filter(table["act_id"], mask).to_pylist()
        for act_id, text in zip(ids, pc.filter(texts, mask).to_pylist(), strict=True):
            matches = list(CROSSLINE_CASE_PATTERN.finditer(text))
            assert matches
            tokens = {start: (start, end, marker) for start, end, marker in up._iter_us_unit_marker_tokens(text)}
            for match in matches:
                start = match.start("candidate")
                token = tokens.get(start)
                if token is None:
                    continue
                trimmed_end = start
                while trimmed_end and text[trimmed_end - 1].isspace():
                    trimmed_end -= 1
                gap = text[trimmed_end:start]
                assert gap == match.group("gap")
                assert all(character.isspace() for character in gap)
                assert "\n" in gap or "\r" in gap
                citation_match = up._CITATION_NUMBER_SUFFIX_RE.search(text, 0, trimmed_end)
                structural_match = up._STRUCTURAL_UNIT_WORD_SUFFIX_RE.search(
                    text, 0, trimmed_end
                )
                context_text = match.group("context")
                assert (citation_match is not None) != (structural_match is not None)
                context_match = citation_match or structural_match
                assert context_match is not None
                assert context_match.start() == match.start("context")
                assert context_match.group() == context_text
                if citation_match:
                    cases.append(
                        _case(
                            "citation",
                            file.name,
                            act_id,
                            text,
                            token,
                            citation_match.start(),
                            context_text,
                            gap,
                        )
                    )
                if structural_match:
                    cases.append(
                        _case(
                            "structural",
                            file.name,
                            act_id,
                            text,
                            token,
                            structural_match.start(),
                            context_text,
                            gap,
                        )
                    )
    return cases, row_total, [file.name for file in files]


def _marker_metadata(body: str, tokens: list[tuple[int, int, str]]) -> dict[int, tuple]:
    """Simulate production suffix checks from exact match-end indexes.

    Positive lookahead enumerates overlapping suffix matches once per body;
    membership at `trimmed` is equivalent to production's anchored
    `search(body, 0, trimmed)` without its quadratic repeated prefix scan.
    Emitted cases are also asserted against the production calls in `scan`.
    """
    citation_ends = {
        match.start(1) + len(match.group(1))
        for match in _CITATION_SUFFIX_AT_EACH_POSITION.finditer(body)
    }
    structural_ends = {
        match.start(1) + len(match.group(1))
        for match in _STRUCTURAL_SUFFIX_AT_EACH_POSITION.finditer(body)
    }
    usc_ends = {
        match.start(1) + len(match.group(1))
        for match in _USC_SUFFIX_AT_EACH_POSITION.finditer(body)
    }
    bare_state_ends = {
        match.start(1) + len(match.group(1))
        for match in _BARE_STATE_SUFFIX_AT_EACH_POSITION.finditer(body)
    }
    result = {}
    for start, end, _ in tokens:
        trimmed = start
        while trimmed and body[trimmed - 1].isspace():
            trimmed -= 1
        structural = trimmed in structural_ends
        citation = trimmed in citation_ends
        crossed = "\n" in body[trimmed:start] or "\r" in body[trimmed:start]
        continuation = bool(PROPOSED_CITATION_CONTINUATION.match(body[end:]))
        eligible_parenthesized_citation = (
            citation
            and body[start] == "("
            and trimmed not in usc_ends
            and trimmed not in bare_state_ends
        )
        result[start] = (
            structural or citation,
            crossed,
            structural,
            continuation,
            eligible_parenthesized_citation,
        )
    return result


def _trace(
    body: str,
    targets: set[int],
    mode: str,
    tokens: list[tuple[int, int, str]],
    metadata: dict[int, tuple],
) -> dict[int, tuple]:
    stack: list[UnitStep] = []
    ladder = None
    last_rejected_end = None
    result = {}
    for start, end, token in tokens:
        current, crossed, structural, continuation, eligible_citation = metadata[start]
        reject = current if mode == "current" else current and (
            not crossed
            or (
                mode == "proposed"
                and (structural or not eligible_citation or continuation)
            )
        )
        chained = last_rejected_end is not None and up._CHAIN_CONNECTOR_GAP_RE.fullmatch(
            body[last_rejected_end:start]
        )
        if chained or reject:
            last_rejected_end = end
        else:
            last_rejected_end = None
            if ladder is None:
                if up._marker_matches_kind(token, "digit"):
                    ladder = up._DIGIT_OUTERMOST_UNIT_PATH_LADDER
                elif up._marker_matches_kind(token, "upper_alpha"):
                    ladder = up._OH_UPPER_ALPHA_OUTERMOST_UNIT_PATH_LADDER
                elif up._marker_matches_kind(token, "lower_alpha"):
                    ladder = up._UNIT_PATH_LADDER
            if ladder is not None:
                expected = ladder[len(stack)] if len(stack) < len(ladder) else None
                if expected and up._marker_matches_kind(token, expected):
                    stack.append(UnitStep(kind=expected, value=token))
                else:
                    for index, step in enumerate(stack):
                        if up._marker_matches_kind(token, step.kind):
                            stack = stack[: index + 1]
                            stack[index] = UnitStep(kind=step.kind, value=token)
                            break
        if end in targets:
            result[end] = tuple((step.kind, step.value) for step in stack)
    return result


def add_path_deltas(cases: list[dict], root: Path) -> None:
    by_row: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for case in cases:
        by_row[(case["source_file"], case["act_id"])].append(case)
    tables = {}
    for (file_name, act_id), row_cases in by_row.items():
        if file_name not in tables:
            table = pq.read_table(root / file_name, columns=["act_id", "text"])
            tables[file_name] = dict(zip(table["act_id"].to_pylist(), table["text"].to_pylist()))
        body = normalize_ingested_text(tables[file_name][act_id])
        targets = {case["end"] for case in row_cases}
        tokens = [
            token
            for token in up._iter_us_unit_marker_tokens(body)
            if token[1] <= max(targets)
        ]
        metadata = _marker_metadata(body, tokens)
        traces = {
            mode: _trace(body, targets, mode, tokens, metadata)
            for mode in ("current", "proposed", "blanket")
        }
        for case in row_cases:
            for mode, trace in traces.items():
                case[f"{mode}_path"] = trace[case["end"]]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: measure_g4_newline_context.py CORPUS_DIR")
    root = Path(sys.argv[1]).resolve()
    cases, rows, files = scan(root)
    citations = [case for case in cases if case["population"] == "citation"]
    structural = [case for case in cases if case["population"] == "structural"]
    legacy_structural = [
        case
        for case in structural
        if case["marker_form"] == "parenthesized"
        and LEGACY_STRUCTURAL_GAP.fullmatch(case["gap"])
    ]
    assert len(files) == 53 and rows == 2_038_247
    assert (len(citations), len({c["act_id"] for c in citations})) == (747, 501)
    assert Counter((c["context_branch"], c["marker_form"]) for c in citations) == {
        ("section_symbol", "parenthesized"): 425,
        ("section_word", "parenthesized"): 188,
        ("bare_state_code", "parenthesized"): 16,
        ("section_symbol", "period"): 18,
        ("section_word", "period"): 30,
        ("bare_state_code", "period"): 70,
    }
    assert Counter(c["judgment"] for c in citations) == {
        "genuine_entry": 691,
        "citation_continuation": 6,
        "nonstructural_token": 50,
    }
    assert {
        c["case_id"]
        for c in citations
        if c["judgment"] == "citation_continuation"
    } == set(CITATION_CONTINUATION_IDS)
    assert {
        c["case_id"] for c in citations if c["judgment"] == "nonstructural_token"
    } == BARE_CODE_NONSTRUCTURAL_IDS | PERIOD_NONSTRUCTURAL_IDS
    assert Counter(c["audit_stratum"] for c in citations) == {
        "bare_state_code_all_marker_forms": 86,
        "section_or_symbol_period": 48,
        "section_or_symbol_parenthesized_single_break": 31,
        "section_or_symbol_parenthesized_multiple_breaks": 582,
    }
    assert Counter((c["judgment"], c["proposed_token_decision"]) for c in citations) == {
        ("genuine_entry", "accept"): 607,
        ("genuine_entry", "reject"): 84,
        ("citation_continuation", "reject"): 6,
        ("nonstructural_token", "reject"): 50,
    }
    assert (len(structural), len({c["act_id"] for c in structural})) == (3_056, 2_369)
    assert Counter(c["marker_form"] for c in structural) == {
        "parenthesized": 2_824,
        "period": 232,
    }
    assert (len(legacy_structural), len({c["act_id"] for c in legacy_structural})) == (
        1_221,
        835,
    )
    assert Counter(c["source_file"] for c in legacy_structural) == {
        "us_ny_statutes.parquet": 1_216,
        "us_dc_statutes.parquet": 3,
        "us_tn_statutes.parquet": 2,
    }
    assert Counter(c["judgment"] for c in legacy_structural) == {
        "continuation": 1_205,
        "genuine_entry": 16,
    }
    add_path_deltas(cases, root)
    rng = random.Random(20260805)
    strata = defaultdict(list)
    for case in legacy_structural:
        strata[case["reason"]].append(case["case_id"])
    audit_ids = sorted(
        case_id
        for reason, ids in strata.items()
        for case_id in (ids if len(ids) <= 25 else rng.sample(ids, 25))
    )
    summary = {
        "snapshot": SNAPSHOT,
        "glob": "us_*_statutes.parquet",
        "file_count": len(files),
        "row_count": rows,
        "normalization": "text.replace('\\\\n', '\\n') exactly as ingest_us_statute_rows",
        "population_definition": (
            "Exact production citation/structural suffix regexes immediately before the "
            "exact production parenthesized/period candidate-token union, with an arbitrary "
            "str.isspace() gap containing at least one CR or LF."
        ),
        "citation": {
            "occurrences": len(citations),
            "rows": len({c["act_id"] for c in citations}),
            "judgments": Counter(c["judgment"] for c in citations),
            "proposed_direct_decisions": Counter(
                c["proposed_token_decision"] for c in citations
            ),
            "by_context_branch_and_marker_form": Counter(
                f"{c['context_branch']}::{c['marker_form']}" for c in citations
            ),
            "exhaustive_audit": {
                "reviewed_occurrences": len(citations),
                "mutually_exclusive_strata": Counter(
                    c["audit_stratum"] for c in citations
                ),
                "method": (
                    "Hand-read every case: all bare-state-code forms first; all remaining "
                    "period forms second; then every residual Section/section-symbol "
                    "parenthesized case split by one versus multiple physical line breaks. "
                    "Per-case judgment, reason, context, gap, branch, and marker form are in "
                    "the full ledger."
                ),
            },
            "changed_surface": {
                "definition": "Section/section-symbol + parenthesized token only",
                "occurrences": sum(
                    c["context_branch"] in {"section_word", "section_symbol"}
                    and c["marker_form"] == "parenthesized"
                    for c in citations
                ),
                "judgments": Counter(
                    c["judgment"]
                    for c in citations
                    if c["context_branch"] in {"section_word", "section_symbol"}
                    and c["marker_form"] == "parenthesized"
                ),
                "false_accepts": sum(
                    c["judgment"] != "genuine_entry"
                    and c["proposed_token_decision"] == "accept"
                    for c in citations
                ),
                "false_rejects": sum(
                    c["judgment"] == "genuine_entry"
                    and c["proposed_token_decision"] == "reject"
                    and c["context_branch"] in {"section_word", "section_symbol"}
                    and c["marker_form"] == "parenthesized"
                    for c in citations
                ),
            },
            "retained_recall_debt": {
                "bare_state_code_genuine_entries": sum(
                    c["judgment"] == "genuine_entry"
                    and c["context_branch"] == "bare_state_code"
                    for c in citations
                ),
                "period_genuine_entries": sum(
                    c["judgment"] == "genuine_entry" and c["marker_form"] == "period"
                    for c in citations
                    if c["context_branch"] != "bare_state_code"
                ),
            },
            "genuine_entry_path_deltas": sum(
                c["judgment"] == "genuine_entry"
                and c["current_path"] != c["proposed_path"]
                for c in citations
            ),
            "current_to_proposed_path_deltas": sum(
                c["current_path"] != c["proposed_path"] for c in citations
            ),
            "current_to_blanket_path_deltas": sum(
                c["current_path"] != c["blanket_path"] for c in citations
            ),
            "current_to_blanket_delta_rows": len(
                {
                    c["act_id"]
                    for c in citations
                    if c["current_path"] != c["blanket_path"]
                }
            ),
        },
        "structural": {
            "occurrences": len(structural),
            "rows": len({c["act_id"] for c in structural}),
            "by_marker_form": Counter(c["marker_form"] for c in structural),
            "legacy_exact_one_lf_parenthesized_subset": {
                "occurrences": len(legacy_structural),
                "rows": len({c["act_id"] for c in legacy_structural}),
                "judgments": Counter(c["judgment"] for c in legacy_structural),
                "audit_case_count": len(audit_ids),
                "audit_case_ids": audit_ids,
            },
            "current_to_proposed_path_deltas": sum(
                c["current_path"] != c["proposed_path"] for c in structural
            ),
            "current_to_blanket_path_deltas": sum(
                c["current_path"] != c["blanket_path"] for c in structural
            ),
            "current_to_blanket_delta_rows": len(
                {
                    c["act_id"]
                    for c in structural
                    if c["current_path"] != c["blanket_path"]
                }
            ),
        },
        "proposal": (
            "Keep structural-word, bare-state-code, full-USC, and every period-style "
            "cross-newline rejection unchanged. Only Section/section-symbol plus a "
            "parenthesized token is eligible; reject its comma/year or optional "
            "parenthetical-chain + 'of this act' continuations, otherwise accept. "
            "Same-line behavior is unchanged."
        ),
    }
    out = Path(__file__).resolve().parent
    (out / "2026-08-05-defs-core-follow-on-2-g4-newline-full.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "2026-08-05-defs-core-follow-on-2-g4-newline-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=dict))


if __name__ == "__main__":
    main()
