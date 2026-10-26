"""Pair index and line processing. Pure functions: no file or stdio access."""

from collections.abc import Iterable, Iterator, KeysView
from dataclasses import dataclass

from interactions.model import NO_INTERACTION, Interaction, normalize

type Pair = tuple[str, str]
# (negated severity, file position, interaction): the smallest tuple is the best interaction.
type Entry = tuple[int, int, Interaction]


@dataclass(frozen=True, slots=True)
class InteractionIndex:
    """Best interaction per unordered drug pair, built once from the data file."""

    pairs: dict[Pair, Entry]
    neighbors: dict[str, dict[str, Entry]]
    duplicates: tuple[Pair, ...]

    @property
    def known_drugs(self) -> KeysView[str]:
        """Every drug that appears in at least one interaction."""
        return self.neighbors.keys()

    @classmethod
    def build(cls, interactions: Iterable[Interaction]) -> InteractionIndex:
        """Index interactions (given in file order) by sorted drug pair.

        If a pair occurs more than once, the highest severity wins and, among equal severities,
        the earliest in the file. Pairs that occur more than once are reported in ``duplicates``.
        """
        pairs: dict[Pair, Entry] = {}
        duplicated: dict[Pair, None] = {}
        for position, interaction in enumerate(interactions):
            first, second = interaction.drugs
            key: Pair = (first, second) if first <= second else (second, first)
            candidate: Entry = (-interaction.severity, position, interaction)
            current = pairs.get(key)
            if current is None:
                pairs[key] = candidate
                continue
            duplicated[key] = None
            if candidate[:2] < current[:2]:
                pairs[key] = candidate
        neighbors: dict[str, dict[str, Entry]] = {}
        for (first, second), entry in pairs.items():
            neighbors.setdefault(first, {})[second] = entry
            neighbors.setdefault(second, {})[first] = entry
        return cls(pairs=pairs, neighbors=neighbors, duplicates=tuple(duplicated))

    def most_severe(self, drugs: Iterable[str]) -> Interaction | None:
        """The most severe interaction among normalized ``drugs``; ties go to the earliest record.

        Unknown and repeated drugs are ignored, and order does not matter. For each drug on the
        line only its partners that are also on the line are visited (a set intersection), so the
        cost is at most n^2/2 lookups for n distinct drugs (190 for 20) and does not grow with
        the number of interactions in the data.
        """
        on_line = set(drugs)
        best: Entry | None = None
        for drug in on_line:
            partners = self.neighbors.get(drug)
            if partners is None:
                continue
            for other in partners.keys() & on_line:
                entry = partners[other]
                if best is None or entry[:2] < best[:2]:
                    best = entry
        return None if best is None else best[2]


def parse_drugs(line: str) -> list[str]:
    """Split a line on any whitespace and normalize each drug name.

    A token that is empty after normalization (only invisible characters) is not a drug.
    """
    return [name for token in line.split() if (name := normalize(token))]


def format_result(interaction: Interaction | None) -> str:
    """``MAJOR: <description>`` or ``No interaction``."""
    return NO_INTERACTION if interaction is None else interaction.format()


def process_lines(lines: Iterable[str], index: InteractionIndex) -> Iterator[str]:
    """Yield exactly one result line (without newline) per input line, lazily and in order."""
    for line in lines:
        yield format_result(index.most_severe(parse_drugs(line)))
