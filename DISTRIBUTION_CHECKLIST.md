# Distribution Checklist (Production Release)

Use this checklist before shipping IMG-UPSCLR to end users.

## Product Quality

1. Run local smoke tests: `./scripts/test_local.sh`
2. Validate desktop workflows:
   - single image run
   - multi-image run (2-12)
   - rejected run (>12 images)
3. Validate web workflows:
   - upload 1 image
   - upload 12 images
   - reject 13 images
   - download ZIP works

## Security

1. Review `SECURITY.md` controls and environment variables.
2. Run dependency vulnerability checks (`pip-audit`) for:
   - `requirements-web.txt`
   - `requirements-desktop.txt`
3. Run static checks (Bandit/Semgrep) on release branch.
4. Confirm production values:
   - `ALLOWED_ORIGINS`
   - `TRUSTED_HOSTS`
   - `ENABLE_API_DOCS=false`

## Legal and Compliance

1. Regenerate third-party notices:
   - `python3 scripts/generate_third_party_notices.py`
2. Review `THIRD_PARTY_NOTICES.md` with legal counsel.
3. Finalize:
   - `EULA_TEMPLATE.md` -> your final EULA
   - `PRIVACY_POLICY_TEMPLATE.md` -> your final privacy policy
4. Ensure installer/app package includes:
   - `LICENSE`
   - `THIRD_PARTY_NOTICES.md`
   - security notes and legal docs

## macOS Distribution

1. Build app: `./scripts/build_macos_app.sh`
2. Verify signature:
   - `codesign --verify --deep --strict dist/IMG-UPSCLR.app`
3. Configure notary profile and Developer ID identity:
   - `./scripts/setup_notary_profile.sh APPLE_NOTARY`
   - `export MACOS_CODESIGN_IDENTITY="Developer ID Application: ..."`
4. Notarize and staple:
   - `./scripts/notarize_macos_app.sh`
5. Package release:
   - `./scripts/package_release_bundle.sh`

## Windows Distribution

1. Build app on Windows host:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_app.ps1`
2. Build installer on Windows host:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1`
   - requires NSIS (`makensis.exe`)
3. Sign installer and executable with your code-signing cert.
4. Validate install/uninstall in clean VM.

## Website Distribution

1. Build image:
   - `docker build -t img-upsclr .`
2. Runtime check:
   - `docker run --rm -p 8000:8000 img-upsclr`
   - `GET /health`
3. Deploy with TLS and monitoring enabled.
