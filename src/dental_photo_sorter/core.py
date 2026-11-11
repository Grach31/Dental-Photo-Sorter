"""Offline import, EXIF metadata, appointment matching and safe file copies."""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import sys
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

EXTENSIONS = {".jpg", ".jpeg", ".heic", ".heif", ".cr2", ".cr3", ".nef", ".dng", ".tif", ".tiff"}
EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"

@dataclass(frozen=True)
class Appointment:
    name: str
    start: datetime
    end: datetime

@dataclass(frozen=True)
class Photo:
    path: Path
    captured: datetime | None
    camera: str = ""

def parse_schedule(text: str, day: str) -> list[Appointment]:
    """Accept verified lines: HH:MM-HH:MM Patient Name; no silent OCR guessing."""
    date = datetime.strptime(day, "%Y-%m-%d").date()
    result = []
    pattern = re.compile(r"^\s*(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})\s+(.+?)\s*$")
    for line in text.splitlines():
        if not line.strip():
            continue
        m = pattern.match(line)
        if not m:
            raise ValueError(f"Не распознана строка расписания: {line}")
        start = datetime.combine(date, datetime.strptime(m[1], "%H:%M").time())
        end = datetime.combine(date, datetime.strptime(m[2], "%H:%M").time())
        if end <= start:
            raise ValueError(f"Конец приёма должен быть позже начала: {line}")
        result.append(Appointment(m[3].strip(), start, end))
    if not result:
        raise ValueError("Расписание пустое")
    return result

def read_metadata(paths: list[Path], exiftool: str = "exiftool", offset_minutes: int = 0) -> list[Photo]:
    """Read EXIF in batches to avoid Windows command-line length limits."""
    if not paths:
        return []
    if exiftool == "exiftool":
        bundled = Path(getattr(sys, "_MEIPASS", "")) / "exiftool" / "exiftool.exe"
        if bundled.is_file():
            exiftool = str(bundled)
    by_path = {}
    for begin in range(0, len(paths), 80):
        batch = paths[begin:begin + 80]
        try:
            proc = subprocess.run(
                [exiftool, "-json", "-DateTimeOriginal", "-CreateDate", "-Model", *map(str, batch)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=True,
            )
            entries = json.loads(proc.stdout)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
            raise RuntimeError("ExifTool не найден или не смог прочитать фотографии. Проверь установку ExifTool.") from exc
        for entry in entries:
            if entry.get("SourceFile"):
                by_path[str(Path(entry["SourceFile"]).resolve()).casefold()] = entry
    result = []
    for path in paths:
        entry = by_path.get(str(path.resolve()).casefold(), {})
        value = entry.get("DateTimeOriginal") or entry.get("CreateDate")
        captured = None
        if value:
            try:
                captured = datetime.strptime(value[:19], EXIF_FORMAT) + timedelta(minutes=offset_minutes)
            except ValueError:
                pass
        result.append(Photo(path, captured, str(entry.get("Model", ""))))
    return result

def scan_folder(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix.lower() in EXTENSIONS)

def match(photo: Photo, appointments: list[Appointment]) -> int | None:
    if photo.captured is None:
        return None
    candidates = [i for i, appt in enumerate(appointments) if appt.start <= photo.captured < appt.end]
    return candidates[0] if len(candidates) == 1 else None

def safe_name(value: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return clean[:80] or "unknown"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def copy_verified(photo: Photo, destination: Path) -> tuple[Path, str]:
    """Never delete source; use temp file + digest check + atomic rename."""
    destination.mkdir(parents=True, exist_ok=True)
    digest = sha256(photo.path)
    target = destination / photo.path.name
    if target.exists():
        if sha256(target) == digest:
            return target, digest
        target = destination / f"{photo.path.stem}_{digest[:12]}{photo.path.suffix}"
    if target.exists():
        if sha256(target) == digest:
            return target, digest
        target = destination / f"{photo.path.stem}_{digest}{photo.path.suffix}"
        if target.exists():
            if sha256(target) == digest:
                return target, digest
            raise FileExistsError(f"Conflicting archive file: {target}")
    temp = destination / f".{uuid.uuid4().hex}.partial"
    try:
        shutil.copy2(photo.path, temp)
        if sha256(temp) != digest:
            raise IOError("Контрольная сумма копии не совпала")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return target, digest
