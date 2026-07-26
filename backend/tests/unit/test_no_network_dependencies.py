"""Track D, item D3 — zero-network guardrail (director mandate: "everything
local -- no cloud anywhere"; gates G6/G7 require the enrichment pipeline and
the MCP server to be fully offline).

Static AST check: neither `app.enrich` nor `app.mcp` may import a
network-capable library at module scope. RED today because neither package
exists yet (ModuleNotFoundError) -- once they exist, this becomes a live
regression guard against an accidental network dependency creeping in
(e.g. a future LLM-enricher import forgetting ruling R4's "optional, off by
default" boundary).
"""

from __future__ import annotations

import ast
import importlib
import pkgutil

BANNED_NETWORK_MODULES = {
    "httpx",
    "requests",
    "urllib.request",
    "aiohttp",
    "socket",
    "http.client",
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


def _assert_package_imports_no_network_libraries(package_name: str) -> None:
    package = importlib.import_module(package_name)
    assert package.__file__ is not None
    for _finder, name, _is_pkg in pkgutil.walk_packages(
        package.__path__, prefix=f"{package_name}."
    ):
        module = importlib.import_module(name)
        source = open(module.__file__, encoding="utf-8").read()
        imported = _imported_module_names(source)
        banned_hits = imported & BANNED_NETWORK_MODULES
        assert not banned_hits, f"{name} imports network-capable module(s): {banned_hits}"


def test_enrich_package_imports_no_network_libraries():
    _assert_package_imports_no_network_libraries("app.enrich")


def test_mcp_package_imports_no_network_libraries():
    _assert_package_imports_no_network_libraries("app.mcp")
