"""Domain types: severity levels, interaction records and drug-name normalization."""

import unicodedata
from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    """Interaction severity; a larger value is more severe. Names are the output labels."""

    MINOR = 1
    MODERATE = 2
    MAJOR = 3

    @classmethod
    def parse(cls, value: str) -> Severity:
        """Convert a severity string such as ``"major"`` (any case); raise ``ValueError``."""
        try:
            return cls[value.strip().upper()]
        except KeyError:
            raise ValueError(f"unknown severity {value!r}") from None


@dataclass(frozen=True, slots=True)
class Interaction:
    """A pairwise interaction. ``drugs`` holds the two normalized names, in file order."""

    drugs: tuple[str, str]
    severity: Severity
    description: str

    def format(self) -> str:
        """The output line for this interaction: ``MAJOR: <description>``."""
        return f"{self.severity.name}: {self.description}"


NO_INTERACTION = "No interaction"


def normalize(name: str) -> str:
    """Canonical form of a drug name, used for both the data file and the input.

    NFKC folds compatibility characters (e.g. full-width letters), then the name is stripped
    and case-folded.
    """
    return unicodedata.normalize("NFKC", name).strip().casefold()
