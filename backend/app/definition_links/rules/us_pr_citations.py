"""PR's own registered `CitationRule` (sprint 2026-08-04-defs-us-pr,
cycle-5 item 27; core seam spec v2.3 M12 -- core named this panel
explicitly as `CitationRule`'s intended consumer). Registration only:
`pr_profile.find_citations` already exists and is already correct as a
pure function (item 4, prior cycles) -- no new extraction logic here,
mirrors `il_scope_triggers.py`'s "wraps an existing extractor verbatim"
shape.

Documented, accepted limitation (already-merged `us_profile.py`, out of
this panel's write-set): `USProfile.find_citations` runs baseline FIRST
and claims its own matched spans before any registered `CitationRule` is
even considered, so a real `N L.P.R.A. § N` citation's bare `§ N` portion
is always claimed by baseline's own `_SECTION_SYMBOL_RE` first -- the
fuller L.P.R.A. form this rule's `find_citations` would otherwise return
never survives, regardless of registration. See `test_pr_profile_
citation_rule_live_cycle5.py`'s own documentation test for the pinned
proof. The three PR citation shapes that do NOT collide with any baseline
pattern (`Ley N-YYYY` dash form, `Ley Núm. N de <fecha>`, bare
`Artículo N`) are this rule's clean, uncollided positive contribution.
"""

from __future__ import annotations

from app.definition_links import pr_profile
from app.definition_links.rules.registry import CitationRule, register_citation_rule

register_citation_rule(
    CitationRule(jurisdiction_codes=("US-PR",), find=pr_profile.find_citations)
)
