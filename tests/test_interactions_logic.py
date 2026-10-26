"""Unit tests for severity parsing, loading and matching."""

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from interactions.lib.interactions_logic import (
    Interaction,
    Severity,
    find_interactions,
    get_interactions,
    load_interactions_from_list,
)

SILDENAFIL_TAMSULOSIN = Interaction(
    drugs=("sildenafil", "tamsulosin"),
    severity=Severity.MODERATE,
    description="Sildenafil and tamsulosin.",
)


class TestSeverity:
    def test_ordering(self) -> None:
        assert Severity.MAJOR > Severity.MODERATE > Severity.MINOR

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("major", Severity.MAJOR),
            ("moderate", Severity.MODERATE),
            ("minor", Severity.MINOR),
            ("MAJOR", Severity.MAJOR),
            ("Moderate", Severity.MODERATE),
        ],
    )
    def test_parse(self, text: str, expected: Severity) -> None:
        assert Severity.parse(text) is expected

    @pytest.mark.parametrize("text", ["severe", "", " major"])
    def test_parse_unknown_raises(self, text: str) -> None:
        with pytest.raises(KeyError):
            Severity.parse(text)

    def test_names_are_output_labels(self) -> None:
        assert [s.name for s in Severity] == ["MINOR", "MODERATE", "MAJOR"]


class TestInteraction:
    def test_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            SILDENAFIL_TAMSULOSIN.description = "changed"  # type: ignore[misc]


class TestLoadInteractionsFromList:
    def test_converts_items(self, raw_fixture_interactions: list[dict[str, Any]]) -> None:
        result = load_interactions_from_list(raw_fixture_interactions)
        assert len(result) == len(raw_fixture_interactions)
        assert result[0] == Interaction(
            drugs=("foo", "bar"), severity=Severity.MODERATE, description="Foo and bar moderate."
        )
        assert [i.severity for i in result] == [
            Severity.MODERATE,
            Severity.MINOR,
            Severity.MAJOR,
            Severity.MAJOR,
            Severity.MAJOR,
            Severity.MODERATE,
        ]

    def test_empty(self) -> None:
        assert load_interactions_from_list([]) == []

    def test_accepts_any_iterable(self) -> None:
        raw = ({"drugs": ["a", "b"], "severity": "minor", "description": "d"} for _ in range(2))
        assert len(load_interactions_from_list(raw)) == 2

    @pytest.mark.parametrize("missing", ["drugs", "severity", "description"])
    def test_missing_key_raises(self, missing: str) -> None:
        item = {"drugs": ["a", "b"], "severity": "minor", "description": "d"}
        del item[missing]
        with pytest.raises(KeyError):
            load_interactions_from_list([item])

    def test_unknown_severity_raises(self) -> None:
        item = {"drugs": ["a", "b"], "severity": "critical", "description": "d"}
        with pytest.raises(KeyError):
            load_interactions_from_list([item])


class TestFindInteractions:
    @pytest.mark.parametrize(
        ("drugs", "expected"),
        [
            (set(), []),
            ({"acetaminophen"}, []),
            ({"sildenafil"}, []),
            ({"tamsulosin"}, []),
            ({"sildenafil", "tamsulosin"}, [SILDENAFIL_TAMSULOSIN]),
            ({"sildenafil", "tamsulosin", "other"}, [SILDENAFIL_TAMSULOSIN]),
            ({"sildenafil", "acetaminophen"}, []),
            ({"Sildenafil", "Tamsulosin"}, []),  # matching is case sensitive
        ],
    )
    def test_matching(self, drugs: set[str], expected: list[Interaction]) -> None:
        assert find_interactions([SILDENAFIL_TAMSULOSIN], drugs) == expected

    def test_no_interactions(self) -> None:
        assert find_interactions([], {"a", "b"}) == []

    def test_multiple_matches_keep_file_order(
        self, raw_fixture_interactions: list[dict[str, Any]]
    ) -> None:
        interactions = load_interactions_from_list(raw_fixture_interactions)
        result = find_interactions(interactions, {"alpha", "beta", "gamma", "delta"})
        assert [i.description for i in result] == [
            "Alpha and beta major (first).",
            "Alpha and gamma major (second).",
            "Alpha and delta moderate.",
        ]

    def test_frozenset_input(self) -> None:
        result = find_interactions([SILDENAFIL_TAMSULOSIN], frozenset({"sildenafil", "tamsulosin"}))
        assert result == [SILDENAFIL_TAMSULOSIN]

    def test_empty_drug_tuple_matches_every_line(self) -> None:
        # Current behavior: the empty set is a subset of any set of drugs.
        everything = Interaction(drugs=(), severity=Severity.MINOR, description="x")
        assert find_interactions([everything], {"a"}) == [everything]


class TestRanking:
    """CLI ranking is a stable sort by descending severity."""

    def test_same_severity_keeps_file_order(self) -> None:
        items = [
            Interaction((), severity, f"{n} {severity.name.lower()}")
            for n, severity in [
                (1, Severity.MAJOR),
                (1, Severity.MODERATE),
                (1, Severity.MINOR),
                (2, Severity.MAJOR),
                (2, Severity.MODERATE),
                (2, Severity.MINOR),
            ]
        ]
        result = sorted(items, key=lambda i: i.severity, reverse=True)
        assert [i.description for i in result] == [
            "1 major",
            "2 major",
            "1 moderate",
            "2 moderate",
            "1 minor",
            "2 minor",
        ]


class TestGetInteractions:
    def test_reads_json_from_cwd(self, fixture_dir: Path) -> None:
        result = get_interactions({"foo", "bar"})
        assert [i.description for i in result] == ["Foo and bar moderate."]

    def test_no_match(self, fixture_dir: Path) -> None:
        assert get_interactions({"nothing"}) == []

    def test_cwd_file_is_what_is_read(self, fixture_dir: Path) -> None:
        (fixture_dir / "interactions.json").write_text(
            '[{"drugs": ["x", "y"], "severity": "minor", "description": "custom"}]'
        )
        assert [i.description for i in get_interactions({"x", "y"})] == ["custom"]

    def test_missing_file_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            get_interactions({"a"})

    def test_spec_example_against_real_file(self, real_dir: Path) -> None:
        result = get_interactions({"sildenafil", "tamsulosin", "valaciclovir"})
        assert [i.severity for i in result] == [Severity.MODERATE]
        assert result[0].description.startswith("Sildenafil may potentiate")
