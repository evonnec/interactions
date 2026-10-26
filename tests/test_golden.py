"""Spec examples run against the real interactions.json, plus subprocess smoke tests."""

import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import RunCli

SPEC_INPUT = (
    "sildenafil tamsulosin valaciclovir\n"
    "sildenafil ibuprofen\n"
    "valaciclovir doxepin ticlopidine ibuprofen\n"
)
SPEC_OUTPUT = [
    "MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, "
    "resulting in symptomatic hypotension in some patients.",
    "No interaction",
    "MAJOR: Valaciclovir may decrease the excretion rate of Doxepin "
    "which could result in a higher serum level.",
]
RUN_MAIN = "from interactions.cli import main; main()"


@pytest.mark.usefixtures("real_dir")
def test_spec_examples_in_process(run_cli: RunCli) -> None:
    assert run_cli(SPEC_INPUT) == SPEC_OUTPUT


@pytest.mark.usefixtures("real_dir")
def test_real_data_tie_prints_one_line(run_cli: RunCli) -> None:
    assert run_cli("sildenafil nitroglycerin lovastatin\n") == [
        "MAJOR: Phosphodiesterase-5 (PDE5) inhibitors may potentiate the hypotensive "
        "effect of organic nitrates."
    ]


def test_spec_examples_subprocess(repo_root: Path) -> None:
    """Run the package in a fresh interpreter from the repo root."""
    result = subprocess.run(
        [sys.executable, "-c", RUN_MAIN],
        input=SPEC_INPUT,
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == SPEC_OUTPUT


def test_subprocess_without_interactions_json_fails(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", RUN_MAIN],
        input="a b\n",
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert result.returncode != 0
    assert "FileNotFoundError" in result.stderr


def test_real_input_one_output_line_per_input_line(repo_root: Path) -> None:
    """Every line of the committed input.txt yields exactly one output line (10,004 -> 10,004)."""
    input_text = (repo_root / "input.txt").read_text()
    input_lines = input_text.split("\n")[:-1]
    result = subprocess.run(
        [sys.executable, "-c", RUN_MAIN],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 0
    output_lines = result.stdout.split("\n")[:-1]
    assert len(input_lines) == 10_004
    assert len(output_lines) == len(input_lines)
