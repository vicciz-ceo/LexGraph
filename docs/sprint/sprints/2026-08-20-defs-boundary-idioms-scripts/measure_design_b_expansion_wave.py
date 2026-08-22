"""Design (b) expansion-wave reconstruction (read-only precision sampler).

Sprint 2026-08-20-defs-boundary-idioms. Reconstructs Item 2 design (b)'s
"expansion wave" -- the (row, term, definition_text) items per-term
admission would NEWLY add on rows where the primary engine (as it exists
TODAY, at HEAD 326f898, i.e. after Item 1's idiom widening but BEFORE
Item 2/3 land) already finds >= 1 entry -- per the log doc's own "Planner
pass 2, Item 2 design" + "Simulation methodology" sections. This population
is DISTINCT from the 130-loss-recovery population (rows where the primary
engine finds 0 entries today, which get the SAME merge but by construction
never "collide" with anything -- that is Item 2's headline fix, not the
expansion wave under study here).

No backend/ files are modified. Design (b)'s guard-site change is:

    if not candidates and heading_was_derived:
        candidates = _extract_inline_quoted_definitions(text, scope=scope)

becomes (informally) an always-run-when-heading_was_derived merge: run the
fallback unconditionally whenever heading_was_derived, and admit a fallback
candidate into `candidates` only when (a) its own term does not collide
with any primary-engine term already in `candidates` on that row, and (b)
it passes the evidence-derived implausible-capture filter (log doc: bare
stopword term, or term/definition_text beginning with a 4-digit-year-dash
amendment-caption shape).

Key simplification (verified, not assumed): for the population this script
targets -- rows where `extract_definitions_from_section` already returns
>= 1 candidate under TODAY's (unpatched) code -- the guard's `if not
candidates` branch is provably False, so TODAY's unpatched
`extract_definitions_from_section` already returns EXACTLY the primary
engine's own candidates (the fallback never fires for these rows in
production, today, by construction of the existing guard). So no class
patch is needed to obtain "primary_candidates" for this population; the
script calls the REAL, unmodified `extract_definitions_from_section` to get
it, and separately calls the REAL, unmodified `_extract_inline_quoted_
definitions` to get the fallback's own candidates, then applies design
(b)'s merge/filter itself (a pure function below, `admit_fallback`) to
decide what design (b) would ADD beyond what's already there. This is
mechanically identical to monkeypatching the guard and calling the patched
method -- it is simpler because, for exactly this population, the branch
design (b) changes is never taken by the unpatched code, so calling around
it is equivalent to calling through a patch of it.

Scope, matching the Planner's own scoping (log doc: "seeded 200-row
sample... across the 16 jurisdictions reachable through family-3/OH/ME"):
this script does NOT invent a different population -- it uses the SAME 16
jurisdictions (US-WA, US-VA, US-FED, US-UT, US-TX, US-SC, US-AZ, US-NJ,
US-MI, US-ND, US-NY, US-OK, US-NM, US-NV, US-OH, US-ME), but runs the FULL
row population within those 16 jurisdictions' files (683,393 rows) rather
than a 200-row sample of them -- a full census within the Planner's own
scope, not a variant of the mechanism. (Timing check: ~1,100 rows/sec for
the heading-recognition prefix alone on this machine -- the full 683,393
rows are well within this task's time budget.)

Corpus: the pinned snapshot named in run_gate2.sh,
/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = Path(
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/"
    "301000fc3465374ee0f23c3c6953a8a861e95cad"
)
OUT_DIR = Path(__file__).resolve().parent / "run" / "design_b"

JURISDICTION_FILES = [
    "us_wa_statutes.parquet", "us_va_statutes.parquet", "us_federal_statutes.parquet",
    "us_ut_statutes.parquet", "us_tx_statutes.parquet", "us_sc_statutes.parquet",
    "us_az_statutes.parquet", "us_nj_statutes.parquet", "us_mi_statutes.parquet",
    "us_nd_statutes.parquet", "us_ny_statutes.parquet", "us_ok_statutes.parquet",
    "us_nm_statutes.parquet", "us_nv_statutes.parquet", "us_oh_statutes.parquet",
    "us_me_statutes.parquet",
]

# The 130-loss-recovery population (investigation.md's full 134-row table,
# grouped to its 100 distinct (jurisdiction, source_row) rows -- see
# expansion_precision.md's "Method" section for the full table this was
# transcribed from). Any row here is EXCLUDED from the expansion-wave
# population: design (b)'s merge on these rows IS the 130-loss recovery,
# not new incremental expansion, per this task's explicit scope.
EXCLUDE_ROWS: set[tuple[str, int]] = {
    ("US-FED", 72), ("US-FED", 2333), ("US-FED", 2476), ("US-FED", 3651),
    ("US-FED", 4978), ("US-FED", 11310), ("US-FED", 12889), ("US-FED", 34432),
    ("US-FED", 45011),
    ("US-ME", 505), ("US-ME", 1027), ("US-ME", 1783), ("US-ME", 4663),
    ("US-ME", 5405), ("US-ME", 5529), ("US-ME", 9589), ("US-ME", 11069),
    ("US-ME", 16584), ("US-ME", 18220),
    ("US-MI", 10463),
    ("US-NJ", 1732), ("US-NJ", 2286), ("US-NJ", 11124), ("US-NJ", 13259),
    ("US-NJ", 21386), ("US-NJ", 23205),
    ("US-NY", 601), ("US-NY", 691), ("US-NY", 1504), ("US-NY", 1978),
    ("US-NY", 2032), ("US-NY", 2768), ("US-NY", 4091), ("US-NY", 4747),
    ("US-NY", 5396), ("US-NY", 6869), ("US-NY", 7009), ("US-NY", 7103),
    ("US-NY", 9087), ("US-NY", 10039), ("US-NY", 13882), ("US-NY", 16586),
    ("US-NY", 19198), ("US-NY", 26977), ("US-NY", 27664), ("US-NY", 27958),
    ("US-NY", 29376),
    ("US-OH", 1511), ("US-OH", 2752), ("US-OH", 3296), ("US-OH", 3447),
    ("US-OH", 4820), ("US-OH", 4941), ("US-OH", 6141), ("US-OH", 6791),
    ("US-OH", 6965), ("US-OH", 7807), ("US-OH", 9540), ("US-OH", 9694),
    ("US-OH", 11936), ("US-OH", 12152), ("US-OH", 12352), ("US-OH", 12756),
    ("US-OH", 13220), ("US-OH", 13992), ("US-OH", 15375), ("US-OH", 16260),
    ("US-OH", 17614), ("US-OH", 18568), ("US-OH", 18663), ("US-OH", 18782),
    ("US-OH", 20067), ("US-OH", 20117), ("US-OH", 22284), ("US-OH", 22796),
    ("US-OH", 24054), ("US-OH", 25046), ("US-OH", 29285), ("US-OH", 29721),
    ("US-OH", 29882), ("US-OH", 30073), ("US-OH", 31324), ("US-OH", 31905),
    ("US-OH", 32464),
    ("US-OK", 4467), ("US-OK", 5753), ("US-OK", 8656),
    ("US-SC", 404), ("US-SC", 3814), ("US-SC", 7246), ("US-SC", 18781),
    ("US-VA", 3366), ("US-VA", 7729), ("US-VA", 9693), ("US-VA", 13341),
    ("US-WA", 717), ("US-WA", 1171), ("US-WA", 9202), ("US-WA", 19155),
    ("US-WA", 31321),
}
assert len(EXCLUDE_ROWS) == 100, f"expected 100 distinct excluded rows, got {len(EXCLUDE_ROWS)}"

_STOPWORDS = {"for", "and", "or", "the", "a", "an", "of", "in", "to", "with", "by"}
_YEAR_DASH_RE = re.compile(r"^\d{4}[—–-]")


def is_implausible(term: str, definition_text: str) -> bool:
    """Design (b)'s evidence-derived implausible-capture filter, exactly
    per the log doc: a bare stopword term, or a term/definition_text
    beginning with a 4-digit-year+dash amendment-caption shape."""
    if term.strip().lower() in _STOPWORDS:
        return True
    if _YEAR_DASH_RE.match(term) or _YEAR_DASH_RE.match(definition_text):
        return True
    return False


def admit_fallback(primary_candidates, fallback_candidates):
    """Design (b)'s merge/filter, applied as a pure function to two
    already-computed candidate lists. Returns the list of fallback
    candidates design (b) would ADMIT (i.e. append to `candidates`) beyond
    what the primary engine already found."""
    primary_terms = {t for c in primary_candidates for t in c.terms}
    admitted = []
    for fc in fallback_candidates:
        assert len(fc.terms) == 1, "_extract_inline_quoted_definitions always emits 1-term candidates"
        term = fc.terms[0]
        if term in primary_terms:
            continue
        if is_implausible(term, fc.definition_text):
            continue
        admitted.append(fc)
    return admitted


def jurisdiction_of(path: Path) -> str:
    code = path.name.removeprefix("us_").removesuffix("_statutes.parquet")
    return "US-FED" if code == "federal" else f"US-{code.upper()}"


def load_production():
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    import app.definition_links.rules.us_body_preamble  # noqa: F401  (registration side-effect)
    from app.definition_links.normalize import strip_wikilinks
    from app.definition_links.profiles import get_profile
    from app.definition_links.us_profile import _extract_inline_quoted_definitions

    return strip_wikilinks, get_profile, _extract_inline_quoted_definitions


def detect(profile, body: str, raw: str, row: dict):
    """Exactly mirrors measure_actual_production_all_rows.capture()'s own
    recognized/derived/b1_winner/scope/heading_was_derived detection (the
    `current=True` branch, i.e. TODAY's real production dispatch), minus
    the `extract_local_scope_definitions` call (irrelevant to the
    fallback-suppression guard, which lives entirely inside
    `extract_definitions_from_section`)."""
    heading = row["section_title"] or ""
    recognized = profile.is_definitions_heading(heading, body)
    rule_only = getattr(profile, "heading_recognized_only_by_rule", None)
    recognized_by_registered_rule = bool(
        recognized and callable(rule_only) and rule_only(heading, body)
    )
    derived = None
    if not recognized:
        derive_b1 = getattr(profile, "derive_body_preamble_match", None)
        if callable(derive_b1):
            derived = derive_b1(
                heading, body, raw_source=raw,
                article_number=row["section_number"] or "", chapter=row["chapter"],
            )
    if not recognized and derived is None:
        return None
    b1_winner = bool(getattr(derived, "b1_winner", False))
    scope = profile.determine_scope(body)
    heading_was_derived = True if b1_winner else ((derived is not None) or recognized_by_registered_rule)
    return scope, heading_was_derived, b1_winner, raw


def main() -> None:
    strip_wikilinks, get_profile, _extract_inline_quoted_definitions = load_production()

    wave: list[dict] = []
    rows_scanned = 0
    rows_heading_was_derived = 0
    rows_primary_nonempty = 0
    rows_primary_nonempty_not_excluded = 0
    rows_gaining_terms = 0

    for filename in JURISDICTION_FILES:
        path = SNAPSHOT / filename
        jurisdiction = jurisdiction_of(path)
        profile = get_profile(jurisdiction)
        for batch_number, batch in enumerate(
            pq.ParquetFile(path).iter_batches(
                columns=["act_id", "section_title", "text", "chapter", "section_number"],
                batch_size=4096,
            )
        ):
            for offset, row in enumerate(batch.to_pylist()):
                row_number = batch_number * 4096 + offset
                rows_scanned += 1
                raw = row["text"] or ""
                body, _ = strip_wikilinks(profile.normalize_for_parsing(raw))
                detection = detect(profile, body, raw, row)
                if detection is None:
                    continue
                scope, heading_was_derived, b1_winner, raw_source = detection
                if not heading_was_derived:
                    continue
                rows_heading_was_derived += 1

                if b1_winner:
                    primary_candidates = profile.extract_definitions_from_section(
                        body, scope=scope, heading_was_derived=True,
                        raw_source=raw_source, b1_winner=True,
                    )
                else:
                    primary_candidates = profile.extract_definitions_from_section(
                        body, scope=scope, heading_was_derived=True,
                    )

                if len(primary_candidates) == 0:
                    continue  # the 130-loss-recovery mechanism, not this population
                rows_primary_nonempty += 1

                if (jurisdiction, row_number) in EXCLUDE_ROWS:
                    continue
                rows_primary_nonempty_not_excluded += 1

                fallback_candidates = _extract_inline_quoted_definitions(body, scope=scope)
                if not fallback_candidates:
                    continue
                admitted = admit_fallback(primary_candidates, fallback_candidates)
                if not admitted:
                    continue
                rows_gaining_terms += 1
                for candidate in admitted:
                    wave.append({
                        "jurisdiction": jurisdiction,
                        "source_file": filename,
                        "source_row": row_number,
                        "act_id": str(row["act_id"] or f"{filename}:{row_number}"),
                        "term": candidate.terms[0],
                        "definition_text": candidate.definition_text,
                        "scope": candidate.scope,
                    })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wave.sort(key=lambda r: (r["jurisdiction"], r["source_file"], r["source_row"], r["term"]))
    with (OUT_DIR / "expansion_wave.jsonl").open("w", encoding="utf-8") as handle:
        for item in wave:
            handle.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")

    summary = {
        "rows_scanned_16_jurisdictions": rows_scanned,
        "rows_heading_was_derived": rows_heading_was_derived,
        "rows_primary_nonempty_today": rows_primary_nonempty,
        "rows_primary_nonempty_excluding_130_recovery": rows_primary_nonempty_not_excluded,
        "rows_gaining_new_fallback_terms": rows_gaining_terms,
        "new_terms_total": len(wave),
        "by_jurisdiction": {},
    }
    by_j: dict[str, int] = {}
    for item in wave:
        by_j[item["jurisdiction"]] = by_j.get(item["jurisdiction"], 0) + 1
    summary["by_jurisdiction"] = dict(sorted(by_j.items()))
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
