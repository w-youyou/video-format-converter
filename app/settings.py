from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_WIDTH = 1100
DEFAULT_HEIGHT = 720
DEFAULT_PRESET_ID = "mp4_compat"


@dataclass
class AppSettings:
    last_input_dir: str = ""
    last_output_dir: str = ""
    last_preset_id: str = DEFAULT_PRESET_ID
    window_width: int = DEFAULT_WIDTH
    window_height: int = DEFAULT_HEIGHT


def settings_path() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home())
    return Path(appdata) / "VideoFormatConverter" / "settings.json"


def load_settings() -> AppSettings:
    path = settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return AppSettings()
    if not isinstance(data, dict):
        return AppSettings()
    return AppSettings(
        last_input_dir=str(data.get("last_input_dir") or ""),
        last_output_dir=str(data.get("last_output_dir") or ""),
        last_preset_id=str(data.get("last_preset_id") or DEFAULT_PRESET_ID),
        window_width=_positive_int(data.get("window_width"), DEFAULT_WIDTH),
        window_height=_positive_int(data.get("window_height"), DEFAULT_HEIGHT),
    )


def save_settings(settings: AppSettings) -> None:
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return


def _positive_int(value: object, default: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default
