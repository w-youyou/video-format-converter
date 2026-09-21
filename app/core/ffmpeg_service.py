from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from itertools import count
from pathlib import Path

from app.core.presets import Preset

_thumb_seq = count(1)

MSG_EXISTS = "输出文件已存在，未覆盖。请更换路径或在确认后覆盖。"
MSG_SAME_FILE = "输出文件不能和源文件相同，请更换保存位置。"
MSG_NO_AUDIO = "该视频没有音频轨道，无法提取音频。请改用「通用 MP4」。"
MSG_COPY_FAIL = "该文件不能无重编码转到 MP4，请改用「通用 MP4」。"
MSG_FAIL_HINT = "可展开「详细日志」查看详情。"
MSG_CANCELLED = "已取消"

_CLOCK_RE = re.compile(r"^out_time=(\d+):(\d{2}):(\d{2}(?:\.\d+)?)$")
_US_RE = re.compile(r"^out_time_us=(-?\d+)$")
_MS_RE = re.compile(r"^out_time_ms=(-?\d+)$")


def next_thumbnail_path() -> str:
    seq = next(_thumb_seq)
    name = f"vfc_thumb_{os.getpid()}_{seq}.jpg"
    return str(Path(tempfile.gettempdir()) / name)


def build_thumbnail_cmd(
    ffmpeg: str,
    input_path: str,
    output_jpg: str,
    duration_sec: float | None,
) -> list[str]:
    if duration_sec is not None and duration_sec > 0:
        seek = max(duration_sec * 0.1, 0.0)
        seek_arg = format(seek, ".6f").rstrip("0").rstrip(".") or "0"
    else:
        seek_arg = "1"
    return [
        ffmpeg,
        "-ss",
        seek_arg,
        "-i",
        input_path,
        "-frames:v",
        "1",
        "-q:v",
        "3",
        "-y",
        output_jpg,
    ]


def delete_thumbnail_file(path: str | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def default_output_path(input_path: str, suffix: str) -> str:
    source = Path(input_path)
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    return str(source.with_name(f"{source.stem}_转换{suffix}"))


def replace_output_suffix(path: str, suffix: str) -> str:
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    return str(Path(path).with_suffix(suffix))


def is_same_media_path(path_a: str, path_b: str) -> bool:
    if not path_a or not path_b:
        return False
    left = os.path.normcase(os.path.abspath(path_a))
    right = os.path.normcase(os.path.abspath(path_b))
    return left == right


def format_argv_for_copy(argv: list[str]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(argv)
    import shlex

    return shlex.join(argv)


def build_convert_cmd(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    preset: Preset,
    *,
    overwrite: bool = False,
    with_progress: bool = False,
) -> list[str]:
    cmd: list[str] = [ffmpeg]
    if overwrite:
        cmd.append("-y")
    cmd.append("-hide_banner")
    if with_progress:
        cmd.extend(["-nostats", "-progress", "pipe:1"])
    cmd.extend(["-i", input_path, *preset.args, output_path])
    return cmd


def parse_out_time_sec(line: str, duration_sec: float | None = None) -> float | None:
    text = line.strip()
    clock = _CLOCK_RE.match(text)
    if clock:
        hours = int(clock.group(1))
        minutes = int(clock.group(2))
        seconds = float(clock.group(3))
        return hours * 3600 + minutes * 60 + seconds

    us_match = _US_RE.match(text)
    if us_match:
        return max(int(us_match.group(1)), 0) / 1_000_000

    ms_match = _MS_RE.match(text)
    if ms_match:
        raw = max(int(ms_match.group(1)), 0)
        as_usec = raw / 1_000_000
        if duration_sec is not None and duration_sec > 0 and as_usec > duration_sec * 2:
            return raw / 1000
        return as_usec
    return None


def percent_from_out_time_sec(out_time_sec: float, duration_sec: float) -> int:
    if duration_sec <= 0:
        return 0
    percent = int((out_time_sec / duration_sec) * 100)
    if percent < 0:
        return 0
    if percent >= 100:
        return 99
    return percent


def delete_output_file(path: str | None, retries: int = 5, delay_sec: float = 0.2) -> None:
    if not path:
        return
    target = Path(path)
    for attempt in range(retries):
        try:
            target.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt + 1 >= retries:
                return
            time.sleep(delay_sec)
        except OSError:
            return


def humanize_ffmpeg_error(stderr: str, preset_id: str | None = None) -> str:
    if preset_id == "mp3_audio":
        return MSG_NO_AUDIO
    if preset_id == "copy_mux":
        return MSG_COPY_FAIL
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    tail = " ".join(lines[-2:]) if lines else "转换失败。"
    return f"{tail} {MSG_FAIL_HINT}"

