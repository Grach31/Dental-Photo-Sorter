"""Generate local previews without modifying camera originals."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

JPEG = {".jpg", ".jpeg"}
HEIC = {".heic", ".heif"}
RAW = {".cr2", ".cr3", ".nef", ".dng", ".tif", ".tiff"}

def preview_bytes(path: Path, exiftool: str = "exiftool") -> bytes | None:
    """Return JPEG bytes, or an embedded RAW preview if available."""
    if exiftool == "exiftool":
        bundled = Path(getattr(sys, "_MEIPASS", "")) / "exiftool" / "exiftool.exe"
        if bundled.is_file():
            exiftool = str(bundled)
    if path.suffix.lower() in JPEG:
        return path.read_bytes()
    if path.suffix.lower() not in RAW | HEIC:
        return None
    if path.suffix.lower() in HEIC:
        try:
            import pillow_heif
            from io import BytesIO
            pillow_heif.register_heif_opener()
            from PIL import Image
            with Image.open(path) as im:
                im.thumbnail((1200, 1200))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                output = BytesIO()
                im.save(output, format="JPEG", quality=85)
                return output.getvalue()
        except (ImportError, OSError, ValueError):
            pass
    for tag in ("-PreviewImage", "-JpgFromRaw", "-ThumbnailImage"):
        try:
            result = subprocess.run(
                [exiftool, "-b", tag, str(path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=40, check=True,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        if result.stdout.startswith(b"\xff\xd8\xff"):
            return result.stdout
    return None
