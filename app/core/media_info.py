from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

UNKNOWN = "未知"
PROBE_FAILED_MESSAGE = "无法读取视频信息。请确认这是可播放的视频文件。"


@dataclass
class MediaInfo:
    path: str
    filename: str
    size_bytes: int
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    fps: float | None = None
    bit_rate: int | None = None
    warning: str | None = None


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    value = float(size_bytes)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024.0
        if value < 1024:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} PB"


def format_size_change(src_bytes: int, dst_bytes: int) -> str:
    src_text = format_size(max(src_bytes, 0))
    dst_text = format_size(max(dst_bytes, 0))
    if src_bytes <= 0:
        return f"{src_text} → {dst_text}"
    ratio = (src_bytes - dst_bytes) / src_bytes
    if abs(ratio) < 0.01:
        return f"{src_text} → {dst_text}（体积基本不变）"
    percent = int(round(abs(ratio) * 100))
    if ratio > 0:
        return f"{src_text} → {dst_text}（压缩 {percent}%）"
    return f"{src_text} → {dst_text}（增大 {percent}%）"


def format_duration(duration_sec: float | None) -> str:
    if duration_sec is None:
        return UNKNOWN
    total = max(int(round(duration_sec)), 0)
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_resolution(width: int | None, height: int | None) -> str:
    if width is None or height is None:
        return UNKNOWN
    return f"{width}×{height}"


def format_fps(fps: float | None) -> str:
    if fps is None:
        return UNKNOWN
    if abs(fps - round(fps)) < 1e-6:
        return f"{int(round(fps))} fps"
    return f"{fps:.2f} fps"


def format_bit_rate(bit_rate: int | None) -> str:
    if bit_rate is None:
        return UNKNOWN
    return f"{bit_rate / 1_000_000:.1f} Mbps"


def format_codec(codec: str | None) -> str:
    if not codec:
        return UNKNOWN
    return codec


def file_size_bytes(path: str) -> int | None:
    try:
        return Path(path).stat().st_size
    except OSError:
        return None
