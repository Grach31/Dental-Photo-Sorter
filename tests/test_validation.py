import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.validation import validate_paths, require_unique_appointments
from dental_photo_sorter.core import parse_schedule

def test_source_archive_separation(tmp_path):
    src = tmp_path / "card"
    src.mkdir()
    validate_paths(src, tmp_path / "archive")
    with pytest.raises(ValueError):
        validate_paths(src, src / "archive")

def test_duplicate_schedule_blocked():
    appts = parse_schedule("09:00-10:00 Test\n09:00-10:00 Test", "2026-11-11")
    with pytest.raises(ValueError):
        require_unique_appointments(appts)
