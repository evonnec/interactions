"""In-process tests of ``interactions.cli.main`` (argument handling, data resolution, errors)."""

import io
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

import interactions
from interactions import cli
from interactions.data import load_file
from interactions.model import Interaction

type Invoke = Callable[..., tuple[int, str, str]]

FOO_BAR = "MODERATE: Foo and bar moderate."


@pytest.fixture
def invoke(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> Invoke:
    """Call ``cli.main(argv)`` with STDIN text; return (exit code, stdout, stderr)."""

    def _invoke(stdin: str, argv: Sequence[str] = ()) -> tuple[int, str, str]:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
        code = cli.main(list(argv))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _invoke


class TestSuccess:
    def test_prints_one_line_per_input_line(self, invoke: Invoke, mini_data_path: Path) -> None:
        code, out, err = invoke("foo bar\n\nalpha beta gamma\n", ["--data", str(mini_data_path)])
        assert (code, err) == (0, "")
        assert out == f"{FOO_BAR}\nNo interaction\nMAJOR: Alpha and beta major (first).\n"

    def test_empty_stdin_prints_nothing(self, invoke: Invoke, mini_data_path: Path) -> None:
        assert invoke("", ["--data", str(mini_data_path)]) == (0, "", "")

    def test_no_trailing_newline_and_crlf(self, invoke: Invoke, mini_data_path: Path) -> None:
        _, out, _ = invoke("foo bar\r\nfoo bar", ["--data", str(mini_data_path)])
        assert out == f"{FOO_BAR}\n{FOO_BAR}\n"

    def test_data_is_loaded_once(
        self, invoke: Invoke, mini_data_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[Path] = []

        def counting(path: Path) -> list[Interaction]:
            calls.append(path)
            return load_file(path)

        monkeypatch.setattr(cli, "load_file", counting)
        invoke("foo bar\n" * 50, ["--data", str(mini_data_path)])
        assert calls == [mini_data_path]


class TestDataResolution:
    def test_cwd_file_used_when_present(self, invoke: Invoke, mini_data_path: Path) -> None:
        shutil.copy(mini_data_path, Path("interactions.json"))
        assert invoke("foo bar\n")[1] == f"{FOO_BAR}\n"

    def test_bundled_data_used_when_no_cwd_file(self, invoke: Invoke) -> None:
        assert not Path("interactions.json").exists()
        _, out, err = invoke("sildenafil tamsulosin\n")
        assert err == ""
        assert out.startswith("MODERATE: Sildenafil may potentiate")

    def test_data_flag_overrides_cwd_file(self, invoke: Invoke, mini_data_path: Path) -> None:
        Path("interactions.json").write_text("[]", encoding="utf-8")
        assert invoke("foo bar\n", ["--data", str(mini_data_path)])[1] == f"{FOO_BAR}\n"

    def test_data_flag_overrides_bundled(self, invoke: Invoke, tmp_path: Path) -> None:
        other = tmp_path / "other.json"
        other.write_text(
            '[{"drugs": ["sildenafil", "tamsulosin"], "severity": "minor",'
            ' "description": "Mine."}]',
            encoding="utf-8",
        )
        assert invoke("sildenafil tamsulosin\n", ["--data", str(other)])[1] == "MINOR: Mine.\n"


class TestInformationalFlags:
    def test_help_does_not_read_stdin(
        self, invoke: Invoke, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, _ = invoke("foo bar\n", ["--help"])
        assert code == 0
        assert "usage: interactions" in out
        assert "--data" in out
        assert "Exit codes" in out

    def test_version(self, invoke: Invoke) -> None:
        assert invoke("", ["--version"]) == (0, f"interactions {interactions.__version__}\n", "")

    def test_unknown_flag_is_a_usage_error(self, invoke: Invoke) -> None:
        code, out, err = invoke("foo bar\n", ["--bogus"])
        assert (code, out) == (2, "")
        assert "unrecognized arguments: --bogus" in err

    def test_positional_argument_is_a_usage_error(self, invoke: Invoke) -> None:
        code, out, err = invoke("", ["input.txt"])
        assert (code, out) == (2, "")
        assert "unrecognized arguments: input.txt" in err

    def test_data_flag_requires_a_value(self, invoke: Invoke) -> None:
        assert invoke("", ["--data"])[0] == 2


class TestErrors:
    def test_missing_data_file(self, invoke: Invoke) -> None:
        code, out, err = invoke("foo bar\n", ["--data", "other.json"])
        assert (code, out) == (1, "")
        assert err == "error: data file not found: other.json\n"

    def test_missing_data_file_detected_with_empty_stdin(self, invoke: Invoke) -> None:
        assert invoke("", ["--data", "other.json"])[0] == 1

    def test_malformed_json(self, invoke: Invoke) -> None:
        Path("bad.json").write_text("[{", encoding="utf-8")
        code, out, err = invoke("foo bar\n", ["--data", "bad.json"])
        assert (code, out) == (1, "")
        assert err.startswith("error: bad.json: invalid JSON at line 1 col")
        assert err.count("\n") == 1

    def test_invalid_record(self, invoke: Invoke) -> None:
        Path("bad.json").write_text(
            '[{"drugs": ["a"], "severity": "minor", "description": "d"}]', encoding="utf-8"
        )
        code, out, err = invoke("a\n", ["--data", "bad.json"])
        assert (code, out) == (1, "")
        assert err == "error: bad.json: record 0: drugs must have exactly 2 distinct names, got 1\n"

    def test_invalid_utf8_on_stdin(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mini_data_path: Path,
    ) -> None:
        raw = io.BytesIO(b"foo bar\n\xff\xfe\n")
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(raw, encoding="ascii"))
        code = cli.main(["--data", str(mini_data_path)])
        err = capsys.readouterr().err
        assert code == 1
        assert err.startswith("error: input is not valid UTF-8")


class TestStdinEncoding:
    def test_leading_bom_is_ignored(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mini_data_path: Path,
    ) -> None:
        raw = io.BytesIO(b"\xef\xbb\xbffoo bar\nfoo bar\n")
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(raw, encoding="utf-8", newline="\n"))
        assert cli.main(["--data", str(mini_data_path)]) == 0
        assert capsys.readouterr().out == f"{FOO_BAR}\n{FOO_BAR}\n"

    def test_stdin_is_utf8_even_if_the_locale_is_latin1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        data = tmp_path / "wide.json"
        data.write_text(
            '[{"drugs": ["sa", "b"], "severity": "minor", "description": "d"}]', encoding="utf-8"
        )
        raw = (chr(0xFF53) + "a b\n").encode()  # full-width s: NFKC folds it to "s"
        stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="latin-1", newline="\n")
        monkeypatch.setattr("sys.stdin", stdin)
        assert cli.main(["--data", str(data)]) == 0
        assert capsys.readouterr().out == "MINOR: d\n"


class TestDuplicatePairsWarning:
    def test_warns_on_stderr_but_keeps_stdout_clean(self, invoke: Invoke) -> None:
        Path("dup.json").write_text(
            '[{"drugs": ["a", "b"], "severity": "minor", "description": "one"},'
            ' {"drugs": ["b", "a"], "severity": "major", "description": "two"}]',
            encoding="utf-8",
        )
        code, out, err = invoke("a b\n", ["--data", "dup.json"])
        assert (code, out) == (0, "MAJOR: two\n")
        assert err == (
            "warning: duplicate interaction pair a/b: using the most severe, then earliest\n"
        )


class TestBrokenPipe:
    def test_closed_stdout_exits_quietly(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mini_data_path: Path,
    ) -> None:
        class ClosedPipe(io.StringIO):
            def write(self, s: str, /) -> int:
                raise BrokenPipeError

        monkeypatch.setattr("sys.stdin", io.StringIO("foo bar\n" * 3))
        monkeypatch.setattr("sys.stdout", ClosedPipe())
        assert cli.main(["--data", str(mini_data_path)]) == 0
        assert capsys.readouterr().err == ""
