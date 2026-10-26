"""Generate a reproducible sample input for the CLI and print it to STDOUT.

Drug names are sampled from the dataset, so random lines often contain real interactions
(including ties at the top severity). Defaults respect the spec limits: 1 to 20 drugs per line and
1 to 10,000 lines. The same ``--seed`` always produces the same output.

    python scripts/gen_input.py --lines 10000 --drugs-per-line 20 --seed 0 > big_input.txt
"""

import argparse
import json
import random
from collections.abc import Sequence
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "src" / "interactions" / "data"
DEFAULT_DATA = DEFAULT_DATA / "interactions.json"
MAX_LINES = 10_000
MAX_DRUGS_PER_LINE = 20


def dataset_drugs(path: Path) -> list[str]:
    """Sorted distinct drug names found in a data file."""
    records = json.loads(path.read_text(encoding="utf-8"))
    return sorted({drug for record in records for drug in record["drugs"]})


def generate(drugs: Sequence[str], lines: int, drugs_per_line: int, seed: int) -> list[str]:
    """``lines`` space-separated lines of ``drugs_per_line`` distinct drugs each."""
    if not 1 <= lines <= MAX_LINES:
        raise ValueError(f"lines must be between 1 and {MAX_LINES}")
    if not 1 <= drugs_per_line <= min(MAX_DRUGS_PER_LINE, len(drugs)):
        raise ValueError(f"drugs-per-line must be between 1 and {MAX_DRUGS_PER_LINE}")
    rng = random.Random(seed)
    return [" ".join(rng.sample(list(drugs), drugs_per_line)) for _ in range(lines)]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("--lines", type=int, default=MAX_LINES)
    parser.add_argument("--drugs-per-line", type=int, default=MAX_DRUGS_PER_LINE)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args(argv)
    try:
        lines = generate(dataset_drugs(args.data), args.lines, args.drugs_per_line, args.seed)
    except ValueError as error:
        parser.error(str(error))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
