from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    suffix: str
    args: list[str]


_PRESETS: tuple[Preset, ...] = (
    Preset(
        id="mp4_compat",
        name="通用 MP4",
        description="微信和播放器一般都能打开",
        suffix=".mp4",
        args=[
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
        ],
    ),
    Preset(
        id="mp4_small",
        name="压缩体积",
        description="文件更小，方便发给别人",
        suffix=".mp4",
        args=[
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
        ],
    ),
    Preset(
        id="mp3_audio",
        name="提取音频 MP3",
        description="只要声音，不要画面",
        suffix=".mp3",
        args=["-vn", "-c:a", "libmp3lame", "-q:a", "2"],
    ),
    Preset(
        id="copy_mux",
        name="原画转封装",
        description="尽量不重编码，转成 MP4 封装",
        suffix=".mp4",
        args=["-map", "0:v:0", "-map", "0:a:0?", "-c", "copy", "-sn"],
    ),
)


def all_presets() -> list[Preset]:
    return list(_PRESETS)


def get_preset(preset_id: str) -> Preset:
    for preset in _PRESETS:
        if preset.id == preset_id:
            return preset
    return _PRESETS[0]
