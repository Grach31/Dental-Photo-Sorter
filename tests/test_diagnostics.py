import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dental_photo_sorter.diagnostics import check_tool, diagnostics

def test_missing_dependency():
    with patch("dental_photo_sorter.diagnostics.shutil.which", return_value=None):
        ok, message = check_tool("exiftool", ["-ver"])
    assert not ok and "PATH" in message

def test_installed_dependency():
    result = subprocess.CompletedProcess([], 0, "12.0\n", "")
    with patch("dental_photo_sorter.diagnostics.shutil.which", return_value="C:/tools/exiftool.exe"):
        with patch("dental_photo_sorter.diagnostics.subprocess.run", return_value=result):
            ok, message = check_tool("exiftool", ["-ver"])
    assert ok and "12.0" in message

def test_both_dependencies_reported():
    with patch("dental_photo_sorter.diagnostics.shutil.which", return_value=None):
        result = diagnostics()
    assert len(result) == 2 and all(not ok for ok, _ in result)
