"""Ctrl-C ends the process at once, without a traceback or interpreter noise (issue #35).

On POSIX the entry point restores SIGINT's default action, so the process dies by SIGINT (a shell
reports 130; ``subprocess`` reports -2). The subprocess tests need POSIX signals and process
groups; the entry-point test runs everywhere and covers the ``KeyboardInterrupt`` fallback.
"""

import builtins
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX signals and pipes")
CMD = [sys.executable, "-m", "interactions"]
LINE = b"sildenafil tamsulosin\n"
KILLED_BY_SIGINT = -signal.SIGINT


@pytest.mark.parametrize(
    ("inherited", "posix_expected"),
    [
        (signal.default_int_handler, [(signal.SIGINT, signal.SIG_DFL)]),
        (signal.SIG_IGN, []),  # issue #56: an ignored SIGINT stays ignored
    ],
    ids=["python-default", "inherited-ignore"],
)
@pytest.mark.parametrize("posix", [True, False], ids=["posix", "windows"])
def test_entry_restores_default_sigint_on_posix_and_maps_import_interrupt_to_130(
    monkeypatch: pytest.MonkeyPatch,
    inherited: object,
    posix_expected: list[tuple[int, object]],
    posix: bool,
) -> None:
    import interactions.__main__ as entry_module

    monkeypatch.setattr(entry_module, "RESTORE_DEFAULT_SIGINT", posix)
    installed: list[tuple[int, object]] = []
    monkeypatch.setattr(
        signal, "signal", lambda number, handler: installed.append((number, handler))
    )
    monkeypatch.setattr(signal, "getsignal", lambda number: inherited)
    real_import = builtins.__import__

    def interrupted_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "interactions.cli":
            raise KeyboardInterrupt
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", interrupted_import)
    try:
        assert entry_module.entry() == 130
        assert installed == (posix_expected if posix else [])
    finally:
        monkeypatch.undo()
        sys.modules.pop("interactions.__main__", None)  # keep runpy tests free of warnings


@POSIX_ONLY
def test_inherited_ignored_sigint_is_respected() -> None:
    """Issue #56: a background job (``cmd &``, ``trap '' INT``) survives a stray Ctrl-C."""
    p = subprocess.Popen(
        CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN),
    )
    try:
        time.sleep(0.5)  # let the entry point run
        p.send_signal(signal.SIGINT)
        out, err = p.communicate(LINE * 3, timeout=60)
    finally:
        if p.poll() is None:
            p.kill()
    assert (p.returncode, out.count(b"\n"), err) == (0, 3, b"")


@POSIX_ONLY
def test_sigint_during_startup_kills_the_process_quietly(tmp_path: Path) -> None:
    """SIGINT delivered while ``interactions.cli`` is imported (before ``main`` runs)."""
    code = (
        "import builtins, os, runpy, signal\n"
        "real = builtins.__import__\n"
        "def hook(name, *a, **k):\n"
        "    if name == 'interactions.cli':\n"
        "        builtins.__import__ = real\n"
        "        os.kill(os.getpid(), signal.SIGINT)\n"
        "    return real(name, *a, **k)\n"
        "builtins.__import__ = hook\n"
        "runpy.run_module('interactions', run_name='__main__')\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        cwd=tmp_path,
        check=False,
        timeout=60,
    )
    assert (r.returncode, r.stderr) == (KILLED_BY_SIGINT, b"")


@POSIX_ONLY
def test_sigint_right_after_spawn_ends_the_process_quickly() -> None:
    """Whatever phase the process is in, Ctrl-C ends it and it never hangs.

    Before our entry point runs (interpreter start-up, ``site``, importing the package) the
    interpreter's own handling applies: it may print its traceback and exit 1. That window is
    outside the program's control and only tolerated here.
    """
    for delay in (0.0, 0.002, 0.01, 0.05):
        p = subprocess.Popen(
            CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            time.sleep(delay)
            p.send_signal(signal.SIGINT)
            code = p.wait(timeout=30)
            assert p.stderr is not None
            stderr = p.stderr.read()
            assert code in (KILLED_BY_SIGINT, 1)
            assert stderr == b"" or b"KeyboardInterrupt" in stderr  # start-up window only
        finally:
            p.kill()
            for stream in (p.stdin, p.stdout, p.stderr):
                assert stream is not None
                stream.close()


@POSIX_ONLY
def test_ctrl_c_on_a_pipeline_exits_130_quietly() -> None:
    """``producer | interactions | grep``: SIGINT reaches the whole process group, so the reader
    of STDOUT dies too; the buffered results must not be flushed into the dead pipe."""
    script = f"for i in $(seq 10); do echo '{LINE.decode().strip()}'; done; exec sleep 30"
    producer = subprocess.Popen(["sh", "-c", script], stdout=subprocess.PIPE, process_group=0)
    group = producer.pid
    tool = subprocess.Popen(
        CMD,
        stdin=producer.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        process_group=group,
    )
    assert producer.stdout is not None
    assert tool.stdout is not None
    assert tool.stderr is not None
    producer.stdout.close()
    consumer = subprocess.Popen(
        ["grep", "MAJOR"], stdin=tool.stdout, stdout=subprocess.DEVNULL, process_group=group
    )
    tool.stdout.close()
    try:
        time.sleep(1.5)
        os.killpg(group, signal.SIGINT)
        code = tool.wait(timeout=30)
        stderr = tool.stderr.read()
    finally:
        for p in (producer, consumer, tool):
            p.kill()
            p.wait()
        tool.stderr.close()
    assert (code, stderr) == (KILLED_BY_SIGINT, b"")


@POSIX_ONLY
@pytest.mark.parametrize("workload", ["help", "results"])
def test_ctrl_c_while_stdout_is_a_full_pipe_does_not_hang(tmp_path: Path, workload: str) -> None:
    """The reader is alive but never reads: the write blocks, Ctrl-C must still end the process."""
    stdin_path = tmp_path / "in.txt"
    stdin_path.write_bytes(LINE * 20_000)  # about 2.5 MB of results, far more than a pipe holds
    r, w = os.pipe()
    os.set_blocking(w, False)
    try:
        while True:
            os.write(w, b"x" * 65536)
    except BlockingIOError:
        pass
    os.set_blocking(w, True)
    with stdin_path.open("rb") as stdin:
        p = subprocess.Popen(
            [*CMD, "--help"] if workload == "help" else CMD,
            stdin=stdin,
            stdout=w,
            stderr=subprocess.PIPE,
        )
    os.close(w)
    assert p.stderr is not None
    try:
        time.sleep(1.0)
        p.send_signal(signal.SIGINT)
        try:
            code = p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pytest.fail("still running 15 s after SIGINT")
        stderr = p.stderr.read()
    finally:
        p.kill()
        p.wait()
        p.stderr.close()
        os.close(r)
    assert (code, stderr) == (KILLED_BY_SIGINT, b"")


@POSIX_ONLY
def test_second_ctrl_c_while_blocked_is_harmless(tmp_path: Path) -> None:
    r, w = os.pipe()
    os.set_blocking(w, False)
    try:
        while True:
            os.write(w, b"x" * 65536)
    except BlockingIOError:
        pass
    os.set_blocking(w, True)
    p = subprocess.Popen(
        [*CMD, "--help"], stdin=subprocess.DEVNULL, stdout=w, stderr=subprocess.PIPE
    )
    os.close(w)
    assert p.stderr is not None
    try:
        time.sleep(1.0)
        p.send_signal(signal.SIGINT)
        p.send_signal(signal.SIGINT)
        code = p.wait(timeout=15)
        stderr = p.stderr.read()
    finally:
        p.kill()
        p.wait()
        p.stderr.close()
        os.close(r)
    assert (code, stderr) == (KILLED_BY_SIGINT, b"")
