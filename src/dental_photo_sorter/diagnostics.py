"""Offline environment diagnostics for the Windows prototype."""
from __future__ import annotations
import shutil
import sys
from pathlib import Path
import subprocess

def check_tool(command: str, arguments: list[str]) -> tuple[bool, str]:
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "exiftool" / "exiftool.exe" if command == "exiftool" else None
    executable = str(bundled) if bundled is not None and bundled.is_file() else shutil.which(command)
    if not executable:
        return False, f"{command}: не найден в PATH"
    try:
        result = subprocess.run([executable, *arguments], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{command}: ошибка запуска: {exc}"
    output = (result.stdout or result.stderr).strip().splitlines()
    summary = output[0] if output else "без информации о версии"
    return result.returncode == 0, f"{command}: {summary}"

def diagnostics() -> list[tuple[bool, str]]:
    return [
        check_tool("exiftool", ["-ver"]),
        check_tool("tesseract", ["--version"]),
    ]
