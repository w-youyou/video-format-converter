import sys

from PySide6.QtWidgets import QApplication

from app.ui.fonts import ensure_chinese_font
from app.ui.main_window import MainWindow
from app.ui.theme import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ensure_chinese_font(app)
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
