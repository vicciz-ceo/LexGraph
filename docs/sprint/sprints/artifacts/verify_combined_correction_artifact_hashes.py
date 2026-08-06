#!/usr/bin/env python3
"""Verify deterministic hashes for the committed combined-correction evidence.

Only stable persisted tuple fields participate in the hash.  Human/machine
judgments deliberately remain reviewable artifact metadata rather than hidden
hash inputs.  The rejected-summary file is compact evidence only: its full
ledgers are intentionally uncommitted, so it must not claim a self-verifiable
ledger hash.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORE_FIELDS = (
    "file",
    "jurisdiction",
    "act_id",
    "derived_heading",
    "terms",
    "before",
    "after",
)
EXACT_ARTIFACTS = (
    ROOT / "2026-08-07-defs-us-combined-structural-exact.json",
    ROOT / "2026-08-07-defs-us-combined-ne-sd-exact.json",
)
REJECTED_SUMMARY = ROOT / "2026-08-07-defs-us-combined-fed-rejected-summary.json"


def canonical_changed_ledger_sha256(payload: dict) -> str:
    """Return the hash of sorted persisted tuple facts only."""
    projection = {
        "changed_persisted_keys": sorted(
            [{field: item.get(field) for field in CORE_FIELDS} for item in payload["changed_persisted_keys"]],
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
        )
    }
    return hashlib.sha256(
        json.dumps(projection, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    for path in EXACT_ARTIFACTS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored = payload["canonical_changed_ledger_sha256"]
        actual = canonical_changed_ledger_sha256(payload)
        assert stored == actual, f"{path.name}: stored {stored}, recomputed {actual}"
        print(f"PASS {path.name} {actual}")

    summary = json.loads(REJECTED_SUMMARY.read_text(encoding="utf-8"))
    for name, item in summary.items():
        if name.startswith("rejected_"):
            assert item["full_ledger_committed"] is False, name
            assert "canonical_changed_ledger_sha256" not in item, name
    print(f"PASS {REJECTED_SUMMARY.name} compact-only; no unverifiable full-ledger hash")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
