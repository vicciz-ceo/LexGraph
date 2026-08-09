# M-R121 code-review adjudication v2

> **Historical, superseded by M-R122.** This bounded closure was not a full
> runtime-prototype proof. The complete 193,830-member audit is in `../mr122/`.

Status: **PASS.** All 124 durable disputed keys and the complete 63-row closure are classified under uniform M-R121 semantics, with zero unclassified decisions or irreducible list ambiguities. Production remains untouched.

## Corrected bindings

- Colorado `Nebraska`: **drop the old removal / preserve**. The source explicitly designates the states, respectively, as `"Colorado"` and `"Nebraska"`; the generic reciprocal alias/name relation controls the inline fallback miscapture.
- West Virginia mixed-delimiter item: **reject the WIP removal / preserve**. Opening curly plus closing straight is not a like-delimiter occurrence, so raw source fails open.
- Neither removal is in the v2 ledger.

## Decisions and closure

- Old-ledger disputes: **71 drop old removal**, **42 keep old removal**.
- WIP extras: **3 accept removal**, **6 reject removal**, **2 accept addition**, **0 reject addition**.
- Artifact records: 124 disputed decisions + 92 old-baseline closure changes + 64 WIP-to-runtime changes + 16 out-of-dispute closure adjustments = **296**.

| Same 63 rows | Left tuples | Runtime tuples | Removed | Added | Delta |
|---|---:|---:|---:|---:|---:|
| Archived old baseline → v2 | 749 | 665 | 88 | 4 | **92** |
| Bounded WIP → v2 | 687 | 665 | 43 | 21 | **64** |

The four closure additions are:

- `us_in_statutes.parquet:16942` — "utility"
- `us_in_statutes.parquet:16942` — "works"
- `us_in_statutes.parquet:51336` — "utility"
- `us_in_statutes.parquet:51336` — "works"

Replacing 172 old-certificate entries on these rows with the 92-change closure yields **556 = 552 removals + 4 additions**. Row-local intersection is 86; 86 old changes drop; six changes are new.

## Independent byte comparison

The independently generated reviewer and final-audit ledgers were byte-identical. Both SHA-256 values are `17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`. Exact set diff: empty; the durable copy is `expected_changed.jsonl`.

## Out-of-dispute closure

- DC row 2644: drop 12 old removals under a shared forwarding relation — "Adult education", "Alternative program", "At-risk", "At-risk high school over-age supplement", "Elementary ELL", "Level 1: Special Education", "Level 2: Special Education", "Level 3: Special Education", "Level 4: Special Education", "Limited English Proficient/Non-English Proficient", "Special Education Level 2 ESY", "Special Education Level 3 ESY".
- Federal row 7066: drop 1 old removal under an alias relation — "Standby Support Program Account".
- Maryland row 6509: drop 2 old removals under colon/enumerated direct relations — "Consequential damages", "Transfer".
- Hawaii row 5: add 1 removal because legislative-history structure is non-substantive — "Intoxicants and Narcotics: The insurer shall not be liable for any loss sustained or contracted in consequence of the insured's being intoxicated or under the influence of any narcotic unless administered on the advice of a physician.".

## Control and gates

`R7_reciprocal_respectively_designation` uses novel Cerulea/Borealia identities, followed within the fallback gap by paragraph 2's `shall include and bind`, and requires byte-for-byte preservation at direct and persistence altitudes. The reciprocal matcher shares the complete structural alias/name verb family (`referred to`, `known`, `designated`, `established`, `maintained`) with the singular matcher. Patched prototype: **78 passed**. Current unpatched production pair: **25 failed, 21 passed**; R7's preservation pair passes production, while the pre-fix runtime prototype omitted Borealia.

## Hashes

- Expected ledger: `17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`
- Independent final ledger: `17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`
- Reviewer adjudication: `d62b2ab9daf0fc9f6eabd486921005bdd2e336855596478914f0ef22676b6d95`
- Membership: `632fa4b617fbca7cc4f7c1f7eef8bfc5d3be8a9b7f90c5338edc499a2a69a9e0`
- Closure: `83d811066db2f5c182d63a53dfabeea8fca954a2b7aa188816ed14044f179b3c`
- WIP delta: `99ef2b1b61241dc8e5daff310407e318f60db04eb4097b078140a16b6286b93b`
- Baseline: `f065d8ee838effaba250ea13fb9c234904b3a63985893f0a921d856bc396b3f8` (592694 records)
- WIP: `15207cf77a23ecdc77945559e8939583370b3e5b4b142db15868fb42fbd37a1f` (592168 records)
- Prototype: `be87a590ae7806555623947239e673e92e326944fc018b341cadb0f7a832c9ee`
- Unit control: `78b8808b4e41df70d61ed6d2a0ebe4a71640382fcead2bd3f80adcb6e270ef31`
- Persistence control: `2c448bb67e9846ff5033a9f0e6e45f72d450f9bfc2e1a11d5fd90ddf6579263c`
- Combined v1 adjudication input: `b3a866c7f3582a14b91041212e5ef4fa299bb37addfdf9d954230407c2bf608c`
