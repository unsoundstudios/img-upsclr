#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="${ROOT_DIR}/release"
APP_SLUG="IMG-UPSCLR"
APP_PATH="${ROOT_DIR}/dist/${APP_SLUG}.app"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${RELEASE_DIR}/${APP_SLUG}-${STAMP}"

mkdir -p "${OUT_DIR}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle at ${APP_PATH}. Run scripts/build_macos_app.sh first."
  exit 1
fi

cp -R "${APP_PATH}" "${OUT_DIR}/${APP_SLUG}.app"
cp "${ROOT_DIR}/THIRD_PARTY_NOTICES.md" "${OUT_DIR}/THIRD_PARTY_NOTICES.md"
cp "${ROOT_DIR}/SECURITY.md" "${OUT_DIR}/SECURITY.md"
cp "${ROOT_DIR}/LICENSE" "${OUT_DIR}/LICENSE"

(
  cd "${RELEASE_DIR}"
  zip -r "${APP_SLUG}-${STAMP}-macOS.zip" "${APP_SLUG}-${STAMP}" >/dev/null
  shasum -a 256 "${APP_SLUG}-${STAMP}-macOS.zip" > "${APP_SLUG}-${STAMP}-macOS.sha256"
)

echo "Created release package:"
echo "  ${RELEASE_DIR}/${APP_SLUG}-${STAMP}-macOS.zip"
echo "  ${RELEASE_DIR}/${APP_SLUG}-${STAMP}-macOS.sha256"
