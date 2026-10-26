"""Command line entry point: read drug lists from STDIN, print interactions."""

import sys

from interactions.lib.interactions_logic import get_interactions


def main() -> None:
    for line in sys.stdin.read().splitlines():
        drugs = set(line.split())
        # sorted() is stable, so ties keep their order from interactions.json.
        interactions = sorted(get_interactions(drugs=drugs), key=lambda i: i.severity, reverse=True)
        if not interactions:
            print("No interaction")
            continue
        top = interactions[0].severity
        for interaction in interactions:
            if interaction.severity == top:
                print(f"{interaction.severity.name}: {interaction.description}")
