"""Sprint 2026-07-29-definition-links -- deterministic/no-LLM guardrail.

Gate G1: "same input always yields the same links, no LLM/ML in the path."
Mirrors `tests/unit/test_no_network_dependencies.py`'s existing convention
(static AST check, no module-scope network import) and extends the banned
set with common LLM/ML client libraries, since this feature's entire premise
is wholly deterministic regex/rule-based extraction -- never a model call.

RED today because `app.definition_links` does not exist yet
(ModuleNotFoundError) -- once it exists, this becomes a live regression
guard against an accidental network or ML dependency creeping into the
linker.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil

BANNED_MODULES = {
    "httpx",
    "requests",
    "urllib.request",
    "aiohttp",
    "socket",
    "http.client",
    "openai",
    "anthropic",
    "transformers",
    "torch",
    "sklearn",
    "spacy",
}


def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_definition_links_package_imports_no_network_or_ml_libraries():
    package = importlib.import_module("app.definition_links")
    assert package.__file__ is not None
    for _finder, name, _is_pkg in pkgutil.walk_packages(
        package.__path__, prefix="app.definition_links."
    ):
        module = importlib.import_module(name)
        source = open(module.__file__, encoding="utf-8").read()
        imported = _imported_module_names(source)
        banned_hits = imported & BANNED_MODULES
        assert not banned_hits, f"{name} imports network/ML module(s): {banned_hits}"
