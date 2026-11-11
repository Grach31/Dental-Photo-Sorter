"""Windows desktop UI: local import with mandatory confirmation."""
from __future__ import annotations
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget,
)
from .core import parse_schedule, scan_folder, read_metadata, match, safe_name, copy_verified
from .database import connect
from .ocr import recognize

APP_DIR = Path.home() / "Documents" / "DentalPhotoSorter"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dental Photo Sorter · локальный режим")
        self.resize(1060, 720)
        self.photos = []
        self.appointments = []
        self.source = None
        self.db = connect(APP_DIR / "index.sqlite")
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        main = QWidget()
        layout = QVBoxLayout(main)
        form = QFormLayout()
        self.clinic = QLineEdit("Кабинет 1")
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        from PySide6.QtCore import QDate
        self.date.setDate(QDate.currentDate())
        self.offset = QSpinBox()
        self.offset.setRange(-1440, 1440)
        self.offset.setSuffix(" мин")
        self.dest = QLineEdit(str(APP_DIR / "Photos"))
        form.addRow("Кабинет:", self.clinic)
        form.addRow("Дата расписания:", self.date)
        form.addRow("Поправка часов камеры:", self.offset)
        form.addRow("Архив фотографий:", self.dest)
        layout.addLayout(form)
        browse_dest = QPushButton("Выбрать папку архива")
        browse_dest.clicked.connect(self.choose_destination)
        layout.addWidget(browse_dest)
        layout.addWidget(QLabel("Расписание: одна строка на пациента — 09:00-10:00 Фамилия Имя. Проверь после OCR."))
        self.schedule = QTextEdit()
        self.schedule.setPlaceholderText("09:00-10:00 Пациент 001\n10:00-11:00 Пациент 002")
        self.schedule.setMaximumHeight(125)
        layout.addWidget(self.schedule)
        actions = QHBoxLayout()
        for title, callback in [
            ("Распознать скриншот", self.import_screenshot),
            ("Выбрать SD-карту / папку", self.choose_source),
            ("Проверить распределение", self.preview),
            ("Копировать подтверждённые", self.import_photos),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel("Исходные файлы никогда не удаляются. Неоднозначные снимки остаются без назначения.")
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Файл", "Время съёмки", "Камера", "Назначение (можно изменить)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.tabs.addTab(main, "Импорт")

        settings = QWidget()
        s = QVBoxLayout(settings)
        self.sync = QCheckBox("Синхронизация (будет доступна в будущей версии)")
        self.sync.setEnabled(False)
        s.addWidget(self.sync)
        s.addWidget(QLabel("База и фото хранятся на этом компьютере.\n"
                           "Общая синхронизация ещё не реализована.\n"
                           "Не копируй файл SQLite в общую синхронизируемую папку."))
        s.addStretch()
        self.tabs.addTab(settings, "Синхронизация")

    def error(self, exc):
        QMessageBox.warning(self, "Проверь данные", str(exc))

    def choose_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка архива", self.dest.text())
        if folder:
            self.dest.setText(folder)

    def import_screenshot(self):
        file, _ = QFileDialog.getOpenFileName(self, "Скриншот расписания", "", "Изображения (*.png *.jpg *.jpeg *.bmp)")
        if file:
            try:
                self.schedule.setPlainText(recognize(Path(file)))
                QMessageBox.information(self, "Проверка", "OCR выполнен. Исправь текст в формате ЧЧ:ММ-ЧЧ:ММ Фамилия Имя перед продолжением.")
            except Exception as exc:
                self.error(exc)

    def choose_source(self):
        folder = QFileDialog.getExistingDirectory(self, "SD-карта или папка DCIM")
        if folder:
            self.source = Path(folder)
            self.status.setText(f"Выбрана папка: {folder}")

    def preview(self):
        if self.source is None:
            return self.error("Сначала выбери карту памяти или папку.")
        try:
            self.appointments = parse_schedule(self.schedule.toPlainText(), self.date.date().toString("yyyy-MM-dd"))
            paths = scan_folder(self.source)
            self.photos = read_metadata(paths, offset_minutes=self.offset.value())
            self.preview_signature = (self.schedule.toPlainText(), self.date.date().toString("yyyy-MM-dd"), self.offset.value(), self.clinic.text(), self.dest.text())
            self.table.setRowCount(len(self.photos))
            uncertain = 0
            for row, photo in enumerate(self.photos):
                index = match(photo, self.appointments)
                if index is None:
                    uncertain += 1
                for col, value in enumerate([photo.path.name, str(photo.captured or "Нет EXIF"), photo.camera]):
                    cell = QTableWidgetItem(value)
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, col, cell)
                selector = QComboBox()
                selector.addItem("Не определено — не импортировать", None)
                for i, appt in enumerate(self.appointments):
                    selector.addItem(f"{appt.start:%H:%M} — {appt.name}", i)
                if index is not None:
                    selector.setCurrentIndex(index + 1)
                self.table.setCellWidget(row, 3, selector)
            self.status.setText(f"Найдено {len(self.photos)} фото; требуют проверки {uncertain}. Проверь каждую группу перед копированием.")
        except Exception as exc:
            self.error(exc)

    def import_photos(self):
        if not self.photos or self.table.rowCount() != len(self.photos):
            return self.error("Сначала проверь распределение.")
        if self.preview_signature != (self.schedule.toPlainText(), self.date.date().toString("yyyy-MM-dd"), self.offset.value(), self.clinic.text(), self.dest.text()):
            return self.error("Настройки изменились после проверки. Нажми «Проверить распределение» ещё раз.")
        chosen = [(photo, self.table.cellWidget(i, 3).currentData()) for i, photo in enumerate(self.photos)]
        selected = [(photo, index) for photo, index in chosen if index is not None]
        if not selected:
            return self.error("Нет назначенных фотографий.")
        reply = QMessageBox.question(
            self, "Подтверждение", f"Скопировать {len(selected)} фотографий в {self.dest.text()}?\n"
            "Проверь назначения: автоматическое совпадение по времени не подтверждает личность пациента.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        count = 0
        try:
            for photo, index in selected:
                appt = self.appointments[index]
                day = appt.start.strftime("%Y-%m-%d")
                archive_root = Path(self.dest.text()).expanduser().resolve()
                if not self.dest.text().strip() or archive_root == self.source.resolve() or self.source.resolve() in archive_root.parents:
                    raise ValueError("Архив нельзя размещать внутри папки исходных фотографий.")
                destination = archive_root / safe_name(self.clinic.text()) / day / safe_name(f"{appt.start:%H-%M}_{appt.name}")
                target, digest = copy_verified(photo, destination)
                # A visit is identified by clinic/date/start/name locally; no cross-device identity inference.
                visit_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{self.clinic.text()}|{appt.start.isoformat()}|{appt.name}"))
                patient_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"local-visit|{visit_id}"))
                now = datetime.now().isoformat()
                with self.db:
                    self.db.execute("INSERT OR IGNORE INTO patients VALUES (?, ?, ?)", (patient_id, appt.name, now))
                    self.db.execute("INSERT OR IGNORE INTO visits VALUES (?, ?, ?, ?, ?, ?)", (visit_id, patient_id, self.clinic.text(), appt.start.isoformat(), appt.end.isoformat(), now))
                    self.db.execute("INSERT OR IGNORE INTO photos VALUES (?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid5(uuid.NAMESPACE_URL, str(target))), visit_id, photo.path.name, photo.captured.isoformat() if photo.captured else None, digest, str(target), photo.camera))
                count += 1
            QMessageBox.information(self, "Готово", f"Скопировано или проверено {count} фото. Оригиналы на SD-карте сохранены.")
        except Exception as exc:
            self.error(f"Импорт остановлен после {count} файлов: {exc}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
