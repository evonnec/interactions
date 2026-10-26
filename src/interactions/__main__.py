"""Entry points: ``python -m interactions`` and the ``interactions`` console script."""

EXIT_INTERRUPTED = 130  # same as cli.EXIT_INTERRUPTED; cli is not imported yet when this is used


def entry() -> int:
    """Run the CLI. ``cli`` is imported here, inside the Ctrl-C guard, so that a Ctrl-C during
    start-up (importing argparse, pathlib, json, ...) also exits 130 instead of a traceback."""
    try:
        from interactions.cli import main
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    return main()


if __name__ == "__main__":
    raise SystemExit(entry())
