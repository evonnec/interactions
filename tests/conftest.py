"""Shared fixtures for the test suite."""

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from interactions.data import load_bundled, load_file
from interactions.index import InteractionIndex

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
REPO_ROOT = TESTS_DIR.parent
MINI_DATA = DATA_DIR / "mini_interactions.json"

type RunProcess = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test from an empty temp dir so hidden CWD dependence fails immediately."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def mini_data_path() -> Path:
    return MINI_DATA


@pytest.fixture
def mini_records() -> list[dict[str, Any]]:
    """The small hand-made dataset (ties, all severities) as parsed JSON."""
    records: list[dict[str, Any]] = json.loads(MINI_DATA.read_text(encoding="utf-8"))
    return records


@pytest.fixture
def mini_index() -> InteractionIndex:
    return InteractionIndex.build(load_file(MINI_DATA))


@pytest.fixture(scope="session")
def spec_index() -> InteractionIndex:
    """Index of the dataset shipped in the package (for shipped-data contract tests only)."""
    return InteractionIndex.build(load_bundled())


@pytest.fixture
def run_process() -> RunProcess:
    """Run ``python -m interactions`` in a subprocess; returns the CompletedProcess (text mode)."""

    def _run(
        stdin: str = "", *args: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "interactions", *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=cwd,
            check=False,
        )

    return _run
