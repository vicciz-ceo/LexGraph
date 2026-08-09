# M-R116 all-53 result: blocked on a genuine B1 loss

The winner-only all-53 measurement completed against snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`. The pre-write membership gate
passed: both the current and evaluated B1 populations are exactly 193,827 rows
with SHA-256
`362b863878533a6dd8bb876e25b300bd88bd2fe5d34aedca180a2e690b6ae08d`.

The resulting ledger has 168 source-adjudication records (166 removals and two
additions). Fail-closed adjudication stopped at the following genuine removal:

| field | value |
| --- | --- |
| source | `us_ar_statutes.parquet:8096` |
| source row | `STATE_AR_T5_C64_S4_S5-64-411` / Ark. Code § 5-64-411 |
| candidate | `recreation center` |
| current definition text | `a public place of entertainment consisting of various types of entertainment, including without limitation billiards or pool, ping pong or table tennis, bowling, video games, pinball machines, or any other similar type of entertainment` |
| source evidence | `(e) As used in this section, "recreation center" means a public place of entertainment ...` |

This is a direct current-B1 definition, so it is not an acceptable filter loss.
The current payload filter takes the earlier occurrence of `recreation center`
in subsection `(a)(2)(D)`'s facility list rather than its direct subsection
`(e)` definition. That earlier occurrence has no local payload and therefore
causes the later valid baseline candidate to be suppressed.

M-R116 permits only the matched plural-list/anaphora repair inside current B1
winners and prohibits new generic dispatch or synthesis. Restoring this direct
baseline candidate needs a separate, explicitly authorized preservation rule;
no such repair is proposed here. The run is therefore blocked, with no
Developer transition or production mutation authorized.

Reproducible artifacts are in `all-v1/`: `summary.json`, `changed.jsonl`, both
membership ledgers, and `all_adjudication_run.log` (the fail-closed error).
