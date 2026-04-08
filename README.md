# IGS Map Annotator

IGS Map Annotator is a desktop app for planning and annotating Foxhole hex maps.
It provides drawing, symbol stamping, map grid references, measurement tools, and PNG export with a legend.

## What The App Does

- Loads local hex map images from `assets/`.
- Fetches live map metadata from the Foxhole War API.
- Lets you annotate with:
  - Select/move
  - Line, Arrow, Tank line, Infantry line
  - Filled Polygon
  - Filled Circle
  - Text labels
  - Erase
  - Ruler (distance + azimuth)
- Lets you stamp tactical symbols from `Annotassets/` in Friendly/Enemy variants.
- Exports the visible viewport to PNG with a generated legend.
- Checks GitHub on launch to notify when a newer version exists.

## Key Rules/Behaviors

- Grid overlay uses 17 columns (A-Q) and 15 rows (1-15).
- Ruler distance assumes one large grid square is 125 meters.
- Ruler azimuth uses 0 degrees = straight up, clockwise positive.

## UI Overview

- Left panel: categorized symbol tiles with Friendly (F) and Enemy (E) variant buttons.
- Top ribbon:
  - Row 1: drawing tools and color controls.
  - Row 2 (hover-reveal): formatting, zoom, undo/clear, export.

## Project Layout

- `UIhandling.py`: main application source.
- `fetch_hex_images.py`: helper for map image acquisition.
- `assets/`: map images and app icon (`IGS.png`).
- `Annotassets/`: annotation symbol images.

## Requirements

- Python 3.10+ (tested in a venv workflow)
- Packages:
  - `PySide6`
  - `requests`
  - `pyinstaller` (only for building an executable)

## Run From Source

```powershell
python UIhandling.py
```

## Build A Windows App (PyInstaller)

```powershell
python -m PyInstaller --noconfirm --clean --name IGSMapAnnotator --windowed --add-data "assets;assets" --add-data "Annotassets;Annotassets" UIhandling.py
```

Build output:

- `dist/IGSMapAnnotator/IGSMapAnnotator.exe`

Notes:

- The app window icon is loaded from `assets/IGS.png` at runtime.
- If you want the Windows EXE file icon itself changed in Explorer, provide an `.ico` file and add `--icon path\\to\\icon.ico` to the PyInstaller build command.

## Update Check

On launch, the app compares:

- Local git `HEAD` commit hash
- Latest commit on `main` from the repository:
  - `https://github.com/ATLAStheactualtitan/IGSCode`

If newer remote commit is found, the app shows an update notification.
