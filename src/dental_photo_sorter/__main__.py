"""Windows executable entrypoint with a non-interactive packaged smoke test."""
from __future__ import annotations
import os
import sys

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from dental_photo_sorter.app import MainWindow
        app = QApplication([])
        window = MainWindow()
        assert window.tabs.count() == 3
        window.close()
        window.db.close()
        print("Dental Photo Sorter self-test OK")
        raise SystemExit(0)
    from dental_photo_sorter.app import main
    raise SystemExit(main())
