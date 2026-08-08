# M-R114 Indiana shared-relation resolution

Measurement: `us_in_statutes.parquet`, shard `16/53`, pinned snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`.

The corrected changed-key ledger hash is
`33b372618247542777902187332c00b7b19d477bf4aa035f16ba9e26091ff507`.
The source adjudication ledger is committed at
`../mr114/in-v1/in_mr114_adjudication.jsonl`; its summary records 3,365
source-grounded additions, two removals, and zero genuine losses, ambiguities,
or unclassified changes.

Both list members are genuine forwarding definitions:

```text
As used in this section: (1) "utility"; and (2) "works";
have the meaning set forth for those terms in section 8.1 of this chapter.
```

| source row | baseline behavior | M-R114 behavior |
| --- | --- | --- |
| `STATE_IN_T8_A1.5_C3_S8-1.5-3-8.2` | `utility -> ; and`; `works -> substantive forwarding tuple` | remove only malformed `utility` tuple; add forwarding `utility`; retain `works` definition bytes |
| `STATE_IN_T8_A1.5_C3_S8-1.5-3-8.3` | `utility -> ; and`; `works -> substantive forwarding tuple` | remove only malformed `utility` tuple; add forwarding `utility`; retain `works` definition bytes |

The runtime rule recognizes a bounded numbered quoted list whose immediately
following forwarding relation structurally governs its members. It first keeps
the last member's established substantive baseline tuple unchanged, then adds
the shared relation only for missing members. A quoted numbered duty list with
no forwarding relation remains non-dispatching.
