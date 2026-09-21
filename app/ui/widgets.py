from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QIcon,
    QPainter,
    QPixmap,
    QPolygon,
    QResizeEvent,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.media_info import (
    UNKNOWN,
    MediaInfo,
    file_size_bytes,
    format_bit_rate,
    format_codec,
    format_duration,
    format_fps,
    format_resolution,
    format_size,
)

INFO_ROWS = (
    "文件名",
    "路径",
    "大小",
    "时长",
    "分辨率",
    "视频编码",
    "音频编码",
    "帧率",
    "比特率",
)

EMPTY_VALUE = "—"
PLACEHOLDER_THUMB = "暂无封面"
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv"}
MSG_MULTI_FILES = "一次只能转换一个文件，已使用第一个视频。"
MSG_NOT_VIDEO = "请拖入视频文件。"
PLAY_BTN_SIZE = 64


def _apple_play_icon(size: int = PLAY_BTN_SIZE) -> QIcon:
    """圆形半透明底 + 白色三角（播放）。"""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    # 轻微高光环，接近系统控件质感
    painter.setBrush(QColor(255, 255, 255, 28))
    painter.drawEllipse(3, 3, size - 6, size - 6)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawEllipse(5, 5, size - 10, size - 10)
    painter.setBrush(QColor(255, 255, 255))
    # 三角略偏右，视觉居中
    tri = QPolygon(
        [
            QPoint(int(size * 0.40), int(size * 0.30)),
            QPoint(int(size * 0.40), int(size * 0.70)),
            QPoint(int(size * 0.72), int(size * 0.50)),
        ]
    )
    painter.drawPolygon(tri)
    painter.end()
    return QIcon(pix)


def _apple_pause_icon(size: int = PLAY_BTN_SIZE) -> QIcon:
    """圆形半透明底 + 白色双竖条（暂停）。"""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.setBrush(QColor(255, 255, 255, 28))
    painter.drawEllipse(3, 3, size - 6, size - 6)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawEllipse(5, 5, size - 10, size - 10)
    painter.setBrush(QColor(255, 255, 255))
    bar_w = size * 0.10
    bar_h = size * 0.36
    top = (size - bar_h) / 2
    gap = size * 0.08
    left1 = size / 2 - gap / 2 - bar_w
    left2 = size / 2 + gap / 2
    radius = bar_w / 2
    painter.drawRoundedRect(QRectF(left1, top, bar_w, bar_h), radius, radius)
    painter.drawRoundedRect(QRectF(left2, top, bar_w, bar_h), radius, radius)
    painter.end()
    return QIcon(pix)


class DropZone(QFrame):
    select_clicked = Signal()
    clear_clicked = Signal()
    file_dropped = Signal(str)
    drop_hint = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(72)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.setProperty("dropActive", False)

        self.btn_select = QPushButton("选择视频")
        self.btn_select.setObjectName("btnSelect")
        self.btn_select.setFixedHeight(32)
        self.btn_select.setMinimumWidth(104)
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.setFlat(False)
        self.btn_select.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.btn_select.setStyleSheet(
            "QPushButton#btnSelect {"
            "  background-color: #f4f4f4;"
            "  color: #0d0d0d;"
            "  border: 1px solid rgba(13, 13, 13, 0.12);"
            "  border-radius: 8px;"
            "  padding: 0 16px;"
            "  font-weight: 600;"
            "}"
            "QPushButton#btnSelect:hover {"
            "  background-color: #ebebeb;"
            "  border-color: rgba(13, 13, 13, 0.20);"
            "}"
            "QPushButton#btnSelect:pressed {"
            "  background-color: #e2e2e2;"
            "}"
            "QPushButton#btnSelect:disabled {"
            "  background-color: rgba(13, 13, 13, 0.03);"
            "  color: rgba(13, 13, 13, 0.35);"
            "  border-color: rgba(13, 13, 13, 0.08);"
            "}"
        )
        self.btn_select.clicked.connect(self.select_clicked.emit)

        self.btn_clear = QPushButton("清除")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.setFixedHeight(32)
        self.btn_clear.setMinimumWidth(72)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setEnabled(False)
        self.btn_clear.setToolTip("清除当前已选视频")
        self.btn_clear.clicked.connect(self.clear_clicked.emit)

        hint = QLabel("或把视频拖到这里")
        hint.setObjectName("dropHint")
        hint.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        sub = QLabel("支持 mp4 / mkv / mov / avi / webm / flv / wmv")
        sub.setObjectName("dropSubHint")
        sub.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        text_col.addWidget(hint)
        text_col.addWidget(sub)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        layout.addWidget(self.btn_select, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text_col, stretch=1)

    def set_has_file(self, has_file: bool) -> None:
        self.btn_clear.setEnabled(has_file)


    def _set_active(self, active: bool) -> None:
        self.setProperty("dropActive", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._set_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_active(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_active(False)
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        paths = [url.toLocalFile() for url in urls if url.toLocalFile()]
        if not paths:
            event.ignore()
            return
        video_paths = [
            path
            for path in paths
            if Path(path).is_file() and Path(path).suffix.lower() in VIDEO_SUFFIXES
        ]
        if not video_paths:
            self.drop_hint.emit(MSG_NOT_VIDEO)
            event.acceptProposedAction()
            return
        if len(paths) > 1 or len(video_paths) > 1:
            self.drop_hint.emit(MSG_MULTI_FILES)
        self.file_dropped.emit(video_paths[0])
        event.acceptProposedAction()


class ThumbnailLabel(QLabel):
    """按源画面真实比例完整显示：竖屏竖着看，小视频不硬拉满。"""

    def __init__(self, parent=None) -> None:
        super().__init__(PLACEHOLDER_THUMB, parent)
        self.setObjectName("thumbLabel")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setScaledContents(False)
        self._source: QPixmap | None = None
        self._aspect_w = 16
        self._aspect_h = 9

    def set_media_aspect(self, width: int | None, height: int | None) -> None:
        if width and height and width > 0 and height > 0:
            self._aspect_w = int(width)
            self._aspect_h = int(height)

    def clear_media_aspect(self) -> None:
        self._aspect_w = 16
        self._aspect_h = 9

    def aspect_ratio(self) -> float:
        return self._aspect_w / max(self._aspect_h, 1)

    def source_pixel_size(self) -> QSize | None:
        if self._source is None or self._source.isNull():
            return None
        return self._source.size()

    def show_placeholder(self, text: str = PLACEHOLDER_THUMB) -> None:
        self._source = None
        self.setPixmap(QPixmap())
        self.setText(text)
        self.setToolTip(text if text != PLACEHOLDER_THUMB else "")

    def show_image(self, path: str) -> bool:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return False
        pixmap.setDevicePixelRatio(1.0)
        self._source = pixmap
        if pixmap.width() > 0 and pixmap.height() > 0:
            self._aspect_w = pixmap.width()
            self._aspect_h = pixmap.height()
        self.setText("")
        self.setToolTip("")
        self._rescale()
        return True

    def _rescale(self) -> None:
        if self._source is None:
            return
        rect = self.contentsRect()
        if rect.width() < 2 or rect.height() < 2:
            return
        dpr = float(self.devicePixelRatioF() or 1.0)
        target_w = max(int(rect.width() * dpr), 1)
        target_h = max(int(rect.height() * dpr), 1)
        # 不超过源像素：小分辨率视频保持「小」
        target_w = min(target_w, max(self._source.width(), 1))
        target_h = min(target_h, max(self._source.height(), 1))
        scaled = self._source.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        self.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rescale()


class ThumbnailPane(QWidget):
    """右侧预览：默认停在正封面，点「播放」后在窗内播放源视频。"""

    play_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("thumbPane")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._source_path = ""
        self._playing = False

        self._stage = QWidget(self)
        self._stage.setObjectName("previewStage")

        self.thumb_label = ThumbnailLabel(self._stage)
        self.video_widget = QVideoWidget(self._stage)
        self.video_widget.setObjectName("videoWidget")
        self.video_widget.hide()

        self.btn_play = QPushButton(self._stage)
        self.btn_play.setObjectName("btnPreviewPlay")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setFixedSize(PLAY_BTN_SIZE, PLAY_BTN_SIZE)
        self.btn_play.setEnabled(False)
        self.btn_play.setFlat(True)
        self.btn_play.setIconSize(QSize(PLAY_BTN_SIZE, PLAY_BTN_SIZE))
        self._icon_play = _apple_play_icon()
        self._icon_pause = _apple_pause_icon()
        self.btn_play.setIcon(self._icon_play)
        self.btn_play.setToolTip("播放")
        self.btn_play.clicked.connect(self._on_play_clicked)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addStretch(1)
        outer.addWidget(self._stage, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addStretch(1)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self.video_widget)
        self._player.playbackStateChanged.connect(self._on_playback_state)
        self._player.errorOccurred.connect(self._on_player_error)

    def set_media_aspect(self, width: int | None, height: int | None) -> None:
        self.thumb_label.set_media_aspect(width, height)
        self._layout_thumb()

    def clear_media_aspect(self) -> None:
        self.thumb_label.clear_media_aspect()
        self._layout_thumb()

    def set_source_video(self, path: str | None) -> None:
        self.stop_playback()
        self._source_path = path or ""
        can_play = bool(self._source_path and Path(self._source_path).is_file())
        self.btn_play.setEnabled(can_play)
        self._set_play_icon(playing=False)
        self.btn_play.show()
        self._show_cover()

    def stop_playback(self) -> None:
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._player.stop()
        self._playing = False
        self._set_play_icon(playing=False)
        self._show_cover()

    def _set_play_icon(self, *, playing: bool) -> None:
        if playing:
            self.btn_play.setIcon(self._icon_pause)
            self.btn_play.setToolTip("暂停")
        else:
            self.btn_play.setIcon(self._icon_play)
            self.btn_play.setToolTip("播放")

    def _show_cover(self) -> None:
        self.video_widget.hide()
        self.thumb_label.show()
        self.btn_play.show()
        self.btn_play.raise_()

    def _show_video(self) -> None:
        self.thumb_label.hide()
        self.video_widget.show()
        self.btn_play.show()
        self.btn_play.raise_()

    def _on_play_clicked(self) -> None:
        if not self._source_path:
            return
        if self._playing:
            self._player.pause()
            return
        self._show_video()
        self._player.setSource(
            QUrl.fromLocalFile(str(Path(self._source_path).resolve()))
        )
        self._player.play()
        self.play_clicked.emit()

    def _on_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._playing = playing
        if playing:
            self._set_play_icon(playing=True)
            self._show_video()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._set_play_icon(playing=False)
        else:
            self._set_play_icon(playing=False)
            self._show_cover()

    def _on_player_error(self, *_args: object) -> None:
        self._playing = False
        self._set_play_icon(playing=False)
        self._show_cover()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._layout_thumb()

    def _layout_thumb(self) -> None:
        area_w = max(self.width() - 8, 1)
        area_h = max(self.height() - 8, 1)
        ratio = self.thumb_label.aspect_ratio()

        if area_w / max(area_h, 1) >= ratio:
            box_h = area_h
            box_w = max(int(box_h * ratio), 1)
        else:
            box_w = area_w
            box_h = max(int(box_w / ratio), 1)

        src = self.thumb_label.source_pixel_size()
        if src is not None and not self._playing:
            box_w = min(box_w, max(src.width(), 1))
            box_h = min(box_h, max(src.height(), 1))
            if box_w / max(box_h, 1) > ratio:
                box_w = max(int(box_h * ratio), 1)
            else:
                box_h = max(int(box_w / ratio), 1)

        box_w = max(box_w, 1)
        box_h = max(box_h, 1)
        self._stage.setFixedSize(box_w, box_h)
        self.thumb_label.setGeometry(0, 0, box_w, box_h)
        self.video_widget.setGeometry(0, 0, box_w, box_h)
        self.thumb_label._rescale()
        self.btn_play.move(
            max((box_w - self.btn_play.width()) // 2, 0),
            max((box_h - self.btn_play.height()) // 2, 0),
        )
        self.btn_play.raise_()


class InfoTable(QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(len(INFO_ROWS), 2, parent)
        self.setObjectName("infoTable")
        self.setHorizontalHeaderLabels(["项目", "内容"])
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setShowGrid(False)
        for row, key in enumerate(INFO_ROWS):
            self.setItem(row, 0, QTableWidgetItem(key))
            self.setItem(row, 1, QTableWidgetItem(EMPTY_VALUE))
        self._full_path = ""

    def set_selected_file(self, path: str) -> None:
        file_path = Path(path)
        self.item(0, 1).setText(file_path.name)
        self.item(0, 1).setToolTip(file_path.name)
        self._full_path = str(file_path)
        self._refresh_path_cell()
        size = file_size_bytes(path)
        self._set_value(2, format_size(size) if size is not None else UNKNOWN)
        for row in range(3, 9):
            self._set_value(row, UNKNOWN)

    def clear(self) -> None:
        self._full_path = ""
        for row in range(len(INFO_ROWS)):
            self._set_value(row, EMPTY_VALUE)
        self.item(0, 1).setToolTip("")
        self.item(1, 1).setToolTip("")

    def apply_media_info(self, info: MediaInfo) -> None:
        self.set_selected_file(info.path)
        self._set_value(2, format_size(info.size_bytes))
        self._set_value(3, format_duration(info.duration_sec))
        self._set_value(4, format_resolution(info.width, info.height))
        self._set_value(5, format_codec(info.video_codec))
        self._set_value(6, format_codec(info.audio_codec))
        self._set_value(7, format_fps(info.fps))
        self._set_value(8, format_bit_rate(info.bit_rate))

    def _set_value(self, row: int, text: str) -> None:
        item = self.item(row, 1)
        item.setText(text)
        item.setToolTip(text)

    def _refresh_path_cell(self) -> None:
        item = self.item(1, 1)
        if not self._full_path:
            item.setText(EMPTY_VALUE)
            item.setToolTip("")
            return
        item.setToolTip(self._full_path)
        width = max(self.columnWidth(1) - 16, 40)
        item.setText(
            self.fontMetrics().elidedText(
                self._full_path, Qt.TextElideMode.ElideMiddle, width
            )
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_path_cell()
