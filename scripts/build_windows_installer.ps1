Param(
  [string]$NsisCompiler = "C:\Program Files (x86)\NSIS\makensis.exe",
  [string]$AppName = "IMG-UPSCLR",
  [string]$AppVersion = "1.0.0"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $NsisCompiler)) {
  throw "NSIS compiler not found: $NsisCompiler"
}

& powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_app.ps1 -AppName $AppName
New-Item -ItemType Directory -Path .\installers\windows\output -Force | Out-Null

& $NsisCompiler `
  /DAPP_NAME="$AppName" `
  /DAPP_VERSION="$AppVersion" `
  .\installers\windows\IMG-UPSCLR.nsi

Write-Host "Built Windows NSIS installer in installers\windows\output"
