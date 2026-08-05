"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, Job 3.

The cluster model: every predicate here is a COMMITTED, EXECUTABLE
function (never a prose sentence -- contract's own binding requirement),
operating on rows produced by `c1_denominator.py`.

## Two populations, two cluster levels -- a resolution of an ambiguity
## in the contract, named explicitly for the panel manager to confirm
## or correct

The contract's own text uses "candidate row" at TWO different
granularities without reconciling them: cluster 1's predicate and its
own disposal count ("~91,605 characters... 33.1%") are stated at the
CHARACTER level (33.1% of 276,815 raw quote characters), while C2 says
"the full ~92,600-row population" -- the SPAN count, not the character
count. Both cannot be the same population (33.1% of 276,815 is ~91,600;
33.1% of 92,600 would be ~30,600 -- a different, wrong number).

Resolution adopted here, after measuring both (see `c1_denominator.py`'s
own docstring for the reproduction): this module implements TWO cluster
levels.

- **Level 0 (character level, cluster 1 only).** Every raw quote
  character in the corpus (article-body text, normalized) is either
  word-internal (this cluster) or eligible. This partition is total and
  disjoint BY CONSTRUCTION (a single boolean predicate: every character
  is on exactly one side) -- there is no other Level-0 cluster, and none
  is needed. Level 0 is how the ~92,602-span population in Level 1 gets
  CONSTRUCTED (word-internal characters are excluded before pairing),
  not itself a partition of that population.
- **Level 1 (span level, clusters 2+).** The ~92,602 paired candidate
  spans -- built from Level-0-eligible characters only -- are what C2's
  backbone test actually iterates, matching the contract's own "~92,600-
  row population" wording literally. This is genuinely INCOMPLETE this
  round (Job 3: "propose the initial cluster set... do not attempt all
  20-40") -- most rows are expected to remain unassigned, which is C2's
  expected RED state, not a bug in this module.

## Buckets

Every cluster is assigned exactly one bucket: `captured` / `fixed` /
`proven-not-a-definition` / `director-named residual`. `fixed` is not
used by any cluster this round (C4's fix loop, not opened yet).
"""

from __future__ import annotations

_HEB_LETTER_LOW = "א"
_HEB_LETTER_HIGH = "ת"


def is_hebrew_letter(ch: str) -> bool:
    return bool(ch) and _HEB_LETTER_LOW <= ch <= _HEB_LETTER_HIGH


# --- Level 0 -- cluster 1 (character level) ---------------------------

CLUSTER_1_WORD_INTERNAL_QUOTE = "word_internal_quote"


def is_word_internal_quote(prev_char: str, next_char: str) -> bool:
    """Cluster 1's predicate, verbatim per the contract: a quote character
    immediately preceded AND followed by a Hebrew letter (U+05D0-U+05EA),
    with no intervening whitespace, is word-internal and cannot be a term
    delimiter. Falsifiable: feed it any two characters and it returns a
    definite verdict, no context beyond the two adjacent characters
    needed -- deliberately the simplest possible executable predicate,
    matching the contract's own stated form exactly."""
    return is_hebrew_letter(prev_char) and is_hebrew_letter(next_char)


def is_vav_conjunction_false_positive(prev_char: str, before_prev_char: str) -> bool:
    """A MEASURED false-positive candidate of `is_word_internal_quote`,
    found by tracing `c1_denominator.py`'s own `unpaired_trailing_quotes`
    diagnostic to real corpus text (not assumed): a quote whose
    `prev_char` is a bare, standalone vav conjunction ("ו", itself
    preceded by whitespace or start-of-body) is the OPENING delimiter of
    a second term in a `"term1" ו"term2"` list (e.g. `"רכב" ו"דרך"` --
    "car" AND "road", two real terms), never an abbreviation. Cluster 1's
    literal predicate cannot distinguish this from a genuine word-internal
    abbreviation (both neighbors are Hebrew letters either way), so this
    is reported as a SEPARATE diagnostic, never folded into cluster 1's
    own bucketing this round -- see `c1_denominator.py`'s docstring for
    the measured corpus-wide count (2,096 / 91,611 = 2.3%, 1,004 files)
    and the independent confirmation (correcting for it drops the
    unrelated `unpaired_trailing_quotes` diagnostic by 83%, 1,676 -> 282).
    This function only classifies the `prev_char` side; `next_char` being
    a Hebrew letter is already guaranteed by the caller (only invoked
    when `is_word_internal_quote` was already True)."""
    return prev_char == "ו" and (before_prev_char == "" or before_prev_char.isspace())


# --- Level 1 -- span-level clusters (implemented this round) ----------

CLUSTER_PRODUCTION_CAPTURED = "production_captured"
CLUSTER_WIKI_TABLE_MARKUP_ATTRIBUTE = "wiki_table_markup_attribute"
CLUSTER_INTERPRETATION_LAWS_NEVER_REACHED = "interpretation_laws_never_reached"

# M31 enumerated residual (6): 29 never-reached entry lines, named
# examples חוק הפרשנות art.3 and פקודת הפרשנות art.1 -- the Interpretation
# Laws' ENTIRE definitions lists. Filenames confirmed against the real
# corpus directory listing (not assumed) before being hardcoded here.
_INTERPRETATION_LAW_ARTICLES = {
    ("פקודת הפרשנות.wiki", "1"),
    ("חוק הפרשנות.wiki", "3"),
}


def cluster_wiki_table_markup_attribute(row: dict) -> bool:
    """Found this round, by hand-reading a sample of the ~16% of spans
    whose `term_text` has no Hebrew letter at all (e.g. `'100px'`,
    `'table-layout: fixed; width: 100%;'`): MediaWiki table markup
    (`! width="200px" | ...`) uses `"` as an HTML-attribute delimiter.
    This is counted as a raw quote character by C1's signal-agnostic scan
    (correctly -- M18 forbids filtering the DENOMINATOR by capture-rule
    relevance) but is never Hebrew legal-drafting text. Measured
    corpus-wide (`c1_denominator.py`'s own `_HTML_ATTR_RE`, which computes
    this row's own `preceded_by_html_attribute` feature): 13,114 eligible
    quote characters / 251 files match `[A-Za-z][A-Za-z-]*=` immediately
    before the quote (align/width/style/colspan/rowspan/dir/class/...).
    Verified safe: zero of these spans are ever `production_captured`
    (sampled and spot-checked -- see the sprint log)."""
    return bool(row["preceded_by_html_attribute"])


def cluster_production_captured(row: dict) -> bool:
    """A span whose exact text (`term_text`) appears among the terms of a
    real `DefinitionCandidate` the UNMODIFIED production `HebrewProfile`
    dispatch produced for this span's own article (see
    `c1_denominator.py::_production_captured_terms`, which mirrors
    `pipeline.py` lines 236-273 exactly). Known limitation (string
    membership, not offset identity): a term string that is genuinely
    captured from a DIFFERENT entry in the same article, but happens to
    be textually identical to this span, is indistinguishable from this
    span being the captured one. Named in the sprint log's honest gaps,
    not hidden."""
    return bool(row["production_captured"])


def cluster_interpretation_laws_never_reached(row: dict) -> bool:
    """M31 residual (6): the Interpretation Laws' definitions lists are
    never reached by any rule today. A precise, named, small cluster --
    exact (file, article_number) match, uncaptured. Deliberately NOT a
    coarse "any uncaptured span in a definitions-heading article" rule;
    see this module's docstring for why that coarser form was rejected
    this round (it would launder six textually-distinct residual classes
    into one undifferentiated bucket, exactly what C2's design is meant
    to prevent)."""
    key = (row["file"], row["article_number"])
    return key in _INTERPRETATION_LAW_ARTICLES and not row["production_captured"]


# `(cluster_id, predicate, bucket, description)` -- registration order is
# NOT significant for correctness (assign_span_clusters below evaluates
# every predicate and reports ALL matches, so a double-assignment is a
# genuine finding, never silently resolved by "first wins").
SPAN_CLUSTERS: tuple[tuple[str, "callable", str, str], ...] = (
    (
        CLUSTER_WIKI_TABLE_MARKUP_ATTRIBUTE,
        cluster_wiki_table_markup_attribute,
        "proven-not-a-definition",
        "MediaWiki table markup (`width=\"...\"` etc.) -- an HTML-attribute "
        "quote, never Hebrew legal-drafting text. 13,114 spans / 251 files.",
    ),
    (
        CLUSTER_PRODUCTION_CAPTURED,
        cluster_production_captured,
        "captured",
        "Span text appears among a real DefinitionCandidate.terms produced "
        "by the unmodified production HebrewProfile dispatch for its article.",
    ),
    (
        CLUSTER_INTERPRETATION_LAWS_NEVER_REACHED,
        cluster_interpretation_laws_never_reached,
        "director-named residual",
        "M31 residual (6): חוק הפרשנות art.3 / פקודת הפרשנות art.1, "
        "uncaptured -- the Interpretation Laws' entire definitions lists.",
    ),
)


def assign_span_clusters(row: dict) -> list[str]:
    """Every span-level cluster id whose predicate matches `row`. Empty
    list == unassigned (the expected, honest state for most rows this
    round -- C2's backbone test reports these, it does not hide them)."""
    return [cluster_id for cluster_id, predicate, _, _ in SPAN_CLUSTERS if predicate(row)]


# --- Proposed (NOT implemented this round) -- Job 3's own explicit ----
# --- instruction: "do not attempt all 20-40". Named here so the shape --
# --- of the remaining work is visible to the panel manager and to -----
# --- whoever runs C4's fix loop, not left as a bare unassigned count. --

PROPOSED_CLUSTERS = (
    {
        "id": "vav_conjunction_word_internal_false_positive",
        "seed_residual": "NOT inherited -- found this round, by this "
        "Planner, tracing c1_denominator.py's own unpaired_trailing_"
        "quotes diagnostic (1,676/128,234 articles) to real corpus text.",
        "predicate_sketch": "is_vav_conjunction_false_positive(prev_char, "
        "before_prev_char) -- see this module's own function. Measured: "
        "2,096 of 91,611 cluster-1 disposals (2.3%), 1,004 files, are a "
        "standalone-vav second-term opener ('רכב\" ו\"דרך') misclassified "
        "as word-internal. Correcting it drops odd-parity articles 83% "
        "(1,676 -> 282) and raises the naive eligible/2 span estimate "
        "from ~92,602 to ~93,650 (+1.1%).",
        "bucket": "NOT YET DECIDED -- a candidate CORRECTION to cluster "
        "1's own contract-specified predicate, reported for the panel "
        "manager's sign-off, not applied unilaterally by this Planner. "
        "If confirmed, this stops being a 'cluster' at all and becomes "
        "an amendment to cluster 1 itself.",
    },
    {
        "id": "definitions_heading_uncaptured_numbered_subitems",
        "seed_residual": "parent contract residual (1): 44 articles / ~202 "
        "terms, class-(d) numbered/lettered sub-item shape, zero capture.",
        "predicate_sketch": "is_definitions_heading_article and not "
        "production_captured and the article body has numbered/lettered "
        "sub-item markers (e.g. leading `(\\d+)`/`(א)`) with no `:-` line "
        "-- needs a real structural detector, not yet built.",
        "bucket": "director-named residual",
    },
    {
        "id": "class_c_local_scope_under_claims",
        "seed_residual": "parent contract residual (2): 15/44 class-C "
        "scope='local' firing articles under-claim (never over-claim).",
        "predicate_sketch": "requires replicating determine_scope's "
        "class-C heading-trigger detection to identify the firing "
        "population, then checking for a same-article genuine mention "
        "with no USES_DEFINITION edge -- a containment-side check, not a "
        "pure span-text predicate; does not fit this module's row shape "
        "without extending it with mention data.",
        "bucket": "director-named residual",
    },
    {
        "id": "cross_path_separator_divergence_and_position_zero_anchor",
        "seed_residual": "parent contract residual (3): ~67-254 cross-path "
        "separator divergences (M30, zero over-capture) + parse_entry's "
        "position-0 anchor dropping entries with leading content.",
        "predicate_sketch": "is_definitions_heading_article is False and "
        "not production_captured and the article body has a genuine "
        "list-shape entry line whose header does not start at column 0 "
        "(leading `<ins>`/numbering) or uses a qualifier-interrupted "
        "separator M30 named -- needs the real list-shape entry scanner, "
        "not re-implemented here.",
        "bucket": "director-named residual",
    },
    {
        "id": "siman_chelek_captured_but_uncontained",
        "seed_residual": "parent contract residual (4): 2 core-blocked "
        "containment REDs (M20/M27) -- closes on core-2 G9 merge PLUS an "
        "IL-side scope_value fix.",
        "predicate_sketch": "NOT a span-text predicate at all -- these "
        "spans ARE already captured (scope='siman'/'chelek' capture "
        "shipped; they fall inside CLUSTER_PRODUCTION_CAPTURED today). "
        "The residual is about USES_DEFINITION containment (a mention-"
        "linking behavior), which this row shape (one quoted span, one "
        "article) cannot express. Tracked instead by the existing, "
        "frozen, still-RED "
        "test_definition_links_il_siman_chelek_containment_live.py -- "
        "named here for the cluster TABLE's completeness, not "
        "double-counted as an unassigned span.",
        "bucket": "director-named residual",
    },
    {
        "id": "akraza_zot_heading_embedded",
        "seed_residual": "parent contract residual (5): 'אכרזה זאת', 1 "
        "file, definitional, unreachable by any rule today.",
        "predicate_sketch": "OUTSIDE this denominator's own population by "
        "construction -- the quoted span lives entirely inside the "
        "article's HEADING line, and this script's C1 methodology (see "
        "c1_denominator.py's own docstring, 'Heading vs body') scans "
        "BODY text only because that is what pipeline.py actually "
        "normalizes/extracts from. Flagged as an OPEN QUESTION for the "
        "panel manager: does C1's population need a documented, additive "
        "heading-scan extension to make this residual expressible as a "
        "row at all, or does it stay a permanently-out-of-population "
        "named exception? Not decided by this Planner round.",
        "bucket": "director-named residual",
    },
    {
        "id": "unquoted_definitional_constructions",
        "seed_residual": "contract amendment 1 (C1's bounded scout item): "
        "whether Hebrew ever defines a term WITHOUT a quote delimiter. "
        "MEASURED, NOT near-zero -- this cluster is OPENED, per the "
        "contract's own branching instruction. See "
        "c1_complement_scout.py + the sprint log for the full method.",
        "predicate_sketch": "N/A -- definitionally OUTSIDE the quoted-span "
        "population (every row in c1_span_population.jsonl has "
        "quote-delimited term_text by construction). Two measured "
        "sub-populations, both scanned corpus-wide from the scout's own "
        "hit lists (`c1_complement_scout_hits.jsonl`), not sampled: "
        "(A) parenthetical `(TRIGGER - X)` unquoted apposition, hand-"
        "verified sample of 37/120: 33/37 (89%) ALREADY captured by "
        "`extract_adhoc_definitions` (`להלן` only) / "
        "`il_adhoc_scope_triggers.py` (5 more trigger words) -- these "
        "rules never required quotes, they strip them if present. Small "
        "residual (4/37 sampled) unexplained this round. "
        "(B) `:-`/`::-` list-entry lines with an unquoted `word(s) - "
        "definition` header, same grammar the quoted list-shape rules use "
        "minus the quotes: 22 REAL natural-language definitions measured "
        "corpus-wide (out of 331 total quote-less entry-marker lines; 177 "
        "of the other 309 are mathematical/formula notation, a distinct "
        "shape, not counted here), across 4 files -- 13 in `חוק זכיון ים "
        "המלח` art.1 (heading `הגדרות`, is_definitions_heading=True), 5 "
        "in `תקנות התעבורה` art.386 (license-type definitions), 2 in "
        "`פקודת הפרשנות`, 2 in `תקנות מס הכנסה (כללים לאישור ולניהול קופות "
        "גמל)`. VERIFIED 100% uncaptured for the largest case (`חוק זכיון "
        "ים המלח`: real `extract_definitions_from_section` call on its "
        "real, normalized body returns 0 candidates for all 13 terms, "
        "e.g. 'שנה - תקופה של 12 חדשים רצופים', 'טונה - טונה מטרית של "
        "1000 קילוגרם') -- `extract._QUOTE_RE`-based term parsing cannot "
        "see an unquoted header at all. Connects to, and likely partially "
        "explains, the parent contract's residual (6) -- `פקודת הפרשנות` "
        "recurs in BOTH this scout's hit list and M29's own "
        "never-reached-lines finding.",
        "bucket": "(A) mostly captured, small residual; (B) director-"
        "named residual -- a genuine, measured, NEW buildable class "
        "(sub-population B was not previously named anywhere in the "
        "parent sprint's log) for a future C4 cycle: a fallback header "
        "parse when `_parse_terms_and_qualifier` finds zero quoted spans "
        "but the pre-dash header is a short Hebrew word run.",
    },
)
