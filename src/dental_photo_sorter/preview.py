"""Generate local previews without modifying camera originals."""
from __future__ import annotations
import subprocess
from pathlib import Path

JPEG = {".jpg", ".jpeg"}
RAW = {".cr2", ".cr3", ".nef", ".dng", ".tif", ".tiff"}

def preview_bytes(path: Path, exiftool: str = "exiftool") -> bytes | None:
    """Return JPEG bytes, or an embedded RAW preview if available."""
    if path.suffix.lower() in JPEG:
        return path.read_bytes()
    if path.suffix.lower() not in RAW:
        return None
    for tag in ("-PreviewImage", "-JpgFromRaw", "-ThumbnailImage"):
        try:
            result = subprocess.run(
                [exiftool, "-b", tag, str(path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=40, check=True,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
        if result.stdout.startswith(b"\xff\xd8\xff"):
            return result.stdout
    return None
