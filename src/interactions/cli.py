"""Command line interface: read drug lists from STDIN, print one result line per input line.

Exit codes: 0 success, 1 data or input error, 2 usage error.
"""

import argparse
import contextlib
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import interactions
from interactions.data import DataError, load_bundled, load_file
from interactions.index import InteractionIndex, process_lines

DATA_FILENAME = "interactions.json"
EXIT_OK = 0
EXIT_ERROR = 1


class _VersionAction(argparse.Action):
    """``--version`` that looks the version up only when it is requested (keeps startup fast)."""

    def __init__(self, option_strings: Sequence[str], dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, nargs=0, help="show the version and exit")

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        print(f"{parser.prog} {interactions.__version__}")
        parser.exit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="interactions",
        description=(
            "Read lines of space-separated drug names from STDIN and print, for each line, the "
            "most severe interaction as '{SEVERITY}: {description}', or 'No interaction'. "
            "Ties are resolved to the interaction that appears first in the data file."
        ),
        epilog=(
            "The data file is --data if given, else ./interactions.json if it exists in the "
            "current directory, else the dataset bundled with the package. "
            "Exit codes: 0 success, 1 data or input error, 2 usage error."
        ),
    )
    parser.add_argument("--data", metavar="PATH", type=Path, help="interactions JSON file to use")
    parser.add_argument("--version", action=_VersionAction)
    return parser


def load_index(data: Path | None) -> InteractionIndex:
    """Resolve the data source (``--data``, then ./interactions.json, then bundled) and index it."""
    if data is not None:
        interactions = load_file(data)
    elif Path(DATA_FILENAME).is_file():
        interactions = load_file(Path(DATA_FILENAME))
    else:
        interactions = load_bundled()
    return InteractionIndex.build(interactions)


def _silence_stdout() -> None:
    """Point stdout at /dev/null so the interpreter's exit-time flush cannot fail (Python docs)."""
    with contextlib.suppress(OSError, ValueError):
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())


def run(index: InteractionIndex) -> int:
    """Stream STDIN to STDOUT; one output line per input line."""
    stdin = sys.stdin
    if hasattr(stdin, "reconfigure"):
        # utf-8-sig is strict UTF-8 that also drops one BOM at the very start of the stream
        stdin.reconfigure(encoding="utf-8-sig", errors="strict")
    try:
        sys.stdout.writelines(f"{result}\n" for result in process_lines(stdin, index))
        sys.stdout.flush()
    except BrokenPipeError:
        _silence_stdout()
    except UnicodeDecodeError as error:
        print(f"error: input is not valid UTF-8: {error.reason}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:  # argparse exits for --help, --version and usage errors
        return stop.code if isinstance(stop.code, int) else EXIT_OK
    try:
        index = load_index(args.data)  # eager: a bad data file fails before STDIN is read
    except DataError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    for first, second in index.duplicates:
        print(
            f"warning: duplicate interaction pair {first}/{second}: "
            "using the most severe, then earliest",
            file=sys.stderr,
        )
    return run(index)


if __name__ == "__main__":
    raise SystemExit(main())
