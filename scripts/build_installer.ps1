param(
    [string]$PythonExe = "c:/Users/schal/Documents/IGS Code/.venv-1/Scripts/python.exe",
    [string]$InnoCompiler = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[1/3] Building app with PyInstaller..."
& $PythonExe -m PyInstaller --noconfirm --clean --name IGSMapAnnotator --windowed --icon="assets\IGS.ico" --add-data "assets;assets" --add-data "Annotassets;Annotassets" UIhandling.py

if (-not (Test-Path "dist\IGSMapAnnotator\IGSMapAnnotator.exe")) {
    throw "Build failed: dist\\IGSMapAnnotator\\IGSMapAnnotator.exe not found."
}

Write-Host "[2/3] Verifying Inno Setup compiler..."
if (-not (Test-Path $InnoCompiler)) {
    throw "Inno Setup compiler not found at '$InnoCompiler'. Install Inno Setup 6 or pass -InnoCompiler with the correct path."
}

Write-Host "[3/3] Building installer..."
& $InnoCompiler "installer\IGSMapAnnotator.iss"

Write-Host "Done. Installer output folder: installer_output"
