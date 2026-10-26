"""Unit tests for the domain types and name normalization."""

import dataclasses

import pytest

from interactions.model import Interaction, Severity, normalize

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
