from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pytest
from dental_photo_sorter.core import Appointment, Photo, parse_schedule, match, copy_verified, safe_name

def test_parse_and_match():
    appts = parse_schedule("09:00-10:00 Первый\n10:00-11:00 Второй", "2026-11-11")
    assert match(Photo(Path("a.jpg"), datetime(2026,11,11,9,15)), appts) == 0
    assert match(Photo(Path("b.jpg"), datetime(2026,11,11,11,15)), appts) is None

def test_ambiguous():
    a = Appointment("A", datetime(2026,11,11,9), datetime(2026,11,11,11))
    b = Appointment("B", datetime(2026,11,11,10), datetime(2026,11,11,12))
    assert match(Photo(Path("a.jpg"), datetime(2026,11,11,10,30)), [a,b]) is None

def test_copy_keeps_source(tmp_path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"test")
    target, digest = copy_verified(Photo(source, None), tmp_path / "archive")
    assert source.exists() and target.read_bytes() == b"test"
    assert copy_verified(Photo(source, None), tmp_path / "archive")[0] == target

def test_sanitization():
    assert safe_name('A/B:C') == 'A_B_C'
