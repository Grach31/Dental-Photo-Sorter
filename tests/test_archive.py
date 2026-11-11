import sqlite3
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.database import connect
from dental_photo_sorter.archive import list_visits, list_photos, verify_archive, export_manifest, backup_database
from dental_photo_sorter.core import sha256

def test_archive_queries_export_integrity_and_backup(tmp_path):
    db = connect(tmp_path / "index.sqlite")
    photo = tmp_path / "image.jpg"
    photo.write_bytes(b"synthetic")
    with db:
        db.execute("INSERT INTO patients VALUES ('p1','Test Person','2026-11-11')")
        db.execute("INSERT INTO visits VALUES ('v1','p1','Clinic A','2026-11-11T09:00','2026-11-11T10:00','2026-11-11')")
        db.execute("INSERT INTO photos VALUES ('f1','v1','image.jpg','2026-11-11T09:30',?,?,?)", (sha256(photo), str(photo), "Canon"))
    assert len(list_visits(db, "Test")) == 1
    assert len(list_photos(db, "v1")) == 1
    assert verify_archive(db) == []
    assert export_manifest(db, tmp_path / "manifest.csv") == 1
    backup_database(db, tmp_path / "backup.sqlite")
    with sqlite3.connect(tmp_path / "backup.sqlite") as snap:
        assert snap.execute("SELECT COUNT(*) FROM photos").fetchone()[0] == 1
    photo.write_bytes(b"modified")
    assert verify_archive(db)[0][1] == "Изменён"
