# IMG-UPSCLR

IMG-UPSCLR is production-focused image upscaling software for desktop and web.

It includes:
- A desktop app for macOS and Windows.
- A web app with the same processing core.
- Real-ESRGAN integration for AI upscaling paths.
- A consistent batch limit of 12 images per run.

## What It Does

- Upscales single images or batches.
- Supports PNG, JPG, JPEG, WEBP, TIFF, and BMP.
- Uses one shared processing engine across desktop, web, and CLI.
- Keeps output naming consistent with `_UPSCALED` suffix by default.

## Processing Modes

- `smart`: Recommended. Routes each image to the safest path based on content.
- `crisp`: Detail-safe path for UI, logos, text, and hard-edge assets.
- `photo`: AI-first path for photo and render content.
- `classic`: Original script-style behavior.

Backward-compatible mode aliases are accepted in CLI and API (`auto`, `ui`, `artwork`).

## Limits

- Maximum images per job: `12`
- Default max file size (web): `25 MB` per image
- Default scale range: `1.0` to `30.0`

## Repository Structure

- `desktop_app.py`: Desktop UI entry point (PySide6)
- `web_api.py`: FastAPI backend
- `web_frontend/`: Web UI
- `upscaler_core.py`: Shared processing engine
- `esrgan_backend.py`: Real-ESRGAN setup and execution
- `scripts/`: Build, packaging, notarization, and test scripts
- `installers/windows/IMG-UPSCLR.nsi`: NSIS installer script

## Quick Start

### Desktop on macOS

Run locally:

```bash
./scripts/run_desktop_macos.sh
```

Build app bundle:

```bash
./scripts/build_macos_app.sh
```

Output:

- `dist/IMG-UPSCLR.app`

### Desktop on Windows

Build app folder on Windows host:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_app.ps1
```

Build installer with NSIS on Windows host:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1
```

Optional version override:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1 -AppVersion 1.0.0
```

Installer output:

- `installers\windows\output\IMG-UPSCLR-Setup-<version>.exe`

### Web App Local Run

```bash
./scripts/run_web_local.sh
```

Open:

- `http://localhost:8000/app/`

### Docker Run

Build:

```bash
docker build -t img-upsclr .
```

Run:

```bash
docker run --rm -p 8000:8000 img-upsclr
```

Health endpoint:

- `GET /health`

## macOS Distribution

Store notarization credentials:

```bash
export APPLE_ID="you@example.com"
export TEAM_ID="ABCDE12345"
export APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
./scripts/setup_notary_profile.sh APPLE_NOTARY
```

Set signing identity:

```bash
export MACOS_CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export NOTARY_KEYCHAIN_PROFILE="APPLE_NOTARY"
```

Build, notarize, staple, package:

```bash
./scripts/build_notarized_macos_release.sh
```

Dry-run notarization validation:

```bash
DRY_RUN=1 ./scripts/notarize_macos_app.sh
```

## Test and Validation

Run smoke tests:

```bash
./scripts/test_local.sh
```

This validates:
- Desktop import and dry-run flow.
- Web job creation and completion.
- 12-image limit enforcement.

## Configuration

Key variables:

- `MAX_UPLOAD_FILES`
- `MAX_FILE_SIZE_MB`
- `MAX_JOB_AGE_HOURS`
- `ENABLE_API_DOCS`
- `ALLOWED_ORIGINS`
- `TRUSTED_HOSTS`
- `FRAME_ANCESTORS`

## Wix Integration

If you want the same UI in Wix, embed the deployed `/app/` route in an HTML iframe.

Deployment requirements:
- Host this app publicly (for example Render using `render.yaml`).
- Set `ALLOWED_ORIGINS` to your Wix domains.
- Set `TRUSTED_HOSTS` to your API host/domain.
- Set `FRAME_ANCESTORS` to include your Wix domains.

Then in Wix:
- Add an HTML iframe element.
- Set iframe URL to `https://your-api-domain/app/`.
- Resize for desktop and mobile layouts.

## Security and Hardening

Current baseline includes:
- Server-side image validation.
- Upload filename sanitization.
- CORS allowlist controls.
- Trusted host validation.
- Security response headers.
- Automatic cleanup of old web job folders.

Read:
- `SECURITY.md`
- `DISTRIBUTION_CHECKLIST.md`

## Legal and Licensing

Generate third-party notices:

```bash
python3 scripts/generate_third_party_notices.py
```

Output:
- `THIRD_PARTY_NOTICES.md`

Legal templates:
- `EULA_TEMPLATE.md`
- `PRIVACY_POLICY_TEMPLATE.md`
- `LICENSE`

Use legal counsel before commercial distribution.

## CI

Workflow:
- `.github/workflows/release-validation.yml`

It runs:
- Web smoke tests.
- macOS build checks.
- Windows app build and NSIS installer build.
