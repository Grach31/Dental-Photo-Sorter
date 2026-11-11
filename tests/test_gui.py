"""Synthetic end-to-end GUI acceptance checks, no patient data."""
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtWidgets import QApplication
from dental_photo_sorter.core import Photo

def test_gui_preview_and_archive(tmp_path, monkeypatch):
    import dental_photo_sorter.app as module
    monkeypatch.setattr(module, "APP_DIR", tmp_path / "app")
    app = QApplication.instance() or QApplication([])
    window = module.MainWindow()
    assert window.tabs.count() == 3
    card = tmp_path / "card"
    card.mkdir()
    (card / "synthetic.jpg").write_bytes(b"not-a-real-jpeg")
    window.source = card
    window.dest.setText(str(tmp_path / "archive"))
    window.date.setDate(window.date.date().fromString("2026-11-11", "yyyy-MM-dd"))
    window.schedule.setPlainText("09:00-10:00 Test Patient")
    fake = [Photo(card / "synthetic.jpg", datetime(2026, 11, 11, 9, 30), "Canon")]
    with patch.object(module, "read_metadata", return_value=fake):
        window.preview()
    assert window.table.rowCount() == 1
    assert window.table.cellWidget(0, 3).currentData() == 0
    window.schedule.setPlainText("10:00-11:00 Changed")
    with patch.object(module.QMessageBox, "warning") as warning:
        window.import_photos()
    assert warning.called
    window.close()
    window.db.close()
