"""Command line interface: read drug lists from STDIN, print one result line per input line.

Exit codes: 0 success, 1 data, input or output error, 2 usage error, 130 interrupted (Ctrl-C).
"""

import argparse
import contextlib
import errno
import os
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

import interactions
from interactions.data import DataError, load_bundled, load_file
from interactions.index import InteractionIndex, process_lines

DATA_FILENAME = "interactions.json"
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130  # 128 + SIGINT, the shell convention
# Windows reports a write to a pipe whose reader has gone (ERROR_NO_DATA) as EINVAL, not EPIPE.
_CLOSED_PIPE_ERRNOS = frozenset(
    {errno.EPIPE} | ({errno.EINVAL} if sys.platform == "win32" else set())
)


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
            "Exit codes: 0 success, 1 data, input or output error, 2 usage error, "
            "130 interrupted."
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


class InputError(Exception):
    """STDIN cannot be read or is not valid UTF-8."""


def _silence_stdout() -> None:
    """Point stdout at /dev/null so the interpreter's exit-time flush cannot fail (Python docs)."""
    with contextlib.suppress(OSError, ValueError, AttributeError):  # AttributeError: no stdout
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            os.close(devnull)


def _checked_lines(stdin: Iterable[str]) -> Iterator[str]:
    """Yield STDIN lines; raise ``InputError`` at the first line that is not valid UTF-8.

    STDIN is decoded with ``errors="surrogateescape"``: each undecodable byte becomes a lone
    surrogate, which a valid UTF-8 stream can never contain. Checking per line (instead of letting
    the decoder fail on a whole 8 KB chunk) makes the failure exact: every line before the bad
    one has been yielded, and the bad line's number is known.
    """
    lines = iter(stdin)
    number = 0
    while True:
        try:
            line = next(lines)
        except StopIteration:
            return
        except OSError as error:
            raise InputError(f"cannot read input: {error.strerror or error}") from None
        number += 1
        if not line.isascii():
            try:
                line.encode("utf-8")
            except UnicodeEncodeError:
                raise InputError(f"line {number}: invalid UTF-8") from None
        yield line


def run(index: InteractionIndex) -> int:
    """Stream STDIN to STDOUT; one output line per input line.

    Both streams are pinned to UTF-8 and ``\\n`` line endings on every platform. If STDIN is
    invalid on line N, the results for lines 1..N-1 are written first, then the error is reported.
    """
    stdin, stdout = sys.stdin, sys.stdout
    if stdin is None or stdout is None:
        closed = "stdin" if stdin is None else "stdout"
        print(f"error: {closed} is closed", file=sys.stderr)
        return EXIT_ERROR
    if hasattr(stdin, "reconfigure"):
        # utf-8-sig is UTF-8 that also drops one BOM at the very start of the stream
        stdin.reconfigure(encoding="utf-8-sig", errors="surrogateescape", newline="\n")
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    try:
        stdout.writelines(f"{result}\n" for result in process_lines(_checked_lines(stdin), index))
    except InputError as error:
        stdout.flush()  # the results before the bad line come first
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    stdout.flush()
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI; never raises for I/O problems (see the exit codes in the module docstring)."""
    try:
        stderr = sys.stderr
        if hasattr(stderr, "reconfigure"):  # messages are UTF-8 with "\n" endings on every platform
            stderr.reconfigure(encoding="utf-8", errors="backslashreplace", newline="\n")
        code = _main(argv)
        if sys.stdout is not None:
            sys.stdout.flush()  # --help/--version output is flushed here, not at interpreter exit
        return code
    except BrokenPipeError:  # the reader of STDOUT went away: not an error
        _silence_stdout()
        return EXIT_OK
    except KeyboardInterrupt:
        # Results still buffered are discarded: the reader may be gone (a flush would hit EPIPE) or
        # not reading (a flush would block, and Ctrl-C must always end the process). Pointing
        # fd 1 at /dev/null makes the interpreter's exit-time flush harmless.
        _silence_stdout()
        return EXIT_INTERRUPTED
    except OSError as error:
        _silence_stdout()
        if error.errno in _CLOSED_PIPE_ERRNOS:
            return EXIT_OK
        print(f"error: cannot write output: {error.strerror or error}", file=sys.stderr)
        return EXIT_ERROR


def _main(argv: Sequence[str] | None) -> int:
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
