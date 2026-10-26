"""Property-style tests: the indexed implementation equals a brute-force reference."""

import random
from typing import Any

import pytest

from interactions.data import parse_records
from interactions.index import InteractionIndex, process_lines
from tests.reference import reference_output

SEVERITIES = ["minor", "moderate", "major"]


def random_records(rng: random.Random, vocabulary: list[str], count: int) -> list[dict[str, Any]]:
    """Random records over a small vocabulary, so duplicate pairs and ties are common."""
    records = []
    for n in range(count):
        first, second = rng.sample(vocabulary, 2)
        records.append(
            {
                "drugs": [first, second],
                "severity": rng.choice(SEVERITIES),
                "description": f"record {n}",
            }
        )
    return records


def random_lines(rng: random.Random, vocabulary: list[str], count: int) -> list[str]:
    lines = []
    for _ in range(count):
        size = rng.randint(0, 60)  # beyond the spec's 20: long lines must work too
        tokens = [rng.choice([*vocabulary, "unknown1", "unknown2"]) for _ in range(size)]
        tokens = [t.upper() if rng.random() < 0.2 else t for t in tokens]  # case noise
        separator = rng.choice([" ", "  ", "\t", " \x0c "])
        lines.append(separator.join(tokens) + rng.choice(["", "\n", "\r\n"]))
    return lines


@pytest.mark.parametrize("seed", range(25))
def test_index_matches_brute_force(seed: int) -> None:
    rng = random.Random(seed)
    vocabulary = [f"drug{n}" for n in range(rng.randint(3, 25))]
    records = random_records(rng, vocabulary, rng.randint(1, 60))
    lines = random_lines(rng, vocabulary, 200)
    index = InteractionIndex.build(parse_records(records))
    assert list(process_lines(lines, index)) == reference_output(records, lines)


def test_index_matches_brute_force_on_mini_dataset(
    mini_records: list[dict[str, Any]], mini_index: InteractionIndex
) -> None:
    vocabulary = ["foo", "bar", "baz", "qux", "alpha", "beta", "gamma", "delta", "other"]
    lines = random_lines(random.Random(99), vocabulary, 500)
    assert list(process_lines(lines, mini_index)) == reference_output(mini_records, lines)
