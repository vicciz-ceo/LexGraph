"""Per-jurisdiction rule registry package (sprint 2026-08-04-defs-core-scope,
gate C4; seam spec `## Seam spec (published)`, Seam 2).

Auto-discovery mechanism -- core-authored, stable forever, no per-rule logic
here: importing this package imports every sibling module directly inside
it, in filename-sort order. Each sibling module self-registers its own
rule(s) by calling a `registry.register_*` function at ITS OWN import time
(a module-level side effect) -- a family panel's entire change to the repo
is therefore adding ONE new file to this directory (plus its own tests),
never editing this file, `registry.py`, or any other shared module. File
creation never conflicts in git, so multiple panels landing concurrently is
inherently conflict-free.
"""

from __future__ import annotations

import pkgutil
from importlib import import_module

for _module_info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    import_module(f"{__name__}.{_module_info.name}")

del _module_info
