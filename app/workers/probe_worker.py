from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.command_runner import run
from app.core.ffprobe_service import build_cmd, parse
from app.core.media_info import PROBE_FAILED_MESSAGE, file_size_bytes


class ProbeWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, ffprobe: str, path: str, parent=None) -> None:
        super().__init__(parent)
        self._ffprobe = ffprobe
        self._path = path

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return
            size = file_size_bytes(self._path)
            if size is None:
                size = 0
            if not Path(self._path).is_file():
                self.failed.emit(PROBE_FAILED_MESSAGE)
                return
            cmd = build_cmd(self._ffprobe, self._path)
            if self.isInterruptionRequested():
                return
            result = run(cmd, timeout=30.0)
            if self.isInterruptionRequested():
                return
            info = parse(result.stdout, self._path, size)
            if result.returncode != 0 and info.video_codec is None:
                info.warning = PROBE_FAILED_MESSAGE
            self.finished_ok.emit(info)
        except Exception:
            self.failed.emit(PROBE_FAILED_MESSAGE)
