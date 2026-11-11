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
