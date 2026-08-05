"""PR's own registered `HeadingRule` (sprint 2026-08-04-defs-us-pr,
cycle-9 item 31; core seam spec v2 -- `HeadingRule`, sprint
2026-08-04-defs-core-dispatch item I1/I6). Registration only:
`pr_profile.is_definitions_heading` already exists and is already correct
as a pure function (items 1/cycle-2, prior cycles) -- no new detection
logic here, mirrors `rules/us_pr_citations.py`'s "wraps an existing
extractor verbatim" shape. `is_definitions_heading`'s signature
(`(heading: str) -> bool`) already matches `HeadingRule.matches`'s
`Callable[[str], bool]` exactly, so no adapter/lambda is needed.

**No `body_confirms`.** Own fresh corpus measurement (23,636-row
`us_pr_statutes.parquet`, ground truth built independently of this
function's own machinery): 633/633 = 100.00% precision, 633/635 = 99.69%
recall (the 2 misses are both CORRECT Table-of-Contents rejections). Well
above the ~90% floor the headings panel's own D-DF ruling needed a
`body_confirms` gate to reach -- but `body_confirms` can only ever REJECT
a heading match, never rescue a miss, so at 100% precision there is no
false-positive rate for a body-side gate to rescue and adding one would be
pure downside. Data-backed, not inherited from the headings panel's own,
structurally different, answer. Full measurement in the sprint contract
and `test_pr_profile_heading_rule_live_cycle9.py`'s module docstring.
"""

from __future__ import annotations

from app.definition_links import pr_profile
from app.definition_links.rules.registry import HeadingRule, register_heading_rule

register_heading_rule(
    HeadingRule(jurisdiction_codes=("US-PR",), matches=pr_profile.is_definitions_heading)
)
