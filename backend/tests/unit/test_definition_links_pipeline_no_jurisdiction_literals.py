"""RED guard test for gate C3 / manager ruling M13 (sprint
2026-08-04-defs-core-scope): "pipeline.py retains no jurisdiction-specific
literals" once the profile-dispatched scope + extraction seam lands (I1/I2).

The previous Planner rejected a structural absence-of-symbol test as
"low-value churn" and proposed closing I3 by code review alone; the
program manager's second opinion favored the guard and the manager ruled
for it (M13): C3's ENTIRE content is this property, it regresses silently,
and no other test in this suite covers it -- I1/I2's own tests prove the
seam EXISTS, not that the OLD Hebrew-only literals are GONE. A rename or a
"just this once" inline fallback could pass every other test in this
sprint while silently reintroducing the exact thing C3 forbids.

Mechanical, source-level check -- mirrors this package's own established
convention for this shape of guard
(`test_definition_links_no_network_dependencies.py`'s AST-based static
check of banned imports) rather than a behavioral test. RED today because
`pipeline.py` still defines every one of the seam spec's own "Deleted /
emptied -- do not build on these" symbols, verbatim, at module level.
"""

from __future__ import annotations

import ast
import inspect

# The seam spec's own "Deleted / emptied" list (## Seam spec (published),
# "Deleted / emptied -- do not build on these"): these 5 symbols move from
# pipeline.py into us_profile.py / behind the 5 Protocol methods this
# sprint adds to JurisdictionProfile. pipeline.py after this sprint calls
# only `profile.*` methods for anything jurisdiction-specific.
BANNED_SYMBOL_NAMES = {
    "_CHAPTER_SCOPE_TRIGGERS",
    "_determine_scope",
    "_is_placeholder_heading",
    "_derive_heading_from_body",
    "_extract_inline_quoted_definitions",
}

# Jurisdiction-specific LITERAL substrings -- proves C3's "no
# jurisdiction-specific literals" property directly, not merely that the 5
# named symbols above are gone. A rename that kept the literal Hebrew
# trigger phrases inline under a new name would dodge the symbol-name
# check above while still violating C3; this catches that case too.
BANNED_LITERAL_SUBSTRINGS = (
    "לענין פרק זה",
    "לענין סימן זה",
    "לענין עבירה",
    "בפרק זה",
    "בסימן זה",
)

# pipeline.py's direct calls to these two Hebrew-only extraction functions
# are deleted by the seam spec, replaced by
# `profile.extract_local_scope_definitions(...)` -- the functions
# themselves are NOT deleted (they become IL's own registered
# ScopeTriggerRule bodies), but pipeline.py itself must never import or
# call them directly again.
BANNED_CALL_NAMES = {"extract_local_definitions", "extract_adhoc_definitions"}


def _pipeline_source() -> str:
    from app.definition_links import pipeline

    return inspect.getsource(pipeline)


def _module_level_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def test_pipeline_module_defines_none_of_the_deleted_jurisdiction_specific_symbols():
    top_level = _module_level_names(_pipeline_source())
    hits = top_level & BANNED_SYMBOL_NAMES
    assert not hits, (
        f"pipeline.py still defines jurisdiction-specific symbol(s) {sorted(hits)} "
        f"at module level -- C3 requires these to live behind the profile seam "
        f"(us_profile.py / the rule registry), never in shared pipeline code."
    )


def test_pipeline_module_contains_no_hebrew_scope_trigger_literals():
    source = _pipeline_source()
    hits = [s for s in BANNED_LITERAL_SUBSTRINGS if s in source]
    assert not hits, (
        f"pipeline.py's source still contains jurisdiction-specific literal "
        f"string(s) {hits} -- C3's entire content is that pipeline.py retains "
        f"NO jurisdiction-specific literals, whether or not they are still "
        f"reachable under one of the named symbols checked above."
    )


def test_pipeline_module_no_longer_references_the_hebrew_only_extraction_functions_directly():
    source = _pipeline_source()
    hits = [name for name in BANNED_CALL_NAMES if name in source]
    assert not hits, (
        f"pipeline.py's source still references {hits} directly -- these calls "
        f"must be replaced by `profile.extract_local_scope_definitions(...)` "
        f"(C2/C3); the Hebrew-only functions themselves stay reachable only "
        f"via IL's own registered ScopeTriggerRule, never a direct pipeline.py "
        f"import/call."
    )
