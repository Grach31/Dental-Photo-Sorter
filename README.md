# Dental Photo Sorter

Local-first Windows dental photo organizer (prototype).

## Available functionality
- Import a schedule screenshot with local Tesseract OCR or type a verified schedule manually.
- Import Canon/Nikon JPG, CR2, CR3, NEF and other supported camera files from an SD card.
- Read capture time using ExifTool (batched for large cards), correct camera clock offset.
- Suggest photo-to-appointment grouping, leaving overlaps and missing EXIF unassigned.
- Review or change each assignment, preview JPEG and embedded RAW previews where present.
- Copy originals safely without deleting source; verify SHA-256 and avoid filename collisions.
- Browse previous visits, inspect archived file paths, verify archive integrity.
- Export a local CSV manifest; create a consistent SQLite database backup.
- Local-only database with stable record IDs; future synchronization remains disabled.

## Windows
Open [Windows build workflow](../../actions/workflows/windows.yml). After a **successful** run, download the `DentalPhotoSorter-Windows` artifact and extract the EXE. ExifTool and Tesseract are **not bundled**. See [installation guide](docs/INSTALL-WINDOWS.md).

## Privacy
Do not commit patient photos, names, schedules, exports, or SQLite databases. The current prototype does not encrypt local storage. Protect the workstation and back up both the database and image archive. Do not use as the sole clinical archive without validation and an approved data-protection process.

## Known limitations
- OCR requires operator correction; it does not parse arbitrary clinic schedule layouts automatically.
- Camera time matching is a suggestion, **not identity verification**.
- Patients with the same name are not automatically merged across visits.
- RAW preview requires embedded JPEG preview; not every camera file has one.
- No installer signing, background synchronization, multi-user authorization, or integrated encrypted backup.
- No verified real-camera or Windows end-to-end acceptance test yet.

## Source
Python 3.11+, PySide6, SQLite, ExifTool, Tesseract, PyInstaller. Tests: `python -m pytest -q`.
