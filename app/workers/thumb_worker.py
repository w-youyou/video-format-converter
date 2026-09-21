from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.command_runner import run
from app.core.ffmpeg_service import build_thumbnail_cmd, next_thumbnail_path

THUMB_FAILED_PREFIX = "无法生成封面："


class ThumbWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        ffmpeg: str,
        input_path: str,
        duration_sec: float | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ffmpeg = ffmpeg
        self._input_path = input_path
        self._duration_sec = duration_sec

    def run(self) -> None:
        output = next_thumbnail_path()
        try:
            if self.isInterruptionRequested():
                return
            cmd = build_thumbnail_cmd(
                self._ffmpeg, self._input_path, output, self._duration_sec
            )
            result = run(cmd, timeout=30.0)
            if self.isInterruptionRequested():
                Path(output).unlink(missing_ok=True)
                return
            if (
                result.returncode == 0
                and Path(output).is_file()
                and Path(output).stat().st_size > 0
            ):
                self.finished_ok.emit(output)
                return
            Path(output).unlink(missing_ok=True)
            reason = (result.stderr or result.stdout or "抽帧失败").strip()
            reason = reason.splitlines()[-1] if reason else "抽帧失败"
            self.failed.emit(f"{THUMB_FAILED_PREFIX}{reason}")
        except Exception as exc:
            Path(output).unlink(missing_ok=True)
            self.failed.emit(f"{THUMB_FAILED_PREFIX}{exc}")
