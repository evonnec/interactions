"""Command line entry point: read drug lists from STDIN, print interactions."""

import sys

from interactions.lib.interactions_logic import get_interactions


def main() -> None:
    for line in sys.stdin.read().splitlines():
        drugs = set(line.split())
        # sorted() is stable, so among equal severities the first in interactions.json is first.
        interactions = sorted(get_interactions(drugs=drugs), key=lambda i: i.severity, reverse=True)
        if not interactions:
            print("No interaction")
            continue
        best = interactions[0]
        print(f"{best.severity.name}: {best.description}")
