"""End-to-end tests of ``interactions.cli.main`` using a fixture dataset."""

from pathlib import Path

import pytest

from tests.conftest import RunCli

pytestmark = pytest.mark.usefixtures("fixture_dir")


class TestMain:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("foo bar", "MODERATE: Foo and bar moderate."),
            ("bar foo", "MODERATE: Foo and bar moderate."),
            ("foo baz", "MINOR: Foo and baz minor."),
            ("foo bar baz", "MODERATE: Foo and bar moderate."),  # moderate beats minor
            ("foo bar qux", "MAJOR: Foo and qux major."),  # major beats moderate
            ("foo", "No interaction"),
            ("zzz yyy", "No interaction"),
            ("Foo Bar", "No interaction"),  # case sensitive
            ("foo foo bar", "MODERATE: Foo and bar moderate."),  # duplicate tokens
            ("  foo \t bar  ", "MODERATE: Foo and bar moderate."),  # odd whitespace
            ("", "No interaction"),  # blank line
            ("   ", "No interaction"),
        ],
    )
    def test_single_line(self, run_cli: RunCli, line: str, expected: str) -> None:
        assert run_cli(line + "\n") == [expected]

    def test_one_output_line_per_input_line_in_order(self, run_cli: RunCli) -> None:
        stdin = "foo bar\nnothing\nfoo baz\n\nfoo qux\n"
        assert run_cli(stdin) == [
            "MODERATE: Foo and bar moderate.",
            "No interaction",
            "MINOR: Foo and baz minor.",
            "No interaction",
            "MAJOR: Foo and qux major.",
        ]

    def test_no_trailing_newline(self, run_cli: RunCli) -> None:
        assert run_cli("foo bar\nfoo baz") == [
            "MODERATE: Foo and bar moderate.",
            "MINOR: Foo and baz minor.",
        ]

    def test_crlf_line_endings(self, run_cli: RunCli) -> None:
        assert run_cli("foo bar\r\nfoo baz\r\n") == [
            "MODERATE: Foo and bar moderate.",
            "MINOR: Foo and baz minor.",
        ]

    def test_empty_stdin_prints_nothing(self, run_cli: RunCli) -> None:
        assert run_cli("") == []

    def test_prints_nothing_to_stderr(
        self, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run_cli("foo bar\n")
        assert capsys.readouterr().err == ""

    def test_many_lines(self, run_cli: RunCli) -> None:
        assert run_cli("foo bar\n" * 500) == ["MODERATE: Foo and bar moderate."] * 500

    def test_20_drugs_per_line(self, run_cli: RunCli) -> None:
        line = " ".join([f"d{n}" for n in range(18)] + ["foo", "baz"])
        assert run_cli(line) == ["MINOR: Foo and baz minor."]

    def test_missing_interactions_file_raises(
        self,
        run_cli: RunCli,
        tmp_path_factory: pytest.TempPathFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path_factory.mktemp("empty"))
        with pytest.raises(FileNotFoundError):
            run_cli("foo bar\n")

    def test_file_is_read_from_cwd(self, run_cli: RunCli, fixture_dir: Path) -> None:
        (fixture_dir / "interactions.json").write_text("[]")
        assert run_cli("foo bar\n") == ["No interaction"]


class TestTies:
    def test_first_in_file_is_printed_first(self, run_cli: RunCli) -> None:
        # Pins current ordering; the extra tie lines are covered by the xfail tests below.
        assert run_cli("alpha beta gamma\n")[0] == "MAJOR: Alpha and beta major (first)."

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "spec: each input line must produce exactly one output line "
            "(current behavior prints every top-severity tie, one per line)"
        ),
    )
    def test_exactly_one_line_when_top_severity_ties(self, run_cli: RunCli) -> None:
        assert run_cli("alpha beta gamma\n") == ["MAJOR: Alpha and beta major (first)."]

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "spec: output lines must stay aligned with input lines "
            "(current behavior prints extra lines for ties, shifting later results)"
        ),
    )
    def test_ties_do_not_misalign_following_lines(self, run_cli: RunCli) -> None:
        assert run_cli("alpha beta gamma\nfoo baz\n") == [
            "MAJOR: Alpha and beta major (first).",
            "MINOR: Foo and baz minor.",
        ]

    def test_lower_severity_not_printed_alongside_top(self, run_cli: RunCli) -> None:
        # alpha+delta is moderate and must not appear next to the major result.
        assert run_cli("alpha beta delta\n") == ["MAJOR: Alpha and beta major (first)."]
