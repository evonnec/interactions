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


# Unicode Default_Ignorable_Code_Point (DerivedCoreProperties.txt, Unicode 16): characters that
# are invisible in running text, such as U+FEFF (BOM / zero width no-break space), U+200B-U+200F
# (zero width space, ZWNJ, ZWJ, directional marks), U+00AD (soft hyphen), U+2060-U+206F (word
# joiner and invisible operators), variation selectors and the Hangul fillers. They are not
# whitespace, so ``str.split`` keeps them inside a token, and NFKC does not remove them; Unicode's
# own NFKC_Casefold matching form drops them for the same reason. Visible Cf characters that are
# not default ignorable (for example U+0600 ARABIC NUMBER SIGN) are deliberately kept.
_IGNORABLE_RANGES = (
    (0x00AD, 0x00AD),
    (0x034F, 0x034F),
    (0x061C, 0x061C),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)
IGNORABLE: dict[int, None] = {
    code: None for low, high in _IGNORABLE_RANGES for code in range(low, high + 1)
}


def normalize(name: str) -> str:
    """Canonical form of a drug name, used for both the data file and the input.

    Invisible default-ignorable characters are removed (before NFKC, so they cannot block a
    composition, and after, in case a compatibility mapping produced one), NFKC folds
    compatibility characters (e.g. full-width letters), then the name is stripped and case-folded.
    The result can be empty (a token that consisted only of invisible characters).
    """
    if not name.isascii():
        name = unicodedata.normalize("NFKC", name.translate(IGNORABLE)).translate(IGNORABLE)
    return name.strip().casefold()
