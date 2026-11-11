import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.preview import preview_bytes

def test_jpeg_preview(tmp_path):
    file = tmp_path / "photo.jpg"
    file.write_bytes(b"jpeg bytes")
    assert preview_bytes(file) == b"jpeg bytes"

def test_raw_embedded_preview(tmp_path):
    file = tmp_path / "photo.CR3"
    file.write_bytes(b"synthetic raw")
    calls = [subprocess.CompletedProcess([], 0, b"", b""),
             subprocess.CompletedProcess([], 0, b"\xff\xd8\xfftest", b"")]
    with patch("dental_photo_sorter.preview.subprocess.run", side_effect=calls) as mocked:
        assert preview_bytes(file) == b"\xff\xd8\xfftest"
    assert mocked.call_count == 2

def test_unsupported_preview(tmp_path):
    file = tmp_path / "notes.txt"
    file.write_bytes(b"notes")
    assert preview_bytes(file) is None

def test_heic_discovered(tmp_path):
    from dental_photo_sorter.core import scan_folder
    heic = tmp_path / "IMG_5382.HEIC"
    heic.write_bytes(b"synthetic")
    assert scan_folder(tmp_path) == [heic]

def test_heic_embedded_fallback(tmp_path):
    heic = tmp_path / "IMG_5382.HEIC"
    heic.write_bytes(b"not a valid HEIC")
    with patch("dental_photo_sorter.preview.subprocess.run", return_value=subprocess.CompletedProcess([], 0, bytes([255,216,255]) + b"preview", b"")):
        assert preview_bytes(heic) == bytes([255,216,255]) + b"preview"
