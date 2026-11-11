"""Offline synthetic metadata tests: no patient data."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.core import read_metadata, scan_folder, match, parse_schedule

def test_exiftool_out_of_order_and_missing_time(tmp_path):
    first = tmp_path / "canon.CR3"
    second = tmp_path / "nikon.NEF"
    first.write_bytes(b"fake")
    second.write_bytes(b"fake")
    payload = [
        {"SourceFile": str(second), "DateTimeOriginal": "2026:11:11 10:20:00", "Model": "Nikon"},
        {"SourceFile": str(first), "DateTimeOriginal": "2026:11:11 09:10:00", "Model": "Canon"},
    ]
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload), stderr="")
    with patch("dental_photo_sorter.core.subprocess.run", return_value=fake):
        photos = read_metadata([first, second], offset_minutes=5)
    assert photos[0].camera == "Canon"
    assert photos[0].captured == datetime(2026, 11, 11, 9, 15)
    assert photos[1].camera == "Nikon"
    appts = parse_schedule("09:00-10:00 Test One\n10:00-11:00 Test Two", "2026-11-11")
    assert [match(p, appts) for p in photos] == [0, 1]

def test_missing_exif_is_unassigned(tmp_path):
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"fake")
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps([{"SourceFile": str(source)}]), stderr="")
    with patch("dental_photo_sorter.core.subprocess.run", return_value=fake):
        photo = read_metadata([source])[0]
    assert photo.captured is None
    assert match(photo, parse_schedule("09:00-10:00 Test", "2026-11-11")) is None

def test_scan_filters_formats(tmp_path):
    (tmp_path / "a.CR3").write_bytes(b"")
    (tmp_path / "b.NEF").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("x")
    assert len(scan_folder(tmp_path)) == 2

def test_large_card_uses_batched_exif(tmp_path):
    from unittest.mock import patch
    files = [tmp_path / f"image_{i:03d}.jpg" for i in range(165)]
    for file in files:
        file.write_bytes(b"x")
    def fake_run(args, **kwargs):
        batch = [Path(item) for item in args if str(item).endswith(".jpg")]
        payload = [{"SourceFile": str(path), "DateTimeOriginal": "2026:11:11 09:00:00"} for path in batch]
        return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")
    with patch("dental_photo_sorter.core.subprocess.run", side_effect=fake_run) as mocked:
        result = read_metadata(files)
    assert mocked.call_count == 3
    assert len(result) == 165
    assert all(item.captured for item in result)
