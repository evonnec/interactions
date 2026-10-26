"""Unit tests for the pair index, line parsing and result formatting (no I/O)."""

from collections.abc import Iterator

import pytest

from interactions.index import InteractionIndex, format_result, parse_drugs, process_lines
from interactions.model import Interaction, Severity


def make(first: str, second: str, severity: Severity, text: str) -> Interaction:
    return Interaction((first, second), severity, text)


class TestBuild:
    def test_pair_key_is_order_free(self) -> None:
        index = InteractionIndex.build([make("b", "a", Severity.MINOR, "x")])
        assert list(index.pairs) == [("a", "b")]
        assert index.known_drugs == {"a", "b"}

    def test_duplicate_pair_higher_severity_wins(self) -> None:
        index = InteractionIndex.build(
            [make("a", "b", Severity.MINOR, "first"), make("b", "a", Severity.MAJOR, "second")]
        )
        assert index.duplicates == (("a", "b"),)
        assert index.most_severe(["a", "b"]) == make("b", "a", Severity.MAJOR, "second")

    def test_duplicate_pair_equal_severity_earliest_wins(self) -> None:
        index = InteractionIndex.build(
            [make("a", "b", Severity.MAJOR, "first"), make("b", "a", Severity.MAJOR, "second")]
        )
        best = index.most_severe(["b", "a"])
        assert best is not None
        assert best.description == "first"

    def test_duplicates_reported_once_per_pair(self) -> None:
        index = InteractionIndex.build([make("a", "b", Severity.MINOR, str(n)) for n in range(3)])
        assert index.duplicates == (("a", "b"),)

    def test_no_duplicates_for_distinct_pairs(self, mini_index: InteractionIndex) -> None:
        assert mini_index.duplicates == ()


class TestMostSevere:
    def test_no_match(self, mini_index: InteractionIndex) -> None:
        assert mini_index.most_severe(["foo"]) is None
        assert mini_index.most_severe([]) is None
        assert mini_index.most_severe(["beta", "gamma"]) is None  # known drugs, no pair record

    def test_single_match(self, mini_index: InteractionIndex) -> None:
        best = mini_index.most_severe(["foo", "baz"])
        assert best is not None
        assert best.description == "Foo and baz minor."

    def test_order_on_line_does_not_matter(self, mini_index: InteractionIndex) -> None:
        assert mini_index.most_severe(["foo", "bar"]) == mini_index.most_severe(["bar", "foo"])

    def test_mixed_severities_pick_highest(self, mini_index: InteractionIndex) -> None:
        best = mini_index.most_severe(["foo", "bar", "baz", "qux"])
        assert best is not None
        assert best.description == "Foo and qux major."

    def test_tie_goes_to_earliest_in_file_not_line_order(
        self, mini_index: InteractionIndex
    ) -> None:
        # alpha/beta (record 2) precedes alpha/gamma (record 3); list gamma first on the line.
        for line in (["gamma", "alpha", "beta"], ["beta", "alpha", "gamma"]):
            best = mini_index.most_severe(line)
            assert best is not None
            assert best.description == "Alpha and beta major (first)."

    def test_lower_severity_tie_does_not_beat_higher(self) -> None:
        index = InteractionIndex.build(
            [
                make("a", "b", Severity.MINOR, "minor 1"),
                make("a", "c", Severity.MINOR, "minor 2"),
                make("a", "d", Severity.MAJOR, "major"),
            ]
        )
        best = index.most_severe(["a", "b", "c", "d"])
        assert best is not None
        assert best.description == "major"

    def test_repeated_and_unknown_drugs_are_ignored(self, mini_index: InteractionIndex) -> None:
        best = mini_index.most_severe(["zzz", "foo", "foo", "yyy", "bar"])
        assert best is not None
        assert best.description == "Foo and bar moderate."

    def test_pair_must_be_complete(self, mini_index: InteractionIndex) -> None:
        assert mini_index.most_severe(["alpha"]) is None


class TestParseDrugs:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("foo bar\n", ["foo", "bar"]),
            ("  Foo \t BAR \r\n", ["foo", "bar"]),
            ("foo\x0cbar", ["foo", "bar"]),  # form feed separates, never splits the line
            ("foo\u2028bar", ["foo", "bar"]),
            ("", []),
            ("   \n", []),
            ("sil\u200bdenafil \u200b \ufeff tamsulosin\u00ad", ["sildenafil", "tamsulosin"]),
        ],
    )
    def test_parse_drugs(self, line: str, expected: list[str]) -> None:
        assert parse_drugs(line) == expected


class TestFormatResult:
    def test_none(self) -> None:
        assert format_result(None) == "No interaction"

    def test_interaction(self) -> None:
        assert format_result(make("a", "b", Severity.MODERATE, "Text.")) == "MODERATE: Text."


class TestProcessLines:
    def test_one_result_per_line_in_order(self, mini_index: InteractionIndex) -> None:
        lines = ["foo bar\n", "\n", "alpha beta gamma\n", "foo baz", "nothing here\n"]
        assert list(process_lines(lines, mini_index)) == [
            "MODERATE: Foo and bar moderate.",
            "No interaction",
            "MAJOR: Alpha and beta major (first).",
            "MINOR: Foo and baz minor.",
            "No interaction",
        ]

    def test_is_lazy(self, mini_index: InteractionIndex) -> None:
        consumed: list[str] = []

        def source() -> Iterator[str]:
            for line in ("foo bar", "foo baz"):
                consumed.append(line)
                yield line

        results = process_lines(source(), mini_index)
        assert consumed == []
        next(results)
        assert consumed == ["foo bar"]

    def test_case_insensitive(self, mini_index: InteractionIndex) -> None:
        assert list(process_lines(["FOO Bar"], mini_index)) == ["MODERATE: Foo and bar moderate."]
