from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QProcess, Signal

from app.core.ffmpeg_service import (
    MSG_CANCELLED,
    delete_output_file,
    humanize_ffmpeg_error,
    parse_out_time_sec,
    percent_from_out_time_sec,
)


class ConvertWorker(QObject):
    started = Signal()
    log_line = Signal(str)
    progress = Signal(int)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        if sys.platform == "win32":
            self._enable_no_window()
        self._output_path = ""
        self._preset_id = ""
        self._duration_sec: float | None = None
        self._stderr_buffer = ""
        self._stderr_all = ""
        self._stdout_buffer = ""
        self._last_out_time = -1.0
        self._last_percent = -1
        self._cancelled = False
        self._done = False

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def start_convert(
        self,
        argv: list[str],
        output_path: str,
        preset_id: str = "",
        duration_sec: float | None = None,
    ) -> None:
        if self.is_running() or len(argv) < 2:
            return
        self._output_path = output_path
        self._preset_id = preset_id
        self._duration_sec = duration_sec
        self._stderr_buffer = ""
        self._stderr_all = ""
        self._stdout_buffer = ""
        self._last_out_time = -1.0
        self._last_percent = -1
        self._cancelled = False
        self._done = False
        self._process.setProgram(argv[0])
        self._process.setArguments(argv[1:])
        self.started.emit()
        self._process.start()

    def cancel(self) -> None:
        if not self.is_running():
            return
        self._cancelled = True
        self._process.terminate()
        if not self._process.waitForFinished(3000):
            self._process.kill()
            self._process.waitForFinished(3000)

    def _enable_no_window(self) -> None:
        create_no_window = 0x08000000
        try:
            modifier = self._process.setCreateProcessArgumentsModifier

            def _no_console(args: object) -> None:
                flags = getattr(args, "flags", None)
                if flags is not None:
                    args.flags = int(flags) | create_no_window

            modifier(_no_console)
        except Exception:
            return

    def _on_stderr(self) -> None:
        chunk = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_all += chunk
        self._stderr_buffer += chunk.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in self._stderr_buffer:
            line, self._stderr_buffer = self._stderr_buffer.split("\n", 1)
            if line.strip():
                self.log_line.emit(line)

    def _on_stdout(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += chunk.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split("\n", 1)
            self._handle_progress_line(line)

    def _handle_progress_line(self, line: str) -> None:
        if self._cancelled or self._done:
            return
        duration = self._duration_sec
        if duration is None or duration <= 0:
            return
        out_time = parse_out_time_sec(line, duration)
        if out_time is None:
            return
        if self._last_out_time >= 0 and out_time + 0.05 < self._last_out_time:
            return
        self._last_out_time = out_time
        percent = percent_from_out_time_sec(out_time, duration)
        if percent == self._last_percent:
            return
        self._last_percent = percent
        self.progress.emit(percent)

    def _emit_ok(self) -> None:
        if self._done:
            return
        self._done = True
        self.finished_ok.emit(self._output_path)

    def _emit_failed(self, message: str) -> None:
        if self._done:
            return
        self._done = True
        self.failed.emit(message)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error != QProcess.ProcessError.FailedToStart:
            return
        if self.is_running():
            return
        if self._cancelled:
            delete_output_file(self._output_path)
            self._emit_failed(MSG_CANCELLED)
            return
        self._emit_failed(humanize_ffmpeg_error(self._stderr_all, self._preset_id))

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self._stdout_buffer.strip():
            self._handle_progress_line(self._stdout_buffer)
            self._stdout_buffer = ""
        if self._stderr_buffer.strip():
            self.log_line.emit(self._stderr_buffer.strip())
            self._stderr_buffer = ""
        self.log_line.emit(f"退出码：{exit_code}")
        if self._cancelled:
            delete_output_file(self._output_path)
            self._emit_failed(MSG_CANCELLED)
            return
        if exit_code == 0:
            self._emit_ok()
            return
        self._emit_failed(humanize_ffmpeg_error(self._stderr_all, self._preset_id))
