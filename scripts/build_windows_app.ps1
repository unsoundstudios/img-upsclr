Param(
  [string]$Python = "python",
  [string]$VenvDir = ".venv-win",
  [string]$AppName = "IMG-UPSCLR"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $VenvDir)) {
  & $Python -m venv $VenvDir
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$esrganBundleDir = Join-Path (Resolve-Path ".").Path "build\esrgan_bundle"
$iconPath = Join-Path (Resolve-Path ".").Path "assets\img-upsclr_logo.ico"

if (!(Test-Path $iconPath)) {
  throw "Missing Windows app icon: $iconPath"
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements-desktop.txt
if (Test-Path $esrganBundleDir) { Remove-Item $esrganBundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $esrganBundleDir | Out-Null
& $venvPython scripts/install_esrgan_backend.py --target-dir $esrganBundleDir

if (Test-Path "dist\$AppName") { Remove-Item "dist\$AppName" -Recurse -Force }
if (Test-Path "build\$AppName") { Remove-Item "build\$AppName" -Recurse -Force }

& $venvPython -m PyInstaller `
  --clean `
  --noconfirm `
  --windowed `
  --name $AppName `
  --icon $iconPath `
  --add-data "assets\img-upsclr_logo.ico;assets" `
  --add-data "assets\img-upsclr_logo.png;assets" `
  --add-data "$esrganBundleDir;realesrgan" `
  desktop_app.py

Write-Host "Built Windows app folder at dist\$AppName"
