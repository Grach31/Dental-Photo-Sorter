"""Safety validation independent of Qt."""
from __future__ import annotations
from pathlib import Path

def validate_paths(source: Path, archive: Path, database: Path | None = None) -> None:
    if not source.exists() or not source.is_dir():
        raise ValueError("Исходная папка не найдена.")
    src = source.resolve()
    dst = archive.expanduser().resolve()
    if src == dst or src in dst.parents:
        raise ValueError("Архив нельзя создавать внутри исходной папки.")
    if dst == src or dst in src.parents:
        raise ValueError("Исходная папка не должна находиться внутри архива.")
    if database is not None and dst == database.resolve().parent:
        raise ValueError("Не размещай фотографии в папке служебной базы.")

def require_unique_appointments(appointments) -> None:
    seen = set()
    for appt in appointments:
        key = (appt.start, appt.end, appt.name.casefold())
        if key in seen:
            raise ValueError(f"Повторяющаяся запись в расписании: {appt.name} {appt.start:%H:%M}")
        seen.add(key)
