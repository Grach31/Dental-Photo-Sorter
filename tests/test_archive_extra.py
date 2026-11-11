import csv
import sqlite3
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.database import connect
from dental_photo_sorter.archive import export_manifest, backup_database, list_visits

def test_csv_escapes_spreadsheet_formula(tmp_path):
    db = connect(tmp_path / "db.sqlite")
    with db:
        db.execute("INSERT INTO patients VALUES ('p','=CMD()','now')")
        db.execute("INSERT INTO visits VALUES ('v','p','clinic','2026-11-11T09:00','2026-11-11T10:00','now')")
        db.execute("INSERT INTO photos VALUES ('f','v','image.jpg','now','digest','C:/archive/image.jpg','Nikon')")
    output = tmp_path / "manifest.csv"
    assert export_manifest(db, output) == 1
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[1][0] == "'=CMD()"
    assert len(list_visits(db, "=CMD()")) == 1

def test_backup_never_overwrites(tmp_path):
    db = connect(tmp_path / "db.sqlite")
    target = tmp_path / "backup.sqlite"
    backup_database(db, target)
    with pytest.raises(FileExistsError):
        backup_database(db, target)
