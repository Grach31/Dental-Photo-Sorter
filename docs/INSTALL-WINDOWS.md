# Windows prototype setup

**Status: prototype, not validated with real patient data. Do not use as the sole clinical archive.**

## Download
Open GitHub Actions > Windows build > latest successful run > Artifacts > DentalPhotoSorter-Windows.
Extract the ZIP to a local folder and run DentalPhotoSorter.exe.

**For a first trial:** Download the newest workflow artifact even if the run is marked failed, provided the artifact exists. The workflow attempts to upload the EXE independently of the test result. This is an **unsigned experimental build**; Windows SmartScreen may warn. Do not bypass organization security policies. Test with synthetic photos first.

To check the executable without opening the UI, run in PowerShell:
```powershell
.\\DentalPhotoSorter.exe --self-test
$LASTEXITCODE
```
Exit code 0 indicates the packaged UI initialized successfully (not a complete camera workflow test).

## External free tools (required for current prototype)
- ExifTool from https://exiftool.org/ (Windows: rename exiftool(-k).exe to exiftool.exe and add its directory to PATH).
- Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki (install Russian and English language data, add installation directory to PATH).

The EXE currently does not bundle ExifTool or Tesseract. Without ExifTool the photo preview cannot read timestamps; without Tesseract you can still manually enter the schedule.

## Проверка компонентов
Во вкладке «Синхронизация» нажми «Проверить ExifTool и Tesseract». Оба инструмента должны определяться в PATH. Это диагностическая проверка, не установка.

## Workflow
1. Set the clinic, date, destination folder, and camera clock correction.
2. Enter a verified schedule, one line per appointment: `09:00-10:00 Patient 001`.
3. Optionally use the screenshot OCR button, then manually correct OCR output to the above format.
4. Select the SD card's DCIM folder; click **Проверить распределение**.
5. Review all assignments and choose **Не определено** for uncertain files.
6. Confirm copying. Sources are never deleted.
7. Open the «Архив» tab to search visits, verify SHA-256 checksums, export CSV or back up the SQLite database. A database backup does not include photo files.

## Data and sync
The local SQLite database lives in `Documents/DentalPhotoSorter/index.sqlite` and photos are copied to the chosen archive directory. Back up both. No synchronization exists yet. Never put the SQLite database into a generic shared sync folder. The program does not yet encrypt local photos or databases; use approved workstation and full-disk encryption controls.

## Important
- For testing, use synthetic or properly de-identified data only.
- Patient identity is **not** automatically matched across visits; names are not reliable identifiers.
- The current executable is portable rather than a signed Windows installer.
