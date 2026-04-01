# IMG-UPSCLR

IMG-UPSCLR is an image upscaler for desktop and web.

It supports:
- Single image upscaling
- Batch upscaling up to 12 images per run
- Smart mode for mixed asset types
- Real-ESRGAN AI enhancement paths

## Features

- Modes: `smart`, `crisp`, `photo`, `classic`
- Formats: PNG, JPG, JPEG, WEBP, TIFF, BMP
- Default output suffix: `_UPSCALED`
- Shared core engine across desktop, web, and CLI

## Project Files

- `desktop_app.py`: Desktop application UI
- `web_api.py`: Web backend (FastAPI)
- `web_frontend/`: Web user interface
- `upscaler_core.py`: Processing core
- `esrgan_backend.py`: Real-ESRGAN integration
- `scripts/`: Build and run scripts

## Desktop Use (macOS)

Run locally:

```bash
./scripts/run_desktop_macos.sh
```

Build app:

```bash
./scripts/build_macos_app.sh
```

Output:

- `dist/IMG-UPSCLR.app`

## Desktop Use (Windows)

Build app on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_app.ps1
```

Build NSIS installer on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1
```

Output:

- `installers\windows\output\IMG-UPSCLR-Setup-<version>.exe`

## Web Use (Local)

Run:

```bash
./scripts/run_web_local.sh
```

Open:

- `http://localhost:8000/app/`

## Docker

Build:

```bash
docker build -t img-upsclr .
```

Run:

```bash
docker run --rm -p 8000:8000 img-upsclr
```

## Wix Embed

To use the same web UI on Wix:

1. Deploy this app to a public host.
2. Use your hosted URL `https://your-api-domain/app/`.
3. In Wix, add an Embed a Site element.
4. Set the iframe URL to `https://your-api-domain/app/`.
5. Publish your Wix page.
