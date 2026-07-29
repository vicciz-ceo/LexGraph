# POC Corpus Verification Run — sprint 2026-07-29-definition-links

Read-only verification of `app.definition_links` (ingest + `run_definition_linking`)
against the real POC corpus: 6,133 Hebrew law `.wiki` files in
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/`. Nothing in any repo
worktree, the main checkout, or the POC directory was modified. All artifacts
(scratch sqlite DBs, logs, this report) live under
`pocrun/` in the session scratchpad. Code under test: worktree
`sprint/2026-07-29-definition-links`, HEAD `3faeae0` at run start.

## 0. Method notes / caveats (read this before the numbers)

- **Two DBs**: `pilot.sqlite` (104-law deterministic sample, Stage 1) and
  `full.sqlite` (all 6,133 laws, one matter, Stage 2+). A read-only snapshot
  `full_snapshot.sqlite` (copied immediately after run1 committed) was used for
  all SQL analysis and the diagnostic timing profile below, so those reads
  never contended with the determinism-check writer process.
- **Concurrency caveat on wall-clock times**: the determinism re-run (`run2`)
  and the diagnostic per-document timing profile were launched at
  approximately the same time and ran **concurrently** on the same machine
  (both single-threaded Python processes competing for CPU). `run2`'s
  1625.5s and the timing profile's 1801.6s total are both inflated by this
  contention and are NOT clean solo-run measurements. **`run1`'s 1106.5s is
  the only isolated, uncontended measurement** and is what the runtime
  projection and "slowest laws" ranking below should be read against
  qualitatively (the profile's *relative* ranking of slow laws is still valid
  even though its absolute seconds are inflated ~1.6x by contention).
- The per-law "slowest laws" breakdown is a **separate diagnostic
  re-computation** (`timing_profile.py`), not instrumentation added to
  `run_definition_linking` itself (which is a single opaque call with no
  built-in per-law timing, and per the mission brief app code was never to be
  patched). It replays Stage 2 (definition extraction) + Stage 3
  (article↔definition matching) per document using the *same, unmodified*
  library functions the pipeline calls, reading already-ingested
  Article/SourceSpan rows. It does **not** include Stage 4 (cross-law
  derivation) or ORM write/flush overhead, so its per-law seconds are a
  lower bound on that law's true contribution to the real pipeline call, but
  the sort order (which laws are slow) is meaningful.

## 1. Timing pilot (Stage 1) — 104-law deterministic sample

Sample: every 61st file of the sorted `.wiki` file list (100 files) plus
חוק העונשין, חוק הגנת הפרטיות, חוק הבנקאות (שירות ללקוח), חוק המחשבים (all 4
were not already in the stride sample) → **104 laws**.

| Phase | Result |
|---|---|
| Ingest | 104/104 ok, 0 crashes, 0.39s |
| Link run 1 | 6,225 assertions created, 1,153 definitions created, 3 degraded-skipped articles, 32.87s |
| Link run 2 (rerun, same matter) | **0** new assertions, **0** new definitions, 32.32s |
| Rebuild-from-scratch (fresh DB, same 104 laws) | identical counts on every dimension (documents/articles/definitions/assertions_total/uses_definition/derives_from_law) |

Pilot corpus stats: 3,952 articles, 1,153 definitions, 6,088 USES_DEFINITION,
137 DERIVES_FROM_LAW (7 resolved). Biggest pilot documents by article count:
חוק העונשין (650), חוק הביטוח הלאומי (571), פקודת החברות (550) — none
dominated runtime disproportionately.

**Projection**: pilot sample was byte/article-count skewed toward larger laws
(pilot avg. law = 36.9x corpus-wide byte share vs. 59x file-count share).
Using the article-count ratio (127,903 / 3,952 ≈ 32.4x) against the pilot's
32.87s link time projected ≈ 1,065s (~18 min) for the full corpus — this
matched the actual isolated run1 time (1,106.5s) closely, confirming
near-linear scaling with total article count (no quadratic blowup observed
even though several full-corpus documents, e.g. תקנות התכנון והבניה
(בקשה להיתר) at 1,203 articles, are 2-3x larger than any pilot document).

## 2. Full-corpus run (Stage 2)

**Ingestion** (chunked, 1000 files/call, 7 Bash calls): **6,133/6,133 laws
ingested, 0 crashes, 20.31s total, 127,903 articles created.**

**Linking, run1** (isolated, no concurrent load): **1,106.5s** —
223,669 assertions created, 49,711 definitions created, 277 degraded-skipped
articles.

## 3. Determinism check — PASS

| | run1 (isolated) | run2 (same matter, rerun; ran concurrently with the timing profile) |
|---|---|---|
| elapsed | 1106.5s | 1625.5s (inflated by concurrent CPU contention — see §0) |
| created_assertions | 223,669 | **0** |
| created_definitions | 49,711 | **0** |
| skipped_degraded_article_ids | 277 | 277 (identical) |

Second call created zero new rows and reproduced the identical degraded-skip
count. Combined with the pilot's rebuild-from-scratch match (§1), determinism
holds at both sample and full-corpus scale: **PASS**.

## 4. Crash / degraded census

- **Ingestion crashes: 0 / 6,133** (chunk-by-chunk progress log:
  `full_ingest_progress.json` — ok_count=6133, crash_count=0).
- **Linking crashes: 0** — one successful call each on run1 and run2, no
  exceptions.
- **Degraded (bidi-reversed) articles skipped: 277 / 127,903 (0.22%)** —
  identical on both runs.

## 5. Totals

| Metric | Count |
|---|---|
| Documents (laws) ingested | 6,133 |
| Articles | 127,903 |
| Definitions | 49,711 |
| Assertions, total | 223,669 |
| USES_DEFINITION | 219,176 |
| DERIVES_FROM_LAW, total | 4,493 |
| DERIVES_FROM_LAW, resolved (object_entity_id set) | 2,928 (65.2%) |
| DERIVES_FROM_LAW, unresolved (object_entity_id NULL) | 1,565 (34.8%) |
| Degraded-skipped articles | 277 (0.22% of articles) |
| Crashed files | 0 |

## 6. Distributions

**Top 10 laws by definitions:**

| Law | # definitions |
|---|---|
| פקודת מס הכנסה | 334 |
| תקנות התעבורה | 317 |
| תקנות הטיס (הפעלת כלי טיס וכללי טיסה) | 246 |
| חוק הביטוח הלאומי | 238 |
| חוק התכנון והבניה | 238 |
| חוק התכנון והבניה_תזכיר חוק | 218 |
| תקנות המדידות (מדידות ומיפוי) | 167 |
| תקנות התכנון והבניה (בקשה להיתר, תנאיו ואגרות) | 166 |
| חוק התקשורת (בזק ושידורים) | 150 |
| כללי המים (חישוב עלויות והכנסות...) | 149 |

**Top 10 laws by USES_DEFINITION edges:**

| Law | # edges |
|---|---|
| תקנות התעבורה | 3,275 |
| פקודת מס הכנסה | 3,254 |
| תקנות הטיס (הפעלת כלי טיס וכללי טיסה) | 2,527 |
| חוק החברות | 2,075 |
| חוק התכנון והבניה | 1,946 |
| חוק חדלות פירעון ושיקום כלכלי | 1,945 |
| חוק הגנה על בריאות הציבור (מזון) | 1,854 |
| חוק הביטוח הלאומי | 1,808 |
| חוק התכנון והבניה_תזכיר חוק | 1,700 |
| תקנות הטיס (רשיונות לעובדי טיס) | 1,463 |

**Top unresolved DERIVES_FROM_LAW target strings** (grouped by identical
proposition text — reveals the resolution gap concentrated on laws whose
official title carries a parenthetical qualifier):

| Raw matched proposition | Count |
|---|---|
| "תאגיד בנקאי" כהגדרתו חוק הבנקאות | 23 |
| "מבטח" כהגדרתו חוק הפיקוח על שירותים פיננסיים | 17 |
| "קופת גמל" כהגדרתן חוק הפיקוח על שירותים פיננסיים | 14 |
| "נותן ערבות אחר" כהגדרתם חוק הפיקוח על שירותים פיננסיים | 11 |
| "תאגיד בנקאי" כמשמעותו חוק הבנקאות | 10 |
| "חברה מנהלת" כהגדרתן חוק הפיקוח על שירותים פיננסיים | 10 |
| "נותן ערבות אחר" כהגדרתו חוק הפיקוח על שירותים פיננסיים | 9 |
| "מבטח" כהגדרתו חוק הפיקוח על הביטוח | 9 |
| "חומר מסוכן" כהגדרתו חוק החומרים המסוכנים, התשנ"ג-1993 | 9 |
| "תאגיד בנקאי" כהגדרתם חוק הבנקאות | 8 |

(`"חוק הבנקאות "` and `"חוק הפיקוח על שירותים פיננסיים "` alone account for
~92 of the unresolved edges above — both are laws whose real, ingested title
carries a required parenthetical qualifier the extractor drops; see §8,
Issue 3.)

**Top 10 laws by article count** (size context): תקנות התכנון והבניה
(בקשה להיתר, תנאיו ואגרות) 1,203; תקנות התעבורה 1,023; קובץ החלטות מועצת
מקרקעי ישראל 902; תקנות התעבורה_החלת... 877; חוק השיפוט הצבאי 791; תקנות סדר
הדין האזרחי (אכיפת פסקי-חוץ) 702; תקנות הטיס (הפעלת כלי טיס וכללי טיסה) 702;
תקנות סדר הדין האזרחי הישנות 701; **חוק העונשין 650**; חוק התכנון והבניה 617.

## 7. Runtime: 5 slowest laws (diagnostic profile, Stage 2+3 only — see §0 caveat)

| Rank | Law | Diagnostic seconds | Articles | Candidates (definitions) | Edges |
|---|---|---|---|---|---|
| 1 | תקנות הטיס (הפעלת כלי טיס וכללי טיסה) | 81.42s | 702 | 248 | 6,625 |
| 2 | תקנות התעבורה | 76.81s | 1,023 | 317 | 8,304 |
| 3 | פקודת מס הכנסה | 72.83s | 554 | 340 | 10,634 |
| 4 | תקנות התכנון והבניה (בקשה להיתר, תנאיו ואגרות) | 54.85s | 1,203 | 166 | 1,150 |
| 5 | תקנות ההתגוננות האזרחית (מפרטים לבניית מקלטים) | 47.61s | 369 | 127 | 2,180 |

Note on the manager's interim read of the log tail: the log printed the
top-10 slowest **worst-first**; "חוק הגנה על בריאות הציבור (מזון)" at 32.3s
is real but is **rank 8**, not the worst — the tail of a truncated view
happened to land mid-list. The authoritative sorted data
(`timing_profile.json`) puts תקנות הטיס (הפעלת כלי טיס) at the top (81.4s).

**No pathological blowup found.** Cost tracks the (definitions × articles)
product per document, not article count alone: תקנות התכנון והבניה (בקשה
להיתר) has the single largest article count in the corpus (1,203) but only
166 definitions, and ranks 4th, well behind laws with far fewer articles but
more definitions (e.g. פקודת מס הכנסה, 554 articles × 340 definitions).
**חוק העונשין** (650 articles, 102 definitions per the pilot ingest) does
**not** appear in the top 20 slowest at all — its definitions×articles
product (~66k) is comfortably below the top offenders (e.g. חוק החברות at
147×564≈83k took 22.6s), so there is no evidence of the pathological
blowup the brief flagged as a risk to watch for.

## 8. Three confirmed engine issues

### Issue 1 (HIGH) — duplicate article-number cross-attribution

**Root cause**: `run_definition_linking` builds
`number_to_article = {art.number: art for art, _ in doc_articles}` — a plain
dict keyed by article **number** per document. When a document's wiki source
contains more than one `@ N.` marker with the same `N` (schedules, appendices,
or numbered sub-lists that reuse the article-marker syntax), only the
**last**-seen Article row survives in the dict. Any `ArticleUsesTermEdge`
found in *any* of the duplicate-numbered articles' body text gets attributed
via this dict to whichever Article row currently occupies that number slot —
which may not be the article where the match actually occurred.

**Confirmed concretely**: `צו איסור הלבנת הון (חובות זיהוי, דיווח וניהול
רישומים של מפעיל מערכת לתיווך באשראי למניעת הלבנת הון)` has two Article rows
both numbered "17". The real one (id `1ee3b932…`) contains the bare term
"פעולה" multiple times ("פרטי כל פעולה כספית שבוצעה", "תאריך ביצוע הפעולה"
etc.). The persisted assertion "Article 17 uses the definition of 'פעולה'"
instead points at the **second** Article "17" (id `9f0baeef…`), whose stored
body is **empty** (`quote_text = ''`) — its "heading" field is actually a
mis-parsed list-item sentence fragment, not a real heading. A reviewer
opening this assertion's cited evidence would see no supporting text at all.

**Affected scale**: 6,423 (document, article-number) groups have ≥2 rows,
across **703 / 6,133 documents (11.5% of the corpus)**. Not every duplicate
group necessarily produces a misattributed edge (only those where a match
happens to land on the number), but the exposure is corpus-wide, not a
one-off.

### Issue 2 (MEDIUM) — repealed/deleted definition entries extracted as live

**Root cause**: Stage 2 extraction has no guard against a definitions-entry
body that is just a Knesset repeal marker, e.g. `"(((נמחקה);))"` ("repealed").
Such an entry is persisted as a normal `Definition` row and then matched like
any other term throughout the document.

**Confirmed concretely**: in חוק החברות (Companies Law), the term "בית
המשפט" ("the Court" — one of the most generic phrases in Hebrew legal text)
is defined with `definition_text = "(((נמחקה);))"`. This phantom "definition"
is the `object_entity_id` for **98** USES_DEFINITION assertions — **4.7% of
this single document's 2,075 edges** — each falsely claiming the article
"uses" a definition that was formally deleted and no longer exists in the
law's actual text.

**Affected scale**: at least one other `(((נמחקה);))`-bodied definition
("שטר מניה") exists in the same document (0 edges attached, so no additional
harm there), suggesting this pattern recurs wherever an amended law leaves a
repeal marker in place of a deleted definitions entry — likely a handful of
documents corpus-wide, but each occurrence can generate a large, silently
wrong edge cluster if the repealed term happens to be a common word.

### Issue 3 (MEDIUM) — parenthetical-qualifier resolution gap in cross-law derivation

**Root cause**: `_LAW_REF_RE` (`app/definition_links/derivation.py`) is
`r"^ב((?:חוק|פקודת|פקודה)\s+[^,;()]+(?:,\s*[^,;()]*?\d{4})?)"` — the
captured group explicitly excludes `(` and `)`. Any law whose real, ingested
title requires a parenthetical qualifier (e.g. `חוק הבנקאות (שירות ללקוח)`,
`חוק מיסוי מקרקעין (שבח ורכישה)`) can **never** resolve via this path: the
regex stops at the first `(` in the clause text, producing a short name that
does not exact-match the document's full title in `known_law_titles` — even
though the target document is genuinely present in the matter. A related,
compounding artifact: the character class also allows `.`, so a clause ending
in a sentence-period (e.g. "...בחוק מיסוי מקרקעין.") captures that trailing
period into the "law name," which would block an exact match even if the
paren issue were fixed.

**Confirmed concretely**: "חוק הבנקאות" and "חוק הפיקוח על שירותים
פיננסיים" alone account for roughly 100+ of the 1,565 unresolved
DERIVES_FROM_LAW edges (§6) purely from this truncation, not from any
genuine ambiguity or absent target law.

**Distinct from a good design decision**: ruling M5's "never fabricate a
guess" is working as intended for cases like "חוק קופות גמל" → no document
titled exactly that exists (the real law is "חוק הפיקוח על שירותים
פיננסיים (קופות גמל)") — correctly left unresolved, since resolving a
colloquial short name to a differently-titled law would require semantic
knowledge the design deliberately does not attempt. Issue 3 is a narrower,
mechanical regex-boundary defect layered on top of that otherwise-sound
policy.

## 9. Hand spot-check — 15 links quoted against source text

Verdict key: CORRECT = accurate and useful; DEBATABLE = mechanically
defensible but of limited/ambiguous value, or a "correct" non-resolution
reached for an accidental rather than principled reason; WRONG = factually
incorrect. **Score: 11/15 CORRECT, 4/15 DEBATABLE, 0/15 WRONG.**

### USES_DEFINITION (5)

1. **חוק מידע גנטי, Art. 14, term "ועדת אתיקה"** — article: "...החליט המטפל
   כאמור יודיע מיד על **החלטתו לועדת אתיקה** ויצרף את התוצאות..."; definition:
   "כמשמעותם בחוק זכויות החולה". **CORRECT** — exact, specific term, ל-prefix
   surface form correctly matched.

2. **צו בדבר הוראות ביטחון (יהודה והשומרון), Art. 130, term "עבירה"**
   (chapter-scoped) — article: "...יורה שאותו אדם יישפט על **העבירה**
   שמואשם בה."; definition: "מעשה, מחדל או נסיון, שהם בני עונשין לפי דין או
   תחיקת בטחון". **CORRECT** — generic word ("offense"), but chapter-scoping
   correctly restricts it to the defining chapter, and the usage is genuine.

3. **תנאים להיתר סוג למיתקנים פוטו-וולטאיים, Art. 15, term "מיתקן
   פוטו-וולטאי"** — article: "**תכנון והתקנה של מיתקן פוטו-וולטאי** יבטיחו
   שהפעלתו..."; definition: "מיתקן חשמל לייצור חשמל בטכנולוגיה
   פוטו-וולטאית". **CORRECT** — clean bare match, unambiguous compound term.

4. **חוק רישוי שירותים ומקצועות בענף הרכב, Art. 247, term "צו שמאי רכב"**
   — article, list item (5): "[[=צו שמאי רכב|צו הפיקוח על מצרכים ושירותים
   (שמאי רכב), התש״ם–1980]] **(להלן – צו שמאי רכב)**"; definition_text is
   literally the term itself ("צו שמאי רכב"), an artifact of the
   `(להלן – X)` adhoc-definition extractor. **DEBATABLE** — mechanically a
   real string match within the declared local scope, but the "definition"
   carries no substantive content (self-referential label), so the edge adds
   no analytical value.

5. **תקנות הסעה בטיחותית לילדים..., Art. 7, term "אחראי"** — article:
   "...יודיע איש צוות ממעון היום השיקומי על כך **לאחראי** על הפעוט..."
   ; definition: "כהגדרתם בחוק מעונות יום שיקומיים". **CORRECT** — genuine,
   meaningful reference in context, though "אחראי" (short/generic "person
   responsible") is flagged separately as a genericness risk (§10).

### DERIVES_FROM_LAW, resolved (5) — all CORRECT

1. `"גיל פרישה" כמשמעותו חוק גיל פרישה` → resolved to **חוק גיל פרישה**.
   Clause: "...לא יפחת מגיל פרישה מוקדמת, **כמשמעותו בחוק גיל פרישה**...".
   **CORRECT** — exact target, semantically sound.
2. `"החלטה להטיל קנס" כהגדרתם חוק הפרות תעבורה מינהליות` → resolved to
   **חוק הפרות תעבורה מינהליות**. **CORRECT**.
3. `"חברת בת ממשלתית" כמשמעותן חוק החברות הממשלתיות, התשל"ה-1975` →
   resolved to **חוק החברות הממשלתיות** (year suffix correctly stripped).
   **CORRECT**.
4. `"קבלן כוח אדם" כהגדרתם חוק העסקת עובדים על ידי קבלני כוח אדם,
   התשנ"ו-1996` → resolved to **חוק העסקת עובדים על ידי קבלני כוח אדם**.
   **CORRECT**.
5. `"רכב פרטי" כהגדרתם פקודת התעבורה` → resolved to **פקודת התעבורה**.
   **CORRECT**.

### DERIVES_FROM_LAW, unresolved (5)

1. `"פעוט עם מוגבלות" כמשמעותה חוק הסעד` — full clause: "...ועדת אבחון,
   **כמשמעותה בחוק הסעד (טיפול באנשים עם מוגבלות שכלית-התפתחותית),
   התשכ"ט-1969**, מצאה שיש לו מוגבלות...". **DEBATABLE** — a human resolves
   this instantly to the parenthetically-qualified law; the engine's decline
   is Issue 3 (paren truncation), not a principled ambiguity call.
2. `"נושא משרה" כהגדרתו חוק החברות ולעניין חברה להפעלת מערכת סליקה
   פנסיונית מרכזית - לרבות כל עובד הכפוף לו במישרין` — target law "חוק
   החברות" is unambiguous and present in the corpus (2,075 USES_DEFINITION
   edges elsewhere), but the greedy regex swallowed the entire trailing
   qualifying clause into the "matched text". **DEBATABLE** — correctly
   avoided a wrong guess, but the underlying extraction is unusable as
   evidence and a human would resolve "חוק החברות" easily.
3. `"חברה מנהלת" כהגדרתה חוק קופות גמל` — no document titled exactly "חוק
   קופות גמל" exists in the corpus (the real law is "חוק הפיקוח על שירותים
   פיננסיים (קופות גמל)"). **CORRECT** — a colloquial short name genuinely
   differs from the official title; declining to fuzzy-guess is the right
   call here.
4. `"הכנסה חייבת" כהגדרתו חוק מיסוי מקרקעין.` (note trailing period) —
   real law is "חוק מיסוי מקרקעין (שבח ורכישה), התשכ"ג-1963". **DEBATABLE**
   — double gap (paren truncation + captured trailing period); a human
   resolves this immediately, the engine's non-resolution is accidental.
5. `"חברת תשלומים" כהגדרתם חוק הסדרת העיסוק בשירותי תשלום` — verified: no
   document titled exactly this exists; the actual ingested law is "חוק
   הסדרת העיסוק בשירותי תשלום **וייזום תשלום**" (a later amendment expanded
   the official title). **CORRECT** — the clause's shorter name is an
   outdated reference to a since-renamed law; declining to guess is right.

## 10. False-positive hunt

Ten USES_DEFINITION matches were sampled deterministically (evenly-strided
across all 219,176 edges ordered by id) and checked by hand:

| # | Term | Law | Verdict |
|---|---|---|---|
| 1 | ועדת אתיקה | חוק מידע גנטי | clean, specific |
| 2 | ייצור | תקנות תוצרת אורגנית | clean (matched via מ-prefix "מייצור עצמי"), moderately generic but correctly law-scoped |
| 3 | בית המשפט | חוק החברות | **CONFIRMED FALSE POSITIVE** — repealed `(נמחקה)` definition, Issue 2 |
| 4 | סכום ההשקעה | כללי התקשורת (בזק ושידורים) | clean, specific |
| 5 | פעולה | צו איסור הלבנת הון (...) | **CONFIRMED WRONG-ARTICLE ATTRIBUTION** — Issue 1 (semantic claim plausible, but the cited Article's body is empty) |
| 6 | ספק תכנים | חוק מניעת פגיעת גוף שידורים זר... | clean, genuine cross-reference within a compound definition body |
| 7 | בעל רישיון בלו | חוק הבלו על דלק | clean, genuine definition-of-a-definition cross-reference |
| 8 | חברה ממשלתית | חוק התכנון והבניה_תזכיר חוק | clean, specific compound term |
| 9 | ועדת החוקה | חוק חדלות פירעון ושיקום כלכלי | clean, specific |
| 10 | ציוד כיבוי | תקנות שירותי הכבאות | clean, specific |

**Rate in this sample: 2/10 (20%) have a confirmed defect** when checked
against source text and article attribution — both defects map to Issues 1
and 2 above, not to random noise. **8/10 are clean, specific, meaningful
matches** — no case of an obviously-wrong semantic match (e.g. a defined
term matching an unrelated sense of the same word) was found in this sample.

**Separate macro-level "common-word" check** (the director's specific
concern): 2,384 of 49,711 definitions (4.8%) have terms ≤3 characters. The
heaviest-firing ones are all short, everyday Hebrew words that ARE formally,
correctly, law-wide-scoped defined terms within their own law and DO
recur legitimately hundreds of times in that one law:

| Term | Law | USES_DEFINITION edges |
|---|---|---|
| רכב (vehicle) | תקנות התעבורה | 415 |
| צבא (army) | חוק השיפוט הצבאי | 348 |
| מס (tax) | פקודת מס הכנסה | 296 |
| בית משפט / רשם | תקנות סדר הדין האזרחי הישנות | 190 |
| השר (the Minister) | חוק הביטוח הלאומי | 179 |
| נמל (port) | תקנות הנמלים | 158 |
| אדם (person) | פקודת מס הכנסה | 146 |
| צו (order) | צו בדבר הוראות ביטחון (יהודה והשומרון) | 146 |

None of these are wrong — each term is genuinely defined in its own law and
genuinely reappears that often — but they are **low-signal, high-volume**:
a reviewer triaging proposed assertions will see hundreds of "Article N uses
'רכב'"-style edges per law that don't discriminate between meaningfully
different provisions. This is a usefulness/precision-of-recall concern
distinct from the true 20% defect rate above, not a correctness bug.

## 11. Files in this directory

- `pilot.sqlite`, `pilot_rebuild.sqlite` — Stage 1 pilot DBs
- `full.sqlite` — the full-corpus matter (post run1+run2, 0 net change)
- `full_snapshot.sqlite` — read-only snapshot used for all SQL analysis
- `pilot_sample.json`, `all_wiki_files.json` — file lists
- `run_pilot.py`, `ingest_full.py`, `link_full.py`, `analyze_full.py`,
  `spotcheck.py`, `timing_profile.py` — scripts (all read/write only inside
  this scratch directory + read-only against the POC corpus)
- `pilot_summary.json`, `full_link_result_run1.json`,
  `full_link_result_run2.json`, `full_ingest_progress.json`,
  `analysis_full.json`, `spotcheck_detail.json`, `timing_profile.json` — raw
  data backing every number in this report

## 12. Manager addendum (independently verified)

- Headline numbers re-derived by the manager via direct SQL on `full.sqlite`:
  223,669 / 219,176 / 4,493 / 1,565 / 49,711 — all exact matches. run1/run2
  result JSON observed directly (watcher on the pids), determinism PASS.
- Issue 2 blast radius correction: corpus-wide, **2,981 USES_DEFINITION
  edges point at definitions whose body contains a נמחקה (repealed) marker**
  (~1.4% of all USES_DEFINITION edges) — larger than the single-document
  example in §8; the report's "handful of documents" undersells it.
- Scratch artifacts (sqlite DBs, scripts, raw JSON) live in the session
  scratchpad and are NOT committed; this report is the durable record.
