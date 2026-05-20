Param(
  [string]$NsisCompiler = "C:\Program Files (x86)\NSIS\makensis.exe",
  [string]$Python = "python",
  [string]$AppName = "IMG-UPSCLR",
  [string]$AppVersion = "0.0.1"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $NsisCompiler)) {
  throw "NSIS compiler not found: $NsisCompiler"
}

& powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_app.ps1 -Python $Python -AppName $AppName
if ($LASTEXITCODE -ne 0) {
  throw "Windows app build failed with exit code $LASTEXITCODE"
}
New-Item -ItemType Directory -Path .\installers\windows\output -Force | Out-Null

& $NsisCompiler `
  /DAPP_NAME="$AppName" `
  /DAPP_VERSION="$AppVersion" `
  .\installers\windows\IMG-UPSCLR.nsi
if ($LASTEXITCODE -ne 0) {
  throw "NSIS installer build failed with exit code $LASTEXITCODE"
}

Write-Host "Built Windows NSIS installer in installers\windows\output"
