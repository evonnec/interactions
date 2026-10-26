"""Shared fixtures for the test suite."""

import io
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from interactions import cli

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent

type RunCli = Callable[[str], list[str]]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def raw_fixture_interactions() -> list[dict[str, Any]]:
    """The fixture dataset as parsed JSON."""
    data: list[dict[str, Any]] = json.loads((FIXTURES_DIR / "interactions.json").read_text())
    return data


@pytest.fixture
def fixture_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp dir holding the fixture interactions.json, made the CWD."""
    shutil.copy(FIXTURES_DIR / "interactions.json", tmp_path / "interactions.json")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def real_dir(monkeypatch: pytest.MonkeyPatch) -> Path:
    """The repository root (with the real interactions.json) as the CWD."""
    monkeypatch.chdir(REPO_ROOT)
    return REPO_ROOT


@pytest.fixture
def run_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> RunCli:
    """Run ``cli.main()`` with the given STDIN text; return stdout split into lines."""

    def _run(stdin_text: str) -> list[str]:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
        cli.main()
        return capsys.readouterr().out.splitlines()

    return _run
