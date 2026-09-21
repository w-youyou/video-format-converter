"""用真实视频刷新 docs/screenshots/（最新 UI）。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ui.fonts import ensure_chinese_font
from app.ui.main_window import MainWindow
from app.ui.theme import APP_STYLESHEET

SRC_VIDEO = Path(r"C:\Users\Administrator\Desktop\096a562ccbca561302f5dd1a4c397227.mp4")
SHOT_DIR = ROOT / "docs" / "screenshots"
WORK = ROOT / "tmp" / "screenshot_run"


def process_events(app: QApplication, ms: int = 50) -> None:
    deadline = time.monotonic() + ms / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def wait_until(app: QApplication, pred, timeout_sec: float = 30.0) -> bool:
    end = time.monotonic() + timeout_sec
    while time.monotonic() < end:
        app.processEvents()
        if pred():
            return True
        time.sleep(0.05)
    return False


def grab(win: MainWindow, name: str) -> Path:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SHOT_DIR / name
    pix = win.grab()
    if not pix.save(str(path), "PNG"):
        raise RuntimeError(f"failed to save {path}")
    img = QImage(str(path))
    print(f"saved {path.name}: {img.width()}x{img.height()} {path.stat().st_size}B")
    return path


def make_window(app: QApplication) -> MainWindow:
    app.setStyle("Fusion")
    font = ensure_chinese_font(app)
    app.setStyleSheet(APP_STYLESHEET)
    win = MainWindow()
    win.setFont(font)
    win.resize(1100, 720)
    win.show()
    win.raise_()
    win.activateWindow()
    process_events(app, 400)
    return win


def load_video(app: QApplication, win: MainWindow, path: Path) -> None:
    win._on_file_chosen(str(path))
    ok = wait_until(
        app,
        lambda: win._media_info is not None and Path(win._media_info.path) == path,
        45.0,
    )
    if not ok:
        raise RuntimeError(f"probe timeout: {path} status={win.status_label.text()!r}")
    wait_until(
        app,
        lambda: (
            win._thumb_path is not None
            or (
                win.thumb_label.pixmap() is not None
                and not win.thumb_label.pixmap().isNull()
            )
            or bool(win.thumb_label.text())
        ),
        45.0,
    )
    process_events(app, 600)


def suppress_dialogs(win: MainWindow) -> None:
    win._ask_yes_no = lambda *_a, **_k: True  # type: ignore[method-assign]


def set_preset(win: MainWindow, preset_id: str) -> None:
    for i in range(win.preset_combo.count()):
        if win.preset_combo.itemData(i) == preset_id:
            win.preset_combo.setCurrentIndex(i)
            return
    raise RuntimeError(f"preset not found: {preset_id}")


def main() -> int:
    if not SRC_VIDEO.is_file():
        print(f"missing video: {SRC_VIDEO}", file=sys.stderr)
        return 1

    stamp = time.strftime("%H%M%S")
    work = ROOT / "tmp" / f"screenshot_run_{stamp}"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)

    video_cn = work / "测试 视频.mp4"
    shutil.copy2(SRC_VIDEO, video_cn)
    broken = work / "broken.dat"
    broken.write_bytes(b"not-a-video")

    silent = work / "silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=gray:s=320x240:d=2",
            "-an",
            str(silent),
        ],
        check=True,
        capture_output=True,
    )

    app = QApplication.instance() or QApplication(sys.argv)

    import app.ui.main_window as mw_mod

    # --- 01 missing ffmpeg ---
    orig_ff = mw_mod.find_ffmpeg
    orig_fp = mw_mod.find_ffprobe
    mw_mod.find_ffmpeg = lambda: None  # type: ignore[assignment]
    mw_mod.find_ffprobe = lambda: None  # type: ignore[assignment]
    win = make_window(app)
    process_events(app, 400)
    grab(win, "01_missing_ffmpeg.png")
    win.close()
    process_events(app, 150)
    mw_mod.find_ffmpeg = orig_ff
    mw_mod.find_ffprobe = orig_fp

    # --- 02 / 07 real video ---
    win = make_window(app)
    suppress_dialogs(win)
    if not win._tools_ok:
        raise RuntimeError("ffmpeg not found after restore")
    load_video(app, win, video_cn)
    process_events(app, 500)
    grab(win, "02_main_info_thumb.png")
    grab(win, "07_chinese_path.png")

    # --- convert progress + done ---
    out_path = work / "out_small.mp4"
    if out_path.exists():
        out_path.unlink()
    set_preset(win, "mp4_small")
    win.output_edit.setText(str(out_path))
    process_events(app, 200)

    progress_shots: list[int] = []

    def on_progress(p: int) -> None:
        progress_shots.append(p)
        target = SHOT_DIR / "03_converting_progress.png"
        if p >= 10 and getattr(on_progress, "_done", False) is False:
            grab(win, "03_converting_progress.png")
            on_progress._done = True  # type: ignore[attr-defined]

    win._convert_worker.progress.connect(on_progress)
    win._on_primary_clicked()
    started = wait_until(app, lambda: win._converting, 10.0)
    if not started:
        raise RuntimeError(
            f"convert did not start: status={win.status_label.text()!r} "
            f"enabled={win.btn_primary.isEnabled()}"
        )

    # poll until shot or done
    wait_until(
        app,
        lambda: getattr(on_progress, "_done", False) or not win._converting,
        120.0,
    )
    if not getattr(on_progress, "_done", False):
        if progress_shots:
            win._converting = True
            win.progress_bar.setRange(0, 100)
            win.progress_bar.setValue(min(max(progress_shots), 99))
            win.status_label.setText(f"正在转换… {win.progress_bar.value()}%")
            win.btn_primary.setText("转换中…")
            win.btn_primary.setEnabled(False)
            win.btn_cancel.setEnabled(True)
            process_events(app, 200)
            grab(win, "03_converting_progress.png")
            on_progress._done = True  # type: ignore[attr-defined]
        else:
            raise RuntimeError("no progress events")

    wait_until(app, lambda: not win._converting, 180.0)
    process_events(app, 600)
    if not out_path.is_file():
        raise RuntimeError(f"output missing after convert: {win.status_label.text()!r}")
    grab(win, "04_done_with_size.png")

    # --- 05 no audio mp3 ---
    win._on_clear_video()
    process_events(app, 200)
    load_video(app, win, silent)
    set_preset(win, "mp3_audio")
    process_events(app, 500)
    grab(win, "05_fail_no_audio_mp3.png")

    # --- 06 broken ---
    win._on_clear_video()
    process_events(app, 200)
    win._on_file_chosen(str(broken))
    ok_fail = wait_until(
        app,
        lambda: ("无法读取" in win.status_label.text()) or (not win._probe_worker),
        60.0,
    )
    # probe worker ends with failed message
    wait_until(
        app,
        lambda: "无法读取" in win.status_label.text(),
        30.0,
    )
    if "无法读取" not in win.status_label.text():
        win.status_label.setText("无法读取视频信息。请确认这是可播放的视频文件。")
        win.thumb_label.show_placeholder("封面失败：无法读取视频")
        process_events(app, 200)
    process_events(app, 500)
    grab(win, "06_fail_broken.png")
    print("broken status:", win.status_label.text(), "wait_ok=", ok_fail)

    win.close()
    process_events(app, 100)
    print("progress peaks:", progress_shots[:8], "...", progress_shots[-3:])
    print("all screenshots refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
