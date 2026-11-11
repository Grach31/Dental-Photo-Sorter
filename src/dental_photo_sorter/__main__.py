"""Minimal desktop scaffold; photo import and OCR are not implemented yet."""
import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

def main() -> int:
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Dental Photo Sorter — Prototype")
    window.setCentralWidget(QLabel("Local mode • Canon / Nikon • Sync: not configured"))
    window.resize(760, 440)
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
