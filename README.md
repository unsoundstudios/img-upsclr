# IMG-UPSCLR

IMG-UPSCLR is a desktop image upscaler for macOS and Windows.

## Overview

IMG-UPSCLR supports:
- Single image upscaling
- Batch upscaling up to 12 images per run
- Smart mode for mixed assets
- Real-ESRGAN AI enhancement paths

Supported formats:
- PNG
- JPG
- JPEG
- WEBP
- TIFF
- BMP

## Processing Modes

- `smart`: Recommended adaptive mode
- `crisp`: Detail-safe mode for UI, logos, and text
- `photo`: AI-first mode for photo and render assets
- `classic`: Original script-style behavior

Legacy aliases are still accepted in CLI:
- `auto` -> `smart`
- `ui` -> `crisp`
- `artwork` -> `photo`

## Project Structure

- `desktop_app.py`: Desktop UI
- `upscaler_core.py`: Processing core
- `esrgan_backend.py`: Real-ESRGAN backend integration
- `upscale_images.py`: CLI entry point
- `scripts/`: Build and run scripts
- `installers/windows/IMG-UPSCLR.nsi`: Windows NSIS installer script

## Run Desktop App (macOS)

```bash
./scripts/run_desktop_macos.sh
```

## Build Desktop App (macOS)

```bash
./scripts/build_macos_app.sh
```

Build output:
- `dist/IMG-UPSCLR.app`

## Build Desktop App (Windows)

Run on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_app.ps1
```

## Build Windows Installer (NSIS)

Run on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1
```

Optional version override:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1 -AppVersion 1.0.0
```

Installer output:
- `installers\windows\output\IMG-UPSCLR-Setup-<version>.exe`

## CLI Usage

Basic run:

```bash
python3 upscale_images.py --input _images --output _images/upscaled_10x --scale 10
```

Common options:
- `--mode smart|crisp|photo|classic`
- `--max-images 12`
- `--suffix _UPSCALED`
- `--overwrite`

## Notes

- The desktop app and CLI share the same processing engine.
- Real-ESRGAN backend is installed automatically by project scripts.
