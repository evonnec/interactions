"""Loading and matching of drug-drug interactions."""

import json
from collections.abc import Iterable, Set
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

type RawInteraction = dict[str, Any]
type Drugs = Set[str]

INTERACTIONS_FILE = Path("interactions.json")


class Severity(IntEnum):
    """Interaction severity; a larger value is more severe."""

    MINOR = 1
    MODERATE = 2
    MAJOR = 3

    @classmethod
    def parse(cls, value: str) -> Severity:
        """Convert a severity string from the JSON file, e.g. ``"major"``."""
        return cls[value.upper()]


@dataclass(frozen=True, slots=True)
class Interaction:
    drugs: tuple[str, ...]
    severity: Severity
    description: str


def load_interactions_from_list(json_list: Iterable[RawInteraction]) -> list[Interaction]:
    return [
        Interaction(
            drugs=tuple(item["drugs"]),
            severity=Severity.parse(item["severity"]),
            description=item["description"],
        )
        for item in json_list
    ]


def find_interactions(interactions: Iterable[Interaction], drugs: Drugs) -> list[Interaction]:
    return [i for i in interactions if set(i.drugs) <= drugs]


def get_interactions(drugs: Drugs) -> list[Interaction]:
    json_list = json.loads(INTERACTIONS_FILE.read_text())
    interactions = load_interactions_from_list(json_list)
    return find_interactions(interactions=interactions, drugs=drugs)
