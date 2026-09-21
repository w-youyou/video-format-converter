"""Codex 浅色主题（对照 OpenAI Codex light chrome / codex-light tokens）。

surface #fcfcfc / panel #ffffff / ink #0d0d0d / accent #0169cc
border ≈ ink 10–16%
"""

APP_STYLESHEET = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans SC", "SimHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #fcfcfc;
    color: #0d0d0d;
}

QWidget#mainRoot {
    background-color: #fcfcfc;
    color: #0d0d0d;
}

QLabel {
    background: transparent;
    color: rgba(13, 13, 13, 0.72);
}

QLabel#statusLabel {
    color: rgba(13, 13, 13, 0.50);
    font-size: 12px;
    padding: 2px 0;
}

QLabel#filenameSuffix {
    color: rgba(13, 13, 13, 0.50);
    font-size: 13px;
    padding: 0 4px;
}

QLabel#dropHint {
    color: #0d0d0d;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}

QLabel#dropOr {
    color: rgba(13, 13, 13, 0.40);
    font-size: 11px;
    font-weight: 400;
    background: transparent;
}

QLabel#dropSubHint {
    color: rgba(13, 13, 13, 0.42);
    font-size: 11px;
    background: transparent;
}

QFrame#dropZone {
    background-color: #fafafa;
    border: 1.5px dashed rgba(13, 13, 13, 0.18);
    border-radius: 12px;
    max-height: 72px;
}

QFrame#dropZone[dropActive="true"] {
    background-color: rgba(1, 105, 204, 0.06);
    border: 1.5px dashed #0169cc;
}

QPushButton#btnSelect {
    background-color: #f4f4f4;
    color: #0d0d0d;
    border: 1px solid rgba(13, 13, 13, 0.12);
    font-weight: 600;
    border-radius: 8px;
    padding: 0 16px;
    min-height: 32px;
}

QPushButton#btnSelect:hover {
    background-color: #ebebeb;
    border-color: rgba(13, 13, 13, 0.20);
}

QPushButton#btnSelect:disabled {
    background-color: rgba(13, 13, 13, 0.03);
    color: rgba(13, 13, 13, 0.35);
    border-color: rgba(13, 13, 13, 0.08);
}

QPushButton#btnClear {
    background-color: #ffffff;
    color: rgba(13, 13, 13, 0.72);
    border: 1px solid rgba(13, 13, 13, 0.12);
    border-radius: 8px;
    padding: 0 14px;
    min-height: 32px;
}

QPushButton#btnClear:hover {
    background-color: #f5f5f5;
    border-color: rgba(13, 13, 13, 0.20);
    color: #0d0d0d;
}

QPushButton#btnClear:disabled {
    background-color: rgba(13, 13, 13, 0.03);
    color: rgba(13, 13, 13, 0.32);
    border-color: rgba(13, 13, 13, 0.08);
}

QFrame#panelCard {
    background-color: #ffffff;
    border: 1px solid rgba(13, 13, 13, 0.10);
    border-radius: 12px;
}

QLineEdit, QComboBox, QPlainTextEdit {
    background-color: #ffffff;
    color: #0d0d0d;
    border: 1px solid rgba(13, 13, 13, 0.12);
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: rgba(1, 105, 204, 0.22);
    selection-color: #0d0d0d;
    min-height: 16px;
}

QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover {
    border-color: rgba(13, 13, 13, 0.22);
    background-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {
    border-color: #0169cc;
    background-color: #ffffff;
}

QLineEdit:disabled, QComboBox:disabled, QPlainTextEdit:disabled {
    color: rgba(13, 13, 13, 0.35);
    background-color: rgba(13, 13, 13, 0.03);
    border-color: rgba(13, 13, 13, 0.08);
}

QLineEdit::placeholder {
    color: rgba(13, 13, 13, 0.35);
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid rgba(13, 13, 13, 0.45);
    width: 0;
    height: 0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0d0d0d;
    border: 1px solid rgba(13, 13, 13, 0.12);
    border-radius: 8px;
    selection-background-color: rgba(1, 105, 204, 0.10);
    outline: none;
    padding: 4px;
}

QPushButton {
    background-color: #ffffff;
    color: rgba(13, 13, 13, 0.88);
    border: 1px solid rgba(13, 13, 13, 0.12);
    border-radius: 8px;
    padding: 6px 14px;
    min-height: 28px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #f5f5f5;
    border-color: rgba(13, 13, 13, 0.18);
}

QPushButton:pressed {
    background-color: #eeeeee;
}

QPushButton:disabled {
    color: rgba(13, 13, 13, 0.32);
    background-color: rgba(13, 13, 13, 0.03);
    border-color: rgba(13, 13, 13, 0.08);
}

QPushButton#btnPrimary {
    background-color: #0d0d0d;
    color: #ffffff;
    border: 1px solid #0d0d0d;
    font-weight: 600;
    border-radius: 999px;
    padding: 7px 18px;
    min-height: 30px;
}

QPushButton#btnPrimary:hover {
    background-color: #2a2a2a;
    border-color: #2a2a2a;
}

QPushButton#btnPrimary:pressed {
    background-color: #000000;
}

QPushButton#btnPrimary:disabled {
    background-color: rgba(13, 13, 13, 0.28);
    color: rgba(255, 255, 255, 0.70);
    border-color: transparent;
}

QPushButton#btnToggleLog:checked {
    background-color: rgba(1, 105, 204, 0.10);
    border-color: rgba(1, 105, 204, 0.40);
    color: #0169cc;
}

QProgressBar {
    background-color: rgba(13, 13, 13, 0.06);
    border: 1px solid rgba(13, 13, 13, 0.08);
    border-radius: 6px;
    text-align: center;
    color: rgba(13, 13, 13, 0.65);
    font-size: 11px;
    min-height: 10px;
    max-height: 12px;
}

QProgressBar::chunk {
    background-color: #0169cc;
    border-radius: 5px;
}

QPlainTextEdit#logView {
    font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
    font-size: 12px;
    background-color: #ffffff;
    border: 1px solid rgba(13, 13, 13, 0.10);
    border-radius: 10px;
    padding: 8px;
    color: #0d0d0d;
}

QTableWidget#infoTable {
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    outline: none;
    color: #0d0d0d;
}

QTableWidget#infoTable::item {
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid rgba(13, 13, 13, 0.06);
    color: rgba(13, 13, 13, 0.88);
}

QTableWidget#infoTable::item:selected {
    background: transparent;
    color: rgba(13, 13, 13, 0.88);
}

QHeaderView::section {
    background-color: transparent;
    color: rgba(13, 13, 13, 0.45);
    border: none;
    border-bottom: 1px solid rgba(13, 13, 13, 0.10);
    padding: 8px;
    font-size: 12px;
    font-weight: 500;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: rgba(13, 13, 13, 0.14);
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(13, 13, 13, 0.22);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: rgba(13, 13, 13, 0.14);
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    width: 0;
}

QToolTip {
    background-color: #ffffff;
    color: #0d0d0d;
    border: 1px solid rgba(13, 13, 13, 0.14);
    padding: 6px 8px;
    border-radius: 6px;
}

QMessageBox {
    background-color: #fcfcfc;
}

QMessageBox QLabel {
    color: rgba(13, 13, 13, 0.88);
}

QLabel#missingBanner {
    color: #9b1c1c;
    background-color: rgba(224, 46, 42, 0.08);
    border: 1px solid rgba(224, 46, 42, 0.28);
    border-radius: 8px;
    padding: 10px 12px;
}

QWidget#thumbPane {
    background-color: #ffffff;
    border: 1px solid rgba(13, 13, 13, 0.10);
    border-radius: 12px;
}

QWidget#previewStage {
    background-color: #f0f0f0;
    border: 1px solid rgba(13, 13, 13, 0.10);
    border-radius: 8px;
}

QLabel#thumbLabel {
    background-color: #f0f0f0;
    color: rgba(13, 13, 13, 0.45);
    border-radius: 8px;
}

QPushButton#btnPreviewPlay {
    background: transparent;
    border: none;
}

QPushButton#btnPreviewPlay:disabled {
    opacity: 0.45;
}
"""
