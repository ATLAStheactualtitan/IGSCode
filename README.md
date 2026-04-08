# IGS Map Annotator

IGS Map Annotator is a Windows app for drawing and planning on Foxhole hex maps.

Use it to place symbols, draw tactical overlays, measure distance and azimuth, and export a clean PNG of exactly what you see on screen.

## Quick Start (Downloaded App)

1. Open the app executable.
2. Pick a hex from the Hex dropdown at the top.
3. Choose a drawing tool or symbol.
4. Add your markings on the map.
5. Click Export PNG to save your annotated view with legend.

## Main Features

- Draw tools:
  - Line
  - Arrow
  - Tank line
  - Infantry line
  - Filled polygon
  - Filled circle
  - Text labels
  - Erase
- Symbol stamping:
  - Categorized symbol selector on the left
  - Friendly (F) and Enemy (E) variants
- Ruler tool:
  - Shows live distance and azimuth from an origin point
  - Distance uses 125 meters per large grid square
  - Azimuth uses 0 degrees at straight up and increases clockwise
- Export:
  - Saves the visible map area to PNG
  - Includes a legend of icons/lines used in that view

## Interface Guide

- Left panel:
  - Symbol categories and symbol tiles
  - Click F or E to select which variant to stamp
- Top ribbon:
  - Row 1 always visible: map and drawing/color controls
  - Row 2 appears on hover: width/text, zoom, undo, clear, export
- Map area:
  - Mouse wheel zooms
  - Middle mouse pans
  - Grid coordinates are shown near the cursor

## Tool Usage

- Line/Arrow/Tank/Inf:
  - Left click to place nodes
  - Right click to finish
- Polygon:
  - Left click to place corners
  - Right click to close/fill
- Circle:
  - Left click center
  - Move mouse
  - Left click edge to commit
- Ruler:
  - Left click sets origin
  - Move mouse to read distance and azimuth
  - Right click or Esc clears ruler
- Text:
  - Left click to place editable label
- Erase:
  - Left click an annotation to remove it

## Keyboard Shortcuts

- S: Select
- L: Line
- A: Arrow
- Z: Tank line
- W: Infantry line
- P: Polygon
- C: Circle
- R: Ruler
- T: Text
- E: Erase
- Ctrl+Z: Undo
- Ctrl++ / Ctrl+-: Zoom in/out
- Esc: Cancel active drawing mode action

## Update Notification

At launch, the app checks GitHub for a newer version and notifies you if one is available.

Repository:

- https://github.com/ATLAStheactualtitan/IGSCode

## Troubleshooting

- If map images are missing:
  - Ensure the assets folder is present next to the executable.
- If symbols are missing:
  - Ensure the Annotassets folder is present next to the executable.
- If export fails:
  - Check write permissions for the chosen save folder.
