"""STDERR and STDIN edge cases (#48, #49) and gaps found by mutation testing (#50)."""

import errno
import io
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from interactions import cli

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX file descriptors")
CMD = [sys.executable, "-m", "interactions"]
LINE = b"sildenafil tamsulosin\n"
SILD = (
    b"MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in "
    b"symptomatic hypotension in some patients."
)
DUPLICATES = (
    '[{"drugs":["a","b"],"severity":"minor","description":"one"},'
    '{"drugs":["b","a"],"severity":"major","description":"two"}]'
)


def limit_file_size() -> None:
    """``preexec_fn``: a write beyond 4 KiB to a file fails with EFBIG (CPython ignores SIGXFSZ)."""
    import resource

    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))


# --- #48: STDERR closed or broken ------------------------------------------------------------
def run_without_stderr(stdin: bytes, *args: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    """Run the CLI with file descriptor 2 closed."""
    return subprocess.run(
        ["sh", "-c", 'exec "$@" 2>&-', "sh", *CMD, *args],
        input=stdin,
        stdout=subprocess.PIPE,
        cwd=cwd,
        check=False,
        timeout=60,
    )


@POSIX_ONLY
class TestClosedStderr:
    """With fd 2 closed, ``sys.stderr`` is None: diagnostics must never end up on STDOUT."""

    def test_duplicate_pair_warning(self, tmp_path: Path) -> None:
        (tmp_path / "dup.json").write_text(DUPLICATES, encoding="utf-8")
        r = run_without_stderr(b"a b\n", "--data", "dup.json", cwd=tmp_path)
        assert (r.returncode, r.stdout) == (0, b"MAJOR: two\n")

    def test_data_error(self, tmp_path: Path) -> None:
        r = run_without_stderr(b"a b\n", "--data", "missing.json", cwd=tmp_path)
        assert (r.returncode, r.stdout) == (1, b"")

    def test_invalid_input_keeps_the_results_before_it(self, tmp_path: Path) -> None:
        r = run_without_stderr(LINE + b"\xff\n", cwd=tmp_path)
        assert (r.returncode, r.stdout) == (1, SILD + b"\n")

    def test_usage_error(self, tmp_path: Path) -> None:
        r = run_without_stderr(b"", "--bogus", cwd=tmp_path)
        assert (r.returncode, r.stdout) == (2, b"")

    def test_write_error(self, tmp_path: Path) -> None:
        with (tmp_path / "out.txt").open("wb") as out:
            r = subprocess.run(
                ["sh", "-c", 'exec "$@" 2>&-', "sh", *CMD],
                input=LINE * 20_000,
                stdout=out,
                preexec_fn=limit_file_size,
                check=False,
                timeout=60,
            )
        written = (tmp_path / "out.txt").read_bytes()
        assert r.returncode == 1
        assert b"error" not in written
        assert b"warning" not in written


@POSIX_ONLY
@pytest.mark.parametrize(
    ("args", "stdin", "expected"),
    [(["--data", "nope.json"], b"", 1), (["--bogus"], b"", 2), ([], b"\xff\n", 1)],
    ids=["data-error", "usage-error", "invalid-input"],
)
def test_broken_stderr_pipe_keeps_the_documented_exit_code(
    tmp_path: Path, args: list[str], stdin: bytes, expected: int
) -> None:
    reader, writer = os.pipe()
    os.close(reader)  # the reader of STDERR is gone
    try:
        r = subprocess.run(
            [*CMD, *args],
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=writer,
            cwd=tmp_path,
            check=False,
            timeout=60,
        )
    finally:
        os.close(writer)
    assert r.returncode == expected


@POSIX_ONLY
def test_broken_stderr_pipe_does_not_stop_the_results(tmp_path: Path) -> None:
    (tmp_path / "dup.json").write_text(DUPLICATES, encoding="utf-8")
    reader, writer = os.pipe()
    os.close(reader)
    try:
        r = subprocess.run(
            [*CMD, "--data", "dup.json"],
            input=b"a b\n",
            stdout=subprocess.PIPE,
            stderr=writer,
            cwd=tmp_path,
            check=False,
            timeout=60,
        )
    finally:
        os.close(writer)
    assert (r.returncode, r.stdout) == (0, b"MAJOR: two\n")


class TestDiagnostic:
    def test_closed_stderr_writes_nothing_to_stdout(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.stderr", None)
        cli._diagnostic("error: x")
        assert capsys.readouterr() == ("", "")

    @pytest.mark.parametrize("method", ["write", "flush"])
    @pytest.mark.parametrize(
        "exc", [BrokenPipeError(), OSError(errno.ENOSPC, "full"), ValueError()]
    )
    def test_failing_stderr_is_silenced_and_never_raises(
        self, monkeypatch: pytest.MonkeyPatch, method: str, exc: Exception
    ) -> None:
        silenced: list[object] = []

        class Broken(io.StringIO):
            def write(self, s: str, /) -> int:
                if method == "write":
                    raise exc
                return super().write(s)

            def flush(self) -> None:
                if method == "flush":
                    raise exc

        broken = Broken()
        monkeypatch.setattr("sys.stderr", broken)
        monkeypatch.setattr(cli, "_silence", silenced.append)
        cli._diagnostic("error: x")
        assert silenced == [broken]

    def test_main_returns_the_documented_code_with_a_broken_stderr(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class Broken(io.StringIO):
            def write(self, s: str, /) -> int:
                raise BrokenPipeError

        monkeypatch.setattr("sys.stderr", Broken())
        monkeypatch.setattr(cli, "_silence", lambda stream: None)
        assert cli.main(["--bogus"]) == 2
        assert cli.main(["--data", "missing.json"]) == 1


# --- #49: inherited O_NONBLOCK -----------------------------------------------------------------
@POSIX_ONLY
def test_nonblocking_stdin_is_not_taken_for_end_of_input(tmp_path: Path) -> None:
    reader, writer = os.pipe()
    os.set_blocking(reader, False)  # what a parent may leave behind
    p = subprocess.Popen(
        CMD, stdin=reader, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=tmp_path
    )
    os.close(reader)
    try:
        os.write(writer, LINE)
        time.sleep(1.0)  # the child is now waiting for more input
        os.write(writer, LINE)
        os.close(writer)
        out, err = p.communicate(timeout=60)
    finally:
        p.kill()
        p.wait()
    assert (p.returncode, out, err) == (0, (SILD + b"\n") * 2, b"")


@POSIX_ONLY
def test_nonblocking_stdout_pipe_receives_all_the_output(tmp_path: Path) -> None:
    reader, writer = os.pipe()
    os.set_blocking(writer, False)  # the CLI's STDOUT; the pipe fills long before the end
    stdin_path = tmp_path / "in.txt"
    stdin_path.write_bytes(LINE * 5_000)
    with stdin_path.open("rb") as stdin:
        p = subprocess.Popen(CMD, stdin=stdin, stdout=writer, stderr=subprocess.PIPE, cwd=tmp_path)
    os.close(writer)
    assert p.stderr is not None
    chunks: list[bytes] = []
    try:
        time.sleep(1.0)  # let the pipe fill up before anything is read
        while chunk := os.read(reader, 65536):
            chunks.append(chunk)
            time.sleep(0.001)
        err = p.stderr.read()
        code = p.wait(timeout=60)
    finally:
        p.kill()
        p.wait()
        p.stderr.close()
        os.close(reader)
    assert (code, err) == (0, b"")
    assert b"".join(chunks) == (SILD + b"\n") * 5_000


@POSIX_ONLY
def test_make_blocking_clears_o_nonblock() -> None:
    reader, writer = os.pipe()
    os.set_blocking(reader, False)
    with os.fdopen(reader, "rb") as stream:
        cli._make_blocking(stream)
        assert os.get_blocking(reader)
    os.close(writer)


@pytest.mark.parametrize("stream", [io.StringIO(), object()], ids=["no-fileno", "not-a-stream"])
def test_make_blocking_ignores_streams_without_a_descriptor(stream: object) -> None:
    cli._make_blocking(stream)


# --- #50: mutation gaps ------------------------------------------------------------------------
def test_results_precede_the_error_line_when_streams_are_merged(tmp_path: Path) -> None:
    """Without ``stdout.flush()`` before the message, the error would come first with ``2>&1``."""
    r = subprocess.run(
        CMD,
        input=LINE * 3 + b"\xff\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=tmp_path,
        check=False,
        timeout=60,
    )
    assert r.stdout == (SILD + b"\n") * 3 + b"error: line 4: invalid UTF-8\n"


def test_flush_happens_before_the_input_error_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In-process version of the ordering test: record the order of the flush and the message."""
    events: list[str] = []

    class Stdout(io.StringIO):
        def flush(self) -> None:
            events.append("flush")

    class Stderr(io.StringIO):
        def write(self, s: str, /) -> int:
            events.append(f"stderr:{s.strip()}")
            return len(s)

    stdin = io.TextIOWrapper(io.BytesIO(LINE + b"\xff\n"), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", Stdout())
    monkeypatch.setattr("sys.stderr", Stderr())
    assert cli.main([]) == 1
    assert events[:2] == ["flush", "stderr:error: line 2: invalid UTF-8"]


@pytest.mark.parametrize("exc", [OSError(errno.ENOSPC, "No space left on device"), OSError(5, "")])
def test_write_error_silences_stdout_so_the_exit_flush_cannot_fail_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], exc: OSError
) -> None:
    """Mocked failing stream: runs on every OS (``/dev/full`` exists only on Linux)."""
    silenced: list[str] = []

    class FailingStdout(io.StringIO):
        def write(self, s: str, /) -> int:
            raise exc

    monkeypatch.setattr("sys.stdin", io.StringIO("a b\n"))
    monkeypatch.setattr("sys.stdout", FailingStdout())
    monkeypatch.setattr(cli, "_silence_stdout", lambda: silenced.append("stdout"))
    assert cli.main([]) == 1
    assert silenced == ["stdout"]
    assert capsys.readouterr().err == f"error: cannot write output: {exc.strerror or exc}\n"


@POSIX_ONLY
def test_write_error_end_to_end_without_dev_full(tmp_path: Path) -> None:
    """RLIMIT_FSIZE makes ``write()`` fail with EFBIG, so this also runs on macOS."""
    with (tmp_path / "out.txt").open("wb") as out:
        r = subprocess.run(
            CMD,
            input=LINE * 20_000,
            stdout=out,
            stderr=subprocess.PIPE,
            preexec_fn=limit_file_size,
            check=False,
            timeout=60,
        )
    assert (r.returncode, r.stderr) == (1, b"error: cannot write output: File too large\n")
