from pathlib import Path
import os
import subprocess
import sys
import time

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.ffmpeg_service import (
    MSG_CANCELLED,
    MSG_NO_AUDIO,
    MSG_SAME_FILE,
    build_convert_cmd,
    default_output_path,
    delete_thumbnail_file,
    format_argv_for_copy,
    is_same_media_path,
    replace_output_suffix,
)
from app.core.media_info import (
    MediaInfo,
    PROBE_FAILED_MESSAGE,
    format_size_change,
)
from app.core.presets import Preset, all_presets, get_preset
from app.core.which_ffmpeg import find_ffmpeg, find_ffprobe
from app.settings import AppSettings, load_settings, save_settings
from app.ui.widgets import DropZone, InfoTable, ThumbnailPane
from app.workers.convert_worker import ConvertWorker
from app.workers.probe_worker import ProbeWorker
from app.workers.thumb_worker import THUMB_FAILED_PREFIX, ThumbWorker

WINDOW_TITLE = "视频格式转换器"
VIDEO_FILTER = "视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv);;所有文件 (*.*)"
MSG_TOOLS_OK = "已检测到 ffmpeg，请选择视频"
MSG_TOOLS_MISSING = (
    "未找到 ffmpeg/ffprobe。请安装后将其加入 PATH，或设置环境变量 VFC_FFMPEG。"
)
MSG_DONE = "转换完成"
MSG_PRIMARY_START = "开始转换"
MSG_PRIMARY_BUSY = "转换中…"
MSG_PRIMARY_OPEN = "打开所在文件夹"
MSG_OPEN_FILE = "打开文件"
MSG_OVERWRITE = "文件已存在，是否覆盖？"
MSG_CLOSE_CONFIRM = "正在转换，确定要退出吗？退出将取消当前任务。"
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(960, 640)
        self._settings = load_settings()
        self.resize(self._settings.window_width, self._settings.window_height)
        self._ffmpeg_path: str | None = None
        self._ffprobe_path: str | None = None
        self._tools_ok = False
        self._converting = False
        self._primary_mode = "start"
        self._last_output_path = ""
        self._convert_duration: float | None = None
        self._convert_t0 = 0.0
        self._user_cancelled = False
        self._syncing_output = False
        self._probe_worker: ProbeWorker | None = None
        self._thumb_worker: ThumbWorker | None = None
        self._media_info: MediaInfo | None = None
        self._thumb_path: str | None = None
        self._has_input = False
        self._build_ui()
        self._apply_saved_preset()
        self._convert_worker = ConvertWorker(self)
        self._convert_worker.started.connect(self._on_convert_started)
        self._convert_worker.progress.connect(self._on_convert_progress)
        self._convert_worker.log_line.connect(self._append_log)
        self._convert_worker.finished_ok.connect(self._on_convert_ok)
        self._convert_worker.failed.connect(self._on_convert_failed)
        self._detect_tools()
        self._sync_filename_from_path()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("mainRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.missing_banner = QLabel("")
        self.missing_banner.setObjectName("missingBanner")
        self.missing_banner.setWordWrap(True)
        self.missing_banner.hide()
        layout.addWidget(self.missing_banner)

        self.drop_zone = DropZone()
        self.drop_zone.select_clicked.connect(self._on_select_video)
        self.drop_zone.clear_clicked.connect(self._on_clear_video)
        self.drop_zone.file_dropped.connect(self._on_file_chosen)
        self.drop_zone.drop_hint.connect(self._on_drop_hint)
        layout.addWidget(self.drop_zone)

        middle = QHBoxLayout()
        middle.setSpacing(12)
        self.info_table = InfoTable()
        self.info_table.setMinimumWidth(360)
        info_card = QFrame()
        info_card.setObjectName("panelCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.addWidget(self.info_table)
        self.thumb_pane = ThumbnailPane()
        self.thumb_label = self.thumb_pane.thumb_label
        # 信息在左，视频预览（封面+播放）在右
        middle.addWidget(info_card, stretch=3)
        middle.addWidget(self.thumb_pane, stretch=2)
        layout.addLayout(middle, stretch=1)

        layout.addLayout(self._build_bottom())

    def _build_bottom(self) -> QVBoxLayout:
        bottom = QVBoxLayout()
        bottom.setSpacing(8)

        row_preset = QHBoxLayout()
        row_preset.addWidget(QLabel("预设"))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        for preset in all_presets():
            self.preset_combo.addItem(preset.name, preset.id)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        row_preset.addWidget(self.preset_combo, stretch=1)
        row_preset.addWidget(QLabel("输出路径"))
        self.output_edit = QLineEdit()
        self.output_edit.setObjectName("outputEdit")
        self.output_edit.setPlaceholderText("将在选择视频后自动填写")
        row_preset.addWidget(self.output_edit, stretch=2)
        self.btn_browse = QPushButton("浏览…")
        self.btn_browse.setObjectName("btnBrowse")
        self.btn_browse.clicked.connect(self._on_browse_output)
        row_preset.addWidget(self.btn_browse)
        bottom.addLayout(row_preset)

        row_filename = QHBoxLayout()
        row_filename.addWidget(QLabel("最终文件名"))
        self.filename_edit = QLineEdit()
        self.filename_edit.setObjectName("outputPreview")
        self.filename_edit.setPlaceholderText("选择视频后可修改输出文件名")
        row_filename.addWidget(self.filename_edit, stretch=1)
        self.filename_suffix_label = QLabel("")
        self.filename_suffix_label.setObjectName("filenameSuffix")
        self.filename_suffix_label.setMinimumWidth(48)
        row_filename.addWidget(self.filename_suffix_label)
        bottom.addLayout(row_filename)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        bottom.addWidget(self.progress_bar)

        self.status_label = QLabel("请选择视频")
        self.status_label.setObjectName("statusLabel")
        bottom.addWidget(self.status_label)

        row_buttons = QHBoxLayout()
        self.btn_primary = QPushButton(MSG_PRIMARY_START)
        self.btn_primary.setObjectName("btnPrimary")
        self.btn_primary.setEnabled(False)
        self.btn_primary.clicked.connect(self._on_primary_clicked)
        self.btn_open_file = QPushButton(MSG_OPEN_FILE)
        self.btn_open_file.setObjectName("btnOpenFile")
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.clicked.connect(self._on_open_file)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_convert)
        self.btn_toggle_log = QPushButton("详细日志")
        self.btn_toggle_log.setObjectName("btnToggleLog")
        self.btn_toggle_log.setCheckable(True)
        row_buttons.addWidget(self.btn_primary)
        row_buttons.addWidget(self.btn_open_file)
        row_buttons.addWidget(self.btn_cancel)
        row_buttons.addStretch(1)
        row_buttons.addWidget(self.btn_toggle_log)
        bottom.addLayout(row_buttons)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(120)
        self.log_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.log_view.hide()
        self.btn_toggle_log.toggled.connect(self.log_view.setVisible)
        bottom.addWidget(self.log_view)
        self.output_edit.textChanged.connect(self._on_output_changed)
        self.filename_edit.textChanged.connect(self._on_filename_changed)
        self.filename_edit.editingFinished.connect(self._normalize_filename_edit)
        self._refresh_suffix_label()
        return bottom

    def _apply_saved_preset(self) -> None:
        preset_id = self._settings.last_preset_id
        for index in range(self.preset_combo.count()):
            if self.preset_combo.itemData(index) == preset_id:
                self.preset_combo.setCurrentIndex(index)
                return

    def _current_preset(self) -> Preset:
        preset_id = self.preset_combo.currentData()
        if isinstance(preset_id, str):
            return get_preset(preset_id)
        return all_presets()[0]

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def _sanitize_stem(self, stem: str) -> str:
        cleaned = "".join(
            "_" if ch in _INVALID_FILENAME_CHARS or ord(ch) < 32 else ch for ch in stem
        )
        return cleaned.strip(" .")

    def _refresh_suffix_label(self) -> None:
        self.filename_suffix_label.setText(self._current_preset().suffix)

    def _output_parent_dir(self) -> Path:
        current = self.output_edit.text().strip()
        if current:
            parent = Path(current).parent
            if str(parent):
                return parent
        if self._settings.last_output_dir:
            return Path(self._settings.last_output_dir)
        if self._media_info and self._media_info.path:
            return Path(self._media_info.path).parent
        return Path.cwd()

    def _sync_filename_from_path(self) -> None:
        if self._syncing_output:
            return
        self._syncing_output = True
        try:
            self._refresh_suffix_label()
            output = self.output_edit.text().strip()
            if not output:
                self.filename_edit.clear()
                return
            self.filename_edit.setText(Path(output).stem)
        finally:
            self._syncing_output = False

    def _apply_filename_to_path(self) -> None:
        if self._syncing_output:
            return
        stem = self._sanitize_stem(self.filename_edit.text())
        if not stem:
            return
        preset = self._current_preset()
        new_path = str(self._output_parent_dir() / f"{stem}{preset.suffix}")
        if self.output_edit.text() == new_path:
            return
        self._syncing_output = True
        try:
            self.output_edit.setText(new_path)
            self._refresh_suffix_label()
        finally:
            self._syncing_output = False

    def _normalize_filename_edit(self) -> None:
        if self._syncing_output:
            return
        stem = self._sanitize_stem(self.filename_edit.text())
        if stem != self.filename_edit.text():
            self._syncing_output = True
            try:
                self.filename_edit.setText(stem)
            finally:
                self._syncing_output = False
        self._apply_filename_to_path()

    def _persist_settings(self) -> None:
        settings = AppSettings(
            last_input_dir=self._settings.last_input_dir,
            last_output_dir=self._settings.last_output_dir,
            last_preset_id=self._current_preset().id,
            window_width=max(self.width(), 960),
            window_height=max(self.height(), 640),
        )
        if self._media_info and self._media_info.path:
            settings.last_input_dir = str(Path(self._media_info.path).parent)
        output = self.output_edit.text().strip()
        if output:
            settings.last_output_dir = str(Path(output).parent)
        self._settings = settings
        save_settings(settings)

    def _reset_primary_to_start(self) -> None:
        if self._converting:
            return
        self._primary_mode = "start"
        self.btn_primary.setText(MSG_PRIMARY_START)
        self.btn_open_file.setEnabled(False)
        self._update_primary_enabled()

    def _set_busy(self, busy: bool) -> None:
        self._converting = busy
        self.drop_zone.setEnabled(not busy)
        self.drop_zone.setAcceptDrops(not busy)
        self.drop_zone.btn_select.setEnabled(not busy)
        self.drop_zone.set_has_file((not busy) and self._has_input)
        self.preset_combo.setEnabled(not busy)
        self.output_edit.setEnabled(not busy)
        self.filename_edit.setEnabled(not busy)
        self.btn_browse.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.btn_open_file.setEnabled(False)
        self.thumb_pane.btn_play.setEnabled(
            (not busy)
            and bool(self._media_info and self._media_info.path)
            and self._media_info.video_codec is not None
        )
        if busy:
            self.thumb_pane.stop_playback()
            self._primary_mode = "converting"
            self.btn_primary.setText(MSG_PRIMARY_BUSY)
            self.btn_primary.setEnabled(False)
            duration = self._convert_duration
            if duration is not None and duration > 0:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(0)
            else:
                self.progress_bar.setRange(0, 0)
            return
        self.progress_bar.setRange(0, 100)
        self._reset_primary_to_start()

    def _update_primary_enabled(self) -> None:
        if self._converting:
            self.btn_primary.setEnabled(False)
            return
        if self._primary_mode == "open":
            self.btn_primary.setEnabled(bool(self._last_output_path))
            self.btn_open_file.setEnabled(bool(self._last_output_path))
            return
        preset = self._current_preset()
        output = self.output_edit.text().strip()
        info = self._media_info
        has_source = info is not None and bool(info.path)
        can_start = bool(
            has_source and self._tools_ok and output and self._ffmpeg_path
        )
        if has_source and info is not None and is_same_media_path(info.path, output):
            can_start = False
        if preset.id == "mp3_audio" and (info is None or info.audio_codec is None):
            can_start = False
        self.btn_primary.setEnabled(can_start)
        self.btn_open_file.setEnabled(False)

    def _detect_tools(self) -> None:
        self._ffmpeg_path = find_ffmpeg()
        self._ffprobe_path = find_ffprobe()
        self._tools_ok = bool(self._ffmpeg_path and self._ffprobe_path)
        self.btn_primary.setEnabled(False)

        if self._ffmpeg_path:
            self._append_log(f"ffmpeg: {self._ffmpeg_path}")
        else:
            self._append_log("ffmpeg: 未找到")
        if self._ffprobe_path:
            self._append_log(f"ffprobe: {self._ffprobe_path}")
        else:
            self._append_log("ffprobe: 未找到")

        if self._tools_ok:
            self.missing_banner.hide()
            self.status_label.setText(MSG_TOOLS_OK)
            return

        self.missing_banner.setText(MSG_TOOLS_MISSING)
        self.missing_banner.show()
        self.status_label.setText(MSG_TOOLS_MISSING)

    def _on_drop_hint(self, message: str) -> None:
        self.status_label.setText(message)
        self._append_log(message)

    def _on_select_video(self) -> None:
        if self._converting:
            return
        start_dir = self._settings.last_input_dir or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频", start_dir, VIDEO_FILTER
        )
        if path:
            self._on_file_chosen(path)

    def _on_clear_video(self) -> None:
        if self._converting:
            return
        self._stop_probe()
        self._stop_thumb()
        self.thumb_pane.stop_playback()
        self._media_info = None
        self._last_output_path = ""
        self._has_input = False
        self._clear_thumbnail()
        self.thumb_pane.clear_media_aspect()
        self.thumb_pane.set_source_video(None)
        self.info_table.clear()
        self._syncing_output = True
        try:
            self.output_edit.clear()
            self.filename_edit.clear()
        finally:
            self._syncing_output = False
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setToolTip("")
        if self._tools_ok:
            self.status_label.setText(MSG_TOOLS_OK)
        else:
            self.status_label.setText(MSG_TOOLS_MISSING)
        self.drop_zone.set_has_file(False)
        self._reset_primary_to_start()
        self._update_primary_enabled()
        self._append_log("已清除当前视频")

    def _on_browse_output(self) -> None:
        if self._converting:
            return
        preset = self._current_preset()
        current = self.output_edit.text().strip()
        start = current or self._settings.last_output_dir or ""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "浏览…",
            start,
            f"输出文件 (*{preset.suffix});;所有文件 (*.*)",
        )
        if path:
            self.output_edit.setText(replace_output_suffix(path, preset.suffix))

    def _on_output_changed(self, _text: str = "") -> None:
        self._sync_filename_from_path()
        self._reset_primary_to_start()

    def _on_filename_changed(self, _text: str = "") -> None:
        self._apply_filename_to_path()
        self._reset_primary_to_start()

    def _on_preset_changed(self, _index: int = 0) -> None:
        preset = self._current_preset()
        self._refresh_suffix_label()
        current = self.output_edit.text().strip()
        if current:
            self.output_edit.setText(replace_output_suffix(current, preset.suffix))
        elif self._media_info:
            self.output_edit.setText(
                default_output_path(self._media_info.path, preset.suffix)
            )
        self._sync_filename_from_path()
        if (
            preset.id == "mp3_audio"
            and self._media_info is not None
            and self._media_info.audio_codec is None
        ):
            self.status_label.setText(MSG_NO_AUDIO)
        elif self._media_info is not None and self._tools_ok and not self._converting:
            if self._primary_mode != "open":
                self.status_label.setText(MSG_TOOLS_OK)
        self._reset_primary_to_start()

    def _on_file_chosen(self, path: str) -> None:
        if self._converting:
            return
        self._settings.last_input_dir = str(Path(path).parent)
        self._last_output_path = ""
        self._has_input = True
        self.drop_zone.set_has_file(True)
        self._reset_primary_to_start()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._media_info = None
        self.thumb_pane.clear_media_aspect()
        self.thumb_pane.set_source_video(None)
        self._clear_thumbnail()
        self.info_table.set_selected_file(path)
        self.status_label.setToolTip(path)
        preset = self._current_preset()
        self.output_edit.setText(default_output_path(path, preset.suffix))
        self._update_primary_enabled()
        if not self._tools_ok or not self._ffprobe_path:
            self.status_label.setText(MSG_TOOLS_MISSING)
            return
        self.status_label.setText("正在读取视频信息…")
        self._start_probe(path)

    def _start_probe(self, path: str) -> None:
        self._stop_probe()
        worker = ProbeWorker(self._ffprobe_path or "", path, self)
        worker.finished_ok.connect(self._on_probe_ok)
        worker.failed.connect(self._on_probe_failed)
        self._probe_worker = worker
        worker.start()

    def _stop_probe(self) -> None:
        worker = self._probe_worker
        if worker is None:
            return
        self._probe_worker = None
        try:
            worker.finished_ok.disconnect(self._on_probe_ok)
        except (TypeError, RuntimeError):
            pass
        try:
            worker.failed.disconnect(self._on_probe_failed)
        except (TypeError, RuntimeError):
            pass
        if worker.isRunning():
            worker.requestInterruption()
            worker.wait(3000)

    def _on_probe_ok(self, info: object) -> None:
        if not isinstance(info, MediaInfo):
            self._on_probe_failed(PROBE_FAILED_MESSAGE)
            return
        self._media_info = info
        self.info_table.apply_media_info(info)
        self.thumb_pane.set_media_aspect(info.width, info.height)
        self.thumb_pane.set_source_video(info.path)
        self._on_preset_changed()
        if info.warning or info.video_codec is None:
            self.status_label.setText(PROBE_FAILED_MESSAGE)
            self.thumb_label.show_placeholder(
                f"{THUMB_FAILED_PREFIX}没有视频画面"
            )
            self.thumb_pane.btn_play.setEnabled(False)
        elif self._tools_ok:
            self.status_label.setText(MSG_TOOLS_OK)
            self._start_thumb(info)

        if (
            self._current_preset().id == "mp3_audio"
            and info.audio_codec is None
        ):
            self.status_label.setText(MSG_NO_AUDIO)
        self._append_log(f"已读取：{info.filename}")
        self._update_primary_enabled()

    def _on_probe_failed(self, message: str) -> None:
        self._media_info = None
        self.status_label.setText(message or PROBE_FAILED_MESSAGE)
        self.thumb_label.show_placeholder(f"{THUMB_FAILED_PREFIX}无法读取视频")
        self._append_log(message or PROBE_FAILED_MESSAGE)
        self._update_primary_enabled()

    def _start_thumb(self, info: MediaInfo) -> None:
        if not self._ffmpeg_path:
            self.thumb_label.show_placeholder(f"{THUMB_FAILED_PREFIX}未找到 ffmpeg")
            return
        self._stop_thumb()
        worker = ThumbWorker(
            self._ffmpeg_path, info.path, info.duration_sec, self
        )
        worker.finished_ok.connect(self._on_thumb_ok)
        worker.failed.connect(self._on_thumb_failed)
        self._thumb_worker = worker
        worker.start()

    def _stop_thumb(self) -> None:
        worker = self._thumb_worker
        if worker is None:
            return
        self._thumb_worker = None
        try:
            worker.finished_ok.disconnect(self._on_thumb_ok)
        except (TypeError, RuntimeError):
            pass
        try:
            worker.failed.disconnect(self._on_thumb_failed)
        except (TypeError, RuntimeError):
            pass
        if worker.isRunning():
            worker.requestInterruption()
            worker.wait(3000)

    def _clear_thumbnail(self) -> None:
        self._stop_thumb()
        delete_thumbnail_file(self._thumb_path)
        self._thumb_path = None
        self.thumb_label.show_placeholder()

    def _on_thumb_ok(self, path: str) -> None:
        delete_thumbnail_file(self._thumb_path)
        self._thumb_path = path
        if not self.thumb_label.show_image(path):
            self.thumb_label.show_placeholder(f"{THUMB_FAILED_PREFIX}无法打开封面文件")
            return
        self.thumb_pane._layout_thumb()
        if self._media_info is not None:
            self.thumb_pane.set_source_video(self._media_info.path)

    def _on_thumb_failed(self, message: str) -> None:
        self.thumb_label.show_placeholder(message)
        self._append_log(message)
        if self._media_info is not None:
            # 无封面时仍可播放源文件
            self.thumb_pane.set_source_video(self._media_info.path)

    def _ask_yes_no(self, message: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(WINDOW_TITLE)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(message)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        yes_btn = box.button(QMessageBox.StandardButton.Yes)
        no_btn = box.button(QMessageBox.StandardButton.No)
        if yes_btn is not None:
            yes_btn.setText("是")
        if no_btn is not None:
            no_btn.setText("否")
        return box.exec() == QMessageBox.StandardButton.Yes

    def _on_primary_clicked(self) -> None:
        if self._converting:
            return
        if self._primary_mode == "open":
            self._open_output_folder(self._last_output_path)
            return
        self._on_start_convert()

    def _on_open_file(self) -> None:
        if self._converting or not self._last_output_path:
            return
        path = self._last_output_path
        if not Path(path).is_file():
            self.status_label.setText("输出文件不存在，无法打开。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.normpath(path)))

    def _on_start_convert(self) -> None:
        if self._converting:
            return
        info = self._media_info
        output = self.output_edit.text().strip()
        preset = self._current_preset()
        if info is None or not self._ffmpeg_path or not output:
            return
        if is_same_media_path(info.path, output):
            self.status_label.setText(MSG_SAME_FILE)
            return
        if preset.id == "mp3_audio" and info.audio_codec is None:
            self.status_label.setText(MSG_NO_AUDIO)
            self._update_primary_enabled()
            return
        overwrite = False
        if Path(output).exists():
            if not self._ask_yes_no(MSG_OVERWRITE):
                return
            overwrite = True
        argv = build_convert_cmd(
            self._ffmpeg_path,
            info.path,
            output,
            preset,
            overwrite=overwrite,
            with_progress=True,
        )
        self._user_cancelled = False
        self._convert_duration = info.duration_sec
        self._settings.last_output_dir = str(Path(output).parent)
        self._append_log(format_argv_for_copy(argv))
        self._convert_worker.start_convert(
            argv, output, preset.id, info.duration_sec
        )

    def _on_cancel_convert(self) -> None:
        if not self._converting:
            return
        self._user_cancelled = True
        self._convert_worker.cancel()

    def _on_convert_started(self) -> None:
        self.thumb_pane.stop_playback()
        self._convert_t0 = time.monotonic()
        self._set_busy(True)
        self.status_label.setText("正在转换…")

    def _on_convert_progress(self, percent: int) -> None:
        if not self._converting:
            return
        value = max(0, min(percent, 99))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        text = f"正在转换… {value}%"
        elapsed = time.monotonic() - self._convert_t0
        if value >= 3 and elapsed >= 0.4:
            remaining = elapsed * (100 - value) / value
            text += f"，{self._format_eta(remaining)}"
        self.status_label.setText(text)

    def _format_eta(self, seconds: float) -> str:
        total = max(int(round(seconds)), 0)
        if total < 60:
            return f"约剩余 {total} 秒"
        minutes, sec = divmod(total, 60)
        if minutes < 60:
            return f"约剩余 {minutes} 分 {sec} 秒"
        hours, minutes = divmod(minutes, 60)
        return f"约剩余 {hours} 小时 {minutes} 分"

    def _on_convert_ok(self, output_path: str) -> None:
        self._converting = False
        self.drop_zone.setEnabled(True)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.btn_select.setEnabled(True)
        self.drop_zone.set_has_file(self._has_input)
        self.preset_combo.setEnabled(True)
        self.output_edit.setEnabled(True)
        self.filename_edit.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self._last_output_path = output_path
        self._primary_mode = "open"
        self.btn_primary.setText(MSG_PRIMARY_OPEN)
        self.btn_primary.setEnabled(True)
        self.btn_open_file.setEnabled(True)

        size_text = ""
        src_bytes = self._media_info.size_bytes if self._media_info else 0
        try:
            dst_bytes = Path(output_path).stat().st_size
        except OSError:
            dst_bytes = 0
        if src_bytes > 0 and dst_bytes > 0:
            size_text = format_size_change(src_bytes, dst_bytes)
            self._append_log(size_text)

        if size_text:
            self.status_label.setText(f"{MSG_DONE}：{size_text}")
        else:
            self.status_label.setText(f"{MSG_DONE}：{output_path}")
        self.status_label.setToolTip(output_path)
        self._append_log(MSG_DONE)
        self._persist_settings()

    def _on_convert_failed(self, message: str) -> None:
        cancelled = self._user_cancelled or message == MSG_CANCELLED
        self._set_busy(False)
        self.progress_bar.setValue(0)
        text = MSG_CANCELLED if cancelled else message
        self.status_label.setText(text)
        self._append_log(text)

    def _open_output_folder(self, path: str) -> None:
        if not path:
            return
        target = os.path.normpath(path)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", target])
            return
        folder = str(Path(target).parent)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._converting or self._convert_worker.is_running():
            if not self._ask_yes_no(MSG_CLOSE_CONFIRM):
                event.ignore()
                return
            self._user_cancelled = True
            self._convert_worker.cancel()
        self.thumb_pane.stop_playback()
        self._persist_settings()
        self._stop_probe()
        self._stop_thumb()
        if self._convert_worker.is_running():
            self._convert_worker.cancel()
        delete_thumbnail_file(self._thumb_path)
        self._thumb_path = None
        super().closeEvent(event)
