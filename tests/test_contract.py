"""End-to-end CLI contract tests: bytes on STDIN in, bytes on STDOUT out, via a subprocess.

These run against the dataset bundled in the package (a shipped-data contract) from an empty
working directory, so they also prove the CLI does not depend on the repository layout.
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import interactions
from interactions.data import bundled_data_path
from tests.conftest import DATA_DIR, REPO_ROOT, RunProcess
from tests.reference import reference_output

GRAMMAR = re.compile(r"^((MAJOR|MODERATE|MINOR): .+|No interaction)$")


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_input", REPO_ROOT / "scripts/gen_input.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def shipped_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = json.loads(bundled_data_path().read_text(encoding="utf-8"))
    return records


class TestGolden:
    def test_spec_examples_byte_for_byte(self, run_process: RunProcess) -> None:
        expected = (DATA_DIR / "spec_examples.out").read_bytes()
        result = subprocess.run(
            [sys.executable, "-m", "interactions"],
            input=(DATA_DIR / "spec_examples.in").read_bytes(),
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout == expected
        assert result.stderr == b""

    def test_tie_prints_only_first_record_in_file(self, run_process: RunProcess) -> None:
        result = run_process("sildenafil nitroglycerin lovastatin\n")
        assert result.stdout == (
            "MAJOR: Phosphodiesterase-5 (PDE5) inhibitors may potentiate the hypotensive "
            "effect of organic nitrates.\n"
        )


class TestOneLinePerInput:
    @pytest.mark.parametrize(
        "text",
        [
            "sildenafil tamsulosin\n",
            "\n",
            "   \n",
            "\n\n\n",
            "sildenafil",  # no trailing newline
            "sildenafil nitroglycerin lovastatin\nsildenafil tamsulosin\n",
            "sildenafil tamsulosin\r\nsildenafil ibuprofen\r\n",
            "a b c d e f g h i j k l m n o p q r s t\n",
        ],
    )
    def test_line_count_matches(self, run_process: RunProcess, text: str) -> None:
        result = run_process(text)
        assert result.returncode == 0
        assert len(result.stdout.splitlines()) == len(text.splitlines())

    @pytest.mark.parametrize(
        "separator",
        ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"],
        ids=["VT", "FF", "FS", "GS", "RS", "NEL", "LS", "PS"],
    )
    def test_exotic_line_breaks_inside_a_line_do_not_split_it(
        self, run_process: RunProcess, separator: str
    ) -> None:
        stdin = f"sildenafil{separator}tamsulosin\nsildenafil ibuprofen\n"
        result = run_process(stdin)
        assert result.stdout.split("\n") == [
            "MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, "
            "resulting in symptomatic hypotension in some patients.",
            "No interaction",
            "",
        ]

    def test_empty_stdin_gives_empty_output(self, run_process: RunProcess) -> None:
        result = run_process("")
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.fixture(scope="module")
def generated() -> list[str]:
    generator = load_generator()
    drugs = generator.dataset_drugs(bundled_data_path())
    lines: list[str] = generator.generate(drugs, lines=10_000, drugs_per_line=20, seed=7)
    return lines


class TestRandomInput:
    """A seeded 10,000 x 20 input generated at test time, checked against the reference."""

    def test_invariants_and_reference(
        self,
        run_process: RunProcess,
        generated: list[str],
        shipped_records: list[dict[str, Any]],
    ) -> None:
        result = run_process("\n".join(generated) + "\n")
        assert result.returncode == 0
        assert result.stderr == ""
        output = result.stdout.splitlines()
        assert len(output) == len(generated) == 10_000
        assert all(GRAMMAR.match(line) for line in output)
        assert any(line != "No interaction" for line in output)
        assert output == reference_output(shipped_records, generated)


class TestMatchingRules:
    @pytest.mark.parametrize(
        "line",
        [
            "sildenafil tamsulosin",
            "Sildenafil Tamsulosin",
            "SILDENAFIL TAMSULOSIN",
            "tamsulosin sildenafil",
            "  sildenafil \t tamsulosin  ",
            "sildenafil sildenafil tamsulosin",
            "sildenafil tamsulosin unknowndrug",
        ],
    )
    def test_variants_give_identical_output(self, run_process: RunProcess, line: str) -> None:
        baseline = run_process("sildenafil tamsulosin\n").stdout
        assert baseline.startswith("MODERATE: ")
        assert run_process(line + "\n").stdout == baseline


class TestExitCodesAndStreams:
    def test_works_from_any_directory_without_data_file(
        self, run_process: RunProcess, tmp_path: Path
    ) -> None:
        result = run_process("sildenafil tamsulosin\n", cwd=tmp_path)
        assert result.returncode == 0
        assert result.stdout.startswith("MODERATE: Sildenafil")

    def test_cwd_data_file_takes_precedence(self, run_process: RunProcess, tmp_path: Path) -> None:
        (tmp_path / "interactions.json").write_text(
            '[{"drugs": ["x", "y"], "severity": "major", "description": "Local."}]',
            encoding="utf-8",
        )
        assert run_process("x y\n", cwd=tmp_path).stdout == "MAJOR: Local.\n"

    def test_data_flag(self, run_process: RunProcess, mini_data_path: Path) -> None:
        result = run_process("foo bar\n", "--data", str(mini_data_path))
        assert result.stdout == "MODERATE: Foo and bar moderate.\n"

    def test_help(self, run_process: RunProcess) -> None:
        result = run_process("", "--help")
        assert result.returncode == 0
        assert "usage: interactions" in result.stdout
        assert result.stderr == ""

    def test_help_does_not_wait_for_stdin(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "interactions", "--help"],
            stdin=subprocess.PIPE,  # open and never written to or closed by the test
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0

    def test_version(self, run_process: RunProcess) -> None:
        result = run_process("", "--version")
        assert result.stdout == f"interactions {interactions.__version__}\n"

    def test_bad_flag_is_exit_2(self, run_process: RunProcess) -> None:
        result = run_process("", "--nope")
        assert result.returncode == 2
        assert result.stdout == ""
        assert "usage:" in result.stderr

    def test_missing_data_file(self, run_process: RunProcess) -> None:
        result = run_process("", "--data", "missing.json")
        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr == "error: data file not found: missing.json\n"
        assert "Traceback" not in result.stderr

    def test_malformed_data_file(self, run_process: RunProcess, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("{", encoding="utf-8")
        result = run_process("a b\n", "--data", "bad.json", cwd=tmp_path)
        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.startswith("error: bad.json: invalid JSON")
        assert "Traceback" not in result.stderr

    def test_closed_stdout_has_no_traceback(self, tmp_path: Path) -> None:
        big_input = tmp_path / "big.txt"
        big_input.write_text("sildenafil tamsulosin\n" * 20_000, encoding="utf-8")
        with big_input.open("rb") as stdin:
            process = subprocess.Popen(
                [sys.executable, "-m", "interactions"],
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tmp_path,
            )
            assert process.stdout is not None
            assert process.stderr is not None
            first = process.stdout.readline()
            process.stdout.close()  # like `| head -1`
            stderr = process.stderr.read()
            process.stderr.close()
            code = process.wait(timeout=60)
        assert first.startswith(b"MODERATE: Sildenafil")
        assert code == 0
        assert stderr == b""


class TestByteOrderMark:
    """A leading UTF-8 BOM (issue #31) must not change the output; later ones are not stripped."""

    BOM = b"\xef\xbb\xbf"

    @staticmethod
    def run(stdin: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "-m", "interactions"], input=stdin, capture_output=True, check=False
        )

    @pytest.mark.parametrize("line", [b"sildenafil tamsulosin", b"sildenafil nitroglycerin"])
    def test_leading_bom_is_ignored(self, line: bytes) -> None:
        with_bom = self.run(self.BOM + line + b"\n")
        without = self.run(line + b"\n")
        assert with_bom.stdout == without.stdout != b"No interaction\n"
        assert (with_bom.returncode, with_bom.stderr) == (0, b"")

    @pytest.mark.parametrize(
        ("stdin", "expected"),
        [
            (BOM, b""),  # a BOM alone is an empty stream
            (BOM + b"\n", b"No interaction\n"),  # BOM then a blank line
            (BOM + b" sildenafil tamsulosin\n", None),
            (BOM + b"sildenafil tamsulosin\n", None),
            # only the first BOM of the stream is dropped; later ones are ordinary characters
            (b"x\n" + BOM + b"sildenafil tamsulosin\n", b"No interaction\nNo interaction\n"),
            (BOM + BOM + b"sildenafil tamsulosin\n", b"No interaction\n"),
        ],
    )
    def test_only_one_leading_bom_is_dropped(self, stdin: bytes, expected: bytes | None) -> None:
        result = self.run(stdin)
        assert result.returncode == 0
        if expected is None:
            assert result.stdout.startswith(b"MODERATE: Sildenafil")
        else:
            assert result.stdout == expected
