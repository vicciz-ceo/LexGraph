"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, Job 3.

The cluster model: every predicate here is a COMMITTED, EXECUTABLE
function (never a prose sentence -- contract's own binding requirement),
operating on rows produced by `c1_denominator.py` /
`c1_heading_denominator.py`.

## Two populations, two cluster levels -- RULED (M33-1, panel manager,
## CONFIRMED as this Planner originally resolved it)

Round 1 found the contract's own text uses "candidate row" at TWO
different granularities without reconciling them: cluster 1's predicate
and its own disposal count ("~91,605 characters... 33.1%") are stated at
the CHARACTER level, while C2 says "the full ~92,600-row population" --
the SPAN count. Ruling M33-1 confirmed the resolution Round 1 proposed:

- **Level 0 (character level, cluster 1 only).** Every raw quote
  character in the corpus is either word-internal (this cluster) or
  eligible. Total and disjoint BY CONSTRUCTION -- there is no other
  Level-0 cluster, and none is needed. Level 0 is how the Level-1 span
  population gets CONSTRUCTED (word-internal characters are excluded
  before pairing), not itself a partition of it.
- **Level 1 (span level, clusters 2+).** The paired candidate spans --
  built from Level-0-eligible characters only -- are what C2's backbone
  test(s) actually iterate, matching the contract's "~92,600-row
  population" wording literally. Genuinely INCOMPLETE by design (Job 3:
  "propose the initial cluster set... do not attempt all 20-40").

## Level 1 has TWO populations as of Round 2 (ruling M33-3) -- BODY
## (primary) and HEADING (additive, separately measured)

Ruling M33-3: excluding heading-embedded quoted spans from any
population at all, because "the dispatch path differs," would repeat
the exact signal-dependence this contract outlaws for `הגדרות`-headed
articles. BODY stays primary (it is what production actually parses --
`c1_denominator.py`, 93,509 rows); HEADING is additive and separately
measured (`c1_heading_denominator.py`, 353 rows) because folding them
together would silently move the already-reproduced ~92,600 headline.
`SPAN_CLUSTERS` below classifies BODY rows; `HEADING_CLUSTERS` (further
down) classifies HEADING rows -- two distinct manifests, two distinct
cluster registries, never mixed in one `assign_*` call.

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


def _is_standalone_vav_conjunction(prev_char: str, char_before_prev: str) -> bool:
    """`prev_char` is a bare, one-letter vav conjunction ("ו", "and") in
    its own right -- itself preceded by whitespace or start-of-text, not
    a letter INSIDE a longer word. Private helper for `is_word_internal_
    quote`'s M33 refinement below; not itself a cluster predicate."""
    return prev_char == "ו" and (char_before_prev == "" or char_before_prev.isspace())


def is_word_internal_quote(prev_char: str, next_char: str, char_before_prev: str = "") -> bool:
    """Cluster 1's predicate -- REFINED per ruling M33-2 (panel manager,
    2026-08-05, `2026-08-05-defs-il-certification-log.md`). Original
    (pre-M33) form, exactly as the signed-off contract first stated it: a
    quote character immediately preceded AND followed by a Hebrew letter
    (U+05D0-U+05EA), with no intervening whitespace, is word-internal.

    **M33 correction, now APPLIED (Round 1 reported it as a candidate,
    not applied -- Round 2 applies it, per the panel manager's explicit
    ruling that a stated-falsifiable predicate that is measurably false
    is worse than no template at all).** The original form has a MEASURED
    2.3% false-positive rate (2,096/91,611 disposals, 1,004 files -- this
    Planner's own Round-1 finding, independently re-verified by the panel
    manager against `"רכב" ו"דרך"` before ruling, not accepted on report):
    when `prev_char` is a bare, standalone vav conjunction ("ו", itself
    preceded by whitespace or start-of-text -- `char_before_prev`), the
    quote is the OPENING delimiter of a SECOND term in a `"t1" ו"t2"`
    list (e.g. "רכב" AND "דרך", two distinct real terms), never an
    abbreviation, and must NOT be classified word-internal even though
    both immediate neighbors are Hebrew letters. Independent confirmation
    this correction is right, not merely different: applying it drops the
    unrelated `unpaired_trailing_quotes` diagnostic in `c1_denominator.py`
    from 1,676 articles to 282 (-83%).

    `char_before_prev` defaults to `""` (treated as start-of-text, i.e. a
    lone `prev_char='ו'` with no further context is assumed standalone)
    for callers that cannot supply three characters -- every call site in
    this package supplies it explicitly. See `backend/tests/unit/
    test_certification_clusters_word_internal_quote.py` for the committed
    unit test pinning the `ו"` conjunction case this refinement exists
    for (M33's own explicit instruction: the refinement must carry its
    own committed unit test, not rely on the corpus-scale manifest to
    exercise it)."""
    if not (is_hebrew_letter(prev_char) and is_hebrew_letter(next_char)):
        return False
    if _is_standalone_vav_conjunction(prev_char, char_before_prev):
        return False
    return True


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
    # HISTORICAL -- no longer a proposed cluster. Round 1 found and
    # reported (not applied) a 2.3% false-positive rate in cluster 1's
    # own predicate (the standalone-vav second-term-opener shape, e.g.
    # `"רכב" ו"דרך"`). Ruling M33-2 (panel manager) directed this be
    # APPLIED, not left as a proposal: `is_word_internal_quote` (this
    # module, above) now folds the correction in directly, with its own
    # committed unit test (`backend/tests/unit/
    # test_certification_clusters_word_internal_quote.py`). Left as a
    # comment, not a dict entry, so the shape of this tuple stays "things
    # not yet decided", not "a running commentary on past decisions".
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
        "predicate_sketch": "ROUND 2 CORRECTION (this Planner, verified "
        "against the real file, not assumed): ruling M33-3 named the new "
        "heading population as 'the honest home' for this residual -- "
        "that is not quite right, and worth stating precisely rather "
        "than silently absorbed. The real marker line is `@ (תיקון: "
        "תשפ\"ג) : באכרזה זאת, \"...\" - ...` -- NO number between `@` "
        "and `(תיקון`, so it matches NEITHER `sections._ARTICLE_MARKER_"
        "RE` NOR `_BARE_ARTICLE_MARKER_RE`. `sections.parse_articles` on "
        "the real file returns ZERO Article objects (confirmed live) -- "
        "there is no `.heading` string to scan at all, so this residual "
        "is unreachable by BOTH the body population AND the new heading "
        "population. The true, more fundamental gap (see "
        "`c1_heading_denominator.py`'s own 'numberless @ marker "
        "diagnostic'): 121 whole files (2.0% of the corpus) produce ZERO "
        "articles because of this exact `@`-marker shape, a `sections.py` "
        "(frozen) gap -- not a rule-module-only fix, and not this "
        "population's own boundary question after all.",
        "bucket": "director-named residual -- but escalate the ROOT "
        "CAUSE (the 121-file zero-article gap) rather than treat this as "
        "a heading-population classification question; see "
        "`c1_heading_denominator.py`.",
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
    {
        "id": "numberless_at_marker_zero_article_files",
        "seed_residual": "NOT inherited -- found this round (Round 2), by "
        "this Planner, while investigating why the אכרזה זאת residual "
        "does not appear in the new heading population (ruling M33-3).",
        "predicate_sketch": "A file-level (not row-level) finding: "
        "`sections.parse_articles` returns ZERO Article objects for 121 "
        "files (2.0% of the corpus) because their own `@`-prefixed "
        "marker line matches NEITHER `_ARTICLE_MARKER_RE` (no number) "
        "NOR `_BARE_ARTICLE_MARKER_RE` (has trailing content) -- e.g. "
        "`@ (תיקון: תשפ\"ג) : באכרזה זאת, ...`. 21,498 such lines / 1,646 "
        "files corpus-wide (most of those files also have OTHER, valid "
        "numbered markers elsewhere -- only 121 end up fully article-"
        "less). See `c1_heading_denominator.py`'s own "
        "`numberless_at_marker_diagnostic`.",
        "bucket": "director-named residual -- a `sections.py` (frozen) "
        "gap, not rule-module-only work; closer in shape to M20's סימן/"
        "חלק breadcrumb blocker than to anything a family panel can fix "
        "without a scoped frozen-file escalation.",
    },
)

# --- Level 1b -- heading-population clusters (M33-3) -------------------

CLUSTER_HEADING_QUOTED_SPAN_UNREACHED = "heading_quoted_span_unreached"


def cluster_heading_quoted_span_unreached(row: dict) -> bool:
    """Every row in `c1_heading_span_population.jsonl` matches this
    cluster, and ONLY this cluster -- verified by exhaustive grep
    (`c1_heading_denominator.py`'s own docstring), not assumed: no rule
    anywhere in `backend/app/definition_links` reads `Article.heading`
    TEXT content today (only its own boolean match against `is_
    definitions_heading`'s known patterns). This is not a coarse
    catch-all standing in for undifferentiated work -- it is an
    accurate description of a single, uniform, verified fact: every
    heading-embedded quoted span is EQUALLY unreached, because the
    concept of reading heading text for extraction does not exist yet
    anywhere in the codebase, so there is nothing to differentiate
    between rows on."""
    return row.get("production_captured") is False


HEADING_CLUSTERS: tuple[tuple[str, "callable", str, str], ...] = (
    (
        CLUSTER_HEADING_QUOTED_SPAN_UNREACHED,
        cluster_heading_quoted_span_unreached,
        "director-named residual",
        "Every heading-embedded quoted span, corpus-wide (353 rows, 55,348 "
        "articles have at least one quote-bearing heading -- most word-"
        "internal abbreviation noise, 353 real candidate spans after "
        "pairing). Zero rules read heading text; zero are captured.",
    ),
)


def assign_heading_clusters(row: dict) -> list[str]:
    """Analogous to `assign_span_clusters`, for the SEPARATE heading
    population (`c1_heading_span_population.jsonl`) -- never mix rows
    from the two manifests through the wrong `assign_*` function; their
    schemas differ (`heading_text` vs none, no `is_definitions_heading_
    article`/`preceded_by_html_attribute` columns)."""
    return [cluster_id for cluster_id, predicate, _, _ in HEADING_CLUSTERS if predicate(row)]
