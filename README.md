# Dental Photo Sorter

Local-first Windows application for organizing dental photography from Canon and Nikon.

## Planned workflow
1. Import screenshot of appointments; locally OCR and verify patient names and times.
2. Import JPG / CR2 / CR3 / NEF files from SD cards.
3. Read EXIF capture times, including camera-specific clock corrections.
4. Suggest photo-to-appointment grouping; uncertain images remain unassigned.
5. Preview and confirm before copying original photos into patient/visit folders.

## Technology
Python, PySide6, SQLite, ExifTool and local Tesseract OCR. Optional future sync uses stable IDs and event history, but **sync is not implemented**.

## Data safety
Never upload real patient photographs, schedules, databases or identifiers to GitHub. Use synthetic data in tests. Do not merge patients by name alone. Cross-clinic data exchange requires authorization and appropriate technical and legal safeguards.

## Current status
Initial source-code scaffold only. No working import, OCR, installer or sync yet.
