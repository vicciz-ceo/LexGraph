# Recon review — 2026-07-29-definition-links

Sources read in full:
- `poc-dossier.md` — AI-for-others → LexGraph transfer analysis
- `repo-dossier.md` — LexGraph repo state
- `def-dossier.md` — deterministic definition-linking algorithm

Findings below are drawn only from what these three report. Where they conflict, the conflict is called out explicitly rather than silently resolved.

## What the POC (AI-for-others) built

### 1. israeli-laws-wiki
Path: `/Users/nerya/AI for others/israeli-laws-wiki`

- A version-controlled scrape of Hebrew Wikisource's "ספר החוקים הפתוח" (Open Book of Laws).
- 6,133 `.wiki` files under `data/laws/`, each with a sibling `.meta.json` (pageid, revid, sha1, kind, url).
- Scraper is stdlib-only Python, incremental via `state/manifest.json`, one git commit per scrape run.
- Markup uses `@ N. <heading>` to mark each article/section start — a ready-made, cheap section-splitting anchor.
- `[[wikilink|display]]` marks both cross-law references and intra-law section references (`[[סעיף 2]]`, `[[בסעיפים 3]]`).
- Definitions sections are self-identifying: heading literally `הגדרות`, body opens `: בחוק זה -`, one bullet per term.

Sample entry shape (`חוק להגנת רכוש מופקד.wiki`):
```
@ 1. הגדרות
: בחוק זה -
:- "האפוטרופוס הכללי" - כמשמעותו [[חוק האפוטרופוס הכללי|...]];
```
This corpus (6,133 real files) is the raw material the current sprint's definitions-parsing must work against.

### 2. israeli-boi-directives
Path: `/Users/nerya/AI for others/israeli-boi-directives`

- 251 Bank of Israel banking-supervision instruments (140 in-force directives, 13 cancelled, 98 amending circulars) as PDF-extracted `.txt` + `.meta.json`.
- Index manifests are hand-verified ground truth for linkage — every circular that names a directive is cross-checked against that directive's own affected-instruments column.
- Key transferable lesson: index-derived edges (AMENDED_BY/CANCELLED_BY, confidence 0.95) outrank text-mined citations (confidence 0.7–0.9) — prefer structured index data over prose parsing whenever both exist.
- The scraper exits non-zero if any PDF yields no text — an integrity guard worth keeping as a convention for any future PDF ingestion.
- PDF extraction is also the origin of the "scrambled RTL word order" edge case used later in the def-dossier's risk analysis.

### 3. lexgraph-assertions-db (most load-bearing subproject)
- Imports LexGraph's own `backend/app/models` directly: `sys.path.insert(0, "/Users/nerya/LexGraph/backend")`, `from app.models import Assertion, AssertionEvidence, ..., SourceSpan, User`.
- Builds a real, schema-compatible SQLite DB (`lexgraph_assertions.sqlite`, ~76 MB) — confirmed to match the live 13-table schema in this checkout.
- Totals: 42,301 assertions / 46,336 evidence rows across 4 matters. Per-type: AMENDED_BY 22,750, CANCELLED_BY 13, ENACTED_UNDER 4,555, REFERENCES 14,983.
- REFERENCES (conf 0.95): every `[[wikilink]]` outside the `<מקור>` block, resolved to another law's `Document` by exact-title match (13,639 deduped pairs).
- AMENDED_BY (0.9 primary / 0.7 fallback): parsed from `<מקור>` block citation triples; 21,420 left unresolved rather than fabricated.
- ENACTED_UNDER (0.9/0.5): first instrument named after the phrase `בתוקף סמכות` only — an earlier version that kept scanning further mis-attributed a directive's enabling law; documented as a postmortem caution against "keep scanning for any match" heuristics.
- BOI→law cross-corpus linking: 497 edges spanning 68 laws, via longest-title-match (prose) and directive-number regex (directive-to-directive).
- Every assertion: `origin=system_generated`, `status=proposed`, `jurisdiction=IL`, authored by a seeded system user — explicitly framed as proposals for human review, never auto-accepted.
- Verification step confirms every Phase B edge's resolved target is actually named in its own evidence quote (0 unsupported edges across 1,481 checked).
- Shared `normalize_title()` helper (strip `[נוסח חדש]` markers, trailing year suffixes, normalize Hebrew typographic quotes, collapse whitespace) used identically across phases.
- **Confirmed gap, most relevant to this sprint**: no article/section-level modeling anywhere. `subject_entity_type`/`object_entity_type` are always `"document"` — whole law to whole law/directive, never article to article. The `@ N.` markers and `הגדרות` bullets are visible in the raw `.wiki` data but are never parsed into article or definition records by this POC.
- `CANCELLED_BY` is a new assertion type outside LexGraph's existing controlled vocabulary — the POC's own README flags it would need `assertion_type_is_proposed_new` if submitted through the real API. Direct signal that the assertion-type vocabulary already has (or needs) an extension path.

### 4. AI-for-Lawyers
- Public workshop/training site (`lawyers.nerya.io`), not a data pipeline.
- Only generic, low-value transfer idea: the `docs/sprint/current-sprint.json` + `docs/sprint/sprints/<date>-<slug>.md` sprint-tracking convention (which this very review file follows) and a pattern of small `tests/check-*.mjs` scripts per concern.
- No law text, no schema, no relevance to the entity model.

### 5. carpenter-il / electrician-il
- Confirmed unrelated: Israeli trade-business Claude Code plugins (quoting, invoicing via Green Invoice API, price catalogs).
- No legal text, no database schema resembling LexGraph's.
- Only a loose, stretch-level idea: `corrections.json`'s "human corrections feed back into future estimates" pattern is conceptually similar to LexGraph's `status=proposed` → human-review → revision workflow, but not a real data/schema transfer.

## Current LexGraph state

**Entity model** (`backend/app/models/`, 13 tables, SQLAlchemy 2 + Pydantic v2). Repo-dossier notes schema is **frozen post-F1; changes require escalation**.

- `Organization → Repository → Matter` — organizational hierarchy.
- `Document` (`id`, `repository_id`, `matter_id`, `title`) — **title only, no body text, no sub-document structure.**
- `SourceSpan` (`id`, `document_id`, `matter_id`, `quote_text`) — the only place article/quoted text actually lives today; a flat quote, not an addressable article/section unit.
- `Assertion` — subject/object modeled as `entity_type` + `entity_id` pairs, plus `assertion_type`, `proposition`/`proposition_raw`, `origin`, `status`, `confidence`, `jurisdiction`, effective dates, revision pointer.
- `AssertionRevision`, `AssertionEvidence` (evidence roles: supports/contradicts/contextualizes/qualifies/primary_basis/secondary_basis), `AssertionRating`, `AssertionComment`, `AuditEvent`.

**Where definition-linking plugs in:**
- Repo-dossier proposes a new deterministic service module, `app.services.definition_linker` or `article_linker.py`.
- Analogous existing pattern: `app.enrich` / `HeuristicEnricher`, invoked via `python -m app.cli enrich --matter-id={matter_id}`.
- That enricher is pluggable, fully offline, and returns draft assertions with evidence pre-linked to real `SourceSpan` rows; re-running is idempotent (checked via the duplicates service).

**Gaps vs. the POC and vs. what the def-dossier's algorithm needs:**

- **No article/section entity exists.** Neither `Document` nor `SourceSpan` has an addressable article/section unit, but the def-dossier's core edge type is `{law_id, article_id, term, definition_id, matched_surface_form, char_offset}` — `article_id` has no home in the current schema.
- **`app/enrich/suggester.py` (`HeuristicEnricher`) is English-only.** It matches contract phrases (`survives termination`, `conflicts with`, `modifies|amends`, `applies to`) against `SourceSpan.quote_text` for contract-assertion typing. Def-dossier confirms via grep (`הגדר|definition|defined_term|glossary` — zero matches anywhere in `backend/`) that **there is no existing Hebrew/statute/definitions extraction logic to inherit or fix; this is greenfield.**
- The only reusable pattern from the existing enricher is its *shape*: pure deterministic functions returning candidates with evidence pointers, kept separate from any DB/pipeline concerns.
- **No ingestion pipeline** moves the `.wiki` corpus into LexGraph's `Document`/`SourceSpan` tables today — current test fixtures use placeholder text ("Sample quoted text.", "Test Document"). `lexgraph-assertions-db/build_assertions_db.py` already proves the corpus loads against this exact schema, but it only creates whole-document assertions, never articles.
- **Assertion-type vocabulary is controlled** (`ALLOWED_ASSERTION_TYPES`, per repo-dossier). The POC already had to flag `CANCELLED_BY` as needing `assertion_type_is_proposed_new`; the same extension point will likely be needed for whatever type(s) definition-linking introduces.

## Refinements the POC implies for LexGraph

1. **Introduce an article/section sub-document entity (or a structured `SourceSpan` extension) addressable by ID.**
   Rationale: neither `Document` nor `SourceSpan` has an addressable article/section unit today, but the def-dossier's core edge type requires `article_id`.
   Affected area: `backend/app/models/` — new model or `SourceSpan` extension; schema frozen post-F1, needs explicit escalation.

2. **Add a `Definition` record type (term, definition_text, scope, source article/law) distinct from a bare Assertion proposition string.**
   Rationale: repo-dossier's own model candidates already list this as an option; the def-dossier's scope rules (law-wide / chapter-scoped / section-local, nested sub-definitions) don't fit a flat `proposition` string cleanly.
   Affected area: new model + migration, `app/models/__init__.py`.

3. **Extend the assertion-type vocabulary — candidates `DEFINES`, `USES_DEFINITION` (or `article_uses_term`), `DERIVES_FROM_LAW`.**
   Rationale: mirrors the exact extension gap the POC already hit with `CANCELLED_BY` (`assertion_type_is_proposed_new`); keeps definition-linking output representable as Assertions if a separate Definition table isn't adopted.
   Affected area: `app/models/assertion.py` vocabulary, `app/services/`.

4. **Build `app/services/definition_linker.py` as pure deterministic functions, no DB/pipeline coupling, mirroring `HeuristicEnricher`'s shape.**
   Rationale: def-dossier explicitly calls this out as the one reusable POC pattern; keeps the extractor unit-testable directly against raw `.wiki` text.
   Affected area: new service module, `backend/tests/unit/`.

5. **Reuse `build_assertions_db.py`'s `WIKILINK_RE`, `normalize_title()`, and "drop rather than guess" resolution discipline** for both intra-law section links and cross-law derivation resolution.
   Rationale: already proven end-to-end against 6,133 real law files; keeps new behavior consistent with the existing REFERENCES/AMENDED_BY extraction logic.
   Affected area: new definition_linker; possibly a shared `app/services/legal_text_normalization.py`.

6. **Ingest the `israeli-laws-wiki` corpus (or a representative slice) as real test fixtures**, replacing/augmenting placeholder text.
   Rationale: the def-dossier's edge cases (15 scattered `הגדרות` sections in `חוק העונשין`, nested sub-definitions in `חוק הגנת הפרטיות`, unquoted `(להלן - X)` in `חוק הבנקאות (שירות ללקוח)`) are only reproducible against the real corpus.
   Affected area: `backend/tests/integration/`, possibly a fixtures directory seeded via `lexgraph-assertions-db`'s loader.

7. **Adopt confidence/provenance tiering consistent with the POC**: index/structural derivation higher confidence than regex/prose-derived; always `origin=system_generated`, `status=proposed`, never auto-accepted.
   Rationale: matches the existing REFERENCES (0.95) vs AMENDED_BY-fallback (0.7) split and the project's existing review-workflow philosophy.
   Affected area: `definition_linker` output contract; conforms to existing `app/services/permissions.py`/review workflow without needing changes there.

8. **Add a degraded-text guard for non-wikisource sources** (PDF-extracted BOI directives showed scrambled RTL word order): flag-and-route to manual review rather than attempting auto-correction.
   Rationale: def-dossier identifies this as the single biggest determinism risk in the whole design; directly reusable if BOI directive text is ever run through the definitions extractor.
   Affected area: `definition_linker` input validation, analogous to the POC scraper's "exit non-zero on empty PDF text" convention.

9. **Expose the feature via a CLI command and/or route analogous to `enrich`** — `python -m app.cli link-definitions --matter-id={matter_id}`, or `/api/v1/matters/{matter_id}/definitions`.
   Rationale: repo-dossier already proposes this integration point; keeps parity with the existing enrichment CLI UX.
   Affected area: `app/cli.py`, `app/routers/`.

## Deterministic definition-linking design

Algorithm from `def-dossier.md`, compressed into implementable stages. Grounded in `israeli-laws-wiki/data/laws/*.wiki` (primary) and `israeli-boi-directives/data/directives/*.txt` (PDF edge case only). Def-dossier confirms `backend/app/enrich/{suggester,pipeline,base}.py` contributes nothing to this — no Hebrew/definitions logic exists to inherit.

### Stage 0 — text normalization
Runs on a parsing-side copy only; the original text stays untouched for citation/quoting.
1. Unicode NFC normalization.
2. Strip Hebrew niqqud (U+0591–U+05C7) defensively.
3. Collapse dash variants — en dash (U+2013), em dash (U+2014), Hebrew maqaf (U+05BE) — to canonical `-`.
4. Collapse quote variants — straight `"`, curly `“`/`”`, gershayim (U+05F4) — to one quote class. The single geresh `׳` is **never** a term-quote (it's the abbreviation mark, e.g. `תשמ"א`).
5. Record `[[...]]` spans as "already-linked" hints, then strip the brackets to get plain text for regex passes — these brackets are a scrape artifact; a general solution must not depend on them.

### Stage 1 — locate definitions sections (scope, not yet terms)
1. Match `@ N. <heading>` lines against observed heading forms: `הגדרות`, `הגדרת מונחים`, `הגדרה` (singular, seen once), `הגדרות ופירוש`.
2. **Do not assume section 1.** `חוק העונשין` alone has 15 separate `הגדרות` sections scattered through the law (§§34כד, 51א, 91, 144א, 175, 184, 224, 236, 268, 312, 368א, 413א, 414, 461, 470, 485), each scoped to its own chapter (`לענין פרק זה` / `לענין סימן זה` / `לענין עבירה`).
3. A section's scope runs from its `@ N.` line to the next `@ N.` line at the same or shallower level, or to a `==` chapter break — whichever comes first.

### Stage 2 — extract (term, definition) pairs
Primary pattern: `:-?"term"(, "term2")*( ו"lastterm")?(qualifier)? - definition;` (entries may span multiple physical lines).
- **Multi-term single definition**: one dash, N terms → emit one definition node with N `defines` edges.
- **Qualifier-before-dash**: e.g. `"ניפוק", של דבר -` — the qualifier clause is captured but excluded from the term string itself.
- **List-form definitions**: an indented `:: (1) ... (2) ...` block with no closing `;` until the final item — treat the whole block through the next `:-` line as the definition body.
- **Nested sub-definitions**: `לעניין הגדרה זו, "X" - ...` appearing inside another definition's body (`חוק הגנת הפרטיות §3`). Recurse Stage 2 on the outer definition's body; the inner term is scoped only to the outer term's own occurrences, not law-wide.
- **Ad-hoc unquoted inline definitions**: `(להלן - X)` / `(להלן: "X")` outside any הגדרות section, defined by apposition. Higher false-positive risk — require the captured span ≤4 tokens, prefer the quoted variant when present.
- **Local scoped definitions inside ordinary articles**: triggered by `לענין זה,` / `בסעיף זה,` immediately before a quoted-term-dash-definition (`חוק העונשין §35(ב)`, `§35(ג)`). Stage 2 must run over **every** article body, not only detected הגדרות scopes; resulting scope is tagged `local` vs `chapter` vs `law-wide`.
- Entries end at `;`; a trailing `.` ends the section's last entry.

### Stage 3 — build the article→definition link index
For each defined term T with scope S (law-wide / chapter-scoped / section-local):
1. Build an inflection-tolerant matcher for T's first token: Hebrew prefix letters `ובלכמשה`, 1–2 stacked, before the root.
2. Handle construct-state insertion of the definite article before the *second* word of a multi-word term: `"מאגר מידע"` (as defined) appears in running text as `מאגר המידע` — build the regex to allow an optional `ה` immediately before the last word.
3. Handle construct-plural of the first word (`מאגר` → `מאגרי`) — not derivable from a general suffix rule, so build a **small closed inflection table per term** at extraction time: {as defined, ה-inserted before final word, construct-plural of first word if it ends in a regular-plural-taking ending} × definite-article variants — a deterministic, explainable closed-list alternation instead of open-ended morphology.
4. Use a manual boundary check instead of `\b` (unreliable across Hebrew bidi/punctuation): character before must be start-of-string/whitespace/`(`/`"`/maqaf; character after must be whitespace/`,`/`.`/`;`/`)`/`"`/end-of-string.
5. Run each term's regex over every article body **within its scope** (whole law / chapter / section as applicable). Each match becomes an `article_uses_term` edge: `{law_id, article_id, term, definition_id, matched_surface_form, char_offset}`.
6. **Longest-match-wins**: sort term regexes by token-length descending; once a span is claimed by a longer term, shorter terms may not claim overlapping offsets. Never define a matcher for a bare substring unless that substring is itself an independently defined term.
7. Exclude matches inside the term's own definition entry and its own `@ N.` heading line — that's the definition, not a use.
8. Exclude matches inside a *different* term's definition body unless the nested-definition case (Stage 2) already scopes it there explicitly.

### Stage 4 — detect cross-law derivation and link the two laws
Trigger-phrase inventory, corpus-wide counts from a `grep -o` sweep of `israeli-laws-wiki/data/laws/*.wiki`:

| phrase | raw count | meaning / binding |
|---|---|---|
| `כהגדרתו` | 7,468 | "as defined therein" — masc. singular |
| `כהגדרתה` | 3,131 | fem. singular |
| `כהגדרתם` | 2,696 | masc. plural |
| `כהגדרתן` | 552 | fem. plural |
| `כהגדרת` | 13,955 | construct form, always followed by an explicit term name — no pronoun-gender resolution needed |
| `כמשמעותו` | 5,752 | "as meant therein" — semantically identical to כהגדרתו |
| `כמשמעותה` | 2,696 | fem. singular |
| `כמשמעותם` | 1,740 | masc. plural |
| `כמשמעותן` | 385 | fem. plural |
| `כמשמעות` | 10,645 | construct form |
| `לפי חוק` | 7,503 | weaker/generic reference, **not** necessarily a defined-term derivation — must be filtered |
| `כאמור בחוק` | 51 | rare, "as stated in [law]" — treat like `לפי חוק` |

Binding rule — a `כהגדרת*`/`כמשמעות*` trigger is a cross-law derivation only when immediately followed by:
- `ב` + law name (optionally ending in a year pattern, e.g. `בחוק המחשבים, התשנ"ה-1995`; year optional on repeat mentions), or
- `בפקודת <name>` (Mandatory-era "פקודה" handled the same as `בחוק`), or
- the anaphoric forms `בחוק האמור` / `אותו חוק` / `החוק האמור`, resolved to the most recently named law in the preceding text of the same sentence, falling back to the same paragraph.

If instead followed by `בסעיף <N>`, that's a same-law internal reference — route to Stage 3, not Stage 4.

Law-name extraction regex once triggered: `(?:חוק|פקודת|פקודה)\s+[^,;()]+(?:,\s*תש[א-ת]"[א-ת]-\d{4})?` — year stripped for the identity key (amendments keep the same short name).

Emit a `law_derives_definition` edge: `{source_law_id, source_term, target_law_id, trigger_phrase, matched_text}`. If the target law can't be resolved, still emit the edge with `target_law_id: null` and the raw matched string preserved — a deliberate exception to the "drop rather than guess" rule, since the string is preserved for later resolution, not fabricated as a conclusion.

`לפי חוק` (7,503 occurrences) is classified as a **substantive cross-reference**, not a definition derivation, unless it appears inside a definitions-section entry directly after a quoted term with no other dash-definition text — i.e. the whole definition body IS `לפי חוק X`. Otherwise it's a separate `article_cites_law` edge type.

### Stage 5 — false-positive guards
1. A quoted span not followed by `-`/`–` within ~3 tokens is a plain quotation (law-title quote, direct speech), not a definition.
2. Reject candidate terms shorter than 2 characters or consisting only of digits/Hebrew numeral letters (avoids matching quoted sub-item labels like `"א"`).
3. Reject a `כהגדרתו`/`כמשמעותו`-class match if immediately followed by `בסעיף` — that's Stage 3 territory, not Stage 4.
4. When a short law name is ambiguous (e.g. `חוק הבנקאות` alone matches both `חוק הבנקאות (רישוי)` and `חוק הבנקאות (שירות ללקוח)` in the corpus), require exact match against the full title list before any fuzzy fallback — never silently pick one.
5. For PDF-sourced text (as in `israeli-boi-directives/data/directives/*.txt`): require a bidi-sanity check before running any of the above; if reversed-word-order artifacts are detected, flag the whole file "extraction-quality: degraded" and route to manual review — do not attempt deterministic auto-correction, since the corruption pattern is PDF-tool-dependent.

### Worked example
`חוק הגנת הפרטיות.wiki` line 51:
```
:- "חומר מחשב", "מחשב" ו"פלט" - כהגדרתם [[בחוק המחשבים]];
```
→ 3 terms (`חומר מחשב`, `מחשב`, `פלט`), each gets a `defines` node sharing one derivation-clause body; one `law_derives_definition` edge per term to `חוק המחשבים`, trigger `כהגדרתם`.

### Edge cases enumerated in the dossier
- Nested scoped sub-definition — `חוק הגנת הפרטיות.wiki` line 62 (`מידע אישי` → inner term `אדם הניתן לזיהוי`, scoped only to the outer term).
- Chapter-scoped, non-§1 definitions section — `חוק העונשין.wiki` §34כד, lead line `לענין עבירה -`; terms there must not leak into a global law-wide scope.
- Construct-state/plural inflection — `"מאגר מידע"` appears as 8 distinct observed surface forms in running text (`מאגר המידע`, `במאגר המידע`, `מאגרי מידע`, `במאגרי מידע`, `מאגרי המידע`, `שבמאגר המידע`, `למאגרי מידע`/`למאגר המידע`, `ממאגר המידע`) — none a literal substring of the defined string, hence the closed candidate-set approach in Stage 3.
- Unquoted inline `(להלן - X)` outside any הגדרות section — `חוק הבנקאות (שירות ללקוח).wiki` line 79 (term `הטעיה`); same file line 291 also demonstrates curly-quote (U+201D) and en-dash (U+2013) normalization needs.
- PDF/OCR degraded-text risk from BOI directives — flagged in the def-dossier as the single biggest determinism risk in the whole design, and explicitly not auto-correctable.

## Open questions for the Planner/director

1. Schema is frozen post-F1 per repo-dossier ("changes require escalation") — does representing article-level entities and/or a `Definition` table count as the kind of change needing explicit sign-off before this sprint proceeds, or is there an already-approved extension path?
2. Model choice is open across all three dossiers: dedicated `Definition`/`DefinitionLink` tables vs. new `assertion_type` values (`DEFINES`, `USES_DEFINITION`, `DERIVES_FROM_LAW`) on the existing `Assertion`/`SourceSpan` shape. Repo-dossier lists both as candidates without deciding; def-dossier's edge shapes (`article_uses_term`, `law_derives_definition`) don't map cleanly to either without a decision.
3. Should the `israeli-laws-wiki` corpus (or a slice of it) be vendored into LexGraph as real test fixtures, given the current suite only has placeholder text and the def-dossier's edge cases are only reproducible against real files like `חוק העונשין.wiki` and `חוק הגנת הפרטיות.wiki`?
4. Is `lexgraph-assertions-db/build_assertions_db.py` reusable in-place as the ingestion path for loading `.wiki` files into `Document`/`SourceSpan`, or does article-level granularity require a new loader — the POC's loader only ever creates whole-document rows?
5. Def-dossier proposes emitting unresolved cross-law derivation edges with `target_law_id: null` rather than dropping them — this diverges from the POC's otherwise-consistent "drop rather than guess" rule. Should this exception be adopted as-is, or should unresolved derivations be dropped like everything else for consistency?
6. No dossier specifies who/what triggers `definition_linker` runs in production — CLI only (like `enrich`), a new API route, or both? Repo-dossier lists both as options without deciding.
