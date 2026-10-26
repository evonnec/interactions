"""Regression tests for issues found by adversarial testing, grouped by issue number.

Tests marked xfail(strict=True) document defects that are still open; the marker is removed in
the change that fixes the issue (strict=True makes the test fail once the defect is fixed).
"""

import errno
import io
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from interactions import cli
from interactions.data import DataError, load_file, parse_records

SILD = (
    "MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in "
    "symptomatic hypotension in some patients."
)


def run_bytes(
    stdin: bytes, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "interactions", *args],
        input=stdin,
        capture_output=True,
        env=env,
        check=False,
        timeout=60,
    )


def invoke(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stdin: object
) -> tuple[int, str, str]:
    monkeypatch.setattr("sys.stdin", stdin)
    code = cli.main([])
    out, err = capsys.readouterr()
    return code, out, err


# --- #36: tests that kill the surviving mutants (should PASS today) --------------------------
@pytest.mark.parametrize("flag", ["--help", "--version", "--bogus"])
def test_flag_does_not_wait_for_open_stdin(flag: str) -> None:
    p = subprocess.Popen(
        [sys.executable, "-m", "interactions", flag],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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


# #31 (leading BOM) is covered by TestByteOrderMark in test_contract.py and test_cli.py.


# --- #32: description line breaks ------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="#32")
@pytest.mark.parametrize(
    "desc", ["a\nb", "a\rb", "a" + chr(0x2028) + "b", "a\x85b", "a\x00b", "a\x0cb"]
)
def test_description_must_be_a_single_line(desc: str) -> None:
    with pytest.raises(DataError):
        parse_records([{"drugs": ["a", "b"], "severity": "minor", "description": desc}])


# --- #33: stdio pinning ----------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="#33")
def test_windows_universal_newlines_do_not_split_on_lone_cr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = b"sildenafil\rtamsulosin\nsildenafil ibuprofen\n"
    stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8", newline=None)  # as on Windows
    assert invoke(monkeypatch, capsys, stdin)[1] == SILD + "\nNo interaction\n"


@pytest.mark.xfail(strict=True, reason="#33")
def test_non_ascii_description_is_utf8_regardless_of_locale(tmp_path: Path) -> None:
    data = tmp_path / "uni.json"
    data.write_text(
        '[{"drugs":["a","b"],"severity":"major","description":"dose \\u2265 10 mg"}]',
        encoding="utf-8",
    )
    r = run_bytes(b"a b\n", "--data", str(data), env={**os.environ, "PYTHONIOENCODING": "latin-1"})
    assert (r.returncode, r.stdout) == (0, "MAJOR: dose ≥ 10 mg\n".encode())


# --- #34: invalid UTF-8 mid-stream -----------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="#34")
def test_invalid_utf8_mid_stream_gives_exact_prefix() -> None:
    r = run_bytes(b"sildenafil tamsulosin\n" * 3000 + b"\xff\n" + b"sildenafil tamsulosin\n")
    assert r.returncode == 1
    assert r.stdout.count(b"\n") in (0, 3000)
    assert b"3001" in r.stderr


# --- #35: stdio failures ---------------------------------------------------------------------
class FailingWriter(io.StringIO):
    def __init__(self, exc: BaseException) -> None:
        super().__init__()
        self.exc = exc

    def write(self, s: str, /) -> int:
        raise self.exc


@pytest.mark.xfail(strict=True, raises=OSError, reason="#35")
def test_stdout_disk_full_is_one_error_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.stdout", FailingWriter(OSError(errno.ENOSPC, "No space left on device"))
    )
    assert invoke(monkeypatch, capsys, io.StringIO("a b\n"))[0] == 1


@pytest.mark.xfail(strict=True, reason="#35")
def test_ctrl_c_exits_130(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def lines() -> Iterator[str]:
        yield "sildenafil tamsulosin\n"
        raise KeyboardInterrupt

    try:  # pytest aborts the whole session on an escaping KeyboardInterrupt
        code = invoke(monkeypatch, capsys, lines())[0]
    except KeyboardInterrupt:
        pytest.fail("KeyboardInterrupt escaped cli.main")
    assert code == 130


@pytest.mark.xfail(strict=True, raises=(AttributeError, TypeError), reason="#35")
@pytest.mark.parametrize("stream", ["sys.stdin", "sys.stdout"])
def test_closed_std_stream_is_clean(monkeypatch: pytest.MonkeyPatch, stream: str) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("a b\n"))
    monkeypatch.setattr(stream, None)
    assert cli.main([]) == 1


# --- #37: loader tracebacks ------------------------------------------------------------------
@pytest.mark.xfail(strict=True, raises=(RecursionError, ValueError), reason="#37")
@pytest.mark.parametrize("text", ["[" * 200_000 + "]" * 200_000, "[" + "1" * 5000 + "]"])
def test_pathological_json_is_a_data_error(tmp_path: Path, text: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DataError):
        load_file(path)
