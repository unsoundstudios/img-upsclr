Param(
  [string]$Python = "python",
  [string]$VenvDir = ".venv-win",
  [string]$AppName = "IMG-UPSCLR"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [ScriptBlock]$Command,
    [Parameter(Mandatory = $true)]
    [string]$Label
  )

  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

if (Test-Path $VenvDir) {
  $existingVenvPython = Join-Path $VenvDir "Scripts\python.exe"
  if (!(Test-Path $existingVenvPython)) {
    Remove-Item $VenvDir -Recurse -Force
  } else {
    & $existingVenvPython --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
      Remove-Item $VenvDir -Recurse -Force
    }
  }
}

if (!(Test-Path $VenvDir)) {
  & $Python -m venv $VenvDir
  if ($LASTEXITCODE -ne 0) {
    throw "Python venv creation failed with exit code $LASTEXITCODE"
  }
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$esrganBundleDir = Join-Path (Resolve-Path ".").Path "build\esrgan_bundle"
$iconPath = Join-Path (Resolve-Path ".").Path "assets\img-upsclr_logo.ico"

if (!(Test-Path $iconPath)) {
  throw "Missing Windows app icon: $iconPath"
}

Invoke-Checked { & $venvPython -m pip install --upgrade pip } "pip upgrade"
Invoke-Checked { & $venvPython -m pip install -r requirements-desktop.txt } "dependency install"
if (Test-Path $esrganBundleDir) { Remove-Item $esrganBundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $esrganBundleDir | Out-Null
Invoke-Checked { & $venvPython scripts/install_esrgan_backend.py --target-dir $esrganBundleDir } "Real-ESRGAN install"

if (Test-Path "dist\$AppName") { Remove-Item "dist\$AppName" -Recurse -Force }
if (Test-Path "build\$AppName") { Remove-Item "build\$AppName" -Recurse -Force }

Invoke-Checked {
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
} "PyInstaller build"

Write-Host "Built Windows app folder at dist\$AppName"
