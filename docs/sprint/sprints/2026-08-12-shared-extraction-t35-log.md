
## Gate-3 adjudication (program manager, 2026-08-12)

Corpus-wide before/after over 105 parquet files via the Planner's two-stage
tooling. Raw differ result:

    before: 47,910 rows / 79,651 terms
    after:  47,940 rows / 80,866 terms
    terms present before and absent after: 1,627
    terms gained: 2,842        net: +1,215

M-R64's gate reads "no term captured today may disappear", which assumes the
before-set is correct. Here it is not: the before-set is exactly the phantom
population this sprint exists to remove. So each loss was classified.

    1,081  sentence-length (>60 chars) -- whole clauses captured as terms
      497  starts with an enumerator
       45  heading punctuation (trailing ':' or em-dash)
        2  section labels ("SEC. n. DEFINITION.")
        2  not classifiable by heuristic -- adjudicated individually below

The 2 residuals, both in `USC_T20_C48_S3401`, checked against pinned source:
  - `education stabilization fund` -- appears as a proper noun in running prose
    ("...amounts otherwise available through the Education Stabilization Fund,
    there is appropriated..."), not as a definiendum.
  - `maintenance of effort` -- appears inside a heading ("Emergency Assistance
    and Relief to Schools; Maintenance of Effort and Equity").
Both are phantoms. **Zero genuine terms lost.**

That same row is the clearest illustration of the fix: it went from 9 terms --
mostly whole clauses such as `"(3) the term 'Secretary' means the Secretary of
Education;"` -- to 12 clean definienda: Secretary, State, cost of attendance,
full-service community school, institution of higher education, public school,
qualifying emergency, high-poverty school, and others.

MANAGER NOTE ON PROCESS: two probes of mine produced false readings before this
one held. The first monkeypatched a ceiling the target function never reads; the
second read a field named `term` when the records carry `terms`, silently
measuring rows instead of terms and reporting a false all-clear. Both failed
silently rather than erroring. The verdict above is asserted against the
differ's own totals (79,651 / 80,866 / 1,627) inside the script, so a schema
drift fails loudly instead of producing a comfortable number.
