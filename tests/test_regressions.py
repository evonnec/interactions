"""Regression tests for issues found by adversarial testing, grouped by issue number.

A defect that is found but not fixed yet is kept as ``xfail(strict=True)`` with its issue number;
strict=True makes the test fail once the defect is fixed, which is the reminder to remove it.
"""

import errno
import io
import os
import signal
import subprocess
import sys
import unicodedata
from collections.abc import Iterator
from pathlib import Path

import pytest

from interactions import cli
from interactions.data import UNPRINTABLE, DataError, load_file, parse_records
from interactions.index import format_result

SILD = (
    "MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in "
    "symptomatic hypotension in some patients."
)
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX file descriptors")
CMD = [sys.executable, "-m", "interactions"]


def run_bytes(
    stdin: bytes, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [*CMD, *args], input=stdin, capture_output=True, env=env, check=False, timeout=60
    )


def invoke(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stdin: object
) -> tuple[int, str, str]:
    monkeypatch.setattr("sys.stdin", stdin)
    code = cli.main([])
    out, err = capsys.readouterr()
    return code, out, err


class FailingWriter(io.StringIO):
    """A STDOUT whose every write fails with ``exc``."""

    def __init__(self, exc: BaseException) -> None:
        super().__init__()
        self.exc = exc

    def write(self, s: str, /) -> int:
        raise self.exc


# --- #31 (leading BOM): see TestByteOrderMark in test_contract.py and test_cli.py ---------------


# --- #32: descriptions must be a single printable line ----------------------------------------
@pytest.mark.parametrize(
    "desc",
    [
        "a\nb",
        "a\rb",
        "a" + chr(0x2028) + "b",
        chr(0x2029),
        "a\x85b",
        "a\x00b",
        "a\x0cb",
        "a\ud800b",
    ],
)
def test_description_must_be_a_single_line(desc: str) -> None:
    with pytest.raises(DataError, match="single line"):
        parse_records([{"drugs": ["a", "b"], "severity": "minor", "description": "x" + desc + "x"}])


def test_description_may_contain_tabs_and_non_ascii() -> None:
    description = "dose ≥ 10 mg\tdaily µg"
    (record,) = parse_records(
        [{"drugs": ["a", "b"], "severity": "minor", "description": description}]
    )
    assert record.description == description


def test_unprintable_rule_matches_unicode_categories_for_every_code_point() -> None:
    """Every control character, line boundary and lone surrogate is rejected; nothing else."""
    rejected = {"Cc", "Zl", "Zp", "Cs"}
    for code in range(sys.maxunicode + 1):
        char = chr(code)
        expected = unicodedata.category(char) in rejected and char != "\t"
        assert bool(UNPRINTABLE.search(char)) is expected, hex(code)


def test_every_accepted_description_formats_to_exactly_one_line(
    mini_records: list[dict[str, str]],
) -> None:
    for interaction in parse_records(mini_records):
        text = format_result(interaction)
        assert len(text.splitlines()) == 1
        assert text.isprintable() or "\t" in text


def test_bad_description_in_data_file_fails_before_stdin_is_read(tmp_path: Path) -> None:
    data = tmp_path / "nl.json"
    data.write_text(
        '[{"drugs":["a","b"],"severity":"major","description":"one\\ntwo"}]', encoding="utf-8"
    )
    result = run_bytes(b"a b\nx y\n", "--data", str(data))
    assert result.returncode == 1
    assert result.stdout == b""
    assert (
        result.stderr
        == (
            f"error: {data}: record 0: "
            "description must be a single line without control characters\n"
        ).encode()
    )


# --- #33: stdio is pinned to UTF-8 and "\n" on every platform ---------------------------------
def test_windows_universal_newlines_do_not_split_on_lone_cr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = b"sildenafil\rtamsulosin\nsildenafil ibuprofen\n"
    stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8", newline=None)  # as on Windows
    assert invoke(monkeypatch, capsys, stdin)[1] == SILD + "\nNo interaction\n"


def test_stdout_is_utf8_with_lf_newlines_whatever_the_platform_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data = tmp_path / "uni.json"
    data.write_text(
        '[{"drugs":["a","b"],"severity":"major","description":"dose \\u2265 10 mg"}]',
        encoding="utf-8",
    )
    sink = io.BytesIO()
    # What CPython builds on Windows with output redirected: cp1252 and "\r\n" translation.
    stdout = io.TextIOWrapper(sink, encoding="cp1252", newline="\r\n")
    monkeypatch.setattr("sys.stdin", io.StringIO("a b\nx y\n"))
    monkeypatch.setattr("sys.stdout", stdout)
    assert cli.main(["--data", str(data)]) == 0
    assert sink.getvalue() == "MAJOR: dose ≥ 10 mg\nNo interaction\n".encode()


def test_non_ascii_description_is_utf8_regardless_of_locale(tmp_path: Path) -> None:
    data = tmp_path / "uni.json"
    data.write_text(
        '[{"drugs":["a","b"],"severity":"major","description":"dose \\u2265 10 mg"}]',
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONIOENCODING": "latin-1"}
    r = run_bytes(b"a b\n", "--data", str(data), env=env)
    assert (r.returncode, r.stdout, r.stderr) == (0, "MAJOR: dose ≥ 10 mg\n".encode(), b"")


def test_subprocess_stdio_bytes_are_identical_on_every_platform() -> None:
    """Real child process (runs on Windows too): lone CR never splits, CRLF does, output is LF."""
    r = run_bytes(b"sildenafil\rtamsulosin\r\nsildenafil tamsulosin\r\n")
    assert r.returncode == 0
    assert r.stderr == b""
    # CR is whitespace inside line 1: one pair (SILD), not two lines; line 2 is the same pair
    assert r.stdout == (SILD + "\n").encode() * 2


def test_subprocess_utf8_output_under_a_legacy_console_code_page(tmp_path: Path) -> None:
    data = tmp_path / "uni.json"
    data.write_text(
        '[{"drugs":["a","b"],"severity":"major","description":"dose \\u2265 10 mg"}]',
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    r = run_bytes(b"\xef\xbb\xbfa b\r\nb a\r\n", "--data", str(data), env=env)
    assert (r.returncode, r.stderr) == (0, b"")
    assert r.stdout == "MAJOR: dose ≥ 10 mg\nMAJOR: dose ≥ 10 mg\n".encode()


# --- #34: invalid UTF-8 mid-stream: exact prefix, named line ----------------------------------
def test_invalid_utf8_far_into_the_stream_gives_exact_prefix_and_line_number() -> None:
    good = b"sildenafil tamsulosin\n"
    r = run_bytes(good * 3000 + b"\xff\n" + good)  # far beyond the first 8 KB decode chunk
    assert r.returncode == 1
    assert r.stdout == (SILD + "\n").encode() * 3000
    assert r.stderr == b"error: line 3001: invalid UTF-8\n"


@pytest.mark.parametrize(
    ("stdin", "good_lines", "bad_line"),
    [
        (b"\xff\n", 0, 1),
        (b"a b\n\xc3(\n", 1, 2),  # invalid continuation byte
        (b"a b\nx y\n\xe2\x82", 2, 3),  # truncated multi-byte sequence at EOF, no newline
        (b"a b\n\xed\xa0\x80 c\n", 1, 2),  # UTF-8 encoded surrogate
    ],
)
def test_invalid_utf8_reports_the_first_bad_line(
    stdin: bytes, good_lines: int, bad_line: int
) -> None:
    r = run_bytes(stdin)
    assert r.returncode == 1
    assert r.stdout == b"No interaction\n" * good_lines
    assert r.stderr == f"error: line {bad_line}: invalid UTF-8\n".encode()


def test_stdin_read_error_is_one_error_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def lines() -> Iterator[str]:
        yield "a b\n"
        raise OSError(errno.EIO, "Input/output error")

    code, out, err = invoke(monkeypatch, capsys, lines())
    assert (code, out, err) == (
        1,
        "No interaction\n",
        "error: cannot read input: Input/output error\n",
    )


# --- #35: stdio failures are clean errors, not tracebacks -------------------------------------
@pytest.mark.parametrize("exc", [OSError(errno.ENOSPC, "No space left on device"), OSError(5, "")])
def test_stdout_write_error_is_one_error_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], exc: OSError
) -> None:
    monkeypatch.setattr("sys.stdout", FailingWriter(exc))
    code, _, err = invoke(monkeypatch, capsys, io.StringIO("a b\n"))
    assert code == 1
    assert err == f"error: cannot write output: {exc.strerror or exc}\n"


def test_stdout_flush_failure_is_one_error_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FlushFails(io.StringIO):
        def flush(self) -> None:
            raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("sys.stdout", FlushFails())
    code, _, err = invoke(monkeypatch, capsys, io.StringIO("a b\n"))
    assert (code, err) == (1, "error: cannot write output: No space left on device\n")


def test_errno_counted_as_closed_pipe_is_quiet(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Stands in for Windows, where a write to a closed pipe fails with EINVAL, not EPIPE."""
    monkeypatch.setattr(cli, "_CLOSED_PIPE_ERRNOS", frozenset({errno.EINVAL}))
    monkeypatch.setattr("sys.stdout", FailingWriter(OSError(errno.EINVAL, "Invalid argument")))
    assert invoke(monkeypatch, capsys, io.StringIO("a b\n"))[0::2] == (0, "")


def test_broken_pipe_on_flush_is_quiet(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FlushFails(io.StringIO):
        def flush(self) -> None:
            raise BrokenPipeError

    monkeypatch.setattr("sys.stdout", FlushFails())
    assert invoke(monkeypatch, capsys, io.StringIO("a b\n"))[0::2] == (0, "")


def test_ctrl_c_exits_130(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def lines() -> Iterator[str]:
        yield "sildenafil tamsulosin\n"
        raise KeyboardInterrupt

    try:  # pytest aborts the whole session on an escaping KeyboardInterrupt
        code, _, err = invoke(monkeypatch, capsys, lines())
    except KeyboardInterrupt:
        pytest.fail("KeyboardInterrupt escaped cli.main")
    assert (code, err) == (130, "")


@pytest.mark.parametrize("stream", ["stdin", "stdout"])
def test_closed_std_stream_is_a_clean_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stream: str
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("a b\n"))
    monkeypatch.setattr(f"sys.{stream}", None)
    assert cli.main([]) == 1
    assert capsys.readouterr().err == f"error: {stream} is closed\n"


@POSIX_ONLY
@pytest.mark.parametrize(
    ("redirect", "stream"), [(">&-", "stdout"), ("<&-", "stdin")], ids=["stdout", "stdin"]
)
def test_closed_file_descriptor_is_a_clean_error(redirect: str, stream: str) -> None:
    r = subprocess.run(
        ["sh", "-c", f'exec "$@" {redirect}', "sh", *CMD],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert r.returncode == 1
    assert r.stderr == f"error: {stream} is closed\n".encode()


@POSIX_ONLY
@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_info_flag_into_a_closed_pipe_exits_0_quietly(flag: str) -> None:
    read_end, write_end = os.pipe()
    os.close(read_end)  # the reader is gone before the child writes: EPIPE is certain
    try:
        r = subprocess.run(
            [*CMD, flag], stdout=write_end, stderr=subprocess.PIPE, check=False, timeout=60
        )
    finally:
        os.close(write_end)
    assert (r.returncode, r.stderr) == (0, b"")


@POSIX_ONLY
@pytest.mark.skipif(not Path("/dev/full").exists(), reason="needs /dev/full (Linux)")
def test_disk_full_is_a_clean_error_end_to_end() -> None:
    with Path("/dev/full").open("wb") as full:
        r = subprocess.run(
            CMD, input=b"a b\n", stdout=full, stderr=subprocess.PIPE, check=False, timeout=60
        )
    assert r.returncode == 1
    assert r.stderr == b"error: cannot write output: No space left on device\n"


@POSIX_ONLY
def test_sigint_while_reading_stdin_exits_130_without_traceback() -> None:
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}  # so the first result is visible immediately
    p = subprocess.Popen(
        CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    assert p.stdin is not None
    assert p.stdout is not None
    assert p.stderr is not None
    try:
        p.stdin.write(b"sildenafil tamsulosin\n")
        p.stdin.flush()
        assert p.stdout.readline() == (SILD + "\n").encode()  # now blocked reading stdin
        p.send_signal(signal.SIGINT)
        code = p.wait(timeout=30)
        stderr = p.stderr.read()
    finally:
        p.kill()
        for stream in (p.stdin, p.stdout, p.stderr):
            stream.close()
    assert code == -signal.SIGINT  # killed by SIGINT; a shell reports 130
    assert stderr == b""


# --- #36: tests that kill the surviving mutants -----------------------------------------------
@pytest.mark.parametrize("flag", ["--help", "--version", "--bogus"])
def test_flag_does_not_wait_for_open_stdin(flag: str) -> None:
    p = subprocess.Popen(
        [*CMD, flag], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        code = p.wait(timeout=15)  # stdin stays open and silent
    except subprocess.TimeoutExpired:
        p.kill()
        pytest.fail(f"{flag} blocked on stdin")
    finally:
        for stream in (p.stdin, p.stdout, p.stderr):
            assert stream is not None
            stream.close()
    assert code == (2 if flag == "--bogus" else 0)


def test_stdin_decoded_as_utf8_even_if_locale_is_latin1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = (chr(0xFF53) + "ildenafil tamsulosin\n").encode()  # full-width s
    stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="latin-1", newline="\n")
    assert invoke(monkeypatch, capsys, stdin)[:2] == (0, SILD + "\n")


def test_interacting_pair_beyond_the_20th_drug_is_found() -> None:
    filler = " ".join(f"unknown{n}" for n in range(30))
    assert (
        run_bytes(f"{filler} sildenafil {filler} tamsulosin\n".encode()).stdout
        == (SILD + "\n").encode()
    )


# --- #37: loader tracebacks -------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["[" * 200_000 + "]" * 200_000, "[" + "1" * 5000 + "]"],
    ids=["deeply-nested", "huge-integer"],  # a long id would overflow Windows' env var limit
)
def test_pathological_json_is_a_data_error(tmp_path: Path, text: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DataError, match="invalid JSON"):
        load_file(path)


def test_data_file_with_a_bom_loads(tmp_path: Path) -> None:
    path = tmp_path / "bom.json"
    path.write_bytes(b'\xef\xbb\xbf[{"drugs":["a","b"],"severity":"minor","description":"d"}]')
    assert [i.description for i in load_file(path)] == ["d"]
