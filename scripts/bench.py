"""Time the CLI end to end on an input file (best of N runs, output discarded).

Run from the repository root with the project's interpreter:

    uv run python scripts/bench.py                       # committed input.txt
    uv run python scripts/bench.py --input big.txt -n 10

Works against any version of the package: it calls ``interactions.cli.main`` in a fresh
interpreter, so the data file is loaded exactly as a real invocation would load it.
"""

import argparse
import statistics
import subprocess
import sys
import time
from pathlib import Path

RUN_MAIN = "from interactions.cli import main; main()"


def time_once(input_path: Path) -> float:
    with input_path.open("rb") as stdin:
        start = time.perf_counter()
        subprocess.run(
            [sys.executable, "-c", RUN_MAIN],
            stdin=stdin,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("input.txt"))
    parser.add_argument("-n", "--runs", type=int, default=5)
    args = parser.parse_args()
    lines = sum(1 for _ in args.input.open("rb"))
    times = [time_once(args.input) for _ in range(args.runs)]
    print(
        f"{args.input}: {lines} lines, {args.runs} runs: "
        f"best {min(times):.3f}s, median {statistics.median(times):.3f}s"
    )


if __name__ == "__main__":
    main()
