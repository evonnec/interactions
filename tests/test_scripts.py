"""Tests for the helper scripts (not part of the installed package) and module entry points."""

import runpy
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, RunProcess
from tests.test_contract import load_generator

DATA = REPO_ROOT / "src" / "interactions" / "data" / "interactions.json"


class TestGenInput:
    def test_defaults_respect_spec_bounds(self, capsys: pytest.CaptureFixture[str]) -> None:
        generator = load_generator()
        assert generator.main([]) == 0
        lines = capsys.readouterr().out.splitlines()
        assert 1 <= len(lines) <= 10_000
        assert all(1 <= len(line.split()) <= 20 for line in lines)

    def test_is_deterministic_for_a_seed(self) -> None:
        generator = load_generator()
        drugs = generator.dataset_drugs(DATA)
        first = generator.generate(drugs, lines=50, drugs_per_line=5, seed=3)
        assert first == generator.generate(drugs, lines=50, drugs_per_line=5, seed=3)
        assert first != generator.generate(drugs, lines=50, drugs_per_line=5, seed=4)

    def test_lines_have_distinct_drugs_from_the_dataset(self) -> None:
        generator = load_generator()
        drugs = set(generator.dataset_drugs(DATA))
        for line in generator.generate(sorted(drugs), lines=20, drugs_per_line=20, seed=1):
            tokens = line.split()
            assert len(set(tokens)) == 20
            assert set(tokens) <= drugs

    @pytest.mark.parametrize(("lines", "per_line"), [(0, 5), (10_001, 5), (5, 0), (5, 21)])
    def test_out_of_bounds_is_rejected(self, lines: int, per_line: int) -> None:
        generator = load_generator()
        with pytest.raises(ValueError, match="must be between"):
            generator.generate(["a"] * 30, lines=lines, drugs_per_line=per_line, seed=0)

    def test_cli_rejects_bad_args(self) -> None:
        generator = load_generator()
        with pytest.raises(SystemExit) as stop:
            generator.main(["--lines", "0"])
        assert stop.value.code == 2


class TestEntryPoints:
    def test_python_dash_m_interactions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["interactions", "--version"])
        with pytest.raises(SystemExit) as stop:
            runpy.run_module("interactions", run_name="__main__")
        assert stop.value.code == 0

    def test_input_txt_one_output_line_per_input_line(
        self, run_process: RunProcess, repo_root: Path
    ) -> None:
        text = (repo_root / "input.txt").read_text(encoding="utf-8")
        result = run_process(text)
        assert result.returncode == 0
        assert len(text.split("\n")[:-1]) == 10_004
        assert len(result.stdout.split("\n")[:-1]) == 10_004
