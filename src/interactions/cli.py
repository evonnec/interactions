import click
import sys
from interactions.lib.interactions_logic import get_interactions

def main():
    whole_input = sys.stdin.read()
    for line in whole_input.splitlines():
        drugs = set(line.split())
        interactions = get_interactions(drugs=drugs)
        sorted_interactions = sorted(interactions, reverse=True)
        if not sorted_interactions:
            print('No interaction')
        for interaction in sorted_interactions:
            if interaction.severity == sorted_interactions[0].severity:
                print(interaction.severity.upper() + ': ' + interaction.description)
    # Test at scale
    # Fill in README
