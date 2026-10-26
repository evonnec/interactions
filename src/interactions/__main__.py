"""Entry points: ``python -m interactions`` and the ``interactions`` console script."""

import signal
import sys

EXIT_INTERRUPTED = 130  # same as cli.EXIT_INTERRUPTED; cli is not imported yet when this is used
RESTORE_DEFAULT_SIGINT = sys.platform != "win32"  # module-level so tests cover both platforms


def entry() -> int:
    """Run the CLI.

    On POSIX, SIGINT gets its default action first: Ctrl-C then terminates the process at once, in
    every phase, including a ``write()`` blocked on a full pipe (which a Python-level handler
    cannot interrupt on every platform) and a pipeline whose reader has gone. The shell reports
    130 (128 + SIGINT). Nothing needs cleanup: results not yet written are simply dropped. Windows
    keeps Python's handler, and ``KeyboardInterrupt`` is turned into exit 130 here and in ``main``.

    A SIGINT the parent chose to ignore (``cmd &`` in a script, ``nohup``, ``trap '' INT``) is
    inherited as ``SIG_IGN`` and left alone, so a Ctrl-C meant for another process can't kill us.
    """
    if RESTORE_DEFAULT_SIGINT and signal.getsignal(signal.SIGINT) is signal.default_int_handler:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        from interactions.cli import main
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    return main()


if __name__ == "__main__":
    raise SystemExit(entry())
