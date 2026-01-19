# Google Photos Takeout Metadata Fixer

This script repairs **Google Photos Takeout exports** by restoring timestamps, GPS data, and sensible filenames using the JSON sidecar files provided by Google Takeout. It supports **both photos and videos**, handles many of Google’s odd edge cases, and outputs a clean, chronologically named media library suitable for re-uploading to Google Photos (including via Pixel devices).

This project exists because Google Photos Takeout:

* strips or breaks EXIF metadata
* stores dates and GPS info in sidecar JSON files
* produces inconsistent filenames
* treats photos and videos differently

This script puts everything back together again.

---

## What this script does

* Recursively scans a Google Photos Takeout directory
* Matches each photo/video with its JSON sidecar (including supplemental metadata cases)
* Extracts:

  * photo taken / creation timestamps
  * GPS latitude, longitude, altitude
* Writes correct metadata back using **ExifTool**
* Renames files using a consistent, sortable format:

  ```
  YYYY_MM_DD_HHMMSS_originalFilename.ext
  ```
* Copies all fixed media to a new output directory (non-destructive)
* Correctly handles **photos vs videos** (MediaCreateDate, TrackCreateDate, etc.)
* Detects Google Takeout bugs where PNG files are actually JPEGs and fixes them
* Logs ExifTool output and errors for audit/debugging

---

## Requirements

### Software

* **Python 3.9+** (earlier versions may work but are untested)
* **ExifTool** (Windows executable)

### Python standard library only

No third-party Python packages are required.

---

## Folder structure (example)

```
Takeout/
└── Google Photos/
    ├── Album 1/
    │   ├── IMG_0001.jpg
    │   ├── IMG_0001.jpg.json
    │   └── ...
    ├── Album 2/
    └── ...
```

---

## Configuration

Edit the following paths at the top of the script:

```python
INPUT_PATH = r"C:\path\to\extracted\Takeout\Google Photos"
OUTPUT_PATH = r"S:\path\for\fixed\photos"
EXIFTOOL_PATH = r"C:\path\to\exiftool.exe"

EXIFTOOL_ARGUMENTS_FILE = r"C:\path\to\save\exiftool_arguments.txt"
EXIFTOOL_OUTPUT_LOG_FILE = r"C:\path\to\save\exiftool_output_log.txt"
EXIFTOOL_OUTPUT_ERRORS_FILE = r"C:\path\to\save\exiftool_output_errors.txt"
MEDIA_FILES_DICTIONARY_FILE = r"C:\path\to\save\media_files_dictionary.txt"
```

Make sure the output directory exists before running.

---

## Supported file types

### Photos

* JPG / JPEG
* PNG
* HEIC

### Videos

* MP4
* MOV
* AVI
* MKV

(Other formats may work but are not explicitly tested.)

---

## How it works (high level)

1. **Scan** all media files recursively
2. **Locate JSON sidecars**, including:

   * `.json`
   * `.supplemental-metadata.json`
   * renamed / truncated variants
3. **Extract metadata** from JSON
4. **Generate ExifTool commands** dynamically
5. **Run ExifTool in stay_open mode** for performance
6. **Detect and fix broken PNGs** that are actually JPEGs
7. **Write logs** for verification

---

## Running the script

```bash
python metadata-fixer.py
```

Depending on library size, this may take minutes or hours. Progress is shown during execution.

---

## Output

* All fixed media is written to `OUTPUT_PATH`
* Originals are **never modified**
* Filenames are prefixed with a UTC timestamp
* Metadata is restored in a Google Photos–friendly way

Example output filename:

```
2019_08_14_163522_IMG_1234.jpg
```

---

## Logs and debugging

* `exiftool_output_log.txt` – ExifTool standard output
* `exiftool_output_errors.txt` – errors and warnings
* `media_files_dictionary.txt` – optional debug mapping of media → JSON

These are extremely useful if something looks off.

---

## Known quirks and design decisions

* All timestamps are written in **UTC** (matching Google Takeout JSON)
* If both `photoTakenTime` and `creationTime` exist, `photoTakenTime` is preferred
* Files without a matching JSON are skipped but logged
* Album structure is flattened by design (Google Photos doesn’t rely on folders)

---

## Typical use case

1. Download Google Photos Takeout
2. Extract Takeout archive
3. Run this script
4. Upload fixed media to another image storage service; or keep on your own storage.

---

### Background / Motivation

I made this script after discovering that my old Pixel phone still had unlimited Google Photos storage (as of 19th January 2026).

I downloaded my entire library via Google Takeout, fixed the metadata using this script, and re-uploaded only photos and videos taken after 1st June 2021 (when free storage ended) back to Google Photos via the Pixel.

I now use Syncthing to automatically push new photos from my current phone to the Pixel for upload.

---

## Disclaimer

This script is provided as-is. Always:

* Keep multiple backups
* Test on a small subset first
* Verify results before deleting anything

---

## Why this exists

Because Google Photos Takeout gives you *all your memories*… just not in a usable state.

This script makes them whole again.

And I didn't want to pay the fee for "Metadata Fixer For Google Takeout".

---

## License

MIT
