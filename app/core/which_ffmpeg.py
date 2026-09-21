from __future__ import annotations

import os
import shutil
from pathlib import Path

_COMMON_DIRS = (
    Path(r"C:\ffmpeg\bin"),
    Path(r"C:\Program Files\ffmpeg\bin"),
)


def _existing_file(path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_file():
        return str(candidate.resolve())
    return None


def _find(env_name: str, executable: str) -> str | None:
    found = _existing_file(os.environ.get(env_name))
    if found:
        return found

    found = _existing_file(shutil.which(executable))
    if found:
        return found

    for folder in _COMMON_DIRS:
        found = _existing_file(str(folder / executable))
        if found:
            return found
    return None


def find_ffmpeg() -> str | None:
    name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    return _find("VFC_FFMPEG", name)


def find_ffprobe() -> str | None:
    name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    return _find("VFC_FFPROBE", name)
