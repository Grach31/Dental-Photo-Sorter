from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.database import connect

def test_schema(tmp_path):
    with connect(tmp_path / "test.sqlite") as db:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"patients", "visits", "photos", "sync_events"} <= names
