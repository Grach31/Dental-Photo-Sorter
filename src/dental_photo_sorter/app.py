"""Windows desktop UI: local import with mandatory confirmation."""
from __future__ import annotations
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget, QInputDialog,
)
from .core import parse_schedule, scan_folder, read_metadata, match, safe_name, copy_verified
from .database import connect
from .ocr import recognize
from .preview import preview_bytes
from .validation import validate_paths, require_unique_appointments
from .archive import list_visits, list_photos, verify_archive, export_manifest, backup_database
from .diagnostics import diagnostics

APP_DIR = Path.home() / "Documents" / "DentalPhotoSorter"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dental Photo Sorter · локальный режим")
        self.resize(1060, 720)
        self.photos = []
        self.appointments = []
        self.source = None
        self.preview_signature = None
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
        self.image_preview = QLabel("Выбери фотографию в таблице для просмотра JPG")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(180)
        layout.addWidget(self.image_preview)
        self.table.itemSelectionChanged.connect(self.show_photo)
        self.tabs.addTab(main, "Импорт")
        archive = QWidget()
        archive_layout = QVBoxLayout(archive)
        archive_actions = QHBoxLayout()
        for title, callback in [
            ("Обновить архив", self.refresh_archive),
            ("Проверить целостность", self.verify_files),
            ("Экспорт CSV", self.export_csv),
            ("Резервная копия базы", self.backup_db),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            archive_actions.addWidget(button)
        archive_layout.addLayout(archive_actions)
        self.archive_search = QLineEdit()
        self.archive_search.setPlaceholderText("Поиск по пациенту")
        self.archive_search.textChanged.connect(self.refresh_archive)
        archive_layout.addWidget(self.archive_search)
        self.visits_table = QTableWidget(0, 4)
        self.visits_table.setHorizontalHeaderLabels(["Пациент", "Кабинет", "Дата приёма", "Фото"])
        self.visits_table.horizontalHeader().setStretchLastSection(True)
        self.visits_table.itemSelectionChanged.connect(self.show_visit)
        archive_layout.addWidget(self.visits_table)
        self.visit_files = QTextEdit()
        self.visit_files.setReadOnly(True)
        self.visit_files.setMaximumHeight(160)
        archive_layout.addWidget(self.visit_files)
        self.tabs.addTab(archive, "Архив")
        self.refresh_archive()

        settings = QWidget()
        s = QVBoxLayout(settings)
        self.sync = QCheckBox("Синхронизация (будет доступна в будущей версии)")
        self.sync.setEnabled(False)
        s.addWidget(self.sync)
        s.addWidget(QLabel("База и фото хранятся на этом компьютере.\n"
                           "Общая синхронизация ещё не реализована.\n"
                           "Не копируй файл SQLite в общую синхронизируемую папку."))
        check_dependencies = QPushButton("Проверить ExifTool и Tesseract")
        check_dependencies.clicked.connect(self.check_dependencies)
        s.addWidget(check_dependencies)
        s.addStretch()
        self.tabs.addTab(settings, "Синхронизация")

    def check_dependencies(self):
        results = diagnostics()
        QMessageBox.information(
            self, "Проверка компонентов",
            "\n".join(("✓ " if ok else "✗ ") + message for ok, message in results)
            + "\nExifTool нужен для времени съёмки и RAW; Tesseract — для OCR."
        )

    def refresh_archive(self, *_):
        rows = list_visits(self.db, self.archive_search.text())
        self.visit_ids = [row[0] for row in rows]
        self.visits_table.setRowCount(len(rows))
        for i, (_, patient, clinic, date, count) in enumerate(rows):
            for j, value in enumerate((patient, clinic, date, str(count))):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.visits_table.setItem(i, j, item)

    def show_visit(self):
        row = self.visits_table.currentRow()
        if row < 0 or row >= len(self.visit_ids):
            return
        photos = list_photos(self.db, self.visit_ids[row])
        self.visit_files.setPlainText("\n".join(f"{name} | {captured or 'Нет EXIF'} | {path}" for path, name, captured, _ in photos))

    def verify_files(self):
        try:
            errors = verify_archive(self.db)
            if errors:
                self.error(f"Проблемных файлов: {len(errors)}\n" + "\n".join(f"{reason}: {path}" for path, reason in errors[:10]))
            else:
                QMessageBox.information(self, "Проверка", "Все зарегистрированные фотографии существуют и совпадают по SHA-256.")
        except Exception as exc:
            self.error(exc)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт списка", "dental_manifest.csv", "CSV (*.csv)")
        if path:
            try:
                count = export_manifest(self.db, Path(path))
                QMessageBox.information(self, "Экспорт", f"Экспортировано {count} записей. CSV содержит данные пациентов, храни локально.")
            except Exception as exc:
                self.error(exc)

    def backup_db(self):
        name = datetime.now().strftime("dental-db-%Y%m%d-%H%M%S.sqlite")
        path, _ = QFileDialog.getSaveFileName(self, "Резервная копия базы (без фотографий)", name, "SQLite (*.sqlite)")
        if path:
            try:
                backup_database(self.db, Path(path))
                QMessageBox.information(self, "Копия создана", "База сохранена. Фотографии необходимо резервировать отдельно.")
            except Exception as exc:
                self.error(exc)

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
            self.photos = []
            self.table.setRowCount(0)
            self.preview_signature = None
            self.source = Path(folder)
            self.status.setText(f"Выбрана папка: {folder}")

    def preview(self):
        if self.source is None:
            return self.error("Сначала выбери карту памяти или папку.")
        try:
            self.photos = []
            self.preview_signature = None
            self.table.setRowCount(0)
            self.appointments = parse_schedule(self.schedule.toPlainText(), self.date.date().toString("yyyy-MM-dd"))
            require_unique_appointments(self.appointments)
            validate_paths(self.source, Path(self.dest.text()).expanduser())
            paths = scan_folder(self.source)
            if not paths:
                raise ValueError("В выбранной папке нет поддерживаемых фотографий.")
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

    def show_photo(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.photos):
            self.image_preview.setText("Фотография не выбрана")
            return
        photo = self.photos[row]
        data = preview_bytes(photo.path)
        if not data:
            self.image_preview.setText("Для этого файла нет доступного предпросмотра.")
            return
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if pixmap.isNull():
            self.image_preview.setText("Не удалось открыть изображение")
            return
        self.image_preview.setPixmap(pixmap.scaled(760, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def import_photos(self):
        if not self.photos or self.table.rowCount() != len(self.photos):
            return self.error("Сначала проверь распределение.")
        if self.source is None or not self.source.is_dir():
            return self.error("Исходная папка больше не доступна.")
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
            archive_root = Path(self.dest.text()).expanduser().resolve()
            validate_paths(self.source, archive_root)
            for photo, index in selected:
                appt = self.appointments[index]
                day = appt.start.strftime("%Y-%m-%d")
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
            self.refresh_archive()
            QMessageBox.information(self, "Готово", f"Скопировано или проверено {count} фото. Оригиналы на SD-карте сохранены.")
        except Exception as exc:
            self.error(f"Импорт остановлен после {count} файлов: {exc}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
