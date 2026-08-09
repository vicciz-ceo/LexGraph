# M-R115 all-53 narrow-parser blocker

Pinned snapshot: `301000fc3465374ee0f23c3c6953a8a861e95cad`.

The narrowed runtime-only measurement completed 53 files / 2,038,247 rows and
changed 1,848 keys (1,682 additions, 166 removals). This is materially smaller
than M-R114's rejected 61,053-key expansion, but source adjudication remains
fail-closed. The ledger SHA-256 is
`5f5d0b38d25cc55c800a09e1777a1d64155a17383fe352957b67a01bdca0ee34`.

Adjudication halted on an invalid addition from
`USC_T49_C53_S5307`:

| field | value |
| --- | --- |
| term | `.\n\nSubsec. (a)(2). Pub. L. 105–178, §3007(b)(3), inserted` |
| emitted definition | `Designated recipient.—The term" after "(2)".` |
| source family | malformed legislative-history / subsection-amendment text |

The earlier Colorado index false addition was fixed by requiring a list marker
and its quote to be on the same line. This federal result proves that generic
numbered-colon baseline-entry synthesis is still unsafe even with that bound.
It is not a source-adjudication gap and must not be repaired with a corpus or
term exception.

Result: **blocked**. Do not promote the narrowed prototype or transition to
Developer. HI (25 deltas) and FED (23 deltas) remain separately measured, but
the FED false addition prevents certification.
