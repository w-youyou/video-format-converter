from __future__ import annotations

import json
from pathlib import Path

from app.core.media_info import MediaInfo, PROBE_FAILED_MESSAGE


def build_cmd(ffprobe: str, path: str) -> list[str]:
    return [
        ffprobe,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        path,
    ]


def parse(stdout: str, path: str, size_bytes: int) -> MediaInfo:
    info = MediaInfo(
        path=path,
        filename=Path(path).name,
        size_bytes=size_bytes,
    )
    try:
        data = json.loads(stdout) if stdout and stdout.strip() else {}
    except json.JSONDecodeError:
        info.warning = PROBE_FAILED_MESSAGE
        return info

    if not isinstance(data, dict):
        info.warning = PROBE_FAILED_MESSAGE
        return info

    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    if not isinstance(streams, list):
        streams = []

    info.duration_sec = _to_float(fmt.get("duration"))
    info.bit_rate = _to_int(fmt.get("bit_rate"))

    video = _pick_video_stream(streams)
    audio = _pick_audio_stream(streams)

    if video is None:
        info.warning = PROBE_FAILED_MESSAGE
        if audio:
            info.audio_codec = audio.get("codec_name") or None
        return info

    if info.duration_sec is None:
        info.duration_sec = _to_float(video.get("duration"))
    if info.bit_rate is None:
        info.bit_rate = _to_int(video.get("bit_rate"))

    info.width = _to_int(video.get("width"))
    info.height = _to_int(video.get("height"))
    info.video_codec = video.get("codec_name") or None
    info.fps = _parse_frame_rate(video.get("avg_frame_rate"))
    if audio:
        info.audio_codec = audio.get("codec_name") or None
    return info


def _pick_video_stream(streams: list) -> dict | None:
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        if stream.get("codec_type") != "video":
            continue
        if _is_attached_pic(stream):
            continue
        return stream
    return None


def _pick_audio_stream(streams: list) -> dict | None:
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == "audio":
            return stream
    return None


def _is_attached_pic(stream: dict) -> bool:
    disposition = stream.get("disposition") or {}
    if not isinstance(disposition, dict):
        return False
    return bool(disposition.get("attached_pic"))


def _parse_frame_rate(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"0/0", "N/A"}:
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        num = _to_float(left)
        den = _to_float(right)
        if num is None or den is None or den == 0:
            return None
        return num / den
    return _to_float(text)


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)
