from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int


def run(argv: list[str], timeout: float = 30.0) -> CommandResult:
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        raise TypeError("argv 必须是 list[str]")

    kwargs: dict = {
        "args": argv,
        "shell": False,
        "capture_output": True,
        "timeout": timeout,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    started = time.perf_counter()
    try:
        completed = subprocess.run(**kwargs)
        return CommandResult(
            argv=list(argv),
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except FileNotFoundError as exc:
        return CommandResult(
            argv=list(argv),
            returncode=-1,
            stdout="",
            stderr=str(exc),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return CommandResult(
            argv=list(argv),
            returncode=-1,
            stdout=stdout,
            stderr=(stderr + "\n命令超时").strip(),
            duration_ms=int(timeout * 1000),
        )
