"""Single clean-checkout entrypoint for Q-D1 -> independent Q-D2 -> Q-D3."""

from __future__ import annotations

import argparse
from pathlib import Path

from qa_d1_measure import measure as measure_d1
from qa_d2_independent_denominator import measure as measure_d2
from qa_d3_crosscheck import crosscheck


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    measure_d1(args.snapshot, args.out)
    measure_d2(args.snapshot, args.out)
    result = crosscheck(args.out)
    print(f"G7 CERTIFICATION PASS qd3={result['summary_hash']}")


if __name__ == "__main__":
    main()
