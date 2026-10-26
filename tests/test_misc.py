"""Tests for the package metadata and the sample-input generator."""

import pytest

import interactions
from interactions import make_input_file


def test_version_is_a_string() -> None:
    assert isinstance(interactions.__version__, str)
    assert interactions.__version__


def test_make_input_file_prints_1000_identical_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_input_file.main()
    lines = capsys.readouterr().out.splitlines()
    assert lines == [make_input_file.STRING_OF_DRUGS] * 1000
    assert len(make_input_file.STRING_OF_DRUGS.split()) == 20
