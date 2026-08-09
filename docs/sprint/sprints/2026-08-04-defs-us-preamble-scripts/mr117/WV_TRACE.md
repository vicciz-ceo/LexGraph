# M-R117 West Virginia direct-to-persistence trace

Pinned source: `STATE_WV_C49_A8_S4` (`us_wv_statutes.parquet:3459`).

The source template entry has a curly opening delimiter and a straight closing
delimiter: `“This power of attorney ... at any time."`. It is a current B1
candidate whose current emitted definition text is `By: ... (Parent/Legal
Custodian signature)`.

| stage | observed result |
| --- | --- |
| current local-scope candidates | none for the template entry |
| current definitions-section candidates | template candidate present |
| raw-body runtime section candidates | candidate preserved: no valid matched delimiters |
| `capture_row` parser body | `normalize_for_parsing` changes the mismatched pair to a straight `"..."` pair |
| patched heading on parser body | `None` |
| patched local candidates | none |
| patched definitions-section candidates when called directly | candidate present, but never reached by capture after heading becomes `None` |
| capture first-wins / dedup | no emissions; dedup has no key |
| persisted tuple | absent because no candidate reaches the pipeline |

Therefore the loss occurs at the patched B1 derived-heading eligibility gate,
before local/section union and before pipeline first-wins persistence. The
apparent direct-versus-persistence disagreement is caused by raw source quote
identity being erased by parser normalization. A production quote-grammar
change would not address that carrier mismatch.
