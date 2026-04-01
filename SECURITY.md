# Security Hardening Notes

This project has baseline hardening in code, plus a release checklist for distribution.

## Already Enforced

- Max upload count enforced server-side (`MAX_UPLOAD_FILES`, default `12`)
- Max file size enforced server-side (`MAX_FILE_SIZE_MB`, default `25`)
- Uploaded files are validated as real images server-side before processing
- Upscaling path is ESRGAN-only (no non-ESRGAN fallback engine)
- Uploaded filenames are sanitized
- CORS uses explicit allowlist by default (`ALLOWED_ORIGINS`)
- Trusted host header validation enabled (`TRUSTED_HOSTS`)
- Embedding is blocked by default (`FRAME_ANCESTORS='none'`)
- Security headers are set on responses:
  - `Content-Security-Policy`
  - `X-Frame-Options` (`DENY` by default, `SAMEORIGIN` when `FRAME_ANCESTORS='self'`)
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: no-referrer`
  - `Cross-Origin-Opener-Policy`
  - `Cross-Origin-Resource-Policy`
- Old job directories are pruned over time (`MAX_JOB_AGE_HOURS`)
- API docs are disabled by default in production (`ENABLE_API_DOCS=false`)

## Distribution Checklist (Recommended)

1. Lock dependencies to exact versions before release.
2. Run vulnerability scanning (`pip-audit`) in CI and fail on critical findings.
3. Run static security checks (Bandit/Semgrep) in CI.
4. Sign and notarize macOS app builds before public distribution.
5. Run container image scans (Trivy/Grype) on release builds.
6. Configure TLS and WAF/rate-limits at your hosting layer.
7. Set strict production env vars:
   - `ALLOWED_ORIGINS=https://your-domain.com`
   - `TRUSTED_HOSTS=your-domain.com`
   - `FRAME_ANCESTORS='none'` (or a specific trusted embed origin)
   - `ENABLE_API_DOCS=false`
8. Add centralized logging and alerting for failed/abnormal upload patterns.

## Trust Statement

No software can be guaranteed \"100% secure,\" but this project now includes concrete controls and a release process suitable for serious distribution when the checklist is completed.
