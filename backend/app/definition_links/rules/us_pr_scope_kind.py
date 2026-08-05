"""PR's own registered `ScopeKindRule` (sprint 2026-08-04-defs-us-pr,
cycle-9 item 32, gate P3's chapter half; core seam spec manager ruling
M-D2 -- the kind behind `determine_scope`). Registration only:
`pr_profile.detect_pr_chapter_scope` already exists as a pure,
first-sentence-anchored function (see its own docstring in `pr_profile.py`
for the full M-D3-erratum anchoring rationale and the measured 21/633
canonical-row population) -- no new detection logic here, mirrors
`rules/us_pr_citations.py`'s "wraps an existing extractor verbatim" shape.
`detect_pr_chapter_scope`'s signature (`(body_text: str) -> str | None`)
already matches `ScopeKindRule.detect`'s `Callable[[str], str | None]`
exactly, so no adapter/lambda is needed.

Dispatch (`USProfile.determine_scope`, unchanged by this registration):
baseline-first (English `_US_CHAPTER_SCOPE_TRIGGERS`, which never fires on
Spanish text) wins whenever IT already detects `"chapter"`; only when
baseline falls through to its `"law-wide"` default is this rule tried.
`detect_pr_chapter_scope` returning `None` ("no opinion") lets that
`"law-wide"` default stand -- this rule never manufactures a `"local"` or
any other scope kind.
"""

from __future__ import annotations

from app.definition_links import pr_profile
from app.definition_links.rules.registry import ScopeKindRule, register_scope_kind_rule

register_scope_kind_rule(
    ScopeKindRule(jurisdiction_codes=("US-PR",), detect=pr_profile.detect_pr_chapter_scope)
)
