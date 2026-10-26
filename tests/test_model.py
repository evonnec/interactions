"""Unit tests for the domain types and name normalization."""

import dataclasses

import pytest

from interactions.model import IGNORABLE, Interaction, Severity, normalize

SAMPLE = Interaction(drugs=("a", "b"), severity=Severity.MAJOR, description="A and b.")


class TestSeverity:
    def test_ordering(self) -> None:
        assert Severity.MAJOR > Severity.MODERATE > Severity.MINOR

    def test_names_are_output_labels(self) -> None:
        assert [s.name for s in Severity] == ["MINOR", "MODERATE", "MAJOR"]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("major", Severity.MAJOR),
            ("MODERATE", Severity.MODERATE),
            ("Minor", Severity.MINOR),
            (" major ", Severity.MAJOR),
        ],
    )
    def test_parse(self, text: str, expected: Severity) -> None:
        assert Severity.parse(text) is expected

    @pytest.mark.parametrize("text", ["severe", "", "contraindicated"])
    def test_parse_unknown_raises_value_error(self, text: str) -> None:
        with pytest.raises(ValueError, match="unknown severity"):
            Severity.parse(text)


class TestInteraction:
    def test_is_frozen_and_slotted(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            SAMPLE.description = "changed"  # type: ignore[misc]
        assert not hasattr(SAMPLE, "__dict__")

    def test_format(self) -> None:
        assert SAMPLE.format() == "MAJOR: A and b."


class TestNormalize:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("sildenafil", "sildenafil"),
            ("Sildenafil", "sildenafil"),
            ("SILDENAFIL", "sildenafil"),
            ("  sildenafil\t", "sildenafil"),
            ("\uff33ildenafil", "sildenafil"),  # full-width S folds under NFKC
            ("Stra\u00dfe", "strasse"),  # casefold, not just lower
        ],
    )
    def test_normalize(self, raw: str, expected: str) -> None:
        assert normalize(raw) == expected


class TestNormalizeInvisible:
    """Default-ignorable characters are removed, on the data side and the input side alike (#47)."""

    @pytest.mark.parametrize(
        "char",
        [
            "\u00ad",
            "\u200b",
            "\u200c",
            "\u200d",
            "\u200f",
            "\u2060",
            "\u2064",
            "\ufe0f",
            "\ufeff",
            "\U000e0020",
            "\U000e0100",
        ],
    )
    def test_removed_anywhere(self, char: str) -> None:
        assert normalize(f"{char}sil{char}den{char}afil{char}") == "sildenafil"

    def test_every_ignorable_code_point_is_invisible_and_removed(self) -> None:
        for code in IGNORABLE:
            assert normalize(f"a{chr(code)}b") == "ab", hex(code)

    def test_only_invisible_characters_normalize_to_empty(self) -> None:
        assert normalize("\u200b\ufeff\u00ad") == ""

    def test_removal_precedes_composition(self) -> None:
        assert normalize("e\u034f\u0301") == normalize("\u00e9") == "\u00e9"

    def test_removal_after_nfkc(self) -> None:
        assert normalize("a\u3164b") == "ab"  # NFKC maps the Hangul filler to another ignorable

    def test_visible_format_characters_are_kept(self) -> None:
        assert normalize("a\u0600b") == "a\u0600b"

    def test_ascii_is_unchanged(self) -> None:
        assert normalize(" Sildenafil-X ") == "sildenafil-x"
