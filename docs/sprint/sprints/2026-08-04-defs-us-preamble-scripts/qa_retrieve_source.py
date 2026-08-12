"""Retrieve one adjudication source row from the pinned parquet by stable locator."""

from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow.parquet as pq

from qa_g7_common import CertificationError, SNAPSHOT_ID, sha256_value, validate_corpus


def retrieve(snapshot: Path, source_file: str, source_row: int, source_row_id: str, source_row_sha256: str) -> dict:
    """Fail closed unless a supplied committed locator resolves identically."""
    validate_corpus(snapshot)
    path = snapshot / source_file
    if path.parent.resolve() != snapshot.resolve() or not path.is_file():
        raise CertificationError(f"source file is not in pinned snapshot: {source_file}")
    if source_row < 0:
        raise CertificationError("source_row must be nonnegative")
    index = 0
    for batch in pq.ParquetFile(path).iter_batches(columns=["act_id", "section_title", "text", "chapter", "section_number"], batch_size=2048):
        for row in batch.to_pylist():
            if index == source_row:
                actual_id = str(row["act_id"] or f"{source_file}:{source_row}")
                actual_hash = sha256_value({"act_id": actual_id, "heading": row["section_title"] or "", "body": row["text"] or ""})
                if actual_id != source_row_id or actual_hash != source_row_sha256:
                    raise CertificationError("pinned source row identity/hash disagreement")
                return {"snapshot_id": SNAPSHOT_ID, "source_file": source_file, "source_row": source_row,
                        "source_row_id": actual_id, "source_row_sha256": actual_hash, "row": row}
            index += 1
    raise CertificationError(f"source_row {source_row} is outside {source_file}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--source-row", required=True, type=int)
    parser.add_argument("--source-row-id", required=True)
    parser.add_argument("--source-row-sha256", required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(retrieve(args.snapshot, args.source_file, args.source_row, args.source_row_id, args.source_row_sha256), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
