# M-R113 Indiana counterexample

Measurement: `us_in_statutes.parquet`, shard `16/53`, pinned snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`.

Canonical changed-key ledger hash: `14d1747d0cf6603005981cf0afd26c68e6a5b737dabdc628ac69bc6466a220a1`.
It contains 3,363 additions and four removals. Two removals are punctuation-
only pseudo-candidates for `utility` (`; and`), but the other two are genuine
forwarding definitions and block the default-preserve prototype:

| source row | removed term | current text |
| --- | --- | --- |
| `STATE_IN_T8_A1.5_C3_S8-1.5-3-8.2` | `works` | `;\n\nhave the meaning set forth for those terms in section 8.1 of this chapter.` |
| `STATE_IN_T8_A1.5_C3_S8-1.5-3-8.3` | `works` | `;\n\nhave the meaning set forth for those terms in section 8.1 of this chapter.` |

Each source says: `As used in this section: (1) "utility"; and (2) "works";
have the meaning set forth for those terms in section 8.1 of this chapter.`
The current term-local boundary ends at the semicolon immediately after the
quote, which leaves no text for `works`; that is an invalid structural boundary
for an alias list whose shared forwarding relation follows the last alias.

Result: **unsafe**. The prototype would lose two genuine `works` tuples; do
not transition Item 7 to Developer or continue all-53 certification until a
term-list-aware boundary can preserve the common trailing relationship without
retaining the `utility` pseudo-candidate.
