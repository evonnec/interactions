"""Unit tests for data loading and validation."""

import json
from pathlib import Path
from typing import Any

import pytest

from interactions.data import (
    DataError,
    bundled_data_path,
    load_bundled,
    load_file,
    parse_records,
)
from interactions.model import Interaction, Severity


def record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"drugs": ["a", "b"], "severity": "minor", "description": "A and b."}
    return {**base, **overrides}


class TestParseRecords:
    def test_valid_records_keep_file_order(self) -> None:
        result = parse_records([record(), record(drugs=["c", "d"], severity="MAJOR")])
        assert result == [
            Interaction(("a", "b"), Severity.MINOR, "A and b."),
            Interaction(("c", "d"), Severity.MAJOR, "A and b."),
        ]

    def test_empty_array_is_valid(self) -> None:
        assert parse_records([]) == []

    def test_drug_names_are_normalized(self) -> None:
        (result,) = parse_records([record(drugs=[" Sildenafil ", "TAMSULOSIN"])])
        assert result.drugs == ("sildenafil", "tamsulosin")

    def test_invisible_characters_in_drug_names_are_removed(self) -> None:
        (result,) = parse_records([record(drugs=["silde\u200bnafil", "\ufefftamsulosin\u00ad"])])
        assert result.drugs == ("sildenafil", "tamsulosin")

    @pytest.mark.parametrize("name", ["\u200b", "\ufeff\u00ad", " \u2060 "])
    def test_drug_name_empty_after_normalization_is_rejected(self, name: str) -> None:
        with pytest.raises(DataError, match="drug names must not be empty"):
            parse_records([record(drugs=[name, "b"])])

    def test_names_equal_after_removing_invisible_characters_are_not_distinct(self) -> None:
        with pytest.raises(DataError, match="distinct"):
            parse_records([record(drugs=["a\u200b", "a"])])

    @pytest.mark.parametrize(
        ("raw", "message"),
        [
            ({}, "top level must be an array"),
            ("text", "top level must be an array"),
            (None, "top level must be an array"),
            (["x"], "record 0: record must be an object"),
            (
                [record(), {"drugs": ["a", "b"], "description": "d"}],
                "record 1: missing key(s): severity",
            ),
            ([record(extra=1)], "record 0: unknown key(s): extra"),
            ([record(drugs=[])], "record 0: drugs must have exactly 2 distinct names, got 0"),
            ([record(drugs=["a"])], "record 0: drugs must have exactly 2 distinct names, got 1"),
            ([record(drugs=["a", "b", "c"])], "got 3"),
            ([record(drugs="ab")], "record 0: drugs must be an array of strings"),
            ([record(drugs=["a", 1])], "record 0: drugs must be an array of strings"),
            ([record(drugs=["a", ""])], "record 0: drug names must not be empty"),
            ([record(drugs=["a", "  "])], "record 0: drug names must not be empty"),
            ([record(drugs=["a b", "c"])], "record 0: drug names must not contain whitespace"),
            ([record(drugs=["a", "a"])], "record 0: drugs must be 2 distinct names"),
            ([record(drugs=["Sildenafil", "sildenafil"])], "got 'sildenafil' twice"),
            ([record(severity="contraindicated")], "record 0: unknown severity 'contraindicated'"),
            ([record(severity=3)], "record 0: severity must be a string"),
            ([record(description="")], "record 0: description must be a non-empty string"),
            ([record(description="  ")], "record 0: description must be a non-empty string"),
            ([record(description=None)], "record 0: description must be a non-empty string"),
        ],
    )
    def test_invalid_data_is_rejected(self, raw: object, message: str) -> None:
        with pytest.raises(DataError, match=message.replace("(", r"\(").replace(")", r"\)")):
            parse_records(raw)


class TestLoadFile:
    def test_loads_valid_file(self, mini_data_path: Path) -> None:
        interactions = load_file(mini_data_path)
        assert len(interactions) == 6
        assert interactions[0].drugs == ("foo", "bar")

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(DataError, match=r"data file not found: .*nope\.json"):
            load_file(tmp_path / "nope.json")

    def test_directory_is_unreadable(self, tmp_path: Path) -> None:
        with pytest.raises(DataError, match="cannot read data file"):
            load_file(tmp_path)

    def test_invalid_utf8(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_bytes(b"[\xff]")
        with pytest.raises(DataError, match="not valid UTF-8"):
            load_file(path)

    def test_truncated_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text('[{"drugs": ["a",', encoding="utf-8")
        with pytest.raises(DataError, match=r"bad.json: invalid JSON at line 1 col \d+"):
            load_file(path)

    def test_validation_error_names_file_and_record(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([record(), record(drugs=[])]), encoding="utf-8")
        with pytest.raises(DataError, match=r"bad.json: record 1: drugs must have exactly 2"):
            load_file(path)


class TestBundledData:
    """Shipped-data contract tests."""

    def test_bundled_file_exists_and_is_valid(self) -> None:
        assert bundled_data_path().is_file()
        assert len(load_bundled()) == 152

    def test_bundled_copy_matches_repo_root_copy(self, repo_root: Path) -> None:
        root_copy = repo_root / "interactions.json"
        assert root_copy.read_bytes() == bundled_data_path().read_bytes()
