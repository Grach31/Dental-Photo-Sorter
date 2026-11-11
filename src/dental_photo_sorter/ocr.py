"""Optional local OCR. Always requires visual confirmation by the operator."""
from pathlib import Path
import subprocess

def recognize(image: Path, executable: str = "tesseract") -> str:
    try:
        process = subprocess.run(
            [executable, str(image), "stdout", "-l", "rus+eng", "--psm", "6"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=90, check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Для распознавания скриншота установи Tesseract OCR с русским языком.") from exc
    return process.stdout
