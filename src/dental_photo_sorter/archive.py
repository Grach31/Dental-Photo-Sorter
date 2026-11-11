"""Local archive browsing, integrity verification and offline backup."""
from __future__ import annotations
import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from .core import sha256

def list_visits(db: sqlite3.Connection, search: str = "") -> list[tuple]:
    return db.execute(
        """SELECT v.id, p.display_name, v.clinic_id, v.appointment_start,
                  COUNT(ph.id) AS photo_count
           FROM visits v JOIN patients p ON p.id = v.patient_id
           LEFT JOIN photos ph ON ph.visit_id = v.id
           WHERE p.display_name LIKE ? ESCAPE '\\'
           GROUP BY v.id, p.display_name, v.clinic_id, v.appointment_start
           ORDER BY v.appointment_start DESC""",
        ("%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",),
    ).fetchall()

def list_photos(db: sqlite3.Connection, visit_id: str) -> list[tuple]:
    return db.execute(
        "SELECT stored_path, original_filename, capture_time, sha256 FROM photos WHERE visit_id=? ORDER BY capture_time, original_filename",
        (visit_id,),
    ).fetchall()

def verify_archive(db: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return paths and reasons for missing or modified files; never change files."""
    errors = []
    for path, digest in db.execute("SELECT stored_path, sha256 FROM photos"):
        file = Path(path)
        if not file.is_file():
            errors.append((path, "Отсутствует"))
        elif sha256(file) != digest:
            errors.append((path, "Изменён"))
    return errors

def export_manifest(db: sqlite3.Connection, output: Path) -> int:
    """Export metadata only. Output may contain patient identifiers; keep local."""
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = db.execute(
        """SELECT p.display_name, v.clinic_id, v.appointment_start,
                  ph.original_filename, ph.capture_time, ph.stored_path, ph.sha256
           FROM photos ph JOIN visits v ON v.id=ph.visit_id
           JOIN patients p ON p.id=v.patient_id
           ORDER BY v.appointment_start, ph.original_filename"""
    ).fetchall()
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["patient", "clinic", "visit", "filename", "captured", "path", "sha256"])
        writer.writerows(rows)
    return len(rows)

def backup_database(db: sqlite3.Connection, destination: Path) -> Path:
    """Consistent SQLite snapshot; does not back up image files."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")
    with sqlite3.connect(destination) as backup:
        db.backup(backup)
    return destination
